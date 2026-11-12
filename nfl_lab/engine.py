"""NFL line origination, validation and skill/luck decomposition.

Deterministic: identical inputs produce identical outputs. Any input that fails its
receipt check aborts the run rather than publishing a number.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

from . import math as m

ROOT = Path(__file__).resolve().parent.parent


def load_json(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def load_csv(relative: str) -> list[dict]:
    import csv
    with (ROOT / relative).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def round_value(value, places: int = 4):
    if isinstance(value, float):
        return round(value, places)
    if isinstance(value, dict):
        return {k: round_value(v, places) for k, v in value.items()}
    if isinstance(value, list):
        return [round_value(v, places) for v in value]
    return value


def verify_receipts() -> dict:
    receipts = load_json("research/nfl/receipts.json")
    for entry in receipts["datasets"]:
        rows = load_csv(entry["file"])
        if len(rows) != entry["rows"]:
            raise ValueError(f"Receipt row count mismatch: {entry['file']}")
        for row in rows:
            if row.get("SourceURL") != entry["source_url"]:
                raise ValueError(f"Row source mismatch in {entry['file']}")
            if not row.get("CheckedOn"):
                raise ValueError(f"Row without a check date in {entry['file']}")
    return receipts


def team_table(standings: list[dict]) -> tuple[list[dict], float]:
    team_games = sum(int(r["W"]) + int(r["L"]) + int(r["T"]) for r in standings)
    league_ppg = sum(int(r["PF"]) for r in standings) / team_games
    teams = []
    for r in standings:
        games = int(r["W"]) + int(r["L"]) + int(r["T"])
        pf, pa = int(r["PF"]), int(r["PA"])
        expected = m.expected_wins(pf, pa, games)
        teams.append({
            "id": r["TeamCode"],
            "team": r["Team"],
            "conference": r["Conference"],
            "games": games,
            "w": int(r["W"]), "l": int(r["L"]), "t": int(r["T"]),
            "pct": float(r["PCT"]),
            "pf": pf, "pa": pa, "net": int(r["NetPts"]),
            "off_ppg": m.scoring_rate(pf, games),
            "def_ppa": m.scoring_rate(pa, games),
            "pyth_pct": m.pythagorean_win_pct(pf, pa),
            "expected_wins": expected,
            "luck_residual": m.luck_residual(int(r["W"]) + 0.5 * int(r["T"]), expected),
            "source_url": r["SourceURL"],
            "source_ids": ["NFL-STANDINGS", "PYTH-NFL"],
        })
    return teams, league_ppg


def originated_games(fixtures: list[dict], teams: list[dict], league_ppg: float) -> list[dict]:
    by_name = {}
    for t in teams:
        by_name[t["team"]] = t
        by_name[t["team"].split()[-1]] = t
    by_name["49ers"] = next(t for t in teams if t["id"] == "SF")
    games = []
    for fixture in fixtures:
        home, away = by_name[fixture["Home"]], by_name[fixture["Away"]]
        projection = m.project_game(home["off_ppg"], home["def_ppa"],
                                    away["off_ppg"], away["def_ppa"], league_ppg)
        p_home = projection["win_prob_home"]
        games.append({
            "id": fixture["id"],
            "matchup": f"{away['id']} @ {home['id']}",
            "away_team": away["team"], "home_team": home["team"],
            "kickoff": f"{fixture['Date']} {fixture['KickoffET']} ET",
            "tv": fixture["TV"],
            "game_url": fixture["GameURL"],
            "model_home_points": projection["home_points"],
            "model_away_points": projection["away_ppg"],
            "originated_spread_home": projection["spread_home"],
            "originated_total": projection["total"],
            "model_p_home": p_home,
            "fair_home_price": m.american_from_probability(p_home),
            "fair_away_price": m.american_from_probability(1 - p_home),
            "market_spread": None, "market_total": None, "market_prices": None,
            "clv": None, "closing_price": None,
            "line_status": "Originated · model only · no market comparison",
            "source_ids": ["NFL-STANDINGS", "NFL-SCHEDULE", "PYTH-NFL", "REPO"],
            "game_source_url": fixture["GameURL"],
            "source_url": fixture["SourceURL"],
        })
    return games


def calibration(teams: list[dict]) -> dict:
    """Out-of-sample-ish check: does points-based expectation beat a flat .500 guess?

    Both are scored against the same actual win rates, so this is a fair comparison of two
    baselines on the same 32 rows. It is NOT a holdout: the Pythagorean exponent is a
    published constant, not fitted here, but the evaluation rows are in-sample for nothing
    else, and the sample is one partial season.
    """
    outcomes = [1.0 if t["pct"] >= 0.5 else 0.0 for t in teams]
    models = {
        "Pythagorean (PF/PA, x=2.37)": [t["pyth_pct"] for t in teams],
        "Flat .500 (no information)": [0.5 for _ in teams],
    }
    scores = {}
    for label, probs in models.items():
        scores[label] = {"brier": m.brier(outcomes, probs),
                         "bins": m.reliability_bins(outcomes, probs)}
    return {
        "scored_rows": len(teams),
        "outcome_definition": "1 if the club's displayed PCT is at least .500, else 0",
        "scores": scores,
        "interpretation": ("A lower Brier score than the flat .500 reference means the scoring "
                           "profile carried information about the displayed record in this snapshot. "
                           "It does not establish predictive skill for future games."),
        "source_ids": ["NFL-STANDINGS", "PYTH-NFL"],
    }


# Pairs that cannot be independent evidence because the two columns share arithmetic.
CAVEATS = {
    "off_ppg~net": "Mechanical: net points is defined as PF minus PA and this column is PF per game, so "
                   "the two series share the same scoring totals.",
    "def_ppa~net": "Mechanical: net points is defined as PF minus PA and this column is PA per game, so "
                   "the two series share the same scoring totals.",
    "net~pct": "Mechanical: wins and net points move together by construction in a small sample.",
    "pct~luck_residual": "Tautological: the residual subtracts a function of PF/PA from wins while PCT is "
                        "wins divided by games, so both series contain the same win count.",
    "net~luck_residual": "Structurally induced: the expectation is computed from PF and PA, which also "
                         "define net points, so the two sides are not independent measurements.",
}


def team_correlations(teams: list[dict]) -> list[dict]:
    metrics = [("off_ppg", "Points scored per game"),
               ("def_ppa", "Points allowed per game"),
               ("net", "Net point differential"),
               ("pct", "Displayed win percentage"),
               ("luck_residual", "Actual minus expected wins")]
    rows = []
    for (a, label_a), (b, label_b) in itertools.combinations(metrics, 2):
        x = [t[a] for t in teams]
        y = [t[b] for t in teams]
        r = m.pearson(x, y)
        p = m.permutation_p_value(x, y, draws=5000)
        key = f"{a}~{b}"
        caveat = CAVEATS.get(key)
        rows.append({"id": key, "pair": f"{label_a} vs {label_b}",
                     "n": len(teams), "pearson": r, "raw_p": p,
                     "kind": "Team-level cross-sectional",
                     "evidence": ("Derived · not independent evidence" if caveat
                                  else "Derived · exploratory"),
                     "caveat": caveat,
                     "counts_as_independent_evidence": caveat is None,
                     "source_ids": ["NFL-STANDINGS", "PYTH-NFL", "REPO"]})
    adjusted = m.holm([row["raw_p"] for row in rows])
    for row, value in zip(rows, adjusted):
        row["holm_p"] = value
    return rows


def not_collected() -> list[dict]:
    blank = {"n": None, "pearson": None, "raw_p": None, "holm_p": None}
    return [
        {"id": "NC-1", "pair": "Same-game leg dependence (spread vs total)",
         "kind": "Not collected — needs play-by-play or closing-line archive",
         "evidence": "Unverified · blank", **blank,
         "source_ids": ["NFL-SCHEDULE", "REPO"]},
        {"id": "NC-2", "pair": "Player prop to team outcome dependence",
         "kind": "Not collected — needs player game logs and snap counts",
         "evidence": "Unverified · blank", **blank,
         "source_ids": ["NFL-INJURY", "REPO"]},
        {"id": "NC-3", "pair": "Multi-leg parlay joint distribution (3+ legs)",
         "kind": "Not collected — pairwise values cannot identify a 3+ leg joint",
         "evidence": "Unverified · blank", **blank,
         "source_ids": ["REPO"]},
        {"id": "NC-4", "pair": "Backup-versus-starter performance gap by position",
         "kind": "Not collected — no published depth chart and no snap counts retrieved",
         "evidence": "Unverified · blank", **blank,
         "source_ids": ["NFL-INJURY", "REPO"]},
    ]


GATES = [
    ("G01", "Provenance and contract",
     "Every input row carries an official URL, a check date and an exact scope.",
     "PASS for the snapshot layer: 32 standings rows, 20 injury rows and 14 fixtures each "
     "carry an NFL.com URL and the 2026-11-12 check date, and are regenerated from saved text."),
    ("G02", "Temporal integrity",
     "No input may post-date the moment a projection is made.",
     "PASS for the originated lines: inputs are pre-kickoff (standings and injury report "
     "published before the Week 10 games). FAIL for the probability calibration, which scores "
     "models against outcomes already inside the same snapshot."),
    ("G03", "Coverage and power",
     "Adequate sample, complete universe, pre-declared scope.",
     "FAIL. Eight or nine games per club, one partial season, no multi-season history, and the "
     "injury sample is one game."),
    ("G04", "Forecast quality",
     "Proper scores against a stated reference, measured before any price is used.",
     "PARTIAL. A Brier comparison against a flat .500 reference exists for the team record; no "
     "sequential, multi-season or out-of-sample forecast evaluation exists."),
    ("G05", "Joint dependence",
     "Leg dependence measured on the actual pairing, not asserted.",
     "FAIL for parlays and props. No pairwise or 3+ leg joint estimate exists; only team-level "
     "cross-sectional correlations are available, which are a different quantity."),
    ("G06", "Executable economics",
     "A real, timestamped, settlement-complete price from an identified operator.",
     "FAIL. No sportsbook price, limit, hold or settlement rule for these NFL markets was "
     "retrieved, so ROI, CLV and stake sizing cannot be computed."),
    ("G07", "Uncertainty and robustness",
     "Uncertainty quantified and conclusions stable to reasonable choices.",
     "FAIL. The projections use a published exponent and a single assumed home-field constant "
     "with no interval, and no sensitivity sweep is published."),
    ("G08", "Selection and multiple testing",
     "All trials counted; multiplicity controlled.",
     "FAIL. The 10 team-level correlations are Holm-adjusted and displayed as exploratory, but "
     "no strategy search with a pre-registered family of trials exists."),
    ("G09", "Forward shadow and risk",
     "A dated, prospective, stake-capped record before any reward.",
     "FAIL. No forward record exists yet; the shadow ledger is specified but empty."),
    ("G10", "Reproducibility and rights",
     "Deterministic rebuild and recorded permission for the intended use.",
     "PASS for reproducibility (byte-identical rebuilds, hashed inputs) and OPEN for rights: "
     "NFL.com terms 1.3 restrict systematic retrieval and commercial use, so nothing here is "
     "released as a dataset or a betting service."),
]

STRATEGIES = [
    {"id": "NS01", "name": "Home spread from scoring profiles", "category": "Single bets",
     "hypothesis": "Price the home club's margin from its own scoring rate, the visitor's "
                   "concession rate and a fixed home adjustment; compare with any offered line.",
     "failure": "Ignores injuries, rest, weather, travel, quarterback changes and market movement. "
                "One assumed home-field constant cannot represent 32 clubs.",
     "gates": {"G01": "pass", "G02": "pass", "G03": "blocked", "G04": "blocked", "G05": "n/a",
               "G06": "blocked", "G07": "blocked", "G08": "blocked", "G09": "blocked", "G10": "open"}},
    {"id": "NS02", "name": "Away spread mirror", "category": "Single bets",
     "hypothesis": "The same two-sided projection read from the visitor's side, used to test "
                   "whether the originated number is symmetric and internally consistent.",
     "failure": "Derived arithmetically from NS01, so it shares every weakness and cannot confirm it.",
     "gates": {"G01": "pass", "G02": "pass", "G03": "blocked", "G04": "blocked", "G05": "n/a",
               "G06": "blocked", "G07": "blocked", "G08": "blocked", "G09": "blocked", "G10": "open"}},
    {"id": "NS03", "name": "Game total from combined scoring rates", "category": "Single bets",
     "hypothesis": "Sum the two conditional scoring means; compare with an offered total and its "
                   "over/under prices.",
     "failure": "Scoring rates are season-to-date and heavily influenced by opponent quality; "
                "pace and weather are absent.",
     "gates": {"G01": "pass", "G02": "pass", "G03": "blocked", "G04": "blocked", "G05": "n/a",
               "G06": "blocked", "G07": "blocked", "G08": "blocked", "G09": "blocked", "G10": "open"}},
    {"id": "NS04", "name": "Record-versus-scoring regression signal", "category": "Single bets",
     "hypothesis": "Clubs whose actual record is far from their points-based expectation are "
                   "candidates whose future results may move toward the expectation.",
     "failure": "The residual is descriptive. It mixes schedule strength, special teams and luck, "
                "and the sample is one partial season.",
     "gates": {"G01": "pass", "G02": "blocked", "G03": "blocked", "G04": "blocked", "G05": "n/a",
               "G06": "blocked", "G07": "blocked", "G08": "blocked", "G09": "blocked", "G10": "open"}},
    {"id": "NP01", "name": "Two-leg spread plus total pair", "category": "Parlays",
     "hypothesis": "Combine NS01 and NS03 on the same game after measuring their dependence.",
     "failure": "No joint distribution exists. Multiplying the two probabilities assumes a "
                "correlation of zero, which is exactly the assumption this project refuses to make.",
     "gates": {"G01": "pass", "G02": "pass", "G03": "blocked", "G04": "blocked", "G05": "blocked",
               "G06": "blocked", "G07": "blocked", "G08": "blocked", "G09": "blocked", "G10": "open"}},
    {"id": "NP02", "name": "Cross-game two-leg parlay", "category": "Parlays",
     "hypothesis": "Combine two clubs' independent games and test whether the product of the "
                   "single-leg probabilities is adequate.",
     "failure": "Cross-game legs are plausibly independent, but that is untested here and each leg "
                "still fails its own gates.",
     "gates": {"G01": "pass", "G02": "pass", "G03": "blocked", "G04": "blocked", "G05": "blocked",
               "G06": "blocked", "G07": "blocked", "G08": "blocked", "G09": "blocked", "G10": "open"}},
    {"id": "NPR01", "name": "Availability-adjusted team line", "category": "Player props / combos",
     "hypothesis": "Adjust a club's scoring projection by which listed players are out, doubtful "
                   "or questionable, using the official game-status categories.",
     "failure": "Status is not contribution. Without depth charts, snap shares or a published "
                "starter list, an 'Out' cannot be converted into points.",
     "gates": {"G01": "pass", "G02": "pass", "G03": "blocked", "G04": "blocked", "G05": "blocked",
               "G06": "blocked", "G07": "blocked", "G08": "blocked", "G09": "blocked", "G10": "open"}},
    {"id": "NPR02", "name": "Next-man-up team combo", "category": "Player props / combos",
     "hypothesis": "When a starter is out, test whether the replacement's usage and the team's "
                   "scoring change in a repeatable direction.",
     "failure": "Requires snap counts, target shares and player logs, none of which were retrieved. "
                "No claim about a second- or third-string player is made.",
     "gates": {"G01": "blocked", "G02": "blocked", "G03": "blocked", "G04": "blocked", "G05": "blocked",
               "G06": "blocked", "G07": "blocked", "G08": "blocked", "G09": "blocked", "G10": "open"}},
]


def evaluate(strategies: list[dict]) -> list[dict]:
    rows = []
    for s in strategies:
        # N/A is never counted as a pass; it only leaves the applicable denominator.
        passed = sum(1 for v in s["gates"].values() if v == "pass")
        applicable = sum(1 for v in s["gates"].values() if v != "n/a")
        qualified = passed == applicable
        rows.append({
            "id": s["id"], "name": s["name"], "category": s["category"],
            "hypothesis": s["hypothesis"], "failure": s["failure"],
            "gates": s["gates"], "passed": passed, "applicable": applicable,
            "qualified": qualified,
            "roi": None, "clv": None, "rank": None, "merit_points": 0, "cash_reward": None,
            "status": "Qualified" if qualified else "Blocked",
            "source_ids": ["REPO", "NFL-STANDINGS"],
        })
    return rows


def leaderboard(evaluations: list[dict]) -> dict:
    qualified = [e for e in evaluations if e["qualified"]]
    return {
        "divisions": ["Single bets", "Parlays", "Player props / combos"],
        "entries": sorted(qualified, key=lambda e: (e["category"], e["id"])),
        "counts": {d: sum(1 for e in qualified if e["category"] == d)
                   for d in ("Single bets", "Parlays", "Player props / combos")},
        "not_applicable_rule": "G05 is not applicable to single bets. It is excluded from the "
                               "denominator and is never counted as a pass.",
        "ranking_metric": "Verified ROI lower 95% bound on a frozen common test window, "
                          "with log loss as tie-break",
        "merit_points": {"1": 3, "2": 2, "3": 1},
        "cash_reward": None,
        "empty_because": "No candidate has an executable price, a joint-dependence estimate or a "
                         "forward record, so no entry can be ranked.",
        "shadow_ledger": {
            "status": "Open and empty",
            "rules": [
                "One row per pre-kickoff entry: timestamp, game, market, line, price, operator and a "
                "screenshot-free text capture of the quote.",
                "Stake capped at a fixed fraction of a notional bankroll; no chasing and no stake "
                "increase after a loss.",
                "Score only after settlement using the operator's published rule.",
                "Report closing-line value and the lower confidence bound, never a single hot run.",
                "Every entry keeps its losing rows; deleting a row disqualifies the strategy.",
            ],
            "entries": [],
        },
    }


def availability() -> list[dict]:
    """Availability index from the official status categories only.

    The index is a count of listed players, NOT a measurement of lost talent, because the
    retrieved report gives no starter designation and no snap share.
    """
    rows = load_csv("data/nfl-injuries-2026-w10.csv")
    out = []
    for team in sorted({r["Team"] for r in rows}):
        players = [r for r in rows if r["Team"] == team]
        out.append({
            "id": f"AV-{team[:3].upper()}",
            "team": team,
            "listed_players": len(players),
            "out": sum(1 for p in players if p["GameStatus"] == "Out"),
            "doubtful": sum(1 for p in players if p["GameStatus"] == "Doubtful"),
            "questionable": sum(1 for p in players if p["GameStatus"] == "Questionable"),
            "full_practice": sum(1 for p in players if p["PracticeStatus"].startswith("Full")),
            "limited": sum(1 for p in players if p["PracticeStatus"].startswith("Limited")),
            "did_not_practice": sum(1 for p in players if p["PracticeStatus"].startswith("Did Not")),
            "unavailable_due_to_g_league": None,
            "starters_affected": None,
            "backup_replacement_count": None,
            "depth_chart_status": "Not published in retrieved sources",
            "talent_lost": None,
            "note": "Counts only. Converting a status into lost on-field value needs depth charts, "
                    "snap shares and player performance data that were not retrieved.",
            "source_ids": ["NFL-INJURY", "NFL-INJURY-POLICY"],
            "source_url": "https://www.nfl.com/injuries/",
        })
    return out


def injury_flags(injuries: list[dict]) -> list[dict]:
    flags = []
    for row in injuries:
        if bool(row["GameStatus"]) != bool(row["Injury"]):
            flags.append({
                "id": f"INJFLAG-{row['id']}",
                "item": f"{row['Player']} ({row['Team']}) status and reason differ",
                "finding": f"Game status is '{row['GameStatus'] or 'blank'}' while the reason is "
                           f"'{row['Injury'] or 'blank'}'. The rendered page does not explain why.",
                "unverified_value": None,
                "status": "Needs review",
                "source_ids": ["NFL-INJURY"],
                "source_url": row["PlayerURL"],
            })
    return flags


def build() -> dict:
    receipts = verify_receipts()
    standings = load_csv("data/nfl-standings-2026.csv")
    fixtures = load_csv("data/nfl-schedule-2026-w10.csv")
    injuries = load_csv("data/nfl-injuries-2026-w10.csv")
    teams, league_ppg = team_table(standings)
    games = originated_games(fixtures, teams, league_ppg)
    evaluations = evaluate(STRATEGIES)
    inputs = sorted(list((ROOT / "data").glob("nfl-*.csv"))
                    + list((ROOT / "nfl_lab").glob("*.py"))
                    + [ROOT / "research/nfl/receipts.json"])
    manifest = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    result = {
        "schema_version": 1,
        "snapshot_date": "2026-11-12",
        "mode": "Non-commercial NFL research; no wagering, no dataset release, no live odds",
        "verified_rows": {
            "standings": len(standings), "injuries": len(injuries), "fixtures": len(fixtures),
            "total": len(standings) + len(injuries) + len(fixtures),
        },
        "assumptions": {
            "pythagorean_exponent": m.PYTH_EXPONENT,
            "pythagorean_source": "Published NFL convention (Football Outsiders / "
                                  "Pro-Football-Reference; see PYTH-NFL). Not fitted here.",
            "home_adjustment_points": m.HFA_POINTS,
            "home_adjustment_source": "Project assumption chosen before evaluation; no official "
                                      "NFL home-field value was retrieved.",
            "win_probability_sd": 13.86,
            "win_probability_source": "Project assumption for the normal approximation; no "
                                      "official NFL margin variance was retrieved.",
        },
        "league": {"team_games": sum(t["games"] for t in teams),
                   "league_points_per_team_game": league_ppg},
        "teams": teams,
        "games": games,
        "calibration": calibration(teams),
        "correlations": team_correlations(teams),
        "not_collected": not_collected(),
        "availability": availability(),
        "injury_flags": injury_flags(injuries),
        "gates": [{"id": g[0], "name": g[1], "rule": g[2], "current": g[3]} for g in GATES],
        "evaluations": evaluations,
        "leaderboard": leaderboard(evaluations),
        "input_sha256": manifest,
        "run_hash": hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
        "limitations": [
            "One partial season, eight or nine games per club.",
            "No market prices, limits, hold or settlement rules were retrieved.",
            "No depth chart, snap count or player game log was retrieved.",
            "Team-level correlation is not leg-level dependence.",
            "The NFL.com terms restrict systematic retrieval and commercial use.",
        ],
    }
    return round_value(result, 4)


def run(check: bool = False) -> None:
    target = ROOT / "research" / "nfl" / "results.json"
    text = json.dumps(build(), indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if check:
        if not target.exists() or target.read_text(encoding="utf-8") != text:
            raise SystemExit("STALE: run python -m nfl_lab run")
        print("OK: NFL results reproduce exactly from receipt-checked inputs")
        return
    target.write_text(text, encoding="utf-8")
    print(f"Built research/nfl/results.json: {len(json.loads(text)['games'])} originated games, "
          f"0 qualified strategies, no market values inferred")
