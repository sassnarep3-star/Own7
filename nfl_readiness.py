"""Decision-readiness rows, the removal-of-luck panel and the Lions read-back.

Session arena/34a52a38-own7 (2026-11-17). Pure data and arithmetic: every number is computed at
build time from a committed artefact, or is a dated official read recorded below with its source.
A blank means the value is not in the record; it is never filled with a zero or an estimate.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _csv(rel: str) -> list[dict]:
    with open(ROOT / rel, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


# --- Official read of the Week 10 injury report, Detroit section, taken 2026-11-17 -----------------
# Source: https://www.nfl.com/injuries/league/2026/REG10 (Arena fetch_page, rendered text, chunk 1
# of 8; the Lions section is inside that chunk). A blank value means the official cell is empty.
OFFICIAL_READ_ID = "NFL-INJ-W10-READ-1117"
OFFICIAL_READ_URL = "https://www.nfl.com/injuries/league/2026/REG10"
OFFICIAL_READ_DATE = "2026-11-17"
LIONS_OFFICIAL = [
    # player, position, injury, practice status, game status
    ("Brian Branch", "S", "", "Full Participation in Practice", ""),
    ("Jared Goff", "QB", "", "Full Participation in Practice", ""),
    ("Kerby Joseph", "S", "Knee", "Did Not Participate In Practice", "Out"),
    ("Cade Mays", "C", "Ankle", "Did Not Participate In Practice", "Out"),
    ("D.J. Reed", "CB", "Hip", "Did Not Participate In Practice", "Out"),
    ("Jacob Saylors", "RB", "", "Full Participation in Practice", ""),
    ("Amon-Ra St. Brown", "WR", "Rib", "Limited Participation in Practice", "Questionable"),
    ("Sione Vaki", "RB", "Ankle", "Limited Participation in Practice", "Questionable"),
    ("DJ Wonnum", "DE", "", "Full Participation in Practice", ""),
]

AVAIL_PATH = "nfl-availability-28ef/data/injuries-week10-2026.csv"
ASSUR_PATH = "nfl-assurance-9580ac3f/data/injuries.csv"
RESULTS_PATH = "nfl-results/data/games-2026-w1-9.csv"
DEPTH_PATH = "nfl-availability-28ef/data/depth-slots-week10-2026.csv"


def _norm(value: str) -> str:
    return (value or "").strip()


def lions_delta() -> list[dict]:
    """Official read versus the two immutable desk captures (both dated/undated as stated)."""
    avail = {r["player"]: r for r in _csv(AVAIL_PATH) if r["club_abbr"] == "DET"}
    assur = {r["player"]: r for r in _csv(ASSUR_PATH) if r["team"] == "DET"}
    out = []
    for player, pos, inj, prac, game in LIONS_OFFICIAL:
        a = avail[player]
        s = assur[player]
        official = (inj, prac, game)
        a_vals = (_norm(a["injury"]), _norm(a["practice_status"]), _norm(a["game_status"]))
        s_vals = (_norm(s["injury"]), _norm(s["practice_status"]), _norm(s["game_status"]))
        names = ("injury", "practice", "game status")
        a_diff = [names[i] for i in range(3) if a_vals[i] != official[i]]
        s_diff = [names[i] for i in range(3) if s_vals[i] != official[i]]
        out.append({
            "player": player, "position": pos, "official": official,
            "availability": a_vals, "availability_checked_on": a["checked_on"],
            "assurance": s_vals,
            "availability_diff": a_diff, "assurance_diff": s_diff,
        })
    return out


def _fmt(values: tuple[str, str, str]) -> str:
    return " / ".join(v if v else "—" for v in values)


def luck_panel() -> dict:
    """Removal-of-luck figures, read from nfl-results/analysis.json (no re-estimation)."""
    res = _json("nfl-results/analysis.json")
    luck = res["luck_analysis"]
    best_id = luck["best_observed"]["id"]
    best = next(c for c in res["candidates"] if c["id"] == best_id)
    stat = best["stat"]
    p1 = luck["p_best_single_test"]
    n_family_stated = luck["strategies_tested"]
    n_graded = res["leaderboard_counts"]["tested"]
    fw_stated = luck["family_wise_false_positive"]
    fw_graded = 1 - (1 - p1) ** n_graded
    return {
        "best_id": best_id,
        "wins": stat["wins"], "losses": stat["losses"], "bets": stat["bets"],
        "hit": stat["hit_rate"], "ci_low": stat["ci_low"], "ci_high": stat["ci_high"],
        "band_low": stat["luck_band_low"], "band_high": stat["luck_band_high"],
        "p_single": p1,
        "perm_p": res["benchmarks"]["spread"]["permutation_p_value"],
        "bh_q": stat["q_value"] if "q_value" in stat else best["q_value"],
        "first_half": stat["first_half_hit_rate"], "second_half": stat["second_half_hit_rate"],
        "n_family_stated": n_family_stated, "fw_stated": fw_stated,
        "n_graded": n_graded, "fw_graded": fw_graded,
        "fw_stated_recomputed": 1 - (1 - p1) ** n_family_stated,
    }


def readiness_rows() -> list[dict]:
    """One row per requirement in the 2026-11-17 brief. status: Done | Partial | Blocked | Not started."""
    price = _json("nfl-lifecycle-3f5c/data/price-snapshots.json")
    stages = [m[st] for m in price["markets"] for st in ("opening", "closing") if st in m]
    market_lines = sum(1 for s in stages if s.get("market_line") is not None)
    fair_lines = sum(1 for s in stages if s.get("fair_line") is not None)
    repl = _json("nfl-lifecycle-3f5c/data/replacement-depth.json")["counts"]
    corr = _json("nfl-lifecycle-3f5c/data/correlation-audit.json")
    demo = _json("nfl-lifecycle-3f5c/data/demotion-gate.json")
    origin = _json("nfl-lifecycle-3f5c/data/origination-order.json")["reconciliation"]
    res = _json("nfl-results/analysis.json")
    avail = _csv(AVAIL_PATH)
    assur = _csv(ASSUR_PATH)
    depth = _csv(DEPTH_PATH)
    games = _csv(RESULTS_PATH)
    w7 = _csv("data/nfl-injuries-week7-2026.csv")
    club_rows = _csv("nfl-availability-28ef/data/club-summary-week10-2026.csv")
    multi = sum(1 for r in depth if r["cell_holds_multiple"] == "yes")
    luck = luck_panel()
    nfl_csv = sorted(p for p in ROOT.rglob("*.csv") if ".git" not in p.parts and "nfl" in str(p).lower())
    nfl_csv_count = len(nfl_csv)
    n_stage = len(stages)
    rows = [
        # --- Originate, price, verify -------------------------------------------------------------
        ("RQ01", "Price-snapshot store: opening and closing numbers for every originated market",
         "Partial", "No licensed price with a capture time; price-data policy not decided (NF05, NF06); NFL.com has no odds page at /odds/",
         f"{n_stage} stage cells (42 markets × open/close); {market_lines} with a market line",
         f"{n_stage} of {n_stage} stage cells with a market line and capture time",
         "nfl-lifecycle-3f5c/site/price-snapshots.html", ["NFL-ODDS-PATH", "NFL-TERMS"]),
        ("RQ02", "Verified results feed for backtests and ROI",
         "Partial", "ROI blocked: no executable price (gate RG03); Week 10 finals not in the feed",
         f"{len(games)} official final scores, Weeks 1–9",
         f"{len(games) + 14} = {len(games)} + 14 Week 10 finals, each with a price",
         "nfl-results-games.html", ["NFL-SCHEDULE", "NFL-STANDINGS"]),
        ("RQ03", "Originate the side first, then the total, then the moneyline",
         "Done", "None for the order; prices remain blank (RQ01)",
         f"{origin['checked_games']} of {origin['checked_games']} games reconcile with the canonical engine; {len(origin['mismatches'])} mismatches",
         "Done (order enforced by test)",
         "nfl-lifecycle-3f5c/site/origination-order.html", ["REPO"]),
        ("RQ04", "Fair line, market line and difference as separate columns",
         "Partial", "Market line blank in every stage cell (RQ01); difference therefore blank",
         f"{fair_lines} of {n_stage} stage cells hold a model fair line; {market_lines} hold a market line",
         f"{n_stage} of {n_stage} with fair and market line; difference computed for each",
         "nfl-lifecycle-3f5c/site/fair-market-diff.html", ["REPO"]),
        ("RQ05", "Signal separated from staking in the leaderboard",
         "Done", "Desk-level only; the canonical results leaderboard is not yet split (logged as LS10)",
         "Rank computed from signal fields only (test-enforced)",
         "Canonical leaderboard adopts the split",
         "nfl-lifecycle-3f5c/site/leaderboard.html", ["REPO"]),
        ("RQ06", "Leaderboard never shows backtest numbers; every strategy pre-registered",
         "Done", "Corrected 2026-11-17 on the results leaderboard; other desks' leaderboards still show hit-rate columns (NF38)",
         f"0 backtest metrics on the results leaderboard; {res['leaderboard_counts']['tested']} variants listed, none ranked",
         "Every desk's leaderboard passes the same check",
         "nfl-results-leaderboard.html", ["REPO"]),
        ("RQ07", "Pre-register each strategy; freeze the rule before results are seen",
         "Partial", "No strategy-level registration hash; the only dated rule is DG-1 (2026-11-14)",
         "1 rule dated (DG-1); 0 strategy-level registration hashes in the results or lifecycle data",
         "Each strategy carries a commit hash taken before its evaluation window opens",
         "nfl-lifecycle-3f5c/site/demotion.html", ["REPO"]),
        ("RQ08", "Demotion gate: a live strategy goes back to paper",
         "Done", "No strategy is live, so the gate has not fired",
         f"{demo['demotion_count']} demotions; armed: {str(demo['armed']).lower()}",
         "Applies once a strategy is live (none is)",
         "nfl-lifecycle-3f5c/site/demotion.html", ["REPO"]),
        ("RQ09", "Correlations computed only from official numbers, with n published",
         "Done", f"{corr['blank_by_rule']} rows blank by rule (n below 3 or no source)",
         f"{corr['with_coefficients']} of {corr['audited_rows']} rows carry a coefficient and n; {corr['failed']} failures",
         f"{corr['audited_rows']} of {corr['audited_rows']} audited with n and a source",
         "nfl-lifecycle-3f5c/site/correlation-audit.html", ["REPO"]),
        ("RQ10", "Model outputs stored as a probability plus its inputs, not just a pick",
         "Partial", "Results models forecast margins and totals; no win probability is stored",
         "0 probabilities stored; 7 margin and total models (M00–M06) store forecasts only",
         "Every forecast stored as a probability with its inputs",
         "nfl-results-skill.html", ["REPO"]),
        ("RQ11", "Price our own line and publish the residual against the market, on a schedule",
         "Blocked", "No market line (RQ01); no scheduled capture permitted without written consent (RQ18)",
         "0 residuals published",
         "84 of 84 stage cells with a dated market line",
         "nfl-lifecycle-3f5c/site/fair-market-diff.html", ["NFL-TERMS"]),
        ("RQ12", "Turn the 136-game log into the pre-registered backtest corpus",
         "Partial", "Corpus exists; no registration hash recorded before scoring",
         f"{len(games)} games in the corpus, one season (2026)",
         "Corpus with a registration hash dated before the scoring window",
         "nfl-results-games.html", ["NFL-SCHEDULE"]),
        ("RQ13", "Decide the price-data policy before any backtest is published",
         "Blocked", "No policy decision recorded; source-use restriction open (NF06)",
         "0 signed policy decisions",
         "1 signed decision by the owner",
         "nfl-review.html", ["NFL-TERMS"]),
        ("RQ14", "Two-stage leaderboard: proper-score qualification, then prospective CLV/ROI escrow",
         "Blocked", "No closing price, so CLV and ROI are undefined",
         "0 CLV values; 0 ROI values",
         "A prospective multi-week sample with a licensed closing price",
         "nfl-results-leaderboard.html", ["NFL-TERMS"]),
        ("RQ15", "Vig-free market consensus against the originated fair line",
         "Blocked", "No market prices (RQ01)",
         f"0 of {n_stage} market stage cells",
         f"{n_stage} of {n_stage} with a market price",
         "nfl-lifecycle-3f5c/site/fair-market-diff.html", ["REPO"]),
        ("RQ16", "Rank with Brier skill, a game-cluster lower bound and a multiplicity adjustment",
         "Partial", "Family-wise multiplicity computed; no Brier score or cluster lower bound in the artefacts",
         f"Family-wise false-positive {luck['fw_stated']:.1%} ({luck['n_family_stated']} tests stated)",
         "Brier skill with a game-cluster lower bound over all graded variants",
         "nfl-results-skill.html", ["REPO"]),
        ("RQ17", "Proper-score divisions: singles, game parlays, same-game parlays, prop combos",
         "Not started", "Only singles (spread and total) are graded; combos need joint evidence (RQ37)",
         "1 of 4 divisions (singles)",
         "4 of 4 divisions, each ranked separately",
         "nfl-results-leaderboard.html", ["REPO"]),
        ("RQ18", "Scheduled capture of injury reports and depth pages with retained hashes",
         "Blocked", "Scheduled retrieval of NFL.com conflicts with terms §1.3 (systematic retrieval) without written consent (NF35)",
         "0 scheduled captures; 1 dated official read (2026-11-17), from one page read",
         "Written permission or a licensed feed, then a dated read every day from Wednesday to kickoff",
         "nfl-review.html", ["NFL-TERMS", "NFL-INJURY-POLICY"]),
        ("RQ19", "Injury report as a timestamped series, with a clock time on each read",
         "Partial", "Captures carry a date only, no clock time; no delta is published from a series",
         f"0 clock-timed reads; {len(avail)} Week 10 rows captured on 2026-11-13 (date only)",
         "Every read timed; deltas published for each designation change",
         "nfl-availability-28ef/site/availability.html", ["NFL-INJ-W10-READ-1117", "NFL-INJ-W10-RECHECK-1114"]),
        ("RQ20", "Lions Week 10 designations (Joseph, Mays, Reed) populated from the official page",
         "Done", "Captures are immutable and dated 2026-11-13, so the official read is published as a delta instead of overwriting them",
         "3 of 3 confirmed Out on the official page (2026-11-17); see delta table",
         "Done",
         "#lions-delta", [OFFICIAL_READ_ID]),
        ("RQ21", "Re-capture and republish the Week 10 injury tables; reconcile the row counts",
         "Partial", "Three desks hold three counts for one report, and no full official recount was done (NF33)",
         f"{len(avail)} rows (availability desk) · {len(assur)} (assurance desk) · 20 (research extract)",
         "One complete official recount that matches every row (8 chunks)",
         "nfl-availability-28ef/site/availability.html", [OFFICIAL_READ_ID, "NFL-INJ-W10-RECHECK-1114"]),
        ("RQ22", "Availability graph: who was expected to start, and who actually did",
         "Not started", "No official Game Book or inactive list captured",
         "0 Game Books; 0 inactive-list datasets",
         f"{len(games)} of {len(games)} games with official starters and game-day status",
         "nfl-injuries.html", ["NFL-INJURY"]),
        ("RQ23", "Use official Game Books for actual starters and game-day status",
         "Not started", "Game Books not retrieved",
         "0 of 136 games",
         "136 of 136 games (weeks 1–9 first)",
         "nfl-injuries.html", ["NFL-INJURY"]),
        ("RQ24", "Depth from playing time (snap counts), not jersey order",
         "Not started", "No snap-count source captured; route (b) unverified",
         "0 clubs on the snap-count route",
         "32 of 32 clubs with verified snap counts",
         "nfl-lifecycle-3f5c/site/replacement-depth.html", ["NFL-DEPTH-PATH"]),
        ("RQ25", "Depth-order source verified for all 32 clubs before a backup-deficiency feature",
         "Partial", "Route (a) printed charts: Houston is an image and was not transcribed (NF15)",
         "31 of 32 clubs with a printed chart (cfdd desk scope note)",
         "32 of 32 clubs verified by one route",
         "nfl-availability-28ef/site/depth.html", ["NFL-DEPTH-PATH"]),
        ("RQ26", "Depth slots as groups: shared and empty slots shown faithfully",
         "Done", "Shared cells listed as shared; they carry no individual rank",
         f"{multi} of {len(depth)} printed slot rows hold more than one player",
         "Every shared cell labelled",
         "nfl-availability-28ef/site/depth.html", ["NFL-DEPTH-PATH"]),
        ("RQ27", "Replacement depth, not only the fact of a replacement",
         "Partial", f"{repl['no_named_backup']} starter losses have no named backup; {repl['not_on_chart']} injury rows are not on a printed chart",
         f"{repl['starter_losses_with_named_backup']} of {repl['starter_losses']} starter losses have a named printed backup",
         f"{repl['starter_losses']} of {repl['starter_losses']} with a dated, named printed slot",
         "nfl-lifecycle-3f5c/site/replacement-depth.html", ["NFL-DEPTH-PATH"]),
        ("RQ28", "Model depth as groups, not a single starter (for example three rank-1 receivers)",
         "Partial", "The depth tables keep rank and shared cells; no group model is fitted",
         f"{multi} shared printed cells recorded",
         "Every rank-1 group modelled as a group",
         "nfl-availability-28ef/site/depth.html", ["NFL-DEPTH-PATH"]),
        ("RQ29", "Texans depth published as an image: obtain an authorised structured source",
         "Blocked", "Chart is an image; transcription by eye is not permitted",
         "0 of 1 authorised structured sources",
         "1 authorised structured source for Houston",
         "nfl-availability-28ef/site/depth.html", ["NFL-DEPTH-PATH"]),
        ("RQ30", "Flag stale depth rows against the official transactions log",
         "Blocked", "No transactions log captured (roster events unknown)",
         "0 transactions logged",
         "Every depth row checked against a dated transaction log",
         "nfl-review.html", ["NFL-STANDINGS"]),
        ("RQ31", "Dated depth register: date and source on every row",
         "Done", "Club sites are the source; Houston excluded",
         f"{len(depth)} of {len(depth)} printed slot rows carry a date and source",
         "Done for every club with a chart",
         "nfl-availability-28ef/site/depth.html", ["NFL-DEPTH-PATH"]),
        ("RQ32", "Roster turnover as a dated event (trades, releases, IR moves)",
         "Not started", "No transaction log; depth is not versioned against roster events",
         "0 dated roster events",
         "Each starter change tied to its official dated event",
         "nfl-review.html", ["NFL-STANDINGS"]),
        ("RQ33", "Announced-starter evidence field, with no inferred replacement",
         "Not started", "No official dated starter announcement captured",
         "0 announcements captured",
         "Each announced starter with its official source and date",
         "nfl-review.html", ["NFL-STANDINGS"]),
        ("RQ34", "32-team roster and IR sweep before any team-level model is trusted",
         "Not started", "No reserve or IR list captured",
         "0 of 32 reserve lists",
         "32 of 32 dated reserve lists",
         "nfl-injuries.html", ["NFL-INJURY"]),
        ("RQ35", "Injury signal as a surprise against the prior read, never a level",
         "Blocked", "Needs two dated reads per player per game week (RQ19, RQ18)",
         "1 of 9 scored weeks archived (Week 7)",
         "9 of 9 scored weeks with two dated reads each",
         "nfl-injuries.html", ["NFL-INJURY"]),
        ("RQ36", "Archive official weekly injury reports for past seasons",
         "Blocked", "Systematic retrieval needs written consent (terms §1.3, NF35)",
         f"1 of 9 scored weeks archived ({len(w7)} Week 7 rows, replacement and deficiency blank)",
         "9 of 9 scored weeks",
         "nfl-injuries.html", ["NFL-INJURY", "NFL-TERMS"]),
        ("RQ37", "Injury and personnel ablations: identical model with and without the features",
         "Not started", "No with/without model has been fitted",
         "0 ablations run",
         "1 chronological holdout comparison with uncertainty",
         "nfl-validation.html", ["REPO"]),
        ("RQ38", "Joint-evidence gate for parlays and prop combos",
         "Done", "No validated joint probability; player-prop logs not retrieved (NM01)",
         "0 combos ranked",
         "A validated joint probability and the operator's void and push rules",
         "nfl-results-correlation.html", ["REPO"]),
        ("RQ39", "Control baseline on every leaderboard run (random picks, favourites only)",
         "Partial", "Neutral league-mean and home-field-only nulls exist; random-pick and favourites-only baselines do not",
         "2 nulls (neutral line, home-field-only); 0 random or favourites baselines",
         "Random and favourites baselines in every run",
         "nfl-results-skill.html", ["REPO"]),
        ("RQ40", "Two-sided 'what would change our mind' field on every strategy",
         "Not started", "No per-strategy field exists; the phrase appears nowhere in the repository",
         f"0 of {len(res['candidates'])} graded variants carry the field",
         f"{len(res['candidates'])} of {len(res['candidates'])} with both sides stated",
         "nfl-results-leaderboard.html", ["REPO"]),
        ("RQ41", "Public analysis layer; raw row-level data held in a private store",
         "Blocked", f"{nfl_csv_count} NFL-named CSV files are committed and served by the public site; the rights gate (RG10) says nothing is released (NF34)",
         f"{nfl_csv_count} public NFL-named CSV files",
         "0 row-level files public, or written permission recorded",
         "nfl-review.html", ["NFL-TERMS", "REPO"]),
        ("RQ42", "Alerts on source and schema change, with freshness monitoring",
         "Partial", "Build fails on drift for three extracts; no alert channel is configured",
         "3 extract row-count pins (32 / 20 / 14) enforced in CI; 0 alert channels",
         "1 alert channel with a freshness threshold",
         "nfl-review.html", ["REPO"]),
        ("RQ43", "Weekly 'what changed' diff rather than a static snapshot",
         "Not started", "Needs two dated weekly snapshots of one table",
         "0 published diffs",
         "1 published diff per week, from Week 11",
         "nfl-review.html", ["REPO"]),
        ("RQ44", "Every model total published twice until one estimator wins, with a gap column",
         "Partial", "Seven total variants exist (M00–M06); no paired gap column in a published page",
         "7 total variants in the results analysis",
         "Paired estimators with a gap column until a walk-forward test picks one",
         "nfl-results-skill.html", ["REPO"]),
        ("RQ45", "Per-team view: starters out, replacements named, net injury count",
         "Partial", "Net injury count is not defined in the artefacts",
         f"{len(club_rows)} clubs with a Week 10 summary (4 clubs on bye)",
         "32 clubs with a defined net count",
         "nfl-availability-28ef/site/clubs.html", ["NFL-INJ-W10-RECHECK-1114"]),
        ("RQ46", "Interactive offense-vs-defense matchup matrix (1st–4th string)",
         "Not started", "Depends on RQ24–RQ27",
         "0 matrix cells",
         "All 32 clubs by unit and string",
         "nfl-availability-28ef/site/depth.html", ["NFL-DEPTH-PATH"]),
        ("RQ47", "Stadium roof, surface and NWS hourly wind and precipitation overlay",
         "Not started", "No roof/surface record and no weather grid captured",
         "0 of 150 fixtures with a roof or weather value",
         "150 of 150 fixtures (136 + 14) with a dated value each",
         "nfl-results-games.html", ["NFL-SCHEDULE"]),
        ("RQ48", "Venue of every fixture from the official game centre",
         "Not started", "The results file has no venue column",
         f"0 of {len(games)} venues transcribed",
         f"{len(games)} of {len(games)} venues with a source",
         "nfl-results-games.html", ["NFL-SCHEDULE"]),
        ("RQ49", "Fixture-context features from published schedule facts only",
         "Partial", "Venue and roof not captured (RQ47, RQ48); rest-day and schedule facts unverified",
         "0 fixture-context features published",
         "Feature set built only from captured schedule facts",
         "nfl-results-games.html", ["NFL-SCHEDULE"]),
        ("RQ50", "Injury-hub read stored with its clock time; publish the delta, not the level",
         "Partial", "Same gap as RQ19: no clock time and no series",
         "1 dated official read (2026-11-17) published as a delta, 9 rows",
         "A timed series from Wednesday to kickoff",
         "#lions-delta", [OFFICIAL_READ_ID]),
        ("RQ51", "Calibrate what 'Questionable' means from outcomes, not from old percentages",
         "Blocked", "Needs inactive lists, which are not captured (RQ22)",
         "0 designations measured",
         "Pre-registered sample size of Questionable players with outcomes (size not yet set)",
         "nfl-injuries.html", ["NFL-INJURY-POLICY"]),
        ("RQ52", "Injury-designation reliability (play rate per designation, with confidence intervals)",
         "Blocked", "Needs inactive lists over several seasons",
         "0 seasons joined",
         "Pre-registered season count (not yet set), joined to inactive lists",
         "nfl-injuries.html", ["NFL-INJURY-POLICY"]),
        ("RQ53", "Train, validation and final-holdout seasons",
         "Not started", "One season in the record",
         "1 season archived (2026)",
         "At least one prior season archived, with the split pre-registered",
         "nfl-validation.html", ["REPO"]),
        ("RQ54", "Kickoff and declared onside-kick regime priors",
         "Not started", "No kickoff or onside data captured",
         "0 seasons with priors",
         "Pre-registered priors with a source for each season",
         "nfl-validation.html", ["REPO"]),
        ("RQ55", "Reject ranking strategies by season-long ROI",
         "Not started", "The brief's rejection ID (SG-03) is not in the repository; the rule is not recorded",
         "0 recorded rejections of this proposal",
         "Rule recorded and dated",
         "nfl-suggestions.html", ["REPO"]),
        ("RQ56", "Reject depth order derived from jersey number, experience or salary",
         "Not started", "The brief's rejection ID (SG-05) is not in the repository; the rule is not recorded",
         "0 recorded rejections of this proposal",
         "Rule recorded and dated",
         "nfl-suggestions.html", ["REPO"]),
        ("RQ57", "Decision-readiness table on the landing page, one row per requirement",
         "Done", "None",
         f"{'{ROWS}'} rows published with gate and clearing number",
         "Done",
         "index.html", ["REPO"]),
        ("RQ58", "Removal-of-luck panel on the dashboard",
         "Done", "Family size disputed: 18 stated, 30 graded (NF37)",
         f"Family-wise {luck['fw_stated']:.1%} (18 stated) · {luck['fw_graded']:.1%} (30 graded)",
         "Done",
         "index.html#luck-panel", ["REPO"]),
        ("RQ59", "Executive summary with the important details",
         "Done", "Refreshed 2026-11-17 (dated update section)",
         "1 executive summary; dated update added",
         "Done",
         "executive-summary.html", ["REPO"]),
        ("RQ60", "Suggestions and questions, each with the evidence it needs",
         "Done", "Suggestions are proposals only and are not implemented",
         f"{len(_json('research/nfl-suggestions.json')['suggestions'])} suggestions published, none implemented",
         "Done",
         "nfl-suggestions.html", ["REPO"]),
    ]
    out = []
    for rid, req, status, gate, now, clears, href, sids in rows:
        out.append({"id": rid, "requirement": req, "status": status, "gate": gate,
                    "now": now, "clears": clears, "href": href, "source_ids": sids})
    total = len(out)
    for row in out:
        row["now"] = row["now"].replace("{ROWS}", str(total))
    return out
