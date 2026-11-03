"""Compute Pearson correlations between 2025-26 team-season stats.

Input : data/teams-2025-26.csv (every row carries an official NBA.com source link)
Output: data/team-correlations-2025-26.csv

These are CROSS-SECTIONAL team-season correlations (n = 30 teams, one value per
team). They are NOT bet-leg correlations: leg-level correlation requires per-game
paired outcomes, which are not available from the verified sources (see
docs/strategies.md). Run: python3 scripts/compute_team_correlations.py
"""
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "teams-2025-26.csv"
OUT = ROOT / "data" / "team-correlations-2025-26.csv"
SOURCE = "https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season"

PAIRS = [
    ("WIN%", "+/-"),
    ("WIN%", "TOV"),
    ("PTS", "FG%"),
    ("PTS", "3P%"),
    ("PTS", "AST"),
    ("REB", "OREB"),
]


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy)


def main():
    rows = list(csv.DictReader(SRC.open()))
    out = []
    for a, b in PAIRS:
        xs = [float(r[a]) for r in rows]
        ys = [float(r[b]) for r in rows]
        r = pearson(xs, ys)
        out.append({
            "Pair": f"{a} vs {b}",
            "n_teams": len(rows),
            "r": f"{r:.3f}",
            "r_squared": f"{r * r:.3f}",
            "Method": "Pearson, cross-sectional across 30 team-season rows (not bet-leg correlation)",
            "Input_file": "data/teams-2025-26.csv",
            "Source": SOURCE,
            "Verified": "computed from verified inputs",
        })
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    for o in out:
        print(o["Pair"], o["r"], o["r_squared"])


if __name__ == "__main__":
    main()
