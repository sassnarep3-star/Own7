#!/usr/bin/env python3
"""Calibration, luck decomposition and closing-line value.

Three questions this module answers, in this order:

1. Is the model any good?            -> compare its error to the market's error.
2. Is the hit rate skill or luck?    -> compare observed hits to the hits the model's
                                        own probabilities predicted, and to a coin.
3. Did we beat the close?            -> open-to-close movement, in the direction we took.

The answers are allowed to be bad news. On the Week 9 capture they are bad news, and
the desk reports that rather than the flattering hit rate.
"""
from __future__ import annotations

import math

import staking


def rmse(pred, actual) -> float:
    n = len(pred)
    return math.sqrt(sum((p - a) ** 2 for p, a in zip(pred, actual)) / n) if n else None


def mae(pred, actual) -> float:
    n = len(pred)
    return sum(abs(p - a) for p, a in zip(pred, actual)) / n if n else None


def calibration(rows_side: list[dict], rows_total: list[dict]) -> dict:
    """Model error versus market error, home-perspective.

    A market spread of `market_line` from the home column means the home side is favoured
    by `market_line`, so the market's expected home margin is `-market_line`. Both the
    model and the market are scored on the same 15 games against the same official margin.
    """
    actual_m = [r["actual_margin"] for r in rows_side]
    model_m = [r["model_fair_line"] for r in rows_side]
    market_m = [-r["market_line"] for r in rows_side]

    actual_t = [r["actual_total"] for r in rows_total]
    model_t = [r["model_fair_total"] for r in rows_total]
    market_t = [r["market_total"] for r in rows_total]

    model_sd = _sd(model_m)
    market_sd = _sd(market_m)
    edges = [abs(r["edge_points"]) for r in rows_side if r["edge_points"] is not None]

    verdict = "model_error_exceeds_market"
    if rmse(model_m, actual_m) < rmse(market_m, actual_m):
        verdict = "model_error_below_market"

    return {
        "n_games": len(rows_side),
        "side": {
            "model_rmse": round(rmse(model_m, actual_m), 3),
            "market_rmse": round(rmse(market_m, actual_m), 3),
            "model_mae": round(mae(model_m, actual_m), 3),
            "market_mae": round(mae(market_m, actual_m), 3),
            "model_sd": round(model_sd, 3),
            "market_sd": round(market_sd, 3),
        },
        "total": {
            "model_rmse": round(rmse(model_t, actual_t), 3),
            "market_rmse": round(rmse(market_t, actual_t), 3),
            "model_mae": round(mae(model_t, actual_t), 3),
            "market_mae": round(mae(market_t, actual_t), 3),
        },
        "mean_abs_side_edge": round(sum(edges) / len(edges), 3) if edges else None,
        "verdict": verdict,
        "reading": (
            "The model is less accurate than the market on both markets. That does not make a "
            "hit rate impossible, but it means any positive result on this capture is not "
            "evidence of skill. It is evidence that 15 games is noise."
            if verdict == "model_error_exceeds_market" else
            "The model error is below the market error on the margin. That is necessary but not "
            "sufficient: with 15 games the difference is well inside sampling error."
        ),
    }


def _sd(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def luck_decomposition(side_graded: dict, board_side: list[dict]) -> dict:
    """Observed hits versus the hits the model itself expected, and versus a coin.

    If the model's own probabilities predict far fewer wins than were observed, the
    excess is luck. This is the exact mechanism by which a poor model produces a
    flattering record, so the desk publishes the three numbers side by side.
    """
    bets = [d for d in side_graded["decisions"] if d["decision"] == "bet"]
    by_event = {r["event_id"]: r for r in board_side}
    expected = 0.0
    counted = 0
    for b in bets:
        r = by_event[b["event_id"]]
        p = r.get("model_home_cover_prob")
        if p is None:
            continue
        # p is the probability the HOME side covers. Which side did we back?
        picked_home = b["pick"] == r["home"]
        expected += p if picked_home else (1.0 - p)
        counted += 1
    observed = side_graded["wins"]
    losses = side_graded["losses"]
    n = observed + losses
    return {
        "n_settled": n,
        "observed_wins": observed,
        "model_expected_wins": round(expected, 2),
        "coin_expected_wins": round(n * 0.5, 2),
        "excess_over_model_expectation": round(observed - expected, 2),
        "excess_over_coin": round(observed - n * 0.5, 2),
        "p_vs_model_expectation": _binom_p(observed, n, expected / n if n else 0.5),
        "p_vs_coin": staking.exact_binomial_two_sided(observed, losses),
        "reading": (
            "The number to watch is excess_over_model_expectation, not the hit rate. Wins far "
            "ABOVE the model's own expectation mean variance flattered it; wins far BELOW mean the "
            "model's own probabilities were overconfident and the record was worse than the model "
            "predicted. Either way the hit rate alone misleads, in opposite directions."
        ),
    }


def _binom_p(k: int, n: int, p: float) -> float | None:
    """Two-sided exact p against a non-0.5 baseline, by the same no-more-likely rule."""
    if n == 0 or p in (0.0, 1.0):
        return None
    obs = math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))
    tol = obs * (1 + 1e-9)
    total = 0.0
    for j in range(n + 1):
        pj = math.comb(n, j) * (p ** j) * ((1 - p) ** (n - j))
        if pj <= tol:
            total += pj
    return round(min(1.0, total), 6)


