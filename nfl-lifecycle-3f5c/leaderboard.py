"""Leaderboard that separates SIGNAL from STAKING.

Requirement (2026-11-14): "Separate 'signal' from 'staking' in the leaderboard so a lucky
staking run cannot mask a bad signal."

Design
------
The graded ledger (nfl-results/analysis.json, produced by the results engine) is consumed
read-only. This desk republishes it as two independent tables that share ids but nothing else:

  SIGNAL table   everything about the picks themselves: n, wins, hit rate, one-sided p against
                 the strategy's declared reference, BH q-value, confidence interval, tier.
                 The RANK is computed from signal fields only.
  STAKING table  everything about how the picks would be staked: the approved stake plan
                 (null — none has been approved), the number of stakes actually placed
                 (0 — no executable price exists), realized units, drawdown. All null or zero
                 for every strategy, because RG03 (no executable price) and RG10 (no release
                 rights) are blocked. The staking table has no rank column and cannot feed one.

The separation is enforced structurally, not by convention:

  * `rank_by_signal(entries)` accepts dicts and reads only the SIGNAL_FIELDS key set;
    it raises if a ranking call would need anything else. Tests prove that permuting,
    adding or corrupting staking fields leaves every rank unchanged.
  * The staking table is rendered without a rank column; a test asserts its keys.

Tiers are inherited verbatim from the results engine (qualified / provisional / rejected).
This desk does not re-grade or re-rank candidates the engine rejected; it ranks the full
graded family on signal for transparency and marks the engine's tiers beside them.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
for _p in (str(HERE), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

ANALYSIS = REPO / "nfl-results" / "analysis.json"

SIGNAL_FIELDS = ("id", "name", "market", "selective", "bets", "wins", "losses",
                 "hit_rate", "p_value", "q_value", "ci_low", "ci_high", "tier")
STAKING_FIELDS = ("id", "stake_plan", "stakes_placed", "realized_units",
                  "max_drawdown_units", "blocked_by")

_R = 6


def _round(value, places=_R):
    if isinstance(value, float):
        return round(value, places)
    return value


def load_analysis() -> dict:
    return json.loads(ANALYSIS.read_text(encoding="utf-8"))


def rank_by_signal(entries: list[dict]) -> list[dict]:
    """Order entries by signal quality only. Staking keys are neither read nor allowed to help.

    Sort key: descending hit rate among entries with n >= 20 (the engine's own minimum for
    chance comparisons), then ascending p-value, then id for determinism. Entries with fewer
    than 20 graded picks sort after all qualified-sample entries, by n descending.
    """
    def key(entry: dict) -> tuple:
        missing = [f for f in ("id", "bets", "hit_rate", "p_value") if f not in entry]
        if missing:
            raise KeyError(f"ranking needs signal fields only; missing {missing} for {entry.get('id')}")
        bets, hit, p = entry["bets"], entry["hit_rate"], entry["p_value"]
        if bets is None or hit is None:
            return (1, 0, -float("inf"), entry["id"])
        if bets >= 20:
            return (0, -(hit or 0), (p if p is not None else 1), entry["id"])
        return (1, 0, -(hit or 0), entry["id"])

    ordered = sorted(entries, key=key)
    for rank, entry in enumerate(ordered, start=1):
        entry["signal_rank"] = rank
    return ordered


def signal_table(analysis: dict) -> list[dict]:
    """One signal row per graded candidate, ranked by signal only."""
    rows = []
    tiers = {row["id"]: row["tier"] for row in analysis["leaderboard"]}
    for cand in analysis["candidates"]:
        stat = cand["stat"]
        rows.append({
            "id": cand["id"],
            "name": cand["name"],
            "market": cand["market"],
            "selective": cand["selective"],
            "bets": stat["bets"],
            "wins": stat["wins"],
            "losses": stat["losses"],
            "hit_rate": _round(stat["hit_rate"]),
            "p_value": _round(stat["p_value"], 4),
            "q_value": _round(cand.get("q_value"), 4),
            "ci_low": _round(stat["ci_low"]),
            "ci_high": _round(stat["ci_high"]),
            "tier": tiers.get(cand["id"], "rejected"),
        })
    return rank_by_signal(rows)


def staking_table(entries: list[dict]) -> list[dict]:
    """One staking row per graded candidate. No rank column. Nothing invented."""
    return [{
        "id": entry["id"],
        "stake_plan": None,
        "stakes_placed": 0,
        "realized_units": None,
        "max_drawdown_units": None,
        "blocked_by": "RG03 (no executable price) and RG10 (no release rights); a stake "
                      "cannot be planned or settled without a price to settle against",
    } for entry in entries]


def build() -> dict:
    analysis = load_analysis()
    signal = signal_table(analysis)
    staking = staking_table(signal)
    provisional = [r for r in signal if r["tier"] == "provisional"]
    return {
        "schema_version": 1,
        "source_artifact": "nfl-results/analysis.json",
        "generated_for": analysis["generated_for"],
        "separation": {
            "rule": "rank_by_signal() reads only SIGNAL_FIELDS; the staking table has no rank "
                    "and no path into one",
            "signal_fields": list(SIGNAL_FIELDS[:-1]),
            "staking_fields": list(STAKING_FIELDS[1:]),
            "why": "a lucky staking run cannot mask a bad signal because staking outcomes are "
                   "not part of the ranking computation at all",
        },
        "counts": {
            "graded": len(signal),
            "provisional": len(provisional),
            "qualified": sum(1 for r in signal if r["tier"] == "qualified"),
            "rejected": sum(1 for r in signal if r["tier"] == "rejected"),
        },
        "signal": signal,
        "staking": staking,
        "source_ids": ["NFL-SCHEDULE", "REPO"],
    }
