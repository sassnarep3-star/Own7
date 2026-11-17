"""The injury and depth desk: what the league states, and how deep each club must reach.

The user's requirement is specific - know when a second, third or fourth string player
has to replace a starter, on defence and on offence alike. This module answers exactly
that, and states just as precisely where it cannot answer it:

  * a replacement is only implied where the league prints a game status;
  * a club with no captured chart has no printed ranks, so no depth can be computed;
  * a chart with no printed date cannot be shown to be current.

Every row links to the official injury report and to the official club depth chart it
was read from.
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, ROOT, check_artifact, read_csv, round_value, write_csv  # noqa: E402

OUT = DATA / "injuries.json"
INJURIES = ROOT / "nfl-availability-28ef" / "data" / "injuries-week10-2026.csv"
DEPTH = DATA / "depth.json"

UNIT_LABEL = {"Offense": "Offence", "Defense": "Defence", "Special Teams": "Special teams"}


def build():
    injuries = read_csv(INJURIES)
    depth = Path(DEPTH).read_text(encoding="utf-8")
    import json
    depth = json.loads(depth)

    status_counts = Counter((r.get("game_status") or "(none printed)") for r in injuries)
    practice_counts = Counter(r.get("practice_status") for r in injuries)

    # Rows the league does not give a game status for. Listed per club so a reader can
    # see how much of each club's list is unusable for a replacement calculation.
    no_status = defaultdict(int)
    for row in injuries:
        if not (row.get("game_status") or "").strip():
            no_status[row["club_abbr"]] += 1

    deficiencies = []
    for row in depth["slots"]:
        if row["tier"] != "out" or not row["starter_unavailable"]:
            continue
        deficiencies.append({
            "club": row["club"],
            "unit": row["unit"], "unit_label": UNIT_LABEL.get(row["unit"], row["unit"]),
            "position": row["position"], "slot": row["slot"],
            "game_status": "Out",
            "replacement_depth": row["replacement_depth"],
            "depth_label": {2: "Second string", 3: "Third string",
                            4: "Fourth string"}.get(row["replacement_depth"],
                                                    "Fifth string or deeper"
                                                    if (row["replacement_depth"] or 0) >= 5
                                                    else None),
            "replacement_player": row["replacement_player"],
            "reach": row["reach"],
            "slot_exhausted": row["slot_exhausted"],
            "no_backup_printed": row["no_backup_printed"],
            "depth_source_url": row["source_url"],
            "depth_checked_on": row["checked_on"],
            "injury_source_url": "https://www.nfl.com/injuries/league/2026/REG10",
        })
    deficiencies.sort(key=lambda r: (r["club"], r["unit_label"], r["position"]))

    by_club_unit = defaultdict(lambda: defaultdict(int))
    for row in deficiencies:
        if row["replacement_depth"]:
            by_club_unit[row["club"]][row["unit_label"]] += 1

    club_rows = []
    for row in depth["club_rollup"]:
        club_rows.append({
            "club": row["club"],
            "injury_rows": row["injury_rows"],
            "rows_with_game_status": row["rows_with_official_game_status"],
            "rows_without_game_status": no_status.get(row["club"], 0),
            "ruled_out": row["rows_ruled_out"],
            "questionable": row["rows_questionable"],
            "defence_replacements": by_club_unit[row["club"]]["Defence"],
            "offence_replacements": by_club_unit[row["club"]]["Offence"],
            "special_teams_replacements": by_club_unit[row["club"]]["Special teams"],
            "deepest_reach": row["deepest_reach"],
            "slots_with_no_printed_replacement": row["slots_with_no_printed_replacement"],
            "printed_slots_captured": row["printed_slots_captured"],
            "note": row["note"],
        })

    write_csv(DATA / "deficiencies.csv", deficiencies)
    write_csv(DATA / "club-injury-depth.csv", club_rows)

    payload = {
        "built_on": "2026-11-14",
        "scope": "Week 10 2026 official injury report joined to each club's own printed "
                 "depth chart.",
        "sources": {
            "injury_report": "https://www.nfl.com/injuries/league/2026/REG10",
            "injury_source_id": "CP-NFL-INJ-W10",
            "depth_charts": "31 club depth charts; Houston renders none",
            "depth_source_ids": ["CP-NFL-DEPTH-27", "CP-NFL-DEPTH-BYE4"],
        },
        "status_coverage": {
            "rows": len(injuries),
            "by_game_status": {k: v for k, v in sorted(status_counts.items())},
            "by_practice_status": {k: v for k, v in sorted(practice_counts.items())},
            "ceiling": "A replacement is implied only where the league prints a game "
                       "status. It prints one on "
                       f"{sum(v for k, v in status_counts.items() if k != '(none printed)')} "
                       f"of {len(injuries)} rows.",
        },
        "deficiency_counts": {
            "slots_needing_a_replacement": len(deficiencies),
            "offence": sum(1 for r in deficiencies if r["unit"] == "Offense"),
            "defence": sum(1 for r in deficiencies if r["unit"] == "Defense"),
            "special_teams": sum(1 for r in deficiencies if r["unit"] == "Special Teams"),
            "second_string": sum(1 for r in deficiencies if r["replacement_depth"] == 2),
            "third_string": sum(1 for r in deficiencies if r["replacement_depth"] == 3),
            "fourth_or_deeper": sum(1 for r in deficiencies
                                    if (r["replacement_depth"] or 0) >= 4),
            "no_printed_replacement": sum(1 for r in deficiencies if r["slot_exhausted"]),
        },
        "deficiencies": deficiencies,
        "club_rows": club_rows,
        "limits": [
            "A printed rank is an ordering, not a measurement of how good the "
            "replacement is. No point value, probability or line adjustment is produced "
            "from one, because no snap count, target share or performance log was "
            "retrieved to justify it.",
            "The league prints a game status on a minority of rows, so this table is a "
            "floor on each club's depletion, not a complete count.",
            "Houston's chart renders as an image on its club site, so Houston has no "
            "printed ranks and its depth is blank rather than guessed.",
            "Chicago's chart is dated 10/31/2026, before the ledger it is joined to; "
            "Denver, Philadelphia and Tampa print no date; Philadelphia's chart is "
            "self-labelled unofficial.",
        ],
    }
    return round_value(payload, 6)


def main():
    if check_artifact(OUT, build()):
        payload = build()
        counts = payload["deficiency_counts"]
        print(f"  {counts['slots_needing_a_replacement']} slots need a replacement: "
              f"{counts['offence']} offence, {counts['defence']} defence, "
              f"{counts['special_teams']} special teams; "
              f"{counts['second_string']} from 2nd string, "
              f"{counts['third_string']} from 3rd, "
              f"{counts['no_printed_replacement']} with none printed")


if __name__ == "__main__":
    main()
