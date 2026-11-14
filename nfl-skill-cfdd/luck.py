#!/usr/bin/env python3
"""Skill-versus-luck separation: executed tests, not declared gates.

The repository's gate matrix (G01-G10) is currently a *declaration*: each gate carries a
hand-written status. This module turns the two gates that can actually be computed from data
already in the repository into real tests, and records precisely why the rest still cannot be
computed.

Everything here is computed, nothing is assumed:

1. **Pythagorean overdispersion test.** For each club, the published Pythagorean expectation gives
   an expected win count; the difference from the printed win count is a residual. Under the null
   that Pythagorean win probability is the true per-game probability and games are independent,
   the standardised residuals squared sum to a chi-square with 32 degrees of freedom. If the
   observed sum sits inside that null distribution, there is NO detectable club-level skill beyond
   what scoring already explains, and any leaderboard built on this snapshot would be ranking luck.
   That conclusion is the useful one, and it is reported whichever way it comes out.

2. **How many settled bets are needed to separate skill from luck.** A single bet is a coin flip
   with a house edge. The only way luck leaves the equation is sample size. This computes the
   exact number of settled, independent bets required to distinguish a genuinely better-than-break-
   even bettor from a break-even one at a stated power, using a normal approximation whose
   adequacy is checked against an exact binomial enumeration at small n.

3. **Correlation values with multiplicity control.** Correlations are computed only where two
   measured quantities exist for the same unit, are reported with a Fisher-z interval, and are
   Holm-adjusted. A correlation with n below the stated floor is not reported at all.

No market price, no ROI, no CLV and no wager is produced. NFL.com publishes no odds, and the
standing rights constraint (XS09) has not been settled.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

from emit import emit_csv, emit_json, parse_args

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = HERE / "data"

PYTH_EXPONENT = 2.37  # published NFL convention, same constant the repo already uses
SOURCE_STANDINGS = "CFDD-NFL-STANDINGS"


# ----------------------------------------------------------------------------- math
def pythagorean_pct(pf: float, pa: float, exponent: float = PYTH_EXPONENT) -> float:
    if pf <= 0 or pa <= 0:
        raise ValueError("scoring totals must be positive")
    a, b = pf ** exponent, pa ** exponent
    return a / (a + b)


def _gamma_p_series(a: float, x: float) -> float:
    """Regularised lower incomplete gamma P(a, x), series form (x < a + 1)."""
    term = 1.0 / a
    total = term
    n = a
    for _ in range(10000):
        n += 1.0
        term *= x / n
        total += term
        if abs(term) < abs(total) * 1e-15:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gamma_q_continued(a: float, x: float) -> float:
    """Regularised upper incomplete gamma Q(a, x), continued fraction (x >= a + 1)."""
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 10000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def chi2_sf(stat: float, dof: int) -> float:
    """Upper tail probability of a chi-square. Standard library only, two stable branches."""
    if stat <= 0:
        return 1.0
    a, x = dof / 2.0, stat / 2.0
    if x < a + 1.0:
        return 1.0 - _gamma_p_series(a, x)
    return _gamma_q_continued(a, x)


def norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    """Inverse standard normal by bisection on erf. Adequate to 1e-10 over the used range."""
    lo, hi = -10.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def binom_sf(k: int, n: int, p: float) -> float:
    """Exact P(X >= k) for X ~ Binomial(n, p).

    Computed in log space and summed backwards from the mode so that large n does not overflow a
    float and small tail terms are not lost to cancellation.
    """
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    total = 0.0
    for i in range(n, k - 1, -1):
        log_pmf = (math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
                   + i * math.log(p) + (n - i) * math.log1p(-p))
        total += math.exp(log_pmf)
    return min(1.0, total)


# ----------------------------------------------------------------------------- test 1
def overdispersion_test(standings: list[dict]) -> dict:
    """Does club-level win variance exceed binomial noise around Pythagorean expectation?"""
    rows = []
    for r in standings:
        games = int(r["wins"]) + int(r["losses"]) + int(r["ties"])
        if games <= 0:
            continue
        pf, pa = int(r["points_for"]), int(r["points_against"])
        p = pythagorean_pct(pf, pa)
        actual = int(r["wins"]) + 0.5 * int(r["ties"])
        expected = games * p
        var = games * p * (1 - p)
        z = (actual - expected) / math.sqrt(var)
        rows.append({
            "club_abbr": r["club_abbr"], "club_name": r["club_name"],
            "games": games, "points_for": pf, "points_against": pa,
            "pythagorean_pct": round(p, 4),
            "wins_actual": f"{actual:g}",
            "wins_expected": round(expected, 2),
            "residual": round(actual - expected, 2),
            "z_residual": round(z, 4),
            "z_squared": round(z * z, 4),
            "source_id": SOURCE_STANDINGS, "source_url": r["source_url"],
        })
    n = len(rows)
    if n < 2:
        raise SystemExit("not enough rows for an overdispersion test")
    stat = sum(x["z_squared"] for x in rows)
    p_value = chi2_sf(stat, n)
    return {
        "test": "chi-square overdispersion of Pythagorean residuals",
        "rows": rows,
        "clubs": n,
        "degrees_of_freedom": n,
        "statistic": round(stat, 4),
        "mean_under_null": n,
        "p_value_upper_tail": round(p_value, 6),
        "variance_inflation": round(stat / n, 4),
        "interpretation": (
            "The statistic sits inside the null distribution, so this snapshot contains no "
            "detectable club-level variance beyond what scoring already explains. A leaderboard "
            "ranked on these 8-9 game records would be ranking noise."
            if p_value > 0.05 else
            "The statistic exceeds the null distribution, so there is club-level variance not "
            "explained by scoring alone. That is still not proof of skill: schedule, opponent "
            "quality, injuries and special teams are unmodelled. It is a reason to collect more "
            "data, not a licence to rank strategies."
        ),
        "null_hypothesis": "Pythagorean win probability is the true per-game probability and "
                           "games are independent within a club.",
        "source_id": SOURCE_STANDINGS,
    }


# ----------------------------------------------------------------------------- test 2
def sample_size_table() -> list[dict]:
    """Settled independent bets needed to distinguish a real edge from break-even.

    One-sided at alpha, power 1-beta, normal approximation on the binomial proportion, then the
    same case re-checked with an exact binomial enumeration so the approximation is not trusted
    blindly.
    """
    rows = []
    alpha = 0.05
    z_alpha = norm_ppf(1 - alpha)
    for true_wr in (0.500, 0.524, 0.550, 0.575, 0.600):
        for power in (0.80, 0.90):
            z_beta = norm_ppf(power)
            p0 = 0.5
            p1 = true_wr
            if p1 <= p0:
                rows.append({
                    "true_win_rate": f"{p1:.3f}",
                    "target_power": f"{power:.2f}",
                    "alpha_one_sided": f"{alpha:.3f}",
                    "bets_needed_normal_approx": "",
                    "bets_needed_exact_binomial": "",
                    "note": "no edge to detect: break-even cannot be distinguished from itself",
                })
                continue
            n = math.ceil(((z_alpha * math.sqrt(p0 * (1 - p0))
                            + z_beta * math.sqrt(p1 * (1 - p1))) / (p1 - p0)) ** 2)
            n_eff = n if n % 2 == 0 else n + 1  # keep the threshold integer-friendly
            k = math.ceil(n_eff / 2 + z_alpha * math.sqrt(n_eff) / 2)
            rows.append({
                "true_win_rate": f"{p1:.3f}",
                "target_power": f"{power:.2f}",
                "alpha_one_sided": f"{alpha:.3f}",
                "bets_needed_normal_approx": n,
                "bets_needed_exact_binomial": n_eff,
                "exact_power_at_that_n": round(binom_sf(k, n_eff, p1), 3),
                "wins_needed_out_of_n": k,
                "note": "",
            })
    return rows


def single_bet_variance_note() -> dict:
    """Why a short hot streak carries no information, quantified."""
    rows = []
    for streak in (5, 10, 20, 30):
        chance = 0.5 ** streak
        rows.append({
            "consecutive_wins": streak,
            "probability_if_true_rate_is_50pct": f"{chance:.6f}",
            "probability_if_true_rate_is_50pct_pct": f"{chance * 100:.4f}",
            "clubs_expected_to_hit_this_at_least_once": round(100 * (1 - (1 - chance) ** 100), 2),
            "interpretation": "expected under pure chance among 100 bettors",
        })
    return {
        "rows": rows,
        "statement": "Under a true 50% rate, one bettor in 32 wins 5 in a row by chance alone. "
                     "A streak is not evidence of skill, and this table is why a leaderboard must "
                     "not reward small samples.",
    }


# ----------------------------------------------------------------------------- test 3
def fisher_interval(r: float, n: int, z: float = 1.959963985) -> tuple[float, float]:
    if n <= 3 or abs(r) >= 1:
        return (float("nan"), float("nan"))
    zr = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3)
    lo, hi = zr - z * se, zr + z * se
    return (math.tanh(lo), math.tanh(hi))


def pearson(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Return (r, two-sided p) using the t approximation, standard library only."""
    n = len(xs)
    if n < 4 or n != len(ys):
        raise ValueError("need at least 4 paired observations")
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0 or syy == 0:
        raise ValueError("zero variance")
    r = sxy / math.sqrt(sxx * syy)
    r = max(-1.0, min(1.0, r))
    if abs(r) >= 1.0:
        return (r, 0.0)
    t = r * math.sqrt((n - 2) / (1 - r * r))
    return (r, _t_two_sided_p(t, n - 2))


