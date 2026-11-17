"""Control baselines for NR-PREREG-1 (strategies.py). Deterministic, standard library only.

Input : nfl-results/data/games-2026-w1-9.csv (official final scores, 136 rows, retrieved 2026-11-14)
Output: nfl-readiness-1467fdf7/data/controls.json

Run `python nfl-readiness-1467fdf7/controls.py --check` to recompute and demand byte-identical output.
"""
from __future__ import annotations

import csv
import json
import math
import random
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
import strategies as reg  # noqa: E402

GAMES_CSV = REPO / "nfl-results" / "data" / "games-2026-w1-9.csv"
OUT = HERE / "data" / "controls.json"


def load_games():
    with GAMES_CSV.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    games = []
    for r in rows:
        games.append({
            "week": int(r["week"]),
            "date": r["date"],
            "away": r["away"],
            "home": r["home"],
            "away_score": int(r["away_score"]),
            "home_score": int(r["home_score"]),
            "source_url": r["source_url"],
            "evidence": r["evidence"],
        })
    games.sort(key=lambda g: (g["week"], g["date"], g["away"], g["home"]))
    return games


def winner(g):
    if g["home_score"] > g["away_score"]:
        return g["home"]
    if g["away_score"] > g["home_score"]:
        return g["away"]
    return None  # tie: not graded straight-up


def record_before(games, team, week):
    """Prior win % using only games in weeks < week (no leakage). Returns Fraction or None if no games."""
    played = 0
    score = Fraction(0)
    for g in games:
        if g["week"] >= week:
            continue
        if team not in (g["home"], g["away"]):
            continue
        played += 1
        w = winner(g)
        if w is None:
            score += Fraction(str(reg.RECORD_TIE_CREDIT))
        elif w == team:
            score += 1
    if played == 0:
        return None
    return score / played


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (None, None)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (round(max(0.0, centre - half), 6), round(min(1.0, centre + half), 6))


def summarise(picks_hit, weeks):
    """picks_hit: list of (week, hit bool) for graded games only."""
    n = len(picks_hit)
    k = sum(1 for _, h in picks_hit if h)
    lo, hi = wilson(k, n)
    first = [h for w, h in picks_hit if w in reg.SAMPLE["halves"]["first"]]
    second = [h for w, h in picks_hit if w in reg.SAMPLE["halves"]["second"]]
    drop = {}
    for wk in sorted(set(weeks)):
        rest = [h for w, h in picks_hit if w != wk]
        drop[f"drop_week_{wk}"] = round(sum(rest) / len(rest), 6) if rest else None
    return {
        "n_graded": n,
        "hits": k,
        "hit_rate": round(k / n, 6) if n else None,
        "wilson95": [lo, hi],
        "first_half": {"n": len(first), "hits": sum(first), "rate": round(sum(first) / len(first), 6) if first else None},
        "second_half": {"n": len(second), "hits": sum(second), "rate": round(sum(second) / len(second), 6) if second else None},
        "drop_one_week_rate": drop,
        "drop_one_week_min": min(drop.values()) if drop else None,
        "drop_one_week_max": max(drop.values()) if drop else None,
    }


def random_band(graded, seed, reps):
    """Distribution of hit counts for a fair coin pick on each graded game."""
    rng = random.Random(seed)
    n = len(graded)
    counts = []
    for _ in range(reps):
        counts.append(sum(1 for _ in range(n) if rng.random() < 0.5))
    counts.sort()
    lo_i = int(0.025 * reps)
    hi_i = min(reps - 1, int(0.975 * reps))
    return {
        "replicates": reps,
        "seed": seed,
        "n": n,
        "rate_p2_5": round(counts[lo_i] / n, 6),
        "rate_p97_5": round(counts[hi_i] / n, 6),
        "rate_median": round(counts[reps // 2] / n, 6),
    }


def build():
    games = load_games()
    graded = [g for g in games if winner(g) is not None]
    ties = [g for g in games if winner(g) is None]

    rng = random.Random(reg.RANDOM_SEED)
    rows = []
    for g in games:
        w = winner(g)
        rec_h = record_before(games, g["home"], g["week"])
        rec_a = record_before(games, g["away"], g["week"])
        # C-REC: higher prior win %; tie or no prior record -> home (pre-registered)
        if rec_h is None and rec_a is None:
            rec_pick = g["home"]
        elif rec_a is None:
            rec_pick = g["home"]
        elif rec_h is None:
            rec_pick = g["away"]
        elif rec_a > rec_h:
            rec_pick = g["away"]
        else:
            rec_pick = g["home"]
        rand_pick = g["home"] if rng.random() < 0.5 else g["away"]
        rows.append({
            "week": g["week"],
            "date": g["date"],
            "away": g["away"],
            "home": g["home"],
            "away_score": g["away_score"],
            "home_score": g["home_score"],
            "winner": w,
            "graded": w is not None,
            "C-HOME": g["home"],
            "C-REC": rec_pick,
            "C-RAND": rand_pick,
            "rec_pct_home": None if rec_h is None else round(float(rec_h), 6),
            "rec_pct_away": None if rec_a is None else round(float(rec_a), 6),
            "source_url": g["source_url"],
            "evidence": g["evidence"],
        })

    summaries = {}
    for cid in ("C-RAND", "C-HOME", "C-REC"):
        hits = [(r["week"], r[cid] == r["winner"]) for r in rows if r["graded"]]
        summaries[cid] = summarise(hits, [r["week"] for r in rows if r["graded"]])
    band = random_band([r for r in rows if r["graded"]], reg.RANDOM_SEED, reg.RANDOM_REPLICATES)

    # C-REC vs C-HOME head-to-head on the same graded games
    diff_pp = round(
        (summaries["C-REC"]["hit_rate"] - summaries["C-HOME"]["hit_rate"]) * 100, 4
    )

    # Gate evaluation, computed mechanically from the pre-registered rules
    gate_results = {}
    for cid, s in summaries.items():
        g3 = s["n_graded"] >= 153
        g4 = s["wilson95"][0] is not None and s["wilson95"][0] > band["rate_p97_5"]
        g5 = (s["first_half"]["rate"] or 0) > 0.5 and (s["second_half"]["rate"] or 0) > 0.5
        gate_results[cid] = {"G3_sample": g3, "G4_beats_chance_band": g4, "G5_both_halves_above_50": g5}
    gate_results["C-REC"]["margin_vs_C-HOME_pp"] = diff_pp
    gate_results["C-REC"]["G_margin_vs_C-HOME"] = diff_pp >= reg.HOME_MARGIN_MIN_PP

    return {
        "registration_id": reg.REGISTRATION_ID,
        "registration_commit": "813ce25",
        "frozen_on": reg.FROZEN_ON,
        "universe": {
            "games": len(games),
            "graded_straight_up": len(graded),
            "ties_excluded": [{"week": t["week"], "away": t["away"], "home": t["home"],
                               "score": f'{t["away"]} {t["away_score"]} - {t["home"]} {t["home_score"]}',
                               "source_url": t["source_url"]} for t in ties],
            "source_csv": "nfl-results/data/games-2026-w1-9.csv",
            "source_urls": sorted({g["source_url"] for g in games}),
        },
        "chance_band": band,
        "summaries": summaries,
        "gates": gate_results,
        "rows": rows,
    }


def to_text(result):
    return json.dumps(result, indent=2, sort_keys=True) + "\n"


def main(argv):
    result = build()
    text = to_text(result)
    if "--check" in argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("controls.json is not byte-identical to a fresh rebuild", file=sys.stderr)
            return 1
        print("controls.json reproduces byte-identically")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
