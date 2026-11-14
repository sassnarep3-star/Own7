"""Questions and suggestions for the market-lifecycle desk.

Requirement (2026-11-14): "I want a clear list of questions, informations and answers that need
to be addressed before any decision can be reasonably made based upon the information that we
already have and do not have. Suggestions need to be made to discover missing information."

Every question states what is already known (with its source), what is missing, what decision it
blocks, and what would close it. Every suggestion carries evidence, what it unlocks, cost, risk,
a runnable acceptance test, and a deliberately blank decision record: nothing here is presented
as decided. Adoption is a reviewer choice, recorded outside this file.
"""

QUESTIONS = [
    {"id": "LQ01", "question": "What are the opening and closing numbers for every market we "
              "originate for Week 10?",
     "status": "answered",
     "info_held": "42 market records (14 games x side/total/moneyline), each with an opening "
                  "snapshot (v2026-11-12) and a closing snapshot (v2026-11-14 for the 13 "
                  "pre-kickoff games; terminal for the played Thursday game), inputs-hashed",
     "info_missing": "nothing for the model side; the market-side number (what an operator "
                     "offered) does not exist in this repository",
     "blocks": "nothing — the store is complete for its model-side scope",
     "closes_when": "already closed by the price-snapshot store (data/price-snapshots.json)",
     "source_ids": ["NFL-STANDINGS", "LC-NFL-STANDINGS-1114", "NFL-SCHED-W10", "REPO"]},

    {"id": "LQ02", "question": "Does the ordered pipeline (side, then total, then moneyline) "
              "produce the same numbers as the canonical engine?",
     "status": "answered",
     "info_held": "yes: all 14 games reconcile field-for-field with research/nfl/results.json "
                  "(0 mismatches); the order is a disclosure of dependency, not a second model",
     "info_missing": "a second independent model implementation would strengthen this, but no "
                     "divergence exists to explain",
     "blocks": "nothing",
     "closes_when": "already closed by stages.reconcile_with_canonical (runs every build)",
     "source_ids": ["NFL-STANDINGS", "PYTH-NFL", "REPO"]},

    {"id": "LQ03", "question": "Is any market price available for the fair-vs-market and "
              "difference columns?",
     "status": "answered-but-constraining",
     "info_held": "no: no sportsbook price is licensed or retrieved (standing constraints XS09/CF10; "
                  "NFL.com terms 1.3 restrict systematic retrieval; no operator feed is cleared)",
     "info_missing": "a rights-cleared price source with timestamped open/close per market",
     "blocks": "market-line columns, difference columns, ROI, CLV, rewards, and any live "
               "promotion (gate RG03)",
     "closes_when": "the reviewer approves a specific rights-cleared source; the store's schema "
                    "already reserves the columns",
     "source_ids": ["CFDD-NFL-TERMS", "REPO"]},

    {"id": "LQ04", "question": "For every starter lost, what is the depth of the replacement?",
     "status": "answered",
     "info_held": "173 starter losses among 265 on-chart injury rows; 158 have a named next-in-line "
                  "on the printed chart; 72 rows print no backup; 61 injury rows are not on any "
                  "printed chart; Houston's chart remains unobtainable (31/32 clubs)",
     "info_missing": "7 of 32 club charts were captured for bye clubs only in the newest pass; the "
                     "join covers printed charts from 2026-11-12/13, which may move before kickoff",
     "blocks": "any claim that a specific Week 10 line should move on a specific replacement",
     "closes_when": "a fresh pre-kickoff chart capture for all 32 clubs, joined to the late-week "
                    "injury report (suggestion LS07)",
     "source_ids": ["X28-NFL-INJ-W10", "CFDD-NFL-STANDINGS", "REPO"]},

    {"id": "LQ05", "question": "Which rights-cleared source will fill the market columns, if any?",
     "status": "open",
     "info_held": "the schema is ready: every market row reserves market_line and fair_minus_market "
                  "fields; the source register can accept the source once approved",
     "info_missing": "a reviewer decision naming the source and its permitted use",
     "blocks": "market/difference columns, ROI, CLV, staking plans, rewards, promotion to live",
     "closes_when": "decision recorded; source registered with its terms; store re-run",
     "source_ids": ["CFDD-NFL-TERMS", "REPO"]},

    {"id": "LQ06", "question": "Should injury and depth information re-originate a line before "
              "kickoff?",
     "status": "open",
     "info_held": "the current model prices lines from scoring profiles only; injuries are tracked "
                  "(326-row ledger, depth join) but never feed a line; the snapshot store is "
                  "append-only and can hold a second model variant's snapshots side by side",
     "info_missing": "whether an injury-adjusted variant beats the base variant out-of-sample "
                     "(walk-forward on the saved weeks 1-9 official scores)",
     "blocks": "the closing-snapshot policy for future weeks (capture what the base model says, "
               "or capture both variants)",
     "closes_when": "suggestion LS03's paper trial is run and reviewed",
     "source_ids": ["X28-NFL-INJ-W10", "NFL-SCHEDULE", "REPO"]},

    {"id": "LQ07", "question": "How often should the store capture snapshots?",
     "status": "open",
     "info_held": "two capture points exist per market this week (open 2026-11-12, close "
                  "2026-11-14); the store's policy field is explicit and versioned",
     "info_missing": "the reviewer's cadence decision (at open; at every input-vintage change; "
                     "final pre-kickoff; or injury-news-triggered)",
     "blocks": "operationalising the store beyond one week",
     "closes_when": "suggestion LS02's cadence is adopted or amended",
     "source_ids": ["REPO"]},

    {"id": "LQ08", "question": "Are the model's fixed constants (home field 2.0 points, margin "
              "sd 13.86) defensible?",
     "status": "open",
     "info_held": "both are disclosed assumptions, chosen before evaluation, with no interval "
                  "published; the snapshot store records every inputs hash so any sensitivity "
                  "rerun is traceable",
     "info_missing": "a sensitivity sweep showing conclusion stability across reasonable values",
     "blocks": "confidence in the fair lines themselves (gate G07 was FAIL on this point)",
     "closes_when": "suggestion LS04's sweep is run and published",
     "source_ids": ["PYTH-NFL", "REPO"]},

    {"id": "LQ09", "question": "Do the demotion gate's thresholds hold up before anything is live?",
     "status": "open",
     "info_held": "the gate (DG-1) is pre-registered with fixed thresholds (D1 alpha 0.01, D2 "
                  "alpha 0.05, D3 Brier margin 0.05) and its logic is unit-tested on synthetic "
                  "windows; 0 live entries exist so the gate is armed and idle",
     "info_missing": "a paper replay of the gate over the 120-row graded history to see how often "
                     "it would have fired",
     "blocks": "trust that the gate neither over- nor under-fires when a strategy first goes live",
     "closes_when": "suggestion LS06's replay is run and reviewed",
     "source_ids": ["NFL-SCHEDULE", "REPO"]},

    {"id": "LQ10", "question": "What would make a strategy's signal trustworthy enough to rank it "
              "for review?",
     "status": "answered-but-constraining",
     "info_held": "the results engine's rules: pre-registered trial family, BH q <= 0.10, leakage-"
                  "free walk-forward grading, luck bands published; 30 variants graded, 1 "
                  "provisional (q=0.022 on n=120), 0 qualified; the lifecycle leaderboard ranks on "
                  "signal only and staking cannot feed the rank",
     "info_missing": "a price (for RG03) and release rights (for RG10) before any entry can be "
                     "qualified or rewarded",
     "blocks": "qualified tier, rewards, live state",
     "closes_when": "LQ05 closes and a new pre-registered season of trials runs",
     "source_ids": ["NFL-SCHEDULE", "REPO"]},
]

