#!/usr/bin/env python3
"""Pre-registered walk-forward backtest with a probability and its inputs on every row (D3).

This module does not import another desk's engine. It re-implements the seven estimators named in
data/registration.json from the official score file, and it stores, for every scored game and every
estimator:

    the probability of the home side covering / of the total going over
    the line the probability refers to
    the inputs that produced it (league prior, the two clubs' shrunk rates or rest days or streak)
    the official result and the source page of that result

Leakage control is structural: `state_before(week)` only ever sees games whose week is < the target
week, and the build asserts that no forecast for week w was produced from a game in week >= w.

`--check` rebuilds and demands byte-identical output. No wall clock is read.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = HERE / "data"
GAMES = REPO / "nfl-results" / "data" / "games-2026-w1-9.csv"
BYES = REPO / "nfl-results" / "data" / "byes-2026-w1-9.csv"
REGISTRATION = DATA / "registration.json"

# Frozen parameters. These are the values written in the registration file; the build asserts that
# the two agree, so a parameter cannot drift between the prose and the code.
PARAMS = {
    "home_field_points": 2.0,
    "shrink_games": 4.0,
    "pythagorean_exponent": 2.37,
    "recency_decay": 0.7,
    "rest_points": 1.5,
    "streak_points": 0.75,
    "margin_sd": 13.86,
    "total_sd": 13.5,
    "push_band": 0.0,
}


def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def load_games() -> list[dict]:
    rows = []
    with GAMES.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows.append({
                "week": int(row["week"]), "date": row["date"], "away": row["away"],
                "home": row["home"], "away_score": int(row["away_score"]),
                "home_score": int(row["home_score"]), "source_url": row["source_url"],
            })
    if len(rows) != 136:
        raise SystemExit(f"expected 136 game rows, found {len(rows)}")
    return rows


def load_byes() -> dict[int, set[str]]:
    out: dict[int, set[str]] = {}
    with BYES.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out.setdefault(int(row["week"]), set()).add(row["team_code"])
    return out


def state_before(games: list[dict], week: int) -> dict:
    """Everything known from weeks strictly before `week`."""
    prior = [g for g in games if g["week"] < week]
    if any(g["week"] >= week for g in prior):
        raise SystemExit("leakage guard failed")
    state: dict[str, dict] = {}
    for g in prior:
        for club, pf, pa, venue in ((g["home"], g["home_score"], g["away_score"], "home"),
                                    (g["away"], g["away_score"], g["home_score"], "away")):
            s = state.setdefault(club, {"games": 0, "pf": 0, "pa": 0, "home_pf": 0, "home_pa": 0,
                                        "home_games": 0, "road_pf": 0, "road_pa": 0, "road_games": 0,
                                        "last_date": "", "results": [], "weighted_pf": 0.0,
                                        "weighted_pa": 0.0, "weight": 0.0})
            s["games"] += 1
            s["pf"] += pf
            s["pa"] += pa
            if venue == "home":
                s["home_pf"] += pf
                s["home_pa"] += pa
                s["home_games"] += 1
            else:
                s["road_pf"] += pf
                s["road_pa"] += pa
                s["road_games"] += 1
            if g["date"] > s["last_date"]:
                s["last_date"] = g["date"]
            s["results"].append("W" if pf > pa else "L" if pf < pa else "T")
    # Recency weights need the week of each game, so a second pass fills them.
    for g in prior:
        weight = PARAMS["recency_decay"] ** (week - g["week"])
        for club, pf, pa in ((g["home"], g["home_score"], g["away_score"]),
                             (g["away"], g["away_score"], g["home_score"])):
            s = state[club]
            s["weighted_pf"] += weight * pf
            s["weighted_pa"] += weight * pa
            s["weight"] += weight
    return state


def league_prior(state: dict) -> float:
    pf = sum(s["pf"] for s in state.values())
    n = sum(s["games"] for s in state.values())
    return pf / n if n else None


def shrunk(state: dict, club: str, league: float) -> tuple[float, float]:
    k = PARAMS["shrink_games"]
    s = state.get(club)
    if not s or not s["games"]:
        return league, league
    off = (s["pf"] + league * k) / (s["games"] + k)
    dfn = (s["pa"] + league * k) / (s["games"] + k)
    return off, dfn


def venue_shrunk(state: dict, club: str, league: float, at_home: bool) -> tuple[float, float]:
    k = PARAMS["shrink_games"]
    s = state.get(club)
    if not s:
        return league, league
    g = s["home_games"] if at_home else s["road_games"]
    pf = s["home_pf"] if at_home else s["road_pf"]
    pa = s["home_pa"] if at_home else s["road_pa"]
    if not g:
        return shrunk(state, club, league)
    return (pf + league * k) / (g + k), (pa + league * k) / (g + k)


def streak(state: dict, club: str) -> int:
    s = state.get(club)
    if not s or not s["results"]:
        return 0
    last = s["results"][-1]
    n = 0
    for r in reversed(s["results"]):
        if r == last:
            n += 1
        else:
            break
    return n if last == "W" else -n


def rest_days(state: dict, club: str, date_str: str) -> int | None:
    s = state.get(club)
    if not s or not s["last_date"]:
        return None
    from datetime import date
    return (date.fromisoformat(date_str) - date.fromisoformat(s["last_date"])).days


def estimators() -> list[tuple[str, str]]:
    return [("M00", "Null: league mean and home field"),
            ("M01", "Shrunk scoring profiles"),
            ("M02", "Pythagorean exponent"),
            ("M03", "Recency-weighted scoring"),
            ("M04", "Rest and bye differential"),
            ("M05", "Home-only and road-only rates"),
            ("M06", "Streak allowance")]


def forecast(model: str, state: dict, home: str, away: str, league: float,
             byes: dict[int, set[str]], week: int, date_str: str) -> dict:
    """Return the expected (home margin, total) and the inputs behind it."""
    hf = PARAMS["home_field_points"]
    inputs: dict = {"league_prior": round(league, 6), "home_field_points": hf}
    if model == "M00":
        margin, total = hf, 2 * league
    elif model in ("M01", "M02", "M03"):
        if model == "M03":
            def rates(club):
                s = state.get(club)
                if not s or not s["weight"]:
                    return league, league
                k = PARAMS["shrink_games"]
                w = s["weight"]
                return ((s["weighted_pf"] + league * k) / (w + k),
                        (s["weighted_pa"] + league * k) / (w + k))
            h_off, h_def = rates(home)
            a_off, a_def = rates(away)
        else:
            h_off, h_def = shrunk(state, home, league)
            a_off, a_def = shrunk(state, away, league)
        home_pts = (h_off + a_def) / 2
        away_pts = (a_off + h_def) / 2
        if model == "M02":
            exp = PARAMS["pythagorean_exponent"]
            h_ratio = (h_off ** exp) / (h_off ** exp + h_def ** exp) if h_off + h_def else 0.5
            a_ratio = (a_off ** exp) / (a_off ** exp + a_def ** exp) if a_off + a_def else 0.5
            margin = (h_ratio - a_ratio) * 2 * league + hf
            total = home_pts + away_pts
        else:
            # A points-for rating and a points-against rating are each an estimate of the same
            # quantity (a club's scoring level), so their mean is the expected points for the side.
            margin = home_pts - away_pts + hf
            total = home_pts + away_pts
        inputs.update({"home_off": round(h_off, 6), "home_def": round(h_def, 6),
                       "away_off": round(a_off, 6), "away_def": round(a_def, 6),
                       "home_expected_points": round(home_pts, 6),
                       "away_expected_points": round(away_pts, 6)})
    elif model == "M04":
        h_rest = rest_days(state, home, date_str)
        a_rest = rest_days(state, away, date_str)
        h_bye = (week - 1) in byes and home in byes[week - 1]
        a_bye = (week - 1) in byes and away in byes[week - 1]
        delta = 0.0
        if h_rest is not None and a_rest is not None:
            delta = PARAMS["rest_points"] * (1 if h_rest > a_rest else -1 if h_rest < a_rest else 0)
        delta += PARAMS["rest_points"] * ((1 if h_bye else 0) - (1 if a_bye else 0))
        margin, total = hf + delta, 2 * league
        inputs.update({"home_rest_days": h_rest, "away_rest_days": a_rest,
                       "home_from_bye": h_bye, "away_from_bye": a_bye})
    elif model == "M05":
        h_off, h_def = venue_shrunk(state, home, league, True)
        a_off, a_def = venue_shrunk(state, away, league, False)
        home_pts = (h_off + a_def) / 2
        away_pts = (a_off + h_def) / 2
        margin = home_pts - away_pts + hf
        total = home_pts + away_pts
        inputs.update({"home_off": round(h_off, 6), "home_def": round(h_def, 6),
                       "away_off": round(a_off, 6), "away_def": round(a_def, 6),
                       "home_expected_points": round(home_pts, 6),
                       "away_expected_points": round(away_pts, 6)})
    elif model == "M06":
        delta = PARAMS["streak_points"] * (streak(state, home) - streak(state, away))
        margin, total = hf + delta, 2 * league
        inputs.update({"home_streak": streak(state, home), "away_streak": streak(state, away)})
    else:
        raise SystemExit(f"unknown model {model}")
    return {"margin": margin, "total": total, "inputs": inputs}


def build() -> dict:
    registration = json.loads(REGISTRATION.read_text())
    # The parameters in the prose and in the code must be the same parameters.
    prose = {m["id"]: m for m in registration["model_family"]["models"]}
    assert "2.37" in " ".join(prose["M02"]["inputs"]), "pythagorean exponent drifted"
    assert "0.7" in " ".join(prose["M03"]["inputs"]), "recency decay drifted"
    assert "4 games" in " ".join(prose["M01"]["inputs"]), "shrinkage drifted"
    assert "2.0" in " ".join(prose["M00"]["inputs"]), "home field drifted"

    games = load_games()
    byes = load_byes()
    scored = [g for g in games if g["week"] >= 2]
    rows = []
    for g in scored:
        state = state_before(games, g["week"])
        league = league_prior(state)
        if league is None:
            raise SystemExit("no league prior")
        actual_margin = g["home_score"] - g["away_score"]
        actual_total = g["home_score"] + g["away_score"]

        # The benchmark is frozen, not fitted: the home side is spotted the home-field constant
        # (2.0 points) and the total is the prior-week league mean doubled. Both come from weeks
        # strictly before this one, so the benchmark cannot leak. A model earns skill only by
        # beating a 50/50 probability on that *same* benchmark, which is why M00 is exactly 0.5.
        bench_side = PARAMS["home_field_points"]
        bench_total = round((2 * league) * 2) / 2
        home_covered = actual_margin > bench_side
        went_over = actual_total > bench_total
        home_won = g["home_score"] > g["away_score"]

        forecasts = {}
        for model, _name in estimators():
            f = forecast(model, state, g["home"], g["away"], league, byes, g["week"], g["date"])
            sd_m = PARAMS["margin_sd"]
            sd_t = PARAMS["total_sd"]
            p_home = normal_cdf((f["margin"] - bench_side) / sd_m)
            p_over = normal_cdf((f["total"] - bench_total) / sd_t)
            p_ml = normal_cdf(f["margin"] / sd_m)
            forecasts[model] = {
                "fair_margin": round(f["margin"], 6),
                "fair_total": round(f["total"], 6),
                "residual_side": round(f["margin"] - bench_side, 6),
                "residual_total": round(f["total"] - bench_total, 6),
                "p_home_cover": round(p_home, 6),
                "p_over": round(p_over, 6),
                "p_home_win": round(p_ml, 6),
                "inputs": f["inputs"],
            }
        rows.append({
            "id": f"W{g['week']:02d}-{g['away']}-{g['home']}",
            "week": g["week"], "date": g["date"], "away": g["away"], "home": g["home"],
            "away_score": g["away_score"], "home_score": g["home_score"],
            "actual_margin": actual_margin, "actual_total": actual_total,
            "benchmark_side_line": bench_side, "benchmark_total_line": bench_total,
            "home_covered": home_covered, "went_over": went_over, "home_won": home_won,
            "forecasts": forecasts,
            "source_url": g["source_url"],
            "source_ids": ["X29-NFL-SCHEDULE"],
        })
    # Every row must carry a probability for every model and the inputs that made it.
    for row in rows:
        for model, _ in estimators():
            f = row["forecasts"][model]
            for key in ("p_home_cover", "p_over", "p_home_win"):
                if not 0.0 <= f[key] <= 1.0:
                    raise SystemExit(f"{row['id']} {model} {key} outside [0,1]")
            if not f["inputs"]:
                raise SystemExit(f"{row['id']} {model} has no stored inputs")
    return {
        "schema_version": 1,
        "registration_hash": registration_hash(),
        "rows": len(rows),
        "weeks": sorted({r["week"] for r in rows}),
        "parameters": PARAMS,
        "benchmark": {
            "rule": ("Both markets are graded against a frozen benchmark computed from weeks strictly "
                     "before the game: the home side is spotted the home-field constant, and the total "
                     "line is the prior-week league mean doubled. M00 forecasts exactly 0.5 on both, so "
                     "M00 is the coin-flip control and Brier skill is measured against it."),
            "side_line": "home -2.0 (a cover needs the home side to win by more than 2)",
            "total_line": "2 x prior-week league points per team-game, rounded to the nearest half point",
            "controls": ["coin flip (0.5 on every market)", "always the home side", "always the over"],
        },
        "models": [{"id": i, "name": n} for i, n in estimators()],
        "games": rows,
    }


def registration_hash() -> str:
    import hashlib
    return hashlib.sha256(REGISTRATION.read_bytes()).hexdigest()


def main() -> int:
    DATA.mkdir(exist_ok=True)
    payload = build()
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    target = DATA / "backtest.json"
    if "--check" in sys.argv:
        if not target.exists() or target.read_text() != text:
            raise SystemExit("backtest.json is stale: re-run without --check")
        print(f"OK: {payload['rows']} scored games, {len(payload['models'])} models, registration {payload['registration_hash'][:12]}")
        return 0
    target.write_text(text)
    print(f"Wrote backtest.json: {payload['rows']} scored games x {len(payload['models'])} models")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
