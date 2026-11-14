#!/usr/bin/env python3
"""Independent line-by-line re-verification of committed NFL observations
against freshly retrieved official NFL.com evidence.

Session arena/81ddda65-own7. This is a re-check of the *current* committed CSVs
against the evidence captured in research/nfl/evidence-81ddda65/. It does NOT
inherit any earlier session's verification. A value that the official source does
not confirm is reported as a mismatch, never silently filled in.

Usage:
    python3 scripts/verify_nfl_81ddda65.py            # report
    python3 scripts/verify_nfl_81ddda65.py --check    # exit 1 on any mismatch

Method note: the evidence file holds rendered-text captures from the Arena page
reader (direct sandbox HTTPS to nfl.com is blocked). These are normalized
transcriptions, not raw HTTP archives.
"""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE = os.path.join(ROOT, "research", "nfl", "evidence-81ddda65",
                        "official-nfl-2026-11-14.json")

DATA = {
    "standings": os.path.join(ROOT, "data", "nfl-standings-week10-2026.csv"),
    "team_defense": os.path.join(ROOT, "data", "nfl-team-defense-passing-2026.csv"),
    "team_offense": os.path.join(ROOT, "data", "nfl-team-offense-passing-2026.csv"),
    "player_passing": os.path.join(ROOT, "data", "nfl-players-passing-2026.csv"),
    "injuries": os.path.join(ROOT, "data", "nfl-injuries-2026-w10.csv"),
}


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_evidence():
    with open(EVIDENCE, encoding="utf-8") as f:
        return json.load(f)


def num(value):
    """Normalize a cell to float, or None if blank/non-numeric."""
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.upper() in {"NA", "N/A", "NONE"}:
        return None
    # strip a trailing 'T' (e.g. '82T' long gain) only when the prefix is numeric
    try:
        return float(text)
    except ValueError:
        if text.endswith("T") and text[:-1].replace(".", "", 1).isdigit():
            return float(text[:-1])
        return None


def close(a, b, tol=0.051):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) <= tol


def eq(a, b):
    left = "" if a is None else str(a)
    right = "" if b is None else str(b)
    return left.strip() == right.strip()


def check_standings(ev, csv_rows):
    mism = []
    ev_by = {r["team"]: r for r in ev["standings"]}
    for row in csv_rows:
        team = row["Team"]
        if team not in ev_by:
            mism.append(f"standings: {team} not in official evidence")
            continue
        e = ev_by[team]
        for key, evkey in [("W", "W"), ("L", "L"), ("T", "T"), ("PCT", "PCT"),
                           ("PF", "PF"), ("PA", "PA"), ("NetPts", "NetPts")]:
            if not close(num(row.get(key)), num(e[evkey])):
                mism.append(f"standings {team}.{key}: csv={row.get(key)!r} official={e[evkey]!r}")
        # internal consistency: PCT and NetPts
        w, l, t = num(row["W"]), num(row["L"]), num(row["T"])
        pf, pa = num(row["PF"]), num(row["PA"])
        if None not in (w, l, t) and not close(num(row["PCT"]), (w + t / 2.0) / (w + l + t)):
            mism.append(f"standings {team}.PCT internal formula mismatch")
        if None not in (pf, pa) and not close(num(row["NetPts"]), pf - pa):
            mism.append(f"standings {team}.NetPts internal mismatch (PF-PA)")
    if len(ev_by) != len(csv_rows):
        mism.append(f"standings row count: csv={len(csv_rows)} official={len(ev_by)}")
    return mism


def check_team_defense(ev, csv_rows):
    mism = []
    ev_by = {r["team"]: r for r in ev["team_defense_passing"]}
    cols = ["Att", "Cmp", "CmpPct", "YdsPerAtt", "Yds", "TD", "INT", "Rate",
            "First", "FirstPct", "Plus20", "Plus40", "Lng", "Sck"]
    for row in csv_rows:
        team = row["Team"]
        if team not in ev_by:
            mism.append(f"team_defense: {team} not in official evidence")
            continue
        vals = ev_by[team]["vals"]
        for col, v in zip(cols, vals):
            got = row.get(col)
            if col == "Lng":
                if not eq(got, v):
                    mism.append(f"team_defense {team}.{col}: csv={got!r} official={v!r}")
            elif not close(num(got), num(v)):
                mism.append(f"team_defense {team}.{col}: csv={got!r} official={v!r}")
    if len(ev_by) != len(csv_rows):
        mism.append(f"team_defense row count: csv={len(csv_rows)} official={len(ev_by)}")
    return mism


