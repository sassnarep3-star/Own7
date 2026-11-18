#!/usr/bin/env python3
"""Build the NFL snap-count / playing-time desk (nfl-snapcount-e5e4).

Every value published by this desk is transcribed from the official NFL Game Book
**Playtime Percentage** table (snap counts and snap share on Offense, Defense and
Special Teams), linked from the official NFL Game Centre. Nothing is inferred: where
the official artefact does not publish a value the cell is emitted blank and the row
is listed in the flag register.

This desk answers four open requirements from the brief:
  R11  model depth from playing time, never from jersey order;
  R31  capture official inactive lists and snap counts (snap counts here);
  R52  resolve the depth-order source - snap counts are the official source;
  R56  use snap counts as the starter proxy when the depth chart is unavailable.

Inputs (all committed, all read-only):
  raw/g*.txt   faithful line-by-line extracts of the 13 played Week 10 Game Books

Outputs: data/*.csv, data/*.json

The depth-vs-snap cross-reference reads the committed club depth-chart transcription
from the skill desk (nfl-skill-cfdd/data/depth-slots-2026-11-14.csv) read-only. The
four clubs captured there (CHI, DEN, PHI, TB) did not play in Week 10, so the
cross-reference yields zero joinable rows; the gap is published, never filled.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
RAW = HERE / "raw"
DATA = HERE / "data"
DATA.mkdir(exist_ok=True)

sys.path.insert(0, str(HERE))
import emit  # noqa: E402

CHECKED = "2026-11-18"
SOURCE_LABEL = "NFL Game Book - Playtime Percentage (official PDF)"
DEPTH_PATH = REPO / "nfl-skill-cfdd" / "data" / "depth-slots-2026-11-14.csv"

# position (as published) -> coarse position group used for snap-share aggregation.
# Kept explicit and fixed so the grouping is reproducible and auditable.
POSITION_GROUP = {
    "OL": "Offensive Line", "T": "Offensive Line", "G": "Offensive Line",
    "C": "Offensive Line", "T/G": "Offensive Line", "G/C": "Offensive Line",
    "G/T": "Offensive Line", "C/G": "Offensive Line",
    "QB": "Quarterback",
    "RB": "Running Back", "FB": "Running Back", "HB": "Running Back",
    "WR": "Wide Receiver", "WR/CB": "Wide Receiver",
    "TE": "Tight End",
    "K": "Special Teams (K/P/LS)", "P": "Special Teams (K/P/LS)", "LS": "Special Teams (K/P/LS)",
    "DL": "Defensive Line", "DT": "Defensive Line", "DE": "Defensive Line", "NT": "Defensive Line",
    "LB": "Linebacker",
    "CB": "Cornerback",
    "S": "Safety / Defensive Back", "DB": "Safety / Defensive Back",
}


def parse_raw(path: Path) -> dict:
    """Parse one raw Game Book extract into meta + a list of snap rows."""
    meta = {"raw_file": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        tag = parts[0]
        if tag == "SOURCE":
            meta["source_url"] = parts[1]
        elif tag == "GAMECENTER":
            meta["gamecenter_url"] = parts[1]
        elif tag == "CAPTURED_UTC":
            meta["captured_utc"] = parts[1]
        elif tag == "TABLE_LABEL":
            meta["table_label"] = parts[1]
        elif tag == "GAME":
            (meta["game_id"], meta["away"], meta["home"], meta["date"],
             meta["stadium"], meta["location"]) = parts[1:7]
        elif tag == "PLAYTIME":
            # PLAYTIME|<team>|<player>|<pos>|<off_snaps>|<off_pct>|<def_snaps>|<def_pct>|<st_snaps>|<st_pct>
            # Trailing blank cells are dropped by split(), so pad to 10 fields.
            parts = parts + [""] * (10 - len(parts))
            rows.append({
                "team": parts[1],
                "player": parts[2],
                "position": parts[3],
                "off_snaps": parts[4],
                "off_pct": parts[5],
                "def_snaps": parts[6],
                "def_pct": parts[7],
                "st_snaps": parts[8],
                "st_pct": parts[9],
            })
        else:
            raise SystemExit(f"unknown tag {tag!r} in {path.name}")
    return meta, rows


def to_int(value: str) -> int:
    """'65' -> 65; '' or ' ' -> 0 (did not play that phase)."""
    return int(value) if value.strip() else 0


def total_snaps(row: dict) -> int:
    return to_int(row["off_snaps"]) + to_int(row["def_snaps"]) + to_int(row["st_snaps"])


# ---------------------------------------------------------------- load raw

raw_files = sorted(RAW.glob("g*.txt"))
games = []
all_rows = []
duplicate_notes = []
for rf in raw_files:
    meta, rows = parse_raw(rf)
    # PDF pagination can repeat a row at a page break (e.g. a kicker whose ST
    # snaps appear once in the body and once in the continuation tail). Dedupe on
    # (team, player, position), keeping the more complete row; record each merge.
    best: dict[tuple, dict] = {}
    for r in rows:
        key = (r["team"], r["player"], r["position"])
        r["_complete"] = sum(1 for k in ("off_snaps", "def_snaps", "st_snaps") if r[k].strip())
        if key in best:
            duplicate_notes.append(
                {"raw_file": rf.name, "game_id": meta["game_id"], "team": r["team"],
                 "player": r["player"], "position": r["position"],
                 "detail": "row repeated by PDF pagination; the more complete of the two kept"})
            if r["_complete"] > best[key]["_complete"]:
                best[key] = r
        else:
            best[key] = r
    rows = list(best.values())
    games.append(meta)
    for r in rows:
        r.update(meta)
        all_rows.append(r)

by_game = {g["game_id"]: g for g in games}

# ------------------------------------------------------- per-game snap records
# One row per player per game: the verbatim snap counts and share for each phase.
snap_records = []
for idx, r in enumerate(all_rows, start=1):
    snap_records.append({
        "snap_id": f"SN{idx:04d}",
        "game_id": r["game_id"],
        "date": r["date"],
        "venue": r["stadium"],
        "team": r["team"],
        "player": r["player"],
        "position": r["position"],
        "off_snaps": r["off_snaps"] or "",
        "off_pct": r["off_pct"] or "",
        "def_snaps": r["def_snaps"] or "",
        "def_pct": r["def_pct"] or "",
        "st_snaps": r["st_snaps"] or "",
        "st_pct": r["st_pct"] or "",
        "total_snaps": total_snaps(r),
        "table_label": r.get("table_label", ""),
        "source_url": r["source_url"],
        "raw_file": r["raw_file"],
        "raw_sha256": r["sha256"],
    })

# ------------------------------- per-team position-group snap shares (per game)
# For each game, team and position group: total snaps on each phase, and the share
# of that team's phase snaps. Purely arithmetic over the transcribed snap counts.
group_shares = []
for g in games:
    team_phase = defaultdict(int)      # (team, phase) -> total snaps
    team_group_phase = defaultdict(int)  # (team, group, phase) -> total snaps
    for r in all_rows:
        if r["game_id"] != g["game_id"]:
            continue
        group = POSITION_GROUP.get(r["position"], "Ungrouped")
        for phase, key in (("Offense", "off_snaps"), ("Defense", "def_snaps"),
                           ("Special Teams", "st_snaps")):
            n = to_int(r[key])
            if n:
                team_phase[(r["team"], phase)] += n
                team_group_phase[(r["team"], group, phase)] += n
    for (team, group, phase), snaps in sorted(team_group_phase.items()):
        team_total = team_phase[(team, phase)]
        group_shares.append({
            "game_id": g["game_id"],
            "team": team,
            "position_group": group,
            "phase": phase,
            "snaps": snaps,
            "team_phase_snaps": team_total,
            "share": round(snaps / team_total, 4) if team_total else "",
            "source_url": g["source_url"],
            "raw_file": g["raw_file"],
        })

# --------------------------------------------- playing-time depth (R11, R52, R56)
# For each game, team, position group and phase, rank the players who played that
# phase by snap count. Rank 1 is the playing-time starter. This order comes from
# playing time only - never from jersey number, experience or salary.
playtime_depth = []
for g in games:
    keys = defaultdict(list)
    for r in all_rows:
        if r["game_id"] != g["game_id"]:
            continue
        group = POSITION_GROUP.get(r["position"], "Ungrouped")
        for phase, key in (("Offense", "off_snaps"), ("Defense", "def_snaps"),
                           ("Special Teams", "st_snaps")):
            n = to_int(r[key])
            if n:
                keys[(r["team"], group, phase)].append((n, r))
    for (team, group, phase), entries in sorted(keys.items()):
        entries.sort(key=lambda t: (-t[0], t[1]["player"]))
        for rank, (n, r) in enumerate(entries, start=1):
            playtime_depth.append({
                "depth_id": f"PD{len(playtime_depth) + 1:04d}",
                "game_id": g["game_id"],
                "team": team,
                "position_group": group,
                "position": r["position"],
                "phase": phase,
                "player": r["player"],
                "snaps": n,
                "depth_rank": rank,
                "role": "Starter (by playing time)" if rank == 1
                        else f"Backup #{rank} (by playing time)",
                "source_url": g["source_url"],
                "raw_file": g["raw_file"],
            })

# ------------------------------------------------- replacement-depth view
# For each game + team + position group + phase, the playing-time starter and the
# next player(s) behind them - i.e. who would replace the starter if he left, ranked
# by the snaps they actually played. This is the snap-count replacement depth.
replacement_rows = []
for g in games:
    by_slot = defaultdict(list)
    for r in all_rows:
        if r["game_id"] != g["game_id"]:
            continue
        group = POSITION_GROUP.get(r["position"], "Ungrouped")
        for phase, key in (("Offense", "off_snaps"), ("Defense", "def_snaps"),
                           ("Special Teams", "st_snaps")):
            n = to_int(r[key])
            if n:
                by_slot[(r["team"], group, phase)].append((n, r))
    for (team, group, phase), entries in sorted(by_slot.items()):
        entries.sort(key=lambda t: (-t[0], t[1]["player"]))
        if not entries:
            continue
        starter_n, starter = entries[0]
        backups = entries[1:]
        for b_rank, (b_n, b) in enumerate(backups, start=1):
            replacement_rows.append({
                "replacement_id": f"RP{len(replacement_rows) + 1:04d}",
                "game_id": g["game_id"],
                "team": team,
                "position_group": group,
                "phase": phase,
                "starter_player": starter["player"],
                "starter_snaps": starter_n,
                "replacement_player": b["player"],
                "replacement_snaps": b_n,
                "replacement_rank": b_rank,
                "source_url": g["source_url"],
                "raw_file": g["raw_file"],
            })

# ---------------------------------- depth-vs-snap cross-reference (read-only)
# Join the committed club depth-chart transcription to the snap counts. The four
# captured clubs did not play in Week 10, so this is a published zero-row gap.
depth_rows = []
if DEPTH_PATH.exists():
    with DEPTH_PATH.open(newline="", encoding="utf-8") as fh:
        depth_rows = list(csv.DictReader(fh))
playing_clubs = {r["team"] for r in all_rows}
depth_clubs = {r["club_abbr"] for r in depth_rows}
depth_vs_snap = []
for r in depth_rows:
    if r["club_abbr"] in playing_clubs:
        depth_vs_snap.append({
            "depth_id": r["depth_id"],
            "club": r["club_abbr"],
            "unit": r["unit"],
            "position": r["position"],
            "rank": r["rank"],
            "depth_player": r["player"],
            "snap_source": "not joined - see flagged page",
            "source_url": r["source_url"],
        })

# ------------------------------------------------------------- ledger + flags
ledger = []
for g in games:
    ledger.append({
        "artifact": f"Game Book {g['game_id']} {g['away']}@{g['home']} - Playtime Percentage",
        "vintage": f"{g['date']} game; captured {g['captured_utc']}",
        "captured_utc": g["captured_utc"],
        "sha256": g["sha256"],
        "raw_file": g["raw_file"],
        "source_url": g["source_url"],
        "table_label": g.get("table_label", ""),
        "immutable": "yes",
    })

flags = [
    {
        "flag_id": "SN-F01",
        "item": "Playtime Percentage tables labelled '(Unofficial)' in the official Game Book",
        "detail": (
            "Four of the thirteen Week 10 Game Books print the Playtime Percentage table "
            "with an '(Unofficial)' label (g05 HOU@CLE, g09 BUF@NYJ, g11 SEA@LV, g13 LAR@AZ). "
            "The table is still the one published inside the official NFL Game Book PDF linked "
            "from the official Game Centre; the label is recorded verbatim on each row and the "
            "desk does not treat these as a different source class. The desk does not claim the "
            "label was removed or that these counts are certified official statistics."
        ),
        "value_published": "the transcribed snap counts (label carried)",
        "why_blank": "",
        "source_url": "https://static.www.nfl.com/image/upload/v1794829724/gamecenter/ab583279-4feb-11f1-abca-2c54536568a9.pdf",
        "route": "none - the label is part of the official artefact and is published as printed",
    },
    {
        "flag_id": "SN-F02",
        "item": "Depth-vs-snap cross-reference returns zero joinable rows",
        "detail": (
            "The committed official club depth-chart transcription "
            "(nfl-skill-cfdd/data/depth-slots-2026-11-14.csv) covers CHI, DEN, PHI and TB "
            "only. None of the four played in Week 10, so there is no game in which to "
            "compare a printed depth order against actual snap counts. The cross-reference "
            "is therefore a published zero-row gap, not a satisfied join."
        ),
        "value_published": "0 joinable rows",
        "why_blank": "no overlap between the four depth-chart clubs and the 26 clubs that played",
        "source_url": "https://www.chicagobears.com/team/depth-chart",
        "route": "capture official depth charts for the 26 clubs that played in Week 10",
    },
    {
        "flag_id": "SN-F03",
        "item": "LAC @ BAL (W10-14) has no Playtime Percentage table",
        "detail": (
            "The fourteenth Week 10 fixture (LAC @ BAL, Monday 2026-11-16) had not produced a "
            "Game Book at capture time, so no Playtime Percentage table exists for it. The desk "
            "publishes the 13 played fixtures only; the 14th is carried as a known gap."
        ),
        "value_published": "",
        "why_blank": "the official Game Book for W10-14 was not available at capture",
        "source_url": "https://www.nfl.com/games/chargers-at-ravens-2026-reg-10",
        "route": "re-capture the W10-14 Game Book after the game is final",
    },
]
for note in duplicate_notes:
    flags.append({
        "flag_id": f"SN-DUP-{len(flags) + 1:02d}",
        "item": f"Repeated Playtime Percentage row: {note['player']} ({note['team']}, {note['position']})",
        "detail": (
            f"In {note['raw_file']} ({note['game_id']}) the official PDF repeated the row for "
            f"{note['player']} at a page break. The more complete of the two occurrences was "
            f"kept; the repetition is a pagination artefact of the PDF, not a second appearance."
        ),
        "value_published": "one deduplicated row",
        "why_blank": "",
        "source_url": note and by_game[note["game_id"]]["source_url"],
        "route": "none - the dedup rule is deterministic and recorded",
    })

summary = {
    "generated_utc": CHECKED,
    "raw_files": len(raw_files),
    "games_captured": len(games),
    "fixtures_in_week10_slate": 14,
    "snap_record_rows": len(snap_records),
    "players_captured": len(snap_records),
    "position_group_share_rows": len(group_shares),
    "playtime_depth_rows": len(playtime_depth),
    "replacement_depth_rows": len(replacement_rows),
    "depth_vs_snap_joinable_rows": len(depth_vs_snap),
    "depth_chart_clubs_captured": len(depth_clubs),
    "playing_clubs_in_week10": len(playing_clubs),
    "tables_labelled_unofficial": sum(1 for g in games if g.get("table_label") == "Unofficial"),
    "duplicate_rows_merged": len(duplicate_notes),
    "flags": len(flags),
}

# ------------------------------------------------------------------ emit
emit.emit_csv(DATA / "snap-records.csv", snap_records)
emit.emit_csv(DATA / "position-group-shares.csv", group_shares)
emit.emit_csv(DATA / "playtime-depth.csv", playtime_depth)
emit.emit_csv(DATA / "replacement-depth.csv", replacement_rows)
# The depth-vs-snap join is a published zero-row gap. Emit a header-only CSV so the
# empty table is explicit and auditable rather than silently absent.
DVS_FIELDS = ["depth_id", "club", "unit", "position", "rank", "depth_player",
              "snap_source", "source_url"]
if depth_vs_snap:
    emit.emit_csv(DATA / "depth-vs-snap.csv", depth_vs_snap)
else:
    import io
    buf = io.StringIO(newline="")
    csv.DictWriter(buf, fieldnames=DVS_FIELDS).writeheader()
    emit.emit(DATA / "depth-vs-snap.csv", buf.getvalue())
emit.emit_json(DATA / "capture-summary.json", summary)
emit.emit_json(DATA / "snapshot-ledger.json", ledger)
emit.emit_json(DATA / "flags.json", flags)

print(json.dumps(summary, indent=2))
