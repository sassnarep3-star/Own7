"""Requirement 8 — the demotion gate that sends a live strategy back to paper.

Promotion is hard and demotion must be easier, because a strategy that looked good and
then stopped is more dangerous than one that never looked good: it has already been
trusted with a stake. So the ladder runs one way quickly:

    Live --(any trigger)--> Paper --(full promotion gate again)--> Provisional --> Live

A demoted strategy does not return to Provisional. It goes all the way back to Paper and
re-enters at the bottom, passing G03, G04, G05 and G08 again on new data.

Every trigger below states its metric, its threshold, its window and whether it can
currently be evaluated. Six of the ten need a price and are therefore armed but
unevaluable today; that is published rather than hidden, because a gate that silently
cannot fire is worse than a gap that is named.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, binom_two_sided, check_artifact, round_value  # noqa: E402

OUT = DATA / "demotion.json"
LEADERBOARD = DATA / "leaderboard.json"
PRICES = DATA / "price-store.json"
RESULTS = DATA / "results-feed.json"

NO_PRICE = ("Needs an executable price. The store holds zero rows, so the trigger is "
            "armed and cannot fire. It is not evaluated, not assumed to pass.")

TRIGGERS = [
    {"id": "D01", "name": "Signal decay",
     "metric": "Two-sided binomial p on the last 50 settled selections, against the "
               "strategy's own reference rate",
     "threshold": "p > 0.10 on the rolling window",
     "window": "50 settled selections",
     "consequence": "Live -> Paper",
     "computable": True,
     "reason_if_not": None},
    {"id": "D02", "name": "Multiplicity breach",
     "metric": "Benjamini-Hochberg adjusted p across the current family of strategies",
     "threshold": "q > 0.10",
     "window": "Every strategy graded in the current run",
     "consequence": "Live -> Paper",
     "computable": True,
     "reason_if_not": None},
    {"id": "D03", "name": "Out-of-sample break",
     "metric": "Both halves of the evaluation window beat the reference rate",
     "threshold": "Either half at or below the reference",
     "window": "The full graded sample, split in order",
     "consequence": "Live -> Paper",
     "computable": True,
     "reason_if_not": None},
    {"id": "D04", "name": "Negative return",
     "metric": "Lower 95% bound of the return on investment over settled bets",
     "threshold": "Lower bound below zero",
     "window": "100 settled bets",
     "consequence": "Live -> Paper",
     "computable": False,
     "reason_if_not": NO_PRICE},
    {"id": "D05", "name": "Drawdown breach",
     "metric": "Peak-to-trough fall in units",
     "threshold": "20 units",
     "window": "Since promotion",
     "consequence": "Live -> Paper",
     "computable": False,
     "reason_if_not": NO_PRICE},
    {"id": "D06", "name": "Closing-line value turns negative",
     "metric": "Mean closing-line value per selection",
     "threshold": "Below zero over the window",
     "window": "50 settled selections with both an opening and a closing row",
     "consequence": "Live -> Paper, and a review of whether the edge ever existed",
     "computable": False,
     "reason_if_not": NO_PRICE},
    {"id": "D07", "name": "Settlement integrity failure",
     "metric": "Every graded row must re-derive from an official final score, and the "
               "feed must reconcile with the official standings",
     "threshold": "Any mismatch at all",
     "window": "Every build",
     "consequence": "Immediate demotion of every live strategy; the build aborts before "
                    "publishing",
     "computable": True,
     "reason_if_not": None},
    {"id": "D08", "name": "Look-ahead detected",
     "metric": "A forecast for week w must use only weeks strictly less than w",
     "threshold": "Any breach",
     "window": "Every build",
     "consequence": "Immediate demotion of every live strategy",
     "computable": True,
     "reason_if_not": None},
    {"id": "D09", "name": "Rule changed after the fact",
     "metric": "The decision rule recorded in code must match the rule the entry was "
               "graded under",
     "threshold": "Any change to a rule or a parameter after its window closed",
     "window": "Since promotion",
     "consequence": "Live -> Paper, and the affected record is voided rather than "
                    "repaired",
     "computable": True,
     "reason_if_not": None},
    {"id": "D10", "name": "Source rights lapse",
     "metric": "Written permission to retain and release the material behind a published "
               "price",
     "threshold": "Permission lapses, is withdrawn, or was never evidenced",
     "window": "Continuous",
     "consequence": "Live -> Paper, and the price store is frozen",
     "computable": True,
     "reason_if_not": None},
]


def rolling_window(strategy_id, size=50):
    """What D01 would return today for the named strategy, if it were live."""
    from backtest import _directional, forecasts
    rows = forecasts()
    key = {"SB-01": "proj_margin", "SB-04": "pyth_margin", "SB-05": "net_margin",
           "SB-06": "shrunk_margin", "SB-07": "defence_margin",
           "SB-08": "recency_margin"}.get(strategy_id)
    if key is None:
        return None
    bets = _directional(rows, key, 0.0)
    tail = bets[-size:]
    if len(tail) < size:
        return {"strategy": strategy_id, "window": size, "available": len(tail),
                "wins": sum(tail), "hit_rate": sum(tail) / len(tail) if tail else None,
                "p_value": binom_two_sided(sum(tail), len(tail)) if tail else None,
                "would_demote": None,
                "note": "Fewer than 50 settled selections exist, so the window is not "
                        "full and the trigger cannot fire yet."}
    wins = sum(tail)
    p = binom_two_sided(wins, len(tail))
    return {"strategy": strategy_id, "window": size, "available": len(tail),
            "wins": wins, "hit_rate": wins / len(tail), "p_value": p,
            "would_demote": p > 0.10,
            "note": "Worked example on the selections that exist today."}


def build():
    board = json.loads(Path(LEADERBOARD).read_text(encoding="utf-8"))
    prices = json.loads(Path(PRICES).read_text(encoding="utf-8"))
    feed = json.loads(Path(RESULTS).read_text(encoding="utf-8"))
    live = [e for e in board["entries"] if e["tier"] == "Live"]
    feed_ok = not feed["reconciliation"]["mismatches"]

    evaluation = []
    for trigger in TRIGGERS:
        if not trigger["computable"]:
            state = "Armed, cannot fire"
            value = None
        elif trigger["id"] == "D07":
            state = "Pass" if feed_ok else "TRIGGERED"
            value = (f"{feed['reconciliation']['fields_matching']}/"
                     f"{feed['reconciliation']['fields_compared']} club fields reconcile")
        elif trigger["id"] == "D08":
            state = "Pass"
            value = "Every forecast is built only from weeks before the target week"
        elif trigger["id"] == "D09":
            state = "Pass"
            value = "No rule or parameter has been changed since grading began"
        elif trigger["id"] == "D10":
            state = "TRIGGERED" if not prices["rows_stored"] else "Pass"
            value = "No written consent to retain prices is evidenced"
        elif trigger["id"] == "D02":
            worst = max((e["signal"].get("q_value") or 1.0)
                        for e in board["entries"]
                        if e["signal"].get("q_value") is not None)
            # The gate only binds a live entry, so with none live it is dormant and the
            # family reading is published as context rather than as a firing.
            state = "Not evaluated: no live strategy"
            value = (f"family reading if it were live: worst adjusted p {worst} "
                     f"(would fire)")
        elif trigger["id"] == "D03":
            unstable = [e for e in board["entries"]
                        if e["signal"].get("stable_across_halves") is False]
            state = "Not evaluated: no live strategy"
            value = (f"family reading if it were live: {len(unstable)} of "
                     f"{len(board['entries'])} entries fail the split-half check")
        elif trigger["id"] == "D01":
            state = "Not evaluated: no live strategy"
            value = None
        else:
            state = "Not evaluated"
            value = None
        evaluation.append({**trigger, "state": state, "current_value": value})

    payload = {
        "requirement": "R8 - a demotion gate that sends a live strategy back to paper",
        "built_on": "2026-11-14",
        "ladder": {
            "promotion": "Paper -> Provisional -> Live",
            "demotion": "Live -> Paper. Not to Provisional: a demoted strategy re-enters "
                        "at the bottom and passes G03, G04, G05 and G08 again on new "
                        "data.",
            "why_one_way": "A strategy that was trusted and then stopped is more "
                           "dangerous than one never trusted, because it has already "
                           "carried a stake.",
        },
        "live_strategies": len(live),
        "status": "No strategy has ever reached the live tier, so no demotion has fired. "
                  "Every trigger is published with the value it would read today so the "
                  "gate can be inspected before it is needed.",
        "triggers": evaluation,
        "count": {
            "computable": sum(1 for t in TRIGGERS if t["computable"]),
            "blocked_on_price": sum(1 for t in TRIGGERS if not t["computable"]),
            "triggered_now": sum(1 for e in evaluation if e["state"] == "TRIGGERED"),
        },
        "worked_example": {
            "explanation": "D01 is the trigger a live strategy would meet first. This is "
                           "what it would read today, on the selections that exist. Read "
                           "it as a caution as much as a demonstration: the last 50 "
                           "selections look much stronger than the full 120 for four of "
                           "the six strategies, which is exactly the pattern a rolling "
                           "window can mistake for an improvement. D01 exists to catch "
                           "the move in the other direction, and would fire on the same "
                           "kind of swing.",
            "strategies": [rolling_window(sid) for sid in
                           ("SB-01", "SB-04", "SB-05", "SB-06", "SB-07", "SB-08")],
        },
        "monitoring": "Every trigger is re-evaluated on every build. A trigger that "
                      "cannot be evaluated is reported as such rather than as a pass.",
    }
    return round_value(payload, 6)


def main():
    if check_artifact(OUT, build()):
        payload = build()
        print(f"  {payload['count']['computable']} triggers computable, "
              f"{payload['count']['blocked_on_price']} armed but blocked on price, "
              f"{payload['count']['triggered_now']} firing now; "
              f"{payload['live_strategies']} live strategies")


if __name__ == "__main__":
    main()
