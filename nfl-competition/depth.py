"""Requirement 6 — track the depth of the replacement, not just the fact of one.

"The starter is out" is one bit. What matters to a projection is how far down its own
printed chart a club has to reach: a second-string replacement is a different problem
from a fourth-string one, and a slot with no printed name behind the starter is different
again. So this module computes, for every slot on every captured depth chart:

    unavailable ranks   the printed ranks the official report rules out
    replacement depth   the printed rank of the first name in that slot who is available
    reach               replacement depth minus one: how many names the club goes past
    exhausted           every printed name in the slot is ruled out, so no replacement
                        is printed at all

Three availability tiers are handled separately and never mixed, because the league
prints them with different authority:

    Out                 the official game status. This is the only tier that states a
                        player will not play.
    Questionable        the official game status. Stated as a risk, not an absence.
    Did not practise    a practice status only. Published separately and labelled as a
                        weaker signal, because the league does not print a game status
                        for these players at all.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, ROOT, check_artifact, read_csv, round_value, write_csv  # noqa: E402

OUT = DATA / "depth.json"
DEPTH_A = ROOT / "nfl-availability-28ef" / "data" / "depth-slots-week10-2026.csv"
DEPTH_B = ROOT / "nfl-skill-cfdd" / "data" / "depth-slots-2026-11-14.csv"
JOIN = ROOT / "nfl-skill-cfdd" / "data" / "depletion-join-2026-11-14.csv"
INJURIES = ROOT / "nfl-availability-28ef" / "data" / "injuries-week10-2026.csv"

# The four clubs on bye in Week 10 have no injury row, because the league publishes
# none for a club that is not playing. They are still listed so the table covers all 32.
BYE_CLUBS = {"CHI", "DEN", "PHI", "TB"}

CLUB_NOTES = {
    "CHI": "On bye in Week 10; the league publishes no Week 10 injury row.",
    "DEN": "On bye in Week 10; the league publishes no Week 10 injury row.",
    "PHI": "On bye in Week 10; the league publishes no Week 10 injury row.",
    "TB": "On bye in Week 10; the league publishes no Week 10 injury row.",
    "HOU": "The club site renders its depth chart as an image with no table, on two "
           "independent reads. No printed ranks, so no depth can be computed.",
}

TIERS = [
    {"id": "out", "label": "Official game status: Out",
     "authority": "The league states the player will not play.",
     "source_ids": ["CP-NFL-INJ-W10"]},
    {"id": "questionable", "label": "Official game status: Questionable",
     "authority": "The league states a risk. Not an absence, so the depth below is the "
                  "depth the club would need, not the depth it will use.",
     "source_ids": ["CP-NFL-INJ-W10"]},
    {"id": "dnp", "label": "Did not participate in practice",
     "authority": "A practice status only. The league prints no game status for these "
                  "players, so this tier is a weaker signal and is published separately "
                  "rather than folded into the Out figures.",
     "source_ids": ["CP-NFL-INJ-W10"]},
]

STATUS_TO_TIER = {
    "Out": "out",
    "Doubtful": "out",
    "Questionable": "questionable",
}


def load_charts():
    """(club, unit, position, slot) -> ordered [(rank, player, source_url, checked_on)]."""
    charts = defaultdict(list)
    for path in (DEPTH_A, DEPTH_B):
        for row in read_csv(path):
            key = (row["club_abbr"], row["unit"], row["position"], row["slot"])
            player = (row.get("player") or "").strip()
            if not player:
                continue
            charts[key].append({
                "rank": int(row["rank"]), "player": player,
                "source_url": row["source_url"], "checked_on": row["checked_on"],
                "evidence_file": row.get("evidence_file", ""),
            })
    for roster in charts.values():
        roster.sort(key=lambda entry: entry["rank"])
    return charts


def load_availability():
    """(club, player) -> {tier: True}. From the official report and the printed join."""
    join = read_csv(JOIN)
    availability = defaultdict(dict)
    meta = {}
    for row in join:
        club = row["club_abbr"]
        player = (row["player"] or "").strip()
        if not player:
            continue
        status = (row.get("game_status") or "").strip()
        practice = (row.get("practice_status") or "").strip()
        tier = STATUS_TO_TIER.get(status)
        if tier:
            availability[(club, player)][tier] = True
        if practice.startswith("Did Not Participate"):
            availability[(club, player)]["dnp"] = True
        meta[(club, player)] = {
            "on_printed_chart": row.get("on_printed_chart") == "yes",
            "printed_unit": row.get("printed_unit", ""),
            "printed_position": row.get("printed_position", ""),
            "printed_slot": row.get("printed_slot", ""),
            "printed_rank": row.get("printed_rank", ""),
            "game_status": status,
            "practice_status": practice,
            "injury_source_url": row.get("injury_source_url", ""),
            "depth_source_url": row.get("depth_source_url", ""),
            "injury_checked_on": row.get("injury_checked_on", ""),
            "depth_checked_on": row.get("depth_checked_on", ""),
        }
    return availability, meta


def slot_depth(charts, availability, tier):
    """For every slot, the printed rank of the first name who is available."""
    rows = []
    for (club, unit, position, slot), roster in sorted(charts.items()):
        unavailable = [entry for entry in roster
                       if availability.get((club, entry["player"]), {}).get(tier)]
        if not unavailable:
            continue
        unavailable_ranks = sorted({entry["rank"] for entry in unavailable})
        available = [entry for entry in roster if entry["rank"] not in unavailable_ranks]
        replacement = available[0] if available else None
        deepest = max(entry["rank"] for entry in roster)
        rows.append({
            "club": club, "unit": unit, "position": position, "slot": slot,
            "tier": tier,
            "printed_names": len(roster),
            "unavailable_ranks": ",".join(str(r) for r in unavailable_ranks),
            "unavailable_count": len(unavailable_ranks),
            "starter_unavailable": 1 in unavailable_ranks,
            "replacement_depth": replacement["rank"] if replacement else None,
            "replacement_player": replacement["player"] if replacement else None,
            "reach": (replacement["rank"] - 1) if replacement else None,
            "slot_exhausted": replacement is None,
            "deepest_rank_printed": deepest,
            "no_backup_printed": deepest == 1,
            "source_url": roster[0]["source_url"],
            "checked_on": roster[0]["checked_on"],
        })
    return rows


def player_replacements(charts, availability, meta, slot_rows, tier):
    index = {(row["club"], row["unit"], row["position"], row["slot"]): row
             for row in slot_rows}
    out = []
    for (club, player), info in sorted(meta.items()):
        if not info["on_printed_chart"]:
            continue
        if not availability.get((club, player), {}).get(tier):
            continue
        key = (club, info["printed_unit"], info["printed_position"], info["printed_slot"])
        slot = index.get(key)
        out.append({
            "club": club, "player": player,
            "unit": info["printed_unit"], "position": info["printed_position"],
            "slot": info["printed_slot"],
            "own_rank": int(info["printed_rank"]) if info["printed_rank"] else None,
            "tier": tier, "game_status": info["game_status"] or None,
            "replacement_player": slot["replacement_player"] if slot else None,
            "replacement_depth": slot["replacement_depth"] if slot else None,
            "reach": slot["reach"] if slot else None,
            "slot_exhausted": slot["slot_exhausted"] if slot else None,
            "no_backup_printed": slot["no_backup_printed"] if slot else None,
            "injury_source_url": info["injury_source_url"],
            "depth_source_url": info["depth_source_url"],
        })
    out.sort(key=lambda row: (row["club"], row["own_rank"] or 99, row["position"]))
    return out


def club_rollup(slot_rows, player_rows, join_rows, charts, all_clubs):
    clubs = sorted(all_clubs)
    by_club = defaultdict(list)
    for row in slot_rows:
        by_club[row["club"]].append(row)
    players_by_club = defaultdict(list)
    for row in player_rows:
        players_by_club[row["club"]].append(row)
    join_by_club = defaultdict(list)
    for row in join_rows:
        join_by_club[row["club_abbr"]].append(row)
    out = []
    for club in clubs:
        rows = by_club.get(club, [])
        starters_out = [r for r in rows if r["starter_unavailable"] and r["tier"] == "out"]
        reached = [r["replacement_depth"] for r in starters_out if r["replacement_depth"]]
        exhausted = [r for r in rows if r["slot_exhausted"] and r["tier"] == "out"]
        no_backup = [r for r in rows if r["no_backup_printed"] and r["tier"] == "out"]
        chart_slots = sum(1 for key in charts if key[0] == club)
        out.append({
            "club": club,
            "injury_rows": len(join_by_club.get(club, [])),
            "rows_with_official_game_status": sum(
                1 for r in join_by_club.get(club, [])
                if (r.get("game_status") or "").strip()),
            "rows_ruled_out": sum(1 for r in join_by_club.get(club, [])
                                  if (r.get("game_status") or "").strip() == "Out"),
            "rows_questionable": sum(1 for r in join_by_club.get(club, [])
                                     if (r.get("game_status") or "").strip() == "Questionable"),
            "printed_slots_captured": chart_slots,
            "starters_out_offence": sum(1 for r in starters_out if r["unit"] == "Offense"),
            "starters_out_defence": sum(1 for r in starters_out if r["unit"] == "Defense"),
            "starters_out_special_teams": sum(1 for r in starters_out
                                              if r["unit"] == "Special Teams"),
            "replacements_from_2nd_string": sum(1 for r in reached if r == 2),
            "replacements_from_3rd_string": sum(1 for r in reached if r == 3),
            "replacements_from_4th_string_or_deeper": sum(1 for r in reached if r >= 4),
            "deepest_reach": max(reached) - 1 if reached else None,
            "slots_with_no_printed_replacement": len(exhausted),
            "slots_with_no_backup_printed_at_all": len(no_backup),
            "players_named": len(players_by_club.get(club, [])),
            "note": CLUB_NOTES.get(club, ""),
        })
    return out


def build():
    charts = load_charts()
    availability, meta = load_availability()
    join_rows = read_csv(JOIN)
    injuries = read_csv(INJURIES)

    all_slots, all_players = [], []
    for tier in TIERS:
        slots = slot_depth(charts, availability, tier["id"])
        all_slots.extend(slots)
        all_players.extend(player_replacements(charts, availability, meta, slots,
                                               tier["id"]))

    write_csv(DATA / "replacement-depth-by-slot.csv", all_slots)
    write_csv(DATA / "replacement-depth-by-player.csv", all_players)

    out_slots = [r for r in all_slots if r["tier"] == "out"]
    out_players = [r for r in all_players if r["tier"] == "out"]
    # A "starter ruled out" is a first-string name on a printed chart carrying the
    # official Out status. Backups ruled out are counted separately, because a club
    # losing its second string loses depth, not its starter.
    starters = [r for r in out_players if r["own_rank"] == 1]
    all_clubs = ({r["club"] for r in all_slots} | {r["club_abbr"] for r in join_rows} |
                 {key[0] for key in charts} | BYE_CLUBS | {"HOU"})
    rollup = club_rollup(all_slots, all_players, join_rows, charts, all_clubs)
    write_csv(DATA / "club-replacement-depth.csv", rollup)

    no_status = sum(1 for r in join_rows if not (r.get("game_status") or "").strip())
    payload = {
        "requirement": "R6 - depth of the replacement, not just the fact of one",
        "built_on": "2026-11-14",
        "definitions": {
            "replacement_depth": "The printed rank, on the club's own depth chart, of the "
                                 "first name in the slot who is not ruled out. 2 means a "
                                 "second-string player steps in; 3 means a third-string "
                                 "player; and so on.",
            "reach": "replacement_depth - 1. How many printed names the club must go "
                     "past.",
            "slot_exhausted": "Every printed name in the slot is ruled out, so no "
                              "replacement is printed. Published blank and flagged, "
                              "never filled with a guess.",
            "no_backup_printed": "The club prints one name in the slot and no one behind "
                                 "him.",
        },
        "tiers": TIERS,
        "coverage": {
            "injury_rows": len(join_rows),
            "rows_with_an_official_game_status": len(join_rows) - no_status,
            "rows_without_an_official_game_status": no_status,
            "why_that_ceiling_matters": "A replacement is only implied where the league "
                                        "prints a game status. For the other rows the "
                                        "report states a practice status and no game "
                                        "status, so no replacement is implied and no "
                                        "depth is computed.",
            "clubs_with_a_captured_chart": len({key[0] for key in charts}),
            "clubs_without_a_captured_chart": sorted(
                {r["club_abbr"] for r in join_rows} - {key[0] for key in charts}),
            "printed_slots": sum(len(v) for v in charts.values()),
        },
        "headline": {
            "starters_ruled_out": len(starters),
            "non_starters_ruled_out": len(out_players) - len(starters),
            "replacements_from_2nd_string": sum(1 for r in out_slots
                                                if r["starter_unavailable"]
                                                and r["replacement_depth"] == 2),
            "replacements_from_3rd_string": sum(1 for r in out_slots
                                                if r["starter_unavailable"]
                                                and r["replacement_depth"] == 3),
            "replacements_from_4th_or_deeper": sum(1 for r in out_slots
                                                   if r["starter_unavailable"]
                                                   and (r["replacement_depth"] or 0) >= 4),
            "slots_with_no_printed_replacement": sum(1 for r in out_slots
                                                     if r["slot_exhausted"]),
            "slots_with_no_backup_printed": sum(1 for r in out_slots
                                                if r["no_backup_printed"]),
        },
        "headline_definition": "A starter ruled out is a first-string name printed on "
                               "the club's own chart who carries the official Out "
                               "status. The replacement depth is that slot's printed "
                               "rank of the first available name.",
        "club_rollup": rollup,
        "slots": all_slots,
        "players": all_players,
        "not_measured": [
            "No point value, probability or line adjustment is produced from a depth. A "
            "printed rank is an ordering, not a measurement of how good the replacement "
            "is, and no snap count or performance log was retrieved to turn it into one.",
            "Snap share, target share and usage are not published by the official injury "
            "report, so the 'next man up' impact on a projection stays blank.",
            "Houston's chart renders as an image on its club site, so Houston has no "
            "printed ranks and its depth is blank.",
        ],
    }
    return round_value(payload, 6)


def main():
    if check_artifact(OUT, build()):
        payload = build()
        head = payload["headline"]
        print(f"  {payload['coverage']['printed_slots']} printed slots; "
              f"{head['starters_ruled_out']} starters ruled out; replacements "
              f"{head['replacements_from_2nd_string']} from 2nd string, "
              f"{head['replacements_from_3rd_string']} from 3rd, "
              f"{head['replacements_from_4th_or_deeper']} from 4th or deeper")


if __name__ == "__main__":
    main()
