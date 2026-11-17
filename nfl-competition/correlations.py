"""Requirement 7 — correlations from officially sourced numbers only, with n published.

Three rules bind this module:

  1. Every quantity is computed from numbers an official page printed. If the inputs are
     not traceable to a registered source the value is left blank, not estimated.
  2. Every row carries its n. A correlation without a sample size cannot be judged, so a
     row that cannot state one is not published with a value.
  3. Provenance is published per row, naming the official numbers used and the source ids.

Club-level correlations are labelled as a different quantity from leg-level dependence.
A correlation between two clubs' season scoring rates says nothing about whether two legs
inside one game move together, and the table never conflates the two.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (DATA, ROOT, check_artifact, chi2_phi_p, fisher_ci,  # noqa: E402
                    pearson, pearson_p, phi_coefficient, read_csv, round_value)

OUT = DATA / "correlations.json"
FEED = DATA / "results-feed.csv"
STANDINGS = ROOT / "nfl-skill-cfdd" / "data" / "standings-2026-11-14.csv"
BACKTEST = DATA / "backtest.json"

FEED_IDS = ["CP-NFL-RESULTS-W1-9", "CP-NFL-W10-GAME-WASNYG"]
STANDINGS_IDS = ["CP-NFL-STANDINGS"]

MECHANICAL = {
    "C05": "Both series are built from the same club's same games, so the pair is not two "
           "independent measurements. Published as a description of the season, not as "
           "evidence.",
    "C06": "Pythagorean expectation is computed from the same points-for and "
           "points-against that decide the games, so a high correlation is a validity "
           "check on the formula, not a discovery.",
}


def _row(cid, quantity, level, n, value, method, provenance, source_ids, source_url,
         p=None, ci=None, note=None, counts_as_evidence=None):
    return {
        "id": cid, "quantity": quantity, "level": level, "n": n,
        "value": value, "p_value": p,
        "ci95_low": ci[0] if ci else None, "ci95_high": ci[1] if ci else None,
        "method": method, "provenance": provenance, "source_ids": source_ids,
        "source_url": source_url, "note": note,
        "mechanical_caveat": MECHANICAL.get(cid),
        "counts_as_independent_evidence": (counts_as_evidence if counts_as_evidence
                                           is not None else MECHANICAL.get(cid) is None),
    }


def build():
    feed = read_csv(FEED)
    backtest = json.loads(Path(BACKTEST).read_text(encoding="utf-8"))
    standings = read_csv(STANDINGS)
    rows = []

    # ---- C1a  same-game dependence, model-free legs -------------------------------
    league_total = sum(int(r["total_points"]) for r in feed) / len(feed)
    a = b = c = d = 0
    for row in feed:
        home_win = int(row["home_margin"]) > 0
        over = int(row["total_points"]) > league_total
        if home_win and over:
            a += 1
        elif home_win and not over:
            b += 1
        elif not home_win and over:
            c += 1
        else:
            d += 1
    n1 = a + b + c + d
    phi1 = phi_coefficient(a, b, c, d)
    rows.append(_row(
        "C01", "Same-game dependence: home win vs over the league mean total",
        "Leg level (two legs in one game)", n1, phi1,
        "Phi coefficient on the 2x2 joint outcome table",
        f"Official final scores for {n1} games; the threshold is the league mean total "
        f"of {league_total:.4f} points, itself derived from the same official scores",
        FEED_IDS, "https://www.nfl.com/schedules/2026/by-week/week-1",
        p=chi2_phi_p(phi1, n1),
        note="This is the quantity a same-game parlay price depends on. Both legs use "
             "only official numbers, so the estimate needs no model."))

    # ---- C02  same-event dependence, by definition --------------------------------
    rows.append(_row(
        "C02", "Dependence between a leg and itself (the same event twice)",
        "Leg level", len(feed), 1.0,
        "Not estimated. Two legs on the same event cannot disagree, so the dependence is "
        "1 by definition.",
        "Definition, not measurement. Recorded so that a slip built this way is never "
        "priced as if its legs were independent.",
        FEED_IDS, "https://www.nfl.com/schedules/2026/by-week/week-1",
        p=None,
        note="Included because it is the failure mode that matters: a two-leg slip built "
             "from one event looks like a parlay and is not one.",
        counts_as_evidence=False))

    # ---- C03  cross-game dependence within a week ---------------------------------
    by_week = {}
    for row in feed:
        by_week.setdefault(int(row["week"]), []).append(row)
    pairs = []
    for week in sorted(by_week):
        games = by_week[week]
        for i in range(len(games)):
            for j in range(i + 1, len(games)):
                pairs.append((int(games[i]["home_margin"]) > 0,
                              int(games[j]["home_margin"]) > 0))
    a = sum(1 for x, y in pairs if x and y)
    b = sum(1 for x, y in pairs if x and not y)
    c = sum(1 for x, y in pairs if not x and y)
    d = sum(1 for x, y in pairs if not x and not y)
    phi3 = phi_coefficient(a, b, c, d)
    rows.append(_row(
        "C03", "Cross-game dependence: two home-win legs in the same week",
        "Leg level (two legs in different games, same week)", len(pairs), phi3,
        "Phi coefficient over every unordered pair of games played in the same week",
        f"Official final scores; {len(pairs)} game pairs drawn from "
        f"{len(by_week)} weeks",
        FEED_IDS, "https://www.nfl.com/schedules/2026/by-week/week-1",
        p=chi2_phi_p(phi3, len(pairs)),
        note="Legs in different games share a week, so a common shock can move them "
             "together. The estimate is small, but with this n the interval is wide."))

    # ---- C04  margin against total, season level ----------------------------------
    margins = [int(r["home_margin"]) for r in feed]
    totals = [int(r["total_points"]) for r in feed]
    r4 = pearson(margins, totals)
    rows.append(_row(
        "C04", "Home margin against total points",
        "Game level", len(feed), r4, "Pearson correlation",
        f"Official final scores for {len(feed)} games",
        FEED_IDS, "https://www.nfl.com/schedules/2026/by-week/week-1",
        p=pearson_p(r4, len(feed)), ci=fisher_ci(r4, len(feed)),
        note="A negative value would mean blowouts tend to be low scoring. It is a "
             "description of the season, not a betting relationship."))

    # ---- C05 / C06  club season rates ---------------------------------------------
    pf = [int(r["points_for"]) / (int(r["wins"]) + int(r["losses"]) + int(r["ties"]))
          for r in standings]
    pa = [int(r["points_against"]) / (int(r["wins"]) + int(r["losses"]) + int(r["ties"]))
          for r in standings]
    r5 = pearson(pf, pa)
    rows.append(_row(
        "C05", "Club points scored per game against points allowed per game",
        "Club level", len(standings), r5, "Pearson correlation",
        "Official standings read on 2026-11-14; PF and PA divided by games played",
        STANDINGS_IDS, "https://www.nfl.com/standings/",
        p=pearson_p(r5, len(standings)), ci=fisher_ci(r5, len(standings))))

    pyth = []
    actual = []
    for row in standings:
        f = int(row["points_for"])
        against = int(row["points_against"])
        if f > 0 and against > 0:
            pyth.append((f ** 2.37) / (f ** 2.37 + against ** 2.37))
            games = int(row["wins"]) + int(row["losses"]) + int(row["ties"])
            actual.append((int(row["wins"]) + 0.5 * int(row["ties"])) / games)
    r6 = pearson(pyth, actual)
    rows.append(_row(
        "C06", "Pythagorean expectation against actual win percentage",
        "Club level", len(pyth), r6, "Pearson correlation",
        "Official standings read on 2026-11-14; the exponent 2.37 is a published "
        "convention, not fitted here",
        STANDINGS_IDS + ["PYTH-NFL"], "https://www.nfl.com/standings/",
        p=pearson_p(r6, len(pyth)), ci=fisher_ci(r6, len(pyth))))

    # ---- C07 / C08  the model's own information -----------------------------------
    forecast_quality = backtest["forecast_quality"]
    proj_margin = []
    act_margin = []
    proj_total = []
    act_total = []
    # Rebuild the walk-forward pairs from the published forecast quality is not enough,
    # so the forecast rows are recomputed here from the same module the backtest used.
    from backtest import forecasts
    for row in forecasts():
        proj_margin.append(row["proj_margin"])
        act_margin.append(row["actual_margin"])
        proj_total.append(row["proj_total"])
        act_total.append(row["actual_total"])
    r7 = pearson(proj_margin, act_margin)
    rows.append(_row(
        "C07", "Forecast home margin against actual home margin (walk-forward)",
        "Game level", len(proj_margin), r7, "Pearson correlation",
        f"Official final scores; the forecast is built only from weeks before each game, "
        f"so all {len(proj_margin)} pairs are out of sample",
        FEED_IDS, "https://www.nfl.com/schedules/2026/by-week/week-1",
        p=pearson_p(r7, len(proj_margin)), ci=fisher_ci(r7, len(proj_margin)),
        note="The one correlation that carries information about the model rather than "
             "about the season."))
    r8 = pearson(proj_total, act_total)
    rows.append(_row(
        "C08", "Forecast total against actual total (walk-forward)",
        "Game level", len(proj_total), r8, "Pearson correlation",
        f"Official final scores; {len(proj_total)} out-of-sample pairs",
        FEED_IDS, "https://www.nfl.com/schedules/2026/by-week/week-1",
        p=pearson_p(r8, len(proj_total)), ci=fisher_ci(r8, len(proj_total)),
        note="Near zero here is the reason the totals board scores 50.4% against its own "
             f"number (see backtest SB-09). Forecast residual SD "
             f"{forecast_quality['total_residual_sd']} points."))

    # ---- C09 / C10  deliberately blank --------------------------------------------
    for cid, quantity, why in (
        ("C09", "Player prop to team outcome dependence",
         "No per-game player log, target share or snap count was retrieved from any "
         "official source. The official injury report prints a status, not a usage "
         "number, so both series are missing."),
        ("C10", "Three-leg parlay joint distribution",
         "Only 8 weeks carry enough games to build a three-leg slip, and the joint cell "
         "counts are too small to estimate a dependence. Published blank rather than "
         "estimated from 8 slips."),
    ):
        rows.append(_row(
            cid, quantity, "Leg level", None, None,
            "Not computed", why, ["CP-NFL-INJ-W10"] if cid == "C09" else FEED_IDS,
            "https://www.nfl.com/injuries/league/2026/REG10" if cid == "C09"
            else "https://www.nfl.com/schedules/2026/by-week/week-1",
            note="Blank by rule. A number here would be a guess presented as a "
                 "measurement."))

    for row in rows:
        if row["value"] is not None and row["n"] is None:
            raise SystemExit(f"REFUSING TO PUBLISH: {row['id']} has a value but no n")

    payload = {
        "requirement": "R7 - correlations from officially sourced numbers, n published",
        "built_on": "2026-11-14",
        "rules": [
            "Every value is computed from numbers an official page printed.",
            "Every row states its n. A row that cannot state one carries no value.",
            "Club-level correlation is a different quantity from leg-level dependence "
            "and is labelled as such.",
        ],
        "counts": {
            "rows": len(rows),
            "with_values": sum(1 for r in rows if r["value"] is not None),
            "blank": sum(1 for r in rows if r["value"] is None),
            "labelled_mechanical": sum(1 for r in rows if r["mechanical_caveat"]),
        },
        "league_mean_total_used_as_threshold": league_total,
        "rows": rows,
    }
    return round_value(payload, 6)


def main():
    if check_artifact(OUT, build()):
        payload = build()
        print(f"  {payload['counts']['with_values']} correlations computed from official "
              f"numbers, {payload['counts']['blank']} left blank; every published row "
              f"carries n")


if __name__ == "__main__":
    main()