def selection_test(rows: list[dict], graded: dict, market: str) -> dict:
    """Does the model disagree with the market in a consistent direction?

    A model that is merely noisy picks each side about half the time, and its record is
    uninformative. A model that is systematically one-sided is making a directional claim, and
    that claim can be tested on its own: how often did it like the home side, and was it right
    to? This separates "no signal" from "a signal with the wrong sign", which are very different
    findings and look identical if you only report a hit rate.
    """
    by_event = {r["event_id"]: r for r in rows}
    # For the side board the two directions are home and away; for the total board they are over
    # and under. Either way the question is the same: is the model one-sided?
    if market == "side":
        first, second = "home", "away"
    else:
        first, second = "OVER", "UNDER"
    picked_first = 0
    bets = 0
    for d in graded["decisions"]:
        if d["decision"] != "bet":
            continue
        bets += 1
        if d["pick"] == first or (market == "side" and d["pick"] == by_event[d["event_id"]]["home"]):
            picked_first += 1
    from math import comb
    if bets == 0:
        return {"n_bets": 0}
    obs = comb(bets, picked_first) * 0.5 ** bets
    tol = obs * (1 + 1e-9)
    p = min(1.0, sum(comb(bets, k) * 0.5 ** bets for k in range(bets + 1)
                     if comb(bets, k) * 0.5 ** bets <= tol))
    return {
        "market": market,
        "n_bets": bets,
        "picked_home" if market == "side" else "picked_over": picked_first,
        "picked_away" if market == "side" else "picked_under": bets - picked_first,
        "share_home" if market == "side" else "share_over": round(picked_first / bets, 4),
        "p_versus_balanced": round(p, 6),
        "reading": (
            "If the share of home picks is far from half, the model is making a directional claim "
            "rather than adding noise. Combined with the hit rate, that distinguishes an "
            "uninformative model from one whose signal is inverted."
            if abs(picked_first / bets - 0.5) < 0.25 else
            "The model is strongly one-sided. That is a directional claim, and the hit rate then "
            "measures whether the direction was right, not whether the model was lucky."
        ),
    }


def closing_line_value(rows: list[dict], graded: dict, market: str = "side") -> dict:
    """CLV: the line we could have taken at the open versus the close, in points.

    The desk stakes at the open (see staking.grade_flat_stake), so CLV is measurable. It
    is measured in *points*, not basis points, because on this capture several lines moved
    more than ten points: a probability-only measure would report a few basis points for a
    move that is worth a dozen points of handicap, which is the opposite of informative.

    For the side board the column is the move that favoured our pick:
        pick at home and the market line rose (home laid more) -> we got the better number
    For the total board it is the move against over bettors, signed for our pick.
    """
    by_event = {r["event_id"]: r for r in rows}
    detail = []
    for d in graded["decisions"]:
        if d["decision"] != "bet":
            continue
        r = by_event[d["event_id"]]
        if market == "side":
            o, c = r.get("market_line_open"), r.get("market_line")
            if o is None or c is None:
                detail.append({"event_id": d["event_id"], "game": d["game"],
                               "pick": d["pick"], "clv_points": None,
                               "why": "open or close line missing"})
                continue
            # Picked side's own spread at open and close.
            o_pick = o if d["pick"] == r["home"] else -o
            c_pick = c if d["pick"] == r["home"] else -c
        else:
            o, c = r.get("market_total_open"), r.get("market_total")
            if o is None or c is None:
                detail.append({"event_id": d["event_id"], "game": d["game"],
                               "pick": d["pick"], "clv_points": None,
                               "why": "open or close line missing"})
                continue
            o_pick, c_pick = o, c
        clv = round(o_pick - c_pick, 2)
        detail.append({
            "event_id": d["event_id"], "game": d["game"], "pick": d["pick"],
            "open_line": o_pick, "close_line": c_pick,
            "clv_points": clv,
            "beat_close": clv > 0,
        })
    vals = [x["clv_points"] for x in detail if x["clv_points"] is not None]
    return {
        "detail": detail,
        "n": len(vals),
        "mean_points": round(sum(vals) / len(vals), 2) if vals else None,
        "median_points": round(sorted(vals)[len(vals) // 2], 2) if vals else None,
        "share_beat_close": round(sum(1 for v in vals if v > 0) / len(vals), 3) if vals else None,
        "basis": "picked side's own line at open minus the same side's line at close, in points",
        "reading": (
            "A strategy with a real edge beats the close on most bets. Positive CLV in points "
            "means we consistently took the better number. A record that wins while losing at "
            "the close is winning on variance."
        ),
    }
