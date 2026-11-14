#!/usr/bin/env python3
"""Session 243828fc: re-check the Week 10 official injury report against the saved desk ledger.

Inputs (read-only, nothing in other sessions' folders is edited):
  * data/live-injury-report-week10-2026-11-14.psv   – every row transcribed from the live nfl.com page
                                                       read through fetch_page on 2026-11-14 (8 chunks)
  * ../nfl-availability-28ef/data/injuries-week10-2026.csv   – the saved ledger (read 2026-11-13)
  * ../nfl-availability-28ef/data/depth-slots-week10-2026.csv – printed club charts (read 2026-11-12/13)

Outputs (deterministic):
  * data/diff-ledger-vs-live.csv        – one row per player in either source, every field compared
  * data/live-depletion.csv             – every live player with Out/Doubtful/Questionable, matched to the printed
                                           chart, with the printed names behind him (no inferred values)
  * data/summary.json                   – counts used in the published page

Usage:  python3 build_live_check.py          (write outputs)
        python3 build_live_check.py --check  (regenerate in memory; fail if committed outputs differ)
"""
from __future__ import annotations

import csv
import io
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DESK = REPO / "nfl-availability-28ef"
sys.path.insert(0, str(DESK))
from depth import norm_name  # noqa: E402  (the desk's own comparison key, reused unchanged)

LIVE_PSV = HERE / "data" / "live-injury-report-week10-2026-11-14.psv"
LEDGER = DESK / "data" / "injuries-week10-2026.csv"
SLOTS = DESK / "data" / "depth-slots-week10-2026.csv"
OUT_DIFF = HERE / "data" / "diff-ledger-vs-live.csv"
OUT_DEPL = HERE / "data" / "live-depletion.csv"
OUT_SUM = HERE / "data" / "summary.json"

LIVE_URL = "https://www.nfl.com/injuries/league/2026/REG10"
LIVE_READ = "2026-11-14"
PRACTICE = {"F": "Full Participation in Practice", "L": "Limited Participation in Practice",
            "DNP": "Did Not Participate In Practice", "": ""}
PRACTICE_CODE = {v: k for k, v in PRACTICE.items()}
GAME_STATUS_ALERT = ("Out", "Doubtful", "Questionable")


def load_live():
    rows = []
    lines = LIVE_PSV.read_text(encoding="utf-8").splitlines()  # raw input: kept out of Git (see .gitignore)
    header = lines[0].split("|")
    assert header == ["game", "club", "player", "position", "injury", "practice", "game_status"], header
    for n, line in enumerate(lines[1:], start=2):
        parts = line.split("|")
        assert len(parts) == 7, (n, line)
        g, club, player, pos, inj, prac, gs = parts
        assert prac in PRACTICE, (n, prac)
        assert gs in ("", *GAME_STATUS_ALERT), (n, gs)
        rows.append({"game": g, "club": club, "player": player, "position": pos, "injury": inj.strip(),
                     "practice": PRACTICE[prac], "game_status": gs})
    return rows


def load_ledger():
    rows = []
    with LEDGER.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append({"club": r["club_abbr"], "player": r["player"].strip(), "position": r["position"],
                         "injury": r["injury"].strip(), "practice": r["practice_status"].strip(),
                         "game_status": r["game_status"].strip(), "ledger_source": r["source_url"],
                         "ledger_checked_on": r["checked_on"]})
    return rows


