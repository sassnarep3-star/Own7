#!/usr/bin/env python3
"""Parse the saved printed depth charts into one slot table.

Two sources feed this table, and the date difference is published, not hidden:
  * this session's 2026-11-13 reads of 17 club pages (evidence/depth-*.md)
  * the 2026-11-12 club-page transcription already in the repository
    (nfl-assurance-9580ac3f/data/depth.csv), reused as an 11-12 snapshot

Nothing is inferred. A printed blank stays blank. Where a club printed two names in one cell the
slot records both and says so; it does not invent an order inside the cell.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from emit import emit_csv, emit_json, parse_args

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
EVIDENCE = HERE / "evidence"
DATA = HERE / "data"
IMPORT = REPO / "nfl-assurance-9580ac3f" / "data" / "depth.csv"

LINK_CELL = re.compile(r"\[([^\]]+)\]\((https://[^)]+)\)")
PLAIN_CELL = re.compile(r"^(?:\d+\s+)?([A-Za-z][^|]*?)\s*$")
UNIT_RE = re.compile(r"^#+\s*\**\s*(offense|defense|special teams)\s*\**\s*$", re.IGNORECASE)
UNIT_NAMES = {"offense": "Offense", "defense": "Defense", "special teams": "Special Teams"}

# clubs whose chart this session read on 2026-11-13
OWN_FILES = sorted(EVIDENCE.glob("depth-*.md"))

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def norm_name(value: str) -> str:
    """Comparison key only: letters/digits, lowercased, generational suffix dropped."""
    text = value.replace("’", "'").lower()
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    parts = [p for p in text.split() if p]
    while parts and parts[-1] in SUFFIXES:
        parts.pop()
    return "".join(parts)


def parse_cell(cell: str):
    """Return (names, urls, multiple_flag) for one printed cell."""
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


def parse_evidence_file(path: Path):
    text = path.read_text(encoding="utf-8")
    header = {}
    for line in text.split("\n"):
        m = re.match(r"^(url|title|read_on|page_stamp|page_footer):\s*(.*)$", line)
        if m:
            header[m.group(1)] = m.group(2).strip()
    if "url" not in header:
        return None
    if "NOT OBTAINED" in text.split("\n")[0]:
        return {"club": path.stem.split("-")[1], "failed": True, **header}

    rows = []
    unit = None
    for line in text.split("\n"):
        stripped = line.strip()
        m = UNIT_RE.match(stripped)
        if m:
            unit = UNIT_NAMES[m.group(1).lower()]
            continue
        if not stripped.startswith("|") or unit is None:
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if cells and cells[0].lower() == "position":
            continue
        if all(c in ("---", "") for c in cells):
            continue
        rows.append((unit, cells))

    slots = []
    row_counter: dict[tuple, int] = {}
    for unit, cells in rows:
        position = cells[0]
        if not position and rows and slots:
            # continuation row (Green Bay prints these): append to the previous chain
            target = slots[-1]
            for offset, cell in enumerate(cells[1:], start=1):
                names, urls, multi = parse_cell(cell)
                if names:
                    rank = _next_rank(target)
                    slots.append(
                        {
                            "club_abbr": target["club_abbr"],
                            "unit": target["unit"],
                            "position": target["position"],
                            "slot": target["slot"],
                            "rank": rank,
                            "player": " / ".join(names),
                            "cell_holds_multiple": "yes" if multi else "no",
                            "player_urls": " ".join(urls),
                            "source_url": target["source_url"],
                            "checked_on": target["checked_on"],
                            "evidence_file": target["evidence_file"],
                            "note": "continuation row on the printed chart",
                        }
                    )
            continue
        key = (unit, position)
        row_counter[key] = row_counter.get(key, 0) + 1
        slot_index = row_counter[key]
        for offset, cell in enumerate(cells[1:], start=1):
            names, urls, multi = parse_cell(cell)
            if not names:
                slots.append(
                    {
                        "club_abbr": path.stem.split("-")[1],
                        "unit": unit,
                        "position": position,
                        "slot": slot_index,
                        "rank": offset,
                        "player": "",
                        "cell_holds_multiple": "no",
                        "player_urls": "",
                        "source_url": header["url"],
                        "checked_on": header.get("read_on", ""),
                        "evidence_file": f"nfl-availability-28ef/evidence/{path.name}",
                        "note": "printed blank on the club chart",
                    }
                )
                continue
            slots.append(
                {
                    "club_abbr": path.stem.split("-")[1],
                    "unit": unit,
                    "position": position,
                    "slot": slot_index,
                    "rank": offset,
                    "player": " / ".join(names),
                    "cell_holds_multiple": "yes" if multi else "no",
                    "player_urls": " ".join(urls),
                    "source_url": header["url"],
                    "checked_on": header.get("read_on", ""),
                    "evidence_file": f"nfl-availability-28ef/evidence/{path.name}",
                    "note": header.get("page_stamp", ""),
                }
            )
    return {"club": path.stem.split("-")[1], "failed": False, "slots": slots, **header}


def _next_rank(target: dict) -> int:
    return target["rank"] + 1


def _drop_trailing_blanks(slots: list[dict]) -> list[dict]:
    """Drop padding blanks at the end of a printed chain; keep blanks the club printed inside one.

    Most club charts print four to seven columns and leave the unused ones empty. Those trailing
    empty columns carry no information. A blank that a club printed *before* a named player - the
    Jets print one - is real and is kept.
    """
    groups: dict[tuple, list[dict]] = {}
    for row in slots:
        groups.setdefault((row["club_abbr"], row["unit"], row["position"], row["slot"]), []).append(row)
    keep = []
    for rows in groups.values():
        last_named = max((r["rank"] for r in rows if r["player"]), default=0)
        keep.extend(r for r in rows if r["rank"] <= last_named)
    keep.sort(key=lambda r: (r["club_abbr"], r["unit"], r["position"], r["slot"], r["rank"]))
    return keep


def import_assurance_rows():
    """Reuse the in-repo 2026-11-12 club transcription as its own dated snapshot."""
    ranks = ("first", "second", "third", "fourth", "fifth")
    rank_of = {key: i + 1 for i, key in enumerate(ranks)}
    out = []
    with IMPORT.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            # A blank cell the club printed *before* a named player is kept blank; only trailing
            # blanks are dropped (see _drop_trailing_blanks). An interior blank means the club
            # printed no name at that rank, which is a finding, not a gap to fill.
            last_named = max((rank_of[k] for k in ranks if row.get(k, "").strip()), default=0)
            for rank_key in ranks[:last_named]:
                rank = rank_of[rank_key]
                value = row[rank_key].strip()
                if not value:
                    out.append(
                        {
                            "club_abbr": row["team"],
                            "unit": row["unit"],
                            "position": row["position"],
                            "slot": int(row["slot"]),
                            "rank": rank,
                            "player": "",
                            "cell_holds_multiple": "no",
                            "player_urls": "",
                            "source_url": row["source_url"],
                            "checked_on": "2026-11-12",
                            "evidence_file": "nfl-assurance-9580ac3f/data/depth.csv",
                            "note": "the club printed no name at this rank; left blank, not filled in",
                        }
                    )
                    continue
                names = [n.strip() for n in value.split("/")] if "/" in value else [value]
                out.append(
                    {
                        "club_abbr": row["team"],
                        "unit": row["unit"],
                        "position": row["position"],
                        "slot": int(row["slot"]),
                        "rank": rank,
                        "player": " / ".join(names),
                        "cell_holds_multiple": "yes" if len(names) > 1 else "no",
                        "player_urls": "",
                        "source_url": row["source_url"],
                        "checked_on": "2026-11-12",
                        "evidence_file": "nfl-assurance-9580ac3f/data/depth.csv",
                        "note": "transcribed 2026-11-12 by session arena/9580ac3f-own7; reused here as an 11-12 snapshot",
                    }
                )
    return out


def build():
    slots = []
    failures = []
    for path in OWN_FILES:
        parsed = parse_evidence_file(path)
        if parsed is None:
            continue
        if parsed.get("failed"):
            failures.append({"club_abbr": parsed["club"], "url": parsed["url"], "read_on": parsed.get("read_on", ""),
                             "reason": "no depth-chart table in the rendered text"})
            continue
        slots.extend(parsed["slots"])

    imported = import_assurance_rows()
    own_clubs = {s["club_abbr"] for s in slots}
    imported = [r for r in imported if r["club_abbr"] not in own_clubs]
    slots.extend(imported)

    slots.sort(key=lambda r: (r["club_abbr"], r["unit"], r["position"], r["slot"], r["rank"]))
    slots = _drop_trailing_blanks(slots)
    for i, row in enumerate(slots, start=1):
        row["depth_id"] = f"D-{row['club_abbr']}-{i:03d}"
    ordered = ["depth_id", "club_abbr", "unit", "position", "slot", "rank", "player",
               "cell_holds_multiple", "player_urls", "source_url", "checked_on",
               "evidence_file", "note"]
    slots = [{k: r[k] for k in ordered} for r in slots]
    return slots, failures


def main() -> None:
    slots, failures = build()
    emit_csv(DATA / "depth-slots-week10-2026.csv", slots)
    summary = {
        "slots": len(slots),
        "clubs": len({r["club_abbr"] for r in slots}),
        "clubs_by_date": {
            d: sorted({r["club_abbr"] for r in slots if r["checked_on"] == d})
            for d in sorted({r["club_abbr"] and r["checked_on"] for r in slots})
        },
        "multi_name_cells": sum(1 for r in slots if r["cell_holds_multiple"] == "yes"),
        "blank_slots": sum(1 for r in slots if not r["player"]),
        "failures": failures,
    }
    emit_json(DATA / "depth-summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parse_args("Parse the saved printed depth charts into one slot table.")
    main()
