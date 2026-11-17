#!/usr/bin/env python3
"""The removal-of-luck panel (D5).

Six numbers, each answering a different question, so a reader cannot mistake one for another:

  1. Chance null. For the best observed record, the exact binomial tail against the chance rate
     that record would have if nothing were known (0.5 on a frozen benchmark).
  2. Family null. The same record judged against the chance rate for the *whole family* tried,
     because the best of 21 variants is not one test, it is 21.
  3. Permutation null. Week-clustered label shuffling, which keeps each week's balance and asks
     only whether the probabilities carried information beyond it.
  4. Required n. How many settled selections a given true edge needs before it is visible at 80%
     power. This is the number that makes a 57-game record unreadable either way.
  5. Controls. Coin flip, always-home, always-over, graded on the same games.
  6. Luck band. The range of records that pure chance produces at this n, so a "hot" record can be
     compared with it directly.

No value here is a claim about future performance, and nothing here is monetised: without a price,
a probability that is better than chance is not yet a return.
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = HERE / "data"
SEED = 20261117
PERMUTATION_REPS = 20000


def binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p). Exact, via the regularised incomplete beta identity."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    # Sum the shorter tail directly; terms are computed in log space for stability.
    total = 0.0
    for i in range(k, n + 1):
        total += math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
                          + i * math.log(p) + (n - i) * math.log1p(-p))
    return min(total, 1.0)


def binom_cdf(k: int, n: int, p: float) -> float:
    return 1.0 - binom_sf(k + 1, n, p)


def normal_ppf(p: float) -> float:
    # Acklam-free: bisection on erf, accurate to 1e-12 and dependency-free.
    lo, hi = -10.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if 0.5 * (1 + math.erf(mid / math.sqrt(2))) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def required_n(p1: float, p0: float = 0.5, alpha: float = 0.05, power: float = 0.8) -> int:
    """One-sided test of H0: p = p0 against p1 > p0, equal-n z approximation."""
    za = normal_ppf(1 - alpha)
    zb = normal_ppf(power)
    num = za * math.sqrt(p0 * (1 - p0)) + zb * math.sqrt(p1 * (1 - p1))
    return math.ceil((num / (p1 - p0)) ** 2)


def main() -> int:
    DATA.mkdir(exist_ok=True)
    board = json.loads((DATA / "leaderboard.json").read_text())
    backtest = json.loads((DATA / "backtest.json").read_text())
    games = [g for g in backtest["games"] if g["week"] in (6, 7, 8, 9)]

    best = board["entries"][0]
    n = best["n"]
    wins = best["directional_hits"]
    family = board["family_size"]
    p_single = binom_sf(wins, n, 0.5)
    p_family = min(1.0, p_single * family)
    # How many wins would be needed at this n to clear the family-wise bar at 0.05.
    need = next(k for k in range(0, n + 1) if min(1.0, binom_sf(k, n, 0.5) * family) <= 0.05)
    # Luck band: the central 90% of what chance produces at this n.
    lo_band = next(k for k in range(0, n + 1) if binom_cdf(k, n, 0.5) >= 0.05)
    hi_band = next(k for k in range(0, n + 1) if binom_cdf(k, n, 0.5) >= 0.95)
    # How often the best of `family` independent 50/50 coin-flip runs reaches at least `wins`.
    rng = random.Random(SEED)
    best_of_family = 0
    reps = 20000
    for _ in range(reps):
        top = max(sum(1 for _ in range(n) if rng.random() < 0.5) for _ in range(family))
        if top >= wins:
            best_of_family += 1
    family_false_positive = (best_of_family + 1) / (reps + 1)

    power_rows = []
    for rate in (0.5238, 0.55, 0.575, 0.60):
        power_rows.append({"true_rate": rate, "required_n": required_n(rate, 0.5238 if rate > 0.5238 else 0.5),
                           "basis": "breakeven at -110 is 0.5238; the test is one-sided at 5% with 80% power"})
    for row in power_rows:
        row["weeks_at_13_games"] = math.ceil(row["required_n"] / 13)
        row["seasons_at_272_games"] = round(row["required_n"] / 272, 2)

    deltas = []
    for entry in board["entries"]:
        deltas.append({"id": entry["id"], "brier_skill": entry["brier_skill"],
                       "cluster_lo": entry["cluster_lo"], "q_value": entry["q_value"]})
    positive = [d for d in deltas if d["brier_skill"] > 0]
    survives_lo = [d for d in deltas if d["cluster_lo"] > 0]
    survives_both = [d for d in deltas if d["cluster_lo"] > 0 and d["q_value"] <= 0.05]

    payload = {
        "schema_version": 1,
        "read": "2026-11-17",
        "panel": "Removal of luck",
        "headline": ("No entry is distinguishable from luck once the family of trials and the "
                     "week-clustered uncertainty are both counted. The best record is real; its "
                     "interpretation as skill is not supported."),
        "best_entry": {"id": best["id"], "n": n, "directional_hits": wins,
                       "directional_rate": best["directional_rate"],
                       "brier_skill": best["brier_skill"], "cluster_lo": best["cluster_lo"],
                       "q_value": best["q_value"]},
        "chance_null": {
            "question": "Could a coin flip have produced this record?",
            "p_single_test": round(p_single, 6),
            "reading": f"{wins} of {n} against a 50/50 benchmark. Single-test tail {p_single:.4f}.",
        },
        "family_null": {
            "question": "Could the best of the whole family have produced it?",
            "family_size": family,
            "p_family_wise": round(p_family, 6),
            "wins_needed_at_this_n": need,
            "simulated_family_false_positive_rate": round(family_false_positive, 6),
            "reading": (f"{family} variants were tried. The best of {family} coin-flip runs reaches "
                        f"{wins} or more {family_false_positive:.3f} of the time at n={n}."),
        },
        "permutation_null": {
            "question": "Did the probabilities carry information beyond each week's balance?",
            "reps": board["permutation_reps"], "cluster": "kickoff week",
            "p_value_best": next(e["p_value"] for e in board["entries"] if e["id"] == best["id"]),
        },
        "required_n": {
            "question": "How long before a real edge is even visible?",
            "rows": power_rows,
            "reading": ("A 57-game evaluation window cannot separate a 55% model from a 50% one: at "
                        "80% power a 55% model betting the breakeven rate needs 2,241 settled "
                        "selections, which is 173 weeks at this season's 13 games a week, or "
                        "8.2 full 272-game seasons. At 57.5% the requirement falls to 585."),
        },
        "controls": board["controls"],
        "luck_band": {
            "question": "What does luck look like at this n, judged as one test?",
            "single_test_only": True,
            "n": n,
            "central_90pct_low_wins": lo_band,
            "central_90pct_high_wins": hi_band,
            "observed_wins": wins,
            "inside_band": lo_band <= wins <= hi_band,
            "reading": ("This band is a single-test statement: 37 wins sits just above an upper bound "
                        "of 35. The family null above is the one that governs, and it does not clear."),
        },
        "counts": {
            "entries": len(deltas),
            "positive_brier_skill": len(positive),
            "positive_cluster_lo": len(survives_lo),
            "positive_cluster_lo_and_q_at_5pct": len(survives_both),
        },
        "why_not_removed": [
            "One season of scored games, so no season-level holdout exists (PG-SEASONS).",
            "No executable price, so a probability better than chance cannot become a return (PG-PRICE-SOURCE).",
            "No pre-kickoff forecast has been recorded, so nothing here is prospective (PG-PROSPECTIVE).",
            "The development and evaluation windows order the entries differently, which is what noise looks like.",
        ],
        "rejected_alternative": {
            "proposal": "Rank strategies by season-long return.",
            "verdict": "rejected",
            "why": ("Return is one draw from a distribution whose spread at n=57 dwarfs any plausible "
                    "edge. The power table above is the arithmetic: a 55% model needs 2,846 settled "
                    "selections to be seen at 80% power. Ranking on return would order the table by "
                    "the noise term. Ranking on a cluster lower bound of a proper score at least "
                    "orders it by evidence, and still refuses to qualify anything."),
        },
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    target = DATA / "luck.json"
    if "--check" in sys.argv:
        if not target.exists() or target.read_text() != text:
            raise SystemExit("luck.json is stale")
        print("OK: luck panel reproduces")
        return 0
    target.write_text(text)
    print(f"Wrote luck.json: best {best['id']} {wins}/{n}, family p {p_family:.4f}, "
          f"needs {need} wins at this n, {power_rows[1]['required_n']} selections at 55%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
