"""Decision-readiness register: one row per requirement in the 2026-11-17 brief.

Status vocabulary (fixed; build.py rejects anything else):
  Built               exists in the repo and was checked by a test or a build in an earlier desk
  Built here          created by this desk in this session
  Resolved in part    a specific defect was fixed or verified; the requirement as written is still open
  Partial             some of the requirement exists; the gate column says what is missing
  Blocked: rights     cannot proceed without NFL.com written consent or a licensed feed (see flag F01)
  Blocked: data       no verified official source or dataset exists in the repo yet
  Not started         nothing in the repo for this requirement
  Decision needed     requires an owner decision that is not in the repo
  Rejected (per brief) the brief itself rejects this approach; recorded so nobody builds it by accident

Fields:
  gate      what blocks the requirement now
  clears    the number or artefact that would clear it
  current   the value measured now (computed by build.py where a file exists; otherwise text)
  official  official URLs that support a fact in the row; [] means the row is an internal
            method, decision or repo state with no external fact (stated, not hidden)
"""

OFF_INJ = "https://www.nfl.com/injuries/"
OFF_TERMS = "https://www.nfl.com/legal/terms/"
OFF_WK5 = "https://www.nfl.com/schedules/2026/by-week/week-5"
OFF_GAMECENTRE = "https://www.nfl.com/games/giants-at-commanders-2026-reg-5"

STATUSES = {
    "Built", "Built here", "Resolved in part", "Partial", "Blocked: rights", "Blocked: data",
    "Not started", "Decision needed", "Rejected (per brief)",
}

GROUPS = [
    ("A", "Origination, pricing and market data"),
    ("B", "Results, luck removal and leaderboard integrity"),
    ("C", "Injuries and availability"),
    ("D", "Depth charts and personnel"),
    ("E", "Models, probabilities and validation"),
    ("F", "Strategies, divisions and rewards"),
    ("G", "Site, governance and data policy"),
]

R = []


def add(id_, group, text, status, gate, clears, current, evidence, official=(), flags=()):
    assert status in STATUSES, (id_, status)
    # No repo artefact: leave the evidence blank. The page shows "No repo artefact yet" (it does not point at this file).
    evidence = evidence or ""
    if not evidence.strip() and "F20" not in flags:
        flags = tuple(flags) + ("F20",)  # blank evidence is always flagged (see F20)
    R.append({
        "id": id_, "group": group, "text": text, "status": status, "gate": gate,
        "clears": clears, "current": current, "evidence": evidence,
        "official": list(official), "flags": list(flags),
    })


# A. Origination, pricing and market data
add("A01", "A", "Price-snapshot store: opening and closing numbers for every market we originate",
    "Partial", "No opening lines and no licensed closing prices in the repo; the price-data policy is undecided (A12).",
    "Opening and closing numbers for all 136 games x 3 markets from a source whose terms allow the use.",
    "{snap_records} records in the lifecycle store; market cells blank by rights.",
    "nfl-lifecycle-3f5c/site/price-snapshots.html", flags=("F15",))
add("A02", "A", "Verified results feed so backtests and ROI can be computed",
    "Partial", "Results are verified (official final scores). ROI needs an executable price, which does not exist (A01).",
    "A licensed price for each of the {n_graded} graded games.",
    "{games} official final scores; {n_graded} graded straight-up; 1 tie excluded.",
    "nfl-results/data/games-2026-w1-9.csv", official=(OFF_WK5,))
add("A03", "A", "Originate the side first, then the total, then the moneyline",
    "Built", "None for the order itself.", "n/a (met)",
    "Lifecycle origination order reconciles 14 of 14 games (origination-order.json: checked_games 14, mismatches 0); pricing desk produces side, total and moneyline for 120 of 136 games (nfl-pricing/data/origination.json counts).",
    "nfl-lifecycle-3f5c/site/origination-order.html")
