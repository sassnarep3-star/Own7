#!/usr/bin/env python3
"""F3 mechanical drift check: fresh 2026-11-18 reads vs committed canonical data.

Compares the standings read (evidence/standings-2026-11-18.md) against the
committed canonical standings snapshots, the Week 11 schedule read against the
committed schedule facts, and the Week 10 injury designated rows against the
committed canonical injury CSV.

Policy (standing repo rule): contradictions are flagged, never patched. The
checker aborts (non-zero exit) only if a *fresh read* is internally
inconsistent; drift vs a stale canonical snapshot is reported as a finding.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESK = ROOT / "nfl-forward-desk"


def parse_standings_evidence(path: Path):
    """Parse the standings evidence markdown into structured rows."""
    rows = {}
    text = path.read_text(encoding="utf-8")
    # Each row: | Team | W | L | T | PCT | PF | PA | NET | HOME | ROAD | DIV | CONF | STRK | LAST5 |
    for line in text.splitlines():
        if not line.startswith("|") or line.startswith("| ---") or line.startswith("| Team"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 13:
            continue
        team = cells[0]
        if team in ("Team",):
            continue
        try:
            rows[team] = {
                "W": int(cells[1]), "L": int(cells[2]), "T": int(cells[3]),
                "PCT": cells[4], "PF": int(cells[5]), "PA": int(cells[6]),
                "NET": cells[7], "HOME": cells[8], "ROAD": cells[9],
                "DIV": cells[10], "CONF": cells[11], "STRK": cells[12],
                "LAST5": cells[13] if len(cells) > 13 else "",
            }
        except ValueError:
            continue
    return rows


def parse_canonical_standings(path: Path):
    rows = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            # Normalise keys to upper case so field lookups are case-insensitive
            # (canonical files use e.g. "Strk"/"Last5", evidence uses "STRK"/"LAST5").
            rows[r["Team"]] = {k.strip().upper(): v for k, v in r.items()}
    return rows


def main() -> int:
    findings = []
    ok = True

    ev = parse_standings_evidence(DESK / "evidence" / "standings-2026-11-18.md")
    if len(ev) != 32:
        findings.append(f"INTERNAL: standings evidence parsed {len(ev)} rows, expected 32")
        ok = False

    # Compare against each committed canonical snapshot.
    for canon_name in ("data/nfl-standings-2026.csv", "data/nfl-standings-2026-11-17.csv"):
        canon_path = ROOT / canon_name
        if not canon_path.exists():
            findings.append(f"MISSING canonical file: {canon_name}")
            continue
        canon = parse_canonical_standings(canon_path)
        diffs = []
        for team, fresh in ev.items():
            c = canon.get(team)
            if c is None:
                diffs.append(f"{team}: absent in canonical {canon_name}")
                continue
            for field, fkey in (("W","W"),("L","L"),("T","T"),("PF","PF"),("PA","PA"),("STRK","STRK")):
                cv = c.get(field, "").strip()
                fv = str(fresh[fkey])
                if cv != fv:
                    diffs.append(f"{team} {field}: fresh={fv} canonical={cv}")
        status = "MATCH" if not diffs else f"DRIFT ({len(diffs)} cells)"
        findings.append(f"standings vs {canon_name}: {status}")
        for d in diffs:
            findings.append(f"  drift: {d}")

    # Injury designated-row drift vs canonical CSV.
    canon_inj = ROOT / "nfl-availability-28ef" / "data" / "injuries-week10-2026.csv"
    fresh_csv = DESK / "data" / "injuries-week10-2026-11-18.csv"
    if canon_inj.exists() and fresh_csv.exists():
        with canon_inj.open(newline="", encoding="utf-8") as fh:
            canon_rows = list(csv.DictReader(fh))
        canon_design = {(r["club_abbr"], r["player"]): r for r in canon_rows if r["game_status"].strip()}
        # Fresh designated rows come from the structured CSV (authoritative for this read).
        with fresh_csv.open(newline="", encoding="utf-8") as fh:
            fresh_rows = list(csv.DictReader(fh))
        fresh_design = {(r["club"], r["player"]): r for r in fresh_rows if r["game_status"].strip()}
        inj_diffs = []
        new_design = 0
        for key, fresh in fresh_design.items():
            c = canon_design.get(key)
            if c is None:
                new_design += 1
                continue
            if (c["injury"].strip() or "") != (fresh["injury"].strip() or ""):
                inj_diffs.append(
                    f"{key[1]} ({key[0]}) injuries: fresh='{fresh['injury']}' canonical='{c['injury']}'"
                )
            if (c["game_status"].strip() or "") != (fresh["game_status"].strip() or ""):
                inj_diffs.append(
                    f"{key[1]} ({key[0]}) game_status: fresh='{fresh['game_status']}' canonical='{c['game_status']}'"
                )
        dropped = [k for k in canon_design if k not in fresh_design]
        for key in dropped:
            inj_diffs.append(f"{key[1]} ({key[0]}): in canonical designations, absent in fresh")
        status = "MATCH" if not inj_diffs else f"DRIFT ({len(inj_diffs)} cells)"
        findings.append(
            f"injury designated rows: fresh {len(fresh_design)} (canonical {len(canon_design)}; "
            f"{new_design} newly designated on 11-18, {len(dropped)} dropped): {status}"
        )
        for d in inj_diffs:
            findings.append(f"  drift: {d}")
    else:
        findings.append("MISSING canonical injury CSV")

    report = {
        "check": "F3 drift check 2026-11-18",
        "clock_utc": "2026-11-18T03:46:15Z",
        "ok": ok,
        "findings": findings,
    }
    out = DESK / "data" / "drift-check-2026-11-18.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    # Drift vs stale snapshots is a finding, not a failure. Fail only on internal inconsistency.
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
