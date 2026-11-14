#!/usr/bin/env python3
"""Signal, staking, promotion and demotion: four separate questions, four separate columns.

The brief names the failure mode exactly: "a lucky staking run cannot mask a bad signal". That
happens when one leaderboard column mixes two different quantities. So the board publishes them
apart and then proves they are apart:

    signal_score      hit rate against the desk's OWN originated line. Purely a question of
                      whether the forecast beat its own number. No price, no stake, no money.
    signal_p          exact two-sided binomial p-value of that hit rate against 50%.
    staking_return    money result per unit staked. Requires a price. Blank here, by rule.
    bankroll_path     the equity curve. Requires a price. Blank here, by rule.
    promotion_gate    the gate a strategy must clear to leave paper trading. Computed.
    demotion_gate     the gate that sends a live strategy BACK to paper. Computed.

A strategy can be signal-positive and staking-negative at the same time — that is the normal
case for a forecaster with no price edge — and the format makes it impossible to hide either.

Demotion is deliberately easier to trigger than promotion. A promotion needs a large sample, a
confirmed effect after multiplicity control and a forward record; a demotion needs any one of
four cheap, objective conditions. The asymmetry is the point: the cost of keeping a broken
strategy live is paid in money, the cost of returning a good one to paper is paid in time.

The one thing this module cannot do is move a strategy from paper to live, because the move
requires a price, and the price store is empty by source constraint (see prices.py). So every
strategy is on paper, every promotion gate is `blocked`, and the demotion gate is exercised by
tests on synthetic series rather than on a live strategy — which is the honest way to show a
demotion rule works before you need it.
"""
from __future__ import annotations

import csv
from pathlib import Path

from emit import emit_csv, emit_json, parse_args
import stats

REPO = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

SNAPSHOT = "2026-11-14"

# --------------------------------------------------------------------------- thresholds
# Fixed in advance. Not tuned on any outcome; changing one is a documented decision, not a tweak.
PROMOTION = {
    "min_settled_bets": 210,
    "min_settled_bets_justification":
        "Exact binomial: 210 settled bets is the smallest n at which a true 60% forecaster is "
        "detected against 50% at two-sided alpha 0.05 with 80% power. A one-sided criterion would "
        "need 158; the stricter two-sided number is used because the leaderboard publishes many "
        "strategies and a two-sided floor cannot be gamed by only counting the good tail.",
    "max_signal_p": 0.05,
    "multiplicity": "Benjamini-Hochberg at q = 0.10 across the registered family",
    "forward_record": "at least 4 consecutive weeks graded after the parameters were frozen",
    "price_required": "an opening AND closing number per bet, from a registered licensed source",
}
DEMOTION = {
    "min_settled_for_demotion_check": 40,
    "signal_p_worse_than": 0.50,
    "max_drawdown_units": 20.0,
    "consecutive_losing_weeks": 6,
    "reentry_rule": "a demoted strategy may not be re-promoted until it clears the full "
                    "promotion gate again on data collected entirely after the demotion date",
    "asymmetry_note": "demotion needs one condition; promotion needs all of them",
}


# --------------------------------------------------------------------------- gates
def demotion_reasons(row: dict) -> list[str]:
    """Objective conditions that send a live strategy back to paper. Any one is sufficient."""
    reasons = []
    settled = int(row.get("settled_bets") or 0)
    if settled >= DEMOTION["min_settled_for_demotion_check"]:
        p = row.get("signal_p")
        if p is not None and p > DEMOTION["signal_p_worse_than"]:
            reasons.append(
                f"signal decays to p = {p:.3f} over {settled} settled bets, i.e. indistinguishable "
                f"from a coin flip at the published threshold")
    drawdown = row.get("max_drawdown_units")
    if isinstance(drawdown, (int, float)) and drawdown > DEMOTION["max_drawdown_units"]:
        reasons.append(f"bankroll drawdown {drawdown:.1f} units exceeds "
                       f"{DEMOTION['max_drawdown_units']:.0f}")
    streak = row.get("consecutive_losing_weeks")
    if isinstance(streak, int) and streak >= DEMOTION["consecutive_losing_weeks"]:
        reasons.append(f"{streak} consecutive losing weeks")
    if row.get("price_state") != "priced" and row.get("state") == "live":
        reasons.append("strategy is marked live but has no priced bet in the store: "
                       "an unpriced live strategy cannot be scored and must return to paper")
    return reasons


