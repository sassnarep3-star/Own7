#!/usr/bin/env python3
"""Deterministic repository scan for the review desk (no network, no timestamps).

Writes nfl-review-1c6816a0/data/scan.json. `--check` recomputes it and fails if the committed
file differs, so the findings cannot silently drift from the tree they describe.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "nfl-review-1c6816a0" / "data" / "scan.json"
WORKFLOW = ROOT / ".github" / "workflows" / "check.yml"
REGISTER = ROOT / "research" / "nfl-decision-readiness.json"
SOURCES = ROOT / "research" / "sources.json"
EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".artifacts", "nfl-review-1c6816a0"}

# Official host classes. A host is official only if it is an NFL league domain or a member-club
# domain. GitHub is the repository itself (a repo artifact, not an external official source).
NFL_HOST_SUFFIX = ("nfl.com",)
# Member-club hosts are allowlisted ONLY for the clubs the decision register actually cites.
# Any other club domain is classed NOT OFFICIAL (unclassified) until it is checked.
CLUB_HOSTS = {"www.atlantafalcons.com", "www.chicagobears.com"}
REPO_HOST = "github.com"
FLAG_NAME = re.compile(r"flag|review", re.I)
NON_FACT_PREFIXES = ("nba", "rent", "rental", "market-evidence", "handoff")
DR_ID = re.compile(r"DR-\d{2}")


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def walk_files():
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        parts = set(p.relative_to(ROOT).parts)
        if parts & EXCLUDE_DIRS:
            continue
        yield p


def host_class(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host == REPO_HOST:
        return "repository (not an external official source)"
    if host.endswith(NFL_HOST_SUFFIX):
        return "official: NFL"
    if host in CLUB_HOSTS:
        return "official: member club"
    return "NOT OFFICIAL (unclassified)"


def ci_commands() -> list[str]:
    """The research-static reproduction commands (same parser as run_ci.py)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from run_ci import extract_commands  # noqa: E402  (single source of truth)
    return [x["command"] for x in extract_commands(WORKFLOW.read_text(encoding="utf-8"))]


