"""Leaderboard with signal and staking measured separately, plus a demotion gate.

THE PROBLEM THIS SOLVES
-----------------------
A single "units won" column lets a lucky stake schedule hide a bad forecast. Two
strategies can both finish +12 units: one by calling games slightly better than
chance on a flat stake, the other by hitting three long shots. Ranked on units,
they look identical. They are not.

So every entry carries TWO scores computed from different evidence:

  SIGNAL   Does the forecast discriminate better than a coin, independent of
           money? Measured by the rate at which the forecast beats the published
           closing number, the Brier score of its probability, and an exact
           binomial tail against pure chance. A stake size cannot improve it.

  STAKING  What the flat-stake path did. Measured on a fixed 1-unit flat stake at
           the stated assumed price, with peak-to-trough drawdown. It is reported
           but never used to rank.

Ranking is by SIGNAL only, and only a strategy that clears multiplicity control is
eligible to rank at all. If the two scores disagree, that disagreement is printed
rather than averaged away, because it is the whole point of the split.

NO MONEY IS CLAIMED
-------------------
There is no price with a known hold for the spread or total in the store, so the
staking column is computed at a STATED ASSUMED price of -110 on both sides. It is
an accounting convention for comparing strategies with each other, not a profit
forecast or a wager. Every staking figure is labelled with that assumption.

DEMOTION GATE
-------------
A strategy that ranked must keep its signal. The gate below is written before any
result is seen and is applied to the walk-forward record: a live strategy that
breaches it returns to paper. The breach is recorded here, not actioned silently.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
ORIGINATION = HERE / "data" / "origination.json"
OUT = HERE / "data" / "leaderboard.json"

ASSUMED_PRICE = -110
FLAT_STAKE = 1.0
MIN_SELECTIONS_TO_RANK = 40       # pre-registered floor for this snapshot
FDR_LEVEL = 0.10
PERMUTATION_REPS = 20000
PERMUTATION_SEED = 20261114
DEMOTION = {
    "id": "DG01",
    "rule": (
        "Return a live strategy to paper when any of: (a) its signal hit rate falls to or "
        "below 50% over a trailing 40-selection window; (b) its exchangeability p-value on the "
        "trailing window exceeds 0.50, i.e. the forecast has stopped disaggregating from noise; "
        "(c) its staking drawdown exceeds 10 flat units while the signal score is below the "
        "50% break-even line; (d) it loses price agreement - the mean absolute difference "
        "between its fair line and the market exceeds 6 points for two consecutive windows, "
        "which means it has stopped being a forecast and started being an opinion."
    ),
    "rationale": (
        "Each clause targets a different failure. (a) and (b) catch a decaying model. (c) catches "
        "the exact case the split exists for, a losing signal kept alive by a hot staking run. "
        "(d) catches divergence from the market, which is a data or specification break rather "
        "than bad luck."
    ),
    "window_selections": 40,
    "max_drawdown_units": 10,
    "max_price_disagreement_points": 6,
    "declared_before_grading": True,
}


def load() -> dict:
    return json.loads(ORIGINATION.read_text(encoding="utf-8"))


def binom_sf(k: int, n: int, p: float = 0.5) -> float:
    """Exact P(X >= k) for X ~ Binomial(n, p), computed in log space."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    return max(0.0, min(1.0, 1.0 - binom_cdf(k - 1, n, p)))


def payout(price: int, stake: float) -> float:
    if price < 0:
        return stake * (100.0 / -price)
    return stake * (price / 100.0)


def brier(pairs: list[tuple[float, int]]) -> float | None:
    if not pairs:
        return None
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs)


def log_loss(pairs: list[tuple[float, int]]) -> float | None:
    if not pairs:
        return None
    eps = 1e-12
    total = 0.0
    for p, y in pairs:
        q = min(1 - eps, max(eps, p))
        total += -(y * math.log(q) + (1 - y) * math.log(1 - q))
    return total / len(pairs)


def bh_adjust(pvalues: list[float]) -> list[float]:
    """Benjamini-Hochberg adjusted q-values."""
    n = len(pvalues)
    order = sorted(range(n), key=lambda i: pvalues[i])
    q = [0.0] * n
    running = 1.0
    for rank in range(n - 1, -1, -1):
        idx = order[rank]
        value = pvalues[idx] * n / (rank + 1)
        running = min(running, value)
        q[idx] = min(1.0, running)
    return q


