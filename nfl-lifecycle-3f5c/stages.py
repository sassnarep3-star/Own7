"""Ordered origination pipeline: the side first, then the total, then the moneyline.

Requirement (2026-11-14): "Originate the side first, then the total, then the moneyline."

The pipeline publishes three stages with explicit dependencies:

  Stage 1  SIDE        expected margin from the two clubs' scoring profiles + home field.
                       Output: the originated spread, stated from the home club's point of view.
  Stage 2  TOTAL       expected combined points. Depends on: the same two per-club point
                       expectations produced for the side (no new inputs).
  Stage 3  MONEYLINE   win probability mapped from the stage-1 margin through a normal
                       approximation, then zero-hold fair prices. Depends on: stage 1 only.

Stage outputs must reconcile exactly with the canonical engine's single-shot projection
(nfl_origination.engine.project_game): the ordering is a disclosure of dependency, not a
different model. The reconciliation test is part of this desk's suite and runs on every build.

All math is delegated to nfl_origination.math so there is exactly one implementation of the
model. No market price is ever produced here.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
for _p in (str(HERE), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from nfl_origination import math as m  # noqa: E402

from vintages import load_vintage, VINTAGE_A, VINTAGE_B  # noqa: E402

FIXTURES = REPO / "data" / "nfl-schedule-2026-w10.csv"

STAGES = [
    {"order": 1, "id": "side", "name": "Side",
     "inputs": "each club's points-per-game scored and conceded from the standings vintage, "
               "league scoring mean, home-field assumption (2.0 points, disclosed constant)",
     "depends_on": [],
     "output": "originated spread, stated from the home club's point of view"},
    {"order": 2, "id": "total", "name": "Total",
     "inputs": "the same two per-club point expectations computed for the side",
     "depends_on": ["side"],
     "output": "originated total (expected combined points)"},
    {"order": 3, "id": "moneyline", "name": "Moneyline",
     "inputs": "the stage-1 projected margin through a normal win-probability map "
               "(sd 13.86, disclosed assumption); zero-hold conversion to American prices",
     "depends_on": ["side"],
     "output": "model fair home and away prices (not prices anyone offers)"},
]


def load_fixtures() -> list[dict]:
    with FIXTURES.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 14:
        raise ValueError(f"Expected 14 Week 10 fixtures, got {len(rows)}")
    return rows


def team_table(vintage_rows: list[dict]) -> tuple[list[dict], float]:
    """Same construction as the canonical engine: scoring rates from a standings vintage."""
    team_games = sum(int(r["W"]) + int(r["L"]) + int(r["T"]) for r in vintage_rows)
    league_ppg = sum(int(r["PF"]) for r in vintage_rows) / team_games
    teams = []
    for r in vintage_rows:
        games = int(r["W"]) + int(r["L"]) + int(r["T"])
        teams.append({
            "code": r.get("_code", ""),
            "team": r["Team"],
            "games": games,
            "off_ppg": m.scoring_rate(int(r["PF"]), games),
            "def_ppa": m.scoring_rate(int(r["PA"]), games),
        })
    return teams, league_ppg


def _by_name(teams: list[dict]) -> dict:
    by_name = {}
    for t in teams:
        by_name[t["team"]] = t
        by_name[t["team"].split()[-1]] = t
    by_name["49ers"] = next(t for t in teams if t["team"] == "San Francisco 49ers")
    return by_name


def _code_map(vintage_rows: list[dict]) -> dict:
    """Team name -> club code, mirroring the canonical engine's identifiers."""
    codes = {}
    for r in vintage_rows:
        name = r["Team"]
        suffix = name.split()[-1]
        codes[name] = suffix
        codes[suffix] = suffix
    codes["San Francisco 49ers"] = "SF"
    codes["49ers"] = "SF"
    codes["Las Vegas Raiders"] = "LV"
    codes["Raiders"] = "LV"
    codes["Los Angeles Rams"] = "LA"
    codes["Rams"] = "LA"
    codes["Arizona Cardinals"] = "AZ"
    codes["Cardinals"] = "AZ"
    codes["Washington Commanders"] = "WAS"
    codes["Commanders"] = "WAS"
    codes["Kansas City Chiefs"] = "KC"
    codes["Chiefs"] = "KC"
    return codes


