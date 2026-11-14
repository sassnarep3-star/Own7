#!/usr/bin/env python3
"""Depth of replacement: how much of a printed queue a club actually loses, not just that it lost.

Every earlier desk in this repository recorded the *fact* of a replacement — "a starter is out and
the next name on the chart moves up". That is nearly information-free: replacing the first name of
a five-deep receiver queue and replacing the only body at right guard are completely different
events, and a count of "starters out" scores them the same.

This module measures the depth instead. For every injured player who appears on their club's own
printed chart it records:

  printed_rank        the position the club itself prints the player in (1 = first string)
  queue_depth         how many distinct names THAT club prints in that slot
  ranks_consumed      how many printed names must move up to cover the injury
                        = queue_depth - printed_rank + 1, floored at 1
  replacement_is      the player who actually takes the vacated slot, taken as the next printed
                        name below, with their own name so the reader can check it
  successors_left     how many printed names remain below the replacement
  uncovered           "yes" when nobody is printed behind the injured player: the club has no
                        listed body at all and the replacement must come from outside the chart

Two limits are stated rather than hidden:

  * ``queue_depth`` counts names PRINTED, which is not the same as names *available*. A club that
    prints four receivers is not thereby four receivers healthy.
  * No snap count, target share or player value is available, so nothing here is converted into
    points, a win probability or a line adjustment. It is a count structure, published as one.
  * Charts are dated. Each row carries the date the club printed on the chart and the date the
    chart was read, because a stale chart understates a queue that has since lost a body too.

The join to the injury ledger is done on (club, normalised player name) only. A player who appears
in the NFL.com injury report but on no saved chart is reported as unmatched with the reason, never
attached to a slot by guesswork.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

from emit import emit_csv, emit_json, parse_args
import charts

REPO = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

INJURIES = REPO / "data" / "nfl-injuries-2026-w10.csv"
INJURY_SOURCE = "https://www.nfl.com/injuries/"
INJURY_READ_ON = "2026-11-12"

UNIT_OF_GROUP = {
    # Position-group map. Report labels differ from chart labels, so the join is by group rather
    # than by exact string, exactly as the earlier desk had to do.
    "QB": "Offense", "RB": "Offense", "FB": "Offense", "WR": "Offense", "TE": "Offense",
    "T": "Offense", "G": "Offense", "C": "Offense", "OT": "Offense", "OG": "Offense",
    "OL": "Offense", "LT": "Offense", "LG": "Offense", "RG": "Offense", "RT": "Offense",
    "DE": "Defense", "DT": "Defense", "NT": "Defense", "EDGE": "Defense", "LB": "Defense",
    "ILB": "Defense", "OLB": "Defense", "MLB": "Defense", "WLB": "Defense", "SLB": "Defense",
    "CB": "Defense", "DB": "Defense", "S": "Defense", "FS": "Defense", "SS": "Defense",
    "SAF": "Defense", "NB": "Defense", "N": "Defense",
    "K": "Special Teams", "P": "Special Teams", "LS": "Special Teams", "H": "Special Teams",
    "PR": "Special Teams", "KR": "Special Teams", "PK": "Special Teams",
}
# Statuses that mean the player is unavailable for the game. Practice-only labels are not used:
# the ledger's own game-status column is the only thing that implies game availability.
UNAVAILABLE = {"OUT", "DOUBTFUL"}


def norm(name: str) -> str:
    """Normalise a printed name for joining. No nickname expansion, no initial guessing."""
    text = unicodedata.normalize("NFKD", name)
    text = text.replace("'", "").replace("\u2019", "").replace(".", "")
    return re.sub(r"\s+", " ", text).strip().lower()


def load_injuries() -> list[dict]:
    with INJURIES.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def slot_index(club_rows: list[dict]) -> dict[tuple[str, str, int], list[dict]]:
    """(unit, position, slot) -> players sorted by printed rank."""
    out: dict[tuple[str, str, int], list[dict]] = {}
    for row in club_rows:
        key = (row["unit"], row["position"], int(row["slot"]))
        out.setdefault(key, []).append(row)
    for players in out.values():
        players.sort(key=lambda r: (r["printed_rank"], int(r.get("order_in_cell") or 0)))
    return out


def match_player(club_rows: list[dict], name: str) -> dict | None:
    target = norm(name)
    hits = [r for r in club_rows if norm(r["player"]) == target]
    if not hits:
        return None
    # A player printed in more than one slot (a returner who is also a receiver) is a real and
    # common case. Take the slot with the smallest printed rank, i.e. the deepest role on the
    # chart; the ambiguity is recorded in the row rather than resolved silently.
    hits.sort(key=lambda r: (int(r["printed_rank"]), r["unit"], r["position"], int(r["slot"])))
    return hits[0]


def build() -> tuple[list[dict], list[dict], dict]:
    depth_rows, _, depth_stats = charts.build_depth_rows()
    by_club: dict[str, list[dict]] = {}
    for row in depth_rows:
        by_club.setdefault(row["club_abbr"], []).append(row)

    injuries = load_injuries()
    # The injury CSV prints short club names ("Commanders"); the charts are keyed by club code.
    # Derive the short name from the full name and check uniqueness, so a collision aborts rather
    # than silently attaching a player to the wrong club.
    from snapshots import FULL_NAME
    short_to_code: dict[str, str] = {}
    for code, full in FULL_NAME.items():
        short = full.split()[-1]
        if short in short_to_code and short_to_code[short] != code:
            raise SystemExit(f"short club name {short!r} is ambiguous")
        short_to_code[short] = code
    name_to_code = short_to_code

    joined: list[dict] = []
    unmatched: list[dict] = []
    for injury in injuries:
        club = name_to_code.get(injury.get("Team") or injury.get("TeamName") or "")
        player = injury.get("Player", "")
        if club is None:
            unmatched.append({"player": player, "club_printed": injury.get("Team", ""),
                              "reason": "club name not mapped to a club code"})
            continue
        club_rows = by_club.get(club, [])
        if not club_rows:
            unmatched.append({"player": player, "club_printed": injury.get("Team", ""),
                              "reason": f"no printed chart was captured for {club}"})
            continue
        hit = match_player(club_rows, player)
        if hit is None:
            unmatched.append({"player": player, "club_printed": injury.get("Team", ""),
                              "reason": "not printed on the captured chart"})
            continue
        slot = int(hit["slot"])
        players = slot_index(club_rows)[(hit["unit"], hit["position"], slot)]
        depth = len({p["printed_rank"] for p in players})
        rank = int(hit["printed_rank"])
        ranks_consumed = max(1, depth - rank + 1)
        below = [p for p in players if int(p["printed_rank"]) > rank]
        replacement = below[0] if below else None
        successors_left = max(0, len({p["printed_rank"] for p in below}) - 1)
        game_status = (injury.get("GameStatus") or "").strip()
        joined.append({
            "injury_id": injury.get("id", ""),
            "club_abbr": club,
            "player": player,
            "report_position": injury.get("Position", ""),
            "injury": injury.get("Injury", ""),
            "practice_status": injury.get("PracticeStatus", ""),
            "game_status": game_status,
            "unavailable_for_game": "yes" if game_status.upper() in UNAVAILABLE else
                                    ("no" if game_status else ""),
            "printed_unit": hit["unit"],
            "printed_position": hit["position"],
            "printed_slot": slot,
            "printed_rank": rank,
            "printed_queue_depth": depth,
            "ranks_consumed": ranks_consumed,
            "replacement_player": replacement["player"] if replacement else "",
            "replacement_printed_rank": replacement["printed_rank"] if replacement else "",
            "replacement_player_url": replacement["player_url"] if replacement else "",
            "successors_remaining_below": successors_left,
            "uncovered_slot": "yes" if replacement is None else "no",
            "printed_in_multiple_slots": "yes" if sum(
                1 for r in club_rows if norm(r["player"]) == norm(player)) > 1 else "no",
            "chart_date_printed": hit["chart_date_printed"],
            "chart_read_on": hit["read_on"],
            "chart_source_url": hit["source_url"],
            "injury_source_url": INJURY_SOURCE,
            "injury_read_on": INJURY_READ_ON,
        })

    # Club-level roll-up, offence and defence kept apart because they fail differently.
    club_rows_out: list[dict] = []
    for club in sorted(set(by_club) | {r["club_abbr"] for r in joined}):
        club_joined = [r for r in joined if r["club_abbr"] == club]
        chart = by_club.get(club, [])
        record = {
            "club_abbr": club,
            "printed_chart_available": "yes" if chart else "no",
            "printed_slots": len({(r["unit"], r["position"], r["slot"]) for r in chart}),
            "injury_rows_matched": len(club_joined),
            "unmatched_injury_rows": sum(1 for u in unmatched if u["club_printed"]
                                         and name_to_code.get(u["club_printed"]) == club),
            "chart_date_printed": (chart[0]["chart_date_printed"] if chart else ""),
            "chart_read_on": (chart[0]["read_on"] if chart else ""),
            "source_url": (chart[0]["source_url"] if chart else ""),
        }
        for unit, label in (("Offense", "offense"), ("Defense", "defense"),
                            ("Special Teams", "special_teams")):
            subset = [r for r in club_joined if r["printed_unit"] == unit]
            out = [r for r in subset if r["unavailable_for_game"] == "yes"]
            record[f"{label}_players_listed"] = len(subset)
            record[f"{label}_unavailable"] = len(out)
            record[f"{label}_ranks_consumed"] = sum(r["ranks_consumed"] for r in out)
            record[f"{label}_uncovered_slots"] = sum(1 for r in out if r["uncovered_slot"] == "yes")
            listed = len({(r["printed_position"], r["printed_slot"]) for r in subset})
            record[f"{label}_listed_slots"] = listed
        club_rows_out.append(record)

    summary = {
        "injury_rows_read": len(injuries),
        "matched": len(joined),
        "unmatched": len(unmatched),
        "clubs_with_chart": depth_stats["clubs_with_printed_chart"],
        "clubs_without_chart": depth_stats["clubs_without_printed_chart"],
        "unmatched_reasons": _count(unmatched),
        "unavailable_matched": sum(1 for r in joined if r["unavailable_for_game"] == "yes"),
        "uncovered_slots": sum(1 for r in joined if r["uncovered_slot"] == "yes"),
        "multiple_slot_players": sum(1 for r in joined if r["printed_in_multiple_slots"] == "yes"),
        "quantity_defined": "ranks_consumed = printed names that must move up to cover the injury "
                            "= queue_depth - printed_rank + 1. A count of printed bodies. Not a "
                            "point value, not a probability, not a line adjustment.",
        "limits": [
            "printed depth counts names printed by the club, not names healthy and available",
            "no snap count, target share or player grade is available, so no value is assigned",
            "charts are dated; a stale chart can understate a queue that has since lost a body",
            "practice-participation labels are recorded but are not used to infer game availability",
        ],
    }
    return joined, club_rows_out, {**summary, "unmatched_rows": unmatched}


def _count(rows: list[dict]) -> dict:
    out: dict[str, int] = {}
    for row in rows:
        out[row["reason"]] = out.get(row["reason"], 0) + 1
    return out


def main() -> None:
    parse_args(__doc__ or "depth_cost")
    joined, clubs, summary = build()
    emit_csv(DATA / "replacement-depth-2026-w10.csv", joined)
    emit_csv(DATA / "replacement-depth-by-club-2026-w10.csv", clubs)
    emit_json(DATA / "replacement-depth-summary-2026-w10.json", summary)
    print(f"Depth of replacement: {summary['matched']} of {summary['injury_rows_read']} injury "
          f"rows joined to a printed slot; {summary['uncovered_slots']} sit in a slot with no "
          f"printed replacement; {summary['unmatched']} unmatched with the reason recorded.")


if __name__ == "__main__":
    main()