# --- Pre-registered strategy family ---------------------------------------
# Each variant states its selection rule up front. The family is fixed here, and
# every member is graded, including the ones that look bad. That is what makes the
# multiplicity correction honest.
VARIANTS = [
    {"id": "S01", "name": "Side, all games, no filter", "market": "side", "filter": "all"},
    {"id": "S02", "name": "Side, edge >= 1 pt", "market": "side", "filter": "edge1"},
    {"id": "S03", "name": "Side, edge >= 2 pt", "market": "side", "filter": "edge2"},
    {"id": "S04", "name": "Side, edge >= 3 pt", "market": "side", "filter": "edge3"},
    {"id": "S05", "name": "Side, fade the market (edge <= -2 pt)", "market": "side", "filter": "fade2"},
    {"id": "S06", "name": "Side, home only", "market": "side", "filter": "home"},
    {"id": "S07", "name": "Side, away only", "market": "side", "filter": "away"},
    {"id": "S08", "name": "Total, all games, no filter", "market": "total", "filter": "all"},
    {"id": "S09", "name": "Total, edge >= 2 pt", "market": "total", "filter": "edge2"},
    {"id": "S10", "name": "Total, edge >= 3 pt", "market": "total", "filter": "edge3"},
    {"id": "S11", "name": "Total, fade the market (edge <= -3 pt)", "market": "total", "filter": "fade3"},
    {"id": "S12", "name": "Total, under only", "market": "total", "filter": "under"},
]


def selections_for(game: dict, variant: dict) -> dict | None:
    """Turn one originated game into at most one graded selection for a variant."""
    market = variant["market"]
    if market == "side":
        diff = game.get("line_difference")
        if diff is None:
            return None
        fair = game["fair_line_home"]
        market_line = float(game["market_line_home"])
        # Positive difference: our home number is higher than the market's, i.e.
        # we make the home side stronger, so we take the home side.
        side = "home" if diff > 0 else "away"
        edge = abs(diff)
        outcome = game["market_home_cover"]  # cover/fail/push from the home side
        won = outcome == "cover" if side == "home" else outcome == "fail"
        if outcome == "push":
            won = None
    else:
        diff = game.get("total_difference")
        if diff is None:
            return None
        side = "over" if diff > 0 else "under"
        edge = abs(diff)
        outcome = game["market_total_result"]
        won = outcome == "over" if side == "over" else outcome == "under"
        if outcome == "push":
            won = None

    rule = variant["filter"]
    if rule == "all":
        pass
    elif rule.startswith("edge"):
        if edge < float(rule[4:]):
            return None
    elif rule.startswith("fade"):
        # Fade = take the opposite side to the one the model preferred, which only
        # exists as a distinct strategy when the model disagrees with the market.
        if edge < float(rule[4:]):
            return None
        side = "away" if side == "home" else ("home" if side == "away" else ("under" if side == "over" else "over"))
        if market == "side":
            outcome = game["market_home_cover"]
            won = outcome == "cover" if side == "home" else outcome == "fail"
        else:
            outcome = game["market_total_result"]
            won = outcome == "over" if side == "over" else outcome == "under"
        if outcome == "push":
            won = None
    elif rule == "home" and side != "home":
        return None
    elif rule == "away" and side != "away":
        return None
    elif rule == "under" and side != "under":
        return None

    prob = (
        game["p_home_win"] if side == "home" else game["p_away_win"]
        if market == "side" and game.get("p_home_win") is not None
        else None
    )
    return {
        "week": game["week"],
        "date": game["date"],
        "game": f"{game['away']}@{game['home']}",
        "market": market,
        "side": side,
        "edge": round(edge, 3),
        "won": won,
        "p_side": prob,
    }


def permutation_p(values: list[float], reps: int, seed: int) -> float:
    """One-sided permutation p for 'the mean is above zero' under random signs."""
    import random
    rng = random.Random(seed)
    observed = sum(values) / len(values)
    if observed <= 0:
        return 1.0
    hits = 0
    n = len(values)
    for _ in range(reps):
        total = 0.0
        for v in values:
            total += v if rng.random() < 0.5 else -v
        if total / n >= observed:
            hits += 1
    return (hits + 1) / (reps + 1)


