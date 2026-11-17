"""Requirement 4 — publish the fair line, the market line and the difference.

Three separate columns, always. The rule that matters is the third one: a difference is
printed only when a market line exists. When the market line is blank the difference is
blank too. It is never zero, never the fair line restated, and never a placeholder.

A reader should be able to look at one row and see exactly what the model says, exactly
what the market said, and whether anyone has actually recorded the second one.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, check_artifact, normal_cdf, round_value, write_csv  # noqa: E402

OUT = DATA / "boards.json"
OUT_CSV = DATA / "boards.csv"
ORIGINATION = DATA / "origination.json"
BACKTEST = DATA / "backtest.json"

NO_MARKET = ("No consulted official source publishes a price or a point spread for this "
             "market (see the nfl.com/odds/ negative result, CP-NFL-ODDS-ABSENT). Blank, "
             "not zero.")

FIELDS = [
    "market_id", "game_id", "matchup", "market", "selection",
    "fair_line", "market_line", "difference",
    "fair_price", "market_price", "price_difference",
    "fair_line_basis", "status", "game_url", "source_ids",
]


def build():
    import json
    origination = json.loads(Path(ORIGINATION).read_text(encoding="utf-8"))
    backtest = json.loads(Path(BACKTEST).read_text(encoding="utf-8"))
    residual = backtest["forecast_quality"]

    rows = []
    for game in origination["board"]:
        spread = game["stage_1_side"]["spread_home"]
        total = game["stage_2_total"]["total"]
        p_home = game["stage_3_moneyline"]["p_home"]
        p_away = game["stage_3_moneyline"]["p_away"]
        base = {
            "game_id": game["game_id"], "matchup": game["matchup"],
            "game_url": game["game_url"],
            "source_ids": ";".join(game["source_ids"]),
        }
        rows.append({**base,
                     "market_id": f"{game['game_id']}-SIDE-HOME", "market": "Side",
                     "selection": f"{game['home']} (home)",
                     "fair_line": spread, "market_line": None,
                     "difference": None,
                     "fair_price": 100, "market_price": None, "price_difference": None,
                     "fair_line_basis": "Stage 1. Convention: negative favours the home "
                                        "club. Fair price is +100 because a side covers "
                                        "its own line half the time by construction.",
                     "status": "Originated only"})
        rows.append({**base,
                     "market_id": f"{game['game_id']}-SIDE-AWAY", "market": "Side",
                     "selection": f"{game['away']} (away)",
                     "fair_line": -spread, "market_line": None, "difference": None,
                     "fair_price": 100, "market_price": None, "price_difference": None,
                     "fair_line_basis": "The same stage-1 number, seen from the away "
                                        "club. Fair price +100 for the same reason.",
                     "status": "Originated only"})

        over_p = None
        if residual.get("total_bias") is not None and residual.get("total_residual_sd"):
            # P(actual total > model total) measured from the 121 walk-forward residuals.
            over_p = normal_cdf(-residual["total_bias"] / residual["total_residual_sd"])
        rows.append({**base,
                     "market_id": f"{game['game_id']}-TOTAL-OVER", "market": "Total",
                     "selection": "Over",
                     "fair_line": total, "market_line": None, "difference": None,
                     "fair_price": None if over_p is None else american(over_p),
                     "market_price": None, "price_difference": None,
                     "fair_line_basis": "Stage 2: the sum of the stage-1 pair.",
                     "status": "Originated only"})
        rows.append({**base,
                     "market_id": f"{game['game_id']}-TOTAL-UNDER", "market": "Total",
                     "selection": "Under",
                     "fair_line": total, "market_line": None, "difference": None,
                     "fair_price": None if over_p is None else american(1 - over_p),
                     "market_price": None, "price_difference": None,
                     "fair_line_basis": "Stage 2: the sum of the stage-1 pair.",
                     "status": "Originated only"})
        rows.append({**base,
                     "market_id": f"{game['game_id']}-MONEYLINE-HOME",
                     "market": "Moneyline", "selection": f"{game['home']} (home)",
                     "fair_line": None, "market_line": None, "difference": None,
                     "fair_price": game["stage_3_moneyline"]["fair_price_home"],
                     "market_price": None, "price_difference": None,
                     "fair_line_basis": "Stage 3: a moneyline has no points, so the line "
                                        "column is blank by definition and the fair value "
                                        "is carried as a price.",
                     "status": "Originated only"})
        rows.append({**base,
                     "market_id": f"{game['game_id']}-MONEYLINE-AWAY",
                     "market": "Moneyline", "selection": f"{game['away']} (away)",
                     "fair_line": None, "market_line": None, "difference": None,
                     "fair_price": game["stage_3_moneyline"]["fair_price_away"],
                     "market_price": None, "price_difference": None,
                     "fair_line_basis": "Stage 3: as above, from the away side.",
                     "status": "Originated only"})

    # Integrity: a difference may only exist where a market line exists.
    violations = [
        row["market_id"] for row in rows
        if row["difference"] is not None and row["market_line"] is None
    ]
    if violations:
        raise SystemExit(f"REFUSING TO PUBLISH: difference without a market line: "
                         f"{violations[:5]}")
    if any(row["market_line"] is not None for row in rows):
        raise SystemExit("REFUSING TO PUBLISH: a market line appeared without a "
                         "registered official source that publishes one")

    write_csv(OUT_CSV, rows, FIELDS)
    payload = {
        "requirement": "R4 - fair line, market line and difference as separate columns",
        "built_on": "2026-11-14",
        "games": len(origination["board"]),
        "markets": len(rows),
        "columns": {
            "fair_line": "The model's number, from the three-stage origination.",
            "market_line": NO_MARKET,
            "difference": "fair_line minus market_line. Blank whenever the market line "
                          "is blank; never printed as zero.",
            "fair_price": "The model's fair, zero-hold price. Not an offered price.",
            "market_price": NO_MARKET,
            "price_difference": "Blank whenever the market price is blank.",
        },
        "why_the_difference_is_blank": [
            "NFL.com returns a 404 at /odds/ and prints no spread, total or price on "
            "any page this project read, including the Week 10 game page.",
            "No operator or sportsbook was consulted: the NFL.com terms restrict use of "
            "the material to individual non-commercial informational purposes, and the "
            "project has no written consent to retrieve prices systematically.",
            "A difference is the whole point of the column, so it is left empty rather "
            "than filled with an estimate that would look like an edge.",
        ],
        "over_price_derivation": {
            "method": "P(actual total > model total) from the 121 walk-forward residuals",
            "n": residual.get("n"),
            "mean_residual_model_minus_actual": residual.get("total_bias"),
            "residual_sd": residual.get("total_residual_sd"),
            "p_over": over_p,
            "caveat": "This measures the model's own tendency to over-forecast totals. "
                      "It is not a market comparison and not a claim of value.",
        },
        "rows": rows,
    }
    return round_value(payload, 6)


def american(p):
    from model import american_from_probability
    return american_from_probability(p)


def main():
    if check_artifact(OUT, build()):
        payload = build()
        print(f"  {payload['markets']} market rows across {payload['games']} games; "
              f"every market_line and difference blank by rule")


if __name__ == "__main__":
    main()
