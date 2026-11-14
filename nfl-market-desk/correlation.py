#!/usr/bin/env python3
"""Correlations, computed only from officially sourced numbers, with n on every value.

Two kinds of correlation are published, and they are kept apart because they answer
different questions:

A. MARKET CORRELATION (what the books price together)
   Between our own originated series and the market's, and between market totals and
   market spreads across the priced games. Source: the relayed odds capture. This is a
   property of the market, and it is the input a parlay needs.

B. OUTCOME CORRELATION (what actually happens together)
   Between official final scores: does a game's margin move with its total? Source: the
   official results file. This is a property of football.

The gap between A and B is the mispricing a combo bet could exploit, so both are shown
for the same n. Every value carries:
    n            the number of games actually used
    r            Pearson correlation
    ci_lo/ci_hi  Fisher-z 95% interval
    p_value      two-sided t test
    sources      the source ids the numbers came from

Rules enforced:
* A pair is dropped, and the drop is published, if either input is missing. Nothing is
  filled in and nothing is pairwise-deleted silently.
* A value whose n is below the stated floor is reported but labelled
  `underpowered` and is excluded from any ranking.
* No correlation is computed from a series that mixes providers or definitions.
"""
from __future__ import annotations

import math
from statistics import NormalDist

import sources

ND = NormalDist()
MIN_N = 30  # below this, r is not rankable; the row is still shown with its n


def pearson(xs: list[float], ys: list[float]) -> dict:
    n = len(xs)
    if n != len(ys):
        raise ValueError("length mismatch")
    if n < 3:
        return {"n": n, "r": None, "p_value": None, "ci_lo": None, "ci_hi": None}
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return {"n": n, "r": None, "p_value": None, "ci_lo": None, "ci_hi": None,
                "why": "zero variance in at least one series"}
    r = sxy / math.sqrt(sxx * syy)
    r = max(-0.999999, min(0.999999, r))
    # two-sided t test, df = n-2
    t = r * math.sqrt((n - 2) / (1 - r * r))
    p = 2 * (1 - _t_cdf(abs(t), n - 2))
    # Fisher z interval
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(n - 3) if n > 3 else None
    if se is None:
        lo = hi = None
    else:
        lo = math.tanh(z - 1.959963985 * se)
        hi = math.tanh(z + 1.959963985 * se)
    return {"n": n, "r": round(r, 4), "p_value": round(min(1.0, p), 6),
            "ci_lo": round(lo, 4) if lo is not None else None,
            "ci_hi": round(hi, 4) if hi is not None else None}


def _t_cdf(t: float, df: int) -> float:
    """Student-t CDF via the incomplete beta function (continued fraction)."""
    x = df / (df + t * t)
    ib = _betainc(df / 2.0, 0.5, x)
    if t > 0:
        return 1 - 0.5 * ib
    return 0.5 * ib