SUGGESTIONS = [
    {"id": "LS01", "title": "Approve a rights-cleared price source to fill the market columns",
     "evidence": "every one of the 42 market records has a blank market cell with a stated reason; "
                 "fair-vs-market and difference columns are computed nowhere",
     "unlocks": "market-line and difference columns, CLV, ROI, staking plans, qualified tier, "
                "rewards, a meaningful demotion gate on live entries",
     "cost": "reviewer decision plus a licence or a permissible source; engineering is a "
             "single collector script writing to the existing store",
     "risk": "rights breaches if a source is used outside its terms; wrong-vintage pricing if "
             "capture timestamps are sloppy",
     "acceptance_test": "after adoption: every market row carries market_line and "
                        "fair_minus_market values with a registered timestamped source link, and "
                        "scripts/check_site.py still passes with no filled-without-source cell",
     "status": "for review - not adopted", "decision": None,
     "source_ids": ["CFDD-NFL-TERMS", "REPO"]},

    {"id": "LS02", "title": "Adopt a snapshot cadence: open, every input-vintage change, final "
              "pre-kickoff",
     "evidence": "this week's store has exactly two capture points (2026-11-12, 2026-11-14); the "
                 "policy field is explicit but unapproved",
     "unlocks": "a real open-to-close history; honest CLV the moment a price exists",
     "cost": "a scheduled capture per week; storage is trivial (42 rows per week)",
     "risk": "over-capturing creates noise; under-capturing loses the true close",
     "acceptance_test": "store rebuild stays byte-stable; new entries append without mutating "
                        "history; each entry carries its inputs hash",
     "status": "for review - not adopted", "decision": None,
     "source_ids": ["REPO"]},

    {"id": "LS03", "title": "Run an injury-and-depth-adjusted model variant as a paper trial",
     "evidence": "the depth join names 158 starter losses with a printed next-in-line; the base "
                 "model ignores all of it; weeks 1-9 official scores (120 graded rows) exist",
     "unlocks": "answers LQ06 with evidence instead of assertion; could become the first "
                "pre-registered seasonal trial for the 2026 close",
     "cost": "one variant definition, one walk-forward grade, multiplicity control (it joins the "
             "declared trial family)",
     "risk": "multiple-testing inflation if tried ad hoc; overfitting to one week's injuries",
     "acceptance_test": "variant pre-registered before grading; graded with the engine's own "
                        "walk-forward machinery; published with its BH q-value whatever it is",
     "status": "for review - not adopted", "decision": None,
     "source_ids": ["X28-NFL-INJ-W10", "NFL-SCHEDULE", "REPO"]},

    {"id": "LS04", "title": "Publish a sensitivity sweep for home-field and margin-sd constants",
     "evidence": "HFA=2.0 and sd=13.86 are single disclosed constants; gate G07 records FAIL on "
                 "robustness; the snapshot store carries inputs hashes, so sweep variants are "
                 "traceable",
     "unlocks": "closes G07's robustness FAIL; intervals on the fair lines",
     "cost": "a parameter sweep over a small grid, published as tables",
     "risk": "low; the risk is presentation (sweeps must not be confused with tuning)",
     "acceptance_test": "sweep tables published with per-value fair lines; conclusions labelled "
                        "stable or unstable per row",
     "status": "for review - not adopted", "decision": None,
     "source_ids": ["PYTH-NFL", "REPO"]},

    {"id": "LS05", "title": "Add the three-column fair / market / difference layout to the "
              "canonical lines page (request logged, not applied)",
     "evidence": "this desk publishes the layout on its own page; the canonical nfl-lines.html "
                 "generator (nfl_pages.py) is another session's file, so the change is logged "
                 "in COORDINATION.md instead of made",
     "unlocks": "one place to read fair vs market vs difference per game",
     "cost": "three header cells and three cells per row in the generator; blanks preserved by "
             "the existing data-empty contract",
     "risk": "low; the integration session must keep blanks blank until LS01 closes",
     "acceptance_test": "after integration: every row shows all three columns; difference blank "
                        "whenever market is blank; check_site.py passes",
     "status": "for review - not adopted", "decision": None,
     "source_ids": ["NFL-STANDINGS", "REPO"]},

    {"id": "LS06", "title": "Replay the demotion gate over the graded history (paper simulation)",
     "evidence": "DG-1's triggers are fixed and unit-tested on synthetic windows only; 0 live "
                 "entries means the gate has never operated on real history",
     "unlocks": "evidence about firing frequency before the gate ever gates anything",
     "cost": "one replay script over the 120-row graded ledger",
     "risk": "misreading a paper replay as a promise about future behaviour",
     "acceptance_test": "replay decisions recorded with windows and p-values; no live state "
                        "changes; the replay is labelled paper-only",
     "status": "for review - not adopted", "decision": None,
     "source_ids": ["NFL-SCHEDULE", "REPO"]},

    {"id": "LS07", "title": "Capture all 32 printed depth charts fresh before each week's kickoffs",
     "evidence": "the join relies on charts captured 2026-11-12/13; four bye clubs were captured "
                 "last; Houston's chart renders as an image and has never been obtained",
     "unlocks": "replacement-depth tracking that is current at close; closes LQ04's freshness gap",
     "cost": "a weekly capture pass over 32 club pages; one failure (HOU) needs a printed-list "
             "alternative or remains documented as not obtained",
     "risk": "charts move without notice; a stale chart silently misstates depth",
     "acceptance_test": "weekly join published with per-club capture dates; unobtainable charts "
                        "listed as failures, never substituted",
     "status": "for review - not adopted", "decision": None,
     "source_ids": ["CFDD-HOU-DEPTH", "X28-NFL-INJ-W10", "REPO"]},

    {"id": "LS08", "title": "Keep rewards withheld until RG03 and RG10 both clear",
     "evidence": "every reward field in the graded ledger is null by rule; the leaderboard's "
                 "separation makes staking outcomes irrelevant to rank, so no reward is owed on "
                 "signal alone",
     "unlocks": "nothing (this is a hold), but protects the project from paying on unvalidated "
                "signal",
     "cost": "none",
     "risk": "the competition framing without rewards may feel inert; the alternative is worse",
     "acceptance_test": "reward fields stay null; any change must cite the rights decision",
     "status": "for review - not adopted", "decision": None,
     "source_ids": ["CFDD-NFL-TERMS", "REPO"]},

    {"id": "LS09", "title": "Weekly fresh official re-verification of standings, schedule and "
              "injuries",
     "evidence": "the 2026-11-14 fresh read re-attested 32/32 standings rows and 14/14 fixtures "
                 "and caught the one officially completed Week 10 game; the same pass weekly "
                 "keeps every desk honest",
     "unlocks": "per-week vintage transitions for the snapshot store; early detection of "
                "schedule changes",
     "cost": "three page reads and one diff script per week",
     "risk": "low; the risk of skipping it is a stale universe",
     "acceptance_test": "each week publishes a vintage transition record (moved clubs must equal "
                        "the clubs that played)",
     "status": "for review - not adopted", "decision": None,
     "source_ids": ["LC-NFL-STANDINGS-1114", "LC-NFL-SCHED-REG10-1114", "REPO"]},

    {"id": "LS10", "title": "Wire the signal/staking split into the canonical results leaderboard "
              "(request logged, not applied)",
     "evidence": "this desk proves the split and ranks on signal only; nfl-results-leaderboard.html "
                 "is another session's file, so its change is logged rather than made",
     "unlocks": "one leaderboard where rank cannot be bought by a lucky staking run",
     "cost": "a second table and a note in the canonical generator",
     "risk": "low; the integration session must preserve the engine's tiers verbatim",
     "acceptance_test": "after integration: canonical leaderboard shows signal and staking "
                        "tables separately; ranks identical to this desk's signal ranks",
     "status": "for review - not adopted", "decision": None,
     "source_ids": ["NFL-SCHEDULE", "REPO"]},
]