add("A04", "A", "Publish the model's fair line, the market line and the difference as separate columns",
    "Partial", "No market line exists, so the difference column is blank everywhere (A01).",
    "Priced market line for each originated game, archived before kickoff.",
    "Columns exist; market and difference cells blank by rule.",
    "nfl-lifecycle-3f5c/site/fair-market-diff.html")
add("A05", "A", "Separate 'signal' from 'staking' in the leaderboard",
    "Built", "None for the separation itself.", "n/a (met)",
    "Lifecycle leaderboard ranks on signal fields only; staking is not a rank input (desk test).",
    "nfl-lifecycle-3f5c/site/leaderboard.html")
add("A06", "A", "Track the depth of the replacement, not just the fact of a replacement",
    "Partial", "Official depth charts are not verified for all 32 clubs (D05).",
    "Depth rank of each replacement from a verified official depth chart for 32 of 32 clubs.",
    "Lifecycle desk: 173 starter losses, 158 with a named backup (nfl-lifecycle-3f5c/data/replacement-depth.json counts; read 2026-11-17).",
    "nfl-lifecycle-3f5c/site/replacement-depth.html")
add("A07", "A", "Compute correlations only from officially sourced numbers and publish n with each value",
    "Partial", "The pricing desk's correlation uses closing prices that come from a non-official source (Pro-Football-Reference, flag F09).",
    "A correlation recomputed only from official inputs, with n printed beside each value.",
    "Lifecycle correlation audit: 22 rows audited, 0 failures (per desk README). Pricing correlation uses non-official inputs.",
    "nfl-lifecycle-3f5c/site/correlation-audit.html", flags=("F09",))
add("A08", "A", "Define a demotion gate that sends a live strategy back to paper",
    "Built", "None for the gate definition.", "n/a (met)",
    "DG-1 pre-registered and armed; 0 live entries and 0 demotions (nfl-lifecycle-3f5c/data/demotion-gate.json: demotion_count 0, live_entries 0).",
    "nfl-lifecycle-3f5c/site/demotion.html")
add("A09", "A", "Pre-register every strategy; forbid backtest numbers from ever appearing on the leaderboard",
    "Resolved in part", "The results leaderboard shows a backtest hit rate (64.2%) for a provisional entry, which the rule forbids (F08).",
    "Leaderboard shows only pre-registered out-of-sample rows; backtest numbers removed or moved.",
    "This desk: NR-PREREG-1 frozen at commit 813ce25 (strategies.py). Results desk: 1 provisional entry with backtest figures on its page.",
    "nfl-readiness-1467fdf7/site/strategies.html", flags=("F08",))
add("A10", "A", "Price a line ourselves and publish the residual against the market, on a schedule, from day one",
    "Partial", "Our fair line exists, but no market line is archived (A01), so no residual can be published.",
    "A dated market line archived before each kickoff, plus a scheduled residual run.",
    "Fair lines exist for 14 games (lifecycle: origination-order.json) and 120 games (pricing: origination.json). No market residual is published; no market line is archived.",
    "nfl-pricing/site/index.html")
add("A11", "A", "Turn the 136-game log into the pre-registered backtest corpus",
    "Partial", "The 136 scores were retrieved on 2026-11-14, after they were final, so this corpus cannot be pre-registered (F12).",
    "A corpus frozen before its scores exist: prospective weeks registered first, then graded.",
    "136 official scores retrieved 2026-11-14 (retrospective).",
    "nfl-results/data/games-2026-w1-9.csv", official=(OFF_WK5,), flags=("F12",))
add("A12", "A", "Decide the price-data policy before any backtest is published",
    "Decision needed", "No written policy exists in the repo.",
    "A signed policy file naming each permitted price source and its terms.",
    "No policy file.", "", flags=("F15",))
add("A13", "A", "Publish the league's dated schedule announcement beside the live schedule page",
    "Partial", "Only one dated schedule evidence file exists in the repo.",
    "A dated announcement archived for each week, linked from the schedule view.",
    "1 dated evidence file (schedule, read 2026-11-14) in the lifecycle desk.",
    "nfl-lifecycle-3f5c/evidence/schedule-reg10-2026-11-14.md", official=(OFF_WK5,))
