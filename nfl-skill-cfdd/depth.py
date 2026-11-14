#!/usr/bin/env python3
"""Parse the four newly captured printed depth charts into the same slot table shape the
availability desk already uses, so the two sets join without a translation layer.

Scope, stated plainly:
  * This session read 4 club pages on 2026-11-14: CHI, DEN, PHI, TB. Those are the four clubs no
    chart had been captured for in any earlier snapshot.
  * Houston is NOT captured. The club's page returns a heading and an image and no table; the
    earlier desk recorded the same failure on 2026-11-13 and this read reproduces it. Houston stays
    a published gap.
  * Nothing is inferred. A printed blank stays blank. Two names printed in one cell are both kept
    and the cell is marked, with no order invented between them.
"""
from __future__ import annotations

import re
from pathlib import Path

from emit import emit_csv, emit_json, parse_args

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
DATA = HERE / "data"

CLUBS = {
    "CHI": "Chicago Bears",
    "DEN": "Denver Broncos",
    "PHI": "Philadelphia Eagles",
    "TB": "Tampa Bay Buccaneers",
}

LINK_CELL = re.compile(r"\[([^\]]+)\]\((https://[^)]+)\)")
UNIT_RE = re.compile(r"^##\s*(Offense|Defense|Special Teams)\s*$", re.IGNORECASE)
ROW_RE = re.compile(r"^\|\s*([A-Za-z/]+)\s*\|(.*)\|\s*$")
# The club pages print the chart date in different shapes; keep only what is actually rendered.
STAMP_RE = re.compile(r"^page_stamp:\s*(.*)$", re.MULTILINE)
READ_RE = re.compile(r"^read_on:\s*(.*)$", re.MULTILINE)
URL_RE = re.compile(r"^url:\s*(.*)$", re.MULTILINE)


def parse_cell(cell: str):
    cell = cell.strip()
    if not cell:
        return [], [], False
    links = LINK_CELL.findall(cell)
    if links:
        names = [n.strip() for n, _ in links]
        return names, [u for _, u in links], len(names) > 1
    stripped = re.sub(r"^\d+\s+", "", cell).strip()
    if not stripped:
        return [], [], False
    return [stripped], [], False


def parse_file(path: Path, club: str) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    url = URL_RE.search(text).group(1).strip()
    read_on = READ_RE.search(text).group(1).strip()
    stamp = STAMP_RE.search(text)
    stamp = stamp.group(1).strip().strip('"') if stamp else ""
    rows, unit, slot_counts = [], None, {}
    blank_cells = 0
    for line in text.splitlines():
        m = UNIT_RE.match(line.strip())
        if m:
            unit = m.group(1).title().replace("Special Teams", "Special Teams")
            slot_counts[unit] = 0
            continue
        if unit is None or not line.startswith("|"):
            continue
        m = ROW_RE.match(line)
        if not m:
            continue
        position = m.group(1).strip()
        cells = [c for c in m.group(2).split("|")]
        if cells and cells[-1].strip() == "":
            cells = cells[:-1]
        slot_counts[unit] += 1
        slot = slot_counts[unit]
        for rank, cell in enumerate(cells, start=1):
            names, urls, multiple = parse_cell(cell)
            if not names:
                # A printed blank is not a row, but it is a fact about the source and is counted.
                if rank == 1:
                    blank_cells += 1
                continue
            rows.append({
                "club_abbr": club,
                "club_name": CLUBS[club],
                "unit": unit,
                "position": position,
                "slot": slot,
                "rank": rank,
                "player": names[0] if len(names) == 1 else " / ".join(names),
                "cell_holds_multiple": "yes" if multiple else "no",
                "player_urls": " ".join(urls),
                "chart_date_printed": stamp,
                "source_url": url,
                "checked_on": read_on,
                "evidence_file": str(path.relative_to(HERE.parent)),
            })
    for r in rows:
        r["_first_cell_blank"] = ""
    return rows, blank_cells


def main() -> None:
    parse_args(__doc__)
    all_rows = []
    blank_total = 0
    for club in CLUBS:
        path = EVIDENCE / f"depth-{club}.md"
        if not path.exists():
            raise SystemExit(f"missing evidence file: {path}")
        club_rows, club_blanks = parse_file(path, club)
        blank_total += club_blanks
        all_rows.extend(club_rows)
    if not all_rows:
        raise SystemExit("no depth slots parsed")
    for i, row in enumerate(all_rows, start=1):
        row_id = f"K-{row['club_abbr']}-{row['unit'][:3].upper()}-{row['slot']:03d}-{row['rank']}"
        row["depth_id"] = row_id

    order = ["depth_id", "club_abbr", "club_name", "unit", "position", "slot", "rank", "player",
             "cell_holds_multiple", "player_urls", "first_cell_blank", "chart_date_printed",
             "source_url", "checked_on", "evidence_file"]
    first_rank_keys = {(r["club_abbr"], r["unit"], r["slot"]) for r in all_rows
                       if int(r["rank"]) == 1}
    for r in all_rows:
        r["first_cell_blank"] = (
            "no" if (r["club_abbr"], r["unit"], r["slot"]) in first_rank_keys else "yes")
    all_rows = [{k: r[k] for k in order} for r in all_rows]
    emit_csv(DATA / "depth-slots-2026-11-14.csv", all_rows)

    by_club: dict[str, dict] = {}
    for r in all_rows:
        key = r["club_abbr"]
        entry = by_club.setdefault(key, {"club_abbr": key, "club_name": r["club_name"], "slots": 0,
                                         "offense": 0, "defense": 0, "special_teams": 0,
                                         "multi_name_cells": 0, "deepest_rank": 0,
                                         "chart_date_printed": r["chart_date_printed"],
                                         "source_url": r["source_url"]})
        entry["slots"] += 1
        entry[{"Offense": "offense", "Defense": "defense",
               "Special Teams": "special_teams"}[r["unit"]]] += 1
        if r["cell_holds_multiple"] == "yes":
            entry["multi_name_cells"] += 1
        entry["deepest_rank"] = max(entry["deepest_rank"], int(r["rank"]))
    emit_json(DATA / "depth-summary-2026-11-14.json", {
        "clubs_captured": sorted(by_club),
        "clubs_requested": sorted(CLUBS),
        "total_printed_slots": len(all_rows),
        "per_club": [by_club[k] for k in sorted(by_club)],
        "not_captured": {
            "HOU": "club page renders a heading and an image, no table; the 2026-11-13 failure was "
                   "reproduced on 2026-11-14 and Houston stays a published blank",
        },
        "blank_printed_cells": blank_total,
        "read_on": "2026-11-14",
        "scope": "Printed chart ranks only. No snap count, no snap share, no performance value and "
                 "no point contribution is produced from a rank.",
    })
    print(f"OK: {len(all_rows)} printed slots across {len(by_club)} clubs")


if __name__ == "__main__":
    main()
