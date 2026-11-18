"""Final integration audit content for the 2026-11-18 NFL workspace review.

This module reads existing ledgers and creates a source-linked summary. It does not
refresh NFL datasets, make a price, or infer an unobserved value.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Inventory is explicit so the no-backtest-numbers rule can be reviewed against every NFL
# leaderboard route, including empty/status-only pages and the unmerged PR proposal.
LEADERBOARDS = [
    {"id": "LB-NFL-CANONICAL", "path": "nfl-leaderboard.html", "label": "NFL origination competition", "state": "No entries; charter only", "finding": "The root NFL board publishes a competition charter and candidate-status structure, but no candidate performance rows qualify.", "published": True, "conflict": False, "source_ids": ["REPO"]},
    {"id": "LB-NFL-RESEARCH", "path": "nfl/leaderboard.html", "label": "NFL research desk", "state": "No eligible entries", "finding": "The table states there are no eligible entries; no performance values are published.", "published": True, "conflict": False, "source_ids": ["REPO"]},
    {"id": "LB-ORIGINATION", "path": "nfl/origination/leaderboard.html", "label": "NFL origination desk", "state": "Empty / blank fields", "finding": "Rank and result cells are blank; no candidate performance values are published.", "published": True, "conflict": False, "source_ids": ["REPO"]},
    {"id": "LB-ASSURANCE", "path": "nfl-assurance-9580ac3f/site/leaderboard.html", "label": "NFL assurance desk", "state": "Empty results table", "finding": "The results table has no candidate rows.", "published": True, "conflict": False, "source_ids": ["REPO"]},
    {"id": "LB-COMPETITION", "path": "nfl-competition/site/leaderboard.html", "label": "NFL competition desk", "state": "Backtest metrics on leaderboard", "finding": "Publishes ranks, selection counts, hit rates, p-values / adjusted values and signal scores from retrospective analysis.", "published": True, "conflict": True, "source_ids": ["REPO"]},
    {"id": "LB-LIFECYCLE", "path": "nfl-lifecycle-3f5c/site/leaderboard.html", "label": "NFL lifecycle desk", "state": "Backtest metrics on leaderboard", "finding": "Publishes signal ranks, bets / wins, hit rates, p-values and BH q-values, including provisional or rejected signals.", "published": True, "conflict": True, "source_ids": ["REPO"]},
    {"id": "LB-MARKET", "path": "nfl-market-desk/site/leaderboard.html", "label": "NFL market desk", "state": "Backtest metrics on leaderboard", "finding": "Publishes retrospective sample / hit-rate / significance metrics and ROI / market-error summaries; price and outcomes are on the page.", "published": True, "conflict": True, "source_ids": ["REPO"]},
    {"id": "LB-PRICING", "path": "nfl-pricing/site/leaderboard.html", "label": "NFL pricing desk", "state": "Backtest + assumed-price metrics", "finding": "Publishes hit rate, BH q, Brier and staking units at an assumed -110 price; the page is retrospective, not a prospective qualification board.", "published": True, "conflict": True, "source_ids": ["REPO"]},
    {"id": "LB-RESULTS", "path": "nfl-results-leaderboard.html", "label": "NFL results desk", "state": "Corrected: eligibility only", "finding": "Shows eligibility / not-ranked status; its historical metrics remain on the separate skill-analysis page.", "published": True, "conflict": False, "source_ids": ["REPO"]},
    {"id": "LB-SKILL", "path": "nfl-skill-cfdd/site/leaderboard.html", "label": "NFL skill desk", "state": "Evidence absence only", "finding": "Settled-bet counts are zero and ranks describe missing evidence; no hit-rate or score values are presented.", "published": True, "conflict": False, "source_ids": ["REPO"]},
    {"id": "LB-PR57", "path": "nfl-readiness/site/leaderboard.html", "label": "PR #57 proposal — not published", "state": "Closed unmerged; not published", "finding": "The proposed page ranks 21 retrospective model-market entries and displays Brier skill, clustered bounds, p/q values and directional hit rates; zero qualified does not make it prospective.", "published": False, "conflict": True, "source_ids": ["C756-PR57"]},
    {"id": "LB-NBA-EXCLUDED", "path": "leaderboard.html", "label": "Root leaderboard (NBA)", "state": "Out of NFL scope", "finding": "This root route is an NBA page; it is not counted as an NFL leaderboard.", "published": True, "conflict": False, "source_ids": ["REPO"]},
    {"id": "LB-VERIFIED-REDIRECT", "path": "verified/leaderboard.html", "label": "Legacy compatibility route", "state": "Redirect only; not NFL", "finding": "This legacy URL redirects to the NBA root leaderboard; it contains no NFL data table.", "published": True, "conflict": False, "source_ids": ["REPO"]},
]


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _count_rows(path: str, key: str) -> int:
    return len(_json(path)[key])


def _csv_rows(path: str) -> int:
    with (ROOT / path).open(newline="", encoding="utf-8") as stream:
        return sum(1 for _ in csv.DictReader(stream))


def inventory() -> dict:
    """Return counts from committed artefacts; the assurance ledger is a subset."""
    flags = _json("research/nfl/flags.json")["flags"]
    return {
        "landing": _count_rows("research/nfl-decision-readiness.json", "requirements"),
        "origination_scope": _count_rows("research/nfl-requirements.json", "requirements"),
        "readiness": _count_rows("research/nfl-readiness.json", "rows"),
        "readiness_1467": _count_rows("nfl-readiness-1467fdf7/data/requirements.json", "rows"),
        "readiness_e7ef": _count_rows("nfl-readiness-e7ef/data/readiness.json", "rows"),
        "assurance_subset": _count_rows("nfl-assurance-9580ac3f/decisions.json", "requirements"),
        "saved_result_rows": _csv_rows("nfl-results/data/games-2026-w1-10.csv"),
        "flags_total": len(flags),
        "flags_open": sum(row["status"] == "Needs review" for row in flags),
        "published_nfl_leaderboards": sum(row["published"] and row["id"] not in {"LB-NBA-EXCLUDED", "LB-VERIFIED-REDIRECT", "LB-PR57"} for row in LEADERBOARDS),
        "published_backtest_leaderboard_conflicts": sum(row["published"] and row["conflict"] for row in LEADERBOARDS),
        "unpublished_backtest_leaderboard_proposals": sum(not row["published"] and row["conflict"] for row in LEADERBOARDS),
    }


def render() -> str:
    """Render a compact executive/decision page using the canonical site's helpers."""
    import nfl_pages as p

    counts = inventory()

    def internal(path: str, label: str):
        return p._Markup(f'<a href="{p.esc(path)}">{p.esc(label)} ↗</a>')

    def state(text: str, kind: str):
        return p._Markup(p.badge(text, kind))

    body = p.notice(
        "Executive disposition: the site is a research workspace, not a live betting or reward system.",
        "The combined tree contains originated-line, results, availability and competition artefacts, "
        "but its source policies and evaluation windows are not yet one governed prospective program. "
        "Prices, residuals, ROI, CLV and rewards stay blank unless an authorized, executable price and "
        "a pre-registered settlement policy exist. This audit uses dated repository evidence; it does "
        "not claim that every old row was re-fetched on 2026-11-18.",
        info=True,
    )
    body += p.metrics([
        ("Saved result rows", counts["saved_result_rows"], "Dated NFL schedule transcriptions; not a live feed", "data"),
        ("Landing requirement rows", counts["landing"], "Count is not reconciled with the expanded registers", "requirements"),
        ("Scoped origination register", counts["origination_scope"], "Separate 16-row project-scope register", "requirements"),
        ("Expanded full registers", f"{counts['readiness_1467']} / {counts['readiness_e7ef']} / {counts['readiness']}", "Different counts; no row-level crosswalk establishes why", "audit"),
        ("Open review flags", f"{counts['flags_open']} of {counts['flags_total']}", "Each open item remains visible on Flagged for Review", "review"),
        ("Published NFL leaderboards scanned", counts["published_nfl_leaderboards"], "Status-only and empty pages included", "leaderboard"),
        ("Published backtest leaderboard conflicts", sum(row["published"] and row["conflict"] for row in LEADERBOARDS), "Four specialist pages; one additional PR proposal is not published", "review"),
    ])

    questions = [
        {
            "id": "Q-PRICE",
            "question": "Can market residual, ROI or a reward be stated now?",
            "answer": "No unified, rights-cleared opening-and-closing price policy is recorded across the desks. Keep market and residual fields blank; third-party historical observations are not official NFL prices and are not silently combined.",
            "blocker": "A written price-data policy, an authorized source, timestamped open/close observations, and frozen settlement/stake rules.",
            "artifact": "nfl-lifecycle-3f5c/site/price-snapshots.html",
            "source_ids": ["NFL-TERMS", "C756-NFL-TERMS-1118", "CP-NFL-ODDS-ABSENT", "REPO"],
        },
        {
            "id": "Q-RESULTS",
            "question": "Can historical game outcomes be replayed?",
            "answer": f"The committed results file has {counts['saved_result_rows']} game rows and deterministic checks reproduce it. This is a dated corpus, not a new full-season or prospective evaluation; ROI still requires an executable price and stake policy.",
            "blocker": "For a skill claim: freeze chronological train/validation/holdout seasons and then collect forecasts prospectively before kickoff.",
            "artifact": "nfl-results-games.html",
            "source_ids": ["X29-NFL-SCHEDULE", "E7EF-SCHED-REG10-1117", "REPO"],
        },
        {
            "id": "Q-AVAILABILITY",
            "question": "Does a blank injury-report status mean available, or does a listed player actually play?",
            "answer": "Neither conclusion follows from a blank report cell. The 2026-11-18 partial official read confirms the three named Detroit report rows as Out; it does not establish a complete Week 10 recount or actual participation.",
            "blocker": "Join timestamped official designations to official inactive/Game Book evidence and player-game snaps, preserving missing and conflicting states.",
            "artifact": "nfl-assurance-9580ac3f/site/availability.html",
            "source_ids": ["C756-NFL-INJ-W10-1118", "GB-NFL-GAMEBOOK-PDF", "REPO"],
        },
        {
            "id": "Q-DEPTH",
            "question": "Can a depth-chart row identify the actual replacement and its effect?",
            "answer": "No. Published charts can contain shared or empty slots and can become stale after transactions; chart order is not snaps or confirmed game participation. Jersey order, experience and salary are not substitutes.",
            "blocker": "A club-by-club official source register plus transaction-aware, point-in-time active/inactive and participation evidence; do not trust a team model before the 32-team sweep.",
            "artifact": "nfl-availability-28ef/site/depth.html",
            "source_ids": ["GB-CLUB-DEPTH", "NFL-TERMS", "REPO"],
        },
        {
            "id": "Q-COMBINATIONS",
            "question": "Can parlays or player-prop combinations be ranked?",
            "answer": "Not from multiplying marginal probabilities. A directly validated joint probability and the applicable operator push/void/settlement rules are prerequisites; player-prop outcomes are a separate evidence requirement.",
            "blocker": "A prospectively validated joint model at the exact thresholds, adequate joint samples, and registered settlement rules for each division.",
            "artifact": "nfl-results-correlation.html",
            "source_ids": ["X29-NFL-SCHEDULE", "REPO"],
        },
        {
            "id": "Q-LEADERBOARD",
            "question": "Are all public NFL leaderboards free of backtest results?",
            "answer": "No. The canonical results leaderboard is status-only, but four specialist NFL pages still display historical performance metrics; two other templates retain performance headers without candidate rows. See NF38 on Flagged for Review.",
            "blocker": "A final integration change or a logged owner request for each specialist page; until then, do not use those historical rankings as a prospective skill leaderboard.",
            "artifact": "nfl-review.html",
            "source_ids": ["REPO"],
        },
        {
            "id": "Q-LEDGER",
            "question": "Which requirement count is canonical?",
            "answer": f"The landing ledger has {counts['landing']} rows; a separate {counts['origination_scope']}-row origination register is project-scoped; the three expanded full registers have {counts['readiness_1467']}, {counts['readiness_e7ef']} and {counts['readiness']} rows. The {counts['assurance_subset']}-row assurance register is a subset. Closed PR #57 proposed 132 rows and is excluded. These counts are not reconciled one-to-one.",
            "blocker": "One verbatim requirement inventory, a row-ID crosswalk for split/duplicate wording, and 0 unmatched or duplicated requirements.",
            "artifact": "nfl-readiness.html",
            "source_ids": ["REPO", "C756-PR57"],
        },
        {
            "id": "Q-AUTOMATION",
            "question": "Can scheduled injury/depth collection begin now?",
            "answer": "No scheduled NFL.com collection is enabled. The current official terms read states systematic retrieval is prohibited absent express prior written consent; this is a source-policy gate, not legal advice.",
            "blocker": "Written permission or an authorized licensed feed, plus a retention, freshness and conflict policy.",
            "artifact": "nfl-results-decisions.html",
            "source_ids": ["C756-NFL-TERMS-1118", "NFL-TERMS", "REPO"],
        },
    ]
    body += p.section(
        "Questions that must be answered before a decision",
        p.table(
            "final-audit-questions",
            "Known information, missing information, and decision gates",
            [
                ("Question", lambda row: p.rich(row["question"], row["id"])),
                ("What the repository can say", "answer"),
                ("Gate / number or condition that clears it", "blocker"),
                ("Open the artifact", lambda row: internal(row["artifact"], "Review")),
            ],
            questions,
            note="Source links are attached to every row. A page or table existing is not treated as evidence that its gate has passed.",
        ),
        eyebrow="DECISION READINESS",
        subtitle="The answers below distinguish observations, repository policy and missing evidence; none is filled by inference.",
        sid="decision-questions",
    )

    def leaderboard_link(row):
        path = row["path"]
        if row["id"] == "LB-PR57":
            url = "https://github.com/sassnarep3-star/Own7/blob/04caf1dc5881c3f45a405f07d91ced52e0fbb47b/nfl-readiness/site/leaderboard.html"
            return p._Markup(f'<a href="{p.esc(url)}" target="_blank" rel="noopener noreferrer">Unmerged PR file ↗</a>')
        return internal(path, path)

    body += p.section(
        "Full NFL leaderboard publication audit",
        p.table(
            "nfl-leaderboard-publication-audit",
            "Published NFL leaderboard pages and the unmerged PR proposal",
            [
                ("Page", lambda row: p.rich(row["label"], row["id"])),
                ("Path / review copy", leaderboard_link),
                ("Disposition", "state"),
                ("Observed content", "finding"),
            ],
            LEADERBOARDS,
            note="All ten published NFL leaderboard routes were reviewed. Four published specialist pages contain retrospective performance numbers; the fifth conflict row is the closed, unmerged PR proposal. Empty, blank or status-only boards are not counted as current violations. The root `leaderboard.html` is an NBA page and is excluded. Historical statistics may remain on clearly-labelled analysis pages; this audit does not claim they are live or profitable. Each row links to its repository artifact/PR record; official NFL links are included on rows whose statements rely on external NFL facts, not used to imply that NFL authored this project policy.",
        ),
        eyebrow="NO BACKTEST NUMBERS ON A LEADERBOARD",
        subtitle="This is a publication-policy audit, not a re-test of each desk's underlying analysis.",
        sid="leaderboard-publication-audit",
    )

    ledgers = [
        {"id": "L-16", "name": "Scoped origination requirements", "count": counts["origination_scope"], "scope": "research/nfl-requirements.json; project-scope register, not a full brief crosswalk.", "where": "index.html#origination-requirements", "source_ids": ["REPO"]},
        {"id": "L-70", "name": "Landing brief ledger", "count": counts["landing"], "scope": "Displayed on index.html; published line-by-line brief ledger, not yet crosswalked to other full registers.", "where": "index.html#brief-requirements", "source_ids": ["REPO"]},

        {"id": "L-81", "name": "Expanded readiness register", "count": counts["readiness"], "scope": "research/nfl-readiness.json; full register with decisions and suggestions.", "where": "nfl-readiness.html", "source_ids": ["REPO"]},
        {"id": "L-79", "name": "Readiness desk 1467fdf7", "count": counts["readiness_1467"], "scope": "Separate 2026-11-17 requirement desk; no one-to-one crosswalk to the other full ledgers is established.", "where": "nfl-readiness-1467fdf7/site/index.html", "source_ids": ["REPO"]},
        {"id": "L-80", "name": "Readiness desk e7ef", "count": counts["readiness_e7ef"], "scope": "Separate 2026-11-17 requirement crosswalk; no one-to-one crosswalk to the other full ledgers is established.", "where": "nfl-readiness-e7ef/site/requirement-readiness.html", "source_ids": ["REPO"]},
        {"id": "L-SUBSET", "name": "Assurance subset (not a full ledger)", "count": counts["assurance_subset"], "scope": "20 assurance-only requirements; not comparable as a full brief count.", "where": "nfl-assurance-9580ac3f/site/requirements.html", "source_ids": ["REPO"]},
        {"id": "L-PR57", "name": "Unmerged PR #57 proposal (excluded)", "count": 132, "scope": "Claim stated by the PR body; stale branch is not part of the published site and was not accepted as verified data.", "where": "https://github.com/sassnarep3-star/Own7/pull/57", "source_ids": ["C756-PR57"]},
    ]
    for row in ledgers:
        row["status"] = "Published" if row["id"] == "L-70" else ("Subset" if row["id"] == "L-SUBSET" else "Separate / unmerged")

    def ledger_link(row):
        path = row["where"]
        if path.startswith("https://"):
            return p._Markup(f'<a href="{p.esc(path)}" target="_blank" rel="noopener noreferrer">Open ↗</a>')
        return internal(path, "Open")

    body += p.section(
        "Requirement ledgers do not yet reconcile",
        p.table(
            "requirement-ledger-inventory",
            "Repository requirement ledgers",
            [
                ("Ledger", lambda row: p.rich(row["name"], row["id"])),
                ("Rows", "count"),
                ("Scope", "scope"),
                ("Disposition", "status"),
                ("Inspect", ledger_link),
            ],
            ledgers,
            note="The 16-row originator register is project-scoped, not a full brief count. The 20-row assurance ledger is a subset. PR #57 is unmerged and excluded. The root landing's 70-row count must not be described as exhaustively reconciled until a verbatim crosswalk yields zero unmatched and zero duplicate requirement IDs.",
        ),
        eyebrow="TRACEABILITY",
        subtitle="The row-count differences are observed repository facts, not a conclusion that one ledger is correct.",
        sid="ledger-inventory",
    )

    live_checks = [
        {"id": "SRC-TERMS", "check": "NFL.com terms, Section 1.3", "observation": "Read 2026-11-18, first rendered chunk (index 0; 9 total); the page is dated 2024-05-16. The section limits use to individual non-commercial informational purposes and prohibits systematic retrieval without express prior written consent.", "limitation": "Text check only; no permission/licence is recorded and this is not legal advice.", "source_ids": ["C756-NFL-TERMS-1118"]},
        {"id": "SRC-INJ-DET", "check": "Week 10 injury report, Detroit rows", "observation": "Read 2026-11-18, first rendered chunk (index 0; 8 total). Kerby Joseph, Cade Mays and D.J. Reed each display Game Status Out in the official page.", "limitation": "Only the first of eight rendered chunks was read; no complete report recount or raw row-level copy was retained.", "source_ids": ["C756-NFL-INJ-W10-1118"]},
        {"id": "SRC-SCHED", "check": "Week 10 schedule", "observation": "Read 2026-11-18, first rendered chunk (index 0; 2 total); saved result artefacts were not refreshed or overwritten.", "limitation": "Partial page read; not a re-verification of the full 149-row results corpus.", "source_ids": ["C756-NFL-SCHED-W10-1118"]},
    ]
    body += p.section(
        "Focused official-source checks on 2026-11-18",
        p.table(
            "final-audit-live-checks",
            "Official pages read during this integration review",
            [
                ("Source check", lambda row: p.rich(row["check"], row["id"])),
                ("Observed", "observation"),
                ("Scope / limitation", "limitation"),
            ],
            live_checks,
            note="These are limited rendered-page checks, not immutable archives. NFL.com terms restrict systematic collection; no scheduled snapshot job was enabled.",
        ),
        eyebrow="SOURCE REVIEW",
        sid="source-checks",
    )

    suggestions = [
        {"id": "S1", "proposal": "Reconcile the requirement ledgers before claiming complete coverage.", "gate": "One verbatim inventory; 0 unmatched and 0 duplicate requirement IDs across the root and expanded registers.", "next": "Use the existing line-by-line ledgers as inputs; do not add new rows without matching a verbatim requirement.", "source_ids": ["REPO"]},
        {"id": "S2", "proposal": "Make leaderboard publication prospective-only; move historical results to clearly labelled skill-analysis pages.", "gate": "A site-wide scan finds 0 backtest-derived metric cells or ranks on any page named leaderboard; prospective entries have frozen registration and eligibility status only.", "next": "Log a scoped request for each specialist desk; preserve analysis artifacts, but do not present their backtest ranks as prospective skill.", "source_ids": ["REPO"]},
        {"id": "S3", "proposal": "Resolve price rights and one market-data policy before publishing residuals or returns.", "gate": "One authorized provider with documented rights and timestamped open/close coverage for every originated market, plus frozen vig and settlement rules.", "next": "Until this exists, keep market lines, residuals, CLV, ROI and reward cells blank.", "source_ids": ["C756-NFL-TERMS-1118", "NFL-TERMS", "REPO"]},
        {"id": "S4", "proposal": "Build an authorized, point-in-time availability series with actual participation evidence.", "gate": "32/32 club source route verified; official report/depth/roster/inactive/transaction snapshots retain timestamps and conflict states; actual starters and snaps joined by game.", "next": "Do not infer starters from jersey number, chart order, experience or salary; do not start scheduled retrieval without permission.", "source_ids": ["C756-NFL-TERMS-1118", "C756-NFL-INJ-W10-1118", "GB-NFL-GAMEBOOK-PDF", "REPO"]},
        {"id": "S5", "proposal": "Freeze a singles-only prospective baseline before kickoff; keep combinations behind direct joint validation.", "gate": "Registration commit predates the window; chronological holdout, proper-score controls, uncertainty and multiplicity are published; joint combos have direct joint evidence and operator settlement rules.", "next": "No prospective score or reward is reported until its gate passes.", "source_ids": ["X29-NFL-SCHEDULE", "REPO"]},
    ]
    body += p.section(
        "Suggestions to review before implementation",
        p.table(
            "final-audit-suggestions",
            "Suggested next steps",
            [
                ("Proposal", lambda row: p.rich(row["proposal"], row["id"])),
                ("Acceptance gate", "gate"),
                ("Safe next action", "next"),
            ],
            suggestions,
            note="These are recommendations, not completed work or owner approvals. The existing suggestions register remains available for full rationale and acceptance tests.",
        ),
        eyebrow="SUGGESTIONS",
        subtitle="Prioritize permissions and data integrity before adding more model complexity.",
        sid="audit-suggestions",
    )

    body += p.section(
        "Existing review pages",
        '<div class="grid-3">'
        '<a class="path-card" href="nfl-suggestions.html"><span class="step">01 / REVIEW</span><h3>Suggestions</h3><p>Prioritized proposals, prerequisites and acceptance tests.</p><span class="card-link">Open suggestions →</span></a>'
        '<a class="path-card" href="nfl-questions.html"><span class="step">02 / ANSWERS</span><h3>Questions</h3><p>What is sourced, what remains unknown, and what would close each gap.</p><span class="card-link">Open questions →</span></a>'
        '<a class="path-card" href="nfl-review.html"><span class="step">03 / FLAGS</span><h3>Flagged for Review</h3><p>Non-blocking irregularities and unverified claims with source links.</p><span class="card-link">Open review register →</span></a>'
        '</div>',
        eyebrow="RELATED PAGES",
    )
    return body
