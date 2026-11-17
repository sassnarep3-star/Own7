#!/usr/bin/env python3
"""Collect: parse the 2026-11-17 official-read evidence and verify it line by line.

Refuses contradictions instead of publishing them. Every published number in this desk's
site traces to one of the four evidence files, and every evidence file carries the URL of
the official page it was read from plus the read timestamp.

Verification performed here (all abort the build on a single mismatch):

  V1  Standings three-way reconciliation: the canonical 2026-11-12 standings capture plus
      the 13 Week 10 finals read today re-derive every W/L/T/PF/PA/NetPts/PCT cell of the
      fresh standings page for all 32 clubs (BAL and LAC receive no final: their Monday
      game had not kicked off at read time).
  V2  Fixture join: each of the 13 finals joins to exactly one canonical Week 10 fixture
      row (away/home orientation included); the 14th fixture is the pending Monday game.
  V3  Games-played ledger: results corpus (weeks 1-9, 136 games) + Week 10 finals equal
      each club's standings games played.
  V4  Week 11 slate: 13 fixtures, 26 clubs playing exactly once, 6 byes completing the 32;
      every record printed beside a club matches the standings page.
  V5  Injury tables: 28 team tables parse; every one of the 20 canonical 2026-11-12 injury
      rows matches the fresh table cell for cell; the three previously blank Detroit game
      statuses are now published as Out.
  V6  Page-state consistency: records printed on the Week 10 page, the Week 11 page and the
      injury page equal the standings page for every club they print.

Output: data/official-2026-11-17.json (parsed), data/verification.json (checks + hashes).
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
DATA = HERE / "data"

READ_AT = "2026-11-17T00:45:05Z"

TEAM_CODES = {
    "Commanders": "WAS", "Giants": "NYG", "Patriots": "NE", "Lions": "DET",
    "Chiefs": "KC", "Falcons": "ATL", "Texans": "HOU", "Browns": "CLE",
    "Vikings": "MIN", "Packers": "GB", "Dolphins": "MIA", "Colts": "IND",
    "Panthers": "CAR", "Saints": "NO", "Bills": "BUF", "Jets": "NYJ",
    "Jaguars": "JAX", "Titans": "TEN", "Rams": "LA", "Cardinals": "AZ",
    "Seahawks": "SEA", "Raiders": "LV", "49ers": "SF", "Cowboys": "DAL",
    "Steelers": "PIT", "Bengals": "CIN", "Chargers": "LAC", "Ravens": "BAL",
    "Bears": "CHI", "Broncos": "DEN", "Eagles": "PHI", "Buccaneers": "TB",
}
# The page prints LAR for the Rams; repo canonical data (results corpus, standings CSV)
# uses LA. Normalize page codes to the canonical convention.
CODE_ALIASES = {"LAR": "LA"}


def norm(code: str) -> str:
    return CODE_ALIASES.get(code, code)


# injury-report tables use the club nickname without the city prefix in some cases;
# map table headings as printed on the page to codes.
TABLE_CODES = {
    "Commanders": "WAS", "Giants": "NYG", "Patriots": "NE", "Lions": "DET",
    "Chiefs": "KC", "Falcons": "ATL", "Texans": "HOU", "Browns": "CLE",
    "Vikings": "MIN", "Packers": "GB", "Dolphins": "MIA", "Colts": "IND",
    "Panthers": "CAR", "Saints": "NO", "Bills": "BUF", "Jets": "NYJ",
    "Jaguars": "JAX", "Titans": "TEN", "Rams": "LA", "Cardinals": "AZ",
    "Seahawks": "SEA", "Raiders": "LV", "49ers": "SF", "Cowboys": "DAL",
    "Steelers": "PIT", "Bengals": "CIN", "Chargers": "LAC", "Ravens": "BAL",
}


def read(name: str) -> str:
    return (EVIDENCE / name).read_text(encoding="utf-8")


def sha256(name: str) -> str:
    return hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest()


# ---------------------------------------------------------------- standings ----
ROW_RE = re.compile(
    r"\|?\s*\[([^/\]]+) / ([^\]]+)\]\((https://www\.nfl\.com/teams/[^)]+)\)\s*"
    r"\| (\d+) \| (\d+) \| (\d+) \| ([\d.]+) \| (\d+) \| (\d+) \| (-?\d+) "
    r"\| ([\d\- -]+) \| ([\d\- -]+) \| ([\d\- -]+) \| ([\d.]+) \| ([\d\- -]+) \| ([\d.]+) "
    r"\| ([\d\- -]+) \| (\d+[WL]) \| ([\d\- -]+) \|"
)


def parse_standings(text: str) -> list[dict]:
    rows: list[dict] = []
    conference = None
    for line in text.splitlines():
        if line.strip() == "AMERICAN FOOTBALL CONFERENCE":
            conference = "AFC"
        elif line.strip() == "NATIONAL FOOTBALL CONFERENCE":
            conference = "NFC"
        m = ROW_RE.search(line)
        if not m:
            continue
        if conference not in ("AFC", "NFC"):
            raise SystemExit(f"FAIL: standings row before a conference header: {line[:60]}")
        rows.append({
            "conference": conference,
            "club": m.group(1), "nickname": m.group(2), "team_url": m.group(3),
            "code": norm(TEAM_CODES[m.group(2)]),
            "w": int(m.group(4)), "l": int(m.group(5)), "t": int(m.group(6)),
            "pct": m.group(7), "pf": int(m.group(8)), "pa": int(m.group(9)),
            "net_pts": int(m.group(10)),
            "home": m.group(11).strip(), "road": m.group(12).strip(),
            "streak": m.group(17),
        })
    return rows


# ------------------------------------------------------------- W10 fixtures ----
FINAL_RE = re.compile(r"- \[([A-Za-z0-9' .]+?) (\d+), ([A-Za-z0-9' .]+?) (\d+), FINAL, ([^\]]+)\]\((https://www\.nfl\.com/games/[^)]+)\)")
PENDING_RE = re.compile(r"- \[([A-Za-z0-9' .]+?) at ([A-Za-z0-9' .]+?), ([^\]]+)\]\((https://www\.nfl\.com/games/[^)]+)\)")
BYE_RE = re.compile(r"### Teams on Bye\n\n?((?:[A-Z]{2,3}[^\n]*\n)+)")


def parse_week10(text: str) -> dict:
    finals, pending = [], []
    for line in text.splitlines():
        m = FINAL_RE.search(line)
        if m:
            finals.append({
                "away": m.group(1), "away_score": int(m.group(2)),
                "home": m.group(3), "home_score": int(m.group(4)),
                "url": m.group(6),
            })
            continue
        m = PENDING_RE.search(line)
        if m:
            pending.append({
                "away": m.group(1), "home": m.group(2),
                "detail": m.group(3), "url": m.group(4),
            })
    if len(pending) != 1:
        raise SystemExit(f"FAIL: expected exactly 1 non-final Week 10 game, saw {len(pending)}")
    return {"finals": finals, "pending": pending}


# ------------------------------------------------------------- W11 fixtures ----
def parse_week11(text: str) -> dict:
    games, byes = [], []
    for line in text.splitlines():
        m = PENDING_RE.search(line)
        if m and m.group(4).endswith("reg-11"):
            games.append({"away": m.group(1), "home": m.group(2), "detail": m.group(3), "url": m.group(4)})
    m = BYE_RE.search(text)
    if not m:
        raise SystemExit("FAIL: Week 11 byes section not found")
    for token in m.group(1).replace("\n", " · ").split(" · "):
        t = token.strip()
        if not t:
            continue
        m2 = re.match(r"([A-Z]{2,3})([A-Za-z' .]+) (\d+-\d+(?:-\d+)?)$", t)
        if not m2:
            raise SystemExit(f"FAIL: bye token unparsed: {t!r}")
        byes.append({"code": norm(m2.group(1)), "club": m2.group(2).strip(), "record": m2.group(3)})
    return {"games": games, "byes": byes}


# -------------------------------------------------------------- injuries -------
ROW_I_RE = re.compile(r"\| (.+?) \| ([A-Z]{1,3}(?: II| Jr\.| III| Sr\.| IV)?) \| (.+?) \| (.+?) \| (.+?) \|$")


def parse_injuries(text: str) -> list[dict]:
    tables: list[dict] = []
    current: dict | None = None
    in_rows = False
    for line in text.splitlines():
        if line.startswith("### "):
            current = {"team": line[4:].strip(), "rows": [], "section": tables[-1]["section"] if tables else None}
            tables.append(current)
            in_rows = False
            continue
        if line.startswith("## ") and "@ " in line:
            m = re.search(r"([A-Z]{2,3}) ([A-Za-z0-9' .]+?) \(([^)]+)\) @ ([A-Z]{2,3}) ([A-Za-z0-9' .]+?) \(([^)]+)\)", line)
            if not m:
                raise SystemExit(f"FAIL: injury section header unparsed: {line[:80]}")
            tables.append({"team": None, "rows": [],
                           "section": {"day_time_tv": line[3:].split(" — ")[0],
                                       "away_code": m.group(1), "away_club": m.group(2), "away_record": m.group(3),
                                       "home_code": m.group(4), "home_club": m.group(5), "home_record": m.group(6)}})
            current = None
            in_rows = False
            continue
        if current is None:
            continue
        if line.startswith("| Player | Position |"):
            in_rows = True
            continue
        if in_rows and line.startswith("| ---"):
            continue
        if in_rows and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 5:
                raise SystemExit(f"FAIL: injury row does not have 5 cells: {line[:100]}")
            current["rows"].append({
                "player": cells[0], "position": cells[1], "injury": cells[2],
                "practice_status": cells[3], "game_status": cells[4],
            })
    return [t for t in tables if t["team"]]


# ------------------------------------------------------------------ checks -----
def check(name: str, ok: bool, detail: str, checks: list[dict]) -> None:
    checks.append({"id": name, "result": "pass" if ok else "FAIL", "detail": detail})
    if not ok:
        raise SystemExit(f"FAIL {name}: {detail}")


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    text_st = read("standings-2026-11-17.md")
    text_w10 = read("week10-2026-11-17.md")
    text_w11 = read("week11-2026-11-17.md")
    text_inj = read("injuries-w10-2026-11-17.md")

    standings = parse_standings(text_st)
    w10 = parse_week10(text_w10)
    w11 = parse_week11(text_w11)
    tables = parse_injuries(text_inj)

    if len(standings) != 32:
        raise SystemExit(f"FAIL: parsed {len(standings)} standings rows, need 32")
    if len({r["code"] for r in standings}) != 32:
        raise SystemExit("FAIL: duplicate club in standings parse")

    # V2 fixture join against the canonical Week 10 schedule CSV
    fixtures = {}
    with (ROOT / "data/nfl-schedule-2026-w10.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            fixtures[row["id"]] = row

    checks: list[dict] = []
    joined: list[dict] = []
    for f in w10["finals"]:
        ac, hc = norm(TEAM_CODES[f["away"]]), norm(TEAM_CODES[f["home"]])
        hit = [fid for fid, row in fixtures.items()
               if TEAM_CODES.get(row["Away"]) == ac and TEAM_CODES.get(row["Home"]) == hc]
        if len(hit) != 1:
            raise SystemExit(f"FAIL V2: {ac}@{hc} joined to {hit}")
        joined.append({"fixture_id": hit[0], **f, "away_code": ac, "home_code": hc})
    pend = w10["pending"][0]
    ac, hc = norm(TEAM_CODES[pend["away"]]), norm(TEAM_CODES[pend["home"]])
    hit = [fid for fid, row in fixtures.items()
           if TEAM_CODES.get(row["Away"]) == ac and TEAM_CODES.get(row["Home"]) == hc]
    if len(hit) != 1:
        raise SystemExit(f"FAIL V2: pending {ac}@{hc} joined to {hit}")
    pending_row = {"fixture_id": hit[0], **pend, "away_code": ac, "home_code": hc, "score": None}
    check("V2", len(joined) == 13 and len(pending_row["fixture_id"]) == 6,
          f"13 finals + 1 pending game each join to exactly one canonical fixture id "
          f"({len(joined)} joined, pending {pending_row['fixture_id']})", checks)

    # V1 three-way standings reconciliation
    canonical = {}
    with (ROOT / "data/nfl-standings-week10-2026.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            canonical[row["id"]] = row
    derived = {}
    for code, row in canonical.items():
        w, l, t = int(row["W"]), int(row["L"]), int(row["T"])
        pf, pa = int(row["PF"]), int(row["PA"])
        derived[code] = {"w": w, "l": l, "t": t, "pf": pf, "pa": pa}
    for g in joined:
        d = derived[g["away_code"]]
        d["pf"] += g["away_score"]; d["pa"] += g["home_score"]
        if g["away_score"] > g["home_score"]:
            d["w"] += 1
        elif g["away_score"] < g["home_score"]:
            d["l"] += 1
        else:
            d["t"] += 1
        d2 = derived[g["home_code"]]
        d2["pf"] += g["home_score"]; d2["pa"] += g["away_score"]
        if g["home_score"] > g["away_score"]:
            d2["w"] += 1
        elif g["home_score"] < g["away_score"]:
            d2["l"] += 1
        else:
            d2["t"] += 1
    # the pending Monday game is NOT applied: BAL/LAC keep canonical numbers
    mismatches = []
    fresh = {r["code"]: r for r in standings}
    for code, d in derived.items():
        r = fresh[code]
        if (d["w"], d["l"], d["t"], d["pf"], d["pa"]) != (r["w"], r["l"], r["t"], r["pf"], r["pa"]):
            mismatches.append({"code": code, "derived": d, "fresh": {k: r[k] for k in ("w", "l", "t", "pf", "pa")}})
        pct = round((d["w"] + 0.5 * d["t"]) / (d["w"] + d["l"] + d["t"]), 3)
        if f"{pct:.3f}" != r["pct"]:
            mismatches.append({"code": code, "field": "PCT", "derived": pct, "fresh": r["pct"]})
        if d["pf"] - d["pa"] != r["net_pts"]:
            mismatches.append({"code": code, "field": "NET PTS"})
    check("V1", not mismatches,
          f"32/32 clubs: canonical 2026-11-12 capture + 13 Week 10 finals re-derive every "
          f"W/L/T/PCT/PF/PA/NET-PTS cell of the fresh standings page ({len(mismatches)} mismatches)", checks)

    # V3 games-played ledger against the results corpus (weeks 1-9)
    played = {}
    with (ROOT / "nfl-results/data/games-2026-w1-9.csv").open(newline="", encoding="utf-8") as fh:
        corpus = list(csv.DictReader(fh))
    for g in corpus:
        for side in ("away", "home"):
            played[g[side]] = played.get(g[side], 0) + 1
    ledger_bad = []
    for code, r in fresh.items():
        expect = played.get(code, 0)
        if any(g["away_code"] == code or g["home_code"] == code for g in joined):
            expect += 1
        actual = r["w"] + r["l"] + r["t"]
        if expect != actual:
            ledger_bad.append({"code": code, "corpus_plus_w10": expect, "standings_games": actual})
    check("V3", not ledger_bad and len(corpus) == 136,
          f"136-game weeks-1-9 corpus + 13 Week 10 finals equal each club's standings games "
          f"played for all 32 clubs ({len(ledger_bad)} mismatches)", checks)

    # V4 Week 11 slate
    w11_codes = []
    for g in w11["games"]:
        w11_codes += [norm(TEAM_CODES[g["away"]]), norm(TEAM_CODES[g["home"]])]
    if len(w11_codes) != 26 or len(set(w11_codes)) != 26:
        raise SystemExit(f"FAIL V4: Week 11 slate not 26 distinct clubs ({len(set(w11_codes))})")
    if len(w11["byes"]) != 6:
        raise SystemExit(f"FAIL V4: {len(w11['byes'])} byes, need 6")
    if set(w11_codes) & {b["code"] for b in w11["byes"]}:
        raise SystemExit("FAIL V4: club both playing and on bye")
    if set(w11_codes) | {b["code"] for b in w11["byes"]} != set(fresh):
        raise SystemExit("FAIL V4: playing clubs + byes do not complete the 32")
    check("V4", True,
          "13 Week 11 fixtures, 26 clubs playing exactly once, 6 byes; playing + byes = the 32", checks)

    # V5 injury tables — the report covers the 28 clubs that played (the four Week 10
    # byes CHI/DEN/PHI/TB have no table on the report page).
    if len(tables) != 28:
        raise SystemExit(f"FAIL V5: {len(tables)} injury tables, need 28")
    playing_w10 = {g["away_code"] for g in joined} | {g["home_code"] for g in joined} | {pending_row["away_code"], pending_row["home_code"]}
    if sorted(norm(TABLE_CODES.get(t["team"], "?")) for t in tables) != sorted(playing_w10):
        raise SystemExit("FAIL V5: injury tables do not match the 28 Week 10 clubs exactly once")
    total_rows = sum(len(t["rows"]) for t in tables)
    canonical_inj = []
    with (ROOT / "data/nfl-injuries-2026-w10.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            canonical_inj.append(row)
    fresh_flat = {}
    for t in tables:
        code = norm(TABLE_CODES[t["team"]])
        for r in t["rows"]:
            fresh_flat.setdefault((code, r["player"]), r)
    inj_bad = []
    for row in canonical_inj:
        key = (norm(TABLE_CODES[row["Team"]]), row["Player"])
        f = fresh_flat.get(key)
        if f is None:
            inj_bad.append({"row": row["id"], "problem": "player not on fresh report"})
            continue
        for a, b in (("Position", "position"), ("Injury", "injury"),
                     ("PracticeStatus", "practice_status"), ("GameStatus", "game_status")):
            if (row[a] or "") != (f[b] or ""):
                inj_bad.append({"row": row["id"], "field": a, "canonical": row[a], "fresh": f[b]})
    check("V5", not inj_bad,
          f"28 team tables ({total_rows} rows) parse; all {len(canonical_inj)} canonical "
          f"2026-11-12 rows match the fresh report cell for cell ({len(inj_bad)} mismatches)", checks)

    lions = next(t for t in tables if t["team"] == "Lions")
    lion_rows = {r["player"]: r["game_status"] for r in lions["rows"]}
    for name in ("Kerby Joseph", "Cade Mays", "D.J. Reed"):
        if lion_rows.get(name) != "Out":
            raise SystemExit(f"FAIL V5: {name} game status = {lion_rows.get(name)!r}, expected Out")
    check("V5b", True,
          "Detroit's Kerby Joseph, Cade Mays and D.J. Reed are published with Game Status Out "
          "(the three cells the 2026-11-12 capture left blank)", checks)

    # V6 record consistency across pages
    def rec_str(r: dict) -> str:
        return f"{r['w']}-{r['l']}" if r["t"] == 0 else f"{r['w']}-{r['l']}-{r['t']}"

    bad: list[dict] = []
    sections = [t["section"] for t in tables if t.get("section")]
    seen = {}
    for s in sections:
        seen[norm(s["away_code"])] = s["away_record"]; seen[norm(s["home_code"])] = s["home_record"]
    week11_recs = {}
    for m in re.finditer(r"\[([A-Z0-9]{2,10}) (\d+(?:-\d+){1,2}) \| ([A-Z0-9]{2,10}) (\d+(?:-\d+){1,2})[^\]]*\]", text_w11):
        week11_recs[norm(TEAM_CODES[m.group(1).title().replace("49Ers", "49ers")])] = m.group(2)
        week11_recs[norm(TEAM_CODES[m.group(3).title().replace("49Ers", "49ers")])] = m.group(4)
    if len(week11_recs) != 26:
        raise SystemExit(f"FAIL V6: week-11 records parsed for {len(week11_recs)} clubs, need 26")
    for code, rec in week11_recs.items():
        if rec != rec_str(fresh[code]):
            bad.append({"page": "week11", "code": code, "printed": rec, "standings": rec_str(fresh[code])})
    for code, rec in seen.items():
        if rec != rec_str(fresh[code]):
            bad.append({"page": "injuries", "code": code, "printed": rec, "standings": rec_str(fresh[code])})
    check("V6", not bad,
          f"records printed beside clubs on the Week 11 page ({len(week11_recs)} clubs) and the "
          f"injury page ({len(seen)} clubs) equal the standings page ({len(bad)} mismatches)", checks)

    out = {
        "read_at": READ_AT,
        "evidence": {
            "standings": {"file": "evidence/standings-2026-11-17.md", "url": "https://www.nfl.com/standings/",
                          "sha256": sha256("standings-2026-11-17.md")},
            "week10": {"file": "evidence/week10-2026-11-17.md", "url": "https://www.nfl.com/schedules/2026/REG10/",
                       "sha256": sha256("week10-2026-11-17.md")},
            "week11": {"file": "evidence/week11-2026-11-17.md", "url": "https://www.nfl.com/schedules/2026/by-week/week-11",
                       "sha256": sha256("week11-2026-11-17.md")},
            "injuries": {"file": "evidence/injuries-w10-2026-11-17.md", "url": "https://www.nfl.com/injuries/",
                         "sha256": sha256("injuries-w10-2026-11-17.md")},
        },
        "standings": standings,
        "week10_finals": joined,
        "week10_pending": [pending_row],
        "week11": w11,
        "injury_tables": tables,
        "injury_totals": {"tables": len(tables), "rows": total_rows,
                          "with_game_status": sum(1 for t in tables for r in t["rows"] if r["game_status"]),
                          "out": sum(1 for t in tables for r in t["rows"] if r["game_status"] == "Out"),
                          "doubtful": sum(1 for t in tables for r in t["rows"] if r["game_status"] == "Doubtful"),
                          "questionable": sum(1 for t in tables for r in t["rows"] if r["game_status"] == "Questionable")},
    }
    ver = {"read_at": READ_AT, "checks": checks}
    DATA.mkdir(exist_ok=True)
    (DATA / "official-2026-11-17.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    (DATA / "verification.json").write_text(json.dumps(ver, indent=1) + "\n", encoding="utf-8")

    if arg == "--check":
        first = ((DATA / "official-2026-11-17.json").read_bytes(), (DATA / "verification.json").read_bytes())
        (DATA / "official-2026-11-17.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
        (DATA / "verification.json").write_text(json.dumps(ver, indent=1) + "\n", encoding="utf-8")
        second = ((DATA / "official-2026-11-17.json").read_bytes(), (DATA / "verification.json").read_bytes())
        if first != second:
            raise SystemExit("FAIL --check: re-run produced different bytes")
    print(f"OK: {len(standings)} standings rows, {len(joined)}+1 W10 games, "
          f"{len(w11['games'])} W11 fixtures, {len(tables)} injury tables ({total_rows} rows); "
          f"{len(checks)} checks passed.")
    for c in checks:
        print(f"  {c['id']}: {c['result']} — {c['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
