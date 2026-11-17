"""Walk-forward grading of the originated board, with no look-ahead.

A forecast for a game in week w is built only from games in weeks strictly less than w,
including the home allowance and the margin spread, so nothing about week w or later can
leak into it. Week 1 is not scored because no club has played.

Two things this module refuses to do:

  * It will not grade a forecast against itself. Betting the over on your own total is a
    coin flip by construction, so that test is published as a control, not as a result.
  * It will not produce a return. Every staking column is None, because a return needs
    an executable price and no consulted official source publishes one.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (DATA, benjamini_hochberg, binom_two_sided, brier, log_loss,  # noqa: E402
                    mean, round_value, wilson_interval)
from model import (RECENCY_DECAY, SHRINK_GAMES, american_from_probability,  # noqa: E402
                   league_mean, load_feed, measured_home_margin, originate,
                   pythagorean, team_rates)

OUT = DATA / "backtest.json"

EVAL_WEEKS = range(2, 11)
PERM_REPS = 5000
PERM_SEED = 20261114

NO_PRICE = ("No consulted official source publishes an executable price, so no return, "
            "stake, drawdown or closing-line value can be computed. The cell is blank "
            "by rule and is never filled with an estimate.")


# ------------------------------------------------------------------ forecasts

def recency_rates(games, decay=RECENCY_DECAY):
    """Exponentially weighted scoring rates; the most recent game carries weight 1."""
    ordered = sorted(games, key=lambda r: (int(r["week"]), r["date"]))
    table = {}
    for row in ordered:
        for club, scored, allowed in ((row["home"], int(row["home_score"]), int(row["away_score"])),
                                      (row["away"], int(row["away_score"]), int(row["home_score"]))):
            table.setdefault(club, {"w": 0.0, "pf": 0.0, "pa": 0.0, "gp": 0})
            entry = table[club]
            entry["w"] += 1.0
            entry["pf"] += scored
            entry["pa"] += allowed
            entry["gp"] += 1
            entry["weight"] = entry["w"]
            entry["w"] *= decay
    for entry in table.values():
        total = entry["weight"]
        entry["off"] = entry["pf"] / total if total else None
        entry["def"] = entry["pa"] / total if total else None
    return table


def forecasts(hfa_override=None):
    """If hfa_override is given it replaces the measured home allowance in stage 1.

    Used only by the sensitivity check, to show how much of the board's record is a
    consequence of the home allowance rather than of the team ratings.
    """
    feed = load_feed()
    rows = []
    for week in EVAL_WEEKS:
        prior = [r for r in feed if int(r["week"]) < week]
        targets = [r for r in feed if int(r["week"]) == week]
        if not prior or not targets:
            continue
        rates = team_rates(prior)
        recent = recency_rates(prior)
        league = league_mean(prior)
        stats = measured_home_margin(prior)
        hfa, sd = stats["mean"], stats["sd"]
        if hfa_override is not None:
            hfa = hfa_override
        tie_rate = sum(1 for r in prior if int(r["home_margin"]) == 0) / len(prior)
        for row in targets:
            home, away = row["home"], row["away"]
            if home not in rates or away not in rates or sd is None:
                continue
            base = originate(rates[home], rates[away], league, hfa, sd, tie_rate)
            shrunk = originate(rates[home], rates[away], league, hfa, sd, tie_rate,
                               shrink=SHRINK_GAMES)
            rec = recent.get(home), recent.get(away)
            recency = None
            if rec[0] and rec[1] and rec[0]["off"] is not None:
                recency = originate({"off": rec[0]["off"], "def": rec[0]["def"], "gp": rec[0]["gp"]},
                                    {"off": rec[1]["off"], "def": rec[1]["def"], "gp": rec[1]["gp"]},
                                    league, sd * 0.0 + hfa, sd, tie_rate)
            pyth_home = pythagorean(rates[home]["pf"], rates[home]["pa"])
            pyth_away = pythagorean(rates[away]["pf"], rates[away]["pa"])
            net_home = rates[home]["net"] - rates[away]["net"]
            defence = originate(rates[home], rates[away], league, hfa, sd, tie_rate,
                                defense_weight=2.0)
            rows.append({
                "game_id": row["game_id"], "week": week, "home": home, "away": away,
                "actual_margin": int(row["home_margin"]),
                "actual_total": int(row["total_points"]),
                "proj_margin": base["side"]["margin_home"],
                "proj_total": base["total"]["total"],
                "p_home": base["moneyline"]["p_home"],
                "shrunk_margin": shrunk["side"]["margin_home"],
                "shrunk_total": shrunk["total"]["total"],
                "recency_margin": recency["side"]["margin_home"] if recency else None,
                "recency_total": recency["total"]["total"] if recency else None,
                "defence_margin": defence["side"]["margin_home"],
                "pyth_margin": ((pyth_home - pyth_away) * 34.0
                                if pyth_home is not None and pyth_away is not None else None),
                "net_margin": net_home + hfa,
                "league_mean_total": 2 * league,
                "prior_games": len(prior),
                "prior_home_games": rates[home]["gp"],
                "prior_away_games": rates[away]["gp"],
                "home_win": 1 if int(row["home_margin"]) > 0 else
                            (0 if int(row["home_margin"]) < 0 else None),
                "source_url": row["source_url"],
                "game_url": row["source_url"],
            })
    return rows


# ------------------------------------------------------------------ strategies

def _directional(rows, margin_key, floor=0.0):
    """Pick the club the forecast favours. Grade against who actually won."""
    bets = []
    for row in rows:
        projected = row[margin_key]
        if projected is None or abs(projected) < floor:
            continue
        if row["home_win"] is None:
            continue
        pick_home = projected > 0
        bets.append(1 if pick_home == bool(row["home_win"]) else 0)
    return bets


def _conviction_parlays(rows, legs):
    """Cross-game parlay: the N highest-conviction sides of the same week."""
    by_week = {}
    for row in rows:
        by_week.setdefault(row["week"], []).append(row)
    slips = []
    for week in sorted(by_week):
        ranked = sorted(by_week[week], key=lambda r: -abs(r["proj_margin"]))
        chosen = ranked[:legs]
        if len(chosen) < legs or any(r["home_win"] is None for r in chosen):
            continue
        win = all((r["proj_margin"] > 0) == bool(r["home_win"]) for r in chosen)
        slips.append(1 if win else 0)
    return slips


def _same_game_pair(rows):
    """Two legs from one game: the favoured side wins, and the total beats the board."""
    slips, leg_a, leg_b = [], [], []
    for row in rows:
        if row["home_win"] is None:
            continue
        a = 1 if (row["proj_margin"] > 0) == bool(row["home_win"]) else 0
        over = row["actual_total"] - row["proj_total"]
        if abs(over) < 1e-9:
            continue
        b = 1 if over > 0 else 0
        leg_a.append(a)
        leg_b.append(b)
        slips.append(1 if a and b else 0)
    return slips, leg_a, leg_b


def _duplicate_legs(rows):
    """A two-leg slip built from the same event twice. Included as a control."""
    slips = []
    for row in rows:
        if row["home_win"] is None:
            continue
        a = 1 if (row["proj_margin"] > 0) == bool(row["home_win"]) else 0
        slips.append(1 if a and a else 0)
    return slips


def _skill_score(rows, forecast_key, actual_key, null_key):
    """1 - MSE(model)/MSE(null). Positive means the forecast beat the reference."""
    pairs = [(row[forecast_key], row[actual_key], row[null_key]) for row in rows
             if row[forecast_key] is not None]
    if not pairs:
        return None, None, None, 0
    mse = mean([(f - a) ** 2 for f, a, _ in pairs])
    null_mse = mean([(n - a) ** 2 for _, a, n in pairs])
    bias = mean([f - a for f, a, _ in pairs])
    mae = mean([abs(f - a) for f, a, _ in pairs])
    if not null_mse:
        return None, mae, bias, len(pairs)
    return 1 - mse / null_mse, mae, bias, len(pairs)


def _proper_scores(rows, key="p_home"):
    pairs = [(row[key], row["home_win"]) for row in rows if row["home_win"] is not None]
    if not pairs:
        return None, None, None, None, 0
    probs = [p for p, _ in pairs]
    outcomes = [o for _, o in pairs]
    null_brier = brier(outcomes, [0.5] * len(outcomes))
    null_logloss = log_loss(outcomes, [0.5] * len(outcomes))
    return (brier(outcomes, probs), log_loss(outcomes, probs),
            null_brier, null_logloss, len(pairs))


STRATEGIES = [
    {"id": "SB-01", "division": "Single bets", "market": "Side (directional)",
     "name": "Board side, every game",
     "rule": "Back the club the stage-1 margin favours, in every forecastable game.",
     "kind": "directional", "key": "proj_margin", "floor": 0.0},
    {"id": "SB-02", "division": "Single bets", "market": "Side (directional)",
     "name": "Board side, conviction at least 3 points",
     "rule": "As SB-01, but only where the stage-1 margin is at least 3 points from zero.",
     "kind": "directional", "key": "proj_margin", "floor": 3.0},
    {"id": "SB-03", "division": "Single bets", "market": "Side (directional)",
     "name": "Board side, conviction at least 6 points",
     "rule": "As SB-01, but only where the stage-1 margin is at least 6 points from zero.",
     "kind": "directional", "key": "proj_margin", "floor": 6.0},
    {"id": "SB-04", "division": "Single bets", "market": "Side (directional)",
     "name": "Pythagorean differential side",
     "rule": "Back the club with the higher Pythagorean expectation from prior points.",
     "kind": "directional", "key": "pyth_margin", "floor": 0.0},
    {"id": "SB-05", "division": "Single bets", "market": "Side (directional)",
     "name": "Net-points differential side",
     "rule": "Back the club with the better prior net points per game, plus the measured "
             "home allowance. Ignores the opponent's defence entirely.",
     "kind": "directional", "key": "net_margin", "floor": 0.0},
    {"id": "SB-06", "division": "Single bets", "market": "Side (directional)",
     "name": "Shrunk-rates side",
     "rule": "As SB-01, with each club's rates shrunk toward the league mean by "
             "games/(games+4).",
     "kind": "directional", "key": "shrunk_margin", "floor": 0.0},
    {"id": "SB-07", "division": "Single bets", "market": "Side (directional)",
     "name": "Defence-weighted side",
     "rule": "As SB-01, with the opponent's concession rate weighted double.",
     "kind": "directional", "key": "defence_margin", "floor": 0.0},
    {"id": "SB-08", "division": "Single bets", "market": "Side (directional)",
     "name": "Recency-weighted side",
     "rule": "As SB-01, with prior games weighted geometrically at 0.85 per game of age.",
     "kind": "directional", "key": "recency_margin", "floor": 0.0},
    {"id": "SB-09", "division": "Single bets", "market": "Total (control)",
     "name": "Over the board's own total",
     "rule": "Back the over on the stage-2 total in every game. Published as a control: "
             "a forecast graded against its own number is a coin flip by construction, "
             "so any deviation from 50% here is noise or bias, never edge.",
     "kind": "total_control", "key": "proj_total"},
    {"id": "SB-10", "division": "Single bets", "market": "Total (accuracy)",
     "name": "Total accuracy against the league mean",
     "rule": "Score the stage-2 total by squared error against the league-mean total, "
             "which is the reference a forecaster must beat.",
     "kind": "skill", "forecast_key": "proj_total", "actual_key": "actual_total",
     "null_key": "league_mean_total"},
    {"id": "SB-11", "division": "Single bets", "market": "Side (accuracy)",
     "name": "Margin accuracy against a zero margin",
     "rule": "Score the stage-1 margin by squared error against a forecast of zero, "
             "which is the reference a forecaster must beat.",
     "kind": "skill", "forecast_key": "proj_margin", "actual_key": "actual_margin",
     "null_key": "n/a"},
    {"id": "SB-12", "division": "Single bets", "market": "Moneyline",
     "name": "Moneyline probability, proper scores",
     "rule": "Score the stage-3 win probability with Brier and log loss against a flat "
             "50% reference, on every game that did not end tied.",
     "kind": "proper"},
    {"id": "PB-01", "division": "Parlays", "market": "Two-leg, same game",
     "name": "Favoured side plus over the board total",
     "rule": "Both legs must win: the favoured club wins, and the total beats the "
             "stage-2 total.",
     "kind": "same_game"},
    {"id": "PB-02", "division": "Parlays", "market": "Two-leg, same event",
     "name": "Favoured side plus the same side again",
     "rule": "Both legs are the same event, so the slip is not a parlay at all. "
             "Published as a control to show what a dependence of 1.0 costs.",
     "kind": "duplicate"},
    {"id": "PB-03", "division": "Parlays", "market": "Two-leg, cross-game",
     "name": "Two highest-conviction sides of the week",
     "rule": "In each week, back the two games with the largest stage-1 margin. Both "
             "must win.",
     "kind": "cross", "legs": 2},
    {"id": "PB-04", "division": "Parlays", "market": "Three-leg, cross-game",
     "name": "Three highest-conviction sides of the week",
     "rule": "In each week, back the three games with the largest stage-1 margin. All "
             "three must win.",
     "kind": "cross", "legs": 3},
    {"id": "PP-01", "division": "Player props / combos", "market": "Player props",
     "name": "Replacement-back usage combo",
     "rule": "Would test whether a named replacement's usage moves in a repeatable "
             "direction when a starter is ruled out.",
     "kind": "blocked",
     "blocked_because": "No per-game player log, target share or snap count was "
                        "retrieved from any official source. The NFL.com injury report "
                        "gives a status, not a usage number."},
    {"id": "PP-02", "division": "Player props / combos", "market": "Prop combo",
     "name": "Quarterback passing combo with the game total",
     "rule": "Would test the dependence between a passing prop and the game total.",
     "kind": "blocked",
     "blocked_because": "Same as PP-01. Publishing a dependence for a prop without the "
                        "underlying per-game numbers would be a fabrication."},
]


# ---------------------------------------------------------------- permutation

def permutation_null(rows, kind, spec, reps=PERM_REPS, seed=PERM_SEED):
    """Shuffle forecasts across games and rebuild the statistic.

    This is the null that matters: it keeps the forecasts and the results exactly as
    they are and destroys only the pairing, so a low p-value means the forecast was
    matched to the right game, not merely that its spread of values was unusual.
    """
    rng = random.Random(seed)

    def statistic(order):
        if kind == "directional":
            wins, n = 0, 0
            for row, source in zip(rows, order):
                projected = source[spec["key"]]
                if projected is None or abs(projected) < spec.get("floor", 0.0):
                    continue
                if row["home_win"] is None:
                    continue
                n += 1
                wins += 1 if (projected > 0) == bool(row["home_win"]) else 0
            return wins / n if n else None, n
        if kind == "skill":
            pairs = [(order[i][spec["forecast_key"]], row[spec["actual_key"]],
                      row[spec["null_key"]] if spec["null_key"] != "n/a" else 0.0)
                     for i, row in enumerate(rows)
                     if order[i][spec["forecast_key"]] is not None]
            if not pairs:
                return None, 0
            mse = mean([(f - a) ** 2 for f, a, _ in pairs])
            null_mse = mean([(nl - a) ** 2 for _, a, nl in pairs])
            return (1 - mse / null_mse if null_mse else None), len(pairs)
        if kind == "proper":
            pairs = [(order[i]["p_home"], row["home_win"]) for i, row in enumerate(rows)
                     if row["home_win"] is not None]
            if not pairs:
                return None, 0
            return brier([o for _, o in pairs], [p for p, _ in pairs]), len(pairs)
        if kind in ("same_game", "duplicate", "cross", "total_control"):
            return None, 0
        return None, 0

    identity = list(rows)
    observed, n = statistic(identity)
    if observed is None or n < 8:
        return {"observed": observed, "n": n, "reps": 0, "p_value": None,
                "null_median": None, "null_p95": None}
    hits = 0
    draws = []
    for _ in range(reps):
        shuffled = identity[:]
        rng.shuffle(shuffled)
        value, _ = statistic(shuffled)
        if value is None:
            continue
        draws.append(value)
        # Two-sided against the reference point of the statistic: 0.5 for a rate,
        # 0 for a skill score, and the flat-50% Brier for a proper score.
        reference = 0.5 if kind in ("directional", "total_control") else (
            brier([r["home_win"] for r in rows if r["home_win"] is not None],
                  [0.5] * sum(1 for r in rows if r["home_win"] is not None))
            if kind == "proper" else 0.0)
        if abs(value - reference) >= abs(observed - reference) - 1e-12:
            hits += 1
    draws.sort()
    return {
        "observed": observed, "n": n, "reps": len(draws),
        "p_value": (hits + 1) / (len(draws) + 1) if draws else None,
        "null_median": draws[len(draws) // 2] if draws else None,
        "null_p95": draws[int(0.95 * len(draws)) - 1] if len(draws) >= 20 else None,
    }


# ------------------------------------------------------------------- grading

def grade(strategy, rows):
    """Return the signal half of a strategy's record. The staking half is always None."""
    base = {
        "id": strategy["id"], "name": strategy["name"], "division": strategy["division"],
        "market": strategy["market"], "rule": strategy["rule"],
        "kind": strategy["kind"],
        "signal": {}, "staking": {
            "stake_units": None, "roi": None, "profit_units": None,
            "max_drawdown_units": None, "closing_line_value": None,
            "blank_because": NO_PRICE},
    }
    kind = strategy["kind"]
    if kind == "blocked":
        base["signal"] = {"n": None, "wins": None, "losses": None, "hit_rate": None,
                          "null_rate": None, "p_value": None, "q_value": None,
                          "ci_low": None, "ci_high": None, "statistic": None,
                          "blocked_because": strategy["blocked_because"]}
        base["status"] = "Blocked"
        return base

    if kind == "directional":
        bets = _directional(rows, strategy["key"], strategy.get("floor", 0.0))
        n = len(bets)
        wins = sum(bets)
        hit = wins / n if n else None
        low, high = wilson_interval(wins, n) if n else (None, None)
        perm = permutation_null(rows, kind, strategy)
        half = n // 2
        first = mean(bets[:half]) if half else None
        second = mean(bets[half:]) if n - half else None
        base["signal"] = {
            "n": n, "wins": wins, "losses": n - wins, "hit_rate": hit,
            "null_rate": 0.5, "p_value": perm["p_value"],
            "binomial_p": binom_two_sided(wins, n) if n else None,
            "ci_low": low, "ci_high": high, "statistic": "hit rate vs a 50% reference",
            "first_half_hit_rate": first, "second_half_hit_rate": second,
            "stable_across_halves": (first is not None and second is not None
                                     and first > 0.5 and second > 0.5),
            "permutation": perm,
        }
        base["status"] = "Graded"
        return base

    if kind == "total_control":
        slips = []
        for row in rows:
            diff = row["actual_total"] - row[strategy["key"]]
            if abs(diff) < 1e-9:
                continue
            slips.append(1 if diff > 0 else 0)
        n = len(slips)
        wins = sum(slips)
        low, high = wilson_interval(wins, n) if n else (None, None)
        base["signal"] = {
            "n": n, "wins": wins, "losses": n - wins, "hit_rate": wins / n if n else None,
            "null_rate": 0.5, "p_value": binom_two_sided(wins, n) if n else None,
            "ci_low": low, "ci_high": high,
            "statistic": "hit rate vs a 50% reference (control: grading a forecast "
                         "against its own number)",
            "permutation": None,
        }
        base["status"] = "Control"
        return base

    if kind == "skill":
        null_key = strategy["null_key"]
        pairs_rows = []
        for row in rows:
            enriched = dict(row)
            if null_key == "n/a":
                enriched[null_key] = 0.0
            pairs_rows.append(enriched)
        skill, mae, bias, n = _skill_score(pairs_rows, strategy["forecast_key"],
                                           strategy["actual_key"], null_key)
        perm = permutation_null(rows, kind, strategy)
        base["signal"] = {
            "n": n, "wins": None, "losses": None, "hit_rate": None, "null_rate": 0.0,
            "p_value": perm["p_value"], "ci_low": None, "ci_high": None,
            "statistic": "skill score = 1 - MSE(model)/MSE(reference); positive is better "
                         "than the reference",
            "skill_score": skill, "mae": mae, "bias": bias, "permutation": perm,
        }
        base["status"] = "Graded"
        return base

    if kind == "proper":
        br, ll, null_br, null_ll, n = _proper_scores(rows)
        perm = permutation_null(rows, kind, strategy)
        base["signal"] = {
            "n": n, "wins": None, "losses": None, "hit_rate": None,
            "null_rate": null_br, "p_value": perm["p_value"], "ci_low": None,
            "ci_high": None,
            "statistic": "Brier score; lower is better. Reference is a flat 50% forecast.",
            "brier": br, "log_loss": ll, "null_brier": null_br, "null_log_loss": null_ll,
            "permutation": perm,
        }
        base["status"] = "Graded"
        return base

    if kind == "same_game":
        slips, leg_a, leg_b = _same_game_pair(rows)
        n = len(slips)
        wins = sum(slips)
        pa = mean(leg_a) if leg_a else None
        pb = mean(leg_b) if leg_b else None
        expected = (pa * pb) if (pa is not None and pb is not None) else None
        observed = wins / n if n else None
        low, high = wilson_interval(wins, n) if n else (None, None)
        base["signal"] = {
            "n": n, "wins": wins, "losses": n - wins, "hit_rate": observed,
            "null_rate": expected,
            "p_value": binom_two_sided(wins, n, expected) if (n and expected) else None,
            "ci_low": low, "ci_high": high,
            "statistic": "joint hit rate vs the rate implied if the two legs were "
                         "independent",
            "leg_1_rate": pa, "leg_2_rate": pb,
            "dependence_note": "The null here is the product of the two observed leg "
                               "rates, not 25%. Legs that move together make the joint "
                               "rate differ from the product.",
        }
        base["status"] = "Graded"
        return base

    if kind == "duplicate":
        slips = _duplicate_legs(rows)
        n = len(slips)
        wins = sum(slips)
        single = _directional(rows, "proj_margin", 0.0)
        single_rate = mean(single) if single else None
        expected = single_rate ** 2 if single_rate is not None else None
        low, high = wilson_interval(wins, n) if n else (None, None)
        base["signal"] = {
            "n": n, "wins": wins, "losses": n - wins,
            "hit_rate": wins / n if n else None, "null_rate": expected,
            "p_value": binom_two_sided(wins, n, expected) if (n and expected) else None,
            "ci_low": low, "ci_high": high,
            "statistic": "joint hit rate vs the independence-implied rate",
            "leg_1_rate": single_rate, "leg_2_rate": single_rate,
            "dependence_note": "Both legs are the same event, so the hit rate equals the "
                               "single-leg rate rather than its square. A slip like this "
                               "is one bet wearing two legs, and pricing it as a parlay "
                               "would be wrong.",
        }
        base["status"] = "Control"
        return base

    if kind == "cross":
        slips = _conviction_parlays(rows, strategy["legs"])
        n = len(slips)
        wins = sum(slips)
        single = _directional(rows, "proj_margin", 0.0)
        single_rate = mean(single) if single else None
        expected = single_rate ** strategy["legs"] if single_rate is not None else None
        low, high = wilson_interval(wins, n) if n else (None, None)
        base["signal"] = {
            "n": n, "wins": wins, "losses": n - wins,
            "hit_rate": wins / n if n else None, "null_rate": expected,
            "p_value": binom_two_sided(wins, n, expected) if (n and expected) else None,
            "ci_low": low, "ci_high": high,
            "statistic": "joint hit rate vs the rate implied if the legs were independent",
            "leg_rate": single_rate, "legs": strategy["legs"],
            "dependence_note": "Cross-game legs share a week, so a common shock can move "
                               "them together. The independence-implied rate is a "
                               "reference, not a claim that the legs are independent.",
        }
        base["status"] = "Graded"
        return base

    raise SystemExit(f"unknown strategy kind: {kind}")


