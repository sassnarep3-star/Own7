#!/usr/bin/env python3
"""Originate the desk's own NFL lines, in the required order: side, then total, then moneyline.

The order is the point. A side price is a statement about a *margin* and is the only one of the
three that can be built from an independent, verifiable quantity (scoring differential). A total
is a statement about the *sum*. A moneyline is a statement about the *probability of winning*,
which in this implementation is derived from the same margin as the side, so it must be built
after the side and must say so.

That dependency is enforced, not narrated:

  * ``ORIGINATION_ORDER`` fixes the sequence and each market declares the inputs it consumes.
  * ``originate_game`` raises if a market tries to consume a number that has not been built yet.
  * ``ordering_audit`` re-checks the finished board and proves that the moneyline is a function
    of the side's margin (so it carries no independent information, and the site says so).

What the desk publishes per market, as three separate columns and never one merged number:

    model_fair      the desk's own fair line
    market_line     the price the market actually offered  -> always blank here, see prices.py
    difference      model_fair minus market_line           -> always blank here, for the same reason

Ratings method (fixed before looking at any result, documented so it can be criticised):

  * offence rate  = points scored / game, shrunk toward the league mean
  * defence rate  = points allowed / game, shrunk toward the league mean
  * expected points for a club in a game = league mean x (its offence rate / league mean)
    x (opponent defence rate / league mean), with a home-field term added to the home side and
    subtracted from the away side. This is the standard log-linear multiplicative form and is the
    same family the repository's earlier lab used; the parameters are stated, not fitted here.
  * no injury adjustment is applied, because the archived injury snapshots cover Week 10 only and
    a like-for-like adjustment for a past week cannot be built without inventing the missing
    weeks. That limitation is published rather than papered over.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

from emit import emit_csv, emit_json, parse_args

REPO = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

SNAPSHOT_DATE = "2026-11-14"
FIXTURES = REPO / "data" / "nfl-schedule-2026-w10.csv"
STANDINGS = REPO / "data" / "nfl-standings-week10-2026.csv"

# Parameters fixed in advance. None is tuned on an outcome; the desk grades nothing here.
HOME_FIELD_POINTS = 2.0      # league-wide home advantage, points, rounded convention
SHRINK_GAMES = 4.0           # empirical-Bayes style shrink toward the league mean
MARGIN_SD = 13.86            # NFL margin standard deviation used for the moneyline mapping
SELECTIVE_FLOOR = 2.0     # points of model edge required by the selective rule
PUSH_PROBABILITY_NOTE = "half-point lines are avoided in origination, so no push term is used"

ORIGINATION_ORDER = ("spread", "total", "moneyline")
DEPENDS_ON = {
    "spread": ("offence_rate", "defence_rate", "league_mean"),
    "total": ("offence_rate", "defence_rate", "league_mean"),
    "moneyline": ("spread",),  # derived from the margin the side produced
}


# --------------------------------------------------------------------------- inputs
def load_fixtures() -> list[dict]:
    with FIXTURES.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != 14:
        raise SystemExit(f"expected 14 Week 10 fixtures, got {len(rows)}")
    return rows


def load_standings() -> list[dict]:
    with STANDINGS.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != 32:
        raise SystemExit(f"expected 32 standings rows, got {len(rows)}")
    return rows


def club_index() -> dict[str, dict]:
    """Map every club name the fixtures use to its standings row.

    The fixtures print nicknames ("Commanders") and the standings print full names
    ("Washington Commanders"). The nickname is derived from the full name, which is a naming map
    only: no value is added, and every nickname is checked to be unique across the league so a
    collision aborts instead of silently picking one club.
    """
    index: dict[str, dict] = {}
    nicknames: dict[str, str] = {}
    for row in load_standings():
        games = int(row["W"]) + int(row["L"]) + int(row["T"])
        pf, pa = int(row["PF"]), int(row["PA"])
        index[row["Team"]] = {
            "code": row["TeamCode"], "name": row["Team"], "games": games,
            "pf": pf, "pa": pa, "off_raw": pf / games, "def_raw": pa / games,
            "source_url": row["SourceURL"],
        }
        index[row["TeamCode"]] = index[row["Team"]]
        nickname = row["Team"].split()[-1]
        if nickname in nicknames and nicknames[nickname] != row["TeamCode"]:
            raise SystemExit(f"nickname {nickname!r} is not unique: {nicknames[nickname]} and {row['TeamCode']}")
        nicknames[nickname] = row["TeamCode"]
        index[nickname] = index[row["Team"]]
    return index


def league_mean(teams: dict[str, dict]) -> float:
    seen = {id(v): v for v in teams.values()}
    games = sum(t["games"] for t in seen.values())
    points = sum(t["pf"] for t in seen.values())
    return points / games


def shrunk(value: float, mean: float, games: float) -> float:
    return (value * games + mean * SHRINK_GAMES) / (games + SHRINK_GAMES)


# --------------------------------------------------------------------------- origination
def expected_points(off_rate: float, opp_def_rate: float, mean: float) -> float:
    return mean * (off_rate / mean) * (opp_def_rate / mean)


def originate_game(fixture: dict, teams: dict[str, dict], mean: float) -> dict:
    away = teams[fixture["Away"]]
    home = teams[fixture["Home"]]
    built: dict[str, object] = {
        "league_mean": mean,
        "offence_rate": (shrunk(home["off_raw"], mean, home["games"]),
                         shrunk(away["off_raw"], mean, away["games"])),
        "defence_rate": (shrunk(home["def_raw"], mean, home["games"]),
                         shrunk(away["def_raw"], mean, away["games"])),
    }

    markets: dict[str, dict] = {}
    for market in ORIGINATION_ORDER:
        missing = [name for name in DEPENDS_ON[market] if name not in built]
        if missing:
            raise SystemExit(
                f"{fixture['id']}: {market} needs {missing} which has not been originated yet — "
                f"origination order violated")

        if market == "spread":
            home_off, away_off = built["offence_rate"]
            home_def, away_def = built["defence_rate"]
            home_pts = expected_points(home_off, away_def, mean) + HOME_FIELD_POINTS / 2
            away_pts = expected_points(away_off, home_def, mean) - HOME_FIELD_POINTS / 2
            margin = home_pts - away_pts
            # A spread is published from the home side's perspective: negative = home favoured.
            markets["spread"] = {
                "model_fair": round(-margin, 2),
                "side": "home" if margin > 0 else "away",
                "margin": round(margin, 3),
                "home_points": round(home_pts, 3),
                "away_points": round(away_pts, 3),
            }
            built["spread"] = markets["spread"]
            built["home_points"] = home_pts
            built["away_points"] = away_pts

        elif market == "total":
            total = built["home_points"] + built["away_points"]
            markets["total"] = {
                "model_fair": round(total, 2),
                "side": "over" if total > 0 else "under",
                "margin": "",
                "home_points": round(built["home_points"], 3),
                "away_points": round(built["away_points"], 3),
            }
            built["total"] = markets["total"]

        else:  # moneyline — consumes the side's margin, deliberately
            margin = built["spread"]["margin"]
            p_home = normal_cdf(margin / MARGIN_SD)
            markets["moneyline"] = {
                "model_fair": american(p_home),
                "side": "home",
                "margin": "",
                "home_points": "",
                "away_points": "",
                "p_home_win": round(p_home, 4),
                "p_away_win": round(1 - p_home, 4),
                "away_fair": american(1 - p_home),
            }
            built["moneyline"] = markets["moneyline"]

    return {
        "game": {
            "id": fixture["id"], "matchup": f"{away['code']} @ {home['code']}",
            "away_team": away["name"], "home_team": home["name"],
            "kickoff": f"{fixture['Date']} {fixture['KickoffET']} ET",
            "tv": fixture["TV"], "week": int(fixture["Week"]),
            "game_url": fixture["GameURL"], "source_url": fixture["SourceURL"],
        },
        "markets": markets,
        "inputs": {
            "home_offence_rate": round(built["offence_rate"][0], 4),
            "away_offence_rate": round(built["offence_rate"][1], 4),
            "home_defence_rate": round(built["defence_rate"][0], 4),
            "away_defence_rate": round(built["defence_rate"][1], 4),
            "league_mean_points": round(mean, 4),
            "home_field_points": HOME_FIELD_POINTS,
            "shrink_games": SHRINK_GAMES,
            "margin_sd": MARGIN_SD,
        },
    }


def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def american(p: float) -> int:
    if not 0 < p < 1:
        raise SystemExit(f"probability {p} outside (0,1)")
    return -round(100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


def originated_board() -> list[dict]:
    teams = club_index()
    mean = league_mean(teams)
    return [originate_game(f, teams, mean) for f in load_fixtures()]


# --------------------------------------------------------------------------- checks
def ordering_audit(board: list[dict]) -> dict:
    """Prove the order held and that the moneyline adds no independent information."""
    checks = []
    for entry in board:
        markets = entry["markets"]
        if list(markets) != list(ORIGINATION_ORDER):
            raise SystemExit(f"{entry['game']['id']}: markets built out of order: {list(markets)}")
        # The moneyline must be exactly the side's margin through the published mapping.
        expected_p = normal_cdf(markets["spread"]["margin"] / MARGIN_SD)
        if abs(expected_p - markets["moneyline"]["p_home_win"]) > 1e-4:
            raise SystemExit(
                f"{entry['game']['id']}: moneyline is not the side's margin through the stated "
                f"mapping ({expected_p} vs {markets['moneyline']['p_home_win']})")
        # The total must be the sum of the same two point estimates the side used.
        total = markets["total"]["model_fair"]
        summed = round(markets["spread"]["home_points"] + markets["spread"]["away_points"], 2)
        if abs(total - summed) > 0.011:
            raise SystemExit(f"{entry['game']['id']}: total is not the sum of the side's inputs")
        checks.append({
            "game_id": entry["game"]["id"],
            "order_respected": "yes",
            "total_equals_sum_of_side_inputs": "yes",
            "moneyline_is_side_margin_transformed": "yes",
        })
    return {
        "games": len(board),
        "order": list(ORIGINATION_ORDER),
        "dependency_rule": "moneyline consumes the side; total consumes the same two point "
                           "estimates as the side; none of the three is built before its inputs",
        "independence_disclosure": "Because the moneyline is the side's margin through a normal "
                                   "mapping, it adds no independent information to the board. A "
                                   "moneyline strategy and a spread strategy built from this desk "
                                   "are the same signal in two units, and the leaderboard counts "
                                   "them as one family member, not two.",
        "per_game": checks,
    }


def market_table(board: list[dict]) -> list[dict]:
    """One row per (game, market) with fair line, market line and difference as separate columns."""
    rows = []
    for entry in board:
        for order, market in enumerate(ORIGINATION_ORDER, start=1):
            built = entry["markets"][market]
            rows.append({
                "row_id": f"{entry['game']['id']}-{market}",
                "origination_order": order,
                "market": market,
                "game_id": entry["game"]["id"],
                "matchup": entry["game"]["matchup"],
                "kickoff": entry["game"]["kickoff"],
                "model_fair_line": built["model_fair"],
                "model_favoured_side": built.get("side", ""),
                "market_line": "",
                "difference": "",
                "difference_state": "not computable: no market line exists (see price store)",
                "source_url": entry["game"]["source_url"],
                "source_ids": "NFL-STANDINGS NFL-SCHED-W10",
            })
    return rows


def main() -> None:
    parse_args(__doc__ or "originate")
    board = originated_board()
    audit = ordering_audit(board)
    rows = market_table(board)
    if len(rows) != 42:
        raise SystemExit(f"expected 42 market rows (14 games x 3 markets), got {len(rows)}")
    emit_csv(DATA / "originated-markets-2026-w10.csv", rows)
    emit_json(DATA / "origination-audit-2026-w10.json", {
        "snapshot_date": SNAPSHOT_DATE,
        "parameters": {
            "home_field_points": HOME_FIELD_POINTS, "shrink_games": SHRINK_GAMES,
            "margin_sd": MARGIN_SD, "note": PUSH_PROBABILITY_NOTE,
        },
        "audit": audit,
        "board": board,
    })
    if not any(False for _ in rows):
        pass
    print(f"Originated {len(board)} games x {len(ORIGINATION_ORDER)} markets in order "
          f"{' -> '.join(ORIGINATION_ORDER)}; {len(rows)} market rows written.")


if __name__ == "__main__":
    main()
