#!/usr/bin/env python3
"""Append this desk's official sources to the project registry (append-only).

Ids are namespaced X28-*. Nothing already in research/sources.json is modified or removed.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
REGISTRY = REPO / "research" / "sources.json"
LOCAL = HERE / "data" / "sources.json"

CHECKED = "2026-11-13"
ACCESS = "Arena fetch_page rendered text; not an HTTP-status attestation and not a licensed feed"

INJURY = {
    "id": "X28-NFL-INJ-W10",
    "publisher": "National Football League",
    "title": "Official NFL injury report — Week 10, 2026 (all games)",
    "url": "https://www.nfl.com/injuries/league/2026/REG10",
    "kind": "injuries",
    "authority": "League participation and game-status reporting",
    "scope": ("All 14 Week 10 fixtures: 28 clubs, 326 player rows with practice status and game "
              "status. Read on 2026-11-13 (Friday). Game-status cells are populated for 5 clubs "
              "only; 301 of 326 rows carry no game status on the page."),
    "checked_on": CHECKED,
    "access": ACCESS + "; all 8 rendered chunks read and saved under nfl-availability-28ef/evidence/",
    "status": "Content checked",
}

# club, abbr, host, page heading printed by the club, date stamp printed by the club (if any)
CLUBS = [
    ("Atlanta Falcons", "ATL", "www.atlantafalcons.com", "Atlanta Falcons Depth Chart", ""),
    ("Buffalo Bills", "BUF", "www.buffalobills.com", "Buffalo Bills Depth Chart", ""),
    ("Carolina Panthers", "CAR", "www.panthers.com", "Carolina Panthers Depth Chart / 2026 Depth Chart", ""),
    ("Cincinnati Bengals", "CIN", "www.bengals.com", "2026 Bengals Depth Chart", ""),
    ("Dallas Cowboys", "DAL", "www.dallascowboys.com", "Unofficial 2026 Dallas Cowboys Depth Chart", ""),
    ("Green Bay Packers", "GB", "www.packers.com", "Green Bay Packers Depth Chart", "Unofficial, Nov. 10, 2026"),
    ("Indianapolis Colts", "IND", "www.colts.com", "Indianapolis Colts Depth Chart", ""),
    ("Jacksonville Jaguars", "JAX", "www.jaguars.com", "Jaguars Depth Chart", ""),
    ("Kansas City Chiefs", "KC", "www.chiefs.com", "Kansas City Chiefs Unofficial Depth Chart", ""),
    ("Los Angeles Chargers", "LAC", "www.chargers.com", "Los Angeles Chargers Depth Chart", ""),
    ("Los Angeles Rams", "LAR", "www.therams.com", "Rams Unofficial Depth Chart", ""),
    ("Las Vegas Raiders", "LV", "www.raiders.com", "Depth Chart", "as of November 10, 2026"),
    ("Minnesota Vikings", "MIN", "www.vikings.com", "2026 Unofficial Depth Chart", ""),
    ("New Orleans Saints", "NO", "www.neworleanssaints.com", "New Orleans Saints Unofficial Depth Chart", ""),
    ("New York Jets", "NYJ", "www.newyorkjets.com", "Unofficial Depth Chart", ""),
    ("San Francisco 49ers", "SF", "www.49ers.com", "San Francisco 49ers Depth Chart", "Updated as of 11/10/26"),
    ("Tennessee Titans", "TEN", "www.tennesseetitans.com", "UNOFFICIAL DEPTH CHART", "as of 11/10/26"),
]


def club_entry(name, abbr, host, heading, stamp):
    title = f"{name} printed depth chart (Week 10, 2026)"
    scope = (f"Printed positional slots for offence, defence and special teams in the club's own "
             f"order; first name listed = first string. Page heading: \"{heading}\".")
    if stamp:
        scope += f" Date printed on the page: \"{stamp}\"."
    scope += " No snap counts, no injury designation, no game-day personnel confirmation."
    return {
        "id": f"X28-{abbr}-DEPTH",
        "publisher": f"{name} (NFL member club)",
        "title": title,
        "url": f"https://{host}/team/depth-chart",
        "kind": "depth",
        "team": abbr,
        "authority": "Official club website; several clubs label the chart 'unofficial'",
        "scope": scope,
        "checked_on": CHECKED,
        "access": ACCESS + f"; rendered rows saved to nfl-availability-28ef/evidence/depth-{abbr}.md",
        "status": "Content checked",
    }


HOU = {
    "id": "X28-HOU-DEPTH",
    "publisher": "Houston Texans (NFL member club)",
    "title": "Houston Texans printed depth chart — NOT OBTAINED",
    "url": "https://www.houstontexans.com/team/depth-chart",
    "kind": "depth",
    "team": "HOU",
    "authority": "Official club website",
    "scope": ("The page title and the heading 'Unofficial Depth Chart' were returned on "
              "2026-11-13, but no depth-chart table was present in the rendered text. No Texans "
              "chain is published by this desk and nothing was substituted from another source."),
    "checked_on": CHECKED,
    "access": ACCESS + "; attempt recorded in nfl-availability-28ef/evidence/depth-HOU.md",
    "status": "Not obtained",
}


def main() -> None:
    entries = [INJURY] + [club_entry(*c) for c in CLUBS] + [HOU]
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
