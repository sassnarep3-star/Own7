"""NFL origination and evidence gates: standard-library research primitives.

All numeric examples in tests are SYNTHETIC. This module does not fetch data,
place bets, estimate missing inputs, or authorize NFL-derived price publication.
Thresholds are transparent project policy, not league standards or proof of skill.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta
import hashlib
import json
import math
import random
import statistics
from typing import Iterable

GATES = [
    ('G01', 'Rights & provenance', 'Explicit permission for intended use; official input URLs, retrieval times and immutable evidence hashes.'),
    ('G02', 'Schema & coverage', 'Required fields, stable identities, offer/settlement definitions and missingness report; no imputed unknowns.'),
    ('G03', 'Information chronology', 'Every feature available before a sealed forecast; train labels end before test kickoff, with embargo.'),
    ('G04', 'Sample & power', 'Preregistered power/precision analysis; at least 500 settled selections, 200 distinct games and 60 dates.'),
    ('G05', 'Forecast quality', 'Beat frozen no-vig market and simple baselines on log loss; inspect calibration bins, not accuracy alone.'),
    ('G06', 'Dependence & settlement', 'Aligned joint outcomes and operator-specific void/push/DNP/OT rules; never assume parlay legs independent.'),
    ('G07', 'Executable economics', 'Timestamped offers, limits, fees, voids and closing prices; positive net return and CLV after all costs.'),
    ('G08', 'Selection & multiplicity', 'Register every attempted variant; Holm family includes failures; report a sealed, untouched confirmation test.'),
    ('G09', 'Prospective shadow', 'At least 60 future calendar days and 200 games with immutable pregame forecasts and complete abstention log.'),
    ('G10', 'Risk & abstention', 'Common flat paper stakes, game/date exposure caps, drawdown stop and no chase/martingale behavior.'),
    ('G11', 'Reproducibility', 'Pinned code/environment, input hashes, deterministic rerun and independent implementation checks.'),
    ('G12', 'Reviewed decision', 'Named reviewer approves a versioned proposal after questions are resolved; implementation is a separate change.'),
]
MARKETS = ('Single bets', 'Parlays', 'Player props / combos')
POLICY = {'min_selections': 500, 'min_games': 200, 'min_dates': 60, 'alpha': 0.05,
          'shadow_days': 60, 'shadow_games': 200, 'max_units_per_game': 1,
          'max_units_per_day': 5, 'max_drawdown_units': 10,
          'bootstrap_replicates': 10000, 'block_dates': 7, 'seed': 20261112}


def finite(value, name='value'):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + ' must be finite and numeric')
    return float(value)


def probability(value, name='probability', closed=False):
    p = finite(value, name)
    if (closed and not 0 <= p <= 1) or (not closed and not 0 < p < 1):
        raise ValueError(name + ' outside permitted probability range')
    return p


def decimal_odds(p):
    return 1 / probability(p)


def american_decimal(price):
    price = finite(price, 'American price')
    if price == 0 or abs(price) < 100:
        raise ValueError('American price must be >= +100 or <= -100')
    return 1 + (price / 100 if price > 0 else 100 / -price)


def decimal_american(price):
    price = finite(price, 'decimal price')
    if price <= 1:
        raise ValueError('Decimal price must exceed 1')
    return 100 * (price - 1) if price >= 2 else -100 / (price - 1)


def devig_two_way(prices):
    if len(prices) != 2:
        raise ValueError('Exactly two mutually exclusive, exhaustive outcomes required')
    inverses = [1 / finite(x, 'decimal price') for x in prices]
    if any(x <= 0 or x >= 1 for x in inverses) or sum(inverses) <= 1:
        raise ValueError('Two-way no-vig requires positive overround')
    total = sum(inverses)
    return [x / total for x in inverses]


def expected_value(p, price):
    return probability(p) * (finite(price, 'price') - 1) - (1 - p)


def settle(stake, price, outcome):
    stake, price = finite(stake, 'stake'), finite(price, 'price')
    if stake < 0 or price <= 1 or outcome not in ('win', 'loss', 'push', 'void'):
        raise ValueError('Invalid settlement inputs')
    return stake * (price - 1) if outcome == 'win' else -stake if outcome == 'loss' else 0.0


def phi(x):
    return 0.5 * (1 + math.erf(finite(x) / math.sqrt(2)))


def half_point(value, name):
    value = finite(value, name)
    if abs(value * 2 - round(value * 2)) > 1e-9 or abs(value - round(value)) < 1e-9:
        raise ValueError(name + ' must be a half-point: continuous normal model cannot price integer pushes')
    return value


def originate_research(market, *, p_home=None, p_away=None, p_tie=None,
                       margin_mean=None, margin_sd=None, total_mean=None, total_sd=None,
                       spread=None, total=None):
    """Return mathematical research prices, NOT authorization to publish NFL lines.

    Margin = home minus away. Home spread is signed from the home team's view.
    Normal distributions are explicit modeling assumptions. Integer lines abstain
    because a continuous distribution assigns zero push mass to real discrete scores.
    Tie probability is separate; a two-way moneyline treats a tie as a push.
    """
    if market not in ('moneyline', 'spread', 'total'):
        raise ValueError('Unknown market')
    out = {'market': market, 'evidence_class': 'Derived research calculation',
           'publication_authorized': False, 'fair_decimal': None, 'fair_american': None,
           'push_probability': None, 'assumptions': []}
    if market == 'moneyline':
        h, a, t = (probability(x, closed=True) for x in (p_home, p_away, p_tie))
        if abs(h + a + t - 1) > 1e-10 or h + a == 0:
            raise ValueError('Win/loss/tie probabilities must sum to one with nonzero decisive mass')
        p = h / (h + a)
        out.update({'push_probability': t, 'assumptions': ['Tie pushes; operator rules must confirm']})
    elif market == 'spread':
        mu, sd = finite(margin_mean, 'margin mean'), finite(margin_sd, 'margin SD')
        line = half_point(spread, 'spread')
        if sd <= 0: raise ValueError('Margin SD must be positive')
        p = 1 - phi((-line - mu) / sd)
        out.update({'push_probability': 0, 'assumptions': ['Normal margin distribution', 'Half-point line; no push']})
    else:
        mu, sd = finite(total_mean, 'total mean'), finite(total_sd, 'total SD')
        line = half_point(total, 'total')
        if sd <= 0: raise ValueError('Total SD must be positive')
        p = 1 - phi((line - mu) / sd)
        out.update({'push_probability': 0, 'assumptions': ['Normal total distribution is an approximation', 'Half-point line; no push']})
    if not 0 < p < 1:
        out['abstention'] = 'Numerical probability at boundary; no price released'
        return out
    out.update({'p_cover': p, 'fair_decimal': decimal_odds(p), 'fair_american': decimal_american(decimal_odds(p))})
    return out


def pearson(x, y):
    if len(x) != len(y) or len(x) < 3:
        raise ValueError('At least three aligned pairs required')
    x, y = [finite(v) for v in x], [finite(v) for v in y]
    if len(set(x)) < 2 or len(set(y)) < 2:
        return None
    return statistics.correlation(x, y)


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j+1]] == values[order[i]]:
            j += 1
        rank = (i + j + 2) / 2
        for k in range(i, j + 1): result[order[k]] = rank
        i = j + 1
    return result


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def event_phi(x, y):
    if len(x) != len(y) or not x or any(v not in (0, 1, False, True) for v in [*x, *y]):
        raise ValueError('Aligned binary outcomes required')
    return pearson([int(v) for v in x], [int(v) for v in y])


def quantile(values, q):
    values = sorted(values)
    index = (len(values) - 1) * q
    lo, hi = math.floor(index), math.ceil(index)
    return values[lo] + (values[hi] - values[lo]) * (index - lo)


def paired_block_interval(x, y, *, replicates=2000, block=5, seed=20261112):
    """Exploratory circular paired-block interval; horizon is an assumption."""
    point = pearson(x, y)
    if point is None or len(x) < max(3, block) or replicates < 100 or block < 1:
        return {'n': len(x), 'estimate': point, 'low': None, 'high': None, 'status': 'Undefined or insufficient pairs'}
    rng, estimates, n = random.Random(seed), [], len(x)
    for _ in range(replicates):
        xx, yy = [], []
        while len(xx) < n:
            start = rng.randrange(n)
            for j in range(min(block, n-len(xx))):
                xx.append(x[(start+j) % n]); yy.append(y[(start+j) % n])
        r = pearson(xx, yy)
        if r is not None: estimates.append(r)
    if len(estimates) < replicates * .95:
        return {'n': n, 'estimate': point, 'low': None, 'high': None, 'status': 'Too many degenerate resamples'}
    return {'n': n, 'estimate': point, 'low': quantile(estimates, .025), 'high': quantile(estimates, .975),
            'replicates': replicates, 'block_pairs': block, 'seed': seed,
            'status': 'Exploratory; no selection adjustment or confirmatory coverage claim'}


def joint_binary(rows):
    """rows = aligned (leg_a, leg_b, observed_joint_hit); no product assumption."""
    if not rows or any(len(r) != 3 or any(v not in (0, 1) for v in r) for r in rows):
        raise ValueError('Aligned binary legs and joint outcome required')
    if any(a & b != joint for a, b, joint in rows):
        raise ValueError('Joint outcome contradicts legs')
    a, b, j = ([r[i] for r in rows] for i in range(3))
    pa, pb, pj = statistics.mean(a), statistics.mean(b), statistics.mean(j)
    return {'n': len(rows), 'p_a': pa, 'p_b': pb, 'joint': pj, 'phi': event_phi(a, b),
            'frechet_low': max(0, pa+pb-1), 'frechet_high': min(pa, pb),
            'independence_product': pa*pb, 'note': 'Product is a comparison, not an estimate. Pairwise values do not identify 3+ leg joints.'}


def frechet_many(probabilities):
    p = [probability(x, closed=True) for x in probabilities]
    if len(p) < 2: raise ValueError('At least two legs required')
    return {'low': max(0, sum(p)-len(p)+1), 'high': min(p),
            'note': 'Bounds use known marginals only; they do not estimate the actual joint probability.'}


def parse_time(value):
    if not isinstance(value, str): raise ValueError('ISO timestamp required')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None: raise ValueError('Timezone-aware timestamp required')
    return result


def audit_chronology(records, embargo_hours=24):
    games = {}
    for r in records:
        known, sealed, kickoff = (parse_time(r[k]) for k in ('known_at', 'sealed_at', 'event_at'))
        if not known <= sealed < kickoff:
            raise ValueError('Forecast uses future information or is not sealed before kickoff')
        gid = r['game_id']
        if gid in games and games[gid] != kickoff:
            raise ValueError('Inconsistent kickoff for same game')
        games[gid] = kickoff
    ordered = sorted(games.items(), key=lambda x: (x[1], x[0]))
    folds = []
    for i in range(1, len(ordered)):
        train, test = ordered[:i], ordered[i:]
        if train[-1][1] + timedelta(hours=embargo_hours) <= test[0][1]:
            folds.append({'train_games': [g for g, _ in train], 'test_games': [g for g, _ in test]})
    return {'records': len(records), 'distinct_games': len(games), 'valid_expanding_folds': len(folds),
            'embargo_hours': embargo_hours, 'note': 'Valid chronology is necessary, not evidence of predictive skill.'}


def proper_scores(probabilities, outcomes):
    if len(probabilities) != len(outcomes) or not outcomes or any(o not in (0, 1) for o in outcomes):
        raise ValueError('Aligned binary outcomes required')
    p = [probability(x, closed=True) for x in probabilities]
    brier = statistics.mean((a-b)**2 for a, b in zip(p, outcomes))
    losses = [-(math.log(a) if o else math.log1p(-a)) if 0 < a < 1 else (0 if a == o else float('inf')) for a, o in zip(p, outcomes)]
    return {'n': len(p), 'brier': brier, 'log_loss': statistics.mean(losses) if all(math.isfinite(x) for x in losses) else float('inf')}


def calibration_bins(probabilities, outcomes, bins=10):
    proper_scores(probabilities, outcomes)
    groups = defaultdict(list)
    for p, y in zip(probabilities, outcomes): groups[min(bins-1, int(p*bins))].append((p, y))
    rows = [{'bin': k, 'n': len(v), 'mean_forecast': statistics.mean(x[0] for x in v),
             'observed_rate': statistics.mean(x[1] for x in v)} for k, v in sorted(groups.items())]
    return {'bins': rows, 'ece': sum(len(v)/len(outcomes)*abs(statistics.mean(x[0] for x in v)-statistics.mean(x[1] for x in v)) for v in groups.values())}


def holm(pvalues):
    p = [probability(x, closed=True) for x in pvalues]
    order, prior, adjusted = sorted(range(len(p)), key=lambda i: p[i]), 0, [0]*len(p)
    for rank, index in enumerate(order):
        prior = max(prior, min(1, (len(p)-rank)*p[index]))
        adjusted[index] = prior
    return adjusted


def date_block_return_bound(records, *, replicates=10000, block=7, seed=20261112):
    """Circular date-block bootstrap of net return/unit; whole dates stay together."""
    by_date = defaultdict(lambda: {'profit': 0.0, 'stake': 0.0})
    for r in records:
        day = parse_time(r['event_at']).date().isoformat()
        by_date[day]['profit'] += finite(r['profit'], 'profit')
        by_date[day]['stake'] += finite(r['stake'], 'stake')
    days = sorted(by_date)
    if len(days) < block or any(by_date[d]['stake'] <= 0 for d in days):
        return {'dates': len(days), 'roi': None, 'low': None, 'high': None, 'status': 'Insufficient dates or invalid stake'}
    rng, means, n = random.Random(seed), [], len(days)
    for _ in range(replicates):
        profit = stake = 0.0
        while stake < n:  # equal weight per date in the resampled date sequence
            start = rng.randrange(n)
            for j in range(block):
                item = by_date[days[(start+j) % n]]
                profit += item['profit']; stake += item['stake']
        means.append(profit/stake)
    roi = sum(v['profit'] for v in by_date.values()) / sum(v['stake'] for v in by_date.values())
    return {'dates': n, 'roi': roi, 'low': quantile(means, .025), 'high': quantile(means, .975),
            'replicates': replicates, 'block_dates': block, 'seed': seed,
            'status': 'Assumption-based interval; does not remove luck or adjust for strategy mining'}


def evaluate_gates(evidence):
    rows = []
    for gid, name, rule in GATES:
        item = evidence.get(gid, {})
        status = item.get('status', 'Unknown')
        if status not in ('Pass', 'Fail', 'Unknown'): raise ValueError('Invalid gate status')
        passed = status == 'Pass' and bool(item.get('artifact_sha256')) and bool(item.get('source_ids'))
        rows.append({'id': gid, 'name': name, 'rule': rule, 'status': 'Pass' if passed else 'Fail',
                     'reported_status': status, 'artifact_sha256': item.get('artifact_sha256'),
                     'source_ids': item.get('source_ids', []),
                     'reason': item.get('reason', 'No verified artifact supplied')})
    return {'qualified': all(r['status'] == 'Pass' for r in rows),
            'passed': sum(r['status'] == 'Pass' for r in rows), 'total': len(rows), 'gates': rows}


def leaderboard(candidates, competition):
    """Rank only fully qualified entries in the SAME market/window/offer/stake cohort."""
    eligible, rejected = [], []
    required = ('market', 'window_id', 'offer_universe_sha256', 'stake_policy_id', 'scored_events_sha256')
    for c in candidates:
        reasons = []
        if c.get('market') not in MARKETS: reasons.append('Unknown market')
        if any(not c.get(k) for k in required): reasons.append('Missing cohort identity')
        gates = evaluate_gates(c.get('gate_evidence', {}))
        if not gates['qualified']: reasons.append('Not all 12 gates have verified artifacts')
        for key in ('selections', 'games', 'dates', 'shadow_days', 'shadow_games'):
            minimum = POLICY['min_selections' if key == 'selections' else 'min_games' if key in ('games', 'shadow_games') else 'min_dates' if key == 'dates' else 'shadow_days']
            if not isinstance(c.get(key), int) or c[key] < minimum: reasons.append(key + ' below policy floor')
        for key in ('roi_lower_95', 'clv', 'log_loss', 'holm_p'):
            try: finite(c.get(key), key)
            except ValueError: reasons.append(key + ' missing/invalid')
        if not reasons:
            if c['roi_lower_95'] <= 0 or c['clv'] <= 0 or c['holm_p'] > POLICY['alpha']:
                reasons.append('Conservative performance criteria not met')
            if c['market'] != competition['market'] or any(c.get(k) != competition.get(k) for k in required[1:]):
                reasons.append('Different competition cohort')
        if reasons: rejected.append({'id': c.get('id'), 'reasons': reasons})
        else: eligible.append(c)
    if len({c['id'] for c in eligible}) != len(eligible): raise ValueError('Duplicate eligible strategy identity')
    eligible.sort(key=lambda c: (-c['roi_lower_95'], c['log_loss'], c['sealed_at'], c['id']))
    return {'eligible': [{**c, 'rank': i+1, 'merit_points': (3,2,1)[i] if i < 3 else 0}
                         for i, c in enumerate(eligible)], 'rejected': rejected,
            'cash_rewards': None, 'reward_note': 'Non-transferable, non-monetary merit only; no funded cash prize.'}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
