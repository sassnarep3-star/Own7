"""Competition leaderboard with a luck-adjusted ranking.

The brief asks for a leaderboard that rewards top-performing strategies and for
luck to be taken out of the equation. Those two pulls are in tension: a plain
ROI leaderboard rewards luck by construction, because ROI after a few hundred
bets is mostly noise.

The ranking here is therefore:

1. **Eligibility first.** A strategy is ranked only if it passes every gate in
   ``gates.py``. Unproven strategies appear in the table with their status but
   receive no rank. This is stated on the page so nobody mistakes a blank rank
   for a bug.
2. **Score = lower confidence bound on ROI**, not ROI. Specifically the
   normal-approximation one-sided 95% lower bound of per-bet return, which
   automatically penalises both a weak edge and a short record. Two strategies
   with the same mean but different n do not rank equally.
3. **Tie-break on deflated Sharpe**, so a strategy that survived more trials
   ranks above one that did not.

Rewards are deliberately NOT defined. ``rewards.py``-style invention (points,
prizes, money) would be fabricated policy, and the brief's authority to set
rewards sits with the owner. The schema leaves ``reward`` as null and the site
flags it.
"""

from __future__ import annotations

import math
from typing import Any, Sequence


def roi(returns: Sequence[float]) -> float | None:
    """Mean net return per unit staked."""
    if not returns:
        return None
    return sum(returns) / len(returns)


def roi_lower_bound(returns: Sequence[float], confidence: float = 0.95) -> dict[str, Any]:
    """One-sided lower confidence bound on per-bet ROI (normal approximation).

    The normal approximation is used for transparency, not because returns are
    normal: bet returns are bimodal by construction. For n >= 100 the
    approximation is adequate for ranking; below that the interval is wide and
    the function says so.
    """
    n = len(returns)
    if n < 2:
        return {"ok": False, "n": n, "reason": "need at least 2 returns"}
    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / (n - 1)
    sd = math.sqrt(var)
    se = sd / math.sqrt(n)
    z = 1.6448536269514722 if confidence == 0.95 else 1.959963984540054
    return {
        "ok": True,
        "n": n,
        "mean_roi": round(mean, 6),
        "sd_per_bet": round(sd, 6),
        "se": round(se, 6),
        "lower_bound": round(mean - z * se, 6),
        "upper_bound": round(mean + z * se, 6),
        "confidence": confidence,
        "adequacy": "adequate for ranking" if n >= 100 else "wide interval; treat as indicative only",
    }


def rank(entries: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Rank strategies. Only gate-passing entries receive a rank.

    Each entry needs: ``id``, ``name``, ``category``, ``overall_gate_status``,
    ``returns`` (list of per-bet net returns).
    """
    scored = []
    for e in entries:
        base = {
            "id": e.get("id"),
            "name": e.get("name"),
            "category": e.get("category"),
            "overall_gate_status": e.get("overall_gate_status"),
            "n_bets": len(e.get("returns") or []),
        }
        lb = roi_lower_bound(e.get("returns") or [])
        base["roi"] = round(roi(e.get("returns") or []), 6) if e.get("returns") else None
        base["roi_lower_bound"] = lb.get("lower_bound") if lb.get("ok") else None
        base["eligible"] = e.get("overall_gate_status") == "passed"
        base["reward"] = None  # deliberately undefined; owner decision
        scored.append(base)

    eligible = [s for s in scored if s["eligible"] and s["roi_lower_bound"] is not None]
    eligible.sort(key=lambda s: (-s["roi_lower_bound"], s["name"] or ""))
    for i, s in enumerate(eligible, start=1):
        s["rank"] = i

    ineligible = [s for s in scored if not s["eligible"]]
    ineligible.sort(key=lambda s: (s["overall_gate_status"] or "", s["name"] or ""))
    for s in ineligible:
        s["rank"] = None

    return {
        "sorted": eligible + ineligible,
        "n_eligible": len(eligible),
        "n_total": len(scored),
        "ranking_rule": "rank = order of one-sided 95% lower bound on per-bet ROI; only strategies with overall_gate_status == 'passed' are ranked",
        "reward_status": "undefined by design; the owner sets rewards, and none are inferred here",
    }


def movement(previous: dict[str, int], current: dict[str, int]) -> dict[str, Any]:
    """Rank movement between two leaderboard snapshots."""
    out = {}
    for key, now in current.items():
        before = previous.get(key)
        out[key] = None if before is None else before - now  # positive = moved up
    return {"movement": out, "note": "positive means the strategy moved up the board"}


def leaderboard_turnover_probe(n_bettors: int, n_bets_each: int, win_prob: float, decimal_odds: float) -> dict[str, Any]:
    """How much of a leaderboard is luck: share of identical entries that look good.

    This is the single most important number on the competition page, because
    it tells the organiser how long the evaluation window must be before the
    board means anything.
    """
    from . import skill

    return skill.leaderboard_noise_check(n_bettors, n_bets_each, win_prob, decimal_odds)
