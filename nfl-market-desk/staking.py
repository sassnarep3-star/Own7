#!/usr/bin/env python3
"""Staking, kept strictly separate from signal.

The requirement was: a lucky staking run must not be able to mask a bad signal. The
way to guarantee that is to compute the two things on different inputs and never let
one feed the other.

    SIGNAL  = did the forecast beat the market line?  (points edge, hit rate, p-value)
              computed against the market line only. Stake never enters.

    STAKING = what a fixed stake would have returned at a *stated price under a stated
              rule* (flat 1 unit at the relayed close). It is a reporting layer.

Consequences that are enforced, not merely described:

* Every staking figure is published beside the signal figures, and the leaderboard
  refuses to promote on staking alone: the promotion gate reads the signal tier only.
* Where a price is missing, ROI is blank. No price is invented and no ROI uses a
  notional -110.
* A staking result is never described as profit actually obtained. Nothing was wagered.
* Push handling is explicit and counted, not silently dropped.
"""
from __future__ import annotations

import math
from statistics import NormalDist

ND = NormalDist()
UNIT = 1.0


def payout_units(price: float, won: bool, push: bool = False) -> float:
    """Return in units for a 1-unit stake at an American price."""
    if push:
        return 0.0
    if won:
        return 100.0 / price if price > 0 else 100.0 / abs(price)
    return -1.0


def settle_spread(pick_line: float, actual_margin: float) -> str:
    """pick_line is the side's own spread (negative = laying points)."""
    margin_from_pick = actual_margin + pick_line
    if abs(margin_from_pick) < 1e-9:
        return "push"
    return "win" if margin_from_pick > 0 else "loss"


def settle_total(side: str, line: float, actual_total: float) -> str:
    if abs(actual_total - line) < 1e-9:
        return "push"
    over = actual_total > line
    if side == "OVER":
        return "win" if over else "loss"
    return "win" if not over else "loss"


def exact_binomial_two_sided(wins: int, losses: int, p: float = 0.5) -> float | None:
    """Exact two-sided binomial p-value by summing outcomes no more likely than observed.

    Pushes are excluded before this is called; the caller reports how many were excluded.
    """
    n = wins + losses
    if n == 0:
        return None
    total = 0.0
    obs = math.comb(n, wins) * (p ** wins) * ((1 - p) ** (n - wins))
    tol = obs * (1 + 1e-9)
    for k in range(n + 1):
        pk = math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))
        if pk <= tol:
            total += pk
    return round(min(1.0, total), 6)


def wilson(wins: int, n: int, z: float = 1.959963985):
    if n == 0:
        return (None, None)
    phat = wins / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    return (round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4))


def required_n(hit: float, baseline: float = 0.5, power: float = 0.8, alpha: float = 0.05) -> int:
    """Observations needed to distinguish `hit` from `baseline` at the stated power."""
    if hit <= baseline:
        return 0
    z_a = ND.inv_cdf(1 - alpha / 2)
    z_b = ND.inv_cdf(power)
    return math.ceil(((z_a * math.sqrt(0.25) + z_b * math.sqrt(hit * (1 - hit))) ** 2) / ((hit - baseline) ** 2))


