#!/usr/bin/env python3
"""Parse the saved official per-game player logs and prove them before publishing.

This closes the gap every earlier session recorded as "blank: no per-game player logs retrieved".
The logs exist on NFL.com's own player pages, they were read on 2026-11-14, and they are saved
verbatim under ``nfl-market-desk/evidence/player-*.md``.

Two independent checks run before anything is written. Either one failing aborts the build:

  1. **Season-total reconciliation.** Every additive column in the "Recent Games" rows must sum to
     the value printed in the same column of the player's ``2026`` career row. A mis-read digit
     would break this on at least one column.
  2. **Results-feed agreement.** For every game a player has a row for, the opponent printed on the
     player page must be the opponent in the official results feed, the venue must be home or away
     as printed (``@`` prefix), and the printed score must equal the feed's score. The feed is
     ``nfl-results/data/games-2026-w1-9.csv``, itself reconciled against the official standings on
     W-L-T, PF and PA.

What is deliberately *not* done: no value is interpolated for a column the page left blank, and a
player page whose header could not be matched to the page's own column list is recorded as
unparseable instead of being guessed at.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
RESULTS = REPO / "nfl-results" / "data" / "games-2026-w1-9.csv"

NICKNAME_TO_CODE = {
    "Cardinals": "AZ", "Falcons": "ATL", "Ravens": "BAL", "Bills": "BUF", "Panthers": "CAR",
    "Bears": "CHI", "Bengals": "CIN", "Browns": "CLE", "Cowboys": "DAL", "Broncos": "DEN",
    "Lions": "DET", "Packers": "GB", "Texans": "HOU", "Colts": "IND", "Jaguars": "JAX",
    "Chiefs": "KC", "Raiders": "LV", "Chargers": "LAC", "Rams": "LA", "Dolphins": "MIA",
    "Vikings": "MIN", "Patriots": "NE", "Saints": "NO", "Giants": "NYG", "Jets": "NYJ",
    "Eagles": "PHI", "Steelers": "PIT", "49ers": "SF", "Seahawks": "SEA", "Buccaneers": "TB",
    "Titans": "TEN", "Commanders": "WAS",
}
CLUB_NAME_TO_CODE = {
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

# Printed header -> our column name. A page that prints no header (Allen, Cook, Chase, Higgins) is
# mapped by the column order its career table uses, which the evidence file records verbatim.
QB_RECENT = ["CMP", "ATT", "PYDS", "YPA", "PTD", "INT", "SACKS", "SACK_YDS", "RATE",
             "CAR", "RYDS", "YPC", "RTD", "FUM", "LOST"]
RB_RECENT = ["CAR", "RYDS", "YPC", "LNG", "RTD", "REC", "RECYDS", "YPR", "LNG_REC", "RECTD",
             "FUM", "LOST"]
WR_RECENT = ["REC", "RECYDS", "YPR", "LNG", "RECTD", "CAR", "RYDS", "YPC", "LNG_RUSH", "RTD",
             "FUM", "LOST"]

# The 2026 career row is printed with its own column order, which differs from the Recent Games
# order for rushers and receivers: the career table prints ONE long column per phase and omits the
# second long column. Names alone cannot disambiguate repeated ``YDS``/``AVG``/``TD`` headers, so
# the mapping is by printed position and is stated explicitly instead of guessed.
QB_CAREER = ["CMP", "ATT", "PYDS", "YPA", "PTD", "INT", "SACKS", "SACK_YDS", "RATE",
             "CAR", "RYDS", "YPC", "RTD", "FUM", "LOST"]
RB_CAREER = ["ATT", "RYDS", "YPA_R", "RTD", "REC", "RECYDS", "YPR_C", "LNG_REC", "RECTD",
             "FUM", "LOST"]
WR_CAREER = ["REC", "RECYDS", "YPR", "LNG", "RECTD", "CAR", "RYDS", "YPC", "LNG_RUSH", "RTD",
             "FUM", "LOST"]

# recent column name -> index in that position's career row. Only additive columns appear.
ADDITIVE_PAIRS = {
    "QB": {name: index for index, name in enumerate(QB_CAREER) if name in
           {"CMP", "ATT", "PYDS", "PTD", "INT", "SACKS", "SACK_YDS", "CAR", "RYDS", "RTD",
            "FUM", "LOST"}},
    "RB": {"CAR": 0, "RYDS": 1, "RTD": 3, "REC": 4, "RECYDS": 5, "RECTD": 8, "FUM": 9, "LOST": 10},
    "WR": {"REC": 0, "RECYDS": 1, "RECTD": 4, "CAR": 5, "RYDS": 6, "RTD": 9, "FUM": 10,
           "LOST": 11},
}
# A tight end is printed with the receiver column layout on NFL.com, so TE resolves to the WR spec.
POSITION_LAYOUT = {"QB": "QB", "RB": "RB", "WR": "WR", "TE": "WR"}
RECENT_BY_POSITION = {"QB": QB_RECENT, "RB": RB_RECENT, "WR": WR_RECENT}
CAREER_ROWS = {"QB": QB_CAREER, "RB": RB_CAREER, "WR": WR_CAREER}
HEADER_TO_COLUMNS = {
    "REC|YDS|AVG|LNG|TD|ATT|YDS|AVG|LNG|TD|FUM|LOST": WR_RECENT,
    "ATT|YDS|AVG|LNG|TD|REC|YDS|AVG|LNG|TD|FUM|LOST": RB_RECENT,
}

SCORE = re.compile(r"^(?P<result>[WL])\s+(?P<own>\d+)\s+-\s+(?P<opp>\d+)$")
META = re.compile(r"^(url|page_title|read_on|position_printed|club_printed|recent_games_header):\s*(.*)$")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_evidence(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    rows: list[list[str]] = []
    career: list[str] | None = None
    career_header: list[str] = []
    section = None
    for raw in text.splitlines():
        match = META.match(raw)
        if match:
            meta[match.group(1)] = match.group(2).strip()
            continue
        if raw.startswith("## "):
            section = raw[3:].strip()
            continue
        if not raw.startswith("|"):
            continue
        cells = _cells(raw)
        if not cells or cells[0] in ("---",) or set(cells[0]) <= set("-: "):
            continue
        if cells[0] == "SEASON":
            career_header = cells[4:]
            continue
        if cells[0] == "WK":
            continue
        if section and section.startswith("2026 season total"):
            career = cells
        elif section and section.startswith("Recent games"):
            rows.append(cells)
    return {"meta": meta, "rows": rows, "career": career, "career_header": career_header,
            "path": path}


def layout_for(position: str) -> str:
    layout = POSITION_LAYOUT.get(position)
    if layout is None:
        raise SystemExit(f"no column layout recorded for printed position {position!r}")
    return layout


def columns_for(parsed: dict) -> tuple[list[str], str]:
    pos = layout_for(parsed["meta"].get("position_printed", ""))
    header = parsed["meta"].get("recent_games_header", "")
    if header and not header.startswith("none"):
        cells = [c for c in _cells(header)[3:]]
        key = "|".join(cells)
        if key in HEADER_TO_COLUMNS:
            return HEADER_TO_COLUMNS[key], "printed header"
        raise ValueError(f"{parsed['path'].name}: unrecognised printed header {key!r}")
    return RECENT_BY_POSITION[pos], f"career-table column order for {pos} (page prints no header)"


def results_index() -> dict[tuple[int, str, str], dict]:
    """(week, club, opponent) -> feed row."""
    out = {}
    for row in csv.DictReader(RESULTS.open(encoding="utf-8", newline="")):
        week = int(row["week"])
        out[(week, row["away"], row["home"])] = row
        out[(week, row["home"], row["away"])] = row
    return out


def parse_all() -> tuple[list[dict], list[dict]]:
    """Return (per-game rows, per-player check records). Aborts on any contradiction."""
    feed = results_index()
    games: list[dict] = []
    checks: list[dict] = []
    for path in sorted(EVIDENCE.glob("player-*.md")):
        parsed = parse_evidence(path)
        meta = parsed["meta"]
        player = path.stem.replace("player-", "")
        club = meta.get("club_printed", "")
        club_code = CLUB_NAME_TO_CODE.get(club)
        if club_code is None:
            raise SystemExit(f"{path.name}: club {club!r} is not an NFL club name")
        columns, column_basis = columns_for(parsed)
        if parsed["career"] is None:
            raise SystemExit(f"{path.name}: no 2026 season total printed")
        career = parsed["career"]
        # career: season, team, G, GS, then the stat columns
        career_stats = career[4:]
        errors: list[str] = []
        totals = {name: 0 for name in ADDITIVE_PAIRS.get(layout_for(meta.get("position_printed", "")), {})}
        player_rows = 0
        for cells in parsed["rows"]:
            week = int(cells[0])
            opponent_raw = cells[1]
            venue = "away" if opponent_raw.startswith("@") else "home"
            opponent = NICKNAME_TO_CODE.get(opponent_raw.lstrip("@"))
            score = SCORE.match(cells[2])
            if opponent is None or score is None:
                errors.append(f"week {week}: unparseable opponent/score {cells[:3]}")
                continue
            feed_row = feed.get((week, club_code, opponent))
            if feed_row is None:
                # A club can legitimately have no fixture in that week only if it was on bye, and a
                # bye cannot produce a player row. Treat it as a contradiction.
                errors.append(f"week {week}: {club_code} has no official fixture against {opponent}")
                continue
            feed_home = feed_row["home"] == club_code
            if venue != ("home" if feed_home else "away"):
                errors.append(f"week {week}: venue disagrees with the official fixture")
            own_score = int(score.group("own"))
            opp_score = int(score.group("opp"))
            feed_own = int(feed_row["home_score"] if feed_home else feed_row["away_score"])
            feed_opp = int(feed_row["away_score"] if feed_home else feed_row["home_score"])
            if (own_score, opp_score) != (feed_own, feed_opp):
                errors.append(
                    f"week {week}: printed {own_score}-{opp_score} but the results feed says "
                    f"{feed_own}-{feed_opp}")
            if (score.group("result") == "W") != (own_score > opp_score):
                errors.append(f"week {week}: printed result letter contradicts the printed score")
            stats = cells[3:]
            if len(stats) != len(columns):
                errors.append(f"week {week}: {len(stats)} stat cells for {len(columns)} columns")
                continue
            record = {
                "player_slug": player,
                "player": meta.get("page_title", "").split(" Stats Summary")[0],
                "position": meta.get("position_printed", ""),
                "club_abbr": club_code,
                "week": week,
                "opponent": opponent,
                "venue": venue,
                "result": score.group("result"),
                "team_points": own_score,
                "opponent_points": opp_score,
                "source_url": meta.get("url", ""),
                "read_on": meta.get("read_on", ""),
                "evidence_file": str(path.relative_to(REPO)),
            }
            for name, value in zip(columns, stats):
                if value == "":
                    record[name] = ""
                    continue
                try:
                    record[name] = int(value) if "." not in value else float(value)
                except ValueError:
                    record[name] = ""
                    errors.append(f"week {week}: non-numeric {name} value {value!r}")
            for name in totals:
                value = record.get(name)
                if isinstance(value, (int, float)):
                    totals[name] += value
            games.append(record)
            player_rows += 1

        # Check 1: every additive column must equal the printed season total exactly, comparing
        # the recent-games column to the career column that carries the same quantity.
        pos = layout_for(meta.get("position_printed", ""))
        career_order = CAREER_ROWS.get(pos)
        if career_order is None:
            raise SystemExit(f"{path.name}: no career column spec for position {pos!r}")
        printed_career_header = parsed["career_header"]
        header_note = "career header not printed; standard order used"
        if printed_career_header:
            if printed_career_header != career_order:
                raise SystemExit(
                    f"{path.name}: printed career header {printed_career_header} does not match the "
                    f"recorded order {career_order}; refusing to guess")
            header_note = "printed career header matched the recorded order"
        if len(career_stats) != len(career_order):
            raise SystemExit(
                f"{path.name}: print supplies {len(career_stats)} season columns but the recorded "
                f"{pos} career order has {len(career_order)}")
        total_mismatches = []
        for recent_name, career_index in sorted(ADDITIVE_PAIRS[pos].items()):
            printed = career_stats[career_index]
            if printed in ("", None):
                continue
            wanted = int(float(printed))
            got = totals[recent_name]
            if got != wanted:
                total_mismatches.append({"column": recent_name, "recomputed": got,
                                         "printed": wanted})
        if total_mismatches:
            raise SystemExit(
                f"{path.name}: per-game rows do not sum to the printed season total: "
                + "; ".join(f"{m['column']} {m['recomputed']} != {m['printed']}"
                            for m in total_mismatches))
        if errors:
            raise SystemExit(f"{path.name}: " + " | ".join(errors))

        checks.append({
            "player_slug": player,
            "player": meta.get("page_title", "").split(" Stats Summary")[0],
            "position": meta.get("position_printed", ""),
            "club_abbr": club_code,
            "games_parsed": player_rows,
            "columns_assigned": len(columns),
            "column_basis": column_basis,
            "additive_columns_checked": sum(
                1 for name, index in ADDITIVE_PAIRS[pos].items()
                if career_stats[index] not in ("", None)),
            "career_header_basis": header_note,
            "season_totals_reconcile": "yes",
            "opponent_venue_score_reconcile": "yes",
            "source_url": meta.get("url", ""),
            "read_on": meta.get("read_on", ""),
            "evidence_file": str(path.relative_to(REPO)),
        })
    if not games:
        raise SystemExit("no player game rows parsed")
    return games, checks