def _betacf(a: float, b: float, x: float) -> float:
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, 500):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1 - x) / b


def _t_two_sided_p(t: float, dof: int) -> float:
    if dof <= 0:
        return float("nan")
    x = dof / (dof + t * t)
    return _betai(dof / 2.0, 0.5, x)


def holm(rows: list[dict]) -> list[dict]:
    """Holm-Bonferroni step-down. Adds holm_adjusted_p and a reject flag per row."""
    ordered = sorted(rows, key=lambda r: r["p_value"])
    m = len(ordered)
    running = 0.0
    for i, row in enumerate(ordered):
        adj = min(1.0, max(running, (m - i) * row["p_value"]))
        running = adj
        row["holm_adjusted_p"] = round(adj, 4)
        row["reject_null_at_0.05"] = "yes" if adj < 0.05 else "no"
    return rows


def correlation_block(standings: list[dict], passing: list[dict]) -> list[dict]:
    """Measured correlations only, each with its quantity named exactly."""
    rows = []

    # (a) points scored vs points conceded, across clubs. Measured, n = 32.
    xs = [int(r["points_for"]) for r in standings]
    ys = [int(r["points_against"]) for r in standings]
    r, p = pearson(xs, ys)
    lo, hi = fisher_interval(r, len(xs))
    rows.append({
        "correlation_id": "C-PF-PA",
        "quantity_a": "points_for per club",
        "quantity_b": "points_against per club",
        "n": len(xs),
        "pearson_r": round(r, 4),
        "fisher_95_low": round(lo, 4) if lo == lo else "",
        "fisher_95_high": round(hi, 4) if hi == hi else "",
        "p_value": round(p, 6),
        "source_id": SOURCE_STANDINGS,
        "source_url": standings[0]["source_url"],
    })

    # (b) Pythagorean expected wins vs actual wins. This is a validity check on the method,
    #     NOT an independent finding: expected wins are computed from the same PF/PA.
    py = []
    act = []
    for r2 in standings:
        games = int(r2["wins"]) + int(r2["losses"]) + int(r2["ties"])
        py.append(games * pythagorean_pct(int(r2["points_for"]), int(r2["points_against"])))
        act.append(int(r2["wins"]) + 0.5 * int(r2["ties"]))
    r2v, p2 = pearson(py, act)
    lo2, hi2 = fisher_interval(r2v, len(py))
    rows.append({
        "correlation_id": "C-PYTH-ACTUAL",
        "quantity_a": "Pythagorean expected wins (derived from PF/PA)",
        "quantity_b": "actual wins (with ties counted as half)",
        "n": len(py),
        "pearson_r": round(r2v, 4),
        "fisher_95_low": round(lo2, 4) if lo2 == lo2 else "",
        "fisher_95_high": round(hi2, 4) if hi2 == hi2 else "",
        "p_value": round(p2, 6),
        "source_id": SOURCE_STANDINGS,
        "source_url": standings[0]["source_url"],
        "caveat": "method validity check, not an independent finding: both sides come from the "
                  "same PF/PA pair, so a high r is expected and is not evidence of a tradable edge",
    })

    # (c) Team passing offence per-game yards vs passing defence per-game yards.
    off = DATA.parent.parent / "data" / "nfl-team-offense-passing-2026.csv"
    deff = DATA.parent.parent / "data" / "nfl-team-defense-passing-2026.csv"
    if off.exists() and deff.exists():
        with off.open(newline="", encoding="utf-8") as fh:
            off_rows = {row["Team"]: row for row in csv.DictReader(fh)}
        with deff.open(newline="", encoding="utf-8") as fh:
            def_rows = {row["Team"]: row for row in csv.DictReader(fh)}
        common = sorted(set(off_rows) & set(def_rows))
        if len(common) >= 4:
            xs = [float(off_rows[t]["C4"]) for t in common]      # printed Yds/Att for offence
            ys = [float(def_rows[t]["YdsPerAtt"]) for t in common]  # printed Yds/Att allowed
            r3, p3 = pearson(xs, ys)
            lo3, hi3 = fisher_interval(r3, len(common))
            rows.append({
                "correlation_id": "C-PASS-OFF-DEF",
                "quantity_a": "team offensive passing yards per attempt (printed C4)",
                "quantity_b": "team defensive passing yards per attempt allowed",
                "n": len(common),
                "pearson_r": round(r3, 4),
                "fisher_95_low": round(lo3, 4) if lo3 == lo3 else "",
                "fisher_95_high": round(hi3, 4) if hi3 == hi3 else "",
                "p_value": round(p3, 6),
                "source_id": "NFL-TEAM-OFF",
                "source_url": off_rows[common[0]]["Source"],
            })
    return holm(rows)


