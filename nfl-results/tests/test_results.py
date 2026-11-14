"""Tests for the results capture and the skill/luck engine.

These are not decoration. Each one pins a property that would otherwise let a wrong
number reach the site: reconciliation, leakage, determinism, and the anti-overclaim
rules that decide whether anything may be called skill.
"""
from __future__ import annotations

import csv
import importlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "nfl-results"))

import engine  # noqa: E402


class ResultsCapture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (ROOT / "nfl-results" / "data" / "games-2026-w1-9.csv").open(encoding="utf-8") as handle:
            cls.games = list(csv.DictReader(handle))
        with (ROOT / "nfl-results" / "data" / "byes-2026-w1-9.csv").open(encoding="utf-8") as handle:
            cls.byes = list(csv.DictReader(handle))

    def test_every_game_has_an_official_source_and_date(self):
        for row in self.games:
            self.assertEqual(row["source_url"],
                             f"https://www.nfl.com/schedules/2026/by-week/week-{row['week']}")
            self.assertTrue(row["source_url"].startswith("https://www.nfl.com/"))
            self.assertEqual(row["retrieved"], "2026-11-14")
            self.assertRegex(row["date"], r"^2026-\d{2}-\d{2}$")

    def test_no_fixture_is_duplicated(self):
        keys = [(r["week"], r["away"], r["home"]) for r in self.games]
        self.assertEqual(len(keys), len(set(keys)))

    def test_no_club_plays_twice_in_a_week(self):
        per_week: dict[str, list[str]] = {}
        for r in self.games:
            per_week.setdefault(r["week"], []).extend([r["away"], r["home"]])
        for week, clubs in per_week.items():
            self.assertEqual(len(clubs), len(set(clubs)), f"duplicate club in week {week}")

    def test_game_counts_match_byes(self):
        by_week: dict[str, int] = {}
        for r in self.games:
            by_week[r["week"]] = by_week.get(r["week"], 0) + 1
        bye_week: dict[str, int] = {}
        for r in self.byes:
            bye_week[r["week"]] = bye_week.get(r["week"], 0) + 1
        for week, count in by_week.items():
            self.assertEqual(count, (32 - bye_week.get(week, 0)) // 2,
                             f"week {week} game count inconsistent with its byes")

    def test_reconciliation_holds(self):
        """The 136 parsed games must reproduce the official standings exactly."""
        with (ROOT / "data" / "nfl-standings-2026.csv").open(encoding="utf-8") as handle:
            standings = list(csv.DictReader(handle))
        import subprocess
        proc = subprocess.run([sys.executable, str(ROOT / "nfl-results" / "extract.py")],
                              capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("reconciled with 32 official standings rows", proc.stdout)
        self.assertEqual(len(standings), 32)

    def test_scores_are_plausible(self):
        for r in self.games:
            for side in ("away_score", "home_score"):
                value = int(r[side])
                self.assertGreaterEqual(value, 0)
                self.assertLessEqual(value, 100, "an NFL score above 100 would be a parse error")


class NoLeakage(unittest.TestCase):
    def test_prior_state_excludes_the_target_week(self):
        games = engine.load_games()
        for week in (2, 5, 9):
            state = engine.prior_state(games, week)
            for row in state.values():
                for r in row["results"]:
                    self.assertLess(r["week"], week)

    def test_week_one_is_not_scored(self):
        games = engine.load_games()
        rows = engine.walk_forward(games, engine.load_byes())
        self.assertTrue(all(r["week"] >= 2 for r in rows))
        self.assertEqual(len(rows), 120)

    def test_leave_one_out_uses_an_earlier_cut(self):
        games = engine.load_games()
        byes = engine.load_byes()
        a = engine.loo_forecast(games, byes, 5, "M01", "BUF", "NYJ")
        b = engine.loo_forecast(games, byes, 9, "M01", "BUF", "NYJ")
        self.assertNotEqual(a, b, "later weeks must have more information, not the same")


class Determinism(unittest.TestCase):
    def test_engine_output_is_stable(self):
        first = json.dumps(engine.build(), sort_keys=True)
        second = json.dumps(engine.build(), sort_keys=True)
        self.assertEqual(first, second)

    def test_committed_analysis_is_current(self):
        fresh = engine.build()
        committed = json.loads((ROOT / "nfl-results" / "analysis.json").read_text(encoding="utf-8"))
        self.assertEqual(json.dumps(fresh, sort_keys=True), json.dumps(committed, sort_keys=True),
                         "analysis.json is stale; re-run nfl-results/engine.py")


class NoFalseSkillClaims(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analysis = engine.build()

    def test_qualified_requires_every_gate_to_pass(self):
        for c in self.analysis["candidates"]:
            if c["qualified"]:
                self.assertTrue(all(g["status"] == "pass" for g in c["gates"]),
                                f"{c['id']} was qualified with a non-pass gate")

    def test_blocked_gates_are_never_treated_as_passes(self):
        for c in self.analysis["candidates"]:
            for g in c["gates"]:
                self.assertIn(g["status"], ("pass", "fail", "blocked"))
            if any(g["status"] == "blocked" for g in c["gates"]):
                self.assertFalse(c["qualified"])

    def test_provisional_entries_earn_nothing(self):
        for row in self.analysis["leaderboard"]:
            if row["tier"] != "qualified":
                self.assertEqual(row["merit_points"], 0)
                self.assertIsNone(row["cash_reward"])
                self.assertIsNone(row["roi"])
                self.assertIsNone(row["clv"])

    def test_no_money_fields_are_ever_populated(self):
        for row in self.analysis["leaderboard"]:
            self.assertIsNone(row["roi"], "ROI requires a price this project does not have")
            self.assertIsNone(row["clv"], "CLV requires a closing price this project does not have")

    def test_luck_analysis_uses_a_meaningful_sample(self):
        best = self.analysis["luck_analysis"]["best_observed"]
        self.assertGreaterEqual(best["bets"], 20,
                                "a tiny record must not be reported as the best strategy")

    def test_totals_market_is_not_presented_as_skill(self):
        total = self.analysis["benchmarks"]["total"]
        spread = self.analysis["benchmarks"]["spread"]
        # If totals carry no information, nothing in the site may say they do.
        if total["directional"]["hit_rate"] is not None and total["directional"]["hit_rate"] <= 0.55:
            self.assertLess(abs(total["correlation_board_vs_actual"] or 0), 0.2)


class LegDependence(unittest.TestCase):
    def test_joint_table_sums_to_graded_games(self):
        analysis = engine.build()
        leg = analysis["correlations"]["leg_dependence"]
        self.assertEqual(sum(leg["table"].values()), leg["n_games"])

    def test_independence_baseline_is_the_product_of_marginals(self):
        leg = engine.build()["correlations"]["leg_dependence"]
        expected = leg["p_home_cover"] * leg["p_over"]
        # Output floats are rounded to six decimals for cross-platform stability, so the
        # identity only holds to that precision; assert the tolerance rather than exactness.
        self.assertAlmostEqual(leg["p_home_and_over_independent"], expected, places=5)


class Math(unittest.TestCase):
    def test_benjamini_hochberg_is_monotone(self):
        pvals = [0.001, 0.02, 0.04, 0.3, 0.9]
        qs = engine.benjamini_hochberg(pvals)
        order = sorted(range(len(pvals)), key=lambda i: pvals[i])
        for a, b in zip(order, order[1:]):
            self.assertLessEqual(qs[a], qs[b] + 1e-12)

    def test_binomial_tail_is_a_probability(self):
        for k, n in ((10, 20), (15, 20), (1, 5)):
            value = engine.binom_sf(k, n)
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 1)

    def test_required_sample_grows_as_the_edge_shrinks(self):
        big = engine.required_sample(0.60)
        small = engine.required_sample(0.52)
        self.assertGreater(small, big)

    def test_normal_ppf_inverts_normal_cdf(self):
        for p in (0.05, 0.5, 0.95):
            self.assertAlmostEqual(engine.normal_cdf(engine.normal_ppf(p)), p, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
