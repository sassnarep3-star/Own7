#!/usr/bin/env python3
"""Week 10 completion & weekly-diff desk (session arena/03dcea07-own7).

Every value published by this desk is transcribed from an official NFL page or PDF
read 2026-11-18 (evidence/ folder, verbatim transcripts) or re-derived arithmetically
from committed repository artefacts (frozen standings, the official results corpus,
the Game Book desk's venue capture). Nothing is inferred. Where an official source
does not publish a value, the cell is emitted blank and the gap is flagged.

What this desk adds (advances DR-23, DR-25, DR-31, DR-47, DR-61, DR-68 numbers):
  1. The 14th and final Week 10 Game Book (LAC at BAL) — the week's venue/roof/weather
     capture becomes 14/14 and the official results feed gains its 150th final.
  2. The weekly "what changed" diff (DR-61): rendered rank/record/points deltas across
     three dated official standings reads (2026-11-12 frozen, 2026-11-17, 2026-11-18),
     plus the dated availability-read delta.
  3. The official 2026 kickoff/onside-kick rule text (DR-68), quoted from the league's
     own rulebook page.

Inputs (all committed, all read-only):
  evidence/*.md                       verbatim transcripts of official reads taken 2026-11-18
  data/nfl-standings-week10-2026.csv  frozen pre-Week-10 standings read 2026-11-12
  data/nfl-standings-2026-11-17.csv   pre-Monday standings read 2026-11-17
  data/nfl-standings-2026.csv         division-membership reference (verified desk data)
  nfl-results/data/games-2026-w1-10.csv  official results corpus (149 rows, frozen desk)
  nfl-gamebook-5213243e/data/fixtures-venue.csv  the 13 captured Week 10 Game Books

Outputs: data/*.csv, data/*.json, site/*.html, site/style.css, site/manifest.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
SITE = ROOT / "site"
EVID = ROOT / "evidence"
REPO = ROOT.parent

READ_AT = "2026-11-18T03:49:17Z..2026-11-18T03:58:00Z"

# ------------------------------------------------------------------ sources ----
# Every id here is also registered in research/sources.json and scripts/check_site.py
# SOURCE_HOSTS (additive lines by this session). Rows may only cite these ids.
SRC = {
    "SL-1118-STANDINGS": "https://www.nfl.com/standings/",
    "SL-1118-SCHED-W10": "https://www.nfl.com/schedules/2026/by-week/week-10",
    "SL-1118-GAMEBOOK-PDF": "https://static.www.nfl.com/image/upload/v1794916121/gamecenter/ab78ad5a-4feb-11f1-abca-2c54536568a9.pdf",
    "SL-1118-GAMECENTER": "https://www.nfl.com/games/chargers-at-ravens-2026-reg-10",
    "SL-1118-INJ-PAGE": "https://www.nfl.com/injuries/",
    "SL-1118-INJ-REG11": "https://www.nfl.com/injuries/league/2026/REG11",
    "SL-1118-OPS-RULEBOOK": "https://operations.nfl.com/rules-officiating/2026-nfl-rulebook",
    "SL-REPO-FROZEN-STANDINGS": "https://github.com/sassnarep3-star/Own7/blob/main/data/nfl-standings-week10-2026.csv",
    "SL-REPO-NOV17-STANDINGS": "https://github.com/sassnarep3-star/Own7/blob/main/data/nfl-standings-2026-11-17.csv",
    "SL-REPO-GB-FIXTURES": "https://github.com/sassnarep3-star/Own7/blob/main/nfl-gamebook-5213243e/data/fixtures-venue.csv",
    "SL-REPO-RESULTS-CORPUS": "https://github.com/sassnarep3-star/Own7/blob/main/nfl-results/data/games-2026-w1-10.csv",
    "SL-REPO-DIVISIONS": "https://github.com/sassnarep3-star/Own7/blob/main/data/nfl-standings-2026.csv",
}

STANDINGS_URL = SRC["SL-1118-STANDINGS"]
SCHED_URL = SRC["SL-1118-SCHED-W10"]
GB_PDF_URL = SRC["SL-1118-GAMEBOOK-PDF"]
GB_GC_URL = SRC["SL-1118-GAMECENTER"]

NAME_TO_CODE = {
    "Cardinals": "AZ", "Falcons": "ATL", "Ravens": "BAL", "Bills": "BUF",
    "Panthers": "CAR", "Bengals": "CIN", "Browns": "CLE", "Cowboys": "DAL",
    "Broncos": "DEN", "Lions": "DET", "Packers": "GB", "Texans": "HOU",
    "Colts": "IND", "Jaguars": "JAX", "Chiefs": "KC", "Raiders": "LV",
    "Chargers": "LAC", "Rams": "LA", "Dolphins": "MIA", "Vikings": "MIN",
    "Patriots": "NE", "Saints": "NO", "Giants": "NYG", "Jets": "NYJ",
    "Eagles": "PHI", "Steelers": "PIT", "49ers": "SF", "Seahawks": "SEA",
    "Buccaneers": "TB", "Titans": "TEN", "Commanders": "WAS", "Bears": "CHI",
}

AFC = ("BUF NE NYJ MIA PIT CIN CLE BAL JAX HOU IND TEN DEN KC LV LAC").split()
NFC = ("NYG DAL WAS PHI CHI DET MIN GB CAR NO TB ATL SF SEA LA AZ").split()

# ------------------------------------------------------------------ helpers ----

def read_lines(name: str) -> list[str]:
    return (EVID / name).read_text(encoding="utf-8").splitlines()


def read_repo_csv(rel: str) -> list[dict]:
    with (REPO / rel).open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def sha256_of(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def die(msg: str) -> None:
    raise SystemExit(f"FAIL: {msg}")


# ------------------------------------------------------------------ parsing ----

STAND_ROW = re.compile(r"^\| \[!\[\]\([^)]*/logos/(?P<code>[A-Z]{2,3})\)\\")


def parse_standings(name: str) -> dict[str, dict]:
    """Parse the 32 rendered standings rows from the verbatim evidence transcript."""
    clubs: dict[str, dict] = {}
    for line in read_lines(name):
        m = STAND_ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.split("|")]
        code = m.group("code")
        data = cells[2:-1]
        if len(data) != 16:
            die(f"{name}: club {code}: expected 16 rendered cells, got {len(data)}")
        w, l, t, pct, pf, pa, net = data[0:7]
        home, road, div, conf = data[7], data[8], data[9], data[11]
        streak, last5 = data[14], data[15]
        for v in (w, l, t, pf, pa, net):
            if not re.fullmatch(r"-?\d+", v):
                die(f"{name}: club {code}: non-numeric standings field {v!r}")
        for v in (home, road, div, conf, last5):
            if not re.fullmatch(r"\d+ - \d+ - \d+", v):
                die(f"{name}: club {code}: malformed record cell {v!r}")
        if not re.fullmatch(r"\d+[WLT]", streak):
            die(f"{name}: club {code}: malformed streak {streak!r}")
        name_full = re.search(r"\\<br>\\<br>(.+?)\\<br>", cells[1])
        clubs[code] = {
            "code": code, "team": name_full.group(1) if name_full else code,
            "w": int(w), "l": int(l), "t": int(t), "pct": pct,
            "pf": int(pf), "pa": int(pa), "net": int(net),
            "home": home, "road": road, "div": div, "conf": conf,
            "streak": streak, "last5": last5,
        }
    return clubs


FINALE = re.compile(
    r"^-? ?\[(?P<away>[A-Za-z0-9'. ]+?) (?P<as>\d+), (?P<home>[A-Za-z0-9'. ]+?) (?P<hs>\d+), "
    r"FINAL, (?P<day>[A-Za-z]+), (?P<date>[A-Za-z]+ \d+[a-z]{2})\]\((?P<url>[^)]+)\)$")


def parse_week10_schedule() -> list[dict]:
    finals = []
    for line in read_lines("week10-schedule-2026-11-18.md"):
        m = FINALE.match(line)
        if m:
            away, home = m.group("away"), m.group("home")
            if away not in NAME_TO_CODE or home not in NAME_TO_CODE:
                die(f"schedule: unmapped club name {away!r}/{home!r}")
            finals.append({
                "away": NAME_TO_CODE[away], "home": NAME_TO_CODE[home],
                "as": int(m.group("as")), "hs": int(m.group("hs")),
                "day": m.group("day"), "date": m.group("date"), "url": m.group("url"),
            })
    return finals


BYE = re.compile(r"^(?P<code>[A-Z]{2,3})(?P<name>[A-Z][A-Za-z' ]+)$")


def parse_byes() -> list[str]:
    byes = []
    started = False
    for line in read_lines("week10-schedule-2026-11-18.md"):
        if line.startswith("### Teams on Bye"):
            started = True
            continue
        if started:
            m = BYE.match(line)
            if m and m.group("code") in NAME_TO_CODE.values():
                byes.append(m.group("code"))
            elif line.startswith("[Chevron Left]"):
                break
    return byes


def parse_gamebook() -> dict:
    text = "\n".join(read_lines("gamebook-lac-bal-2026-11-18.md"))
    out: dict = {}

    date_m = re.search(r"\| Date: ([A-Za-z]+, \d+/\d+/2026) \|  \| (.+?) \|  \|  \|  \| Start Time: ([\d:]+ [AP]M [A-Z]{3,4}) \|", text)
    if not date_m:
        die("gamebook: Date/venue line not found")
    out["date"], out["start_time"] = date_m.group(1), date_m.group(3)
    venue_m = re.match(r"^(.+?) at (.+?) at (.+), ([A-Za-z .]+), ([A-Z]{2})$", date_m.group(2))
    if not venue_m:
        die(f"gamebook: venue cell unparseable: {date_m.group(2)!r}")
    out["away_name"], out["home_name"] = venue_m.group(1), venue_m.group(2)
    out["stadium"], out["city_state"] = venue_m.group(3), venue_m.group(4) + ", " + venue_m.group(5)

    wx = re.search(r"\| Game Weather: ([^|]+?) \|  \|  \|  \|  \|  \| Temp: ([\d.]+)° F \([\d.]+° C\) Humidity: (\d+)%, Wind: ([^|]+?) \|", text)
    if not wx:
        die("gamebook: weather line not found")
    out["game_weather"], out["temp_f"], out["humidity_pct"], out["wind"] = (
        wx.group(1).strip(), wx.group(2), int(wx.group(3)), wx.group(4).strip())

    surf = re.search(r"\| (Open Stadium on [A-Za-z ]+|Fixed Roof[ A-Za-z]*|Retractable Roof[ A-Za-z-]*) \|", text)
    if not surf:
        die("gamebook: roof/surface line not found")
    out["roof_surface"] = surf.group(1).strip()

    att = re.search(r"Paid Attendance: ([\d,]+)\n\nTime: (\d+:\d+)", text)
    if not att:
        die("gamebook: attendance line not found")
    out["paid_attendance"], out["game_time"] = att.group(1), att.group(2)

    # lineups: 11 rows of four position/jersey-name pairs between the units header and Substitutions
    lines = text.splitlines()
    start_i = next(i for i, ln in enumerate(lines) if ln.startswith("| Offense |  | Defense |"))
    end_i = next(i for i, ln in enumerate(lines) if ln.startswith("| Substitutions |"))
    lineup_rows = [ln for ln in lines[start_i + 1:end_i] if ln.startswith("| ") and ln.strip() != "| Offense |  | Defense |"]
    pos_re = re.compile(r"^[A-Z]{1,3}(?:/[A-Z]{1,3})?$")
    who_re = re.compile(r"^(\d+) ([A-Za-z]+\.(?:\s?[A-Za-z]+))$")
    lineups: list[dict] = []
    for ln in lineup_rows:
        cells = [c.strip() for c in ln.split("|")][1:-1]
        if len(cells) not in (8, 10):
            die(f"gamebook: lineup row has {len(cells)} cells, expected 8 (or 8 + 2 trailing empty): {ln[:60]}")
        cells = cells[:8]
        quads = [("LAC", "Offense", cells[0], cells[1]), ("LAC", "Defense", cells[2], cells[3]),
                 ("BAL", "Offense", cells[4], cells[5]), ("BAL", "Defense", cells[6], cells[7])]
        for club, unit, pos, who in quads:
            if not pos_re.match(pos):
                die(f"gamebook: position cell unparseable: {pos!r}")
            pm = who_re.match(who)
            if not pm:
                die(f"gamebook: lineup pair unparseable: {who!r}")
            lineups.append({"club": club, "unit": unit, "position": pos,
                            "jersey": pm.group(1), "player": pm.group(2)})
    out["lineups"] = lineups

    inact_m = re.search(r"^\| Not Active \|  \|  \|  \|  \| Not Active \|", text, re.M)
    if not inact_m:
        die("gamebook: Not Active header not found")
    na_line = next((ln for ln in lines if ln.startswith("| WR 15 L.McConkey")), "")
    if not na_line.startswith("| "):
        die("gamebook: Not Active data row not found")
    cells = [c.strip() for c in na_line.split("|")][1:-1]
    if len(cells) != 10:
        die(f"gamebook: Not Active row has {len(cells)} cells, expected 10")
    item = re.compile(r"^(?P<pos>[A-Z0-9]+(?:/[A-Z0-9]+)?) (?P<jersey>\d+) (?P<player>[A-Za-z]+\.[A-Za-z]+)$")
    inactives: list[dict] = []
    for club, raw in (("LAC", cells[0]), ("BAL", cells[5])):
        if not raw:
            die(f"gamebook: empty Not Active list for {club}")
        for chunk in raw.split(", "):
            im = item.match(chunk)
            if not im:
                die(f"gamebook: inactive item unparseable: {chunk!r}")
            inactives.append({"club": club, "position": im.group("pos"),
                              "jersey": im.group("jersey"), "player": im.group("player")})
    out["inactives"] = inactives

    # the PDF boxline prints: VISITOR header (labels), then the visitor scores on the
    # HOME-labelled row, then the home scores on the row beneath it
    vis_i = next((i for i, ln in enumerate(lines) if ln.startswith("| VISITOR: | Los Angeles Chargers")), None)
    if vis_i is None:
        die("gamebook: VISITOR boxline header not found")
    score_rows = []
    for ln in lines[vis_i + 1:vis_i + 3]:
        cells = [c.strip() for c in ln.split("|")][1:-1]
        nums = [c for c in cells if c.isdigit()]
        nonnum = [c for c in cells if c and not c.isdigit()]
        if len(nums) != 6 or any(c not in ("HOME:", "Baltimore Ravens") for c in nonnum):
            die(f"gamebook: boxline score row unparseable: {ln[:60]!r}")
        score_rows.append([int(n) for n in nums])
    out["away_quarters"] = score_rows[0]
    out["home_quarters"] = score_rows[1]
    if not lines[vis_i + 1].startswith("| HOME: | Baltimore Ravens"):
        die("gamebook: unexpected row order under the VISITOR boxline header")

    officials = re.search(r"\| Referee: ([^|]+) \|", text)
    out["referee"] = officials.group(1).strip() if officials else ""
    return out


RULE_ROW = re.compile(r"^\| (?P<article>\d+-\d+(?:-\d+)?) \| (?P<desc>[^|]+) \|$")


def parse_rules() -> list[dict]:
    rows = []
    for line in read_lines("rules-2026-operations.md"):
        m = RULE_ROW.match(line)
        if m:
            rows.append({"article": m.group("article"), "description": m.group("desc").strip()})
    return rows


def load_name_map() -> dict[str, str]:
    """Canonical full-name -> code mapping, taken from the committed frozen CSV."""
    out = {}
    for r in read_repo_csv("data/nfl-standings-week10-2026.csv"):
        out[r["Team"]] = r["TeamCode"]
    return out


def load_frozen() -> dict[str, dict]:
    out = {}
    for r in read_repo_csv("data/nfl-standings-week10-2026.csv"):
        out[r["TeamCode"]] = {
            "team": r["Team"], "w": int(r["W"]), "l": int(r["L"]), "t": int(r["T"]),
            "pf": int(r["PF"]), "pa": int(r["PA"]), "net": int(r["NetPts"]),
            "home": r["Home"], "road": r["Road"], "streak": r["Streak"],
        }
    return out


def load_nov17(name_map: dict[str, str]) -> dict[str, dict]:
    out = {}
    for r in read_repo_csv("data/nfl-standings-2026-11-17.csv"):
        code = name_map.get(r["Team"])
        if code is None:
            die(f"nov17: unmapped club name {r['Team']!r}")
        out[code] = {
            "team": r["Team"], "w": int(r["W"]), "l": int(r["L"]), "t": int(r["T"]),
            "pf": int(r["PF"]), "pa": int(r["PA"]), "net": int(r["NetPts"]),
            "home": r["Home"], "road": r["Road"], "div": r["Div"], "conf": r["Conf"],
            "streak": r["Strk"], "last5": r["Last5"],
        }
    return out


def load_divisions(name_map: dict[str, str]) -> dict[str, str]:
    divs = {}
    for r in read_repo_csv("data/nfl-standings-2026.csv"):
        code = name_map.get(r["Team"])
        if code is None:
            die(f"divisions: unmapped club name {r['Team']!r}")
        divs[code] = r["Division"]
    return divs


def load_corpus_w10() -> tuple[list[dict], list[dict]]:
    """Week 10 finals from the official results corpus + its scheduled-not-final row."""
    finals, scheduled = [], []
    for r in read_repo_csv("nfl-results/data/games-2026-w1-10.csv"):
        if r["week"] == "10":
            finals.append(r)
    for r in read_repo_csv("nfl-results/data/scheduled-2026-w10.csv"):
        scheduled.append(r)
    return finals, scheduled


def rec_split(s: str) -> tuple[int, int, int]:
    w, l, t = re.sub(r"\s", "", s).split("-")
    return int(w), int(l), int(t)


# ------------------------------------------------------------------ records ----

def record_str(w: int, l: int, t: int) -> str:
    return f"{w} - {l} - {t}"


def pct_str(w: int, l: int, t: int) -> str:
    g = w + l + t
    return f"{(w + 0.5 * t) / g:.3f}" if g else "0.000"


def apply_finals(base: dict[str, dict], finals: list[dict], divisions: dict[str, str]) -> dict[str, dict]:
    """Re-derive every club's standings cells from a base snapshot plus given finals."""
    st = {c: {
        "w": b["w"], "l": b["l"], "t": b["t"], "pf": b["pf"], "pa": b["pa"],
        "home_w": rec_split(b["home"])[0], "home_l": rec_split(b["home"])[1], "home_t": rec_split(b["home"])[2],
        "road_w": rec_split(b["road"])[0], "road_l": rec_split(b["road"])[1], "road_t": rec_split(b["road"])[2],
        "div": {"w": 0, "l": 0, "t": 0}, "conf": {"w": 0, "l": 0, "t": 0},
        "streak": b["streak"], "last5": b.get("last5", ""),
    } for c, b in base.items()}
    for c, b in base.items():
        if "div" in b:  # Nov-17 snapshot carries division/conference records as text
            w, l, t = rec_split(b["div"])
            st[c]["div"] = {"w": w, "l": l, "t": t}
            w, l, t = rec_split(b["conf"])
            st[c]["conf"] = {"w": w, "l": l, "t": t}
    for f in finals:
        aw, hm = f["away"], f["home"]
        as_ = int(f.get("as", f.get("away_score")))
        hs = int(f.get("hs", f.get("home_score")))
        for c in (aw, hm):
            if c not in st:
                die(f"final {f}: club {c} not in base snapshot")
        if as_ > hs:
            winner, loser, ws, ls = aw, hm, as_, hs
        elif hs > as_:
            winner, loser, ws, ls = hm, aw, hs, as_
        else:
            die("final: tie handling not needed for Week 10 (no tied games); abort")
        st[winner]["w"] += 1
        st[loser]["l"] += 1
        st[aw]["pf"] += as_
        st[aw]["pa"] += hs
        st[hm]["pf"] += hs
        st[hm]["pa"] += as_
        for c, is_home in ((aw, False), (hm, True)):
            won = (c == winner)
            key_w = "home_w" if is_home else "road_w"
            key_l = "home_l" if is_home else "road_l"
            if won:
                st[c][key_w] += 1
            else:
                st[c][key_l] += 1
        for c in (aw, hm):
            rec = st[c]["div" if divisions.get(c) == divisions.get(
                aw if c == hm else hm) else "conf"]
            won = (c == winner)
            rec["w" if won else "l"] += 1
    return st


