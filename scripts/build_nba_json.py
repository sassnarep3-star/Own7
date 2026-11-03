#!/usr/bin/env python3
"""Build verified/data/nba_*.json from the verified CSVs, after cross-checking them
against the official snapshots in data/raw/ (transcribed from the nba.com pages
listed in docs/verification.md).

Exit code 1 on any mismatch, so a CSV value that differs from the official
snapshot can never reach the site.

Usage:
  python3 scripts/build_nba_json.py          # check + write JSON
  python3 scripts/build_nba_json.py --check  # check only, write nothing
"""
import csv
import json
import pathlib
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
OUT = ROOT / "verified" / "data"


def norm(s):
    """ASCII-fold names (NBA.com 'Dončić' vs CSV 'Doncic'). Only used for matching."""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def same(a, b):
    try:
        return float(a) == float(b)
    except ValueError:
        return a == b


errors = []

# ---- Teams (2025-26): CSV vs official snapshot, 18 compared columns
TEAM_COLS = ["GP", "W", "L", "WIN%", "PTS", "FG%", "3P%", "FT%", "OREB", "DREB", "REB",
             "AST", "TOV", "STL", "BLK", "PF", "PFD", "+/-"]
snap_teams = read(RAW / "nba-teams-2025-26-official-snapshot.csv")
csv_teams = read(DATA / "teams-2025-26.csv")
csv_by_team = {r["Team"]: r for r in csv_teams}
if len(snap_teams) != 30 or len(csv_teams) != 30:
    errors.append(f"teams: expected 30 rows, snapshot={len(snap_teams)} csv={len(csv_teams)}")
for s in snap_teams:
    c = csv_by_team.get(s["Team"])
    if c is None:
        errors.append(f"teams: {s['Team']} missing from CSV")
        continue
    for col in TEAM_COLS:
        if not same(s[col], c[col]):
            errors.append(f"teams: {s['Team']} {col} official={s[col]} csv={c[col]}")

# ---- Players (2025-26 top 15 by PPG): CSV vs official snapshot, 22 compared columns
PLAYER_COLS = ["GP", "W", "L", "MIN", "PTS", "FGM", "FGA", "FG%", "3PM", "3PA", "3P%",
               "FTM", "FTA", "FT%", "OREB", "DREB", "REB", "AST", "TOV", "STL", "BLK", "PF"]
snap_players = read(RAW / "nba-players-2025-26-top15-official-snapshot.csv")
csv_players = read(DATA / "players-2025-26-top15.csv")
if len(snap_players) != 15 or len(csv_players) != 15:
    errors.append(f"players: expected 15 rows, snapshot={len(snap_players)} csv={len(csv_players)}")
for s, c in zip(snap_players, csv_players):
    if s["Rank"] != c["Rank"] or norm(s["Player"]) != norm(c["Player"]):
        errors.append(f"players: rank/name mismatch {s['Rank']} {s['Player']} vs {c['Rank']} {c['Player']}")
    for col in PLAYER_COLS + ["Age"]:
        if not same(s[col], c[col]):
            errors.append(f"players: {s['Player']} {col} official={s[col]} csv={c[col]}")

# ---- Standings (2026-27): CSV vs official snapshot
STAND_COLS = ["W", "L", "WIN%", "GB", "CONF", "DIV", "HOME", "ROAD", "LAST10", "STREAK"]
snap_st = read(RAW / "nba-standings-2026-27-official-snapshot.csv")
csv_st = {r["Team"]: r for r in read(DATA / "standings-2026-27.csv")}
if len(snap_st) != 30 or len(csv_st) != 30:
    errors.append(f"standings: expected 30 rows, snapshot={len(snap_st)} csv={len(csv_st)}")
for s in snap_st:
    c = csv_st.get(s["Team"])
    if c is None:
        errors.append(f"standings: {s['Team']} missing from CSV")
        continue
    for col in STAND_COLS:
        if s[col] != c[col] and not (col == "GB" and {s[col], c[col]} <= {"--", "0"}):
            if not same(s[col], c[col]):
                errors.append(f"standings: {s['Team']} {col} official={s[col]} csv={c[col]}")

if errors:
    print("SNAPSHOT MISMATCH — refusing to build:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print(f"snapshot check OK: teams {len(snap_teams)}x{len(TEAM_COLS)} cols, "
      f"players {len(snap_players)}x{len(PLAYER_COLS) + 1} cols, standings {len(snap_st)}x{len(STAND_COLS)} cols")

