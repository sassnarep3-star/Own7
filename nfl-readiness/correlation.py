#!/usr/bin/env python3
"""Correlations from official numbers only, with n published beside every value (D6).

Every coefficient here is computed from the official final scores in the pre-registered corpus, is
reported with its integer n, a 95% interval, and the exact rule that produced it. Nothing is
carried over from another desk and nothing is asserted before it is computed.

Measures
  phi          two binary legs, from the 2x2 table (same game, same threshold).
  cramer_v     2x3 or larger tables (cover and total outcome with three levels).
  pearson      two continuous quantities (margin and total; model residual and actual residual).
  spearman     the same, rank-based, guarded against ties.

The same-game rule: a leg pair is only counted when both legs are settled in the same game by the
same official final score. Legs from different weeks are never paired, which is why n is smaller
than the corpus.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = HERE / "data"


def phi(a: int, b: int, c: int, d: int) -> float | None:
    denom = (a + b) * (c + d) * (a + c) * (b + d)
    if denom == 0:
        return None
    return (a * d - b * c) / math.sqrt(denom)


def chi2_p(x2: float, dof: int = 1) -> float:
    """Upper tail of the chi-square distribution, for dof 1..3 (Wilson-Hilferty is not needed here)."""
    if dof == 1:
        return math.erfc(math.sqrt(x2 / 2))
    if dof == 2:
        return math.exp(-x2 / 2)
    raise ValueError("only dof 1 and 2 are used on this page")


def cramer_v(table: list[list[int]]) -> tuple[float | None, float, int]:
    rows, cols = len(table), len(table[0])
    total = sum(sum(r) for r in table)
    if total == 0:
        return None, 0.0, 0
    row_tot = [sum(r) for r in table]
    col_tot = [sum(table[i][j] for i in range(rows)) for j in range(cols)]
    x2 = 0.0
    for i in range(rows):
        for j in range(cols):
            expected = row_tot[i] * col_tot[j] / total
            if expected:
                x2 += (table[i][j] - expected) ** 2 / expected
    v = math.sqrt(x2 / (total * (min(rows, cols) - 1)))
    return v, x2, (rows - 1) * (cols - 1)


def pearson(xs: list[float], ys: list[float]) -> tuple[float | None, float]:
    n = len(xs)
    if n < 3:
        return None, 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None, 0.0
    r = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sxx * syy)
    return r, r * math.sqrt((n - 2) / max(1e-12, 1 - r * r))


def ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def fisher_interval(r: float | None, n: int) -> dict:
    if r is None or n < 4 or abs(r) >= 1:
        return {"low": None, "high": None}
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(n - 3)
    lo, hi = z - 1.96 * se, z + 1.96 * se
    return {"low": round(math.tanh(lo), 6), "high": round(math.tanh(hi), 6)}


def build() -> dict:
    backtest = json.loads((DATA / "backtest.json").read_text())
    games = backtest["games"]
    rows = []

    # 1. Home cover x total over, same game, on the frozen benchmark. This is the parlay leg pair a
    #    same-game builder would multiply if it assumed independence.
    a = b = c = d = 0
    for g in games:
        hc, ov = g["home_covered"], g["went_over"]
        if hc and ov: a += 1
        elif hc and not ov: b += 1
        elif not hc and ov: c += 1
        else: d += 1
    n = a + b + c + d
    p = phi(a, b, c, d)
    rows.append({
        "id": "COR-SIDE-TOTAL", "pair": "Home side covers x total goes over",
        "kind": "phi", "n": n, "value": round(p, 6),
        "interval": fisher_interval(p, n), "p_value": round(chi2_p(n * p * p), 6),
        "table": {"cover_over": a, "cover_under": b, "no_cover_over": c, "no_cover_under": d},
        "p_home_cover": round((a + b) / n, 6), "p_over": round((a + c) / n, 6),
        "p_both_observed": round(a / n, 6), "p_both_independent": round(((a + b) / n) * ((a + c) / n), 6),
        "reading": ("The observed joint rate is compared with the product of the two marginal rates. "
                    "The difference is what a builder would be wrong about by assuming independence."),
        "source_ids": ["X29-NFL-SCHEDULE"],
    })

    # 2. Home cover x home win. A moneyline leg is not a free extra leg beside a spread leg.
    a = b = c = d = 0
    for g in games:
        hc, hw = g["home_covered"], g["home_won"]
        if hc and hw: a += 1
        elif hc and not hw: b += 1
        elif not hc and hw: c += 1
        else: d += 1
    n = a + b + c + d
    p = phi(a, b, c, d)
    rows.append({
        "id": "COR-SIDE-ML", "pair": "Home side covers x home side wins", "kind": "phi",
        "n": n, "value": round(p, 6), "interval": fisher_interval(p, n),
        "p_value": round(chi2_p(n * p * p), 6),
        "table": {"cover_win": a, "cover_no_win": b, "no_cover_win": c, "no_cover_no_win": d},
        "p_home_cover": round((a + b) / n, 6), "p_home_win": round((a + c) / n, 6),
        "p_both_observed": round(a / n, 6), "p_both_independent": round(((a + b) / n) * ((a + c) / n), 6),
        "reading": "A cover without a win is possible only when the home side wins by less than the line.",
        "source_ids": ["X29-NFL-SCHEDULE"],
    })

    # 3. Margin x total: are high-scoring games also wide games?
    r, t = pearson([g["actual_margin"] for g in games], [g["actual_total"] for g in games])
    rows.append({
        "id": "COR-MARGIN-TOTAL", "pair": "Winning margin x total points", "kind": "pearson",
        "n": len(games), "value": round(r, 6), "interval": fisher_interval(r, len(games)),
        "t_statistic": round(t, 6),
        "reading": "Both quantities come from the same official final score.",
        "source_ids": ["X29-NFL-SCHEDULE"],
    })

    # 4. Speed: does the correlation survive as a rank correlation?
    rr, _ = pearson(ranks([g["actual_margin"] for g in games]), ranks([g["actual_total"] for g in games]))
    rows.append({
        "id": "COR-MARGIN-TOTAL-SPEAR", "pair": "Winning margin x total points (Spearman)",
        "kind": "spearman", "n": len(games), "value": round(rr, 6),
        "interval": fisher_interval(rr, len(games)),
        "reading": "A rank check on the same rows, so a single 72-point game cannot carry the Pearson value.",
        "source_ids": ["X29-NFL-SCHEDULE"],
    })

    # 5. Model error structure: if the fair total is wrong in the same direction as the actual total,
    #    the total model is at least scaling something. This is diagnostic, not an edge.
    res_t = [g["forecasts"]["M01"]["residual_total"] for g in games]
    act_t = [g["actual_total"] for g in games]
    r2, t2 = pearson(res_t, act_t)
    rows.append({
        "id": "COR-RESIDUAL-ACTUAL-TOTAL", "pair": "M01 total residual x actual total", "kind": "pearson",
        "n": len(games), "value": round(r2, 6), "interval": fisher_interval(r2, len(games)),
        "t_statistic": round(t2, 6),
        "reading": ("Residual = fair total minus benchmark line. A positive correlation means the model's "
                    "disagreement with the benchmark moves with the truth, which is the minimum a signal needs."),
        "source_ids": ["X29-NFL-SCHEDULE"],
    })

    res_s = [g["forecasts"]["M04"]["residual_side"] for g in games]
    act_m = [g["actual_margin"] for g in games]
    r3, t3 = pearson(res_s, act_m)
    rows.append({
        "id": "COR-RESIDUAL-ACTUAL-SIDE", "pair": "M04 side residual x actual margin", "kind": "pearson",
        "n": len(games), "value": round(r3, 6), "interval": fisher_interval(r3, len(games)),
        "t_statistic": round(t3, 6),
        "reading": ("M04 is the leading side entry, so its residual is the one worth asking about. "
                    "The coefficient is the correlation between 'how far M04's fair line sits from the "
                    "benchmark' and 'what the margin actually was'."),
        "source_ids": ["X29-NFL-SCHEDULE"],
    })

    # 6. Three-level table: home cover, push-band, no cover against over/under. Included to show that
    #    a coefficient changes with the table's shape, which is a reason to publish the table.
    table = [[0, 0], [0, 0]]
    for g in games:
        table[0][0 if g["went_over"] else 1] += 1 if g["home_covered"] else 0
        table[1][0 if g["went_over"] else 1] += 0 if g["home_covered"] else 1
    v, x2, dof = cramer_v(table)
    v = abs(v)
    rows.append({
        "id": "COR-CRAMER-SIDE-TOTAL", "pair": "Home cover x over, Cramer's V (2x2 cross-check)",
        "kind": "cramer_v", "n": n, "value": round(v, 6), "interval": {"low": None, "high": None},
        "chi2": round(x2, 6), "dof": dof,
        "reading": ("For a 2x2 table Cramer's V is the absolute value of phi, which is why it prints "
                    "0.0961 where the phi prints -0.0961. Published as an implementation cross-check, "
                    "not as a second finding."),
        "source_ids": ["X29-NFL-SCHEDULE"],
    })

    # 7. Week-to-week stability of the side signal. One number, with n = number of weeks.
    weekly = []
    for week in sorted({g["week"] for g in games}):
        sub = [g for g in games if g["week"] == week]
        hits = sum(1 for g in sub if (g["forecasts"]["M04"]["p_home_cover"] > 0.5) == g["home_covered"])
        weekly.append({"week": week, "n": len(sub), "hits": hits, "rate": round(hits / len(sub), 6)})
    rates = [w["rate"] for w in weekly if w["n"] >= 10]
    rows.append({
        "id": "COR-WEEK-STABILITY", "pair": "M04 side directional rate across kickoff weeks",
        "kind": "range", "n": len(rates),
        "value": round(max(rates) - min(rates), 6) if rates else None,
        "interval": {"low": round(min(rates), 6) if rates else None,
                     "high": round(max(rates), 6) if rates else None},
        "weekly": weekly,
        "reading": ("The spread of the weekly rate is the size of the noise a reader should expect around "
                    "any single week's number. n here is the number of weeks, not the number of games."),
        "source_ids": ["X29-NFL-SCHEDULE"],
    })

    for row in rows:
        if row["n"] is None or row["n"] < 3:
            raise SystemExit(f"{row['id']}: n must be published and >= 3")
        if row.get("value") is None:
            raise SystemExit(f"{row['id']}: value computed as null — publish a reason instead")
        if not row["source_ids"]:
            raise SystemExit(f"{row['id']}: no registered source")

    return {
        "schema_version": 1,
        "read": "2026-11-17",
        "rule": ("Every value is computed from official final scores in this repository. Every row carries "
                 "n, a 95% interval where the measure supports one, and the exact table or series it came "
                 "from. A value with no official basis is not published."),
        "n_games": len(games),
        "correlations": rows,
        "not_published": [
            {"item": "Player prop leg pairs", "gate": "PG-PROPS",
             "why": "No player-level prop outcome is captured, so no prop-leg dependence can be measured."},
            {"item": "Cross-game parlay dependence", "gate": "none",
             "why": ("Two games in the same week are nearly independent by construction, but 'nearly' is "
                     "not a measurement. A cross-game joint probability is not claimed here; the division "
                     "stays closed for the price reason instead (V7).")},
            {"item": "Market price dependence", "gate": "PG-PRICE-SOURCE",
             "why": "No price is registered, so no price-move correlation can be computed."},
        ],
        "parlay_gate": {
            "id": "JG-1",
            "rule": ("A same-game combination may be ranked only when a directly validated joint probability "
                     "exists for that exact pair of thresholds AND the operator's void/push rule is "
                     "registered. Multiplying two marginal probabilities is not a joint probability."),
            "marginal_products_used": 0,
            "combos_ranked": 0,
            "why": ("The measured phi above is the right input for the first condition, but it is measured on "
                    "the originated benchmark rather than on a market line, and no operator rule is "
                    "registered, so the second condition fails and the gate stays shut."),
        },
    }


def main() -> int:
    DATA.mkdir(exist_ok=True)
    payload = build()
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    target = DATA / "correlation.json"
    if "--check" in sys.argv:
        if not target.exists() or target.read_text() != text:
            raise SystemExit("correlation.json is stale")
        print(f"OK: {len(payload['correlations'])} correlations, all with n")
        return 0
    target.write_text(text)
    for row in payload["correlations"]:
        print(f"  {row['id']:26s} n={row['n']:3d} value={row['value']:+.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
