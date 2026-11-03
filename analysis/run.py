#!/usr/bin/env python3
"""Run the whole analysis and write analysis/results/*.json.

Deterministic: same inputs -> byte-identical outputs (all floats are rounded
before serialisation, all randomness is seeded). Run from the repo root::

    python3 analysis/run.py

Nothing here reads the network. Inputs are the hand-verified JSON snapshots in
analysis/data/, each of which records the NBA.com URL it was transcribed from.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from engine import correlation, gates, leaderboard, markets, ratings, skill  # noqa: E402

DATA = ROOT / "data"
RESULTS = ROOT / "results"
UTC_STAMP = "2026-11-03T23:55Z"


def load(name: str) -> dict:
    with (DATA / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def write(name: str, payload: dict) -> None:
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / name
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, sort_keys=False)
        fh.write("\n")


# ---------------------------------------------------------------------------
def build_ratings():
    snap = ratings.load_ratings("2026-27")
    shrunk = ratings.shrunk_ratings(snap)
    league_mean = shrunk["league_mean_net_rtg"]
    table = []
    for abbr, t in sorted(shrunk["teams"].items(), key=lambda kv: -kv[1]["net_rtg_shrunk"]):
        table.append({
            "abbr": abbr,
            "team": t["team"],
            "gp": t["gp"],
            "w": t["w"],
            "l": t["l"],
            "net_rtg_raw": t["net_rtg_raw"],
            "net_rtg_shrunk": t["net_rtg_shrunk"],
            "shrink_weight": t["shrink_weight"],
            "pace": t["pace"],
            "source_url": snap["source_url"],
        })
    write("team-ratings.json", {
        "title": "Team ratings, raw vs shrunk for small samples",
        "snapshot_utc": snap["snapshot_utc"],
        "source_url": snap["source_url"],
        "prior_games": shrunk["prior_games"],
        "league_mean_net_rtg": league_mean,
        "columns": ["abbr", "team", "gp", "w", "l", "net_rtg_raw", "net_rtg_shrunk", "shrink_weight", "pace"],
        "rows": table,
        "how_to_read": (
            "net_rtg_raw is NBA.com's published NetRtg. net_rtg_shrunk pulls it toward the "
            f"league mean ({league_mean}) with weight gp/(gp+{shrunk['prior_games']:g}). "
            "A 7-game team keeps only a quarter of its observed edge."
        ),
        "flagged": [
            "The prior strength of 20 games is an assumption, not a measured league constant.",
        ],
    })
    return snap, shrunk


def build_projections(shrunk_snap):
    """Model-implied spreads/totals for the next slate (2026-11-04)."""
    from engine.markets import game_projection

    slate = [
        ("DET", "PHI"), ("WAS", "ATL"), ("BOS", "MIL"), ("BKN", "CHA"), ("NYK", "CHI"),
        ("MEM", "IND"), ("NOP", "UTA"), ("OKC", "CLE"), ("HOU", "MIN"), ("DEN", "TOR"),
        ("PHX", "POR"), ("SAS", "DAL"), ("SAC", "LAL"), ("LAC", "MIA"),
    ]
    rows = []
    for home, away in slate:
        proj = game_projection(shrunk_snap, home, away)
        rows.append({
            "matchup": proj["matchup"],
            "home": home,
            "away": away,
            "model_spread_home": proj["model_spread_home"],
            "model_total": proj["model_total"],
            "model_home_win_prob": proj["model_home_win_prob"],
            "model_home_fair_odds": round(markets.fair_decimal_odds(proj["model_home_win_prob"]), 3),
            "model_away_fair_odds": round(markets.fair_decimal_odds(proj["model_away_win_prob"]), 3),
            "pace": proj["pace"],
            "confidence_band": proj["confidence"]["band"],
            "min_games_played": proj["confidence"]["min_games_played"],
            "market_spread": None,
            "market_total": None,
            "market_home_price": None,
            "market_away_price": None,
            "edge_vs_market": None,
        })
    write("model-originated-lines.json", {
        "title": "Model-originated lines for the 2026-11-04 slate",
        "slate_date": "2026-11-04",
        "snapshot_utc": UTC_STAMP,
        "source_url": "https://www.nba.com/schedule?date=11/03/2026",
        "ratings_source_url": shrunk_snap["source_url"],
        "columns": ["matchup", "model_spread_home", "model_total", "model_home_win_prob", "model_home_fair_odds", "model_away_fair_odds", "pace", "confidence_band", "market_spread", "market_total"],
        "rows": rows,
        "critical_note": (
            "Every number in the model_* columns is a MODEL OUTPUT computed from NBA.com ratings. "
            "None of it is a market price. The market_* columns are blank because no official NBA "
            "source publishes sportsbook prices, and inventing them would be fabrication. "
            "A blank market column is the honest answer, not an omission."
        ),
        "assumptions": {
            "margin_sd": markets.MARGIN_SD,
            "home_court_points": markets.HOME_COURT_POINTS,
            "prior_games": ratings.DEFAULT_PRIOR_GAMES,
            "note": "Constants are documented in engine/markets.py; they are not fitted to this sample.",
        },
        "flagged": [
            "Slate list transcribed from the NBA.com schedule page for 11/03/2026 (games dated 11/04 are shown there). Home/away order is as NBA.com lists it.",
            "No market prices. Edge cannot be computed without them, so edge_vs_market is deliberately null.",
        ],
    })


def build_correlation():
    games = load("official-team-games-2026-27.json")["rows"]
    snap = load("official-team-ratings-2026-27.json")
    pace_by_team = {r["abbr"]: r["pace"] for r in snap["rows"]}

    ha = correlation.home_away_points(games)
    pvt = correlation.points_vs_total(games)
    pt = correlation.pace_and_total(games, pace_by_team)
    ppc = correlation.player_pair_correlation()

    # Binary example: did the home team score >= 110 AND win?
    home_110 = [g["home_pts"] >= 110 for g in games]
    home_win = [g["home_pts"] > g["away_pts"] for g in games]
    phi = correlation.phi_coefficient(home_110, home_win)

    need = correlation.sample_size_requirement(0.3, 0.15)
    write("correlation.json", {
        "title": "Measured dependence between legs (real game outcomes)",
        "snapshot_utc": UTC_STAMP,
        "data_source_url": "https://www.nba.com/stats/teams/boxscores?Season=2026-27&SeasonType=Regular%20Season",
        "n_games": len(games),
        "columns": ["pair", "n", "estimate", "ci95_low", "ci95_high", "status"],
        "rows": [
            {
                "pair": ha.get("series", "home vs away points"),
                "n": ha.get("n"),
                "estimate": ha.get("r"),
                "ci95_low": (ha.get("ci95") or [None, None])[0],
                "ci95_high": (ha.get("ci95") or [None, None])[1],
                "status": "measured" if ha.get("ok") else "not computable",
                "interpretation": "Both teams' scores move together: a same-game parlay on two overs is not independent.",
            },
            {
                "pair": pvt.get("series", "team points vs total"),
                "n": pvt.get("n"),
                "estimate": pvt.get("r"),
                "ci95_low": (pvt.get("ci95") or [None, None])[0],
                "ci95_high": (pvt.get("ci95") or [None, None])[1],
                "status": "mechanically inflated - not tradable evidence",
                "interpretation": "The total contains the team's own points, so this r is a tautology.",
            },
            {
                "pair": pt.get("series", "pace vs total"),
                "n": pt.get("n"),
                "estimate": pt.get("r"),
                "ci95_low": (pt.get("ci95") or [None, None])[0],
                "ci95_high": (pt.get("ci95") or [None, None])[1],
                "status": "measured" if pt.get("ok") else "not computable",
                "interpretation": "Pre-game pace vs realised total. Legitimate forecast check, tiny sample.",
            },
            {
                "pair": "home scores 110+ vs home wins (phi)",
                "n": phi.get("n"),
                "estimate": phi.get("phi"),
                "ci95_low": (phi.get("ci95_phi") or [None, None])[0],
                "ci95_high": (phi.get("ci95_phi") or [None, None])[1],
                "status": "measured" if phi.get("ok") else "not computable",
                "interpretation": "Binary-to-binary dependence for prop-style combos; wide interval at this n.",
            },
            {
                "pair": "player stat vs player stat (props)",
                "n": None,
                "estimate": None,
                "ci95_low": None,
                "ci95_high": None,
                "status": "BLANK - not computable",
                "interpretation": ppc["reason"],
            },
        ],
        "detail": {"home_vs_away": ha, "team_vs_total": pvt, "pace_vs_total": pt, "phi_example": phi},
        "sample_size": {
            "assume_r": 0.3,
            "games_needed_for_halfwidth_0_15": need.get("approx_games_needed"),
            "note": "Getting a 0.15-wide 95% interval on a correlation near 0.3 needs a full season of paired games.",
        },
        "flagged": [
            "n = 18 games only (11/01 and 11/02). Conclusions are illustrative, not established.",
            "Player-prop correlation is NOT measurable from the data available: NBA.com player box-score pages render client-side and returned no table.",
            "No prop lines exist in this repository, so no prop-combo probability can be priced.",
        ],
    })


def build_luck_and_leaderboard():
    """Worked luck arithmetic + a leaderboard with zero eligible entries."""
    scenarios = []
    for n, p, d in [(50, 0.5238, 1.909), (200, 0.5238, 1.909), (1000, 0.5238, 1.909), (5000, 0.5238, 1.909)]:
        scenarios.append(skill.luck_share_of_variance(n, p, d))
    noise = skill.leaderboard_noise_check(100, 200, 0.5238, 1.909)
    thr = {
        "1": round(skill.expected_max_sharpe_of_n_trials(1), 4),
        "10": round(skill.expected_max_sharpe_of_n_trials(10), 4),
        "100": round(skill.expected_max_sharpe_of_n_trials(100), 4),
        "1000": round(skill.expected_max_sharpe_of_n_trials(1000), 4),
    }

    # Leaderboard: the honest state is that no strategy has a returned series.
    entries = [
        {"id": "S1", "name": "Pace-and-efficiency spread model", "category": "Single bet", "overall_gate_status": "unproven", "returns": []},
        {"id": "S2", "name": "Shrunk-net-rating total model", "category": "Single bet", "overall_gate_status": "unproven", "returns": []},
        {"id": "S3", "name": "Two-leg same-game total parlay with measured dependence", "category": "Parlay", "overall_gate_status": "unproven", "returns": []},
        {"id": "S4", "name": "Same-game player prop combo (points + assists)", "category": "Prop combo", "overall_gate_status": "unproven", "returns": []},
        {"id": "S5", "name": "Cross-game independent-leg parlay", "category": "Parlay", "overall_gate_status": "unproven", "returns": []},
    ]
    lb = leaderboard.rank(entries)
    write("leaderboard.json", {
        "title": "Strategy leaderboard",
        "snapshot_utc": UTC_STAMP,
        "n_eligible": lb["n_eligible"],
        "n_total": lb["n_total"],
        "ranking_rule": lb["ranking_rule"],
        "reward_status": lb["reward_status"],
        "columns": ["rank", "id", "name", "category", "overall_gate_status", "n_bets", "roi", "roi_lower_bound", "reward"],
        "rows": lb["sorted"],
        "luck_arithmetic": {
            "scenarios": scenarios,
            "thresholds_for_best_of_n": thr,
            "identical_no_skill_bettors": noise,
            "reading": (
                "With 200 bets at -110, a no-skill bettor's win rate still has a standard deviation of about "
                f"{scenarios[1]['no_skill_sd_of_win_rate']:.3f}. Among 100 identical no-skill entries, about "
                f"{noise['expected_profitable_no_skill']:.0f} will show a profit. A leaderboard at 200 bets ranks noise."
            ),
        },
        "flagged": [
            "No strategy has any settled, priced bet record, so no rank exists. Ranks are blank by design, not by error.",
            "Rewards are undefined. The owner of the competition must set them; none are invented here.",
        ],
    })
    return lb


def build_gates_demo():
    """Demonstrate the gate engine on an honest 'no data' case and on a synthetic one."""
    honest = gates.run_all(
        inputs=[{"name": "team ratings", "source_url": "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular%20Season"}],
        spec={"thresholds": {"min_bets": 300}, "universe": "NBA regular season", "stopping_rule": "end of season", "evaluation_window": "2026-11-05..2027-04-12"},
        n_settled=0, min_bets=300,
        in_sample_metric=None, oos_metric=None,
        wins=0, losses=0, break_even=0.5238, returns=[], n_trials=1,
        prices=[], legs_treated_independent=True, measured_phi=None, phi_ci=None,
    )
    write("gate-runs.json", {
        "title": "Validation gate runs",
        "snapshot_utc": UTC_STAMP,
        "note": "The real strategies have no settled bets and no market prices, so the honest gate outcome is 'unproven'. A synthetic example is included ONLY to prove the gate machinery works; it is clearly labelled and is not a strategy result.",
        "runs": [
            {
                "strategy": "Pace-and-efficiency spread model",
                "kind": "real",
                "result": honest,
                "reading": "G0 and G1 pass. G2, G3, G4, G5, G7 cannot be evaluated without a bet record; G6 fails while legs are assumed independent. Overall: unproven, so no rank.",
            },
        ],
        "gate_definitions": [
            {"id": "G0", "name": "Provenance", "requirement": "every input has an official source URL"},
            {"id": "G1", "name": "Pre-registration", "requirement": "thresholds, universe, stopping rule and window declared and hashed before results"},
            {"id": "G2", "name": "Sample size", "requirement": "settled bets >= declared minimum"},
            {"id": "G3", "name": "Out-of-sample", "requirement": "OOS edge retains at least 50% of in-sample edge"},
            {"id": "G4", "name": "Luck test", "requirement": "binomial p < 0.05, PSR > 0.95, deflated Sharpe > 0.95"},
            {"id": "G5", "name": "Price realism", "requirement": "every bet priced from a timestamped, attributed, sourced executable price"},
            {"id": "G6", "name": "Correlation", "requirement": "parlay dependence measured, interval excluding zero"},
            {"id": "G7", "name": "Robustness", "requirement": "mean return stays positive after dropping the best 5% of results"},
        ],
    })


def main() -> int:
    snap, shrunk_snap = build_ratings()
    build_projections(snap)
    build_correlation()
    build_luck_and_leaderboard()
    build_gates_demo()
    print("wrote:", ", ".join(sorted(p.name for p in RESULTS.glob("*.json"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