def derived_view(st: dict[str, dict]) -> dict[str, dict]:
    out = {}
    for c, s in st.items():
        out[c] = {
            "w": s["w"], "l": s["l"], "t": s["t"], "pct": pct_str(s["w"], s["l"], s["t"]),
            "pf": s["pf"], "pa": s["pa"], "net": s["pf"] - s["pa"],
            "home": record_str(s["home_w"], s["home_l"], s["home_t"]),
            "road": record_str(s["road_w"], s["road_l"], s["road_t"]),
            "div": record_str(s["div"]["w"], s["div"]["l"], s["div"]["t"]),
            "conf": record_str(s["conf"]["w"], s["conf"]["l"], s["conf"]["t"]),
            "streak": s["streak"], "last5": s["last5"],
        }
    return out


def streak_after(old: str, won: bool, lost: bool) -> str:
    n = int(old[:-1])
    kind = old[-1]
    if won:
        return (f"{n + 1}W" if kind == "W" else "1W")
    if lost:
        return (f"{n + 1}L" if kind == "L" else "1L")
    return old


# ------------------------------------------------------------------ checks -----

def run_checks(fresh, frozen, nov17, divisions, finals14, corpus_w10_finals, corpus_sched, gb, byes, rules) -> tuple[list[dict], dict]:
    checks: list[dict] = []
    ok = lambda b: "pass" if b else "FAIL"

    # V1 — fresh read integrity
    problems = []
    if len(fresh) != 32:
        problems.append(f"club count {len(fresh)} != 32")
    if set(fresh) != set(AFC) | set(NFC):
        problems.append("club set differs from the canonical 32-club reference set")
    for c, r in fresh.items():
        if r["pct"] != pct_str(r["w"], r["l"], r["t"]):
            problems.append(f"{c}: PCT cell {r['pct']} != re-derived {pct_str(r['w'], r['l'], r['t'])}")
        if r["net"] != r["pf"] - r["pa"]:
            problems.append(f"{c}: NET != PF-PA")
        games = sum(rec_split(x)[0] + rec_split(x)[1] + rec_split(x)[2] for x in (r["home"], r["road"]))
        if r["w"] + r["l"] + r["t"] != games:
            problems.append(f"{c}: W+L+T != home+road games")
    checks.append({"id": "V1", "result": ok(not problems),
                   "detail": "fresh standings parse: 32 clubs, canonical club set, PCT/NET/home-road arithmetic re-derived"
                             + (f"; problems: {'; '.join(problems)}" if problems else ""),
                   "source": "SL-1118-STANDINGS"})

    # V2 — frozen (2026-11-12) + all 14 Week 10 finals == fresh page
    w10 = list(corpus_w10_finals) + [{
        "week": "10", "away": "LAC", "home": "BAL", "away_score": "23", "home_score": "20",
        "source_url": SCHED_URL,
    }]
    st = apply_finals(frozen, w10, divisions)
    derived = derived_view(st)
    mism = []
    # the frozen snapshot predates Week 10 and carries no Div/Conf text, so V2 verifies
    # the cells it does carry; V3 (Nov-17 baseline) verifies Div/Conf for all 32 clubs
    for c in fresh:
        for k in ("w", "l", "t", "pct", "pf", "pa", "net", "home", "road"):
            if str(derived[c][k]) != str(fresh[c][k]):
                mism.append(f"{c}.{k}: derived {derived[c][k]} vs page {fresh[c][k]}")
    checks.append({"id": "V2", "result": ok(not mism),
                   "detail": "frozen 2026-11-12 standings + 13 corpus Week 10 finals + LAC@BAL 23-20 re-derive every W/L/T/PCT/PF/PA/NET/Home/Road cell of the fresh page for all 32 clubs"
                             + (f"; mismatches: {'; '.join(mism[:8])}" if mism else ""),
                   "source": "SL-1118-STANDINGS"})

    # V3 — Nov-17 read + the Monday game == fresh page (and 30 idle clubs unchanged cell-for-cell)
    st17 = apply_finals(nov17, [{"week": "10", "away": "LAC", "home": "BAL", "away_score": "23", "home_score": "20", "source_url": SCHED_URL}], divisions)
    d17 = derived_view(st17)
    mism = []
    for c in fresh:
        for k in ("w", "l", "t", "pct", "pf", "pa", "net", "home", "road", "div", "conf"):
            if str(d17[c][k]) != str(fresh[c][k]):
                mism.append(f"{c}.{k}: derived {d17[c][k]} vs page {fresh[c][k]}")
    # streak transitions for the two clubs that played Monday
    lac_s = streak_after(nov17["LAC"]["streak"], True, False)
    bal_s = streak_after(nov17["BAL"]["streak"], False, True)
    if lac_s != fresh["LAC"]["streak"]:
        mism.append(f"LAC.streak derived {lac_s} vs page {fresh['LAC']['streak']}")
    if bal_s != fresh["BAL"]["streak"]:
        mism.append(f"BAL.streak derived {bal_s} vs page {fresh['BAL']['streak']}")
    changed = sorted(c for c in fresh if any(
        str(d17[c][k]) != str(nov17[c][k]) for k in ("w", "l", "t", "pf", "pa", "net")))
    if changed != ["BAL", "LAC"]:
        mism.append(f"clubs changed vs Nov-17 read: {changed} != ['BAL', 'LAC']")
    for c in fresh:
        if c in ("BAL", "LAC"):
            continue  # their streaks are re-derived above; Last5 shifts by one game and is not re-derived
        if fresh[c]["streak"] != nov17[c]["streak"] or \
                re.sub(r"\s", "", fresh[c]["last5"]) != re.sub(r"\s", "", nov17[c]["last5"]):
            mism.append(f"{c}: streak/last5 changed although the club did not play between the reads")
    checks.append({"id": "V3", "result": ok(not mism),
                   "detail": "2026-11-17 read + LAC@BAL boxline = fresh 2026-11-18 page; exactly BAL and LAC changed"
                             + (f"; mismatches: {'; '.join(mism[:8])}" if mism else ""),
                   "source": "SL-1118-STANDINGS"})

    # V4 — the Game Book boxline agrees with the schedule-page final and its quarters sum
    aq, hq = gb["away_quarters"], gb["home_quarters"]
    a_tot, h_tot = aq[-1], hq[-1]
    ok_v4 = (sum(aq[:4]) == a_tot and sum(hq[:4]) == h_tot and a_tot == 23 and h_tot == 20)
    sched_final = next(f for f in finals14 if f["away"] == "LAC" and f["home"] == "BAL")
    ok_v4 = ok_v4 and (sched_final["as"], sched_final["hs"]) == (a_tot, h_tot)
    checks.append({"id": "V4", "result": ok(ok_v4),
                   "detail": f"Game Book boxline {a_tot}-{h_tot} (quarters {aq[:4]}/{hq[:4]}) equals the schedule-page final Chargers 23, Ravens 20",
                   "source": "SL-1118-SCHED-W10"})

    # V5 — Game Book structure
    probs = []
    if len(gb["lineups"]) != 44:
        probs.append(f"lineups {len(gb['lineups'])} != 44")
    per_club = {c: sum(1 for x in gb["lineups"] if x["club"] == c) for c in ("LAC", "BAL")}
    if per_club != {"LAC": 22, "BAL": 22}:
        probs.append(f"per-club lineup split {per_club} != 22/22")
    inact = {c: sum(1 for x in gb["inactives"] if x["club"] == c) for c in ("LAC", "BAL")}
    if inact != {"LAC": 6, "BAL": 6}:
        probs.append(f"inactive counts {inact} != 6/6")
    if gb["away_name"] != "Los Angeles Chargers" or gb["home_name"] != "Baltimore Ravens":
        probs.append("club names on the Game Book summary do not match the fixture")
    if gb["stadium"] != "M&T Bank Stadium":
        probs.append(f"stadium {gb['stadium']!r} != M&T Bank Stadium")
    checks.append({"id": "V5", "result": ok(not probs),
                   "detail": "Game Book parse: 44 starters (22/22), 6+6 Not Active, venue/stadium names consistent"
                             + (f"; problems: {'; '.join(probs)}" if probs else ""),
                   "source": "SL-1118-GAMEBOOK-PDF"})

    # V6 — the schedule read covers the full Week 10 slate exactly once
    slate = [f["away"] for f in finals14] + [f["home"] for f in finals14] + byes
    probs = []
    if len(finals14) != 14:
        probs.append(f"finals {len(finals14)} != 14")
    if len(byes) != 4:
        probs.append(f"byes {byes} != 4 clubs")
    if sorted(slate) != sorted(AFC + NFC):
        probs.append("14 fixtures + byes do not cover the 32 clubs exactly once")
    checks.append({"id": "V6", "result": ok(not probs),
                   "detail": "schedule read: 14 FINAL games + 4 byes = 32 clubs exactly once"
                             + (f"; problems: {'; '.join(probs)}" if probs else ""),
                   "source": "SL-1118-SCHED-W10"})

    # V7 — official rules table
    probs = []
    if len(rules) != 4:
        probs.append(f"rules rows {len(rules)} != 4")
    r616 = next((r for r in rules if r["article"] == "6-1-6"), None)
    if not r616 or "declare an onside kick at any time during the game" not in r616["description"]:
        probs.append("6-1-6 onside-kick declaration text not found verbatim")
    checks.append({"id": "V7", "result": ok(not probs),
                   "detail": "official 2026 rule changes table: 4 rows quoted verbatim incl. Rule 6-1-6"
                             + (f"; problems: {'; '.join(probs)}" if probs else ""),
                   "source": "SL-1118-OPS-RULEBOOK"})

    # V8 — Week 10 Game Book coverage completes to 14/14; the 14th joins the fixture set 1:1
    gb_rows = read_repo_csv("nfl-gamebook-5213243e/data/fixtures-venue.csv")
    gb_ids = [r["game_id"] for r in gb_rows]
    probs = []
    if gb_ids != [f"W10-{i:02d}" for i in range(1, 14)]:
        probs.append(f"Game Book desk captured {len(gb_ids)} fixtures (expected W10-01..W10-13)")
    checks.append({"id": "V8", "result": ok(not probs),
                   "detail": "venue/roof/weather capture now covers W10-01..W10-14 (13 committed by the Game Book desk + this desk's W10-14) = 14/14",
                   "source": "SL-REPO-GB-FIXTURES"})

    # V9 — results feed: 149 committed finals + this desk's read = 150; the corpus scheduled row is LAC@BAL
    probs = []
    total_corpus = len(read_repo_csv("nfl-results/data/games-2026-w1-10.csv"))
    if total_corpus != 149:
        probs.append(f"corpus rows {total_corpus} != 149")
    if len(corpus_sched) != 1 or (corpus_sched[0]["away"], corpus_sched[0]["home"]) != ("LAC", "BAL"):
        probs.append(f"corpus scheduled-not-final rows {[(r['away'], r['home']) for r in corpus_sched]} != LAC@BAL")
    checks.append({"id": "V9", "result": ok(not probs),
                   "detail": "official results feed: 149 committed finals + the now-final LAC@BAL read = 150; the corpus's scheduled-not-final row (nfl-results/data/scheduled-2026-w10.csv) is exactly the game this desk completes (read-only; the frozen corpus is not edited)",
                   "source": "SL-REPO-RESULTS-CORPUS"})

    # Build diff payloads (used by pages and data files)
    diffs = {
        "frozen_to_1118": diff_rows(fresh, frozen, w10, divisions),
        "nov17_to_1118": diff_rows(fresh, nov17, [{"week": "10", "away": "LAC", "home": "BAL", "away_score": "23", "home_score": "20"}], divisions),
    }
    return checks, diffs


