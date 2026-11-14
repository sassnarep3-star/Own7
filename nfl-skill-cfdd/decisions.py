#!/usr/bin/env python3
"""Questions, suggestions and review flags: the decision layer.

The owner asked for a clear list of questions, information and answers that must be settled before
a decision is reasonable, plus suggestions that discover the missing information. This module
produces three registers:

  Q  questions      - split into what is known with a source, what is missing, what closes it,
                      and what it blocks. A question with no official source for its answer has a
                      blank answer field, never a guess.
  S  suggestions    - each with evidence, what it unlocks, cost, risk, an acceptance test that can
                      actually be run, and the questions it depends on.
  F  flags          - every irregularity found while doing the above, with its official link.

Nothing here is marked decided. The choice record is empty by design and starts empty.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from emit import emit_csv, emit_json, parse_args

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = HERE / "data"

READ_ON = "2026-11-14"
STANDINGS = "https://www.nfl.com/standings/"
INJURIES = "https://www.nfl.com/injuries/league/2026/REG10"


# ------------------------------------------------------------------------------ questions
QUESTIONS = [
    {
        "question_id": "Q01",
        "question": "Is the 2026 Week 10 standings snapshot reproducible from an official page?",
        "area": "data provenance",
        "known": "yes: 32 rows read from the official standings page on 2026-11-14, every row "
                 "re-deriving W+L+T, PCT and NET PTS",
        "known_source": STANDINGS,
        "missing": "",
        "what_closes_it": "already closed for this read date",
        "blocks": "nothing",
        "status": "answered",
    },
    {
        "question_id": "Q02",
        "question": "Did any club's record move since the frozen 2026-11-12 snapshot?",
        "area": "data provenance",
        "known": "two clubs moved (WAS, NYG); their deltas imply exactly one result, WAS 24 - NYG 21",
        "known_source": STANDINGS,
        "missing": "",
        "what_closes_it": "closed: the deltas are checked against the league points identity",
        "blocks": "nothing",
        "status": "answered",
    },
    {
        "question_id": "Q03",
        "question": "Which standings columns can be named with confidence?",
        "area": "data provenance",
        "known": "W, L, T, PCT, PF, PA, NET PTS and the trailing record are named by the page legend",
        "known_source": STANDINGS,
        "missing": "the rendered table does not identify which of the three unnamed 3-part records "
                   "is HOME, ROAD, DIV or CONF, and two decimals are unnamed",
        "what_closes_it": "a machine-readable or column-labelled official export, or an official "
                          "page whose header row renders",
        "blocks": "strategy S9 (divisional underdog), and any home/road split",
        "status": "open",
    },
    {
        "question_id": "Q04",
        "question": "Does any club show skill beyond what its scoring already explains?",
        "area": "skill vs luck",
        "known": "no: Pythagorean residuals give chi-square 19.03 on 32 df, p=0.966. The variance "
                 "is 0.59x what independent games would produce, which is the opposite of "
                 "overdispersion",
        "known_source": STANDINGS,
        "missing": "a second season, to test whether any residual persists",
        "what_closes_it": "two full seasons of the same measured quantity",
        "blocks": "any leaderboard ranking, and every reward",
        "status": "answered-but-constraining",
    },
    {
        "question_id": "Q05",
        "question": "How many settled bets are needed before a strategy can be called skill based?",
        "area": "skill vs luck",
        "known": "153 settled independent bets to distinguish a 60% true rate from break-even at "
                 "80% power; 2,682 bets at a 52.4% rate; 617 at 55%",
        "known_source": "derived in nfl-skill-cfdd/luck.py from the exact binomial",
        "missing": "the settled bets themselves: zero exist",
        "what_closes_it": "a prospective shadow ledger that accumulates real, dated results",
        "blocks": "rewards, prizes and any 'selectively skill based' claim",
        "status": "answered-but-constraining",
    },
    {
        "question_id": "Q06",
        "question": "What is the leg correlation for a 2, 3 or 4-leg parlay?",
        "area": "correlation",
        "known": "club-level correlations were measured and are a DIFFERENT quantity: "
                 "points_for vs points_against r=-0.087 (Holm p=0.889, not significant)",
        "known_source": STANDINGS,
        "missing": "joint settlement of legs on the same ticket; no ticket, price or settled leg "
                   "history exists",
        "what_closes_it": "a priced, settled, timestamped ticket log",
        "blocks": "every parlay and same-game-parlay strategy, and parlay prize design",
        "status": "open",
    },
    {
        "question_id": "Q07",
        "question": "What is the leg correlation for a player-prop combination?",
        "area": "correlation",
        "known": "nothing about props: no prop line, no prop settlement and no per-game player log "
                 "was retrieved",
        "known_source": "",
        "missing": "prop lines, prop settlement, per-game player logs",
        "what_closes_it": "a licensed prop feed, which the rights constraint currently blocks",
        "blocks": "S6 and every combo built on props",
        "status": "open",
    },
    {
        "question_id": "Q08",
        "question": "Does every club publish a readable printed depth chart?",
        "area": "availability",
        "known": "31 of 32 do. The four clubs previously missing (CHI, DEN, PHI, TB) were captured "
                 "on 2026-11-14; they were the Week 10 bye clubs",
        "known_source": "https://www.chicagobears.com/team/depth-chart",
        "missing": "Houston renders a heading and an image and no table, on two independent reads",
        "what_closes_it": "an accessible or text version of the Houston chart, or the league's own "
                          "depth page, which currently serves no chart",
        "blocks": "S7 for Houston only; the club's 16 injury rows keep a blank rank",
        "status": "open",
    },
    {
        "question_id": "Q09",
        "question": "Is every club's depth chart current?",
        "area": "availability",
        "known": "only Chicago prints a chart date (10/31/2026), which is EARLIER than the Week 10 "
                 "injury ledger. Philadelphia's chart still lists two players its own news feed "
                 "reported waived on 2026-11-13",
        "known_source": "https://www.philadelphiaeagles.com/team/depth-chart",
        "missing": "a printed update date for 30 of 31 readable charts",
        "what_closes_it": "clubs printing a chart date, or a league-wide chart with a date",
        "blocks": "any claim that a printed rank reflects this week's lineup",
        "status": "open",
    },
    {
        "question_id": "Q10",
        "question": "How many clubs publish a game status (Out / Doubtful / Questionable)?",
        "area": "availability",
        "known": "4 of 28 clubs on the Week 10 report; the other 24 rows keep a blank game status",
        "known_source": INJURIES,
        "missing": "game status for the remaining 24 clubs",
        "what_closes_it": "reading each club's own Friday game-status report instead of the league "
                          "aggregate",
        "blocks": "any depletion index that needs to know who is actually unavailable",
        "status": "open",
    },
    {
        "question_id": "Q11",
        "question": "What does a blank game status mean?",
        "area": "availability",
        "known": "unknown. The league page prints an empty cell; it does not say whether that means "
                 "'will play', 'not yet decided' or 'not submitted'",
        "known_source": INJURIES,
        "missing": "a publisher statement of what a blank means",
        "what_closes_it": "the NFL injury-report policy page, or a club report that states the rule",
        "blocks": "interpreting 301 of 326 injury rows",
        "status": "open",
    },
    {
        "question_id": "Q12",
        "question": "What is a lost starting player worth in points?",
        "area": "availability",
        "known": "nothing measurable. The printed rank is an ordering; it carries no measured amount",
        "known_source": "",
        "missing": "snap counts and a before/after performance series",
        "what_closes_it": "per-game snap counts and team performance with and without the player",
        "blocks": "turning the depletion index into any line adjustment (S3, S7)",
        "status": "open",
    },
    {
        "question_id": "Q13",
        "question": "Can a price be retrieved from an official source?",
        "area": "rights and price",
        "known": "no. NFL.com publishes no odds; the terms restrict systematic retrieval; the "
                 "rights question XS09 is unsettled",
        "known_source": "https://www.nfl.com/legal/terms/",
        "missing": "a licensed odds source with explicit permission for this use",
        "what_closes_it": "a written licence or an openly licensed odds feed",
        "blocks": "every price, ROI, CLV, reward and wager in this project",
        "status": "blocked",
    },
    {
        "question_id": "Q14",
        "question": "Does the originated line beat a market line?",
        "area": "origination",
        "known": "cannot be known: there is no market line to compare against",
        "known_source": "",
        "missing": "a market line for the same fixture at a timestamped moment",
        "what_closes_it": "Q13",
        "blocks": "the entire origination thesis",
        "status": "blocked",
    },
    {
        "question_id": "Q15",
        "question": "Is the league injury aggregate consistent with club-published reports?",
        "area": "availability",
        "known": "at least one documented disagreement: New Orleans. A club headline states four "
                 "Saints out and two questionable while the league page prints blank for all "
                 "twelve Saints rows",
        "known_source": INJURIES,
        "missing": "a systematic read of all 28 club reports on the same day",
        "what_closes_it": "reading the 28 club Friday reports (suggestion S3)",
        "blocks": "trusting the league aggregate as the sole availability source",
        "status": "open",
    },
]


# ------------------------------------------------------------------------------ suggestions
SUGGESTIONS = [
    {
        "suggestion_id": "P01",
        "title": "Read every club's own Friday game-status report",
        "addresses": "Q10 Q11 Q15",
        "evidence": "only 4 of 28 clubs carry a game status on the league page, while at least one "
                    "club headline disagrees with the league row for the same club",
        "unlocks": "game status for up to 28 clubs, and a cross-check on the league aggregate",
        "cost": "28 page reads per week, transcribed with the same evidence-file discipline",
        "risk": "club reports may use different wording or timing; a difference must be published, "
                "not reconciled by preference",
        "acceptance_test": "for one week, at least 24 of 28 clubs carry a non-blank game status and "
                           "every disagreement with the league page is listed with both links",
        "depends_on": "nothing",
        "priority": 1,
        "effort": "medium",
        "unblocks_most": "yes",
    },
    {
        "suggestion_id": "P02",
        "title": "Settle the rights question before any price work",
        "addresses": "Q13 Q14",
        "evidence": "no price exists anywhere in the repository, and the terms restrict systematic "
                    "retrieval; every economic gate is blocked on this one question",
        "unlocks": "prices, ROI, CLV, parlays, prop combos and every reward",
        "cost": "a written permission, or a licensed feed with a contract",
        "risk": "proceeding without it would publish prices this project has no right to use",
        "acceptance_test": "a named licence or written permission is on file, with its scope quoted",
        "depends_on": "nothing",
        "priority": 1,
        "effort": "external",
        "unblocks_most": "yes",
    },
    {
        "suggestion_id": "P03",
        "title": "Start a dated forward shadow ledger now, at zero stake",
        "addresses": "Q05",
        "evidence": "153 settled bets are needed to separate a 60% rate from break-even, and zero "
                    "exist; a forward record cannot be created retrospectively",
        "unlocks": "the only path to a skill claim, and the only honest path to a leaderboard",
        "cost": "one row per fixture per week, recorded before kickoff",
        "risk": "a shadow record invites hindsight editing, so rows must be committed before the "
                "game and hashed",
        "acceptance_test": "rows exist for 4 consecutive weeks, all timestamped before kickoff, and "
                           "the file hash chain verifies",
        "depends_on": "nothing (does not require a price if the market column stays blank)",
        "priority": 2,
        "effort": "low",
        "unblocks_most": "yes",
    },
    {
        "suggestion_id": "P04",
        "title": "Capture snap counts to make the depletion index measurable",
        "addresses": "Q12",
        "evidence": "the index is currently a count of printed slots; without snap counts it cannot "
                    "become a point value, and inventing one would be a fabrication",
        "unlocks": "a measured backup-deficit, and therefore S3 and S7",
        "cost": "a snap-count source, which is not currently in the official set",
        "risk": "snap counts are widely published but not by NFL.com, so the source must be justified",
        "acceptance_test": "for one week, every printed starter ruled Out has a measured snap share "
                           "and a named replacement with a measured snap share",
        "depends_on": "P01",
        "priority": 3,
        "effort": "high",
        "unblocks_most": "partly",
    },
    {
        "suggestion_id": "P05",
        "title": "Publish a reproducible 'what a blank means' policy after reading the league rule",
        "addresses": "Q11",
        "evidence": "301 of 326 injury rows carry a blank game status and the page does not define "
                    "the blank",
        "unlocks": "a defensible reading of the largest block of rows in the ledger",
        "cost": "one policy-page read and one test",
        "risk": "if the rule cannot be found, the blank must stay unexplained rather than assumed",
        "acceptance_test": "either a quoted publisher statement, or a permanent flag stating no "
                           "statement exists",
        "depends_on": "nothing",
        "priority": 2,
        "effort": "low",
        "unblocks_most": "partly",
    },
    {
        "suggestion_id": "P06",
        "title": "Add a second season before any persistence claim",
        "addresses": "Q04",
        "evidence": "every residual test sits inside the null on one partial season, so there is "
                    "nothing to persist yet",
        "unlocks": "a skill-persistence test, which is the only credible basis for 'selectively "
                   "skill based'",
        "cost": "a second season of the same measured quantities",
        "risk": "one season can look skilful by chance; this is exactly what P06 prevents",
        "acceptance_test": "the same overdispersion test run on two seasons, with the result "
                           "published whichever way it comes out",
        "depends_on": "time",
        "priority": 4,
        "effort": "high",
        "unblocks_most": "yes, eventually",
    },
    {
        "suggestion_id": "P07",
        "title": "Resolve the unnamed standings columns from a labelled source",
        "addresses": "Q03",
        "evidence": "three 3-part records and two decimals are printed but not named, so S9 cannot "
                    "be evaluated and no home/road split can be used",
        "unlocks": "S9, home/road splits, and a complete standings table",
        "cost": "one labelled export or a page whose header row renders",
        "risk": "a third-party label could disagree with the official one; the official label wins",
        "acceptance_test": "every column in the standings table is named by an official header",
        "depends_on": "nothing",
        "priority": 3,
        "effort": "low",
        "unblocks_most": "partly",
    },
    {
        "suggestion_id": "P08",
        "title": "Automate the arithmetic and identity checks that caught this week's moves",
        "addresses": "Q01 Q02",
        "evidence": "the W==L and PF==PA identities independently derived a 24-21 result from the "
                    "standings deltas alone, which is a cheap truth check on any future read",
        "unlocks": "a weekly re-verification that needs no manual work",
        "cost": "already built and running in CI",
        "risk": "none material",
        "acceptance_test": "CI fails if any row or the league identity stops reproducing",
        "depends_on": "nothing",
        "priority": 1,
        "effort": "done",
        "unblocks_most": "yes",
    },
    {
        "suggestion_id": "P09",
        "title": "Keep the leaderboard empty until V4, V5 and V9 pass",
        "addresses": "Q04 Q05",
        "evidence": "a leaderboard on 8-9 game records ranks noise: the residuals are less "
                    "dispersed than chance, not more",
        "unlocks": "credibility; a populated leaderboard that is wrong costs more than an empty one",
        "cost": "none",
        "risk": "an empty board looks like no progress, so the gate counts must be shown beside it",
        "acceptance_test": "the board stays empty while any strategy has an unresolved gate",
        "depends_on": "nothing",
        "priority": 1,
        "effort": "done",
        "unblocks_most": "yes",
    },
    {
        "suggestion_id": "P10",
        "title": "Ask Houston for a text-accessible chart, and record the failure while waiting",
        "addresses": "Q08",
        "evidence": "two independent reads (2026-11-13 and 2026-11-14) return an image and no table",
        "unlocks": "S7 and the depletion index for one AFC club",
        "cost": "one accessibility request",
        "risk": "the gap may persist all season, so the blank must remain visible on the site",
        "acceptance_test": "Houston's 16 injury rows either carry a rank, or the flag stays open",
        "depends_on": "nothing",
        "priority": 3,
        "effort": "low",
        "unblocks_most": "no",
    },
]


# ------------------------------------------------------------------------------ flags
FLAGS = [
    {
        "flag_id": "CF01",
        "title": "Two clubs' standings rows moved between the frozen read and this one",
        "detail": "WAS and NYG both changed. The deltas imply exactly one result, WAS 24 - NYG 21, "
                  "and the league points identity still balances at 6,291. Nothing was back-filled "
                  "into the frozen snapshot.",
        "severity": "informational",
        "status": "explained",
        "source_url": STANDINGS,
    },
    {
        "flag_id": "CF02",
        "title": "The standings table prints columns it does not name",
        "detail": "Three 3-part records and two decimals render without a header. The page legend "
                  "names HOME, ROAD, DIV and CONF but the rendered order does not identify which is "
                  "which, so they are withheld rather than guessed.",
        "severity": "open",
        "status": "open",
        "source_url": STANDINGS,
    },
    {
        "flag_id": "CF03",
        "title": "Chicago's printed chart is dated before the injury ledger it is joined to",
        "detail": "The Bears print 'Depth Chart (As of 10/31/2026)'. The injury ledger is Week 10. "
                  "The chart date is published on every CHI row rather than assumed current.",
        "severity": "open",
        "status": "open",
        "source_url": "https://www.chicagobears.com/team/depth-chart",
    },
    {
        "flag_id": "CF04",
        "title": "Philadelphia's chart contradicts the club's own news feed",
        "detail": "The chart lists Hollywood Brown and Fred Johnson, while the same page's headline "
                  "list reports both waived on 2026-11-13. The chart is also self-labelled "
                  "'UNOFFICIAL' by the club.",
        "severity": "open",
        "status": "open",
        "source_url": "https://www.philadelphiaeagles.com/team/depth-chart",
    },
    {
        "flag_id": "CF05",
        "title": "Philadelphia prints a depth slot with no first-string name",
        "detail": "One DT row prints an empty first cell and Ty Robinson as second string. The slot "
                  "is kept with the gap preserved and counted, not filled.",
        "severity": "open",
        "status": "open",
        "source_url": "https://www.philadelphiaeagles.com/team/depth-chart",
    },
    {
        "flag_id": "CF06",
        "title": "Houston publishes no readable depth chart on two independent reads",
        "detail": "The page renders a heading and an image with no table. Houston's 16 injury rows "
                  "keep a blank rank and a blank replacement.",
        "severity": "open",
        "status": "open",
        "source_url": "https://www.houstontexans.com/team/depth-chart",
    },
    {
        "flag_id": "CF07",
        "title": "Only 4 of 28 clubs publish a game status",
        "detail": "301 of 326 injury rows carry a blank game status. This desk cannot say who is "
                  "actually unavailable for 24 clubs, which caps every availability conclusion.",
        "severity": "blocking",
        "status": "open",
        "source_url": INJURIES,
    },
    {
        "flag_id": "CF08",
        "title": "The Pythagorean residuals are less dispersed than chance",
        "detail": "The overdispersion statistic is 19.03 on 32 df (p=0.966), a variance inflation of "
                  "0.59. That is not evidence of skill; it is a caution against reading a "
                  "leaderboard into 8-9 game records.",
        "severity": "informational",
        "status": "explained",
        "source_url": STANDINGS,
    },
    {
        "flag_id": "CF09",
        "title": "A correlation with r=0.87 is a validity check, not a finding",
        "detail": "Pythagorean expected wins correlate with actual wins at r=0.867 by construction, "
                  "because both sides come from the same PF/PA pair. It is published as a method "
                  "check and must not be read as a tradable signal.",
        "severity": "informational",
        "status": "explained",
        "source_url": STANDINGS,
    },
    {
        "flag_id": "CF10",
        "title": "No price, no ROI and no CLV exists anywhere in this desk",
        "detail": "NFL.com publishes no odds and the rights question is unsettled, so market, ROI, "
                  "CLV, stake and reward fields are blank by rule and are asserted blank by a test.",
        "severity": "blocking",
        "status": "open",
        "source_url": "https://www.nfl.com/legal/terms/",
    },
    {
        "flag_id": "CF11",
        "title": "The four clubs with no chart were the Week 10 bye clubs",
        "detail": "This explains the earlier gap: a bye club has no Week 10 injury row, so the "
                  "missing charts never showed up as unmatched injury rows. The charts are now "
                  "captured and are ready for Week 11.",
        "severity": "informational",
        "status": "explained",
        "source_url": STANDINGS,
    },
    {
        "flag_id": "CF13",
        "title": "Some players are printed in more than one depth slot",
        "detail": "24 of 265 matched injury rows are players their own club prints in more than one "
                  "slot, and 1 of the 8 ruled-out starters is one of them. The join uses one "
                  "printed slot per player (the most prominent) and marks every affected row, so "
                  "the named replacement is correct for that slot but could differ in another slot "
                  "the club also lists him in.",
        "severity": "open",
        "status": "open",
        "source_url": "https://www.nfl.com/injuries/league/2026/REG10",
    },
    {
        "flag_id": "CF14",
        "title": "The standings page updates its columns on different cadences, so a mid-update "
                 "read looks arithmetically wrong",
        "detail": "Read on 2026-11-14 after the Thursday game, all 32 rows are self-consistent and "
                  "PCT equals (W + T/2) / (W + L + T) on every one (NYG 5-3-1 gives 0.611; WAS "
                  "3-5-1 gives 0.389). An earlier render of the same page on the same day still "
                  "showed the pre-game W/L columns while PCT had already moved, which makes the "
                  "publisher appear to use a private convention. It does not; the page was mid-"
                  "update. Any capture must therefore be rejected if its own PCT does not "
                  "re-derive from its own W/L/T, and that check is enforced by collect.py.",
        "severity": "open",
        "status": "open",
        "source_url": STANDINGS,
    },
    {
        "flag_id": "CF12",
        "title": "The depletion index weights are a project choice, not a measurement",
        "detail": "Rank weights (1.00 / 0.45 / 0.20 / 0.10) and status multipliers order clubs "
                  "against each other. They are disclosed on the page and are never converted to "
                  "points, probability or price.",
        "severity": "informational",
        "status": "explained",
        "source_url": "https://www.nfl.com/injuries/league/2026/REG10",
    },
]


def main() -> None:
    parse_args(__doc__)
    emit_csv(DATA / "questions-2026-11-14.csv", QUESTIONS)
    emit_csv(DATA / "suggestions-2026-11-14.csv", SUGGESTIONS)
    emit_csv(DATA / "flags-2026-11-14.csv", FLAGS)

    # The choice record: one row per suggestion, decision blank. It is deliberately empty of any
    # decision so that a reviewer, not this session, records the choice.
    choice = [{
        "suggestion_id": s["suggestion_id"],
        "title": s["title"],
        "priority": s["priority"],
        "decision": "",
        "decided_on": "",
        "decision_by": "",
        "note": "blank by design: this session does not adopt, defer or reject on the owner's behalf",
    } for s in SUGGESTIONS]
    emit_csv(DATA / "choice-record-2026-11-14.csv", choice)

    emit_json(DATA / "decisions-2026-11-14.json", {
        "read_on": READ_ON,
        "questions": len(QUESTIONS),
        "questions_answered": sum(1 for q in QUESTIONS if q["status"] == "answered"),
        "questions_open": sum(1 for q in QUESTIONS if q["status"] == "open"),
        "questions_blocked": sum(1 for q in QUESTIONS if q["status"] == "blocked"),
        "questions_constraining": sum(1 for q in QUESTIONS
                                      if q["status"] == "answered-but-constraining"),
        "suggestions": len(SUGGESTIONS),
        "flags": len(FLAGS),
        "flags_open": sum(1 for f in FLAGS if f["status"] == "open"),
        "flags_explained": sum(1 for f in FLAGS if f["status"] == "explained"),
        "decisions_recorded": 0,
        "decision_policy": "This desk proposes and tests. It does not adopt. Any decision is "
                           "recorded in choice-record-2026-11-14.csv by the reviewer.",
    })
    print(f"OK: {len(QUESTIONS)} questions, {len(SUGGESTIONS)} suggestions, {len(FLAGS)} flags")


if __name__ == "__main__":
    main()