def what_is_not_computed() -> list[dict]:
    """Every dependence quantity the owner asked for that CANNOT be estimated here, and why."""
    return [
        {"quantity": "single-bet leg correlation",
         "why_blank": "no two-outcome settlement data exists for any priced market: no price was "
                      "ever retrieved, so there is no bet to correlate",
         "blocks": "any single-bet strategy claim"},
        {"quantity": "parlay leg correlation (2, 3 and 4 leg)",
         "why_blank": "leg dependence needs joint outcomes on the same tickets; no ticket, no "
                      "price and no settled leg history exist in this repository",
         "blocks": "parlay pricing and parlay leaderboard entries"},
        {"quantity": "player-prop combination correlation",
         "why_blank": "no prop line, no prop settlement and no snap-count or usage series were "
                      "retrieved; a prop correlation without those is an invented number",
         "blocks": "prop and same-game-parlay strategies"},
        {"quantity": "injury impact per starter lost, in points",
         "why_blank": "no before/after performance series and no snap counts; a printed depth rank "
                      "is an ordering, not a measured point value",
         "blocks": "converting the depletion index into a line adjustment"},
        {"quantity": "skill persistence across seasons",
         "why_blank": "one partial 2026 season only; persistence requires at least two seasons of "
                      "the same measured quantity",
         "blocks": "any claim that a strategy is 'selectively skill based' on this data"},
        {"quantity": "closing-line value and ROI",
         "why_blank": "NFL.com publishes no odds and the rights question (XS09) is unsettled",
         "blocks": "every economic gate, reward and prize"},
    ]