def check_team_offense(ev, csv_rows):
    mism = []
    ev_by = {r["team"]: r for r in ev["team_offense_passing"]}
    cols = [f"C{i}" for i in range(1, 16)]
    for row in csv_rows:
        team = row["Team"]
        if team not in ev_by:
            mism.append(f"team_offense: {team} not in official evidence")
            continue
        vals = ev_by[team]["vals"]
        for col, v in zip(cols, vals):
            if not close(num(row.get(col)), num(v)):
                mism.append(f"team_offense {team}.{col}: csv={row.get(col)!r} official={v!r}")
    if len(ev_by) != len(csv_rows):
        mism.append(f"team_offense row count: csv={len(csv_rows)} official={len(ev_by)}")
    return mism


def check_player_passing(ev, csv_rows):
    mism = []
    ev_by = {r["player"]: r for r in ev["player_passing"]}
    cols = ["PassYds", "YdsPerAtt", "Att", "Cmp", "CmpPct", "TD", "INT", "Rate",
            "First", "FirstPct", "Plus20", "Plus40", "Lng", "Sck", "SckY"]
    for row in csv_rows:
        player = row["Player"]
        if player not in ev_by:
            mism.append(f"player_passing: {player} not in official evidence")
            continue
        e = ev_by[player]
        if not close(num(row.get("Rank")), num(e["rank"]), tol=0.0):
            mism.append(f"player_passing {player}.Rank: csv={row.get('Rank')!r} official={e['rank']!r}")
        vals = e["vals"]
        for col, v in zip(cols, vals):
            got = row.get(col)
            if col == "Lng":
                if not eq(got, v):
                    mism.append(f"player_passing {player}.{col}: csv={got!r} official={v!r}")
            elif not close(num(got), num(v)):
                mism.append(f"player_passing {player}.{col}: csv={got!r} official={v!r}")
    if len(ev_by) != len(csv_rows):
        mism.append(f"player_passing row count: csv={len(csv_rows)} official={len(ev_by)}")
    return mism


def check_injuries(ev, csv_rows):
    mism = []
    ev_rows = ev["injuries_thursday_tnf"]
    if len(ev_rows) != len(csv_rows):
        mism.append(f"injuries row count: csv={len(csv_rows)} official={len(ev_rows)}")
    for row, e in zip(csv_rows, ev_rows):
        for col, evkey in [("Team", "team"), ("Player", "player"), ("Position", "position"),
                           ("Injury", "injury"), ("PracticeStatus", "practice"),
                           ("GameStatus", "game")]:
            if not eq(row.get(col), e[evkey]):
                mism.append(f"injuries {e['player']}.{col}: csv={row.get(col)!r} official={e[evkey]!r}")
    return mism


def run_all():
    ev = load_evidence()
    results = {}
    results["standings"] = check_standings(ev, load_csv(DATA["standings"]))
    results["team_defense"] = check_team_defense(ev, load_csv(DATA["team_defense"]))
    results["team_offense"] = check_team_offense(ev, load_csv(DATA["team_offense"]))
    results["player_passing"] = check_player_passing(ev, load_csv(DATA["player_passing"]))
    results["injuries"] = check_injuries(ev, load_csv(DATA["injuries"]))
    return results


def main():
    results = run_all()
    total = 0
    for name, mism in results.items():
        total += len(mism)
        status = "OK" if not mism else "MISMATCH"
        print(f"[{status}] {name}: {len(mism)} mismatch(es)")
        for m in mism:
            print("    -", m)
    print(f"\nTotal mismatches: {total}")
    print("Evidence:", os.path.relpath(EVIDENCE, ROOT),
          "retrieved", load_evidence()["retrieved_on"])
    if "--check" in sys.argv:
        return 1 if total else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
