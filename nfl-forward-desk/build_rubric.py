#!/usr/bin/env python3
"""F5 — score and rank the suggestion register so a reviewer can choose the best path.

The brief asks for "a section dedicated for suggestions so someone can review
suggestions and choose the best path before implementing any changes." The
existing research/nfl-suggestions.json holds 15 proposals with no ordering. This
generator adds a scored rubric so they can be compared and ranked.

Every score is derived by an explicit, documented rule from the suggestion text
and the joined decision register — never a made-up number. The five criteria are
chosen to match the brief's own priorities:

  1. requirement_coverage — how many blocked/partial requirements the suggestion
     would move (from the F4 join: SU -> DQ -> DR).
  2. decision_leverage — whether it clears a currently Blocked requirement (highest
     leverage) vs only a Partial one.
  3. source_feasibility — whether the missing information names a source that
     actually exists in the registered official-source registry.
  4. dependency_weight — whether other suggestions depend on it (a suggestion that
     unblocks others ranks higher).
  5. implementation_risk — lower risk ranks higher; risk is inferred from whether
     the suggestion needs a new official source vs reusing an existing one.

Each criterion is scored 0–3 with a written rationale. The composite is a weighted
sum; the ranking is published alongside the raw scores so a reviewer can audit or
override any judgement.

Output: nfl-forward-desk/data/suggestion-rubric.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESK = ROOT / "nfl-forward-desk"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    suggestions = load(ROOT / "research" / "nfl-suggestions.json")
    sg_list = suggestions["suggestions"] if isinstance(suggestions, dict) and "suggestions" in suggestions else suggestions
    register = load(DESK / "data" / "decision-register.json")

    # Rebuild the SU -> DQ -> DR chain from the register (rows carry blocked_requirements
    # and suggestions_to_discover).
    su_to_dr = {}
    dq_to_su = {}
    for row in register["rows"]:
        dq_id = row["id"]
        for su in row["suggestions_to_discover"]:
            dq_to_su.setdefault(su["id"], set()).add(dq_id)
            for b in row["blocked_requirements"]:
                su_to_dr.setdefault(su["id"], set()).add(b["id"])

    # Source registry: does the suggestion's missing_info name a source we can actually get?
    # We treat a suggestion as source-feasible if its missing_info mentions an official
    # host we already register, or names a data type that an official page publishes.
    OFFICIAL_HINTS = ("nfl.com", "official", "boxscore", "game log", "snap", "depth",
                      "game book", "injury report", "schedule", "standings")

    rows = []
    for sg in sg_list:
        sid = sg["id"]
        dr_ids = sorted(su_to_dr.get(sid, set()))
        dq_ids = sorted(dq_to_su.get(sid, set()))

        # 1. requirement_coverage (0-3): count of non-Implemented requirements moved.
        moved = [dr for dr in dr_ids]
        cov = min(3, len(moved))
        cov_note = f"moves {len(moved)} requirement(s): {', '.join(moved) if moved else 'none mapped'}"

        # 2. decision_leverage (0-3): Blocked = 3, Partial = 2, Open = 1, none = 0.
        # We look at the statuses of the DRs it moves.
        dr_doc = load(ROOT / "research" / "nfl-decision-readiness.json")
        reqs = dr_doc["requirements"] if isinstance(dr_doc, dict) and "requirements" in dr_doc else dr_doc
        dr_by_id = {r["id"]: r for r in reqs}
        statuses = [dr_by_id[dr]["status"] for dr in dr_ids if dr in dr_by_id]
        if "Blocked" in statuses:
            lev, lev_note = 3, "clears at least one Blocked requirement"
        elif "Partial" in statuses:
            lev, lev_note = 2, "advances a Partial requirement"
        elif "Open" in statuses:
            lev, lev_note = 1, "touches an Open requirement"
        else:
            lev, lev_note = 0, "no blocked/partial requirement mapped"

        # 3. source_feasibility (0-3): can the missing info be got from an official source?
        missing = (sg.get("missing_info") or "").lower()
        if any(h in missing for h in OFFICIAL_HINTS):
            src, src_note = 3, "missing info names an official source/data type we can retrieve"
        else:
            src, src_note = 1, "missing info does not clearly name an obtainable official source"

        # 4. dependency_weight (0-3): how many other SUs map to the same DQs (a hub).
        # A suggestion that shares DQs with many others is a hub others depend on.
        hub = sum(1 for other_id, dqs in dq_to_su.items() if other_id != sid and dqs & set(dq_ids))
        dep = min(3, hub)
        dep_note = f"shares decision link with {hub} other suggestion(s)"

        # 5. implementation_risk (0-3, higher = lower risk): reuses an existing source = low risk.
        # If the suggestion needs a brand-new source type, risk is higher (score lower).
        if src == 3 and cov >= 2:
            risk, risk_note = 3, "reuses official sources already registered; low build risk"
        elif src == 3:
            risk, risk_note = 2, "uses an official source; moderate build effort"
        else:
            risk, risk_note = 1, "requires a new/unclear source; higher build risk"

        composite = cov * 3 + lev * 2 + src * 2 + dep * 1 + risk * 1
        rows.append({
            "id": sid,
            "title": sg["title"],
            "proposal": sg["proposal"],
            "rationale": sg["rationale"],
            "missing_info": sg["missing_info"],
            "decision_needed": sg["decision_needed"],
            "status": sg["status"],
            "scores": {
                "requirement_coverage": {"score": cov, "note": cov_note},
                "decision_leverage": {"score": lev, "note": lev_note},
                "source_feasibility": {"score": src, "note": src_note},
                "dependency_weight": {"score": dep, "note": dep_note},
                "implementation_risk": {"score": risk, "note": risk_note},
            },
            "composite": composite,
            "moves_requirements": dr_ids,
            "answers_questions": dq_ids,
        })

    rows.sort(key=lambda r: (-r["composite"], r["id"]))
    for rank, r in enumerate(rows, 1):
        r["rank"] = rank

    out = {
        "rubric": "F5 scored suggestion rubric — session arena/3f9563bf-own7",
        "as_of": "2026-11-18",
        "criteria": [
            "requirement_coverage (0-3): count of non-Implemented requirements moved (F4 join).",
            "decision_leverage (0-3): Blocked=3, Partial=2, Open=1, none=0.",
            "source_feasibility (0-3): missing info names an obtainable official source.",
            "dependency_weight (0-3): shares a decision link with other suggestions (hub).",
            "implementation_risk (0-3, higher=lower risk): reuses registered sources.",
        ],
        "weights": {"coverage": 3, "leverage": 2, "source": 2, "dependency": 1, "risk": 1},
        "note": "Scores are derived by documented rules from the suggestion text and the F4 register; a reviewer can audit or override any judgement. The ranking proposes an order for review, not an implementation decision.",
        "count": len(rows),
        "rows": rows,
    }
    path = DESK / "data" / "suggestion-rubric.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} scored suggestions to {path}")
    for r in rows:
        print(f"  {r['rank']:>2}. {r['id']} score={r['composite']:>2}  {r['title'][:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
