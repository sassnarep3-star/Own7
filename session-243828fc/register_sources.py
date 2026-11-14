#!/usr/bin/env python3
"""Append this session's official sources to the project registry (append-only), then
add their hosts to the audit's SOURCE_HOSTS table (idempotent).

IDs are namespaced X243-*. Nothing already in research/sources.json is modified or removed.
Repository links are registered by exact URL and must point to files that exist on main.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
REGISTRY = REPO / "research" / "sources.json"
CHECK_SITE = REPO / "scripts" / "check_site.py"
CHECKED = "2026-11-14"
FETCH = "Arena fetch_page rendered text on 2026-11-14; not an HTTP-status attestation and not a licensed feed"
REPO_PREFIX = "https://github.com/sassnarep3-star/Own7/"

NEW = [
    dict(id="X243-NFL-INJ-W10", publisher="National Football League", title="Official NFL injury report, Week 10 2026",
         url="https://www.nfl.com/injuries/league/2026/REG10", kind="injuries", host="www.nfl.com",
         authority="League participation and game-status reporting",
         scope="Read 14 Nov 2026, chunks 0-7. Row transcription NOT yet checked line by line: row-level values are withheld and UNVERIFIED.",
         status="Content read; transcription unverified"),
    dict(id="X243-NFL-STANDINGS", publisher="National Football League", title="NFL standings 2026",
         url="https://www.nfl.com/standings/", kind="standings", host="www.nfl.com", authority="League standings",
         scope="Chunk 0 read 14 Nov 2026; 24 of 32 teams compared (8 not yet checked).", status="Partially checked"),
    dict(id="X243-NFL-TERMS", publisher="National Football League", title="NFL.com Terms and Conditions (updated May 16, 2024)",
         url="https://www.nfl.com/legal/terms", kind="legal", host="www.nfl.com", authority="Site terms of use, §1.3 permitted use",
         scope="Chunk 0 read 14 Nov 2026; §1.3 read. Not legal advice.", status="Content read"),
    dict(id="X243-NFL-STATS", publisher="National Football League", title="NFL 2026 player stats",
         url="https://www.nfl.com/stats/player-stats/", kind="stats", host="www.nfl.com", authority="League player statistics",
         scope="Page read 14 Nov 2026 to confirm it exists. No backup-comparison data collected from it.", status="Page confirmed; not used for values"),
    dict(id="X243-NFL-INACTIVES-W9", publisher="National Football League", title="NFL Week 9 inactives: players ruled out for Sunday's games",
         url="https://www.nfl.com/news/nfl-week-9-inactives-players-ruled-out-sunday-2026-season", kind="inactives",
         host="www.nfl.com", authority="Official game-day inactive lists (example of the format)",
         scope="Chunk 0 read 14 Nov 2026 to confirm the page exists and its format. Used only as a format example.", status="Format example"),
    dict(id="X243-DET-CHART", publisher="Detroit Lions", title="Detroit Lions depth chart (club page, labelled unofficial)",
         url="https://www.detroitlions.com/team/depth-chart", kind="depth", host="www.detroitlions.com",
         authority="Club's own working chart, labelled unofficial",
         scope="Read 14 Nov 2026. Headed '2026 Unofficial Depth Chart'. Kerby Joseph not printed.", status="Content read; unofficial"),
    dict(id="X243-GRA-HOME", publisher="Gambling Regulatory Authority (Singapore)", title="GRA home page",
         url="https://www.gra.gov.sg/", kind="regulator", host="www.gra.gov.sg", authority="Singapore gambling regulator",
         scope="Read 14 Nov 2026.", status="Content read"),
    dict(id="X243-GRA-UNLAWFUL", publisher="Gambling Regulatory Authority (Singapore)", title="Unlawful remote gambling activities",
         url="https://www.gra.gov.sg/harm-minimisation/unlawful-remote-gambling-activities", kind="regulator",
         host="www.gra.gov.sg", authority="Official GRA statement on unlicensed remote gambling",
         scope="Read 14 Nov 2026. Cites no Act by name. Penalties as stated on the page.", status="Content read"),
    dict(id="X243-GRA-PROBLEM", publisher="Gambling Regulatory Authority (Singapore)", title="Problem gambling",
         url="https://www.gra.gov.sg/harm-minimisation/problem-gambling", kind="regulator", host="www.gra.gov.sg",
         authority="Official GRA page on problem gambling support", scope="Read 14 Nov 2026.", status="Content read"),
    dict(id="X243-RGA-2014", publisher="Singapore Statutes Online (Attorney-General's Chambers)", title="Remote Gambling Act 2014",
         url="https://sso.agc.gov.sg/Act/RGA2014", kind="statute", host="sso.agc.gov.sg", authority="Statute text (official)",
         scope="Attempted 14 Nov 2026: 'Page Not Found' from this sandbox. Statute text UNVERIFIED.", status="Not reachable"),
]


def repo_urls() -> list[str]:
    """Every github link the session's data and generator use, read from the files themselves."""
    found: set[str] = set()
    for f in list((HERE / "data").glob("*.json")) + [HERE / "build_site.py"]:
        found.update(re.findall(r"https://github\.com/sassnarep3-star/Own7/[^\"\s)]+", f.read_text(encoding="utf-8")))
    found.discard(REPO_PREFIX + "blob/main/")  # a prefix constant, not a link
    return sorted(found)


def main() -> int:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    existing = {r["id"] for r in reg}
    added = []
    for rec in NEW:
        if rec["id"] in existing:
            continue
        reg.append({"id": rec["id"], "publisher": rec["publisher"], "title": rec["title"], "url": rec["url"],
                    "kind": rec["kind"], "authority": rec["authority"], "checked_on": CHECKED,
                    "status": rec["status"], "scope": rec["scope"], "access": FETCH})
        added.append(rec["id"])
    hosts = {rec["id"]: rec["host"] for rec in NEW}
    # repository links: one id per exact URL, file must exist on this branch (main after merge)
    for i, url in enumerate(repo_urls(), 1):
        rid = f"X243-REPO-{i:02d}"
        path = url[len(REPO_PREFIX):]
        if path.startswith("blob/main/"):
            rel = path[len("blob/main/"):]
            if not (REPO / rel).exists():
                raise SystemExit(f"repo link target missing: {rel}")
        elif path.startswith("pull/"):
            pass  # open pull requests, checked with gh before publishing
        else:
            raise SystemExit(f"unsupported repo link form: {url}")
        hosts[rid] = "github.com"
        if rid not in existing:
            reg.append({"id": rid, "publisher": "Project repository (Own7)", "title": url[len(REPO_PREFIX):],
                        "url": url, "kind": "repository", "authority": "Repository file or pull request (project record)",
                        "checked_on": CHECKED, "status": "Repository record",
                        "scope": "Project file, checked on this branch 14 Nov 2026; not an external official source.",
                        "access": "Repository read on the session branch"})
            added.append(rid)
    REGISTRY.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")
    # audit host table: insert once, before class Page
    text = CHECK_SITE.read_text(encoding="utf-8")
    marker = "# NFL session 243828fc (arena/243828fc-own7)"
    if marker not in text:
        block = marker + " — official hosts and repo records registered by register_sources.py.\nSOURCE_HOSTS.update(" + json.dumps(hosts, indent=4, sort_keys=True) + ")\n\n\n"
        text = text.replace("class Page(HTMLParser):", block + "class Page(HTMLParser):", 1)
        CHECK_SITE.write_text(text, encoding="utf-8")
    print("added:", len(added), "registry now:", len(reg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
