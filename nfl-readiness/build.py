#!/usr/bin/env python3
"""Decision-readiness desk: deterministic checks behind research/nfl-readiness.json.

Every number the register cites is recomputed here from committed files:
  * a 2026-11-17 read of the official NFL.com injury page (chunk 0) and schedule page,
    transcribed into nfl-readiness/evidence/ (manual reads, see README of the desk);
  * the three repo Week 10 injury tables, and the depth-slot files;
  * the results feed and the Week 10 game files;
  * the one-sided sample-size arithmetic used for every "number that would clear it".

Usage:
  python nfl-readiness/build.py          # write data/*.json
  python nfl-readiness/build.py --check  # fail if committed data/*.json is stale
Standard library only.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESK = ROOT / "nfl-readiness"
DATA = DESK / "data"
EVID = DESK / "evidence"
AS_OF = "2026-11-17"
LIVE_URL = "https://www.nfl.com/injuries/"
SCHED_URL = "https://www.nfl.com/schedules/"


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def norm_name(name: str) -> str:
    name = name.lower().replace(".", "").replace("'", "").replace("-", " ")
    name = re.sub(r"\s+(jr|sr|ii|iii|iv)$", "", name.strip())
    return re.sub(r"\s+", " ", name).strip()


def clean(value: str) -> str:
    return (value or "").strip()


# Club codes: the official logo code for the Rams is "LA"; the repo's games files use "LAR".
CANON = {"LA": "LAR"}


def canon(code: str) -> str:
    code = clean(code)
    return CANON.get(code, code)


# Practice labels: the origination desk prints "DNP", "Limited", "Full"; the official page prints
# the long form. Only a real difference in meaning counts as a mismatch.
PRACTICE = {"dnp": "did not participate in practice", "limited": "limited participation in practice",
            "full": "full participation in practice", "fp": "full participation in practice"}


def norm_practice(value: str) -> str:
    v = clean(value).lower()
    return PRACTICE.get(v, v)


def nickname_map() -> dict[str, str]:
    out = {}
    for g in read_csv(ROOT / "nfl-availability-28ef/data/games-week10-2026.csv"):
        out[clean(g["away_name"])] = canon(g["away_abbr"])
        out[clean(g["home_name"])] = canon(g["home_abbr"])
    return out


# ---------- 1. Desk-by-desk Week 10 injury tables ----------------------------------------
DESKS = {
    "availability-28ef": {
        "path": ROOT / "nfl-availability-28ef/data/injuries-week10-2026.csv",
        "club": "club_abbr", "player": "player", "injury": "injury",
        "practice": "practice_status", "game": "game_status", "checked_on": "2026-11-13",
    },
    "assurance-9580ac3f": {
        "path": ROOT / "nfl-assurance-9580ac3f/data/injuries.csv",
        "club": "team", "player": "player", "injury": "injury",
        "practice": "practice_status", "game": "game_status", "checked_on": "not recorded in file",
    },
    "origination-lab": {
        "path": ROOT / "nfl/origination/data/injuries-2026-w10.csv",
        "club": "club", "player": "player", "injury": "injury",
        "practice": "practice", "game": "designation", "checked_on": "not recorded in file",
    },
    "canonical-legacy": {
        "path": ROOT / "data/nfl-injuries-2026-w10.csv",
        "club": "Team", "player": "Player", "injury": "Injury",
        "practice": "PracticeStatus", "game": "GameStatus", "checked_on": "2026-11-12",
        "club_is_nickname": True,
    },
}

GAMES_W10 = ROOT / "nfl-availability-28ef/data/games-week10-2026.csv"


def load_desk(spec: dict) -> list[dict]:
    rows = read_csv(spec["path"])
    nick = nickname_map() if spec.get("club_is_nickname") else {}
    return [{"club": nick.get(clean(r[spec["club"]]), canon(r[spec["club"]])),
             "player": clean(r[spec["player"]]),
             "injury": clean(r[spec["injury"]]), "practice": clean(r[spec["practice"]]),
             "game": clean(r[spec["game"]])} for r in rows]


def desk_summary(name: str, spec: dict, rows: list[dict], playing: set[str]) -> dict:
    clubs = {r["club"] for r in rows}
    return {
        "file": str(spec["path"].relative_to(ROOT)),
        "rows": len(rows),
        "clubs_with_rows": len(clubs),
        "playing_clubs_with_zero_rows": sorted(playing - clubs),
        "rows_with_game_status": sum(1 for r in rows if r["game"]),
        "rows_with_injury_text": sum(1 for r in rows if r["injury"]),
        "checked_on_recorded": spec["checked_on"],
        "clubs_present": sorted(clubs),
    }


# ---------- 2. Live 2026-11-17 chunk versus each desk ------------------------------------
FIELDS = (("injury", "live_injury"), ("practice", "live_practice_status"), ("game", "live_game_status"))


def compare_live(live: list[dict], desk_rows: list[dict]) -> dict:
    index: dict[tuple[str, str], dict] = {}
    for r in desk_rows:
        index.setdefault((r["club"], norm_name(r["player"])), r)
    matched, unmatched, mismatches = 0, [], []
    field_mismatch = {f: 0 for f, _ in FIELDS}
    for lr in live:
        lr = dict(lr, club=canon(lr["club"]))
        key = (lr["club"], norm_name(lr["player"]))
        dr = index.get(key)
        if dr is None:
            unmatched.append(f'{lr["club"]} {lr["player"]}')
            continue
        matched += 1
        for field, live_col in FIELDS:
            live_val = norm_practice(lr[live_col]) if field == "practice" else clean(lr[live_col]).lower()
            desk_val = norm_practice(dr[field]) if field == "practice" else dr[field].lower()
            if live_val != desk_val:
                field_mismatch[field] += 1
                mismatches.append({"club": lr["club"], "player": lr["player"], "field": field,
                                   "live": clean(lr[live_col]), "desk": dr[field],
                                   "list_complete": lr["list_complete"]})
    unmatched_injured = sum(1 for lr in live if f'{lr["club"]} {lr["player"]}' in unmatched and clean(lr["live_injury"]))
    return {"live_rows_compared": len(live), "matched": matched, "unmatched": unmatched,
            "unmatched_with_live_injury_text": unmatched_injured,
            "field_mismatches": field_mismatch, "mismatch_rows": mismatches}


# ---------- 3. Depth groups (printed rank 1 >1 player) ------------------------------------
def depth_groups() -> dict:
    avail = read_csv(ROOT / "nfl-availability-28ef/data/depth-slots-week10-2026.csv")
    cfdd = read_csv(ROOT / "nfl-skill-cfdd/data/depth-slots-2026-11-14.csv")
    def count(rows: list[dict], club: str, units: set[str] | None) -> tuple[int, int]:
        groups: dict[tuple, int] = {}
        for r in rows:
            if clean(r["rank"]) != "1" or (units and r["unit"] not in units):
                continue
            key = (r[club], r["unit"], r["position"])
            groups[key] = groups.get(key, 0) + 1
        return len(groups), sum(1 for v in groups.values() if v > 1)

    out: dict[str, dict] = {}
    for label, rows in (("availability-28ef", avail), ("skill-cfdd-bye-clubs", cfdd)):
        groups, multi = count(rows, "club_abbr", None)
        groups_os, multi_os = count(rows, "club_abbr", {"Offense", "Defense"})
        out[label] = {"rows": len(rows), "clubs": len({r["club_abbr"] for r in rows}),
                      "rank1_groups": groups, "rank1_groups_with_more_than_one_player": multi,
                      "offense_defense_rank1_groups": groups_os,
                      "offense_defense_groups_with_more_than_one_player": multi_os}
    a, c = out["availability-28ef"], out["skill-cfdd-bye-clubs"]
    out["combined"] = {
        "rank1_groups": a["rank1_groups"] + c["rank1_groups"],
        "rank1_groups_with_more_than_one_player": a["rank1_groups_with_more_than_one_player"] + c["rank1_groups_with_more_than_one_player"],
        "offense_defense_groups_with_more_than_one_player": a["offense_defense_groups_with_more_than_one_player"] + c["offense_defense_groups_with_more_than_one_player"],
    }
    return out


# ---------- 4. Week 10 finals and the results feed ---------------------------------------
def week10_check(live_finals: list[dict]) -> dict:
    games = read_csv(GAMES_W10)
    pairs = {(canon(g["away_abbr"]), canon(g["home_abbr"])) for g in games}
    orig = read_csv(ROOT / "nfl/origination/data/games-2026-w10.csv")
    orig_pairs = {(canon(g["away"]), canon(g["home"])) for g in orig}
    final_rows = [r for r in live_finals if r["status_as_read"] == "Final"]
    unconfirmed = [r["game"] for r in live_finals if r["status_as_read"] != "Final"]
    matched = [(canon(r["away"]), canon(r["home"])) for r in final_rows if (canon(r["away"]), canon(r["home"])) in pairs]
    feed = read_csv(ROOT / "nfl-results/data/games-2026-w1-9.csv")
    weeks = sorted({int(r["week"]) for r in feed})
    venue_notes = [clean(g["venue_note"]) for g in orig]
    return {
        "schedule_games_w10": len(games),
        "official_final_read_2026_11_17": len(final_rows),
        "not_shown_final": unconfirmed,
        "final_pairs_matching_repo_w10_pairs": len(matched),
        "origination_w10_pairs_matching_schedule_read": len(orig_pairs & pairs),
        "origination_w10_rows": len(orig),
        "origination_w10_venue_notes_populated": sum(1 for v in venue_notes if v),
        "results_feed_rows": len(feed),
        "results_feed_weeks": weeks,
        "results_feed_retrieved": sorted({r["retrieved"] for r in feed}),
    }


# ---------- 5. One-sided sample-size arithmetic -----------------------------------------
def n_required(p1: float, p0: float = 0.5, alpha_one_sided: float = 0.05, power: float = 0.80) -> int:
    z_a = 1.6448536269514722   # one-sided alpha 0.05
    z_b = 0.8416212335729143   # power 0.80
    num = z_a * math.sqrt(p0 * (1 - p0)) + z_b * math.sqrt(p1 * (1 - p1))
    return math.ceil((num / (p1 - p0)) ** 2)


def clearing_numbers() -> dict:
    return {
        "method": "One-sample binomial test of H0 p=0.5, one-sided alpha 0.05, power 0.80 "
                  "(normal approximation). Reproduces the 617 / 153 / 2,682 values published on "
                  "the NFL results and skill pages.",
        "n_for_p55": n_required(0.55),
        "n_for_p60": n_required(0.60),
        "n_for_p524": n_required(0.524),
        "regular_season_games_2026": 32 * 17 // 2,
        "games_feed_w1_9": 136,
        "games_w10_official_final_read": 13,
        "games_w10": 14,
    }


def build() -> dict[str, object]:
    live = read_csv(EVID / "live-injury-chunk0-2026-11-17.csv")
    finals = read_csv(EVID / "week10-finals-official-2026-11-17.csv")
    games = read_csv(GAMES_W10)
    playing = {canon(g["away_abbr"]) for g in games} | {canon(g["home_abbr"]) for g in games}
    desks = {}
    rows_by_desk = {}
    for name, spec in DESKS.items():
        rows = load_desk(spec)
        rows_by_desk[name] = rows
        desks[name] = desk_summary(name, spec, rows, playing)
    comparisons = {}
    for name in ("availability-28ef", "assurance-9580ac3f", "origination-lab"):
        comparisons[name] = compare_live(live, rows_by_desk[name])
    lions = {}
    for name in ("availability-28ef", "assurance-9580ac3f", "origination-lab"):
        lions[name] = {r["player"]: r["game"] or "(blank)" for r in rows_by_desk[name]
                       if r["club"] == "DET" and r["player"] in ("Kerby Joseph", "Cade Mays", "D.J. Reed")}
    return {
        "as_of": AS_OF,
        "live_source": LIVE_URL,
        "schedule_source": SCHED_URL,
        "live_chunk": {"rows": len(live), "clubs": sorted({r["club"] for r in live}),
                       "complete_clubs": sorted({r["club"] for r in live if r["list_complete"] == "yes"}),
                       "partial_clubs": sorted({r["club"] for r in live if r["list_complete"] != "yes"})},
        "desks": desks,
        "live_vs_desk": comparisons,
        "lions_game_status_by_desk": lions,
        "depth_groups": depth_groups(),
        "week10": week10_check(finals),
        "row_level_injury_rows_in_repo": sum(d["rows"] for d in desks.values()),
        "clearing": clearing_numbers(),
    }


def dump(obj: dict) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    result = build()
    target = DATA / "readiness-checks-2026-11-17.json"
    text = dump(result)
    if "--check" in argv:
        if not target.exists() or target.read_text(encoding="utf-8") != text:
            print(f"STALE: {target.relative_to(ROOT)} does not match recomputed output")
            return 1
        print(f"OK: {target.relative_to(ROOT)} reproduces from committed evidence")
        return 0
    DATA.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
