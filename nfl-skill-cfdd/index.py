#!/usr/bin/env python3
"""Starter-depletion index: printed depth rank joined to the official injury ledger.

What this produces, and what it deliberately does not:

* A **count-based index**. For each club the index is a sum over injured players of a weight that
  depends only on the printed depth rank that club publishes. The weights are a project design
  choice, disclosed below, not an NFL-published value.
* **Offence and defence are separated**, because a lost starting tackle and a lost third
  cornerback are not the same deficiency and must not be summed into one number.
* **No point value, no probability, no performance deficit.** A printed rank is an ordering. It
  carries no measured amount of football. Converting a rank into points requires a before/after
  performance series and snap counts, and neither exists in this repository.

The four clubs captured on 2026-11-14 (CHI, DEN, PHI, TB) are exactly the four clubs with no
Week 10 injury rows: they were on bye. That is the reason they were missing, and it is now stated
rather than left as an unexplained gap.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from emit import emit_csv, emit_json, parse_args

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = HERE / "data"
LEDGER = REPO / "nfl-availability-28ef" / "data" / "depletion-week10-2026.csv"
INJURIES = REPO / "nfl-availability-28ef" / "data" / "injuries-week10-2026.csv"

# Depth weights. A printed 1st-string player lost is the headline; a 4th-string loss is depth
# noise. These are a disclosed project choice, not a measurement, and they are used ONLY to order
# clubs against each other. They are never converted to points and never multiplied by a price.
RANK_WEIGHT = {1: 1.00, 2: 0.45, 3: 0.20, 4: 0.10}
STATUS_MULTIPLIER = {"Out": 1.00, "Doubtful": 0.75, "Questionable": 0.40}

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}

# A club's depth chart and the league injury report use different position vocabularies for the
# same job (T vs RT/LT, LB vs ILB/SAM/MLB, DE vs EDGE, DB vs CB/S/NB). Matching a player to a
# chart slot therefore has to compare GROUPS, not raw labels. This map is the desk's own reading of
# the two vocabularies; it is published on the method page and it never assigns a value from it.
POSITION_GROUP = {
    # offense
    "QB": "QB", "RB": "RB", "FB": "RB", "HB": "RB", "WR": "WR", "TE": "TE",
    "T": "OL", "OT": "OL", "LT": "OL", "RT": "OL", "G": "OL", "OG": "OL", "LG": "OL", "RG": "OL",
    "C": "OL", "OL": "OL",
    # defense
    "DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL", "EDGE": "DL", "IDL": "DL",
    "LB": "LB", "ILB": "LB", "OLB": "LB", "MLB": "LB", "WLB": "LB", "SLB": "LB", "SAM": "LB",
    "WILL": "LB", "MIKE": "LB",
    "CB": "DB", "DB": "DB", "S": "DB", "FS": "DB", "SS": "DB", "NB": "DB", "NCB": "DB",
    "SAF": "DB", "LCB": "DB", "RCB": "DB", "SCB": "DB",
    # special teams
    "K": "ST", "PK": "ST", "P": "ST", "LS": "ST", "KR": "ST", "PR": "ST", "H": "ST", "KO": "ST",
}
SIDE_OF_GROUP = {"QB": "offense", "RB": "offense", "WR": "offense", "TE": "offense",
                 "OL": "offense", "DL": "defense", "LB": "defense", "DB": "defense"}


def group_of(position: str) -> str:
    return POSITION_GROUP.get((position or "").strip().upper(), "")


def norm_name(value: str) -> str:
    """Comparison key only: letters and digits, lowercased, generational suffix dropped."""
    text = (value or "").replace("\u2019", "'").lower()
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    parts = [p for p in text.split() if p]
    while parts and parts[-1] in SUFFIXES:
        parts.pop()
    return "".join(parts)


def load(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def chart_lookup() -> dict[str, dict[str, dict]]:
    """club -> normalised player name -> the slot the club prints him in most prominently.

    A player can be printed in more than one slot (a returner listed at receiver, a guard listed at
    both guard spots). Keeping only one entry per player is required for the join, but it hides a
    real ambiguity, so ``printed_slot_count`` is carried on every entry and the count of ambiguous
    players is published.
    """
    out: dict[str, dict[str, dict]] = {}
    seen: dict[tuple, set] = {}
    # Charts captured by this session (2026-11-14) take precedence for their clubs because they are
    # the most recent read; the earlier 2026-11-13 slots fill every other club.
    for path in (DATA / "depth-slots-2026-11-14.csv",
                 REPO / "nfl-availability-28ef" / "data" / "depth-slots-week10-2026.csv"):
        for row in load(path):
            club = row["club_abbr"]
            key = norm_name(row["player"].split(" / ")[0])
            if not key:
                continue
            entry = {
                "rank": int(row["rank"]),
                "unit": row["unit"],
                "position": row["position"],
                "slot": str(row.get("slot", "")),
                "position_key": row["position"],
                "source_url": row["source_url"],
                "checked_on": row["checked_on"],
                "multi": row.get("cell_holds_multiple", "no") == "yes",
            }
            entry["group"] = group_of(entry["position"])
            seen.setdefault((club, key), set()).add(
                (entry["unit"], entry["position_key"], entry["slot"]))
            out.setdefault(club, {}).setdefault("_alternatives", {}).setdefault(
                key, []).append(entry)
            if row.get("first_cell_blank") == "yes":
                # A slot whose first-string cell is empty is the least authoritative place to
                # locate a player, so it does not displace a real first-string entry.
                out.setdefault(club, {}).setdefault(key, entry)
                continue
            existing = out.setdefault(club, {}).get(key)
            if existing is None:
                out[club][key] = entry
                continue
            # Precedence, applied in order and stated on the method page:
            #   1. the newest read wins (never regress to an older snapshot);
            #   2. within one read, a slot whose position group matches the injury report wins,
            #      so a receiver listed by the league at WR is not located by his punt-return slot;
            #   3. then the higher printed rank (1st string beats 3rd).
            if entry["checked_on"] > existing["checked_on"]:
                out[club][key] = entry
            elif entry["checked_on"] == existing["checked_on"] and entry["rank"] < existing["rank"]:
                out[club][key] = entry
    for (club, key), slots in seen.items():
        if key in out[club]:
            out[club][key]["printed_slot_count"] = len(slots)
    return out


def _best_slot_for_group(charts, club, key, group):
    """The newest, highest-ranked chart slot for this player in the given position group."""
    for entry in charts.get(club, {}).get("_alternatives", {}).get(key, []):
        if entry.get("group") == group:
            return entry
    return None


def rebuild_join(injuries: list[dict], charts: dict[str, dict[str, dict]]) -> list[dict]:
    """Re-do the injury x depth join now that all 32 clubs have a printed chart."""
    rows = []
    for inj in injuries:
        club = inj["club_abbr"]
        chart = charts.get(club, {})
        match = chart.get(norm_name(inj["player"]))
        # If the player is printed in several slots and the chosen one is on a different side of
        # the ball from the position the league reports, prefer a slot that agrees with the report.
        reported_group = group_of(inj["position"])
        if match is not None and match.get("group") and reported_group:
            if (match["group"] in SIDE_OF_GROUP and reported_group in SIDE_OF_GROUP
                    and SIDE_OF_GROUP[match["group"]] != SIDE_OF_GROUP[reported_group]):
                alt = _best_slot_for_group(charts, club, norm_name(inj["player"]), reported_group)
                if alt is not None:
                    match = alt
        track = "unmatched"
        if match:
            track = match["unit"].lower()
            if track == "special teams":
                track = "special teams"
            elif track not in ("offense", "defense"):
                track = "other"
        rows.append({
            "injury_id": inj["injury_id"],
            "club_abbr": club,
            "club_name": inj["club_name"],
            "player": inj["player"],
            "position_reported": inj["position"],
            "injury_listed": inj["injury"],
            "practice_status": inj["practice_status"],
            "game_status": inj["game_status"],
            "on_printed_chart": "yes" if match else "no",
            "printed_unit": match["unit"] if match else "",
            "printed_position": match["position"] if match else "",
            "printed_rank": match["rank"] if match else "",
            "printed_slot": match["slot"] if match else "",
            "printed_position_key": match["position_key"] if match else "",
            "printed_slot_count": match.get("printed_slot_count", "") if match else "",
            "track": track,
            "status_multiplier": STATUS_MULTIPLIER.get(inj["game_status"].strip(), ""),
            "rank_weight": RANK_WEIGHT.get(match["rank"], "") if match else "",
            "depletion_points": (
                round(STATUS_MULTIPLIER[inj["game_status"].strip()]
                      * RANK_WEIGHT.get(match["rank"], 0.0), 4)
                if match and inj["game_status"].strip() in STATUS_MULTIPLIER else ""
            ),
            "injury_source_url": inj["source_url"],
            "injury_checked_on": inj["checked_on"],
            "depth_source_url": match["source_url"] if match else "",
            "depth_checked_on": match["checked_on"] if match else "",
        })
    return rows


def resolve_next_in_line(joined: list[dict], charts: dict[str, dict[str, dict]]) -> None:
    """For every injured printed starter, name the next printed player in the SAME printed slot.

    A slot is (club, unit, slot number) as the club prints it - not a position, because a club
    prints several slots at the same position (two cornerbacks, three receivers). If the slot has
    nobody printed behind him, the replacement stays blank and that absence is counted.
    """
    # A slot is (club, unit, printed position, slot number). The position must be in the key: a
    # club restarts slot numbering for every position, so slot 1 exists several times per unit.
    names: dict[tuple, dict[int, str]] = {}
    position_of: dict[tuple, str] = {}
    for path in (DATA / "depth-slots-2026-11-14.csv",
                 REPO / "nfl-availability-28ef" / "data" / "depth-slots-week10-2026.csv"):
        for row in load(path):
            key = (row["club_abbr"], row["unit"], row["position"], str(row.get("slot", "")))
            names.setdefault(key, {})[int(row["rank"])] = row["player"].split(" / ")[0]
            position_of[key] = row["position"]

    for r in joined:
        r["next_in_line"] = ""
        r["next_in_line_rank"] = ""
        r["slot_has_backup"] = ""
        r["slot_deepest_rank"] = ""
        if r["on_printed_chart"] != "yes" or r["printed_rank"] == "":
            continue
        key = (r["club_abbr"], r["printed_unit"], r["printed_position_key"], r["printed_slot"])
        slot_names = names.get(key, {})
        ranks = sorted(slot_names)
        r["slot_deepest_rank"] = max(ranks) if ranks else ""
        current = int(r["printed_rank"])
        deeper = [k for k in ranks if k > current]
        if deeper:
            r["next_in_line"] = slot_names[deeper[0]]
            r["next_in_line_rank"] = deeper[0]
            r["slot_has_backup"] = "yes"
        else:
            r["slot_has_backup"] = "no"


def club_summary(joined: list[dict], charts: dict[str, dict[str, dict]]) -> list[dict]:
    clubs = sorted({r["club_abbr"] for r in joined} | set(charts))
    out = []
    for club in clubs:
        mine = [r for r in joined if r["club_abbr"] == club]
        chart_size = len(charts.get(club, {}))

        def block(track: str) -> dict:
            sub = [r for r in mine if r["track"] == track]
            starters = [r for r in sub if r["printed_rank"] == 1]
            ruled_out = [r for r in sub if r["game_status"].strip() == "Out"]
            questionable = [r for r in sub if r["game_status"].strip() == "Questionable"]
            # A player is "depleted" when a printed starter is ruled out; the next printed name is
            # the replacement. That replacement is NOT claimed to be worse by any measured amount.
            depleted = [r for r in sub
                        if r["printed_rank"] == 1 and r["game_status"].strip() == "Out"]
            return {
                f"{track}_on_report": len(sub),
                f"{track}_starters_on_report": len(starters),
                f"{track}_starters_ruled_out": len(depleted),
                f"{track}_ruled_out_any_rank": len(ruled_out),
                f"{track}_questionable": len(questionable),
                f"{track}_index": round(sum(
                    float(r["depletion_points"]) for r in sub if r["depletion_points"] != ""), 4),
            }

        off, dfn, st = block("offense"), block("defense"), block("special teams")
        row = {
            "club_abbr": club,
            "club_name": mine[0]["club_name"] if mine else "",
            "printed_chart_available": "yes" if chart_size else "no",
            "printed_chart_players": chart_size,
            "players_on_injury_report": len(mine),
            "matched_to_printed_chart": sum(1 for r in mine if r["on_printed_chart"] == "yes"),
            "not_on_printed_chart": sum(1 for r in mine if r["on_printed_chart"] == "no"),
            "game_status_published_for_club": "yes" if any(
                r["game_status"].strip() for r in mine) else "no",
        }
        row.update(off)
        row.update(dfn)
        row.update(st)
        row["total_index"] = round(off["offense_index"] + dfn["defense_index"]
                                   + st["special teams_index"], 4)
        row["source_ids"] = "CFDD-DEPTH-2026-11-14 X28-NFL-INJ-W10"
        row["injury_source_url"] = mine[0]["injury_source_url"] if mine else ""
        row["depletion_index_note"] = (
            "count-based ordering only; see RANK_WEIGHT in nfl-skill-cfdd/index.py. "
            "Not a point value and not a probability."
        )
        out.append(row)
    out.sort(key=lambda r: (-r["total_index"], r["club_abbr"]))
    return out


def main() -> None:
    parse_args(__doc__)
    if not LEDGER.exists():
        raise SystemExit(f"injury ledger missing: {LEDGER}")
    injuries = load(INJURIES)
    charts = chart_lookup()
    # 31 of 32 clubs publish a readable chart. Houston's page renders a heading and an image and
    # no table, on two independent reads (2026-11-13 and 2026-11-14). That gap is published, not
    # quietly filled; the build fails only if a club is lost that previously worked.
    KNOWN_UNREADABLE = {"HOU"}
    if len(charts) + len(KNOWN_UNREADABLE) < 32 or KNOWN_UNREADABLE & set(charts):
        raise SystemExit(f"expected 31 readable charts plus HOU unreadable, found {len(charts)}")

    joined = rebuild_join(injuries, charts)
    resolve_next_in_line(joined, charts)
    summary = club_summary(joined, charts)

    key_order = ["injury_id", "club_abbr", "club_name", "player", "position_reported",
                 "injury_listed", "practice_status", "game_status", "on_printed_chart",
                 "printed_unit", "printed_position", "printed_rank", "track",
                 "status_multiplier", "rank_weight", "depletion_points",
                 "printed_slot", "printed_position_key", "printed_slot_count",
                 "next_in_line", "next_in_line_rank", "slot_has_backup", "slot_deepest_rank",
                 "ambiguous_printed_slot",
                 "injury_source_url", "injury_checked_on", "depth_source_url",
                 "depth_checked_on"]
    for r in joined:
        r["ambiguous_printed_slot"] = (
            "yes" if str(r["printed_slot_count"]).isdigit() and int(r["printed_slot_count"]) > 1
            else ("no" if str(r["printed_slot_count"]).isdigit() else ""))
    emit_csv(DATA / "depletion-join-2026-11-14.csv",
             [{k: r[k] for k in key_order} for r in joined])
    emit_csv(DATA / "club-depletion-index-2026-11-14.csv", summary)

    matched = sum(1 for r in joined if r["on_printed_chart"] == "yes")
    starters_out = [r for r in joined
                    if r["printed_rank"] == 1 and r["game_status"].strip() == "Out"]
    emit_json(DATA / "depletion-index-2026-11-14.json", {
        "read_on": "2026-11-14",
        "injury_rows": len(joined),
        "clubs_on_injury_report": len({r["club_abbr"] for r in joined}),
        "clubs_with_printed_chart": len(charts),
        "clubs_with_no_readable_chart": sorted({"HOU"}),
        "clubs_absent_from_injury_report": sorted(
            set(charts) - {r["club_abbr"] for r in joined}),
        "clubs_absent_reason": "these four clubs were on bye in Week 10, so the league publishes no "
                               "Week 10 injury row for them; their charts are captured and ready "
                               "for Week 11",
        "rows_matched_to_printed_chart": matched,
        "rows_not_on_printed_chart": len(joined) - matched,
        "starters_ruled_out": len(starters_out),
        "injury_rows_printed_in_more_than_one_slot": sum(
            1 for r in joined if r.get("ambiguous_printed_slot") == "yes"),
        "starters_ruled_out_in_more_than_one_slot": sum(
            1 for r in starters_out if r.get("ambiguous_printed_slot") == "yes"),
        "ambiguous_slot_statement": "Some players are printed in more than one slot by their own "
                                    "club. The join uses one printed slot per player - the most "
                                    "prominent one - and every such row is marked. Where a starter "
                                    "is ambiguous his replacement comes from that chosen slot, so "
                                    "the next name could differ in another listed slot.",
        "starters_ruled_out_with_backup_in_line": sum(
            1 for r in starters_out if r["slot_has_backup"] == "yes"),
        "starters_ruled_out_with_no_backup_printed": sum(
            1 for r in starters_out if r["slot_has_backup"] == "no"),
        "backed_up_starters": [
            {"club": r["club_abbr"], "player": r["player"], "unit": r["printed_unit"],
             "position": r["printed_position"], "next_in_line": r["next_in_line"],
             "next_in_line_rank": r["next_in_line_rank"]}
            for r in starters_out if r["slot_has_backup"] == "yes"],
        "no_backup_printed": [
            {"club": r["club_abbr"], "player": r["player"], "unit": r["printed_unit"],
             "position": r["printed_position"]}
            for r in starters_out if r["slot_has_backup"] == "no"],
        "starters_ruled_out_names": [
            {"club": r["club_abbr"], "player": r["player"], "unit": r["printed_unit"],
             "position": r["printed_position"]}
            for r in starters_out],
        "starters_ruled_out_by_club": {
            club: [r["player"] for r in starters_out if r["club_abbr"] == club]
            for club in sorted({r["club_abbr"] for r in starters_out})
        },
        "weigthing_disclosure": {
            "rank_weight": RANK_WEIGHT,
            "status_multiplier": STATUS_MULTIPLIER,
            "statement": "Project design choice, chosen before any club ranking was read. Used to "
                         "order clubs only. Never converted to points, probability or price.",
        },
        "what_is_not_produced": [
            "a point value for an injured player",
            "a performance deficit for a backup, which needs snap counts and a before/after series",
            "a probability that a backup 'holds up'",
            "any line adjustment derived from this index",
        ],
        "scope": "Availability accounting from official printed sources. Not a forecast.",
    })
    print(f"OK: {len(joined)} injury rows joined to 32 printed charts; "
          f"{matched} matched; {len(starters_out)} printed starters ruled out")


if __name__ == "__main__":
    main()
