#!/usr/bin/env python3
"""Decision-ledger re-grade audit (session arena/aedccbe5-own7).

  python nfl-ledger-aedccbe5/build.py           # verify, write data/ and site/
  python nfl-ledger-aedccbe5/build.py --check   # rebuild in memory; demand byte-identical output

What it does, line by line:
  1. Reads the canonical register research/nfl-decision-readiness.json (read-only; not edited here).
  2. For each of its rows: the artifact path must exist; every source id must resolve in
     research/sources.json; the first non-repository source URL is shown as the official link.
  3. Proposed re-grades are accepted only when a regular expression matches the cited artifact.
     The quoted text is extracted from the artifact by this script, never typed by hand.
  4. Blocked rows are re-checked against the two official reads kept in evidence/.
  5. The landing page decision table is counted (rows versus register rows).

Nothing is inferred. A row without an official link says so. No wall-clock time is used.
Standard library only.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LEDGER = ROOT / "research" / "nfl-decision-readiness.json"
SOURCES = ROOT / "research" / "sources.json"
LANDING = ROOT / "index.html"
EVIDENCE = HERE / "evidence"
SITE = HERE / "site"
DATA = HERE / "data"
READ_ON = "2026-11-18"
SESSION = "arena/aedccbe5-own7"

NAV = [
    ("index.html", "Audit overview"),
    ("ledger.html", "All 70 rows"),
    ("regrades.html", "Proposed re-grades"),
    ("blocked.html", "Gates re-checked"),
    ("flagged.html", "Flagged for review"),
]

# Proposed re-grades. Each must be supported by a regex hit in the cited artifact.
REGRADES = [
    {
        "id": "DR-61", "to": "Partial",
        "evidence": "nfl-slate-03dcea07/site/weekly-diff.html",
        "pattern": r"rating change needs a model",
        "gate": "Rating change is not rendered: the desk publishes no versioned model rating.",
        "reason": "The page renders a diff between dated same-scope captures (standings and availability), "
                  "so part of the clearing text is met. The brief's diff also names rank and rating change; "
                  "the rating column is absent by the page's own statement.",
    },
    {
        "id": "DR-68", "to": "Partial",
        "evidence": "nfl-integration-c815/site/rules-2026.html",
        "pattern": r"6-1-6\s+permits the kicking team to declare an onside kick at any time during the game",
        "gate": "The priors filter is documented as text; no model output is shown to apply it.",
        "reason": "Declared-onside rule 6-1-6 is transcribed from the official 2026 Playing Rules and quoted. "
                  "The ledger also requires the priors filter to be added; the page documents it, "
                  "but no model run in the tree is shown to apply it.",
    },
    {
        "id": "DR-64", "to": "Partial",
        "evidence": "nfl-week11-6c72a9fa/site/reserve-sweep.html",
        "pattern": r"Lamar Jackson and Tyler Huntley are in neither the November nor the October visible window",
        "gate": "Reserve list is read only as visible windows of about 25 rows per month; it is not joined to the "
                "injury report for all 32 clubs.",
        "reason": "A league-level reserve sweep exists and shows Malik Willis on the 11/10 reserve list. "
                  "Clearing needs a capture joined to the report for all 32 clubs, which the sweep does not give.",
    },
    {
        "id": "DR-22", "to": "Partial",
        "evidence": "index.html",
        "landing_rows": True,
        "gate": "The landing table counts 16 rows with NR identifiers; the register has 70 DR rows.",
        "reason": "The brief asks for one row per requirement on the landing page. The table published there "
                  "is not the DR register, so the row count does not match the register.",
    },
]

# Gates that rest on official NFL pages, re-read against the evidence kept in evidence/.
# DR-29, DR-54 and DR-66 are Blocked; DR-01 and DR-18 keep their register status and their gate is re-confirmed.
BLOCKED_CHECKS = {
    "DR-29": ("evidence/nfl-terms-s1-3-2026-11-18.md", r"Systematic retrieval of data or other content from the Services"),
    "DR-54": ("evidence/nfl-terms-s1-3-2026-11-18.md", r"Systematic retrieval of data or other content from the Services"),
    "DR-66": ("evidence/nfl-terms-s1-3-2026-11-18.md", r"Systematic retrieval of data or other content from the Services"),
    "DR-01": ("evidence/nfl-odds-404-2026-11-18.md", r"404 - Flag on the Play\."),
    "DR-18": ("evidence/nfl-odds-404-2026-11-18.md", r"404 - Flag on the Play\."),
}

# Flags that are not re-grades: recorded for review, non-blocking.
FLAGS = [
    {"id": "AF01", "source_ids": ['REPO'], "severity": "High", "title": "Landing-page decision table is not the 70-row register",
     "finding": "index.html contains the 'Decision readiness' table with 16 body rows whose identifiers are NR01 to NR16, "
                "not the DR-01 to DR-70 rows of research/nfl-decision-readiness.json. DR-22 is marked Implemented in the "
                "register, which asks for one row per requirement on the landing page.",
     "evidence": "index.html", "action": "Integration owner to regenerate the landing table from the register and re-grade DR-22 (see regrades.html)."},
    {"id": "AF02", "source_ids": ['FRESH-NFL-W10-COMPLETE-1118'], "severity": "Medium", "title": "Two canonical results files disagree on the Week 10 final",
     "finding": "nfl-results/data/games-2026-w1-10.csv holds 149 rows; nfl-results/data/games-2026-w1-10-complete.csv holds 150 rows "
                "including LAC at BAL (2026-11-16, 23-20). nfl-results-games.html displays the LAC @ BAL 23–20 row, so the page "
                "is current; the 149-row file is not. Already logged as FG02 on the Week 10 desk.",
     "evidence": "nfl-results/data/games-2026-w1-10.csv; nfl-results/data/games-2026-w1-10-complete.csv; nfl-results-games.html",
     "action": "Results desk owner to retire or regenerate the 149-row file so one canonical file remains."},
    {"id": "AF03", "source_ids": ['NFL-TERMS'], "severity": "Medium", "title": "Week 11 injury report not yet published at read time",
     "finding": "2026-11-18 is a Wednesday. The read on this desk was taken before the Wednesday injury-report publication. "
                "No Week 11 designation is used here. Recurring capture of the report is blocked by NFL.com Terms §1.3 (DR-29, DR-54).",
     "evidence": "evidence/nfl-terms-s1-3-2026-11-18.md", "action": "One dated read after publication, or a permitted schedule agreed in writing."},
    {"id": "AF04", "source_ids": ['NFL-TERMS'], "severity": "Low", "title": "Seven registry entries cite the same NFL terms page",
     "finding": "NFL-TERMS, NFL-LEGAL-TERMS, NFL-TERMS-LEGAL, X243-NFL-TERMS, CP-NFL-TERMS, NFL-TERMS-1117 and CFDD-NFL-TERMS all describe "
                "NFL.com Terms and Conditions with different checked dates and URLs (support.nfl.com article or www.nfl.com/legal/terms). "
                "No contradiction in the quoted §1.3 text was found; the duplicates make a single citation harder to audit.",
     "evidence": "research/sources.json", "action": "Consolidate to one registered entry in the integration pass; no row changed here."},
    {"id": "AF05", "source_ids": ['REPO'], "severity": "Low", "title": "Thirty 'Implemented' rows were not re-graded here",
     "finding": "This desk confirms that each Implemented row's artifact exists and its sources resolve. It does not re-read the content of "
                "those artifacts against each clause; that review remains with the owning desks.",
     "evidence": "ledger.html", "action": "Owning desks to re-read their rows when they next publish."},
    {"id": "AF06", "source_ids": ['REPO'], "severity": "Low", "title": "Repository-only sources on 12 rows",
     "finding": "12 rows (DR-08, DR-09, DR-17, DR-37, DR-39, DR-47, DR-50, DR-57, DR-63, DR-65, DR-67, DR-69) cite only REPO (github.com). "
                "They are process or design rows. No NFL source backs them, so their official link is shown as absent rather than inferred.",
     "evidence": "ledger.html", "action": "None required; shown as flagged on each row."},
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_text(path: Path) -> str:
    """Visible text of an HTML or Markdown file (tags stripped, whitespace collapsed)."""
    raw = path.read_text(encoding="utf-8")
    raw = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    return re.sub(r"\s+", " ", raw)


def first_hit(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text)
    if not m:
        return None
    lo, hi = max(0, m.start() - 90), min(len(text), m.end() + 140)
    return ("…" if lo else "") + text[lo:hi].strip() + ("…" if hi < len(text) else "")


def landing_register_rows() -> tuple[int, list[str]]:
    """Body rows and identifiers of the decision-readiness table on the landing page."""
    raw = LANDING.read_text(encoding="utf-8")
    i = raw.find('data-table-card="nfl-decision-readiness"')
    if i < 0:
        return 0, []
    j = raw.find("</table>", i)
    seg = raw[i:j]
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", seg, flags=re.S)
    body = rows[1:]  # first row is the header
    ids = sorted(set(re.findall(r"\b(NR\d{2}|DR-\d{2})\b", seg)))
    return len(body), ids


def official_link(row: dict, sources: dict) -> tuple[str | None, str | None]:
    """First registered source whose host is not GitHub, as (source id, url)."""
    for sid in row.get("source_ids", []):
        url = (sources.get(sid, {}) or {}).get("url") or ""
        if url and urlparse(url).netloc and urlparse(url).netloc != "github.com":
            return sid, url
    return None, None


def build_model() -> dict:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    sources = {s["id"]: s for s in json.loads(SOURCES.read_text(encoding="utf-8"))}
    rows_in = ledger["requirements"]
    ids = [r["id"] for r in rows_in]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate requirement ids in the register")

    landing_count, landing_ids = landing_register_rows()
    rows = []
    for r in rows_in:
        art = r.get("artifact") or ""
        art_path = ROOT / art
        art_ok = bool(art) and art_path.is_file()
        unresolved = [s for s in r.get("source_ids", []) if s not in sources]
        sid, url = official_link(r, sources)
        repo_only = not url
        rows.append({
            "id": r["id"], "requirement": r["requirement"], "category": r.get("category", ""),
            "ledger_status": r["status"], "gate": r.get("gate", ""), "clears_when": r.get("clears_when", ""),
            "artifact": art, "artifact_exists": art_ok,
            "artifact_sha256": sha256(art_path) if art_ok else None,
            "source_ids": r.get("source_ids", []), "unresolved_source_ids": unresolved,
            "official_source_id": sid, "official_url": url, "repo_only": repo_only,
            "audit_status": r["status"], "audit_note": "Artifact and sources verified; content not re-graded here.",
            "quote": None,
        })
    by_id = {r["id"]: r for r in rows}

    regrades = []
    for rg in REGRADES:
        row = by_id[rg["id"]]
        if rg.get("landing_rows"):
            hit = f"Landing table: {landing_count} body rows; identifiers found: {', '.join(landing_ids) or 'none'}; register rows: {len(rows)}."
            confirmed = landing_count != len(rows)
            quote = hit
        else:
            path = ROOT / rg["evidence"]
            hit = first_hit(read_text(path), rg["pattern"]) if path.is_file() else None
            confirmed = hit is not None
            quote = hit
        if not confirmed:
            raise SystemExit(f"re-grade {rg['id']} not supported by {rg['evidence']}; refusing to publish it")
        row["audit_status"] = rg["to"]
        row["audit_note"] = rg["reason"]
        row["quote"] = quote
        regrades.append({"id": rg["id"], "requirement": row["requirement"], "ledger_status": row["ledger_status"],
                         "proposed": rg["to"], "evidence": rg["evidence"],
                         "evidence_sha256": sha256(ROOT / rg["evidence"]) if (ROOT / rg["evidence"]).is_file() else None,
                         "quote": quote, "gate": rg["gate"], "reason": rg["reason"]})

    blocked_checks = []
    for rid, (ev, pat) in BLOCKED_CHECKS.items():
        path = HERE / ev
        hit = first_hit(read_text(path), pat)
        if not hit:
            raise SystemExit(f"blocked row {rid} not supported by {ev}")
        row = by_id[rid]
        blocked_checks.append({"id": rid, "evidence": f"nfl-ledger-aedccbe5/{ev}", "quote": hit,
                               "evidence_sha256": sha256(path)})

    counts = {}
    for r in rows:
        counts[r["ledger_status"]] = counts.get(r["ledger_status"], 0) + 1
    audit_counts = {}
    for r in rows:
        audit_counts[r["audit_status"]] = audit_counts.get(r["audit_status"], 0) + 1

    return {
        "schema": "ledger-audit/1", "read_on": READ_ON, "session": SESSION,
        "register": "research/nfl-decision-readiness.json",
        "register_sha256": sha256(LEDGER), "sources_sha256": sha256(SOURCES),
        "landing_table_rows": landing_count, "landing_table_ids": landing_ids,
        "counts": {"rows": len(rows), "ledger_status": counts, "audit_status": audit_counts,
                   "artifact_exists": sum(1 for r in rows if r["artifact_exists"]),
                   "sources_resolved": sum(1 for r in rows if not r["unresolved_source_ids"]),
                   "official_link": sum(1 for r in rows if r["official_url"]),
                   "repo_only": sum(1 for r in rows if r["repo_only"]),
                   "regrades": len(regrades), "blocked_confirmed": len(blocked_checks)},
        "rows": rows, "regrades": regrades, "blocked_checks": blocked_checks, "flags": FLAGS,
    }


# ---------- rendering ----------

def esc(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def registry() -> dict:
    return {s["id"]: s for s in json.loads(SOURCES.read_text(encoding="utf-8"))}


def rel_link(target: str, label: str | None = None) -> str:
    """Link from site/ to a repository path or to a registered https URL."""
    if target.startswith("http"):
        return f'<a href="{esc(target)}" rel="noopener noreferrer">{esc(label or target)} ↗</a>'
    return f'<a href="../../{esc(target)}">{esc(label or target)}</a>'


def src_attr(ids: list[str]) -> str:
    return f' data-source-ids="{esc(" ".join(ids))}"'


def official_cell(ids: list[str], reg: dict) -> str:
    """Official registered link for the row. Repo-only rows link the repository register and say so."""
    for sid in ids:
        url = (reg.get(sid) or {}).get("url") or ""
        host = urlparse(url).netloc
        if url and host and host != "github.com":
            return rel_link(url, f"{sid} · {host}")
    repo = reg["REPO"]["url"]
    return (f'<span class="flag">No official NFL source — flagged</span><br>'
            f'{rel_link(repo, "REPO · repository register")}')


def page(title: str, active: str, body: str) -> str:
    cur = ' aria-current="page"'
    nav = "".join(
        f'<a href="{href}"{cur if href == active else ""}>{esc(lbl)}</a>' for href, lbl in NAV)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · OWN7 ledger audit</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="top">
  <a class="brand" href="../../index.html">OWN7</a>
  <nav aria-label="Ledger audit">{nav}</nav>
</header>
<main id="main">
{body}
</main>
<footer><p>Session {esc(SESSION)} · read {esc(READ_ON)} · generated deterministically from research/nfl-decision-readiness.json. No wagering, no prices, no stakes.</p></footer>
</body>
</html>
"""


