#!/usr/bin/env python3
"""Parse every saved club depth-chart transcription into one slot table.

Inputs are *transcriptions of the clubs' own printed charts* that earlier sessions already read and
committed. This module fetches nothing and invents nothing; it re-reads the saved text so that
**depth of replacement** can be measured from the printed rank, rather than asserted because a
story mentioned a backup.

Three evidence formats exist and all three are supported, because a parser that silently skips a
format would quietly understate depth:

  1. ``nfl-availability-28ef/evidence/depth-<CLUB>.md`` — 19 clubs, read 2026-11-13.
     Headings ``## Offense`` / ``## Defense`` / ``## Special Teams``.
  2. ``nfl-skill-cfdd/evidence/depth-<CLUB>.md`` — 4 clubs, read 2026-11-14 (the Week 10 byes).
     Same shape; HOU's file is a *failure record* and correctly yields no rows.
  3. ``nfl-availability-28ef/evidence/depth-GB.md`` — read 2026-11-13. Uses
     ``#### **OFFENSE**`` headings, prints jersey numbers inside the name cell, and uses a
     CONTINUATION ROW with an empty position cell when a chain runs past the third column.
  4. ``nfl-assurance-9580ac3f/data/depth-source.txt`` — 10 clubs transcribed 2026-11-12 as a
     pipe-delimited ``team|unit|position|first|second|...`` file. Used only for clubs with no
     markdown evidence, and always reported with its own, earlier read date.

Rules that keep the output honest:
  * A printed cell holding two names is kept as one *shared cell*; it is never split into an
    invented order. A continuation row is attributed to the slot it continues (documented in the
    output), never to a new slot.
  * A club whose chart produced no rows is recorded as unavailable with the reason. Nothing is
    substituted.
  * ``slot_depth`` is the count of distinct ranks the club actually prints in that slot. It is a
    count of printed bodies, not a strength rating, not a point value and not a probability.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent

MD_EVIDENCE_DIRS = [
    REPO / "nfl-availability-28ef" / "evidence",
    REPO / "nfl-skill-cfdd" / "evidence",
]
ASSURANCE_DEPTH = REPO / "nfl-assurance-9580ac3f" / "data" / "depth-source.txt"

UNIT_WORDS = {
    "offense": "Offense", "defence": "Defense", "defense": "Defense",
    "special teams": "Special Teams",
}
MD_ROW = re.compile(r"^\|\s*(?P<pos>[A-Za-z0-9]*)\s*\|(?P<cells>.*)\|\s*$")
LINK = re.compile(r"\[(?P<name>[^\]]+)\]\((?P<url>[^)]+)\)")
DOUBLE_LINK = re.compile(r"\]\([^)]*\)\s*\[")
JERSEY = re.compile(r"^(?P<num>\d{1,2})\s+(?P<name>\S.*)$")
SEPARATOR = re.compile(r"^:?-{2,}:?$")


def _unit_of(heading: str) -> str | None:
    plain = re.sub(r"[^A-Za-z ]", "", heading).strip().lower()
    return UNIT_WORDS.get(plain)


def parse_markdown(path: Path) -> dict:
    """Return {url, read_on, page_stamp, units: {unit: [slot rows]}} for one saved chart."""
    text = path.read_text(encoding="utf-8")
    meta = {"url": "", "read_on": "", "page_stamp": "", "jersey_numbers_in_cell": "no",
            "continuation_rows": "no"}
    for line in text.splitlines():
        if line.startswith("url:"):
            meta["url"] = line.split(":", 1)[1].strip()
        elif line.startswith("read_on:"):
            meta["read_on"] = line.split(":", 1)[1].strip()
        elif line.startswith("page_stamp:"):
            # The evidence files sometimes add a parenthetical after the quoted stamp; keep the
            # stamp the club prints and drop the annotation, which the table note carries instead.
            raw = line.split(":", 1)[1].strip()
            quoted = re.match(r'"(?P<stamp>[^"]*)"', raw)
            meta["page_stamp"] = (quoted.group("stamp") if quoted else raw.split("  ")[0]).strip()
        elif line.startswith("note:") and "CONTINUATION ROW" in line:
            meta["continuation_rows"] = "yes"
        elif line.startswith("|") and meta["jersey_numbers_in_cell"] == "no":
            first_cell = line.strip().strip("|").split("|")[0]
            if JERSEY.match(first_cell.strip()):
                meta["jersey_numbers_in_cell"] = "yes"

    units: dict[str, list[dict]] = {}
    unit = None
    last_slot: dict[str, dict] = {}
    for raw in text.splitlines():
        if raw.lstrip().startswith("#"):
            heading = raw.lstrip("#").strip()
            found = _unit_of(heading)
            if found:
                unit = found
                units.setdefault(unit, [])
                last_slot.pop(unit, None)
            continue
        if unit is None:
            continue
        match = MD_ROW.match(raw)
        if not match:
            continue
        position = match.group("pos").strip()
        cells = match.group("cells").split("|")
        # Skip the printed header row and the markdown separator row. Only these two: an empty
        # position cell is a CONTINUATION ROW (see the GB evidence) and must not be dropped.
        stripped = [c.strip() for c in cells]
        if position.lower() == "position":
            continue
        if stripped and all(SEPARATOR.match(c) for c in stripped if c) and any(stripped):
            continue
        players = []
        for rank, cell in enumerate(cells, start=1):
            cell = cell.strip()
            if not cell:
                continue
            links = LINK.findall(cell)
            shared = "yes" if DOUBLE_LINK.search(cell) else "no"
            if links:
                for order, (label, url) in enumerate(links, start=1):
                    players.append({"rank": rank, "order_in_cell": order, "name": label.strip(),
                                    "url": url.strip(), "shared_cell": shared})
            else:
                # Plain printed name, possibly preceded by a jersey number.
                name = cell
                num = JERSEY.match(cell)
                if num:
                    name = num.group("name").strip()
                players.append({"rank": rank, "order_in_cell": 1, "name": name, "url": "",
                                "shared_cell": shared})
        if not players:
            continue
        if position == "":
            # Continuation row: append to the slot directly above, in the same printed order.
            previous = last_slot.get(unit)
            if previous is None:
                continue
            previous["continued"] = "yes"
            for player in players:
                player["rank"] = max(p["rank"] for p in previous["players"]) + 1
                previous["players"].append(player)
            continue
        row = {"position": position, "players": players, "continued": "no"}
        units[unit].append(row)
        last_slot[unit] = row
    return {**meta, "units": units}


def parse_assurance() -> dict[str, list[dict]]:
    """team -> [{unit, position, players}] from the 2026-11-12 pipe transcription."""
    if not ASSURANCE_DEPTH.is_file():
        return {}
    out: dict[str, list[dict]] = {}
    for line in ASSURANCE_DEPTH.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 4:
            continue
        team, unit, position = parts[0].strip(), parts[1].strip(), parts[2].strip()
        players = []
        for rank, cell in enumerate(parts[3:], start=1):
            cell = cell.strip()
            if not cell:
                continue
            shared = "yes" if "/" in cell else "no"
            for order, name in enumerate([x.strip() for x in cell.split("/") if x.strip()], start=1):
                players.append({"rank": rank, "order_in_cell": order, "name": name,
                                "url": "", "shared_cell": shared})
        if players:
            out.setdefault(team, []).append({"position": position, "players": players,
                                             "continued": "no", "unit_hint": unit})
    return out


def available_clubs() -> set[str]:
    clubs = {p.stem.split("-", 1)[1] for d in MD_EVIDENCE_DIRS if d.is_dir()
             for p in d.glob("depth-*.md")}
    return clubs | set(parse_assurance())


def build_depth_rows() -> tuple[list[dict], list[dict], dict]:
    """One row per printed slot position, plus one availability row per club.

    A *slot* is one printed position column such as ``WR 1``. Its ``slot_depth`` is the number of
    distinct printed ranks in that slot. That is the quantity the brief asks for: replacing the
    first name of a five-deep queue is a different event from replacing the only body at a
    position, and the table keeps them apart.
    """
    rows: list[dict] = []
    clubs: list[dict] = []
    sources_used: dict[str, dict] = {}
    md_files: dict[str, Path] = {}
    for directory in MD_EVIDENCE_DIRS:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("depth-*.md")):
            club = path.stem.split("-", 1)[1]
            md_files[club] = path  # later directory (the 11-14 read) wins; conflict is visible below

    for club, path in sorted(md_files.items()):
        parsed = parse_markdown(path)
        if not parsed["units"]:
            clubs.append({"club_abbr": club, "unit": "(all)",
                          "printed_chart_available": "no",
                          "reason": "saved evidence parsed to no slot rows (chart rendered as an image or page failed)",
                          "chart_date_printed": parsed["page_stamp"] or "not printed",
                          "read_on": parsed["read_on"],
                          "source_url": parsed["url"],
                          "evidence_file": str(path.relative_to(REPO))})
            sources_used[club] = {"format": "markdown", "path": str(path.relative_to(REPO)),
                                  "read_on": parsed["read_on"], "url": parsed["url"]}
            continue
        sources_used[club] = {"format": "markdown", "path": str(path.relative_to(REPO)),
                              "read_on": parsed["read_on"], "url": parsed["url"]}
        _emit_club(rows, clubs, club, parsed["units"], parsed, str(path.relative_to(REPO)))

    assurance = parse_assurance()
    for club, unit_rows in sorted(assurance.items()):
        if club in md_files:
            continue  # markdown evidence is dated later; never mix two reads of one chart
        units: dict[str, list[dict]] = {}
        for row in unit_rows:
            units.setdefault(row["unit_hint"], []).append(row)
        meta = {"url": f"(see nfl-assurance-9580ac3f/sources/registry.json entry A958-{club}-DEPTH)",
                "read_on": "2026-11-12", "page_stamp": "",
                "continuation_rows": "no", "jersey_numbers_in_cell": "no"}
        sources_used[club] = {"format": "pipe", "path": str(ASSURANCE_DEPTH.relative_to(REPO)),
                              "read_on": "2026-11-12", "url": meta["url"]}
        _emit_club(rows, clubs, club, units, meta, str(ASSURANCE_DEPTH.relative_to(REPO)))

    stats = {
        "clubs_with_printed_chart": sorted({c["club_abbr"] for c in clubs
                                            if c.get("printed_chart_available") == "yes"}),
        "clubs_without_printed_chart": sorted({c["club_abbr"] for c in clubs
                                               if c.get("printed_chart_available") == "no"}),
        "slot_rows": len(rows),
        "sources": sources_used,
    }
    return rows, clubs, stats


def _emit_club(rows, clubs, club, units, meta, evidence_file) -> None:
    slot_counter: dict[tuple[str, str], int] = {}
    for unit in ("Offense", "Defense", "Special Teams"):
        unit_rows = units.get(unit) or []
        if not unit_rows:
            continue
        before = len(rows)
        for row in unit_rows:
            key = (unit, row["position"])
            slot_counter[key] = slot_counter.get(key, 0) + 1
            slot = slot_counter[key]
            ranks = sorted({p["rank"] for p in row["players"]})
            depth = len(ranks)
            for player in row["players"]:
                rows.append({
                    "chart_id": f"{club}-{unit[:3].upper()}-{row['position']}-{slot}-{player['rank']}",
                    "club_abbr": club, "unit": unit, "position": row["position"],
                    "slot": slot, "printed_rank": player["rank"],
                    "printed_depth": depth,
                    "player": player["name"], "player_url": player["url"],
                    "shared_cell": player["shared_cell"],
                    "continuation_row": row.get("continued", "no"),
                    "chart_date_printed": meta["page_stamp"] or "not printed",
                    "read_on": meta["read_on"],
                    "source_url": meta["url"],
                    "evidence_file": evidence_file,
                })
        unit_slot_rows = rows[before:]
        slots = {(r["position"], r["slot"]) for r in unit_slot_rows}
        clubs.append({
            "club_abbr": club, "unit": unit, "printed_chart_available": "yes",
            "printed_slots": len(slots), "printed_names": len(unit_slot_rows),
            "slots_with_one_body": sum(
                1 for (pos, sl) in slots
                if max(r["printed_depth"] for r in unit_slot_rows
                       if r["position"] == pos and r["slot"] == sl) == 1),
            "deepest_printed_queue": max(r["printed_depth"] for r in unit_slot_rows),
            "shared_cells": sum(1 for r in unit_slot_rows if r["shared_cell"] == "yes"),
            "chart_date_printed": meta["page_stamp"] or "not printed",
            "read_on": meta["read_on"],
            "source_url": meta["url"],
            "evidence_file": evidence_file,
        })