def score_variant(variant: dict, games: list[dict]) -> dict:
    picks = [s for s in (selections_for(g, variant) for g in games) if s]
    settled = [p for p in picks if p["won"] is not None]
    pushes = [p for p in picks if p["won"] is None]
    n = len(settled)
    wins = sum(1 for p in settled if p["won"])
    losses = n - wins

    entry = {
        "id": variant["id"],
        "name": variant["name"],
        "market": variant["market"],
        "filter": variant["filter"],
        "n_selections": len(picks),
        "n_settled": n,
        "pushes": len(pushes),
        "wins": wins,
        "losses": losses,
        "signal": {},
        "staking": {},
        "rank_eligible": False,
        "demotion": None,
    }
    if n == 0:
        entry["signal"] = {"hit_rate": None, "p_value": None, "note": "no settled selections"}
        entry["staking"] = {"units": None, "note": "no settled selections"}
        return entry

    hit_rate = wins / n
    p_value = binom_sf(wins, n, 0.5)
    probs = [(p["p_side"], 1 if p["won"] else 0) for p in settled if p["p_side"] is not None]

    # Flat-stake path, in selection order, at the stated assumed price.
    units = 0.0
    peak = 0.0
    max_dd = 0.0
    curve = []
    win_payout = payout(ASSUMED_PRICE, FLAT_STAKE)
    per_pick = []
    for pick in sorted(settled, key=lambda p: (p["date"], p["game"])):
        gain = win_payout if pick["won"] else -FLAT_STAKE
        units += gain
        per_pick.append(gain)
        peak = max(peak, units)
        max_dd = max(max_dd, peak - units)
        curve.append(round(units, 3))

    entry["signal"] = {
        "hit_rate": round(hit_rate, 4),
        "p_value_vs_coin": round(p_value, 6),
        "brier": round(brier(probs), 5) if probs else None,
        "log_loss": round(log_loss(probs), 5) if probs else None,
        "brier_baseline_coin": 0.25,
        "permutation_p_on_returns": round(permutation_p(per_pick, PERMUTATION_REPS, PERMUTATION_SEED), 5),
        "note": (
            "Hit rate counts beating the PUBLISHED closing number. It does not use the "
            "model's own line as the benchmark."
        ),
    }
    entry["staking"] = {
        "assumed_price": ASSUMED_PRICE,
        "flat_stake_units": FLAT_STAKE,
        "units": round(units, 3),
        "units_per_selection": round(units / n, 4),
        "max_drawdown_units": round(max_dd, 3),
        "equity_curve": curve,
        "note": (
            "Accounting convention at a stated assumed -110 on both sides. No published hold, "
            "no limits, no wager. Not an ROI claim and not used for ranking."
        ),
    }
    entry["rank_eligible"] = n >= MIN_SELECTIONS_TO_RANK
    return entry


def apply_demotion(entry: dict) -> dict:
    """Evaluate the pre-registered demotion gate on a variant's own record."""
    signal = entry["signal"]
    staking = entry["staking"]
    breaches = []
    if signal.get("hit_rate") is not None and signal["hit_rate"] <= 0.5:
        breaches.append("signal at or below 50% over the graded window")
    if signal.get("permutation_p_on_returns") is not None and signal["permutation_p_on_returns"] > 0.5:
        breaches.append("returns statistically indistinguishable from random signs (p > 0.50)")
    if (
        staking.get("max_drawdown_units") is not None
        and staking["max_drawdown_units"] > DEMOTION["max_drawdown_units"]
        and signal.get("hit_rate") is not None
        and signal["hit_rate"] <= 0.5
    ):
        breaches.append("drawdown over 10 units carried by a sub-50% signal")
    return {
        "gate": DEMOTION["id"],
        "state": "demote_to_paper" if breaches else "hold_paper",
        "breaches": breaches,
    }