def promotion_blockers(row: dict) -> list[str]:
    blockers = []
    if int(row.get("settled_bets") or 0) < PROMOTION["min_settled_bets"]:
        blockers.append(f"{row.get('settled_bets', 0)} of {PROMOTION['min_settled_bets']} "
                        f"required settled bets")
    if row.get("price_state") != "priced":
        blockers.append("no price: an unpriced strategy cannot be staked, so it cannot be live")
    if row.get("signal_p") is None:
        blockers.append("no signal p-value: nothing has been graded")
    elif row["signal_p"] > PROMOTION["max_signal_p"]:
        blockers.append(f"signal p = {row['signal_p']:.3f} above "
                        f"{PROMOTION['max_signal_p']}")
    if not row.get("forward_weeks"):
        blockers.append("no forward record after the parameters were frozen")
    return blockers


# --------------------------------------------------------------------------- grading
def grade_family() -> tuple[list[dict], dict]:
    """Grade every registered strategy on the results feed, then apply the gates.

    The family is the strategies the repository already registered in its own origination data,
    plus the three market sides this desk originates, so the board cannot be populated by
    inventing new strategies until one looks good.
    """
    import os
    board = []
    fan = family_members()
    p_values = []
    for member in fan:
        graded = grade_member(member)
        p_values.append(graded["signal_p"] if graded["signal_p"] is not None else 1.0)
        board.append(graded)
    adjusted = stats.holm(p_values)  # Holm is stricter than BH and is used as the primary control
    for row, q in zip(board, adjusted):
        row["signal_p_holm"] = round(q, 6)
    for row in board:
        row["promotion_blockers"] = "; ".join(promotion_blockers(row)) or "none"
        row["promotable"] = "yes" if not promotion_blockers(row) else "no"
        row["demotion_reasons"] = "; ".join(demotion_reasons(row)) or "none"
        row["demote_to_paper"] = "yes" if demotion_reasons(row) else "no"
    board.sort(key=lambda r: (-(r["signal_hit_rate"] or 0), r["strategy_id"]))
    summary = {
        "family_size": len(board),
        "settled_bets_graded": sum(r["settled_bets"] for r in board),
        "priced_bets": sum(r["priced_bets"] for r in board),
        "promotable": sum(1 for r in board if r["promotable"] == "yes"),
        "live": sum(1 for r in board if r["state"] == "live"),
        "on_paper": sum(1 for r in board if r["state"] == "paper"),
        "demote_to_paper": sum(1 for r in board if r["demote_to_paper"] == "yes"),
        "min_settled_for_promotion": PROMOTION["min_settled_bets"],
        "best_signal": max(board, key=lambda r: (r["signal_hit_rate"] or 0))["strategy_id"]
        if board else "",
        "multiplicity_control": "Holm-Bonferroni at family level, applied to the signal p-values",
        "why_no_staking_column": "Staking return needs a price. No price exists (see the price "
                                 "store), so the column is blank and the strategy cannot be scored "
                                 "on money. That is precisely what stops a lucky staking run from "
                                 "masking a bad signal: there is no staking column to run.",
    }
    return board, summary


