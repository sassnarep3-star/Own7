#!/usr/bin/env python3
"""Week 11 injury-hub first read (2026-11-18): parser, drift alarm and CSV writer.

Input : nfl-fresh-1118/evidence/injury-hub-w11-2026-11-18.md (the retained transcript of the
        three chunks of https://www.nfl.com/injuries/ read on 2026-11-18).
Checks: every count the transcript must satisfy is pinned below. A missing field, an unknown
        designation, a duplicate, a count change, or a disagreement with the official Week 11
        schedule capture or the 2026-11-18 standings capture raises an error (drift alarm).
Output: one deterministic game-level CSV (no player names), each row carrying the registered
        official source id and URL. Player rows are validated in memory only.

  python nfl-fresh-1118/injury_w11.py          # parse, validate, write the game-level CSV
  python nfl-fresh-1118/injury_w11.py --check  # parse, validate, compare with the committed CSV
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EVIDENCE = HERE / "evidence" / "injury-hub-w11-2026-11-18.md"
GAMES_CSV = HERE / "data" / "injury-w11-2026-11-18-games.csv"
# Player-level rows are raw row-level data. They are validated in memory and are NOT written to a
# CSV or published on the site (see flag FI09 in the desk).
SCHED_CSV = ROOT / "nfl-results" / "data" / "scheduled-2026-w11.csv"
STANDINGS_CSV = ROOT / "data" / "nfl-standings-2026-11-18.csv"

HUB_URL = "https://www.nfl.com/injuries/"
SOURCE_ID = "FRESH-NFL-INJHUB-W11-1118"
READ_UPPER_BOUND = "2026-11-18T06:24:07Z"
NO_INJ = "No Injuries Reported"
HEADER = ["Player", "Position", "Injuries", "Practice Status", "Game Status"]
PRACTICE = ("Did Not Participate In Practice", "Limited Participation in Practice",
            "Full Participation in Practice")
# Only designations observed in captures retained in this repository. Any other value fails the
# build: a new designation must be verified and added deliberately, never guessed.
GAME_STATUS = ("", "Out", "Questionable")

# Pinned expectations for this capture (drift alarm).
EXPECT_GAMES = 13
EXPECT_TEAMS = 26
EXPECT_TABLE_CLUBS = {"Colts": 11, "Texans": 15}
EXPECT_PLAYER_ROWS = 26
EXPECT_NIR_CLUBS = 24
EXPECT_BYES = 6

GAME_RE = re.compile(r"^### Game (\d+) — (.+)$")
TEAM_RE = re.compile(r"^- ([A-Z]{2,3}) (.+) \((\d+-\d+(?:-\d+)?)\)$")
CLUB_RE = re.compile(r"^#### (.+)$")
NIR_RE = re.compile(r"^(.+): No Injuries Reported$")
PROFILE_RE = re.compile(r"^- (.+?) — (https://www\.nfl\.com/players/\S+)")
DAY_RE = re.compile(r"^([A-Z]+), ([A-Z]+) (\d+)(?:ST|ND|RD|TH)$")
TIME_RE = re.compile(r"^(\d{1,2}:\d{2} [AP]M)EST$")


def _norm_time(text: str) -> str:
    return re.sub(r"\s+", "", text).upper()


def parse(text: str) -> dict:
    """Parse the transcript into games, team bullets, club tables and profile links."""
    errors: list[str] = []
    games: list[dict] = []
    profiles: dict[str, str] = {}
    in_profiles = False
    current = None
    club = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## P. "):
            in_profiles = True
            continue
        if in_profiles:
            m = PROFILE_RE.match(line)
            if m:
                if m.group(1) in profiles:
                    errors.append(f"duplicate profile link for {m.group(1)}")
                profiles[m.group(1)] = m.group(2)
            continue
        if line.startswith("## "):
            current, club = None, None
            continue
        m = GAME_RE.match(line)
        if m:
            parts = m.group(2).split(" — ")
            if len(parts) != 3:
                errors.append(f"game {m.group(1)}: header has {len(parts)} parts, expected 3")
                continue
            day_text, time_text, network = parts
            dm = DAY_RE.match(day_text)
            tm = TIME_RE.match(time_text)
            if not dm or not tm:
                errors.append(f"game {m.group(1)}: unparsed day or time: {line}")
                continue
            when = datetime.strptime(f"{dm.group(2).title()} {dm.group(3)} 2026", "%B %d %Y").date()
            current = {"game_no": int(m.group(1)), "date": when.isoformat(), "weekday": dm.group(1).title(),
                       "kickoff_et": tm.group(1), "network": network, "teams": [], "club_status": {}}
            games.append(current)
            club = None
            continue
        if current is None:
            continue
        m = TEAM_RE.match(line)
        if m:
            current["teams"].append({"abbr": m.group(1), "nickname": m.group(2), "record": m.group(3)})
            continue
        m = CLUB_RE.match(line)
        if m:
            club = m.group(1)
            if club in current["club_status"]:
                errors.append(f"game {current['game_no']}: club {club} listed twice")
            current["club_status"][club] = {"kind": "table", "rows": []}
            continue
        m = NIR_RE.match(line)
        if m:
            name = m.group(1)
            if name in current["club_status"]:
                errors.append(f"game {current['game_no']}: club {name} listed twice")
            current["club_status"][name] = {"kind": "nir", "rows": []}
            club = None
            continue
        if line.startswith("|") and club is not None:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if cells == HEADER or all(c.startswith("---") for c in cells):
                continue
            if len(cells) != 5:
                errors.append(f"{club}: row has {len(cells)} cells, expected 5: {line}")
                continue
            current["club_status"][club]["rows"].append(cells)
    return {"games": games, "profiles": profiles, "errors": errors}


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _nickname_match(nickname: str, standings: list[dict]) -> list[dict]:
    return [r for r in standings if r["Team"].split(" ")[-1] == nickname
            or r["Team"].endswith(" " + nickname)]


def build() -> dict:
    """Parse, validate and return the rows, CSV text and evidence hash. Raises SystemExit on error."""
    text = EVIDENCE.read_text(encoding="utf-8")
    parsed = parse(text)
    errors = list(parsed["errors"])
    games = parsed["games"]
    profiles = parsed["profiles"]

    if len(games) != EXPECT_GAMES:
        errors.append(f"expected {EXPECT_GAMES} games, parsed {len(games)}")
    if [g["game_no"] for g in games] != list(range(1, len(games) + 1)):
        errors.append("game numbers are not sequential")

    teams = [t for g in games for t in g["teams"]]
    if any(len(g["teams"]) != 2 for g in games):
        errors.append("a game does not have exactly two team lines")
    if len({t["abbr"] for t in teams}) != EXPECT_TEAMS or len(teams) != EXPECT_TEAMS:
        errors.append(f"expected {EXPECT_TEAMS} distinct team lines")

    player_rows: list[dict] = []
    nir_clubs = 0
    table_counts: dict[str, int] = {}
    game_rows: list[dict] = []
    seen_players: set[tuple[str, str]] = set()
    for g in games:
        names = [t["nickname"] for t in g["teams"]]
        for name in g["club_status"]:
            if name not in names:
                errors.append(f"game {g['game_no']}: club block '{name}' is not one of {names}")
        status_text = {}
        for t in g["teams"]:
            block = g["club_status"].get(t["nickname"])
            if block is None:
                errors.append(f"game {g['game_no']}: no status line for {t['nickname']}")
                continue
            if block["kind"] == "nir":
                nir_clubs += 1
                status_text[t["abbr"]] = NO_INJ
                continue
            table_counts[t["nickname"]] = len(block["rows"])
            status_text[t["abbr"]] = f"{len(block['rows'])} players listed"
            for cells in block["rows"]:
                player, position, injuries, practice, game_status = cells
                if not player or not position:
                    errors.append(f"{t['nickname']}: player or position blank")
                if practice not in PRACTICE:
                    errors.append(f"{player}: unknown practice status '{practice}'")
                if game_status not in GAME_STATUS:
                    errors.append(f"{player}: unknown game status '{game_status}'")
                key = (t["nickname"], player)
                if key in seen_players:
                    errors.append(f"duplicate player row {key}")
                seen_players.add(key)
                if player not in profiles:
                    errors.append(f"{player}: no profile link in transcript section P")
                player_rows.append({
                    "game_no": g["game_no"], "date": g["date"], "club_abbr": t["abbr"],
                    "club_nickname": t["nickname"], "player": player, "position": position,
                    "injuries": injuries, "practice_status": practice, "game_status": game_status,
                    "player_profile_url": profiles.get(player, ""), "source_id": SOURCE_ID,
                    "source_url": HUB_URL, "read_upper_bound_utc": READ_UPPER_BOUND,
                })
        away, home = g["teams"][0], g["teams"][1]
        game_rows.append({
            "game_no": g["game_no"], "date": g["date"], "weekday": g["weekday"],
            "kickoff_et": g["kickoff_et"], "network_as_printed": g["network"],
            "away_abbr": away["abbr"], "away_nickname": away["nickname"], "away_record": away["record"],
            "home_abbr": home["abbr"], "home_nickname": home["nickname"], "home_record": home["record"],
            "away_status": status_text.get(away["abbr"], ""), "home_status": status_text.get(home["abbr"], ""),
            "source_id": SOURCE_ID, "source_url": HUB_URL, "read_upper_bound_utc": READ_UPPER_BOUND,
        })

    if table_counts != EXPECT_TABLE_CLUBS:
        errors.append(f"table clubs {table_counts} != pinned {EXPECT_TABLE_CLUBS}")
    if len(player_rows) != EXPECT_PLAYER_ROWS:
        errors.append(f"player rows {len(player_rows)} != pinned {EXPECT_PLAYER_ROWS}")
    if nir_clubs != EXPECT_NIR_CLUBS:
        errors.append(f"'No Injuries Reported' clubs {nir_clubs} != pinned {EXPECT_NIR_CLUBS}")
    if len(profiles) != EXPECT_PLAYER_ROWS:
        errors.append(f"profile links {len(profiles)} != player rows {EXPECT_PLAYER_ROWS}")

    # Cross-check 1: official Week 11 schedule capture (pairings, orientation, date, kickoff).
    sched = _read_csv(SCHED_CSV)
    sched_pairs = {(r["away"], r["home"]): r for r in sched}
    if len(sched) != EXPECT_GAMES:
        errors.append(f"schedule capture has {len(sched)} rows, expected {EXPECT_GAMES}")
    for gr in game_rows:
        s = sched_pairs.get((gr["away_abbr"], gr["home_abbr"]))
        if s is None:
            errors.append(f"game {gr['game_no']}: {gr['away_abbr']}@{gr['home_abbr']} not in schedule capture")
            continue
        if s["date"] != gr["date"]:
            errors.append(f"game {gr['game_no']}: date {gr['date']} != schedule {s['date']}")
        if _norm_time(s["kickoff"]) != _norm_time(gr["kickoff_et"]):
            errors.append(f"game {gr['game_no']}: kickoff {gr['kickoff_et']} != schedule {s['kickoff']}")
    hub_clubs = {t["abbr"] for t in teams}
    sched_clubs = {r["away"] for r in sched} | {r["home"] for r in sched}
    if hub_clubs != sched_clubs:
        errors.append(f"club sets differ: hub-only {sorted(hub_clubs - sched_clubs)}, "
                      f"schedule-only {sorted(sched_clubs - hub_clubs)}")

    # Cross-check 2: 2026-11-18 standings capture (32 clubs; records as printed = W-L[-T]).
    standings = _read_csv(STANDINGS_CSV)
    if len(standings) != 32:
        errors.append(f"standings capture has {len(standings)} rows, expected 32")
    on_report: set[str] = set()
    for t in teams:
        matches = _nickname_match(t["nickname"], standings)
        if len(matches) != 1:
            errors.append(f"{t['nickname']}: {len(matches)} standings matches, expected 1")
            continue
        r = matches[0]
        expected = f"{r['W']}-{r['L']}" + (f"-{r['T']}" if r["T"] not in ("", "0") else "")
        if expected != t["record"]:
            errors.append(f"{t['nickname']}: record {t['record']} != standings {expected}")
        on_report.add(r["Team"])
    byes = sorted(r["Team"] for r in standings if r["Team"] not in on_report)
    if len(byes) != EXPECT_BYES:
        errors.append(f"clubs not on this report: {len(byes)} != pinned {EXPECT_BYES}")

    if errors:
        raise SystemExit("injury_w11 drift alarm:\n - " + "\n - ".join(errors))

    games_buf = io.StringIO()
    w = csv.DictWriter(games_buf, fieldnames=list(game_rows[0].keys()), lineterminator="\n")
    w.writeheader()
    w.writerows(game_rows)
    return {
        "games": game_rows, "players": player_rows, "byes": byes,
        "table_counts": table_counts, "nir_clubs": nir_clubs,
        "games_csv": games_buf.getvalue(),
        "evidence_sha256": hashlib.sha256(EVIDENCE.read_bytes()).hexdigest(),
        "sched_pairs": len(sched_pairs), "standings_matches": len(on_report),
    }


def main(argv: list[str]) -> int:
    result = build()
    if "--check" in argv:
        stale = []
        for path, content in ((GAMES_CSV, result["games_csv"]),):
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(str(path.relative_to(ROOT)))
        if stale:
            raise SystemExit("FAIL: stale injury_w11 CSVs: " + ", ".join(stale))
        print(f"OK: injury_w11 transcript validates ({len(result['games'])} games, "
              f"{len(result['players'])} player rows validated in memory, {len(result['byes'])} clubs not on report); CSV current.")
        return 0
    GAMES_CSV.parent.mkdir(parents=True, exist_ok=True)
    GAMES_CSV.write_text(result["games_csv"], encoding="utf-8")
    print(f"Wrote {GAMES_CSV.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
