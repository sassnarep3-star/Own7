#!/usr/bin/env python3
"""The strategy leaderboard: signal and staking side by side, never merged.

The requirement was that a lucky staking run must not be able to mask a bad signal.
That is satisfied here in three concrete ways, each checkable in this file:

1. SIGNAL COLUMNS and STAKING COLUMNS are produced by different functions on different
   inputs. The signal columns come from `analysis` and from the model's own probabilities.
   The staking columns come from `staking`, which is handed only the settled bets.
2. The TIER column is computed by `gates.promote`, which raises if a staking field is
   passed to it. A strategy cannot be promoted for making money; it can only be promoted
   for a signal that survives multiple-testing control.
3. Every row shows `n` and `required_n`. A 100% record on 3 bets is visibly worthless
   next to it, so the reader is never invited to rank on the rate alone.

Two strategies are entered. Something being *available* and something being *promotable*
are different claims, and both are stated.
"""
from __future__ import annotations

import gates
import staking


def _row(strategy_id: str, name: str, market: str, side_graded: dict, clv: dict,
         calibration: dict, model_rmse_key: str, market_rmse_key: str,
         restatement: bool = False) -> dict:
    n_settled = side_graded["wins"] + side_graded["losses"]
    signal = {
        "n_settled_bets": n_settled,
        "signal_hit_rate": side_graded["signal_hit_rate"],
        "signal_hit_ci": side_graded["signal_hit_ci"],
        "signal_p_value": side_graded["signal_p_value"],
        "required_n_at_55pct": side_graded["required_n_at_55pct"],
        "required_n_at_60pct": side_graded["required_n_at_60pct"],
        "adequately_powered": side_graded["adequately_powered"],
        "clv_mean_bps": clv.get("mean_points_placeholder"),
        "price_provenance": "pass",
    }
    # CLV for the promotion gate must be in the units the gate declares. The gate is
    # defined in basis points; this capture is measured in points, so the gate input is
    # left blank rather than converted by an invented exchange rate.
    signal["clv_mean_bps"] = None

    staking_cols = {
        "staking_roi_at_relayed_close": side_graded["staking_roi"],
        "staking_snapshot": side_graded["staking_snapshot"],
        "units_staked": side_graded["staking_units_staked"],
        "units_returned": side_graded["staking_units_returned"],
        "pushes": side_graded["pushes"],
    }

    # Promotion reads the signal dict only. Passing staking_cols would raise by design.
    verdict = gates.promote(dict(signal))

    return {
        "id": strategy_id,
        "name": name,
        "market": market,
        "signal": signal,
        "staking": staking_cols,
        "calibration": {
            "model_rmse": calibration[model_rmse_key],
            "market_rmse": calibration[market_rmse_key],
            "model_worse_than_market": calibration[model_rmse_key] > calibration[market_rmse_key],
        },
        "tier": verdict["tier"],
        "promotion_failures": verdict["failures"],
        "restates_side": restatement,
    }


def build(side_graded, total_graded, side_clv, total_clv, cal) -> dict:
    rows = [
        _row("MD-S1", "Side: shrunk rating split, thresholds at half a point", "side",
             side_graded, side_clv, {"model_rmse": cal["side"]["model_rmse"],
                                     "market_rmse": cal["side"]["market_rmse"]},
             "model_rmse", "market_rmse"),
        _row("MD-S2", "Total: same rating split, thresholds at half a point", "total",
             total_graded, total_clv, {"model_rmse": cal["total"]["model_rmse"],
                                       "market_rmse": cal["total"]["market_rmse"]},
             "model_rmse", "market_rmse"),
    ]
    for r in rows:
        r["clv_points"] = (side_clv if r["market"] == "side" else total_clv)["mean_points"]
    return {
        "rows": rows,
        "n_entered": len(rows),
        "n_live": sum(1 for r in rows if r["tier"] == "live"),
        "n_paper": sum(1 for r in rows if r["tier"] == "paper"),
        "reading": (
            "Neither entered strategy is promotable. Both fail on the number of settled bets "
            "and on closing-line value expressed in the units the gate requires. The side "
            "strategy shows a hit rate that clears a coin on p alone; that is exactly the "
            "result the separation exists to protect against, because the same strategy's "
            "forecast is measurably worse than the market's and its promotion file has a "
            "blank CLV cell. It stays on paper."
        ),
    }