add("A14", "A", "Transcribe the venue of every fixture from the official game centre and publish it",
    "Not started", "The games tables have no venue column.",
    "Venue transcribed for 150 fixtures (weeks 1-9: 136; week 10: 14), each linked to its game-centre page.",
    "No venue column: the header of nfl-results/data/games-2026-w1-9.csv and of nfl-availability-28ef/data/games-week10-2026.csv (both read 2026-11-17). Venue cells filled: 0.", "nfl-results/data/games-2026-w1-9.csv; nfl-availability-28ef/data/games-week10-2026.csv", official=(OFF_GAMECENTRE,))
add("A15", "A", "Ingest game-level results to make the ratings opponent-aware",
    "Not started", "Results are ingested, but no rating model exists.",
    "A rating model with a walk-forward test that uses only earlier games.",
    "0 rating models; 136 results available.", "nfl-results/engine.py")

# B. Results, luck removal and leaderboard integrity
add("B01", "B", "Compute and publish the 'removal of luck' panel on the site dashboard",
    "Built here", "The panel is on this desk's landing page; the root dashboard link is pending integration (G02).",
    "Panel on the root dashboard.",
    "Random {c_rand_rate} (band {band_low}-{band_high}); home {c_home_rate}; record {c_rec_rate}; spread board p = 0.0021 permutation (results desk).",
    "nfl-readiness-1467fdf7/site/index.html")
add("B02", "B", "Add a control baseline (random picks; favourites only) to every leaderboard run",
    "Partial", "Market favourites need an official or licensed line, which the repo does not have. A record-based proxy is used instead.",
    "A licensed closing line for each graded game, so the favourite control is a market favourite.",
    "Random, home and record-proxy controls computed for {n_graded} games.",
    "nfl-readiness-1467fdf7/site/controls.html", official=(OFF_WK5,))
add("B03", "B", "Two-stage skill leaderboard: proper-score qualification, then prospective CLV/ROI escrow",
    "Not started", "No stored probability forecasts and no closing line value (E02, A01).",
    "At least 153 settled probability forecasts with stored closing prices.",
    "0 probability forecasts stored.", "")
add("B04", "B", "Vig-free market consensus vs originated fair-line decomposition",
    "Blocked: data", "No market prices in the repo (A01).",
    "Two or more permitted price sources per game, so the consensus can be vig-removed.",
    "0 market sources.", "")
add("B05", "B", "Publish every model total twice until one wins",
    "Not started", "No totals model with two estimators exists in the repo.",
    "Two totals estimators run walk-forward, with a gap column, and one chosen on the comparison.",
    "0 estimator pairs.", "")
add("B06", "B", "Add a drift alarm to every scraper: pin row counts and fields, fail loudly",
    "Partial", "Earlier desks abort on contradictions, but no row-count contract exists for the injury table (F06).",
    "A row-count and field contract for each capture, with the build failing when either changes.",
    "Extraction script aborts on contradictions (earlier desk). Injury table contract: none.",
    "nfl-readiness-1467fdf7/injury_check.py", official=(OFF_INJ,), flags=("F06",))
add("B07", "B", "Publish a weekly 'what changed' diff instead of a static snapshot",
    "Not started", "Only two dated reads of the same table exist; no diff is generated.",
    "Two consecutive weekly snapshots of the same table, with a diff column.",
    "2 dated reads of the Week 10 injury report (2026-11-14 desk capture; 2026-11-17 official read).",
    "nfl-readiness-1467fdf7/injury_check.py", official=(OFF_INJ,))
add("B08", "B", "Store every injury-hub read with its clock time and publish the delta, never the level",
    "Blocked: rights", "Repeated reads of nfl.com are systematic retrieval under Terms §1.3 (F01).",
    "Written NFL consent or a licensed feed, then timestamped reads from kickoff week onwards.",
    "0 timestamped reads (desk captures record a date only).", "", official=(OFF_TERMS,), flags=("F01",))

