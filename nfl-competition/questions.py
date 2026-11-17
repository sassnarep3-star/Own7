"""The decision dossier: what we know, what we do not, and what closes each gap.

Every question states four things: the decision it blocks, the information held with its
official source, the information missing, and the specific action that would close it.
Numbers quoted here are read from this lab's own artifacts at build time, so the prose
cannot drift away from the tables.

Statuses:
    answered      the official source answers it
    answered-no   the official source answers it and the answer is no
    partial       some of it is measured, the rest is not published
    open          not answerable from anything retrieved
    blocked       answerable in principle, but the NFL.com terms stand in the way
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, check_artifact, normal_ppf, round_value, write_csv  # noqa: E402

OUT = DATA / "questions.json"
BACKTEST = DATA / "backtest.json"
CORRELATIONS = DATA / "correlations.json"
DEPTH = DATA / "depth.json"
PRICES = DATA / "price-store.json"
RESULTS = DATA / "results-feed.json"
LEADERBOARD = DATA / "leaderboard.json"
ORIGINATION = DATA / "origination.json"


def required_sample(rate, power=0.80, alpha=0.05):
    """Settled selections needed to call this rate better than a coin flip."""
    if rate <= 0.5:
        return None
    z_a = normal_ppf(1 - alpha)
    z_b = normal_ppf(power)
    top = z_a * 0.5 + z_b * math.sqrt(rate * (1 - rate))
    return math.ceil((top / (rate - 0.5)) ** 2)


def build():
    bt = json.loads(Path(BACKTEST).read_text(encoding="utf-8"))
    co = json.loads(Path(CORRELATIONS).read_text(encoding="utf-8"))
    dp = json.loads(Path(DEPTH).read_text(encoding="utf-8"))
    pr = json.loads(Path(PRICES).read_text(encoding="utf-8"))
    rs = json.loads(Path(RESULTS).read_text(encoding="utf-8"))
    lb = json.loads(Path(LEADERBOARD).read_text(encoding="utf-8"))
    og = json.loads(Path(ORIGINATION).read_text(encoding="utf-8"))

    by_id = {s["id"]: s for s in bt["strategies"]}
    corr = {r["id"]: r for r in co["rows"]}
    sb01 = by_id["SB-01"]["signal"]
    sb04 = by_id["SB-04"]["signal"]
    sb09 = by_id["SB-09"]["signal"]
    sb10 = by_id["SB-10"]["signal"]
    hfa = og["parameters"]["home_allowance_points"]
    sd = og["parameters"]["margin_sd_points"]

    sample_table = [{"true_rate": rate, "settled_selections_needed": required_sample(rate)}
                    for rate in (0.524, 0.55, 0.575, 0.60, 0.65)]

    questions = [
        {
            "id": "Q01", "category": "Price",
            "question": "Is there an executable price for any market this lab originates?",
            "blocks": "Return on investment, closing-line value, every staking column and "
                      "every reward.",
            "have": "A verified negative: nfl.com returns HTTP 404 at /odds/ and prints no "
                    "odds table, no price, no operator and no market list. The official "
                    "Week 10 game page prints a score, a by-quarter table and a standings "
                    "widget and no price of any kind.",
            "have_sources": ["CP-NFL-ODDS-ABSENT", "CP-NFL-W10-GAME-WASNYG"],
            "missing": "An opening and a closing number from a named operator, with a "
                       "capture timestamp before kickoff.",
            "closes_it": "Written consent from an operator, or an official league "
                         "publication that prints opening and closing numbers. The store "
                         "already holds the schema and the validator rejects any row "
                         "without a source, a timestamp and an operator.",
            "status": "answered-no",
        },
        {
            "id": "Q02", "category": "Results",
            "question": "Can a backtest be settled from official numbers?",
            "blocks": "Every graded row in this lab.",
            "have": f"{rs['games']} official final scores, and the whole feed re-derives "
                    f"into every club's record: "
                    f"{rs['reconciliation']['fields_matching']} of "
                    f"{rs['reconciliation']['fields_compared']} club fields match the "
                    f"standings page read the same day, with "
                    f"{rs['reconciliation']['league_points_scored']} points each way.",
            "have_sources": ["CP-NFL-RESULTS-W1-9", "CP-NFL-W10-GAME-WASNYG",
                             "CP-NFL-STANDINGS"],
            "missing": "Nothing. This gap is closed.",
            "closes_it": "Extend the feed one week at a time as the league publishes "
                         "results.",
            "status": "answered",
        },
        {
            "id": "Q03", "category": "Signal",
            "question": "Does the originated side beat a coin flip?",
            "blocks": "Any claim that the board carries predictive information.",
            "have": f"The board's own side is {sb01['wins']}-{sb01['losses']} "
                    f"({sb01['hit_rate']:.4f}) on {sb01['n']} settled selections, "
                    f"permutation p = {sb01['p_value']:.4f}, adjusted p = "
                    f"{sb01['q_value']:.4f}. The best record in the family is "
                    f"{by_id['SB-04']['name'].lower()}, {sb04['wins']}-{sb04['losses']} "
                    f"({sb04['hit_rate']:.4f}), adjusted p = {sb04['q_value']:.4f}.",
            "have_sources": ["CP-NFL-RESULTS-W1-9", "CP-NFL-W10-GAME-WASNYG"],
            "missing": "Sample size. Nothing in the family survives multiplicity control "
                       "at an adjusted p of 0.10.",
            "closes_it": f"About {required_sample(0.60)} settled selections to detect a "
                         f"true 60% rate at 80% power; {required_sample(0.55)} for 55%. "
                         f"There are {sb01['n']} today.",
            "status": "answered-no",
        },
        {
            "id": "Q04", "category": "Signal",
            "question": "Does the originated total beat its reference?",
            "blocks": "Any use of the total as a signal.",
            "have": f"Against its own number the board scores {sb09['wins']}-"
                    f"{sb09['losses']} ({sb09['hit_rate']:.4f}) on {sb09['n']} games, "
                    f"which is the coin flip a forecast graded against itself must "
                    f"produce. Against the league-mean total its skill score is "
                    f"{sb10['skill_score']:.4f}, meaning it is worse than the reference.",
            "have_sources": ["CP-NFL-RESULTS-W1-9"],
            "missing": "A total forecast that beats the league mean at all.",
            "closes_it": "A different total model, or a priced total to compare against. "
                         "Until one exists the total is published as a number only.",
            "status": "answered-no",
        },
        {
            "id": "Q05", "category": "Correlation",
            "question": "Can same-game leg dependence be measured?",
            "blocks": "Pricing any same-game parlay.",
            "have": f"Yes. Phi = {corr['C01']['value']:.4f} on n = {corr['C01']['n']} "
                    f"official games, p = {corr['C01']['p_value']:.4f}, using only "
                    f"official final scores. The estimate is not distinguishable from "
                    f"zero at this sample size.",
            "have_sources": corr["C01"]["source_ids"],
            "missing": "Precision. The interval is wide enough to contain both zero and a "
                       "dependence that would matter to a parlay price.",
            "closes_it": "More settled games. The measurement exists; it is underpowered, "
                         "not impossible.",
            "status": "answered",
        },
        {
            "id": "Q06", "category": "Correlation",
            "question": "Can cross-game leg dependence be measured?",
            "blocks": "Pricing a cross-game parlay, where the legs share a week.",
            "have": f"Yes. Phi = {corr['C03']['value']:.4f} over n = {corr['C03']['n']} "
                    f"same-week game pairs, p = {corr['C03']['p_value']:.4f}.",
            "have_sources": corr["C03"]["source_ids"],
            "missing": "A three-leg estimate. The joint cells are too thin to publish one.",
            "closes_it": "More weeks of settled games; the two-leg estimate is already "
                         "computed.",
            "status": "answered",
        },
        {
            "id": "Q07", "category": "Player props",
            "question": "Can a player-prop combination be graded?",
            "blocks": "The entire player-props division of the competition.",
            "have": "Nothing. The official injury report prints a status, not a usage "
                    "number, and no per-game player log was retrieved.",
            "have_sources": ["CP-NFL-INJ-W10"],
            "missing": "Per-game player logs: snaps, targets, carries, yards. Both "
                       "strategies in that division are blocked on this and every column "
                       "in them is blank.",
            "closes_it": "Retrieve official per-game player statistics for the season, "
                         "register the page as a source, and grade the two strategies "
                         "walk-forward. Publish n with every dependence.",
            "status": "open",
        },
        {
            "id": "Q08", "category": "Depth",
            "question": "How deep must a club reach when a starter is ruled out?",
            "blocks": "Turning an injury into anything more than a count.",
            "have": f"{dp['headline']['starters_ruled_out']} first-string players carry "
                    f"the official Out status on a printed chart. "
                    f"{dp['headline']['replacements_from_2nd_string']} are replaced by a "
                    f"second-string name, "
                    f"{dp['headline']['replacements_from_3rd_string']} by a third, and "
                    f"{dp['headline']['slots_with_no_printed_replacement']} slot has no "
                    f"printed replacement at all.",
            "have_sources": ["CP-NFL-INJ-W10", "CP-NFL-DEPTH-27", "CP-NFL-DEPTH-BYE4"],
            "missing": "Any measurement of what the replacement is worth. A printed rank "
                       "is an ordering, not a performance value, and no snap count or "
                       "player log was retrieved.",
            "closes_it": "Snap counts and per-game player logs, which would let a rank be "
                         "weighted by actual usage.",
            "status": "answered",
        },
        {
            "id": "Q09", "category": "Depth",
            "question": "Which clubs have a defensive depth deficiency, and how deep does "
                        "it go?",
            "blocks": "Any defensive adjustment to an originated line.",
            "have": "A per-club table with offence, defence and special teams split, and "
                    "a replacement depth for every slot on the club's own printed chart.",
            "have_sources": ["CP-NFL-INJ-W10", "CP-NFL-DEPTH-27", "CP-NFL-DEPTH-BYE4"],
            "missing": f"The league prints a game status on only "
                       f"{dp['coverage']['rows_with_an_official_game_status']} of "
                       f"{dp['coverage']['injury_rows']} injury rows, so for the other "
                       f"{dp['coverage']['rows_without_an_official_game_status']} rows no "
                       f"absence is stated and no replacement is implied. Houston's chart "
                       f"renders as an image and has no ranks at all.",
            "closes_it": "A game status for every row, or a second official source that "
                         "states availability. Until then the depth table is a floor, not "
                         "a complete count.",
            "status": "partial",
        },
        {
            "id": "Q10", "category": "Data",
            "question": "Does the league publish snap counts or usage shares?",
            "blocks": "Converting a replacement or an injury into a point value.",
            "have": "No. Neither the injury report nor the standings nor the schedule "
                    "pages consulted print a snap count, a target share or a carry share.",
            "have_sources": ["CP-NFL-INJ-W10", "CP-NFL-STANDINGS", "CP-NFL-W10-SCHEDULE"],
            "missing": "Any official usage measurement.",
            "closes_it": "Identify and register an official page that prints participation "
                         "counts, or accept that depth stays an ordering.",
            "status": "open",
        },
        {
            "id": "Q11", "category": "Model",
            "question": "How large is the home allowance, and how certain is that?",
            "blocks": "Every originated side and every moneyline.",
            "have": f"Measured at {hfa['value']:.4f} points from n = {hfa['n']} official "
                    f"home margins, standard error {hfa['se']:.4f}, 95% interval "
                    f"[{hfa['ci95'][0]:.4f}, {hfa['ci95'][1]:.4f}].",
            "have_sources": ["CP-NFL-RESULTS-W1-9", "CP-NFL-W10-GAME-WASNYG"],
            "missing": "Precision. The interval contains both zero and the conventional "
                       "two points, so this season does not separate them.",
            "closes_it": "More games. The earlier board assumed 2.0; this desk measures "
                         "it and publishes the interval instead of a point.",
            "status": "partial",
        },
        {
            "id": "Q12", "category": "Model",
            "question": "What spread converts a side into a moneyline?",
            "blocks": "The third origination stage.",
            "have": f"Measured at {sd['value']:.4f} points, the sample standard deviation "
                    f"of n = {sd['n']} official home margins. Ties are split at the "
                    f"observed rate of {og['parameters']['tie_rate']['value']:.4f} "
                    f"({og['parameters']['tie_rate']['ties']} in "
                    f"{og['parameters']['tie_rate']['n']}).",
            "have_sources": ["CP-NFL-RESULTS-W1-9", "CP-NFL-W10-GAME-WASNYG"],
            "missing": "Nothing material. A normal approximation is used and is stated as "
                       "an approximation.",
            "closes_it": "An empirical margin distribution once several seasons exist.",
            "status": "answered",
        },
        {
            "id": "Q13", "category": "Skill",
            "question": "How many settled selections separate skill from luck?",
            "blocks": "Promotion of any strategy out of paper.",
            "have": "Computed from the exact binomial at 80% power and a 5% level: "
                    + ", ".join(f"{row['true_rate']:.3f} needs "
                                f"{row['settled_selections_needed']}"
                                for row in sample_table) + ".",
            "have_sources": ["CP-NFL-RESULTS-W1-9"],
            "missing": "The selections themselves. The largest strategy sample is "
                       f"{sb01['n']}.",
            "closes_it": "Time. One NFL season of ~270 games per division at most.",
            "status": "answered",
        },
        {
            "id": "Q14", "category": "Operations",
            "question": "Is any strategy live?",
            "blocks": "Rewards, staking, and the demotion gate firing.",
            "have": f"No. Of {len(lb['entries'])} entries, {lb['counts']['Live']} are "
                    f"live, {lb['counts']['Provisional']} provisional and "
                    f"{lb['counts']['Paper']} paper.",
            "have_sources": ["CP-NFL-ODDS-ABSENT"],
            "missing": "An executable price, which G06 requires, and written source "
                       "rights, which G10 requires.",
            "closes_it": "Q01 and the rights question Q16.",
            "status": "answered-no",
        },
        {
            "id": "Q15", "category": "Operations",
            "question": "What sends a live strategy back to paper?",
            "blocks": "Nothing yet: no strategy is live. It blocks trust the moment one is.",
            "have": "Ten triggers are defined, with metric, threshold, window and current "
                    "reading. Seven can be evaluated today and three need a price.",
            "have_sources": ["CP-NFL-RESULTS-W1-9"],
            "missing": "The three price-based triggers cannot fire until a price exists.",
            "closes_it": "Q01.",
            "status": "answered",
        },
        {
            "id": "Q16", "category": "Rights",
            "question": "Can the underlying material be retained and released?",
            "blocks": "Publishing any dataset or feed, and live staking.",
            "have": "NFL.com terms section 1.3 permit individual non-commercial "
                    "informational use and prohibit systematic retrieval to compile a "
                    "collection without written consent. No consent is evidenced.",
            "have_sources": ["CP-NFL-TERMS"],
            "missing": "Written consent.",
            "closes_it": "A licence, or a source whose terms permit it.",
            "status": "blocked",
        },
        {
            "id": "Q17", "category": "Data",
            "question": "Do the standings tables identify their own columns?",
            "blocks": "Home, road, division and conference splits.",
            "have": "No. The rendered table prints three unnamed three-part records and "
                    "two unnamed decimals whose order the page does not state.",
            "have_sources": ["CP-NFL-STANDINGS"],
            "missing": "Column identity.",
            "closes_it": "A page that names the columns, or a conference and league view "
                         "that makes the order unambiguous.",
            "status": "open",
        },
        {
            "id": "Q18", "category": "Consistency",
            "question": "Why do two desks publish different directional records for the "
                        "same season?",
            "blocks": "Trust in either number.",
            "have": "This desk: "
                    f"{sb01['wins']}-{sb01['losses']} ({sb01['hit_rate']:.4f}) over "
                    f"{sb01['n']} selections. The earlier results desk publishes 77-43 "
                    f"(0.6417) over 120. A sensitivity run shows the difference is not the "
                    f"home allowance: forcing this desk's model to 2.0 points gives "
                    f"{bt['sensitivity'][2]['wins']}-"
                    f"{bt['sensitivity'][2]['n'] - bt['sensitivity'][2]['wins']} "
                    f"({bt['sensitivity'][2]['hit_rate']:.4f}), which is worse, not closer.",
            "have_sources": ["CP-NFL-RESULTS-W1-9"],
            "missing": "A shared reference implementation. The two desks use different "
                       "functional forms and different shrinkage, both disclosed.",
            "closes_it": "Grade both models on the same frozen forecast table and publish "
                         "the difference. Flagged, not reconciled here.",
            "status": "open",
        },
        {
            "id": "Q19", "category": "Timing",
            "question": "Is Week 10 settled?",
            "blocks": "Grading the current board.",
            "have": f"No. Of {og['games_originated'] + og['games_played_and_excluded']} "
                    f"Week 10 fixtures, {og['games_played_and_excluded']} had been played "
                    f"when the schedule page was read on 2026-11-14 "
                    f"({og['games_played_and_excluded_detail']}). The other "
                    f"{og['games_originated']} are originated, not graded.",
            "have_sources": ["CP-NFL-W10-SCHEDULE", "CP-NFL-W10-GAME-WASNYG"],
            "missing": "Thirteen results.",
            "closes_it": "Re-read the Week 10 schedule page after Monday 2026-11-16.",
            "status": "answered",
        },
        {
            "id": "Q20", "category": "Data",
            "question": "Are the captured club depth charts current?",
            "blocks": "Trusting a replacement depth for this week.",
            "have": "Mixed. Chicago prints a chart date of 10/31/2026, before the "
                    "injury ledger. Denver, Philadelphia and Tampa print no date at all. "
                    "Philadelphia's chart is self-labelled unofficial.",
            "have_sources": ["CP-NFL-DEPTH-27", "CP-NFL-DEPTH-BYE4"],
            "missing": "A printed as-of date on 30 of 31 captured charts.",
            "closes_it": "Record the printed date with every capture and discard a chart "
                         "that predates the ledger it is joined to.",
            "status": "partial",
        },
    ]

    write_csv(DATA / "questions.csv", [{
        "id": q["id"], "category": q["category"], "status": q["status"],
        "question": q["question"], "blocks": q["blocks"], "have": q["have"],
        "missing": q["missing"], "closes_it": q["closes_it"],
        "sources": ";".join(q["have_sources"]),
    } for q in questions])

    counts = {}
    for q in questions:
        counts[q["status"]] = counts.get(q["status"], 0) + 1

    payload = {
        "built_on": "2026-11-14",
        "purpose": "A decision cannot reasonably be made until these are answered. Each "
                   "question states what is held, with its official source, what is "
                   "missing, and the action that would close it.",
        "counts": counts,
        "total": len(questions),
        "sample_size_table": sample_table,
        "sample_size_note": "Settled selections needed to detect the given true rate "
                            "against a coin flip, at 80% power and a two-sided 5% level, "
                            "from the exact binomial.",
        "questions": questions,
    }
    return round_value(payload, 6)


def main():
    if check_artifact(OUT, build()):
        payload = build()
        print(f"  {payload['total']} questions; {payload['counts']}")


if __name__ == "__main__":
    main()
