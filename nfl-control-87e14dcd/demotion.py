"""Fail-closed live-to-paper demotion gate.

Every numerical threshold comes from the repository's NFL project protocol. These are
project design choices, not official NFL standards. Forecast-signal evidence, market
returns and exposure controls are independent checks. Realized stake ROI cannot repair a
failed signal gate.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def load_json(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def project_policy() -> dict:
    competition = load_json("research/nfl-protocol.json")["competition"]
    return {
        "minimum_settled_selections": competition["min_settled_selections"],
        "minimum_distinct_games": competition["min_distinct_games"],
        "minimum_distinct_dates": competition["min_distinct_dates"],
        "minimum_shadow_games": competition["shadow_min_games"],
        "minimum_shadow_calendar_days": competition["shadow_min_calendar_days"],
        "maximum_units_per_game": competition["max_units_per_game"],
        "maximum_units_per_day": competition["max_units_per_day"],
        "maximum_drawdown_units": competition["max_drawdown_units"],
        "familywise_alpha": competition["familywise_alpha"],
        "signal_skill_lower_95_must_exceed": 0.0,
        "net_return_lower_95_must_exceed": 0.0,
        "notes": (
            "500 settled selections, 200 distinct games, 60 dates, 200 prospective shadow games, "
            "60 prospective shadow days and exposure caps are OWN7 project policy. Signal quality "
            "is evaluated independently of staking returns; a positive stake run cannot override a failed signal gate."
        ),
    }


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _strict_true(evidence: dict, field: str, name: str, reasons: list[dict]) -> bool:
    passed = evidence.get(field) is True
    if not passed:
        reasons.append({"gate": name, "reason": f"{field} is missing or not true; fail closed."})
    return passed


def evaluate_demotion(current_mode: str, evidence: dict, policy: dict | None = None) -> dict:
    """Evaluate a live strategy and return a demotion decision.

    ``stake_roi`` is intentionally not read. It is neither a signal score nor an input to
    signal eligibility. The lower confidence bound on net return after costs is a separate
    economics gate; stake caps/drawdown are separate risk controls.
    """
    if current_mode not in {"paper", "live"}:
        raise ValueError("current_mode must be 'paper' or 'live'")
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a mapping")
    policy = policy or project_policy()
    if current_mode == "paper":
        return {
            "from_mode": "paper",
            "to_mode": "paper",
            "decision": "not_applicable",
            "demoted": False,
            "reasons": ["Already paper/research-only; there is no live state to demote."],
            "operational_gate_pass": False,
            "signal_gate_pass": False,
            "economics_gate_pass": False,
            "risk_gate_pass": False,
            "stake_roi_used_for_signal": False,
        }

    reasons: list[dict] = []
    operational_fields = (
        ("rights_authorized", "source rights"),
        ("price_source_authorized", "price-source authorization"),
        ("source_integrity_ok", "source provenance/integrity"),
        ("quote_fresh", "quote freshness"),
        ("settlement_contract_match", "market/settlement contract"),
        ("model_hash_matches", "frozen model and data hashes"),
        ("all_required_gates_pass", "all required promotion gates"),
        ("evaluation_window_frozen", "prospective evaluation window"),
        ("attempt_registry_complete", "all attempted strategies registered for multiplicity control"),
        ("risk_telemetry_complete", "risk telemetry"),
    )
    operational_passes = [
        _strict_true(evidence, field, label, reasons)
        for field, label in operational_fields
    ]

    sample_requirements = (
        ("settled_selections", "minimum_settled_selections", "settled selections"),
        ("distinct_games", "minimum_distinct_games", "distinct games"),
        ("distinct_dates", "minimum_distinct_dates", "distinct dates"),
        ("shadow_games", "minimum_shadow_games", "prospective shadow games"),
        ("shadow_calendar_days", "minimum_shadow_calendar_days", "prospective shadow days"),
    )
    sample_passes = []
    for field, threshold, label in sample_requirements:
        observed = _number(evidence.get(field))
        required = _number(policy.get(threshold))
        passed = observed is not None and required is not None and observed >= required
        sample_passes.append(passed)
        if not passed:
            reasons.append({
                "gate": "sample maturity",
                "reason": (f"{label} is missing or below the project floor "
                           f"({observed if observed is not None else 'blank'} / "
                           f"{required if required is not None else 'blank'})."),
            })

    signal_lcb = _number(evidence.get("signal_skill_lower_95"))
    signal_lcb_pass = signal_lcb is not None and signal_lcb > float(policy["signal_skill_lower_95_must_exceed"])
    adjusted_p = _number(evidence.get("familywise_adjusted_p"))
    multiplicity_pass = adjusted_p is not None and adjusted_p <= float(policy["familywise_alpha"])
    signal_gate_pass = all(sample_passes) and signal_lcb_pass and multiplicity_pass
    if signal_lcb is None:
        reasons.append({"gate": "signal skill", "reason": "95% lower bound for signal skill versus the frozen baseline is blank."})
    elif not signal_lcb_pass:
        reasons.append({"gate": "signal skill", "reason": "95% lower bound for signal skill versus the frozen baseline is not above zero."})
    if adjusted_p is None:
        reasons.append({"gate": "signal multiplicity", "reason": "Familywise-adjusted p-value is blank."})
    elif not multiplicity_pass:
        reasons.append({"gate": "signal multiplicity", "reason": f"Familywise-adjusted p-value exceeds alpha={policy['familywise_alpha']}."})

    return_lcb = _number(evidence.get("net_return_lower_95"))
    economics_gate_pass = return_lcb is not None and return_lcb > float(policy["net_return_lower_95_must_exceed"])
    if return_lcb is None:
        reasons.append({"gate": "economics", "reason": "Net-return lower 95% bound after costs is blank; authorized prices and matched settlements are required."})
    elif not economics_gate_pass:
        reasons.append({"gate": "economics", "reason": "Net-return lower 95% bound after costs is not above zero."})

    exposure_fields = (
        ("max_units_per_game_observed", "maximum_units_per_game", "units per game"),
        ("max_units_per_day_observed", "maximum_units_per_day", "units per day"),
        ("drawdown_units_observed", "maximum_drawdown_units", "drawdown units"),
    )
    risk_passes = []
    for observed_field, limit_field, label in exposure_fields:
        observed = _number(evidence.get(observed_field))
        limit = _number(policy.get(limit_field))
        passed = observed is not None and limit is not None and observed <= limit
        risk_passes.append(passed)
        if not passed:
            reasons.append({
                "gate": "risk limits",
                "reason": (f"Observed {label} is missing or exceeds the project cap "
                           f"({observed if observed is not None else 'blank'} / "
                           f"{limit if limit is not None else 'blank'})."),
            })

    operational_gate_pass = all(operational_passes) and all(sample_passes)
    risk_gate_pass = all(risk_passes)
    demote = not (operational_gate_pass and signal_gate_pass and economics_gate_pass and risk_gate_pass)
    return {
        "from_mode": "live",
        "to_mode": "paper" if demote else "live",
        "decision": "demote_to_paper" if demote else "remain_live",
        "demoted": demote,
        "reasons": reasons,
        "operational_gate_pass": operational_gate_pass,
        "signal_gate_pass": signal_gate_pass,
        "economics_gate_pass": economics_gate_pass,
        "risk_gate_pass": risk_gate_pass,
        "stake_roi_used_for_signal": False,
        "signal_inputs": {
            "settled_selections": evidence.get("settled_selections"),
            "distinct_games": evidence.get("distinct_games"),
            "distinct_dates": evidence.get("distinct_dates"),
            "shadow_games": evidence.get("shadow_games"),
            "shadow_calendar_days": evidence.get("shadow_calendar_days"),
            "signal_skill_lower_95": evidence.get("signal_skill_lower_95"),
            "familywise_adjusted_p": evidence.get("familywise_adjusted_p"),
            "attempt_registry_complete": evidence.get("attempt_registry_complete"),
        },
        "economics_inputs": {"net_return_lower_95": evidence.get("net_return_lower_95")},
        "risk_inputs": {
            field: evidence.get(field)
            for field, _, _ in exposure_fields
        },
    }


def current_status(price_store: dict) -> dict:
    """Describe repository state and a fail-closed counterfactual; claim no real wager."""
    protocol = load_json("research/nfl-protocol.json")
    source_rights = protocol.get("source_rights", {})
    competition = protocol.get("competition", {})
    evidence = {
        "rights_authorized": source_rights.get("nfl_gambling_use_authorized") is True,
        "price_source_authorized": bool(price_store["source_status"]["authorized_price_source_ids"]),
        "source_integrity_ok": False,
        "quote_fresh": False,
        "settlement_contract_match": False,
        "model_hash_matches": False,
        # No separate live-promotion gate record exists; do not infer it from a different results pipeline.
        "all_required_gates_pass": False,
        "evaluation_window_frozen": False,
        "attempt_registry_complete": False,
        "risk_telemetry_complete": False,
        # Historical retrospective grades are not a prospective shadow ledger.
        "settled_selections": 0,
        "distinct_games": 0,
        "distinct_dates": 0,
        "shadow_games": 0,
        "shadow_calendar_days": 0,
        "signal_skill_lower_95": None,
        "familywise_adjusted_p": None,
        "net_return_lower_95": None,
        "max_units_per_game_observed": None,
        "max_units_per_day_observed": None,
        "drawdown_units_observed": None,
        # This field is intentionally ignored by evaluate_demotion.
        "stake_roi": None,
    }
    hypothetical = evaluate_demotion("live", evidence)
    return {
        "schema_version": 1,
        "checked_on": "2026-11-14",
        "actual_project_state": {
            "mode": protocol.get("mode"),
            "live_strategy_records": 0,
            "cash_payments_enabled": competition.get("cash_payments_enabled"),
            "demotion_event_executed": False,
            "statement_limit": "Repository configuration only; no sportsbook account or external live deployment was inspected.",
        },
        "counterfactual_live_check": hypothetical,
        "decision": "No live strategy exists in this project state; no actual demotion event occurred. If one were marked live under current known evidence, this gate returns it to paper.",
        "policy": project_policy(),
        "source_ids": ["X87-NFL-TERMS-1414", "X87-NFL-ODDS-1414", "REPO"],
    }
