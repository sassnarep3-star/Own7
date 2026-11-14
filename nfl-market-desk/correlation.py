#!/usr/bin/env python3
"""Correlation values: measured where two official numbers exist for the same unit, refused otherwise.

The brief's rule is narrower than "compute more correlations". It is: compute only from officially
sourced numbers, and publish ``n`` beside every value. This module adds three things the earlier
desks could not:

  1. **Player-prop leg dependence, measured from real joint outcomes.** Earlier sessions left every
     prop correlation blank because no per-game player log had been retrieved. Eight official
     NFL.com player logs are now parsed and verified (see ``player_stats.py``), so two team-mates'
     same-game markets can be correlated on the weeks they both played. That is a genuine
     leg-dependence measurement, and its sample size is small — which is why ``n`` is printed next
     to every value and a minimum-n floor suppresses anything below it.
  2. **An explicit refusal table.** Every correlation someone might reasonably want, and the reason
     it is not computed. A blank with a named reason is more useful than a plausible number.
  3. **n first.** No coefficient appears without its sample size, on the page or in the CSV.

Sample floor policy: a correlation needs at least 8 paired observations to be published, and 20 to
be treated as anything more than exploratory. Below 20 the interval is wider than the effect is
interesting, and the row says so in its own column rather than in a footnote.
"""
from __future__ import annotations

import csv
from itertools import combinations
from pathlib import Path

from emit import emit_csv, emit_json, parse_args
import player_stats
import stats

REPO = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

COLUMN_LABEL = {
    "PYDS": "passing yards",
    "RYDS": "rushing yards",
    "RECYDS": "receiving yards",
    "REC": "receptions",
    "CAR": "carries",
    "PTD": "passing touchdowns",
    "RECTD": "receiving touchdowns",
}
MIN_PUBLISH_N = 8
MIN_EXPLORATORY_N = 20
SOURCE_PLAYER = "https://www.nfl.com/players/"
READ_ON = "2026-11-14"


def _game_rows() -> list[dict]:
    with (DATA / "verified-results-2026-w1-9.csv").open(encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["result_type"] == "game"]
    for row in rows:
        row["week"] = int(row["week"])
        for key in ("away_score", "home_score", "margin_home", "total_points"):
            row[key] = int(row[key])
    return rows


def _standings() -> list[dict]:
    with (REPO / "data" / "nfl-standings-week10-2026.csv").open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------- game-level
def game_level() -> list[dict]:
    """Correlations between two quantities both measured on the same game, n = games."""
    games = _game_rows()
    margins = [g["margin_home"] for g in games]
    totals = [g["total_points"] for g in games]
    rows = []
    pairs = [
        ("G-MARGIN-TOTAL", "home margin (home - away)", "game total points",
         margins + totals, None),
    ]
    r = stats.pearson(margins, totals)
    n = len(margins)
    rows.append(_row("G-MARGIN-TOTAL", "Home margin vs game total",
                     "home margin (home score - away score)", "game total points",
                     n, r, "Every game in the verified feed, weeks 1-9.",
                     "Two official scores per game. Both quantities are arithmetic on the same "
                     "pair, so this is a structural relationship, not a discoverable edge.",
                     "NFL-STANDINGS NFL-SCHED-X29",
                     "https://www.nfl.com/schedules/2026/by-week/week-1"))
    return rows