add("B09", "B", "Durable, immutable snapshot storage outside the static site, with freshness monitoring and alerts on source or schema change",
    "Partial", "A weekly source-health check exists but tests availability only. No immutable store outside the site and no content or schema alert exist.",
    "An off-site immutable store with hashes, a freshness check per source, and an alert on any schema or row-count change.",
    "Weekly source-health workflow present (availability only). Immutable store: none.",
    ".github/workflows/source-health.yml", flags=("F01",))

# C. Injuries and availability
add("C01", "C", "Build the availability graph as a first-class dataset: expected to start vs actually started",
    "Not started", "No pre-game expected-starter list and no game-day inactive list are captured.",
    "Pre-game starter list and game-day inactive list for every starter in weeks 1-10 (all 32 clubs).",
    "0 expected-starter records.", "", official=(OFF_INJ,))
add("C02", "C", "Make the injury signal a surprise, never a level",
    "Not started", "Needs at least two timestamped reads per player (B08).",
    "At least two timestamped reads per player per week, so the change can be measured.",
    "0 players with two timestamped reads.", "", official=(OFF_INJ,))
add("C03", "C", "Run the 32-team roster/IR sweep before any team-level model is trusted",
    "Partial", "The availability desk's club summary covers 28 clubs; the four bye clubs are in another desk and were not re-verified here (F07).",
    "All 32 clubs swept and verified against the official source.",
    "{club_summary_rows} clubs in the availability club summary; {chart_yes} with a depth chart.",
    "nfl-availability-28ef/data/club-summary-week10-2026.csv", flags=("F07",))
add("C04", "C", "Injury and personnel ablations instead of fixed penalties (with/without, chronological holdouts)",
    "Blocked: data", "No archived weekly injury reports for any scored week (nfl-results analysis, NM03).",
    "Archived reports for at least three seasons, so the with/without comparison has a holdout.",
    "0 archived weekly injury reports for weeks 1-9.",
    "nfl-results/analysis.json", official=(OFF_INJ,))
add("C05", "C", "Capture official availability snapshots with raw hashes, timestamps and conflict flags",
    "Partial", "A scheduled capture would be systematic retrieval under Terms §1.3 (F01). Single reads only.",
    "Repeated dated captures with hashes, under written consent or a licence.",
    "1 read of the Week 10 official report saved with SHA-256 {evidence_sha}.",
    "nfl-readiness-1467fdf7/evidence/nfl-injuries-week10-2026-official-read-2026-11-17.md",
    official=(OFF_INJ,), flags=("F01",))
add("C06", "C", "Capture official inactive lists and snap counts",
    "Blocked: rights", "No official inactive-list or snap-count source has been verified, and capture is restricted (F01).",
    "Official inactive list for each game and snap counts for each player-game, from a permitted source.",
    "0 inactive-list records; 0 snap-count records.", "", official=(OFF_TERMS,), flags=("F01",))
add("C07", "C", "Fix the two depth-parsing failures (Texans image; Packers jersey prefix) before widening coverage",
    "Blocked: data", "The Texans depth chart is published as an image; it needs an authorised structured source, not transcription.",
    "Packers rows parsed with the number stripped and the raw string kept; Texans from a structured source.",
    "Not re-verified this session.", "", flags=("F14",))
add("C08", "C", "Score injury-designation reliability before using it as a feature; calibrate what 'Questionable' means empirically",
    "Blocked: data", "Needs several seasons of designations joined to official inactive lists (C06, C04).",
    "Play rate per designation with confidence intervals across at least three seasons.",
    "0 seasons joined.", "", official=(OFF_INJ,))
add("C09", "C", "Snapshot the injury report every Wednesday, Thursday and Friday, with a dated history",
    "Blocked: rights", "Scheduled capture is systematic retrieval under Terms §1.3 (F01).",
    "Written consent or licence, then dated captures on each named day.",
    "0 scheduled captures.", "", official=(OFF_TERMS,), flags=("F01",))
