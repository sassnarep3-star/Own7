#!/usr/bin/env python3
"""Build the official Game Book desk.

Every value published by this desk is transcribed from an official NFL Game Book
PDF (linked from the official Game Centre) or an official NFL injury report.
Nothing is inferred. Where an official artefact does not publish a value, the
cell is emitted blank and the row is listed in the flag register.

Inputs (all committed, all read-only):
  raw/g*.txt                     faithful line-by-line extracts of the Game Books
  ../nfl-skill-cfdd/data/depth-slots-2026-11-14.csv     official club depth charts
  ../nfl-availability-28ef/data/injuries-week10-2026.csv  published 2026-11-13 report
  ../nfl-availability-28ef/data/games-week10-2026.csv
  data/injuries-live-2026-11-17.csv                     this session's live re-capture

Outputs: data/*.csv, data/*.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
RAW = ROOT / "raw"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

SOURCE_LABEL = "NFL Game Book (official PDF)"
INJURY_LIVE_URL = "https://www.nfl.com/injuries/league/2026/REG10"
INJURY_LIVE_LABEL = "NFL injury report (official, live re-capture)"

# ---------------------------------------------------------------- raw parsing


def parse_raw(path: pathlib.Path):
    meta = {}
    games, starters, inactives = [], [], []
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
        elif tag == "GAME":
            (
                meta["game_id"],
                meta["away"],
                meta["home"],
                meta["date"],
                meta["kickoff"],
                meta["stadium"],
                meta["location"],
                meta["roof_surface"],
                meta["weather"],
                meta["temp_f"],
                meta["humidity"],
                meta["wind"],
                meta["attendance"],
            ) = parts[1:14]
        elif tag in ("OFF", "DEF"):
            starters.append(
                {
                    "club": parts[1],
                    "unit": "Offense" if tag == "OFF" else "Defense",
                    "position": parts[2],
                    "jersey": parts[3],
                    "player": parts[4],
                }
            )
        elif tag == "INA":
            inactives.append(
                {
                    "club": parts[1],
                    "designation": parts[2],
                    "jersey": parts[3],
                    "player": parts[4],
                }
            )
        else:
            raise SystemExit(f"unknown tag {tag!r} in {path.name}")
    meta["raw_file"] = path.name
    meta["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return meta, starters, inactives


SUFFIXES = ("iii", "ii", "iv", "jr", "sr")


def surname(player: str) -> str:
    """'A.Williams' -> 'Williams'; 'A.St. Brown' -> 'St. Brown'; 'Dr.Jones' -> 'Jones'."""
    cleaned = player.strip()
    if "." in cleaned:
        cleaned = cleaned.split(".", 1)[1]
    return cleaned.strip().lower()


def gamebook_token(player: str):
    """Split an official Game Book name into (initial, name-remainder, pre-dot token)."""
    p = player.strip()
    if "." not in p:
        return ("", norm(p), "")
    head, rest = p.split(".", 1)
    pre = norm(head)          # e.g. 'ma' from 'Ma.Wilson', 'dr' from 'Dr.Jones'
    initial = norm(head)[:1]
    return (initial, norm(rest), pre)


def full_name_keys(player: str):
    """Candidate normalized keys for a full name, suffix stripped."""
    n = norm(player)
    for suf in SUFFIXES:
        if n.endswith(suf) and len(n) > len(suf) + 3:
            n = n[: -len(suf)]
            break
    return n


def name_matches(gamebook_name: str, full_name: str) -> bool:
    """Does an official Game Book abbreviated name denote this full name?

    Requires: the full name ends with the Game Book remainder, AND the leading
    character matches. Handles 'C.Davis' vs 'Carlton Davis III' and
    'A.St. Brown' vs 'Amon-Ra St. Brown'. Anything not provable is False.
    """
    initial, remain, pre = gamebook_token(gamebook_name)
    key = full_name_keys(full_name)
    if not remain or not key:
        return False
    if not key.endswith(remain):
        return False
    if initial and key[0] != initial:
        # allow prefixed given names such as 'Ma.Wilson' for 'Malik Wilson'
        if not (pre and key.startswith(pre)):
            return False
    return True


def find_inactive(rows, club, gid, full_name):
    """Unique official Not Active row for a named player, or None if 0 or >1 match."""
    hits = [r for r in rows if r["club"] == club and name_matches(r["player"], full_name)]
    return hits[0] if len(hits) == 1 else None


def norm(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())


# ------------------------------------------------------------------- load raw
raw_files = sorted(RAW.glob("g*.txt"))
games_meta, all_starters, all_inactives = [], [], []
for rf in raw_files:
    meta, starters, inactives = parse_raw(rf)
    games_meta.append(meta)
    for s in starters:
        s.update(meta)
        all_starters.append(s)
    for i in inactives:
        i.update(meta)
        all_inactives.append(i)

by_game = {g["game_id"]: g for g in games_meta}

# ------------------------------------------------------- fixtures + venue table
fixture_rows = []
for g in games_meta:
    fixture_rows.append(
        {
            "game_id": g["game_id"],
            "date": g["date"],
            "kickoff_official": g["kickoff"],
            "away": g["away"],
            "home": g["home"],
            "venue_city_state": g["location"],
            "stadium": g["stadium"],
            "roof_and_surface": g["roof_surface"],
            "game_weather": g["weather"],
            "temp_f": g["temp_f"],
            "humidity_pct": g["humidity"],
            "wind": g["wind"],
            "paid_attendance": g["attendance"],
            "source_url": g["source_url"],
            "source_label": SOURCE_LABEL,
            "gamecenter_url": g["gamecenter_url"],
            "captured_utc": g["captured_utc"],
            "raw_file": g["raw_file"],
            "raw_sha256": g["sha256"],
        }
    )

# The Week 10 slate is 14 fixtures. The 14th (LAC @ BAL) had not been played at
# capture time, so no Game Book exists. Publish the gap explicitly.
BAL_LAC = {
    "game_id": "W10-14",
    "date": "2026-11-16",
    "kickoff_official": "8:15 PM EST",
    "away": "LAC",
    "home": "BAL",
    "venue_city_state": "BALTIMORE, MD",
    "stadium": "M&T BANK STADIUM",
    "roof_and_surface": "",
    "game_weather": "",
    "temp_f": "",
    "humidity_pct": "",
    "wind": "",
    "paid_attendance": "",
    "source_url": "https://www.nfl.com/games/chargers-at-ravens-2026-reg-10",
    "source_label": "NFL Game Centre (official) - fixture not yet played at capture",
    "gamecenter_url": "https://www.nfl.com/games/chargers-at-ravens-2026-reg-10",
    "captured_utc": "2026-11-17",
    "raw_file": "",
    "raw_sha256": "",
}

# -------------------------------------------------------- starters (official)
starter_rows = []
for idx, s in enumerate(all_starters, start=1):
    starter_rows.append(
        {
            "starter_id": f"S{idx:04d}",
            "game_id": s["game_id"],
            "club": s["club"],
            "unit": s["unit"],
            "position": s["position"],
            "jersey": s["jersey"],
            "player": s["player"],
            "status": "Official starter (Game Book lineup)",
            "source_url": s["source_url"],
            "source_label": SOURCE_LABEL,
            "captured_utc": s["captured_utc"],
        }
    )

# ------------------------------------------------------ inactives (official)
inactive_rows = []
for idx, i in enumerate(all_inactives, start=1):
    inactive_rows.append(
        {
            "inactive_id": f"N{idx:04d}",
            "game_id": i["game_id"],
            "club": i["club"],
            "designation": i["designation"],
            "jersey": i["jersey"],
            "player": i["player"],
            "status": "Official Not Active",
            "source_url": i["source_url"],
            "source_label": SOURCE_LABEL,
            "captured_utc": i["captured_utc"],
        }
    )

# ------------------------------------- depth charts (official club pages, read-only)
depth_path = ROOT.parent / "nfl-skill-cfdd" / "data" / "depth-slots-2026-11-14.csv"
depth_rows = list(csv.DictReader(depth_path.open(encoding="utf-8")))

# rank-1 players per (club, unit, position) as the club published them
depth_lookup: dict[tuple[str, str, str], list[dict]] = {}
for d in depth_rows:
    depth_lookup.setdefault((d["club_abbr"], d["unit"], d["position"]), []).append(d)

# -------------------------------------------- availability graph (first-class)
# expected starter = rank-1 name(s) on the official club depth chart for the
# slot's unit/position family; actual starter = name printed in the Game Book
# lineup for the same slot. Neither side is inferred.
UNIT_POS = {
    "Offense": {"QB", "RB", "FB", "WR", "TE", "LT", "LG", "C", "RG", "RT", "LOT", "ROT", "HB"},
    "Defense": {
        "DE", "DT", "NT", "DL", "LB", "ILB", "OLB", "EDGE", "CB", "S", "DB", "SS", "FS",
        "LDE", "RDE",
    },
}

# Which Game Book position maps to which depth-chart position(s).
POS_FAMILY = {
    "QB": ["QB"],
    "RB": ["RB"],
    "FB": ["FB", "RB"],
    "HB": ["RB"],
    "WR": ["WR"],
    "TE": ["TE"],
    "LT": ["LT", "T"],
    "LOT": ["LT", "T"],
    "LG": ["LG", "G"],
    "C": ["C"],
    "RG": ["RG", "G"],
    "RT": ["RT", "T"],
    "ROT": ["RT", "T"],
    "DE": ["DE", "DL", "EDGE"],
    "LDE": ["DE", "DL", "EDGE"],
    "RDE": ["DE", "DL", "EDGE"],
    "DT": ["DT", "DL", "NT"],
    "NT": ["NT", "DT", "DL"],
    "DL": ["DL", "DT", "DE", "NT"],
    "EDGE": ["EDGE", "OLB", "DE", "DL"],
    "LB": ["LB", "ILB", "OLB"],
    "ILB": ["ILB", "LB"],
    "OLB": ["OLB", "LB", "EDGE"],
    "CB": ["CB", "DB"],
    "DB": ["DB", "CB", "S"],
    "S": ["S", "SS", "FS", "DB"],
}

# clubs whose official depth chart is published per unit
DEPTH_CLUBS = {d["club_abbr"] for d in depth_rows}

avail_rows = []
avail_id = 0

for gid, g in by_game.items():
    for club in (g["away"], g["home"]):
        team_starters = [s for s in all_starters if s["game_id"] == gid and s["club"] == club]
        if not team_starters:
            continue
        team_ina = [i for i in all_inactives if i["game_id"] == gid and i["club"] == club]
        if club not in DEPTH_CLUBS:
            continue  # no official depth chart captured for this club -> nothing to join
        for st in team_starters:
            avail_id += 1
            unit = st["unit"]
            fams = POS_FAMILY.get(st["position"], [st["position"]])
            candidates = []
            for fam in fams:
                candidates.extend(depth_lookup.get((club, unit, fam), []))
            rank1 = [c for c in candidates if c["rank"] == "1"]
            rank1_names = sorted({c["player"] for c in rank1})
            actual = st["player"]
            in_rank1 = any(name_matches(actual, n) for n in rank1_names)
            if not rank1_names:
                verdict = "No official rank-1 published for this slot"
            elif in_rank1:
                verdict = "Confirmed: actual starter is the published rank-1"
            else:
                verdict = "Substitution: actual starter is not the published rank-1"
            replacement = ""
            if verdict.startswith("Substitution"):
                # Is the actual starter himself on the official Not Active list? (no)
                # Was he published on the depth chart at a lower rank? (depth of the replacement)
                lower = [c for c in candidates if name_matches(actual, c["player"])]
                if lower:
                    replacement = "; ".join(
                        f"rank {c['rank']} on official chart" for c in sorted(lower, key=lambda x: x["rank"])
                    )
                else:
                    replacement = "not listed on the official depth chart for this slot"
            avail_rows.append(
                {
                    "availability_id": f"AV{avail_id:04d}",
                    "game_id": gid,
                    "club": club,
                    "unit": unit,
                    "position_as_printed": st["position"],
                    "expected_starter_official": " / ".join(rank1_names),
                    "actual_starter_official": actual,
                    "verdict": verdict,
                    "replacement_depth_evidence": replacement,
                    "also_not_active": (
                        "yes" if find_inactive(team_ina, club, gid, actual) else "no"
                    ),
                    "depth_source_url": rank1[0]["source_url"] if rank1 else "",
                    "depth_chart_date": rank1[0]["chart_date_printed"] if rank1 else "",
                    "gamebook_source_url": st["source_url"],
                }
            )

# ------------------------------------------- designation reliability (empirical)
# For every player the official injury report lists, did the official Game Book
# put him on Not Active? Observed rate + Wilson 95% interval. No legacy number.
pub_inj_path = ROOT.parent / "nfl-availability-28ef" / "data" / "injuries-week10-2026.csv"
pub_inj = list(csv.DictReader(pub_inj_path.open(encoding="utf-8", newline="")))

# game_id mapping: published report game ids (W10-01..) vs Game Book ids.
# Match on the club pair to avoid trusting an unverified ordering.
pub_games = {}
for r in csv.DictReader(
    (ROOT.parent / "nfl-availability-28ef" / "data" / "games-week10-2026.csv").open(
        encoding="utf-8", newline=""
    )
):
    pub_games[r["game_id"]] = (r["away_abbr"], r["home_abbr"])

pair_to_book = {}
for gid, g in by_game.items():
    pair_to_book[(g["away"], g["home"])] = gid

report_game_to_book = {}
for pid, (away, home) in pub_games.items():
    if (away, home) in pair_to_book:
        report_game_to_book[pid] = pair_to_book[(away, home)]


def wilson(k: int, n: int, z: float = 1.959963985):
    if n == 0:
        return ("", "")
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)) / denom
    return (round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4))


def designation_key(raw: str) -> str:
    r = (raw or "").strip().lower()
    if r in ("out", "o"):
        return "Out"
    if r in ("questionable", "q"):
        return "Questionable"
    if r in ("doubtful", "d"):
        return "Doubtful"
    if r in ("", "-"):
        return "No game designation published"
    return raw.strip()


designation_rows = []
bucket_stats: dict[str, dict[str, int]] = {}
unmatched_examples = []
for r in pub_inj:
    book_gid = report_game_to_book.get(r["game_id"])
    if not book_gid:
        continue
    club = r["club_abbr"]
    ina = [find_inactive(all_inactives, club, book_gid, r["player"])]
    ina = [i for i in ina if i]
    key = designation_key(r["game_status"])
    st = bucket_stats.setdefault(key, {"n": 0, "inactive": 0})
    st["n"] += 1
    st["inactive"] += 1 if ina else 0
    if ina:
        unmatched_examples.append((r["player"], key, ina[0]["player"]))

for key in ("Out", "Questionable", "Doubtful", "No game designation published"):
    st = bucket_stats.get(key)
    if not st:
        continue
    lo, hi = wilson(st["inactive"], st["n"])
    designation_rows.append(
        {
            "published_designation": key,
            "n_players_joined": st["n"],
            "n_on_official_not_active": st["inactive"],
            "observed_inactive_rate": round(st["inactive"] / st["n"], 4),
            "wilson_95_low": lo,
            "wilson_95_high": hi,
            "method": "joined to official Game Book Not Active list; Wilson score interval",
            "injury_source_url": INJURY_LIVE_URL,
            "gamebook_source": SOURCE_LABEL,
        }
    )

# ------------------------------------------------------------- write the CSVs


def write_csv(name, rows, fields=None):
    if not rows:
        return
    fields = fields or list(rows[0].keys())
    with (DATA / name).open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


# ------------------------------------------- availability delta (what changed)
# as-known (official report, 2026-11-13) -> actual outcome (official Game Book).
# The level is published beside the delta, never instead of it.
delta_rows = []
delta_id = 0
for r in pub_inj:
    book_gid = report_game_to_book.get(r["game_id"])
    if not book_gid:
        continue
    delta_id += 1
    club = r["club_abbr"]
    ina = [find_inactive(all_inactives, club, book_gid, r["player"])]
    ina = [i for i in ina if i]
    designated = designation_key(r["game_status"])
    if ina:
        outcome = "deactivated - confirmed on official Not Active"
        changed = "no change (designation held)"
        if designated == "No game designation published":
            changed = "changed: no designation published, yet was not active"
    else:
        outcome = "not on official Not Active list"
        if designated in ("Out", "Doubtful", "Questionable"):
            changed = f"changed: published as {designated}, was not on Not Active"
        else:
            changed = "no change (no designation, not inactive)"
    delta_rows.append(
        {
            "delta_id": f"D{delta_id:04d}",
            "game_id_as_known": r["game_id"],
            "game_id_gamebook": book_gid,
            "club": club,
            "player": r["player"],
            "position": r["position"],
            "injury": r["injury"],
            "practice_status_as_known": r["practice_status"],
            "designation_as_known": r["game_status"],
            "outcome_from_gamebook": outcome,
            "delta": changed,
            "player_url_official": r.get("player_url", ""),
            "injury_report_url": INJURY_LIVE_URL,
            "gamebook_source_url": by_game[book_gid]["source_url"],
        }
    )

# ------------------------------------------- reserve-list / IR gap audit (VQ-06)
# Players absent from the weekly report are NOT necessarily available: they may
# sit on injured reserve. We cannot verify reserve status from these artefacts,
# so we surface the named cases as an explicit gap instead of asserting health.
reserve_gap = [
    {
        "player": "Malik Willis",
        "club_note": "absent from the Week 10 official injury report",
        "reserve_status_verified": "",
        "why_blank": "no official reserve/IR list was retrieved; absence from the injury report is not evidence of availability",
        "route": "retrieve the official reserve/injured list (club transactions or NFL transactions feed) and join on player id",
    },
    {
        "player": "Lamar Jackson",
        "club_note": "BAL; published at QB on the club depth chart while on injured reserve per prior session finding",
        "reserve_status_verified": "",
        "why_blank": "stale-depth claim from an earlier session; not re-verified against an official reserve list in this session",
        "route": "verify against the official reserve list before publishing any depth conclusion",
    },
    {
        "player": "Tyler Huntley",
        "club_note": "BAL; published at QB on the club depth chart while on injured reserve per prior session finding",
        "reserve_status_verified": "",
        "why_blank": "stale-depth claim from an earlier session; not re-verified against an official reserve list in this session",
        "route": "verify against the official reserve list before publishing any depth conclusion",
    },
]

# ------------------------------------- per-team view: out, replacement named
# For each club: official Not Active list, and for every inactive player whose
# position matches a Game Book lineup slot, the name of the player the official
# Game Book actually started at that position. No depth rank is inferred.
def starter_for_position(club, gid, position):
    fams = POS_FAMILY.get(position, [position])
    hits = [
        s
        for s in all_starters
        if s["game_id"] == gid and s["club"] == club and s["position"] in fams
    ]
    if not hits:
        return ""
    return "; ".join(f"{h['position']} {h['player']}" for h in hits)


team_rows = []
for gid, g in by_game.items():
    for club in (g["away"], g["home"]):
        ina = [i for i in all_inactives if i["game_id"] == gid and i["club"] == club]
        report = [r for r in pub_inj if report_game_to_book.get(r["game_id"]) == gid and r["club_abbr"] == club]
        designated_out = [r for r in report if designation_key(r["game_status"]) == "Out"]
        confirmed_out = [r for r in designated_out if find_inactive(all_inactives, club, gid, r["player"])]
        out_but_active = [r for r in designated_out if not find_inactive(all_inactives, club, gid, r["player"])]
        named = []
        for i in ina:
            repl = starter_for_position(club, gid, i["designation"])
            named.append(f"{i['designation']} {i['player']} -> {repl if repl else 'no matching lineup slot'}")
        team_rows.append(
            {
                "game_id": gid,
                "club": club,
                "official_not_active_count": len(ina),
                "report_rows_as_known": len(report),
                "published_out_count": len(designated_out),
                "published_out_and_inactive": len(confirmed_out),
                "published_out_but_not_inactive": len(out_but_active),
                "out_but_not_inactive_names": "; ".join(r["player"] for r in out_but_active),
                "inactive_and_official_replacement": " | ".join(named),
                "gamebook_source_url": g["source_url"],
                "injury_report_url": INJURY_LIVE_URL,
            }
        )

# ------------------------------- depth-chart coverage (the blocker for SG-05)
depth_coverage = []
for club in sorted({s["club"] for s in all_starters}):
    depth_coverage.append(
        {
            "club": club,
            "official_depth_chart_captured": "yes" if club in DEPTH_CLUBS else "no",
            "depth_rows": len([d for d in depth_rows if d["club_abbr"] == club]),
            "depth_source_url": next(
                (d["source_url"] for d in depth_rows if d["club_abbr"] == club), ""
            ),
            "consequence": (
                "official expected-starter join available"
                if club in DEPTH_CLUBS
                else "expected-starter join not computable - no official depth chart captured for this club"
            ),
        }
    )

write_csv("fixtures-venue.csv", fixture_rows)
write_csv("starters-official.csv", starter_rows)
write_csv("inactives-official.csv", inactive_rows)
write_csv("availability-graph.csv", avail_rows)
write_csv("designation-reliability.csv", designation_rows)
write_csv("availability-delta.csv", delta_rows)
write_csv("reserve-list-gaps.csv", reserve_gap)
write_csv("team-replacement-view.csv", team_rows)
write_csv("depth-chart-coverage.csv", depth_coverage)

# ------------------------------------------------------------- ledger + flags
ledger = []
for g in games_meta:
    ledger.append(
        {
            "artifact": f"Game Book {g['game_id']} {g['away']}@{g['home']}",
            "vintage": f"{g['date']} game; captured {g['captured_utc']}",
            "captured_utc": g["captured_utc"],
            "sha256": g["sha256"],
            "raw_file": g["raw_file"],
            "source_url": g["source_url"],
            "immutable": "yes",
        }
    )
ledger.append(
    {
        "artifact": "Official injury report Week 10 (as-known snapshot)",
        "vintage": "captured 2026-11-13, before kickoff",
        "captured_utc": "2026-11-13",
        "sha256": hashlib.sha256(pub_inj_path.read_bytes()).hexdigest(),
        "raw_file": "nfl-availability-28ef/data/injuries-week10-2026.csv",
        "source_url": INJURY_LIVE_URL,
        "immutable": "yes",
    }
)
ledger.append(
    {
        "artifact": "Official club depth charts (32 clubs)",
        "vintage": "chart date as printed per row",
        "captured_utc": "2026-11-14",
        "sha256": hashlib.sha256(depth_path.read_bytes()).hexdigest(),
        "raw_file": "nfl-skill-cfdd/data/depth-slots-2026-11-14.csv",
        "source_url": "per-club official depth chart pages (see depth_source_url column)",
        "immutable": "yes",
    }
)

flags = [
    {
        "flag_id": "GB-F01",
        "item": "Cleveland Browns and Dallas Cowboys defensive starters",
        "detail": (
            "Both official Game Books publish a defensive lineup, but in these two the "
            "PDF column lost its player-name cells during text extraction (Cowboys rows "
            "show e.g. 'OLB 40' with no name). 528 of 572 starting slots are captured; "
            "the 44 missing slots are Cleveland defense (22) and Dallas defense (22)."
        ),
        "value_published": "",
        "why_blank": "value not recoverable from the official artefact as retrieved; not inferred",
        "source_url": "https://static.www.nfl.com/image/upload/v1794829724/gamecenter/ab583279-4feb-11f1-abca-2c54536568a9.pdf",
        "route": "re-open the Game Book PDF in a viewer and transcribe the defensive column, or pull the same page from the NFL Stats feed",
    },
    {
        "flag_id": "GB-F02",
        "item": "LAC @ BAL (W10-14) Game Book",
        "detail": (
            "The fixture had not kicked off at capture time (2026-11-16 8:15 PM ET was "
            "still in the future relative to the official source state), so no Game Book "
            "exists. Venue and stadium are published on the official Game Centre and are "
            "carried; weather, roof/surface, starters and inactives are blank."
        ),
        "value_published": "",
        "why_blank": "artefact does not exist yet",
        "source_url": "https://www.nfl.com/games/chargers-at-ravens-2026-reg-10",
        "route": "re-capture after the game is final",
    },
    {
        "flag_id": "GB-F03",
        "item": "KC @ ATL game-day temperature / humidity / wind",
        "detail": (
            "The official Game Book for this fixture publishes the roof state "
            "(Retractable Roof - Closed on Field Turf) but no temperature, humidity or "
            "wind values. Left blank rather than substituted from any other source."
        ),
        "value_published": "Retractable Roof - Closed on Field Turf",
        "why_blank": "official artefact does not publish the numbers",
        "source_url": "https://static.www.nfl.com/image/upload/v1794829722/gamecenter/ab582f5b-4feb-11f1-abca-2c54536568a9.pdf",
        "route": "none - the indoor game has no published weather by design",
    },
]

summary = {
    "generated_utc": "2026-11-17",
    "raw_files": len(raw_files),
    "games_with_game_book": len(games_meta),
    "fixtures_in_week10_slate": len(games_meta) + 1,
    "official_starters_captured": len(starter_rows),
    "expected_starter_slots": len(games_meta) * 2 * 22,
    "official_inactives_captured": len(inactive_rows),
    "clubs_with_official_depth_chart": len(DEPTH_CLUBS),
    "availability_graph_rows": len(avail_rows),
    "designation_buckets": len(designation_rows),
    "published_report_rows_joined": sum(b["n"] for b in bucket_stats.values()),
    "availability_delta_rows": len(delta_rows),
    "team_replacement_rows": len(team_rows),
    "clubs_in_week10": len(depth_coverage),
    "clubs_with_depth_chart_playing_week10": len(DEPTH_CLUBS & {s["club"] for s in all_starters}),
    "flags": len(flags),
}

(DATA / "capture-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
(DATA / "snapshot-ledger.json").write_text(json.dumps(ledger, indent=2), encoding="utf-8")
(DATA / "flags.json").write_text(json.dumps(flags, indent=2), encoding="utf-8")

print(json.dumps(summary, indent=2))
print()
print("availability verdicts:")
from collections import Counter

for k, v in Counter(r["verdict"] for r in avail_rows).most_common():
    print(f"  {v:4d}  {k}")
print()
print("designation reliability:")
for r in designation_rows:
    print(
        f"  {r['published_designation']:<38} n={r['n_players_joined']:3d} "
        f"inactive={r['n_on_official_not_active']:3d} rate={r['observed_inactive_rate']:.3f} "
        f"[{r['wilson_95_low']}, {r['wilson_95_high']}]"
    )
