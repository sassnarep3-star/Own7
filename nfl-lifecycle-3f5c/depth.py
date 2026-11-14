"""Depth-of-replacement view over the cfdd desk's printed-depth join (read-only consumer).

Requirement (2026-11-14): "Track the depth of the replacement, not just the fact of a replacement."

The cfdd desk (session arena/cfdd5580-own7) already joined the Week 10 official injury report to
club-printed depth charts and published, per matched row, the injured player's printed rank and
the named next-in-line with that player's printed rank. This desk consumes that artifact
READ-ONLY — no cell is edited, no club chart is re-captured — and publishes what it implies:

  * the distribution of replacement depth: for each unit (offence / defence / special teams),
    how many starter losses (printed rank 1) have a named backup and at which printed rank that
    backup sits, i.e. how deep the club must reach;
  * the same for injuries deeper on the chart (rank 2+), which are replacements of backups;
  * per-club counts of matched rows, named-replacement rows, and the deepest slot touched;
  * a spot re-verification: for a fixed sample of rows, the injured player's name and the named
    replacement are re-found verbatim in the capturing session's saved evidence files. Rows that
    cannot be traced from this desk are reported as such (a read-only limitation), never hidden.

Rows where the club printed no backup behind the injured player (slot_has_backup = no) are the
"no named replacement" class — tracked as their own depth state, because "no backup printed"
is itself depth information. Nothing is inferred to fill a missing name.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
for _p in (str(HERE), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

JOIN = REPO / "nfl-skill-cfdd" / "data" / "depletion-join-2026-11-14.csv"
SUMMARY = REPO / "nfl-skill-cfdd" / "data" / "depth-summary-2026-11-14.json"

# Evidence roots searched for the spot re-verification, with the clubs each covers.
EVIDENCE_ROOTS = {
    "nfl-availability-28ef/evidence": "ATL BUF CAR CIN DAL GB HOU IND JAX KC LAC LAR LV MIN NO NYJ SF TEN",
    "nfl-skill-cfdd/evidence": "CHI DEN PHI TB",
}
DEPTH_CSV_ROOTS = {
    "nfl-assurance-9580ac3f/data/depth.csv": "NE DET NYG SEA BAL MIA CLE AZ WAS PIT",
}
INJURY_CSV_ROOTS = {
    "nfl-assurance-9580ac3f/data/injuries.csv": "WEEK 10 injury ledger (assurance desk)",
}

SPOT_SAMPLE = 12  # fixed sample size, deterministic selection below


def load_join() -> list[dict]:
    with JOIN.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("cfdd depletion join is empty")
    return rows


def _depth_state(row: dict) -> str:
    if row["on_printed_chart"] != "yes":
        return "not on printed chart"
    if row["slot_has_backup"] != "yes":
        return "no named backup printed"
    return "named backup printed"


def _depth_step(row: dict) -> int | None:
    if _depth_state(row) != "named backup printed":
        return None
    try:
        starter = int(row["printed_rank"])
        backup = int(row["next_in_line_rank"])
    except ValueError:
        return None
    return backup - starter


def distribution(rows: list[dict]) -> list[dict]:
    """Depth-of-replacement distribution by unit and depth step, with n per cell."""
    cells: dict[tuple[str, str], int] = {}
    for row in rows:
        unit = row["printed_unit"] or "unprinted"
        step = _depth_step(row)
        step_label = "reaches printed rank +%d" % step if step is not None else _depth_state(row)
        cells[(unit, step_label)] = cells.get((unit, step_label), 0) + 1
    return [{"unit": unit, "depth_state": label, "n": n}
            for (unit, label), n in sorted(cells.items())]


def starter_losses(rows: list[dict]) -> list[dict]:
    """Starter losses (printed rank 1) and how deep the club reaches for the replacement."""
    out = []
    for row in rows:
        if row["on_printed_chart"] != "yes" or row["printed_rank"] != "1":
            continue
        out.append({
            "injury_id": row["injury_id"],
            "club": row["club_abbr"],
            "player": row["player"],
            "position": row["printed_position"],
            "unit": row["printed_unit"] or "unprinted",
            "replacement": row["next_in_line"] or None,
            "replacement_rank": row["next_in_line_rank"] or None,
            "slot_has_backup": row["slot_has_backup"] == "yes",
            "injury_source_url": row["injury_source_url"],
            "depth_source_url": row["depth_source_url"],
        })
    return out


def per_club(rows: list[dict]) -> list[dict]:
    clubs = {}
    for row in rows:
        c = clubs.setdefault(row["club_abbr"], {
            "club": row["club_abbr"], "name": row["club_name"], "injury_rows": 0,
            "on_chart": 0, "named_backup": 0, "starter_losses": 0, "deepest_slot": None})
        c["injury_rows"] += 1
        if row["on_printed_chart"] == "yes":
            c["on_chart"] += 1
            if row["slot_has_backup"] == "yes":
                c["named_backup"] += 1
            if row["printed_rank"] == "1":
                c["starter_losses"] += 1
            try:
                deepest = int(row["slot_deepest_rank"])
            except ValueError:
                deepest = None
            if deepest is not None:
                c["deepest_slot"] = max(c["deepest_slot"] or 0, deepest)
    return [clubs[k] for k in sorted(clubs)]


def _club_files(club: str) -> list[Path]:
    hits = []
    for rel, clubs in EVIDENCE_ROOTS.items():
        if club in clubs.split():
            folder = REPO / rel
            hits.extend(sorted(folder.glob(f"depth-{club}*.md")))
    for rel, clubs in DEPTH_CSV_ROOTS.items():
        if club in clubs.split():
            hits.append(REPO / rel)
    return hits


def spot_verify(rows: list[dict]) -> dict:
    """Deterministic spot sample: re-find player and replacement in saved evidence text."""
    traceable = [r for r in rows if r["on_printed_chart"] == "yes" and r["slot_has_backup"] == "yes"]
    step = max(1, len(traceable) // SPOT_SAMPLE)
    sample = traceable[::step][:SPOT_SAMPLE]
    results = []
    for row in sample:
        player, replacement = row["player"], row["next_in_line"]
        club = row["club_abbr"]
        found_player, found_replacement = False, False
        searched = []
        for path in _club_files(club):
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            searched.append(str(path.relative_to(REPO)))
            if player and player in text:
                found_player = True
            if replacement and replacement in text:
                found_replacement = True
        results.append({
            "injury_id": row["injury_id"], "club": club, "player": player,
            "replacement": replacement,
            "player_traced": found_player,
            "replacement_traced": found_replacement,
            "searched": searched,
            "status": ("PASS" if found_player and found_replacement else
                       "NOT TRACED from this desk (read-only pass; no failure asserted against "
                       "the capturing session)"),
        })
    return {"sample_size": len(sample), "results": results,
            "pass": sum(1 for r in results if r["status"] == "PASS"),
            "not_traced": sum(1 for r in results if r["status"] != "PASS")}


def build() -> dict:
    rows = load_join()
    import json
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    starters = starter_losses(rows)
    named = [s for s in starters if s["slot_has_backup"]]
    return {
        "schema_version": 1,
        "consumed_artifact": str(JOIN.relative_to(REPO)),
        "consumed_summary": str(SUMMARY.relative_to(REPO)),
        "read_only": True,
        "cfdd_scope_note": (
            "The cfdd desk joined 326 Week 10 injury rows to printed club charts for 31 of 32 "
            "clubs (Houston's chart renders as an image and was not obtained). This desk "
            "republishes the replacement-depth view of that join and edits nothing."),
        "cfdd_summary": {"total_printed_slots": summary.get("total_printed_slots"),
                         "clubs_captured": summary.get("clubs_captured")},
        "counts": {
            "injury_rows": len(rows),
            "on_printed_chart": sum(1 for r in rows if r["on_printed_chart"] == "yes"),
            "named_backup": sum(1 for r in rows if _depth_state(r) == "named backup printed"),
            "no_named_backup": sum(1 for r in rows if _depth_state(r) == "no named backup printed"),
            "not_on_chart": sum(1 for r in rows if _depth_state(r) == "not on printed chart"),
            "starter_losses": len(starters),
            "starter_losses_with_named_backup": len(named),
        },
        "distribution": distribution(rows),
        "starter_losses": starters,
        "per_club": per_club(rows),
        "spot_verification": spot_verify(rows),
        "source_ids": ["X28-NFL-INJ-W10", "CFDD-NFL-STANDINGS", "REPO"],
    }
