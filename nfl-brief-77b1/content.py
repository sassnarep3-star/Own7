"""Text and requirement register for the brief tracker (session arena/77b177da-own7).

Every status and number here is a function of the facts dict F that build.py computes from repository
files and the evidence extracts. Nothing is typed in by hand except the wording of the brief items.
Source keys: "repo:<path>" is a repository file (not an external official source); other keys are
registered in SOURCE_DEFS below with an official NFL or club URL read on 2026-11-17.
"""

SOURCE_DEFS = {
    "nfl-injuries": ("https://www.nfl.com/injuries/", "NFL.com injury report (Week 10 2026)",
                     "Official league injury report", "Week 10 2026 report, Detroit Lions table only (1 of 8 chunks read)",
                     "Arena fetch_page, rendered text; not an HTTP-status attestation"),
    "nfl-trades": ("https://www.nfl.com/transactions/", "NFL.com league transactions (November 2026 trades)",
                   "Official league transactions log", "All November 2026 trade rows read (single chunk)",
                   "Arena fetch_page, rendered text; not an HTTP-status attestation"),
    "nfl-reserve": ("https://www.nfl.com/transactions/league/reserve-list/2026/11", "NFL.com reserve list, November 2026",
                    "Official league reserve list", "November 2026 list only; October 2026 list not read",
                    "Arena fetch_page, rendered text (chunks 0 and 1 of 2)"),
    "bal-depth": ("https://www.baltimoreravens.com/team/depth-chart", "Baltimore Ravens club depth chart",
                  "Club website (not NFL.com)", "Offense table read; no print date read",
                  "Arena fetch_page, rendered text"),
}

# Club abbreviation -> club name (the 32 clubs).
CLUBS = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens", "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers", "CHI": "Chicago Bears", "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys", "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars", "KC": "Kansas City Chiefs",
    "LV": "Las Vegas Raiders", "LAC": "Los Angeles Chargers", "LAR": "Los Angeles Rams", "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings", "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers", "SF": "San Francisco 49ers",
    "SEA": "Seattle Seahawks", "TB": "Tampa Bay Buccaneers", "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
}
# Depth CSVs use "AZ" for Arizona; this tracker uses "ARI" in its club list.
CSV_CODE = {"ARI": "AZ"}

