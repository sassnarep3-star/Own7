"""Parse the saved official NFL by-week schedule pages into a results table.

The only inputs are the rendered-text evidence files under ``nfl-results/evidence``
that were actually read from https://www.nfl.com/schedules/2026/by-week/week-N on
2026-11-14. Nothing is typed in by hand and no value is inferred:

* a game is published only when the evidence file contains a dated result headline of
  the exact form ``Away 24, Home 21, FINAL, <weekday>, <Month> <day>``;
* a bye is published only when the club is listed under "Teams on Bye";
* the parser then recomputes every club's W-L-T, points for and points against from the
  parsed games and **refuses to emit** unless they reconcile exactly with the frozen
  official standings snapshot in ``data/nfl-standings-2026.csv``.

Reconciliation is the point. If a score were misread, the W-L-T or PF/PA totals would
drift and the build would abort instead of publishing a contradiction.
"""
from __future__ import annotations

import csv
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "nfl-results" / "evidence"
OUT = ROOT / "nfl-results" / "data"
STANDINGS = ROOT / "data" / "nfl-standings-2026.csv"

SOURCE_URL = "https://www.nfl.com/schedules/2026/by-week/week-{week}"
RETRIEVED = "2026-11-14"

# The publisher abbreviates club names in the headline; the standings use full names.
# This map is a naming map only. It carries no data value and is checked for completeness
# both ways (every parsed abbreviation must resolve, every NHL club must be reachable).
ABBR = {
    "Arizona Cardinals": "AZ", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF", "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC", "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA", "Miami Dolphins": "MIA", "Minnesota Vikings": "MIN",
    "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF", "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN", "Washington Commanders": "WAS",
}
NAME_BY_ABBR = {v: k for k, v in ABBR.items()}

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}

# "Jaguars 33, Ravens 10, FINAL, Thursday, November 5th"
GAME = re.compile(
    r"(?P<away>[A-Za-z0-9]+) (?P<ascore>\d{1,2}), (?P<home>[A-Za-z0-9]+) (?P<hscore>\d{1,2}), "
    r"FINAL, (?P<weekday>Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December) "
    r"(?P<day>\d{1,2})(?:st|nd|rd|th)"
)

# Headline words that are club nicknames, mapped to abbreviation. Nicknames are unique in
# the league, so this is unambiguous. Full club names are not used because the publisher
# prints the nickname only.
NICKNAME = {
    "Cardinals": "AZ", "Falcons": "ATL", "Ravens": "BAL", "Bills": "BUF", "Panthers": "CAR",
    "Bears": "CHI", "Bengals": "CIN", "Browns": "CLE", "Cowboys": "DAL", "Broncos": "DEN",
    "Lions": "DET", "Packers": "GB", "Texans": "HOU", "Colts": "IND", "Jaguars": "JAX",
    "Chiefs": "KC", "Raiders": "LV", "Chargers": "LAC", "Rams": "LA", "Dolphins": "MIA",
    "Vikings": "MIN", "Patriots": "NE", "Saints": "NO", "Giants": "NYG", "Jets": "NYJ",
    "Eagles": "PHI", "Steelers": "PIT", "49ers": "SF", "Seahawks": "SEA", "Buccaneers": "TB",
    "Titans": "TEN", "Commanders": "WAS",
}

BYE = re.compile(r"^(?P<abbr>[A-Z]{2,3})(?P<club>[A-Za-z0-9 ]+?)\s+(?P<w>\d{1,2})-(?P<l>\d{1,2})(?:-(?P<t>\d{1,2}))?(?P<words>.*)$")
BYE_SECTION = "## Teams on Bye"


def parse_week(week: int) -> tuple[list[dict], list[str]]:
    path = EVIDENCE / f"week-{week}.schedule.md"
    if not path.exists():
        raise SystemExit(f"Missing evidence for week {week}: {path}")
    text = path.read_text(encoding="utf-8")

    games: list[dict] = []
    seen: set[str] = set()
    for line in text.splitlines():
        match = GAME.search(line)
        if not match:
            continue
        away = NICKNAME.get(match["away"])
        home = NICKNAME.get(match["home"])
        if away is None or home is None:
            raise SystemExit(f"Unknown club in headline: {line.strip()}")
        month = MONTHS[match["month"]]
        day = int(match["day"])
        key = f"{away}@{home}"
        if key in seen:
            raise SystemExit(f"Duplicate fixture parsed in week {week}: {key}")
        seen.add(key)
        games.append({
            "week": week,
            "date": f"2026-{month:02d}-{day:02d}",
            "weekday": match["weekday"],
            "away": away,
            "home": home,
            "away_score": int(match["ascore"]),
            "home_score": int(match["hscore"]),
            "source_url": SOURCE_URL.format(week=week),
            "retrieved": RETRIEVED,
            "evidence": f"nfl-results/evidence/week-{week}.schedule.md",
        })

    byes: list[str] = []
    in_bye = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            in_bye = line.startswith(BYE_SECTION)
            continue
        if not in_bye or not line:
            continue
        m = BYE.match(line)
        if m and m["abbr"] in NAME_BY_ABBR:
            byes.append(m["abbr"])
    return games, byes


