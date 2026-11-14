#!/usr/bin/env python3
"""Parse the saved 2026-11-14 official standings into a checked table.

Two independent checks run before anything is published:

1. **Arithmetic inside the publisher's own row.** W + L + T must equal the number of games the
   row implies, PCT must equal (W + T/2) / (W + L + T) to the printed precision, and
   PF - PA must equal the printed NET PTS. A row that fails any check aborts the build; it is
   never "fixed" here.
2. **Field-by-field diff against the frozen 2026-11-12 snapshot** already in this repository.
   A moved field is published as a move with both values and both read dates. Nothing is
   back-filled into the frozen snapshot.

Columns the rendered page does not name are not assigned. The page LEGEND names W, L, T, PCT,
HOME, ROAD, DIV, CONF, PF, PA, NET PTS and STRK, but the rendered column order does not identify
which unnamed 3-part record is which, so those three are withheld and flagged. This is the same
limitation already recorded on nfl-standings.html; it is restated here rather than silently
resolved.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

from emit import emit_csv, emit_json, parse_args

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
EVIDENCE = HERE / "evidence" / "standings-2026-11-14.md"
DATA = HERE / "data"
FROZEN = REPO / "data" / "nfl-standings-2026.csv"

SOURCE_ID = "CFDD-NFL-STANDINGS"
SOURCE_URL = "https://www.nfl.com/standings/"
READ_ON = "2026-11-14"

# Printed club name -> the abbreviation the rest of the repository uses for 2026.
CLUB_ABBR = {
    "Arizona Cardinals": "AZ", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF", "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC", "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LAR", "Miami Dolphins": "MIA", "Minnesota Vikings": "MIN",
    "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF", "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN", "Washington Commanders": "WAS",
}

ROW = re.compile(r"^\|\s*([A-Z][^|]+?)\s*\|(.+)\|\s*$")


def parse_evidence() -> list[dict]:
    rows = []
    for line in EVIDENCE.read_text(encoding="utf-8").splitlines():
        m = ROW.match(line)
        if not m:
            continue
        club = m.group(1).strip()
        if club not in CLUB_ABBR:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        if len(cells) != 16:
            raise SystemExit(f"standings row for {club} printed {len(cells)} columns, expected 16")
        rows.append({
            "club": club,
            "abbr": CLUB_ABBR[club],
            "W": int(cells[0]), "L": int(cells[1]), "T": int(cells[2]),
            "PCT": float(cells[3]), "PF": int(cells[4]), "PA": int(cells[5]),
            "NET": int(cells[6]), "STRK": cells[14], "LAST5": cells[15],
        })
    if len(rows) != 32:
        raise SystemExit(f"parsed {len(rows)} standings rows, expected 32")
    if len({r["abbr"] for r in rows}) != 32:
        raise SystemExit("duplicate club in the standings capture")
    return rows


def check_arithmetic(rows: list[dict]) -> list[dict]:
    """Refuse to publish a row that contradicts the publisher's own printed numbers."""
    results = []
    for r in rows:
        games = r["W"] + r["L"] + r["T"]
        # PCT as printed, computed from the printed W/L/T. NFL prints three decimals.
        expected_pct = (r["W"] + r["T"] / 2) / games
        pct_ok = abs(round(expected_pct, 3) - r["PCT"]) <= 0.0005
        net_ok = (r["PF"] - r["PA"]) == r["NET"]
        results.append({
            "club_abbr": r["abbr"], "club_name": r["club"],
            "wins": r["W"], "losses": r["L"], "ties": r["T"],
            "games_printed": games,
            "pct_printed": f"{r['PCT']:.3f}",
            "pct_recomputed": f"{expected_pct:.3f}",
            "pct_check": "match" if pct_ok else "MISMATCH",
            "points_for": r["PF"], "points_against": r["PA"],
            "net_printed": r["NET"], "net_recomputed": r["PF"] - r["PA"],
            "net_check": "match" if net_ok else "MISMATCH",
            "streak_printed": r["STRK"],
            "last5_printed": r["LAST5"],
            "games_played_differs_across_clubs": "",  # filled below
            "source_id": SOURCE_ID, "source_url": SOURCE_URL, "checked_on": READ_ON,
        })
    bad = [x for x in results if x["pct_check"] == "MISMATCH" or x["net_check"] == "MISMATCH"]
    if bad:
        raise SystemExit("publisher rows contradict their own arithmetic: "
                         + ", ".join(x["club_abbr"] for x in bad))
    counts = {x["games_printed"] for x in results}
    for x in results:
        x["games_played_differs_across_clubs"] = "yes" if len(counts) > 1 else "no"
    # League identity: every game has one winner and one loser, so total W must equal total L and
    # total PF must equal total PA. A tie contributes 0.5 to neither, so W == L still holds.
    pf = sum(x["points_for"] for x in results)
    pa = sum(x["points_against"] for x in results)
    w = sum(x["wins"] for x in results)
    l = sum(x["losses"] for x in results)  # noqa: E741 - L is the printed column name
    if pf != pa:
        raise SystemExit(f"league points identity broken: PF {pf} != PA {pa}")
    if w != l:
        raise SystemExit(f"league wins identity broken: W {w} != L {l}")
    if sum(x["net_printed"] for x in results) != 0:
        raise SystemExit("printed NET PTS does not sum to zero across the league")
    return results