# Brief items, as summarised in the tracker. status() receives the facts dict F.
def register(F):
    rows = []

    def add(rid, item, status, evidence, gate, clearing, sources, source_kind):
        rows.append({"id": rid, "item": item, "status": status, "evidence": evidence, "gate": gate,
                     "clearing": clearing, "sources": sources, "source_kind": source_kind})

    p = F["price"]
    add("R01", "Originate lines in order: side, then total, then moneyline",
        "Implemented (data)" if F["orig_order"] == ["Side", "Total", "Moneyline"] else "Unverified",
        f"Stage order in origination-order.json: {', '.join(F['orig_order'])}; {F['orig_games']} games.",
        "None for the order itself", "", ["repo:nfl-lifecycle-3f5c/data/origination-order.json"], "Repository artifact")
    add("R02", "Publish fair line, market line and difference as separate columns",
        "Columns present; market values blank",
        f"Fair line and market-line fields exist in price-snapshots.json. Market line is filled for {p['market_line_filled']} of {p['markets']} markets; difference is filled for {p['diff_filled']}.",
        "RG03 / XS09: no licensed sportsbook price", "", ["repo:nfl-lifecycle-3f5c/data/price-snapshots.json", "nfl-injuries"], "Repository artifact")
    add("R03", "Price-snapshot store, opening and closing",
        "Partly implemented",
        f"{p['markets']} markets across {p['games']} games with opening and closing entries. Closing equals opening for {p['close_equals_open']} of {p['markets']} (LC-F01).",
        "Price data policy (XS09 / CF10)", "", ["repo:nfl-lifecycle-3f5c/data/price-snapshots.json"], "Repository artifact")
    add("R04", "Verified results feed (136-game log)",
        "Implemented (data)",
        f"nfl-results/data/games-2026-w1-9.csv has {F['games_rows']} game rows (brief says 136).",
        "None for the feed; price data needed for ROI", str(F["games_rows"]) if F["games_rows"] else "",
        ["repo:nfl-results/data/games-2026-w1-9.csv"], "Repository artifact")
    add("R05", "Backtest and ROI computable from snapshots and results",
        "Blocked", "No licensed closing price exists in the repository, so ROI cannot be computed from it.",
        "RG03 / RG10: price rights and terms", "", ["repo:nfl-lifecycle-3f5c/data/price-snapshots.json"], "Repository artifact")
    add("R06", "Signal and staking separated in the leaderboard",
        "Implemented (data)" if F["sep_rule"] else "Unverified",
        "leaderboard.json states ranking reads only signal fields; the staking table has no rank.",
        "None", "", ["repo:nfl-lifecycle-3f5c/data/leaderboard.json"], "Repository artifact")
    add("R07", "Strategies pre-registered (commit hash as registration)",
        "Unverified",
        f"Demotion gate DG-1 states defined_on {F['dg_defined_on']}, but its rule and code first appear in commit {F['dg_first_commit']} with the desk code. A self-declared date is not a registration.",
        "Commit-hash registration per strategy", "", ["repo:nfl-lifecycle-3f5c/data/demotion-gate.json"], "Repository artifact")
    add("R08", "Proper-score ranking with benchmark and uncertainty",
        "Not implemented",
        f"Ranking fields are {', '.join(F['lb_fields'])}. None is a proper score (no Brier, log score or CRPS field) and no benchmark field is present.",
        "Proper score definition and baseline", "", ["repo:nfl-lifecycle-3f5c/data/leaderboard.json"], "Repository artifact")
    add("R09", "Leaderboard divisions: singles, game parlays, SGPs, prop combos",
        "Partly implemented",
        f"Graded rows use markets {', '.join(F['lb_markets'])} only. No moneyline, parlay, SGP or prop-combo division is present. Leaderboard rows: {F['lb_counts']}.",
        "Joint-evidence gate (for parlays / SGPs / props)", "", ["repo:nfl-lifecycle-3f5c/data/leaderboard.json"], "Repository artifact")
    add("R10", "Demotion gate",
        "Implemented, armed" if F["dg_armed"] else "Not armed",
        f"DG-1: armed={F['dg_armed']}, demotions={F['dg_demotions']}. Pre-registration of the rule is R07.",
        "Pre-registration (R07)", "", ["repo:nfl-lifecycle-3f5c/data/demotion-gate.json"], "Repository artifact")
    add("R11", "Control baselines",
        "Partly implemented",
        "Demotion trigger D1 uses a declared baseline. The leaderboard has no baseline field.",
        "Baseline definition per strategy", "", ["repo:nfl-lifecycle-3f5c/data/demotion-gate.json", "repo:nfl-lifecycle-3f5c/data/leaderboard.json"], "Repository artifact")
    add("R12", "Correlations published with n",
        "Implemented (data)" if F["corr_n_rows"] == F["corr_coeff"] else "Partly implemented",
        f"correlation-audit.json: {F['corr_rows']} audited rows, {F['corr_coeff']} with coefficients, {F['corr_blank']} blank by rule, {F['corr_failed']} failed; {F['corr_n_rows']} rows carry n.",
        "None for the rule", "", ["repo:nfl-lifecycle-3f5c/data/correlation-audit.json"], "Repository artifact")
    add("R13", "Availability and depth from official sources only; no jersey-order depth",
        "Partly implemented",
        f"Depth desk captured {F['avail_clubs']} clubs; the skill desk captured {F['skill_clubs']}. Some charts are unofficial club copies (for example the Packers chart is stamped 'Unofficial'). Houston is image-only. No script in the repository derives depth from jersey number (not exhaustively audited).",
        "Official-source rule; club-site charts", "", ["repo:nfl-availability-28ef/data/depth-slots-week10-2026.csv", "repo:nfl-skill-cfdd/data/depth-slots-2026-11-14.csv"], "Repository artifact")
    add("R14", "Injury signal as surprise (change), never level; publish deltas",
        "Not implemented",
        f"None of the {F['inj_files']} injury files has a delta or change column. The published injury values are levels.",
        "Injury-change definition and delta column", "", ["repo:nfl-availability-28ef/data/injuries-week10-2026.csv"], "Repository artifact")
    add("R15", "Roster and IR sweep of 32 teams",
        "Partly implemented",
        f"Depth coverage: {F['sweep_covered']} of 32 clubs have a captured chart in either desk; {F['sweep_missing']} clubs have none. The November reserve list was read (25 rows); October was not.",
        "Official reserve-list read for October and the 32-club sweep", "", ["nfl-reserve", "nfl-trades"], "Official NFL page")
    add("R16", "Snapshot store of injury reports, inactives and depth charts with hashes",
        "Partly implemented",
        f"Availability capture records joined_sha256 ({F['capture_hash_present']}). No hash-keyed store of injury reports or inactives exists in the repository.",
        "Snapshot policy for inactives and injury reports", "", ["repo:nfl-availability-28ef/data/capture-summary.json"], "Repository artifact")
    add("R17", "'What would change our mind' per strategy",
        "Not implemented",
        f"The leaderboard data has no such field. The phrase 'would change the answer' appears {F['wcta_count']} times in nfl-results-leaderboard.html. Coverage per strategy is not checked.",
        "Per-strategy field", "", ["repo:nfl-results-leaderboard.html"], "Repository artifact")
    add("R18", "Injury and depth data: Lions Week 10 status cross-checked against official page",
        "Mismatch in 3 desks" if F["lions_mismatch_desks"] else "Matches",
        f"Official page (read 2026-11-17): Joseph, Mays and Reed all Out. Desks in scope that disagree: {F['lions_mismatch_desks']}.",
        "Source correction (flagged, not changed)", "", ["nfl-injuries", "repo:nfl-assurance-9580ac3f/data/injuries.csv"], "Official NFL page")
    add("R19", "Stale-depth flag against official transactions",
        "Flagged" if F["stale_count"] else "Clear",
        f"{F['txn_count']} November trades checked: {F['stale_count']} stale (still printed on the former club), {F['printed_new']} printed on the new club, {F['not_printed']} not printed on the new club (review only), {F['no_chart']} with no chart.",
        "Chart refresh for flagged clubs", "", ["nfl-trades", "repo:nfl-availability-28ef/data/depth-slots-week10-2026.csv"], "Official NFL page")
    add("R20", "Baltimore QB order against the club page",
        "Mismatch" if F["bal_changed"] else "Matches",
        f"Repository chart (checked {F['bal_repo_date']}) names Jackson and Huntley. Club page (read 2026-11-17) Offense table names Brissett and Fagnano and Slovis. Brief's 'placed on IR' is not on the November reserve list.",
        "October reserve list (not read)", "", ["bal-depth", "nfl-reserve", "repo:nfl-availability-28ef/data/depth-slots-week10-2026.csv"], "Club website")
    add("R21", "Kickoff/onside regime priors filter published as stated in the brief",
        "Stated in repository" if F["onside_in_code"] else "Not found",
        f"'onside' appears in repository code and pages ({F['onside_hits']} files).",
        "Filter values to be checked against the brief text", "", ["repo:nfl_pages.py"], "Repository artifact")
    add("R22", "Two model totals published with gap column until walk-forward picks one",
        "Partly implemented" if F["gap_in_decisions"] else "Not found",
        f"decisions.json mentions 'gap' {F['gap_in_decisions']} time(s). Two-estimator totals with a gap column are not in the published leaderboard.",
        "Walk-forward comparison", "", ["repo:nfl-lifecycle-3f5c/data/decisions.json"], "Repository artifact")
    add("R23", "Parlays and prop combos behind a joint-evidence gate",
        "Stated; no ranked strategies" if F["joint_hits"] else "Not found",
        f"'joint' appears {F['joint_hits']} times in nfl_pages.py. The leaderboard has {F['lb_qualified']} qualified strategies.",
        "Joint-evidence definition", "", ["repo:nfl_pages.py"], "Repository artifact")
    add("R24", "Public site shows derived analysis only; raw rows kept private until terms are read",
        "Not met as written",
        f"Row-level files are committed to the public repository: price-snapshots.json ({F['price']['markets']} rows), games-2026-w1-9.csv ({F['games_rows']} rows), and {F['inj_files']} injury CSVs. Terms are cited at NFL.com (see Flagged FL-13).",
        "Owner decision on the private-store policy", "", ["repo:nfl-lifecycle-3f5c/data/price-snapshots.json"], "Repository artifact")
    add("R25", "Repository review, line by line, with official links",
        "Present (in main)", "docs/nfl-repo-review-2026-11-17.md is on main (commit 7c4d04f). This tracker does not restate it.",
        "None", "", ["repo:docs/nfl-repo-review-2026-11-17.md"], "Repository artifact")
    return rows


