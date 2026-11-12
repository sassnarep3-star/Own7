#!/usr/bin/env python3
"""NFL line-origination model (standard library only).

Inputs are the official NFL.com standings rows in ``nfl/data/standings-2026.csv``
(points for, points against, wins, losses, ties). Nothing is scraped and no
market price is used: every number below is either a transcribed official value
with a scored identity check or an explicitly labelled *derived* model output.

The parameters are project design choices, not NFL facts:

``shrink_games``  pseudo-games of league-average regression applied to each
                  team's points-for and points-against rates (0 = no shrinkage)
``hfa``           home-field points added to the home team's projected margin
``sigma``         margin scale of the logistic win-probability map, in points
``pyth_exp``      exponent of the Pythagorean win-expectation diagnostic

Every output is computed twice: once at the documented baseline and once across
a sensitivity grid, so the published spread/total is always a range.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
STANDINGS = HERE / "data" / "standings-2026.csv"
GAMES = HERE / "data" / "games-2026-w10.csv"

BASELINE = {"shrink_games": 4.0, "hfa": 2.0, "sigma": 13.0, "pyth_exp": 2.37}
SENSITIVITY = {
    "shrink_games": (0.0, 4.0, 8.0),
    "hfa": (0.0, 2.0, 3.0),
    "sigma": (11.0, 13.0, 15.0),
}


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_standings() -> list[dict]:
    rows = []
    for raw in load_csv(STANDINGS):
        rows.append(
            {
                "code": raw["team_code"],
                "name": raw["team_name"],
                "conf": raw["conf"],
                "w": int(raw["w"]),
                "l": int(raw["l"]),
                "t": int(raw["t"]),
                "pct": float(raw["pct"]),
                "pf": int(raw["pf"]),
                "pa": int(raw["pa"]),
                "net": int(raw["net"]),
                "source_ids": raw["source_ids"].split(),
            }
        )
    return rows


def load_games() -> list[dict]:
    return load_csv(GAMES)


def pct(w: int, l: int, t: int) -> float:
    games = w + l + t
    return (w + 0.5 * t) / games if games else 0.0


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return num / (dx * dy) if dx and dy else float("nan")


def ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def spearman(xs: list[float], ys: list[float]) -> float:
    return pearson(ranks(xs), ranks(ys))


def fisher_ci(r: float, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n <= 3 or abs(r) >= 1:
        return (float("nan"), float("nan"))
    zr = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(n - 3)
    lo, hi = math.tanh(zr - z * se), math.tanh(zr + z * se)
    return (round(lo, 3), round(hi, 3))


def team_ratings(standings: list[dict], params: dict) -> dict:
    rates = []
    for row in standings:
        games = row["w"] + row["l"] + row["t"]
        rates.append(
            {
                "code": row["code"],
                "games": games,
                "pf_pg": row["pf"] / games,
                "pa_pg": row["pa"] / games,
            }
        )
    league_avg = sum(r["pf_pg"] for r in rates) / len(rates)
    k = params["shrink_games"]
    ratings = {}
    for r in rates:
        off = (r["pf_pg"] * r["games"] + league_avg * k) / (r["games"] + k)
        dfn = (r["pa_pg"] * r["games"] + league_avg * k) / (r["games"] + k)
        ratings[r["code"]] = {
            "games": r["games"],
            "pf_pg": round(r["pf_pg"], 3),
            "pa_pg": round(r["pa_pg"], 3),
            "off_adj": round(off, 3),
            "def_adj": round(dfn, 3),
        }
    return {"league_avg": round(league_avg, 4), "teams": ratings}


def project(games: list[dict], ratings: dict, params: dict) -> list[dict]:
    league_avg = ratings["league_avg"]
    teams = ratings["teams"]
    out = []
    for game in games:
        home, away = game["home"], game["away"]
        exp_home = teams[home]["off_adj"] * teams[away]["def_adj"] / league_avg
        exp_away = teams[away]["off_adj"] * teams[home]["def_adj"] / league_avg
        margin = exp_home - exp_away + params["hfa"]
        total = exp_home + exp_away
        p_home = 1 / (1 + math.exp(-margin / params["sigma"]))
        out.append(
            {
                "game_id": game["game_id"],
                "away": away,
                "home": home,
                "exp_home_points": round(exp_home, 2),
                "exp_away_points": round(exp_away, 2),
                "model_home_margin": round(margin, 2),
                "model_total": round(total, 2),
                "model_home_win_prob": round(p_home, 4),
                "source_ids": game["source_ids"].split(),
            }
        )
    return out


def sensitivity(games: list[dict], standings: list[dict], baseline: dict) -> list[dict]:
    """Worst-case envelope of model margin/total across the parameter grid."""
    out = []
    combos = []
    for k in SENSITIVITY["shrink_games"]:
        for hfa in SENSITIVITY["hfa"]:
            combos.append({"shrink_games": k, "hfa": hfa, "sigma": baseline["sigma"],
                           "pyth_exp": baseline["pyth_exp"]})
    for game in games:
        margins, totals = [], []
        for params in combos:
            ratings = team_ratings(standings, params)
            row = next(r for r in project([game], ratings, params))
            margins.append(row["model_home_margin"])
            totals.append(row["model_total"])
        out.append(
            {
                "game_id": game["game_id"],
                "margin_min": round(min(margins), 2),
                "margin_max": round(max(margins), 2),
                "total_min": round(min(totals), 2),
                "total_max": round(max(totals), 2),
                "grid_points": len(combos),
            }
        )
    return out


def correlations(standings: list[dict], params: dict) -> list[dict]:
    names = {
        "pf_pct": ("Points for per game", "Win percentage", "offence explains part of the standings"),
        "pa_pct": ("Points against per game", "Win percentage", "defence explains part of the standings"),
        "net_pct": ("Net points per game", "Win percentage", "margin-based rating check"),
        "pf_pa": ("Points for per game", "Points against per game", "are scoring and conceding independent"),
        "pyth_pct": ("Pythagorean expected win percentage", "Actual win percentage", "model diagnostic, not a bet signal"),
    }
    pf_pg = [r["pf"] / (r["w"] + r["l"] + r["t"]) for r in standings]
    pa_pg = [r["pa"] / (r["w"] + r["l"] + r["t"]) for r in standings]
    net_pg = [(r["pf"] - r["pa"]) / (r["w"] + r["l"] + r["t"]) for r in standings]
    actual = [r["pct"] for r in standings]
    k = params["pyth_exp"]
    pyth = [p ** k / (p ** k + a ** k) for p, a in zip(pf_pg, pa_pg)]
    series = {
        "pf_pct": (pf_pg, actual),
        "pa_pct": (pa_pg, actual),
        "net_pct": (net_pg, actual),
        "pf_pa": (pf_pg, pa_pg),
        "pyth_pct": (pyth, actual),
    }
    out = []
    for key, (xs, ys) in series.items():
        r = pearson(xs, ys)
        rho = spearman(xs, ys)
        lo, hi = fisher_ci(r, len(xs))
        out.append(
            {
                "id": key,
                "x": names[key][0],
                "y": names[key][1],
                "note": names[key][2],
                "n": len(xs),
                "pearson": round(r, 3),
                "spearman": round(rho, 3),
                "ci_low": lo,
                "ci_high": hi,
                "source_ids": ["NFL-STANDINGS"],
            }
        )
    return out


def compute(params: dict | None = None) -> dict:
    params = dict(BASELINE if params is None else params)
    standings = load_standings()
    games = load_games()
    ratings = team_ratings(standings, params)
    projections = project(games, ratings, params)
    envelope = {row["game_id"]: row for row in sensitivity(games, standings, params)}
    for row in projections:
        band = envelope[row["game_id"]]
        row["margin_range"] = [band["margin_min"], band["margin_max"]]
        row["total_range"] = [band["total_min"], band["total_max"]]
    return {
        "params": params,
        "sensitivity_grid": {k: list(v) for k, v in SENSITIVITY.items()},
        "league_avg_points": ratings["league_avg"],
        "ratings": ratings["teams"],
        "projections": projections,
        "correlations": correlations(standings, params),
        "checks": identity_checks(standings, games),
    }


def identity_checks(standings: list[dict], games: list[dict]) -> dict:
    """Arithmetic identities that would fail if a transcribed value were wrong."""
    pct_bad, net_bad, games_used = [], [], {}
    for row in standings:
        expected_pct = pct(row["w"], row["l"], row["t"])
        if abs(expected_pct - row["pct"]) > 0.0015:
            pct_bad.append(row["code"])
        if row["pf"] - row["pa"] != row["net"]:
            net_bad.append(row["code"])
        games_used.setdefault(row["w"] + row["l"] + row["t"], 0)
        games_used[row["w"] + row["l"] + row["t"]] += 1
    pf_sum = sum(r["pf"] for r in standings)
    pa_sum = sum(r["pa"] for r in standings)
    slate_teams = {t for g in games for t in (g["away"], g["home"])}
    codes = {r["code"] for r in standings}
    return {
        "teams": len(standings),
        "games": len(games),
        "pct_identity_failures": pct_bad,
        "net_identity_failures": net_bad,
        "pf_sum": pf_sum,
        "pa_sum": pa_sum,
        "pf_equals_pa": pf_sum == pa_sum,
        "team_games": sum(r["w"] + r["l"] + r["t"] for r in standings),
        "games_by_played": {str(k): v for k, v in sorted(games_used.items())},
        "slate_teams": len(slate_teams),
        "clubs_not_in_slate": sorted(codes - slate_teams),
        "duplicate_slate_teams": sorted(t for t in slate_teams if sum(
            1 for g in games for x in (g["away"], g["home"]) if x == t) > 1),
    }


if __name__ == "__main__":
    print(json.dumps(compute(), indent=2))
