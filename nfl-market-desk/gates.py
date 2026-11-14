#!/usr/bin/env python3
"""Validation gates, including the demotion gate that returns a live strategy to paper.

A gate is only real if it can fail. Each gate below is a function of the published
data and returns pass / fail / blocked with the evidence that decided it. Nothing here
returns pass when the underlying input is missing: a missing input is `blocked`.
"""
from __future__ import annotations

GATE_DEFS = [
    ("MD-G01", "Price provenance",
     "Every priced row names provider, provider id, source id, https url and retrieval date, "
     "and is labelled relayed. PASS if zero rows lack any of these."),
    ("MD-G02", "Open and close both present",
     "Every originated market carries an opening and a closing observation, so a movement "
     "series exists rather than a single stale number."),
    ("MD-G03", "Official result binding",
     "Every priced game binds to an official final score with a source url, and the binding "
     "is on the club pair, not on a position in a list."),
    ("MD-G04", "Three-column publication",
     "Each board publishes model, market and difference as separate columns, and never omits "
     "the market column when the model disagrees."),
    ("MD-G05", "No synthetic price",
     "No ROI, CLV or edge uses an assumed price such as -110. Where a price is absent the "
     "figure is blank and flagged."),
    ("MD-G06", "Signal/staking separation",
     "Promotion reads the signal tier only. Staking figures are reported but cannot qualify a "
     "strategy. PASS if the promotion function never receives a staking field."),
    ("MD-G07", "Sample-size honesty",
     "Every published rate carries n and the n required to detect it at 80% power, so a rate "
     "on a small sample is visibly non-evidential."),
    ("MD-G08", "Push accounting",
     "Pushes are counted and excluded from the hit-rate denominator before the p-value, and "
     "the count is published."),
    ("MD-G09", "Correlation provenance",
     "Every correlation is computed from official-sourced numbers and publishes its n."),
    ("MD-G10", "Demotion gate armed",
     "A live strategy carries explicit numeric demotion triggers, evaluated on the live ledger, "
     "that send it back to paper. PASS if the rules are numeric and executable."),
]

# The demotion gate, stated as executable thresholds.
DEMOTION_GATE = {
    "id": "MD-G10",
    "name": "Demotion gate (live -> paper)",
    "applies_to": "any strategy with tier == 'live'",
    "holding": "demote to paper when any trigger fires",
    "promotion_back": "requires a fresh out-of-sample window that satisfies every promotion gate again",
    "triggers": [
        {"key": "drawdown_units", "threshold": -20.0, "op": "<=",
         "measures": "cumulative flat-stake units from the peak of the live ledger",
         "why": "a live strategy that has given back 20 units at flat stake is not a 2% edge"},
        {"key": "rolling_50_hit_rate", "threshold": None, "op": "<=",
         "measures": "hit rate over the most recent 50 settled bets against the promoted rate",
         "why": "a rate that has collapsed over a 50-bet window is stale, not unlucky",
         "comparator": "promoted_rate - 2 * binomial_sd(promoted_rate, 50)"},
        {"key": "clv_mean_bps", "threshold": 0.0, "op": "<=",
         "measures": "mean closing-line value in basis points over the live ledger",
         "why": "a strategy that consistently loses at the close is on the wrong side of the market, "
                "regardless of results"},
        {"key": "price_integrity_failures", "threshold": 1, "op": ">=",
         "measures": "count of live bets whose captured price failed provenance or reconciliation",
         "why": "one bad price invalidates the ledger it sits in; demote until it is rebuilt"},
        {"key": "days_since_last_pass", "threshold": 30, "op": ">=",
         "measures": "days since the strategy last cleared every promotion gate on a full re-run",
         "why": "a stale pass is not a pass"},
    ],
}

# Promotion gates for the leaderboard. Staking fields are deliberately absent.
PROMOTION = {
    "paper_to_live": [
        {"key": "n_settled_bets", "min": 200,
         "why": "below 200 settled bets a 55% rate is inside two standard errors of a coin"},
        {"key": "signal_p_value", "max": 0.05,
         "why": "the signal, not the stake, decides promotion"},
        {"key": "q_value_holm", "max": 0.10,
         "why": "the leaderboard tests many strategies; the family-wise error must be controlled"},
        {"key": "price_provenance", "equals": "pass",
         "why": "a strategy priced from unverified numbers cannot go live"},
        {"key": "clv_mean_bps", "min": 0.0,
         "why": "positive closing-line value is the only forward-looking proof of an edge"},
    ],
    "explicitly_excluded": ["staking_roi_at_relayed_close", "units_returned", "best_run", "hot_streak"],
}


def gate_status(results: dict) -> list[dict]:
    out = []
    for gid, name, desc in GATE_DEFS:
        r = results.get(gid, {"status": "blocked", "evidence": "no computation supplied"})
        out.append({"id": gid, "name": name, "definition": desc,
                    "status": r["status"], "evidence": r["evidence"]})
    return out


def promote(strategy: dict) -> dict:
    """Evaluate promotion using signal fields only. Raises if a staking field is present.

    The raise is the point: it makes 'a lucky staking run cannot mask a bad signal' a
    property of the code rather than a promise in a document.
    """
    leaked = [k for k in PROMOTION["explicitly_excluded"] if k in strategy]
    if leaked:
        raise ValueError(f"staking field(s) {leaked} reached the promotion gate")
    failures = []
    for rule in PROMOTION["paper_to_live"]:
        key = rule["key"]
        val = strategy.get(key)
        if val is None:
            failures.append(f"{key}: missing")
            continue
        if "min" in rule and not val >= rule["min"]:
            failures.append(f"{key}={val} < {rule['min']}")
        if "max" in rule and not val <= rule["max"]:
            failures.append(f"{key}={val} > {rule['max']}")
        if rule.get("equals") and val != rule["equals"]:
            failures.append(f"{key}={val} != {rule['equals']}")
    return {"promote": not failures, "failures": failures, "tier": "live" if not failures else "paper"}


def evaluate_demotion(ledger: dict) -> dict:
    """Apply the demotion triggers to a live ledger. Any firing trigger demotes."""
    fired = []
    for t in DEMOTION_GATE["triggers"]:
        key = t["key"]
        val = ledger.get(key)
        if val is None:
            fired.append({"key": key, "status": "unevaluable",
                          "why": "input missing; treated as a demotion trigger because an "
                                 "unverifiable live strategy is not a live strategy"})
            continue
        threshold = t["threshold"]
        if t.get("comparator") == "promoted_rate - 2 * binomial_sd(promoted_rate, 50)":
            from math import sqrt
            p = ledger.get("promoted_rate")
            if p is None:
                fired.append({"key": key, "status": "unevaluable", "why": "promoted_rate missing"})
                continue
            threshold = p - 2 * sqrt(p * (1 - p) / 50)
        if t["op"] == "<=" and val <= threshold:
            fired.append({"key": key, "value": val, "threshold": round(threshold, 4),
                          "status": "fired", "why": t["why"]})
        elif t["op"] == ">=" and val >= threshold:
            fired.append({"key": key, "value": val, "threshold": threshold,
                          "status": "fired", "why": t["why"]})
    return {"demote": bool(fired), "fired": fired}