add("C10", "C", "Treat the injury report as a timestamped series: capture daily from Wednesday to kickoff",
    "Blocked: rights", "Same as C09 (F01).",
    "Daily dated captures Wednesday to kickoff, under consent or licence.",
    "0 daily captures.", "", official=(OFF_TERMS,), flags=("F01",))
add("C11", "C", "Use snap counts as the starter proxy when the depth chart is unavailable",
    "Blocked: data", "No verified official snap-count source (C06); route (b) of D05 is unverified.",
    "A verified snap-count source for all 32 clubs.",
    "0 clubs verified.", "")
add("C12", "C", "Capture the reserve list so 'not listed' never means 'available'",
    "Not started", "No injured-reserve list is captured for any club.",
    "Injured-reserve list for 32 of 32 clubs, dated, so absence from the report is checked against it.",
    "0 of 32 clubs.", "", official=(OFF_INJ,))
add("C13", "C", "Re-capture and republish the Week 10 injury tables (row count, Seattle and Cincinnati)",
    "Partial", "Row count (279 vs 326) and Cincinnati (4 vs 8) are unreconciled; the full official report has not been read in full (F05, F06).",
    "Full read of all official pages reconciled to a row count, club by club.",
    "Desk: {desk_rows} rows; SEA {sea_rows} (brief: 15); CIN {cin_rows} (brief: 4). Spot-check: {rows_compared} rows, {rows_mismatch} mismatches.",
    "nfl-readiness-1467fdf7/site/injury-check.html", official=(OFF_INJ,), flags=("F05", "F06"))
add("C14", "C", "Populate the three missing Lions game-status designations (Joseph, Mays, Reed)",
    "Resolved in part", "Game status now matches the official page (Out) for all three. Kerby Joseph's practice status does not match (F02).",
    "All three game-status cells match the official page and the practice status matches too.",
    "Game status: {lions_game_status}. Practice status for Joseph: desk 'Full Participation' vs official 'Did Not Participate'.",
    "nfl-readiness-1467fdf7/site/injury-check.html", official=(OFF_INJ,), flags=("F02",))
add("C15", "C", "Per-team view: starters out, replacements named, net injury count",
    "Partial", "The club summary has the counts; no per-team view page has been checked this session.",
    "A per-team page where every count links to its official row.",
    "Club summary has starters_ruled_out and related counts per club.",
    "nfl-availability-28ef/data/club-summary-week10-2026.csv")
add("C16", "C", "Add an announced-starter evidence field (not an inferred replacement)",
    "Not started", "The dated official starter changes cited in the brief (VR-24, VR-25, VQ-05) are internal references and have not been verified.",
    "A dated official source for each announced starter change, one row per change.",
    "0 verified announced-starter rows.", "")
add("C17", "C", "Flag stale depth rows against the official transactions log (e.g. BAL QB after two injured-reserve moves)",
    "Not started", "The official transactions log has not been captured or verified.",
    "Transactions log captured, and every depth row checked against the last official roster event.",
    "0 stale-row flags raised by a log check.", "")
add("C18", "C", "Treat roster turnover as a first-class data event (versioned depth and availability)",
    "Not started", "No roster-event table exists.",
    "A versioned table of official roster events, with each depth and availability row pointing to its version.",
    "0 roster-event records.", "")

add("C19", "C", "Use official NFL Game Books for actual starters and game-day status; do not infer depth rank or snaps",
    "Blocked: data", "No Game Book has been captured or verified in this repo; capture is subject to Terms §1.3 (F01).",
    "Game Books captured for each game in the sample, with the starter and status rows linked.",
    "0 Game Books captured.", "", flags=("F01",))
add("C20", "C", "Archive weekly injury reports for past seasons, so the question 'do designations change outcomes?' can be tested",
    "Blocked: rights", "Only archive source is nfl.com, and systematic retrieval needs written consent (F01).",
    "Weekly reports for at least three past seasons, retained with hashes.",
    "0 past-season reports archived.", "", official=(OFF_TERMS,), flags=("F01",))