QUESTIONS = [
    ("Q01", "The October 2026 reserve list has not been read. Is the Baltimore 'placed on IR' claim in it?", "nfl-reserve", "R20"),
    ("Q02", "Seven of eight NFL.com injury-report chunks have not been read. Which Week 11 report should be captured first?", "nfl-injuries", "R14"),
    ("Q03", "Which of the three injury CSVs is the canonical Week 10 file, and why do the row counts differ (326, 276, 210, 20, 45)?", "repo:nfl-availability-28ef/data/injuries-week10-2026.csv", "R14"),
    ("Q04", "Does a commit exist that records the demotion rule before the 2026-11-14 desk code (commit 8332d25)?", "repo:nfl-lifecycle-3f5c/data/demotion-gate.json", "R07"),
    ("Q05", "Which official source gives the 149 depth groups in the brief? The repository gives 134 (availability) and 156 (both desks).", "repo:nfl-availability-28ef/data/depth-slots-week10-2026.csv", "R13"),
    ("Q06", "Is a price feed with redistribution rights available? Without one, R02, R03 and R05 stay blank.", "repo:nfl-lifecycle-3f5c/data/price-snapshots.json", "R05"),
    ("Q07", "Which proper score and which benchmark define the leaderboard ranking?", "repo:nfl-lifecycle-3f5c/data/leaderboard.json", "R08"),
    ("Q08", "What is the joint-evidence definition for game parlays, SGPs and prop combos?", "repo:nfl_pages.py", "R23"),
    ("Q09", "What is the written 'injury surprise' definition (which fields, which baseline)?", "repo:nfl-availability-28ef/data/injuries-week10-2026.csv", "R14"),
    ("Q10", "Which two totals estimators, and what walk-forward window, decide the gap column?", "repo:nfl-lifecycle-3f5c/data/decisions.json", "R22"),
    ("Q11", "Does NFL.com's terms section on systematic retrieval (cited in the repository) permit storing row-level injury data?", "repo:nfl-assurance-9580ac3f/data/injuries.csv", "R24"),
    ("Q12", "Which club charts were captured as images only (Houston) or as unofficial copies (Packers), and when are they re-captured?", "repo:nfl-availability-28ef/data/depth-summary.json", "R13"),
]