def sensitivity(rows_for_grading):
    """How much of the board's directional record comes from the home allowance?

    The older board on nfl-lines.html assumes two points of home advantage and reports
    a 64.2% directional record over 120 games. This desk measures the allowance from
    prior games and reports a lower figure. The two are not contradictory findings about
    the same model, so the sensitivity is published rather than left as a discrepancy a
    reader has to reconcile.
    """
    out = []
    for label, override in (("measured from prior games (this desk)", None),
                            ("fixed at 0.0 points", 0.0),
                            ("fixed at 2.0 points (the older board's assumption)", 2.0)):
        rows = forecasts(hfa_override=override)
        bets = _directional(rows, "proj_margin", 0.0)
        n = len(bets)
        wins = sum(bets)
        out.append({
            "home_allowance": label,
            "n": n, "wins": wins,
            "hit_rate": wins / n if n else None,
            "binomial_p": binom_two_sided(wins, n) if n else None,
        })
    home_only = [r for r in rows_for_grading if r["home_win"] is not None]
    out.append({
        "home_allowance": "reference: back the home club in every game, no model",
        "n": len(home_only), "wins": sum(r["home_win"] for r in home_only),
        "hit_rate": mean([r["home_win"] for r in home_only]) if home_only else None,
        "binomial_p": binom_two_sided(sum(r["home_win"] for r in home_only),
                                      len(home_only)) if home_only else None,
    })
    return out