# D. Depth charts and personnel
add("D01", "D", "Model depth from playing time, not jersey order",
    "Blocked: data", "No verified playing-time source (D05 route b and C11 unverified).",
    "A verified playing-time or snap-count source for 32 of 32 clubs.",
    "0 clubs verified by playing time.", "")
add("D02", "D", "Reject deriving depth order from jersey number, experience or salary",
    "Rejected (per brief)", "None. Recorded so the shortcut is not rebuilt.", "n/a",
    "Rule adopted by the brief.", "")
add("D03", "D", "Model depth slots as groups, not a single starter (149 slots with more than one rank-1 player)",
    "Partial", "The depth-slot file's structure is undocumented: {slot_rows} rows map to {slot_keys} unique slot keys (F13).",
    "A documented slot grammar, and the count of multi-rank-1 slots reproduced from the file.",
    "{multi_flag_rows} rows flagged cell_holds_multiple=yes; 149 not reproduced.",
    "nfl-availability-28ef/data/depth-slots-week10-2026.csv", flags=("F13",))
add("D04", "D", "Represent shared and empty depth slots faithfully (Seattle shared slot; Washington empty slot)",
    "Partial", "Shared-slot column exists; the Seattle and Washington rows have not been checked against the official depth page.",
    "Both slots checked against the official depth page, with the saved source.",
    "{blank_slot_rows} rows with a blank player; column present.",
    "nfl-availability-28ef/data/depth-slots-week10-2026.csv")
add("D05", "D", "Resolve the depth-order source (route a: per-club pages; route b: snap counts) before the backup-deficiency feature",
    "Blocked: data", "Route (a) is verified for fewer than 32 clubs in this repo; route (b) has no verified source.",
    "One route verified for all 32 clubs.",
    "{club_summary_rows} of 32 clubs in the availability desk.",
    "nfl-availability-28ef/data/club-summary-week10-2026.csv", official=(OFF_INJ,))
add("D06", "D", "Official depth-chart register with date and source on every row",
    "Built", "None for the register format.", "n/a (met for the rows present)",
    "Depth-slot rows carry source_url and checked_on columns.",
    "nfl-availability-28ef/data/depth-slots-week10-2026.csv")
add("D07", "D", "Interactive Offense vs Defense matchup deficiency matrix (1st to 4th string)",
    "Not started", "Depends on D05 (depth for 32 clubs).",
    "Matrix built from the verified depth register for all 32 clubs.",
    "0 matrix cells.", "")
add("D08", "D", "Flag backups replacing starters on offense and defense from the official register",
    "Partial", "Replacement records exist for the lifecycle desk only; the 32-club register is not complete (D05).",
    "Replacement flags for all 32 clubs, each linked to its depth row and injury row.",
    "Lifecycle desk replacement flags (per desk README).",
    "nfl-lifecycle-3f5c/site/replacement-depth.html")

# E. Models, probabilities and validation
add("E01", "E", "Start with a singles-only shadow baseline: pre-registered team strength, frozen versions, forecasts recorded before kickoff",
    "Partial", "Controls are frozen (NR-PREREG-1). No forecast ledger records a forecast before kickoff.",
    "At least one full week of pre-kickoff forecasts, each timestamped before its kickoff.",
    "Controls frozen at 813ce25; 0 pre-kickoff forecasts recorded.",
    "nfl-readiness-1467fdf7/strategies.py")
add("E02", "E", "Store every model output as a probability plus its inputs, not just a pick",
    "Not started", "No model in the repo emits a stored probability with its inputs.",
    "A forecast table with probability and inputs for every graded game.",
    "0 stored probabilities.", "")