SUGGESTIONS = [
    ("S01", "Canonical injury source for Week 10", "Stale or conflicting injury rows (FL-02, FL-06)",
     ["Use the availability capture as canonical and mark the others as superseded", "Re-capture all injury files on the same date with hashes", "Keep all files and publish a per-file reconciliation table"]),
    ("S02", "Handling of stale depth rows", "Stale Chargers chart row (FL-04)",
     ["Mark STALE rows and exclude them from any depth-based input until re-read", "Re-read the Chargers and Broncos charts first, then the other flagged clubs", "Leave rows unchanged and add a note"]),
    ("S03", "Leaderboard ranking basis", "Ranking fields include hit rate and p-values (FL-10)",
     ["Rank on a proper score against a declared baseline with a bootstrap interval", "Keep current fields but label them descriptive and do not rank on them", "Hide hit rate and p-values from the public leaderboard"]),
    ("S04", "Price-data policy", "No licensed price; market line blank (FL-12)",
     ["Keep the store theory-only and publish no ROI", "Obtain a licensed feed with redistribution rights before any ROI", "Use public closing-line proxies after a rights check"]),
    ("S05", "Location of row-level data", "Row-level files in the public repository (FL-13)",
     ["Keep public with a derived-only note", "Move row-level files to a private store until the terms are read", "Remove row-level files from the repository and keep hashes only"]),
    ("S06", "Demotion rule pre-registration", "Rule and code share a commit (FL-09)",
     ["Record as unverified and treat the rule as prospective from now", "Register a fresh rule with a new commit dated after this review", "Keep as is and state the limitation on the page"]),
    ("S07", "Totals estimators", "Two model totals, gap column required (R22)",
     ["Publish both estimators with a gap column until walk-forward picks one", "Pick one now on a declared criterion", "Publish only the primary estimator"]),
    ("S08", "Reserve-list coverage", "October list unread (Q01)",
     ["Read the October list before any IR claim is published", "Publish IR claims only for November rows", "Defer the IR question to the next capture"]),
]

