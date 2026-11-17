#!/usr/bin/env python3
"""Proper-score leaderboard with cluster lower bounds and multiplicity control (D4).

Ranking rule (fixed in the registration and enforced here):

  * Divisions are separate: singles, game parlays, same-game parlays, prop combos.
  * Within a division, entries are ordered by the lower bound of Brier skill, never by win rate,
    never by return.
  * The lower bound is a week-clustered bootstrap percentile, because games inside one kickoff
    week share a league state and are not independent draws from the same population.
  * Every entry's p-value is adjusted by Benjamini-Hochberg across the *whole* family tried, and
    the family size is published beside the q-value.
  * Staking fields exist only to be shown and can never move a rank: the rank function raises if a
    staking field is even present in the row it is asked to order.

Also built here:
  * the controls (coin flip, always-home, always-over) so a naive reader can see what luck alone
    looks like;
  * the 1st-4th string matchup matrix inputs are *not* built here (see the availability page).

Output: data/leaderboard.json
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

DEV_WEEKS = (2, 3, 4, 5)
EVAL_WEEKS = (6, 7, 8, 9)
BOOTSTRAP_REPS = 4000
BOOTSTRAP_SEED = 20261117
PERMUTATION_REPS = 20000


def brier(prob: float, outcome: bool) -> float:
    return (prob - (1.0 if outcome else 0.0)) ** 2


def log_loss(prob: float, outcome: bool) -> float:
    p = min(max(prob, 1e-9), 1 - 1e-9)
    return -math.log(p) if outcome else -math.log(1 - p)


def cluster_skill(rows: list[dict], model: str, market: str) -> dict:
    """Brier skill of a model against the 0.5 benchmark, clustered by kickoff week."""
    key = {"side": ("p_home_cover", "home_covered"), "total": ("p_over", "went_over"),
           "moneyline": ("p_home_win", "home_won")}[market]
    pkey, okey = key
    per_game = []
    for r in rows:
        p = r["forecasts"][model][pkey]
        o = r[okey]
        per_game.append((r["week"], p, o))
    # Brier skill against a 50/50 forecast: BS_ref = 0.25 for a Bernoulli outcome.
    def skill(subset):
        bs = sum(brier(p, o) for _, p, o in subset) / len(subset)
        return (0.25 - bs) / 0.25
    total = skill(per_game)
    weeks = sorted({w for w, _, _ in per_game})
    by_week = {w: [x for x in per_game if x[0] == w] for w in weeks}
    # Delete-one-week jackknife then a percentile bootstrap over weeks: both answer "could one
    # week be carrying this?" without pretending the games are independent.
    jack = []
    for w in weeks:
        subset = [x for x in per_game if x[0] != w]
        jack.append(skill(subset))
    rng = random.Random(BOOTSTRAP_SEED)
    boot = []
    for _ in range(BOOTSTRAP_REPS):
        pick = [rng.choice(weeks) for _ in weeks]
        subset = [x for w in pick for x in by_week[w]]
        boot.append(skill(subset))
    boot.sort()
    lo = boot[int(0.025 * len(boot))]
    hi = boot[int(0.975 * len(boot)) - 1]
    hits = sum(1 for _, p, o in per_game if (p > 0.5) == o)
    return {
        "model": model, "market": market, "n": len(per_game),
        "weeks": len(weeks), "brier": round(0.25 * (1 - total), 6),
        "brier_skill": round(total, 6),
        "cluster_lo": round(lo, 6), "cluster_hi": round(hi, 6),
        "jackknife_min": round(min(jack), 6), "jackknife_max": round(max(jack), 6),
        "jackknife_worst_week": weeks[jack.index(min(jack))],
        "directional_hits": hits, "directional_rate": round(hits / len(per_game), 6),
        "mean_log_loss": round(sum(log_loss(p, o) for _, p, o in per_game) / len(per_game), 6),
    }


def permutation_p(rows: list[dict], model: str, market: str, seeds: int = PERMUTATION_REPS) -> float:
    """Exact-ish null: shuffle the outcome labels inside each week, keeping the probabilities.

    Shuffling inside a week preserves the week's outcome base rate, so the test asks whether the
    model's probabilities carried information beyond that week's balance — not whether the season
    happened to favour home sides.
    """
    key = {"side": ("p_home_cover", "home_covered"), "total": ("p_over", "went_over"),
           "moneyline": ("p_home_win", "home_won")}[market]
    pkey, okey = key
    weeks: dict[int, list[tuple[float, bool]]] = {}
    for r in rows:
        weeks.setdefault(r["week"], []).append((r["forecasts"][model][pkey], r[okey]))

    def statistic(groups):
        bs = [brier(p, o) for g in groups.values() for p, o in g]
        return sum(bs) / len(bs)

    observed = statistic(weeks)
    rng = random.Random(BOOTSTRAP_SEED + 1)
    hits = 0
    outcomes = {w: [o for _, o in g] for w, g in weeks.items()}
    probs = {w: [p for p, _ in g] for w, g in weeks.items()}
    for _ in range(seeds):
        shuffled = {}
        for w in weeks:
            labels = outcomes[w][:]
            rng.shuffle(labels)
            shuffled[w] = list(zip(probs[w], labels))
        if statistic(shuffled) <= observed:
            hits += 1
    return (hits + 1) / (seeds + 1)


def bh(pvalues: list[float]) -> list[float]:
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    q = [0.0] * m
    running = 1.0
    for rank, idx in reversed(list(enumerate(order, start=1))):
        running = min(running, pvalues[idx] * m / rank)
        q[idx] = min(running, 1.0)
    return q


def controls(rows: list[dict], market: str) -> list[dict]:
    out = []
    for name, prob in (("Coin flip", 0.5), ("Always home side", 1.0), ("Never home side", 0.0),
                       ("Always over", 1.0), ("Always under", 0.0)):
        if market in ("total",) and name in ("Always home side", "Never home side"):
            continue
        if market in ("side", "moneyline") and name in ("Always over", "Always under"):
            continue
        key = {"side": "home_covered", "total": "went_over", "moneyline": "home_won"}[market]
        bs = sum(brier(prob, r[key]) for r in rows) / len(rows)
        hits = sum(1 for r in rows if (prob > 0.5) == r[key])
        out.append({"name": name, "market": market, "n": len(rows),
                    "brier": round(bs, 6),
                    "brier_skill": round((0.25 - bs) / 0.25, 6),
                    "directional_rate": round(hits / len(rows), 6)})
    return out


def rank_entries(entries: list[dict]) -> list[dict]:
    """Order by the cluster lower bound. A staking field present anywhere is a hard failure."""
    staking_fields = {"roi", "units", "stake", "profit", "payout", "clv", "closing_line_value"}
    for e in entries:
        bad = staking_fields & set(e)
        if bad:
            raise SystemExit(f"staking field(s) {sorted(bad)} reached the rank function")
    return sorted(entries, key=lambda e: (-e["cluster_lo"], -e["brier_skill"], e["id"]))


def build() -> dict:
    backtest = json.loads((DATA / "backtest.json").read_text())
    registration = json.loads((DATA / "registration.json").read_text())
    games = backtest["games"]
    dev = [g for g in games if g["week"] in DEV_WEEKS]
    ev = [g for g in games if g["week"] in EVAL_WEEKS]
    models = [m["id"] for m in backtest["models"]]

    scored = []
    for model in models:
        for market in ("side", "total", "moneyline"):
            s = cluster_skill(ev, model, market)
            s["p_value"] = round(permutation_p(ev, model, market), 6)
            s["id"] = f"{model}-{market.upper()}"
            s["name"] = next(m["name"] for m in backtest["models"] if m["id"] == model)
            s["division"] = "singles"
            s["window"] = "evaluation weeks 6-9"
            scored.append(s)
    # Multiplicity across the whole family actually tried in the evaluation window.
    qs = bh([s["p_value"] for s in scored])
    for s, q in zip(scored, qs):
        s["q_value"] = round(q, 6)
    scored = rank_entries(scored)
    for i, s in enumerate(scored, start=1):
        s["rank"] = i
        s["qualified"] = False
        s["qualified_reason"] = "V7 (no executable price) and V8 (no prospective record) cannot pass today."

    # Development-window score, published beside the evaluation score so a reader can see whether
    # the ranking is stable or whether it is one window's accident.
    for s in scored:
        model, market = s["id"].rsplit("-", 1)
        d = cluster_skill(dev, model, market.lower())
        s["dev_brier_skill"] = d["brier_skill"]
        s["dev_cluster_lo"] = d["cluster_lo"]

    # Concordance between the two windows: does the best development entry stay on top?
    dev_order = [x["id"] for x in sorted(
        [{"id": s["id"], "dev": s["dev_brier_skill"]} for s in scored], key=lambda x: -x["dev"])]
    ev_order = [s["id"] for s in scored]
    agree = sum(1 for a, b in zip(dev_order, ev_order) if a == b)

    divisions = [
        {"id": "singles", "name": "Singles", "entries": len(scored),
         "status": "open — graded on the official result with a frozen benchmark"},
        {"id": "game-parlays", "name": "Game parlays (cross-game)", "entries": 0,
         "status": "closed — no operator void/push rule is registered (V7)"},
        {"id": "same-game-parlays", "name": "Same-game parlays", "entries": 0,
         "status": "closed — a directly validated joint probability is required and does not exist"},
        {"id": "prop-combos", "name": "Player prop combos", "entries": 0,
         "status": "closed — no player-level prop outcome is captured (PG-PROPS)"},
    ]

    return {
        "schema_version": 1,
        "registration_hash": backtest["registration_hash"],
        "rank_basis": ("cluster lower bound on Brier skill against a frozen 0.5 benchmark; "
                       "win rate and return are displayed and never order the table"),
        "family_size": len(scored),
        "bootstrap": {"reps": BOOTSTRAP_REPS, "seed": BOOTSTRAP_SEED, "cluster": "kickoff week"},
        "permutation_reps": PERMUTATION_REPS,
        "fdr_level": 0.05,
        "divisions": divisions,
        "entries": scored,
        "controls": controls(ev, "side") + controls(ev, "total") + controls(ev, "moneyline"),
        "window_concordance": {
            "same_order_positions": agree,
            "of": len(ev_order),
            "development_order": dev_order,
            "evaluation_order": ev_order,
            "reading": ("If the two windows disagree, the evaluation ranking is a property of weeks 6-9 "
                        "and not of the model. That is the single most useful number on this page."),
        },
        "qualified_count": 0,
        "rewards": [],
        "why_no_rewards": ("A reward has to be settled against a price. No price is registered, so no "
                           "entry can be paid, and no entry can be promoted from paper."),
        "forbidden_measures": ["season-long return", "win rate as a rank", "units won"],
        "gate_v7_pass": False, "gate_v8_pass": False,
        "registered_gates": registration["gates"],
    }


def main() -> int:
    DATA.mkdir(exist_ok=True)
    payload = build()
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    target = DATA / "leaderboard.json"
    if "--check" in sys.argv:
        if not target.exists() or target.read_text() != text:
            raise SystemExit("leaderboard.json is stale")
        print(f"OK: {len(payload['entries'])} entries, 0 qualified")
        return 0
    target.write_text(text)
    best = payload["entries"][0]
    print(f"Wrote leaderboard.json: top = {best['id']} skill {best['brier_skill']:+.4f} "
          f"lo {best['cluster_lo']:+.4f} q {best['q_value']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
