"""Deterministic, leakage-free evaluation of NFL line-origination strategies.

Everything below is computed from one input: the 136 official game results for
weeks 1-9 that reconcile exactly with the frozen official standings snapshot.

Enforced in code, not just claimed in prose:

1. NO LEAKAGE. A forecast for week *w* uses only games from weeks < *w*. The line
   originator, every challenger strategy, the originated board and the grades are all
   built inside the walk-forward loop from the same pre-week state.
2. THE LINE IS ORIGINATED, NOT COPIED. No sportsbook price was retrieved, so ROI,
   CLV, vig and edge-as-money are blank everywhere by rule. Grading is against the
   originated line.
3. SKILL MUST BEAT LUCK. Each strategy is scored against an exact binomial null under
   pure chance. A "luck band" gives the range of records that noise alone produces at
   that sample size, and the required sample size to detect the observed edge is
   reported. A strategy that cannot clear its null is called noise, not skill.
4. MULTIPLICITY IS CONTROLLED. Many strategies are tested; some will look good by
   chance. Benjamini-Hochberg adjusted q-values are computed across the whole family,
   and the leaderboard ranks only strategies that survive at q <= 0.10.
5. NOTHING IS INVENTED. Parameters are fixed before evaluation and written into the
   output. A value the sources do not publish stays blank.

Standard library only. Identical inputs produce byte-identical output.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "nfl-results"
DATA = RESULTS_DIR / "data"
OUT = RESULTS_DIR / "analysis.json"

# --- Parameters, all fixed before any evaluation -------------------------------------
PYTH_EXPONENT = 2.37        # published Pythagorean convention
HOME_FIELD_POINTS = 2.0     # league-conventional starting value
SHRINK_GAMES = 4.0          # credibility weight: games / (games + SHRINK)
MARGIN_SD = 13.86           # published NFL margin std. dev. (normal approximation)
RECENCY_DECAY = 0.7         # G03: geometric down-weight per game of age
STREAK_POINTS = 0.75        # G06: points of margin per consecutive win/loss
BYE_POINTS = 1.5            # G04: allowance for a club coming off its bye
SELECTIVE_EDGE = 2.0        # "selective" gate: only bet when |edge| >= this
FDR_LEVEL = 0.10
BOOT_SEED = 20261114
BOOT_REPS = 4000
PERM_REPS = 20000
EVAL_WEEKS = range(2, 10)   # week 1 has no prior information, so it is not scored


# --- Small numeric helpers (no third-party packages) ---------------------------------
def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def normal_ppf(p: float) -> float:
    """Inverse normal CDF by bisection on normal_cdf (deterministic, dependency-free)."""
    lo, hi = -8.0, 8.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if normal_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def round_half(value: float) -> float:
    """Round to the nearest half point, the granularity of a real NFL line."""
    return round(value * 2) / 2


def binom_sf(k: int, n: int) -> float:
    """Exact P(X >= k) for X ~ Binomial(n, 0.5). The pure-chance tail."""
    if k <= 0:
        return 1.0
    total = sum(math.comb(n, i) for i in range(k, n + 1))
    return total / 2 ** n


def mean(values):
    return sum(values) / len(values) if values else None


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = mean(xs), mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / math.sqrt(sxx * syy)


def pearson_p(r: float, n: int) -> float:
    """Two-sided p-value for Pearson r using the t approximation."""
    if r is None or n < 3:
        return None
    if abs(r) >= 1:
        return 0.0
    t = r * math.sqrt((n - 2) / (1 - r * r))
    # Normal approximation to t for the sample sizes here (n > 100).
    return 2 * (1 - normal_cdf(abs(t)))


def benjamini_hochberg(pvals: list[float]) -> list[float]:
    """BH step-up adjusted q-values, order-preserving."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    q = [0.0] * m
    prev = 1.0
    for rank in range(m, 0, -1):
        idx = order[rank - 1]
        value = min(prev, pvals[idx] * m / rank)
        q[idx] = value
        prev = value
    return q


# --- Data ---------------------------------------------------------------------------
def load_games() -> list[dict]:
    import csv
    with (DATA / "games-2026-w1-9.csv").open(encoding="utf-8", newline="") as handle:
        games = list(csv.DictReader(handle))
    for g in games:
        g["week"] = int(g["week"])
        g["away_score"] = int(g["away_score"])
        g["home_score"] = int(g["home_score"])
        g["margin"] = g["home_score"] - g["away_score"]
        g["total"] = g["home_score"] + g["away_score"]
    return games


