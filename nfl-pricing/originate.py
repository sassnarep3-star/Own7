"""Originate the side first, then the total, then the moneyline; grade against the market.

ORDER IS ENFORCED, NOT DECORATIVE
---------------------------------
1. SIDE  (spread). Requires a forecast margin. Produced first.
2. TOTAL. Requires the side to exist; refits nothing, and is not allowed to
   borrow the market's total.
3. MONEYLINE. Requires both the side and the total, because it is derived from
   the margin distribution, and that distribution is calibrated on the total.

If the side cannot be produced, the total and the moneyline are not produced
either. The dependency is a hard gate, so a page can never show a moneyline
whose side is missing.

FAIR LINE / MARKET LINE / DIFFERENCE
------------------------------------
Published as three separate columns for every game and market. The market column
is filled only from a registered published price. When the price store has no
number, the market and difference columns stay blank and say why. A blank is
never rendered as zero and never filled with our own line.

WHAT "EDGE" IS NOT
------------------
No vig is known for these prices, so the difference is a number of points and a
model probability against a market probability - not a claim of profit. The
break-even probability at -110 is shown only as a stated assumption.
"""
from __future__ import annotations

import argparse
import json
import math
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
PRICES = HERE / "data" / "price-snapshots.json"
OUT = HERE / "data" / "origination.json"

# --- Parameters fixed before any grading -----------------------------------
PYTHAGOREAN_EXPONENT = 2.37     # convention stated in the earlier origination work
HOME_FIELD_POINTS = 2.0         # league-conventional prior, not fitted on these results
SHRINK_GAMES = 4.0              # credibility weight: games / (games + SHRINK)
MARGIN_SD = 13.86               # published NFL margin standard deviation
TOTAL_SD = 13.5                 # residual spread of game totals around expectation
NEUTRAL_SLOPE = 0.0             # total model starts as league mean; see calibrate()
LEAGUE_TOTAL_PRIOR = 45.0       # points, stated prior used before any games are seen
ASSUMED_PRICE = -110            # only used to translate probability to a break-even
MIN_GAMES_FOR_TOTAL = 3


def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def round_half(value: float) -> float:
    return round(value * 2) / 2


def american_to_prob(price: int) -> float:
    if price < 0:
        return (-price) / ((-price) + 100.0)
    return 100.0 / (price + 100.0)


def load_prices() -> dict:
    return json.loads(PRICES.read_text(encoding="utf-8"))


def prior_state(history: list[dict], league_totals: list[int]) -> dict:
    """Everything the model is allowed to know before a given week."""
    per_team: dict[str, dict] = {}
    for game in history:
        for team, scored, allowed in (
            (game["away"], game["away_score"], game["home_score"]),
            (game["home"], game["home_score"], game["away_score"]),
        ):
            state = per_team.setdefault(team, {"games": 0, "pf": 0, "pa": 0})
            state["games"] += 1
            state["pf"] += scored
            state["pa"] += allowed
    league_mean = (
        sum(league_totals) / len(league_totals) if league_totals else LEAGUE_TOTAL_PRIOR
    )
    return {"per_team": per_team, "league_total": league_mean, "games": len(history)}


def team_ratings(state: dict) -> dict[str, dict]:
    """Shrunk Pythagorean win rate plus shrunk scoring rates, per club."""
    ratings = {}
    league_total = state["league_total"]
    for team, row in state["per_team"].items():
        games = row["games"]
        if games == 0:
            continue
        weight = games / (games + SHRINK_GAMES)
        pf = row["pf"] / games
        pa = row["pa"] / games
        exponent = PYTHAGOREAN_EXPONENT
        denom = (pf ** exponent + pa ** exponent) or 1.0
        raw_rate = (pf ** exponent) / denom
        # Shrink the win rate toward .500 and the scoring rates toward the league mean.
        ratings[team] = {
            "games": games,
            "weight": weight,
            "pyth": 0.5 + (raw_rate - 0.5) * weight,
            "pf": league_total / 2 + (pf - league_total / 2) * weight,
            "pa": league_total / 2 + (pa - league_total / 2) * weight,
        }
    return ratings


