#!/usr/bin/env python3
"""Compute correlation values from the VERIFIED official tables only.

Input : data/teams-2025-26.csv (30 teams, 2025-26 season averages, nba.com)
        data/players-2025-26-top15.csv (15 players, 2025-26 per-game, nba.com)
Output: handoff/f58e9526/correlation-computed-2025-26.json

What these numbers are (and are not):
  * Pearson r across teams (or players) using season-level averages.
  * Cross-sectional and descriptive. They are NOT game-level correlations and
    NOT correlations between two legs of a parlay or prop combo. Game-level
    logs are not in this repo, so leg correlations remain blank.
  * 95% CI uses the Fisher z-transform (normal approximation). Small n gives
    wide intervals; players (n=15) are reported as a small-sample result.

Usage:
  python3 scripts/compute_correlations.py          # write JSON
  python3 scripts/compute_correlations.py --check  # recompute and compare to the JSON
"""
import csv
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "handoff" / "f58e9526" / "correlation-computed-2025-26.json"

TEAM_SOURCE = "https://www.nba.com/stats/teams/traditional?Season=2025-26&SeasonType=Regular%20Season"
PLAYER_SOURCE = "https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame"

TEAM_PAIRS = [
    ("WIN%", "PTS", "Team win % vs points per game"),
    ("WIN%", "+/-", "Team win % vs point differential per game"),
    ("WIN%", "FG%", "Team win % vs field-goal %"),
    ("WIN%", "3P%", "Team win % vs three-point %"),
    ("WIN%", "TOV", "Team win % vs turnovers per game"),
    ("WIN%", "REB", "Team win % vs rebounds per game"),
    ("PTS", "FG%", "Team points per game vs field-goal %"),
    ("PTS", "TOV", "Team points per game vs turnovers per game"),
]
PLAYER_PAIRS = [
    ("PTS", "MIN", "Player points per game vs minutes per game"),
    ("PTS", "FGA", "Player points per game vs field-goal attempts per game"),
    ("PTS", "AST", "Player points per game vs assists per game"),
]


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy)


def fisher_ci(r, n):
    z = math.atanh(r)
    se = 1 / math.sqrt(n - 3)
    return math.tanh(z - 1.959964 * se), math.tanh(z + 1.959964 * se)


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compute():
    teams = read(ROOT / "data" / "teams-2025-26.csv")
    players = read(ROOT / "data" / "players-2025-26-top15.csv")
    rows = []
    specs = [("teams", teams, TEAM_PAIRS, TEAM_SOURCE, "30 teams"),
             ("players", players, PLAYER_PAIRS, PLAYER_SOURCE, "15 players")]
    for group, data, pairs, src, label in specs:
        for a, b, desc in pairs:
            xs = [float(r[a]) for r in data]
            ys = [float(r[b]) for r in data]
            n = len(xs)
            r = pearson(xs, ys)
            lo, hi = fisher_ci(r, n)
            small = " Small sample (n=15): treat as indicative only." if group == "players" else ""
            rows.append({
                "id": f"CC-{group[0].upper()}{len(rows) + 1:02d}",
                "pair": desc,
                "method": f"Pearson r, {label}, 2025-26 season averages (cross-sectional, not game-level)",
                "correlation_value": f"{r:+.3f}",
                "n_observations": str(n),
                "ci_95": f"{lo:+.3f} to {hi:+.3f} (Fisher z)",
                "status": "verified – computed from verified official values",
                "source_url": src,
                "note": "Descriptive only; not a parlay or prop-combo correlation." + small,
                "_r": round(r, 6),
            })
    return rows


def main():
    rows = compute()
    if "--check" in sys.argv:
        old = json.loads(OUT.read_text(encoding="utf-8"))["rows"]
        bad = []
        for o, n in zip(old, rows):
            if o.get("_r") != n["_r"] or o["correlation_value"] != n["correlation_value"]:
                bad.append(f"{o['id']}: file={o.get('correlation_value')} recomputed={n['correlation_value']}")
        if len(old) != len(rows):
            bad.append(f"row count file={len(old)} recomputed={len(rows)}")
        if bad:
            print("CORRELATION MISMATCH:")
            print("\n".join(" - " + b for b in bad))
            sys.exit(1)
        print(f"correlation check OK: {len(rows)} computed values match the verified tables")
        return
    payload = {
        "title": "Computed correlations from verified official tables (descriptive, not betting leg correlations)",
        "columns": ["id", "pair", "method", "correlation_value", "ci_95", "n_observations", "status",
                    "source_url", "note"],
        "rows": rows,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for r in rows:
        print(f"{r['id']} r={r['correlation_value']} n={r['n_observations']} CI {r['ci_95']} :: {r['pair']}")


if __name__ == "__main__":
    main()