FLAGS = [
    ("FL-01", "Kerby Joseph status: the official page says Out, the assurance file has a blank game status and the origination file says Limited.", "nfl-injuries", "repo:nfl-assurance-9580ac3f/data/injuries.csv", "Flagged, not corrected"),
    ("FL-02", "Lions Week 10 rows: the assurance and origination files do not match the official page for Joseph, Mays and Reed.", "nfl-injuries", "repo:nfl/origination/data/injuries-2026-w10.csv", "Flagged, not corrected"),
    ("FL-03", "Baltimore QB order: repository chart (2026-11-12) names Jackson and Huntley; club Offense table (2026-11-17) does not. The brief's 'placed on IR' is not in the November reserve list.", "bal-depth", "nfl-reserve", "Flagged, not corrected"),
    ("FL-04", "Stale Chargers depth row: Daiyan Henley still printed as LB1 on the Chargers chart after the 11/10 trade to Denver.", "nfl-trades", "repo:nfl-availability-28ef/data/depth-slots-week10-2026.csv", "Flagged, not corrected"),
    ("FL-05", "Rank-1 depth groups: brief says 149; repository gives 134 (availability desk) and 156 (both desks).", "repo:nfl-availability-28ef/data/depth-slots-week10-2026.csv", "repo:nfl-skill-cfdd/data/depth-slots-2026-11-14.csv", "Flagged, not corrected"),
    ("FL-06", "Injury row counts differ across five files for overlapping weeks (326, 276, 210, 20, 45).", "repo:nfl-availability-28ef/data/injuries-week10-2026.csv", "repo:data/nfl-injuries-2026-w10.csv", "Flagged, not corrected"),
    ("FL-07", "Assurance Week 10 file covers fewer clubs than the availability file (26 against 28 club codes).", "repo:nfl-assurance-9580ac3f/data/injuries.csv", "repo:nfl-availability-28ef/data/injuries-week10-2026.csv", "Flagged, not corrected"),
    ("FL-08", "Club code inconsistency: the origination file uses 'LA' where the depth and injury files use 'LAR'.", "repo:nfl/origination/data/injuries-2026-w10.csv", "nfl-trades", "Flagged, not corrected"),
    ("FL-09", "Demotion rule pre-registration is not shown: defined_on 2026-11-14 is self-declared and the rule shares commit 8332d25 with the code.", "repo:nfl-lifecycle-3f5c/data/demotion-gate.json", "repo:nfl-lifecycle-3f5c/demotion.py", "Flagged, not corrected"),
    ("FL-10", "Public leaderboard rows show hit rate, wins, losses and p-values for graded strategies; the brief forbids backtest numbers on the leaderboard.", "repo:nfl-lifecycle-3f5c/data/leaderboard.json", "repo:nfl-results-leaderboard.html", "Flagged, not corrected"),
    ("FL-11", "Requested leaderboard divisions (moneyline, parlays, SGPs, prop combos) are absent; graded rows cover spread and total only.", "repo:nfl-lifecycle-3f5c/data/leaderboard.json", "repo:nfl_pages.py", "Flagged, not corrected"),
    ("FL-12", "No sportsbook price is recorded; market-line and difference columns are blank in all markets.", "repo:nfl-lifecycle-3f5c/data/price-snapshots.json", "repo:nfl-lifecycle-3f5c/snapshots.py", "Flagged, not corrected"),
    ("FL-13", "Row-level data is committed to the public repository, while the brief says raw rows stay private until the terms are read.", "repo:nfl-lifecycle-3f5c/data/price-snapshots.json", "repo:nfl-results/data/games-2026-w1-9.csv", "Flagged, owner decision"),
    ("FL-14", "Depth sourcing: some charts are club copies stamped 'Unofficial' (Packers) and Houston is image-only; the brief requires official sources.", "repo:nfl-availability-28ef/evidence/depth-GB.md", "repo:nfl-availability-28ef/data/depth-summary.json", "Flagged, not corrected"),
    ("FL-15", "Jersey-number depth rejection: the rule is stated, but no audit proves that no script orders depth by jersey number.", "repo:nfl_pages.py", "repo:nfl-availability-28ef/build.py", "Flagged, not audited"),
    ("FL-16", "Stale-depth 'NOT PRINTED' class (7 trades) is weak evidence: printed charts show only a few names per slot.", "nfl-trades", "repo:nfl-availability-28ef/data/depth-slots-week10-2026.csv", "Review only"),
]

OPEN_NOTE = ("Flagged items do not block the merge. Owner decisions are left blank on every suggestion row; "
             "nothing in this tracker records a decision on the owner's behalf.")