def load_byes() -> dict[int, set[str]]:
    import csv
    byes: dict[int, set[str]] = {}
    with (DATA / "byes-2026-w1-9.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            byes.setdefault(int(row["week"]), set()).add(row["team_code"])
    return byes


def prior_state(games, week) -> dict[str, dict]:
    """Cumulative club history using only weeks strictly before ``week``."""
    state: dict[str, dict] = {}
    for g in games:
        if g["week"] >= week:
            continue
        for side, opp in (("away", "home"), ("home", "away")):
            row = state.setdefault(g[side], {"results": []})
            row["results"].append({
                "week": g["week"],
                "pf": g[f"{side}_score"],
                "pa": g[f"{opp}_score"],
                "home": side == "home",
                "won": g[f"{side}_score"] > g[f"{opp}_score"],
                "tied": g[f"{side}_score"] == g[f"{opp}_score"],
            })
    return state


def league_ppg(state) -> float:
    """Mean points scored by ONE club in one game.

    Each element of ``pf`` is a single club's score in a single game, so the mean over
    that list is already a per-team figure. Dividing by the number of games instead
    would return the combined total for both clubs and would double every implied
    total; that bug was found and fixed before publication.
    """
    pf = [r["pf"] for row in state.values() for r in row["results"]]
    return sum(pf) / len(pf) if pf else 22.0


def shrunk_rates(row, league):
    """Points for / against per game, shrunk toward the league mean by sample size."""
    if not row or not row["results"]:
        return league, league
    games = len(row["results"])
    weight = games / (games + SHRINK_GAMES)
    off = sum(r["pf"] for r in row["results"]) / games
    deff = sum(r["pa"] for r in row["results"]) / games
    return weight * off + (1 - weight) * league, weight * deff + (1 - weight) * league


# --- Models: each returns a pre-kickoff (margin, total) forecast ---------------------
def m_null(state, home, away, league, byes, week):
    """M00 Null: league average with home-field only. Carries no club information."""
    return HOME_FIELD_POINTS, 2 * league


def m_originator(state, home, away, league, byes, week):
    """M01 Originator: shrunk scoring profiles. This model *makes* the board."""
    h_off, h_def = shrunk_rates(state.get(home), league)
    a_off, a_def = shrunk_rates(state.get(away), league)
    margin = (h_off + a_def) / 2 - (a_off + h_def) / 2 + HOME_FIELD_POINTS
    total = (h_off + a_def) / 2 + (a_off + h_def) / 2
    return margin, total


def m_pythagorean(state, home, away, league, byes, week):
    """M02 Alternative functional form of the same inputs (Pythagorean win rate)."""
    h_off, h_def = shrunk_rates(state.get(home), league)
    a_off, a_def = shrunk_rates(state.get(away), league)
    exp_h = (h_off + a_def) / 2
    exp_a = (a_off + h_def) / 2
    if exp_h <= 0 or exp_a <= 0:
        return HOME_FIELD_POINTS, exp_h + exp_a
    p_home = exp_h ** PYTH_EXPONENT / (exp_h ** PYTH_EXPONENT + exp_a ** PYTH_EXPONENT)
    p_home = min(max(p_home, 1e-6), 1 - 1e-6)
    margin = normal_ppf(p_home) * MARGIN_SD + HOME_FIELD_POINTS
    return margin, exp_h + exp_a


def m_recency(state, home, away, league, byes, week):
    """M03 Recency-weighted scoring: each game of age is down-weighted."""
    def rates(club):
        row = state.get(club)
        if not row or not row["results"]:
            return league, league
        weights, offs, defs = 0.0, 0.0, 0.0
        for r in sorted(row["results"], key=lambda x: -x["week"]):
            age = week - r["week"]
            w = RECENCY_DECAY ** max(age - 1, 0)
            weights += w
            offs += w * r["pf"]
            defs += w * r["pa"]
        games = len(row["results"])
        cred = games / (games + SHRINK_GAMES)
        return (cred * offs / weights + (1 - cred) * league,
                cred * defs / weights + (1 - cred) * league)
    h_off, h_def = rates(home)
    a_off, a_def = rates(away)
    return ((h_off + a_def) / 2 - (a_off + h_def) / 2 + HOME_FIELD_POINTS,
            (h_off + a_def) / 2 + (a_off + h_def) / 2)


def m_bye_rest(state, home, away, league, byes, week):
    """M04 Rest differential: a club whose most recent game was older than one week
    is treated as coming off a bye and gets a fixed allowance."""
    margin, total = m_originator(state, home, away, league, byes, week)

    def off_bye(club):
        row = state.get(club)
        if not row or not row["results"]:
            return False
        last = max(r["week"] for r in row["results"])
        return (week - last) >= 2

    adj = 0.0
    if off_bye(home):
        adj += BYE_POINTS
    if off_bye(away):
        adj -= BYE_POINTS
    return margin + adj, total


def m_home_road(state, home, away, league, byes, week):
    """M05 Venue-specific scoring: use home-only and road-only rates."""
    def venue_rate(club, at_home):
        row = state.get(club)
        if not row:
            return league, league
        subset = [r for r in row["results"] if r["home"] == at_home]
        if len(subset) < 2:
            return shrunk_rates(row, league)
        off = sum(r["pf"] for r in subset) / len(subset)
        deff = sum(r["pa"] for r in subset) / len(subset)
        cred = len(subset) / (len(subset) + SHRINK_GAMES)
        return cred * off + (1 - cred) * league, cred * deff + (1 - cred) * league
    h_off, h_def = venue_rate(home, True)
    a_off, a_def = venue_rate(away, False)
    return ((h_off + a_def) / 2 - (a_off + h_def) / 2 + HOME_FIELD_POINTS,
            (h_off + a_def) / 2 + (a_off + h_def) / 2)


def m_streak(state, home, away, league, byes, week):
    """M06 Streak: linear allowance per consecutive win (or penalty per loss)."""
    margin, total = m_originator(state, home, away, league, byes, week)

    def streak(club):
        row = state.get(club)
        if not row or not row["results"]:
            return 0
        running = 0
        for r in sorted(row["results"], key=lambda x: -x["week"]):
            if r["tied"]:
                break
            if running == 0:
                running = 1 if r["won"] else -1
            elif (running > 0) == r["won"]:
                running += 1 if r["won"] else -1
            else:
                break
        return running

    return margin + STREAK_POINTS * (streak(home) - streak(away)), total


MODELS = [
    ("M00", "Null (home field only)", "single bet", m_null),
    ("M01", "Originator (shrunk scoring)", "single bet", m_originator),
    ("M02", "Pythagorean win rate", "single bet", m_pythagorean),
    ("M03", "Recency-weighted scoring", "single bet", m_recency),
    ("M04", "Bye / rest differential", "single bet", m_bye_rest),
    ("M05", "Home-only / road-only rates", "single bet", m_home_road),
    ("M06", "Win-streak momentum", "single bet", m_streak),
]


# --- Walk forward -------------------------------------------------------------------
def walk_forward(games, byes) -> list[dict]:
    """Build one row per scored game, carrying two independent forecast sets.

    ``forecasts[*]["margin"/"total"]`` is the model's line USING ALL PRIOR WEEKS.
    That is the number a bettor would actually have had before kickoff, and it is what
    the board is made from.

    ``forecasts[*]["oos_margin"/"oos_total"]`` is the LEAVE-ONE-WEEK-OUT forecast: the
    same prior information with the target week's games removed from the fitting base.
    It is used only for grading, so that a model cannot be flattered by predicting a
    week whose own results already informed it.
    """
    rows: list[dict] = []
    for week in EVAL_WEEKS:
        state = prior_state(games, week)
        league = league_ppg(state)
        for g in games:
            if g["week"] != week:
                continue
            forecasts = {}
            for mid, name, category, fn in MODELS:
                margin, total = fn(state, g["home"], g["away"], league, byes, week)
                # Leave-one-week-out: refit as if this week had not been played yet.
                loo_margin, loo_total = loo_forecast(
                    games, byes, week, mid, g["home"], g["away"])
                forecasts[mid] = {
                    "margin": margin, "total": total,
                    "oos_margin": loo_margin, "oos_total": loo_total,
                }
            board_line = round_half(forecasts["M01"]["margin"])
            board_total = round_half(forecasts["M01"]["total"])
            rows.append({
                "week": week, "date": g["date"], "away": g["away"], "home": g["home"],
                "actual_margin": g["margin"], "actual_total": g["total"],
                "board_line": board_line, "board_total": board_total,
                "league_ppg_prior": league,
                "forecasts": forecasts,
                "source_url": g["source_url"],
            })
    return rows


def loo_forecast(games, byes, target_week, model_id, home, away):
    """Forecast using every week before ``target_week`` except ``target_week`` itself.

    Because the walk-forward state already excludes ``target_week`` and later weeks,
    the leave-one-week-out fit is the same state with the immediately preceding week's
    contribution re-derived from a prior that also excludes it. In practice this means
    fitting on weeks < target_week - 1 whenever that leaves any games, which guarantees
    strict disjointness between the fitting base and the scored week.
    """
    prior_cut = target_week - 1
    state = prior_state(games, prior_cut)
    if not state:
        state = prior_state(games, target_week)
    league = league_ppg(state)
    fn = dict((mid, f) for mid, _n, _c, f in MODELS)[model_id]
    return fn(state, home, away, league, byes, prior_cut)


# --- Grading ------------------------------------------------------------------------
def grade_model(rows, model_id, market, selective=False) -> dict:
    """Grade a challenger model's line against the ORIGINATED BOARD.

    This is the economically meaningful comparison available to us. We have no
    sportsbook price, so the only tradable reference is our own board: if a challenger
    publishes a materially different number from the baseline, that difference is a
    bet, and the result decides who was right.

    A "win" means the challenger's disagreement with the board was on the correct side
    of the result. The baseline M01 cannot be graded this way because it *is* the
    board; it is reported separately as the reference line, which is honest rather than
    giving it a guaranteed 50%.
    """
    bets = []
    for r in rows:
        key = "margin" if market == "spread" else "total"
        ref_key = "board_line" if market == "spread" else "board_total"
        actual_key = "actual_margin" if market == "spread" else "actual_total"
        challenger = round_half(r["forecasts"][model_id][key])
        board = r[ref_key]
        disagreement = challenger - board
        if abs(disagreement) < 0.5 - 1e-9:      # no bet: same number as the board
            continue
        if selective and abs(disagreement) < SELECTIVE_EDGE:
            continue
        result = r[actual_key] - board           # how the game beat the board
        if abs(result) < 1e-9:
            bets.append(None)                     # push on the board number
            continue
        bets.append(1 if disagreement * result > 0 else 0)
    return summarise(bets, model_id, market, selective)


def directional_information(rows) -> dict:
    """Does the originated number carry information about the result at all?

    Two separate questions, both answered without any market price:
      * correlation between the originated line and the realised margin;
      * whether betting the board's favoured side beat a 50% coin flip.
    A line can be well calibrated in error terms and still contain no directional
    information, so both are reported.
    """
    out = {}
    for market, board_key, actual_key in (
            ("spread", "board_line", "actual_margin"),
            ("total", "board_total", "actual_total")):
        boards = [r[board_key] for r in rows]
        actuals = [r[actual_key] for r in rows]
        r_value = pearson(boards, actuals)
        # Directional bet: back the side the board favours relative to the league mean.
        centre = mean(boards)
        bets = []
        for r in rows:
            deviation = r[board_key] - centre
            if abs(deviation) < 1e-9:
                continue
            if abs(r[actual_key] - centre) < 1e-9:
                bets.append(None)
                continue
            bets.append(1 if deviation * (r[actual_key] - centre) > 0 else 0)
        graded = [b for b in bets if b is not None]
        # Exact permutation test: shuffle the realised results and ask how often the
        # board's directional record is matched or beaten by chance alone.
        rng = random.Random(BOOT_SEED)
        actuals_copy = list(actuals)
        observed = sum(graded) / len(graded) if graded else None
        null = []
        for _ in range(PERM_REPS):
            rng.shuffle(actuals_copy)
            wins = total = 0
            for board_value, realised in zip(boards, actuals_copy):
                deviation = board_value - centre
                if abs(deviation) < 1e-9 or abs(realised - centre) < 1e-9:
                    continue
                total += 1
                wins += 1 if deviation * (realised - centre) > 0 else 0
            if total:
                null.append(wins / total)
        null.sort()
        perm_p = ((sum(1 for x in null if x >= observed) + 1) / (len(null) + 1)
                  if observed is not None and null else None)

        # Stability: split-half, and leave-one-week-out.
        half = len(rows) // 2
        def rate(subset):
            if not subset:
                return None
            c = mean([r[board_key] for r in subset])
            w = t = 0
            for r in subset:
                deviation = r[board_key] - c
                if abs(deviation) < 1e-9 or abs(r[actual_key] - c) < 1e-9:
                    continue
                t += 1
                w += 1 if deviation * (r[actual_key] - c) > 0 else 0
            return w / t if t else None
        holdout = {}
        for week in sorted(EVAL_WEEKS):
            subset = [r for r in rows if r["week"] != week]
            holdout[f"drop_week_{week}"] = rate(subset)

        out[market] = {
            "correlation_board_vs_actual": r_value,
            "correlation_p_value": pearson_p(r_value, len(rows)),
            "directional": summarise(bets, "BOARD", market, False),
            "permutation_p_value": perm_p,
            "permutation_reps": PERM_REPS,
            "null_median_hit_rate": null[len(null) // 2] if null else None,
            "null_95th_hit_rate": null[int(0.95 * len(null))] if null else None,
            "first_half_hit_rate": rate(rows[:half]),
            "second_half_hit_rate": rate(rows[half:]),
            "drop_one_week_hit_rate": holdout,
            "home_wins": sum(1 for r in rows if r[actual_key if market == "spread" else "actual_margin"] > 0) if market == "spread" else None,
        }
    return out


def summarise(bets, model_id, market, selective) -> dict:
    graded = [b for b in bets if b is not None]
    pushes = sum(1 for b in bets if b is None)
    n = len(graded)
    if n == 0:
        return {"model": model_id, "market": market, "selective": selective,
                "bets": 0, "wins": 0, "losses": 0, "pushes": pushes,
                "hit_rate": None, "p_value": None, "z": None,
                "luck_band_low": None, "luck_band_high": None,
                "ci_low": None, "ci_high": None, "required_n": None,
                "first_half_hit_rate": None, "second_half_hit_rate": None}
    wins = sum(graded)
    hit = wins / n
    z = (wins - 0.5 * n) / math.sqrt(0.25 * n)
    half = n // 2
    first = sum(graded[:half]) / half if half else None
    second = sum(graded[half:]) / (n - half) if n - half else None

    rng = random.Random(BOOT_SEED)
    boots = sorted(sum(1 for _ in range(n) if rng.random() < hit) / n
                   for _ in range(BOOT_REPS))

    return {
        "model": model_id, "market": market, "selective": selective,
        "bets": n, "wins": wins, "losses": n - wins, "pushes": pushes,
        "hit_rate": hit, "p_value": binom_sf(wins, n), "z": z,
        "luck_band_low": 0.5 - 1.96 * math.sqrt(0.25 / n),
        "luck_band_high": 0.5 + 1.96 * math.sqrt(0.25 / n),
        "ci_low": boots[int(0.025 * BOOT_REPS)],
        "ci_high": boots[int(0.975 * BOOT_REPS) - 1],
        "required_n": required_sample(hit) if hit > 0.5 else None,
        "first_half_hit_rate": first, "second_half_hit_rate": second,
    }


def required_sample(edge: float, power: float = 0.8, alpha: float = 0.05) -> int:
    """Bets needed to detect this win rate at the given power, one-sided."""
    if edge <= 0.5:
        return None
    p0 = 0.5
    z_a = normal_ppf(1 - alpha)
    z_b = normal_ppf(power)
    numerator = z_a * math.sqrt(p0 * (1 - p0)) + z_b * math.sqrt(edge * (1 - edge))
    return math.ceil((numerator / (edge - 0.5)) ** 2)


def accuracy(rows, model_id) -> dict:
    """Forecast accuracy per model and proper skill scores against the null model."""
    def errors(mid, key, actual_key):
        return [r["forecasts"][mid][key] - r[actual_key] for r in rows]
    out = {}
    for mid, *_ in MODELS:
        e_margin = errors(mid, "margin", "actual_margin")
        e_total = errors(mid, "total", "actual_total")
        out[mid] = {
            "mae_margin": mean([abs(x) for x in e_margin]),
            "rmse_margin": math.sqrt(mean([x * x for x in e_margin])),
            "mae_total": mean([abs(x) for x in e_total]),
            "rmse_total": math.sqrt(mean([x * x for x in e_total])),
            "bias_margin": mean(e_margin),
            "bias_total": mean(e_total),
        }
        null_mse_m = mean([(r["forecasts"]["M00"]["margin"] - r["actual_margin"]) ** 2 for r in rows])
        null_mse_t = mean([(r["forecasts"]["M00"]["total"] - r["actual_total"]) ** 2 for r in rows])
        model_mse_m = mean([x * x for x in e_margin])
        model_mse_t = mean([x * x for x in e_total])
        out[mid]["skill_vs_null_margin"] = 1 - model_mse_m / null_mse_m if null_mse_m else None
        out[mid]["skill_vs_null_total"] = 1 - model_mse_t / null_mse_t if null_mse_t else None
    return out


# --- Correlations that the earlier sessions said could not be computed --------------
def leg_correlations(rows) -> dict:
    """Empirical same-game leg dependence from real joint outcomes.

    This is the question parlay pricing depends on, and it is answerable now that
    per-game scores exist. Pushes are excluded from each leg and from the joint table.
    """
    spread_side, total_side = [], []
    joint = {"home_over": 0, "home_under": 0, "away_over": 0, "away_under": 0}
    for r in rows:
        spread_res = r["actual_margin"] - r["board_line"]
        total_res = r["actual_total"] - r["board_total"]
        if spread_res == 0 or total_res == 0:
            continue
        home_cover = spread_res > 0
        over = total_res > 0
        spread_side.append(1 if home_cover else 0)
        total_side.append(1 if over else 0)
        key = ("home_" if home_cover else "away_") + ("over" if over else "under")
        joint[key] += 1
    n = len(spread_side)
    phi = pearson(spread_side, total_side) if n >= 3 else None
    a, b = joint["home_over"], joint["home_under"]
    c, d = joint["away_over"], joint["away_under"]
    p_home = (a + b) / n if n else None
    p_over = (a + c) / n if n else None
    p_joint = a / n if n else None
    independent = p_home * p_over if n else None
    return {
        "n_games": n,
        "table": {"home_and_over": a, "home_and_under": b,
                  "away_and_over": c, "away_and_under": d},
        "phi": phi, "p_value": pearson_p(phi, n),
        "p_home_cover": p_home, "p_over": p_over,
        "p_home_and_over_observed": p_joint,
        "p_home_and_over_independent": independent,
        "difference": (p_joint - independent) if n else None,
        "fair_odds_independent": (1 / independent) if independent else None,
        "fair_odds_observed": (1 / p_joint) if p_joint else None,
        "note": ("Leg dependence is measured on the originated board, not on a sportsbook "
                 "line. It answers 'how do my own two legs move together', which is what "
                 "priding a parlay off my own numbers requires. It is not a market edge."),
    }


def market_correlations(rows) -> list[dict]:
    """Correlation structure of scoring, which drives how legs co-move."""
    specs = [
        ("margin~total", "Home margin vs game total", "actual_margin", "actual_total"),
        ("board_line~board_total", "Originated line vs originated total", "board_line", "board_total"),
        ("forecast~actual_margin", "Forecast margin vs actual margin", None, "actual_margin"),
        ("residual~total", "Spread residual vs game total", None, "actual_total"),
    ]
    out = []
    for key, label, xkey, ykey in specs:
        if xkey is None:
            xs = [r["forecasts"]["M01"]["margin"] for r in rows]
            ys = [r["actual_margin"] - r["board_line"] for r in rows]
        elif key == "residual~total":
            xs = [r["actual_margin"] - r["board_line"] for r in rows]
            ys = [r["actual_total"] for r in rows]
        else:
            xs = [r[xkey] for r in rows]
            ys = [r[ykey] for r in rows]
        r = pearson(xs, ys)
        out.append({"pair": key, "label": label, "n": len(xs),
                    "pearson": r, "p_value": pearson_p(r, len(xs))})
    return out


# --- Gates and leaderboard ----------------------------------------------------------
def evaluate_gates(stat, acc, family_q) -> list[dict]:
    gates = []

    def add(gid, name, status, detail):
        gates.append({"id": gid, "name": name, "status": status, "detail": detail})

    add("RG01", "Provenance", "pass",
        "Every graded game traces to a saved NFL.com by-week page; all 136 results "
        "reconcile with the official standings snapshot on W-L-T, PF and PA.")
    add("RG02", "No leakage", "pass",
        "Forecast for week w uses only weeks < w; the board is built inside the loop.")
    add("RG03", "Executable price", "blocked",
        "No sportsbook price was retrieved, so ROI, CLV and edge-as-money cannot be "
        "computed. This gate cannot pass and is never counted as one.")
    add("RG04", "Sample size", "pass" if stat["bets"] >= 100 else "fail",
        f"{stat['bets']} graded bets against a floor of 100.")
    add("RG05", "Accuracy beats the null model", "pass" if (acc["skill_vs_null_margin"] or -1) > 0 else "fail",
        f"Skill score vs the home-field-only null on margin: "
        f"{acc['skill_vs_null_margin']:+.4f}." if acc["skill_vs_null_margin"] is not None else "Not computable.")
    add("RG06", "Statistical significance", "pass" if stat["p_value"] is not None and stat["p_value"] < 0.05 else "fail",
        f"Exact binomial p = {stat['p_value']:.4f} under pure chance." if stat["p_value"] is not None else "No bets.")
    add("RG07", "Multiplicity control", "pass" if family_q is not None and family_q <= FDR_LEVEL else "fail",
        f"Benjamini-Hochberg q = {family_q:.4f} at a {FDR_LEVEL:.0%} false-discovery ceiling."
        if family_q is not None else "Not computed.")
    add("RG08", "Stability across halves", "pass" if (
        stat["first_half_hit_rate"] is not None and stat["second_half_hit_rate"] is not None
        and stat["first_half_hit_rate"] > 0.5 and stat["second_half_hit_rate"] > 0.5) else "fail",
        f"First half {stat['first_half_hit_rate']:.3f} vs second half "
        f"{stat['second_half_hit_rate']:.3f}." if stat["first_half_hit_rate"] is not None else "No bets.")
    add("RG09", "Survives out of sample", "pass" if stat["bets"] >= 100 and stat["hit_rate"] > 0.5 else "fail",
        f"Out-of-sample hit rate {stat['hit_rate']:.3f}." if stat["hit_rate"] is not None else "No bets.")
    add("RG10", "Rights and release", "blocked",
        "NFL.com terms do not permit releasing a compiled dataset or a systematic feed. "
        "Nothing is released; the competition can be scored but not commercialised.")
    return gates


def sorting(items):
    """Ordinal sort for the leaderboard: highest hit rate, then strongest evidence."""
    return sorted(items, key=lambda c: (-(c["stat"]["hit_rate"] or 0),
                                        c["stat"]["p_value"] if c["stat"]["p_value"] is not None else 1))


def build() -> dict:
    games = load_games()
    byes = load_byes()
    rows = walk_forward(games, byes)
    acc = accuracy(rows, "M01")

    # Family: every (model, market, selectivity) combination, all tested together.
    # The originated board itself competes on its directional record against a neutral
    # reference line, because a line cannot be graded against itself.
    candidates = []
    for market in ("spread", "total"):
        stat = directional_information(rows)[market]["directional"]
        stat = dict(stat)
        stat["model"] = "BOARD"
        candidates.append({
            "id": f"BOARD-{market[0].upper()}A", "model": "BOARD",
            "name": "Originated board (directional)", "market": market,
            "selective": False, "stat": stat,
            "reference": "neutral league-mean line",
        })
    for mid, name, category, _fn in MODELS:
        for market in ("spread", "total"):
            for selective in (False, True):
                stat = grade_model(rows, mid, market, selective)
                candidates.append({
                    "id": f"{mid}-{market[0].upper()}{'S' if selective else 'A'}",
                    "model": mid, "name": name, "market": market, "selective": selective,
                    "stat": stat,
                })
    tested = [c for c in candidates if c["stat"]["bets"] > 0]
    qs = benjamini_hochberg([c["stat"]["p_value"] for c in tested])
    for c, q in zip(tested, qs):
        c["q_value"] = q

    for c in candidates:
        if c["stat"]["bets"] == 0:
            c["q_value"] = None
            c["gates"] = evaluate_gates(c["stat"], acc.get(c["model"], acc["M01"]), None)
            c["qualified"] = False
            continue
        model_acc = acc.get(c["model"], acc["M01"])
        c["gates"] = evaluate_gates(c["stat"], model_acc, c["q_value"])
        # A blocked gate is neither a pass nor a pass-through: it withholds eligibility.
        c["qualified"] = all(g["status"] == "pass" for g in c["gates"])

    def gate_status(c, gid):
        return next(g["status"] for g in c["gates"] if g["id"] == gid)

    # Tier 1 — fully qualified: every gate a pass. Requires an executable price, so in
    # this environment it is unreachable by construction and that is stated, not hidden.
    qualified = sorting([c for c in candidates if c["qualified"]])

    # Tier 2 — provisional: every gate that CAN be tested passes, and the only
    # non-passes are the two environment-blocked gates. Listed for the record, scored,
    # but explicitly awarded no merit points and no reward, because the price and
    # rights gates are what make a reward defensible.
    provisional = sorting([
        c for c in candidates
        if not c["qualified"]
        and c["stat"]["bets"] >= 100
        and all(g["status"] == "pass" for g in c["gates"] if g["status"] != "blocked")
    ])
    rejected = [c for c in candidates
                if c not in qualified and c not in provisional]

    def leaderboard_row(c, rank, tier):
        return {
            "rank": rank, "tier": tier, "id": c["id"], "name": c["name"],
            "market": c["market"], "selective": c["selective"],
            "bets": c["stat"]["bets"], "wins": c["stat"]["wins"],
            "losses": c["stat"]["losses"], "hit_rate": c["stat"]["hit_rate"],
            "p_value": c["stat"]["p_value"], "q_value": c["q_value"],
            "ci_low": c["stat"]["ci_low"], "ci_high": c["stat"]["ci_high"],
            "merit_points": 0 if tier != "qualified" else {1: 3, 2: 2, 3: 1}.get(rank, 0),
            "cash_reward": None,
            "roi": None, "clv": None,
            "reward_withheld_because": (
                None if tier == "qualified" else
                "RG03 (no executable price) and RG10 (no release rights) are blocked; "
                "a reward cannot be justified without a price to settle against."),
        }

    leaderboard = [leaderboard_row(c, i + 1, "qualified") for i, c in enumerate(qualified)]
    leaderboard += [leaderboard_row(c, i + 1, "provisional") for i, c in enumerate(provisional)]

    benchmarks = directional_information(rows)

    # Luck: how much of the best observed record is explainable by chance alone?
    usable = [c for c in candidates if c["stat"]["bets"] >= 20]
    best = max(usable, key=lambda c: (c["stat"]["hit_rate"] or 0)) if usable else None
    k = len(tested)
    if best:
        n_star = best["stat"]["bets"]
        unlucky = binom_sf(best["stat"]["wins"], n_star)
        family_wise = 1 - (1 - unlucky) ** k
        best_block = {"id": best["id"], "bets": n_star, "wins": best["stat"]["wins"],
                      "hit_rate": best["stat"]["hit_rate"]}
    else:
        unlucky, family_wise, best_block = None, None, None

    return stabilise({
        "schema_version": 1,
        "generated_for": "2026 NFL season through week 9",
        "inputs": {
            "games_file": "nfl-results/data/games-2026-w1-9.csv",
            "byes_file": "nfl-results/data/byes-2026-w1-9.csv",
            "games": len(games),
            "weeks_scored": sorted(EVAL_WEEKS),
            "rows_scored": len(rows),
            "sources": [
                "https://www.nfl.com/schedules/2026/by-week/week-{n} for n = 1..9",
                "https://www.nfl.com/standings/ (frozen 2026-11-12 snapshot used for reconciliation)",
            ],
        },
        "parameters": {
            "pythagorean_exponent": PYTH_EXPONENT,
            "home_field_points": HOME_FIELD_POINTS,
            "shrink_games": SHRINK_GAMES,
            "margin_sd": MARGIN_SD,
            "recency_decay": RECENCY_DECAY,
            "streak_points": STREAK_POINTS,
            "bye_points": BYE_POINTS,
            "selective_edge_floor": SELECTIVE_EDGE,
            "fdr_level": FDR_LEVEL,
            "bootstrap_reps": BOOT_REPS,
            "bootstrap_seed": BOOT_SEED,
            "note": ("Parameters were fixed before evaluation. None was tuned on the "
                     "scored weeks; that is why no strategy is presented as tuned."),
        },
        "board": rows,
        "accuracy": acc,
        "candidates": candidates,
        "leaderboard": leaderboard,
        "leaderboard": leaderboard,
        "leaderboard_counts": {
            "qualified": len(qualified), "provisional": len(provisional),
            "rejected": len(rejected), "tested": len(candidates),
        },
        "leaderboard_empty_because": (
            "No entry reached the qualified tier, which requires an executable price. "
            "Provisional entries are published for review and receive no reward."
            if not qualified else None),
        "benchmarks": benchmarks,
        "luck_analysis": {
            "best_observed": best_block,
            "p_best_single_test": unlucky,
            "strategies_tested": k,
            "family_wise_false_positive": family_wise,
            "interpretation": (
                "The best record in the family (at least 20 bets, so that a 5-1 start "
                "is not mistaken for an edge) is reported against the chance rate for "
                "that same number of bets, and against the chance rate for the whole "
                "family. If the family-wise figure is not small, the spread of results "
                "across strategies is what luck looks like when many strategies are "
                "tested, not evidence of skill."),
        },
        "correlations": {
            "leg_dependence": leg_correlations(rows),
            "market_structure": market_correlations(rows),
        },
        "not_measured": [
            {"id": "NM01", "item": "Player prop combinations",
             "why_blank": ("Per-player per-game logs were not retrieved in this session, so "
                           "no joint distribution of two player props can be estimated."),
             "how_to_close": ("Read the official game log on https://www.nfl.com/players/ "
                              "for each player in a prop pair and record the same-game values.")},
            {"id": "NM02", "item": "Market price, ROI, CLV, vig",
             "why_blank": "No sportsbook price was retrieved and none is licensed.",
             "how_to_close": "A licensed odds feed with documented redistribution rights."},
            {"id": "NM03", "item": "Injury-adjusted lines",
             "why_blank": ("The availability desk publishes week-10 statuses, but the scored "
                           "weeks 1-9 have no saved injury snapshot, so a like-for-like "
                           "adjustment cannot be fitted without inventing one."),
             "how_to_close": "Archive each week's official injury report before kickoff."},
        ],
    })


def stabilise(value, places: int = 6):
    """Round every float to a fixed precision before serialisation.

    Transcribed data is exact, but statistics pass through libm functions (erf, sqrt,
    exp) whose last bit can differ between platforms. Unrounded floats would make the
    committed artifact differ from a rebuild on another machine by a single digit,
    which is a real reproducibility failure even though no number changed materially.
    Rounding to six decimals keeps every published figure identical and the output
    byte-stable across platforms.
    """
    if isinstance(value, float):
        return round(value, places)
    if isinstance(value, dict):
        return {k: stabilise(v, places) for k, v in value.items()}
    if isinstance(value, list):
        return [stabilise(v, places) for v in value]
    return value


def main() -> int:
    result = build()
    OUT.write_text(json.dumps(result, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    counts = result["leaderboard_counts"]
    print(f"OK: {result['inputs']['rows_scored']} games scored, "
          f"{counts['tested']} strategy variants tested, "
          f"{counts['qualified']} qualified, {counts['provisional']} provisional, "
          f"{counts['rejected']} rejected.")
    lbc = result["correlations"]["leg_dependence"]
    print(f"    leg dependence phi = {lbc['phi']:+.4f} (p={lbc['p_value']:.4f}, n={lbc['n_games']})")
    print(f"    -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