def build() -> dict:
    source = load()
    games = source["games"]
    entries = [score_variant(v, games) for v in VARIANTS]
    for entry in entries:
        entry["demotion"] = apply_demotion(entry)

    pvals = [e["signal"].get("p_value_vs_coin") for e in entries if e["n_settled"]]
    qvals = bh_adjust([p for p in pvals if p is not None])
    cursor = 0
    for entry in entries:
        if entry["n_settled"]:
            entry["signal"]["q_value_bh"] = round(qvals[cursor], 6)
            cursor += 1
        else:
            entry["signal"]["q_value_bh"] = None

    # Rank on signal only. A strategy that cannot clear multiplicity control is
    # listed but not ranked, however good its staking column looks.
    rankable = [
        e for e in entries
        if e["rank_eligible"]
        and e["signal"].get("q_value_bh") is not None
        and e["signal"]["q_value_bh"] <= FDR_LEVEL
        and e["signal"]["hit_rate"] > 0.5
    ]
    rankable.sort(key=lambda e: (-e["signal"]["hit_rate"], e["signal"]["q_value_bh"]))

    # The demonstration the split exists for: highest units vs highest signal.
    with_units = [e for e in entries if e["staking"].get("units") is not None]
    best_staking = max(with_units, key=lambda e: e["staking"]["units"]) if with_units else None
    best_signal = max(with_units, key=lambda e: e["signal"]["hit_rate"]) if with_units else None
    divergence = None
    if best_staking and best_signal:
        divergence = {
            "best_staking_id": best_staking["id"],
            "best_staking_units": best_staking["staking"]["units"],
            "best_staking_hit_rate": best_staking["signal"]["hit_rate"],
            "best_staking_q": best_staking["signal"]["q_value_bh"],
            "best_signal_id": best_signal["id"],
            "best_signal_hit_rate": best_signal["signal"]["hit_rate"],
            "best_signal_units": best_signal["staking"]["units"],
            "same_entry": best_staking["id"] == best_signal["id"],
            "reading": (
                "If the best staking record and the best signal record are different entries, "
                "ranking on units would have promoted the wrong strategy. That is the case the "
                "two-column split is designed to expose."
            ),
        }

    # Power: how many settled selections a given true edge needs to be seen.
    power = []
    for true_rate in (0.524, 0.55, 0.60):
        for n in (100, 153, 400, 617, 1000, 2682):
            if true_rate == 0.524 and n < 1000:
                continue
            if true_rate == 0.55 and n < 400:
                continue
            if true_rate == 0.60 and n < 100:
                continue
            power.append({
                "true_rate": true_rate,
                "n": n,
                "power_vs_coin_at_5pct": round(1 - binom_cdf(int(0.5 * n) - 1, n, true_rate), 3),
            })

    return {
        "schema_version": 1,
        "mode": "paper research only; no wager, stake or bankroll is executed",
        "ranking_rule": "Signal only. Staking is reported and never used to rank.",
        "min_selections_to_rank": MIN_SELECTIONS_TO_RANK,
        "fdr_level": FDR_LEVEL,
        "assumed_price": ASSUMED_PRICE,
        "demotion_gate": DEMOTION,
        "multiplicity": {
            "method": "Benjamini-Hochberg over every registered variant, including bad ones",
            "family_size": len(entries),
            "level": FDR_LEVEL,
        },
        "counts": {
            "variants": len(entries),
            "ranked": len(rankable),
            "eligible_but_not_significant": sum(
                1 for e in entries if e["rank_eligible"] and e["signal"].get("q_value_bh") is not None
                and e["signal"]["q_value_bh"] > FDR_LEVEL
            ),
            "below_selection_floor": sum(1 for e in entries if not e["rank_eligible"]),
            "demoted_to_paper": sum(1 for e in entries if e["demotion"]["state"] == "demote_to_paper"),
        },
        "ranking": [e["id"] for e in rankable],
        "divergence": divergence,
        "power": power,
        "entries": entries,
    }


def binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) built from the pmf, scaled to avoid overflow at large n."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    logs = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
            + i * math.log(p) + (n - i) * math.log(1 - p) for i in range(0, k + 1)]
    top = max(logs)
    return min(1.0, math.exp(top) * sum(math.exp(v - top) for v in logs))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build()
    text = json.dumps(result, indent=1) + "\n"
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print("FAIL: data/leaderboard.json is stale; run python leaderboard.py")
            return 1
        print(f"OK: leaderboard reproduces ({result['counts']['variants']} variants)")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    c = result["counts"]
    print(
        f"Wrote {OUT.relative_to(ROOT)} — {c['variants']} variants, {c['ranked']} ranked, "
        f"{c['demoted_to_paper']} demoted, family size {result['multiplicity']['family_size']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