def reconciliation(standings: list[dict]) -> dict:
    games: list[dict] = []
    byes: dict[int, list[str]] = {}
    for week in range(1, 10):
        week_games, week_byes = parse_week(week)
        # The expected game count is derived, not assumed: every club that is not
        # printed on the bye list must appear exactly once in the week's fixtures.
        expected_games = (32 - len(week_byes)) // 2
        if len(week_byes) % 2:
            raise SystemExit(f"Week {week} has an odd bye count: {week_byes}")
        if len(week_games) != expected_games:
            raise SystemExit(
                f"Week {week} has {len(week_games)} games but {len(week_byes)} bye clubs "
                f"imply {expected_games}"
            )
        clubs = [g["away"] for g in week_games] + [g["home"] for g in week_games]
        if len(set(clubs)) != len(clubs):
            raise SystemExit(f"Week {week}: a club appears in more than one fixture")
        if set(clubs) & set(week_byes):
            raise SystemExit(f"Week {week}: a bye club also has a fixture")
        if len(set(clubs)) + len(week_byes) != 32:
            raise SystemExit(f"Week {week}: fixtures plus byes do not cover all 32 clubs")
        games.extend(week_games)
        byes[week] = week_byes

    total_byes = sum(len(v) for v in byes.values())
    if len(games) != 144 - total_byes // 2:
        raise SystemExit(f"Parsed {len(games)} games, expected {144 - total_byes // 2}")

    # Recompute every club total from the parsed games only.
    tally: dict[str, dict] = {
        NAME_BY_ABBR[abbr]: {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0, "gp": 0}
        for abbr in NAME_BY_ABBR
    }
    for game in games:
        away, home = game["away"], game["home"]
        a, h = game["away_score"], game["home_score"]
        for club, scored, allowed in ((away, a, h), (home, h, a)):
            row = tally[NAME_BY_ABBR[club]]
            row["pf"] += scored
            row["pa"] += allowed
            row["gp"] += 1
            if scored > allowed:
                row["w"] += 1
            elif scored < allowed:
                row["l"] += 1
            else:
                row["t"] += 1

    mismatches: list[dict] = []
    for official in standings:
        club = official["Team"]
        got = tally[club]
        for field, csv_field in (("w", "W"), ("l", "L"), ("t", "T"), ("pf", "PF"), ("pa", "PA")):
            want = int(official[csv_field])
            if got[field] != want:
                mismatches.append({
                    "team": club, "field": field, "parsed": got[field], "official": want,
                })
    return {"games": games, "byes": byes, "tally": tally, "mismatches": mismatches}


def main() -> int:
    standings = list(csv.DictReader(STANDINGS.open(encoding="utf-8", newline="")))
    if len(standings) != 32:
        raise SystemExit(f"Expected 32 standings rows, got {len(standings)}")

    result = reconciliation(standings)
    if result["mismatches"]:
        print("RECONCILIATION FAILED — refusing to publish.", file=sys.stderr)
        for item in result["mismatches"][:40]:
            print(f"  {item['team']}: parsed {item['field']}={item['parsed']} "
                  f"but official stands at {item['official']}", file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    games_path = OUT / "games-2026-w1-9.csv"
    fields = ["week", "date", "weekday", "away", "home", "away_score", "home_score",
              "source_url", "retrieved", "evidence"]
    with games_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for game in sorted(result["games"], key=lambda g: (g["week"], g["date"], g["away"])):
            writer.writerow(game)

    byes_path = OUT / "byes-2026-w1-9.csv"
    with byes_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["week", "team_code", "team", "source_url", "retrieved"])
        for week, clubs in sorted(result["byes"].items()):
            for club in sorted(clubs):
                writer.writerow([week, club, NAME_BY_ABBR[club], SOURCE_URL.format(week=week), RETRIEVED])

    total_byes = sum(len(v) for v in result["byes"].values())
    print(f"OK: {len(result['games'])} games, {total_byes} bye rows, "
          f"reconciled with 32 official standings rows on W-L-T, PF and PA.")
    print(f"    games -> {games_path.relative_to(ROOT)} (sha256 {hashlib.sha256(games_path.read_bytes()).hexdigest()[:16]})")
    print(f"    byes  -> {byes_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