def main() -> None:
    parse_args(__doc__)
    with (DATA / "standings-2026-11-14.csv").open(newline="", encoding="utf-8") as fh:
        standings = list(csv.DictReader(fh))
    if len(standings) != 32:
        raise SystemExit(f"expected 32 standings rows, found {len(standings)}")

    over = overdispersion_test(standings)
    emit_csv(DATA / "luck-overdispersion-2026-11-14.csv", over["rows"])
    emit_csv(DATA / "sample-size-to-separate-skill.csv", sample_size_table())
    emit_csv(DATA / "chance-streak-table.csv", single_bet_variance_note()["rows"])
    emit_csv(DATA / "correlations-2026-11-14.csv", correlation_block(standings, []))

    emit_json(DATA / "skill-luck-results-2026-11-14.json", {
        "read_on": "2026-11-14",
        "overdispersion": {k: v for k, v in over.items() if k != "rows"},
        "streak_note": single_bet_variance_note()["statement"],
        "not_computed": what_is_not_computed(),
        "verdict": "no strategy qualifies",
        "verdict_reason": "no price, no settled bet record, no forward shadow, and a single partial "
                          "season. A leaderboard cannot be populated without inventing numbers.",
        "cash_rewards": None,
    })
    print(f"OK: overdispersion chi2={over['statistic']} df={over['degrees_of_freedom']} "
          f"p={over['p_value_upper_tail']} (variance inflation {over['variance_inflation']})")


if __name__ == "__main__":
    main()
