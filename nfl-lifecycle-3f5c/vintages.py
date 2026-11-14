"""Input vintages for the market-lifecycle desk.

A vintage is a complete, hash-identified input set. Two vintages exist:

  v2026-11-12  the frozen pre-Week-10 snapshot the canonical engine uses
               (data/nfl-standings-2026.csv, captured 2026-11-12);
  v2026-11-14  this desk's fresh read of https://www.nfl.com/standings/ on 2026-11-14
               (data/standings-2026-11-14.csv, transcribed verbatim from evidence/standings-2026-11-14.md).

Both standings files must parse to 32 rows with internally consistent arithmetic. The v2026-11-14
file must additionally equal the frozen file on the 30 clubs that played no game between the two
reads, and differ from it on NYG and WAS exactly by the officially published Thursday result
(WAS 24 - NYG 21, FINAL). Any other difference aborts the build.
"""
from __future__ import annotations

import csv
import hashlib
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
for _p in (str(HERE), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

READ_ON = "2026-11-14"
STANDINGS_URL = "https://www.nfl.com/standings/"
SCHEDULE_URL = "https://www.nfl.com/schedules/2026/REG10/"

VINTAGE_A = "v2026-11-12"
VINTAGE_B = "v2026-11-14"

# Clubs whose line-model inputs changed between the two reads, per the official result
# "Commanders 24, Giants 21, FINAL" printed on the Week 10 schedule page.
EXPECTED_MOVED = {"NYG", "WAS"}


def _load_standings(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 32:
        raise ValueError(f"{path.name}: expected 32 standings rows, got {len(rows)}")
    seen = set()
    for row in rows:
        code = row["Team"].split()[-1]
        w, l, t = int(row["W"]), int(row["L"]), int(row["T"])
        games = w + l + t
        if games == 0:
            raise ValueError(f"{path.name}: {row['Team']} has zero games")
        pct_raw = (w + 0.5 * t) / games
        # The publisher prints winning percentage rounded half-up to three decimals
        # (e.g. 2.5/8 prints as 0.313); Python's round() is half-even and would disagree,
        # so the check uses the publisher's convention.
        pct = math.floor(pct_raw * 1000 + 0.5) / 1000
        if f"{pct:.3f}" != f"{float(row['PCT']):.3f}":
            raise ValueError(f"{path.name}: {row['Team']} PCT {row['PCT']} != {pct:.3f}")
        if int(row["NetPts"]) != int(row["PF"]) - int(row["PA"]):
            raise ValueError(f"{path.name}: {row['Team']} NetPts is not PF-PA")
        seen.add(row["Team"])
    if len(seen) != 32:
        raise ValueError(f"{path.name}: duplicate team rows")
    return rows


TEAM_CODES = {
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


def _team_code(row: dict) -> str:
    name = row["Team"]
    if name not in TEAM_CODES:
        raise ValueError(f"Unmapped team name: {name!r}")
    return TEAM_CODES[name]


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_vintage(vintage: str) -> dict:
    """Load one standings vintage with its provenance hash."""
    if vintage == VINTAGE_A:
        path = REPO / "data" / "nfl-standings-2026.csv"
        checked_on = "2026-11-12"
        evidence = "frozen repository snapshot (2026-11-12 capture)"
    elif vintage == VINTAGE_B:
        path = HERE / "data" / "standings-2026-11-14.csv"
        checked_on = READ_ON
        evidence = "evidence/standings-2026-11-14.md"
    else:
        raise ValueError(f"Unknown vintage {vintage!r}")
    rows = _load_standings(path)
    return {
        "id": vintage,
        "standings_file": str(path.relative_to(REPO)),
        "checked_on": checked_on,
        "evidence": evidence,
        "source_url": STANDINGS_URL,
        "sha256": sha256_of(path),
        "rows": rows,
        "by_code": {_team_code(r): r for r in rows},
    }


def moved_clubs(a: dict, b: dict) -> set[str]:
    """Clubs whose line-model inputs differ between two standings vintages."""
    moved = set()
    for code, row in a["by_code"].items():
        other = b["by_code"][code]
        for field in ("W", "L", "T", "PF", "PA"):
            if row[field] != other[field]:
                moved.add(code)
                break
    return moved


def check_vintage_transition() -> dict:
    """Enforce the documented relationship between the two vintages; abort on anything else."""
    a = load_vintage(VINTAGE_A)
    b = load_vintage(VINTAGE_B)
    moved = moved_clubs(a, b)
    if moved != EXPECTED_MOVED:
        raise SystemExit(
            f"Vintage transition moved {sorted(moved)}, expected {sorted(EXPECTED_MOVED)}; "
            "re-read https://www.nfl.com/standings/ and update the evidence file before building.")
    # The delta must equal the officially published final: WAS 24 - NYG 21.
    was_a, was_b = a["by_code"]["WAS"], b["by_code"]["WAS"]
    nyg_a, nyg_b = a["by_code"]["NYG"], b["by_code"]["NYG"]
    if (int(was_b["PF"]) - int(was_a["PF"]), int(was_b["PA"]) - int(was_a["PA"])) != (24, 21):
        raise SystemExit("WAS scoring delta does not equal the published 24-21 road win")
    if (int(nyg_b["PF"]) - int(nyg_a["PF"]), int(nyg_b["PA"]) - int(nyg_a["PA"])) != (21, 24):
        raise SystemExit("NYG scoring delta does not equal the published 24-21 home loss")
    return {"vintage_a": a["id"], "vintage_b": b["id"], "moved": sorted(moved),
            "published_final": "WAS 24 - NYG 21 (FINAL, Thursday, November 12th)"}
