#!/usr/bin/env python3
"""Join the official injury report to the printed depth charts.

This answers one question only: when the league lists a player Out / Doubtful / Questionable, what
does the club's own printed chart say about who is behind him? Every cell is either printed by an
official source or blank. No performance deficit, snap count, point value or probability is
produced - that would be an invention.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from depth import norm_name

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

RANK_LABELS = {1: "1st string (printed starter)", 2: "2nd string", 3: "3rd string",
               4: "4th string", 5: "5th string"}


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise SystemExit(f"refusing to write an empty table: {path}")
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_index(slots):
    """club -> normalised player name -> list of slots."""
    index: dict[str, dict[str, list[dict]]] = {}
    for row in slots:
        if not row["player"]:
            continue
        club = index.setdefault(row["club_abbr"], {})
        for name in row["player"].split(" / "):
            club.setdefault(norm_name(name), []).append(row)
    return index


def chain_for(slots, slot_row):
    """Ordered printed names of the one chain the slot belongs to."""
    rows = [r for r in slots
            if r["club_abbr"] == slot_row["club_abbr"] and r["unit"] == slot_row["unit"]
            and r["position"] == slot_row["position"] and r["slot"] == slot_row["slot"]]
    rows.sort(key=lambda r: int(r["rank"]))
    return rows


def main() -> None:
    injuries = load_csv(DATA / "injuries-week10-2026.csv")
    slots = load_csv(DATA / "depth-slots-week10-2026.csv")
    index = build_index(slots)
    clubs_with_chart = {r["club_abbr"] for r in slots}

    # who is ruled Out, per club, for the "next man is also out" test
    out_by_club: dict[str, set[str]] = {}
    for row in injuries:
        if row["game_status"] == "Out":
            out_by_club.setdefault(row["club_abbr"], set()).add(norm_name(row["player"]))

    rows = []
    for inj in injuries:
        club = inj["club_abbr"]
        key = norm_name(inj["player"])
        matches = index.get(club, {}).get(key, [])
        base = {
            "injury_id": inj["injury_id"],
            "club_abbr": club,
            "club_name": inj["club_name"],
            "player": inj["player"],
            "position_reported": inj["position"],
            "injury_listed": inj["injury"],
            "practice_status": inj["practice_status"],
            "game_status": inj["game_status"],
            "injury_source_url": inj["source_url"],
            "injury_checked_on": inj["checked_on"],
        }
        if club not in clubs_with_chart:
            rows.append({
                **base,
                "chart_available": "no - no printed depth chart obtained for this club",
                "unit": "", "position_on_chart": "", "depth_rank": "", "depth_rank_label": "",
                "printed_chain": "", "next_in_line": "", "next_in_line_rank": "",
                "backups_also_out": "", "classification":
                    "no printed depth chart obtained for this club; rank and replacement blank",
                "depth_source_url": "", "depth_checked_on": "", "evidence_file": "",
            })
            continue
        if not matches:
            rows.append({
                **base,
                "chart_available": "yes",
                "unit": "", "position_on_chart": "", "depth_rank": "", "depth_rank_label": "",
                "printed_chain": "", "next_in_line": "", "next_in_line_rank": "",
                "backups_also_out": "",
                "classification": "listed on the injury report but not named on the club's printed chart",
                "depth_source_url": "", "depth_checked_on": "",
                "evidence_file": "nfl-availability-28ef/data/depth-slots-week10-2026.csv",
            })
            continue

        slot_row = matches[0]
        chain = chain_for(slots, slot_row)
        chain_names = [c["player"] for c in chain if c["player"]]
        rank = int(slot_row["rank"])
        skipped = []
        next_name, next_rank = "", ""
        for cand in chain:
            if int(cand["rank"]) <= rank:
                continue
            if not cand["player"]:
                continue
            names = [n for n in cand["player"].split(" / ")]
            if all(norm_name(n) in out_by_club.get(club, set()) for n in names):
                skipped.append(cand["player"])
                continue
            next_name, next_rank = cand["player"], cand["rank"]
            break

        if inj["game_status"] == "Out":
            if rank == 1:
                classification = "starter ruled out"
                if next_name:
                    classification += f" - {RANK_LABELS.get(int(next_rank), next_rank + 'th string')} in line"
                else:
                    classification += " - no further name printed in this chain"
                if skipped:
                    classification += f"; also out behind him: {' / '.join(skipped)}"
            else:
                classification = f"{RANK_LABELS.get(rank, str(rank) + 'th string')} ruled out"
                if next_name:
                    classification += f" - {RANK_LABELS.get(int(next_rank), next_rank + 'th string')} in line"
        elif inj["game_status"] in ("Questionable", "Doubtful"):
            classification = (f"{RANK_LABELS.get(rank, str(rank) + 'th string')} "
                               f"{inj['game_status'].lower()} - not ruled out")
        else:
            classification = (f"{RANK_LABELS.get(rank, str(rank) + 'th string')} on the injury report "
                               f"with no game status published")

        rows.append({
            **base,
            "chart_available": "yes",
            "unit": slot_row["unit"],
            "position_on_chart": slot_row["position"],
            "depth_rank": str(rank),
            "depth_rank_label": RANK_LABELS.get(rank, f"{rank}th string"),
            "printed_chain": " -> ".join(chain_names),
            "next_in_line": next_name,
            "next_in_line_rank": next_rank,
            "backups_also_out": " / ".join(skipped),
            "classification": classification,
            "depth_source_url": slot_row["source_url"],
            "depth_checked_on": slot_row["checked_on"],
            "evidence_file": slot_row["evidence_file"],
        })

    ordered = ["injury_id", "club_abbr", "club_name", "player", "position_reported",
               "injury_listed", "practice_status", "game_status", "chart_available", "unit",
               "position_on_chart", "depth_rank", "depth_rank_label", "printed_chain",
               "next_in_line", "next_in_line_rank", "backups_also_out", "classification",
               "injury_source_url", "injury_checked_on", "depth_source_url", "depth_checked_on",
               "evidence_file"]
    rows = [{k: r[k] for k in ordered} for r in rows]
    write_csv(DATA / "depletion-week10-2026.csv", rows)

    # ---- per-club summary -------------------------------------------------
    chart_date = {}
    chart_url = {}
    for row in slots:
        chart_date.setdefault(row["club_abbr"], row["checked_on"])
        chart_url.setdefault(row["club_abbr"], row["source_url"])

    summary = []
    for club in sorted({r["club_abbr"] for r in rows}):
        club_rows = [r for r in rows if r["club_abbr"] == club]
        def count(**kw):
            return sum(1 for r in club_rows
                       if all(getattr_match(r, k, v) for k, v in kw.items()))
        summary.append({
            "club_abbr": club,
            "club_name": club_rows[0]["club_name"],
            "chart_available": "yes" if club in clubs_with_chart else "no",
            "chart_checked_on": chart_date.get(club, ""),
            "chart_source_url": chart_url.get(club, ""),
            "injury_rows": len(club_rows),
            "ruled_out": sum(1 for r in club_rows if r["game_status"] == "Out"),
            "questionable": sum(1 for r in club_rows if r["game_status"] == "Questionable"),
            "doubtful": sum(1 for r in club_rows if r["game_status"] == "Doubtful"),
            "blank_game_status": sum(1 for r in club_rows if r["game_status"] == ""),
            "starters_ruled_out": sum(1 for r in club_rows
                                      if r["game_status"] == "Out" and r["depth_rank"] == "1"),
            "defence_ruled_out": sum(1 for r in club_rows
                                     if r["game_status"] == "Out" and r["unit"] == "Defense"),
            "offence_ruled_out": sum(1 for r in club_rows
                                     if r["game_status"] == "Out" and r["unit"] == "Offense"),
            "special_teams_ruled_out": sum(1 for r in club_rows
                                           if r["game_status"] == "Out" and r["unit"] == "Special Teams"),
            "not_named_on_chart": sum(1 for r in club_rows
                                      if r["chart_available"] == "yes" and not r["depth_rank"]),
        })
    write_csv(DATA / "club-summary-week10-2026.csv", summary)

    flagged = [r for r in rows if r["game_status"] in ("Out", "Doubtful", "Questionable")
               and r["depth_rank"] == "1"]
    stats = {
        "injury_rows": len(rows),
        "clubs_on_report": len({r["club_abbr"] for r in rows}),
        "clubs_with_chart": len(clubs_with_chart),
        "matched_to_chart": sum(1 for r in rows if r["depth_rank"]),
        "matched_but_unnamed": sum(1 for r in rows
                                   if r["chart_available"] == "yes" and not r["depth_rank"]),
        "no_chart": sum(1 for r in rows if r["chart_available"] != "yes"),
        "starters_with_status": len(flagged),
        "starters_ruled_out": sum(1 for r in rows
                                  if r["game_status"] == "Out" and r["depth_rank"] == "1"),
        "starters_questionable": sum(1 for r in rows
                                     if r["game_status"] == "Questionable" and r["depth_rank"] == "1"),
        "defence_starters_out": sum(1 for r in rows if r["game_status"] == "Out"
                                    and r["depth_rank"] == "1" and r["unit"] == "Defense"),
        "offence_starters_out": sum(1 for r in rows if r["game_status"] == "Out"
                                    and r["depth_rank"] == "1" and r["unit"] == "Offense"),
        "second_string_in_line_for_out_starter": sum(
            1 for r in rows if r["game_status"] == "Out" and r["depth_rank"] == "1"
            and r["next_in_line_rank"] == "2"),
        "third_or_deeper_in_line_for_out_starter": sum(
            1 for r in rows if r["game_status"] == "Out" and r["depth_rank"] == "1"
            and r["next_in_line_rank"] not in ("", "2")),
        "no_name_printed_behind_out_starter": sum(
            1 for r in rows if r["game_status"] == "Out" and r["depth_rank"] == "1"
            and not r["next_in_line"]),
    }
    (DATA / "depletion-summary.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))


def getattr_match(row, key, value) -> bool:
    return row.get(key) == value


if __name__ == "__main__":
    main()