def originate_staged(vintage: str) -> list[dict]:
    """Run the three ordered stages for every Week 10 fixture on one standings vintage."""
    rows = load_vintage(vintage)["rows"]
    codes = _code_map(rows)
    teams, league_ppg = team_table(rows)
    by_name = _by_name(teams)
    games = []
    for fixture in load_fixtures():
        home, away = by_name[fixture["Home"]], by_name[fixture["Away"]]
        # Stage 1: SIDE. One coherent pair of expected point totals; the margin is the side.
        projection = m.project_game(home["off_ppg"], home["def_ppa"],
                                    away["off_ppg"], away["def_ppa"], league_ppg)
        side = projection["spread_home"]
        # Stage 2: TOTAL. Same two point expectations; no new information enters here.
        total = projection["total"]
        # Stage 3: MONEYLINE. The stage-1 margin maps to a win probability and fair prices.
        p_home = m.normal_win_probability(projection["margin_home"])
        fair_home = m.american_from_probability(p_home)
        fair_away = m.american_from_probability(1 - p_home)
        # Stage invariants: the derivative lines must agree with the point expectations.
        if abs((projection["home_points"] - projection["away_ppg"]) - (-side)) > 1e-9:
            raise ValueError(f"{fixture['id']}: side is not the negative of the projected margin")
        if abs((projection["home_points"] + projection["away_ppg"]) - total) > 1e-9:
            raise ValueError(f"{fixture['id']}: total is not the sum of the point expectations")
        games.append({
            "id": fixture["id"],
            "matchup": f"{codes[fixture['Away']]} @ {codes[fixture['Home']]}",
            "away_team": away["team"], "home_team": home["team"],
            "kickoff_date": fixture["Date"],
            "kickoff": f"{fixture['Date']} {fixture['KickoffET']} ET",
            "stage_side_spread_home": round(side, 4),
            "stage_total": round(total, 4),
            "stage_model_p_home": round(p_home, 4),
            "stage_fair_home_price": fair_home,
            "stage_fair_away_price": fair_away,
            "source_ids": ["NFL-STANDINGS", "NFL-SCHED-W10", "PYTH-NFL", "REPO"],
            "game_source_url": fixture["GameURL"],
            "source_url": fixture["SourceURL"],
        })
    return games


def reconcile_with_canonical() -> dict:
    """Staged pipeline on the frozen vintage must equal the canonical engine's numbers exactly.

    The canonical artefact research/nfl/results.json is produced by python -m nfl_origination run
    from receipt-checked inputs. Any divergence between the ordered pipeline and that artefact
    fails this desk's build; it is never silently accepted.
    """
    canonical = json.loads((REPO / "research" / "nfl" / "results.json").read_text(encoding="utf-8"))
    canon_games = {g["id"]: g for g in canonical["games"]}
    staged = originate_staged(VINTAGE_A)
    mismatches = []
    for game in staged:
        ref = canon_games[game["id"]]
        for field, mine in (("originated_spread_home", game["stage_side_spread_home"]),
                            ("originated_total", game["stage_total"]),
                            ("model_p_home", game["stage_model_p_home"]),
                            ("fair_home_price", game["stage_fair_home_price"]),
                            ("fair_away_price", game["stage_fair_away_price"])):
            theirs = ref[field]
            if theirs is None or abs(round(float(theirs), 4) - mine) > 1e-9:
                mismatches.append({"game": game["id"], "field": field,
                                   "staged": mine, "canonical": theirs})
    return {"checked_games": len(staged), "mismatches": mismatches,
            "status": "PASS" if not mismatches else "FAIL",
            "canonical_artifact": "research/nfl/results.json",
            "canonical_run_hash": canonical.get("run_hash")}
