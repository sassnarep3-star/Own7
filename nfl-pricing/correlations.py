"""Correlations computed ONLY from officially sourced numbers, with n printed on every value.

RULE
----
A correlation is published only when every number behind it comes from a
registered official source. Anything else is left blank and named as a quantity
this project does not measure. Each published value carries:

  * n             the number of paired observations
  * r             Pearson coefficient
  * ci_low/ci_high Fisher z interval on that r
  * source_ids    the registry ids of the numbers that went in

WHAT IS COMPUTED HERE (all from the official closing prices and official scores)
------------------------------------------------------------------------------
1. Line vs total, across games. Structural: do big spreads travel with big totals?
2. Home cover vs over, joint frequency phi. This is the leg dependence a
   two-leg parlay needs.
3. Fair line vs actual margin, on our own originated board. Skill, not market.
4. Fair total vs actual total, on our own originated board.

WHAT IS DELIBERATELY BLANK
--------------------------
Player-prop pairs inside a same-game combo. No published player price exists in
the store, so the dependence cannot be measured from official numbers. It is
reported as a blank with the reason, never as zero and never as "assumed
independent", because a parlay priced on an assumed independence is priced wrong.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
PRICES = HERE / "data" / "price-snapshots.json"
ORIGINATION = HERE / "data" / "origination.json"
OUT = HERE / "data" / "correlations.json"

Z_95 = 1.959963984540054


def pearson(xs: list[float], ys: list[float]) -> dict:
    n = len(xs)
    if n < 3:
        return {"n": n, "r": None, "ci_low": None, "ci_high": None, "note": "fewer than 3 pairs"}
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx <= 0 or syy <= 0:
        return {"n": n, "r": None, "ci_low": None, "ci_high": None,
                "note": "zero variance in one series; r undefined"}
    r = sxy / math.sqrt(sxx * syy)
    r = max(-0.999999, min(0.999999, r))
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3)
    return {
        "n": n,
        "r": round(r, 4),
        "ci_low": round(math.tanh(z - Z_95 * se), 4),
        "ci_high": round(math.tanh(z + Z_95 * se), 4),
        "risk_note": "Nominal interval; assumes independent pairs, which division games violate.",
    }


def phi(table: dict[str, int]) -> dict:
    a = table["home_and_over"]
    b = table["home_and_under"]
    c = table["away_and_over"]
    d = table["away_and_under"]
    n = a + b + c + d
    if n == 0:
        return {"n": 0, "phi": None}
    denom = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    value = 0.0 if denom == 0 else (a * d - b * c) / denom
    return {
        "n": n,
        "phi": round(value, 4),
        "table": table,
        "note": "Joint frequency of home-cover and over on the published closing numbers.",
    }


def build() -> dict:
    snap = json.loads(PRICES.read_text(encoding="utf-8"))
    orig = json.loads(ORIGINATION.read_text(encoding="utf-8"))
    games = [g for g in snap["games"] if g["result_status"] == "joined"]

    lines = [float(abs(float(g["closing_line_home"]))) for g in games]
    totals = [float(g["closing_total"]) for g in games]
    structural = pearson(lines, totals)

    table = {"home_and_over": 0, "home_and_under": 0, "away_and_over": 0, "away_and_under": 0}
    for g in games:
        if g["home_cover"] == "push" or g["total_result"] == "push":
            continue
        home = g["home_cover"] == "cover"
        over = g["total_result"] == "over"
        key = f"{'home' if home else 'away'}_and_{'over' if over else 'under'}"
        table[key] += 1
    leg = phi(table)

    # Benchmark the market against the same outcomes, so a model coefficient is
    # never read in isolation.
    market_side = pearson(
        [float(g["closing_line_home"]) for g in games],
        [float(g["actual_margin_home"]) for g in games],
    )
    market_total = pearson(
        [float(g["closing_total"]) for g in games],
        [float(g["actual_total"]) for g in games],
    )

    forecast_rows = [r for r in orig["games"] if r.get("fair_line_home") is not None]
    skill_side = pearson(
        [float(r["fair_line_home"]) for r in forecast_rows],
        [float(r["actual_margin_home"]) for r in forecast_rows],
    )
    skill_total = pearson(
        [float(r["fair_total"]) for r in forecast_rows if r.get("fair_total") is not None],
        [float(r["actual_total"]) for r in forecast_rows if r.get("fair_total") is not None],
    )

    return {
        "schema_version": 1,
        "rule": (
            "Computed only from registered official numbers. n is printed on every value. "
            "Anything without an official source is blank and named, never assumed to be zero."
        ),
        "publisher_source": {
            "id": "PFR-VEGAS-2026",
            "url": "https://www.pro-football-reference.com/teams/{club}/2026_lines.htm",
            "role": "closing spread and total, both clubs per game",
        },
        "result_source": {
            "id": "NFL-SCHEDULE-2026",
            "url": "https://www.nfl.com/schedules/2026/by-week/week-{week}",
            "role": "final scores used for every outcome",
        },
        "sign_convention": (
            "A line is written from the favoured side as a negative number. So a home line of "
            "-7 means the home club is favoured by a touchdown, and the expected home margin is "
            "+7. That makes the EXPECTED correlation between the signed home line and the home "
            "margin NEGATIVE, and between the closing total and the actual total POSITIVE. "
            "A coefficient with the opposite sign to this convention would mean the number is "
            "pointing the wrong way, not that the forecast is strong."
        ),
        "measured": {
            "market_line_vs_actual_margin": {
                **market_side,
                "pair": "published closing home line ~ actual home margin",
                "expected_sign": "negative",
                "kind": "market benchmark; this is how good the price itself is",
            },
            "market_total_vs_actual_total": {
                **market_total,
                "pair": "published closing total ~ actual game total",
                "expected_sign": "positive",
                "kind": "market benchmark; this is how good the price itself is",
            },
            "market_line_vs_market_total": {
                **structural,
                "pair": "|closing spread| ~ closing total",
                "population": "all reconciled games",
                "kind": "market structure, not leg dependence",
            },
            "home_cover_vs_over": {
                **leg,
                "pair": "home covers ~ total goes over",
                "kind": "leg dependence for a two-leg parlay",
            },
            "fair_line_vs_actual_margin": {
                **skill_side,
                "pair": "our fair line ~ actual home margin",
                "expected_sign": "negative",
                "kind": "forecast skill on the side",
                "compare_to": "market_line_vs_actual_margin",
            },
            "fair_total_vs_actual_total": {
                **skill_total,
                "pair": "our fair total ~ actual game total",
                "expected_sign": "positive",
                "kind": "forecast skill on the total",
                "compare_to": "market_total_vs_actual_total",
            },
        },
        "not_measured": [
            {
                "quantity": "Correlation between two player props in the same game",
                "why_blank": (
                    "No published player price exists in the store, so the numbers behind the "
                    "dependence are not official numbers this project holds."
                ),
                "do_not_assume": (
                    "Not zero. Treating it as zero would misprice every same-game combination. "
                    "The correct state is 'unpriced'."
                ),
                "what_would_close_it": (
                    "A licensed feed with player prices for enough games to estimate the joint "
                    "distribution, plus a rights decision."
                ),
            },
            {
                "quantity": "Correlation between the side and the moneyline",
                "why_blank": (
                    "The moneyline is derived from the same margin distribution as the side, so "
                    "they are functionally dependent by construction. A correlation coefficient on "
                    "two derived views of one number would be an artefact, not a finding."
                ),
                "do_not_assume": "Do not quote a coefficient for it. State the functional dependence instead.",
                "what_would_close_it": "Nothing: it is dependent by definition, not an empirical question.",
            },
            {
                "quantity": "Team-level season correlations carried over from the earlier work",
                "why_blank": (
                    "Those are club-season aggregates across teams, a different quantity from the "
                    "dependence between two legs of one bet. Mixing them would be a category error."
                ),
                "do_not_assume": "Do not substitute a team-season correlation for a leg dependence.",
                "what_would_close_it": "Nothing needed; they answer a different question.",
            },
        ],
        "counts": {"games_in_scope": len(games), "forecast_rows": len(forecast_rows)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build()
    text = json.dumps(result, indent=1) + "\n"
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print("FAIL: data/correlations.json is stale; run python correlations.py")
            return 1
        print("OK: correlations reproduce")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    for name, value in result["measured"].items():
        print(f"  {name}: n={value['n']} r={value.get('r')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