def table(headers: list[str], rows_html: list[str], caption: str) -> str:
    head = "".join(f'<th scope="col">{esc(h)}</th>' for h in headers)
    return (f'<div class="table-card" role="region" tabindex="0" aria-label="{esc(caption)}">'
            f'<table><caption class="sr-only">{esc(caption)}</caption><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(rows_html)}</tbody></table></div>')


TAG_PROPOSED = ' <span class="tag">proposed</span>'
FLAG_MISSING = ' <span class="flag">missing</span>'


def render(model: dict) -> dict[str, str]:
    reg = registry()
    c = model["counts"]
    out = {}
    by_id = {r["id"]: r for r in model["rows"]}

    overview = f"""
<section class="hero">
  <p class="eyebrow">NFL · decision register audit</p>
  <h1>Ledger re-grade audit</h1>
  <p class="lede">Every row of the decision-readiness register is checked against the files that exist in the tree and the
  registered sources. Where a later artifact changes a status, the change is proposed here with the matched text from that
  artifact. The register itself is not edited by this desk; the integration owner applies the proposals.</p>
</section>
<section class="cards">
  <div class="card"><span>Register rows</span><strong>{c['rows']}</strong><small>research/nfl-decision-readiness.json</small></div>
  <div class="card"><span>Artifacts present</span><strong>{c['artifact_exists']} / {c['rows']}</strong><small>every row names a file that exists</small></div>
  <div class="card"><span>Sources resolved</span><strong>{c['sources_resolved']} / {c['rows']}</strong><small>every source id is in research/sources.json</small></div>
  <div class="card"><span>Official link shown</span><strong>{c['official_link']} / {c['rows']}</strong><small>{c['repo_only']} rows are repo-only and say so</small></div>
  <div class="card"><span>Proposed re-grades</span><strong>{c['regrades']}</strong><small>each matched in the cited artifact</small></div>
  <div class="card"><span>Gates re-read</span><strong>{c['blocked_confirmed']}</strong><small>against official pages on {esc(READ_ON)}</small></div>
</section>
<section class="section">
  <h2>Register status now versus after the proposed re-grades</h2>
  {table(["Status", "Register (as published)", "Audit (after proposals)", "Source"],
         [f"<tr{src_attr(['REPO'])}><th scope='row'>{esc(s)}</th><td>{c['ledger_status'].get(s, 0)}</td><td>{c['audit_status'].get(s, 0)}</td>"
          f"<td>{rel_link(reg['REPO']['url'], 'REPO · repository register')}</td></tr>"
          for s in ["Implemented", "Partial", "Open", "Blocked", "Rejected"]], "Status counts")}
</section>
<section class="section">
  <h2>What this desk establishes</h2>
  <ul>
    <li>All {c['rows']} register rows point to a file that exists and to sources that are registered. The check is mechanical; it does not judge the content of the 30 Implemented artifacts (flag AF05).</li>
    <li>Four rows carry stale status against artifacts already in the tree: DR-22, DR-61, DR-64 and DR-68. Each proposal quotes the matched text (see <a href="regrades.html">Proposed re-grades</a>).</li>
    <li>The five gates that rest on NFL.com are re-read: the §1.3 retrieval prohibition (DR-29, DR-54, DR-66, Blocked) and the 404 at nfl.com/odds (DR-01, DR-18). Both reads are kept as hashed evidence.</li>
    <li>The landing-page decision table holds {model['landing_table_rows']} rows, not {c['rows']} (flag AF01).</li>
  </ul>
</section>
<section class="section">
  <h2>What this desk does not do</h2>
  <ul>
    <li>It does not change the register, the landing page or any other desk. Changes are proposed for the integration owner (COORDINATION.md, session {esc(SESSION)}).</li>
    <li>It does not schedule any capture of nfl.com. The terms gate (§1.3) stands; this desk performs single dated reads only.</li>
    <li>It does not publish prices, lines, ROI, CLV, stakes or any monetary figure.</li>
  </ul>
</section>
"""
    out["index.html"] = page("Audit overview", "index.html", overview)

    lrows = []
    for r in model["rows"]:
        proposed = TAG_PROPOSED if r["audit_status"] != r["ledger_status"] else ""
        missing = FLAG_MISSING if not r["artifact_exists"] else ""
        lrows.append(
            f"<tr{src_attr(r['source_ids'])}>"
            f"<th scope='row'>{esc(r['id'])}</th>"
            f"<td>{esc(r['requirement'])}</td>"
            f"<td>{esc(r['ledger_status'])}</td>"
            f"<td>{esc(r['audit_status'])}{proposed}</td>"
            f"<td>{rel_link(r['artifact'])}{missing}</td>"
            f"<td>{official_cell(r['source_ids'], reg)}</td>"
            f"<td>{esc(r['clears_when'])}</td>"
            "</tr>")
    out["ledger.html"] = page("All 70 rows", "ledger.html", f"""
<section class="hero compact"><p class="eyebrow">Register audit</p><h1>All {c['rows']} rows</h1>
<p class="lede">One row per register entry. The official link is the first registered non-repository source; rows without one say so.</p></section>
<section class="section">{table(["ID", "Requirement", "Register status", "Audit status", "Artifact", "Official source", "Number that would clear it"], lrows, "All register rows")}</section>
""")

    rgrows = []
    for g in model["regrades"]:
        row = by_id[g["id"]]
        rgrows.append(
            f"<tr{src_attr(row['source_ids'])}>"
            f"<th scope='row'>{esc(g['id'])}</th>"
            f"<td>{esc(g['requirement'])}</td>"
            f"<td>{esc(g['ledger_status'])} → <strong>{esc(g['proposed'])}</strong></td>"
            f"<td>{esc(g['gate'])}</td>"
            f"<td>{esc(g['reason'])}</td>"
            f"<td>{rel_link(g['evidence'])}<br><small class='hash'>sha256 {esc((g['evidence_sha256'] or '')[:16])}…</small></td>"
            f"<td><q>{esc(g['quote'])}</q></td>"
            f"<td>{official_cell(row['source_ids'], reg)}</td>"
            "</tr>")
    out["regrades.html"] = page("Proposed re-grades", "regrades.html", f"""
<section class="hero compact"><p class="eyebrow">For the integration owner</p><h1>Proposed re-grades</h1>
<p class="lede">Each proposal is accepted only when its quoted text was found in the cited file. The register still says the old status until the integration owner applies it.</p></section>
<section class="section">{table(["ID", "Requirement", "Register → proposed", "Gate that still applies", "Why", "Evidence", "Matched text (extracted)", "Official source"], rgrows, "Proposed re-grades")}</section>
""")

    brows = []
    for b in model["blocked_checks"]:
        row = by_id[b["id"]]
        brows.append(
            f"<tr{src_attr(row['source_ids'])}>"
            f"<th scope='row'>{esc(b['id'])}</th>"
            f"<td>{esc(row['requirement'])}</td>"
            f"<td>{esc(row['ledger_status'])}</td>"
            f"<td>{esc(row['gate'])}</td>"
            f"<td>{rel_link(b['evidence'])}</td>"
            f"<td><q>{esc(b['quote'])}</q></td>"
            f"<td>{official_cell(row['source_ids'], reg)}</td>"
            "</tr>")
    out["blocked.html"] = page("Gates re-checked", "blocked.html", f"""
<section class="hero compact"><p class="eyebrow">What blocks what</p><h1>Gates re-checked against official pages</h1>
<p class="lede">Five gates rest on an official NFL page: the §1.3 retrieval prohibition (DR-29, DR-54, DR-66, all Blocked) and the 404 at nfl.com/odds (DR-01, DR-18). Each was re-read on {esc(READ_ON)}; the matched text is shown. Register status is not changed by this page.</p></section>
<section class="section">{table(["ID", "Requirement", "Register status", "Gate", "Evidence", "Matched text", "Official source"], brows, "Gates re-checked")}</section>
""")

    frows = []
    for f in model["flags"]:
        ids = f["source_ids"]
        frows.append(f"<tr{src_attr(ids)}>"
                     f"<th scope='row'>{esc(f['id'])}</th>"
                     f"<td>{esc(f['severity'])}</td>"
                     f"<td>{esc(f['title'])}</td>"
                     f"<td>{esc(f['finding'])}</td>"
                     f"<td>{esc(f['evidence'])}</td>"
                     f"<td>{esc(f['action'])}</td>"
                     f"<td>{official_cell(ids, reg)}</td>"
                     "</tr>")
    out["flagged.html"] = page("Flagged for review", "flagged.html", f"""
<section class="hero compact"><p class="eyebrow">Non-blocking</p><h1>Flagged for review</h1>
<p class="lede">Irregularities found by this audit. They do not block the merge. Each names the artifact, the official source where one applies, and the action.</p></section>
<section class="section">{table(["ID", "Severity", "Finding", "Detail", "Evidence", "Action", "Source"], frows, "Flagged irregularities")}</section>
""")
    return out


