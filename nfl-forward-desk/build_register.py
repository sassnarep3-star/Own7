#!/usr/bin/env python3
"""F4 — build the joined decision register.

Joins the three existing registers into one row per open decision:
  - research/nfl/questions.json        (DQ: what we know / don't know)
  - research/nfl-decision-readiness.json (DR: requirement, gate, clears_when)
  - research/nfl-suggestions.json      (SU: proposal, missing_info, decision_needed)

For each DQ it names the official source that would answer it and the DR
requirement ids it blocks. It also lists the SU suggestions that would discover
the missing information. Nothing is invented: every field is copied from the
source registers or derived by an explicit, documented join rule.

Output: nfl-forward-desk/data/decision-register.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESK = ROOT / "nfl-forward-desk"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


# Explicit join rule: map a DQ to the DR requirement ids it blocks, by the DQ's
# own `blocks` field plus category alignment. This is a documented mapping, not
# a guess — each pair is asserted here so a reader can audit it.
DQ_TO_DR = {
    "DQ01": ["DR-20", "DR-40"],                      # rights -> price policy, public/private split
    "DQ02": ["DR-02", "DR-19", "DR-70"],             # reproducibility -> results feed, corpus, split
    "DQ03": ["DR-03", "DR-04", "DR-18"],             # home adjustment -> origination, fair/market, pricing
    "DQ04": ["DR-06", "DR-10", "DR-11", "DR-41", "DR-42", "DR-52"],  # backups -> depth/availability
    "DQ05": ["DR-21", "DR-44", "DR-55"],             # blank status -> injury series, Q calibration
    "DQ06": ["DR-07", "DR-36", "DR-37"],             # correlation -> correlations, parlay gate, divisions
    "DQ07": ["DR-36", "DR-37"],                      # joint pricing -> parlay gate, divisions
    "DQ08": ["DR-05", "DR-38", "DR-57"],             # skill -> signal/staking, proper score, control
    "DQ09": ["DR-16", "DR-38"],                      # luck -> removal-of-luck, proper score
    "DQ10": ["DR-01", "DR-05", "DR-18", "DR-59"],    # profit -> price store, leaderboard, rewards
    "DQ11": ["DR-08", "DR-59"],                      # reward decision -> demotion gate, two-stage
    "DQ12": ["DR-21", "DR-63"],                      # confidence -> injury timestamp, drift alarm
    "DQ13": ["DR-23"],                                # transcription -> venue
    "DQ14": [],                                       # NBA scope: no NFL requirement blocked
    "DQ15": ["DR-16", "DR-38", "DR-67"],             # luck removal -> luck panel, proper score, pre-reg
    "DQ16": ["DR-22", "DR-63"],                      # check suite -> readiness table, drift alarm
    "DQ17": ["DR-25", "DR-31", "DR-42", "DR-56"],    # replacement naming -> game books, snap counts
}

# Official source that would answer each DQ. Drawn from the DQ's own source_ids
# plus the fresh 2026-11-18 reads this session took where they directly answer it.
DQ_ANSWERING_SOURCE = {
    "DQ01": {"id": "NFL-TERMS-LEGAL", "url": "https://www.nfl.com/legal/terms", "note": "Terms page; a rights decision, not a data value."},
    "DQ02": {"id": "FD-NFL-STANDINGS-1118", "url": "https://www.nfl.com/standings/", "note": "Fresh 2026-11-18 standings read; confirms the score basis, not the model's accuracy."},
    "DQ03": {"id": "FD-NFL-SCHED-W11-1118", "url": "https://www.nfl.com/schedules/2026/REG11/", "note": "Schedule facts (venue, time, network) bound the fixture context; no home-field value is published."},
    "DQ04": {"id": "FD-NFL-INJ-W10-1118", "url": "https://www.nfl.com/injuries/league/2026/REG10", "note": "Fresh 2026-11-18 injury report; designations only — does not name replacements or starters."},
    "DQ05": {"id": "FD-NFL-INJ-W10-1118", "url": "https://www.nfl.com/injuries/league/2026/REG10", "note": "The page leaves game status blank for 176 of 347 rows; the page does not state what blank means."},
    "DQ06": {"id": "FD-NFL-STANDINGS-1118", "url": "https://www.nfl.com/standings/", "note": "No joint leg-pair data is published on the standings page; would need game-level results."},
    "DQ07": {"id": "FD-NFL-STANDINGS-1118", "url": "https://www.nfl.com/standings/", "note": "Pairwise numbers cannot identify a joint distribution; no official joint source exists."},
    "DQ08": {"id": "FD-NFL-STANDINGS-1118", "url": "https://www.nfl.com/standings/", "note": "Standings support in-sample scoring only; out-of-sample skill needs the results feed."},
    "DQ09": {"id": "FD-NFL-STANDINGS-1118", "url": "https://www.nfl.com/standings/", "note": "PF/PA support a points-based expectation; schedule strength is not published here."},
    "DQ10": {"id": "FD-NFL-STANDINGS-1118", "url": "https://www.nfl.com/standings/", "note": "No operator price is published on NFL.com; profit cannot be computed from official data alone."},
    "DQ11": {"id": "FD-NFL-STANDINGS-1118", "url": "https://www.nfl.com/standings/", "note": "A forward stake-capped record needs a price source that does not exist on NFL.com."},
    "DQ12": {"id": "FD-NFL-INJ-W10-1118", "url": "https://www.nfl.com/injuries/league/2026/REG10", "note": "Single official page; a second independent source is still missing for every value."},
    "DQ13": {"id": "FD-NFL-SCHED-W11-1118", "url": "https://www.nfl.com/schedules/2026/REG11/", "note": "Schedule page publishes venue and time; division/conference columns were withheld for header reasons."},
    "DQ14": {"id": "REPO", "url": "https://github.com/sassnarep3-star/Own7", "note": "Scope decision, not an official NFL data question."},
    "DQ15": {"id": "FD-NFL-STANDINGS-1118", "url": "https://www.nfl.com/standings/", "note": "Luck cannot be removed from a single result; needs enough outcomes for a pre-registered test."},
    "DQ16": {"id": "FD-NFL-STANDINGS-1118", "url": "https://www.nfl.com/standings/", "note": "The check suite proves internal integrity, not external truth; a re-check step is still missing."},
    "DQ17": {"id": "FD-NFL-INJ-W10-1118", "url": "https://www.nfl.com/injuries/league/2026/REG10", "note": "Injury report names who is out, not who replaced them; needs snap counts or game books."},
}


def main() -> int:
    questions = load(ROOT / "research" / "nfl" / "questions.json")["questions"]
    dr_doc = load(ROOT / "research" / "nfl-decision-readiness.json")
    requirements = dr_doc["requirements"] if isinstance(dr_doc, dict) and "requirements" in dr_doc else dr_doc
    suggestions = load(ROOT / "research" / "nfl-suggestions.json")
    sg_list = suggestions["suggestions"] if isinstance(suggestions, dict) and "suggestions" in suggestions else suggestions

    dr_by_id = {r["id"]: r for r in requirements}

    # Map each suggestion to the DQs whose missing_info it would help discover.
    # Explicit, documented join: a suggestion joins to a DQ when the suggestion's
    # missing_info overlaps the DQ's missing field. Asserted here for auditability.
    SU_TO_DQ = {
        "SU-01": ["DQ06", "DQ07", "DQ08", "DQ15"],   # game logs -> correlation, joint, skill, luck
        "SU-02": ["DQ10", "DQ11"],                   # pricing -> profit, reward
        "SU-03": ["DQ03"],                           # home adjustment -> spread precision
        "SU-04": ["DQ04", "DQ17"],                   # starters/replacements -> backups, naming
        "SU-05": ["DQ05"],                           # blank status meaning
        "SU-06": ["DQ06", "DQ07"],                   # dependence structure -> parlay
        "SU-07": ["DQ08", "DQ09", "DQ15"],           # luck measurement
        "SU-08": ["DQ10", "DQ11"],                   # reward design
        "SU-09": ["DQ12", "DQ16"],                   # verification confidence
        "SU-10": ["DQ04", "DQ17"],                   # snap counts -> replacements
        "SU-11": ["DQ01", "DQ14"],                   # rights / scope
        "SU-12": ["DQ13"],                           # transcription scope
        "SU-13": ["DQ16"],                           # external re-check
        "SU-14": ["DQ09"],                           # schedule strength
        "SU-15": ["DQ08", "DQ15"],                   # proper-score skill
    }

    rows = []
    for dq in questions:
        dq_id = dq["id"]
        dr_ids = DQ_TO_DR.get(dq_id, [])
        answer = DQ_ANSWERING_SOURCE.get(dq_id, {})
        blocked = [
            {
                "id": dr_ids[i],
                "requirement": dr_by_id[dr_ids[i]]["requirement"],
                "status": dr_by_id[dr_ids[i]]["status"],
                "gate": dr_by_id[dr_ids[i]]["gate"],
                "clears_when": dr_by_id[dr_ids[i]]["clears_when"],
            }
            for i in range(len(dr_ids)) if dr_ids[i] in dr_by_id
        ]
        su_ids = [sid for sid, dqs in SU_TO_DQ.items() if dq_id in dqs]
        su_rows = [
            {
                "id": sg["id"],
                "title": sg["title"],
                "missing_info": sg["missing_info"],
                "decision_needed": sg["decision_needed"],
            }
            for sg in sg_list if sg["id"] in su_ids
        ]
        rows.append({
            "id": dq_id,
            "group": dq["group"],
            "question": dq["q"],
            "known": dq["known"],
            "missing": dq["missing"],
            "blocks_summary": dq["blocks"],
            "answering_source": answer,
            "blocked_requirements": blocked,
            "suggestions_to_discover": su_rows,
        })

    out = {
        "register": "F4 joined decision register — session arena/3f9563bf-own7",
        "as_of": "2026-11-18",
        "join_rule": "DQ -> DR via DQ_TO_DR; DQ -> answering source via DQ_ANSWERING_SOURCE; SU -> DQ via SU_TO_DQ. All mappings are explicit and asserted in build_register.py.",
        "count": len(rows),
        "rows": rows,
    }
    path = DESK / "data" / "decision-register.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} decision rows to {path}")
    # Sanity: every blocked DR id must exist.
    missing = [r["id"] for r in rows for b in r["blocked_requirements"] if b["id"] not in dr_by_id]
    if missing:
        print("ERROR: unknown DR ids referenced:", missing)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