def load_slots():
    with SLOTS.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def build_diff(live, ledger):
    lk = {(r["club"], norm_name(r["player"])): r for r in live}
    gk = {(r["club"], norm_name(r["player"])): r for r in ledger}
    assert len(lk) == len(live), "duplicate live key"
    assert len(gk) == len(ledger), "duplicate ledger key"
    out = []
    for key in sorted(set(lk) | set(gk), key=lambda k: (k[0], k[1])):
        a, b = gk.get(key), lk.get(key)
        name = (b or a)["player"]
        changed = []
        if a and b:
            for f in ("injury", "practice", "game_status"):
                if a[f] != b[f]:
                    changed.append(f)
        if a is None:
            status = "added on live page (not in saved ledger)"
        elif b is None:
            status = "in saved ledger, not on live page"
        elif changed:
            status = "changed: " + ", ".join(changed)
        else:
            status = "identical"
        out.append({
            "club": key[0], "player": name,
            "ledger_injury": a["injury"] if a else "", "live_injury": b["injury"] if b else "",
            "ledger_practice": PRACTICE_CODE.get(a["practice"], a["practice"]) if a else "",
            "live_practice": PRACTICE_CODE.get(b["practice"], b["practice"]) if b else "",
            "ledger_game_status": a["game_status"] if a else "", "live_game_status": b["game_status"] if b else "",
            "status": status,
            "live_source_url": LIVE_URL if b else "", "live_read_on": LIVE_READ if b else "",
            "ledger_source_url": a["ledger_source"] if a else "",
        })
    return out


def chains(slots):
    """(club, unit, position, slot) -> rows sorted by printed rank; plus club -> norm name -> hits."""
    chain_map: dict[tuple, list] = {}
    name_index: dict[str, dict[str, list]] = {}
    for row in slots:
        if not row["player"]:
            continue
        chain_map.setdefault((row["club_abbr"], row["unit"], row["position"], row["slot"]), []).append(row)
        club = name_index.setdefault(row["club_abbr"], {})
        for nm in row["player"].split(" / "):
            club.setdefault(norm_name(nm), []).append(row)
    for k in chain_map:
        chain_map[k].sort(key=lambda r: int(r["rank"]))
    return chain_map, name_index


def build_depletion(live, slots):
    chain_map, name_index = chains(slots)
    clubs_with_chart = {r["club_abbr"] for r in slots}
    out = []
    for r in live:
        if r["game_status"] not in GAME_STATUS_ALERT:
            continue
        base = {"club": r["club"], "player": r["player"], "position_reported": r["position"],
                "injury": r["injury"], "practice": r["practice"], "game_status": r["game_status"],
                "unit": "", "chart_position": "", "chart_slot": "", "matched_rank": "",
                "printed_behind_him": "", "chart_source_url": "", "chart_checked_on": "",
                "note": ""}
        if r["club"] not in clubs_with_chart:
            base["note"] = "No printed chart captured for this club (not verified)."
            out.append(base)
            continue
        hits = name_index.get(r["club"], {}).get(norm_name(r["player"]), [])
        if not hits:
            base["note"] = "Not printed on the club's chart in the captured chart (not verified as a starter)."
            out.append(base)
            continue
        if len(hits) > 1:
            base["note"] = "Name printed in more than one chart slot; not resolved."
            out.append(base)
            continue
        hit = hits[0]
        chain = chain_map[(hit["club_abbr"], hit["unit"], hit["position"], hit["slot"])]
        behind = [c["player"] for c in chain if int(c["rank"]) > int(hit["rank"])][:3]
        base.update({"unit": hit["unit"], "chart_position": hit["position"], "chart_slot": hit["slot"],
                     "matched_rank": hit["rank"],
                     "printed_behind_him": " > ".join(behind) if behind else "(no further name printed)",
                     "chart_source_url": hit["source_url"], "chart_checked_on": hit["checked_on"],
                     "note": "Printed rank %s on the club chart." % hit["rank"]})
        out.append(base)
    return out


def per_club(live, ledger, full_diff):
    clubs = sorted({r["club"] for r in live} | {r["club"] for r in ledger})
    out = {}
    for c in clubs:
        d = [r for r in full_diff if r["club"] == c]
        out[c] = {
            "ledger_rows": sum(1 for r in ledger if r["club"] == c),
            "live_rows": sum(1 for r in live if r["club"] == c),
            "added_on_live": sum(1 for r in d if r["status"].startswith("added")),
            "changed": sum(1 for r in d if r["status"].startswith("changed")),
            "ledger_game_status": sum(1 for r in ledger if r["club"] == c and r["game_status"]),
            "live_game_status": sum(1 for r in live if r["club"] == c and r["game_status"]),
        }
    return out


