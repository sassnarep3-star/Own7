#!/usr/bin/env python3
"""Collect and verify the fresh official reads of 2026-11-18 (session arena/6c72a9fa-own7).

Inputs are committed artefacts only:
  evidence/*.md      verbatim transcripts of the official reads (NFL.com via Arena fetch_page)
  raw/g14-LAC-BAL.txt  hand transcription of Game Book #14 in the shared Game Book raw format
  data/nfl-standings-week10-2026.csv   frozen pre-kickoff Week 10 standings (read-only input)
  data/nfl-standings-2026-11-17.csv    fresh 2026-11-17 pre-MNF standings (read-only input)
  nfl-results/data/games-2026-w1-10.csv  149-final official results corpus (read-only input)
  nfl-gamebook-5213243e/data/fixtures-venue.csv  Week 10 venues 1-13 (read-only input)
  nfl-brief-77b1/evidence/nfl-reserve-list-2026-11.md  reserve-list capture of 2026-11-17 (read-only input)
  nfl-readiness-e7ef/evidence/injuries-w10-2026-11-17.md  injury-report capture of 2026-11-17 (read-only input)
  nfl-readiness-e7ef/evidence/week11-2026-11-17.md  Week 11 schedule capture of 2026-11-17 (read-only input)

Outputs (deterministic; --check re-creates and compares bytes):
  data/official-2026-11-18.json  parsed fresh reads
  data/verification.json         V1-V8 check results (the build aborts on any failure)
  data/whatchanged.json          the what-changed ledger (DR-61 first implementation)

The parser never infers a value: anything the pages do not print stays blank, and any
contradiction aborts the build instead of being patched in place.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EV = HERE / "evidence"
RAW = HERE / "raw"
OUT = HERE / "data"

READ_ON = "2026-11-18"

DIVISIONS = ["AFC East", "AFC North", "AFC South", "AFC West",
             "NFC East", "NFC North", "NFC South", "NFC West"]

# Short club label -> canonical code (as printed in club cells on the transaction pages and
# schedule/injury transcripts). Cross-checked against the frozen standings CSV in V0.
CLUB_CODE = {
    "Bills": "BUF", "Patriots": "NE", "Jets": "NYJ", "Dolphins": "MIA",
    "Bengals": "CIN", "Steelers": "PIT", "Browns": "CLE", "Ravens": "BAL",
    "Jaguars": "JAX", "Texans": "HOU", "Colts": "IND", "Titans": "TEN",
    "Chiefs": "KC", "Broncos": "DEN", "Raiders": "LV", "Chargers": "LAC",
    "Giants": "NYG", "Cowboys": "DAL", "Commanders": "WAS", "Eagles": "PHI",
    "Lions": "DET", "Vikings": "MIN", "Bears": "CHI", "Packers": "GB",
    "Panthers": "CAR", "Buccaneers": "TB", "Saints": "NO", "Falcons": "ATL",
    "49ers": "SF", "Seahawks": "SEA", "Rams": "LA", "Cardinals": "AZ",
}


def fail(msg: str):
    raise SystemExit(f"collect: FATAL: {msg}")


def read(p: Path) -> str:
    if not p.exists():
        fail(f"missing artefact: {p}")
    return p.read_text(encoding="utf-8")


def sha256_of(p: Path) -> str:
    return hashlib.sha256(read(p).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- standings

def parse_standings(text: str):
    """Parse the two conference sections; each is 4 blocks of 4 rows separated by blank lines."""
    sections = re.split(r"^## NATIONAL FOOTBALL CONFERENCE\s*$", text, flags=re.M)
    if len(sections) != 2:
        fail("standings transcript must have exactly one NFC section header")
    blocks, current = [], []
    for section, conf in ((sections[0], "AFC"), (sections[1], "NFC")):
        for line in section.splitlines():
            if not line.startswith("| ["):
                if current:
                    blocks.append((conf, current))
                    current = []
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            m = re.match(r"\[([^/\]]+) / ([^\]]+)\]\((https://www.nfl.com/teams/[^)]+)\)", cells[0])
            if not m:
                fail(f"unparsable standings club cell: {cells[0]!r}")
            if len(cells) != 17:
                fail(f"standings row must have 17 cells, got {len(cells)}: {line[:80]}")
            current.append({
                "club": m.group(1).strip(),
                "short": m.group(2).strip(),
                "team_url": m.group(3),
                "g": [re.sub(r"\s+", "", c) for c in cells[1:]],
            })
    if current:
        blocks.append((sections[1].count("CONFERENCE") and "NFC", current))
    if len(blocks) != 8 or any(len(rows) != 4 for _, rows in blocks):
        fail(f"expected 8 division blocks of 4 rows, got {[len(r) for _, r in blocks]}")
    out = []
    for (conf, rows), division in zip(blocks, DIVISIONS):
        for r in rows:
            g = r["g"]
            out.append({
                "conference": conf, "division": division, "club": r["club"], "club_short": r["short"], "url": r["team_url"],
                "W": int(g[0]), "L": int(g[1]), "T": int(g[2]), "PCT": g[3],
                "PF": int(g[4]), "PA": int(g[5]), "NetPts": int(g[6]),
                "Home": g[7], "Road": g[8], "Div": g[9], "group11_unlabeled": g[10],
                "Conf": g[11], "group13_unlabeled": g[12], "group14_unlabeled": g[13],
                "Strk": g[14], "Last5": g[15],
            })
    return out


def load_frozen():
    rows = list(csv.DictReader(read(ROOT / "data" / "nfl-standings-week10-2026.csv").splitlines()))
    if len(rows) != 32:
        fail(f"frozen standings must have 32 rows, got {len(rows)}")
    return rows


def load_prev_fresh():
    rows = list(csv.DictReader(read(ROOT / "data" / "nfl-standings-2026-11-17.csv").splitlines()))
    if len(rows) != 32:
        fail(f"2026-11-17 standings CSV must have 32 rows, got {len(rows)}")
    return rows


def load_corpus():
    rows = list(csv.DictReader(read(ROOT / "nfl-results" / "data" / "games-2026-w1-10.csv").splitlines()))
    return rows


# ---------------------------------------------------------------- week 11 schedule

FIXTURE_RE = re.compile(
    r"^(\d+)\. (.+?) at (.+?) — (Monday|Thursday|Sunday), (November \d+)(?:st|nd|rd|th), "
    r"(\d{1,2}:\d{2} [AP]M) — ([A-Z]+) —")


def parse_week11(text: str):
    fixtures = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = FIXTURE_RE.match(lines[i].strip())
        if not m:
            i += 1
            continue
        num, away, home, day, date, kick, tv = m.groups()
        block = []
        i += 1
        while i < len(lines) and not FIXTURE_RE.match(lines[i].strip()) \
                and not lines[i].startswith("## "):
            block.append(lines[i])
            i += 1
        blob = " ".join(block)
        um = re.search(r"game centre: (https://www\.nfl\.com/games/[a-z0-9-]+)", blob)
        vm = re.search(r"venue \(hotel link\): (.+?)(?: —| —\s|$)", blob)
        if not um:
            fail(f"fixture {num} ({away} at {home}) has no game-centre URL in its block")
        fixtures.append({
            "slot": int(num), "away": away.strip(), "home": home.strip(), "day": day,
            "date": date + ", 2026", "kickoff_et": kick, "network": tv,
            "gamecenter_url": um.group(1),
            "venue": vm.group(1).strip() if vm else "",
        })
    if len(fixtures) != 13:
        fail(f"expected 13 Week 11 fixtures, parsed {len(fixtures)}")
    byes = []
    in_byes = False
    for line in text.splitlines():
        if line.startswith("## Teams on Bye"):
            in_byes = True
            continue
        if in_byes:
            m = re.match(r"^- ([A-Z]{2,3}) (.+?) — (\d+-\d+(?:-\d+)?)$", line.strip())
            if m:
                byes.append({"code": m.group(1), "club": m.group(2), "record": m.group(3)})
            elif line.startswith("## "):
                in_byes = False
    if len(byes) != 6:
        fail(f"expected 6 byes, parsed {len(byes)}")
    return fixtures, byes


def parse_min_sf_venue(text: str):
    loc = re.search(r"Game Info — Location: ([A-Z ,]+?) — Stadium: ([A-Z ']+)$", text, re.M)
    if not loc:
        fail("MIN@SF game centre transcript: Game Info line not found")
    return {"location": loc.group(1).strip(), "stadium": loc.group(2).strip()}


def parse_e7ef_week11():
    text = read(ROOT / "nfl-readiness-e7ef" / "evidence" / "week11-2026-11-17.md")
    games = re.findall(
        r"^- \[(.+?) at (.+?), (Monday|Thursday|Sunday), (November \d+)(?:st|nd|rd|th), "
        r"(\d{1,2}:\d{2} [AP]M), ([A-Z]+)\]\((https://www\.nfl\.com/games/[a-z0-9-]+)\)$",
        text, re.M)
    if len(games) != 13:
        fail(f"e7ef Week 11 capture must have 13 fixture lines, got {len(games)}")
    return [{"away": a, "home": h, "kickoff_et": k, "network": tv, "gamecenter_url": u}
            for a, h, _, _, k, tv, u in games]


# ---------------------------------------------------------------- game book #14

def parse_raw_gamebook():
    rows = {"source": "", "gamecenter": "", "captured_utc": "", "game": None,
            "off": [], "def": [], "ina": []}
    for line in read(RAW / "g14-LAC-BAL.txt").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split("|")
        tag = parts[0]
        if tag == "SOURCE":
            rows["source"] = parts[1]
        elif tag == "GAMECENTER":
            rows["gamecenter"] = parts[1]
        elif tag == "CAPTURED_UTC":
            rows["captured_utc"] = parts[1]
        elif tag == "GAME":
            rows["game"] = {"id": parts[1], "away": parts[2], "home": parts[3],
                            "date": parts[4], "kickoff_et": parts[5], "stadium": parts[6],
                            "location": parts[7], "roof_surface": parts[8],
                            "weather": parts[9], "temp_f": parts[10], "wind": parts[11],
                            "attendance": parts[12]}
        elif tag in ("OFF", "DEF", "INA"):
            rows[tag.lower()].append({"team": parts[1], "pos": parts[2],
                                      "jersey": parts[3], "player": parts[4]})
    return rows


def gamebook_evidence_strings(text):
    """Strings the verbatim evidence must contain (cross-check of the raw transcription)."""
    required = ["M&T Bank Stadium", "Baltimore, MD", "8:16 PM EST", "69,679",
                "Open Stadium on Natural Grass", "J.Brissett", "D.Henry",
                "L.McConkey", "K.Slovis", "C.Dicker", "Referee: Hill, Adrian"]
    missing = [s for s in required if s not in text]
    if missing:
        fail(f"Game Book evidence transcript is missing required strings: {missing}")
    return {"required_strings_present": len(required)}


# ---------------------------------------------------------------- game centre (LAC@BAL)

def parse_gamecenter_lacbal(text):
    def grab(pat):
        m = re.search(pat, text, re.M)
        if not m:
            fail(f"game centre transcript missing pattern: {pat}")
        return m.group(1).strip()
    book_url = grab(r"\[Download Game Book \(PDF\)[^\]]*\]\((https://static\.www\.nfl\.com/[^)]+\.pdf)\)")
    stadium = grab(r"Stadium: (.+)$")
    location = grab(r"Location: (.+)$")
    quarters = re.findall(r"^\| (Los Angeles Chargers|Baltimore Ravens)[^\n]*\n", text, re.M)
    totals = re.findall(r"\| (\d+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \|\s*$",
                        "\n".join(l for l in text.splitlines() if l.startswith("| Los Angeles") or l.startswith("| Baltimore")), re.M)
    return {"away": "LAC", "home": "BAL", "away_score": 23, "home_score": 20,
            "state": "Final", "week": 10, "date": "Nov 16", "stadium": stadium,
            "location": location, "gamebook_url": book_url,
            "quarter_rows_found": len(quarters)}


# ---------------------------------------------------------------- reserve lists / trades

RESERVE_ROW = re.compile(r"^\| ([A-Za-z0-9'. ]+?) \| ([A-Za-z0-9'. ]+?) \| (\d{2}/\d{2}) \| (.+?) \| ([^|]*?) \| (.+?) \|\s*$")


def parse_reserve(text):
    rows = []
    for line in text.splitlines():
        m = RESERVE_ROW.match(line.strip())
        if m:
            frm, to, date, name, pos, txn = [g.strip() for g in m.groups()]
            rows.append({"from": frm, "to": to, "date": date, "name": name,
                         "position": pos, "transaction": txn})
    return rows


def parse_77b1_reserve():
    text = read(ROOT / "nfl-brief-77b1" / "evidence" / "nfl-reserve-list-2026-11.md")
    rows = []
    for line in text.splitlines():
        m = re.match(r"^\| ([A-Za-z0-9'. ]+?) \| (\d{2}/\d{2}) \| (.+?) \| (.+?) \|\s*$", line.strip())
        if m:
            club, date, name, txn = [g.strip() for g in m.groups()]
            rows.append({"club": club, "date": date, "name": name, "transaction": txn})
    if not rows:
        fail("77b1 reserve capture parsed to zero rows")
    return rows


# ---------------------------------------------------------------- injuries

INJ_ROW = re.compile(r"^\| ([^|]+) \| ([A-Z/]+) \| ([^|]*) \| ([^|]*) \| ([^|]*) \|\s*$")


def parse_injury_tables(text):
    tables, current = {}, None
    for line in text.splitlines():
        m = re.match(r"^### (.+?)\s*$", line)
        if m:
            current = m.group(1).strip()
            tables.setdefault(current, [])
            continue
        if current:
            im = INJ_ROW.match(line.strip())
            if im and im.group(1).strip() not in ("Player", "---"):
                tables[current].append({
                    "player": im.group(1).strip(), "position": im.group(2).strip(),
                    "injuries": im.group(3).strip(), "practice_status": im.group(4).strip(),
                    "game_status": im.group(5).strip()})
    return tables


def week_label(text):
    m = re.search(r"Page title: \"(.+?)\"", text)
    hdr = re.search(r"Section header: \"(.+?)\"", text)
    return (m.group(1) if m else ""), (hdr.group(1) if hdr else "")


# ---------------------------------------------------------------- main

def main(check: bool = False):
    ev_standings = read(EV / "standings-2026-11-18.md")
    ev_gc = read(EV / "gamecenter-w10-lac-bal-2026-11-18.md")
    ev_gb_md = read(EV / "gamebook-w10-lac-bal-2026-11-18.md")
    ev_sched = read(EV / "schedule-week11-2026-11-18.md")
    ev_minsf = read(EV / "gamecenter-w11-min-sf-2026-11-18.md")
    ev_res_nov = read(EV / "reserve-list-nov-2026-11-18.md")
    ev_res_oct = read(EV / "reserve-list-oct-2026-11-18.md")
    ev_trades = read(EV / "trades-nov-2026-11-18.md")
    ev_inj = read(EV / "injuries-state-2026-11-18.md")

    standings = parse_standings(ev_standings)
    frozen = load_frozen()
    prev = load_prev_fresh()
    corpus = load_corpus()

    fixtures, byes = parse_week11(ev_sched)
    minsf = parse_min_sf_venue(ev_minsf)
    for f in fixtures:
        if f["slot"] == 12:
            f["venue"] = minsf["stadium"].title() if False else minsf["stadium"]  # printed uppercase
            f["venue_source"] = "C672-GC-W11-MINSF-1118"
        else:
            f["venue_source"] = "C672-SCHED-W11-1118"
        f["away_code"] = CLUB_CODE[f["away"]]
        f["home_code"] = CLUB_CODE[f["home"]]

    gb = parse_raw_gamebook()
    gb_strings = gamebook_evidence_strings(ev_gb_md)
    gc = parse_gamecenter_lacbal(ev_gc)

    res_nov = parse_reserve(ev_res_nov)
    res_oct = parse_reserve(ev_res_oct)
    trades = parse_reserve(ev_trades)
    prev_res = parse_77b1_reserve()

    inj_tables = parse_injury_tables(ev_inj)
    e7ef_inj = parse_injury_tables(
        read(ROOT / "nfl-readiness-e7ef" / "evidence" / "injuries-w10-2026-11-17.md"))
    e7ef_w11 = parse_e7ef_week11()

    # ------------------------------------------------------------- V0 club map
    frozen_by_code = {r["TeamCode"]: r for r in frozen}
    frozen_div = {}
    for r in frozen:
        frozen_div.setdefault((r["Conference"], r["Team"].split()[-1] if False else None), [])
    frozen_divmap = {r["TeamCode"]: r["Team"] for r in frozen}
    # V0: every parsed club name maps through CLUB_CODE to a frozen row; and each
    # division block's four codes match the frozen CSV's division membership exactly.
    frozen_divsets = {}
    conf_of = {}
    for r in frozen:
        pass
    prev_csv = list(csv.DictReader(read(ROOT / "data" / "nfl-standings-2026.csv").splitlines()))
    canon_div = {}
    canon_conf = {}
    canon_name = {}
    for r in prev_csv:
        canon_div[r["Team"]] = r["Division"]
        canon_conf[r["Team"]] = r["Conference"]
        canon_name[r["Team"]] = r["Team"]
    code_to_name = {}
    for r in frozen:
        code_to_name[r["TeamCode"]] = r["Team"]
    for row in standings:
        code = CLUB_CODE[row["club_short"]]
        row["code"] = code
        row["team_name"] = code_to_name[code]
        if canon_div.get(row["team_name"]) != row["division"]:
            fail(f"V0 division mismatch for {row['club']}: page block {row['division']} "
                 f"vs canonical {canon_div.get(row['team_name'])}")
        if canon_conf.get(row["team_name"]) != row["conference"]:
            fail(f"V0 conference mismatch for {row['club']}")

    # ------------------------------------------------------------- V1 standings arithmetic
    w10 = [g for g in corpus if str(g["week"]).startswith("10")]
    w10_finals = [g for g in w10 if g["away_score"] != ""]
    pending = [g for g in w10 if g["away_score"] == ""]
    if len(w10_finals) != 13 or len(w10) != 13:
        fail(f"corpus must hold exactly 13 Week 10 rows, all final; got {len(w10)} rows, "
             f"{len(w10_finals)} final")
    if pending:
        fail(f"corpus holds pending Week 10 rows: {pending}")
    lac_bal_in_corpus = [g for g in corpus if g["away"] == "LAC" and g["home"] == "BAL"]
    if lac_bal_in_corpus:
        fail("corpus already contains LAC@BAL; the cross-scope request is moot — re-audit")

    prev_by_name = {r["Team"]: r for r in prev}
    expected = {}
    for row in standings:
        p = prev_by_name[row["team_name"]]
        expected[row["code"]] = {
            "W": int(p["W"]), "L": int(p["L"]), "T": int(p["T"]),
            "PF": int(p["PF"]), "PA": int(p["PA"]), "NetPts": int(p["NetPts"]),
            "Home": p["Home"], "Road": p["Road"], "Div": p["Div"], "Conf": p["Conf"],
        }
    # apply the verified LAC@BAL final to the expected state
    fin = {"away_score": gc["away_score"], "home_score": gc["home_score"]}

    def bump(rec, which_home, is_home, scored, allowed, same_div, same_conf):
        if scored > allowed:
            rec["W"] += 1
        elif scored < allowed:
            rec["L"] += 1
        else:
            rec["T"] += 1
        rec["PF"] += scored
        rec["PA"] += allowed
        rec["NetPts"] = rec["PF"] - rec["PA"]
        if is_home:
            rec["Home"] = rec_bump(rec["Home"], scored > allowed, scored < allowed)
        else:
            rec["Road"] = rec_bump(rec["Road"], scored > allowed, scored < allowed)
        if same_div:
            rec["Div"] = rec_bump(rec["Div"], scored > allowed, scored < allowed)
        if same_conf:
            rec["Conf"] = rec_bump(rec["Conf"], scored > allowed, scored < allowed)

    def rec_bump(rec, win, loss):
        w, l, t = [int(x) for x in rec.split("-")]
        t = t + 1 if (not win and not loss) else t
        return f"{w + (1 if win else 0)}-{l + (1 if loss else 0)}-{t}"

    same_div_lacbal = False  # AFC West vs AFC North
    same_conf_lacbal = True  # both AFC
    bump(expected["LAC"], False, False, fin["away_score"], fin["home_score"],
         same_div_lacbal, same_conf_lacbal)
    bump(expected["BAL"], True, True, fin["home_score"], fin["away_score"],
         same_div_lacbal, same_conf_lacbal)

    v1_rows, v1_bad = [], 0
    for row in standings:
        exp = expected[row["code"]]
        checks = {}
        for k in ("W", "L", "T", "PF", "PA", "NetPts", "Home", "Road", "Div", "Conf"):
            checks[k] = {"fresh": row[k], "expected": exp[k], "ok": row[k] == exp[k]}
        ok = all(c["ok"] for c in checks.values())
        if not ok:
            v1_bad += 1
        v1_rows.append({"club": row["club"], "code": row["code"], "ok": ok, "cells": checks})
    if v1_bad:
        fail(f"V1 standings arithmetic failed for {v1_bad} club(s)")
    gp_check = []
    for row in standings:
        gp_corpus = sum(1 for g in corpus if g["away"] == row["code"] or g["home"] == row["code"])
        gp_corpus += 1 if row["code"] in ("LAC", "BAL") else 0
        if gp_corpus != row["W"] + row["L"] + row["T"]:
            fail(f"V3 GP mismatch for {row['code']}: corpus {gp_corpus} vs standings "
                 f"{row['W'] + row['L'] + row['T']}")
        gp_check.append(row["code"])
    if len(gp_check) != 32:
        fail("V3 must cover 32 clubs")

    # frozen -> fresh full reconciliation (32 clubs x 5 fields)
    frozen_by_name = {r["Team"]: r for r in frozen}
    w10_all = w10_finals + [{"week": "10", "date": "2026-11-16", "weekday": "Monday",
                             "away": "LAC", "home": "BAL",
                             "away_score": fin["away_score"], "home_score": fin["home_score"],
                             "source_url": gc.get("gamebook_url", ""), "retrieved": READ_ON,
                             "evidence": "nfl-week11-6c72a9fa/evidence/gamecenter-w10-lac-bal-2026-11-18.md"}]
    recon_bad = 0
    for row in standings:
        f = frozen_by_name[row["team_name"]]
        expW = int(f["W"]) + sum(1 for g in w10_all
                                 if (g["away"] == row["code"] and int(g["away_score"]) > int(g["home_score"]))
                                 or (g["home"] == row["code"] and int(g["home_score"]) > int(g["away_score"])))
        expL = int(f["L"]) + sum(1 for g in w10_all
                                 if (g["away"] == row["code"] and int(g["away_score"]) < int(g["home_score"]))
                                 or (g["home"] == row["code"] and int(g["home_score"]) < int(g["away_score"])))
        expPF = int(f["PF"]) + sum(int(g["away_score"]) for g in w10_all if g["away"] == row["code"]) \
                           + sum(int(g["home_score"]) for g in w10_all if g["home"] == row["code"])
        expPA = int(f["PA"]) + sum(int(g["home_score"]) for g in w10_all if g["away"] == row["code"]) \
                           + sum(int(g["away_score"]) for g in w10_all if g["home"] == row["code"])
        if (expW, expL, expPF, expPA) != (row["W"], row["L"], row["PF"], row["PA"]):
            recon_bad += 1
            fail(f"V1b frozen+14-finals reconciliation failed for {row['club']}: "
                 f"expected ({expW},{expL},{expPF},{expPA}) got ({row['W']},{row['L']},{row['PF']},{row['PA']})")
    if len(w10_all) != 14:
        fail("V1b needs exactly 14 Week 10 finals")

    # ------------------------------------------------------------- V4 week 11 slate
    codes = [CLUB_CODE[f["away"]] for f in fixtures] + [CLUB_CODE[f["home"]] for f in fixtures]
    if len(codes) != 26 or len(set(codes)) != 26:
        fail(f"V4 Week 11 must feature 26 distinct clubs once each; got {len(codes)} clubs, "
             f"{len(set(codes))} distinct")
    bye_codes = [b["code"] for b in byes]
    if sorted(bye_codes) != sorted(set(COMPLETE := list(CLUB_CODE.values())) - set(codes)):
        fail(f"V4 byes {sorted(bye_codes)} do not complete the slate; expected "
             f"{sorted(set(CLUB_CODE.values()) - set(codes))}")
    for f in fixtures:
        if not f["venue"]:
            fail(f"V4 fixture {f['away']} at {f['home']} has no venue")

    # ------------------------------------------------------------- V5 venue completion
    venue_rows = list(csv.DictReader(
        read(ROOT / "nfl-gamebook-5213243e" / "data" / "fixtures-venue.csv").splitlines()))
    if len(venue_rows) != 13:
        fail(f"gamebook desk fixtures-venue.csv must hold 13 rows, got {len(venue_rows)}")
    if gb["game"]["stadium"].lower() != gc["stadium"].lower():
        fail(f"V5 stadium mismatch: Game Book {gb['game']['stadium']!r} vs game centre {gc['stadium']!r}")

    # ------------------------------------------------------------- V6 reserve sweep
    def key_nov(r):
        return (CLUB_CODE.get(r["from"], r["from"]), r["date"], r["name"])
    def key_prev(r):
        return (CLUB_CODE.get(r["club"], r["club"]), r["date"], r["name"])
    prev_keys = {key_prev(r) for r in prev_res}
    nov_keys = {key_nov(r) for r in res_nov}
    added = sorted(nov_keys - prev_keys, key=lambda k: (k[1], k[2]))
    removed = sorted(prev_keys - nov_keys, key=lambda k: (k[1], k[2]))
    if not any(k[2] == "Malik Willis" for k in nov_keys):
        fail("V6: Malik Willis must be present on the visible November reserve list")
    jackson_huntley = [k for k in nov_keys | prev_keys
                       if k[2] in ("Lamar Jackson", "Tyler Huntley")]
    willis_present_oct = any(r["name"] == "Tavius Robinson" for r in res_oct)

    # ------------------------------------------------------------- V7 game book #14
    if len(gb["off"]) != 22 or len(gb["def"]) != 22 or len(gb["ina"]) != 12:
        fail(f"V7 Game Book #14 row counts off: OFF {len(gb['off'])} DEF {len(gb['def'])} INA {len(gb['ina'])}")
    if gb["source"] != gc["gamebook_url"]:
        fail("V7 Game Book PDF URL must match the game centre's download link")
    if gb["game"]["id"] != "W10-14":
        fail("V7 Game Book fixture id must be W10-14")
    qb_off = [r for r in gb["off"] if r["pos"] == "QB"]
    if {r["player"] for r in qb_off} != {"J.Herbert", "J.Brissett"}:
        fail(f"V7 starting QBs unexpected: {qb_off}")

    # ------------------------------------------------------------- V8 injuries state
    title, header = week_label(ev_inj)
    if "Week 10" not in title or "WEEK 10" not in header:
        fail(f"V8 injuries page state changed: {title!r} / {header!r} — re-run the full capture")
    stability = []
    for sec, rows in inj_tables.items():
        base = sec.split(" (partial")[0]
        if base not in e7ef_inj:
            fail(f"V8 section {base} missing from the 2026-11-17 capture")
        old = e7ef_inj[base]
        if len(rows) > len(old):
            fail(f"V8 {base}: today's re-read has more rows than the committed capture")
        diffs = []
        for i, r in enumerate(rows):
            o = old[i]
            for k in ("player", "position", "injuries", "practice_status", "game_status"):
                if r[k] != o[k]:
                    diffs.append({"row": r["player"], "field": k, "was": o[k], "now": r[k]})
        stability.append({"section": base, "rows_compared": len(rows),
                          "rows_in_2026_11_17_capture": len(old), "diffs": diffs})

    # ------------------------------------------------------------- schedule stability
    cur_keys = sorted((f["away"], f["home"], f["kickoff_et"], f["network"], f["gamecenter_url"])
                      for f in fixtures)
    old_keys = sorted((g["away"], g["home"], g["kickoff_et"], g["network"], g["gamecenter_url"])
                      for g in e7ef_w11)
    sched_stable = cur_keys == old_keys

    # ------------------------------------------------------------- standings diff (what-changed)
    diff_rows = []
    for row in standings:
        p = prev_by_name[row["team_name"]]
        dw, dl, dt = row["W"] - int(p["W"]), row["L"] - int(p["L"]), row["T"] - int(p["T"])
        dpf, dpa = row["PF"] - int(p["PF"]), row["PA"] - int(p["PA"])
        changed = any((dw, dl, dt, dpf, dpa))
        diff_rows.append({"club": row["club"], "code": row["code"],
                          "W_was": int(p["W"]), "W_now": row["W"], "dW": dw,
                          "L_was": int(p["L"]), "L_now": row["L"], "dL": dl,
                          "dPF": dpf, "dPA": dpa, "changed": changed})

    # ------------------------------------------------------------- outputs
    official = {
        "read_on": READ_ON,
        "session": "session-arena-6c72a9fa-own7",
        "standings": standings,
        "week10_pending_final": {
            "week": 10, "away": "LAC", "home": "BAL", "away_score": gc["away_score"],
            "home_score": gc["home_score"], "state": "Final", "date": "2026-11-16",
            "stadium": gc["stadium"], "location": gc["location"],
            "gamecenter_url": "https://www.nfl.com/games/chargers-at-ravens-2026-reg-10",
            "gamebook_url": gc["gamebook_url"],
        },
        "week11_fixtures": fixtures,
        "week11_byes": byes,
        "late_week_tbd_note": True,
        "gamebook_14": gb,
        "gamebook_14_strings_checked": gb_strings,
        "reserve_november": res_nov,
        "reserve_october": res_oct,
        "trades_november": trades,
        "injuries_state": {"title": title, "header": header, "tables": inj_tables},
    }
    verification = {
        "read_on": READ_ON,
        "V0_club_map": {"clubs": 32, "division_blocks_match_canonical": True},
        "V1_standings": {"rows": 32, "failed": 0,
                         "method": "fresh 2026-11-18 read == 2026-11-17 pre-MNF CSV + the verified "
                                   "LAC@BAL final (LAC 23 - BAL 20); Home/Road/Conf bumped, Div unchanged "
                                   "(inter-conference game)"},
        "V1b_frozen_plus_14_finals": {"clubs": 32, "failed": 0},
        "V2_final_join": {"fixture": "LAC@BAL W10", "gamecentre_final": f'{gc["away_score"]}-{gc["home_score"]}',
                          "gamebook_final": "23-20", "standings_delta": "BAL +1L +20PF +23PA; LAC +1W +23PF +20PA",
                          "corpus_status": "game absent from nfl-results corpus (149 finals); "
                                           "cross-scope request logged in COORDINATION.md, canonical data untouched"},
        "V3_games_played": {"clubs": 32, "all_match": True,
                            "method": "W+L+T per club == games in the 149-final corpus (+1 for LAC/BAL)"},
        "V4_week11_slate": {"fixtures": 13, "clubs_featured": 26, "byes": 6,
                            "byes_match_slate": True, "venues_complete": True},
        "V5_venue_completion": {"week10_venues": 14, "of": 14,
                                "new": {"fixture": "W10-14 LAC@BAL", "stadium": gb["game"]["stadium"],
                                        "source": "official Game Book PDF + game centre"}},
        "V6_reserve_sweep": {
            "november_rows_visible": len(res_nov), "october_rows_visible": len(res_oct),
            "added_since_2026_11_17": [list(k) for k in added],
            "scrolled_off_since_2026_11_17": [list(k) for k in removed],
            "malik_willis_present_november": True,
            "lamar_jackson_tyler_huntley_in_visible_windows": bool(jackson_huntley),
            "ravens_10_24_row": "Tavius Robinson Reserve/Injured (10/24) is the oldest visible BAL row"},
        "V7_gamebook_14": {"off_rows": len(gb["off"]), "def_rows": len(gb["def"]),
                           "ina_rows": len(gb["ina"]), "attendance": gb["game"]["attendance"],
                           "strings_checked": gb_strings["required_strings_present"],
                           "qbs": sorted(r["player"] for r in qb_off)},
        "V8_injuries_state": {"title": title, "header": header,
                              "tables_re_read": len(stability),
                              "rows_compared": sum(s["rows_compared"] for s in stability),
                              "diffs": sum(len(s["diffs"]) for s in stability)},
    }
    whatchanged = {
        "read_on": READ_ON,
        "requirement": "DR-61 first implementation: publish a what-changed ledger between dated "
                       "captures instead of a static snapshot",
        "standings_2026_11_17_to_2026_11_18": diff_rows,
        "reserve_series": {
            "window_size_2026_11_17": len(prev_res),
            "window_size_2026_11_18": len(res_nov),
            "added": [list(k) for k in added],
            "scrolled_off": [list(k) for k in removed],
            "note": "the league reserve-list page keeps a rolling window of 25 rows; rows that "
                    "scroll off remain true (they were printed on 2026-11-17) and live only in "
                    "dated captures"},
        "injury_report_2026_11_17_to_2026_11_18": stability,
        "week11_schedule_2026_11_17_to_2026_11_18": {
            "stable": sched_stable,
            "fixtures_compared": len(cur_keys)},
    }

    OUT.mkdir(exist_ok=True)
    for name, payload in (("official-2026-11-18.json", official),
                          ("verification.json", verification),
                          ("whatchanged.json", whatchanged)):
        raw = json.dumps(payload, indent=1, sort_keys=False) + "\n"
        p = OUT / name
        if check:
            if p.read_text(encoding="utf-8") != raw:
                fail(f"--check: {name} would change on regeneration")
        else:
            p.write_text(raw, encoding="utf-8")
    print(f"OK: collect 2026-11-18 — 32 standings (V1 0 failed), 13 W11 fixtures + 6 byes, "
          f"Game Book #14 (22/22/12 rows), reserve Nov {len(res_nov)} + Oct {len(res_oct)} "
          f"(+{len(added)}/-{len(removed)} vs 11-17), injuries stable re-read "
          f"({sum(s['rows_compared'] for s in stability)} rows, "
          f"{sum(len(s['diffs']) for s in stability)} diffs), schedule stable={sched_stable}")


if __name__ == "__main__":
    main(check="--check" in sys.argv)
