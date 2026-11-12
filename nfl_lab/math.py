"""NFL line origination and validation math. No market price is ever invented here.

Every quantity is either (a) parsed from an official NFL page by scripts/nfl_extract.py,
(b) an explicitly labelled derived estimate, or (c) blank. The functions in this module
refuse impossible inputs instead of guessing.
"""
from __future__ import annotations

import math
from statistics import fmean

# Football Pythagorean exponent as used for the NFL by Football Outsiders and
# Pro-Football-Reference (see research/nfl/sources.json: PYTH-NFL). It is a published
# convention, not a value we fitted, and it is disclosed as an assumption wherever used.
PYTH_EXPONENT = 2.37
# Project model assumption for home-field advantage measured in points, chosen before any
# evaluation is read. It is NOT estimated from our data and is NOT an NFL-published value.
HFA_POINTS = 2.0
# Total points are the sum of both sides' scoring rates; no market total is available.
LEAGUE_GAMES = 17


def _finite(value) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean is not an observation")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Non-finite value")
    return number


def scoring_rate(points_for: float, games: int) -> float:
    """Points per game scored. Games must be a positive integer count."""
    if not isinstance(games, int) or games <= 0:
        raise ValueError("Games played must be a positive integer")
    return _finite(points_for) / games


def pythagorean_win_pct(points_for: float, points_against: float,
                         exponent: float = PYTH_EXPONENT) -> float:
    """Pythagorean expected win rate. Returns in (0, 1); ties are not modelled here."""
    pf, pa, x = _finite(points_for), _finite(points_against), _finite(exponent)
    if pf <= 0 or pa <= 0:
        raise ValueError("Both scoring totals must be positive")
    return pf ** x / (pf ** x + pa ** x)


def expected_wins(points_for: float, points_against: float, games: int,
                  exponent: float = PYTH_EXPONENT) -> float:
    if not isinstance(games, int) or games <= 0:
        raise ValueError("Games played must be a positive integer")
    return pythagorean_win_pct(points_for, points_against, exponent) * games


def luck_residual(actual_wins: float, expected: float) -> float:
    """Actual minus expected wins. Positive means the record outperformed scoring.

    This is a descriptive residual. It is not proof of luck, clutch skill or a market
    error: it can reflect schedule, opponent strength, special teams and randomness.
    """
    return _finite(actual_wins) - _finite(expected)


def original_line(offense_ppg: float, defense_ppa: float, league_ppg: float,
                  hfa_points: float = HFA_POINTS) -> dict:
    """Price a game total and a spread from scoring rates only.

    The simplest additive construction: a club's expected points in a game is the mean of
    its own scoring rate and its opponent's concession rate, anchored on the league mean,
    plus a home adjustment. It is deliberately naive and is disclosed as such.
    """
    off, dfn, league, hfa = (_finite(offense_ppg), _finite(defense_ppa),
                             _finite(league_ppg), _finite(hfa_points))
    if league <= 0:
        raise ValueError("League scoring mean must be positive")
    if hfa < 0:
        raise ValueError("Home adjustment cannot be negative in this construction")
    return {"offense_component": off, "defense_component": dfn,
            "league_component": league, "home_adjustment": hfa,
            "formula": "team_points = (own_offense + opponent_defense + league)/3 (+hfa at home)"}


def project_game(home_off_ppg: float, home_def_ppa: float,
                 away_off_ppg: float, away_def_ppa: float,
                 league_ppg: float, hfa_points: float = HFA_POINTS) -> dict:
    """Coherent two-sided projection: one score distribution per club.

    home_points and away_points are conditional means. The spread is expressed from the
    home club's point of view (negative = home favoured) and the total is their sum, so
    both derivative lines come from the same pair of numbers.
    """
    league = _finite(league_ppg)
    if league <= 0:
        raise ValueError("League scoring mean must be positive")
    home = (home_off_ppg + away_def_ppa + league) / 3 + _finite(hfa_points)
    away = (away_off_ppg + home_def_ppa + league) / 3
    margin = home - away
    total = home + away
    return {"home_points": home, "away_ppg": away, "margin_home": margin,
            "total": total, "spread_home": -margin,
            "win_prob_home": normal_win_probability(margin)}


def normal_win_probability(margin: float, sd: float = 13.86) -> float:
    """Map a projected margin to a win probability with a normal approximation.

    sd=13.86 is an assumption supplied here, not an NFL figure; it is disclosed wherever
    a probability is shown. Ties are split, which slightly understates the true win rate.
    """
    if sd <= 0:
        raise ValueError("Standard deviation must be positive")
    m = _finite(margin)
    return 0.5 * (1 + math.erf(m / (sd * math.sqrt(2))))


