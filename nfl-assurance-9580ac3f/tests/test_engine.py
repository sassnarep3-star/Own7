import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import engine as e


class PricingTests(unittest.TestCase):
    def test_american_conversion(self):
        self.assertEqual(e.american_decimal(150), 2.5)
        self.assertAlmostEqual(e.american_decimal(-150), 5/3)
        self.assertEqual(e.decimal_american(2), 100)
        self.assertEqual(e.decimal_american(1.5), -200)
        for p in (0, 99, -99, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError): e.american_decimal(p)

    def test_no_vig(self):
        p = e.devig_two_way([1.9, 1.9])
        self.assertEqual(p, [.5, .5])
        q = e.devig_two_way([1.7, 2.2])
        self.assertAlmostEqual(sum(q), 1)
        self.assertGreater(q[0], q[1])
        with self.assertRaises(ValueError): e.devig_two_way([2, 2])
        with self.assertRaises(ValueError): e.devig_two_way([2, 2, 2])

    def test_expected_value_and_settlement(self):
        self.assertAlmostEqual(e.expected_value(.6, 2), .2)
        self.assertAlmostEqual(e.expected_value(.5, 2), 0)
        self.assertEqual(e.settle(10, 2.5, 'win'), 15)
        self.assertEqual(e.settle(10, 2.5, 'loss'), -10)
        self.assertEqual(e.settle(10, 2.5, 'push'), 0)
        self.assertEqual(e.settle(10, 2.5, 'void'), 0)

    def test_synthetic_spread_and_total(self):
        spread = e.originate_research('spread', margin_mean=3, margin_sd=10, spread=-3.5)
        self.assertAlmostEqual(spread['p_cover'], e.phi(-.05))
        total = e.originate_research('total', total_mean=44, total_sd=12, total=43.5)
        self.assertAlmostEqual(total['p_cover'], e.phi(.5/12))
        self.assertFalse(spread['publication_authorized'])
        self.assertFalse(total['publication_authorized'])

    def test_integer_lines_abstain(self):
        with self.assertRaises(ValueError): e.originate_research('spread', margin_mean=3, margin_sd=10, spread=-3)
        with self.assertRaises(ValueError): e.originate_research('total', total_mean=44, total_sd=12, total=44)

    def test_moneyline_tie_push(self):
        r = e.originate_research('moneyline', p_home=.5, p_away=.4, p_tie=.1)
        self.assertAlmostEqual(r['p_cover'], 5/9)
        self.assertAlmostEqual(r['push_probability'], .1)
        with self.assertRaises(ValueError): e.originate_research('moneyline', p_home=.5, p_away=.5, p_tie=.1)

    def test_missing_inputs_never_become_defaults(self):
        with self.assertRaises(ValueError): e.originate_research('spread')
        with self.assertRaises(ValueError): e.originate_research('total', total_mean=44, total_sd=0, total=43.5)


class DependenceTests(unittest.TestCase):
    def test_pearson_known_values(self):
        self.assertAlmostEqual(e.pearson([1,2,3], [2,4,6]), 1)
        self.assertAlmostEqual(e.pearson([1,2,3], [6,4,2]), -1)
        self.assertIsNone(e.pearson([1,1,1], [1,2,3]))

    def test_spearman_ties(self):
        self.assertAlmostEqual(e.spearman([1,2,2,4], [1,2,3,4]), 0.9486832980505138)
        self.assertEqual(e.ranks([10,20,20,40]), [1,2.5,2.5,4])

    def test_zero_correlation_not_independence(self):
        self.assertAlmostEqual(e.pearson([-1,0,1], [1,0,1]), 0)
        self.assertNotEqual(len(set(zip([-1,0,1], [1,0,1]))), 9)

    def test_joint_rate_not_product(self):
        r = e.joint_binary([(1,1,1),(1,0,0),(0,1,0),(0,0,0)])
        self.assertEqual(r['joint'], .25)
        self.assertEqual(r['independence_product'], .25)
        self.assertAlmostEqual(r['phi'], 0)
        exclusive = e.joint_binary([(1,0,0),(0,1,0),(1,0,0),(0,1,0)])
        self.assertEqual(exclusive['joint'], 0)
        self.assertAlmostEqual(exclusive['phi'], -1)
        r = e.joint_binary([(1,1,1),(1,1,1),(0,0,0),(0,0,0)])
        self.assertEqual(r['joint'], .5)
        self.assertNotEqual(r['joint'], r['independence_product'])

    def test_contradictory_joint_rejected(self):
        with self.assertRaises(ValueError): e.joint_binary([(1,1,0)])

    def test_frechet_bounds(self):
        bounds = e.frechet_many([.8,.7,.6])
        self.assertAlmostEqual(bounds['low'], .1)
        self.assertAlmostEqual(bounds['high'], .6)
        self.assertEqual(bounds['note'], e.frechet_many([.8,.7])['note'])
        self.assertEqual(e.frechet_many([.2,.3])['low'], 0)

    def test_bootstrap_reproducible_and_preserves_pairs(self):
        x = list(range(20)); y = [v*2 + (v%3) for v in x]
        a = e.paired_block_interval(x,y,replicates=200,block=5,seed=7)
        b = e.paired_block_interval(x,y,replicates=200,block=5,seed=7)
        self.assertEqual(a,b)
        self.assertLessEqual(a['low'], a['estimate'])
        self.assertGreaterEqual(a['high'], a['estimate'])
        self.assertIsNone(e.paired_block_interval([1,1,1],[1,2,3])['low'])


