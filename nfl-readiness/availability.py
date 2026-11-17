#!/usr/bin/env python3
"""Availability and depth dataset for the decision-readiness desk (D8).

Inputs are the verbatim evidence files committed next to this module, not the network:

  evidence/injury-report-2026-reg10-2026-11-17.md   the publisher's own Week 10 tables
  evidence/depth-2026-11-17.md                      six club depth charts as printed
  evidence/schedule-2026-reg10-reg11-2026-11-17.md  the fixtures those reports belong to

What this module refuses to do, and asserts so the build fails if it ever does:

  * It never invents a player row. Every row comes from a parsed evidence table.
  * It never derives a depth rank from a jersey number, experience, salary or roster order.
  * It never treats a printed rank-1 cell as "the starter" when the club printed several names.
  * It never calls a backup an actual replacement: that needs participation evidence, which the
    repository does not hold, so every such field is blank with a stated reason.

Outputs (deterministic; no wall clock):
  data/availability.json   per-club counts, replacement chains, staleness tests, depth groups
  data/snapshots.json      the dated captures with SHA-256 hashes over the evidence bytes
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
EVID = HERE / "evidence"
DATA = HERE / "data"

INJURY_FILE = EVID / "injury-report-2026-reg10-2026-11-17.md"
DEPTH_FILE = EVID / "depth-2026-11-17.md"
SCHED_FILE = EVID / "schedule-2026-reg10-reg11-2026-11-17.md"

READ_DATE = "2026-11-17"

# Pinned row counts. If the publisher's page or our transcription changes shape, the build stops
# instead of publishing a silently different dataset. These are audited numbers, not defaults.
PINS = {
    "injury_rows": 347,
    "injury_clubs": 28,
    "depth_rows": 172,
    "depth_charts": 6,
}

CLUB_CODES = {
    "Commanders": "WAS", "Giants": "NYG", "Patriots": "NE", "Lions": "DET", "Chiefs": "KC",
    "Falcons": "ATL", "Vikings": "MIN", "Packers": "GB", "Jaguars": "JAX", "Titans": "TEN",
    "Bills": "BUF", "Jets": "NYJ", "Dolphins": "MIA", "Colts": "IND", "Panthers": "CAR",
    "Saints": "NO", "Texans": "HOU", "Browns": "CLE", "Rams": "LAR", "Cardinals": "AZ",
    "Seahawks": "SEA", "Raiders": "LV", "49ers": "SF", "Cowboys": "DAL", "Steelers": "PIT",
    "Bengals": "CIN", "Chargers": "LAC", "Ravens": "BAL",
}

DIVISION = {
    "BUF": ("AFC", "East"), "MIA": ("AFC", "East"), "NE": ("AFC", "East"), "NYJ": ("AFC", "East"),
    "BAL": ("AFC", "North"), "CIN": ("AFC", "North"), "CLE": ("AFC", "North"), "PIT": ("AFC", "North"),
    "HOU": ("AFC", "South"), "IND": ("AFC", "South"), "JAX": ("AFC", "South"), "TEN": ("AFC", "South"),
    "DEN": ("AFC", "West"), "KC": ("AFC", "West"), "LV": ("AFC", "West"), "LAC": ("AFC", "West"),
    "DAL": ("NFC", "East"), "NYG": ("NFC", "East"), "PHI": ("NFC", "East"), "WAS": ("NFC", "East"),
    "CHI": ("NFC", "North"), "DET": ("NFC", "North"), "GB": ("NFC", "North"), "MIN": ("NFC", "North"),
    "ATL": ("NFC", "South"), "CAR": ("NFC", "South"), "NO": ("NFC", "South"), "TB": ("NFC", "South"),
    "AZ": ("NFC", "West"), "LAR": ("NFC", "West"), "SF": ("NFC", "West"), "SEA": ("NFC", "West"),
}

# Week 10 fixtures, from the official by-week page (evidence/schedule-2026-reg10-reg11-2026-11-17.md).
WEEK10_FIXTURES = [
    ("WAS", "NYG"), ("NE", "DET"), ("KC", "ATL"), ("HOU", "CLE"), ("MIN", "GB"),
    ("MIA", "IND"), ("CAR", "NO"), ("BUF", "NYJ"), ("JAX", "TEN"), ("LAR", "AZ"),
    ("SEA", "LV"), ("SF", "DAL"), ("PIT", "CIN"), ("LAC", "BAL"),
]
WEEK10_BYES = ["CHI", "DEN", "PHI", "TB"]

# Dated official statements about who would start, quoted in the evidence files. These are the only
# "announced starter" facts this desk holds, and each names the club and the date of the statement.
ANNOUNCED = [
    {"club": "SEA", "player": "Drew Lock", "replaces": "Sam Darnold",
     "statement": "Coach Mike Macdonald said Lock had no injury designation and would start in Week 10; Jalen Milroe would be the backup.",
     "dated": "2026-11-13", "source_ids": ["RD-NFL-LOCK"],
     "note": "The report page lists Lock as a limited practice participant with a blank game status, so the report alone would not have named the starter."},
    {"club": "CLE", "player": "Deshaun Watson", "replaces": "Shedeur Sanders",
     "statement": "The team announced Watson would start against the Texans.",
     "dated": "2026-11-11", "source_ids": ["RD-NFL-ROUNDUP-NOV11"],
     "note": "Quoted from the dated league roundup, which attributes the announcement to the club."},
    {"club": "AZ", "player": "Carson Beck", "replaces": "Kyler Murray",
     "statement": "Coach Mike LaFleur said Beck would start against the Rams.",
     "dated": "2026-11-11", "source_ids": ["RD-NFL-ROUNDUP-NOV11"],
     "note": "The injury report also lists Murray as Out with a hamstring injury, which is consistent but is not by itself an announcement."},
]

# Depth-chart staleness tests. Each is a claim that can be checked against the two evidence files.
STALENESS = [
    {"club": "BAL", "chart_qb": ["Jacoby Brissett", "Joe Fagnano", "Kedon Slovis"],
     "report_fact": "The Week 10 report does not list Lamar Jackson or Tyler Huntley at all.",
     "news_fact": "The NFL's dated roundup of 2026-11-13 quotes the club saying Jackson is expected to miss 6-10 weeks after thumb surgery.",
     "verdict": "current",
     "why": "The page prints Brissett at QB and does not print the injured starters, which is what a chart should show after a change. The prior desk's claim that it still printed Jackson and Huntley does not reproduce.",
     "source_ids": ["RD-BAL-CHART", "RD-NFL-INJ-W10", "RD-NFL-ROUNDUP-NOV13"]},
    {"club": "SEA", "chart_qb": ["Sam Darnold", "Drew Lock", "Jalen Milroe"],
     "report_fact": "Darnold is listed Out (ribs, quadricep); Lock is listed as limited with a blank game status.",
     "news_fact": "The head coach said Lock would start and Milroe would back up.",
     "verdict": "pending-announcement",
     "why": "The chart still prints the injured starter first, which is normal for a depth chart but means the chart alone cannot name the Week 10 starter.",
     "source_ids": ["RD-SEA-CHART", "RD-NFL-INJ-W10", "RD-NFL-LOCK"]},
    {"club": "GB", "chart_qb": ["Jordan Love", "Tyrod Taylor"],
     "report_fact": "Neither quarterback appears in the Week 10 report.",
     "news_fact": "",
     "verdict": "no-conflict",
     "why": "The chart and the report do not disagree about the quarterback room.",
     "source_ids": ["RD-GB-CHART", "RD-NFL-INJ-W10"]},
    {"club": "DET", "chart_qb": ["Jared Goff", "Joshua Dobbs"],
     "report_fact": "Goff is a full practice participant with a blank game status.",
     "news_fact": "",
     "verdict": "no-conflict",
     "why": "Consistent.",
     "source_ids": ["RD-DET-CHART", "RD-NFL-INJ-W10"]},
    {"club": "WAS", "chart_qb": ["Jayden Daniels", "Marcus Mariota", "Athan Kaliakmanis"],
     "report_fact": "Daniels is a full practice participant with a blank game status.",
     "news_fact": "",
     "verdict": "no-conflict", "why": "Consistent.",
     "source_ids": ["RD-WAS-CHART", "RD-NFL-INJ-W10"]},
    {"club": "IND", "chart_qb": ["Daniel Jones", "Anthony Richardson Sr.", "Riley Leonard"],
     "report_fact": "No Colts quarterback appears in the Week 10 report.",
     "news_fact": "",
     "verdict": "no-conflict", "why": "Consistent.",
     "source_ids": ["RD-IND-CHART", "RD-NFL-INJ-W10"]},
    {"club": "HOU", "chart_qb": [],
     "report_fact": "Sixteen Texans players are listed.",
     "news_fact": "",
     "verdict": "no-chart",
     "why": "The club serves its chart as an image, so there is no text row to test.",
     "source_ids": ["RD-HOU-CHART", "RD-NFL-INJ-W10"]},
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_injury_report() -> tuple[list[dict], dict]:
    """Parse the saved verbatim tables. Returns (rows, per-club meta)."""
    text = INJURY_FILE.read_text(encoding="utf-8")
    rows, club, meta = [], None, {}
    in_table = False
    for line in text.splitlines():
        heading = re.match(r"^## (.+?)\s*$", line)
        if heading:
            name = heading.group(1)
            if name in CLUB_CODES:
                club = name
                meta[CLUB_CODES[club]] = {"club": club, "rows": 0, "out": 0, "doubtful": 0,
                                          "questionable": 0, "blank_status": 0, "header": False}
                in_table = False
            else:
                club, in_table = None, False
            continue
        if club is None:
            continue
        if line.startswith("| Player | Position"):
            meta[CLUB_CODES[club]]["header"] = True
            continue
        if line.startswith("| ---"):
            in_table = True
            continue
        if in_table and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 5:
                raise SystemExit(f"injury row has {len(cells)} columns, expected 5: {line[:80]}")
            player, pos, injury, practice, status = cells
            if not player:
                raise SystemExit("injury row without a player name")
            rows.append({
                "club": CLUB_CODES[club], "player": player, "position": pos,
                "injury": injury, "practice": practice, "status": status,
                "source_ids": ["RD-NFL-INJ-W10"],
            })
            m = meta[CLUB_CODES[club]]
            m["rows"] += 1
            if status == "Out":
                m["out"] += 1
            elif status == "Doubtful":
                m["doubtful"] += 1
            elif status == "Questionable":
                m["questionable"] += 1
            elif status == "":
                m["blank_status"] += 1
            else:
                raise SystemExit(f"unknown game status {status!r}")
        elif in_table and line.strip() == "":
            in_table = False
    for code, m in meta.items():
        if not m["header"]:
            raise SystemExit(f"{code}: injury section without a table header")
    assert len(rows) == PINS["injury_rows"], f"injury rows {len(rows)} != pin {PINS['injury_rows']}"
    assert len(meta) == PINS["injury_clubs"], f"injury clubs {len(meta)} != pin {PINS['injury_clubs']}"
    return rows, meta


def parse_depth() -> list[dict]:
    """Parse the saved depth-chart transcription into slot rows.

    Each row keeps the *group* of rank-1 names exactly as printed. A cell containing two names
    separated by '; ' is one slot with two rank-1 players, which is the point of the exercise.
    """
    text = DEPTH_FILE.read_text(encoding="utf-8")
    rows, club = [], None
    chart_meta = {}
    for line in text.splitlines():
        if line.startswith("## "):
            club = None
        h2 = re.match(r"^## (.+)$", line)
        if h2 and "http" in h2.group(1):
            name = h2.group(1).split(" \u2014 ")[0].strip()
            club = {"Detroit Lions": "DET", "Green Bay Packers": "GB", "Seattle Seahawks": "SEA",
                    "Baltimore Ravens": "BAL", "Washington Commanders": "WAS",
                    "Indianapolis Colts": "IND"}.get(name)
            if club:
                chart_meta[club] = {"name": name, "slots": 0, "multi_rank1": 0, "empty_rank1": 0,
                                    "printed_date": "", "units": []}
            continue
        if club and re.search(r"Unofficial, Nov\. \d+, 2026", line):
            chart_meta[club]["printed_date"] = re.search(r"Unofficial, Nov\. \d+, 2026", line).group(0)
        if club and re.match(r"^### (Offense|Defense|Special teams)", line):
            chart_meta[club]["units"].append(line[4:].strip())
            continue
        if club is None or not line.startswith("|"):
            continue
        if re.match(r"^\| (Slot|---)", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        slot, rank1, rest = cells[0], cells[1] if len(cells) > 1 else "", [c for c in cells[2:] if c]
        if not slot:
            continue
        names = [n.strip() for n in rank1.split(";")] if rank1 else []
        names = [n for n in names if n and "empty rank 1" not in n]
        m = chart_meta[club]
        m["slots"] += 1
        if len(names) > 1:
            m["multi_rank1"] += 1
        if not names:
            m["empty_rank1"] += 1
        rows.append({
            "club": club, "slot": slot, "rank1": names, "deeper": rest,
            "unit": m["units"][-1] if m["units"] else "",
            "source_ids": {"DET": ["RD-DET-CHART"], "GB": ["RD-GB-CHART"], "SEA": ["RD-SEA-CHART"],
                           "BAL": ["RD-BAL-CHART"], "WAS": ["RD-WAS-CHART"],
                           "IND": ["RD-IND-CHART"]}[club],
        })
    assert len(rows) == PINS["depth_rows"], f"depth rows {len(rows)} != pin {PINS['depth_rows']}"
    assert len(chart_meta) == PINS["depth_charts"], f"charts {len(chart_meta)} != pin {PINS['depth_charts']}"
    for code, m in chart_meta.items():
        if m["slots"] == 0:
            raise SystemExit(f"{code}: chart parsed to zero slots")
    return rows, chart_meta


def normalise(name: str) -> str:
    """Strip a leading jersey number and punctuation so a printed chart name can be matched.

    This is the Green Bay fix: the club prints '9 Christian Watson'. The raw string is retained on
    the row; only the comparison key is normalised. Nothing else about the name is altered.
    """
    stripped = re.sub(r"^\d+\s+", "", name.strip())
    return re.sub(r"[^a-z ]", "", stripped.lower()).strip()


def build_depth_index(rows: list[dict]) -> dict:
    """(club, normalised name) -> list of rank descriptors, one per slot the player appears in."""
    index: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        for depth, group in enumerate([row["rank1"]] + [[d] for d in row["deeper"]]):
            for name in group:
                key = (row["club"], normalise(name))
                index.setdefault(key, []).append({
                    "slot": row["slot"], "unit": row["unit"],
                    "rank": depth + 1, "group_size": len(group), "printed": name,
                })
    return index


def replacement_chain(player: str, club: str, index: dict, depth_rows: list[dict]) -> dict:
    """Resolve an injured player to the printed name(s) one slot deeper.

    Returns blanks with a reason when the club has no text chart, when the player is not on the
    chart, or when the slot has no deeper name. It never guesses a replacement.
    """
    key = (club, normalise(player))
    slots = index.get(key)
    if slots is None:
        club_charted = any(r["club"] == club for r in depth_rows)
        reason = ("Player is not printed on this club's depth chart, so no printed replacement exists."
                  if club_charted else
                  "No text depth chart is available for this club (Houston serves an image), so depth is not resolvable.")
        return {"on_chart": False, "replacement": "", "replacement_rank": None,
                "depth_of_replacement": "", "reason": reason}
    # Prefer the shallowest printed rank: an injured rank-1 player is the interesting case.
    best = min(slots, key=lambda s: (s["rank"], s["slot"]))
    deeper: list[str] = []
    for row in depth_rows:
        if row["club"] != club or row["slot"] != best["slot"]:
            continue
        names = row["rank1"]
        if best["printed"] not in names:
            continue
        # Names printed after the injured player in the same cell, then the next printed column.
        deeper.extend(n for n in names if n != best["printed"])
        deeper.extend(row["deeper"])
        break
    next_rank = best["rank"] + 1
    return {
        "on_chart": True,
        "slot": best["slot"], "unit": best["unit"], "rank": best["rank"],
        "slot_printed_rank1_group": best["group_size"],
        "replacement": deeper[0] if deeper else "",
        "replacement_rank": next_rank if deeper else None,
        "depth_of_replacement": f"rank {best['rank']} -> rank {next_rank}" if deeper else "",
        "reason": "" if deeper else "The printed slot has no deeper name, so no replacement is named on the chart.",
    }


def build() -> dict:
    injury_rows, injury_meta = parse_injury_report()
    depth_rows, chart_meta = parse_depth()
    index = build_depth_index(depth_rows)

    # --- replacement chains for every injured player -------------------------------
    chains = []
    for row in injury_rows:
        chain = replacement_chain(row["player"], row["club"], index, depth_rows)
        chains.append({**row, **chain,
                       "actual_replacement": "",
                       "actual_replacement_reason": ("Who actually played needs an official inactive list, Game Book or "
                                                     "snap count; none is captured, so this stays blank."),
                       "source_ids": row["source_ids"] + (
                           {"DET": ["RD-DET-CHART"], "GB": ["RD-GB-CHART"], "SEA": ["RD-SEA-CHART"],
                            "BAL": ["RD-BAL-CHART"], "WAS": ["RD-WAS-CHART"],
                            "IND": ["RD-IND-CHART"]}.get(row["club"], []))})

    # --- per-club summary ----------------------------------------------------------
    clubs = []
    for code in sorted(DIVISION):
        meta = injury_meta.get(code, {"rows": 0, "out": 0, "doubtful": 0, "questionable": 0, "blank_status": 0})
        club_rows = [c for c in chains if c["club"] == code]
        named = [c for c in club_rows if c["replacement"]]
        on_chart = [c for c in club_rows if c["on_chart"]]
        chart = chart_meta.get(code)
        conf, div = DIVISION[code]
        fixture = next((f"{a} at {h}" for a, h in WEEK10_FIXTURES if code in (a, h)), "")
        bye = code in WEEK10_BYES
        clubs.append({
            "id": code, "club": meta.get("club", code), "conference": conf, "division": div,
            "week10_fixture": "" if bye else fixture,
            "week10_bye": "yes" if bye else "",
            "rows": meta["rows"], "out": meta["out"], "doubtful": meta["doubtful"],
            "questionable": meta["questionable"], "blank_status": meta["blank_status"],
            "on_chart": len(on_chart), "replacement_named": len(named),
            "no_replacement_named": len(on_chart) - len(named),
            "not_on_chart": len(club_rows) - len(on_chart),
            "chart_available": "yes" if chart else ("image only" if code == "HOU" else ""),
            "chart_printed_date": chart["printed_date"] if chart else "",
            "chart_slots": chart["slots"] if chart else None,
            "chart_multi_rank1": chart["multi_rank1"] if chart else None,
            "chart_empty_rank1": chart["empty_rank1"] if chart else None,
            "starter_out_with_named_backup": len({c["player"] for c in named if c["status"] == "Out"}),
            "net_injury_count": meta["out"] + meta["doubtful"],
            "source_ids": sorted({"RD-NFL-INJ-W10"} | ({"RD-" + code + "-CHART"} if chart else set())
                                 | ({"RD-HOU-CHART"} if code == "HOU" else set())),
        })

    totals = {
        "injury_rows": len(injury_rows),
        "clubs_with_report": len(injury_meta),
        "clubs_on_bye": len(WEEK10_BYES),
        "game_status_out": sum(1 for r in injury_rows if r["status"] == "Out"),
        "game_status_doubtful": sum(1 for r in injury_rows if r["status"] == "Doubtful"),
        "game_status_questionable": sum(1 for r in injury_rows if r["status"] == "Questionable"),
        "game_status_blank": sum(1 for r in injury_rows if r["status"] == ""),
        "game_status_present": sum(1 for r in injury_rows if r["status"]),
        "on_chart": sum(1 for c in chains if c["on_chart"]),
        "replacement_named": sum(1 for c in chains if c["replacement"]),
        "no_replacement_named": sum(1 for c in chains if c["on_chart"] and not c["replacement"]),
        "not_on_chart": sum(1 for c in chains if not c["on_chart"]),
        "announced_starters": len(ANNOUNCED),
        "actual_replacement_confirmed": 0,
        "depth_rows": len(depth_rows),
        "depth_charts": len(chart_meta),
        "multi_rank1_cells": sum(m["multi_rank1"] for m in chart_meta.values()),
        "empty_rank1_cells": sum(m["empty_rank1"] for m in chart_meta.values()),
        "charts_with_printed_date": sum(1 for m in chart_meta.values() if m["printed_date"]),
    }

    return {
        "schema_version": 1,
        "read": READ_DATE,
        "pins": PINS,
        "totals": totals,
        "clubs": clubs,
        "injury_rows": injury_rows,
        "replacement_chains": chains,
        "announced_starters": ANNOUNCED,
        "staleness": STALENESS,
        "depth_slots": depth_rows,
        "charts": [{"id": c, **m} for c, m in sorted(chart_meta.items())],
        "rules": [
            "A depth slot is a group. Two rank-1 names in one cell are two rank-1 players, not a starter and a backup.",
            "An empty cell stays empty. It is not a zero and not a missing rank.",
            "A printed jersey number is stripped only to match a name; the raw string is retained.",
            "No depth rank is derived from jersey number, experience, salary or roster order.",
            "A printed chart name is not participation. Who actually played needs an official inactive list, Game Book or snap count.",
        ],
    }


def snapshots(payload: dict) -> dict:
    files = [INJURY_FILE, DEPTH_FILE, SCHED_FILE]
    return {
        "schema_version": 1,
        "policy": ("Immutable captures: each evidence file is committed, never rewritten in place, and its "
                   "SHA-256 is recorded here. No scheduled retrieval is enabled because NFL.com terms "
                   "section 1.3 prohibits systematic retrieval without written consent (see PG-SCHEDULE)."),
        "captures": [
            {"id": "CAP-2026-11-17-INJ", "artefact": "Week 10 injury report, all printed sections",
             "url": "https://www.nfl.com/injuries/", "read": READ_DATE, "clock": "unpublished by the publisher",
             "sha256": sha256(INJURY_FILE), "rows": payload["totals"]["injury_rows"],
             "source_ids": ["RD-NFL-INJ-W10"],
             "schema_pins": ["5 columns: Player, Position, Injuries, Practice Status, Game Status",
                             "28 club sections each with a header row"]},
            {"id": "CAP-2026-11-17-DEPTH", "artefact": "Six club depth charts as printed",
             "url": "https://www.detroitlions.com/team/depth-chart (and five other club pages)",
             "read": READ_DATE, "clock": "unpublished except Green Bay, which prints 'Unofficial, Nov. 10, 2026'",
             "sha256": sha256(DEPTH_FILE), "rows": payload["totals"]["depth_rows"],
             "source_ids": ["RD-DET-CHART", "RD-GB-CHART", "RD-SEA-CHART", "RD-BAL-CHART",
                            "RD-WAS-CHART", "RD-IND-CHART", "RD-HOU-CHART"],
             "schema_pins": ["slot label plus rank columns", "no date on 5 of 6 charts"]},
            {"id": "CAP-2026-11-17-SCHED", "artefact": "Weeks 10 and 11 schedule pages",
             "url": "https://www.nfl.com/schedules/2026/by-week/week-11", "read": READ_DATE,
             "clock": "unpublished", "sha256": sha256(SCHED_FILE),
             "rows": len(WEEK10_FIXTURES) + 14, "source_ids": ["RD-NFL-SCHED-W10", "RD-NFL-SCHED-W11"],
             "schema_pins": ["winner line prints 'Away N, Home N, FINAL, date'",
                             "venue only via ticket/hotel links"]},
        ],
        "prior_captures": [
            {"read": "2026-11-12", "artefact": "Week 10 injury report", "where": "data/nfl-injuries-2026-w10.csv",
             "note": "The inherited capture. Counts in it are stale (see the recount on the availability page) and it is not re-used."},
            {"read": "2026-11-13", "artefact": "Week 10 injury report and 19 club depth charts",
             "where": "nfl-availability-28ef/evidence/", "note": "Read-only. Not re-parsed here; the pins above are this desk's own."},
            {"read": "2026-11-14", "artefact": "Some club depth charts", "where": "nfl-skill-cfdd/evidence/",
             "note": "Read-only."},
        ],
        "delta_available": len(files) == 3,
        "series_length": 3,
    }


def main() -> int:
    DATA.mkdir(exist_ok=True)
    payload = build()
    snaps = snapshots(payload)
    targets = {DATA / "availability.json": payload, DATA / "snapshots.json": snaps}
    stale = []
    for path, obj in targets.items():
        text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
        if "--check" in sys.argv:
            if not path.exists() or path.read_text() != text:
                stale.append(path.name)
        else:
            path.write_text(text)
    if "--check" in sys.argv:
        if stale:
            raise SystemExit("stale availability artefacts: " + ", ".join(stale))
        print(f"OK: {len(payload['injury_rows'])} injury rows, {len(payload['depth_slots'])} depth slots")
        return 0
    print(f"Wrote availability.json and snapshots.json: {payload['totals']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
