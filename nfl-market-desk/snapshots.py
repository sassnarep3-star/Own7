#!/usr/bin/env python3
"""Build the price-snapshot store and the verified results feed, then verify both.

Two stores, one script, because they share a single guarantee: a row that cannot be sourced is
published as blank with a named reason, never as a guess.

  data/price-snapshots-2026-w10.csv   one row per originated market, opening + closing columns
  data/verified-results-2026-w1-9.csv the results feed that backtests and ROI must read from

The results feed is not copied by hand. It is re-derived from the two committed sources that
already reconcile against the official standings, and this script re-runs that reconciliation
independently before emitting:

  * scores from ``nfl-results/data/games-2026-w1-9.csv`` (reconciled 160/160 on W-L-T, PF, PA)
  * standings from ``data/nfl-standings-week10-2026.csv`` (official NFL.com snapshot)

If any of the 32 clubs' W-L-T or PF/PA fails to recompute from the feed rows, the build aborts.
That is what makes the feed "verified" in a way a reader can check: the verification runs every
time the file is generated, and CI runs it again.
"""
from __future__ import annotations

import csv
from pathlib import Path

from emit import emit_csv, emit_json, parse_args
import originate
import prices

REPO = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

GAMES = REPO / "nfl-results" / "data" / "games-2026-w1-9.csv"
BYES = REPO / "nfl-results" / "data" / "byes-2026-w1-9.csv"
STANDINGS = REPO / "data" / "nfl-standings-week10-2026.csv"

FULL_NAME = {
    "AZ": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LV": "Las Vegas Raiders", "LAC": "Los Angeles Chargers",
    "LA": "Los Angeles Rams", "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings",
    "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers", "SEA": "Seattle Seahawks", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
}


def load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------- results feed
def build_results() -> tuple[list[dict], dict]:
    games = load(GAMES)
    byes = load(BYES)
    standings = load(STANDINGS)
    if len(standings) != 32:
        raise SystemExit(f"expected 32 standings rows, got {len(standings)}")

    tally = {code: {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0, "gp": 0} for code in FULL_NAME}
    for game in games:
        away, home = game["away"], game["home"]
        if away not in FULL_NAME or home not in FULL_NAME:
            raise SystemExit(f"unknown club code in feed: {away} / {home}")
        a, h = int(game["away_score"]), int(game["home_score"])
        if a == h:
            # The official standings do record ties, so a tie is a real outcome and is counted.
            tally[away]["t"] += 1
            tally[home]["t"] += 1
        else:
            winner, loser = (away, home) if a > h else (home, away)
            tally[winner]["w"] += 1
            tally[loser]["l"] += 1
        for club, scored, allowed in ((away, a, h), (home, h, a)):
            tally[club]["pf"] += scored
            tally[club]["pa"] += allowed
            tally[club]["gp"] += 1

    mismatches = []
    for row in standings:
        code = row["TeamCode"]
        got = tally[code]
        for field, column in (("w", "W"), ("l", "L"), ("t", "T"), ("pf", "PF"), ("pa", "PA")):
            if got[field] != int(row[column]):
                mismatches.append({"club": code, "field": field, "feed": got[field],
                                   "official": int(row[column])})
    if mismatches:
        raise SystemExit("results feed does NOT reconcile with the official standings: "
                         + "; ".join(f"{m['club']} {m['field']} {m['feed']}!={m['official']}"
                                     for m in mismatches))

    # One row per game, plus a row per bye so the feed covers every club-week, not just games.
    rows: list[dict] = []
    for game in games:
        away, home = game["away"], game["home"]
        a, h = int(game["away_score"]), int(game["home_score"])
        rows.append({
            "game_id": f"W{game['week']}-{away}-{home}",
            "week": int(game["week"]),
            "date": game["date"],
            "weekday": game["weekday"],
            "away": away,
            "away_name": FULL_NAME[away],
            "home": home,
            "home_name": FULL_NAME[home],
            "away_score": a,
            "home_score": h,
            "winner": away if a > h else home,
            "margin_home": h - a,
            "total_points": a + h,
            "result_type": "game",
            "reconciled_to_standings": "yes",
            "source_url": game["source_url"],
            "evidence_file": game["evidence"],
            "read_on": game["retrieved"],
        })
    for bye in byes:
        rows.append({
            "game_id": f"W{bye['week']}-{bye['team_code']}-BYE",
            "week": int(bye["week"]),
            "date": "",
            "weekday": "",
            "away": bye["team_code"],
            "away_name": FULL_NAME.get(bye["team_code"], bye["team"]),
            "home": "",
            "home_name": "",
            "away_score": "",
            "home_score": "",
            "winner": "",
            "margin_home": "",
            "total_points": "",
            "result_type": "bye",
            "reconciled_to_standings": "yes",
            "source_url": bye["source_url"],
            "evidence_file": "nfl-results/evidence/week-%s.schedule.md" % bye["week"],
            "read_on": bye["retrieved"],
        })
    rows.sort(key=lambda r: (r["week"], r["result_type"] != "game", r["game_id"]))

    summary = {
        "games": sum(1 for r in rows if r["result_type"] == "game"),
        "byes": sum(1 for r in rows if r["result_type"] == "bye"),
        "weeks_covered": sorted({r["week"] for r in rows}),
        "clubs": len({r["away"] for r in rows} | {r["home"] for r in rows if r["home"]}),
        "fields_reconciled": 32 * 5,
        "mismatches": 0,
        "method": "W-L-T, PF and PA recomputed for all 32 clubs from the feed rows alone and "
                  "compared to the official NFL.com standings snapshot; the build aborts on any "
                  "difference.",
        "not_included": [
            "Week 10 results (the four Week 10 games are not all final at the snapshot date)",
            "play-by-play, drive data, injuries per game, or any player-level outcome",
            "any price, spread, total or moneyline",
        ],
    }
    return rows, summary


# --------------------------------------------------------------------------- price store
def build_prices() -> tuple[list[dict], dict]:
    rows = prices.originated_markets()
    problems = prices.validate(rows)
    if problems:
        raise SystemExit("price store contract violated: " + " | ".join(problems))
    coverage = prices.coverage(rows)
    coverage["snapshot_date"] = originate.SNAPSHOT_DATE
    coverage["schema_fields"] = {
        "open_line": "the opening number, from a licensed source; blank until one is registered",
        "open_price": "the opening price in American odds; blank for the same reason",
        "close_line": "the closing number; blank",
        "close_price": "the closing price; blank",
        "line_move": "close_line - open_line; computable only when both exist",
        "clv_points": "closing value in points for the originated side; blank without a close",
    }
    coverage["empty_because"] = prices.DEFAULT_REASON
    return rows, coverage


def main() -> None:
    parse_args(__doc__ or "snapshots")
    price_rows, price_meta = build_prices()
    result_rows, result_meta = build_results()
    emit_csv(DATA / "price-snapshots-2026-w10.csv", price_rows)
    emit_json(DATA / "price-coverage-2026-w10.json", price_meta)
    emit_csv(DATA / "verified-results-2026-w1-9.csv", result_rows)
    emit_json(DATA / "results-feed-2026-w1-9.json", result_meta)
    print(f"Price store: {price_meta['markets_originated']} markets, "
          f"{price_meta['markets_priced']} priced, {price_meta['coverage_pct']}% coverage.")
    print(f"Verified results feed: {result_meta['games']} games + {result_meta['byes']} byes, "
          f"{result_meta['fields_reconciled']} standings fields reconciled, "
          f"{result_meta['mismatches']} mismatches.")


if __name__ == "__main__":
    main()
