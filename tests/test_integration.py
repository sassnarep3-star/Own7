"""Independently cross-check preserved parallel contributions, not external truth."""
import importlib.util
import re
import unittest
from pathlib import Path

from nba_lab.engine import ROOT, load_csv, load_json
from nba_lab.math import pearson


class ParallelIntegrationTests(unittest.TestCase):
    def test_six_team_coefficients_independently_recomputed(self):
        data = load_csv('data/teams-2025-26.csv')
        rows = load_csv('data/team-correlations-2025-26.csv')
        self.assertEqual(len(rows), 6)
        for row in rows:
            a, b = row['Pair'].split(' vs ')
            value = pearson([float(r[a]) for r in data], [float(r[b]) for r in data])
            self.assertEqual(row['r'], f'{value:.3f}')
            self.assertEqual(row['r_squared'], f'{value * value:.3f}')
            self.assertEqual(int(row['n_teams']), len(data))

    def test_eleven_handoff_values_and_intervals_reproduce(self):
        path = ROOT / 'handoff/f58e9526/compute_correlations.py'
        spec = importlib.util.spec_from_file_location('contributed_correlations', path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        stored = load_json('handoff/f58e9526/correlation-computed-2025-26.json')['rows']
        self.assertEqual(len(stored), 11)
        self.assertEqual(stored, module.compute())
        for row, (a, b, _) in zip(stored[:8], module.TEAM_PAIRS):
            data = load_csv('data/teams-2025-26.csv')
            value = pearson([float(r[a]) for r in data], [float(r[b]) for r in data])
            self.assertAlmostEqual(row['_r'], value, places=6)

    def test_every_contributed_review_flag_is_canonical_and_blank(self):
        original = load_json('market-evidence/evidence.json')
        flags = {r['id']: r for r in load_json('research/catalog.json')['flags']}
        mapping = load_json('research/integration.json')['market_source_map']
        for row in original['flags']:
            canonical = flags[row['id']]
            self.assertEqual(canonical['source_ids'], [mapping[k] for k in row['sources']])
            self.assertIsNone(canonical['unverified_value'])
            self.assertEqual(row['unverified_value'], '')

    def test_incoming_file_review_is_complete_and_pinned(self):
        rows = load_json('research/audit/parallel-review.json')
        self.assertEqual(len(rows), 77)
        self.assertEqual(len({r['path'] for r in rows}), 77)
        for row in rows:
            self.assertTrue(re.fullmatch('[a-f0-9]{64}', row['sha256']))
            self.assertIn('/37e1bbde64cd2dedcc1fffb2ba35a0ed2cdb4f11/', row['source_url'])
            self.assertTrue(row['review_scope'])

    def test_netherlands_and_source_rights_gaps_are_not_filled(self):
        flags = {r['id']: r for r in load_json('research/catalog.json')['flags']}
        for key in ('NL01', 'NL02', 'MF06', 'BLKA01'):
            self.assertIsNone(flags[key]['unverified_value'])
            self.assertEqual(flags[key]['status'], 'Needs review')
        self.assertEqual(flags['NL03']['status'], 'Corrected')
        self.assertEqual(flags['F15']['status'], 'Corrected')


if __name__ == '__main__':
    unittest.main()