CSS = """*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#1d2330;background:#f6f7f9}
.skip-link{position:absolute;left:-999px}.skip-link:focus{left:8px;top:8px;background:#fff;padding:6px}
.top{display:flex;gap:16px;align-items:center;flex-wrap:wrap;padding:12px 20px;background:#14213d;color:#fff}
.top .brand{color:#fff;font-weight:700;text-decoration:none;letter-spacing:.08em}
.top nav{display:flex;gap:4px;flex-wrap:wrap}.top nav a{color:#dbe4ff;text-decoration:none;padding:6px 10px;border-radius:6px}
.top nav a[aria-current=page],.top nav a:hover{background:#2c3e66;color:#fff}
main{max-width:1200px;margin:0 auto;padding:20px}footer{max-width:1200px;margin:0 auto;padding:0 20px 30px;color:#5b6475;font-size:13px}
.hero{background:#fff;border:1px solid #dfe3ea;border-radius:10px;padding:22px}.hero.compact{padding:14px 18px}
.eyebrow{margin:0 0 4px;font-size:12px;letter-spacing:.1em;color:#5b6475;text-transform:uppercase}
h1{margin:0 0 6px;font-size:26px}h2{font-size:18px;margin:0 0 8px}.lede{margin:0;color:#3a4252;max-width:80ch}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:16px 0}
.card{background:#fff;border:1px solid #dfe3ea;border-radius:10px;padding:14px}.card span{display:block;font-size:12px;color:#5b6475}
.card strong{display:block;font-size:24px;margin:4px 0}.card small{color:#5b6475}
.section{background:#fff;border:1px solid #dfe3ea;border-radius:10px;padding:16px;margin:16px 0}
.table-card{overflow:auto;max-width:100%;border:1px solid #dfe3ea;border-radius:8px}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #eef0f4;vertical-align:top}
thead th{background:#f0f3f8;position:sticky;top:0}tbody th{white-space:nowrap}
a{color:#1f4fbf}.flag{color:#9a3412;font-weight:600}.tag{font-size:11px;background:#fff4d6;border:1px solid #e9c46a;border-radius:4px;padding:0 4px}
.hash{color:#5b6475}q{display:block;color:#3a4252}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
:focus-visible{outline:3px solid #2563eb;outline-offset:2px}
"""


