"""Requirement 5 — separate signal from staking on the leaderboard.

The failure this is built to prevent is a staking run being mistaken for a good forecast.
A flat stake that happens to land on a hot month produces a large return and a rank, and
the rank then looks like evidence. So the two halves are published as two tables that
never touch:

  * the signal table is ranked, and every column in it is computable without a price;
  * the staking table is empty, and is declared empty, because every column in it needs
    an executable price that no consulted official source publishes.

A consequence is stated up front: when a price exists, the staking table can demote an
entry, and can never promote one.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, check_artifact, round_value, write_csv  # noqa: E402

OUT = DATA / "leaderboard.json"
OUT_CSV = DATA / "leaderboard.csv"
BACKTEST = DATA / "backtest.json"
PRICES = DATA / "price-store.json"
CORRELATIONS = DATA / "correlations.json"
RESULTS = DATA / "results-feed.json"

NO_PRICE = ("No consulted official source publishes an executable price, so there is no "
            "stake, no return, no drawdown and no closing-line value. Blank by rule.")

GATES = [
    {"id": "G01", "name": "Rule pre-registered",
     "rule": "The decision rule is written down in code before the results are graded, "
             "and no rule is changed after the fact.",
     "blocks": "Promotion of any kind."},
    {"id": "G02", "name": "No look-ahead",
     "rule": "A forecast for week w uses only weeks strictly less than w, including the "
             "home allowance, the margin spread and the league mean.",
     "blocks": "Promotion of any kind."},
    {"id": "G03", "name": "Minimum settled sample",
     "rule": "At least 30 graded selections with a settled official result.",
     "blocks": "Provisional tier."},
    {"id": "G04", "name": "Signal survives multiplicity",
     "rule": "Benjamini-Hochberg adjusted p at most 0.10 across every strategy tested in "
             "the same run.",
     "blocks": "Provisional tier."},
    {"id": "G05", "name": "Out-of-sample stability",
     "rule": "Both halves of the sample beat the reference. Applicable to rate-based "
             "strategies only.",
     "blocks": "Provisional tier."},
    {"id": "G06", "name": "Executable price captured",
     "rule": "The price-snapshot store holds one opening row and one closing row for the "
             "market, from a named operator, captured before kickoff.",
     "blocks": "Live tier, and every reward."},
    {"id": "G07", "name": "Settlement reproducible",
     "rule": "Every graded row re-derives from an official final score, and the whole "
             "feed reconciles with the official standings.",
     "blocks": "Promotion of any kind."},
    {"id": "G08", "name": "Leg dependence measured",
     "rule": "For a multi-leg strategy, a dependence estimate with a published n exists "
             "in correlations.json for exactly that leg structure.",
     "blocks": "Provisional tier for parlays only."},
    {"id": "G09", "name": "No parameter fitted in the window",
     "rule": "Every parameter is either a published constant or measured from weeks "
             "before the game being forecast. Nothing is fitted on the evaluation "
             "window.",
     "blocks": "Promotion of any kind."},
    {"id": "G10", "name": "Source rights cleared",
     "rule": "Written permission exists to retain and release the source material behind "
             "any published price. Not evidenced for NFL.com.",
     "blocks": "Live tier, and release of any dataset."},
]

# Which dependence rows in correlations.json satisfy G08 for which strategy.
DEPENDENCE_FOR = {
    "PB-01": "C01",
    "PB-02": "C02",
    "PB-03": "C03",
    "PB-04": "C03",
}

DIVISIONS = ["Single bets", "Parlays", "Player props / combos"]

REWARD_SCHEDULE = {
    "merit_points": {"1": 3, "2": 2, "3": 1},
    "merit_points_awarded": 0,
    "cash_reward": None,
    "cash_reward_pool": None,
    "prize_eligibility": "A reward requires the live tier, which requires G06. The price "
                         "store holds zero rows, so no entry is eligible.",
    "what_is_being_ranked": "Signal only. Ranking never uses a stake, a return or a "
                            "bankroll, because none of those exist here.",
}


def evaluate_gates(strategy, price_rows, correlation_ids, feed_ok):
    signal = strategy["signal"]
    n = signal.get("n")
    gates = {}

    gates["G01"] = "pass"
    gates["G02"] = "pass"
    # A blocked strategy is not failing the performance gates; the official numbers
    # needed to grade it at all were never retrieved, so those gates do not apply.
    blocked = strategy["kind"] == "blocked"
    control = strategy["status"] == "Control"
    gates["G03"] = "n/a" if blocked else ("pass" if (n or 0) >= 30 else "fail")
    if blocked or control:
        gates["G04"] = "n/a"
    else:
        gates["G04"] = "pass" if signal.get("reject_null_at_fdr_10pct") else "fail"
    if strategy["kind"] == "directional" and not blocked:
        gates["G05"] = "pass" if signal.get("stable_across_halves") else "fail"
    else:
        gates["G05"] = "n/a"
    gates["G06"] = "n/a" if blocked else ("pass" if price_rows else "fail")
    gates["G07"] = "pass" if feed_ok else "fail"
    if strategy["division"] == "Parlays" and not blocked:
        dep = DEPENDENCE_FOR.get(strategy["id"])
        gates["G08"] = "pass" if (dep and dep in correlation_ids) else "fail"
    else:
        gates["G08"] = "n/a"
    gates["G09"] = "pass"
    gates["G10"] = "n/a" if blocked else "fail"

    applicable = [v for v in gates.values() if v != "n/a"]
    return {
        "gates": gates,
        "passed": sum(1 for v in applicable if v == "pass"),
        "applicable": len(applicable),
        "failed": sorted(k for k, v in gates.items() if v == "fail"),
    }


def tier(entry):
    gates = entry["gates"]
    if gates["G01"] != "pass" or gates["G02"] != "pass" or gates["G07"] != "pass" \
            or gates["G09"] != "pass":
        return "Disqualified"
    if entry["strategy_kind"] == "blocked":
        return "Blocked on data"
    # A control exists to demonstrate a property of the test, not to compete. It is
    # never ranked and never promoted.
    if entry.get("status") == "Control":
        return "Control"
    provisional_gates = ("G03", "G04", "G05", "G08")
    if all(gates[g] in ("pass", "n/a") for g in provisional_gates):
        if gates["G06"] == "pass" and gates["G10"] == "pass":
            return "Live"
        return "Provisional"
    return "Paper"


def signal_score(strategy):
    """A single comparable number for ranking. Higher is better. None means unranked.

    It is deliberately a strength-of-evidence measure, not a hit rate: a 60% record on
    18 selections must not outrank a 60% record on 120, and a large p-value must drive
    the score toward zero rather than away from it. So the score grows with the sample
    size, with the distance from the reference, and with the strength of the evidence
    against the null.
    """
    import math
    signal = strategy["signal"]
    if strategy["status"] == "Control":
        return None
    n = signal.get("n")
    if not n:
        return None
    p = signal.get("p_value")
    if p is None or p <= 0:
        return None
    magnitude = abs((signal.get("hit_rate") or 0) - (signal.get("null_rate") or 0))
    if signal.get("skill_score") is not None:
        magnitude = abs(signal["skill_score"])
    if signal.get("brier") is not None and signal.get("null_brier"):
        magnitude = abs(signal["null_brier"] - signal["brier"])
    evidence = -math.log10(max(p, 1e-12))
    return math.log10(n) * magnitude * evidence


def build():
    backtest = json.loads(Path(BACKTEST).read_text(encoding="utf-8"))
    prices = json.loads(Path(PRICES).read_text(encoding="utf-8"))
    correlations = json.loads(Path(CORRELATIONS).read_text(encoding="utf-8"))
    feed = json.loads(Path(RESULTS).read_text(encoding="utf-8"))
    price_rows = prices["rows_stored"]
    correlation_ids = {row["id"] for row in correlations["rows"]
                       if row["value"] is not None}
    feed_ok = not feed["reconciliation"]["mismatches"]

    entries = []
    for strategy in backtest["strategies"]:
        score = evaluate_gates(strategy, price_rows, correlation_ids, feed_ok)
        rank_score = signal_score(strategy)
        entries.append({
            "id": strategy["id"], "name": strategy["name"],
            "division": strategy["division"], "market": strategy["market"],
            "rule": strategy["rule"],
            "strategy_kind": strategy["kind"],
            "signal": strategy["signal"],
            "staking": strategy["staking"],
            **score,
            "signal_score": rank_score,
            "status": strategy.get("status"),
        })
    for entry in entries:
        entry["tier"] = tier(entry)

    ranked = [e for e in entries if e["signal_score"] is not None]
    ranked.sort(key=lambda e: -e["signal_score"])
    for index, entry in enumerate(ranked, start=1):
        entry["signal_rank_overall"] = index
    by_division = {}
    for division in DIVISIONS:
        group = [e for e in ranked if e["division"] == division]
        group.sort(key=lambda e: -e["signal_score"])
        for index, entry in enumerate(group, start=1):
            entry["signal_rank_in_division"] = index
        by_division[division] = [e["id"] for e in group]
    for entry in entries:
        entry.setdefault("signal_rank_overall", None)
        entry.setdefault("signal_rank_in_division", None)

    write_csv(OUT_CSV, [{
        "id": e["id"], "division": e["division"], "market": e["market"],
        "name": e["name"], "tier": e["tier"],
        "signal_rank": e["signal_rank_overall"],
        "n": e["signal"].get("n"), "hit_rate": e["signal"].get("hit_rate"),
        "null_rate": e["signal"].get("null_rate"),
        "p_value": e["signal"].get("p_value"), "q_value": e["signal"].get("q_value"),
        "signal_score": e["signal_score"],
        "staking_rank": None, "roi": None, "units": None, "drawdown": None,
        "merit_points": 0, "cash_reward": None,
        "failed_gates": ";".join(e["failed"]),
    } for e in sorted(entries, key=lambda e: (e["signal_rank_overall"] is None,
                                              e["signal_rank_overall"] or 0))])

    counts = {t: sum(1 for e in entries if e["tier"] == t)
              for t in ("Live", "Provisional", "Paper", "Blocked on data",
                        "Control", "Disqualified")}
    payload = {
        "requirement": "R5 - signal and staking separated on the leaderboard",
        "built_on": "2026-11-14",
        "separation_rule": [
            "The signal table is ranked on evidence strength, never on a return. Its "
            "columns are computable with no price at all.",
            "The staking table is empty and stays empty. When a price exists it can "
            "demote an entry and can never promote one, so a lucky staking run cannot "
            "lift a bad signal.",
            "No column in either table mixes the two: no return, stake or drawdown "
            "appears in the signal table, and no forecast accuracy appears in the "
            "staking table.",
        ],
        "signal_ranking_metric": {
            "name": "signal score",
            "formula": "log10(n) x |statistic - reference| x -log10(p)",
            "why": "A bare hit rate rewards a small sample, so the score scales the "
                   "distance from the reference by the evidence for it. A 60% record on "
                   "18 selections cannot outrank a 60% record on 120, and a result "
                   "consistent with chance scores near zero however large the "
                   "raw gap looks.",
        },
        "gates": GATES,
        "gate_rule": "A gate marked n/a leaves the denominator and is never counted as a "
                     "pass.",
        "tiers": {
            "Paper": "Default. Rules and settlement are sound; the signal has not "
                     "cleared the evidence bar.",
            "Provisional": "G03, G04, G05 and G08 clear. Published for review; no "
                           "reward, no stake.",
            "Live": "Provisional plus G06 (executable price) and G10 (source rights). "
                    "Only a live strategy is exposed to the demotion gate.",
            "Blocked on data": "The official numbers needed to grade the strategy were "
                               "never retrieved, so the performance gates do not apply.",
            "Control": "Published to demonstrate a property of the test - a forecast "
                       "graded against its own number, or a slip whose legs are the same "
                       "event. A control is never ranked and never promoted.",
        },
        "divisions": DIVISIONS,
        "division_members": by_division,
        "counts": counts,
        "rewards": REWARD_SCHEDULE,
        "staking_table": {
            "rows": [],
            "empty_because": NO_PRICE,
            "columns": ["staking_rank", "stake_units", "roi", "profit_units",
                        "max_drawdown_units", "closing_line_value"],
            "effect_on_signal_rank": "None. Ever. By construction: the signal rank is "
                                     "computed before the staking table is read.",
        },
        "entries": entries,
    }
    return round_value(payload, 6)


def main():
    if check_artifact(OUT, build()):
        payload = build()
        print(f"  {len(payload['entries'])} entries; tiers "
              f"{payload['counts']}; staking table rows "
              f"{len(payload['staking_table']['rows'])}")


if __name__ == "__main__":
    main()
