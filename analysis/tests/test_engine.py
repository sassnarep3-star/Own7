"""Self-tests for the line-origination engine.

These tests exist so that a reader can check the arithmetic rather than trust
it. Where a closed form exists, the test uses the closed form:

* P(X<0, Y<0) for a standard bivariate normal with correlation rho is exactly
  1/4 + arcsin(rho)/(2*pi). That pins the bivariate CDF implementation.
* A normal CDF value is checked against a textbook value.
* Independence is checked by requiring the correlated formula to reduce to the
  product when phi = 0.
* Shrinkage is checked for its two limits: 0 games -> league mean, infinite
  games -> observed value.
* Log-loss, ROI bounds and binomial tests are checked against hand-computable
  cases.

Run: python3 -m unittest discover -s analysis/tests -v
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine import correlation, gates, leaderboard, markets, ratings, skill  # noqa: E402


class TestDistributions(unittest.TestCase):
    def test_normal_cdf_textbook(self):
        # Phi(1.96) = 0.9750021..., Phi(0) = 0.5
        self.assertAlmostEqual(ratings.normal_cdf(0.0), 0.5, places=12)
        self.assertAlmostEqual(ratings.normal_cdf(1.959963985), 0.975, places=9)
        self.assertAlmostEqual(ratings.normal_cdf(-1.959963985), 0.025, places=9)

    def test_inverse_normal_roundtrip(self):
        for p in (0.01, 0.05, 0.5, 0.84, 0.975, 0.999):
            z = markets._z(p)
            self.assertAlmostEqual(ratings.normal_cdf(z), p, places=6, msg=f"roundtrip failed at p={p}")

    def test_bivariate_normal_closed_form(self):
        # P(X<0, Y<0) = 1/4 + arcsin(rho) / (2*pi)
        for rho in (-0.9, -0.5, -0.2, 0.0, 0.2, 0.5, 0.9):
            expected = 0.25 + math.asin(rho) / (2 * math.pi)
            got = markets._bivariate_normal_cdf(0.0, 0.0, rho)
            self.assertAlmostEqual(got, expected, places=6, msg=f"rho={rho}: {got} vs {expected}")

    def test_bivariate_reduces_to_independence_at_zero(self):
        for h, k in ((0.0, 0.0), (0.5, -1.2), (2.0, 0.3), (-0.7, 1.1)):
            got = markets._bivariate_normal_cdf(h, k, 0.0)
            expected = ratings.normal_cdf(h) * ratings.normal_cdf(k)
            self.assertAlmostEqual(got, expected, places=10)

    def test_bivariate_monotone_in_rho(self):
        vals = [markets._bivariate_normal_cdf(0.4, 0.4, r) for r in (-0.8, -0.4, 0.0, 0.4, 0.8)]
        self.assertEqual(vals, sorted(vals), "joint upper-tail probability must increase with rho")


class TestShrinkage(unittest.TestCase):
    def test_limits(self):
        self.assertAlmostEqual(ratings.shrunk_net_rating(12.0, 0, 0.0), 0.0)
        self.assertAlmostEqual(ratings.shrunk_net_rating(12.0, 10_000_000, 0.0), 12.0, places=4)

    def test_weight_formula(self):
        self.assertAlmostEqual(ratings.shrinkage_weight(8, 20), 8 / 28, places=12)
        self.assertAlmostEqual(ratings.shrinkage_weight(20, 20), 0.5, places=12)

    def test_shrunk_always_between_observed_and_mean(self):
        for gp in (1, 5, 8, 40, 82):
            v = ratings.shrunk_net_rating(15.0, gp, 0.0, 20)
            self.assertGreater(v, 0.0)
            self.assertLess(v, 15.0)

    def test_real_snapshot_shrinks_champion(self):
        snap = ratings.load_ratings("2026-27")
        s = ratings.shrunk_ratings(snap)
        hou = s["teams"]["HOU"]
        self.assertEqual(hou["net_rtg_raw"], 12.8)
        self.assertLess(hou["net_rtg_shrunk"], hou["net_rtg_raw"])
        self.assertGreater(hou["shrink_weight"], 0.2)
        self.assertLess(hou["shrink_weight"], 0.3)

    def test_all_30_teams_present(self):
        snap = ratings.load_ratings("2026-27")
        self.assertEqual(len(snap["rows"]), 30)
        self.assertEqual(len({r["abbr"] for r in snap["rows"]}), 30)


class TestPricing(unittest.TestCase):
    def test_fair_odds_is_inverse(self):
        self.assertAlmostEqual(markets.fair_decimal_odds(0.5), 2.0)
        self.assertAlmostEqual(markets.fair_decimal_odds(0.25), 4.0)
        self.assertIsNone(markets.fair_decimal_odds(0.0))
        self.assertIsNone(markets.fair_decimal_odds(1.0))

    def test_expected_value_requires_market_price(self):
        self.assertIsNone(markets.expected_value_per_unit(0.55, None))
        # A fair price has zero EV by construction.
        self.assertAlmostEqual(markets.expected_value_per_unit(0.5, 2.0), 0.0)
        # -110 with a true 52.38% is break-even.
        self.assertAlmostEqual(markets.expected_value_per_unit(0.5238, 1.909), 0.0, places=3)

    def test_two_way_devig(self):
        out = markets.remove_two_way_vig(1.909, 1.909)
        self.assertAlmostEqual(out["overround"], 1.0477, places=3)
        self.assertAlmostEqual(out["hold_pct"], 4.77, places=1)
        self.assertAlmostEqual(out["fair_home_prob"], 0.5, places=6)
        self.assertAlmostEqual(out["fair_home_prob"] + out["fair_away_prob"], 1.0, places=9)

    def test_probabilities_sum_to_one(self):
        snap = ratings.load_ratings("2026-27")
        proj = markets.game_projection(snap, "DET", "PHI")
        self.assertAlmostEqual(proj["model_home_win_prob"] + proj["model_away_win_prob"], 1.0, places=6)
        self.assertFalse(proj["is_market_price"])

    def test_spread_sign_convention(self):
        """A clearly better home team must be favoured (negative spread)."""
        snap = ratings.load_ratings("2026-27")
        # HOU (raw +12.8) hosts MIN; HOU should be favoured.
        proj = markets.game_projection(snap, "HOU", "MIN")
        self.assertLess(proj["model_spread_home"], 0)
        self.assertGreater(proj["model_home_win_prob"], 0.5)


class TestParlayCorrelation(unittest.TestCase):
    def test_independent_legs_multiply(self):
        out = markets.parlay_probability_from_correlation(0.6, 0.4, 0.0)
        self.assertTrue(out["ok"])
        self.assertAlmostEqual(out["joint_probability"], 0.24, places=5)
        self.assertAlmostEqual(out["independence_gap"], 0.0, places=5)

    def test_positive_correlation_raises_joint(self):
        out = markets.parlay_probability_from_correlation(0.6, 0.6, 0.5)
        self.assertGreater(out["joint_probability"], 0.36)

    def test_negative_correlation_lowers_joint(self):
        out = markets.parlay_probability_from_correlation(0.6, 0.6, -0.5)
        self.assertLess(out["joint_probability"], 0.36)

    def test_degenerate_rho_rejected(self):
        self.assertFalse(markets.parlay_probability_from_correlation(0.5, 0.5, 1.0)["ok"])

    def test_independent_parlay_product(self):
        self.assertAlmostEqual(markets.parlay_probability_independent([0.5, 0.5, 0.5]), 0.125)

    def test_player_correlation_refuses(self):
        out = correlation.player_pair_correlation()
        self.assertFalse(out["ok"])
        self.assertTrue(out["what_would_be_needed"])


class TestCorrelationMath(unittest.TestCase):
    def test_pearson_perfect(self):
        out = correlation.pearson([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
        self.assertAlmostEqual(out["r"], 1.0, places=9)

    def test_pearson_negative(self):
        out = correlation.pearson([1, 2, 3, 4, 5], [10, 8, 6, 4, 2])
        self.assertAlmostEqual(out["r"], -1.0, places=9)

    def test_pearson_zero_variance(self):
        self.assertFalse(correlation.pearson([1, 1, 1, 1], [1, 2, 3, 4])["ok"])

    def test_phi_known_table(self):
        # 2x2: n11=10, n10=0, n01=0, n00=10 -> phi = 1
        a = [True] * 10 + [False] * 10
        b = [True] * 10 + [False] * 10
        self.assertAlmostEqual(correlation.phi_coefficient(a, b)["phi"], 1.0, places=9)

    def test_phi_independence(self):
        a = [True, True, False, False] * 5
        b = [True, False, True, False] * 5
        self.assertAlmostEqual(correlation.phi_coefficient(a, b)["phi"], 0.0, places=9)

    def test_sample_size_grows_as_interval_narrows(self):
        wide = correlation.sample_size_requirement(0.3, 0.25)["approx_games_needed"]
        narrow = correlation.sample_size_requirement(0.3, 0.10)["approx_games_needed"]
        self.assertGreater(narrow, wide)

    def test_real_game_correlation_runs(self):
        games = []
        import json
        with (ROOT / "data" / "official-team-games-2026-27.json").open() as fh:
            games = json.load(fh)["rows"]
        self.assertEqual(len(games), 18)
        out = correlation.home_away_points(games)
        self.assertTrue(out["ok"])
        # r must be inside its own confidence interval
        self.assertLessEqual(out["ci95"][0], out["r"])
        self.assertGreaterEqual(out["ci95"][1], out["r"])


class TestSkillTests(unittest.TestCase):
    def test_binomial_at_break_even_is_insignificant(self):
        out = skill.binomial_p_value(100, 100, 0.5)
        self.assertGreater(out["p_value"], 0.4)

    def test_binomial_strong_edge(self):
        out = skill.binomial_p_value(600, 400, 0.5)
        self.assertLess(out["p_value"], 1e-6)
        self.assertEqual(out["verdict"], "strong evidence against pure chance (still not proof of skill)")

    def test_binomial_at_vig_break_even(self):
        # 52.38% is break-even at -110; a 55% record over 1000 bets must clear.
        out = skill.binomial_p_value(550, 450, 0.5238)
        # Honest anchor: 55% over 1000 bets is only just at the 5% line
        # (p ~= 0.052) because 52.38% is a demanding break-even.
        self.assertLess(out["p_value"], 0.10)
        self.assertGreater(out["p_value"], 0.01)

    def test_psr_of_zero_mean_is_half(self):
        out = skill.probabilistic_sharpe_ratio([1.0, -1.0] * 50)
        self.assertAlmostEqual(out["psr"], 0.5, places=2)

    def test_psr_rises_with_real_edge(self):
        weak = skill.probabilistic_sharpe_ratio([1.909 - 1] * 52 + [-1.0] * 48)
        strong = skill.probabilistic_sharpe_ratio([1.909 - 1] * 60 + [-1.0] * 40)
        self.assertGreater(strong["psr"], weak["psr"])

    def test_psr_needs_sample(self):
        self.assertFalse(skill.probabilistic_sharpe_ratio([1.0, -1.0])["ok"])

    def test_expected_max_sharpe_increases_with_trials(self):
        vals = [skill.expected_max_sharpe_of_n_trials(n) for n in (1, 10, 100, 1000, 10000)]
        self.assertEqual(vals[0], 0.0)
        self.assertEqual(vals, sorted(vals))

    def test_deflated_sharpe_punishes_multiple_testing(self):
        returns = [1.909 - 1] * 55 + [-1.0] * 45
        psr = skill.probabilistic_sharpe_ratio(returns)["psr"]
        dsr1 = skill.deflated_sharpe_ratio(returns, 1)["deflated_sharpe"]
        dsr500 = skill.deflated_sharpe_ratio(returns, 500)["deflated_sharpe"]
        self.assertGreaterEqual(dsr1, dsr500)
        self.assertLess(dsr500, psr)

    def test_luck_band_narrows_with_n(self):
        a = skill.luck_share_of_variance(100, 0.5238, 1.909)
        b = skill.luck_share_of_variance(400, 0.5238, 1.909)
        self.assertAlmostEqual(a["no_skill_sd_of_win_rate"] / b["no_skill_sd_of_win_rate"], 2.0, places=2)

    def test_block_bootstrap_deterministic(self):
        returns = [1.909 - 1] * 55 + [-1.0] * 45
        a = skill.block_bootstrap_p_value(returns, seed=7)
        b = skill.block_bootstrap_p_value(returns, seed=7)
        self.assertEqual(a["p_value"], b["p_value"])

    def test_block_bootstrap_flags_noise(self):
        # A zero-mean series must not look significant.
        returns = [1.909 - 1, -1.0] * 60
        out = skill.block_bootstrap_p_value(returns)
        self.assertGreater(out["p_value"], 0.05)


class TestGatesAndLeaderboard(unittest.TestCase):
    def test_gate_requires_sources(self):
        out = gates.g0_provenance([{"name": "x", "source_url": ""}])
        self.assertEqual(out["status"], "fail")

    def test_preregistration_hashes(self):
        spec = {"thresholds": {"a": 1}, "universe": "nba", "stopping_rule": "end", "evaluation_window": "x"}
        out = gates.g1_preregistration(spec)
        self.assertEqual(out["status"], "pass")
        self.assertEqual(len(out["evidence"]["spec_sha256"]), 64)
        # Hash must be stable.
        self.assertEqual(out["evidence"]["spec_sha256"], gates.g1_preregistration(spec)["evidence"]["spec_sha256"])

    def test_preregistration_missing_field(self):
        self.assertEqual(gates.g1_preregistration({"thresholds": {"a": 1}})["status"], "fail")

    def test_no_bets_is_not_evaluable_not_pass(self):
        # Pre-registration declarations are incomplete on purpose here, so the
        # overall verdict must NOT be a pass under any reading.
        out = gates.run_all(
            inputs=[{"name": "a", "source_url": "https://www.nba.com/stats/"}],
            spec={"thresholds": {}, "universe": "nba", "stopping_rule": "end", "evaluation_window": "x"},
            n_settled=0, min_bets=100, in_sample_metric=None, oos_metric=None,
            wins=0, losses=0, break_even=0.5238, returns=[], n_trials=1,
            prices=[], legs_treated_independent=True, measured_phi=None, phi_ci=None,
        )
        self.assertNotEqual(out["overall"], "passed")
        self.assertEqual(out["counts"]["pass"], 1)  # only G0 provenance can pass

    def test_complete_spec_with_no_bets_is_unproven(self):
        """With a complete pre-registration but no bets, the honest verdict is 'unproven'."""
        out = gates.run_all(
            inputs=[{"name": "a", "source_url": "https://www.nba.com/stats/"}],
            spec={"thresholds": {"min_bets": 100}, "universe": "nba", "stopping_rule": "end", "evaluation_window": "2026-11-05..2027-04-12"},
            n_settled=0, min_bets=100, in_sample_metric=None, oos_metric=None,
            wins=0, losses=0, break_even=0.5238, returns=[], n_trials=1,
            prices=[], legs_treated_independent=False, measured_phi=0.3, phi_ci=[0.05, 0.55],
        )
        self.assertEqual(out["overall"], "unproven")

    def test_correlation_gate_fails_on_assumed_independence(self):
        out = gates.g6_correlation(True, None, None)
        self.assertEqual(out["status"], "fail")

    def test_correlation_gate_unevaluable_when_ci_spans_zero(self):
        out = gates.g6_correlation(False, 0.42, [-0.06, 0.74])
        self.assertEqual(out["status"], "not_evaluable")

    def test_robustness_needs_sample(self):
        self.assertEqual(gates.g7_robustness([1.0, -1.0])["status"], "not_evaluable")

    def test_rank_leaves_unproven_unranked(self):
        out = leaderboard.rank([
            {"id": "A", "name": "A", "category": "single", "overall_gate_status": "passed",
             "returns": [1.909 - 1] * 60 + [-1.0] * 40},
            {"id": "B", "name": "B", "category": "single", "overall_gate_status": "unproven", "returns": []},
        ])
        ranks = {r["id"]: r["rank"] for r in out["sorted"]}
        self.assertEqual(ranks["A"], 1)
        self.assertIsNone(ranks["B"])
        self.assertIsNone(out["sorted"][0]["reward"])

    def test_lower_bound_below_mean(self):
        lb = leaderboard.roi_lower_bound([1.909 - 1] * 60 + [-1.0] * 40)
        self.assertLess(lb["lower_bound"], lb["mean_roi"])
        self.assertTrue(lb["ok"])

    def test_roi_bounds_shrink_with_n(self):
        small = leaderboard.roi_lower_bound([0.9, -1.0] * 25)
        big = leaderboard.roi_lower_bound([0.9, -1.0] * 500)
        self.assertLess(big["se"], small["se"])


class TestDeterminism(unittest.TestCase):
    def test_results_are_reproducible(self):
        """Re-running the analysis must produce identical JSON."""
        import json
        import subprocess

        before = {}
        for p in sorted((ROOT / "results").glob("*.json")):
            before[p.name] = p.read_text(encoding="utf-8")
        subprocess.run([sys.executable, str(ROOT / "run.py")], check=True, capture_output=True)
        for name, text in before.items():
            self.assertEqual((ROOT / "results" / name).read_text(encoding="utf-8"), text, f"{name} changed between runs")


if __name__ == "__main__":
    unittest.main(verbosity=2)