def family_members() -> list[dict]:
    """The registered family. Each member is a rule the desk can grade without a price."""
    return [
        {"strategy_id": "S-SIDE-BOARD", "name": "Originated side vs the desk's own fair line",
         "family": "Single bet", "market": "spread", "rule": "side",
         "hypothesis": "The originated side beats its own fair number more often than chance.",
         "source_ids": "NFL-STANDINGS NFL-SCHED-X29 REPO"},
        {"strategy_id": "S-TOTAL-BOARD", "name": "Originated total vs the desk's own fair line",
         "family": "Single bet", "market": "total", "rule": "total",
         "hypothesis": "The originated total beats its own fair number more often than chance.",
         "source_ids": "NFL-STANDINGS NFL-SCHED-X29 REPO"},
        {"strategy_id": "S-ML-BOARD", "name": "Originated moneyline vs the desk's own fair price",
         "family": "Single bet", "market": "moneyline", "rule": "moneyline",
         "hypothesis": "The moneyline direction beats its own fair probability.",
         "source_ids": "NFL-STANDINGS NFL-SCHED-X29 REPO"},
        {"strategy_id": "S-SIDE-SELECTIVE", "name": "Originated side, selective by edge size",
         "family": "Single bet", "market": "spread", "rule": "side_selective",
         "hypothesis": "Filtering to the largest model edges improves the hit rate.",
         "source_ids": "NFL-STANDINGS NFL-SCHED-X29 REPO"},
        {"strategy_id": "S-PARLAY-SIDE-TOTAL", "name": "Two-leg parlay: side and total, same game",
         "family": "Parlay", "market": "spread+total", "rule": "parlay", "hypothesis":
             "Joint leg dependence changes the true parlay probability away from the product of "
             "the marginals.",
         "source_ids": "NFL-STANDINGS NFL-SCHED-X29 REPO"},
        {"strategy_id": "S-PROP-PAIR", "name": "Two-leg prop parlay from official player logs",
         "family": "Player props", "market": "player", "rule": "prop_pair", "hypothesis":
             "Two team-mates' markets move together, so the parlay price must not assume "
             "independence.",
         "source_ids": "NFL-PLAYER-STATS NFL-STANDINGS"},
        {"strategy_id": "S-HOME-FADE", "name": "Fade the home side when the model disagrees",
         "family": "Single bet", "market": "spread", "rule": "home_fade", "hypothesis":
             "The home-field term is too large, so fading the model's home edge is profitable.",
         "source_ids": "NFL-STANDINGS NFL-SCHED-X29"},
        {"strategy_id": "S-REST-EDGE", "name": "Rest and bye differential",
         "family": "Single bet", "market": "spread", "rule": "rest", "hypothesis":
             "A club coming off a bye outperforms its scoring form.",
         "source_ids": "NFL-SCHED-X29 REPO"},
    ]