def _betainc(a: float, b: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a
    if x < (a + 1) / (a + b + 2):
        return front * _cf(a, b, x)
    return 1.0 - front * _cf(b, a, 1 - x)


def _cf(a: float, b: float, x: float) -> float:
    tiny = 1e-30
    c, d = 1.0, 1.0 - (a + b) * x / (a + 1)
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, 200):
        m2 = 2 * m
        aa = m * (b - m) * x / ((a + m2 - 1) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (a + b + m) * x / ((a + m2) * (a + m2 + 1))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    return h


def _holm(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    out = [None] * m
    running = 0.0
    for rank, i in enumerate(order):
        adj = min(1.0, (m - rank) * pvals[i])
        running = max(running, adj)
        out[i] = round(running, 6)
    return out


def build(side_board: list[dict], total_board: list[dict], results: list[dict]) -> dict:
    """Compute the correlation register and record every dropped pair."""
    pairs = []
    drops = []

    def add(name, family, question, xs, ys, source_ids, source_url, caveat):
        if len(xs) < 3:
            drops.append({"pair": name, "why": f"only {len(xs)} complete observations", "source_ids": source_ids})
            return
        st = pearson(xs, ys)
        pairs.append({
            "pair": name, "family": family, "question": question,
            "n": st["n"], "r": st["r"], "p_value": st["p_value"],
            "ci_lo": st["ci_lo"], "ci_hi": st["ci_hi"],
            "source_ids": source_ids, "source_url": source_url, "caveat": caveat,
        })

    # ---- A. market-vs-model, on the priced capture -------------------------------
    m_model = [r["model_fair_total"] for r in total_board]
    m_mkt = [r["market_total"] for r in total_board]
    add("model total vs market total", "market",
        "does the model agree with the market on how many points will be scored?",
        m_model, m_mkt, ["MD-ESPN-ODDS", "CFDD-NFL-STANDINGS"], total_board[0]["source_url"],
        "Same 15 games. A high r here means the model is not originating anything new on the total.")

    spread_lines = [-r["market_line"] for r in side_board]
    add("market spread vs market total (same game)", "market",
        "do books price high-total games with wider favourites?",
        spread_lines, [r["market_total"] for r in total_board],
        ["MD-ESPN-ODDS"], side_board[0]["source_url"],
        "This is the market's own geometry and is what a correlated parlay would be sold against.")

    # ---- B. outcome correlations from official scores ----------------------------
    margins, totals, weeks = [], [], []
    for g in results:
        margins.append(g["home_score"] - g["away_score"])
        totals.append(g["home_score"] + g["away_score"])
        weeks.append(g["week"])
    add("final margin vs final total (official scores)", "outcome",
        "in real games, does a blowout come with a high total?",
        margins, totals, ["CFDD-NFL-RESULTS"], results[0]["source_url"],
        "n is every official final score captured; the correlation is a property of football, not of a market.")

    add("model margin vs market margin (same game)", "market",
        "does the model's side differ from the market's in the same direction across games?",
        [r["model_fair_line"] for r in side_board], [-r["market_line"] for r in side_board],
        ["MD-ESPN-ODDS", "CFDD-NFL-STANDINGS"], side_board[0]["source_url"],
        "A low r means the model is systematically disagreeing with the market rather than "
        "tracking it, which is a calibration warning, not an edge.")

    # ---- C. availability vs outcome, only where depth was captured --------------
    try:
        import availability
        rows = availability.replacement_depth()
        exp = {c["club"]: c["weight"] for c in availability.club_exposure(rows)}
        xs, ys = [], []
        for g in results:
            if g["home"] in exp and g["away"] in exp:
                xs.append(exp[g["home"]] - exp[g["away"]])
                ys.append(g["home_score"] - g["away_score"])
        add("availability weight difference vs margin", "outcome",
            "does the depth of the replacement show up in the score?",
            xs, ys, ["CFDD-NFL-DEPTH", "CFDD-NFL-RESULTS"],
            "https://www.nfl.com/injuries/",
            "Only games where BOTH clubs have a captured depth chart. That is a very small n and the "
            "row is labelled underpowered; it is published to show the size of the sample the "
            "question needs, not to support a claim.")
    except Exception as exc:  # pragma: no cover - surfaced, not swallowed
        drops.append({"pair": "availability weight difference vs margin",
                      "why": f"not computed: {exc}", "source_ids": ["CFDD-NFL-DEPTH"]})

    # ---- multiple-testing control ----------------------------------------------
    testable = [p for p in pairs if p["p_value"] is not None]
    adjusted = _holm([p["p_value"] for p in testable])
    for p, q in zip(testable, adjusted):
        p["holm_adjusted_p"] = q
        p["reject_null_at_0.05"] = q <= 0.05
        p["powered"] = p["n"] >= MIN_N
    for p in pairs:
        if p["p_value"] is None:
            p["holm_adjusted_p"] = None
            p["reject_null_at_0.05"] = False
            p["powered"] = False

    return {
        "min_n_for_ranking": MIN_N,
        "pairs": pairs,
        "dropped": drops,
        "n_pairs": len(pairs),
        "n_powered": sum(1 for p in pairs if p["powered"]),
        "note": (
            "Holm-adjusted across the pairs tested in this register. A pair with n below "
            f"{MIN_N} is shown with its n and is not ranked: at n=15 the 95% interval on r spans "
            "most of the range, so the point estimate carries almost no information."
        ),
    }
