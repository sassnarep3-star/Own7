"""Depth of the replacement, not just the fact of one.

THE POINT
---------
"Starter out" is one bit of information. "Starter out, and the printed chart has
three names behind him, and the fourth-string player is now the last man at the
position" is a completely different risk. This module measures the second thing.

For every injury row that could be matched to a club's printed depth chart, it
records the DEPTH OF THE REPLACEMENT:

    replaced_rank        1 = the printed starter is the one on the report
    replacement_rank     the rank that now steps in (2nd/3rd/4th string)
    slot_deepest_rank    how many printed names the position has in total
    remaining_depth      how many printed names sit behind the replacement
    loses_one_deep       no printed name behind the replacement at all
    unit                 Offense / Defense / Special Teams, kept separate

A club that loses a starter at a position printed four deep is in a far better
place than a club that loses a starter at a position printed two deep. Both are
"one starter out"; only the first number tells you which.

WHAT THIS IS NOT
----------------
It is not a point value, a probability or a line adjustment. It is a count of
printed slots with the weights shown in `DEPTH_POINTS`. Nothing here is fitted to
outcomes, because there are 136 games and eight of those per club: far too few to
fit an injury coefficient honestly. Publishing a fitted weight now would be the
same overfitting the leaderboard is built to catch.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
# Two slot files exist and they do NOT overlap: the week-10 capture holds 27
# clubs, and the four Week-10 bye clubs (CHI, DEN, PHI, TB) were captured later
# into a second file. Reading only the first silently drops four clubs, which is
# exactly the error this session found and records as PD01.
SLOT_SOURCES = [
    (ROOT / "nfl-availability-28ef" / "data" / "depth-slots-week10-2026.csv",
     "NFL-AVAIL-DEPTH-W10"),
    (ROOT / "nfl-skill-cfdd" / "data" / "depth-slots-2026-11-14.csv",
     "CFDD-DEPTH-2026-11-14"),
]
JOIN = ROOT / "nfl-skill-cfdd" / "data" / "depletion-join-2026-11-14.csv"
OUT = HERE / "data" / "depth.json"

# Points are a RANK WEIGHT for ordering only. Stated here, not fitted.
DEPTH_POINTS = {1: 3.0, 2: 2.0, 3: 1.25, 4: 0.75, 5: 0.5, 6: 0.25}
UNIT_ORDER = ["Offense", "Defense", "Special Teams"]


def slot_weight(rank: int) -> float:
    return DEPTH_POINTS.get(rank, 0.0)


def build() -> dict:
    slots = []
    slot_origin = {}
    for path, source_id in SLOT_SOURCES:
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                row["_source_id"] = source_id
                row["_file"] = str(path.relative_to(ROOT))
                slots.append(row)
                slot_origin[row["club_abbr"]] = source_id
    joins = list(csv.DictReader(JOIN.open(newline="", encoding="utf-8")))

    # --- printed depth per (club, unit, position) ---------------------------
    depth: dict[tuple[str, str, str], dict[int, str]] = defaultdict(dict)
    slot_sources: dict[str, str] = {}
    for slot in slots:
        key = (slot["club_abbr"], slot["unit"], slot["position"])
        depth[key][int(slot["rank"])] = slot["player"]
        slot_sources[slot["club_abbr"]] = slot["source_url"]

    clubs = sorted({s["club_abbr"] for s in slots})
    units_present = [u for u in UNIT_ORDER if any(s["unit"] == u for s in slots)]

    # --- per injury row, the depth of the replacement -----------------------
    replacements = []
    unmatched = 0
    for row in joins:
        rank = row["printed_rank"]
        if not rank.isdigit():
            unmatched += 1
            continue
        rank = int(rank)
        key = (row["club_abbr"], row["printed_unit"], row["printed_position"])
        chain = depth.get(key, {})
        deepest = max(chain) if chain else rank
        # The next printed name below the injured player, if there is one.
        below = sorted(r for r in chain if r > rank)
        replacement_rank = below[0] if below else None
        remaining = len([r for r in below[1:]]) if below else 0
        replaces = row.get("next_in_line") or (chain.get(replacement_rank) if replacement_rank else "")
        replacements.append({
            "injury_id": row["injury_id"],
            "club": row["club_abbr"],
            "club_name": row["club_name"],
            "player": row["player"],
            "unit": row["printed_unit"],
            "position": row["printed_position"],
            "replaced_rank": rank,
            "replacement_rank": replacement_rank,
            "replacement_player": replaces,
            "slot_deepest_rank": deepest,
            "remaining_depth_behind_replacement": remaining,
            "loses_last_printed_name": replacement_rank is None,
            "slot_source": slot_origin.get(row["club_abbr"]),
            "loses_one_deep": replacement_rank is not None and replacement_rank == deepest,
            "depth_points": slot_weight(rank),
            "injury_source_url": row["injury_source_url"],
            "depth_source_url": row["depth_source_url"],
        })

    # --- per club aggregation, offence and defence never mixed --------------
    per_club = []
    for club in clubs:
        rows = [r for r in replacements if r["club"] == club]
        entry = {
            "club": club,
            "printed_slots": sum(1 for s in slots if s["club_abbr"] == club),
            "depth_source_url": slot_sources.get(club),
            "slot_source": slot_origin.get(club),
            "on_report": len(rows),
            "by_unit": {},
        }
        for unit in units_present:
            unit_rows = [r for r in rows if r["unit"] == unit]
            starters = [r for r in unit_rows if r["replaced_rank"] == 1]
            one_deep = [r for r in unit_rows if r["loses_one_deep"]]
            entry["by_unit"][unit] = {
                "on_report": len(unit_rows),
                "starters_on_report": len(starters),
                "replacement_is_last_printed_name": len(one_deep),
                "depth_points": round(sum(r["depth_points"] for r in unit_rows), 2),
                "mean_replacement_rank": (
                    round(sum(r["replacement_rank"] for r in unit_rows
                              if r["replacement_rank"] is not None) /
                          max(1, len([r for r in unit_rows if r["replacement_rank"] is not None])), 2)
                    if any(r["replacement_rank"] is not None for r in unit_rows) else None
                ),
            }
        entry["total_depth_points"] = round(
            sum(v["depth_points"] for v in entry["by_unit"].values()), 2
        )
        entry["thinnest_positions"] = [
            {
                "unit": r["unit"],
                "position": r["position"],
                "printed_depth": r["slot_deepest_rank"],
                "injured": r["player"],
                "replacement": r["replacement_player"] or None,
            }
            for r in rows
            if r["loses_one_deep"] or r["loses_last_printed_name"]
        ][:6]
        per_club.append(entry)

    per_club.sort(key=lambda c: -c["total_depth_points"])

    flagged = [r for r in replacements if r["loses_last_printed_name"]]
    one_deep = [r for r in replacements if r["loses_one_deep"]]

    return {
        "schema_version": 1,
        "question": "How deep is the replacement, not merely that there is one?",
        "not_a_point_value": (
            "depth_points is an ordering weight for printed slots. It is not a points estimate, "
            "a probability or a line adjustment, and it is not fitted to results."
        ),
        "rank_weight": {str(k): v for k, v in DEPTH_POINTS.items()},
        "units_kept_separate": units_present,
        "slot_sources": [
            {"id": sid, "file": str(path.relative_to(ROOT)),
             "clubs": sorted({r["club_abbr"] for r in slots if r["_source_id"] == sid})}
            for path, sid in SLOT_SOURCES
        ],
        "counts": {
            "clubs_with_printed_chart": len(clubs),
            "printed_slots": len(slots),
            "injury_rows": len(joins),
            "injury_rows_matched_to_a_printed_slot": len(replacements),
            "injury_rows_on_a_ranked_slot": len(replacements),
            "injury_rows_unmatched": unmatched,
            "replacements_at_the_last_printed_name": len(one_deep),
            "replacements_with_no_one_behind_them": len(flagged),
            "offence_rows": sum(1 for r in replacements if r["unit"] == "Offense"),
            "defence_rows": sum(1 for r in replacements if r["unit"] == "Defense"),
            "special_teams_rows": sum(1 for r in replacements if r["unit"] == "Special Teams"),
        },
        "sources": {
            "depth": {
                "id": "CLUB-DEPTH-2026",
                "url_pattern": "https://www.<club>.com/team/depth-chart",
                "note": "One official club page per club; every slot row carries its own club URL.",
            },
            "injury": {
                "id": "NFL-INJURY-W10",
                "url": "https://www.nfl.com/injuries/league/2026/REG10",
            },
        },
        "limitations": [
            "A printed chart is a club publication, not a confirmed starting lineup.",
            "Only Week 10 has a captured chart; earlier weeks have no printed depth to measure.",
            "Nine clubs publish no game status, so 'out' and 'questionable' are not separated everywhere.",
            "Position labels on the report and on the chart differ; the mapping is published separately.",
        ],
        "clubs": per_club,
        "replacements": replacements,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build()
    text = json.dumps(result, indent=1) + "\n"
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print("FAIL: data/depth.json is stale; run python depth.py")
            return 1
        print(f"OK: depth reproduces ({result['counts']['injury_rows_matched_to_a_printed_slot']} rows)")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    c = result["counts"]
    print(
        f"Wrote {OUT.relative_to(ROOT)} — {c['printed_slots']} printed slots, "
        f"{c['injury_rows_matched_to_a_printed_slot']} matched, "
        f"{c['replacements_with_no_one_behind_them']} with no one behind"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