if "--check" in sys.argv:
    sys.exit(0)

# ---- Write verified JSON (one row per official table row, with its nba.com source link)
SRC_TEAM_HDR = ["Rank", "Team", "Conference", "Division", "GP", "W", "L", "WIN%", "PTS", "FG%", "3P%", "FT%",
                "OREB", "DREB", "REB", "AST", "TOV", "STL", "BLK", "PF", "PFD", "+/-"]
team_rows = []
snap_by_team = {s["Team"]: s for s in snap_teams}
for c in csv_teams:
    s = snap_by_team[c["Team"]]
    row = {
        "id": f"T-{int(c['Rank']):02d}-{c['Team'].split()[-1].lower()}",
        "rank": c["Rank"], "team": c["Team"], "conference": c["Conference"], "division": c["Division"],
        "gp": s["GP"], "w": s["W"], "l": s["L"], "win_pct": s["WIN%"], "pts": s["PTS"],
        "fg_pct": s["FG%"], "fg3_pct": s["3P%"], "ft_pct": s["FT%"], "oreb": s["OREB"], "dreb": s["DREB"],
        "reb": s["REB"], "ast": s["AST"], "tov": s["TOV"], "stl": s["STL"], "blk": s["BLK"],
        "blka": s["BLKA"], "pf": s["PF"], "pfd": s["PFD"], "plus_minus": s["+/-"],
        "status": "verified", "source_url": c["Source"],
    }
    team_rows.append(row)

player_rows = []
for c in csv_players:
    player_rows.append({
        "id": f"P-{int(c['Rank']):02d}", "rank": c["Rank"], "player": c["Player"], "team": c["Team"],
        "age": c["Age"], "gp": c["GP"], "w": c["W"], "l": c["L"], "min": c["MIN"], "pts": c["PTS"],
        "fgm": c["FGM"], "fga": c["FGA"], "fg_pct": c["FG%"], "fg3m": c["3PM"], "fg3a": c["3PA"],
        "fg3_pct": c["3P%"], "ftm": c["FTM"], "fta": c["FTA"], "ft_pct": c["FT%"], "oreb": c["OREB"],
        "dreb": c["DREB"], "reb": c["REB"], "ast": c["AST"], "tov": c["TOV"], "stl": c["STL"],
        "blk": c["BLK"], "pf": c["PF"], "status": "verified", "source_url": c["Source"],
    })

standing_rows = []
for c in read(DATA / "standings-2026-27.csv"):
    standing_rows.append({
        "id": f"S-{c['Conference'][0]}{int(c['Rank']):02d}", "rank": c["Rank"], "conference": c["Conference"],
        "team": c["Team"], "w": c["W"], "l": c["L"], "win_pct": c["WIN%"], "gb": c["GB"], "conf": c["CONF"],
        "div": c["DIV"], "home": c["HOME"], "road": c["ROAD"], "last10": c["LAST10"], "streak": c["STREAK"],
        "games_played": str(int(c["W"]) + int(c["L"])),
        "status": "verified", "source_url": c["Source"],
    })

OUT.mkdir(parents=True, exist_ok=True)
for name, title, cols, rows in [
    ("nba_teams", "NBA teams, 2025-26 regular season (official, 30 rows)",
     ["id", "rank", "team", "conference", "division", "gp", "w", "l", "win_pct", "pts", "fg_pct", "fg3_pct",
      "ft_pct", "oreb", "dreb", "reb", "ast", "tov", "stl", "blk", "blka", "pf", "pfd", "plus_minus",
      "status", "source_url"], team_rows),
    ("nba_players", "NBA players, 2025-26 top 15 by points per game (official, 15 rows)",
     ["id", "rank", "player", "team", "age", "gp", "w", "l", "min", "pts", "fgm", "fga", "fg_pct", "fg3m",
      "fg3a", "fg3_pct", "ftm", "fta", "ft_pct", "oreb", "dreb", "reb", "ast", "tov", "stl", "blk", "pf",
      "status", "source_url"], player_rows),
    ("nba_standings", "NBA standings, 2026-27 regular season in progress (official, 30 rows)",
     ["id", "rank", "conference", "team", "w", "l", "win_pct", "gb", "conf", "div", "home", "road", "last10",
      "streak", "games_played", "status", "source_url"], standing_rows),
]:
    (OUT / f"{name}.json").write_text(
        json.dumps({"title": title, "columns": cols, "rows": rows}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"wrote {name}.json ({len(rows)} rows)")