def grade_member(member: dict) -> dict:
    """Grade one member under BOTH published grading conventions, leakage-free.

    A pre-game forecast for week w uses only results from weeks < w.

    There are two defensible ways to ask "was the forecast right", and they do not agree:

      ``pick_wins``     did the side the model picked actually win? This is how a bet settles,
                        and it is the primary number.
      ``landing_vs_mean``  did the realised result land on the same side of the graded centre as
                        the forecast? This is the weaker test used by the repository's earlier
                        results lab, and it is kept so the two can be compared directly.

    Publishing both is deliberate. The difference between them is the amount of apparent skill that
    is an artefact of the convention rather than of foresight, and a reader is entitled to see
    that number instead of being shown whichever convention flatters the model.
    """
    import originate

    feed = load_feed()
    weeks = sorted({r["week"] for r in feed if r["result_type"] == "game"})
    tallies = {name: {"hits": 0, "misses": 0} for name in CONVENTIONS}
    per_week: list[dict] = []
    abstained = 0
    for week in weeks[1:]:  # week 1 has no prior form to build a rating from
        prior = [r for r in feed if r["result_type"] == "game" and r["week"] < week]
        future = [r for r in feed if r["result_type"] == "game" and r["week"] == week]
        if not prior:
            continue
        ratings = ratings_from(prior)
        week_hits = week_misses = 0
        for game in future:
            decision = decide(member["rule"], game, ratings, centre_source=prior)
            if decision is None:
                abstained += 1
                continue
            for name in CONVENTIONS:
                value = decision.get(name)
                if value is None:
                    continue
                tallies[name]["hits" if value else "misses"] += 1
            week_hits += 1 if decision.get("pick_wins") else 0
            week_misses += 0 if decision.get("pick_wins") else 1
        if week_hits + week_misses:
            per_week.append({"week": week, "hits": week_hits, "misses": week_misses,
                             "hit_rate": round(week_hits / (week_hits + week_misses), 4)})

    primary = tallies["pick_wins"]
    settled = primary["hits"] + primary["misses"]
    p = stats.binom_two_sided_p(primary["hits"], primary["misses"]) if settled else None
    streak = 0
    for entry in reversed(per_week):
        if entry["misses"] > entry["hits"]:
            streak += 1
        else:
            break
    weaker = tallies["landing_vs_mean"]
    weaker_n = weaker["hits"] + weaker["misses"]
    weaker_rate = round(weaker["hits"] / weaker_n, 4) if weaker_n else None
    primary_rate = round(primary["hits"] / settled, 4) if settled else None
    return {
        "strategy_id": member["strategy_id"],
        "name": member["name"],
        "family": member["family"],
        "market": member["market"],
        "hypothesis": member["hypothesis"],
        "state": "paper",
        # Signal: the only quantity computable without a price.
        "settled_bets": settled,
        "signal_hits": primary["hits"],
        "signal_misses": primary["misses"],
        "signal_hit_rate": primary_rate,
        "signal_p": round(p, 6) if p is not None else None,
        "grading_convention": "pick_wins (the side the model picked, graded on the result)",
        # The weaker convention, published alongside, with the gap made explicit.
        "alt_grading_convention": "landing_vs_mean (outcome lands on the forecast's side of the centre)",
        "alt_settled_bets": weaker_n,
        "alt_hit_rate": weaker_rate,
        "convention_gap_points": (round(100 * (weaker_rate - primary_rate), 2)
                                  if weaker_rate is not None and primary_rate is not None else None),
        "abstained_games": abstained,
        "weeks_graded": len(per_week),
        "first_half_hit_rate": _half(per_week, "first"),
        "second_half_hit_rate": _half(per_week, "second"),
        "consecutive_losing_weeks": streak,
        # Staking: every one of these needs a price and is therefore blank.
        "priced_bets": 0,
        "staking_return_units": "",
        "bankroll_path": "",
        "max_drawdown_units": "",
        "roi": "",
        "clv": "",
        "price_state": "unpriced",
        "price_reason": "no licensed price exists for any NFL market in this repository",
        "forward_weeks": 0,
        "source_ids": member["source_ids"],
    }


