#!/usr/bin/env python3
"""Compare the 2026-11-14 retrieved NFL standings (official source) against the
committed 2026-11-12 snapshot in data/nfl-standings-2026.csv.

The snapshot is a dated transcription and is never overwritten. This script
reports exact matches and deltas only.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEAM_ALIASES = {
    "BUF": "Buffalo Bills", "NE": "New England Patriots", "NYJ": "New York Jets",
    "MIA": "Miami Dolphins", "PIT": "Pittsburgh Steelers", "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns", "BAL": "Baltimore Ravens", "JAX": "Jacksonville Jaguars",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "TEN": "Tennessee Titans",
    "DEN": "Denver Broncos", "KC": "Kansas City Chiefs", "LV": "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers", "NYG": "New York Giants", "DAL": "Dallas Cowboys",
    "WAS": "Washington Commanders", "PHI": "Philadelphia Eagles", "CHI": "Chicago Bears",
    "DET": "Detroit Lions", "MIN": "Minnesota Vikings", "GB": "Green Bay Packers",
    "CAR": "Carolina Panthers", "NO": "New Orleans Saints", "TB": "Tampa Bay Buccaneers",
    "ATL": "Atlanta Falcons", "SF": "San Francisco 49ers", "SEA": "Seattle Seahawks",
    "LA": "Los Angeles Rams", "ARI": "Arizona Cardinals", "AZ": "Arizona Cardinals",
}


def parse_rows(text):
    rows = {}
    for line in text.splitlines():
        m = re.search(r"\|\s*(\d)\s*\|\s*(\d)\s*\|\s*(\d)\s*\|\s*([0-9.]+)\s*\|\s*([-0-9]+)\s*\|\s*([-0-9]+)\s*\|\s*([-0-9]+)\s*\|", line)
        if not m:
            continue
        team_cell = line.split("|")[1]
        name = re.sub(r"\[.*?\]\(.*?\)", "", team_cell)
        name = re.sub(r"!\[]\(.*?\)", "", name)
        name = re.sub(r"<br\s*/?>", " ", name)
        name = re.sub(r"\s+", " ", name).strip()
        for abbr, full in TEAM_ALIASES.items():
            if full in name or name == full:
                rows[full] = {
                    "W": int(m.group(1)), "L": int(m.group(2)), "T": int(m.group(3)),
                    "PCT": m.group(4), "PF": int(m.group(5)), "PA": int(m.group(6)),
                    "NET": int(m.group(7)),
                }
                break
    return rows


def main():
    chunk0 = (ROOT / "research/nfl/evidence-2026-11-14/standings-chunk-2026-11-14-0.md").read_text()
    chunk1 = (ROOT / "research/nfl/evidence-2026-11-14/standings-chunk-2026-11-14-1.md").read_text()
    live = {}
    live.update(parse_rows(chunk0))
    live.update(parse_rows(chunk1))

    snapshot = {}
    with (ROOT / "data/nfl-standings-2026.csv").open(newline="") as fh:
        for r in csv.DictReader(fh):
            snapshot[r["Team"]] = {
                "W": int(r["W"]), "L": int(r["L"]), "T": int(r["T"]),
                "PCT": r["PCT"], "PF": int(r["PF"]), "PA": int(r["PA"]),
                "NET": int(r["NetPts"]),
            }

    print(f"Live official rows retrieved: {len(live)}   Committed snapshot rows: {len(snapshot)}")
    missing = set(snapshot) - set(live)
    extra = set(live) - set(snapshot)
    print(f"Teams in snapshot not found in live render: {sorted(missing)}")
    print(f"Teams in live render not in snapshot: {sorted(extra)}")

    mismatches = []
    arithmetic_ok = True
    for team in sorted(set(snapshot) & set(live)):
        s, l = snapshot[team], live[team]
        fields = ("W", "L", "T", "PF", "PA", "NET")
        diff = {k: (s[k], l[k]) for k in fields if s[k] != l[k]}
        if diff:
            mismatches.append((team, diff))
        # arithmetic checks on the LIVE rendering
        games = l["W"] + l["L"] + l["T"]
        pct = round((l["W"] + l["T"] / 2) / games, 3) if games else None
        net = l["PF"] - l["PA"]
        if f"{pct:.3f}" != l["PCT"]:
            arithmetic_ok = False
            mismatches.append((team, {"PCT_arithmetic": (l["PCT"], f"{pct:.3f}")}))
        if net != l["NET"]:
            arithmetic_ok = False
            mismatches.append((team, {"NET_arithmetic": (l["NET"], net)}))

    print(f"\nField mismatches (snapshot vs live render): {len(mismatches)}")
    for team, diff in mismatches:
        print(f"  {team}: {diff}")
    print(f"\nLive-render arithmetic (PCT=(W+T/2)/games, NET=PF-PA): {'OK' if arithmetic_ok else 'FAILED'}")
    print(f"\nSnapshot vs live render exact field agreement: {len(set(snapshot)&set(live)) - len(mismatches)}/32 teams")


if __name__ == "__main__":
    main()
