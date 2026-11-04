"""Fail-closed eligibility, not a claim that statistical evidence exists."""
from __future__ import annotations

from datetime import datetime
import math
from urllib.parse import urlparse

GATE_IDS = tuple(f"G{i:02d}" for i in range(1, 11))
CATEGORIES = ("Single bets", "Parlays", "Player props / combos")


def eligible(entry: dict) -> bool:
    """Structural evidence contract; it does not independently certify science/rights."""
    if not isinstance(entry, dict) or entry.get("category") not in CATEGORIES:
        return False
    evidence = entry.get("gate_evidence", {})
    if not isinstance(evidence, dict) or set(evidence) != set(GATE_IDS):
        return False
    for gate_id in GATE_IDS:
        row = evidence[gate_id]
        if not isinstance(row, dict):
            return False
        not_applicable = (gate_id == "G05" and entry.get("category") == "Single bets"
                          and row.get("status") == "not applicable")
        if row.get("status") != "pass" and not not_applicable:
            return False
        value = row.get("artifact_url")
        if not isinstance(value, str):
            return False
        uri = urlparse(value)
        if uri.scheme != "https" or not uri.netloc:
            return False
    return True


def rank_entries(entries: list[dict]) -> list[dict]:
    """Separate categories; reject different windows, exposures or event universes."""
    qualified = [e for e in entries if eligible(e)]
    groups, identities = {}, set()
    for entry in qualified:
        contract = tuple(entry.get(k) for k in ("test_window_id", "stake_policy_id", "offer_universe_id", "evaluation_event_set_hash"))
        if any(not isinstance(v, str) or not v.strip() for v in contract):
            raise ValueError("Common window, exposure, offer universe and scored event set required")
        for metric in ("roi_lcb95", "log_loss"):
            value = entry.get(metric)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("Verified finite ranking metrics required")
        if entry["roi_lcb95"] <= 0 or entry["log_loss"] < 0:
            raise ValueError("Positive lower-bound return and valid log loss required")
        identity = entry.get("strategy_id")
        if not isinstance(identity, str) or not identity.strip() or identity in identities:
            raise ValueError("Unique frozen strategy identity required")
        identities.add(identity)
        try:
            frozen = datetime.fromisoformat(entry["frozen_at"].replace("Z", "+00:00"))
            if frozen.tzinfo is None:
                raise ValueError("Timezone required")
        except (KeyError, AttributeError, TypeError, ValueError) as exc:
            raise ValueError("Valid timezone-aware frozen timestamp required") from exc
        group = groups.setdefault(entry["category"], {"contract": contract, "members": []})
        if group["contract"] != contract:
            raise ValueError("Incomparable entries within a competition category")
        group["members"].append((entry, frozen))
    result = []
    for category, group in sorted(groups.items()):
        members = sorted(group["members"], key=lambda pair: (-pair[0]["roi_lcb95"], pair[0]["log_loss"], pair[1], pair[0]["strategy_id"]))
        for place, (member, _) in enumerate(members, 1):
            result.append({**member, "rank": place,
                           "merit_points": {1: 3, 2: 2, 3: 1}.get(place, 0),
                           "cash_reward": None})
    return result