def grade_flat_stake(rows: list[dict], market: str, snapshot: str = "open") -> dict:
    """Flat 1-unit stakes on every row where the model disagrees with the market.

    A row is only staked when both the model direction and the board price exist.

    `snapshot` is the moment the bet is taken, and it carries a design decision: default
    "open". The desk originates a line *before* the market closes, so the only executable
    moment it can claim is the opening number. Staking at the close would make
    closing-line value identically zero by construction and would quietly assume we could
    trade on information we publish late. If `snapshot` is "close", the CLV column is
    reported as not measurable rather than as zero.

    Direction: back whichever side the model makes the favourite relative to the line.
    """
    decisions = []
    for r in rows:
        d = {"event_id": r["event_id"], "game": r["game"], "market": market}
        if market == "side":
            edge = r.get("edge_points")
            line_key = "market_line_open" if snapshot == "open" else "market_line"
            pr_home = "market_home_price_open" if snapshot == "open" else "market_home_price"
            pr_away = "market_away_price_open" if snapshot == "open" else "market_away_price"
            if edge is None or r.get(line_key) is None:
                continue
            if abs(edge) < 0.5:
                d["decision"] = "pass"
                d["why"] = "model agrees with the market to within half a point"
                decisions.append(d)
                continue
            side = r["home"] if edge > 0 else r["away"]
            pick_line = r[line_key] if edge > 0 else -r[line_key]
            price = float(r[pr_home] if edge > 0 else r[pr_away])
            actual = r["actual_margin"]
            # Convert to the picked side's perspective: home margin, or away margin.
            margin_for_pick = actual if edge > 0 else -actual
            outcome = settle_spread(pick_line, margin_for_pick)
            units = payout_units(price, outcome == "win", outcome == "push")
            d.update({"decision": "bet", "pick": side, "line": pick_line, "price": price,
                      "outcome": outcome, "units": round(units, 4), "snapshot": snapshot})
        elif market == "total":
            edge = r.get("edge_points")
            if edge is None or r.get("market_total") is None:
                continue
            if abs(edge) < 0.5:
                d["decision"] = "pass"
                d["why"] = "model agrees with the market to within half a point"
                decisions.append(d)
                continue
            pick = "OVER" if edge > 0 else "UNDER"
            tk = "market_total_open" if snapshot == "open" else "market_total"
            op = "market_over_price_open" if snapshot == "open" else "market_over_price"
            up = "market_under_price_open" if snapshot == "open" else "market_under_price"
            if r.get(tk) is None:
                continue
            price = float(r[op] if edge > 0 else r[up])
            outcome = settle_total(pick, r[tk], r["actual_total"])
            units = payout_units(price, outcome == "win", outcome == "push")
            d.update({"decision": "bet", "pick": pick, "line": r[tk],
                      "price": price, "outcome": outcome, "units": round(units, 4),
                      "snapshot": snapshot})
        else:
            raise ValueError(market)
        decisions.append(d)

    bets = [d for d in decisions if d["decision"] == "bet"]
    wins = sum(1 for d in bets if d["outcome"] == "win")
    losses = sum(1 for d in bets if d["outcome"] == "loss")
    pushes = sum(1 for d in bets if d["outcome"] == "push")
    staked = float(len(bets))
    returned = round(sum(d["units"] for d in bets), 4)
    lo, hi = wilson(wins, wins + losses)
    return {
        "market": market,
        "decisions": decisions,
        "n_rows": len(rows),
        "n_bets": len(bets),
        "wins": wins, "losses": losses, "pushes": pushes,
        "signal_hit_rate": round(wins / (wins + losses), 4) if (wins + losses) else None,
        "signal_hit_ci": [lo, hi],
        "signal_p_value": exact_binomial_two_sided(wins, losses),
        # Post-hoc power at the *observed* rate is circular: a lucky run lowers its own
        # sample requirement, so a fluke looks adequately powered. The requirement that
        # matters is computed at a rate fixed in advance. Both are published; only the
        # pre-specified one is used to judge adequacy.
        "required_n_at_this_rate_CIRCULAR": required_n(wins / (wins + losses)) if (wins + losses) else None,
        "required_n_at_55pct": required_n(0.55),
        "required_n_at_60pct": required_n(0.60),
        "adequately_powered": (wins + losses) >= required_n(0.55),
        "staking_units_staked": round(staked, 4),
        "staking_units_returned": returned,
        "staking_roi": round(returned / staked, 4) if staked else None,
        "staking_snapshot": snapshot,
        "staking_basis": f"flat 1 unit, relayed DraftKings {snapshot}, push refunded",
        "staking_caveats": [
            "Nothing was wagered. This is a paper computation on a relayed price, not obtained profit.",
            "The price is one provider's number at one snapshot. A real fill could be worse, and limits and availability are unknown.",
            "ROI on this sample is dominated by variance: see the sample-size column before reading the number.",
        ],
    }
