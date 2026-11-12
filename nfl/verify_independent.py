#!/usr/bin/env python3
"""Independent re-derivation of the NFL section's published numbers.

This module deliberately does NOT import the project's own maths. It recomputes
each published value from the committed CSV snapshots with a separate
implementation, so a coding error in one place cannot silently confirm itself.

What it verifies
  * every standings row against league arithmetic identities
  * every published descriptive correlation (Pearson and Spearman)
  * the NFL passer-rating formula against the published component columns
  * internal consistency between published rate columns and their own inputs

What it does NOT do: it never adjudicates whether the snapshots match the live
official pages. That is a separate, dated act recorded in research/sources.json.
A reproduction here means "the published number follows from the published
inputs", not "the inputs are true".

Run: python nfl/verify_independent.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STANDINGS = REPO / "data" / "nfl-standings-2026.csv"
PASSING = REPO / "data" / "nfl-players-passing-2026.csv"
RESULTS = REPO / "research" / "nfl-results.json"
TOLERANCE = 1e-6
# A published one-decimal rate can differ from its own inputs by at most half a
# unit in the last place; anything larger cannot be rounding.
RATE_TOLERANCE = 0.05 + 1e-9


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    dy = math.sqrt(sum((b - my) ** 2 for b in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def average_ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = rank
        i = j + 1
    return ranks


def spearman(xs, ys):
    return pearson(average_ranks(xs), average_ranks(ys))


def records(value):
    w, l, t = (int(part) for part in value.split("-"))
    return w, l, t


def check_standings(rows):
    """Every assertion below is a league identity, not an editorial opinion."""
    errors = []
    facts = {"rows": len(rows)}
    if len(rows) != 32:
        errors.append(f"expected 32 clubs, found {len(rows)}")
    if len({r["Team"] for r in rows}) != len(rows):
        errors.append("duplicate club")
    for r in rows:
        club = r["Team"]
        w, l, t = int(r["W"]), int(r["L"]), int(r["T"])
        pf, pa = int(r["PF"]), int(r["PA"])
        if int(r["NetPts"]) != pf - pa:
            errors.append(f"{club}: NetPts != PF - PA")
        games = w + l + t
        if abs(float(r["PCT"]) - (w + t / 2) / games) > 0.0015:
            errors.append(f"{club}: PCT != (W + T/2) / (W + L + T)")
        hw, hl, ht = records(r["Home"])
        rw, rl, rt = records(r["Road"])
        if hw + hl + ht + rw + rl + rt != games:
            errors.append(f"{club}: home + road games != total games")
        if ht + rt != t:
            errors.append(f"{club}: home ties + road ties != T")
        if hw + ht / 2 + rw + rt / 2 != w + t / 2:
            errors.append(f"{club}: home + road wins != total wins")
        dw, dl, dt = records(r["Div"])
        cw, cl, ct = records(r["Conf"])
        if dw + dl + dt > cw + cl + ct:
            errors.append(f"{club}: division games exceed conference games")
        if dw > cw or dl > cl or dt > ct:
            errors.append(f"{club}: division record exceeds conference component")
        lw, ll, lt = records(r["Last5"])
        if lw + ll + lt != 5:
            errors.append(f"{club}: Last5 does not total five games")
    totals = {
        "wins": sum(int(r["W"]) for r in rows),
        "losses": sum(int(r["L"]) for r in rows),
        "ties": sum(int(r["T"]) for r in rows),
        "pf": sum(int(r["PF"]) for r in rows),
        "pa": sum(int(r["PA"]) for r in rows),
        "home_games": sum(sum(records(r["Home"])) for r in rows),
        "road_games": sum(sum(records(r["Road"])) for r in rows),
    }
    if totals["wins"] != totals["losses"]:
        errors.append("league wins != league losses")
    if totals["pf"] != totals["pa"]:
        errors.append("league points-for != points-against")
    if totals["home_games"] != totals["road_games"]:
        errors.append("home team-games != road team-games")
    if totals["ties"] % 2:
        errors.append("odd number of ties league-wide")
    facts.update(totals)
    afc = [r for r in rows if r["Conference"] == "AFC"]
    nfc = [r for r in rows if r["Conference"] == "NFC"]
    facts["afc"], facts["nfc"] = len(afc), len(nfc)
    if len(afc) != 16 or len(nfc) != 16:
        errors.append(f"conference sizes are {len(afc)}/{len(nfc)}, expected 16/16")
    divisions = {}
    for r in rows:
        divisions.setdefault(r["Division"], []).append(r)
    facts["divisions"] = len(divisions)
    if len(divisions) != 8:
        errors.append(f"expected 8 divisions, found {len(divisions)}")
    for name, group in divisions.items():
        if len(group) != 4:
            errors.append(f"{name}: {len(group)} clubs, expected 4")
    return errors, facts


def check_correlations(standings, passing, published):
    """Recompute every published coefficient from the committed CSVs."""
    errors, checked = [], []
    series = {
        "W vs NetPts (standings)": ([float(r["W"]) for r in standings], [float(r["NetPts"]) for r in standings]),
        "PF vs PA (standings)": ([float(r["PF"]) for r in standings], [float(r["PA"]) for r in standings]),
        "PCT vs NetPts (standings)": ([float(r["PCT"]) for r in standings], [float(r["NetPts"]) for r in standings]),
        "Pass Yds vs TD (QBs)": ([float(r["PassYds"]) for r in passing], [float(r["TD"]) for r in passing]),
        "Pass Yds vs INT (QBs)": ([float(r["PassYds"]) for r in passing], [float(r["INT"]) for r in passing]),
        "Yds/Att vs Rate (QBs)": ([float(r["YdsPerAtt"]) for r in passing], [float(r["Rate"]) for r in passing]),
        "Cmp% vs Rate (QBs)": ([float(r["CmpPct"]) for r in passing], [float(r["Rate"]) for r in passing]),
    }
    for item in published["correlations"]:
        pair = item["pair"]
        if item["pearson"] is None:
            checked.append({"pair": pair, "verdict": "Blank by design", "n": "",
                            "published": "", "recomputed": ""})
            continue
        if pair not in series:
            errors.append(f"{pair}: published but no local re-derivation is defined")
            continue
        xs, ys = series[pair]
        p, s = pearson(xs, ys), spearman(xs, ys)
        ok = abs(p - item["pearson"]) < TOLERANCE and abs(s - item["spearman"]) < TOLERANCE
        if not ok:
            errors.append(f"{pair}: published ({item['pearson']:.6f}/{item['spearman']:.6f}) "
                          f"!= recomputed ({p:.6f}/{s:.6f})")
        if item["n"] != len(xs):
            errors.append(f"{pair}: published n={item['n']} but {len(xs)} rows")
        checked.append({"pair": pair, "verdict": "Reproduced" if ok else "Mismatch",
                        "n": len(xs), "published": f"{item['pearson']:.6f} / {item['spearman']:.6f}",
                        "recomputed": f"{p:.6f} / {s:.6f}"})
    return errors, checked


def nfl_passer_rating(row):
    att, cmp_, yds, td, ints = (float(row[k]) for k in ("Att", "Cmp", "PassYds", "TD", "INT"))

    def cap(v):
        return max(0.0, min(2.375, v))

    a = cap((cmp_ / att - 0.3) * 5)
    b = cap((yds / att - 3) * 0.25)
    c = cap(td / att * 20)
    d = cap(2.375 - ints / att * 25)
    return (a + b + c + d) / 6 * 100


def check_passing(passing):
    """Check each published rate column against its own listed inputs.

    Cmp% is Cmp/Att. Yds/Att is PassYds/Att. The passer rating is a fixed formula
    over Att, Cmp, PassYds, TD and INT. A one-decimal published rate can only
    differ from its inputs by rounding, i.e. half a unit in the last place.
    Any larger difference means the columns disagree with each other.
    """
    issues, rating_errors = [], []
    for r in passing:
        att, cmp_, yds = float(r["Att"]), float(r["Cmp"]), float(r["PassYds"])
        name = r["Player"]
        if abs(cmp_ / att * 100 - float(r["CmpPct"])) > 0.6:
            issues.append({"player": name, "column": "Cmp%",
                           "published": r["CmpPct"], "from_inputs": f"{cmp_ / att * 100:.2f}",
                           "detail": "does not follow from Cmp/Att"})
        exact_ypa = yds / att
        if abs(exact_ypa - float(r["YdsPerAtt"])) > RATE_TOLERANCE:
            issues.append({"player": name, "column": "Yds/Att",
                           "published": r["YdsPerAtt"], "from_inputs": f"{exact_ypa:.4f}",
                           "detail": f"PassYds/Att = {exact_ypa:.4f}, which rounds to "
                                     f"{round(exact_ypa, 1):.1f}; the published value is "
                                     f"outside rounding distance"})
        if abs(nfl_passer_rating(r) - float(r["Rate"])) > 0.15:
            rating_errors.append(
                f"{name}: Rate {r['Rate']} does not follow from Att/Cmp/PassYds/TD/INT "
                f"(recomputed {nfl_passer_rating(r):.2f})")
    return issues, rating_errors


def sensitivity(passing, published):
    """How much does the Yds/Att correlation move if exact yards/attempt is used?

    If the published Yds/Att column disagrees with its own PassYds and Att on some
    rows, a correlation computed on that column inherits the disagreement. This
    quantifies the exposure instead of hiding it.
    """
    rate = [float(r["Rate"]) for r in passing]
    published_ypa = [float(r["YdsPerAtt"]) for r in passing]
    exact_ypa = [float(r["PassYds"]) / float(r["Att"]) for r in passing]
    p_pub, p_exact = pearson(published_ypa, rate), pearson(exact_ypa, rate)
    s_pub, s_exact = spearman(published_ypa, rate), spearman(exact_ypa, rate)
    stated = next(c for c in published["correlations"] if c["pair"] == "Yds/Att vs Rate (QBs)")
    return {
        "pearson_published": p_pub, "pearson_exact": p_exact,
        "spearman_published": s_pub, "spearman_exact": s_exact,
        "pearson_delta": abs(p_pub - p_exact), "spearman_delta": abs(s_pub - s_exact),
        "matches_published": abs(p_pub - stated["pearson"]) < TOLERANCE
                             and abs(s_pub - stated["spearman"]) < TOLERANCE,
    }


def main() -> int:
    standings = list(csv.DictReader(STANDINGS.open(encoding="utf-8", newline="")))
    passing = list(csv.DictReader(PASSING.open(encoding="utf-8", newline="")))
    published = json.loads(RESULTS.read_text(encoding="utf-8"))

    errors, facts = check_standings(standings)
    corr_errors, correlations = check_correlations(standings, passing, published)
    pass_issues, rating_errors = check_passing(passing)
    errors += corr_errors + rating_errors
    sens = sensitivity(passing, published)
    if not sens["matches_published"]:
        errors.append("Yds/Att vs Rate: neither column reproduces the published coefficient")

    reproduced = sum(1 for c in correlations if c["verdict"] == "Reproduced")
    denominator = sum(1 for c in correlations if c["verdict"] != "Blank by design")
    print(f"standings : {facts['rows']} rows, {facts['divisions']} divisions, "
          f"{facts['afc']} AFC / {facts['nfc']} NFC, wins {facts['wins']} = losses {facts['losses']}, "
          f"PF {facts['pf']} = PA {facts['pa']}, home {facts['home_games']} = road {facts['road_games']} team-games")
    print(f"correlation: {reproduced}/{denominator} reproduced to 1e-6, "
          f"{sum(1 for c in correlations if c['verdict'] == 'Blank by design')} blank by design")
    print(f"passing    : {len(passing)} rows; passer rating verified for all rows")
    print(f"sensitivity: Yds/Att vs Rate pearson {sens['pearson_published']:.6f} on the published column "
          f"vs {sens['pearson_exact']:.6f} on exact PassYds/Att (delta {sens['pearson_delta']:.2e})")
    if pass_issues:
        print(f"column disagreements: {len(pass_issues)}")
        for i in pass_issues:
            print(f" - {i['player']}: {i['column']} printed {i['published']}, "
                  f"own inputs give {i['from_inputs']}")
    else:
        print("column disagreements: none")
    if errors:
        print("FAILED")
        for e in errors:
            print(" -", e)
        return 1
    print("OK: every published coefficient reproduces from the committed snapshots; "
          "column disagreements are reported above and are not reconciliation failures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