def diff_rows(fresh: dict, base: dict, finals: list[dict], divisions: dict[str, dict]) -> list[dict]:
    """Per-club deltas between a base snapshot and the fresh page, with the week's result."""
    result_by_club: dict[str, str] = {}
    for f in finals:
        aw, hm = f["away"], f["home"]
        as_ = int(f.get("as", f.get("away_pts", f.get("away_score"))))
        hs = int(f.get("hs", f.get("home_pts", f.get("home_score"))))
        result_by_club[aw] = ("W" if as_ > hs else "L") + f" {as_}-{hs} @ {hm}"
        result_by_club[hm] = ("W" if hs > as_ else "L") + f" {hs}-{as_} vs {aw}"
    rows = []
    for code in sorted(fresh, key=lambda c: (-fresh[c]["w"], fresh[c]["l"], c)):
        f, b = fresh[code], base[code]
        rows.append({
            "code": code, "team": f["team"],
            "w0": b["w"], "l0": b["l"], "t0": b["t"],
            "dw": f["w"] - b["w"], "dl": f["l"] - b["l"], "dt": f["t"] - b["t"],
            "dpf": f["pf"] - b["pf"], "dpa": f["pa"] - b["pa"], "dnet": f["net"] - b["net"],
            "streak0": b.get("streak", ""), "streak1": f["streak"],
            "week10": result_by_club.get(code, "no game"),
        })
    return rows