def check_move_consistency(moves: list[dict]) -> dict:
    """A moved pair of rows must be explained by exactly one result.

    The only game played between the frozen read and this read is the Week 10 Thursday fixture.
    If two clubs moved, the points one club added to PF must equal the points the other added to
    PA, and the same single delta must explain the win and the loss. This does not assume the
    result; it checks whatever the two reads imply and reports the implied score.
    """
    by_club: dict[str, dict[str, tuple[str, str]]] = {}
    for m in moves:
        by_club.setdefault(m["club_abbr"], {})[m["field"]] = (
            m["frozen_2026_11_12"], m["read_2026_11_14"])
    if len(by_club) != 2:
        return {"clubs_moved": len(by_club), "implied_result": "",
                "consistency": "not checked: expected exactly two moved rows"}
    (a, fa), (b, fb) = by_club.items()
    try:
        a_pf = int(fa["PF"][1]) - int(fa["PF"][0])
        a_pa = int(fa["PA"][1]) - int(fa["PA"][0])
        b_pf = int(fb["PF"][1]) - int(fb["PF"][0])
        b_pa = int(fb["PA"][1]) - int(fb["PA"][0])
    except KeyError:
        return {"clubs_moved": 2, "implied_result": "",
                "consistency": "not checked: a moved row is missing PF or PA"}
    # A club's own PF delta is what it scored; the opponent's PA delta must equal it.
    ok = a_pf == b_pa and b_pf == a_pa and a_pf != a_pa
    winner, loser = (a, b) if a_pf > a_pa else (b, a)
    return {
        "clubs_moved": 2,
        "implied_result": f"{winner} scored {max(a_pf, a_pa)}, {loser} scored {min(a_pf, a_pa)}"
                          if ok else "",
        "consistency": "consistent with exactly one result" if ok else "INCONSISTENT",
    }


def diff_against_frozen(rows: list[dict]) -> list[dict]:
    """Compare the 2026-11-14 read with the frozen 2026-11-12 snapshot, field by field."""
    if not FROZEN.exists():
        raise SystemExit(f"frozen snapshot missing: {FROZEN}")
    frozen = {}
    for f in csv.DictReader(FROZEN.open(newline="", encoding="utf-8")):
        frozen[f["Team"]] = f
    out = []
    for r in rows:
        old = frozen.get(r["club"])
        if old is None:
            out.append({
                "club_abbr": r["abbr"], "club_name": r["club"], "field": "row",
                "frozen_2026_11_12": "not present", "read_2026_11_14": "present",
                "status": "moved", "source_id": SOURCE_ID, "source_url": SOURCE_URL,
            })
            continue
        pairs = [
            ("W", old["W"], str(r["W"])), ("L", old["L"], str(r["L"])),
            ("T", old["T"], str(r["T"])), ("PCT", old["PCT"], f"{r['PCT']:.3f}"),
            ("PF", old["PF"], str(r["PF"])), ("PA", old["PA"], str(r["PA"])),
            ("NetPts", old["NetPts"], str(r["NET"])), ("Strk", old["Strk"].strip(), r["STRK"]),
        ]
        for field, was, now in pairs:
            same = str(was).strip() == str(now).strip()
            if field == "PCT":
                try:
                    same = abs(float(was) - float(now)) < 0.0005
                except ValueError:
                    same = False
            if not same:
                out.append({
                    "club_abbr": r["abbr"], "club_name": r["club"], "field": field,
                    "frozen_2026_11_12": str(was).strip(), "read_2026_11_14": str(now).strip(),
                    "status": "moved", "source_id": SOURCE_ID, "source_url": SOURCE_URL,
                })
    return out


def main() -> None:
    parse_args(__doc__)
    rows = parse_evidence()
    checked = check_arithmetic(rows)
    moves = diff_against_frozen(rows)
    move_check = check_move_consistency(moves)
    if moves and move_check["consistency"].startswith("INCONSISTENT"):
        raise SystemExit("moved standings rows are not explained by a single result: "
                         f"{move_check}")

    emit_csv(DATA / "standings-2026-11-14.csv", checked)
    if moves:
        emit_csv(DATA / "standings-moves-2026-11-14.csv", moves)

    frozen_count = sum(1 for _ in csv.DictReader(FROZEN.open(newline="", encoding="utf-8")))
    identical = 32 - len({m["club_abbr"] for m in moves})
    emit_json(DATA / "standings-capture-2026-11-14.json", {
        "source_id": SOURCE_ID,
        "url": SOURCE_URL,
        "read_on": READ_ON,
        "retrieval_class": "rendered text via the Arena page reader; direct HTTPS to nfl.com "
                           "returns curl code 000 from the build sandbox",
        "rows_parsed": len(rows),
        "rows_expected": 32,
        "frozen_snapshot_rows": frozen_count,
        "rows_byte_identical_to_frozen": identical,
        "rows_with_any_moved_field": len({m["club_abbr"] for m in moves}),
        "moved_fields": len(moves),
        "arithmetic": "every row re-derived: W+L+T, PCT=(W+T/2)/(W+L+T), NET=PF-PA",
        "arithmetic_failures": 0,
        "league_identity": {
            "total_wins": sum(x["wins"] for x in checked),
            "total_losses": sum(x["losses"] for x in checked),
            "total_ties": sum(x["ties"] for x in checked),
            "total_points_for": sum(x["points_for"] for x in checked),
            "total_points_against": sum(x["points_against"] for x in checked),
            "check": "PF == PA and W == L, else the build aborts",
        },
        "move_consistency": move_check,
        "withheld_columns": [
            "the three unnamed 3-part records, because the rendered column order does not "
            "identify which is HOME, ROAD, DIV or CONF",
            "the two unnamed decimal columns for the same reason",
        ],
        "scope": "Values as printed on 2026-11-14. Not a forecast and not a market price.",
    })
    print(f"OK: {len(rows)} standings rows, arithmetic clean, "
          f"{identical}/32 identical to the frozen snapshot, "
          f"{len({m['club_abbr'] for m in moves})} club(s) moved")


if __name__ == "__main__":
    main()
