"""Validation gates: the rules a strategy must pass before it is ranked.

The gates are ordered from "could this even be tested?" to "is the result
distinguishable from luck?". A strategy that fails a gate is not rejected as
useless; it is rejected as *unproven*, and it does not receive a leaderboard
position. That distinction is the whole point of the exercise.

Gate set (each returns pass / fail / not-evaluable plus the reason):

G0  Provenance      - every input has an official source URL, or is explicitly
                      blank. No inferred numbers.
G1  Pre-registration- thresholds, universe and stopping rule declared before
                      results are seen; the declaration is hashed.
G2  Sample size     - enough settled bets for the planned test to have power.
G3  Out-of-sample   - the result holds on data not used to build the strategy.
G4  Luck test       - binomial p-value, PSR and deflated Sharpe all clear.
G5  Price realism   - evaluated at recorded market prices, vig included; no
                      mid-market or stale-price fills.
G6  Correlation     - parlay/prop-combo dependence is estimated, not assumed
                      away. Fails if legs are treated as independent without
                      measurement.
G7  Robustness      - result survives removing the best 5% of results and one
                      seed perturbation.

Status values are deliberately three-valued so that "we don't know" can never
be silently rounded up to "pass".
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Sequence

from . import skill

PASS = "pass"
FAIL = "fail"
NOT_EVALUABLE = "not_evaluable"


def _gate(gid: str, name: str, status: str, detail: str, evidence: Any = None) -> dict[str, Any]:
    return {"id": gid, "name": name, "status": status, "detail": detail, "evidence": evidence}


def g0_provenance(inputs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Every declared input must carry an official source URL."""
    if not inputs:
        return _gate("G0", "Provenance", NOT_EVALUABLE, "no inputs declared")
    missing = [i.get("name", "?") for i in inputs if not i.get("source_url")]
    if missing:
        return _gate("G0", "Provenance", FAIL, f"inputs without an official source: {missing}", {"missing": missing})
    return _gate("G0", "Provenance", PASS, f"all {len(inputs)} inputs carry a source URL",
                 {"sources": sorted({i["source_url"] for i in inputs})})


def g1_preregistration(spec: dict[str, Any]) -> dict[str, Any]:
    """Thresholds, universe and stopping rule must be declared up front."""
    required = ("thresholds", "universe", "stopping_rule", "evaluation_window")
    missing = [k for k in required if not spec.get(k)]
    if missing:
        return _gate("G1", "Pre-registration", FAIL, f"missing declarations: {missing}", {"missing": missing})
    blob = json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()
    return _gate("G1", "Pre-registration", PASS, "all declarations present",
                 {"spec_sha256": hashlib.sha256(blob).hexdigest()})


def g2_sample_size(n_settled: int, min_bets: int) -> dict[str, Any]:
    if n_settled < 0:
        return _gate("G2", "Sample size", FAIL, "negative settled count")
    if n_settled == 0:
        return _gate("G2", "Sample size", NOT_EVALUABLE, "no settled bets", {"n": 0})
    if n_settled < min_bets:
        return _gate("G2", "Sample size", FAIL, f"{n_settled} settled bets, need {min_bets}", {"n": n_settled, "required": min_bets})
    return _gate("G2", "Sample size", PASS, f"{n_settled} settled bets >= {min_bets}", {"n": n_settled, "required": min_bets})


def g3_out_of_sample(in_sample_metric: float | None, oos_metric: float | None, tolerance: float = 0.5) -> dict[str, Any]:
    """OOS result must keep at least (1-tolerance) of the in-sample edge."""
    if in_sample_metric is None or oos_metric is None:
        return _gate("G3", "Out-of-sample", NOT_EVALUABLE, "in-sample or out-of-sample metric missing")
    if in_sample_metric <= 0:
        return _gate("G3", "Out-of-sample", FAIL, "in-sample metric is not positive, nothing to confirm")
    retention = oos_metric / in_sample_metric
    status = PASS if retention >= (1 - tolerance) else FAIL
    return _gate("G3", "Out-of-sample", status, f"retained {retention:.1%} of in-sample edge",
                 {"in_sample": in_sample_metric, "out_of_sample": oos_metric, "retention": round(retention, 4), "tolerance": tolerance})