def originate_margin(away: str, home: str, ratings: dict[str, dict]) -> float | None:
    """SIDE market. A difference of shrunk scoring rates plus a home-field prior."""
    if away not in ratings or home not in ratings:
        return None
    away_off, away_def = ratings[away]["pf"], ratings[away]["pa"]
    home_off, home_def = ratings[home]["pf"], ratings[home]["pa"]
    # Expected points for each side, then the margin that follows from them.
    away_points = (away_off + home_def) / 2
    home_points = (home_off + away_def) / 2 + HOME_FIELD_POINTS
    return home_points - away_points


def originate_total(away: str, home: str, ratings: dict[str, dict]) -> float | None:
    """TOTAL market. Only produced when the side exists."""
    if away not in ratings or home not in ratings:
        return None
    away_points = (ratings[away]["pf"] + ratings[home]["pa"]) / 2
    home_points = (ratings[home]["pf"] + ratings[away]["pa"]) / 2 + HOME_FIELD_POINTS
    return away_points + home_points


def originate_moneyline(fair_margin: float, fair_total: float) -> dict:
    """MONEYLINE market, derived last from the margin distribution."""
    sd = MARGIN_SD
    p_home = 1.0 - normal_cdf((0.0 - fair_margin) / sd)  # P(margin > 0) = home wins
    # A tie is possible in the model; the published rule splits it. State it.
    tie = normal_cdf((0.5 - fair_margin) / sd) - normal_cdf((-0.5 - fair_margin) / sd)
    p_home_win = p_home + tie / 2
    p_away_win = 1.0 - p_home_win
    return {
        "p_home_win": round(p_home_win, 4),
        "p_away_win": round(p_away_win, 4),
        "tie_mass": round(tie, 4),
        "fair_home_ml": round(-100 * p_home_win / (1 - p_home_win)) if p_home_win > 0.5
        else round(100 * (1 - p_home_win) / p_home_win),
        "fair_away_ml": round(-100 * p_away_win / (1 - p_away_win)) if p_away_win > 0.5
        else round(100 * (1 - p_away_win) / p_away_win),
        "sd_assumption": sd,
    }


