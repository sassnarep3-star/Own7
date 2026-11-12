import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build
import check

ROOT=Path(__file__).resolve().parents[1]
class SiteTests(unittest.TestCase):
    def test_static_contract(self):
        result=check.run()
        self.assertEqual(result['errors'],[])
        self.assertEqual(result['status'],'passed')
        self.assertEqual(result['pages'],19)
        self.assertEqual(result['sources'],26)
        self.assertGreaterEqual(result['table_rows'],800)
    def test_manifest_pages_exist(self):
        manifest=json.loads((ROOT/'site/manifest.json').read_text())
        self.assertEqual(manifest['pages'],[name for name,_ in build.PAGES])
        for name in manifest['pages']:
            self.assertTrue((ROOT/'site'/name).is_file(),name)
    def test_deterministic_build(self):
        before={p.name:p.read_bytes() for p in (ROOT/'site').iterdir() if p.is_file()}
        build.write_all()
        after={p.name:p.read_bytes() for p in (ROOT/'site').iterdir() if p.is_file()}
        self.assertEqual(before,after)
    def test_real_metrics_remain_null(self):
        strategies=json.loads((ROOT/'strategies.json').read_text())
        for s in strategies['strategies']:
            for key in ('model_probability','fair_line','correlation','roi','clv'):
                self.assertIsNone(s[key],s['id']+' '+key)
        for c in strategies['correlations']:
            for key in ('n','pearson','phi','joint_rate','interval'):
                self.assertIsNone(c[key],c['id']+' '+key)
    def test_suggestions_are_proposed_not_approved(self):
        decisions=json.loads((ROOT/'decisions.json').read_text())
        self.assertTrue(all(s['decision']=='Proposed' for s in decisions['suggestions']))
    def test_leaderboard_empty_and_cash_null(self):
        decisions=json.loads((ROOT/'strategies.json').read_text())
        self.assertEqual(decisions['competition']['eligible_entries'],0)
        self.assertIsNone(decisions['competition']['cash_pool'])

if __name__=='__main__':unittest.main()
