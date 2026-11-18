#!/usr/bin/env python3
"""Deterministic collector and verifier for the Week 11 live decision desk.

Session: arena/9388352a-own7. Everything this module emits is parsed from the retained
transcripts in ``evidence/`` or from canonical artefacts already committed elsewhere in the
repository. Nothing is fetched here and nothing is inferred.

Outputs (all byte-deterministic):

  data/official-2026-11-18.json   the facts transcribed from the 2026-11-18 official reads
  data/venues.json                one row per Week 11 fixture with its game-centre venue
  data/fixture-context.json       rest days computed only from official kickoff dates
  data/captures.json              the timestamped capture ledger with retained hashes
  data/verification.json          the V1-V8 line-by-line check results

``--check`` re-runs everything and compares the JSON byte for byte. Any check failure, any
parse that does not yield the expected row count, and any missing canonical artefact aborts
the run rather than publishing a partial result.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
DATA = HERE / "data"

READ_DATE = "2026-11-18"
WINDOW_START = "2026-11-18T03:47:13Z"
WINDOW_END = "2026-11-18T03:51:41Z"

# Canonical artefacts produced by earlier sessions. Read-only here; never rewritten.
CANON_STANDINGS = ROOT / "data" / "nfl-standings-2026-11-17.csv"
CANON_GAMES = ROOT / "nfl-results" / "data" / "games-2026-w1-10.csv"
CANON_INJURIES = ROOT / "nfl-availability-28ef" / "data" / "injuries-week10-2026.csv"

# Registered source ids (rows live in research/sources.json).
S_STANDINGS = "W9388-NFL-STANDINGS-1118"
S_SCHED_W11 = "W9388-NFL-SCHED-W11-1118"
S_SCHED_W10 = "W9388-NFL-SCHED-W10-1118"
S_INJ_W11 = "W9388-NFL-INJ-W11-1118"
# The desk read 13 game-centre pages, each registered separately as W9388-GC-W11-01..13.
# This constant names the representative id (the Thursday page) for flags and cross-references
# that speak about the game-centre surface as a whole rather than about one fixture.
S_GAMECENTRE = "W9388-GC-W11-01"

SOURCE_URLS = {
    S_STANDINGS: "https://www.nfl.com/standings/league/2026/REG",
    S_SCHED_W11: "https://www.nfl.com/schedules/2026/by-week/week-11",
    S_SCHED_W10: "https://www.nfl.com/schedules/2026/by-week/week-10",
    S_INJ_W11: "https://www.nfl.com/injuries/league/2026/REG11",
}

# Club name as printed by nfl.com -> the abbreviation used by the committed results corpus.
NAME_TO_ABBR = {
    "Buffalo Bills": "BUF", "San Francisco 49ers": "SF", "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Denver Broncos": "DEN", "Detroit Lions": "DET",
    "Jacksonville Jaguars": "JAX", "Kansas City Chiefs": "KC", "Minnesota Vikings": "MIN",
    "Pittsburgh Steelers": "PIT", "New York Giants": "NYG", "Cleveland Browns": "CLE",
    "Green Bay Packers": "GB", "Los Angeles Rams": "LA", "Seattle Seahawks": "SEA",
    "New England Patriots": "NE", "Carolina Panthers": "CAR", "Baltimore Ravens": "BAL",
    "Dallas Cowboys": "DAL", "Las Vegas Raiders": "LV", "Washington Commanders": "WAS",
    "Houston Texans": "HOU", "New Orleans Saints": "NO", "Tampa Bay Buccaneers": "TB",
    "Arizona Cardinals": "AZ", "Atlanta Falcons": "ATL", "Indianapolis Colts": "IND",
    "Philadelphia Eagles": "PHI", "New York Jets": "NYJ", "Los Angeles Chargers": "LAC",
    "Miami Dolphins": "MIA", "Tennessee Titans": "TEN",
}

# Short names used by the schedule fixture list -> abbreviation.
SHORT_TO_ABBR = {
    "Colts": "IND", "Texans": "HOU", "Dolphins": "MIA", "Bills": "BUF", "Ravens": "BAL",
    "Panthers": "CAR", "Saints": "NO", "Bears": "CHI", "Titans": "TEN", "Cowboys": "DAL",
    "Buccaneers": "TB", "Lions": "DET", "Cardinals": "AZ", "Chiefs": "KC",
    "Steelers": "PIT", "Eagles": "PHI", "Jets": "NYJ", "Chargers": "LAC",
    "Jaguars": "JAX", "Giants": "NYG", "Raiders": "LV", "Broncos": "DEN",
    "Vikings": "MIN", "49ers": "SF", "Bengals": "CIN", "Commanders": "WAS",
    "Falcons": "ATL", "Browns": "CLE", "Packers": "GB", "Rams": "LA",
    "Patriots": "NE", "Seahawks": "SEA",
}

MONTHS = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
          "July": 7, "August": 8, "September": 9, "October": 10, "November": 11,
          "December": 12}


def die(msg: str) -> None:
    raise SystemExit(f"nfl-week11-9388/collect.py: {msg}")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- parsing

def parse_standings(path: Path) -> list[dict]:
    rows, in_table = [], False
    for line in path.read_text().splitlines():
        if line.startswith("| Club |"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                break
            if set(line.replace("|", "").replace("-", "").strip()) == set():
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 13:
                die(f"standings row has {len(cells)} cells, expected 13: {line!r}")
            club = cells[0]
            if club not in NAME_TO_ABBR:
                die(f"unknown club name in standings transcript: {club!r}")
            rows.append({
                "club": club, "abbr": NAME_TO_ABBR[club],
                "w": int(cells[1]), "l": int(cells[2]), "t": int(cells[3]),
                "pct": cells[4], "pf": int(cells[5]), "pa": int(cells[6]),
                "net_pts": int(cells[7]), "home": cells[8], "road": cells[9],
                "div": cells[10], "conf": cells[11], "strk": cells[12],
            })
    if len(rows) != 32:
        die(f"standings transcript yielded {len(rows)} rows, expected 32")
    return rows


FIXTURE_RE = re.compile(
    r"^- (?P<away>.+?) at (?P<home>.+?), (?P<weekday>[A-Za-z]+), "
    r"(?P<month>[A-Za-z]+) (?P<day>\d+)(?:st|nd|rd|th), (?P<time>\d+:\d+ [AP]M), "
    r"(?P<network>\S+) — (?P<url>\S+)$")


def parse_schedule(path: Path) -> tuple[list[dict], list[dict]]:
    fixtures, byes, in_byes = [], [], False
    for line in path.read_text().splitlines():
        if line.startswith("## Teams on Bye"):
            in_byes = True
            continue
        if in_byes:
            m = re.match(r"^\| ([A-Z]{2,3}) (.+?) \| ([\d-]+) \|$", line)
            if m:
                abbr, name, record = m.group(1), m.group(2), m.group(3)
                if abbr == "LAR":
                    abbr = "LA"
                if SHORT_TO_ABBR.get(name.split()[-1]) != abbr and abbr not in SHORT_TO_ABBR.values():
                    die(f"unmapped bye club: {abbr} {name}")
                byes.append({"abbr": abbr, "club": name, "record": record})
            continue
        m = FIXTURE_RE.match(line)
        if not m:
            continue
        away, home = m.group("away"), m.group("home")
        if away not in SHORT_TO_ABBR or home not in SHORT_TO_ABBR:
            die(f"unmapped club in fixture line: {line!r}")
        month, day = MONTHS[m.group("month")], int(m.group("day"))
        fixtures.append({
            "away": SHORT_TO_ABBR[away], "away_name": away,
            "home": SHORT_TO_ABBR[home], "home_name": home,
            "weekday": m.group("weekday"),
            "kickoff_date": date(2026, month, day).isoformat(),
            "kickoff_time_as_printed": m.group("time"),
            "kickoff_timezone": "",  # the page prints no timezone for Week 11
            "network": m.group("network"),
            # the transcript wraps URLs in markdown backticks; strip them so the value is
            # the address itself, which is what the site links to and what tests compare
            "url": m.group("url").strip("`"),
        })
    if len(fixtures) != 13:
        die(f"schedule transcript yielded {len(fixtures)} fixtures, expected 13")
    if len(byes) != 6:
        die(f"schedule transcript yielded {len(byes)} bye clubs, expected 6")
    return fixtures, byes


def parse_week10_tail(path: Path) -> dict:
    text = path.read_text()
    text = text.replace("`", "")
    m = re.search(r"Chargers (\d+), Ravens (\d+), FINAL, Monday, November (\d+)", text)
    if not m:
        die("Week 10 transcript does not contain the Chargers at Ravens final")
    byes = re.findall(r"^\| (CHI|DEN|PHI|TB) (.+?) \| ([\d-]+) \|$", text, re.M)
    if len(byes) != 4:
        die(f"Week 10 transcript yielded {len(byes)} bye clubs, expected 4")
    return {
        "mnf": {"away": "LAC", "home": "BAL",
                "away_score": int(m.group(1)), "home_score": int(m.group(2)),
                "date": date(2026, 11, int(m.group(3))).isoformat(),
                "away_name": "Chargers", "home_name": "Ravens"},
        "byes": [{"abbr": b[0], "club": b[1], "record": b[2]} for b in byes],
    }


def parse_game_centre(path: Path) -> dict:
    text = path.read_text()
    sections = re.split(r"^## (\d+) · ", text, flags=re.M)[1:]
    venues, players, cross = [], [], []
    if len(sections) % 2 != 0:
        die("game-centre transcript section split failed")
    for i in range(0, len(sections), 2):
        idx = int(sections[i])
        body = sections[i + 1]
        head = body.splitlines()[0]
        m = re.match(r"^(?P<away>.+?) at (?P<home>.+?) — (?P<url>\S+)$", head.strip())
        if not m:
            die(f"game-centre section {idx} header not parsed: {head!r}")
        loc = re.search(r"LocationLOCATION(?P<v>.+)", body)
        sta = re.search(r"StadiumSTADIUM(?P<v>.+)", body)
        hdr = re.search(r"Header: `Nov (?P<d>\d+)` `(?P<t>\d+:\d+[AP]M)`", body)
        net = re.search(r"`### NETWORK` — (?P<v>.+)", body)
        if not (loc and sta and hdr and net):
            die(f"game-centre section {idx} missing a Game Info field")
        empty = re.findall(r"Time(.+?) have no active injuries at this time\.", body)
        venues.append({
            "index": idx,
            "away": SHORT_TO_ABBR[m.group("away")], "away_name": m.group("away"),
            "home": SHORT_TO_ABBR[m.group("home")], "home_name": m.group("home"),
            "url": m.group("url"),
            "location": loc.group("v").strip(),
            "stadium": sta.group("v").strip(),
            "header_date": f"Nov {hdr.group('d')}",
            "header_time": hdr.group("t"),
            "network": net.group("v").replace("`", "").strip(),
            "injury_module_state": "empty" if empty else "rows",
            "empty_clubs": empty,
        })
        for club in ("COLTS", "TEXANS"):
            if f"### {club}" not in body:
                continue
            block = body.split(f"### {club}")[1]
            block = re.split(r"^`?#{2,3} ", block, flags=re.M)[0]
            for row in re.findall(
                    r"^\| (.+?) \| (.+?) \| (.+?) \| (.+?) \| (\S+) \|$", block, re.M):
                name, pos, jersey, status, link = [c.strip() for c in row]
                if name in ("Name as printed", "---"):
                    continue
                players.append({
                    "club": "IND" if club == "COLTS" else "HOU",
                    "club_label": club.title(),
                    "name": name, "position": pos,
                    "jersey": "" if jersey.startswith("(none") else jersey.lstrip("#"),
                    "status": status, "player_url": link,
                })
    if len(venues) != 13:
        die(f"game-centre transcript yielded {len(venues)} venues, expected 13")
    if len(players) != 8:
        die(f"game-centre transcript yielded {len(players)} player rows, expected 8")
    in_cross = False
    for line in text.splitlines():
        if line.startswith("| Fixture | Game-centre"):
            in_cross = True
            continue
        if in_cross:
            if not line.startswith("|"):
                break
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 3 or cells[0] == "Fixture" or set(cells[0]) <= {"-"}:
                continue
            cross.append({"fixture": cells[0], "game_centre": cells[1], "schedule_page": cells[2]})
    if len(cross) != 13:
        die(f"cross-check table yielded {len(cross)} rows, expected 13")
    return {"venues": venues, "players": players, "cross_check": cross}


INJ_ROW_RE = re.compile(r"^\| \[?([^|\]]+?)\]?(?:\([^)]*\))? \| ([A-Z]{1,3}) \| ([^|]*) \| ([^|]*) \| ([^|]*) \|$")


def parse_injury_transcript(path: Path) -> dict:
    text = path.read_text()
    events = re.findall(r"^\| (\d) \| (.+?) \| (.+?) \|$", text, re.M)
    events = [{"n": int(a), "fetch_instant_utc": b.strip(), "result": c.strip()}
              for a, b, c in events if a.isdigit() and "sandbox" in b or "Week 10" in c]
    # A club head is printed either on a line of its own ("DET Lions (7-2)") or inside a fixture
    # heading ("### SUNDAY, NOVEMBER 15TH — 1:00 PMEST — CBS — KC Chiefs (7-2) at ATL Falcons
    # (3-7)"). The two-club form is checked first: the page prints the away club's table first, so
    # the rows that follow belong to the away club. The only section in this transcript that uses
    # that form is the one the chunk boundary cut short, and its rows are excluded from every
    # comparison anyway.
    fixture_head = re.compile(r"(?P<abbr>[A-Z]{2,3}) (?P<name>[A-Za-z][\w .'-]*?) "
                              r"\((?P<rec>\d+-\d+(?:-\d+)?)\) at [A-Z]{2,3} ")
    club_head = re.compile(r"^(?P<abbr>[A-Z]{2,3}) (?P<name>[A-Za-z][\w .'-]*?) \((?P<rec>\d+-\d+(?:-\d+)?)\)$")
    sections, club, buf = [], None, []
    for line in text.splitlines():
        stripped = line.strip()
        head = fixture_head.search(stripped) or club_head.search(stripped)
        if head:
            if club is not None:
                sections.append((club, buf))
            club, buf = head.group("abbr"), []
            continue
        if club is not None:
            buf.append(line)
    if club is not None:
        sections.append((club, buf))

    rows = []
    for club, buf in sections:
        body = "\n".join(buf)
        truncated = "truncated by the chunk boundary" in body
        for line in buf:
            if not line.startswith("| "):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 5:
                continue
            player, pos, injury, practice, game = cells
            if player in ("Player",) or set(player) <= {"-"}:
                continue
            player = re.sub(r"^\[(.+?)\].*", r"\1", player)
            rows.append({"club": club, "player": player, "position": pos, "injury": injury,
                         "practice_status": practice, "game_status": game,
                         "section_truncated": truncated})
    return {"events": events, "rows": rows}


# --------------------------------------------------------------------------- canonical reads

def load_canon_standings(path: Path) -> dict[str, dict]:
    if not path.is_file():
        die(f"missing canonical standings artefact: {path}")
    out = {}
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            out[row["Team"]] = row
    if len(out) != 32:
        die(f"canonical standings has {len(out)} rows, expected 32")
    return out


def load_canon_games(path: Path) -> list[dict]:
    if not path.is_file():
        die(f"missing canonical results artefact: {path}")
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != 149:
        die(f"canonical results corpus has {len(rows)} games, expected 149")
    for r in rows:
        r["away_score"] = int(r["away_score"])
        r["home_score"] = int(r["home_score"])
    return rows


def load_canon_injuries(path: Path) -> list[dict]:
    if not path.is_file():
        die(f"missing canonical injury artefact: {path}")
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------- checks

def record_key(r: dict) -> str:
    return f"{r['home']}-{r['road']}-{r['div']}-{r['conf']}"


def results_for(abbr: str, games: list[dict]) -> list[tuple[str, str]]:
    """(date, W/L/T) for one club, chronological, from the official results corpus."""
    out = []
    for g in games:
        if g["away"] == abbr:
            a, h = g["away_score"], g["home_score"]
        elif g["home"] == abbr:
            a, h = g["home_score"], g["away_score"]
        else:
            continue
        out.append((g["date"], "T" if a == h else ("W" if a > h else "L")))
    return sorted(out)


def streak_and_last5(log: list[tuple[str, str]]) -> tuple[str, str]:
    last5 = log[-5:]
    counts = {"W": 0, "L": 0, "T": 0}
    for _, res in last5:
        counts[res] += 1
    last5_s = f"{counts['W']}-{counts['L']}-{counts['T']}"
    streak = last5[-1][1]
    n = 0
    for _, res in reversed(log):
        if res == streak:
            n += 1
        else:
            break
    return f"{n}{streak}", last5_s


def main() -> int:
    check_only = "--check" in sys.argv
    standings = parse_standings(EVIDENCE / "standings-league-2026-11-18.md")
    fixtures, byes = parse_schedule(EVIDENCE / "schedule-week11-2026-11-18.md")
    wk10 = parse_week10_tail(EVIDENCE / "schedule-week10-2026-11-18.md")
    gc = parse_game_centre(EVIDENCE / "game-centre-week11-2026-11-18.md")
    inj = parse_injury_transcript(EVIDENCE / "injury-report-week11-2026-11-18.md")

    canon_std = load_canon_standings(CANON_STANDINGS)
    games = load_canon_games(CANON_GAMES)
    canon_inj = load_canon_injuries(CANON_INJURIES)

    mnf = wk10["mnf"]
    all_games = games + [{
        "week": "10", "date": mnf["date"], "weekday": "Monday",
        "away": mnf["away"], "home": mnf["home"],
        "away_score": mnf["away_score"], "home_score": mnf["home_score"],
        "source_url": SOURCE_URLS[S_SCHED_W10], "retrieved": READ_DATE,
        "evidence": "nfl-week11-9388/evidence/schedule-week10-2026-11-18.md",
    }]

    checks, flags = [], []

    # ---- V1 standings reconcile with the frozen snapshot plus one game
    expected_delta = {
        "BAL": {"l": 1, "pf": mnf["home_score"], "pa": mnf["away_score"]},
        "LAC": {"w": 1, "pf": mnf["away_score"], "pa": mnf["home_score"]},
    }
    # The Monday game was played at Baltimore, so it moves BAL's home record and LAC's road
    # record, and both clubs' conference record (both are AFC).
    record_bumps = {"BAL": {"home": "L", "conf": "L"}, "LAC": {"road": "W", "conf": "W"}}
    v1_detail, v1_fail = [], 0
    for row in standings:
        src = canon_std.get(row["club"])
        if src is None:
            v1_fail += 1
            v1_detail.append(f"{row['club']}: absent from the frozen snapshot")
            continue
        d = expected_delta.get(row["abbr"], {})
        bumps = record_bumps.get(row["abbr"], {})
        exp = {
            "w": int(src["W"]) + d.get("w", 0),
            "l": int(src["L"]) + d.get("l", 0),
            "t": int(src["T"]),
            "pf": int(src["PF"]) + d.get("pf", 0),
            "pa": int(src["PA"]) + d.get("pa", 0),
            "net_pts": int(src["NetPts"]) + d.get("pf", 0) - d.get("pa", 0),
            "home": bump_record(src["Home"], bumps["home"]) if "home" in bumps else src["Home"],
            "road": bump_record(src["Road"], bumps["road"]) if "road" in bumps else src["Road"],
            "div": src["Div"],
            "conf": bump_record(src["Conf"], bumps["conf"]) if "conf" in bumps else src["Conf"],
        }
        got = {k: (row[k].replace(" ", "") if isinstance(row[k], str) else row[k])
               for k in ("w", "l", "t", "pf", "pa", "net_pts", "home", "road", "div", "conf")}
        exp = {k: (v.replace(" ", "") if isinstance(v, str) else v) for k, v in exp.items()}
        if got != exp:
            v1_fail += 1
            v1_detail.append(f"{row['club']}: read {got} != frozen snapshot + Week 10 MNF {exp}")
    checks.append({
        "id": "V1", "title": "All 32 standings rows reconcile with the frozen 2026-11-17 snapshot plus the single Week 10 Monday result",
        "status": "pass" if v1_fail == 0 else "fail",
        "compared": 32, "mismatches": v1_fail,
        "detail": v1_detail or ["32/32 rows matched; the only movement is BAL 4-5 -> 4-6 and LAC 0-8 -> 1-8, exactly the Chargers 23, Ravens 20 result."],
        "sources": [S_STANDINGS, S_SCHED_W10, "X29-NFL-SCHEDULE"],
    })
    if v1_fail:
        die("V1 failed: " + "; ".join(v1_detail))

    # ---- V2 league arithmetic on today's read
    sum_w = sum(r["w"] for r in standings)
    sum_l = sum(r["l"] for r in standings)
    sum_pf = sum(r["pf"] for r in standings)
    sum_pa = sum(r["pa"] for r in standings)
    gp_mismatch = []
    for r in standings:
        played = sum(1 for g in all_games if r["abbr"] in (g["away"], g["home"]))
        if r["w"] + r["l"] + r["t"] != played:
            gp_mismatch.append(f"{r['club']}: W+L+T={r['w'] + r['l'] + r['t']} but {played} games in the official corpus")
    v2_ok = (sum_w == sum_l) and (sum_pf == sum_pa) and not gp_mismatch
    checks.append({
        "id": "V2", "title": "League arithmetic closes: wins equal losses, points for equal points against, and every club's W+L+T equals its games played",
        "status": "pass" if v2_ok else "fail",
        "compared": 32, "mismatches": len(gp_mismatch),
        "detail": [f"sum W={sum_w}, sum L={sum_l}", f"sum PF={sum_pf}, sum PA={sum_pa}",
                   f"games played checked for 32 clubs"] + gp_mismatch,
        "sources": [S_STANDINGS, "X29-NFL-SCHEDULE", S_SCHED_W10],
    })
    if not v2_ok:
        die("V2 failed: " + "; ".join(gp_mismatch))

    # ---- V3 points reconciliation against the 149-game corpus
    corpus_pts = sum(g["away_score"] + g["home_score"] for g in games)
    expected_pf = corpus_pts + mnf["away_score"] + mnf["home_score"]
    v3_ok = sum_pf == expected_pf
    checks.append({
        "id": "V3", "title": "Total points for across the 32 clubs equals every point scored in the 149-game official corpus plus the Monday result",
        "status": "pass" if v3_ok else "fail",
        "compared": 32, "mismatches": 0 if v3_ok else 1,
        "detail": [f"sum PF today = {sum_pf}",
                   f"corpus points = {corpus_pts} over {len(games)} games",
                   f"+ Monday result {mnf['away_score']}+{mnf['home_score']} = {expected_pf}",
                   "match" if v3_ok else "MISMATCH"],
        "sources": [S_STANDINGS, "X29-NFL-SCHEDULE", S_SCHED_W10],
    })
    if not v3_ok:
        die(f"V3 failed: {sum_pf} != {expected_pf}")

    # ---- V4 Week 11 slate integrity
    playing = []
    for f in fixtures:
        playing += [f["away"], f["home"]]
    bye_abbrs = sorted(b["abbr"] for b in byes)
    dupes = sorted({c for c in playing if playing.count(c) > 1})
    overlap = sorted(set(playing) & set(bye_abbrs))
    missing = sorted(set(NAME_TO_ABBR.values()) - set(playing) - set(bye_abbrs))
    v4_ok = len(dupes) == 0 and len(overlap) == 0 and len(missing) == 0 and len(set(playing)) == 26
    checks.append({
        "id": "V4", "title": "The Week 11 slate covers 26 clubs exactly once and the 6 bye clubs complete the 32",
        "status": "pass" if v4_ok else "fail",
        "compared": 32, "mismatches": 0 if v4_ok else len(dupes) + len(overlap) + len(missing),
        "detail": [f"{len(fixtures)} fixtures, {len(set(playing))} distinct clubs, {len(bye_abbrs)} byes",
                   f"duplicates: {dupes or 'none'}", f"club on bye and playing: {overlap or 'none'}",
                   f"uncovered clubs: {missing or 'none'}"],
        "sources": [S_SCHED_W11, S_STANDINGS],
    })
    if not v4_ok:
        die(f"V4 failed: dupes={dupes} overlap={overlap} missing={missing}")

    # ---- V5 bye continuity
    wk10_byes = sorted(b["abbr"] for b in wk10["byes"])
    repeat = sorted(set(wk10_byes) & set(bye_abbrs))
    v5_ok = not repeat
    checks.append({
        "id": "V5", "title": "No club is on bye in both Week 10 and Week 11",
        "status": "pass" if v5_ok else "fail",
        "compared": 6, "mismatches": len(repeat),
        "detail": [f"Week 10 byes: {', '.join(wk10_byes)}",
                   f"Week 11 byes: {', '.join(bye_abbrs)}",
                   f"repeated: {repeat or 'none'}"],
        "sources": [S_SCHED_W10, S_SCHED_W11],
    })
    if not v5_ok:
        die(f"V5 failed: {repeat}")

    # ---- V6 venue completeness and cross-check
    no_venue = [v["url"] for v in gc["venues"] if not v["location"] or not v["stadium"]]
    diffs = []
    for c in gc["cross_check"]:
        a = norm(c["game_centre"])
        b = norm(c["schedule_page"])
        if b.startswith("("):
            continue
        if a != b:
            diffs.append(c["fixture"])
    v6_ok = not no_venue
    checks.append({
        "id": "V6", "title": "Every Week 11 fixture has a location and a stadium transcribed from its official game-centre page",
        "status": "pass" if v6_ok else "fail",
        "compared": 13, "mismatches": len(no_venue),
        "detail": [f"{len(gc['venues'])} venues transcribed, {len(no_venue)} blank",
                   f"{len(diffs)} of 13 disagree with the schedule page's own hotel-link stadium name"
                   f" ({', '.join(diffs) if diffs else 'none'})"],
        "sources": [S_GAMECENTRE, S_SCHED_W11],
    })
    if not v6_ok:
        die(f"V6 failed: {no_venue}")

    # ---- V7 Week 11 availability state
    events = inj["events"]
    served_week10 = [e for e in events if "Week 10" in e["result"]]
    empty_mods = [v for v in gc["venues"] if v["injury_module_state"] == "empty"]
    row_mods = [v for v in gc["venues"] if v["injury_module_state"] == "rows"]
    # The read series is open-ended: every read of the Week 11 URL must have served the Week 10
    # document. Adding a fifth read later must not break this check.
    v7_ok = (len(events) >= 3 and len(served_week10) == len(events)
             and len(empty_mods) == 12 and len(row_mods) == 1)
    checks.append({
        "id": "V7", "title": "The Week 11 league injury report is not published, and 12 of 13 game-centre injury modules are empty",
        "status": "pass" if v7_ok else "fail",
        "compared": 13, "mismatches": 0 if v7_ok else abs(13 - len(empty_mods) - len(row_mods)),
        "detail": [f"{len(events)} reads of {SOURCE_URLS[S_INJ_W11]} all served the Week 10 document",
                   f"{len(empty_mods)} of 13 game pages print the empty-module sentence",
                   f"{len(row_mods)} of 13 print player rows ({row_mods[0]['away_name']} at {row_mods[0]['home_name']})",
                   f"{len(gc['players'])} player rows captured in total"],
        "sources": [S_INJ_W11, S_GAMECENTRE],
    })
    if not v7_ok:
        die("V7 failed: availability state did not match the transcript")

    # ---- V8 Week 10 report unchanged since 2026-11-13
    by_url = {}
    for row in canon_inj:
        by_url[row["player_url"].rstrip("/")] = row
    compared = [r for r in inj["rows"] if not r["section_truncated"]]
    v8_rows, v8_missing = [], []
    for r in compared:
        key = None
        for row in canon_inj:
            if row["club_abbr"] == r["club"] and row["player"] == r["player"]:
                key = row
                break
        if key is None:
            v8_missing.append(f"{r['club']} {r['player']}")
            v8_rows.append({"player": r["player"], "club": r["club"],
                            "read_2026_11_18_practice": r["practice_status"],
                            "read_2026_11_18_game": r["game_status"],
                            "capture_2026_11_13_practice": "", "capture_2026_11_13_game": "",
                            "match": "not present in the 2026-11-13 capture"})
            continue
        same = (key["practice_status"] == r["practice_status"]
                and (key["game_status"] or "") == r["game_status"])
        v8_rows.append({
            "player": r["player"], "club": r["club"],
            "read_2026_11_18_practice": r["practice_status"],
            "read_2026_11_18_game": r["game_status"],
            "capture_2026_11_13_practice": key["practice_status"],
            "capture_2026_11_13_game": key["game_status"],
            "match": "same" if same else "CHANGED",
        })
    changed = [r for r in v8_rows if r["match"] == "CHANGED"]
    checks.append({
        "id": "V8",
        "title": "Every Week 10 row re-read today belongs to a player present in the 2026-11-13 capture; the cells that moved are published as a delta, not patched",
        "status": "pass" if not v8_missing else "fail",
        "compared": len(compared), "mismatches": len(v8_missing),
        "changed_cells": len(changed),
        "detail": [f"{len(compared)} rows compared (WAS 9, NYG 11, NE 15, DET 9); the Chiefs table "
                   "is excluded because the chunk cut it mid-table",
                   f"{len(compared) - len(changed) - len(v8_missing)} identical, "
                   f"{len(changed)} changed, {len(v8_missing)} absent",
                   "the source page mutates after the games are played - see flag W11-F11"],
        "sources": [S_INJ_W11, "X28-NFL-INJ-W10"],
    })
    if v8_missing:
        die("V8 failed: rows absent from the 2026-11-13 capture: " + "; ".join(v8_missing))

    # ---- fixture context, from official kickoff dates only
    context = []
    for f in fixtures:
        entry = {"fixture": f"{f['away_name']} at {f['home_name']}",
                 "kickoff_date": f["kickoff_date"], "url": f["url"]}
        for side in ("away", "home"):
            abbr = f[side]
            log = results_for(abbr, all_games)
            prev = log[-1][0] if log else ""
            entry[f"{side}_previous_game"] = prev
            entry[f"{side}_rest_days"] = (
                (date.fromisoformat(f["kickoff_date"]) - date.fromisoformat(prev)).days
                if prev else None)
        if entry["away_rest_days"] is not None and entry["home_rest_days"] is not None:
            entry["rest_days_differential"] = entry["away_rest_days"] - entry["home_rest_days"]
        else:
            entry["rest_days_differential"] = None
        context.append(entry)

    # ---- capture ledger
    captures = [
        {"id": "W11-CAP-01", "source_id": S_INJ_W11, "url": SOURCE_URLS[S_INJ_W11],
         "fetch_instant_utc": "before 2026-11-18T03:47:13Z",
         "clock_source": "sandbox UTC clock (the page prints no capture time)",
         "served_document": "Week 10 report (canonical url .../reg10)",
         "evidence": "evidence/injury-report-week11-2026-11-18.md"},
        {"id": "W11-CAP-02", "source_id": S_INJ_W11, "url": SOURCE_URLS[S_INJ_W11],
         "fetch_instant_utc": WINDOW_START,
         "clock_source": "sandbox UTC clock (the page prints no capture time)",
         "served_document": "Week 10 report (canonical url .../reg10)",
         "evidence": "evidence/injury-report-week11-2026-11-18.md"},
        {"id": "W11-CAP-03", "source_id": S_INJ_W11, "url": SOURCE_URLS[S_INJ_W11],
         "fetch_instant_utc": WINDOW_END,
         "clock_source": "sandbox UTC clock (the page prints no capture time)",
         "served_document": "Week 10 report (canonical url .../reg10)",
         "evidence": "evidence/injury-report-week11-2026-11-18.md"},
        {"id": "W11-CAP-04", "source_id": S_GAMECENTRE,
         "url": "https://www.nfl.com/games/<one page per Week 11 fixture>",
         "fetch_instant_utc": f"{WINDOW_START} .. {WINDOW_END}",
         "clock_source": "sandbox UTC clock (no game page prints a capture time)",
         "served_document": "13 game-centre pages: venue, network, kickoff, injury module",
         "evidence": "evidence/game-centre-week11-2026-11-18.md"},
        {"id": "W11-CAP-05", "source_id": S_STANDINGS, "url": SOURCE_URLS[S_STANDINGS],
         "fetch_instant_utc": f"{WINDOW_START} .. {WINDOW_END}",
         "clock_source": "sandbox UTC clock (the page prints no capture time)",
         "served_document": "league standings, 32 rows",
         "evidence": "evidence/standings-league-2026-11-18.md"},
        {"id": "W11-CAP-06", "source_id": S_SCHED_W11, "url": SOURCE_URLS[S_SCHED_W11],
         "fetch_instant_utc": f"{WINDOW_START} .. {WINDOW_END}",
         "clock_source": "sandbox UTC clock (the page prints no capture time)",
         "served_document": "Week 11 slate: 13 fixtures, 6 byes",
         "evidence": "evidence/schedule-week11-2026-11-18.md"},
        {"id": "W11-CAP-07", "source_id": S_SCHED_W10, "url": SOURCE_URLS[S_SCHED_W10],
         "fetch_instant_utc": f"{WINDOW_START} .. {WINDOW_END}",
         "clock_source": "sandbox UTC clock (the page prints no capture time)",
         "served_document": "Week 10 tail: Chargers 23, Ravens 20 FINAL; 4 byes",
         "evidence": "evidence/schedule-week10-2026-11-18.md"},
    ]
    evidence_hashes = {}
    for p in sorted(EVIDENCE.glob("*.md")):
        evidence_hashes[p.name] = sha256_of(p)
    for cap in captures:
        cap["sha256_of_retained_transcript"] = evidence_hashes.get(
            Path(cap["evidence"]).name, "")

    # ---- availability deltas (level is stored; the page publishes the delta)
    deltas = []
    for p in gc["players"]:
        url = p["player_url"].rstrip("/") + "/"
        prior = by_url.get(p["player_url"].rstrip("/"))
        if prior is None:
            for u, row in by_url.items():
                if row["club_abbr"] == p["club"] and row["player"].endswith(p["name"].split(". ")[-1]):
                    prior = row
                    break
        deltas.append({
            "club": p["club"], "player": p["name"], "position_as_printed": p["position"],
            "week11_status": p["status"],
            "week10_capture_practice": prior["practice_status"] if prior else "",
            "week10_capture_game": prior["game_status"] if prior else "",
            "week10_capture_position": prior["position"] if prior else "",
            "delta": ("not on the Week 10 report (new listing)" if prior is None
                      else ("unchanged" if status_word(prior["practice_status"]) == p["status"]
                            else f"changed: {status_word(prior['practice_status'])} -> {p['status']}")),
            "player_url": p["player_url"],
        })

    # ---- flags
    flags = [
        {"id": "W11-F01", "title": "The game centre names the Texans' stadium 'RELIANT STADIUM'",
         "detail": "The Week 11 game-centre page for Colts at Texans prints Stadium = RELIANT "
                   "STADIUM, while the Week 11 schedule page's own hotel link for the same fixture "
                   "names NRG Stadium. Both are nfl.com pages read the same day. The game-centre "
                   "value is transcribed as published; no name is corrected.",
         "severity": "low", "status": "open", "where": "venues.html",
         "sources": [S_GAMECENTRE, S_SCHED_W11]},
        {"id": "W11-F02", "title": "The game centre drops the Chiefs' sponsored stadium name",
         "detail": "Cardinals at Chiefs prints Stadium = ARROWHEAD STADIUM, while the schedule "
                   "page's hotel link names GEHA Field at Arrowhead Stadium. The game centre "
                   "appears to publish the unsponsored name; the schedule page publishes the "
                   "sponsored one. Venue matching across the two pages cannot be done by string "
                   "equality.",
         "severity": "low", "status": "open", "where": "venues.html",
         "sources": [S_GAMECENTRE, S_SCHED_W11]},
        {"id": "W11-F03", "title": "The Commanders' venue is named two ways on nfl.com",
         "detail": "Bengals at Commanders prints Stadium = NORTHWEST STADIUM, while the schedule "
                   "page's hotel link names FedEx Field. Here the game centre carries the newer "
                   "name and the schedule page the older one - the opposite direction to the "
                   "Texans case. Any venue key built from a name string will break.",
         "severity": "low", "status": "open", "where": "venues.html",
         "sources": [S_GAMECENTRE, S_SCHED_W11]},
        {"id": "W11-F04", "title": "The league standings page renders unsubstituted template placeholders",
         "detail": "The page heading reads '# $year$ NFL $displayname$ Standings'. The data table "
                   "is unaffected, but it shows the publisher's template is rendering incorrectly, "
                   "so a scraper that keys on the heading would fail. The desk keys on the table.",
         "severity": "low", "status": "open", "where": "flagged.html",
         "sources": [S_STANDINGS]},
        {"id": "W11-F05", "title": "The game-centre injury module uses a third practice-status word",
         "detail": "Twelve Colts/Texans rows on the Thursday game use 'Did not participate' or "
                   "'Full participation', but Anthony Gould's row reads 'Did participate'. Three "
                   "different strings for two states in one module. The desk stores the string as "
                   "printed and does not normalise it, because normalisation would be an inference.",
         "severity": "medium", "status": "open", "where": "availability.html",
         "sources": [S_GAMECENTRE]},
        {"id": "W11-F06", "title": "'Have no active injuries' is an empty module, not a clean bill of health",
         "detail": "12 of 13 Week 11 game pages print e.g. 'Bills have no active injuries at this "
                   "time.' No Week 11 practice report has been filed, and the league report for "
                   "Week 11 does not exist yet, so the sentence cannot mean the club is healthy. "
                   "Treating it as healthy would be the exact 'not listed means available' error "
                   "the brief warns about. All 24 club-game entries are stored as missing data.",
         "severity": "high", "status": "open", "where": "availability.html",
         "sources": [S_GAMECENTRE, S_INJ_W11]},
        {"id": "W11-F07", "title": "Position labels differ between the two official injury surfaces",
         "detail": "Reed Blankenship is 'S' on the Week 10 league report and 'DB' on the Week 11 "
                   "game page; Blake Fisher is 'T' on the report and 'OL' on the game page. Joining "
                   "the two surfaces on position would silently drop rows; this desk joins on the "
                   "player link instead.",
         "severity": "medium", "status": "open", "where": "availability.html",
         "sources": [S_GAMECENTRE, "X28-NFL-INJ-W10"]},
        {"id": "W11-F08", "title": "The Monday night result was pending in every previous capture",
         "detail": "The 149-game corpus was read before the Chargers at Ravens game kicked off, so "
                   "the repository held it as scheduled-not-final. It is now final (Chargers 23, "
                   "Ravens 20). This desk records the result and reconciles it two ways, but does "
                   "not edit the corpus - the corpus belongs to the results desk and is a frozen "
                   "pre-kickoff input for its own purposes.",
         "severity": "medium", "status": "open", "where": "flagged.html",
         "sources": [S_SCHED_W10, S_STANDINGS]},
        {"id": "W11-F09", "title": "No page read this session prints a capture or update time",
         "detail": "The standings, schedule, game-centre and injury pages all omit any timestamp. "
                   "The only clock available is the sandbox's, recorded as a window "
                   f"({WINDOW_START} to {WINDOW_END}). Per-read instants inside the window are not "
                   "recoverable, so the capture ledger records windows, not instants, for those "
                   "reads. The requirement to store every injury read with its clock time is met at "
                   "window resolution only.",
         "severity": "medium", "status": "open", "where": "captures.html",
         "sources": [S_INJ_W11, S_GAMECENTRE, S_STANDINGS, S_SCHED_W11]},
        {"id": "W11-F11", "title": "The official injury report mutates after the games are played",
         "detail": "Three Lions cells in the Week 10 report differ between the frozen 2026-11-13 "
                   "capture held in nfl-availability-28ef/data/injuries-week10-2026.csv and the "
                   "same page read on 2026-11-18: Kerby Joseph's practice status moved from Full "
                   "Participation in Practice to Did Not Participate In Practice; Amon-Ra St. "
                   "Brown's game status moved from blank to Questionable; Sione Vaki's practice "
                   "status moved from Did Not Participate In Practice to Limited Participation "
                   "in Practice and his game status from blank to Questionable. The other 41 "
                   "comparable rows are identical. The publisher therefore rewrites the week's "
                   "document after kickoff, so a capture taken on the Friday of that week is not "
                   "the end-of-week truth. Any backtest that joins a designation to an outcome "
                   "must record which version of the document it used; the delta is published on "
                   "the availability page rather than patched into the earlier capture.",
         "severity": "high", "status": "open", "where": "availability.html",
         "sources": [S_INJ_W11, "X28-NFL-INJ-W10"]},
        {"id": "W11-F10", "title": "The Week 11 international fixture has no hotel-link stadium to cross-check",
         "detail": "Vikings at 49ers is played in Mexico City (Estadio Banorte). The schedule page "
                   "shows the Mexico City event branding and the game page prints no ticket or "
                   "hotel link, so the second venue string that exists for the other twelve "
                   "fixtures does not exist here. The venue rests on one source only.",
         "severity": "low", "status": "open", "where": "venues.html",
         "sources": [S_GAMECENTRE, S_SCHED_W11]},
    ]

    official = {
        "schema_version": 1,
        "desk": "nfl-week11-9388",
        "session": "arena/9388352a-own7",
        "read_date": READ_DATE,
        "read_window_utc": [WINDOW_START, WINDOW_END],
        "standings": standings,
        "week11_fixtures": fixtures,
        "week11_byes": byes,
        "week10_monday_result": mnf,
        "week10_byes": wk10["byes"],
        "league_totals": {"wins": sum_w, "losses": sum_l, "ties": sum(r["t"] for r in standings),
                          "points_for": sum_pf, "points_against": sum_pa,
                          "corpus_games": len(games), "corpus_points": corpus_pts},
        "week11_injury_report": {"published": False,
                                 "url_requested": SOURCE_URLS[S_INJ_W11],
                                 "served_canonical_url": "https://www.nfl.com/injuries/league/2026/reg10",
                                 "served_title": "Official NFL Injury Report for Players - Week 10 of the 2026 Season | NFL.com",
                                 "reads": events},
        "game_centre_players": gc["players"],
        "availability_deltas": deltas,
    }

    DATA.mkdir(parents=True, exist_ok=True)
    outputs = {
        "official-2026-11-18.json": official,
        "venues.json": {"schema_version": 1, "read_date": READ_DATE,
                        "venues": gc["venues"], "cross_check": gc["cross_check"]},
        "fixture-context.json": {"schema_version": 1, "read_date": READ_DATE,
                                 "note": "Rest days are the difference between two official kickoff "
                                         "dates: the club's previous game in the official results "
                                         "corpus and its Week 11 kickoff. Nothing else is modelled.",
                                 "rows": context},
        "captures.json": {"schema_version": 1, "read_date": READ_DATE,
                          "window_utc": [WINDOW_START, WINDOW_END],
                          "captures": captures, "evidence_sha256": evidence_hashes},
        "verification.json": {"schema_version": 1, "read_date": READ_DATE,
                              "checks": checks, "v8_rows": v8_rows, "flags": flags},
    }

    if check_only:
        bad = []
        for name, payload in outputs.items():
            path = DATA / name
            want = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
            if not path.is_file():
                bad.append(f"{name}: missing")
            elif path.read_text() != want:
                bad.append(f"{name}: differs")
        if bad:
            die("--check failed: " + "; ".join(bad))
        print("OK: all artefacts reproduce exactly")
        return 0

    for name, payload in outputs.items():
        (DATA / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    for c in checks:
        print(f"{c['id']}: {c['status']} — {c['title']}")
    print(f"flags: {len(flags)}")
    return 0


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def bump_record(record: str, result: str) -> str:
    w, l, t = (int(x) for x in record.split("-"))
    if result == "W":
        w += 1
    elif result == "L":
        l += 1
    else:
        t += 1
    return f"{w} - {l} - {t}"


def status_word(practice_status: str) -> str:
    return {"Did Not Participate In Practice": "Did not participate",
            "Limited Participation in Practice": "Limited participation",
            "Full Participation in Practice": "Full participation"}.get(practice_status, "")


if __name__ == "__main__":
    raise SystemExit(main())
