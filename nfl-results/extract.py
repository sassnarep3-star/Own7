"""Parse the saved official NFL by-week schedule pages into a results table.

The only inputs are the rendered-text evidence files under ``nfl-results/evidence``
that were actually read from https://www.nfl.com/schedules/2026/by-week/week-N on
2026-11-14 (weeks 1-9) and https://www.nfl.com/schedules/2026/REG10 on 2026-11-17
(week 10, frozen pre-Monday read: 13 finals + 1 scheduled-not-final), plus the
2026-11-18 completion re-read of https://www.nfl.com/schedules/2026/by-week/week-10
(week-10.complete.md: all 14 Week 10 finals) and the 2026-11-18 reads of
https://www.nfl.com/schedules/2026/by-week/week-11 and week-12 (weeks 11-12 are
published as kickoff-time fixtures only: no finals, scheduled fixtures and byes
only). Nothing is typed in by hand and no value is inferred:

* a game is published only when the evidence file contains a dated result headline of
  the exact form ``Away 24, Home 21, FINAL, <weekday>, <Month> <day>``;
* a game that the publisher prints with a kickoff time instead of a score is
  published in the scheduled table, never in the results feed;
* a bye is published only when the club is listed under "Teams on Bye";
* the parser then recomputes every club's W-L-T, points for and points against from
  the parsed games and **refuses to emit** unless they reconcile exactly with the
  official standings snapshots in ``data/nfl-standings-2026.csv`` (frozen
  pre-kickoff Week 10 read, reconciles the weeks 1-9 feed),
  ``data/nfl-standings-2026-11-17.csv`` (fresh 2026-11-17 read, reconciles the
  frozen weeks 1-10 feed minus the one scheduled-not-final game) and
  ``data/nfl-standings-2026-11-18.csv`` (fresh 2026-11-18 read, reconciles the
  completed weeks 1-10 feed).

Reconciliation is the point. If a score were misread, the W-L-T or PF/PA totals would
drift and the build would abort instead of publishing a contradiction. Chain checks
tie the snapshots together: the 2026-11-17 snapshot must equal the frozen snapshot
plus exactly the parsed frozen Week 10 deltas, and the 2026-11-18 snapshot must equal
the 2026-11-17 snapshot plus exactly the parsed Week 10 completion deltas (the
Chargers at Ravens Monday final). The completion re-read must also agree with the
frozen Week 10 read on all 13 frozen finals and may only add the fixture the frozen
read printed as scheduled.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "nfl-results" / "evidence"
OUT = ROOT / "nfl-results" / "data"
FROZEN_STANDINGS = ROOT / "data" / "nfl-standings-2026.csv"
FRESH_STANDINGS = ROOT / "data" / "nfl-standings-2026-11-17.csv"
FRESH_STANDINGS_EVIDENCE = ROOT / "research" / "nfl" / "evidence" / "standings-2026-11-17.retrieved.md"
COMPLETE_STANDINGS = ROOT / "data" / "nfl-standings-2026-11-18.csv"
COMPLETE_STANDINGS_EVIDENCE = ROOT / "research" / "nfl" / "evidence" / "standings-2026-11-18.retrieved.md"

SOURCE_URL = "https://www.nfl.com/schedules/2026/by-week/week-{week}"
WEEK_10_URL = "https://www.nfl.com/schedules/2026/REG10"
WEEK_10_COMPLETE_URL = "https://www.nfl.com/schedules/2026/by-week/week-10"
WEEK_11_URL = "https://www.nfl.com/schedules/2026/by-week/week-11"
WEEK_12_URL = "https://www.nfl.com/schedules/2026/by-week/week-12"
# Per-week provenance: the URL actually read and the date it was read.
SOURCE_URL_BY_WEEK = {week: SOURCE_URL.format(week=week) for week in range(1, 10)}
SOURCE_URL_BY_WEEK[10] = WEEK_10_URL
SOURCE_URL_BY_WEEK[11] = WEEK_11_URL
SOURCE_URL_BY_WEEK[12] = WEEK_12_URL
RETRIEVED_BY_WEEK = {week: "2026-11-14" for week in range(1, 10)}
RETRIEVED_BY_WEEK[10] = "2026-11-17"
RETRIEVED_BY_WEEK[11] = "2026-11-18"
RETRIEVED_BY_WEEK[12] = "2026-11-18"
# The 2026-11-18 completion re-read of week 10 carries its own provenance.
WEEK_10_COMPLETE_RETRIEVED = "2026-11-18"

# The publisher abbreviates club names in the headline; the standings use full names.
# This map is a naming map only. It carries no data value and is checked for completeness
# both ways (every parsed abbreviation must resolve, every club must be reachable).
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

# Structural reference lists (naming/structure only, not data): used to check that the
# parsed sections and the fixture/bye cover are complete. The same reference the
# canonical extractor uses.
AFC = ("BUF NE NYJ MIA PIT CIN CLE BAL JAX HOU IND TEN DEN KC LV LAC").split()
NFC = ("NYG DAL WAS PHI CHI DET MIN GB CAR NO TB ATL SF SEA LA AZ").split()

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

# "Chargers at Ravens, Monday, November 16th, 8:15 PM, ESPN"  (scheduled, no score)
SCHEDULED = re.compile(
    r"^(?P<away>[A-Za-z0-9]+) at (?P<home>[A-Za-z0-9]+), "
    r"(?P<weekday>Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December) "
    r"(?P<day>\d{1,2})(?:st|nd|rd|th), (?P<hour>\d{1,2}):(?P<minute>\d{2}) (?P<ampm>AM|PM), (?P<tv>[A-Z]+)$"
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
SCHEDULED_SECTION = "## Scheduled"

# Structural reference: club to division. The 2026-11-17 standings rendering prints no
# division header rows, so division labels come from this reference map, not from the
# page. Conference labels, by contrast, are parsed from the page sections and checked.
CLUB_DIVISION = {
    "BUF": "AFC East", "NE": "AFC East", "NYJ": "AFC East", "MIA": "AFC East",
    "PIT": "AFC North", "CIN": "AFC North", "CLE": "AFC North", "BAL": "AFC North",
    "JAX": "AFC South", "HOU": "AFC South", "IND": "AFC South", "TEN": "AFC South",
    "DEN": "AFC West", "KC": "AFC West", "LV": "AFC West", "LAC": "AFC West",
    "NYG": "NFC East", "DAL": "NFC East", "WAS": "NFC East", "PHI": "NFC East",
    "CHI": "NFC North", "DET": "NFC North", "MIN": "NFC North", "GB": "NFC North",
    "CAR": "NFC South", "NO": "NFC South", "TB": "NFC South", "ATL": "NFC South",
    "SF": "NFC West", "SEA": "NFC West", "LA": "NFC West", "AZ": "NFC West",
}

# The 2026-11-17 standings rendering: the club link now embeds the display name
# ("<img .../logos/CODE>...Name...](team-url) | cells"), and the bare club code the
# November rendering printed between the links is gone. Cells are unchanged: the same
# 16 value cells in the same positions (validated arithmetically below).
ROW_1117 = re.compile(
    r"^\|\s*\[!\[\]\([^)]*/logos/(?P<code>[A-Z]{2,3})\).*?\]\((?P<teamurl>[^)]+)\)\s*\|(?P<rest>.*)$"
)


def parse_week(week: int) -> tuple[list[dict], list[str], list[dict]]:
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
            "source_url": SOURCE_URL_BY_WEEK[week],
            "retrieved": RETRIEVED_BY_WEEK[week],
            "evidence": f"nfl-results/evidence/week-{week}.schedule.md",
        })

    scheduled: list[dict] = []
    in_sched = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            in_sched = line.startswith(SCHEDULED_SECTION)
            continue
        if not in_sched or not line:
            continue
        m = SCHEDULED.match(line.lstrip("- ").strip())
        if not m:
            continue
        away = NICKNAME.get(m["away"])
        home = NICKNAME.get(m["home"])
        if away is None or home is None:
            raise SystemExit(f"Unknown club in scheduled fixture: {line.strip()}")
        scheduled.append({
            "week": week,
            "date": f"2026-{MONTHS[m['month']]:02d}-{int(m['day']):02d}",
            "weekday": m["weekday"],
            "away": away,
            "home": home,
            "kickoff": f"{m['hour']}:{m['minute']} {m['ampm']}",
            "tv": m["tv"],
            "source_url": SOURCE_URL_BY_WEEK[week],
            "retrieved": RETRIEVED_BY_WEEK[week],
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
    return games, byes, scheduled


def parse_week10_complete(
    frozen_games: list[dict], frozen_scheduled: list[dict], frozen_byes: list[str]
) -> tuple[list[dict], list[str]]:
    """Parse the 2026-11-18 completion re-read of week 10 and cross-check it.

    The re-read must agree with the frozen 2026-11-17 read on every frozen final
    (identical pairing, scores and date) and on the bye list, and may only add
    finals for fixtures the frozen read printed as scheduled-not-final. Any other
    difference aborts the build instead of publishing a contradiction. The games
    the re-read adds carry the re-read's own provenance (URL, retrieval date and
    evidence file), so every row of the completed feed names exactly where it came
    from.
    """
    path = EVIDENCE / "week-10.complete.md"
    if not path.exists():
        raise SystemExit(f"Missing evidence for the week 10 completion: {path}")
    text = path.read_text(encoding="utf-8")

    complete: list[dict] = []
    seen: set[str] = set()
    for line in text.splitlines():
        match = GAME.search(line)
        if not match:
            continue
        away = NICKNAME.get(match["away"])
        home = NICKNAME.get(match["home"])
        if away is None or home is None:
            raise SystemExit(f"Unknown club in completion headline: {line.strip()}")
        month = MONTHS[match["month"]]
        day = int(match["day"])
        key = f"{away}@{home}"
        if key in seen:
            raise SystemExit(f"Duplicate fixture parsed in the week 10 completion: {key}")
        seen.add(key)
        complete.append({
            "week": 10,
            "date": f"2026-{month:02d}-{day:02d}",
            "weekday": match["weekday"],
            "away": away,
            "home": home,
            "away_score": int(match["ascore"]),
            "home_score": int(match["hscore"]),
            "source_url": WEEK_10_COMPLETE_URL,
            "retrieved": WEEK_10_COMPLETE_RETRIEVED,
            "evidence": "nfl-results/evidence/week-10.complete.md",
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

    # Cross-check 1: every frozen final must appear identically in the re-read.
    frozen_keys = {}
    for game in frozen_games:
        frozen_keys[f"{game['away']}@{game['home']}"] = game
    for key, game in frozen_keys.items():
        match = next((g for g in complete if f"{g['away']}@{g['home']}" == key), None)
        if match is None:
            raise SystemExit(
                f"Week 10 completion re-read is missing frozen final {key}")
        for field in ("date", "away_score", "home_score"):
            if str(match[field]) != str(game[field]):
                raise SystemExit(
                    f"Week 10 completion re-read contradicts the frozen read on {key}: "
                    f"{field} re-read {match[field]} vs frozen {game[field]}")

    # Cross-check 2: the re-read may only add finals for the frozen scheduled fixtures.
    sched_keys = {f"{g['away']}@{g['home']}" for g in frozen_scheduled}
    frozen_set = set(frozen_keys)
    added = [g for g in complete if f"{g['away']}@{g['home']}" not in frozen_set]
    added_keys = {f"{g['away']}@{g['home']}" for g in added}
    if added_keys != sched_keys:
        raise SystemExit(
            "Week 10 completion re-read added finals beyond the frozen scheduled "
            f"fixtures: added {sorted(added_keys)}, frozen scheduled {sorted(sched_keys)}")

    # Cross-check 3: the bye list must be identical to the frozen read.
    if sorted(byes) != sorted(frozen_byes):
        raise SystemExit(
            "Week 10 completion re-read bye list differs from the frozen read: "
            f"re-read {sorted(byes)} vs frozen {sorted(frozen_byes)}")

    return complete, byes


def parse_standings_snapshot(
    evidence_path: Path = FRESH_STANDINGS_EVIDENCE,
    verified_label: str = "verified snapshot 2026-11-17 (pre Week 10 MNF)",
) -> list[dict]:
    """Parse a fresh standings evidence capture into the same 18-column schema."""
    text = evidence_path.read_text(encoding="utf-8")
    rows: list[dict] = []
    section = None
    seen_codes: set[str] = set()
    for line in text.splitlines():
        if line.strip() == "AMERICAN FOOTBALL CONFERENCE":
            section = "AFC"
            continue
        if line.strip() == "NATIONAL FOOTBALL CONFERENCE":
            section = "NFC"
            continue
        if line.startswith("| [!") and "/logos/" in line:
            match = ROW_1117.match(line)
            if not match:
                raise SystemExit(f"Unparsed standings row in {evidence_path.name}: {line[:80]}")
            code = match["code"]
            if code in seen_codes:
                raise SystemExit(f"Duplicate club row for {code}")
            seen_codes.add(code)
            if section is None:
                raise SystemExit(f"Standings row before any conference section: {line[:80]}")
            cells = [c.strip() for c in match["rest"].strip().strip("|").split("|")]
            values = cells[1:] if cells and cells[0] == "" else cells
            if len(values) != 16:
                raise SystemExit(
                    f"Standings row has {len(values)} value cells, expected 16: {code}")
            num = re.compile(r"^-?\d+(?:\.\d+)?$")
            rec = re.compile(r"^\d+ - \d+ - \d+$")
            streak = re.compile(r"^\d+[WLT]$")
            for i, v in enumerate(values):
                if i == 14:
                    if not streak.match(v):
                        raise SystemExit(f"Unrecognised streak field for {code}: {v!r}")
                    continue
                if i in (1, 2, 3, 4, 5, 6, 7, 8):
                    continue
                if not (num.match(v) or rec.match(v)):
                    raise SystemExit(f"Non-numeric standings field for {code}: {v!r}")
            w, l, t, pct, pf, pa, net = (values[0], values[1], values[2], values[3],
                                         values[4], values[5], values[6])
            w_i, l_i, t_i, pf_i, pa_i, net_i = (int(w), int(l), int(t), int(pf), int(pa), int(net))
            if abs((w_i + t_i / 2) / (w_i + l_i + t_i) - float(pct)) > 0.00051:
                raise SystemExit(f"{code}: PCT does not match (W + T/2)/games")
            if pf_i - pa_i != net_i:
                raise SystemExit(f"{code}: NET PTS is not PF - PA")
            home = [int(x) for x in values[7].split(" - ")]
            road = [int(x) for x in values[8].split(" - ")]
            if (home[0] + road[0], home[1] + road[1], home[2] + road[2]) != (w_i, l_i, t_i):
                raise SystemExit(f"{code}: HOME+ROAD record does not equal overall record")
            if section == "AFC" and code not in AFC or section == "NFC" and code not in NFC:
                raise SystemExit(f"{code}: section does not match the reference conference list")
            rows.append({
                "Conference": section,
                "Division": CLUB_DIVISION[code],
                "Team": NAME_BY_ABBR[code],
                "W": w_i, "L": l_i, "T": t_i,
                "PCT": f"{float(pct):.3f}",
                "PF": pf_i, "PA": pa_i, "NetPts": net_i,
                "Home": values[7].replace(" ", ""),
                "Road": values[8].replace(" ", ""),
                "Div": values[9].replace(" ", ""),
                "Conf": values[11].replace(" ", ""),
                "Strk": values[14],
                "Last5": values[15].replace(" ", ""),
                "Source": "https://www.nfl.com/standings/",
                "Verified": verified_label,
            })
    if len(rows) != 32 or len(set(r["Team"] for r in rows)) != 32:
        raise SystemExit(f"Fresh standings rows={len(rows)}, expected 32 unique clubs")
    if sum(r["W"] for r in rows) != sum(r["L"] for r in rows):
        raise SystemExit("Fresh snapshot: league-wide wins != losses")
    return rows


def tally_from(games: list[dict]) -> dict[str, dict]:
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
    return tally


def reconcile(standings: list[dict], tally: dict[str, dict]) -> list[dict]:
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
    return mismatches


def check_week_structure(week: int, week_games: list[dict], week_byes: list[str],
                         week_scheduled: list[dict]) -> None:
    """Structural checks shared by every week: fixture cover, club disjointness.

    The expected fixture count is derived, not assumed: every club that is not
    printed on the bye list and not in a scheduled-not-final fixture must appear
    exactly once across the week's published results and scheduled fixtures.
    """
    if len(week_byes) % 2:
        raise SystemExit(f"Week {week} has an odd bye count: {week_byes}")
    fixtures = len(week_games) + len(week_scheduled)
    expected_fixtures = (32 - len(week_byes)) // 2
    if fixtures != expected_fixtures:
        raise SystemExit(
            f"Week {week} has {len(week_games)} finals + {len(week_scheduled)} scheduled "
            f"= {fixtures} fixtures but {len(week_byes)} bye clubs imply {expected_fixtures}"
        )
    clubs = [g["away"] for g in week_games] + [g["home"] for g in week_games]
    sched_clubs = [g["away"] for g in week_scheduled] + [g["home"] for g in week_scheduled]
    if len(set(clubs)) != len(clubs):
        raise SystemExit(f"Week {week}: a club appears in more than one result")
    if len(set(sched_clubs)) != len(sched_clubs):
        raise SystemExit(f"Week {week}: a club appears in more than one scheduled fixture")
    if set(clubs) & set(week_byes):
        raise SystemExit(f"Week {week}: a bye club also has a result")
    if set(sched_clubs) & set(week_byes):
        raise SystemExit(f"Week {week}: a bye club also has a scheduled fixture")
    if set(clubs) & set(sched_clubs):
        raise SystemExit(f"Week {week}: a club has both a result and a scheduled fixture")
    if len(set(clubs)) + len(set(sched_clubs)) + len(week_byes) != 32:
        raise SystemExit(f"Week {week}: results, scheduled fixtures and byes do not cover all 32 clubs")


def reconciliation() -> dict:
    # Weeks 1-12 as printed by the publisher: finals, byes and scheduled fixtures.
    # Weeks 1-10 come from the frozen reads (2026-11-14 weeks 1-9; week 10 the
    # 2026-11-17 REG10 read). Weeks 11-12 come from the 2026-11-18 reads and are
    # scheduled-fixture-only capture (no finals at read time).
    parsed: dict[int, tuple[list[dict], list[str], list[dict]]] = {}
    for week in range(1, 13):
        week_games, week_byes, week_scheduled = parse_week(week)
        check_week_structure(week, week_games, week_byes, week_scheduled)
        parsed[week] = (week_games, week_byes, week_scheduled)

    frozen_byes = {week: parsed[week][1] for week in range(1, 11)}

    # Completed week 10: the 2026-11-18 re-read, cross-checked against the frozen
    # read, used to complete the weeks 1-10 results feed.
    complete_w10, complete_w10_byes = parse_week10_complete(
        parsed[10][0], parsed[10][2], parsed[10][1])
    check_week_structure(10, complete_w10, complete_w10_byes, [])

    frozen_sched = parsed[10][2]
    frozen_final_keys = {f"{g['away']}@{g['home']}" for g in parsed[10][0]}
    completed_w10 = parsed[10][0] + [
        g for g in complete_w10
        if f"{g['away']}@{g['home']}" not in frozen_final_keys
    ]

    frozen_feed = [g for week in range(1, 10) for g in parsed[week][0]] + parsed[10][0]
    complete_feed = [g for week in range(1, 10) for g in parsed[week][0]] + completed_w10

    total_byes_all = sum(len(parsed[week][1]) for week in range(1, 13))
    scheduled_all = [g for week in (11, 12) for g in parsed[week][2]]
    expected_finals = 16 * 12 - total_byes_all // 2 - len(scheduled_all)
    if len(complete_feed) != expected_finals:
        raise SystemExit(
            f"Parsed {len(complete_feed)} finals, expected {expected_finals}"
        )

    # Invariant 1 (unchanged): the weeks 1-9 feed reconciles with the frozen
    # pre-kickoff standings snapshot exactly.
    frozen = list(csv.DictReader(FROZEN_STANDINGS.open(encoding="utf-8", newline="")))
    if len(frozen) != 32:
        raise SystemExit(f"Expected 32 frozen standings rows, got {len(frozen)}")
    w1_9 = [g for g in frozen_feed if g["week"] <= 9]
    mismatch_frozen = reconcile(frozen, tally_from(w1_9))

    # Invariant 2 (unchanged): the frozen weeks 1-10 feed (scheduled games excluded)
    # reconciles with the fresh 2026-11-17 snapshot exactly. The snapshot is parsed
    # from its own evidence here so no hand-typed value can intervene.
    fresh = parse_standings_snapshot()
    mismatch_fresh = reconcile(fresh, tally_from(frozen_feed))

    # Invariant 3 (unchanged): 2026-11-17 snapshot == frozen snapshot + exactly the
    # parsed frozen Week 10 result deltas (the scheduled game contributes nothing).
    w10_frozen = [g for g in frozen_feed if g["week"] == 10]
    delta: dict[str, dict] = _delta_table(w10_frozen)

    # Invariant 4 (new): the completed weeks 1-10 feed reconciles with the fresh
    # 2026-11-18 snapshot exactly.
    complete = parse_standings_snapshot(
        COMPLETE_STANDINGS_EVIDENCE,
        "verified snapshot 2026-11-18 (post Week 10, pre Week 11)",
    )
    mismatch_complete = reconcile(complete, tally_from(complete_feed))

    # Invariant 5 (new): 2026-11-18 snapshot == 2026-11-17 snapshot + exactly the
    # parsed Week 10 completion deltas (only the fixtures the frozen read printed
    # as scheduled-not-final).
    completion_delta = _delta_table([g for g in completed_w10
                                     if f"{g['away']}@{g['home']}" not in frozen_final_keys])

    fresh_by_team = {r["Team"]: r for r in fresh}
    drift: list[dict] = []
    for row in complete:
        base = fresh_by_team[row["Team"]]
        d = completion_delta[row["Team"]]
        for field, csv_field in (("w", "W"), ("l", "L"), ("t", "T"), ("pf", "PF"), ("pa", "PA")):
            want = int(base[csv_field]) + d[field]
            if int(row[csv_field]) != want:
                drift.append({
                    "team": row["Team"], "field": field,
                    "snapshot_1117": int(base[csv_field]), "completion_delta": d[field],
                    "snapshot_1118": int(row[csv_field]),
                })
    frozen_by_team = {r["Team"]: r for r in frozen}
    drift_frozen: list[dict] = []
    for row in fresh:
        base = frozen_by_team[row["Team"]]
        d = delta[row["Team"]]
        for field, csv_field in (("w", "W"), ("l", "L"), ("t", "T"), ("pf", "PF"), ("pa", "PA")):
            want = int(base[csv_field]) + d[field]
            if int(row[csv_field]) != want:
                drift_frozen.append({
                    "team": row["Team"], "field": field,
                    "frozen": int(base[csv_field]), "week10_delta": d[field],
                    "fresh": int(row[csv_field]),
                })
    return {
        "games": complete_feed, "frozen_games": frozen_feed,
        "byes": {week: parsed[week][1] for week in range(1, 13)},
        "scheduled": frozen_sched + scheduled_all,
        "scheduled_w10": frozen_sched,
        "scheduled_w11": parsed[11][2],
        "scheduled_w12": parsed[12][2],
        "fresh_standings": fresh, "complete_standings": complete,
        "mismatch_frozen_w1_9": mismatch_frozen,
        "mismatch_fresh_w1_10": mismatch_fresh,
        "mismatch_complete_w1_10": mismatch_complete,
        "snapshot_drift": drift_frozen,
        "completion_drift": drift,
        "tally_frozen": tally_from(w1_9),
        "tally_fresh": tally_from(frozen_feed),
        "tally_complete": tally_from(complete_feed),
    }


def _delta_table(games: list[dict]) -> dict[str, dict]:
    delta: dict[str, dict] = {
        team: {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0} for team in NAME_BY_ABBR.values()
    }
    for game in games:
        a, h = game["away_score"], game["home_score"]
        for club, scored, allowed in ((game["away"], a, h), (game["home"], h, a)):
            row = delta[NAME_BY_ABBR[club]]
            row["pf"] += scored
            row["pa"] += allowed
            if scored > allowed:
                row["w"] += 1
            elif scored < allowed:
                row["l"] += 1
            else:
                row["t"] += 1
    return delta


def main() -> int:
    result = reconciliation()
    failed = False
    if result["mismatch_frozen_w1_9"]:
        print("RECONCILIATION FAILED (weeks 1-9 vs frozen snapshot) — refusing to publish.",
              file=sys.stderr)
        for item in result["mismatch_frozen_w1_9"][:40]:
            print(f"  {item['team']}: parsed {item['field']}={item['parsed']} "
                  f"but official stands at {item['official']}", file=sys.stderr)
        failed = True
    if result["mismatch_fresh_w1_10"]:
        print("RECONCILIATION FAILED (frozen weeks 1-10 vs 2026-11-17 snapshot) — refusing to publish.",
              file=sys.stderr)
        for item in result["mismatch_fresh_w1_10"][:40]:
            print(f"  {item['team']}: parsed {item['field']}={item['parsed']} "
                  f"but official stands at {item['official']}", file=sys.stderr)
        failed = True
    if result["mismatch_complete_w1_10"]:
        print("RECONCILIATION FAILED (completed weeks 1-10 vs 2026-11-18 snapshot) — refusing to publish.",
              file=sys.stderr)
        for item in result["mismatch_complete_w1_10"][:40]:
            print(f"  {item['team']}: parsed {item['field']}={item['parsed']} "
                  f"but official stands at {item['official']}", file=sys.stderr)
        failed = True
    if result["snapshot_drift"]:
        print("SNAPSHOT DRIFT — the 2026-11-17 snapshot is not the frozen snapshot plus the "
              "parsed frozen Week 10 deltas; refusing to publish.", file=sys.stderr)
        for item in result["snapshot_drift"][:40]:
            print(f"  {item['team']}: {item['field']} frozen {item['frozen']} + "
                  f"delta {item['week10_delta']} != fresh {item['fresh']}", file=sys.stderr)
        failed = True
    if result["completion_drift"]:
        print("SNAPSHOT DRIFT — the 2026-11-18 snapshot is not the 2026-11-17 snapshot plus the "
              "parsed Week 10 completion deltas; refusing to publish.", file=sys.stderr)
        for item in result["completion_drift"][:40]:
            print(f"  {item['team']}: {item['field']} snapshot_1117 {item['snapshot_1117']} + "
                  f"delta {item['completion_delta']} != snapshot_1118 {item['snapshot_1118']}",
                  file=sys.stderr)
        failed = True
    if failed:
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    fields = ["week", "date", "weekday", "away", "home", "away_score", "home_score",
              "source_url", "retrieved", "evidence"]

    def write_games(path: Path, rows: list[dict]) -> Path:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for game in sorted(rows, key=lambda g: (g["week"], g["date"], g["away"])):
                writer.writerow(game)
        return path

    games_path = write_games(OUT / "games-2026-w1-9.csv", [g for g in result["frozen_games"] if g["week"] <= 9])
    games10_path = write_games(OUT / "games-2026-w1-10.csv", result["frozen_games"])
    games_complete_path = write_games(OUT / "games-2026-w1-10-complete.csv", result["games"])

    def write_byes(path: Path, weeks: range, url: str) -> Path:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(["week", "team_code", "team", "source_url", "retrieved"])
            for week in weeks:
                for club in sorted(result["byes"][week]):
                    writer.writerow([week, club, NAME_BY_ABBR[club],
                                     SOURCE_URL_BY_WEEK[week], RETRIEVED_BY_WEEK[week]])
        return path

    byes_path = write_byes(OUT / "byes-2026-w1-9.csv", range(1, 10), SOURCE_URL)
    byes10_path = write_byes(OUT / "byes-2026-w1-10.csv", range(1, 11), SOURCE_URL)
    byes_complete_path = write_byes(OUT / "byes-2026-w1-10-complete.csv", range(1, 11), SOURCE_URL)
    byes12_path = write_byes(OUT / "byes-2026-w1-12.csv", range(1, 13), SOURCE_URL)

    sched_fields = ["week", "date", "weekday", "away", "home", "kickoff", "tv",
                    "source_url", "retrieved", "evidence"]

    def write_scheduled(path: Path, rows: list[dict]) -> Path:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=sched_fields, lineterminator="\n")
            writer.writeheader()
            for row in sorted(rows, key=lambda g: (g["week"], g["away"])):
                writer.writerow(row)
        return path

    sched_path = write_scheduled(OUT / "scheduled-2026-w10.csv", result["scheduled_w10"])
    sched11_path = write_scheduled(OUT / "scheduled-2026-w11.csv", result["scheduled_w11"])
    sched12_path = write_scheduled(OUT / "scheduled-2026-w12.csv", result["scheduled_w12"])

    snapshot_fields = ["Conference", "Division", "Team", "W", "L", "T", "PCT", "PF", "PA",
                       "NetPts", "Home", "Road", "Div", "Conf", "Strk", "Last5",
                       "Source", "Verified"]

    def write_snapshot(path: Path, rows: list[dict]) -> Path:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=snapshot_fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        return path

    snapshot_path = write_snapshot(FRESH_STANDINGS, result["fresh_standings"])
    snapshot_complete_path = write_snapshot(COMPLETE_STANDINGS, result["complete_standings"])

    n_fields = 32 * 5
    recon_path = OUT / "reconciliation-2026-11-17.json"
    recon_path.write_text(json.dumps({
        "checked_on": "2026-11-17",
        "frozen_snapshot": "data/nfl-standings-2026.csv",
        "fresh_snapshot": "data/nfl-standings-2026-11-17.csv",
        "fresh_snapshot_source": "https://www.nfl.com/standings/",
        "fresh_snapshot_evidence": "research/nfl/evidence/standings-2026-11-17.retrieved.md",
        "week10_source": WEEK_10_URL,
        "week10_evidence": "nfl-results/evidence/week-10.schedule.md",
        "games_weeks_1_9": len([g for g in result["frozen_games"] if g["week"] <= 9]),
        "games_weeks_1_10": len(result["frozen_games"]),
        "scheduled_not_final": [
            {"week": g["week"], "away": g["away"], "home": g["home"], "kickoff": g["kickoff"],
             "tv": g["tv"], "date": g["date"]} for g in result["scheduled_w10"]],
        "checks": {
            "w1_9_vs_frozen": f"{n_fields} fields reconciled" if not result["mismatch_frozen_w1_9"] else "FAILED",
            "w1_10_vs_fresh": f"{n_fields} fields reconciled" if not result["mismatch_fresh_w1_10"] else "FAILED",
            "fresh_eq_frozen_plus_w10_deltas": "32 clubs x 5 fields hold" if not result["snapshot_drift"] else "FAILED",
        },
    }, indent=2) + "\n", encoding="utf-8")

    completion_added = [g for g in result["games"] if g["source_url"] == WEEK_10_COMPLETE_URL]
    recon18_path = OUT / "reconciliation-2026-11-18.json"
    recon18_path.write_text(json.dumps({
        "checked_on": "2026-11-18",
        "frozen_snapshot": "data/nfl-standings-2026.csv",
        "fresh_snapshot": "data/nfl-standings-2026-11-17.csv",
        "complete_snapshot": "data/nfl-standings-2026-11-18.csv",
        "complete_snapshot_source": "https://www.nfl.com/standings/",
        "complete_snapshot_evidence": "research/nfl/evidence/standings-2026-11-18.retrieved.md",
        "week10_completion_source": WEEK_10_COMPLETE_URL,
        "week10_completion_evidence": "nfl-results/evidence/week-10.complete.md",
        "week11_source": WEEK_11_URL,
        "week11_evidence": "nfl-results/evidence/week-11.schedule.md",
        "week12_source": WEEK_12_URL,
        "week12_evidence": "nfl-results/evidence/week-12.schedule.md",
        "games_weeks_1_9": len([g for g in result["frozen_games"] if g["week"] <= 9]),
        "games_weeks_1_10_frozen": len(result["frozen_games"]),
        "games_weeks_1_10_complete": len(result["games"]),
        "completion_added_finals": [
            {"week": g["week"], "date": g["date"], "weekday": g["weekday"], "away": g["away"],
             "home": g["home"], "away_score": g["away_score"], "home_score": g["home_score"],
             "source_url": g["source_url"], "retrieved": g["retrieved"],
             "evidence": g["evidence"]} for g in completion_added],
        "scheduled_not_final_at_publication": [
            {"week": g["week"], "away": g["away"], "home": g["home"], "kickoff": g["kickoff"],
             "tv": g["tv"], "date": g["date"]} for g in result["scheduled_w11"] + result["scheduled_w12"]],
        "checks": {
            "w1_9_vs_frozen": f"{n_fields} fields reconciled" if not result["mismatch_frozen_w1_9"] else "FAILED",
            "w1_10_frozen_vs_fresh_1117": f"{n_fields} fields reconciled" if not result["mismatch_fresh_w1_10"] else "FAILED",
            "fresh1117_eq_frozen_plus_w10_deltas": "32 clubs x 5 fields hold" if not result["snapshot_drift"] else "FAILED",
            "w1_10_complete_vs_fresh_1118": f"{n_fields} fields reconciled" if not result["mismatch_complete_w1_10"] else "FAILED",
            "fresh1118_eq_fresh1117_plus_completion_deltas": "32 clubs x 5 fields hold" if not result["completion_drift"] else "FAILED",
            "completion_reread_agrees_with_frozen_w10": "13 frozen finals identical + only the scheduled fixture added + byes identical",
        },
    }, indent=2) + "\n", encoding="utf-8")

    total_byes = sum(len(v) for v in result["byes"].values())
    print(f"OK: {len(result['games'])} finals in the completed weeks 1-10 feed "
          f"(frozen w1-10: {len(result['frozen_games'])}), "
          f"{total_byes} bye rows (weeks 1-12), "
          f"{len(result['scheduled_w10'])} frozen scheduled + "
          f"{len(result['scheduled_w11'])} Week 11 + {len(result['scheduled_w12'])} Week 12 scheduled; "
          f"reconciled with 32 official standings rows on W-L-T, PF and PA "
          f"against frozen, 2026-11-17 and 2026-11-18 snapshots; "
          f"snapshot_1118 = snapshot_1117 + parsed Week 10 completion deltas.")
    for path in (games_path, games10_path, games_complete_path, byes_path, byes10_path,
                 byes_complete_path, byes12_path, sched_path, sched11_path, sched12_path,
                 snapshot_path, snapshot_complete_path, recon_path, recon18_path):
        print(f"    {path.relative_to(ROOT)} (sha256 {hashlib.sha256(path.read_bytes()).hexdigest()[:16]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