# --------------------------------------------------------------------------- player-level
def player_level() -> tuple[list[dict], list[dict]]:
    """Same-game correlations between two team-mates, from official per-game logs."""
    games, checks = player_stats.parse_all()
    by_player: dict[str, dict[int, dict]] = {}
    meta: dict[str, dict] = {}
    for row in games:
        by_player.setdefault(row["player_slug"], {})[row["week"]] = row
        meta[row["player_slug"]] = {"player": row["player"], "club": row["club_abbr"],
                                    "position": row["position"], "url": row["source_url"]}
    pairs = [
        ("P-BUF-ALLEN-COOK", "josh-allen", "james-cook",
         ("PYDS", "rushing yards"),
         "A quarterback's passing volume and his lead back's rushing volume compete for the same "
         "drives, so a same-game parlay on both overs must not be priced as independent."),
        ("P-BUF-ALLEN-SHAKIR", "josh-allen", None,
         ("PYDS", "receiving yards"),
         "Passing yards and one receiver's receiving yards are mechanically linked."),
        ("P-DET-GIBBS-STBROWN", "jahmyr-gibbs", "amon-ra-st-brown",
         ("RYDS", "receiving yards"),
         "Two team-mates who split the same touch pool."),
        ("P-CIN-CHASE-HIGGINS", "ja-marr-chase", "tee-higgins",
         ("RECYDS", "receiving yards"),
         "Two receivers on the same team compete for the same targets."),
        ("P-GB-JACOBS-KRAFT", "josh-jacobs", "tucker-kraft",
         ("RYDS", "receiving yards"),
         "Rushing and receiving volume in the same offence."),
    ]
    rows = []
    refusals = []
    for pair_id, a_slug, b_slug, (a_col, b_label), why in pairs:
        if b_slug is None:
            # Khalil Shakir's log was read but not committed as a verified pair partner: the page
            # printed no header and its career row omits a phase, so a column mapping would be a
            # guess. Refuse rather than guess.
            refusals.append({
                "correlation_id": pair_id,
                "quantity_a": "passing yards",
                "quantity_b": "receiving yards",
                "status": "refused",
                "n": "",
                "reason": "Khalil Shakir's page prints no Recent Games header and his career row "
                          "omits the rushing phase, so the receiving column cannot be assigned "
                          "without guessing. The page was read; the mapping is not safe.",
                "how_to_close": "Read the per-game log tab (/stats/logs/) where every column is "
                                "labelled, for both players, then re-run.",
                "source_url": "https://www.nfl.com/players/khalil-shakir/stats/",
            })
            continue
        weeks = sorted(set(by_player.get(a_slug, {})) & set(by_player.get(b_slug, {})))
        if len(weeks) < MIN_PUBLISH_N:
            refusals.append({
                "correlation_id": pair_id, "quantity_a": a_col, "quantity_b": b_label,
                "status": "refused", "n": len(weeks),
                "reason": f"only {len(weeks)} shared games, below the publish floor of "
                          f"{MIN_PUBLISH_N}",
                "how_to_close": "read more player pages for the same club",
                "source_url": meta.get(a_slug, {}).get("url", SOURCE_PLAYER),
            })
            continue
        xs, ys = [], []
        for week in weeks:
            va = by_player[a_slug][week].get(a_col)
            vb = by_player[b_slug][week].get(b_col_for(b_slug, b_label))
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                xs.append(va)
                ys.append(vb)
        n = len(xs)
        r = stats.pearson(xs, ys)
        rows.append(_row(
            pair_id,
            f"{meta[a_slug]['player']} vs {meta[b_slug]['player']}: "
            f"{COLUMN_LABEL.get(a_col, a_col.lower())} and {b_label}",
            f"{meta[a_slug]['player']} ({meta[a_slug]['club']}), {COLUMN_LABEL.get(a_col, a_col)}",
            f"{meta[b_slug]['player']} ({meta[b_slug]['club']}) {b_label}",
            n, r,
            f"Same-game values from the official per-game logs, weeks "
            f"{', '.join(str(w) for w in weeks)}; both columns reconcile to the printed season "
            f"total.",
            why, "NFL-PLAYER-STATS", meta[a_slug]["url"]))
    return rows, refusals


def b_col_for(slug: str, label: str) -> str:
    if label == "receiving yards":
        return "RECYDS"
    if label == "rushing yards":
        return "RYDS"
    return "RECYDS"


# --------------------------------------------------------------------------- row builder
def _row(cid, label, qa, qb, n, r, provenance, caveat, source_ids, url) -> dict:
    if r is None:
        low = high = ""
        p = ""
    else:
        low, high = stats.fisher_ci(r, n)
        p = stats.pearson_p(r, n)
    exploratory_only = "yes" if n < MIN_EXPLORATORY_N else "no"
    return {
        "correlation_id": cid,
        "label": label,
        "quantity_a": qa,
        "quantity_b": qb,
        "n": n,
        "pearson_r": round(r, 4) if r is not None else "",
        "fisher_95_low": round(low, 4) if low != "" else "",
        "fisher_95_high": round(high, 4) if high != "" else "",
        "p_value": round(p, 6) if p != "" else "",
        "significant_0.05": ("yes" if p != "" and p <= 0.05 else "no") if p != "" else "",
        "exploratory_only_n_lt_20": exploratory_only,
        "provenance": provenance,
        "caveat": caveat,
        "source_ids": source_ids,
        "source_url": url,
        "read_on": READ_ON,
    }


