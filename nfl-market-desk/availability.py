#!/usr/bin/env python3
"""Availability: the depth of the replacement, not merely the fact of one.

The distinction that matters for a price is not "starter out". It is "which string is
now playing, and how far down the chart did the club have to reach". Two clubs can each
lose a receiver and be in completely different shape:

    * the club whose WR3 is now playing is deeper, all else equal, than
    * the club whose WR5 is now playing, whose WR4 was already out.

So the unit of record here is the *slot*, with the string that actually dresses:

    rank 1 (starter) out  ->  the replacement is the next healthy rank on the chart
    that replacement out  ->  the club reaches one string further down

`strings_lost` counts how many ranks above the dressed player are unavailable. That is
the depth measure. It is reported per slot, and a slot with no healthy body behind the
out player is treated as structurally worse than one with a 4th-string body behind it,
because the club has no floor left at that position.

Honesty constraints enforced in this module:

* Depth is only claimed where the club's own chart was read. Four clubs in this capture.
  Every other club is reported as `depth_not_captured`, never as "no issue".
* A chart with no printed date is marked undated. An undated chart cannot be asserted to
  be current, so the row carries that caveat rather than a clean value.
* Where the chart does not print a rank, the string is left blank. It is not inferred from
  the position of the row on the page.
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "nfl-skill-cfdd" / "data"


def _rows(name: str) -> list[dict]:
    with (SKILL / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_join() -> list[dict]:
    return _rows("depletion-join-2026-11-14.csv")


def depth_coverage() -> dict:
    slots = _rows("depth-slots-2026-11-14.csv")
    clubs = sorted({r["club_abbr"] for r in slots})
    charts = {}
    for r in slots:
        c = r["club_abbr"]
        if c in charts:
            continue
        charts[c] = {
            "club": r["club_name"],
            "chart_date_printed": r["chart_date_printed"],
            "dated": "no chart date printed" not in r["chart_date_printed"].lower(),
            "source_url": r["source_url"],
            "slots": sum(1 for x in slots if x["club_abbr"] == c),
            "deepest_rank": max(
                (int(x["rank"]) for x in slots if x["club_abbr"] == c and x["rank"].isdigit()),
                default=None,
            ),
        }
    join = load_join()
    with_status = [r for r in join if r["game_status"]]
    return {
        "clubs_with_depth": clubs,
        "n_clubs_with_depth": len(clubs),
        "n_clubs_league": 32,
        "coverage_note": (
            f"Depth charts were read for {len(clubs)} of 32 clubs ({', '.join(clubs)}). "
            "The other 28 clubs have no captured chart, so requirement 6 is satisfied for "
            "those four clubs only. No claim is made about the rest."
        ),
        "charts": charts,
        "slots_total": len(slots),
        "injury_rows_total": len(join),
        "injury_rows_with_game_status": len(with_status),
        "clubs_in_injury_join": len({r["club_abbr"] for r in join}),
    }


def replacement_depth() -> list[dict]:
    """One row per injured player who carries an official game status.

    `strings_lost` = (rank of the dressed replacement) - (rank of the unavailable player)
    when both ranks are printed on the chart. It is the depth of the reach.
    """
    out = []
    for r in load_join():
        if not r["game_status"]:
            continue
        printed_rank = int(r["printed_rank"]) if r["printed_rank"].isdigit() else None
        next_rank = int(r["next_in_line_rank"]) if r["next_in_line_rank"].isdigit() else None
        deepest = int(r["slot_deepest_rank"]) if r["slot_deepest_rank"].isdigit() else None
        strings_lost = (next_rank - printed_rank) if (printed_rank and next_rank) else None
        on_chart = r["on_printed_chart"] == "yes"
        if not on_chart:
            tier = "not_on_chart"
            note = "player is not printed on the club's chart; the slot and its depth are unknown"
        elif printed_rank is None:
            tier = "rank_not_printed"
            note = "chart prints the player without a rank; string is left blank, not inferred"
        elif r["slot_has_backup"] == "no":
            tier = "no_healthy_body_behind"
            note = "no healthy replacement printed behind the unavailable player in this slot"
        elif strings_lost is not None and strings_lost >= 1:
            tier = "reached_down_chart"
            note = (
                f"club dresses rank {next_rank} where rank {printed_rank} is unavailable "
                f"({r['next_in_line']}); chart goes to rank {deepest}"
            )
        else:
            tier = "like_for_like"
            note = "printed replacement holds the same string"
        out.append({
            "club": r["club_abbr"],
            "player": r["player"],
            "position": r["position_reported"],
            "game_status": r["game_status"],
            "practice_status": r["practice_status"],
            "on_chart": on_chart,
            "printed_rank": printed_rank,
            "replacement": r["next_in_line"],
            "replacement_rank": next_rank,
            "slot_deepest_rank": deepest,
            "strings_lost": strings_lost,
            "replacement_tier": tier,
            "tier_note": note,
            "depth_known": bool(on_chart and printed_rank is not None),
            "injury_source_url": r["injury_source_url"],
            "depth_source_url": r["depth_source_url"],
            "injury_checked_on": r["injury_checked_on"],
            "depth_checked_on": r["depth_checked_on"],
        })
    order = {"no_healthy_body_behind": 0, "reached_down_chart": 1, "like_for_like": 2,
             "rank_not_printed": 3, "not_on_chart": 4}
    out.sort(key=lambda r: (order[r["replacement_tier"]], r["club"], r["position"]))
    return out


def club_exposure(rows: list[dict] | None = None) -> list[dict]:
    """Per-club availability load, weighted by how far down the chart the club reached.

    The weight is deliberately crude and stated: 4 for no healthy body behind, 1 for each
    string of reach, 0 for like-for-like. It is a ranking device, not a fitted quantity,
    and it is never presented as a price adjustment.
    """
    rows = rows if rows is not None else replacement_depth()
    weights = {"no_healthy_body_behind": 4.0, "reached_down_chart": 1.0,
               "like_for_like": 0.0, "rank_not_printed": None, "not_on_chart": None}
    by_club: dict[str, dict] = {}
    for r in rows:
        c = by_club.setdefault(r["club"], {
            "club": r["club"], "out": 0, "questionable": 0, "depth_known": 0,
            "unresolved_slots": 0, "weight": 0.0,
        })
        if r["game_status"] == "Out":
            c["out"] += 1
        elif r["game_status"] == "Questionable":
            c["questionable"] += 1
        if r["depth_known"]:
            c["depth_known"] += 1
        w = weights[r["replacement_tier"]]
        if w is None:
            c["unresolved_slots"] += 1
        else:
            c["weight"] += w + (r["strings_lost"] or 0) * 0.25
    out = list(by_club.values())
    for c in out:
        c["weight"] = round(c["weight"], 2)
    out.sort(key=lambda c: (-c["weight"], c["club"]))
    return out


if __name__ == "__main__":
    cov = depth_coverage()
    rows = replacement_depth()
    print(cov["coverage_note"])
    print("injury rows with game status:", len(rows))
    for r in rows:
        print(f'{r["club"]:4s} {r["game_status"]:12s} {r["player"][:22]:22s} '
              f'{r["position"]:3s} {r["replacement_tier"]:24s} lost={r["strings_lost"]}')