def depletion_by_unit(depl):
    alerted = {(r["club"], norm_name(r["player"])) for r in depl}
    out = {}
    for r in depl:
        if r["matched_rank"] != "1":
            continue
        u = r["unit"] or "unknown"
        o = out.setdefault(u, {"starters_out": 0, "starters_doubtful": 0, "starters_questionable": 0,
                               "with_printed_backup": 0, "backup_also_alerted": 0})
        o["starters_" + {"Out": "out", "Doubtful": "doubtful", "Questionable": "questionable"}[r["game_status"]]] += 1
        if r["printed_behind_him"] not in ("", "(no further name printed)"):
            o["with_printed_backup"] += 1
            second = r["printed_behind_him"].split(" > ")[0]
            if (r["club"], norm_name(second)) in alerted:
                o["backup_also_alerted"] += 1
    return out


def write_csv(rows, fields):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def main(check: bool) -> int:
    if not LIVE_PSV.exists():
        if check:
            print("SKIPPED: raw live transcription is not in Git by design (NFL.com terms s.1.3); cannot re-check.")
            return 0
        print("Missing raw live transcription:", LIVE_PSV)
        return 2
    live = load_live()
    ledger = load_ledger()
    slots = load_slots()
    full_diff = build_diff(live, ledger)
    # Committed output = findings only (rows that differ or are new). Identical rows are counted, not published.
    diff = [r for r in full_diff if r["status"] != "identical"]
    depl = build_depletion(live, slots)

    diff_fields = list(full_diff[0].keys())
    depl_fields = ["club", "player", "position_reported", "injury", "practice", "game_status", "unit",
                   "chart_position", "chart_slot", "matched_rank", "printed_behind_him",
                   "chart_source_url", "chart_checked_on", "note"]
    status_counts = Counter(r["status"].split(":")[0] for r in full_diff)
    summary = {
        "live_rows": len(live),
        "live_clubs": len({r["club"] for r in live}),
        "live_rows_with_game_status": sum(1 for r in live if r["game_status"]),
        "live_clubs_with_game_status": len({r["club"] for r in live if r["game_status"]}),
        "ledger_rows": len(ledger),
        "ledger_rows_with_game_status": sum(1 for r in ledger if r["game_status"]),
        "ledger_clubs_with_game_status": len({r["club"] for r in ledger if r["game_status"]}),
        "added_on_live_page": status_counts["added on live page (not in saved ledger)"],
        "in_ledger_not_on_live": status_counts["in saved ledger, not on live page"],
        "identical": status_counts["identical"],
        "published_diff_rows": len(diff),
        "changed": sum(1 for r in full_diff if r["status"].startswith("changed")),
        "changed_game_status": sum(1 for r in full_diff if "game_status" in r["status"]),
        "changed_practice": sum(1 for r in full_diff if "practice" in r["status"]),
        "changed_injury": sum(1 for r in full_diff if "injury" in r["status"]),
        "depletion_alert_rows": len(depl),
        "depletion_matched_to_chart": sum(1 for r in depl if r["matched_rank"]),
        "depletion_starters_rank1": sum(1 for r in depl if r["matched_rank"] == "1"),
        "depletion_rank1_with_printed_next": sum(1 for r in depl if r["matched_rank"] == "1"
                                                  and r["printed_behind_him"] not in ("", "(no further name printed)")),
        "depletion_not_on_chart": sum(1 for r in depl if not r["matched_rank"]),
        "live_url": LIVE_URL, "live_read_on": LIVE_READ,
        "per_club": per_club(live, ledger, full_diff),
        "depletion_by_unit": depletion_by_unit(depl),
    }
    outputs = {
        OUT_DIFF: write_csv(diff, diff_fields),
        OUT_DEPL: write_csv(depl, depl_fields),
        OUT_SUM: json.dumps(summary, indent=2, sort_keys=True) + "\n",
    }
    if check:
        bad = [str(p) for p, text in outputs.items()
               if not p.exists() or p.read_text(encoding="utf-8") != text]
        if bad:
            print("STALE:", *bad, sep="\n  ")
            return 1
        print("OK: committed outputs reproduce exactly from the live transcription and the saved desk inputs.")
        return 0
    for p, text in outputs.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
