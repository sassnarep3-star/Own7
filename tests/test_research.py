"""Deterministic unit/data/leakage checks. Synthetic arrays are tests, not NBA evidence."""
import copy
import csv
import json
import math
import unittest
from pathlib import Path

from nba_lab.engine import ROOT, load_csv, load_json, verify_receipts, validate_source_rights
from nba_lab.math import (bernoulli_joint, brier_score, circular_block_interval,
                          decimal_from_american, expected_net, fair_decimal,
                          holm_adjust, implied_probability, joint_hit_rate,
                          log_loss, pearson, proportional_devig, quantile,
                          ranks, spearman)
from nba_lab.models import beta_probability, walk_forward_demo
from nba_lab.validation import GATE_IDS, eligible, rank_entries


class PricingTests(unittest.TestCase):
    def test_american_positive(self):
        self.assertEqual(decimal_from_american(150), 2.5)

    def test_american_negative(self):
        self.assertAlmostEqual(decimal_from_american(-110), 21 / 11)

    def test_invalid_american(self):
        for v in (0, 50, -90, math.nan, math.inf, True):
            with self.subTest(value=v), self.assertRaises(ValueError):
                decimal_from_american(v)

    def test_implied(self):
        self.assertEqual(implied_probability(2), 0.5)

    def test_invalid_decimal(self):
        for v in (0, 1, -1, math.inf, math.nan):
            with self.subTest(value=v), self.assertRaises(ValueError):
                implied_probability(v)

    def test_devig(self):
        self.assertEqual(proportional_devig([1.9, 1.9]), [0.5, 0.5])
        self.assertAlmostEqual(sum(proportional_devig([2, 3, 4])), 1)

    def test_incomplete_devig(self):
        with self.assertRaises(ValueError):
            proportional_devig([2])

    def test_fair_price(self):
        self.assertEqual(fair_decimal(0.4), 2.5)
        self.assertIsNone(fair_decimal(0))

    def test_push_price(self):
        self.assertAlmostEqual(fair_decimal(0.4, 0.2), 2)
        self.assertAlmostEqual(expected_net(0.4, 2, 0.2), 0)

    def test_ev(self):
        self.assertAlmostEqual(expected_net(0.6, 2), 0.2)

    def test_invalid_settlement(self):
        with self.assertRaises(ValueError):
            expected_net(0.8, 2, 0.4)
        with self.assertRaises(ValueError):
            fair_decimal(0.8, 0.4)

    def test_two_bernoulli_joint(self):
        self.assertAlmostEqual(bernoulli_joint(0.5, 0.5, 0.4), 0.35)
        self.assertAlmostEqual(bernoulli_joint(0.5, 0.5, 0), 0.25)

    def test_infeasible_joint(self):
        for args in ((0.1, 0.9, 1), (0, 0.5, 0), (0.5, 0.5, 2)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                bernoulli_joint(*args)


class StatisticsTests(unittest.TestCase):
    def test_scipy_documented_example(self):
        # Official SciPy pearsonr example, not a model result.
        self.assertAlmostEqual(pearson([1, 2, 3, 4, 5, 6, 7], [10, 9, 2.5, 6, 4, 3, 2]), -0.828503883588428)

    def test_perfect_correlations(self):
        self.assertAlmostEqual(pearson([1, 2, 3], [2, 4, 6]), 1)
        self.assertAlmostEqual(pearson([1, 2, 3], [6, 4, 2]), -1)

    def test_undefined_is_not_zero(self):
        self.assertIsNone(pearson([1, 1, 1], [1, 2, 3]))

    def test_zero_does_not_mean_independence(self):
        self.assertAlmostEqual(pearson([-2, -1, 0, 1, 2], [4, 1, 0, 1, 4]), 0)

    def test_misaligned(self):
        for x, y in (([1], [1]), ([1, 2], [1, 2, 3])):
            with self.assertRaises(ValueError):
                pearson(x, y)

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            pearson([1, math.nan], [2, 3])

    def test_tied_ranks(self):
        self.assertEqual(ranks([2, 1, 2, 4]), [2.5, 1, 2.5, 4])

    def test_spearman(self):
        self.assertAlmostEqual(spearman([1, 2, 2, 3], [5, 4, 4, 1]), -1)

    def test_joint_hits(self):
        self.assertEqual(joint_hit_rate([1, 1, 0, 0], [1, 0, 1, 0]), 0.25)

    def test_nonbinary_hits(self):
        with self.assertRaises(ValueError):
            joint_hit_rate([1, 2], [1, 0])

    def test_quantiles(self):
        self.assertEqual(quantile([0, 10], 0.25), 2.5)
        with self.assertRaises(ValueError):
            quantile([], 0.5)

    def test_bootstrap_deterministic(self):
        a, b = [1, 4, 2, 8, 3, 5], [3, 1, 2, 6, 4, 5]
        options = dict(draws=500, block_length=2, seed=7)
        self.assertEqual(circular_block_interval(a, b, **options), circular_block_interval(a, b, **options))

    def test_bootstrap_undefined(self):
        result = circular_block_interval([1] * 6, [1, 2, 3, 4, 5, 6], draws=100, block_length=2)
        self.assertIsNone(result['low'])
        self.assertEqual(result['valid_resamples'], 0)

    def test_invalid_bootstrap(self):
        for params in (dict(draws=2), dict(block_length=6), dict(block_length=1.5), dict(confidence=1)):
            with self.subTest(params=params), self.assertRaises(ValueError):
                circular_block_interval([1, 2, 3, 4, 5, 6], [2, 3, 4, 5, 6, 7], **params)

    def test_log_loss(self):
        self.assertAlmostEqual(log_loss([1, 0], [0.5, 0.5]), math.log(2))
        self.assertEqual(log_loss([1, 0], [1, 0]), 0)
        self.assertEqual(log_loss([1], [0]), math.inf)

    def test_brier(self):
        self.assertEqual(brier_score([1, 0], [0.5, 0.5]), 0.25)

    def test_invalid_scores(self):
        for func in (log_loss, brier_score):
            with self.assertRaises(ValueError):
                func([], [])
            with self.assertRaises(ValueError):
                func([2], [0.5])

    def test_holm(self):
        expected = [0.03, 0.06, 0.06]
        for x, y in zip(holm_adjust([0.01, 0.04, 0.03]), expected):
            self.assertAlmostEqual(x, y)
        self.assertEqual(holm_adjust([]), [])
        with self.assertRaises(ValueError):
            holm_adjust([1.1])


class DataAndModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = load_csv('data/jokic-games-2025-26.csv')
        cls.settings = load_json('research/protocol.json')['demo']

    def test_receipts_match(self):
        verify_receipts()

    def test_complete_explicit_window(self):
        self.assertEqual(len(self.games), 32)
        self.assertEqual(len({g['GameID'] for g in self.games}), 32)
        self.assertEqual(self.games[0]['Date'], '2026-02-01')
        self.assertEqual(self.games[-1]['Date'], '2026-04-12')

    def test_transcript_row_by_row(self):
        evidence = load_csv('research/evidence/jokic-window-transcript.csv')
        for source, row in zip(evidence, self.games):
            self.assertEqual(source, {k: row[k] for k in source})

    def test_normalized_evidence(self):
        for stem in ('teams-2025-26', 'players-2025-26-top15', 'standings-2026-27'):
            self.assertEqual(load_csv(f'data/{stem}.csv'), load_csv(f'research/evidence/{stem}-normalized.csv'))

    def test_observation_counts(self):
        receipts = load_json('research/evidence/receipts.json')
        self.assertEqual(sum(x['retained_rows'] for x in receipts), 107)

    def test_team_arithmetic(self):
        rows = load_csv('data/teams-2025-26.csv')
        self.assertEqual(sum(int(r['W']) for r in rows), 1230)
        self.assertEqual(sum(int(r['L']) for r in rows), 1230)
        for r in rows:
            self.assertEqual(int(r['GP']), int(r['W']) + int(r['L']))
            self.assertAlmostEqual(float(r['WIN%']), int(r['W']) / int(r['GP']), delta=0.00051)

    def test_standings_arithmetic(self):
        rows = load_csv('data/standings-2026-27.csv')
        self.assertEqual(sum(int(r['W']) for r in rows), sum(int(r['L']) for r in rows))
        self.assertEqual(min(int(r['W']) + int(r['L']) for r in rows), 5)
        self.assertEqual(max(int(r['W']) + int(r['L']) for r in rows), 8)

    def test_corrected_maxima(self):
        rows = load_csv('data/teams-2025-26.csv')
        self.assertEqual(max(rows, key=lambda r: float(r['PTS']))['Team'], 'Denver Nuggets')
        self.assertEqual(max(rows, key=lambda r: float(r['FG%']))['Team'], 'Los Angeles Lakers')
        self.assertEqual(next(r for r in rows if r['Team'] == 'Utah Jazz')['Rank'], '26')

    def test_beta_prior(self):
        self.assertEqual(beta_probability(0, 0), 0.5)
        self.assertEqual(beta_probability(3, 4), 4 / 6)
        with self.assertRaises(ValueError):
            beta_probability(5, 4)

    def test_demo_count_and_blanks(self):
        result = walk_forward_demo(self.games, self.settings)
        self.assertEqual(len(result['forecasts']), 88)
        self.assertEqual(len(result['summaries']), 4)
        for f in result['forecasts']:
            self.assertLess(f['train_end'], f['date'])
            for metric in ('market_decimal', 'edge', 'roi', 'clv', 'fair_model_decimal'):
                self.assertIsNone(f[metric])

    def test_current_and_future_outcomes_do_not_change_current_probability(self):
        before = walk_forward_demo(self.games, self.settings)
        changed = copy.deepcopy(self.games)
        for i in range(15, len(changed)):
            changed[i]['PTS'] = '99'
        after = walk_forward_demo(changed, self.settings)
        original = {(f['event'], f['game_id']): f for f in before['forecasts']}
        for f in after['forecasts']:
            if f['date'] <= self.games[15]['Date']:
                self.assertEqual(f['p_model'], original[f['event'], f['game_id']]['p_model'])

    def test_joint_demo_uses_joint_hits(self):
        result = walk_forward_demo(self.games, self.settings)
        combo = next(f for f in result['forecasts'] if f['event'] == 'PTS + AST combo')
        hits = sum(float(g['PTS']) > 27.5 and float(g['AST']) > 10.5 for g in self.games[:10])
        self.assertEqual(combo['p_model'], (hits + 1) / 12)

    def test_reject_duplicate_and_unsorted_games(self):
        for games in (self.games + [self.games[-1]], self.games[::-1]):
            with self.assertRaises(ValueError):
                walk_forward_demo(games, self.settings)

    def test_rights_fail_closed(self):
        rights = load_json('research/protocol.json')['source_rights']
        self.assertFalse(rights['nba_derived_betting_prices_enabled'])
        self.assertFalse(rights['bulk_collection_enabled'])
        self.assertFalse(rights['nba_gambling_use_authorized'])


class GateTests(unittest.TestCase):
    def fixture(self):
        # Synthetic contract validator fixture; not a real eligible strategy.
        return {'strategy_id': 'synthetic-test', 'category': 'Single bets',
                'gate_evidence': {g: {'status': 'pass', 'artifact_url': 'https://github.com/sassnarep3-star/Own7'} for g in GATE_IDS},
                'test_window_id': 'synthetic', 'stake_policy_id': 'synthetic',
                'offer_universe_id': 'synthetic', 'evaluation_event_set_hash': 'synthetic',
                'roi_lcb95': 0.01, 'log_loss': 0.6, 'frozen_at': '2020-01-01T00:00:00Z'}

    def test_missing_gates_rejected(self):
        self.assertFalse(eligible({}))
        item = self.fixture(); del item['gate_evidence']['G01']
        self.assertFalse(eligible(item))

    def test_missing_evidence_rejected(self):
        item = self.fixture(); item['gate_evidence']['G01']['artifact_url'] = ''
        self.assertFalse(eligible(item))

    def test_partial_or_blocked_rejected(self):
        for status in ('partial', 'blocked', 'not run', 'fail'):
            item = self.fixture(); item['gate_evidence']['G01']['status'] = status
            self.assertFalse(eligible(item))

    def test_single_exemption_explicit(self):
        item = self.fixture(); item['gate_evidence']['G05']['status'] = 'not applicable'
        self.assertTrue(eligible(item))
        item['category'] = 'Parlays'
        self.assertFalse(eligible(item))

    def test_incomparable_or_invalid_scores_rejected(self):
        for field, value in (('test_window_id', None), ('roi_lcb95', -0.1), ('log_loss', math.nan)):
            item = self.fixture(); item[field] = value
            with self.assertRaises(ValueError):
                rank_entries([item])

    def test_merit_only_no_cash(self):
        result = rank_entries([self.fixture()])
        self.assertEqual(result[0]['merit_points'], 3)
        self.assertIsNone(result[0]['cash_reward'])

    def test_malformed_evidence_denied(self):
        for bad in (None, [], 'pass'):
            item = self.fixture(); item['gate_evidence']['G01'] = bad
            self.assertFalse(eligible(item))
        item = self.fixture(); item['gate_evidence']['G01']['artifact_url'] = None
        self.assertFalse(eligible(item))

    def test_common_universe_required(self):
        for field in ('offer_universe_id', 'evaluation_event_set_hash'):
            a, b = self.fixture(), self.fixture(); b['strategy_id'] = 'second'; b[field] = 'different'
            with self.assertRaises(ValueError):
                rank_entries([a, b])

    def test_duplicate_entry_and_invalid_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            rank_entries([self.fixture(), self.fixture()])
        for stamp in ('', 'not a date', '2020-01-01T00:00:00'):
            item = self.fixture(); item['frozen_at'] = stamp
            with self.assertRaises(ValueError):
                rank_entries([item])

    def test_ranking_and_separate_categories(self):
        a, b, c = self.fixture(), self.fixture(), self.fixture()
        a['strategy_id'] = 'A'; b['strategy_id'] = 'B'; b['roi_lcb95'] = 0.02
        c['strategy_id'] = 'C'; c['category'] = 'Parlays'
        result = rank_entries([a, b, c])
        singles = [r for r in result if r['category'] == 'Single bets']
        self.assertEqual([r['strategy_id'] for r in singles], ['B', 'A'])
        self.assertEqual([r['merit_points'] for r in singles], [3, 2])
        self.assertEqual(next(r for r in result if r['strategy_id'] == 'C')['rank'], 1)

    def test_rights_config_cannot_silently_enable_operations(self):
        settings = load_json('research/protocol.json')
        validate_source_rights(settings)
        for key in ('nba_gambling_use_authorized', 'nba_derived_betting_prices_enabled', 'bulk_collection_enabled'):
            for value in (None, True):
                changed = copy.deepcopy(settings); changed['source_rights'][key] = value
                with self.assertRaises(ValueError):
                    validate_source_rights(changed)
        changed = copy.deepcopy(settings); changed['competition']['cash_payments_enabled'] = True
        with self.assertRaises(ValueError):
            validate_source_rights(changed)

    def test_actual_leaderboard_empty(self):
        results = load_json('research/results.json')
        self.assertEqual(rank_entries(results['evaluations']), [])
        self.assertTrue(all(not eligible(e) for e in results['evaluations']))
        self.assertTrue(all(e['roi'] is None for e in results['evaluations']))


if __name__ == '__main__':
    unittest.main()
