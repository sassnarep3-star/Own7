"""NFL audit invariants. These test integrity, not the truth of source pages."""
import copy
import unittest
from unittest.mock import patch

from nfl_lab import engine


class NflEngineTests(unittest.TestCase):
    def test_current_results_reproduce(self):
        self.assertEqual(engine.encode(engine.compute()),
                         (engine.ROOT / 'research/nfl-results.json').read_text(encoding='utf-8'))

    def test_receipt_integrity_is_fail_closed(self):
        with patch.object(engine, 'digest', return_value='not-the-original-hash'):
            with self.assertRaisesRegex(ValueError, 'receipt mismatch'):
                engine.verify_nfl_receipts()

    def test_rights_and_cash_cannot_be_enabled(self):
        settings = engine.load_json('research/nfl-protocol.json')
        engine.validate_nfl_rights(settings)
        for field in ('nfl_gambling_use_authorized', 'nfl_derived_betting_prices_enabled', 'bulk_collection_enabled'):
            modified = copy.deepcopy(settings)
            modified['source_rights'][field] = True
            with self.subTest(field=field), self.assertRaises(ValueError):
                engine.validate_nfl_rights(modified)
        modified = copy.deepcopy(settings)
        modified['competition']['cash_payments_enabled'] = True
        with self.assertRaises(ValueError):
            engine.validate_nfl_rights(modified)

    def test_results_do_not_claim_eligibility_or_dependence(self):
        result = engine.compute()
        self.assertEqual(result['leaderboard'], [])
        self.assertIsNone(result['cash_rewards'])
        self.assertTrue(all(entry['status'] == 'Blocked' for entry in result['evaluations']))
        missing = [item for item in result['correlations'] if item['kind'] == 'Not collected']
        self.assertEqual(len(missing), 6)
        self.assertTrue(all(item['pearson'] is None and item['spearman'] is None for item in missing))

    def test_defensive_minimum_summary_matches_all_teams(self):
        rows = engine.load_csv('data/nfl-team-defense-passing-2026.csv')
        lowest = min(rows, key=lambda row: int(row['Yds']))
        self.assertEqual((lowest['Team'], lowest['Yds']), ('Minnesota Vikings', '1495'))

    def test_exploratory_correlations_are_labeled(self):
        correlations = engine.compute()['correlations']
        measured = [item for item in correlations if item['kind'] != 'Not collected']
        self.assertEqual(len(measured), 7)
        self.assertTrue(all(item['status'] == 'Derived · descriptive' for item in measured))
        self.assertAlmostEqual(measured[0]['pearson'], 0.8463, places=4)


if __name__ == '__main__':
    unittest.main()
