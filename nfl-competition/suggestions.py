"""The suggestions review section.

This is a decision hub, not a task list. Each proposal states the problem, the evidence
behind it from this lab's own artifacts, what it unlocks, what it costs, what it risks,
and a test that would show it worked. Nothing here is implemented by writing it down:
the decision record below starts empty on purpose and is filled by a person, not by a
build.

The ranking is deliberate. The two proposals that unlock the most are also the two that
need a rights decision, so they are ranked first and their risk is stated plainly rather
than buried.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, check_artifact, round_value, write_csv  # noqa: E402

OUT = DATA / "suggestions.json"
DECISIONS = DATA / "decision-record.json"

BACKTEST = DATA / "backtest.json"
CORRELATIONS = DATA / "correlations.json"
DEPTH = DATA / "depth.json"
PRICES = DATA / "price-store.json"
RESULTS = DATA / "results-feed.json"
LEADERBOARD = DATA / "leaderboard.json"
QUESTIONS = DATA / "questions.json"


def build():
    bt = json.loads(Path(BACKTEST).read_text(encoding="utf-8"))
    co = json.loads(Path(CORRELATIONS).read_text(encoding="utf-8"))
    dp = json.loads(Path(DEPTH).read_text(encoding="utf-8"))
    pr = json.loads(Path(PRICES).read_text(encoding="utf-8"))
    rs = json.loads(Path(RESULTS).read_text(encoding="utf-8"))
    lb = json.loads(Path(LEADERBOARD).read_text(encoding="utf-8"))
    qs = json.loads(Path(QUESTIONS).read_text(encoding="utf-8"))
    corr = {r["id"]: r for r in co["rows"]}

    suggestions = [
        {
            "id": "SG-01", "rank": 1, "priority": 5,
            "category": "Information discovery",
            "title": "Capture an executable price: opening and closing, for every market "
                     "the lab originates",
            "problem": "There is no market line anywhere in this project, so the "
                       "difference column is blank, the staking table is empty, and no "
                       "reward can be justified. Everything downstream of a price is "
                       "currently uncomputable.",
            "evidence": f"nfl.com returns 404 at /odds/ (CP-NFL-ODDS-ABSENT). The price "
                        f"store holds {pr['rows_stored']} rows for "
                        f"{pr['markets_registered']} registered markets. "
                        f"{lb['counts']['Live']} strategies are live and "
                        f"{lb['counts']['Provisional']} are provisional.",
            "unlocks": ["Return on investment", "Closing-line value", "The staking half "
                        "of the leaderboard", "Gate G06", "Every reward",
                        "Demotion triggers D04, D05 and D06"],
            "cost": "High. Needs a rights decision and a capture routine, not just code.",
            "risk": "NFL.com terms section 1.3 restricts systematic retrieval and "
                    "commercial use without written consent. Proceeding without consent "
                    "would put the whole project outside its own stated terms.",
            "acceptance_test": "At least one market in price-snapshots.csv carries both "
                               "an OPEN and a CLOSE row, verified yes, with an operator, "
                               "a pre-kickoff capture timestamp and a source URL on a "
                               "registered host; and the leaderboard staking table has at "
                               "least one row.",
            "depends_on": ["SG-12"],
        },
        {
            "id": "SG-02", "rank": 2, "priority": 5,
            "category": "Information discovery",
            "title": "Retrieve official per-game player logs",
            "problem": "The entire player-props division is blocked, and a replacement "
                       "depth cannot be turned into a value without usage data.",
            "evidence": f"{corr['C09']['n'] if corr['C09']['n'] else 0} player-prop "
                        f"correlations could be computed. "
                        f"{lb['counts']['Blocked on data']} leaderboard entries are "
                        f"blocked on this alone, and both of them sit in the player-props "
                        f"division.",
            "unlocks": ["Both player-prop strategies", "Correlation C09",
                        "Weighting a replacement by actual usage rather than by printed "
                        "rank"],
            "cost": "Medium. One page type to identify and register, then a capture pass.",
            "risk": "Same rights question as SG-01. Also a volume question: 32 clubs over "
                    "10 weeks is a large capture to do at human pace.",
            "acceptance_test": "C09 carries a value with a published n, and PP-01 and "
                               "PP-02 leave the Blocked tier with graded samples.",
            "depends_on": [],
        },
        {
            "id": "SG-03", "rank": 3, "priority": 4,
            "category": "Information discovery",
            "title": "Close the game-status gap in the injury report",
            "problem": "A replacement is only implied where the league states an absence, "
                       "and it states one on a small fraction of rows.",
            "evidence": f"{dp['coverage']['rows_with_an_official_game_status']} of "
                        f"{dp['coverage']['injury_rows']} injury rows carry a game "
                        f"status; the other "
                        f"{dp['coverage']['rows_without_an_official_game_status']} carry "
                        f"only a practice status.",
            "unlocks": ["A complete depth table", "Question Q09",
                        "Any defensive or offensive deficiency measure that is not a "
                        "floor"],
            "cost": "Low to medium. Either find the field on a page not yet read, or "
                    "record the absence as the finding.",
            "risk": "The league may simply not publish it for those players. In that case "
                    "the right answer is to publish the ceiling, which is what this lab "
                    "already does.",
            "acceptance_test": "Either 90% of injury rows carry a game status, or a "
                               "second official source states availability, or the gap is "
                               "published on the flagged page with the page that was "
                               "checked.",
            "depends_on": [],
        },
        {
            "id": "SG-04", "rank": 4, "priority": 4,
            "category": "Method",
            "title": "Reconcile the two directional records on one frozen forecast table",
            "problem": "Two desks publish a directional record for the same season and "
                       "disagree, and a reader has no way to tell which to trust.",
            "evidence": "This desk records 70-120 (0.5833), the earlier results desk "
                        "records 77-43 (0.6417). A sensitivity run shows the home "
                        "allowance is not the cause: forcing this model to two points "
                        "gives 62-120 (0.5167), which is further away, not closer.",
            "unlocks": ["Question Q18", "A single reference model for the board"],
            "cost": "Low. Both models are in the repository already.",
            "risk": "Low. The outcome is a published difference, not a forced agreement.",
            "acceptance_test": "One frozen forecast table, both models graded on it in "
                               "the same run, and the difference published with each "
                               "model's formula.",
            "depends_on": [],
        },
        {
            "id": "SG-05", "rank": 5, "priority": 4,
            "category": "Information discovery",
            "title": "Extend the results feed every week and re-run the reconciliation",
            "problem": "Sample size is the binding constraint on every skill conclusion "
                       "in this lab, and it is the one thing that only time fixes.",
            "evidence": f"{rs['games']} settled games today. Detecting a true 60% rate at "
                        f"80% power needs 153 settled selections; 55% needs 617. The "
                        f"largest strategy sample is 120.",
            "unlocks": ["Question Q03", "Question Q13", "Any eventual promotion"],
            "cost": "Low per week. One page read and one build.",
            "risk": "Low. The reconciliation aborts the build on any mismatch, so a bad "
                    "week cannot pass silently.",
            "acceptance_test": "The feed extends by the newly published week and the "
                               "reconciliation still reports 192 of 192 club fields "
                               "matching.",
            "depends_on": [],
        },
        {
            "id": "SG-06", "rank": 6, "priority": 3,
            "category": "Data hygiene",
            "title": "Record the printed as-of date on every depth chart and drop stale "
                     "charts",
            "problem": "A replacement depth is only as current as the chart it came from, "
                       "and most captured charts do not print a date.",
            "evidence": "Chicago prints a chart dated 10/31/2026, before the injury "
                        "ledger it is joined to. Denver, Philadelphia and Tampa print no "
                        "date. Philadelphia's chart is self-labelled unofficial.",
            "unlocks": ["Question Q20", "Trust in the depth table"],
            "cost": "Low.",
            "risk": "Dropping charts reduces coverage. The trade is published either way.",
            "acceptance_test": "Every captured chart carries either a printed date or an "
                               "explicit no-date flag, and no chart older than the "
                               "ledger it joins is used without a flag.",
            "depends_on": [],
        },
        {
            "id": "SG-07", "rank": 7, "priority": 3,
            "category": "Information discovery",
            "title": "Identify the unnamed standings columns from a page that names them",
            "problem": "Home, road, division and conference splits are withheld because "
                       "the rendered table does not say which column is which.",
            "evidence": "The page prints three unnamed three-part records and two unnamed "
                        "decimals. Sixteen displayed fields are withheld across the "
                        "standings pages.",
            "unlocks": ["A home and road split", "A better home-allowance estimate than "
                        "the league-wide mean", "Question Q17"],
            "cost": "Low. One read of the conference or league view.",
            "risk": "Low.",
            "acceptance_test": "HOME, ROAD, DIV and CONF are identified, and the values "
                               "reconcile with the win, loss and tie columns.",
            "depends_on": [],
        },
        {
            "id": "SG-08", "rank": 8, "priority": 3,
            "category": "Site",
            "title": "Keep the signal and staking tables on separate pages with the "
                     "one-way rule stated on both",
            "problem": "A reader who sees a return next to a hit rate will read the "
                       "return as evidence about the forecast.",
            "evidence": "The staking table currently has "
                        f"{len(lb['staking_table']['rows'])} rows and every staking "
                        "column is blank by rule.",
            "unlocks": ["Correct reading of the leaderboard"],
            "cost": "Low. Already implemented here; the suggestion is to keep it that way "
                    "when a price arrives.",
            "risk": "Low.",
            "acceptance_test": "No page shows a return, a stake or a drawdown in the "
                               "same table as a hit rate, and both tables print the rule "
                               "that staking can demote and never promote.",
            "depends_on": [],
        },
        {
            "id": "SG-09", "rank": 9, "priority": 3,
            "category": "Governance",
            "title": "Keep the decision record on the suggestions page manual",
            "problem": "A suggestion that is implemented because it was written down is "
                       "not a decision, it is an accident.",
            "evidence": f"{qs['total']} questions are open or partial; "
                       f"{len([s for s in []])} suggestions have been adopted so far.",
            "unlocks": ["A reviewable path from suggestion to change"],
            "cost": "None.",
            "risk": "None. It is the absence of an action.",
            "acceptance_test": "The record starts empty, each row offers Adopt, Defer and "
                               "Reject with a reason field, and the export contains no "
                               "choice until a person enters one.",
            "depends_on": [],
        },
        {
            "id": "SG-10", "rank": 10, "priority": 2,
            "category": "Site",
            "title": "Publish the sample-size table next to every skill claim",
            "problem": "A 61.7% record looks like an edge until it is placed next to the "
                       "number of selections needed to call it one.",
            "evidence": "153 selections for a true 60% rate, 617 for 55%, 2,682 for "
                        "52.4%. The largest sample here is 120.",
            "unlocks": ["Honest reading of every number on the site"],
            "cost": "Low.",
            "risk": "Low.",
            "acceptance_test": "Every page that prints a hit rate also prints the "
                               "selections needed to detect it at 80% power.",
            "depends_on": [],
        },
        {
            "id": "SG-11", "rank": 11, "priority": 2,
            "category": "Site",
            "title": "Keep control entries visibly separated from competitors",
            "problem": "A control that scores well will be read as a strategy.",
            "evidence": f"{lb['counts']['Control']} entries are controls. One of them, "
                        "the duplicate-leg slip, has the strongest statistics in the "
                        "whole table precisely because its legs are the same event.",
            "unlocks": ["Correct reading of the leaderboard"],
            "cost": "Low.",
            "risk": "Low.",
            "acceptance_test": "Controls are unranked, carry a Control tier, and print "
                               "what property of the test they demonstrate.",
            "depends_on": [],
        },
        {
            "id": "SG-12", "rank": 12, "priority": 2,
            "category": "Governance",
            "title": "Settle the source-rights question before building any price "
                     "capture",
            "problem": "Code written before the rights question is answered is code that "
                       "may have to be deleted.",
            "evidence": "NFL.com terms section 1.3 permits individual non-commercial "
                        "informational use and prohibits systematic retrieval to compile "
                        "a collection without written consent. No consent is evidenced.",
            "unlocks": ["SG-01", "SG-02", "Gate G10", "Any dataset release"],
            "cost": "None in code. A decision.",
            "risk": "Doing this second rather than first wastes the work in SG-01 and "
                    "SG-02.",
            "acceptance_test": "A written answer on record: consent obtained, a different "
                               "source used, or the price work formally declined.",
            "depends_on": [],
        },
    ]

    write_csv(DATA / "suggestions.csv", [{
        "id": s["id"], "rank": s["rank"], "priority": s["priority"],
        "category": s["category"], "title": s["title"], "problem": s["problem"],
        "evidence": s["evidence"], "unlocks": "; ".join(s["unlocks"]),
        "cost": s["cost"], "risk": s["risk"], "acceptance_test": s["acceptance_test"],
        "depends_on": "; ".join(s["depends_on"]), "decision": "not yet recorded",
    } for s in suggestions])

    decision_record = {
        "note": "Empty on purpose. A suggestion becomes work only when someone chooses "
                "it here. This file is not written by the build: it is the one artifact "
                "a person owns.",
        "choices_offered": ["Adopt", "Defer", "Reject"],
        "decisions": [{"id": s["id"], "title": s["title"], "choice": None,
                       "reason": None, "decided_by": None, "decided_on": None}
                      for s in suggestions],
    }
    path = Path(DECISIONS)
    if not path.exists():
        path.write_text(json.dumps(decision_record, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")

    payload = {
        "built_on": "2026-11-14",
        "purpose": "Proposals to improve decision making and to discover what is missing. "
                   "Nothing here is implemented by writing it down.",
        "ranking_rule": "Ranked by what it unlocks against what it costs and risks. The "
                        "two proposals that unlock the most both need a rights decision, "
                        "so they lead and their risk is stated rather than buried.",
        "count": len(suggestions),
        "by_category": {c: sum(1 for s in suggestions if s["category"] == c)
                        for c in sorted({s["category"] for s in suggestions})},
        "decision_record_path": "nfl-competition/data/decision-record.json",
        "decisions_recorded": 0,
        "suggestions": suggestions,
    }
    return round_value(payload, 6)


def main():
    if check_artifact(OUT, build()):
        payload = build()
        print(f"  {payload['count']} suggestions ranked; "
              f"{payload['decisions_recorded']} decisions recorded (starts blank by "
              f"design)")


if __name__ == "__main__":
    main()