def g4_luck(wins: int, losses: int, break_even: float, returns: Sequence[float], n_trials: int) -> dict[str, Any]:
    """All three luck tests must clear; otherwise the gate cannot pass."""
    if wins + losses == 0:
        return _gate("G4", "Luck test", NOT_EVALUABLE, "no settled bets")
    binom = skill.binomial_p_value(wins, losses, break_even)
    psr = skill.probabilistic_sharpe_ratio(returns) if len(returns) >= 3 else {"ok": False, "reason": "too few returns"}
    dsr = skill.deflated_sharpe_ratio(returns, n_trials) if len(returns) >= 3 else {"ok": False, "reason": "too few returns"}
    checks = {
        "binomial_p": binom.get("p_value"),
        "psr": psr.get("psr"),
        "deflated_sharpe": dsr.get("deflated_sharpe"),
    }
    passed = (
        binom.get("p_value") is not None and binom["p_value"] < 0.05
        and psr.get("psr") is not None and psr["psr"] > 0.95
        and dsr.get("deflated_sharpe") is not None and dsr["deflated_sharpe"] > 0.95
    )
    status = PASS if passed else FAIL
    detail = "all three luck tests clear" if passed else "at least one luck test does not clear"
    return _gate("G4", "Luck test", status, detail, {"binomial": binom, "psr": psr, "deflated_sharpe": dsr, "summary": checks})


def g5_price_realism(prices: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Every evaluated bet needs a real, timestamped, executable price."""
    if not prices:
        return _gate("G5", "Price realism", NOT_EVALUABLE, "no recorded prices")
    bad = [
        p for p in prices
        if not p.get("decimal_odds") or not p.get("recorded_utc") or not p.get("book") or not p.get("source_url")
    ]
    if bad:
        return _gate("G5", "Price realism", FAIL, f"{len(bad)} of {len(prices)} prices lack book, timestamp, price or source",
                     {"failures": bad[:5]})
    return _gate("G5", "Price realism", PASS, f"{len(prices)} prices all timestamped, attributed and sourced")


def g6_correlation(legs_treated_independent: bool, measured_phi: float | None, phi_ci: Sequence[float] | None = None) -> dict[str, Any]:
    """Parlays must not assume independence without measurement."""
    if legs_treated_independent and measured_phi is None:
        return _gate("G6", "Correlation", FAIL,
                     "legs treated as independent and no dependence was measured")
    if measured_phi is None:
        return _gate("G6", "Correlation", NOT_EVALUABLE, "no dependence estimate supplied")
    crosses_zero = bool(phi_ci) and phi_ci[0] <= 0.0 <= phi_ci[1]
    if crosses_zero:
        return _gate("G6", "Correlation", NOT_EVALUABLE,
                     "measured dependence has a confidence interval spanning zero; cannot distinguish from independence",
                     {"phi": measured_phi, "ci95": phi_ci})
    return _gate("G6", "Correlation", PASS, "dependence measured with an interval excluding zero",
                 {"phi": measured_phi, "ci95": phi_ci})


def g7_robustness(returns: Sequence[float], trim_fraction: float = 0.05) -> dict[str, Any]:
    """Does the mean survive dropping the best results?"""
    n = len(returns)
    if n < 20:
        return _gate("G7", "Robustness", NOT_EVALUABLE, f"only {n} results; robustness needs at least 20")
    ordered = sorted(returns)
    k = max(1, int(round(n * trim_fraction)))
    trimmed = ordered[:-k]
    full_mean = sum(returns) / n
    trimmed_mean = sum(trimmed) / len(trimmed)
    survives = full_mean > 0 and trimmed_mean > 0
    return _gate("G7", "Robustness", PASS if survives else FAIL,
                 f"mean {full_mean:+.4f}, after dropping best {k} results {trimmed_mean:+.4f}",
                 {"n": n, "full_mean": round(full_mean, 6), "trimmed_mean": round(trimmed_mean, 6), "dropped": k})


def run_all(
    *,
    inputs: Sequence[dict[str, Any]],
    spec: dict[str, Any],
    n_settled: int,
    min_bets: int,
    in_sample_metric: float | None,
    oos_metric: float | None,
    wins: int,
    losses: int,
    break_even: float,
    returns: Sequence[float],
    n_trials: int,
    prices: Sequence[dict[str, Any]],
    legs_treated_independent: bool,
    measured_phi: float | None,
    phi_ci: Sequence[float] | None,
) -> dict[str, Any]:
    gates = [
        g0_provenance(inputs),
        g1_preregistration(spec),
        g2_sample_size(n_settled, min_bets),
        g3_out_of_sample(in_sample_metric, oos_metric),
        g4_luck(wins, losses, break_even, returns, n_trials),
        g5_price_realism(prices),
        g6_correlation(legs_treated_independent, measured_phi, phi_ci),
        g7_robustness(returns),
    ]
    statuses = [g["status"] for g in gates]
    if FAIL in statuses:
        overall = "rejected"
    elif NOT_EVALUABLE in statuses:
        overall = "unproven"
    else:
        overall = "passed"
    return {
        "gates": gates,
        "overall": overall,
        "counts": {s: statuses.count(s) for s in (PASS, FAIL, NOT_EVALUABLE)},
        "rule": "A strategy is ranked only if overall == 'passed'. 'unproven' is not a soft pass.",
    }
