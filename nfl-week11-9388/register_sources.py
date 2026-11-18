#!/usr/bin/env python3
"""Append this desk's official sources to the project registry (append-only).

Ids are namespaced W9388-*. Nothing already in research/sources.json is modified or
removed. Every entry below is a page that was actually read on 2026-11-18 through Arena
fetch_page; no host is registered that was not read.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
REGISTRY = REPO / "research" / "sources.json"

CHECKED = "2026-11-18"
ACCESS = ("Arena fetch_page rendered text; not an HTTP-status attestation and not a licensed "
          "feed")

COMMON = {
    "publisher": "National Football League",
    "authority": "Primary publisher of the official league schedule, standings, game information "
                 "and injury reporting",
    "checked_on": CHECKED,
    "status": "Content checked",
}

AGGREGATE = [
    {
        "id": "W9388-NFL-STANDINGS-1118",
        "title": "NFL league standings, 2026 regular season",
        "url": "https://www.nfl.com/standings/league/2026/REG",
        "kind": "standings",
        "scope": ("All 32 clubs, ordered by winning percentage: W, L, T, PCT, PF, PA, NET PTS, "
                  "HOME, ROAD, DIV, CONF, STRK. Read 2026-11-18 in two chunks, after the Week 10 "
                  "Monday game. Three columns are printed but not named by the page legend and are "
                  "not transcribed. The page heading renders unsubstituted template placeholders "
                  "($year$, $displayname$)."),
        "access": ACCESS + "; both rendered chunks read and saved under nfl-week11-9388/evidence/",
    },
    {
        "id": "W9388-NFL-SCHED-W11-1118",
        "title": "NFL Week 11 schedule, 2026 (by week)",
        "url": "https://www.nfl.com/schedules/2026/by-week/week-11",
        "kind": "schedule",
        "scope": ("13 fixtures with date, kickoff time and network, plus the six clubs on bye. No "
                  "score is printed for any Week 11 fixture. Kickoff times carry no timezone label. "
                  "Footnote on the same page states that Weeks 16-18 contain matchups whose dates "
                  "and networks are not yet determined. Read 2026-11-18 in three chunks."),
        "access": ACCESS + "; all three rendered chunks read and saved under nfl-week11-9388/evidence/",
    },
    {
        "id": "W9388-NFL-SCHED-W10-1118",
        "title": "NFL Week 10 schedule, 2026 (by week) — tail",
        "url": "https://www.nfl.com/schedules/2026/by-week/week-10",
        "kind": "schedule",
        "scope": ("The final rows of Week 10, read 2026-11-18 to settle the Monday night fixture "
                  "that every earlier capture held as pending: Chargers 23, Ravens 20, FINAL, "
                  "Monday November 16th. Also carries the four Week 10 bye clubs. The chunk began "
                  "mid-row, so the first fixture in it is incomplete and is not transcribed."),
        "access": ACCESS + "; one rendered chunk read and saved under nfl-week11-9388/evidence/",
    },
    {
        "id": "W9388-NFL-INJ-W11-1118",
        "title": "Official NFL injury report — Week 11 URL, read three times on 2026-11-18",
        "url": "https://www.nfl.com/injuries/league/2026/REG11",
        "kind": "injuries",
        "scope": ("Requested three times on 2026-11-18. Each time the page served the Week 10 "
                  "document: the canonical URL in the page's own skip-link is .../reg10 and the "
                  "title reads 'Week 10 of the 2026 Season'. The Week 11 tab exists in the week "
                  "selector but there is no Week 11 document behind it at this instant. The Week 10 "
                  "tables in the chunk read (WAS, NYG, NE, DET, KC part) were transcribed and "
                  "compared against the frozen 2026-11-13 capture."),
        "access": ACCESS + "; the first rendered chunk read and saved under nfl-week11-9388/evidence/",
    },
]

# index, away, home, url slug
FIXTURES = [
    (1, "Indianapolis Colts", "Houston Texans", "colts-at-texans-2026-reg-11"),
    (2, "Miami Dolphins", "Buffalo Bills", "dolphins-at-bills-2026-reg-11"),
    (3, "Baltimore Ravens", "Carolina Panthers", "ravens-at-panthers-2026-reg-11"),
    (4, "New Orleans Saints", "Chicago Bears", "saints-at-bears-2026-reg-11"),
    (5, "Tennessee Titans", "Dallas Cowboys", "titans-at-cowboys-2026-reg-11"),
    (6, "Tampa Bay Buccaneers", "Detroit Lions", "buccaneers-at-lions-2026-reg-11"),
    (7, "Arizona Cardinals", "Kansas City Chiefs", "cardinals-at-chiefs-2026-reg-11"),
    (8, "Pittsburgh Steelers", "Philadelphia Eagles", "steelers-at-eagles-2026-reg-11"),
    (9, "New York Jets", "Los Angeles Chargers", "jets-at-chargers-2026-reg-11"),
    (10, "Jacksonville Jaguars", "New York Giants", "jaguars-at-giants-2026-reg-11"),
    (11, "Las Vegas Raiders", "Denver Broncos", "raiders-at-broncos-2026-reg-11"),
    (12, "Minnesota Vikings", "San Francisco 49ers", "vikings-at-49ers-2026-reg-11"),
    (13, "Cincinnati Bengals", "Washington Commanders", "bengals-at-commanders-2026-reg-11"),
]


def main() -> int:
    registry = json.loads(REGISTRY.read_text())
    existing = {row["id"] for row in registry}
    added = []
    for entry in AGGREGATE:
        if entry["id"] in existing:
            continue
        registry.append({**COMMON, **entry, "access": entry["access"]})
        added.append(entry["id"])
    for index, away, home, slug in FIXTURES:
        sid = f"W9388-GC-W11-{index:02d}"
        if sid in existing:
            continue
        url = f"https://www.nfl.com/games/{slug}"
        rows_note = ("8 player rows with practice status (4 per club)" if index == 1
                     else "empty injury module for both clubs")
        registry.append({
            **COMMON,
            "id": sid,
            "title": f"{away} at {home} — Week 11 game centre, 2026",
            "url": url,
            "kind": "game_info",
            "scope": (f"Game Info block: Location and Stadium, kickoff date and time, and the "
                      f"network. Injury module: {rows_note}. Read 2026-11-18, first rendered chunk "
                      f"only. The page prints no capture time."),
            "checked_on": CHECKED,
            "access": ACCESS + "; transcript saved under nfl-week11-9388/evidence/",
            "status": "Content checked",
        })
        added.append(sid)
    # indent=1 with ensure_ascii=False is the registry's existing format; keeping it means
    # this append is a pure addition in the diff and cannot collide with another session's edit.
    REGISTRY.write_text(json.dumps(registry, indent=1, ensure_ascii=False) + "\n")
    print(f"registered {len(added)} source(s); registry now holds {len(registry)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
