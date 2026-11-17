#!/usr/bin/env python3
"""The suggestion section: proposals to review and choose between, before anything is implemented (D9).

This is the part of the brief that asks for a *review workflow*, not a task list. Every proposal
carries the same fields so two of them can be compared:

  unlocks       which requirement IDs it would move
  discovers     the missing datum it would obtain (the brief asks proposals to *find information*)
  evidence      what is already known that makes the proposal worth the cost
  cost, risk    effort and the way it could go wrong
  acceptance    the observable test that would settle whether it worked
  decision      deliberately blank — a reviewer records accept / reject / defer here

Nothing is marked accepted. The desk publishes the options and the blank decision column; choosing
is the reviewer's step, and the registry check refuses a decision string that is not one of the three
allowed words.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = HERE / "data"

ALLOWED_DECISIONS = ("", "accept", "reject", "defer")

# (id, title, unlocks, discovers, evidence, cost, risk, acceptance, priority_scores)
RAW = [
    ("S01", "Obtain official inactive lists for one season",
     ["R10", "R25", "R27", "R35", "R123", "R124"],
     "Who was actually unavailable on game day, per club per week — the datum every availability claim depends on.",
     "347 injury rows and 171 designations are already parsed; 0 games have an inactive list. The ablation arm is empty for exactly this reason.",
     "medium: 272 lists for a season, or 18 for the remaining 2026 weeks",
     "The lists are the publisher's, so the same section 1.3 limit applies to any automated collection; this would be read, not harvested.",
     "For at least 100 games, every player marked Out on the report appears on the inactive list (or a stated reason is recorded).",
     [5, 5, 5]),
    ("S02", "Capture one Game Book per game to fix who actually started",
     ["R10", "R25", "R60", "R63"],
     "The official starting line-up, which is the only way the 'expected versus actual' graph can be closed.",
     "Six depth charts show expected; nothing shows actual.",
     "high: one document per game, in a format that is not always text-extractable",
     "Game Books are large PDFs; extracting a starting line-up reliably is a parsing project of its own.",
     "For 10 checked games, the Game Book's starters match an independent official statement of the same starters.",
     [5, 4, 4]),
    ("S03", "Verify the depth-chart route for the remaining 26 clubs",
     ["R77", "R78", "R59", "R63", "R64"],
     "Which clubs publish a parseable chart at all, and what each club's slot vocabulary is.",
     "26 of 32 are already known to serve text (the prior desk said so); 1 is known to serve an image; the rest are unread by this desk.",
     "low: 26 page reads and a parser adapter per club",
     "Club pages change shape without notice, so each adapter needs a row-count pin or it will silently publish blanks.",
     "32 of 32 clubs parse with a pinned slot count and a recorded print date.",
     [5, 3, 4]),
    ("S04", "Register a permitted price source with opening and closing numbers",
     ["R01", "R04", "R18", "R92", "R118"],
     "The market number, without which no residual, ROI, CLV or reward can exist.",
     "The repository's own price desks hold closing observations from a secondary publisher; none is registered here.",
     "high: a licence conversation, not a fetch",
     "Paying for a feed before the signal is validated would put cost ahead of evidence.",
     "One game shows a stored open, a stored close, and a residual computed against both, from a source whose terms permit it.",
     [5, 5, 3]),
    ("S05", "Turn the report into a multi-day series with hashes",
     ["R21", "R31", "R32", "R33", "R67", "R81", "R83", "R84", "R93"],
     "How a designation evolves between Wednesday and kickoff, which is the actual injury signal.",
     "3 dated captures exist; a delta needs two reads of the same scope.",
     "low if read manually once a day; blocked if automated by section 1.3",
     "A manual read is a person in the loop, which the brief forbids; an automated one needs consent. This is the sharpest conflict in the brief and it is a decision, not a task.",
     "Two consecutive daily captures of the same scope, differing in at least one designation, with both hashes retained.",
     [5, 4, 5]),
    ("S06", "Score the designations against inactive lists once S01 exists",
     ["R12", "R61", "R79", "R80", "R104"],
     "The empirical meaning of Questionable, Doubtful and Out, with intervals.",
     "90 Questionable and 11 Doubtful rows in one week; no outcome for any of them.",
     "medium, and fully dependent on S01",
     "A play rate estimated on one season will be confounded by player quality: stars are listed more and play more.",
     "A play rate per designation with a 95% interval over at least 200 player-games per cell.",
     [4, 4, 4]),
    ("S07", "Add a second, independent season to the corpus",
     ["R111", "R112", "R10", "R122"],
     "A season-level holdout, which is the only clean out-of-sample device this project can afford.",
     "One season, 120 scored games, and a ranking that changes between two halves of it.",
     "high: a second season of scores is 272 more rows, each needing a source page",
     "A second season doubles the work and may show the current signal was a one-season artefact. That is a reason to do it.",
     "The evaluation ranking is computed on season A and reproduced on season B without any parameter change.",
     [5, 4, 5]),
    ("S08", "Publish a pre-kickoff forecast ledger for the rest of 2026",
     ["R43", "R44", "R91", "R122", "V8"],
     "The first genuinely prospective record in this repository.",
     "The model exists; the corpus exists; nothing has been recorded before a kickoff.",
     "low: 13 rows for Week 11 and 13 a week thereafter",
     "The inputs are prior results only, so the Weeks 11 forecast would be weakly informed; publishing a weak number is still better than publishing none, if it is labelled.",
     "13 timestamped forecasts exist with a timestamp earlier than the first kickoff of the week.",
     [5, 3, 5]),
    ("S09", "Add a roster/IR sweep so 'not listed' stops meaning 'unknown'",
     ["R13", "R99", "R100"],
     "Who is unavailable because of a reserve placement rather than because of an injury designation.",
     "The Week 10 report does not list Lamar Jackson; without the reserve list that absence is unexplained.",
     "medium: 32 roster pages with a reserve section",
     "Roster pages carry a status column that changes shape; a missed section would silently make players look available.",
     "For 32 of 32 clubs, a reserve list whose count reconciles with the club's own published roster size.",
     [4, 3, 3]),
    ("S10", "Build the cross-side mismatch matrix for the six charted clubs' opponents",
     ["R63", "R64"],
     "An offence-versus-defence station comparison, which needs both clubs' charts simultaneously.",
     "Six charts are in hand; their Week 10 opponents are not among them.",
     "low: read six more club pages",
     "A single week's chart against a single week's chart is confounded by scheme and by who actually played.",
     "Six paired charts, each with a printed date, producing a matrix with no blank cell that is not explicitly gated.",
     [3, 3, 3]),
    ("S11", "Pin every parser to a schema and a row count, and fail loudly",
     ["R97", "R98", "R51", "R52"],
     "A build that cannot publish a silently wrong table.",
     "This desk pins 347 injury rows, 172 depth slots, 136 game rows and 13 fixtures; a drift already caught two of this desk's own bugs.",
     "low",
     "A pin that is too tight fails on a legitimate update and trains a reviewer to ignore the failure.",
     "A deliberate one-field deletion from a saved page fails the build with a named field and source.",
     [4, 2, 5]),
    ("S12", "Publish the residual against the benchmark for every originated game, on a schedule",
     ["R18", "R92", "R95", "R96"],
     "The size and direction of the model's disagreement with a fixed benchmark, tracked over time.",
     "The residual is already computed per game; it is the trend that is missing.",
     "low",
     "A residual against a model benchmark can be mistaken for a residual against a market. The label has to be unmissable.",
     "Four consecutive weeks of residuals with the benchmark stated on every page.",
     [4, 2, 4]),
    ("S13", "Reconcile the prior desks' claims against a single fresh read",
     ["R128", "Q25"],
     "Which inherited claims are still true today.",
     "Two claims re-read this session did not reproduce (Baltimore's quarterback row, Washington's empty slot).",
     "medium: every claim in every desk, one by one",
     "A claim that fails because the publisher updated a page looks identical to a claim that was wrong when written.",
     "Every claim carries a re-read date and a verdict of reproduced / did-not-reproduce / unreadable.",
     [5, 4, 4]),
    ("S14", "Register a weather and stadium register before touching totals",
     ["R89", "R90", "R14"],
     "Wind, precipitation, roof and surface, which are the standard explanations for a total moving.",
     "The total model is flat (0 total entries distinguishable from the benchmark); weather is a plausible reason to revisit it.",
     "medium",
     "Adding features to a model that has no signal yet is the classic way to manufacture one. This should follow S07, not precede it.",
     "A totals model that improves on the benchmark out of sample *and* whose improvement is attributable to the weather term in an ablation.",
     [2, 3, 2]),
    ("S15", "Write down the price-data policy as a signed decision, not a note",
     ["R20", "R53", "R54"],
     "A record of who decided what about price data, so the blank columns stop being ambiguous.",
     "The policy is currently implied by the blank cells.",
     "low",
     "A written policy can be read as a permission. It has to state the opposite: what is forbidden.",
     "A dated policy file naming the forbidden uses and the person who decided.",
     [4, 1, 4]),
]

DECISION_RULES = [
    {"rule": "One decision per suggestion, recorded as accept, reject or defer. Blank means undecided.",
     "why": "So a reviewer can see at a glance which proposals have been touched."},
    {"rule": "A proposal whose depends_on has not been accepted cannot be accepted.",
     "why": "S06 cannot be built before S01; accepting it early would create a task with no input."},
    {"rule": "Accepting a proposal does not accept its result.",
     "why": "Acceptance buys the experiment, not the finding."},
    {"rule": "Every accepted proposal must name the gate it is expected to clear.",
     "why": "So progress is measured on gates, not on completed tasks."},
    {"rule": "A rejected proposal stays on the page with its reason.",
     "why": "So the same idea is not re-proposed every session."},
]


def build() -> dict:
    rows = []
    for sid, title, unlocks, discovers, evidence, cost, risk, acceptance, scores in RAW:
        rows.append({
            "id": sid, "title": title, "unlocks": unlocks, "discovers": discovers,
            "evidence": evidence, "cost": cost, "risk": risk, "acceptance": acceptance,
            "impact": scores[0], "confidence": scores[1], "unblocking": scores[2],
            "priority": round(scores[0] * 0.5 + scores[1] * 0.2 + scores[2] * 0.3, 2),
            "depends_on": ["S01"] if sid == "S06" else [],
            "decision": "", "decided_by": "", "decided_on": "", "reason": "",
            "source_ids": ["REPO"],
        })
    rows.sort(key=lambda r: (-r["priority"], r["id"]))
    for row in rows:
        if row["decision"] not in ALLOWED_DECISIONS:
            raise SystemExit(f"{row['id']}: decision must be accept/reject/defer or blank")
        if row["decision"] == "" and (row["decided_by"] or row["decided_on"]):
            raise SystemExit(f"{row['id']}: decision metadata without a decision")
    return {
        "schema_version": 1,
        "read": "2026-11-17",
        "purpose": ("Proposals to review and choose between before anything is implemented. Nothing "
                    "on this page is approved. The decision column is deliberately blank and is the "
                    "reviewer's step."),
        "ranking_basis": "impact x 0.5 + confidence x 0.2 + unblocking x 0.3, each scored 1-5; the components are shown so the ranking can be argued with.",
        "decision_rules": DECISION_RULES,
        "counts": {"suggestions": len(rows), "decided": sum(1 for r in rows if r["decision"])},
        "suggestions": rows,
    }


def main() -> int:
    DATA.mkdir(exist_ok=True)
    payload = build()
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    target = DATA / "suggestions.json"
    if "--check" in sys.argv:
        if not target.exists() or target.read_text() != text:
            raise SystemExit("suggestions.json is stale")
        print(f"OK: {payload['counts']}")
        return 0
    target.write_text(text)
    print(f"Wrote suggestions.json: {payload['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