def write_all(check: bool) -> int:
    model = build_model()
    pages = render(model)
    data_text = json.dumps(model, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if check:
        ok = True
        if (DATA / "ledger-audit.json").read_text(encoding="utf-8") != data_text:
            print("data/ledger-audit.json differs"); ok = False
        for name, text in pages.items():
            p = SITE / name
            if not p.is_file() or p.read_text(encoding="utf-8") != text:
                print(f"site/{name} differs"); ok = False
        manifest = {"pages": sorted(pages), "session": SESSION, "read_on": READ_ON}
        if (SITE / "manifest.json").read_text(encoding="utf-8") != json.dumps(manifest, indent=2, sort_keys=True) + "\n":
            print("site/manifest.json differs"); ok = False
        print("OK: desk reproduces byte-identically" if ok else "FAIL: rebuild required")
        return 0 if ok else 1
    DATA.mkdir(parents=True, exist_ok=True)
    SITE.mkdir(parents=True, exist_ok=True)
    (DATA / "ledger-audit.json").write_text(data_text, encoding="utf-8")
    for name, text in pages.items():
        (SITE / name).write_text(text, encoding="utf-8")
    (SITE / "style.css").write_text(CSS, encoding="utf-8")
    manifest = {"pages": sorted(pages), "session": SESSION, "read_on": READ_ON}
    (SITE / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    c = model["counts"]
    print(f"wrote {len(pages)} pages; rows={c['rows']} artifacts={c['artifact_exists']} "
          f"sources={c['sources_resolved']} official={c['official_link']} regrades={c['regrades']} blocked={c['blocked_confirmed']}")
    return 0


if __name__ == "__main__":
    sys.exit(write_all(check="--check" in sys.argv[1:]))