# --------------------------------------------------------------------------- refusals
def refused_team_level() -> list[dict]:
    """Correlations that cannot be computed from what this repository actually holds."""
    return [
        {"correlation_id": "R-MARKET-LINE", "quantity_a": "model fair line",
         "quantity_b": "market line", "status": "refused", "n": "",
         "reason": "no market line exists anywhere in the repository, so the paired sample is "
                   "zero. This is the correlation that would tell you whether the model's edge is "
                   "real, and it cannot be computed without a price.",
         "how_to_close": "register a licensed odds source and record an opening and closing "
                         "number per originated market in the price store",
         "source_url": "https://www.nfl.com/legal/terms/"},
        {"correlation_id": "R-SPREAD-TOTAL-MARKET", "quantity_a": "market spread",
         "quantity_b": "market total", "status": "refused", "n": "",
         "reason": "same as above: no market numbers at all",
         "how_to_close": "as above", "source_url": "https://www.nfl.com/legal/terms/"},
        {"correlation_id": "R-CLV-SIGNAL", "quantity_a": "closing-line value",
         "quantity_b": "signal strength", "status": "refused", "n": "",
         "reason": "CLV needs an opening and a closing price per bet; none exists",
         "how_to_close": "as above", "source_url": "https://www.nfl.com/legal/terms/"},
        {"correlation_id": "R-INJURY-LINE", "quantity_a": "depletion index",
         "quantity_b": "realised margin vs line", "status": "refused", "n": "",
         "reason": "injury snapshots cover Week 10 only and Week 10 has no settled result in the "
                   "feed, so there is no week where both an injury index and a settled outcome "
                   "exist",
         "how_to_close": "archive each week's official injury report before kick-off for a full "
                         "season, then join",
         "source_url": "https://www.nfl.com/injuries/league/2026/REG10"},
        {"correlation_id": "R-DEPTH-MARGIN", "quantity_a": "ranks consumed",
         "quantity_b": "point margin", "status": "refused", "n": "",
         "reason": "the same Week 10 problem: the depth index is a Week 10 snapshot and no Week 10 "
                   "result is settled in the feed",
         "how_to_close": "as above",
         "source_url": "https://www.nfl.com/injuries/league/2026/REG10"},
        {"correlation_id": "R-SNAP-SHARE", "quantity_a": "snap share",
         "quantity_b": "any outcome", "status": "refused", "n": "",
         "reason": "no snap-count source is registered and none was read",
         "how_to_close": "identify an official snap-count publisher with reusable rights",
         "source_url": "https://www.nfl.com/legal/terms/"},
    ]


def main() -> None:
    parse_args(__doc__ or "correlation")
    measured = game_level()
    player_rows, player_refusals = player_level()
    measured.extend(player_rows)
    refusals = refused_team_level() + player_refusals
    for row in measured:
        if row["n"] < MIN_PUBLISH_N:
            raise SystemExit(f"{row['correlation_id']}: published with n={row['n']} below the floor")
        if row["n"] == "" or row["n"] is None:
            raise SystemExit(f"{row['correlation_id']}: published without a sample size")
    emit_csv(DATA / "correlations-2026-11-14.csv", measured)
    emit_csv(DATA / "correlations-refused-2026-11-14.csv", refusals)
    emit_json(DATA / "correlation-summary-2026-11-14.json", {
        "measured": len(measured),
        "refused": len(refusals),
        "min_publish_n": MIN_PUBLISH_N,
        "min_exploratory_n": MIN_EXPLORATORY_N,
        "significant_at_0.05": sum(1 for r in measured if r["significant_0.05"] == "yes"),
        "exploratory_only": sum(1 for r in measured if r["exploratory_only_n_lt_20"] == "yes"),
        "policy": "A value is published only when both quantities come from an official source for "
                  "the same unit, and only with its n. Anything else is refused with the reason and "
                  "the action that would close it.",
        "warning": "With this many pairs tested, one 'significant' result at 0.05 is close to what "
                   "chance produces. The number of tests is published so the reader can discount "
                   "accordingly; no correlation here is presented as an edge.",
    })
    print(f"Correlations: {len(measured)} measured (each with n), {len(refusals)} refused with a "
          f"reason. {sum(1 for r in measured if r['significant_0.05']=='yes')} reach p <= 0.05 out "
          f"of {len(measured)} tests.")


if __name__ == "__main__":
    main()
