"""Fail-closed eligibility, not a claim that statistical evidence exists."""
from __future__ import annotations

import math
from urllib.parse import urlparse

GATE_IDS = tuple(f"G{i:02d}" for i in range(1, 11))


def eligible(entry: dict) -> bool:
    """Structural enforcement. Scientific review must generate the evidence first.

    Every pass needs a nonempty artifact URL. Unknown, missing, partial, failed,
    blocked or not-run gates cannot be silently promoted. Singles alone may mark
    the joint-dependence gate G05 not applicable. No current entry is eligible.
    """
    evidence = entry.get("gate_evidence", {})
    if set(evidence) != set(GATE_IDS):
        return False
    for gate_id in GATE_IDS:
        row = evidence[gate_id]
        not_applicable = (gate_id == "G05" and entry.get("category") == "Single bets"
                          and row.get("status") == "not applicable")
        if row.get("status") != "pass" and not not_applicable:
            return False
        uri = urlparse(row.get("artifact_url", ""))
        if uri.scheme != "https" or not uri.netloc:
            return False
    return True


def rank_entries(entries: list[dict]) -> list[dict]:
    """Separate categories; common window/exposure policy required for comparison."""
    eligible_entries = [e for e in entries if eligible(e)]
    groups = {}
    for entry in eligible_entries:
        key = (entry["category"], entry.get("test_window_id"), entry.get("stake_policy_id"))
        if not all(key):
            raise ValueError("Comparable test window and exposure policy required")
        for metric in ("roi_lcb95", "log_loss"):
            value = entry.get(metric)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("Verified finite ranking metrics required")
        if entry["roi_lcb95"] <= 0:
            raise ValueError("Positive lower-bound return required")
        if not entry.get("frozen_at") or not entry.get("strategy_id"):
            raise ValueError("Frozen submission identity required")
        groups.setdefault(key, []).append(entry)
    result = []
    for key, members in sorted(groups.items()):
        members.sort(key=lambda e: (-e["roi_lcb95"], e["log_loss"], e["frozen_at"], e["strategy_id"]))
        for place, member in enumerate(members, 1):
            result.append({**member, "rank": place,
                           "merit_points": {1: 3, 2: 2, 3: 1}.get(place, 0),
                           "cash_reward": None})
    return result