def american_from_probability(p: float) -> int | None:
    """Fair (zero-hold) American price implied by a probability. Not an offered price."""
    prob = _finite(p)
    if not 0 < prob < 1:
        raise ValueError("Probability must be strictly inside (0, 1)")
    if prob == 0.5:
        return 100
    if prob > 0.5:
        return -round(100 * prob / (1 - prob))
    return round(100 * (1 - prob) / prob)


def break_even_probability(american: int) -> float:
    """Probability needed to break even at the given price, before any hold."""
    odds = _finite(american)
    if abs(odds) < 100:
        raise ValueError("American odds must have magnitude >= 100")
    return (-odds) / (-odds + 100) if odds < 0 else 100 / (odds + 100)


def kelly_fraction(p: float, american: int) -> float:
    """Fraction of bankroll that full Kelly would stake. Can be negative: no bet."""
    prob = _finite(p)
    if not 0 <= prob <= 1:
        raise ValueError("Probability must be inside [0, 1]")
    b = (100 / -american) if american < 0 else (american / 100)
    if b <= 0:
        raise ValueError("Invalid payoff")
    return (prob * (b + 1) - 1) / b


def brier(outcomes, probabilities) -> float:
    """Brier score for binary outcomes. Lower is better; 0.25 is the p=0.5 reference."""
    if not outcomes or len(outcomes) != len(probabilities):
        raise ValueError("Paired non-empty outcome and probability series required")
    total = 0.0
    for y, p in zip(outcomes, probabilities):
        if y not in (0, 1):
            raise ValueError("Outcome must be 0 or 1")
        prob = _finite(p)
        if not 0 <= prob <= 1:
            raise ValueError("Probability must be inside [0, 1]")
        total += (prob - y) ** 2
    return total / len(outcomes)


def reliability_bins(outcomes, probabilities, bins: int = 5):
    """Binned calibration table. Empty bins are reported as None, never as zero."""
    if bins < 2:
        raise ValueError("At least two bins required")
    if not outcomes or len(outcomes) != len(probabilities):
        raise ValueError("Paired non-empty series required")
    edges = [i / bins for i in range(bins + 1)]
    table = []
    for low, high in zip(edges, edges[1:]):
        picked = [(p, y) for p, y in zip(probabilities, outcomes)
                  if (low <= p < high) or (high == 1.0 and p == 1.0)]
        table.append({
            "bin": f"[{low:.1f}, {high:.1f}{']' if high == 1.0 else ')'}",
            "n": len(picked),
            "mean_forecast": fmean(p for p, _ in picked) if picked else None,
            "observed_rate": fmean(y for _, y in picked) if picked else None,
            "difference": (fmean(p for p, _ in picked) - fmean(y for _, y in picked)) if picked else None,
        })
    return table


def pearson(x, y) -> float | None:
    """Pearson r for paired samples; None when either series is constant."""
    if len(x) != len(y) or len(x) < 3:
        raise ValueError("Paired series of at least three points required")
    xs, ys = [_finite(v) for v in x], [_finite(v) for v in y]
    mx, my = fmean(xs), fmean(ys)
    sxx = math.fsum((a - mx) ** 2 for a in xs)
    syy = math.fsum((b - my) ** 2 for b in ys)
    if sxx == 0 or syy == 0:
        return None
    sxy = math.fsum((a - mx) * (b - my) for a, b in zip(xs, ys))
    return sxy / math.sqrt(sxx * syy)


def permutation_p_value(x, y, draws: int = 20000, seed: int = 20261112) -> float:
    """Two-sided permutation p-value for Pearson r; a dependence test, not an edge test."""
    import random
    observed = pearson(x, y)
    if observed is None:
        raise ValueError("Correlation undefined for a constant series")
    if draws < 100:
        raise ValueError("At least 100 draws required")
    rng = random.Random(seed)
    other = list(y)
    count = 0
    magnitude = abs(observed)
    for _ in range(draws):
        rng.shuffle(other)
        value = pearson(x, other)
        if value is not None and abs(value) >= magnitude - 1e-12:
            count += 1
    return (count + 1) / (draws + 1)


def holm(p_values) -> list[float]:
    """Holm-Bonferroni step-down adjustment; monotone and capped at 1."""
    values = [_finite(p) for p in p_values]
    if any(not 0 <= p <= 1 for p in values):
        raise ValueError("p-values must be inside [0, 1]")
    order = sorted(range(len(values)), key=lambda i: values[i])
    adjusted, running = [0.0] * len(values), 0.0
    for rank, index in enumerate(order):
        candidate = (len(values) - rank) * values[index]
        running = max(running, min(1.0, candidate))
        adjusted[index] = running
    return adjusted
