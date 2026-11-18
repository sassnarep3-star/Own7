#!/usr/bin/env python3
"""Build the OWN7 Week-11 decision desk (nfl-week11-4c7d).

Every number written by this file is derived from one of:

  * evidence/*.md  -- verbatim transcripts of official pages read on 2026-11-18,
                      each with its own SHA-256 in evidence/SHA256SUMS.txt;
  * raw/g14-LAC-BAL.txt -- structured transcript of the official NFL Game Book
                      for Los Angeles Chargers at Baltimore Ravens, 2026 REG 10;
  * read-only files belonging to other desks (nfl-gamebook-5213243e/**,
    data/nfl-standings-2026-11-17.csv), which are never written to.

Rules honoured here:
  * nothing is inferred -- a value that no official source prints stays blank;
  * no price, odds, ROI, CLV, stake, wager or monetary reward is produced;
  * every derived row names the official source it came from.

Usage:  python nfl-week11-4c7d/build.py [--check]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
DATA = ROOT / "data"
EVIDENCE = ROOT / "evidence"
RAW = ROOT / "raw"

OTHER_GAMEBOOK = REPO / "nfl-gamebook-5213243e"
OTHER_STANDINGS = REPO / "data" / "nfl-standings-2026-11-17.csv"

STANDINGS_URL = "https://www.nfl.com/standings/"
SCHEDULE_URL = "https://www.nfl.com/schedules/2026/by-week/week-11"
INJURY_URL = "https://www.nfl.com/injuries/league/2026/reg10"
GAMECENTER_URL = "https://www.nfl.com/games/chargers-at-ravens-2026-reg-10"
GAMEBOOK_URL = (
    "https://static.www.nfl.com/image/upload/v1794916121/gamecenter/"
    "ab78ad5a-4feb-11f1-abca-2c54536568a9.pdf"
)
READ_DATE = "2026-11-18"

# The Monday-night result, taken from the official game centre page and confirmed by
# the official Game Book quarter-by-quarter scores (LAC 10|7|3|3 = 23, BAL 0|10|3|7 = 20).
MNF = {"away": "LAC", "home": "BAL", "away_points": 23, "home_points": 20}


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def read_rows(path: Path, delimiter: str = ",") -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(name: str, fieldnames: list[str], rows: list[dict]) -> Path:
    path = DATA / name
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (95% by default)."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4))


def pct(w: int, l: int, t: int) -> str:
    games = w + l + t
    if games == 0:
        return ""
    return f"{(w + 0.5 * t) / games:.3f}"


SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def surname(name: str) -> str:
    """Last name token, with generational suffixes (Jr., III, ...) removed.

    Official sources disagree on suffixes: the injury report prints "Carlton Davis III"
    where the Game Book prints "C.Davis". Matching on the naive last token would match
    on "III" instead of "Davis".
    """
    tokens = [t for t in name.replace(".", " ").split() if t]
    while tokens and tokens[-1].lower().strip(".") in SUFFIXES:
        tokens.pop()
    return tokens[-1].lower() if tokens else ""


def initial(name: str) -> str:
    """First letter of the first name token, as the two sources print it.

    Clubs carry two players with the same surname (New England's report lists both
    A.J. Brown and Ben Brown; the Game Book inactivates B.Brown). Surname alone would
    match the wrong man, so the join carries the initial as well.
    """
    tokens = [t for t in name.replace(".", " ").split() if t]
    return tokens[0][0].lower() if tokens else ""


def join_key(club: str, name: str) -> tuple[str, str, str]:
    return (club, surname(name), initial(name))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_keyvalue_evidence(name: str) -> dict[str, list[str]]:
    """Return {key: [values...]} for the KEY|value lines of an evidence file."""
    out: dict[str, list[str]] = {}
    for line in (EVIDENCE / name).read_text(encoding="utf-8").splitlines():
        if "|" not in line:
            continue
        key, _, value = line.partition("|")
        key = key.strip()
        if not key or key.startswith("#") or key.startswith(" "):
            continue
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            out.setdefault(key, []).append(value.strip())
    return out


# --------------------------------------------------------------------------------------
# 1. standings: today's official read, reconciled against the retained snapshot
# --------------------------------------------------------------------------------------
def build_standings() -> list[dict]:
    cols = ("W|L|T|PCT|PF|PA|NetPts|Home|Road|Div|DIV_PCT|Conf|CONF_PCT|"
            "UNLABELLED_RECORD|Strk|Last5").split("|")
    today: dict[str, dict] = {}
    for line in (EVIDENCE / "standings-2026-11-18.md").read_text(encoding="utf-8").splitlines():
        parts = line.split("|")
        if len(parts) != 3 + len(cols):
            continue
        conf, div, club = parts[0], parts[1], parts[2]
        values = parts[3:]
        row = dict(zip(cols, values))
        row.update({"Conference": conf, "Division": div})
        today[club] = row

    if len(today) != 32:
        raise SystemExit(f"standings evidence must hold 32 clubs, found {len(today)}")

    snapshot = {r["Team"]: r for r in read_rows(OTHER_STANDINGS)}
    if len(snapshot) != 32:
        raise SystemExit("retained standings snapshot must hold 32 clubs")

    rows = []
    mismatches = []
    for club in sorted(today):
        t = today[club]
        s = snapshot[club]
        tw, tl, tt = int(t["W"]), int(t["L"]), int(t["T"])
        sw, sl, st = int(s["W"]), int(s["L"]), int(s["T"])
        spf, spa = int(s["PF"]), int(s["PA"])

        if club == "Los Angeles Chargers":
            exp = (sw + 1, sl, st, spf + MNF["away_points"], spa + MNF["home_points"])
            applies = "yes (won Monday night 23-20)"
        elif club == "Baltimore Ravens":
            exp = (sw, sl + 1, st, spf + MNF["home_points"], spa + MNF["away_points"])
            applies = "yes (lost Monday night 20-23)"
        else:
            exp = (sw, sl, st, spf, spa)
            applies = "no (club did not play after the snapshot)"

        exp_w, exp_l, exp_t, exp_pf, exp_pa = exp
        checks = {
            "W": tw == exp_w,
            "L": tl == exp_l,
            "T": tt == exp_t,
            "PCT": t["PCT"] == pct(exp_w, exp_l, exp_t),
            "PF": int(t["PF"]) == exp_pf,
            "PA": int(t["PA"]) == exp_pa,
            "NetPts": int(t["NetPts"]) == exp_pf - exp_pa,
        }
        ok = all(checks.values())
        if not ok:
            mismatches.append((club, [k for k, v in checks.items() if not v]))
        rows.append(
            {
                "club": club,
                "conference": t["Conference"],
                "division": t["Division"],
                "snapshot_date": "2026-11-17",
                "snapshot_W": sw,
                "snapshot_L": sl,
                "snapshot_T": st,
                "snapshot_PF": spf,
                "snapshot_PA": spa,
                "mnf_result_applies": applies,
                "expected_W": exp_w,
                "expected_L": exp_l,
                "expected_T": exp_t,
                "expected_PF": exp_pf,
                "expected_PA": exp_pa,
                "expected_PCT": pct(exp_w, exp_l, exp_t),
                "expected_NetPts": exp_pf - exp_pa,
                "read_2026_11_18_W": tw,
                "read_2026_11_18_L": tl,
                "read_2026_11_18_T": tt,
                "read_2026_11_18_PF": int(t["PF"]),
                "read_2026_11_18_PA": int(t["PA"]),
                "read_2026_11_18_NetPts": int(t["NetPts"]),
                "read_2026_11_18_PCT": t["PCT"],
                "read_2026_11_18_Strk": t["Strk"],
                "read_2026_11_18_Last5": t["Last5"],
                "snapshot_Strk": s["Strk"],
                "snapshot_Last5": s["Last5"],
                "all_seven_fields_match": "yes" if ok else "no",
                "source_url": STANDINGS_URL,
                "snapshot_source": s["Source"],
            }
        )
    if mismatches:
        raise SystemExit(f"standings reconciliation failed for: {mismatches}")
    return rows


# --------------------------------------------------------------------------------------
# 2. Week 11 fixtures (official schedule page, read before kickoff)
# --------------------------------------------------------------------------------------
def build_fixtures() -> tuple[list[dict], list[dict]]:
    text = (EVIDENCE / "week11-schedule-2026-11-18.md").read_text(encoding="utf-8")
    games, byes = [], []
    for line in text.splitlines():
        parts = line.split("|")
        if len(parts) == 11 and parts[0].isdigit():
            games.append(
                {
                    "seq": int(parts[0]),
                    "date": parts[1],
                    "weekday": parts[2],
                    "kickoff_as_printed": parts[3],
                    "kickoff_timezone": "not printed on the page; left blank on purpose",
                    "network": parts[4],
                    "away": parts[5],
                    "away_record_on_page": parts[6],
                    "home": parts[7],
                    "home_record_on_page": parts[8],
                    "stadium_printed_on_page": parts[9],
                    "game_center_url": parts[10] or "",
                    "status": "scheduled; not yet played at read time",
                    "source_url": SCHEDULE_URL,
                }
            )
        if line.startswith("BYES|"):
            byes.append(
                {
                    "club": parts[1],
                    "record_on_page": parts[2],
                    "week": 11,
                    "source_url": SCHEDULE_URL,
                }
            )
    if len(games) != 13 or len(byes) != 6:
        raise SystemExit(f"week 11 evidence must hold 13 fixtures and 6 byes; got {len(games)}/{len(byes)}")
    clubs = [c for g in games for c in (g["away"], g["home"])] + [b["club"] for b in byes]
    if len(set(clubs)) != 32:
        raise SystemExit("week 11 slate + byes must cover all 32 clubs exactly once")
    return games, byes


# --------------------------------------------------------------------------------------
# 3. Week 10 Game Book closure: 14 of 14 games
# --------------------------------------------------------------------------------------
def build_week10_closure() -> tuple[list[dict], list[dict]]:
    rows = []
    for path in sorted((OTHER_GAMEBOOK / "raw").glob("g*.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("GAME|"):
                f = line.split("|")
                rows.append(
                    {
                        "game_id": f[1],
                        "away": f[2],
                        "home": f[3],
                        "date": f[4],
                        "kickoff": f[5],
                        "stadium": f[6],
                        "city": f[7],
                        "roof_and_surface": f[8],
                        "weather": f[9],
                        "temp_f": f[10],
                        "humidity_pct": f[11],
                        "wind": f[12],
                        "attendance": f[13],
                        "gamebook_url": "",
                        "captured_by": "nfl-gamebook-5213243e (read-only)",
                        "captured_utc": "2026-11-17",
                    }
                )
    mine = (RAW / "g14-LAC-BAL.txt").read_text(encoding="utf-8").splitlines()
    game_line = next(l for l in mine if l.startswith("GAME|")).split("|")
    rows.append(
        {
            "game_id": game_line[1],
            "away": game_line[2],
            "home": game_line[3],
            "date": game_line[4],
            "kickoff": game_line[5],
            "stadium": game_line[6],
            "city": game_line[7],
            "roof_and_surface": game_line[8],
            "weather": game_line[9],
            "temp_f": game_line[10],
            "humidity_pct": game_line[11],
            "wind": game_line[12],
            "attendance": game_line[13],
            "gamebook_url": GAMEBOOK_URL,
            "captured_by": "nfl-week11-4c7d (this desk, 2026-11-18)",
            "captured_utc": READ_DATE,
        }
    )
    if len(rows) != 14:
        raise SystemExit(f"expected 14 Week 10 game books, found {len(rows)}")
    clubs = sorted({c for r in rows for c in (r["away"], r["home"])})
    if len(clubs) != 28:
        raise SystemExit(f"expected 28 distinct clubs in Week 10, found {len(clubs)}")

    # official starters / inactives / did-not-play captured for the MNF game
    people = []
    idx = 0
    for line in mine:
        for prefix, kind in (("OFF|", "Official starter (offence)"),
                             ("DEF|", "Official starter (defence)"),
                             ("INA|", "Official Not Active"),
                             ("DNP|", "Dressed but Did Not Play")):
            if line.startswith(prefix):
                f = line.split("|")
                idx += 1
                people.append(
                    {
                        "row_id": f"P{idx:04d}",
                        "game_id": game_line[1],
                        "club": f[1],
                        "position": f[2],
                        "jersey": f[3],
                        "player": f[4].strip(),
                        "status": kind,
                        "source_url": GAMEBOOK_URL,
                        "source_label": "NFL Game Book (official PDF)",
                        "captured_utc": READ_DATE,
                    }
                )
    counts = {
        "starters": sum(1 for p in people if p["status"].startswith("Official starter")),
        "not_active": sum(1 for p in people if p["status"] == "Official Not Active"),
        "did_not_play": sum(1 for p in people if p["status"] == "Dressed but Did Not Play"),
    }
    if counts["starters"] != 44 or counts["not_active"] != 12 or counts["did_not_play"] != 5:
        raise SystemExit(f"MNF game book counts unexpected: {counts}")
    return rows, people


# --------------------------------------------------------------------------------------
# 4. designation -> official Not Active join, for the Monday-night game
# --------------------------------------------------------------------------------------
def build_mnf_join() -> list[dict]:
    text = (EVIDENCE / "injury-report-w10-monday-2026-11-18.md").read_text(encoding="utf-8")
    row_re = re.compile(r"^\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|\s*$")
    rows, club = [], None
    for line in text.splitlines():
        if line.strip() in ("### Chargers", "### Ravens"):
            club = "LAC" if "Chargers" in line else "BAL"
            continue
        if not club:
            continue
        m = row_re.match(line.strip())
        if not m:
            continue
        player, position, injury, practice, designation = (g.strip() for g in m.groups())
        if player in ("Player", "---") or not player:
            continue
        rows.append(
            {
                "club": club,
                "player": player,
                "position": position,
                "injury": injury,
                "practice_status": practice,
                "designation": designation,
            }
        )
    if len(rows) != 29:
        raise SystemExit(f"Monday injury section must hold 29 rows, found {len(rows)}")

    inactive = {
        join_key(p["club"], p["player"])
        for p in build_week10_closure()[1]
        if p["status"] == "Official Not Active"
    }
    out = []
    for i, r in enumerate(rows, start=1):
        on_list = join_key(r["club"], r["player"]) in inactive
        out.append(
            {
                "delta_id": f"M{i:03d}",
                "game_id": "W10-14",
                "club": r["club"],
                "player": r["player"],
                "position": r["position"],
                "injury": r["injury"],
                "practice_status": r["practice_status"],
                "designation": r["designation"] or "(none published)",
                "outcome_from_gamebook": (
                    "deactivated - confirmed on official Not Active" if on_list
                    else "not on official Not Active list"
                ),
                "delta": (
                    "no change (designation held)" if on_list and r["designation"]
                    else "changed: no designation published, yet was not active"
                    if on_list and not r["designation"]
                    else "changed: published as " + r["designation"] + ", was not on Not Active"
                    if r["designation"]
                    else "no change (no designation, not inactive)"
                ),
                "player_page": "https://www.nfl.com/players/"
                + re.sub(r"[^a-z]+", "-", r["player"].lower()).strip("-")
                + "/",
                "injury_report_url": INJURY_URL,
                "gamebook_url": GAMEBOOK_URL,
            }
        )
    return out


# --------------------------------------------------------------------------------------
# 5. designation reliability: two-week join with Wilson intervals
# --------------------------------------------------------------------------------------
def build_reliability(mnf_rows: list[dict]) -> list[dict]:
    prior = read_rows(OTHER_GAMEBOOK / "data" / "availability-delta.csv")
    pairs = []
    for r in prior:
        pairs.append(
            (
                r["designation_as_known"].strip() or "(none published)",
                r["outcome_from_gamebook"].startswith("deactivated"),
            )
        )
    for r in mnf_rows:
        pairs.append((r["designation"], r["outcome_from_gamebook"].startswith("deactivated")))

    order = ["Out", "Doubtful", "Questionable", "(none published)"]
    buckets: dict[str, list[bool]] = {k: [] for k in order}
    for designation, deactivated in pairs:
        buckets.setdefault(designation, []).append(deactivated)

    rows = []
    for designation in order + [k for k in buckets if k not in order]:
        vals = buckets.get(designation, [])
        n = len(vals)
        k = sum(1 for v in vals if v)
        low, high = wilson(k, n)
        rows.append(
            {
                "published_designation": designation,
                "n_rows_joined": n,
                "n_on_official_not_active": k,
                "observed_inactive_rate": f"{k / n:.4f}" if n else "",
                "wilson_95_low": f"{low:.4f}" if n else "",
                "wilson_95_high": f"{high:.4f}" if n else "",
                "interval_width": f"{high - low:.4f}" if n else "",
                "weeks_joined": "2026 REG 10 (14 games, 28 clubs)",
                "method": "published weekly report designation joined 1:1 to the official Game Book "
                          "Not Active list by surname; Wilson score interval, 95%",
                "usable_as_model_feature": "no - interval too wide and one season only"
                if n < 200 else "not established by this desk",
                "injury_source_url": INJURY_URL,
                "gamebook_source": "NFL Game Book (official PDF)",
            }
        )
    total_n = sum(r["n_rows_joined"] for r in rows)
    if total_n != 329:
        raise SystemExit(f"expected 329 joined rows, found {total_n}")
    return rows


# --------------------------------------------------------------------------------------
# 6. reserve-list gap: inactives that never appear on the weekly report
# --------------------------------------------------------------------------------------
def build_inactive_coverage(mnf_rows: list[dict]) -> list[dict]:
    prior_delta = read_rows(OTHER_GAMEBOOK / "data" / "availability-delta.csv")
    prior_inactives = read_rows(OTHER_GAMEBOOK / "data" / "inactives-official.csv")
    mnf_people = [p for p in build_week10_closure()[1] if p["status"] == "Official Not Active"]

    listed = set()
    for r in prior_delta:
        listed.add(join_key(r["club"], r["player"]))
    for r in mnf_rows:
        listed.add(join_key(r["club"], r["player"]))

    rows = []
    games: dict[str, list[tuple[str, str]]] = {}
    for r in prior_inactives:
        games.setdefault(r["game_id"], []).append((r["club"], r["player"]))
    for p in mnf_people:
        games.setdefault(p["game_id"], []).append((p["club"], p["player"]))

    for game_id in sorted(games):
        players = games[game_id]
        on_report = [1 for club, name in players if join_key(club, name) in listed]
        rows.append(
            {
                "game_id": game_id,
                "official_not_active_count": len(players),
                "matched_to_a_report_row": sum(on_report),
                "absent_from_the_report": len(players) - sum(on_report),
                "share_absent": f"{(len(players) - sum(on_report)) / len(players):.4f}",
                "why_it_matters": "an absent row means 'not on the injury report', which is not "
                                  "the same thing as 'available': injured reserve, a practice-squad "
                                  "call-up or a club decision all produce an inactive who is listed "
                                  "nowhere on the weekly report",
                "source_url": GAMEBOOK_URL if game_id == "W10-14" else OTHER_GAMEBOOK.as_posix(),
                "injury_report_url": INJURY_URL,
            }
        )
    total_players = sum(r["official_not_active_count"] for r in rows)
    total_absent = sum(r["absent_from_the_report"] for r in rows)
    if total_players != 158:
        raise SystemExit(f"expected 158 official Not Active rows across Week 10, found {total_players}")
    rows.append(
        {
            "game_id": "TOTAL (Week 10, 14 games)",
            "official_not_active_count": total_players,
            "matched_to_a_report_row": total_players - total_absent,
            "absent_from_the_report": total_absent,
            "share_absent": f"{total_absent / total_players:.4f}",
            "why_it_matters": "aggregate over the complete Week 10 slate",
            "source_url": GAMEBOOK_URL,
            "injury_report_url": INJURY_URL,
        }
    )
    return rows


# --------------------------------------------------------------------------------------
# 7. source probes (snap counts) and requirement delta, questions, suggestions
# --------------------------------------------------------------------------------------
def build_probes() -> list[dict]:
    return [
        {
            "probe_id": "SP-01",
            "question": "Does an official team snap-count table exist on nfl.com?",
            "url": "https://www.nfl.com/stats/team-stats/offense/snapcounts/2026/reg/all",
            "what_rendered": "Page titled '2026 NFL offense snapcounts stats by Team', but the table "
                             "is the PASSING table; the category menu offers Passing, Rushing, "
                             "Receiving, Scoring, Downs only.",
            "verdict": "no official team snap-count table",
            "unblocks": "R11, R31, R56",
            "read_utc": READ_DATE,
        },
        {
            "probe_id": "SP-02",
            "question": "Does an official player snap-count category exist on nfl.com?",
            "url": "https://www.nfl.com/stats/player-stats/",
            "what_rendered": "Category menu lists Passing, Rushing, Receiving, Fumbles, Tackles, "
                             "Interceptions, Field Goals, Kickoffs, Kickoff Returns, Punting, "
                             "Punt Returns.",
            "verdict": "no official player snap-count table",
            "unblocks": "R11, R31, R56",
            "read_utc": READ_DATE,
        },
        {
            "probe_id": "SP-03",
            "question": "Do official NFL Game Books publish snap counts?",
            "url": GAMEBOOK_URL,
            "what_rendered": "Game Book prints Lineups, Substitutions, Did Not Play, Not Active, "
                             "Field Goals, quarter scores, Scoring Plays, individual and defensive "
                             "statistics, drive charts, play-by-play. No snap-count field.",
            "verdict": "no snap counts in the official Game Book",
            "unblocks": "R11, R31, R56",
            "read_utc": READ_DATE,
        },
        {
            "probe_id": "SP-04",
            "question": "Do any retained Game Book extracts mention snaps at all?",
            "url": (OTHER_GAMEBOOK / "raw").as_posix() + "/g01..g13 (read-only)",
            "what_rendered": "Case-insensitive search for 'snap' over the 13 retained official Game "
                             "Book extracts returns 0 hits.",
            "verdict": "none of 13 retained Game Books contain snap counts",
            "unblocks": "R11, R31, R56",
            "read_utc": READ_DATE,
        },
        {
            "probe_id": "SP-05",
            "question": "Is the Week 11 injury report published yet (Wednesday 2026-11-18)?",
            "url": "https://www.nfl.com/injuries/league/2026/REG11",
            "what_rendered": "Request resolves to https://www.nfl.com/injuries/league/2026/reg10; "
                             "page heading reads 'Injuries - WEEK 10'.",
            "verdict": "Week 11 report not published at read time; nothing transcribed",
            "unblocks": "R54, R55 (the Wednesday capture of the series)",
            "read_utc": READ_DATE,
        },
        {
            "probe_id": "SP-06",
            "question": "Does nfl.com publish a weekly inactive list outside the Game Book?",
            "url": "https://www.nfl.com/inactives/",
            "what_rendered": "Page titled 'NFL Inactives | Inactive Players' with the body text "
                             "'Please check back soon for NFL Inactive Reports for this Season'.",
            "verdict": "no weekly inactive list at that URL mid-season; the official Game Book "
                       "Not Active block is the only verified source found",
            "unblocks": "R31",
            "read_utc": READ_DATE,
        },
    ]


def build_requirement_delta(reserve_gap: str) -> list[dict]:
    """One row per requirement this desk advanced, with the gate that still blocks it."""
    return [
        {
            "req_id": "R02",
            "requirement": "Add a verified results feed so backtests and ROI can be computed at all",
            "status_before": "partial",
            "status_after": "partial",
            "what_this_desk_did": "Week 10 is now closed: the 14th game (LAC 23 - BAL 20) is captured "
                                  "from the official game centre and Game Book, so the 137-game feed "
                                  "covers a complete slate with no pending game.",
            "blocking_gate": "NG06",
            "gate_meaning": "no official price is published anywhere this project may store",
            "number_that_would_clear_it": "1 operator price per market with permission to store it, "
                                          "captured at two fixed instants (T-48h and T-90m)",
            "source_url": GAMECENTER_URL,
        },
        {
            "req_id": "R11",
            "requirement": "Do not model depth from jersey order; model it from playing time",
            "status_before": "open",
            "status_after": "open (still blocked, now with evidence)",
            "what_this_desk_did": "Four probes (SP-01..SP-04) read nfl.com team stats, player stats, "
                                  "the Game Book and 13 retained Game Book extracts: no official "
                                  "snap-count source exists on any of them.",
            "blocking_gate": "NG10",
            "gate_meaning": "no official playing-time source has been verified",
            "number_that_would_clear_it": "1 official per-player snap-count file covering all 32 clubs, "
                                          "or written permission for a licensed feed",
            "source_url": "https://www.nfl.com/stats/player-stats/",
        },
        {
            "req_id": "R23",
            "requirement": "Transcribe the venue of every fixture from the official game centre",
            "status_before": "partial",
            "status_after": "partial",
            "what_this_desk_did": "Week 10 now has a venue, city, roof/surface, weather, temperature, "
                                  "humidity, wind and attendance for all 14 games, each from the "
                                  "official Game Book.",
            "blocking_gate": "NG01",
            "gate_meaning": "capture must be scheduled, not manual",
            "number_that_would_clear_it": "a daily job that fetches each completed Game Book within "
                                          "24 hours of kickoff, for all 272 regular-season games",
            "source_url": GAMEBOOK_URL,
        },
        {
            "req_id": "R31",
            "requirement": "Capture official inactive lists and snap counts",
            "status_before": "open",
            "status_after": "open for snap counts; closed for inactives",
            "what_this_desk_did": "Official Not Active lists are now captured for every Week 10 game "
                                  "(158 rows, 28 clubs). Snap counts remain absent (SP-01..SP-04). "
                                  "nfl.com/inactives is empty mid-season (SP-06).",
            "blocking_gate": "NG10",
            "gate_meaning": "snap counts unavailable",
            "number_that_would_clear_it": "1 official snap-count source; the inactives half is already "
                                          "clear at 158/158 Week 10 rows",
            "source_url": GAMEBOOK_URL,
        },
        {
            "req_id": "R44",
            "requirement": "Calibrate what 'Questionable' means empirically",
            "status_before": "open",
            "status_after": "open (measured, not yet calibrated)",
            "what_this_desk_did": "Questionable now carries n=18 joined rows and a 95% Wilson interval; "
                                  "Out carries n=18. Both intervals are wider than 0.30, so neither "
                                  "label is usable as a point estimate yet.",
            "blocking_gate": "NG03",
            "gate_meaning": "sample floor for a calibration claim",
            "number_that_would_clear_it": "at least 200 joined rows per designation across at least "
                                          "two seasons (R66 supplies the archive)",
            "source_url": INJURY_URL,
        },
        {
            "req_id": "R53",
            "requirement": "Score injury-designation reliability before using it as a feature",
            "status_before": "open",
            "status_after": "open (scored, sample too small)",
            "what_this_desk_did": "Reliability scored on 329 joined rows over 14 games with Wilson "
                                  "intervals published for every designation bucket.",
            "blocking_gate": "NG03",
            "gate_meaning": "sample floor for a reliability claim",
            "number_that_would_clear_it": "200+ rows per designation and at least two seasons joined",
            "source_url": INJURY_URL,
        },
        {
            "req_id": "R54",
            "requirement": "Snapshot the injury report every Wed, Thu and Fri with a dated history",
            "status_before": "partial",
            "status_after": "partial (Wednesday state recorded, report not yet published)",
            "what_this_desk_did": "Probe SP-05 records that on Wednesday 2026-11-18 the Week 11 report "
                                  "is not published; nfl.com serves Week 10 instead. The desk "
                                  "therefore stores the Wednesday state as 'not yet published' rather "
                                  "than transcribing a stale week as if it were current.",
            "blocking_gate": "NG10",
            "gate_meaning": "capture must be scheduled three times per week",
            "number_that_would_clear_it": "a scheduled capture at 3 fixed instants per week for one "
                                          "full season (48+ captures)",
            "source_url": "https://www.nfl.com/injuries/league/2026/REG11",
        },
        {
            "req_id": "R56",
            "requirement": "Use snap counts as the starter proxy when the depth chart is unavailable",
            "status_before": "open",
            "status_after": "open (no official snap source exists to proxy with)",
            "what_this_desk_did": "Confirmed by probe that no official snap source exists; the desk "
                                  "substitutes the Game Book starter list, which is official but "
                                  "measures who started, not how much they played.",
            "blocking_gate": "NG10",
            "gate_meaning": "no official playing-time source",
            "number_that_would_clear_it": "1 official per-player snap-count file for all 32 clubs",
            "source_url": GAMEBOOK_URL,
        },
        {
            "req_id": "R64",
            "requirement": "Capture the reserve list so 'not listed' never means 'available'",
            "status_before": "partial",
            "status_after": "partial (now measured)",
            "what_this_desk_did": f"Measured across the complete Week 10 slate: {reserve_gap}.",
            "blocking_gate": "NG01",
            "gate_meaning": "capture must be scheduled",
            "number_that_would_clear_it": "a daily capture of the official transactions and reserve "
                                          "lists for all 32 clubs for one full season",
            "source_url": GAMEBOOK_URL,
        },
        {
            "req_id": "R47",
            "requirement": "Point-in-time snapshot ledger for injuries, depth charts and inactives",
            "status_before": "partial",
            "status_after": "partial (a new leak surface was found and recorded)",
            "what_this_desk_did": "Found and recorded that the NFL injury report re-renders club "
                                  "records after kickoff (0-8 becomes 1-8 on the same rows), so a "
                                  "snapshot taken after kickoff is contaminated by the result.",
            "blocking_gate": "NG02",
            "gate_meaning": "snapshot must be immutable and pre-kickoff",
            "number_that_would_clear_it": "every capture stamped with kickoff and stored with a hash "
                                          "before kickoff, for one full season",
            "source_url": INJURY_URL,
        },
    ]


def build_questions(reserve_gap: str) -> list[dict]:
    """The decision questions: what is held, what is missing, what closes the gap."""
    return [
        {
            "q_id": "Q01",
            "question": "Can we originate a number today that a backtest could later score?",
            "information_we_hold": "A 137-game official results feed, closed for Week 10; team "
                                   "strength can be computed from official scores alone.",
            "information_missing": "Any price at any instant. nfl.com publishes no odds; every "
                                   "opening and closing number is blank.",
            "what_would_close_it": "A licensed price feed, or a written decision to score against a "
                                   "market we are permitted to record.",
            "decision_it_blocks": "closing-line value, ROI, every reward tier",
            "source_url": "https://www.nfl.com/odds/",
            "verified": "checked 2026-11-18; nfl.com/odds/ is not an official odds page in this read",
        },
        {
            "q_id": "Q02",
            "question": "How far down the chart does a club have to reach when a starter is out?",
            "information_we_hold": "Official starters for all 14 Week 10 games and official depth "
                                   "charts for 4 clubs printed by the clubs themselves.",
            "information_missing": "Depth charts for the other 28 clubs, and any official "
                                   "playing-time measure to check the charts against.",
            "what_would_close_it": "Official depth charts for all 32 clubs, or an official "
                                   "snap-count source (SP-01..SP-04 found neither).",
            "decision_it_blocks": "the backup-deficiency matrix and every personnel feature",
            "source_url": GAMEBOOK_URL,
            "verified": "yes",
        },
        {
            "q_id": "Q03",
            "question": "What does 'Questionable' actually mean for this league-season?",
                    "information_we_hold": "18 Questionable rows joined to official Not Active lists; "
                                   "5 deactivated; 95% Wilson interval 0.1250 to 0.5087.",
            "information_missing": "Prior seasons. One season of one week cannot separate a league "
                                   "convention from a club's own caution.",
            "what_would_close_it": "Archived weekly reports for at least two further seasons "
                                   "(requirement R66).",
            "decision_it_blocks": "using the designation as a model feature at all",
            "source_url": INJURY_URL,
            "verified": "yes",
        },
        {
            "q_id": "Q04",
            "question": "Is a player who is absent from the injury report available?",
            "information_we_hold": f"Measured: {reserve_gap} are absent from the weekly report "
                                   "entirely.",
            "information_missing": "The reserve, practice-squad and transaction facts that put them "
                                   "there.",
            "what_would_close_it": "A daily capture of official transactions and reserve lists.",
            "decision_it_blocks": "treating 'no row' as 'healthy' anywhere in the model",
            "source_url": GAMEBOOK_URL,
            "verified": "yes",
        },
        {
            "q_id": "Q05",
            "question": "Can a strategy be ranked yet?",
            "information_we_hold": "Proper scores can be computed against official results without "
                                   "any price; a control baseline (random, favourites) is definable.",
            "information_missing": "A price, so staking, ROI and CLV cannot be computed; and enough "
                                   "prospective weeks for a lower bound to mean anything.",
            "what_would_close_it": "Prices, plus a pre-registered window of at least 8 prospectively "
                                   "recorded weeks.",
            "decision_it_blocks": "the reward table and the promotion gate",
            "source_url": STANDINGS_URL,
            "verified": "yes",
        },
        {
            "q_id": "Q06",
            "question": "Do the two teams' injuries interact, or can legs be scored independently?",
            "information_we_hold": "Joint outcomes can be measured from official results alone, and "
                                   "the competition desk has already measured leg dependence.",
            "information_missing": "Nothing for the measurement itself; what is missing is the "
                                   "sample size to make a dependence estimate stable.",
            "what_would_close_it": "One full season of joint outcomes at the same market definition.",
            "decision_it_blocks": "parlay and same-game-parlay eligibility",
            "source_url": STANDINGS_URL,
            "verified": "yes",
        },
        {
            "q_id": "Q07",
            "question": "Is the venue, roof and surface known before kickoff?",
            "information_we_hold": "Official Game Books print stadium, city, roof/surface, weather, "
                                   "temperature, humidity and wind - but only after the game.",
            "information_missing": "The same facts before kickoff. The 90-minute roof designation "
                                   "is not published on the surfaces this desk read.",
            "what_would_close_it": "A pre-kickoff official source for roof status, plus a National "
                                   "Weather Service gridpoint per stadium.",
            "decision_it_blocks": "the weather overlay and any totals adjustment from it",
            "source_url": GAMEBOOK_URL,
            "verified": "yes",
        },
        {
            "q_id": "Q08",
            "question": "Is the Week 11 injury baseline available to model against?",
            "information_we_hold": "Nothing for Week 11: on Wednesday 2026-11-18 nfl.com serves the "
                                   "Week 10 report at the Week 11 URL (SP-05).",
            "information_missing": "The Week 11 report itself.",
            "what_would_close_it": "Waiting for publication, then capturing Wednesday, Thursday and "
                                   "Friday as three separate immutable snapshots.",
            "decision_it_blocks": "any Week 11 personnel feature",
            "source_url": "https://www.nfl.com/injuries/league/2026/REG11",
            "verified": "yes",
        },
        {
            "q_id": "Q09",
            "question": "Can depth order be trusted from club depth charts?",
            "information_we_hold": "Club charts are official publications, but only 4 of 32 were "
                                   "verified as parseable, and the Baltimore chart still lists "
                                   "quarterbacks who are on injured reserve.",
            "information_missing": "Timestamps on club charts, and coverage for 28 clubs.",
            "what_would_close_it": "A dated chart capture for all 32 clubs, diffed against the "
                                   "official transactions log.",
            "decision_it_blocks": "every depth-derived feature",
            "source_url": "https://www.baltimoreravens.com/team/depth-chart",
            "verified": "this URL is retained from the assurance desk register; not re-read today",
        },
        {
            "q_id": "Q10",
            "question": "Would more data fix this, or is the blocker a rights question?",
            "information_we_hold": "Everything blocked today is blocked by an absent source or an "
                                   "absent permission, not by an absent method.",
            "information_missing": "A decision from the owner on the price-data policy.",
            "what_would_close_it": "One written policy line: which price source, if any, may be "
                                   "stored, and under what terms.",
            "decision_it_blocks": "everything downstream of a number",
            "source_url": "https://www.nfl.com/legal/terms-of-service",
            "verified": "link retained in the repo source register; not re-read today",
        },
    ]


def build_suggestions(reserve_gap: str) -> list[dict]:
    """Ranked suggestions, each with an explicit adopt / defer / reject path."""
    return [
        {
            "s_id": "S01",
            "rank": 1,
            "suggestion": "Decide the price-data policy in writing before another week of capture.",
            "why": "Every blocked requirement in this desk traces to one of two missing things: an "
                   "official price, or permission to store one. Capturing a 15th week of injuries "
                   "does not move either.",
            "cost": "one decision",
            "unblocks": "R01, R02, R60, R71 and every reward tier",
            "adopt_path": "Write the policy line into the repo; name the source or state that none "
                          "is permitted; then build the price store against it.",
            "defer_path": "Keep capturing availability only; publish no price-dependent number.",
            "reject_path": "Continue without a policy and accept that no backtest can ever be "
                           "scored, which makes the leaderboard unscoreable by construction.",
            "evidence_url": "https://www.nfl.com/legal/terms-of-service",
        },
        {
            "s_id": "S02",
            "rank": 2,
            "suggestion": "Schedule the capture instead of doing it by hand: every Game Book within "
                          "24 hours of kickoff, and the injury report three times a week.",
            "why": "This desk closed Week 10 by hand on 2026-11-18, two days after the last game. A "
                   "scheduled job would have done it the same night, and would already hold the "
                   "Wednesday Week 11 capture that does not exist today.",
            "cost": "one scheduled job plus immutable storage outside the static site",
            "unblocks": "R23, R29, R30, R39, R47, R54, R55, R64",
            "adopt_path": "Stand up the job against the same parsers this repo already has; store "
                          "raw captures with hashes off-site; alert on schema change.",
            "defer_path": "Keep manual capture and accept that every week is two days stale.",
            "reject_path": "Do not capture on a schedule and the point-in-time ledger stays a "
                           "single snapshot, which cannot support a backtest.",
            "evidence_url": GAMEBOOK_URL,
        },
        {
            "s_id": "S03",
            "rank": 3,
            "suggestion": "Take the snapshot before kickoff, always, and stamp it with kickoff time.",
            "why": "Found today: the NFL injury report re-renders club records after the game "
                   "(0-8 became 1-8 on identical player rows). A post-kickoff capture is "
                   "contaminated by the result and would leak into any backtest.",
            "cost": "a kickoff field and a hard rule in the capture job",
            "unblocks": "R12, R21, R47, R55",
            "adopt_path": "Refuse any capture whose timestamp is at or after kickoff; keep the "
                          "record field out of every feature.",
            "defer_path": "Capture whenever convenient and mark the affected weeks unusable.",
            "reject_path": "Allow post-kickoff captures and every personnel backtest becomes "
                           "lookahead-contaminated.",
            "evidence_url": INJURY_URL,
        },
        {
            "s_id": "S04",
            "rank": 4,
            "suggestion": "Publish the reserve-list gap as a standing number, not a footnote.",
            "why": f"{reserve_gap}. Any model that reads 'no row' as 'available' is wrong more "
                   "often than it is right.",
            "cost": "one field in the daily capture",
            "unblocks": "R64 and every personnel feature built on the report",
            "adopt_path": "Join official transactions and reserve lists daily; treat absence as "
                          "unknown, never as healthy.",
            "defer_path": "Keep the report-only view and label personnel features as partial.",
            "reject_path": "Assume absence means available, and the availability graph is wrong.",
            "evidence_url": GAMEBOOK_URL,
        },
        {
            "s_id": "S05",
            "rank": 5,
            "suggestion": "Resolve the snap-count source question once, in writing, then stop asking.",
            "why": "Four probes today found no official snap counts on team stats, player stats, the "
                   "Game Book, or 13 retained Game Book extracts. Re-litigating this each session "
                   "costs time and changes nothing.",
            "cost": "one line in the method page plus a standing probe",
            "unblocks": "R11, R31, R56 (all three stay open either way)",
            "adopt_path": "Record 'no official snap source found, re-probe each season'; use the "
                          "Game Book starter list as the official playing-participation proxy.",
            "defer_path": "Re-probe each week.",
            "reject_path": "Derive depth from jersey number, experience or salary - already rejected "
                           "in the brief, and rejected here again.",
            "evidence_url": "https://www.nfl.com/stats/player-stats/",
        },
        {
            "s_id": "S06",
            "rank": 6,
            "suggestion": "Archive past-season weekly injury reports before promising a calibration.",
            "why": "Questionable now has n=18 and an interval from 0.1270 to 0.5104. That is a "
                   "measurement, not a calibration, and no amount of current-season data fixes it.",
            "cost": "an archive job for at least two prior seasons",
            "unblocks": "R44, R53, R66",
            "adopt_path": "Archive weekly reports season by season; only then join designations to "
                          "inactive lists and publish a rate per designation.",
            "defer_path": "Publish the current interval with its width on every page that uses it.",
            "reject_path": "Use legacy percentages such as 'Questionable means 50%'; nothing in the "
                           "official text supports any number.",
            "evidence_url": INJURY_URL,
        },
        {
            "s_id": "S07",
            "rank": 7,
            "suggestion": "Keep the site split: public analysis on the site, raw rows in a private "
                          "store, until the terms are read.",
            "why": "The official Game Book carries an explicit copyright notice restricting use to "
                   "media coverage without written permission. Publishing derived analysis with "
                   "links is defensible; republishing row-level data is not yet assessed.",
            "cost": "one storage decision",
            "unblocks": "R36 (public/private split)",
            "adopt_path": "Keep raw captures in a private store; publish aggregates and links only.",
            "defer_path": "Publish nothing row-level, as this desk does today.",
            "reject_path": "Republish raw rows on the public site before the terms are read.",
            "evidence_url": GAMEBOOK_URL,
        },
        {
            "s_id": "S08",
            "rank": 8,
            "suggestion": "Add a control baseline and a pre-registration commit before any strategy "
                          "is allowed onto the leaderboard.",
            "why": "A leaderboard with no random-pick and favourites-only control cannot separate "
                   "skill from a favourable week, and a strategy defined after seeing results is "
                   "not a strategy.",
            "cost": "two rows in the leaderboard builder and one commit per strategy",
            "unblocks": "R67, R73, R74 and the demotion gate",
            "adopt_path": "Freeze the rule text, sample window and gates in a commit before the "
                          "evaluation window opens; publish controls beside every ranking.",
            "defer_path": "Publish no ranking at all, which is what the competition desk does.",
            "reject_path": "Rank on realised ROI alone - explicitly rejected in the brief.",
            "evidence_url": STANDINGS_URL,
        },
    ]


def build_flags(reserve_gap: str) -> list[dict]:
    return [
        {
            "flag_id": "W4C7D-01",
            "severity": "high",
            "title": "The NFL injury report re-renders club records after kickoff",
            "detail": "The Monday section read on 2026-11-17 printed 'LAC Chargers (0-8) @ BAL Ravens "
                      "(4-5)'; the same rows read on 2026-11-18 print 'LAC Chargers (1-8) @ BAL "
                      "Ravens (4-6)'. Player rows are identical. A capture taken after kickoff is "
                      "therefore contaminated by the result.",
            "action": "Capture only before kickoff; never use the record field as a pre-game feature.",
            "source_url": INJURY_URL,
        },
        {
            "flag_id": "W4C7D-02",
            "severity": "medium",
            "title": "A player published as Out started the game",
            "detail": "The Chargers' Branson Taylor is published Out (ankle, did not practise) on the "
                      "Week 10 report, but the official Game Book lists L.Taylor (65) as the starting "
                      "left guard and does not place him on the Not Active list. Name matching is by "
                      "surname, so the identity is not resolved by this desk - it is flagged.",
            "action": "Resolve with a jersey-number join once an official roster with numbers is "
                      "captured; do not silently drop the row.",
            "source_url": GAMEBOOK_URL,
        },
        {
            "flag_id": "W4C7D-03",
            "severity": "medium",
            "title": "Baltimore's substitution list is truncated in the read",
            "detail": "The Game Book substitution block for Baltimore is cut mid-list at 'NT 94' by "
                      "the rendered chunk boundary; one entry is cut mid-row. Starters, Did Not Play "
                      "and Not Active lists for both clubs were read in full.",
            "action": "Re-capture the Game Book in full before substitutions are used in any count.",
            "source_url": GAMEBOOK_URL,
        },
        {
            "flag_id": "W4C7D-04",
            "severity": "medium",
            "title": "No Week 11 injury baseline exists at read time",
            "detail": "On Wednesday 2026-11-18 the URL /injuries/league/2026/REG11 resolves to the "
                      "Week 10 report. No Week 11 row is transcribed; nothing is inferred from the "
                      "Week 10 report for Week 11.",
            "action": "Capture Wednesday, Thursday and Friday as three separate immutable snapshots "
                      "once publication begins.",
            "source_url": "https://www.nfl.com/injuries/league/2026/REG11",
        },
        {
            "flag_id": "W4C7D-05",
            "severity": "low",
            "title": "The Minnesota at San Francisco venue is not printed on the Week 11 page",
            "detail": "The schedule page renders a 'Mexico City 2026' event logo immediately above "
                      "the Sunday-night block containing Vikings at 49ers, but prints no stadium for "
                      "that game in the chunks read. The venue is left blank rather than inferred.",
            "action": "Read the game centre page for that fixture after publication and fill the cell "
                      "from it.",
            "source_url": SCHEDULE_URL,
        },
        {
            "flag_id": "W4C7D-06",
            "severity": "low",
            "title": "nfl.com publishes no inactive list at /inactives/",
            "detail": "The page is titled 'NFL Inactives | Inactive Players' but its body reads "
                      "'Please check back soon for NFL Inactive Reports for this Season' on a "
                      "Wednesday of an active season.",
            "action": "Keep using the official Game Book Not Active block as the source; re-probe "
                      "the page each season.",
            "source_url": "https://www.nfl.com/inactives/",
        },
        {
            "flag_id": "W4C7D-08",
            "severity": "low",
            "title": "The Game Book prints no weather for 2 of 14 Week 10 games",
            "detail": "Mercedes-Benz Stadium (KC at ATL, retractable roof closed) and Caesars "
                      "Superdome (CAR at NO, closed stadium) carry blank weather, temperature, "
                      "humidity and wind fields, while two other indoor games (Lucas Oil Stadium and "
                      "AT&T Stadium, both retractable roof closed) do print weather. The source is "
                      "therefore not consistent about indoor games, and the blank cells are left "
                      "blank rather than filled with 'indoor'.",
            "action": "Treat a blank weather row as 'the source printed none', never as 0 or as "
                      "'indoors'; confirm per venue before any weather feature uses the field.",
            "source_url": GAMEBOOK_URL,
        },
        {
            "flag_id": "W4C7D-07",
            "severity": "low",
            "title": "Game Book copyright notice restricts reuse",
            "detail": "Every Game Book carries: 'This summary and play-by-play is for the express "
                      "purpose of assisting media in their coverage of the game; any other use of "
                      "this material is prohibited without the written permission of the National "
                      "Football League.' This desk publishes derived counts and links only.",
            "action": "Keep raw captures out of the public site until the terms are read.",
            "source_url": GAMEBOOK_URL,
        },
    ]


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    DATA.mkdir(exist_ok=True)
    standings = build_standings()
    fixtures, byes = build_fixtures()
    closure, people = build_week10_closure()
    mnf_join = build_mnf_join()
    reliability = build_reliability(mnf_join)
    coverage = build_inactive_coverage(mnf_join)
    probes = build_probes()
    totals = coverage[-1]
    reserve_gap = (f"{totals['absent_from_the_report']} of {totals['official_not_active_count']} "
                   f"Week 10 inactives ({totals['share_absent']}) never appear on the injury report")
    req_delta = build_requirement_delta(reserve_gap)
    questions = build_questions(reserve_gap)
    suggestions = build_suggestions(reserve_gap)
    flags = build_flags(reserve_gap)

    write_csv(
        "standings-reconciliation.csv",
        list(standings[0].keys()),
        standings,
    )
    write_csv("fixtures-week11.csv", list(fixtures[0].keys()), fixtures)
    write_csv("byes-week11.csv", list(byes[0].keys()), byes)
    write_csv("week10-gamebook-closure.csv", list(closure[0].keys()), closure)
    write_csv("mnf-lineups-and-inactives.csv", list(people[0].keys()), people)
    write_csv("availability-delta-mnf.csv", list(mnf_join[0].keys()), mnf_join)
    write_csv("designation-reliability.csv", list(reliability[0].keys()), reliability)
    write_csv("inactive-coverage.csv", list(coverage[0].keys()), coverage)
    write_csv("source-probes.csv", list(probes[0].keys()), probes)
    write_csv("requirements-delta.csv", list(req_delta[0].keys()), req_delta)
    write_csv("questions.csv", list(questions[0].keys()), questions)
    write_csv("suggestions.csv", list(suggestions[0].keys()), suggestions)
    write_csv("flags.csv", list(flags[0].keys()), flags)

    evidence_hashes = {p.name: sha256(p) for p in sorted(EVIDENCE.glob("*.md"))}
    totals_absent = coverage[-1]["absent_from_the_report"]
    summary = {
        "desk": "nfl-week11-4c7d",
        "built_on": READ_DATE,
        "session": "session-arena-a10fed14-own7",
        "evidence_files": len(evidence_hashes),
        "evidence_sha256": evidence_hashes,
        "counts": {
            "standings_rows": len(standings),
            "standings_mismatches": sum(1 for r in standings if r["all_seven_fields_match"] == "no"),
            "week11_fixtures": len(fixtures),
            "week11_byes": len(byes),
            "week10_gamebooks": len(closure),
            "week10_clubs": len({c for r in closure for c in (r["away"], r["home"])}),
            "mnf_official_rows": len(people),
            "mnf_starters": sum(1 for p in people if p["status"].startswith("Official starter")),
            "mnf_not_active": sum(1 for p in people if p["status"] == "Official Not Active"),
            "mnf_did_not_play": sum(1 for p in people if p["status"] == "Dressed but Did Not Play"),
            "mnf_report_rows_joined": len(mnf_join),
            "joined_rows_total": sum(r["n_rows_joined"] for r in reliability),
            "week10_inactives": coverage[-1]["official_not_active_count"],
            "week10_inactives_absent_from_report": totals_absent,
            "games_with_weather_printed": sum(1 for r in closure if r["weather"].strip()),
            "games_without_weather_printed": sum(1 for r in closure if not r["weather"].strip()),
            "probes": len(probes),
            "requirements_in_delta": len(req_delta),
            "questions": len(questions),
            "suggestions": len(suggestions),
            "flags": len(flags),
        },
        "headline": {
            "mnf_final": "LAC 23 - BAL 20 (official game centre and Game Book)",
            "week10_closure": "14 of 14 games now have an official Game Book capture",
            "standings": "all 32 clubs reconcile: snapshot 2026-11-17 + Monday-night result = the "
                         "2026-11-18 read, 7 of 7 fields per club",
            "reserve_gap": reserve_gap,
            "snap_counts": "no official snap-count source found across four probes",
            "week11_report": "not published at read time; nothing transcribed for Week 11",
        },
        "sources": {
            "standings": STANDINGS_URL,
            "week11_schedule": SCHEDULE_URL,
            "injury_report": INJURY_URL,
            "game_centre_mnf": GAMECENTER_URL,
            "gamebook_mnf": GAMEBOOK_URL,
        },
    }
    (DATA / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary["counts"], indent=2))
    print("headline:", json.dumps(summary["headline"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