def build():
    rows = forecasts()
    graded = [grade(strategy, rows) for strategy in STRATEGIES]
    pvals = [entry["signal"].get("p_value") for entry in graded]
    adjusted, rejected = benjamini_hochberg(pvals, level=0.10)
    for entry, q, reject in zip(graded, adjusted, rejected):
        entry["signal"]["q_value"] = q
        entry["signal"]["reject_null_at_fdr_10pct"] = reject

    margins = [row["proj_margin"] - row["actual_margin"] for row in rows]
    totals = [row["proj_total"] - row["actual_total"] for row in rows]
    payload = {
        "requirement": "walk-forward grading of the originated board",
        "built_on": "2026-11-14",
        "weeks_scored": sorted({row["week"] for row in rows}),
        "forecast_rows": len(rows),
        "games_excluded": "week 1 is never scored; a club with no prior game is skipped",
        "leakage_control": "A forecast for week w uses only weeks strictly less than w, "
                           "including the home allowance, the margin spread and the "
                           "league mean.",
        "permutation": {"reps": PERM_REPS, "seed": PERM_SEED,
                        "null": "forecasts are shuffled across games; only the pairing "
                                "is destroyed"},
        "multiplicity": {"method": "Benjamini-Hochberg across all graded strategies",
                         "level": 0.10,
                         "tested": sum(1 for p in pvals if p is not None)},
        "forecast_quality": {
            "n": len(rows),
            "margin_mae": mean([abs(x) for x in margins]) if margins else None,
            "margin_bias": mean(margins) if margins else None,
            "margin_rmse": math.sqrt(mean([x * x for x in margins])) if margins else None,
            "total_mae": mean([abs(x) for x in totals]) if totals else None,
            "total_bias": mean(totals) if totals else None,
            "total_rmse": math.sqrt(mean([x * x for x in totals])) if totals else None,
            "total_residual_sd": (math.sqrt(sum((x - mean(totals)) ** 2 for x in totals)
                                            / (len(totals) - 1)) if len(totals) > 1 else None),
        },
        "sensitivity": sensitivity(rows),
        "strategies": graded,
        "staking_columns": {
            "stake_units": NO_PRICE, "roi": NO_PRICE, "profit_units": NO_PRICE,
            "max_drawdown_units": NO_PRICE, "closing_line_value": NO_PRICE,
        },
    }
    return round_value(payload, 6)


def main():
    payload = build()
    from common import check_artifact
    if check_artifact(OUT, payload):
        scored = [s for s in payload["strategies"] if s["signal"].get("n")]
        print(f"  {payload['forecast_rows']} forecasts; {len(scored)} strategies graded; "
              f"{sum(1 for s in scored if s['signal'].get('reject_null_at_fdr_10pct'))} "
              f"reject the null at FDR 10%")


if __name__ == "__main__":
    main()