add("E03", "E", "Rank with proper scores and uncertainty: Brier skill with a game-cluster lower bound and a multiplicity adjustment",
    "Not started", "No probability forecasts exist (E02).",
    "At least 153 settled probability forecasts, with a Brier skill score and a clustered lower bound.",
    "0 Brier scores. Multiplicity: results desk reports a family-wise false-positive rate of 0.0218 over 18 tests (analysis.json strategies_tested 18), but its leaderboard counts 30 tested; with 30, the same best p-value (0.001223) gives about 0.036.",
    "nfl-results/analysis.json")
add("E04", "E", "Point-in-time snapshot ledger for injuries, depth charts and inactives",
    "Blocked: rights", "Needs repeated dated captures (C05, F01).",
    "Retained dated captures for every game-week before kickoff.",
    "0 retained point-in-time captures.", "", official=(OFF_TERMS,), flags=("F01",))
add("E05", "E", "Split data into train, validation and final holdout seasons",
    "Blocked: data", "Only one season of results exists (2026 weeks 1-9).",
    "At least three seasons of official results.",
    "1 season, 136 games.", "nfl-results/data/games-2026-w1-9.csv", official=(OFF_WK5,))
add("E06", "E", "2026 kickoff and declared onside-kick regime priors filter",
    "Not started", "No official play-by-play onside-kick data captured.",
    "Official onside-kick attempts for each 2026 game captured and dated.",
    "0 onside-kick records.", "")
add("E07", "E", "Stadium roof/surface and NWS hourly wind/precipitation overlay",
    "Not started", "No official roof designation per game and no NWS grid per game are captured.",
    "Official 90-minute roof designation and NWS hourly forecast for each game, dated.",
    "0 overlay records.", "")
add("E08", "E", "Fixture-context feature set built only from published schedule facts",
    "Not started", "No feature set built; schedule facts are only partly captured.",
    "Feature table with a leakage test, from published schedule facts only.",
    "{games} schedule results and 14 week-10 fixtures in the desks; 0 features.",
    "nfl-results/data/games-2026-w1-9.csv", official=(OFF_WK5,))
add("E09", "E", "Keep parlays and prop combos behind a joint-evidence gate",
    "Blocked: data", "No directly validated joint probability; no operator void/push rules (nfl-results NM01).",
    "A validated joint probability and written void/push rules for each product.",
    "0 joint probabilities.", "nfl-results/analysis.json")
add("E10", "E", "Vig-free market consensus vs originated fair-line decomposition view (see B04)",
    "Blocked: data", "Duplicate of B04; no market prices.", "See B04.", "0 market sources.", "")

# F. Strategies, divisions and rewards
add("F01", "F", "Proper-score leaderboard divisions: singles, game parlays, same-game parlays, prop combos",
    "Partial", "Singles has 4 entries (3 controls, 1 cross-reference). The other three divisions are blocked (E09, C04).",
    "Each division populated with pre-registered entries and proper scores.",
    "{singles_entries} singles entries; 3 divisions blocked.",
    "nfl-readiness-1467fdf7/site/strategies.html")
add("F02", "F", "Rank by benchmark-relative skill with uncertainty, not raw win rate",
    "Not started", "No skill score is computed (E03).",
    "A benchmark-relative score with an interval for each ranked strategy.",
    "0 ranked strategies.", "")
add("F03", "F", "Reject ranking strategies by season-long ROI",
    "Rejected (per brief)", "None. Recorded so the shortcut is not built.", "n/a",
    "Rule adopted by the brief.", "")
add("F04", "F", "Add a two-sided 'what would change our mind' field to every strategy entry",
    "Partial", "Done for the four entries in this desk; the 30 results-desk variants are not yet updated (F08).",
    "Every entry in every desk has a confirm and a refute field.",
    "{mind_entries} of 4 entries in this desk.",
    "nfl-readiness-1467fdf7/site/strategies.html")
add("F05", "F", "Reward the top-performing strategies on a leaderboard",
    "Blocked: data", "No strategy passes gate G7 (executable price), and the reward policy is undecided (F17).",
    "At least one strategy passes G1-G7, and a reward policy is decided.",
    "0 qualified; rewards blank by rule.",
    "nfl-readiness-1467fdf7/site/strategies.html")
