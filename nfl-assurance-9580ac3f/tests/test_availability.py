import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import availability as a

ROOT=Path(__file__).resolve().parents[1]
class AvailabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=a.build()
    def test_snapshot_counts(self):
        s=self.data['summary']
        self.assertEqual(s['injury_rows'],276);self.assertEqual(s['teams_with_injury_rows'],26)
        self.assertEqual(s['depth_slots'],289);self.assertEqual(s['depth_teams'],10)
        self.assertEqual(s['offense_slots'],113);self.assertEqual(s['defense_slots'],116)
        self.assertEqual(s['game_status_counts'],{'Blank':270,'Out':5,'Questionable':1})
    def test_every_row_has_official_source(self):
        sources=a.load_sources()
        for key in ('injuries','depth'):
            for row in self.data[key]:
                self.assertTrue(row['source_ids']);self.assertTrue(all(sources[x]['url'].startswith('https://') for x in row['source_ids']))
    def test_blank_is_not_available_or_healthy(self):
        r=next(r for r in self.data['injuries'] if r['player']=='John Bates')
        self.assertIsNone(r['game_status']);self.assertIsNone(r['injury']);self.assertEqual(r['availability'],'Not designated')
    def test_dnp_is_not_out(self):
        r=next(r for r in self.data['injuries'] if r['player']=='Treylon Burks')
        self.assertIsNone(r['game_status']);self.assertEqual(r['availability'],'Not designated')
    def test_out_starter_does_not_confirm_replacement(self):
        r=next(r for r in self.data['depth'] if r['team']=='NE' and r['unit']=='Offense' and r['position']=='LG')
        self.assertTrue(r['first_string_out']);self.assertEqual(r['players'][0],'Ben Brown')
        self.assertIsNone(r['actual_replacement']);self.assertIsNone(r['performance_deficit'])
        rb=next(r for r in self.data['depth'] if r['team']=='NE' and r['unit']=='Offense' and r['position']=='RB')
        self.assertFalse(rb['first_string_out']);self.assertIn('TreVeyon Henderson',rb['later_listed_out'])
    def test_shared_cell_has_no_individual_rank(self):
        r=next(r for r in self.data['depth'] if r['team']=='SEA' and r['position']=='WR' and r['slot']==1)
        self.assertEqual(len(r['entries'][0]['players']),2);self.assertIsNone(r['entries'][0]['rank'])
    def test_blank_second_column_not_compressed(self):
        r=next(r for r in self.data['depth'] if r['team']=='WAS' and r['players'][0]=='Frankie Luvu')
        self.assertIsNone(r['entries'][1]);self.assertEqual(r['entries'][2]['rank'],3);self.assertTrue(r['blank_backup_columns'])
    def test_empty_kicker_not_invented(self):
        r=next(r for r in self.data['depth'] if r['team']=='MIA' and r['position']=='K')
        self.assertEqual(r['players'],['','','','','']);self.assertFalse(r['first_string_out'])
    def test_explicit_aliases_join(self):
        for team,position,name in [('NE','S','Kevin Byard III'),('CLE','FS','Ronnie Hickman'),('AZ','ILB','Mack Wilson Sr.')]:
            r=next(r for r in self.data['depth'] if r['team']==team and r['position']==position and r['players'][0]==name)
            self.assertIsNotNone(r['entries'][0]['practice_status'])
    def test_no_fuzzy_identity_match(self):
        self.assertEqual(a.norm('J.J. McCarthy'),'jjmccarthy');self.assertNotEqual(a.norm('Justin Jefferson'),a.norm('Jaylon Jefferson'))
    def test_fifth_string_not_truncated(self):
        r=next(r for r in self.data['depth'] if r['team']=='PIT' and r['position']=='RB')
        self.assertEqual(r['players'][-1],'Lew Nichols')
    def test_bad_designation_rejected(self):
        with self.assertRaises(ValueError):a.parse_injuries('NE|Test|QB||F|Probable')
    def test_bad_position_unit_rejected(self):
        with self.assertRaises(ValueError):a.parse_depth('NE|Defense|QB|A|B|C|D|E')
    def test_generated_data_deterministic(self):
        before=(ROOT/'data/availability.json').read_bytes();a.write();self.assertEqual(before,(ROOT/'data/availability.json').read_bytes())
    def test_receipt_for_every_data_row(self):
        receipts=json.loads((ROOT/'sources/receipts.json').read_text())['rows']
        ids={r['row_id'] for r in receipts}
        self.assertEqual(len(ids),565)
        self.assertTrue(all(r['id'] in ids for r in self.data['injuries']+self.data['depth']))

if __name__=='__main__':unittest.main()
