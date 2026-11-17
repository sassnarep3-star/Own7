#!/usr/bin/env python3
"""Questions that must be answered before a decision, and the flags (D9).

Each question is split into four columns, because "we do not know" is not one thing:

  held      what this repository actually has, with the number and the page it is on
  missing   what it does not have, named precisely enough to go and get
  blocks    the decision that cannot be taken without it
  closes    the observable event that would end the question

A question is never marked answered on the strength of a document existing. `answered` is set only
where a number on file settles it, and the number is quoted in the `held` cell.

Outputs: data/questions.json, data/flags.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = HERE / "data"

# (id, group, question, held, missing, blocks, closes, answered, source_ids)
QUESTIONS = [
    ("Q01", "Market price",
     "May any market number be published at all?",
     "NFL.com section 1.3 permits individual non-commercial informational use and prohibits systematic retrieval without written consent. No odds publisher is registered.",
     "A written permission, or a price source whose terms permit republication of the number.",
     "Every market column, every residual against the market, every ROI and CLV claim, every reward.",
     "A licence or a permitted source is recorded in research/sources.json with its terms quoted.",
     False, ["RD-NFL-TERMS"]),
    ("Q02", "Market price",
     "Is there a source that prints an opening and a closing number for NFL games?",
     "The repository's own price desks record closing observations from a secondary publisher; this desk registers none.",
     "One publisher that prints both an opening and a closing number with timestamps and that permits the use.",
     "R01 and R18: an opening/closing store and a residual against the market.",
     "A registered source whose page prints both numbers for the same game.",
     False, ["RD-NFL-TERMS"]),
    ("Q03", "Who played",
     "Who actually started, as opposed to who was expected to start?",
     "3 dated announced-starter statements (Seattle, Cleveland, Arizona) and 6 club depth charts, both read 2026-11-17.",
     "An official participation record: an inactive list, a Game Book or a snap count. 0 of 136 games are covered.",
     "R10 (the availability graph), R25, R123, R124 and the cross-side mismatch matrix.",
     "One Game Book or inactive list per captured game, joined to the expected starter.",
     False, ["RD-NFL-INJ-W10", "RD-NFL-LOCK"]),
    ("Q04", "Depth",
     "Is the printed depth chart the right source for depth order?",
     "26 of 32 clubs serve a text chart; this desk verified 6 of them by reading them. Houston serves an image.",
     "A club-by-club verification of the remaining 26, and a structured source for Houston.",
     "Route (a) for all 32 clubs, which is what R77/R78 require before any backup-deficiency feature.",
     "32 of 32 clubs read and parsed from text.",
     False, ["RD-HOU-CHART", "RD-DET-CHART", "RD-GB-CHART"]),
    ("Q05", "Injuries",
     "What does each game designation actually mean on the field?",
     "216 game designations across 347 report rows, from one dated read (70 Out, 11 Doubtful, 90 Questionable, 176 blank).",
     "The play outcome behind each designation. Without it a designation is a label, not a probability.",
     "R61, R79, R80 and any model that uses an injury label as a feature.",
     "Designations joined to inactive lists across at least 200 player-games per designation.",
     False, ["RD-NFL-INJ-W10"]),
    ("Q06", "Injuries",
     "Is 'not on the report' the same as 'available'?",
     "The Week 10 report lists 347 rows for 28 clubs. No reserve or injured-reserve list is captured, so an absent name cannot be explained.",
     "The 32 roster pages' reserve sections, or a transaction log that states IR placements.",
     "R13, R99, R100: any claim that a club is healthy because a name is missing.",
     "32 of 32 reserve lists captured with dates.",
     False, ["RD-NFL-INJ-W10", "RD-NFL-ROUNDUP-NOV13"]),
    ("Q07", "Injuries",
     "How many players does one report actually cover, and are the inherited counts right?",
     "347 rows, 28 clubs (the 4 bye clubs have no section), 171 rows with a game designation. Recomputed from the live page on 2026-11-17.",
     "Nothing for the count itself. The count is settled.",
     "Nothing; the stale 254/6 figures are corrected here.",
     "Settled: 347 rows and 171 designations is the live count.",
     True, ["RD-NFL-INJ-W10"]),
    ("Q08", "Schedule",
     "Can a venue be published for every fixture from an official page?",
     "12 of 13 Week 11 fixtures print a stadium string in the schedule page's own ticket and hotel links; the Mexico City game prints a label, not a stadium.",
     "A league or club page that prints the stadium for the international fixture.",
     "R23: complete venue transcription.",
     "13 of 13 fixtures with a printed stadium.",
     False, ["RD-NFL-SCHED-W11"]),
    ("Q09", "Schedule",
     "Is there an official dated schedule announcement to publish beside the live schedule?",
     "Two dated documents are cited: the flexible-scheduling procedures page and the dated Week 16-18 TBD announcement text.",
     "Nothing for the requirement. It is met.",
     "Nothing.",
     "Settled.",
     True, ["RD-NFL-SCHED-W11"]),
    ("Q10", "Weather",
     "Does weather belong in the model?",
     "Nothing: no forecast feed and no roof/surface register are captured. One page prints a 'Clear' label.",
     "A registered hourly forecast source and a stadium roof/surface register.",
     "R89 and R90, and any totals or passing-prop adjustment for wind.",
     "A forecast grid per stadium plus a roof register.",
     False, ["RD-NFL-SCHED-W10"]),
    ("Q11", "Signal",
     "Is the side signal real?",
     "The best side entry scores +0.057 Brier skill on weeks 6-9 (n=57), cluster lower bound +0.015, family-wise p 0.348 over 21 trials.",
     "A prospective window of pre-kickoff forecasts, and enough games for the required-n bar.",
     "Any claim of skill. The family null does not clear.",
     "A prospective window with a cluster lower bound above zero after adjustment.",
     False, ["X29-NFL-SCHEDULE"]),
    ("Q12", "Signal",
     "Is the total signal real?",
     "No. Every total entry sits within 0.024 Brier skill of zero, and the best total entry has a negative lower bound.",
     "Nothing to answer this question; it is answered negatively.",
     "Any total-based strategy.",
     "Settled: the total model is not distinguishable from the benchmark on this window.",
     True, ["X29-NFL-SCHEDULE"]),
    ("Q13", "Signal",
     "Does the ranking survive the development window?",
     "No: the development order and the evaluation order agree in 1 of 21 positions.",
     "A longer corpus, or a prospective window.",
     "Trusting the ranking as a property of the model rather than of weeks 6-9.",
     "A window in which the order is stable across halves.",
     True, ["X29-NFL-SCHEDULE"]),
    ("Q14", "Signal",
     "How many selections before an edge would even be visible?",
     "2,241 settled selections for a 55% model at 80% power, or 173 weeks at this season's 13 games a week.",
     "Nothing; the arithmetic is settled.",
     "Any short-window reward or ranking claim.",
     "Settled.",
     True, ["X29-NFL-SCHEDULE"]),
    ("Q15", "Combinations",
     "Can two legs in the same game be multiplied?",
     "No. Measured phi for side x total is -0.096 (n=120, 95% interval -0.271 to +0.085); side x moneyline is +0.935 (n=120).",
     "A directly validated joint probability at the exact thresholds, plus the operator's void/push rule.",
     "Every same-game parlay and prop combo.",
     "An operator rule registered and a joint probability validated on a prospective sample.",
     False, ["X29-NFL-SCHEDULE"]),
    ("Q16", "Combinations",
     "Is a player prop combination measurable at all here?",
     "No player-level outcome is captured. 0 prop lines, 0 prop outcomes.",
     "Per-player per-game logs for the players in each proposed pair.",
     "R119 and the prop-combo division.",
     "A per-player game log for every player in a proposed combination.",
     False, ["RD-NFL-PLAYER-STATS"]),
    ("Q17", "Automation",
     "May the collection be automated?",
     "No. Section 1.3 prohibits systematic retrieval without written consent, so no schedule is enabled and each capture is a single targeted read.",
     "Written consent, or an authorised structured feed.",
     "R31, R33, R34, R51, R52, R67 and every daily-series requirement.",
     "A consent record or an authorised feed.",
     False, ["RD-NFL-TERMS"]),
    ("Q18", "Automation",
     "Is one capture a series?",
     "No. Three dated captures exist for this desk; a delta needs two reads of the same scope and a trend needs more.",
     "Daily captures from Wednesday to kickoff.",
     "R21, R82, R83, R84, R93, R94.",
     "Two reads of the same scope with timestamps.",
     False, ["RD-NFL-INJ-W10"]),
    ("Q19", "Ablation",
     "Does availability information improve the model?",
     "Unknown by construction. The 'with personnel' arm is empty because no absence is confirmed in the corpus.",
     "Confirmed absences per game, from inactive lists or Game Books.",
     "R27, R28, R29, R30 and the personnnel weighting of the originated line.",
     "136 games with a confirmed absence set.",
     False, ["X29-NFL-SCHEDULE", "RD-NFL-INJ-W10"]),
    ("Q20", "Ablation",
     "Is a fixed points penalty for a missing starter defensible?",
     "No test in this repository supports one. The pipeline contains 0 fixed penalties.",
     "The same evidence the ablation needs; a penalty is a placeholder for it.",
     "Any injury-adjusted line.",
     "A measured effect with an interval, not a constant.",
     True, ["X29-NFL-SCHEDULE"]),
    ("Q21", "Competition",
     "Can a reward be paid?",
     "No. 0 of 21 entries qualify: V7 (price) and V8 (prospective record) cannot pass.",
     "A price, a prospective record, and a funding decision.",
     "R118 and the whole reward schedule.",
     "One entry passing V1-V8.",
     False, ["RD-NFL-TERMS"]),
    ("Q22", "Competition",
     "Should the leaderboard rank on return?",
     "No. Return at n=57 is dominated by the noise term; the power table shows why.",
     "Nothing; the proposal is rejected with arithmetic.",
     "Nothing.",
     "Settled: rejected.",
     True, ["X29-NFL-SCHEDULE"]),
    ("Q23", "Governance",
     "Is the leaderboard free of backtest numbers presented as results?",
     "Yes. Every entry is labelled `evaluation weeks 6-9` and every one is `qualified: false`.",
     "Nothing.",
     "Nothing.",
     "Settled, and enforced by a build check.",
     True, ["X29-NFL-SCHEDULE"]),
    ("Q24", "Governance",
     "Is the pre-registration prospective?",
     "No. It was written after weeks 1-9 were played, and it says so on every page that cites it.",
     "A window that opens after the registration is committed.",
     "Any prospective claim, and V8.",
     "A forecast recorded before its kickoff.",
     True, ["X29-NFL-SCHEDULE"]),
    ("Q25", "Governance",
     "Can the previous desks' claims be inherited without re-checking?",
     "The specific claims that were re-read did not reproduce (Baltimore's quarterback row, Washington's empty slot). Each is flagged with the fresh text.",
     "A re-read of every claim in every desk, which no desk has done line by line.",
     "Any cross-desk synthesis presented as verified fact.",
     "A re-read of the claim against the publisher, recorded with the text.",
     False, ["RD-BAL-CHART", "RD-NFL-ROUNDUP-NOV13", "RD-WAS-CHART"]),
    ("Q26", "Governance",
     "What is the single most useful next purchase of information?",
     "The cheapest large gain would be inactive lists: they turn 'suspected replacement' into 'confirmed replacement' and unblock the ablation.",
     "The lists themselves.",
     "Q03, Q19 and R25 all close on the same datum.",
     "One season of inactive lists.",
     False, ["RD-NFL-TERMS"]),
]

FLAGS = [
    ("F01", "Prior claim did not reproduce", "high",
     "A prior desk records that Baltimore still publishes Lamar Jackson and Tyler Huntley at quarterback after both went on injured reserve. The page read today prints Jacoby Brissett, Joe Fagnano and Kedon Slovis, and the Week 10 report does not list Jackson or Huntley at all.",
     "The claim is not repeated. The page as served on 2026-11-17 is transcribed.",
     ["RD-BAL-CHART", "RD-NFL-INJ-W10", "RD-NFL-ROUNDUP-NOV13"]),
    ("F02", "Prior claim did not reproduce", "medium",
     "A prior desk records that Washington leaves a depth-chart slot empty. The page read today prints a name in every one of its 29 slots.",
     "The claim is not repeated. Seattle's two-names-in-one-slot case does reproduce and is published instead.",
     ["RD-WAS-CHART", "RD-SEA-CHART"]),
    ("F03", "Stale published counts", "high",
     "A prior desk's requirement text cites 254 injury rows and 4 clubs with a 'no injury' section. The live page has 347 rows and 28 club sections; the other 4 clubs were on bye and have no section at all, which is not the same thing.",
     "Corrected counts published; the discrepancy is recorded rather than silently overwritten.",
     ["RD-NFL-INJ-W10", "RD-NFL-SCHED-W10"]),
    ("F04", "Two injury departments disagree on the same player", "medium",
     "The Week 10 report lists Rasheen Ali as a full practice participant with a blank game status. The same week's official roundup says Ali (ankle) was a full participant. Both are dated, and the report and the news item are not the same document.",
     "Not reconciled. The report value is published and the news value is recorded beside it.",
     ["RD-NFL-INJ-W10", "RD-NFL-ROUNDUP-NOV13"]),
    ("F05", "Depth chart has no date on 31 of 32 clubs", "high",
     "Only Green Bay prints a date on its chart ('Unofficial, Nov. 10, 2026'). The other five charts read here print none, so a reader cannot tell how old a chart is.",
     "The printed date is recorded where it exists and left blank where it does not. R59 is marked partial.",
     ["RD-DET-CHART", "RD-GB-CHART", "RD-BAL-CHART", "RD-WAS-CHART", "RD-IND-CHART", "RD-SEA-CHART"]),
    ("F06", "Houston depth chart is an image", "high",
     "The Houston page prints a heading and then a single image. There is no text row to parse.",
     "No Houston row is transcribed from the image. The club is excluded from the depth join and listed in the matchup page's limits.",
     ["RD-HOU-CHART"]),
    ("F07", "Market columns are empty by policy", "high",
     "No registered publisher of NFL prices exists for this use, so every market cell on every page in this desk is blank.",
     "Published as blank with the reason. No placeholder, no remembered number, no -110 assumption.",
     ["RD-NFL-TERMS"]),
    ("F08", "The registration is retrospective", "medium",
     "The pre-registration file was written on 2026-11-17, after weeks 1-9 had been played. It binds the procedure but it cannot bind the data.",
     "Every page that cites it says so. No prospective claim is made.",
     ["X29-NFL-SCHEDULE"]),
    ("F09", "No player-level prop evidence", "medium",
     "The brief asks for prop combinations. No prop line and no prop outcome is in the repository.",
     "The prop division is closed with a stated gate rather than filled with a proxy.",
     ["RD-NFL-PLAYER-STATS"]),
    ("F10", "One season only", "high",
     "The corpus is weeks 1-9 of one season. A season-level train/validation/holdout split is impossible.",
     "The window split is by week and is labelled as such. PG-SEASONS blocks any stronger claim.",
     ["X29-NFL-SCHEDULE"]),
    ("F11", "Announced-starter sweep is 3 of 32", "medium",
     "Three dated starter announcements are captured (Seattle, Cleveland, Arizona). The brief asks for an evidence field, which implies a sweep.",
     "The three are published with their dates; the sweep is logged as unclaimed.",
     ["RD-NFL-LOCK", "RD-NFL-ROUNDUP-NOV11"]),
    ("F12", "Weather and roof not sourced", "medium",
     "No forecast feed and no stadium register are captured, so the wind and roof overlay in the brief cannot be built.",
     "The columns exist, are blank, and carry the gate that blocks them.",
     ["RD-NFL-SCHED-W10"]),
    ("F13", "One fixture has no printed stadium", "low",
     "The Mexico City fixture prints a game label and a country graphic, not a stadium string.",
     "The venue cell is blank and the fixture is counted in the 12-of-13 figure.",
     ["RD-NFL-SCHED-W11"]),
    ("F14", "Injury report clock time is not published", "medium",
     "The publisher does not print a fetch or publication clock time on the report page, so the 'clock time' requirement cannot be met from the page.",
     "The read date is recorded and the clock cell is explicitly marked 'unpublished by the publisher'.",
     ["RD-NFL-INJ-W10"]),
    ("F15", "Depth join covers 6 of 32 clubs", "high",
     "This desk read 6 club charts. The other 26 either were not read here or serve an image.",
     "Every depth-derived count on the availability page says 6 of 32, and 283 of 347 injured players are marked 'not on chart' rather than guessed.",
     ["RD-DET-CHART", "RD-GB-CHART", "RD-SEA-CHART", "RD-BAL-CHART", "RD-WAS-CHART", "RD-IND-CHART", "RD-HOU-CHART"]),
]


def build() -> tuple[dict, dict]:
    q_rows = []
    for qid, group, question, held, missing, blocks, closes, answered, sids in QUESTIONS:
        q_rows.append({
            "id": qid, "group": group, "question": question, "held": held, "missing": missing,
            "blocks": blocks, "closes": closes,
            "state": "answered" if answered else "open",
            "source_ids": sids,
        })
    f_rows = []
    for fid, title, severity, detail, disposition, sids in FLAGS:
        f_rows.append({"id": fid, "title": title, "severity": severity, "detail": detail,
                       "disposition": disposition, "status": "Needs review",
                       "unverified_value": "", "source_ids": sids})
    questions = {
        "schema_version": 1,
        "read": "2026-11-17",
        "note": ("Every question is split into what is held, what is missing, what it blocks and what "
                 "closes it. 'answered' is used only where a number on file settles the question, and "
                 "that number is quoted in the held cell."),
        "counts": {"questions": len(q_rows),
                   "answered": sum(1 for q in q_rows if q["state"] == "answered"),
                   "open": sum(1 for q in q_rows if q["state"] == "open")},
        "questions": q_rows,
    }
    flags = {
        "schema_version": 1,
        "read": "2026-11-17",
        "note": ("Flagged irregularities. Every row links a registered official source. A flag does not "
                 "block publication; it blocks any claim that depends on the unverified value."),
        "counts": {"flags": len(f_rows), "high": sum(1 for f in f_rows if f["severity"] == "high"),
                   "medium": sum(1 for f in f_rows if f["severity"] == "medium"),
                   "low": sum(1 for f in f_rows if f["severity"] == "low")},
        "flags": f_rows,
    }
    return questions, flags


def main() -> int:
    DATA.mkdir(exist_ok=True)
    questions, flags = build()
    stale = []
    for name, obj in (("questions.json", questions), ("flags.json", flags)):
        text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
        path = DATA / name
        if "--check" in sys.argv:
            if not path.exists() or path.read_text() != text:
                stale.append(name)
        else:
            path.write_text(text)
    if stale:
        raise SystemExit("stale: " + ", ".join(stale))
    print(f"OK: {questions['counts']}, {flags['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
