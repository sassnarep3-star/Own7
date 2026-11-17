"""Requirement 2 — the verified results feed.

A backtest is only worth as much as its settlement data, so this module is the
floor everything else stands on:

  1. every row is a final score printed by NFL.com;
  2. every row names the official page it was read from and the date it was read;
  3. the whole feed is re-derived into each club's W-L-T, PF and PA and compared to
     the standings page read the same day. If any of the 192 club fields disagree the
     build aborts rather than publishing a number.

Settlement rules are stated explicitly so that a graded row can be reproduced by a
reader without guessing. They are project rules for grading an originated line, not
official NFL rules and not the rules of any operator.
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, ROOT, check_artifact, read_csv, round_value, write_csv  # noqa: E402

ARCHIVE = ROOT / "nfl-results" / "data" / "games-2026-w1-9.csv"
BYES = ROOT / "nfl-results" / "data" / "byes-2026-w1-9.csv"
STANDINGS = ROOT / "nfl-skill-cfdd" / "data" / "standings-2026-11-14.csv"
FEED_CSV = DATA / "results-feed.csv"
OUT = DATA / "results-feed.json"

# The Rams are printed "LA" on the standings page and in the by-week archive. A
# three-letter code is needed to join to other tables, so LAR is canonical and the
# printed code is kept alongside it. No other club code is altered.
CANONICAL = {"LA": "LAR"}

# The 137th game. Read from its own official game page on 2026-11-14 because the
# by-week page for Week 10 still shows the other thirteen games as unplayed.
WEEK_10_PLAYED = [{
    "week": 10,
    "date": "2026-11-12",
    "weekday": "Thursday",
    "away": "WAS",
    "home": "NYG",
    "away_score": 24,
    "home_score": 21,
    "status": "FINAL",
    "source_url": "https://www.nfl.com/games/commanders-at-giants-2026-reg-10",
    "retrieved": "2026-11-14",
    "evidence": "nfl-competition/evidence/nfl-game-commanders-at-giants-2026-reg-10.md",
    "source_ids": ["CP-NFL-W10-GAME-WASNYG"],
}]

SETTLEMENT_RULES = [
    {"market": "Side (point spread, home perspective)",
     "rule": "The home side covers when (home points - away points) is strictly greater "
             "than the home spread; it fails when strictly less; it is a push when equal.",
     "tie_case": "A tied game is graded against the spread as a normal result; the "
                 "project does not void it.",
     "authority": "Project grading rule. No operator rule was retrieved, so no operator "
                  "settlement is claimed."},
    {"market": "Total (over / under)",
     "rule": "The over wins when (home points + away points) is strictly greater than "
             "the total; the under wins when strictly less; it is a push when equal.",
     "tie_case": "A push is recorded as neither a win nor a loss and leaves the "
                 "denominator.",
     "authority": "Project grading rule."},
    {"market": "Moneyline",
     "rule": "The home moneyline wins when the home club scores more points; the away "
             "moneyline wins when the away club scores more.",
     "tie_case": "A tied game is void for moneyline grading: the bet is removed from "
                 "both the numerator and the denominator. One tie exists in the feed "
                 "(see the tie row).",
     "authority": "Project grading rule."},
    {"market": "Multi-leg (parlay)",
     "rule": "A parlay wins only if every leg wins under the rules above. A push leg "
             "reduces the leg count rather than voiding the slip.",
     "tie_case": "Stated so a reader can reproduce a graded parlay; no parlay is priced.",
     "authority": "Project grading rule."},
]

FEED_FIELDS = [
    "game_id", "season", "week", "date", "weekday", "home", "away",
    "home_score", "away_score", "home_margin", "total_points", "result",
    "status", "source_url", "retrieved", "evidence", "source_ids",
]


def canon(code):
    return CANONICAL.get(code, code)


def load_archive():
    rows = []
    for row in read_csv(ARCHIVE):
        rows.append({
            "week": int(row["week"]),
            "date": row["date"],
            "weekday": row["weekday"],
            "away": canon(row["away"]),
            "home": canon(row["home"]),
            "away_score": int(row["away_score"]),
            "home_score": int(row["home_score"]),
            "status": "FINAL",
            "source_url": row["source_url"],
            "retrieved": row["retrieved"],
            "evidence": row["evidence"],
            "source_ids": ["CP-NFL-RESULTS-W1-9"],
        })
    return rows


def feed_rows():
    rows = load_archive() + WEEK_10_PLAYED
    rows.sort(key=lambda r: (r["week"], r["date"], r["home"], r["away"]))
    out = []
    for index, row in enumerate(rows, start=1):
        margin = row["home_score"] - row["away_score"]
        out.append({
            "game_id": f"G{index:03d}",
            "season": 2026,
            "week": row["week"],
            "date": row["date"],
            "weekday": row["weekday"],
            "home": row["home"],
            "away": row["away"],
            "home_score": row["home_score"],
            "away_score": row["away_score"],
            "home_margin": margin,
            "total_points": row["home_score"] + row["away_score"],
            "result": "HOME" if margin > 0 else ("AWAY" if margin < 0 else "TIE"),
            "status": row["status"],
            "source_url": row["source_url"],
            "retrieved": row["retrieved"],
            "evidence": row["evidence"],
            "source_ids": ";".join(row["source_ids"]),
        })
    return out


def derive_table(rows):
    table = {}
    for row in rows:
        for club, scored, allowed in ((row["home"], row["home_score"], row["away_score"]),
                                      (row["away"], row["away_score"], row["home_score"])):
            entry = table.setdefault(club, {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0, "gp": 0})
            entry["pf"] += scored
            entry["pa"] += allowed
            entry["gp"] += 1
            if scored > allowed:
                entry["w"] += 1
            elif scored < allowed:
                entry["l"] += 1
            else:
                entry["t"] += 1
    return table


def reconcile(rows):
    """Compare the re-derived table with the standings read the same day."""
    derived = derive_table(rows)
    standings = read_csv(STANDINGS)
    checks, mismatches = [], []
    for row in standings:
        club = canon(row["club_abbr"])
        expected = {
            "w": int(row["wins"]), "l": int(row["losses"]), "t": int(row["ties"]),
            "pf": int(row["points_for"]), "pa": int(row["points_against"]),
            "gp": int(row["wins"]) + int(row["losses"]) + int(row["ties"]),
        }
        got = derived.get(club)
        if got is None:
            mismatches.append({"club": club, "field": "presence",
                               "expected": "present", "derived": "absent"})
            continue
        for field, want in expected.items():
            checks.append({"club": club, "field": field, "expected": want,
                           "derived": got[field], "match": got[field] == want})
            if got[field] != want:
                mismatches.append({"club": club, "field": field, "expected": want,
                                   "derived": got[field]})
    extra = sorted(set(derived) - {canon(r["club_abbr"]) for r in standings})
    for club in extra:
        mismatches.append({"club": club, "field": "presence", "expected": "absent",
                           "derived": "present"})
    return {
        "rows_compared": len(standings),
        "fields_compared": len(checks),
        "fields_matching": sum(1 for c in checks if c["match"]),
        "mismatches": mismatches,
        "league_points_scored": sum(r["total_points"] for r in rows),
        "league_points_allowed": sum(r["total_points"] for r in rows),
        "team_games": sum(v["gp"] for v in derived.values()),
        "clubs": len(derived),
    }


def load_byes():
    if not BYES.exists():
        return []
    return [dict(row) for row in read_csv(BYES)]


def build():
    rows = feed_rows()
    recon = reconcile(rows)
    if recon["mismatches"]:
        raise SystemExit("REFUSING TO PUBLISH: results feed disagrees with the official "
                         f"standings: {recon['mismatches'][:5]}")
    byes = load_byes()
    write_csv(FEED_CSV, rows, FEED_FIELDS)
    by_week = defaultdict(int)
    for row in rows:
        by_week[row["week"]] += 1
    payload = {
        "requirement": "R2 - verified results feed",
        "built_for": "2026 NFL season, weeks 1 to 10 (Week 10 partially played)",
        "read_on": "2026-11-14",
        "games": len(rows),
        "weeks": {str(week): count for week, count in sorted(by_week.items())},
        "weeks_in_feed": sorted(by_week),
        "byes_rows": len(byes),
        "sources": {
            "weeks_1_to_9": "https://www.nfl.com/schedules/2026/by-week/week-1 (136 games, "
                            "captured 2026-11-14)",
            "week_10": "https://www.nfl.com/games/commanders-at-giants-2026-reg-10 "
                       "(1 game, read 2026-11-14)",
        },
        "reconciliation": recon,
        "settlement_rules": SETTLEMENT_RULES,
        "settlement_authority": "Project rule for grading an originated line. No operator "
                                "published a settlement rule to this project.",
        "known_limits": [
            "One partial season; clubs have played eight or nine games.",
            "Every row is a single-source reading of one NFL.com page.",
            "The feed carries no price, so a graded row measures direction, never return.",
            "Byes are carried from the capturing session and are not re-derived here.",
        ],
        "rows": rows,
    }
    return round_value(payload, 6)


def main():
    if check_artifact(OUT, build()):
        payload = build()
        print(f"  {payload['games']} settled games; "
              f"{payload['reconciliation']['fields_matching']}/"
              f"{payload['reconciliation']['fields_compared']} club fields match the "
              f"official standings")


if __name__ == "__main__":
    main()
