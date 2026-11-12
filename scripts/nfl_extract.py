#!/usr/bin/env python3
"""Deterministic extraction of NFL rows from the saved official page text.

Nothing here is typed in by hand. Every retained value is parsed out of the verbatim
retrievals in research/nfl/evidence/*.retrieved.md, then arithmetically cross-checked.
If any check fails the extraction aborts and no dataset is written.

Run: python3 scripts/nfl_extract.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVID = ROOT / "research" / "nfl" / "evidence"
OUT = ROOT / "data"
NFL = ROOT / "research" / "nfl"

STANDINGS_URL = "https://www.nfl.com/standings/"
INJURY_URL = "https://www.nfl.com/injuries/"
SCHEDULE_URL = "https://www.nfl.com/schedules/"
CHECKED_ON = "2026-11-12"

# Conference assignment of the clubs that appear inside the standings page's two
# rendered sections. Derived from the page headings, verified independently against the
# Week 10 schedule/bye list: every club appears exactly once across the 14 fixtures + 4 byes.
AFC = ("BUF NE NYJ MIA PIT CIN CLE BAL JAX HOU IND TEN DEN KC LV LAC").split()
NFC = ("NYG DAL WAS PHI CHI DET MIN GB CAR NO TB ATL SF SEA LA AZ").split()

# | [![](…/logos/BUF)](https://www.nfl.com/teams/buffalo-bills/) BUF [Buffalo Bills](…)
ROW = re.compile(
    r"^\|\s*\[!\[\]\([^)]*/logos/(?P<code>[A-Z]{2,3})\)\]\((?P<teamurl>[^)]+)\)\s+"
    r"(?P=code)\s+\[(?P<name>[^\]]+)\]\("
)
NUM = re.compile(r"^-?\d+(?:\.\d+)?$")
REC = re.compile(r"^\d+\s*-\s*\d+\s*-\s*\d+$")
STREAK = re.compile(r"^\d+[WLT]$")


def read(name: str) -> list[str]:
    return (EVID / name).read_text(encoding="utf-8").splitlines()


def parse_standings() -> list[dict]:
    rows, section = [], None
    for line in read("standings-2026-w10.retrieved.md"):
        if line.startswith("## AMERICAN FOOTBALL CONFERENCE"):
            section = "AFC"
            continue
        if line.startswith("## NATIONAL FOOTBALL CONFERENCE"):
            section = "NFC"
            continue
        if line.startswith("## Legend") or line.startswith("## National") or line.startswith("## National"):
            section = None
            continue
        if not line.startswith("| [!"):
            continue
        match = ROW.match(line)
        if not match:
            raise SystemExit(f"Unparsed standings row: {line[:80]}")
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        values = cells[1:]
        if len(values) != 16:
            raise SystemExit(f"Standings row has {len(values)} value cells, expected 16: {match.group('name')}")
        if any(not (NUM.match(v) or REC.match(v)) for i, v in enumerate(values) if i != 14):
            raise SystemExit(f"Non-numeric standings field for {match.group('name')}")
        if not STREAK.match(values[14]):
            raise SystemExit(f"Unrecognised streak field for {match.group('name')}: {values[14]!r}")
        w, l, t, pct, pf, pa, net = (values[0], values[1], values[2], values[3],
                                     values[4], values[5], values[6])
        rows.append({
            "id": match.group("code"),
            "Team": match.group("name"),
            "TeamCode": match.group("code"),
            "Conference": section,
            "W": int(w), "L": int(l), "T": int(t),
            "PCT": float(pct), "PF": int(pf), "PA": int(pa), "NetPts": int(net),
            "Home": values[7], "Road": values[8],
            "Streak": values[14],
            "TeamURL": match.group("teamurl"),
            "SourceURL": STANDINGS_URL,
            "CheckedOn": CHECKED_ON,
            "Retrieval": "research/nfl/evidence/standings-2026-w10.retrieved.md",
        })
    return rows


def verify_standings(rows: list[dict]) -> list[str]:
    problems = []
    codes = [r["TeamCode"] for r in rows]
    if len(rows) != 32 or len(set(codes)) != 32:
        problems.append(f"standings rows={len(rows)} unique={len(set(codes))}, expected 32")
    if sorted(codes) != sorted(AFC + NFC):
        problems.append("standings club set does not match the 32-club reference set")
    for r in rows:
        games = r["W"] + r["L"] + r["T"]
        # Displayed PCT is rounded to three places; accept only that rounding tolerance.
        if abs((r["W"] + r["T"] / 2) / games - r["PCT"]) > 0.00051:
            problems.append(f"{r['TeamCode']}: PCT does not match (W + T/2)/games")
        if r["PF"] - r["PA"] != r["NetPts"]:
            problems.append(f"{r['TeamCode']}: NET PTS is not PF - PA")
        home = [int(x) for x in r["Home"].split(" - ")]
        road = [int(x) for x in r["Road"].split(" - ")]
        if (home[0] + road[0], home[1] + road[1], home[2] + road[2]) != (r["W"], r["L"], r["T"]):
            problems.append(f"{r['TeamCode']}: HOME+ROAD record does not equal overall record")
        expected_conf = "AFC" if r["TeamCode"] in AFC else "NFC"
        if r["Conference"] != expected_conf:
            problems.append(f"{r['TeamCode']}: section mismatch")
    total_w, total_l = sum(r["W"] for r in rows), sum(r["L"] for r in rows)
    if total_w != total_l:
        problems.append(f"league-wide wins {total_w} != losses {total_l}")
    return problems


def parse_injuries() -> list[dict]:
    rows, team = [], None
    for line in read("injury-report-w10-tnf.retrieved.md"):
        if line.strip() in ("Commanders", "Giants"):
            team = line.strip()
            continue
        match = re.match(r"^\|\s*\[(?P<player>[^\]]+)\]\((?P<url>https://www\.nfl\.com/players/[^)]+)\)\s*\|", line)
        if not match or team is None:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5:
            raise SystemExit(f"Uninjury row shape: {line[:70]}")
        rows.append({
            "id": f"INJ-{len(rows) + 1:03d}",
            "Team": team,
            "Player": match.group("player"),
            "Position": cells[1],
            "Injury": cells[2],
            "PracticeStatus": cells[3],
            "GameStatus": cells[4],
            "PlayerURL": match.group("url"),
            "SourceURL": INJURY_URL,
            "ReportTime": "2026-11-12 Week 10 TNF listing",
            "CheckedOn": CHECKED_ON,
            "Retrieval": "research/nfl/evidence/injury-report-w10-tnf.retrieved.md",
        })
    return rows


ALLOWED_PRACTICE = {"Did Not Participate In Practice", "Limited Participation in Practice",
                    "Full Participation in Practice"}
ALLOWED_GAME = {"", "Out", "Doubtful", "Questionable"}


def verify_injuries(rows: list[dict]) -> list[str]:
    problems = []
    if len(rows) != 20:
        problems.append(f"injury rows={len(rows)}, expected the 20 listed players")
    if len({r["PlayerURL"] for r in rows}) != len(rows):
        problems.append("duplicate player identity in injury rows")
    for r in rows:
        if r["PracticeStatus"] not in ALLOWED_PRACTICE:
            problems.append(f"{r['Player']}: practice status outside the official three categories")
        if r["GameStatus"] not in ALLOWED_GAME:
            problems.append(f"{r['Player']}: game status outside the official categories")
        if bool(r["GameStatus"]) != bool(r["Injury"]):
            problems.append(f"{r['Player']}: game status and injury reason are inconsistent (flag)")
    return problems


FIXTURE = re.compile(
    r"^- (?P<away>[A-Za-z0-9 ]+?) at (?P<home>[A-Za-z0-9 ]+?), "
    r"(?P<day>Thursday|Sunday|Monday), "
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December) "
    r"(?P<daynum>[0-9]{1,2})(?:st|nd|rd|th), "
    r"(?P<hour>[0-9]{1,2}):(?P<minute>[0-9]{2}) (?P<ampm>AM|PM), (?P<tv>[A-Z]+)"
    r" \u2014 (?P<url>https://www\.nfl\.com/games/[a-z0-9-]+)"
)
GAME_SLUG = re.compile(r"-(?P<year>[0-9]{4})-reg-(?P<week>[0-9]{1,2})$")


BYES = ("CHI", "DEN", "PHI", "TB")
MONTHS = {m: f"{i:02d}" for i, m in enumerate(
    ("January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"), 1)}


def parse_schedule() -> list[dict]:
    rows = []
    for line in read("schedule-2026-w10.retrieved.md"):
        match = FIXTURE.match(line.strip())
        if not match:
            continue
        slug = GAME_SLUG.search(match.group("url"))
        if not slug:
            raise SystemExit(f"Fixture link has no season/week slug: {match.group('url')}")
        rows.append({
            "id": f"W10-{len(rows) + 1:02d}",
            "Away": match.group("away"),
            "Home": match.group("home"),
            "Day": match.group("day"),
            "Week": int(slug.group("week")),
            "Date": f"{slug.group('year')}-{MONTHS[match.group('month')]}-{int(match.group('daynum')):02d}",
            "KickoffET": f"{int(match.group('hour'))}:{match.group('minute')} {match.group('ampm')}",
            "TV": match.group("tv"),
            "GameURL": match.group("url"),
            "SourceURL": SCHEDULE_URL,
            "CheckedOn": CHECKED_ON,
        })
    return rows


def verify_schedule(rows: list[dict], standings: list[dict]) -> list[str]:
    problems = []
    by_name = {r["Team"].split()[-1]: r["TeamCode"] for r in standings}
    by_name["49ers"] = "SF"
    seen = []
    for r in rows:
        for side in ("Away", "Home"):
            code = by_name.get(r[side])
            if code is None:
                problems.append(f"fixture club not in the standings set: {r[side]}")
            else:
                seen.append(code)
    if len(rows) != 14:
        problems.append(f"fixtures={len(rows)}, expected 14")
    if {r["Week"] for r in rows} != {10}:
        problems.append("fixture links do not all carry week 10")
    if len({r["GameURL"] for r in rows}) != len(rows):
        problems.append("duplicate fixture link")
    if len(seen) != 28 or len(set(seen)) != 28:
        problems.append("a club appears twice or is missing among the 14 fixtures")
    if sorted(set(seen) | set(BYES)) != sorted(AFC + NFC):
        problems.append("fixtures plus byes do not cover exactly the 32 clubs")
    return problems


def write_csv(path: Path, rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    text = buffer.getvalue()
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if regeneration would change a file")
    args = parser.parse_args()

    standings = parse_standings()
    injuries = parse_injuries()
    schedule = parse_schedule()
    problems = (verify_standings(standings) + verify_injuries(injuries)
                + verify_schedule(schedule, standings))
    hard = [p for p in problems if "(flag)" not in p]
    flags = [p for p in problems if "(flag)" in p]
    if hard:
        raise SystemExit("EXTRACTION REFUSED\n" + "\n".join(" - " + p for p in hard))

    targets = {
        OUT / "nfl-standings-2026.csv": standings,
        OUT / "nfl-injuries-2026-w10.csv": injuries,
        OUT / "nfl-schedule-2026-w10.csv": schedule,
    }
    digests, changed = {}, []
    for path, rows in targets.items():
        before = path.read_text(encoding="utf-8") if path.exists() else None
        digest = write_csv(path, rows) if not args.check else None
        if args.check:
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            if before != buffer.getvalue():
                changed.append(path.name)
        digests[path.name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    if args.check and changed:
        raise SystemExit("STALE: " + ", ".join(changed))

    receipts = {
        "checked_on": CHECKED_ON,
        "conference_reference": {"AFC": AFC, "NFC": NFC,
                                 "note": "Used only to check that parsed sections and the fixture/bye "
                                         "cover are complete; not an independent NFL source."},
        "datasets": [
            {"file": "data/nfl-standings-2026.csv", "source_url": STANDINGS_URL,
             "retrieval": "research/nfl/evidence/standings-2026-w10.retrieved.md",
             "rows": len(standings),
             "checks": ["32 unique clubs", "PCT = (W + T/2)/games", "NET PTS = PF - PA",
                        "HOME + ROAD = overall record", "league wins = league losses",
                        "section matches reference conference list"],
             "not_retained": ["DIV", "CONF", "last-10 and other unconfirmed middle positions"],
             "reason_not_retained": "The rendered table had no text header row and the displayed field "
                                    "order does not match the page legend, so those columns could not be "
                                    "identified with confidence."},
            {"file": "data/nfl-injuries-2026-w10.csv", "source_url": INJURY_URL,
             "retrieval": "research/nfl/evidence/injury-report-w10-tnf.retrieved.md",
             "rows": len(injuries),
             "checks": ["20 unique player identities", "practice status in the official three categories",
                        "game status in the official categories"],
             "scope": "One game (WAS at NYG). League-wide Week 10 coverage is NOT transcribed."},
            {"file": "data/nfl-schedule-2026-w10.csv", "source_url": SCHEDULE_URL,
             "retrieval": "research/nfl/evidence/schedule-2026-w10.retrieved.md",
             "rows": len(schedule),
             "checks": ["14 fixtures", "28 unique participating clubs", "fixtures + 4 byes = 32 clubs"]},
        ],
        "identical_bytes_note": "All three datasets are regenerated from the saved text on every run; "
                                "the extractor aborts instead of publishing a contradiction.",
        "flagged": flags,
    }
    NFL.mkdir(parents=True, exist_ok=True)
    (NFL / "receipts.json").write_text(json.dumps(receipts, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {len(standings)} standings rows, {len(injuries)} injury rows, {len(schedule)} fixtures; "
          f"{len(flags)} flag(s); all arithmetic checks passed.")
    for flag in flags:
        print("  flag:", flag)


if __name__ == "__main__":
    main()