add("F06", "F", "Pre-register each strategy: the definition is frozen before results are seen",
    "Built here", "None for the registration itself (commit 813ce25 precedes the control run).",
    "Each new strategy registered in its own commit before its sample is graded.",
    "NR-PREREG-1: 4 entries frozen at 813ce25.", "nfl-readiness-1467fdf7/strategies.py")
add("F07", "F", "Freeze a rule before it sees data: commit the rule text, sample window and gates to git",
    "Built here", "None for this register.", "n/a (met for NR-PREREG-1)",
    "Rule commit 813ce25; control run committed after it.",
    "nfl-readiness-1467fdf7/strategies.py")

# G. Site, governance and data policy
add("G01", "G", "Split the site into a public analysis layer and a private data layer (raw rows private until terms are read)",
    "Decision needed", "Raw row-level CSVs are public in the repo, and the terms have not been read against that use (F16).",
    "A decision on what is published row-level, recorded in the repo.",
    "Row-level public files: {desk_rows} injury rows in one desk CSV.",
    "nfl-availability-28ef/data/injuries-week10-2026.csv", official=(OFF_TERMS,), flags=("F16",))
add("G02", "G", "Put a decision-readiness table on the landing page: one row per requirement",
    "Built here", "This desk's landing page has it; the root landing page link is pending integration.",
    "Table on the root landing page.", "{req_rows} rows.", "nfl-readiness-1467fdf7/site/index.html")
add("G03", "G", "Make suggestions and create a section so the owner can review them before implementing",
    "Built", "None for the sections themselves.", "n/a (met)",
    "Suggestions pages exist in several desks; this desk's questions appear as Decision-needed rows.",
    "nfl-lifecycle-3f5c/site/suggestions.html")
add("G04", "G", "Clear list of questions, information and answers needed before any decision",
    "Built here", "None for the list; the answers are blank where no source exists.",
    "Every Not-started or Blocked row answered or closed.",
    "{open_rows} of {req_rows} rows open.", "nfl-readiness-1467fdf7/site/index.html")
add("G05", "G", "Executive summary of the important details",
    "Built here", "None.", "n/a",
    "docs/nfl-readiness-1467fdf7-executive-summary.md", "docs/nfl-readiness-1467fdf7-executive-summary.md")
add("G06", "G", "Review the repo line by line, verify from official sources, and flag irregularities",
    "Partial", "This session checked the injury rows for four clubs, the controls for 135 games and one tie. Other desks were not re-verified line by line.",
    "Every published row checked against its official link, with the check saved.",
    "{flags_total} flags raised this session; {flags_open} open.",
    "nfl-readiness-1467fdf7/site/flagged.html")
add("G07", "G", "Every table row has a source link to an official site; unverified cells left blank and flagged",
    "Partial", "Enforced by this desk's test and the root checker. Internal rows (no official fact) are shown with an empty official column.",
    "Each row either links an official source or states it is internal.",
    "{official_rows} of {req_rows} rows link an official source.",
    "nfl-readiness-1467fdf7/build.py")
add("G08", "G", "GitHub Pages live site: clean landing page and category subpages, simple dashboard style",
    "Built", "None beyond the Pages deploy check.", "n/a (met before this session)",
    "Live site from earlier sessions; this desk's pages are added at integration.",
    "https://sassnarep3-star.github.io/Own7/")
add("G09", "G", "Coordinate parallel sessions on COORDINATION.md, one claim per task",
    "Built", "None.", "n/a (met)",
    "Board updated this session (claim and completion rows).", "COORDINATION.md")
add("G10", "G", "Open a pull request, merge without waiting, and confirm the Pages deploy",
    "Partial", "In progress: waits on integration and checks (R6).",
    "Merge commit on main and a successful Pages deploy of that commit.",
    "Recorded in COORDINATION.md after the merge.", "COORDINATION.md")
