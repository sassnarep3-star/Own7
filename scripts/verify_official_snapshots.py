"""Offline mapped-cell comparison against preserved historical transcriptions.

Player identity aliases are explicitly accent-normalized; exact current official
spellings are preserved by the newer canonical receipts. These are not raw archives.

Each snapshot in data/official-snapshots/ records values read from an nba.com page
(URL in its header comment). This script compares every mapped CSV cell with the
snapshot and exits non-zero on any mismatch. It needs no network access.

Run: python3 scripts/verify_official_snapshots.py
"""
import csv
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAP = ROOT / "data" / "official-snapshots"


def identity(text):
    return "".join(c for c in unicodedata.normalize("NFKD",text) if not unicodedata.combining(c)).casefold()


def read_snapshot(name):
    rows = {}
    for line in (SNAP / name).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.strip().split("|")
        rows[parts[0] if not parts[0].isdigit() else parts[1]] = parts
    return rows


def check(label, csv_path, snap_name, key_col, snap_cols, csv_cols, snap_key_index=0):
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    snap = {}
    for line in (SNAP / snap_name).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.strip().split("|")
        key=identity(parts[snap_key_index])
        if key in snap:raise ValueError("Duplicate historical identity alias")
        snap[key] = parts
    mismatches = []
    matched = 0
    for r in rows:
        key = identity(r[key_col])
        if key not in snap:
            mismatches.append(f"{label}: {key} not in official snapshot")
            continue
        s = snap[key]
        ok = True
        for sc, cc in zip(snap_cols, csv_cols):
            if cc == "Player" and identity(r[cc]) == identity(s[sc]):
                if r[cc] != s[sc]:print(f"Identity alias (not verbatim spelling): {s[sc]} -> {r[cc]}; canonical receipt preserves official spelling")
                continue
            if r[cc] != s[sc]:
                mismatches.append(f"{label}: {key} {cc}: csv={r[cc]!r} official={s[sc]!r}")
                ok = False
        matched += ok
    print(f"{label}: {matched}/{len(rows)} rows match official snapshot ({len(snap)} snapshot rows)")
    return mismatches


def main():
    problems = []
    # teams: snapshot Team|GP|W|L|WIN%|PTS|FG%|3P%|FT%|OREB|DREB|REB|AST|TOV|STL|BLK|PF|PFD|+/-
    team_cols = ["GP", "W", "L", "WIN%", "PTS", "FG%", "3P%", "FT%", "OREB", "DREB", "REB", "AST", "TOV", "STL", "BLK", "PF", "PFD", "+/-"]
    problems += check("teams-2025-26", ROOT / "data/teams-2025-26.csv", "teams-2025-26.txt", "Team",
                      list(range(1, 19)), team_cols)
    # players: snapshot Rank|Player|Team|Age|... (25 fields) -> CSV columns by name; match by Player
    player_cols = ["Rank", "Player", "Team", "Age", "GP", "W", "L", "MIN", "PTS", "FGM", "FGA", "FG%", "3PM", "3PA", "3P%", "FTM", "FTA", "FT%", "OREB", "DREB", "REB", "AST", "TOV", "STL", "BLK", "PF"]
    problems += check("players-2025-26-top15", ROOT / "data/players-2025-26-top15.csv", "players-2025-26-top15.txt",
                      "Player", list(range(0, len(player_cols))), player_cols, snap_key_index=1)
    # standings: snapshot Team|W|L|WIN%|GB|CONF|DIV|HOME|ROAD|LAST10|STREAK
    standings_cols = ["W", "L", "WIN%", "GB", "CONF", "DIV", "HOME", "ROAD", "LAST10", "STREAK"]
    problems += check("standings-2026-27", ROOT / "data/standings-2026-27.csv", "standings-2026-27.txt", "Team",
                      list(range(1, 11)), standings_cols)
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("OK: all mapped numeric cells and explicit normalized identities match historical transcriptions; not a renewed external fact check.")


if __name__ == "__main__":
    main()