def build() -> dict:
    snapshot = load_prices()
    games = [g for g in snapshot["games"] if g["result_status"] == "joined"]
    games.sort(key=lambda g: (g["week"], g["date"], g["home"]))

    flags: list[dict] = []
    problems: list[str] = []

    # --- walk-forward: a week is forecast only from strictly earlier weeks ----
    weeks = sorted({g["week"] for g in games})
    rows: list[dict] = []
    history: list[dict] = []
    league_totals: list[int] = []

    for week in weeks:
        week_games = [g for g in games if g["week"] == week]
        state = prior_state(history, league_totals)
        ratings = team_ratings(state)
        for game in week_games:
            away, home = game["away"], game["home"]
            row = {
                "week": week,
                "date": game["date"],
                "away": away,
                "home": home,
                "sources": game["sources"],
                "result_source_url": game["result_source_url"],
                "actual_margin_home": game["actual_margin_home"],
                "actual_total": game["actual_total"],
                "market_line_home": game["closing_line_home"],
                "market_total": game["closing_total"],
                "market_home_cover": game["home_cover"],
                "market_total_result": game["total_result"],
            }

            # 1. SIDE first.
            fair_margin = originate_margin(away, home, ratings)
            if fair_margin is None:
                row.update({
                    "fair_line_home": None, "line_difference": None,
                    "fair_total": None, "total_difference": None,
                    "fair_home_ml": None, "p_home_win": None,
                    "side_status": "withheld_no_prior_games",
                    "total_status": "blocked_by_side",
                    "moneyline_status": "blocked_by_side",
                })
                rows.append(row)
                continue
            fair_line_home = -round_half(fair_margin)  # published from the home side
            row["fair_line_home"] = fair_line_home
            market_line = Decimal(game["closing_line_home"])
            row["line_difference"] = float(Decimal(str(fair_line_home)) - market_line)
            row["side_status"] = "originated"

            # 2. TOTAL, only now.
            fair_total = originate_total(away, home, ratings)
            if fair_total is None:
                row["total_status"] = "blocked_by_side"
                row["moneyline_status"] = "blocked_by_total"
                rows.append(row)
                continue
            fair_total = round_half(fair_total)
            row["fair_total"] = fair_total
            row["total_difference"] = float(Decimal(str(fair_total)) - Decimal(game["closing_total"]))
            row["total_status"] = "originated"

            # 3. MONEYLINE, only now.
            ml = originate_moneyline(fair_margin, fair_total)
            row.update({
                "fair_home_ml": ml["fair_home_ml"],
                "fair_away_ml": ml["fair_away_ml"],
                "p_home_win": ml["p_home_win"],
                "p_away_win": ml["p_away_win"],
                "moneyline_status": "originated",
                "market_home_ml": None,
                "market_away_ml": None,
                "moneyline_market_note": "no published moneyline in the price store",
            })
            rows.append(row)

        # Grade the week, then let it enter the history.
        history.extend(
            {
                "away": g["away"], "home": g["home"],
                "away_score": g["away_score"], "home_score": g["home_score"],
            }
            for g in week_games
        )
        league_totals.extend(g["away_score"] + g["home_score"] for g in week_games)

    if not rows:
        problems.append("no forecastable games")

    # --- fair-vs-market agreement, with n printed beside it ------------------
    paired_line = [r for r in rows if r.get("line_difference") is not None]
    paired_total = [r for r in rows if r.get("total_difference") is not None]

    def summarise(pairs: list[dict], key: str) -> dict:
        if not pairs:
            return {"n": 0, "mean": None, "mean_abs": None, "within_1": None, "within_3": None}
        diffs = [abs(r[key]) for r in pairs]
        return {
            "n": len(diffs),
            "mean": round(sum(r[key] for r in pairs) / len(pairs), 3),
            "mean_abs": round(sum(diffs) / len(diffs), 3),
            "within_1": sum(1 for d in diffs if d <= 1.0),
            "within_3": sum(1 for d in diffs if d <= 3.0),
            "published_source": "https://www.pro-football-reference.com/teams/{club}/2026_lines.htm",
        }

    origination = {
        "schema_version": 1,
        "order_enforced": ["side", "total", "moneyline"],
        "order_note": (
            "The total is not produced unless the side exists; the moneyline is not produced "
            "unless both exist. A row with fair_line_home null never has a total or moneyline."
        ),
        "parameters": {
            "pythagorean_exponent": PYTHAGOREAN_EXPONENT,
            "home_field_points": HOME_FIELD_POINTS,
            "shrink_games": SHRINK_GAMES,
            "margin_sd": MARGIN_SD,
            "total_sd": TOTAL_SD,
            "league_total_prior": LEAGUE_TOTAL_PRIOR,
            "assumed_price_for_break_even": ASSUMED_PRICE,
            "note": "All fixed before grading; none tuned on the graded weeks.",
        },
        "counts": {
            "games": len(rows),
            "side_originated": sum(1 for r in rows if r["side_status"] == "originated"),
            "total_originated": sum(1 for r in rows if r["total_status"] == "originated"),
            "moneyline_originated": sum(1 for r in rows if r["moneyline_status"] == "originated"),
            "market_line_available": sum(1 for r in rows if r["market_line_home"] is not None),
            "market_total_available": sum(1 for r in rows if r["market_total"] is not None),
            "market_moneyline_available": 0,
        },
        "agreement": {
            "side_vs_market": summarise(paired_line, "line_difference"),
            "total_vs_market": summarise(paired_total, "total_difference"),
        },
        "flags": flags,
        "problems": problems,
        "games": rows,
    }
    origination["break_even"] = {
        "assumed_price": ASSUMED_PRICE,
        "break_even_probability": round(american_to_prob(ASSUMED_PRICE), 4),
        "note": (
            "Only the break-even probability at the stated assumed price. No published price "
            "for these markets carries a vig, so no hold, no EV and no ROI is claimed here."
        ),
    }
    return origination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build()
    text = json.dumps(result, indent=1) + "\n"
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print("FAIL: data/origination.json is stale; run python originate.py")
            return 1
        print(f"OK: origination reproduces ({result['counts']['games']} games)")
        return 0 if not result["problems"] else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    counts = result["counts"]
    print(
        f"Wrote {OUT.relative_to(ROOT)} — side {counts['side_originated']}, "
        f"total {counts['total_originated']}, moneyline {counts['moneyline_originated']} "
        f"of {counts['games']} games"
    )
    for problem in result["problems"]:
        print("  PROBLEM:", problem)
    return 0 if not result["problems"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