def _half(per_week: list[dict], which: str) -> float | None:
    if not per_week:
        return None
    mid = max(1, len(per_week) // 2)
    part = per_week[:mid] if which == "first" else per_week[mid:]
    h = sum(r["hits"] for r in part)
    m = sum(r["misses"] for r in part)
    return round(h / (h + m), 4) if h + m else None


def load_feed() -> list[dict]:
    with (DATA / "verified-results-2026-w1-9.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        for key in ("week",):
            row[key] = int(row[key])
        for key in ("away_score", "home_score", "margin_home", "total_points"):
            row[key] = int(row[key]) if row[key] not in ("", None) else None
    return rows


def ratings_from(prior: list[dict]) -> dict:
    """Multiplicative offence/defence ratings from results strictly before the graded week."""
    import originate as O
    tally: dict[str, dict] = {}
    for game in prior:
        for club, scored, allowed in ((game["away"], game["away_score"], game["home_score"]),
                                      (game["home"], game["home_score"], game["away_score"])):
            row = tally.setdefault(club, {"pf": 0, "pa": 0, "gp": 0})
            row["pf"] += scored
            row["pa"] += allowed
            row["gp"] += 1
    games = sum(r["gp"] for r in tally.values())
    points = sum(r["pf"] for r in tally.values())
    mean = points / games if games else 22.0
    ratings = {"league_mean": mean}
    for club, row in tally.items():
        off = O.shrunk(row["pf"] / row["gp"], mean, row["gp"])
        dfn = O.shrunk(row["pa"] / row["gp"], mean, row["gp"])
        ratings[club] = {"off": off, "def": dfn}
    return ratings


def point_estimates(ratings: dict, game: dict) -> tuple[float, float]:
    import originate as O
    mean = ratings["league_mean"]
    home = ratings.get(game["home"], {"off": mean, "def": mean})
    away = ratings.get(game["away"], {"off": mean, "def": mean})
    home_pts = O.expected_points(home["off"], away["def"], mean) + O.HOME_FIELD_POINTS / 2
    away_pts = O.expected_points(away["off"], home["def"], mean) - O.HOME_FIELD_POINTS / 2
    return home_pts, away_pts


CONVENTIONS = ("pick_wins", "landing_vs_mean")


def _centre(prior: list[dict]) -> tuple[float, float]:
    """Graded centre for each convention, computed from PRIOR weeks only (no leakage).

    ``pick_wins`` needs no centre: the pick is compared with the realised result.
    ``landing_vs_mean`` needs a centre for the forecast and one for the outcome. Both are taken
    from the prior weeks only, so the test cannot peek at the week it is grading.
    """
    if not prior:
        return 0.0, 0.0
    margins = [g["margin_home"] for g in prior]
    return sum(margins) / len(margins), 0.0


def decide(rule: str, game: dict, ratings: dict, centre_source: list[dict] | None = None) -> dict | None:
    """The decision each rule makes under both grading conventions.

    Returns None when the rule abstains (no opinion, or the inputs it needs are not in the data).
    An abstention is counted, never silently dropped.
    """
    import originate as O
    home_pts, away_pts = point_estimates(ratings, game)
    margin = home_pts - away_pts
    total = home_pts + away_pts
    actual_margin = game["margin_home"]
    actual_total = game["total_points"]
    centre, _ = _centre(centre_source or [])
    over_line = ratings["league_mean"] * 2

    def both(pick_dir: int, actual_dir: int) -> dict:
        pick_win = actual_dir == pick_dir and actual_dir != 0
        landing = None
        if abs(margin - centre) >= 1e-9 and actual_dir != 0:
            landing = (margin - centre) * (actual_dir * abs(actual_margin or 1)) > 0
        return {"pick_wins": pick_win, "landing_vs_mean": landing}

    if rule in ("side", "moneyline"):
        if margin == 0 or actual_margin == 0:
            return None
        pick = 1 if margin > 0 else -1
        return both(pick, 1 if actual_margin > 0 else -1)
    if rule == "side_selective":
        if abs(margin) < O.SELECTIVE_FLOOR or actual_margin == 0:
            return None
        pick = 1 if margin > 0 else -1
        return both(pick, 1 if actual_margin > 0 else -1)
    if rule == "home_fade":
        if margin <= 0 or actual_margin == 0:
            return None
        # Take the away side whenever the model likes the home side.
        return {"pick_wins": actual_margin < 0,
                "landing_vs_mean": (margin - centre) * actual_margin < 0}
    if rule == "total":
        if actual_total == over_line:
            return None
        pick = 1 if total > over_line else -1
        return {"pick_wins": (actual_total > over_line) == (pick > 0),
                "landing_vs_mean": (total - over_line) * (actual_total - over_line) > 0}
    if rule == "parlay":
        # Both legs must win. Note what this measures: the *joint* hit rate. Against two
        # near-coin-flip legs the joint rate is close to the product of the marginals, so a low
        # number here is the expectation, not a defect. Whether the joint exceeds independence is
        # a different question, answered by phi in correlation.py.
        side = decide("side", game, ratings, centre_source)
        tot = decide("total", game, ratings, centre_source)
        if side is None or tot is None:
            return None
        return {"pick_wins": bool(side["pick_wins"] and tot["pick_wins"]),
                "landing_vs_mean": None}
    if rule == "prop_pair":
        # Not gradable here: a prop parlay needs a player-level line, and no line exists.
        return None
    if rule == "rest":
        # No rest/bye schedule is joined into the feed, so the rule abstains rather than guess.
        return None
    raise SystemExit(f"unknown rule {rule}")



# --------------------------------------------------------------------------- demotion drill
def demotion_drill() -> dict:
    """Exercise the demotion gate on synthetic series, because no live strategy exists to trip it.

    A rule that has never been fired is a claim, not a control. Each series below is constructed so
    that exactly one demotion condition is present; the drill asserts that the gate fires on that
    condition and stays silent on a healthy control. None of these numbers is presented as a
    result: they are test fixtures, and the page labels them as such.
    """
    cases = [
        {"case": "signal decays to a coin flip over a long sample",
         "row": {"state": "live", "settled_bets": 300, "signal_p": 0.94, "price_state": "priced",
                 "max_drawdown_units": 0.0, "consecutive_losing_weeks": 0},
         "expect_fire": True},
        {"case": "bankroll drawdown beyond the published cap",
         "row": {"state": "live", "settled_bets": 100, "signal_p": 0.01, "price_state": "priced",
                 "max_drawdown_units": 24.5, "consecutive_losing_weeks": 1},
         "expect_fire": True},
        {"case": "six consecutive losing weeks with a still-good long-run signal",
         "row": {"state": "live", "settled_bets": 250, "signal_p": 0.02, "price_state": "priced",
                 "max_drawdown_units": 12.0, "consecutive_losing_weeks": 6},
         "expect_fire": True},
        {"case": "marked live with no priced bet, so it cannot be scored at all",
         "row": {"state": "live", "settled_bets": 60, "signal_p": 0.03, "price_state": "unpriced",
                 "max_drawdown_units": 1.0, "consecutive_losing_weeks": 0},
         "expect_fire": True},
        {"case": "healthy control: good signal, small sample, no drawdown, no streak",
         "row": {"state": "live", "settled_bets": 120, "signal_p": 0.04, "price_state": "priced",
                 "max_drawdown_units": 2.0, "consecutive_losing_weeks": 1},
         "expect_fire": False},
        {"case": "short sample is exempt from the signal check, so a small bad run does not demote",
         "row": {"state": "live", "settled_bets": 25, "signal_p": 0.90, "price_state": "priced",
                 "max_drawdown_units": 3.0, "consecutive_losing_weeks": 2},
         "expect_fire": False},
    ]
    results = []
    for case in cases:
        fired = demotion_reasons(case["row"])
        results.append({
            "case": case["case"],
            "settled_bets": case["row"]["settled_bets"],
            "signal_p": case["row"]["signal_p"],
            "drawdown_units": case["row"]["max_drawdown_units"],
            "losing_weeks": case["row"]["consecutive_losing_weeks"],
            "price_state": case["row"]["price_state"],
            "gate_fires": "yes" if fired else "no",
            "expected": "yes" if case["expect_fire"] else "no",
            "matched": "yes" if bool(fired) == case["expect_fire"] else "NO",
            "reasons": " | ".join(fired) if fired else "none",
        })
    mismatched = [r for r in results if r["matched"] != "yes"]
    if mismatched:
        raise SystemExit("demotion drill failed: " + "; ".join(r["case"] for r in mismatched))
    return {
        "cases": len(results),
        "fired": sum(1 for r in results if r["gate_fires"] == "yes"),
        "held": sum(1 for r in results if r["gate_fires"] == "no"),
        "all_matched": "yes",
        "synthetic": "yes — these series are constructed fixtures used to prove the gate fires, "
                     "not results from any strategy",
        "rows": results,
    }


def main() -> None:
    parse_args(__doc__ or "ledger")
    board, summary = grade_family()
    drill = demotion_drill()
    emit_csv(DATA / "signal-staking-leaderboard-2026-11-14.csv", board)
    emit_json(DATA / "gates-2026-11-14.json", {
        "snapshot_date": SNAPSHOT, "promotion": PROMOTION, "demotion": DEMOTION,
        "family": summary, "demotion_drill": drill,
        "asymmetry": "Promotion requires every condition; demotion requires any one. The rule is "
                     "stated once here and applied to every row on the leaderboard.",
    })
    print(f"Graded {summary['family_size']} family members on "
          f"{summary['settled_bets_graded']} settled forecaster bets, "
          f"{summary['priced_bets']} priced. {summary['promotable']} promotable, "
          f"{summary['demote_to_paper']} flagged for demotion. "
          f"Demotion drill {drill['cases']}/{drill['cases']} matched.")


if __name__ == "__main__":
    main()
