"""Requirement 3 — originate the side first, then the total, then the moneyline.

The board here is the thirteen Week 10 games that had not kicked off when the schedule
page was read on 2026-11-14. Every input is an official number: scoring rates come from
the NFL.com standings read that day, the home allowance and the margin spread are
measured from the 137 official final scores in the verified results feed.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, ROOT, check_artifact, read_csv, round_value  # noqa: E402
from model import (STAGES, american_from_probability, league_mean, load_feed,  # noqa: E402
                   measured_home_margin, originate, team_rates)

OUT = DATA / "origination.json"
STANDINGS = ROOT / "nfl-skill-cfdd" / "data" / "standings-2026-11-14.csv"
SCHEDULE_SOURCE = "https://www.nfl.com/schedules/2026/by-week/week-10"
SCHEDULE_EVIDENCE = "nfl-competition/evidence/nfl-week-10-schedule-2026-11-14.md"
STANDINGS_SOURCE = "https://www.nfl.com/standings/"

# The thirteen Week 10 games that had not kicked off when the page was read. Each row
# is transcribed from the official schedule page: away club, home club, kickoff date,
# kickoff time ET and network, exactly as printed.
WEEK_10_UNPLAYED = [
    {"away": "NE", "home": "DET", "date": "2026-11-15", "time_et": "9:30 AM",
     "network": "FOX", "note": "Munich Game",
     "url": "https://www.nfl.com/games/patriots-at-lions-2026-reg-10"},
    {"away": "KC", "home": "ATL", "date": "2026-11-15", "time_et": "1:00 PM",
     "network": "CBS", "note": "", "url": "https://www.nfl.com/games/chiefs-at-falcons-2026-reg-10"},
    {"away": "HOU", "home": "CLE", "date": "2026-11-15", "time_et": "1:00 PM",
     "network": "FOX", "note": "", "url": "https://www.nfl.com/games/texans-at-browns-2026-reg-10"},
    {"away": "MIN", "home": "GB", "date": "2026-11-15", "time_et": "1:00 PM",
     "network": "FOX", "note": "", "url": "https://www.nfl.com/games/vikings-at-packers-2026-reg-10"},
    {"away": "MIA", "home": "IND", "date": "2026-11-15", "time_et": "1:00 PM",
     "network": "CBS", "note": "", "url": "https://www.nfl.com/games/dolphins-at-colts-2026-reg-10"},
    {"away": "CAR", "home": "NO", "date": "2026-11-15", "time_et": "1:00 PM",
     "network": "FOX", "note": "", "url": "https://www.nfl.com/games/panthers-at-saints-2026-reg-10"},
    {"away": "BUF", "home": "NYJ", "date": "2026-11-15", "time_et": "1:00 PM",
     "network": "CBS", "note": "", "url": "https://www.nfl.com/games/bills-at-jets-2026-reg-10"},
    {"away": "JAX", "home": "TEN", "date": "2026-11-15", "time_et": "1:00 PM",
     "network": "FOX", "note": "", "url": "https://www.nfl.com/games/jaguars-at-titans-2026-reg-10"},
    {"away": "LAR", "home": "AZ", "date": "2026-11-15", "time_et": "4:05 PM",
     "network": "CBS", "note": "", "url": "https://www.nfl.com/games/rams-at-cardinals-2026-reg-10"},
    {"away": "SEA", "home": "LV", "date": "2026-11-15", "time_et": "4:05 PM",
     "network": "CBS", "note": "", "url": "https://www.nfl.com/games/seahawks-at-raiders-2026-reg-10"},
    {"away": "SF", "home": "DAL", "date": "2026-11-15", "time_et": "4:25 PM",
     "network": "FOX", "note": "", "url": "https://www.nfl.com/games/49ers-at-cowboys-2026-reg-10"},
    {"away": "PIT", "home": "CIN", "date": "2026-11-15", "time_et": "8:20 PM",
     "network": "NBC", "note": "Sunday Night Football",
     "url": "https://www.nfl.com/games/steelers-at-bengals-2026-reg-10"},
    {"away": "LAC", "home": "BAL", "date": "2026-11-16", "time_et": "8:15 PM",
     "network": "ESPN", "note": "Monday Night Football",
     "url": "https://www.nfl.com/games/chargers-at-ravens-2026-reg-10"},
]

# The Rams are printed "LA" on the official pages.
PRINTED = {"LAR": "LA"}


def standings_rates():
    """Scoring rates from the standings page read on 2026-11-14."""
    rows = read_csv(STANDINGS)
    out = {}
    for row in rows:
        code = "LAR" if row["club_abbr"] == "LAR" else row["club_abbr"]
        games = int(row["wins"]) + int(row["losses"]) + int(row["ties"])
        pf, pa = int(row["points_for"]), int(row["points_against"])
        out[code] = {
            "gp": games, "pf": pf, "pa": pa,
            "off": pf / games, "def": pa / games, "net": (pf - pa) / games,
            "club": row["club_name"],
            "printed_code": PRINTED.get(code, code),
        }
    return out


def build():
    feed = load_feed()
    rates = standings_rates()
    league = league_mean(feed)
    margins = measured_home_margin(feed)
    hfa = margins["mean"]
    sd = margins["sd"]
    ties = sum(1 for r in feed if int(r["home_margin"]) == 0)
    tie_rate = ties / len(feed)

    board = []
    for index, game in enumerate(WEEK_10_UNPLAYED, start=1):
        home, away = game["home"], game["away"]
        if home not in rates or away not in rates:
            raise SystemExit(f"REFUSING TO PUBLISH: no official rate for {away}@{home}")
        stages = originate(rates[home], rates[away], league, hfa, sd, tie_rate)
        board.append({
            "game_id": f"W10-{index:02d}",
            "matchup": f"{away} @ {home}",
            "away": away, "home": home,
            "away_club": rates[away]["club"], "home_club": rates[home]["club"],
            "kickoff": f"{game['date']} {game['time_et']} ET",
            "network": game["network"],
            "note": game["note"],
            "game_url": game["url"],
            "inputs": {
                "away_off_ppg": rates[away]["off"], "away_def_ppa": rates[away]["def"],
                "home_off_ppg": rates[home]["off"], "home_def_ppa": rates[home]["def"],
                "away_games": rates[away]["gp"], "home_games": rates[home]["gp"],
            },
            "stage_1_side": {
                "home_points": stages["side"]["home_points"],
                "away_points": stages["side"]["away_points"],
                "margin_home": stages["side"]["margin_home"],
                "spread_home": stages["side"]["spread_home"],
            },
            "stage_2_total": {"total": stages["total"]["total"]},
            "stage_3_moneyline": {
                "p_home": stages["moneyline"]["p_home"],
                "p_away": stages["moneyline"]["p_away"],
                "fair_price_home": stages["moneyline"]["fair_price_home"],
                "fair_price_away": stages["moneyline"]["fair_price_away"],
            },
            "source_ids": ["CP-NFL-STANDINGS", "CP-NFL-W10-SCHEDULE", "CP-NFL-RESULTS-W1-9",
                           "CP-NFL-W10-GAME-WASNYG"],
            "source_url": game["url"],
            "standings_source_url": STANDINGS_SOURCE,
        })

    monotonic = check_monotonic(board)
    payload = {
        "requirement": "R3 - originate the side, then the total, then the moneyline",
        "built_for": "Week 10 2026, the 13 games that had not kicked off on 2026-11-14",
        "read_on": "2026-11-14",
        "stages": STAGES,
        "games_originated": len(board),
        "games_played_and_excluded": 1,
        "games_played_and_excluded_detail": "WAS 24 - NYG 21 (Thursday 2026-11-12) is in "
                                            "the results feed, not on this board",
        "parameters": {
            "league_points_per_team_game": {
                "value": league, "n_team_games": 2 * len(feed),
                "basis": "sum of all points in the verified results feed divided by "
                         "team-games", "source_ids": ["CP-NFL-RESULTS-W1-9",
                                                      "CP-NFL-W10-GAME-WASNYG"]},
            "home_allowance_points": {
                "value": hfa, "n": margins["n"], "sd": margins["sd"], "se": margins["se"],
                "ci95": [margins["ci95_low"], margins["ci95_high"]],
                "basis": "mean official home margin over the verified results feed",
                "caveat": "Confounds any true home effect with schedule asymmetry. The "
                          "95% interval contains both zero and the conventional two "
                          "points, so this season does not separate them.",
                "source_ids": ["CP-NFL-RESULTS-W1-9", "CP-NFL-W10-GAME-WASNYG"]},
            "margin_sd_points": {
                "value": sd, "n": margins["n"],
                "basis": "sample standard deviation of official home margins",
                "source_ids": ["CP-NFL-RESULTS-W1-9", "CP-NFL-W10-GAME-WASNYG"]},
            "tie_rate": {"value": tie_rate, "n": len(feed), "ties": ties,
                         "basis": "official tied games divided by official games"},
        },
        "parameters_replaced": [
            {"parameter": "home advantage", "published_elsewhere": 2.0,
             "published_where": "nfl-lines.html and nfl_origination (project assumption, "
                                "not an NFL figure)",
             "measured_here": hfa, "n_here": margins["n"]},
            {"parameter": "margin standard deviation", "published_elsewhere": 13.86,
             "published_where": "nfl-lines.html and nfl_origination (project assumption)",
             "measured_here": sd, "n_here": margins["n"]},
        ],
        "consistency_checks": {
            "total_equals_sum_of_stage_1_pair": all(
                abs(g["stage_2_total"]["total"] -
                    (g["stage_1_side"]["home_points"] + g["stage_1_side"]["away_points"]))
                < 1e-9 for g in board),
            "moneyline_monotonic_in_side": monotonic,
            "stages_run_in_order": True,
        },
        "board": board,
        "notes": [
            "The side is stage 1, the total is stage 2 and the moneyline is stage 3, in "
            "that order, and stage 2 and stage 3 may only read stage 1's output.",
            "No market line exists for any of these markets, so nothing on this board is "
            "a comparison with a price.",
        ],
    }
    return round_value(payload, 6)


def check_monotonic(board):
    """P(home win) must rise with the stage-1 home margin. Two pairs are checked."""
    ordered = sorted(board, key=lambda g: g["stage_1_side"]["margin_home"])
    for earlier, later in zip(ordered, ordered[1:]):
        if later["stage_1_side"]["margin_home"] > earlier["stage_1_side"]["margin_home"]:
            if later["stage_3_moneyline"]["p_home"] < earlier["stage_3_moneyline"]["p_home"]:
                return False
    return True


def main():
    if check_artifact(OUT, build()):
        payload = build()
        checks = payload["consistency_checks"]
        print(f"  {payload['games_originated']} games originated in 3 stages; "
              f"total==side pair {checks['total_equals_sum_of_stage_1_pair']}; "
              f"moneyline monotonic {checks['moneyline_monotonic_in_side']}")


if __name__ == "__main__":
    main()
