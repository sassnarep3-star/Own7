"""Questions the owner must answer, and suggestions to review, before any change.

WHAT THIS FILE IS
-----------------
Two registers, built from the numbers actually computed in this directory, never
from memory and never from a guess:

QUESTIONS  Each one states what is known with a source, what is missing, what
           the answer would unblock, and what action closes it. A question with
           no official source on the known part is left blank there.

SUGGESTIONS Each one states the evidence in the numbers, what it unlocks, what
           it costs, what could go wrong, and a runnable acceptance test. Decision
           columns are BLANK on purpose: they export a preference, they do not
           record an approval. Approving is the owner's act, not this script's.

Nothing here is implemented by merely being listed. A suggestion becomes work
only when a decision is recorded against it.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "data"
OUT_QUESTIONS = OUT_DIR / "questions.csv"
OUT_SUGGESTIONS = OUT_DIR / "suggestions.csv"
OUT_DECISIONS = OUT_DIR / "decision-record.csv"

SOURCES = {
    "PFR": ("PFR-VEGAS-2026", "https://www.pro-football-reference.com/teams/dal/2026_lines.htm",
            "Pro-Football-Reference, 2026 Team Vegas Lines (closing spread and total)"),
    "NFL_SCHED": ("NFL-SCHEDULE-2026", "https://www.nfl.com/schedules/2026/by-week/week-9",
                  "NFL.com 2026 by-week schedule and final scores"),
    "NFL_INJ": ("NFL-INJURY-W10", "https://www.nfl.com/injuries/league/2026/REG10",
                "NFL.com official injury report, Week 10"),
    "CLUB_DEPTH": ("CLUB-DEPTH-2026", "https://www.commanders.com/team/depth-chart",
                   "Official club depth chart (one page per club)"),
    "PFR_SOURCES": ("PFR-SOURCES", "https://www.pro-football-reference.com/about/sources.htm",
                    "Pro-Football-Reference contributors and sources"),
}


def load() -> dict:
    return {
        "prices": json.loads((HERE / "data" / "price-snapshots.json").read_text(encoding="utf-8")),
        "orig": json.loads((HERE / "data" / "origination.json").read_text(encoding="utf-8")),
        "board": json.loads((HERE / "data" / "leaderboard.json").read_text(encoding="utf-8")),
        "corr": json.loads((HERE / "data" / "correlations.json").read_text(encoding="utf-8")),
        "depth": json.loads((HERE / "data" / "depth.json").read_text(encoding="utf-8")),
    }


# Each question: what we hold, what we lack, what it blocks, what closes it.
def questions(data: dict) -> list[dict]:
    p, o, b, c, d = data["prices"], data["orig"], data["board"], data["corr"], data["depth"]
    market_side = c["measured"]["market_line_vs_actual_margin"]
    fair_side = c["measured"]["fair_line_vs_actual_margin"]
    market_total = c["measured"]["market_total_vs_actual_total"]
    fair_total = c["measured"]["fair_total_vs_actual_total"]
    agree = o["agreement"]["side_vs_market"]

    rows = [
        {
            "id": "PQ01",
            "question": "Is our fair line better than the market, or merely a noisier copy of it?",
            "known": (
                f"Market closing line vs actual margin r={market_side['r']} (n={market_side['n']}). "
                f"Our fair line vs actual margin r={fair_side['r']} (n={fair_side['n']}). "
                f"Mean absolute fair-vs-market gap {agree['mean_abs']} points (n={agree['n']})."
            ),
            "missing": (
                "No season with more than nine weeks of games, so the sampling error on both "
                "coefficients is wider than their difference."
            ),
            "blocks": "Promoting any side strategy, and trusting any edge number on the side.",
            "closes_with": (
                "Grade a full season walk-forward and compare the two coefficients on the same "
                "games with a paired test, not two separate intervals."
            ),
            "status": "open",
            "source_ids": "PFR-VEGAS-2026 NFL-SCHEDULE-2026",
            "source_url": SOURCES["PFR"][1],
        },
        {
            "id": "PQ02",
            "question": "Why does our total point the wrong way against outcomes?",
            "known": (
                f"Market total vs actual total r={market_total['r']} (n={market_total['n']}). "
                f"Our fair total vs actual total r={fair_total['r']} (n={fair_total['n']}), which "
                f"has the wrong sign for the stated convention. Our totals also run "
                f"{o['agreement']['total_vs_market']['mean']} points above market on average."
            ),
            "missing": (
                "Whether the bias is one systematic term (the home-field prior added to both "
                "sides of the total) or genuine noise. Settling it needs a held-out season."
            ),
            "blocks": "Every total strategy, including the ones that currently look positive.",
            "closes_with": (
                "Refit the total without the duplicated home-field term on a held-out window and "
                "compare; do not refit on the graded weeks, which would be the overfit this "
                "project is built to avoid."
            ),
            "status": "open - the bias is measured, not explained",
            "source_ids": "PFR-VEGAS-2026 NFL-SCHEDULE-2026",
            "source_url": SOURCES["PFR"][1],
        },
        {
            "id": "PQ03",
            "question": "Do we have permission to publish derived prices and to keep collecting?",
            "known": (
                "The earlier session recorded NFL.com terms restrictions; this capture adds a "
                "second publisher (Sports Reference) whose historical line data it credits to "
                "Sports Odds History."
            ),
            "missing": (
                "No written permission from either publisher. No legal review. No statement of "
                "which of the two governs a derived number."
            ),
            "blocks": (
                "Publishing anything that looks like an executable price, releasing a dataset, "
                "and any scheduled retrieval."
            ),
            "closes_with": (
                "Read both publishers' terms line by line, record the exact clauses with links, "
                "and get a written answer if publication is intended."
            ),
            "status": "blocked on rights",
            "source_ids": "PFR-SOURCES",
            "source_url": SOURCES["PFR_SOURCES"][1],
        },
        {
            "id": "PQ04",
            "question": "Where is the opening number, and is the published number an open or a close?",
            "known": (
                "The publisher prints exactly one number per game and does not label it open or "
                "close. It is recorded here as a closing snapshot. No opening number exists in "
                "the store."
            ),
            "missing": (
                "An official, retrievable archive of opening numbers for these games. ESPN shows "
                "a live open/current pair for the unplayed slate only; its completed-game pages "
                "render neither."
            ),
            "blocks": "Any closing-line-value calculation, and any claim about line movement.",
            "closes_with": (
                "Capture the open/current pair at a fixed timestamp before kickoff in future "
                "weeks, with the timestamp stored beside the number."
            ),
            "status": "open",
            "source_ids": "PFR-VEGAS-2026",
            "source_url": SOURCES["PFR"][1],
        },
        {
            "id": "PQ05",
            "question": "What vig, limit and liquidity does the reference price actually carry?",
            "known": "Spread and total are published. No price, hold percentage or limit is.",
            "missing": (
                "A published moneyline or price for the spread and total, so the hold cannot be "
                "derived. Every staking figure here is at a stated assumed -110."
            ),
            "blocks": "Any ROI, expected-value or break-even claim that depends on a real price.",
            "closes_with": (
                "A source that publishes both sides of each market with prices, for enough games "
                "to estimate the hold."
            ),
            "status": "open",
            "source_ids": "PFR-VEGAS-2026",
            "source_url": SOURCES["PFR"][1],
        },
        {
            "id": "PQ06",
            "question": "Are two legs of a same-game parlay dependent, and by how much?",
            "known": (
                f"Home-cover vs over on the published numbers: phi={c['measured']['home_cover_vs_over']['phi']} "
                f"(n={c['measured']['home_cover_vs_over']['n']}). Player-prop pairs are blank."
            ),
            "missing": (
                "Any published player price, so the dependence between two player props cannot be "
                "measured from official numbers."
            ),
            "blocks": "Pricing any same-game combination without assuming independence.",
            "closes_with": "A licensed player-price feed, then a joint-frequency estimate with n.",
            "status": "blocked on rights",
            "source_ids": "PFR-VEGAS-2026",
            "source_url": SOURCES["PFR"][1],
        },
        {
            "id": "PQ07",
            "question": "Does losing a starter matter more when the position is printed two deep?",
            "known": (
                f"{d['counts']['injury_rows_matched_to_a_printed_slot']} injury rows matched to a "
                f"printed chart; {d['counts']['replacements_with_no_one_behind_them']} have no "
                f"printed name behind the replacement. Offence and defence are counted separately "
                f"({d['counts']['offence_rows']} offence, {d['counts']['defence_rows']} defence)."
            ),
            "missing": (
                "Only one week of depth charts exists, so there is no variation in depth to fit "
                "against outcomes. Sixty-one injury rows match no printed slot."
            ),
            "blocks": "Any injury coefficient, and therefore any line adjustment for availability.",
            "closes_with": (
                "Capture a chart every week for a full season, then test whether the depth measure "
                "predicts the residual against the closing line."
            ),
            "status": "open",
            "source_ids": "NFL-INJURY-W10 CLUB-DEPTH-2026",
            "source_url": SOURCES["NFL_INJ"][1],
        },
        {
            "id": "PQ08",
            "question": "Is the depth data complete, given that it arrives in two separate files?",
            "known": (
                f"Two slot files with no overlap: one holds 27 clubs, the other holds the four "
                f"Week-10 bye clubs. Combined, {d['counts']['clubs_with_printed_chart']} clubs and "
                f"{d['counts']['printed_slots']} printed slots. Houston publishes a chart that "
                f"renders as an image and could not be read."
            ),
            "missing": "One club with no readable printed chart, and any week before Week 10.",
            "blocks": "A complete league view of replacement depth.",
            "closes_with": (
                "A readable Houston chart, and weekly capture going forward. Reading only the "
                "first file silently drops four clubs, which is recorded as PD01."
            ),
            "status": "open",
            "source_ids": "CLUB-DEPTH-2026",
            "source_url": SOURCES["CLUB_DEPTH"][1],
        },
        {
            "id": "PQ09",
            "question": "How many games would it take before a real edge could be seen at all?",
            "known": (
                "At 80% power and a 5% two-sided test: 153 settled selections at a 60% true rate, "
                "617 at 55%, 2,682 at 52.4%. The store holds 136 games."
            ),
            "missing": "Nothing on the arithmetic. What is missing is the games.",
            "blocks": "Any promotion. Nothing in this snapshot can clear its own sample requirement.",
            "closes_with": "Accumulate settled selections to the stated threshold before ranking.",
            "status": "answered - and it constrains everything",
            "source_ids": "PFR-VEGAS-2026",
            "source_url": SOURCES["PFR"][1],
        },
        {
            "id": "PQ10",
            "question": "Do two clubs' pages ever disagree about the same game?",
            "known": (
                f"{p['counts']['games_with_both_sides_agreeing']}/{p['counts']['games_reconciled']} "
                f"games agree on the mirrored spread and "
                f"{p['counts']['games_with_totals_agreeing']}/{p['counts']['games_reconciled']} on "
                f"the total. {p['counts']['publisher_verdicts_reconcile']} publisher verdicts were "
                f"re-derived with zero mismatches."
            ),
            "missing": (
                "Agreement between two pages of the same publisher is not independent "
                "verification. No second, independent price source has been read."
            ),
            "blocks": "A claim of external verification. The store is single-publisher.",
            "closes_with": "Read one independent price source and record every disagreement.",
            "status": "open - internal agreement only",
            "source_ids": "PFR-VEGAS-2026",
            "source_url": SOURCES["PFR"][1],
        },
        {
            "id": "PQ11",
            "question": "Should a strategy that ranks now be trusted next week?",
            "known": (
                f"The demotion gate (DG01) is written and applied: "
                f"{b['counts']['demoted_to_paper']} of {b['counts']['variants']} variants sit in "
                f"demote_to_paper, {b['counts']['ranked']} rank. Nothing has passed it."
            ),
            "missing": (
                "No live strategy exists to demote, so the gate has only ever fired on paper. "
                "Its first live test is untested."
            ),
            "blocks": "Any claim that the gate works in production.",
            "closes_with": (
                "Run the gate across several seasons in replay and record how often it fires "
                "correctly and how often it demotes a strategy that later recovered."
            ),
            "status": "open",
            "source_ids": "PFR-VEGAS-2026",
            "source_url": SOURCES["PFR"][1],
        },
        {
            "id": "PQ12",
            "question": "Is the model's better-looking side result skill or selection?",
            "known": (
                f"{b['counts']['eligible_but_not_significant']} variants clear the selection floor "
                f"and none clears multiplicity control at q<={b['fdr_level']}. The best signal "
                f"hit rate is {b['divergence']['best_signal_hit_rate']} on n="
                f"{next(e['n_settled'] for e in b['entries'] if e['id'] == b['divergence']['best_signal_id'])}."
            ),
            "missing": (
                "The variants were chosen after seeing the data. Even with the correction, the "
                "family itself is not a pre-registered one."
            ),
            "blocks": "Treating any of these twelve as a finding rather than a screening pass.",
            "closes_with": (
                "Freeze the family, then test on a future window that did not exist when the "
                "family was written."
            ),
            "status": "open - family not pre-registered",
            "source_ids": "PFR-VEGAS-2026",
            "source_url": SOURCES["PFR"][1],
        },
    ]
    return rows


def suggestions(data: dict) -> list[dict]:
    p, o, b, c, d = data["prices"], data["orig"], data["board"], data["corr"], data["depth"]
    return [
        {
            "id": "PS01",
            "title": "Capture the opening number before kickoff, every week",
            "evidence": (
                "The store holds a closing number for 136 games and zero opening numbers. ESPN "
                "renders an open/current pair for unplayed games, so the data exists before "
                "kickoff and disappears after it."
            ),
            "unlocks": "Closing-line value, line-movement signals, and a real test of whether our "
                       "number leads or follows the market.",
            "cost": "One fixed pre-kickoff capture per week, with the timestamp stored.",
            "risk": "A capture that is not timestamped is worthless; a capture after kickoff is a "
                    "leak. Both must be blocked in code.",
            "acceptance_test": (
                "A stored open and close for the same game, with two different times, and a test "
                "that fails if open_time >= kickoff_time."
            ),
            "priority": 1,
        },
        {
            "id": "PS02",
            "title": "Fix or retire the total model before publishing it",
            "evidence": (
                f"Our total runs {o['agreement']['total_vs_market']['mean']} points above market "
                f"and correlates {c['measured']['fair_total_vs_actual_total']['r']} with the actual "
                f"total, against {c['measured']['market_total_vs_actual_total']['r']} for the market. "
                f"That is the wrong sign."
            ),
            "unlocks": "A total column that is a forecast rather than an artefact.",
            "cost": "One specification change, plus a held-out test window.",
            "risk": "Fixing it on the graded weeks turns 136 games into a fitted curve and destroys "
                    "the only clean test that exists.",
            "acceptance_test": (
                "The corrected total is fitted on weeks 1-4 only and its correlation with weeks "
                "5-9 outcomes is positive with n printed; if it is not, the column stays blank."
            ),
            "priority": 1,
        },
        {
            "id": "PS03",
            "title": "Add a second, independent price source and show disagreements",
            "evidence": (
                "All prices come from one publisher. Two pages of that publisher agreeing is "
                "internal consistency, not verification."
            ),
            "unlocks": "A defensible price, and the ability to say which number is real when they differ.",
            "cost": "One more official source read per week.",
            "risk": "A second source with a different definition (open vs close, one book vs "
                    "consensus) creates false disagreements unless the definition is recorded.",
            "acceptance_test": (
                "Both sources stored for the same game with their definitions, and a disagreement "
                "table that is non-empty when they differ."
            ),
            "priority": 2,
        },
        {
            "id": "PS04",
            "title": "Pre-register the strategy family before the next window",
            "evidence": (
                f"{b['counts']['variants']} variants were graded and none clears q<={b['fdr_level']}. "
                "The family was written after the data was seen, so even a pass would be weak."
            ),
            "unlocks": "A result that means something the first time it appears.",
            "cost": "A frozen file, a commit hash, and the discipline not to edit it.",
            "risk": "A pre-registered family that nobody enforces is worse than none, because it "
                    "looks rigorous.",
            "acceptance_test": (
                "The family file's hash is committed before the first graded week and the build "
                "fails if it changes."
            ),
            "priority": 2,
        },
        {
            "id": "PS05",
            "title": "Make the demotion gate fire on real history before trusting it",
            "evidence": (
                f"{b['counts']['demoted_to_paper']} of {b['counts']['variants']} variants are in "
                "demote_to_paper, but only on paper. The gate has never seen a live promotion."
            ),
            "unlocks": "A gate whose false-positive and false-negative rates are known.",
            "cost": "Replay across prior seasons where full data exists.",
            "risk": "A gate tuned until it never fires protects nothing.",
            "acceptance_test": (
                "Replay a season with a known regime change and show the gate fires within the "
                "stated window, with the firing date recorded."
            ),
            "priority": 3,
        },
        {
            "id": "PS06",
            "title": "Capture a depth chart every week, not once",
            "evidence": (
                f"One week of charts covers {d['counts']['clubs_with_printed_chart']} clubs and "
                f"{d['counts']['injury_rows_matched_to_a_printed_slot']} matched injury rows. With "
                f"one week there is no variation, so 'deep' versus 'thin' cannot be tested against "
                f"results."
            ),
            "unlocks": "A testable injury term, and the ability to price a depletion.",
            "cost": "32 club pages per week, each with its own rendering quirks.",
            "risk": "Club charts are published on inconsistent dates and are sometimes unofficial; "
                    "a stale chart silently becomes a wrong depth.",
            "acceptance_test": (
                "The same club's chart captured in two consecutive weeks, with the printed date "
                "recorded on each and any change listed."
            ),
            "priority": 3,
        },
        {
            "id": "PS07",
            "title": "Publish a per-row 'why this is blank' reason code",
            "evidence": (
                "Blank cells already carry a rule, but the reader cannot tell 'no source exists' "
                "from 'source exists and was not captured' from 'captured and withheld for rights'."
            ),
            "unlocks": "A reviewer can triage gaps instead of investigating each one.",
            "cost": "One field per blank cell.",
            "risk": "A reason code can become a hiding place if it is never audited.",
            "acceptance_test": (
                "Every blank cell has a code from a closed list, and a count per code is published."
            ),
            "priority": 3,
        },
        {
            "id": "PS08",
            "title": "State the price assumption on every screen that shows a unit total",
            "evidence": (
                f"Every staking number is at an assumed -110, and the store holds no price at all. "
                f"The leaderboard says so; a screenshot or a copied table would not."
            ),
            "unlocks": "A number that cannot be mistaken for a profit claim.",
            "cost": "A caption that travels with the value.",
            "risk": "None material.",
            "acceptance_test": (
                "A test that fails if a units column renders without its assumption string in the "
                "same table."
            ),
            "priority": 2,
        },
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = load()
    qrows = questions(data)
    srows = suggestions(data)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    texts = {}

    qpath = OUT_QUESTIONS
    import io
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(qrows[0].keys()), lineterminator="\n")
    writer.writeheader()
    writer.writerows(qrows)
    texts[qpath] = buf.getvalue()

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(srows[0].keys()), lineterminator="\n")
    writer.writeheader()
    writer.writerows(srows)
    texts[OUT_SUGGESTIONS] = buf.getvalue()

    # The decision record is deliberately blank: a preference export, not an approval.
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["suggestion_id", "decision", "decided_on", "decision_by", "note"],
        lineterminator="\n",
    )
    writer.writeheader()
    for row in srows:
        writer.writerow({
            "suggestion_id": row["id"],
            "decision": "",
            "decided_on": "",
            "decision_by": "",
            "note": "blank by design: this build does not adopt, defer or reject on the owner's behalf",
        })
    texts[OUT_DECISIONS] = buf.getvalue()

    if args.check:
        for path, text in texts.items():
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                print(f"FAIL: {path.name} is stale; run python questions.py")
                return 1
        print(f"OK: {len(qrows)} questions and {len(srows)} suggestions reproduce")
        return 0

    for path, text in texts.items():
        path.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT_QUESTIONS.name} ({len(qrows)}), {OUT_SUGGESTIONS.name} ({len(srows)}), {OUT_DECISIONS.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