def desk_of(artifact: str) -> str:
    """Top-level folder of an artifact, or 'root' for files at the repository root."""
    return artifact.split("/")[0] if "/" in artifact else "root"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    files = list(walk_files())
    rels = [rel(p) for p in files]
    cmds = ci_commands()
    cmd_text = "\n".join(cmds)

    # S1: CI commands that reference a python script that does not exist.
    missing_scripts = []
    for c in cmds:
        m = re.search(r"python(?:3)?\s+(?!-m)(\S+\.py)", c)
        if m and not (ROOT / m.group(1)).exists():
            missing_scripts.append({"command": c, "missing": m.group(1)})

    # S2: top-level desks that publish HTML but are not referenced by any CI command.
    desks = {}
    for r in rels:
        top = r.split("/")[0]
        if "/" in r and r.endswith(".html"):
            desks.setdefault(top, 0)
            desks[top] += 1
    # A desk is "in CI" when its folder name appears in a reproduction command.
    not_in_ci = sorted(d for d in desks if d.startswith("nfl") and d not in cmd_text)
    gamebook_in_ci = "nfl-gamebook-5213243e" in cmd_text

    # S3: out-of-scope content for an NFL repository (named by file path, not judged).
    out_of_scope = sorted(r for r in rels if (
        r.startswith("nba_lab/") or r.startswith("nba-") or r.startswith("rental/")
        or re.match(r"^rent[-.]", r) or re.match(r"^rental", r) or r.startswith("market-evidence/")
        or r.startswith("handoff/") or r == "data/jokic-games-2025-26.csv"
        or r.startswith("research/rent") or r.startswith("research/nba")
    ) and r.endswith((".html", ".md", ".py", ".csv", ".json", ".txt")))

    # S4: executive-summary and flagged/review pages (fragmentation of shared outputs).
    exec_summaries = sorted(r for r in rels if "executive" in r.lower() and r.endswith((".html", ".md")))
    flagged_pages = sorted(r for r in rels if r.endswith(".html") and "flag" in Path(r).name.lower())

    # S5: parallel readiness/ledger/week-11 desks covering overlapping topics.
    parallel_prefixes = ("nfl-readiness", "nfl-ledger", "nfl-week11", "nfl-w11", "nfl-fresh", "nfl-injury-recon", "nfl-reconcile")
    parallel_desks = sorted({r.split("/")[0] for r in rels if r.split("/")[0].startswith(parallel_prefixes)})

    # S6: two canonical-looking results files with different row counts.
    results_csv = {}
    for r in rels:
        if r.startswith("nfl-results/data/") and r.endswith(".csv"):
            with (ROOT / r).open(newline="", encoding="utf-8") as fh:
                results_csv[r] = max(sum(1 for _ in csv.reader(fh)) - 1, 0)

    # S7: register checks.
    reg = json.loads(REGISTER.read_text(encoding="utf-8"))
    srcs = {s["id"]: s for s in json.loads(SOURCES.read_text(encoding="utf-8"))}
    index_html = (ROOT / "index.html").read_text(encoding="utf-8")
    index_ids = set(DR_ID.findall(index_html))
    rows = []
    statuses = {}
    for r in reg["requirements"]:
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1
        artifact = r.get("artifact") or ""
        exists = (ROOT / artifact).is_file() if artifact else False
        hosts = []
        for sid in r.get("source_ids", []):
            s = srcs.get(sid)
            if s is None:
                hosts.append({"id": sid, "class": "UNREGISTERED"})
            else:
                hosts.append({"id": sid, "host": urlparse(s["url"]).netloc, "class": host_class(s["url"]), "url": s["url"]})
        desk = desk_of(artifact)
        if desk == "root":
            ci_status = "scripts/check_site.py (root build)"
        elif desk in cmd_text:
            ci_status = "referenced by check.yml"
        else:
            ci_status = "not referenced by check.yml"
        rows.append({
            "id": r["id"],
            "status": r["status"],
            "artifact": artifact,
            "artifact_exists": exists,
            "artifact_is_open_items_page": bool(FLAG_NAME.search(Path(artifact).name)) if artifact else False,
            "sources": hosts,
            "desk_ci": ci_status,
            "listed_on_index": r["id"] in index_ids,
        })
    conflicts = [x["id"] for x in rows if x["status"] == "Implemented" and x["artifact_is_open_items_page"]]
    non_official = [x["id"] for x in rows if any(h.get("class") == "NOT OFFICIAL" or h.get("class") == "UNREGISTERED" for h in x["sources"])]

    doc = {
        "schema": "nfl-review-1c6816a0/scan/1",
        "note": "Deterministic scan of the committed tree. No network, no timestamps. Findings are counts and paths, not judgements about truth.",
        "ci_commands_in_check_yml": len(cmds),
        "ci_commands_missing_script": missing_scripts,
        "html_desks_not_in_ci": not_in_ci,
        "gamebook_desk_in_ci": gamebook_in_ci,
        "out_of_scope_paths": out_of_scope,
        "out_of_scope_count": len(out_of_scope),
        "executive_summary_files": exec_summaries,
        "flagged_or_review_pages": flagged_pages,
        "parallel_desks": parallel_desks,
        "results_csv_row_counts": results_csv,
        "register": {
            "rows": len(rows),
            "status_counts": dict(sorted(statuses.items())),
            "ids_listed_on_index": len(index_ids),
            "implemented_rows_with_open_items_artifact": conflicts,
            "rows_with_non_official_or_unregistered_source": non_official,
            "items": rows,
        },
    }
    text = json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("scan.json is stale: run python nfl-review-1c6816a0/scan.py", file=sys.stderr)
            return 1
        print("scan.json reproduces byte-identically")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {rel(OUT)}: rows={len(rows)} out_of_scope={len(out_of_scope)} flagged_pages={len(flagged_pages)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