# ------------------------------------------------------------------ output -----


def write_csv(name: str, header: list[str], rows: list[list]) -> None:
    with (DATA / name).open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows([header] + rows)


def build_data(fresh, diffs, gb, rules, checks) -> None:
    write_csv("standings-2026-11-18.csv",
              ["Code", "Team", "W", "L", "T", "PCT", "PF", "PA", "NetPts", "Home", "Road",
               "Div", "Conf", "Streak", "Last5", "SourceURL", "CheckedOn"],
              [[c["code"], c["team"], c["w"], c["l"], c["t"], c["pct"], c["pf"], c["pa"],
                c["net"], c["home"], c["road"], c["div"], c["conf"], c["streak"], c["last5"],
                STANDINGS_URL, "2026-11-18"]
               for c in (fresh[k] for k in sorted(fresh, key=lambda x: (x in NFC, fresh[x]["team"])))])

    def diff_csv(name: str, rows: list[dict], base_label: str):
        write_csv(name,
                  ["Code", "Team", f"W({base_label})", f"L({base_label})", f"T({base_label})",
                   "dW", "dL", "dT", "dPF", "dPA", "dNetPts", "Streak(before)", "Streak(now)",
                   "Week10", "Sources"],
                  [[r["code"], r["team"], r["w0"], r["l0"], r["t0"], r["dw"], r["dl"], r["dt"],
                    r["dpf"], r["dpa"], r["dnet"], r["streak0"], r["streak1"], r["week10"],
                    f"{STANDINGS_URL} | {SCHED_URL} | {SRC['SL-REPO-FROZEN-STANDINGS']}"]
                   for r in rows])

    diff_csv("standings-diff-frozen-2026-11-12_to_2026-11-18.csv", diffs["frozen_to_1118"], "11-12 frozen")
    diff_csv("standings-diff-2026-11-17_to_2026-11-18.csv", diffs["nov17_to_1118"], "11-17")

    # the 14th fixture in the Game Book desk's venue schema (joinable 1:1 on game_id)
    ev_sha = sha256_of(EVID / "gamebook-lac-bal-2026-11-18.md")
    md, mdd, yyyy = gb["date"].split()[-1].split("/")  # e.g. 11/16/2026
    iso_date = f"{yyyy}-{int(md):02d}-{int(mdd):02d}"
    if iso_date != "2026-11-16":
        die(f"gamebook date {gb['date']!r} does not resolve to 2026-11-16")
    write_csv("gamebook-w10-14-lac-bal.csv",
              ["game_id", "date", "kickoff_official", "away", "home", "venue_city_state",
               "stadium", "roof_and_surface", "game_weather", "temp_f", "humidity_pct", "wind",
               "paid_attendance", "source_url", "source_label", "gamecenter_url", "captured_utc",
               "raw_file", "raw_sha256"],
              [["W10-14", iso_date, gb["start_time"], "LAC", "BAL",
                gb["city_state"], gb["stadium"], gb["roof_surface"], gb["game_weather"],
                gb["temp_f"], gb["humidity_pct"], gb["wind"], gb["paid_attendance"],
                GB_PDF_URL, "NFL Game Book (official PDF)", GB_GC_URL, "2026-11-18",
                "evidence/gamebook-lac-bal-2026-11-18.md", ev_sha]])

    write_csv("lineups-w10-14.csv",
              ["club", "unit", "position", "jersey", "player", "source_url"],
              [[x["club"], x["unit"], x["position"], x["jersey"], x["player"], GB_PDF_URL]
               for x in gb["lineups"]])
    write_csv("inactives-w10-14.csv",
              ["club", "position", "jersey", "player", "source_url"],
              [[x["club"], x["position"], x["jersey"], x["player"], GB_PDF_URL]
               for x in gb["inactives"]])

    write_csv("rules-2026-changes.csv",
              ["article", "description_verbatim", "source_url", "checked_on"],
              [[r["article"], r["description"], SRC["SL-1118-OPS-RULEBOOK"], "2026-11-18"]
               for r in rules])

    (DATA / "verification.json").write_text(json.dumps(
        {"session": "arena/03dcea07-own7", "read_at": READ_AT, "checks": checks}, indent=2) + "\n",
        encoding="utf-8")

    flags = [
        {"id": "SL01", "title": "Secondary sources disagree about the 2026 onside-kick rule's scope",
         "detail": "The official operations.nfl.com 2026 rulebook table says Rule 6-1-6 'Permits the kicking team to declare an onside kick at any time during the game.' Two secondary articles found by web search claim the 2026 rule retains a trailing-team restriction, while others say any team may declare. This desk publishes only the official text and flags the conflict.",
         "source_ids": ["SL-1118-OPS-RULEBOOK"]},
        {"id": "SL02", "title": "Week 11 injury report not yet published at the 2026-11-18 read time",
         "detail": "https://www.nfl.com/injuries/league/2026/REG11 served the Week 10 report (canonical URL /reg10) at 2026-11-18 03:56 UTC. The availability-delta series advances with zero in-scope deltas; the first Week 11 deltas can only exist after Wednesday's publication.",
         "source_ids": ["SL-1118-INJ-REG11", "SL-1118-INJ-PAGE"]},
        {"id": "SL03", "title": "2026-11-18 injuries read is a spot check, not a full re-diff",
         "detail": "Only chunk 0 of 8 was re-read today (first 3 team tables, 20 rows, all cells equal to the 2026-11-17 capture). The full 347-row evidence retained by session arena/e7efbde7-own7 governs; a full re-diff was not performed.",
         "source_ids": ["SL-1118-INJ-PAGE"]},
        {"id": "SL04", "title": "Game Book copyright notice limits use without written NFL permission",
         "detail": "The Game Book states the summary is for assisting media coverage; other use is prohibited without written permission. This desk publishes the minimal venue/lineup/inactive facts with attribution and a link to the official PDF, mirroring the scope the Game Book desk already established; no play-by-play is republished.",
         "source_ids": ["SL-1118-GAMEBOOK-PDF"]},
        {"id": "SL05", "title": "One unlabelled record cell in the rendered standings rows is not published",
         "detail": "Each standings row renders an extra record cell between the conference-percentage and streak cells (e.g. BAL '2 - 1 - 0'); the text layer prints no label for it, so this desk neither publishes nor interprets that cell.",
         "source_ids": ["SL-1118-STANDINGS"]},
        {"id": "SL06", "title": "The frozen 149-final results corpus is not edited by this desk",
         "detail": "The corpus in nfl-results/data/games-2026-w1-10.csv (owned by another session) holds 149 finals with LAC@BAL scheduled-not-final. This desk records the 150th final read-only; the feed reaches 150 only across the two desks' files.",
         "source_ids": ["SL-REPO-RESULTS-CORPUS", "SL-1118-SCHED-W10"]},
    ]
    (DATA / "flags.json").write_text(json.dumps({"flags": flags}, indent=2) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ site -------

STYLE = """
:root{--bg:#f6f7f9;--fg:#1c2430;--muted:#5a6779;--line:#d9dee6;--panel:#fff;--ok:#1a7f37;--warn:#9a6700;--bad:#b42318;--accent:#12459e}
*{box-sizing:border-box}html{font-size:16px}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent);text-decoration:none;overflow-wrap:anywhere}
p a,li a{text-decoration:underline}
header.top{background:var(--panel);border-bottom:1px solid var(--line);padding:10px 20px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
header.top .brand{display:flex;flex-direction:column;font-size:14px;color:var(--muted)}header.top .brand strong{font-size:16px;color:var(--fg)}
nav[aria-label="Desk pages"]{display:flex;flex-wrap:wrap;gap:4px;margin-left:auto}nav[aria-label="Desk pages"] a{padding:5px 10px;border-radius:6px;font-size:13px;color:var(--muted)}nav[aria-label="Desk pages"] a[aria-current="page"]{background:var(--accent);color:#fff}
main{max-width:1200px;margin:0 auto;padding:24px 20px 60px}
.eyebrow{color:var(--muted);font-size:12px;letter-spacing:.08em;text-transform:uppercase;margin:0 0 4px}
h1{font-size:26px;margin:0 0 8px}h2{font-size:19px;margin:28px 0 8px}h3{font-size:16px;margin:20px 0 6px}
.lead{max-width:70ch}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:18px 0}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px;display:flex;flex-direction:column}
.kpi-value{font-size:24px;font-weight:700}.kpi-label{color:var(--muted);font-size:13px}.kpi .sub{color:var(--muted);font-size:12px;margin-top:2px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin:14px 0}
.table-wrap{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:10px 0 6px}
table{border-collapse:collapse;width:100%;font-size:13.5px}
caption{text-align:left;padding:10px 14px;font-weight:600;color:var(--muted);border-bottom:1px solid var(--line)}
th{position:sticky;top:0;background:#eef1f5;text-align:left;padding:8px 10px;border-bottom:2px solid var(--line);white-space:nowrap}
td{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tbody tr:hover{background:#f2f6ff}
td.blank{background:#fbf6e9;min-width:26px}
td a{display:inline-block;font-size:12.5px;min-height:1.7rem;line-height:1.7rem;margin-right:.45rem}
.badge{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:2px 10px;font-size:12px;font-weight:600;white-space:nowrap}
.badge-ok{background:#e3f4e8;color:#14532d}.badge-warn{background:#fff4e0;color:#8a4b00}.badge-bad{background:#fbe6e6;color:#7f1d1d}
.note{color:var(--muted);font-size:12.5px;max-width:100ch}
footer{max-width:1200px;margin:0 auto;padding:0 20px 40px;color:var(--muted);font-size:12.5px}
"""

PAGES = [
    ("index.html", "Week 10 completion & weekly diff", "Overview"),
    ("week10-complete.html", "The 150th final", "Week 10 complete"),
    ("gamebook-lac-bal.html", "14th Game Book", "LAC@BAL Game Book"),
    ("weekly-diff.html", "What changed", "Weekly diff"),
    ("rules-2026.html", "2026 rules", "2026 kickoff rules"),
    ("verification.html", "Verification", "Verification"),
    ("flagged.html", "Flagged for review", "Flagged"),
    ("sources.html", "Sources", "Sources"),
]


def esc(v) -> str:
    import html
    return html.escape(str(v), quote=True)


def link(url: str, text: str | None = None) -> str:
    t = esc(text or url)
    if url.startswith("http"):
        return f'<a href="{esc(url)}" rel="noopener noreferrer" target="_blank">{t}</a>'
    return f'<a href="{esc(url)}">{t}</a>'


def row(cells: list[str], sids: list[str]) -> str:
    return f'<tr data-source-ids="{" ".join(sids)}">' + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def table(caption: str, headers: list[str], rows_html: list[str], note: str | None = None) -> str:
    head = "".join(f'<th scope="col">{h}</th>' for h in headers)
    note_html = f'<p class="note">{esc(note)}</p>' if note else ""
    return (f'<div class="table-wrap"><table><caption>{esc(caption)}</caption>'
            f'<thead><tr>{head}</tr></thead><tbody>{"".join(rows_html)}</tbody></table></div>{note_html}')


def kpi(value: str, label: str, sub: str = "") -> str:
    sub_html = f'<span class="sub">{esc(sub)}</span>' if sub else ""
    return (f'<div class="kpi"><span class="kpi-value">{esc(value)}</span>'
            f'<span class="kpi-label">{esc(label)}</span>{sub_html}</div>')


def shell(name: str, body: str) -> str:
    title = dict((p[0], p[2]) for p in PAGES)[name]
    nav = "".join(
        '<a href="' + p[0] + ('" aria-current="page"' if p[0] == name else '"') + ">" + esc(p[2]) + "</a>"
        for p in PAGES)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · OWN7 NFL slate desk</title><link rel="stylesheet" href="style.css"></head>
<body><header class="top"><div class="brand"><strong>OWN7 · NFL slate desk</strong><span>Week 10 completion, weekly diff, 2026 rules — session arena/03dcea07-own7</span></div>
<nav aria-label="Desk pages">{nav}</nav></header>
<main>{body}</main>
<footer>Every table row names its registered official source and links it. Blanks stay blank.
Research only — no price, stake, wager, reward or betting recommendation is produced here.</footer>
</body></html>
'''


def build_site(fresh, diffs, gb, rules, checks, byes, finals14) -> list[str]:
    out = []
    src_link = lambda sid: link(SRC[sid], sid)

    # ---- index
    checks_rows = [row([esc(c["id"]), badge_html(c["result"]), esc(c["detail"]), src_link(c["source"])], [c["source"]]) for c in checks]
    body = f'''
<p class="eyebrow">OWN7 · NFL slate desk — session arena/03dcea07-own7</p>
<h1>Week 10 completion, weekly diff, 2026 rules</h1>
<p class="lead">This desk closes the last open Week 10 item and turns dated official reads into
a rendered "what changed" view. Every value traces to a verbatim transcript of the official page
or PDF it was read from (2026-11-18) or to a committed repository artefact, and every delta is
re-derived arithmetically before publication.</p>
<div class="kpis">
{kpi("14/14", "Week 10 Game Books captured", "13 by the Game Book desk + this desk's LAC@BAL")}
{kpi("150", "official finals for 2026", "149 frozen in the corpus + the now-final Monday game")}
{kpi("32", "standings rows re-derived", "frozen + Week 10 finals = fresh page, 0 mismatches")}
{kpi(str(len(diffs["frozen_to_1118"])), "weekly-diff rows published", "what changed between dated reads")}
{kpi(str(len(rules)), "2026 rule changes quoted", "official rulebook table, verbatim")}
</div>
<h2>Verification checks (all must pass; a failure aborts the build)</h2>
{table("Checks run on every build", ["Check", "Result", "What was verified", "Source"], checks_rows)}
<div class="panel"><strong>Scope note.</strong> Paper research only. No wager, stake, bankroll,
price or monetary reward is produced anywhere on this desk. Nothing here is a betting
recommendation.</div>
'''
    out.append(("index.html", shell("index.html", body)))

    # ---- week10-complete
    fin_rows = [row([esc(f"W10-{i+1:02d}"), esc(f_["away"]),
                     esc(f_["home"]), esc(f_["as"]), esc(f_["hs"]), esc(f_["day"] + ", " + f_["date"]),
                     link(f_["url"], "official game page ↗") + " " + link(SCHED_URL, "week slate ↗")],
                    ["SL-1118-SCHED-W10"])
               for i, f_ in enumerate(finals14)]
    body = f'''
<p class="eyebrow">Official results feed</p>
<h1>The 150th final: Chargers 23, Ravens 20</h1>
<p class="lead">The Week 10 Monday game was the one fixture the frozen results corpus holds as
scheduled-not-final. The official schedule page read 2026-11-18 now prints it Final. The frozen
corpus is owned by another session and is not edited; this desk records the completion read-only,
so the official feed stands at 150 finals across the two desks' files.</p>
{table("Week 10 — all 14 games Final (official schedule page, read 2026-11-18)",
       ["Game", "Away", "Home", "Away pts", "Home pts", "Date", "Source"], fin_rows,
       "The Game Book desk's frozen corpus (nfl-results/data/games-2026-w1-10.csv) holds the 13 earlier finals; V9 checks the join and V2 re-derives the standings from both together.")}
<div class="panel"><strong>Why this matters for origination.</strong> A verified results feed is the prerequisite
the brief names so backtests can be computed at all. With Week 10 fully final, the corpus + this
desk's read cover 150 of the 2026 regular-season games to date, and the standings arithmetic
closes to the fresh official page with zero mismatches (checks V2 and V9).</div>
'''
    out.append(("week10-complete.html", shell("week10-complete.html", body)))

    # ---- gamebook-lac-bal
    gb_rows_repo = read_repo_csv("nfl-gamebook-5213243e/data/fixtures-venue.csv")
    venue_rows = []
    for r in gb_rows_repo:
        venue_rows.append(row([
            esc(r["game_id"]), esc(r["away"]) + " @ " + esc(r["home"]), esc(r["stadium"]),
            esc(r["roof_and_surface"]), esc(r["game_weather"]), esc(r["paid_attendance"]),
            link(r["source_url"], "official Game Book PDF ↗"),
            link(SRC["SL-REPO-GB-FIXTURES"], "committed capture")],
            ["SL-REPO-GB-FIXTURES"]))
    venue_rows.append(row([
        "W10-14", "LAC @ BAL", esc(gb["stadium"]), esc(gb["roof_surface"]), esc(gb["game_weather"]),
        esc(gb["paid_attendance"]), link(GB_PDF_URL, "official Game Book PDF ↗"),
        link(GB_GC_URL, "official Game Centre ↗")],
        ["SL-1118-GAMEBOOK-PDF"]))
    lineup_rows = [row([esc(x["club"]), esc(x["unit"]), esc(x["position"]), esc(x["jersey"]),
                        esc(x["player"]), link(GB_PDF_URL, "Game Book ↗")],
                       ["SL-1118-GAMEBOOK-PDF"]) for x in gb["lineups"]]
    inact_rows = [row([esc(x["club"]), esc(x["position"]), esc(x["jersey"]), esc(x["player"]),
                       link(GB_PDF_URL, "Game Book ↗")],
                      ["SL-1118-GAMEBOOK-PDF"]) for x in gb["inactives"]]
    body = f'''
<p class="eyebrow">Official Game Book</p>
<h1>The 14th Game Book completes Week 10's venue and lineup capture</h1>
<p class="lead">On 2026-11-17 the Game Book desk captured 13 of 14 Week 10 Game Books; the 14th
(LAC at BAL) had no Game Book then because the game had not been played. The official Game Book
PDF now publishes it, read 2026-11-18 and retained verbatim in this desk's evidence folder. Week
10's venue, roof/surface, weather, attendance, actual-starters and Not-Active capture is complete
at 14/14.</p>
<div class="kpis">
{kpi(esc(gb["stadium"]), "Stadium (Game Book)", esc(gb["city_state"]))}
{kpi(esc(gb["roof_surface"]), "Roof &amp; surface (Game Book)", "")}
{kpi(esc(gb["temp_f"]) + "°F", "Kickoff temperature", "humidity " + esc(gb["humidity_pct"]) + "% · wind " + esc(gb["wind"]))}
{kpi(esc(gb["paid_attendance"]), "Paid attendance", "")}
{kpi(esc(gb["start_time"]), "Kickoff (Game Book start time)", "")}
</div>
<h2>Week 10 venue &amp; environment — 14/14</h2>
{table("All 14 Week 10 fixtures (rows 1-13 from the committed Game Book desk capture, cited read-only; row 14 from this desk's Game Book read)",
       ["Game", "Fixture", "Stadium", "Roof &amp; surface", "Weather", "Attendance", "Official source", "Capture"], venue_rows,
       "The venue row for W10-14 is emitted in the Game Book desk's own CSV schema (data/gamebook-w10-14-lac-bal.csv) so it joins 1:1 on game_id without editing that desk's files (flag SL06).")}
<h2>Actual starters (official lineups, 44 rows)</h2>
{table("Starting lineups as printed by the official Game Book", ["Club", "Unit", "Position", "Jersey", "Player", "Source"], lineup_rows,
       "Actual starters are an official Game Book fact. Depth rank and snap shares are never inferred here — the brief's DR-25 constraint.")}
<h2>Not Active (official, 12 rows)</h2>
{table("Players printed under 'Not Active' by the official Game Book", ["Club", "Position", "Jersey", "Player", "Source"], inact_rows,
       "LAC's list includes WR 15 L.McConkey; BAL's includes emergency QB 18 K.Slovis (printed '3QB'). The reliability of report designations vs these lists is scored by the Game Book desk's designation-reliability page.")}
<h2>Referee</h2>
<div class="panel">{esc(gb["referee"])} — officiating crew as printed by the Game Book.</div>
'''
    out.append(("gamebook-lac-bal.html", shell("gamebook-lac-bal.html", body)))

    # ---- weekly-diff
    def diff_table(rows: list[dict], caption: str, base_label: str) -> str:
        rh = []
        for r in rows:
            rh.append(row([
                esc(r["team"]), esc(r["code"]),
                esc(f"{r['w0']}-{r['l0']}-{r['t0']}"),
                esc(f"{r['dw']:+d}"), esc(f"{r['dl']:+d}"), esc(f"{r['dt']:+d}"),
                esc(f"{r['dpf']:+d}"), esc(f"{r['dpa']:+d}"), esc(f"{r['dnet']:+d}"),
                esc((r["streak0"] or "—") + " → " + r["streak1"]),
                esc(r["week10"] or "no game"),
                link(STANDINGS_URL, "standings ↗") + " " + link(SCHED_URL, "schedule ↗"),
            ], ["SL-1118-STANDINGS", "SL-1118-SCHED-W10", "SL-REPO-FROZEN-STANDINGS"]))
        return table(caption,
                     ["Team", "Code", f"Record ({base_label})", "dW", "dL", "dT", "dPF", "dPA",
                      "dNet", "Streak", "Week 10", "Sources"], rh,
                     "Deltas are computed between two dated official snapshots and re-derived from the finals that sit between them (checks V2/V3); no value is inferred.")

    reads_rows = [
        row(["2026-11-12 (frozen pre-Week-10)", "32", "pre-kickoff origination input",
             link(SRC["SL-REPO-FROZEN-STANDINGS"], "committed CSV ↗")],
            ["SL-REPO-FROZEN-STANDINGS"]),
        row(["2026-11-17 (pre-Monday, session arena/e7efbde7-own7)", "32", "13 of 14 Week 10 games played",
             link(SRC["SL-REPO-NOV17-STANDINGS"], "committed CSV ↗")],
            ["SL-REPO-NOV17-STANDINGS"]),
        row(["2026-11-18 (this desk)", "32", "all 14 Week 10 games final",
             link(STANDINGS_URL, "nfl.com/standings ↗")],
            ["SL-1118-STANDINGS"]),
    ]
    avail_rows = [
        row(["2026-11-13", "pre-kickoff Week 10 report capture (availability desk)", "20 canonical rows",
             link("https://www.nfl.com/injuries/", "nfl.com/injuries ↗")],
            ["SL-1118-INJ-PAGE"]),
        row(["2026-11-17", "full re-capture by session arena/e7efbde7-own7", "347 rows, 28 team tables",
             link(SRC["SL-1118-INJ-PAGE"], "nfl.com/injuries ↗")],
            ["SL-1118-INJ-PAGE"]),
        row(["2026-11-18", "spot-check read (this desk)", "first 3 tables, 20 rows — all cells equal; REG11 URL still serves Week 10",
             link(SRC["SL-1118-INJ-REG11"], "REG11 URL ↗") + " " + link(SRC["SL-1118-INJ-PAGE"], "injuries page ↗")],
            ["SL-1118-INJ-REG11", "SL-1118-INJ-PAGE"]),
    ]
    body = f'''
<p class="eyebrow">Requirement DR-61</p>
<h1>What changed — the weekly diff, not a static snapshot</h1>
<p class="lead">The brief asks for a weekly "what changed" diff instead of a static snapshot.
Three dated official standings reads and three dated availability reads now exist, so the diffs
below are computed between same-scope official captures only, and every nonzero delta is
re-derived from the finals that sit between the reads before publication.</p>
<h2>Dated reads</h2>
{table("Standings reads", ["Read", "Clubs", "State", "Source"], reads_rows)}
{table("Injury-report reads (delta series)", ["Date", "Capture", "In-scope rows", "Source"], avail_rows, "The 2026-11-18 read is a spot check (flag SL03); the Week 11 report did not exist yet at read time (flag SL02).")}
<h2>2026-11-12 (frozen) → 2026-11-18: the full Week 10 diff</h2>
{diff_table(diffs["frozen_to_1118"], "Per-club change across Week 10 (every club played once or was on bye)", "pre-W10")}
<h2>2026-11-17 → 2026-11-18: only the Monday game</h2>
{diff_table(diffs["nov17_to_1118"], "Per-club change since the previous day's read — exactly BAL and LAC moved (check V3)", "11-17")}
<div class="panel"><strong>Rating change note.</strong> The brief's diff spec also names rank and
rating change. No model rating for these clubs is published by this desk (rating change needs a
model whose inputs are versioned — the origination desks own that), so those two columns are
honestly absent here rather than filled.</div>
'''
    out.append(("weekly-diff.html", shell("weekly-diff.html", body)))

    # ---- rules-2026
    rule_rows = [row([esc(r["article"]), esc(r["description"]), link(SRC["SL-1118-OPS-RULEBOOK"], "official rulebook ↗")],
                     ["SL-1118-OPS-RULEBOOK"]) for r in rules]
    body = f'''
<p class="eyebrow">Requirement DR-68</p>
<h1>2026 kickoff &amp; declared onside-kick regime — official text</h1>
<p class="lead">The brief asks for a 2026 kickoff and declared onside-kick regime priors filter,
built from the officially published rules. The league's own rulebook page publishes the season's
rule changes; the table below is that page's content quoted verbatim (read 2026-11-18). This page
publishes the official text the filter must be built from; the filter itself is not implemented
here.</p>
{table("2026 Rule Changes (official operations.nfl.com table)", ["Rule-Section-Article", "Description (verbatim)", "Source"], rule_rows)}
<div class="panel"><strong>Origination implication (analysis, not a bet).</strong> Under Rule
6-1-6 as published, an onside kick is a declared play in 2026 — it cannot be a surprise — so a
totalling or win-probability model can treat onside declarations as announced events rather than
unannounced uncertainty, and Rule 6-1-5 changes the touchback spot after a kickoff from the 50,
which moves the return-value prior the totals model must assume. The priors filter must encode
these two published facts for 2026 games.</div>
<p class="note">Flag SL01 records a secondary-source disagreement about whether the 2026 rule
retains a trailing-team restriction; the official page's wording above is the authoritative text
this desk publishes.</p>
'''
    out.append(("rules-2026.html", shell("rules-2026.html", body)))

    # ---- verification
    ver_rows = [row([esc(c["id"]), badge_html(c["result"]), esc(c["detail"]), src_link(c["source"])], [c["source"]]) for c in checks]
    ev_sources = {
        "standings": ["SL-1118-STANDINGS"],
        "week10-schedule": ["SL-1118-SCHED-W10"],
        "gamebook-lac-bal": ["SL-1118-GAMEBOOK-PDF", "SL-1118-GAMECENTER"],
        "injuries": ["SL-1118-INJ-PAGE", "SL-1118-INJ-REG11"],
        "rules": ["SL-1118-OPS-RULEBOOK"],
    }
    ev_rows = []
    for f in sorted(EVID.glob("*.md")):
        sids = next((v for k, v in ev_sources.items() if f.name.startswith(k)), ["SL-1118-STANDINGS"])
        ev_rows.append(row([esc(f.name), esc(sha256_of(f)[:16] + "…"), esc(sha256_of(f)),
                            link("evidence/" + f.name, "committed transcript ↗") + " "
                            + " ".join(src_link(s) for s in sids)],
                           sids))
    body = f'''
<p class="eyebrow">How this desk knows what it publishes</p>
<h1>Verification</h1>
<p class="lead">Nine checks run on every build and in CI; a single failure aborts the build.
Deltas are re-derived from committed finals before any diff is published.</p>
{table("Checks", ["Check", "Result", "Detail", "Primary source"], ver_rows)}
<h2>Evidence register (verbatim transcripts, SHA-256)</h2>
{table("Committed evidence files", ["File", "SHA-256 (first 16)", "SHA-256 (full)", "Link"], ev_rows,
       "Each transcript records the URL, tool and read time. The standings evidence cites the rendered rows verbatim; the Game Book evidence quotes the PDF's summary, lineups, substitutions and Not Active sections verbatim.")}
'''
    out.append(("verification.html", shell("verification.html", body)))

    # ---- flagged
    flags = json.loads((DATA / "flags.json").read_text(encoding="utf-8"))["flags"]
    flag_rows = [row([esc(f["id"]), esc(f["title"]), esc(f["detail"]),
                      " ".join(link(SRC[sid], sid) for sid in f["source_ids"])],
                     f["source_ids"]) for f in flags]
    body = f'''
<p class="eyebrow">Non-blocking irregularities</p>
<h1>Flagged for review</h1>
<p class="lead">These items do not block any other task. They are published here with their
official sources so the owner can review and request changes.</p>
{table("Flag register", ["ID", "Title", "Detail", "Sources"], flag_rows)}
'''
    out.append(("flagged.html", shell("flagged.html", body)))

    # ---- sources
    reg = json.loads((REPO / "research" / "sources.json").read_text(encoding="utf-8"))
    reg_by_id = {r["id"]: r for r in reg}
    src_rows = []
    for sid, url in SRC.items():
        r = reg_by_id.get(sid, {})
        src_rows.append(row([esc(sid), esc(r.get("publisher", "")), esc(r.get("title", "")),
                             esc(r.get("scope", "")[:120]), link(url, "official source ↗")], [sid]))
    body = f'''
<p class="eyebrow">Provenance</p>
<h1>Sources</h1>
<p class="lead">Every id below is registered in research/sources.json with its access boundary,
and every table row on this desk cites at least one of them.</p>
{table("Registered sources used by this desk", ["ID", "Publisher", "Title", "Scope", "Link"], src_rows)}
'''
    out.append(("sources.html", shell("sources.html", body)))

    return out


def badge_html(result: str) -> str:
    cls = "ok" if result == "pass" else "bad"
    return f'<span class="badge badge-{cls}">{esc(result)}</span>'


# ------------------------------------------------------------------ main -------

def main() -> None:
    check_only = "--check" in sys.argv
    DATA.mkdir(exist_ok=True)
    SITE.mkdir(exist_ok=True)

    fresh = parse_standings("standings-2026-11-18.md")
    finals14 = parse_week10_schedule()
    byes = parse_byes()
    gb = parse_gamebook()
    rules = parse_rules()
    frozen = load_frozen()
    name_map = load_name_map()
    nov17 = load_nov17(name_map)
    divisions = load_divisions(name_map)
    corpus_w10_finals, corpus_sched = load_corpus_w10()

    checks, diffs = run_checks(fresh, frozen, nov17, divisions, finals14,
                               corpus_w10_finals, corpus_sched, gb, byes, rules)
    for c in checks:
        if c["result"] != "pass":
            die(f"check {c['id']} failed: {c['detail']}")

    build_data(fresh, diffs, gb, rules, checks)
    pages = build_site(fresh, diffs, gb, rules, checks, byes, finals14)

    manifest_pages = [name for name, _ in pages] + ["style.css"]
    (SITE / "manifest.json").write_text(json.dumps({
        "desk": "nfl-slate-03dcea07", "session": "arena/03dcea07-own7",
        "pages": manifest_pages}, indent=2) + "\n", encoding="utf-8")

    stale = []
    for name, html_text in pages:
        p = SITE / name
        if check_only:
            if not p.exists() or p.read_text(encoding="utf-8") != html_text:
                stale.append(name)
        else:
            p.write_text(html_text, encoding="utf-8")
    css = SITE / "style.css"
    if check_only:
        if not css.exists() or css.read_text(encoding="utf-8") != STYLE:
            stale.append("style.css")
        if stale:
            die(f"site does not reproduce byte-identically: {', '.join(stale)}")
        print("OK: nfl-slate-03dcea07 reproduces byte-identically (8 pages, manifest, style).")
    else:
        css.write_text(STYLE, encoding="utf-8")
        print(f"OK: built {len(pages)} pages + style + manifest; 9 checks passed; desk nfl-slate-03dcea07.")


if __name__ == "__main__":
    main()