class ChronologyTests(unittest.TestCase):
    def records(self):
        return [
            {'game_id':'a','known_at':'2026-01-01T00:00:00Z','sealed_at':'2026-01-01T01:00:00Z','event_at':'2026-01-03T00:00:00Z','label_available_at':'2026-01-03T04:00:00Z'},
            {'game_id':'b','known_at':'2026-01-04T00:00:00Z','sealed_at':'2026-01-04T01:00:00Z','event_at':'2026-01-06T00:00:00Z','label_available_at':'2026-01-06T04:00:00Z'},
            {'game_id':'c','known_at':'2026-01-08T00:00:00Z','sealed_at':'2026-01-08T01:00:00Z','event_at':'2026-01-10T00:00:00Z','label_available_at':'2026-01-10T04:00:00Z'}]

    def test_chronology_and_embargo(self):
        r = e.audit_chronology(self.records())
        self.assertEqual(r['distinct_games'],3)
        self.assertEqual(r['valid_expanding_folds'],2)
        self.assertEqual(e.audit_chronology(self.records(),embargo_hours=97)['valid_expanding_folds'],0)

    def test_missing_label_time_blocks_fold(self):
        rows=self.records()
        for row in rows: del row['label_available_at']
        result=e.audit_chronology(rows)
        self.assertEqual(result['valid_expanding_folds'],0)
        self.assertEqual(result['folds_missing_label_time'],2)

    def test_future_leakage_rejected(self):
        rows=self.records();rows[0]['known_at']='2026-01-04T00:00:00Z'
        with self.assertRaises(ValueError): e.audit_chronology(rows)

    def test_naive_timestamp_rejected(self):
        rows=self.records();rows[0]['sealed_at']='2026-01-01T01:00:00'
        with self.assertRaises(ValueError): e.audit_chronology(rows)

    def test_proper_scores_and_calibration(self):
        self.assertAlmostEqual(e.proper_scores([.5,.5],[0,1])['brier'],.25)
        self.assertAlmostEqual(e.proper_scores([.5,.5],[0,1])['log_loss'],math.log(2))
        self.assertEqual(e.proper_scores([0,1],[0,1])['log_loss'],0)
        self.assertTrue(math.isinf(e.proper_scores([0,1],[1,0])['log_loss']))
        self.assertAlmostEqual(e.calibration_bins([.1,.9],[0,1])['ece'],.1)

    def test_holm_known_example(self):
        self.assertEqual(e.holm([.01,.04,.03]), [.03,.06,.06])
        self.assertEqual(e.holm([]),[])

    def test_date_block_bound_reproducible(self):
        rows=[{'event_at':f'2026-01-{i+1:02}T00:00:00Z','profit':.1 if i%2 else -.05,'stake':1} for i in range(14)]
        a=e.date_block_return_bound(rows,replicates=200,block=7,seed=9)
        b=e.date_block_return_bound(rows,replicates=200,block=7,seed=9)
        self.assertEqual(a,b);self.assertEqual(a['dates'],14)
        self.assertLessEqual(a['low'],a['roi']);self.assertGreaterEqual(a['high'],a['roi'])


class CompetitionTests(unittest.TestCase):
    def candidate(self, ident='s1'):
        return {'id':ident,'market':'Single bets','window_id':'future-v1','offer_universe_sha256':'a'*64,
                'stake_policy_id':'flat-v1','scored_events_sha256':'b'*64,'selections':500,'games':200,'dates':60,
                'shadow_days':60,'shadow_games':200,'roi_lower_95':.01,'clv':.01,'log_loss':.65,'holm_p':.01,
                'sealed_at':'2026-01-01T00:00:00Z','gate_evidence':{g:{'status':'Pass','artifact_sha256':'c'*64,'source_ids':['REPO']} for g,_,_ in e.GATES}}

    def cohort(self):
        return {k:self.candidate()[k] for k in ('market','window_id','offer_universe_sha256','stake_policy_id','scored_events_sha256')}

    def test_empty_real_competition(self):
        r=e.leaderboard([],self.cohort());self.assertEqual(r['eligible'],[]);self.assertIsNone(r['cash_rewards'])

    def test_unknown_gate_fails_closed(self):
        c=self.candidate();del c['gate_evidence']['G01']
        r=e.leaderboard([c],self.cohort());self.assertFalse(r['eligible']);self.assertIn('Not all 12 gates',r['rejected'][0]['reasons'][0])

    def test_pass_without_artifact_fails(self):
        c=self.candidate();c['gate_evidence']['G01']['artifact_sha256']=None
        self.assertFalse(e.evaluate_gates(c['gate_evidence'])['qualified'])

    def test_synthetic_qualification_and_merit_only(self):
        candidates=[self.candidate('s3'),self.candidate('s1'),self.candidate('s2')]
        candidates[0]['roi_lower_95']=.03;candidates[1]['roi_lower_95']=.02
        r=e.leaderboard(candidates,self.cohort())
        self.assertEqual([x['id'] for x in r['eligible']],['s3','s1','s2'])
        self.assertEqual([x['merit_points'] for x in r['eligible']],[3,2,1]);self.assertIsNone(r['cash_rewards'])

    def test_mismatched_window_rejected(self):
        c=self.candidate();c['window_id']='other'
        self.assertFalse(e.leaderboard([c],self.cohort())['eligible'])

    def test_small_sample_and_nonpositive_bound_rejected(self):
        c=self.candidate();c['selections']=499
        self.assertFalse(e.leaderboard([c],self.cohort())['eligible'])
        c=self.candidate();c['roi_lower_95']=0
        self.assertFalse(e.leaderboard([c],self.cohort())['eligible'])

    def test_duplicate_identity_rejected(self):
        with self.assertRaises(ValueError):e.leaderboard([self.candidate(),self.candidate()],self.cohort())


if __name__=='__main__':unittest.main()
