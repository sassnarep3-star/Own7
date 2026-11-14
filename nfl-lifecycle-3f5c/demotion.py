"""Demotion gate: the pre-registered rule set that returns a live strategy to paper.

Requirement (2026-11-14): "Define a demotion gate that sends a live strategy back to paper."

A strategy's lifecycle state machine is:

    paper --(promotion gates all pass, engine's qualified tier)--> live
    live  --(any demotion trigger fires)-->                        paper (demoted)

A demoted strategy is not deleted: its record keeps the trigger, the window statistics and the
evidence, and re-promotion requires the full promotion path from scratch, with the failed trial
counted in the pre-registered family (no silent retries).

Pre-registered triggers (fixed 2026-11-14, before any live entry exists; they are constants of
this desk, not tunables):

  D1  Signal collapse.   Over the last 20 graded selections (or all selections if fewer, minimum
                          10 to evaluate at all), the one-sided binomial probability of scoring
                          as few wins as observed, given the declared baseline hit rate from the
                          strategy's validation record, is at most 0.01. "At most 0.01" because
                          demotion must not fire on ordinary variance; 1% is stricter than the
                          5% promotion evidence threshold.
  D2  Repeated failure.  Two consecutive D1 windows (overlapping or not) both evaluate at
                          p <= 0.05 (a looser net than D1's single-shot 0.01): demotion fires
                          even if neither window alone reached 0.01.
  D3  Calibration drift. Mean Brier score over the window exceeds the promotion-time Brier by
                          0.05 or more (scale: 0.25 is the no-information reference).
  D4  Integrity breach.  Any settlement number in the strategy's graded record that cannot be
                          traced to a registered official source. Immediate demotion; the
                          affected selections are quarantined pending re-verification.
  D5  Governance breach. Any stake placed outside the pre-registered staking plan recorded at
                          promotion. Immediate demotion; the plan is re-registered before the
                          strategy can be re-promoted.

Evaluation rule: the gate runs after every graded round while a strategy is live. Triggers are
evaluated in order D1, D2, D3, D4, D5 and the first firing trigger is recorded with its window.

Current application: the leaderboard holds 0 live entries (nothing has reached the qualified
tier, and no executable price exists, so nothing is live). The gate is therefore armed and
idle: 0 demotions. The gate's own acceptance test exercises every trigger on synthetic windows
so the rule set is proven before it is ever needed.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
for _p in (str(HERE), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

D1_ALPHA = 0.01
D2_ALPHA = 0.05
D3_BRIER_MARGIN = 0.05
WINDOW = 20
WINDOW_MIN = 10


def binomial_p_at_most(wins: int, n: int, baseline: float) -> float:
    """P(X <= wins) for X ~ Bin(n, baseline). Exact, via math.comb (no dependencies)."""
    if n <= 0:
        raise ValueError("window must contain at least one graded selection")
    if not 0.0 < baseline < 1.0:
        raise ValueError("baseline hit rate must lie strictly inside (0, 1)")
    if not 0 <= wins <= n:
        raise ValueError("wins must lie inside [0, n]")
    total = 0.0
    for k in range(wins + 1):
        total += math.comb(n, k) * baseline ** k * (1 - baseline) ** (n - k)
    return min(1.0, total)


def evaluate_d1(window_wins: int, window_n: int, baseline: float) -> dict:
    """Signal-collapse trigger. Returns the evaluation with its decision."""
    if window_n < WINDOW_MIN:
        return {"trigger": "D1", "evaluated": False,
                "reason": f"insufficient window: {window_n} graded selections, "
                          f"{WINDOW_MIN} required before the gate may judge"}
    p = binomial_p_at_most(window_wins, window_n, baseline)
    return {"trigger": "D1", "evaluated": True, "window_n": window_n,
            "window_wins": window_wins, "baseline": baseline,
            "p_at_most": round(p, 6), "alpha": D1_ALPHA,
            "fired": p <= D1_ALPHA}


def evaluate_d2(windows: list[tuple[int, int]], baseline: float) -> dict:
    """Repeated-failure trigger: two consecutive windows each failing at the looser 0.05 net."""
    evals = []
    for wins, n in windows[-2:]:
        if n < WINDOW_MIN:
            evals.append({"evaluated": False, "reason": "insufficient window"})
            continue
        p = binomial_p_at_most(wins, n, baseline)
        evals.append({"evaluated": True, "window_n": n, "window_wins": wins,
                      "p_at_most": round(p, 6)})
    fired = (len(evals) == 2 and all(e.get("evaluated") and e["p_at_most"] <= D2_ALPHA
                                     for e in evals))
    return {"trigger": "D2", "evaluated": len(evals) == 2 and all(e.get("evaluated") for e in evals),
            "windows": evals, "alpha": D2_ALPHA, "fired": fired}


def evaluate_d3(window_brier: float, promotion_brier: float) -> dict:
    if window_brier is None or promotion_brier is None:
        return {"trigger": "D3", "evaluated": False,
                "reason": "no comparable Brier pair recorded"}
    drift = window_brier - promotion_brier
    return {"trigger": "D3", "evaluated": True, "window_brier": round(window_brier, 6),
            "promotion_brier": round(promotion_brier, 6), "drift": round(drift, 6),
            "margin": D3_BRIER_MARGIN, "fired": drift >= D3_BRIER_MARGIN}


def evaluate_d4(untraceable_settlements: int) -> dict:
    return {"trigger": "D4", "evaluated": True,
            "untraceable_settlements": untraceable_settlements,
            "fired": untraceable_settlements > 0}


def evaluate_d5(off_plan_stakes: int) -> dict:
    return {"trigger": "D5", "evaluated": True, "off_plan_stakes": off_plan_stakes,
            "fired": off_plan_stakes > 0}


def run_gate(entry: dict) -> dict:
    """Evaluate the whole rule set for one live entry; first firing trigger wins.

    entry keys: id, window_wins, window_n, baseline, window_brier, promotion_brier,
                untraceable_settlements, off_plan_stakes.
    """
    checks = [
        evaluate_d1(entry["window_wins"], entry["window_n"], entry["baseline"]),
        evaluate_d2(entry.get("prior_windows", []), entry["baseline"]),
        evaluate_d3(entry.get("window_brier"), entry.get("promotion_brier")),
        evaluate_d4(entry.get("untraceable_settlements", 0)),
        evaluate_d5(entry.get("off_plan_stakes", 0)),
    ]
    fired = next((c for c in checks if c.get("fired")), None)
    return {"id": entry["id"], "checks": checks,
            "demote": fired is not None,
            "fired_trigger": fired["trigger"] if fired else None}


TRIGGERS = [
    {"id": "D1", "name": "Signal collapse",
     "rule": f"One-sided binomial P(X <= observed wins | n window, declared baseline) <= {D1_ALPHA} "
             f"over the last {WINDOW} graded selections (minimum {WINDOW_MIN} to evaluate).",
     "effect": "automatic demotion to paper"},
    {"id": "D2", "name": "Repeated failure",
     "rule": f"Two consecutive windows both evaluate at P <= {D2_ALPHA} against the declared "
             "baseline; fires even when neither window alone reached the D1 threshold.",
     "effect": "automatic demotion to paper"},
    {"id": "D3", "name": "Calibration drift",
     "rule": f"Window mean Brier exceeds the promotion-time Brier by {D3_BRIER_MARGIN} or more "
             "(0.25 is the no-information reference).",
     "effect": "automatic demotion to paper"},
    {"id": "D4", "name": "Integrity breach",
     "rule": "Any settlement number in the graded record is not traceable to a registered "
             "official source.",
     "effect": "immediate demotion; affected selections quarantined pending re-verification"},
    {"id": "D5", "name": "Governance breach",
     "rule": "Any stake placed outside the pre-registered staking plan recorded at promotion.",
     "effect": "immediate demotion; plan must be re-registered before re-promotion"},
]


def build(live_entries: list[dict] | None = None) -> dict:
    """Evaluate the gate over the live book. Today the live book is empty (nothing qualified)."""
    live = live_entries if live_entries is not None else []
    evaluations = [run_gate(entry) for entry in live]
    demotions = [e for e in evaluations if e["demote"]]
    return {
        "schema_version": 1,
        "gate_id": "DG-1",
        "defined_on": "2026-11-14",
        "state_machine": {"paper": "under paper trial; no stakes, no rewards",
                          "live": "promotion gates passed (engine's qualified tier); stakes "
                                  "allowed only inside the registered plan",
                          "paper (demoted)": "returned by a gate trigger; re-promotion restarts "
                                             "the full promotion path and counts as a new trial"},
        "triggers": TRIGGERS,
        "evaluation_rule": "runs after every graded round while a strategy is live; the first "
                           "firing trigger is recorded with its window",
        "applied_to": {"live_entries": len(live),
                       "because": "nothing has reached the engine's qualified tier and no "
                                  "executable price exists (RG03/RG10), so nothing is live"},
        "demotions": demotions,
        "demotion_count": len(demotions),
        "armed": True,
        "source_ids": ["REPO"],
    }
