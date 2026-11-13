#!/usr/bin/env python3
"""Transcribe the saved official NFL Week 10 injury report into rows.

Every row produced here comes from a rendered line saved under evidence/. Nothing is inferred:
a blank practice/game status stays blank, and an unknown vocabulary word aborts the run.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
DATA = HERE / "data"
BUILD = HERE / "build"

SOURCE_URL = "https://www.nfl.com/injuries/league/2026/REG10"
CHECKED_ON = "2026-11-13"
WEEK = "10"
SEASON = "2026"

PRACTICE_VOCAB = {
    "Did Not Participate In Practice",
    "Limited Participation in Practice",
    "Full Participation in Practice",
}
GAME_VOCAB = {"", "Out", "Doubtful", "Questionable"}

CHUNKS = [f"injury-report-week10-2026.chunk{i}.md" for i in range(8)]
JOINED = EVIDENCE / "injury-report-week10-2026.joined.md"

TEAM_RE = re.compile(
    r"^\[!\[\]\((?P<logo>[^)]*)\)\]\((?P<url>https://www\.nfl\.com/teams/[^)]+)\)\s+"
    r"(?P<abbr>[A-Z]{2,3})\s+\[(?P<name>[^\]]+)\]\(https://www\.nfl\.com/teams/[^)]+\)$"
)
RECORD_RE = re.compile(r"^\((?P<rec>\d+-\d+(?:-\d+)?)\)$")
KICKOFF_RE = re.compile(r"^(?P<time>\d{1,2}:\d{2} [AP]M)EST$")
DAY_RE = re.compile(r"^(?P<day>[A-Z]+DAY), (?P<month>[A-Z]+) (?P<d>\d+)(?:ST|ND|RD|TH)$")
PLAYER_RE = re.compile(r"^\[(?P<name>[^\]]+)\]\((?P<url>https://www\.nfl\.com/players/[^)]+)\)$")


def joined_text() -> str:
    """Concatenate the chunk files exactly as the reader served them.

    Chunk boundaries fall inside a line, so the pieces are joined with no separator and only
    the trailing newline of each chunk file is removed.
    """
    parts = []
    for name in CHUNKS:
        text = (EVIDENCE / name).read_text(encoding="utf-8")
        parts.append(text[:-1] if text.endswith("\n") else text)
    return "".join(parts)


def write_joined(text: str) -> None:
    header = (
        "# Joined rendered text - official NFL injury report, Week 10 2026\n"
        f"# Source: {SOURCE_URL}\n"
        f"# Read on: {CHECKED_ON} via the Arena fetch_page reader (8 chunks, chunkIndex 0-7).\n"
        "# Assembly: the eight chunk files are concatenated with no separator; each fetch chunk\n"
        "#           boundary falls inside a line, so removing only each file's trailing newline\n"
        "#           restores the original rendered text byte for byte.\n"
        f"# sha256(joined): {hashlib.sha256(text.encode('utf-8')).hexdigest()}\n\n"
    )
    JOINED.write_text(header + text, encoding="utf-8")


def parse(text: str):
    lines = text.split("\n")
    games: list[dict] = []
    injuries: list[dict] = []

    day = month = dom = ""
    kickoff = tv = ""
    pending: list[dict] = []          # clubs captured for the upcoming matchup
    club_names: list[str] = []
    current_club: dict | None = None
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        if line.startswith("## "):
            m = DAY_RE.match(line[3:].strip())
            if m:
                day, month, dom = m.group("day"), m.group("month"), m.group("d")
                current_club = None
                club_names = []
                pending = []
            elif line[3:].strip() == "NEWS":
                day = month = dom = ""
                current_club = None
                club_names = []
                pending = []
            i += 1
            continue

        m = KICKOFF_RE.match(line)
        if m:
            kickoff = m.group("time")
            # next non-empty line is the TV listing, then two (team, record) pairs
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            tv = lines[j].strip()
            j += 1
            pending = []
            while j < n and len(pending) < 2:
                t = TEAM_RE.match(lines[j].strip())
                if t:
                    rec = ""
                    k = j + 1
                    while k < n and not lines[k].strip():
                        k += 1
                    if k < n:
                        rm = RECORD_RE.match(lines[k].strip())
                        if rm:
                            rec = rm.group("rec")
                    pending.append(
                        {
                            "abbr": t.group("abbr"),
                            "name": t.group("name"),
                            "record": rec,
                            "url": t.group("url"),
                        }
                    )
                    j = k + 1
                else:
                    j += 1
            if len(pending) != 2:
                raise SystemExit(f"expected 2 clubs after {kickoff}, captured {len(pending)}")
            game_id = f"W{WEEK}-{len(games) + 1:02d}"
            games.append(
                {
                    "game_id": game_id,
                    "day": day,
                    "month": month,
                    "day_of_month": dom,
                    "kickoff_et": kickoff,
                    "tv": tv,
                    "away_abbr": pending[0]["abbr"],
                    "away_name": pending[0]["name"],
                    "away_record": pending[0]["record"],
                    "home_abbr": pending[1]["abbr"],
                    "home_name": pending[1]["name"],
                    "home_record": pending[1]["record"],
                    "source_url": SOURCE_URL,
                }
            )
            club_names = [pending[0]["name"], pending[1]["name"]]
            current_club = None
            i = j
            continue

        if line in club_names:
            current_club = next(c for c in pending if c["name"] == line)
            i += 1
            continue

        if line.startswith("| [") and current_club is not None:
            cells = [c.strip() for c in line.split("|")]
            if len(cells) != 7:
                raise SystemExit(f"row does not have 5 columns: {line!r}")
            pm = PLAYER_RE.match(cells[1])
            if not pm:
                raise SystemExit(f"player cell not a player link: {cells[1]!r}")
            practice, game_status, injury = cells[4], cells[5], cells[3]
            if practice not in PRACTICE_VOCAB:
                raise SystemExit(f"practice status outside official vocabulary: {practice!r}")
            if game_status not in GAME_VOCAB:
                raise SystemExit(f"game status outside official vocabulary: {game_status!r}")
            opponent = next((c for c in pending if c["abbr"] != current_club["abbr"]), None)
            injuries.append(
                {
                    "injury_id": f"I-{current_club['abbr']}-{len(injuries) + 1:03d}",
                    "game_id": games[-1]["game_id"] if games else "",
                    "game_day": day,
                    "kickoff_et": kickoff,
                    "club_abbr": current_club["abbr"],
                    "club_name": current_club["name"],
                    "opponent_abbr": opponent["abbr"] if opponent else "",
                    "player": pm.group("name"),
                    "position": cells[2],
                    "injury": injury,
                    "practice_status": practice,
                    "game_status": game_status,
                    "player_url": pm.group("url"),
                    "source_url": SOURCE_URL,
                    "checked_on": CHECKED_ON,
                    "evidence_file": "nfl-availability-28ef/evidence/injury-report-week10-2026.joined.md",
                }
            )
            i += 1
            continue

        i += 1

    return games, injuries


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise SystemExit(f"refusing to write an empty table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    text = joined_text()
    write_joined(text)
    games, injuries = parse(text)
    DATA.mkdir(parents=True, exist_ok=True)
    write_csv(DATA / "games-week10-2026.csv", games)
    write_csv(DATA / "injuries-week10-2026.csv", injuries)

    clubs = sorted({g["away_abbr"] for g in games} | {g["home_abbr"] for g in games})
    by_club: dict[str, list[dict]] = {}
    for row in injuries:
        by_club.setdefault(row["club_abbr"], []).append(row)

    summary = {
        "source_url": SOURCE_URL,
        "checked_on": CHECKED_ON,
        "week": WEEK,
        "season": SEASON,
        "games": len(games),
        "clubs_listed": len(clubs),
        "clubs": clubs,
        "injury_rows": len(injuries),
        "rows_per_club": {k: len(v) for k, v in sorted(by_club.items())},
        "game_status_counts": {
            s: sum(1 for r in injuries if r["game_status"] == s)
            for s in sorted({r["game_status"] for r in injuries})
        },
        "practice_status_counts": {
            s: sum(1 for r in injuries if r["practice_status"] == s)
            for s in sorted({r["practice_status"] for r in injuries})
        },
        "joined_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }
    (DATA / "capture-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
