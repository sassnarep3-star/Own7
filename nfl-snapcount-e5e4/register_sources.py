#!/usr/bin/env python3
"""Append this desk's official sources to the project registry (append-only).

Ids are namespaced SN-*. Nothing already in research/sources.json is modified or
removed. Every source is an official NFL league artefact read this session via
Arena `fetch_page` (direct HTTPS to nfl.com returns curl 000 in this sandbox, as
every prior session recorded).
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
REGISTRY = REPO / "research" / "sources.json"
LOCAL = HERE / "data" / "sources.json"

CHECKED = "2026-11-18"
ACCESS = "Arena fetch_page rendered PDF text; not a direct HTTP-status attestation and not a licensed feed"

# Representative official Game Book PDF (g01 WAS@NYG). Each fixture has its own
# PDF; this URL is the registered representative and every row links the exact PDF
# it was transcribed from (see the raw/ extracts and the per-row source links).
GAMEBOOK = {
    "id": "SN-NFL-GAMEBOOK-PDF",
    "publisher": "National Football League",
    "title": "Official NFL Game Book (PDF) - Playtime Percentage (snap counts) for 2026 Week 10 fixtures",
    "url": "https://static.www.nfl.com/image/upload/v1794570519/gamecenter/ab5828d9-4feb-11f1-abca-2c54536568a9.pdf",
    "kind": "gamebook",
    "authority": "Official league game record published by NFL.com",
    "scope": (
        "Per-player Playtime Percentage table (snap counts and snap share on Offense, "
        "Defense and Special Teams) transcribed from the official NFL Game Book PDF for "
        "each of the 13 Week 10 fixtures that had been played at capture. This URL is the "
        "representative registered artefact; every published row links the exact Game Book "
        "PDF it was transcribed from. Three of the thirteen tables are labelled "
        "'(Unofficial)' inside the PDF; the desk records that label and does not treat it "
        "as a different source class."
    ),
    "checked_on": CHECKED,
    "access": ACCESS + "; all 13 Playtime Percentage tables read and saved under nfl-snapcount-e5e4/raw/",
    "status": "Content checked",
}

GAMECENTER = {
    "id": "SN-NFL-GAMECENTER",
    "publisher": "National Football League",
    "title": "NFL Game Centre - Week 10 fixture pages",
    "url": "https://www.nfl.com/games/commanders-at-giants-2026-reg-10",
    "kind": "fixture",
    "authority": "Official league game centre",
    "scope": (
        "Official fixture pages for the 13 played Week 10 fixtures. Each carries the "
        "link to that fixture's official Game Book PDF (the source of the Playtime "
        "Percentage table) and the final score. This URL is the representative registered "
        "page; every row links its own fixture page."
    ),
    "checked_on": CHECKED,
    "access": ACCESS + "; Game Centre pages read alongside the Game Book PDFs",
    "status": "Content checked",
}

# The depth-vs-snap cross-reference reads the committed club depth-chart transcription
# captured by the skill desk (nfl-skill-cfdd/data/depth-slots-2026-11-14.csv), which is
# itself sourced from official club depth-chart pages (X28-{ABBR}-DEPTH). That artefact
# is registered here as a repo-carried, official-club-sourced input; the four clubs
# captured (CHI, DEN, PHI, TB) did not play in Week 10, so the cross-reference yields
# zero joinable rows and the gap is published, not filled.
DEPTH = {
    "id": "SN-CLUB-DEPTH",
    "publisher": "Official NFL member clubs (via the skill desk transcription)",
    "title": "Committed official club depth-chart transcription (2026-11-14 snapshot)",
    "url": "https://www.chicagobears.com/team/depth-chart",
    "kind": "depth",
    "authority": "Official member-club depth chart; carried read-only from nfl-skill-cfdd",
    "scope": (
        "Printed positional depth slots for CHI, DEN, PHI and TB only, transcribed on "
        "2026-11-14 and committed at nfl-skill-cfdd/data/depth-slots-2026-11-14.csv. "
        "None of the four clubs played in Week 10, so the depth-vs-snap cross-reference "
        "returns zero rows. Reused read-only; not re-fetched this session."
    ),
    "checked_on": "2026-11-14",
    "access": "Prior session capture carried read-only; not re-fetched this session",
    "status": "Content checked",
}


def main() -> None:
    entries = [GAMEBOOK, GAMECENTER, DEPTH]
    LOCAL.parent.mkdir(parents=True, exist_ok=True)
    LOCAL.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    existing = {row["id"] for row in registry}
    added = [row for row in entries if row["id"] not in existing]
    registry.extend(added)
    REGISTRY.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    print(f"registered {len(added)} new sources; registry now {len(registry)}")


if __name__ == "__main__":
    main()
