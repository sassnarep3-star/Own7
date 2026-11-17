"""Spot-check the availability desk's Week 10 injury rows against the saved official NFL.com text.

Official evidence : nfl-readiness-1467fdf7/evidence/nfl-injuries-week10-2026-official-read-2026-11-17.md
                    (rows read 2026-11-17 from https://www.nfl.com/injuries/ ; SHA-256 recorded in the output)
Compared against  : nfl-availability-28ef/data/injuries-week10-2026.csv

Only clubs whose table is COMPLETE in the saved text are compared. KC is partial and is listed as
not compared. A mismatch is reported, never silently corrected. Standard library only.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
EVIDENCE = HERE / "evidence" / "nfl-injuries-week10-2026-official-read-2026-11-17.md"
DESK_CSV = REPO / "nfl-availability-28ef" / "data" / "injuries-week10-2026.csv"
OUT = HERE / "data" / "injury-spot-check.json"

CLUB_NAMES = {
    "Commanders": "WAS", "Giants": "NYG", "Patriots": "NE", "Lions": "DET", "Chiefs": "KC",
}
COMPLETE_CLUBS = {"WAS", "NYG", "NE", "DET"}
ROW = re.compile(r"^\| (?!Player|---)(.+?) \| (.+?) \| (.*?) \| (.*?) \| (.*?) \|$")


def parse_official(text):
    rows = []
    club = None
    for line in text.splitlines():
        head = line.strip().split(" (")[0]
        if head in CLUB_NAMES and not line.startswith("|"):
            club = CLUB_NAMES[head]
            continue
        if club is None:
            continue
        m = ROW.match(line)
        if m:
            name, pos, injury, practice, game = (x.strip() for x in m.groups())
            rows.append({"club": club, "player": name, "position": pos, "injury": injury,
                         "practice": practice, "game": game})
    return rows


def norm_name(s):
    return re.sub(r"[^a-z]", "", s.lower())


def build_result():
    raw = EVIDENCE.read_bytes()
    text = raw.decode("utf-8")
    official = parse_official(text)
    with DESK_CSV.open(encoding="utf-8", newline="") as fh:
        desk = list(csv.DictReader(fh))
    desk_by = {}
    for r in desk:
        desk_by.setdefault((r["club_abbr"], norm_name(r["player"])), []).append(r)

    compared, mismatches, missing_desk = [], [], []
    for o in official:
        key = (o["club"], norm_name(o["player"]))
        if o["club"] not in COMPLETE_CLUBS:
            continue
        hits = desk_by.get(key, [])
        if not hits:
            missing_desk.append(o)
            continue
        d = hits[0]
        row = {
            "club": o["club"], "player": o["player"],
            "official_injury": o["injury"], "desk_injury": d["injury"],
            "official_practice": o["practice"], "desk_practice": d["practice_status"],
            "official_game": o["game"], "desk_game": d["game_status"],
        }
        fields = []
        if o["injury"] != d["injury"].strip():
            fields.append("injury")
        if o["practice"] != d["practice_status"].strip():
            fields.append("practice")
        if o["game"] != d["game_status"].strip():
            fields.append("game_status")
        row["mismatch_fields"] = fields
        compared.append(row)
        if fields:
            mismatches.append(row)

    desk_complete_clubs = sorted(COMPLETE_CLUBS)
    desk_rows_in_complete = [r for r in desk if r["club_abbr"] in COMPLETE_CLUBS]
    not_in_official = []
    official_keys = {(o["club"], norm_name(o["player"])) for o in official}
    for r in desk_rows_in_complete:
        if (r["club_abbr"], norm_name(r["player"])) not in official_keys:
            not_in_official.append({"club": r["club_abbr"], "player": r["player"]})

    result = {
        "evidence_file": str(EVIDENCE.relative_to(REPO)),
        "evidence_sha256": hashlib.sha256(raw).hexdigest(),
        "evidence_source_url": "https://www.nfl.com/injuries/",
        "evidence_read_on": "2026-11-17",
        "official_rows_parsed": len(official),
        "complete_clubs_compared": desk_complete_clubs,
        "rows_compared": len(compared),
        "rows_with_mismatch": len(mismatches),
        "official_rows_missing_from_desk": missing_desk,
        "desk_rows_in_complete_clubs_not_in_official_text": not_in_official,
        "not_compared": ["KC (table truncated after Patrick Mahomes in the saved text; 6 of 12 desk rows read)"],
        "desk_source": "nfl-availability-28ef/data/injuries-week10-2026.csv",
        "rows": compared,
    }
    return result


def to_text(result):
    return json.dumps(result, indent=2, sort_keys=True) + "\n"


def main(argv):
    result = build_result()
    text_out = to_text(result)
    if "--check" in argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text_out:
            print("injury-spot-check.json is not byte-identical to a fresh rebuild", file=sys.stderr)
            return 1
        print("injury-spot-check.json reproduces byte-identically")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text_out, encoding="utf-8")
    print(f"rows compared {result['rows_compared']}; mismatches {result['rows_with_mismatch']}; official rows missing from desk {len(result['official_rows_missing_from_desk'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
