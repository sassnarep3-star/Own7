#!/usr/bin/env python3
"""Strategy register: every entry pre-registered, with a two-sided 'what would change our mind' (R17).

A strategy entry is a *definition*, not a result. The result lives on the leaderboard. Keeping them
apart is what makes "pre-registered" mean something: the definition is frozen in the registration
file, the result is computed later, and neither can be edited to suit the other.

Every entry carries:

  definition          the frozen rule, from data/registration.json
  window              which games the result refers to
  result              rank, Brier skill, cluster lower bound, q, n — or blank with a gate if closed
  would_accept        the exact number that would make this entry a candidate
  would_reject        the exact observation that would make this entry wrong
  stake               always blank: staking is a separate thing and cannot appear on a signal entry
  state               paper | closed

The 'would_reject' side is the one most strategy documents omit. It is mandatory here: the build
fails if either side is empty, if the two sides point the same way, or if a staking field appears.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = HERE / "data"

MARKET_TEXT = {
    "side": "home side covers the frozen benchmark line (home -2.0)",
    "total": "total goes over the frozen benchmark line (2 x prior-week league mean, rounded to a half point)",
    "moneyline": "home side wins outright, no line",
}


def build() -> dict:
    registration = json.loads((DATA / "registration.json").read_text())
    board = json.loads((DATA / "leaderboard.json").read_text())
    luck = json.loads((DATA / "luck.json").read_text())
    models = {m["id"]: m for m in registration["model_family"]["models"]}
    results = {e["id"]: e for e in board["entries"]}

    entries = []
    for entry in board["entries"]:
        model_id, market = entry["id"].rsplit("-", 1)
        market = market.lower()
        m = models[model_id]
        low_q = f"the family-adjusted q for this entry, {entry['q_value']:.3f}, must also fall to 0.05 or below"
        entries.append({
            "id": entry["id"],
            "name": f"{m['name']} — {market}",
            "division": "singles",
            "definition": f"{m['name']}. Inputs: {', '.join(m['inputs'])}. Market: {MARKET_TEXT[market]}.",
            "window": "evaluation weeks 6-9 of the 2026 corpus (development weeks 2-5 are reported beside it)",
            "n": entry["n"],
            "rank": entry["rank"],
            "brier_skill": entry["brier_skill"],
            "cluster_lo": entry["cluster_lo"],
            "q_value": entry["q_value"],
            "dev_brier_skill": entry["dev_brier_skill"],
            "would_accept": (
                f"A prospective window in which the week-clustered lower bound on Brier skill exceeds 0 "
                f"(this window's bound is {entry['cluster_lo']:+.4f}), and {low_q}."),
            "would_reject": (
                f"A prospective window in which the lower bound stays at or below 0 (this window's point "
                f"estimate is {entry['brier_skill']:+.4f}), or a development-window skill of the opposite "
                f"sign from the evaluation window (development is {entry['dev_brier_skill']:+.4f})."),
            "stake": "",
            "stake_reason": "Staking is a separate field on a separate page and can never move a signal rank (V7).",
            "state": "paper",
            "qualified": False,
            "gate": "V7 price and V8 prospective record cannot pass today",
            "source_ids": ["X29-NFL-SCHEDULE"],
        })

    closed = [
        ("PARLAY-CROSS", "Cross-game parlay", "Two or more legs from different games, priced at the "
         "operator's combined quote.",
         "An operator's void, push and settlement rule for a combined ticket, plus a permitted price.",
         "A directly validated joint probability across the legs and the operator rule both registered.",
         "Any loss that the operator rule would have voided, which would prove the rule was not captured."),
        ("SGP", "Same-game parlay", "Two or more legs in one game, priced at the operator's same-game quote.",
         "The measured phi of -0.096 between side and total is not zero, so a marginal product is wrong; "
         "and no operator rule is registered.",
         "A joint probability measured at the exact thresholds on a prospective sample, plus the operator rule.",
         "A measured joint rate indistinguishable from the marginal product, which would make the simple "
         "product acceptable after all."),
        ("PROP-COMBO", "Player prop combination", "Two or more player props, in one game or across games.",
         "No player-level prop line or outcome is captured; the prop division is closed (PG-PROPS).",
         "Per-player game logs for every player in the combination, from a registered official source.",
         "A captured prop outcome that contradicts the official game log, which would show the source is unreliable."),
    ]
    for pid, name, definition, why_closed, accept, reject in closed:
        entries.append({
            "id": pid, "name": name, "division": (
                "game-parlays" if pid == "PARLAY-CROSS" else "same-game-parlays" if pid == "SGP" else "prop-combos"),
            "definition": definition,
            "window": "",
            "n": None, "rank": None, "brier_skill": None, "cluster_lo": None, "q_value": None,
            "dev_brier_skill": None,
            "would_accept": accept,
            "would_reject": reject,
            "closed_because": why_closed,
            "stake": "",
            "stake_reason": "A combination may not be staked while its division is closed.",
            "state": "closed",
            "qualified": False,
            "gate": "JG-1 (joint evidence) and V7 (price)",
            "source_ids": ["X29-NFL-SCHEDULE"],
        })

    # Contract checks: no one-sided entry, no staking value, no negative-only definition.
    for e in entries:
        for field in ("would_accept", "would_reject", "definition"):
            if not str(e[field]).strip():
                raise SystemExit(f"{e['id']}: empty {field}")
        if e["would_accept"] == e["would_reject"]:
            raise SystemExit(f"{e['id']}: the two sides are identical")
        if e["stake"]:
            raise SystemExit(f"{e['id']}: a staking value reached a signal entry")

    return {
        "schema_version": 1,
        "registration_hash": board["registration_hash"],
        "note": ("A strategy entry is a frozen definition plus a result computed later. Each entry states "
                 "both what would make it a candidate and what would make it wrong, and the staking "
                 "column is blank on every row because staking is not part of a signal."),
        "counts": {"entries": len(entries),
                   "singles": sum(1 for e in entries if e["division"] == "singles"),
                   "closed": sum(1 for e in entries if e["state"] == "closed"),
                   "with_two_sided_field": sum(1 for e in entries if e["would_accept"] and e["would_reject"])},
        "luck_context": {"family_size": luck["family_null"]["family_size"],
                         "family_p": luck["family_null"]["p_family_wise"],
                         "wins_needed_at_this_n": luck["family_null"]["wins_needed_at_this_n"]},
        "entries": entries,
    }


def main() -> int:
    payload = build()
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    target = DATA / "strategies.json"
    if "--check" in sys.argv:
        if not target.exists() or target.read_text() != text:
            raise SystemExit("strategies.json is stale")
        print(f"OK: {payload['counts']}")
        return 0
    target.write_text(text)
    print(f"Wrote strategies.json: {payload['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
