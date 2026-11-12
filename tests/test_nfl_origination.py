"""NFL layer tests: extraction integrity, math contracts, and the no-invention rules."""
import json
import unittest
from pathlib import Path

from nfl_origination import engine
from nfl_origination import math as m

ROOT = Path(__file__).resolve().parent.parent


class ExtractionTests(unittest.TestCase):
    def test_receipts_match_committed_datasets(self):
        engine.verify_receipts()

    def test_row_counts_are_the_verified_counts(self):
        standings = engine.load_csv("data/nfl-standings-week10-2026.csv")
        injuries = engine.load_csv("data/nfl-injuries-2026-w10.csv")
        fixtures = engine.load_csv("data/nfl-schedule-2026-w10.csv")
        self.assertEqual((len(standings), len(injuries), len(fixtures)), (32, 20, 14))
        self.assertEqual(len({r["TeamCode"] for r in standings}), 32)
        self.assertEqual(len({r["PlayerURL"] for r in injuries}), 20)
        self.assertEqual(len({r["GameURL"] for r in fixtures}), 14)

    def test_every_row_has_an_official_https_source_and_a_date(self):
        for name in ("data/nfl-standings-week10-2026.csv", "data/nfl-injuries-2026-w10.csv",
                     "data/nfl-schedule-2026-w10.csv"):
            for row in engine.load_csv(name):
                self.assertTrue(row["SourceURL"].startswith("https://www.nfl.com/"), name)
                self.assertEqual(row["CheckedOn"], "2026-11-12", name)

    def test_standings_arithmetic_is_self_consistent(self):
        for row in engine.load_csv("data/nfl-standings-week10-2026.csv"):
            games = int(row["W"]) + int(row["L"]) + int(row["T"])
            implied = (int(row["W"]) + int(row["T"]) / 2) / games
            self.assertAlmostEqual(implied, float(row["PCT"]), delta=0.00051)
            self.assertEqual(int(row["PF"]) - int(row["PA"]), int(row["NetPts"]))
        rows = engine.load_csv("data/nfl-standings-week10-2026.csv")
        self.assertEqual(sum(int(r["W"]) for r in rows), sum(int(r["L"]) for r in rows))

    def test_injury_statuses_use_only_official_categories(self):
        allowed_practice = {"Did Not Participate In Practice",
                            "Limited Participation in Practice",
                            "Full Participation in Practice"}
        allowed_game = {"", "Out", "Doubtful", "Questionable"}
        for row in engine.load_csv("data/nfl-injuries-2026-w10.csv"):
            self.assertIn(row["PracticeStatus"], allowed_practice)
            self.assertIn(row["GameStatus"], allowed_game)

    def test_blank_is_not_converted_into_available(self):
        """The most likely hallucination: treating a blank status as 'will play'."""
        rows = engine.load_csv("data/nfl-injuries-2026-w10.csv")
        blank = [r for r in rows if not r["GameStatus"]]
        self.assertEqual(len(blank), 17)
        for row in blank:
            self.assertEqual(row["GameStatus"], "")
        for row in engine.build()["availability"]:
            self.assertIsNone(row["talent_lost"])
            self.assertIsNone(row["starters_affected"])
            self.assertIsNone(row["backup_replacement_count"])


class OriginationTests(unittest.TestCase):
    def test_pythagorean_identity_and_bounds(self):
        self.assertAlmostEqual(m.pythagorean_win_pct(300, 300), 0.5)
        self.assertGreater(m.pythagorean_win_pct(350, 200), 0.5)
        self.assertLess(m.pythagorean_win_pct(200, 350), 0.5)
        with self.assertRaises(ValueError):
            m.pythagorean_win_pct(0, 100)

    def test_projection_coherence(self):
        """Spread and total must come from the same pair of numbers, always."""
        for home_off, home_def, away_off, away_def in (
                (24, 20, 21, 23), (30, 18, 15, 28), (17, 26, 27, 19)):
            proj = m.project_game(home_off, home_def, away_off, away_def, 22.0)
            self.assertAlmostEqual(proj["spread_home"], -(proj["home_points"] - proj["away_ppg"]))
            self.assertAlmostEqual(proj["total"], proj["home_points"] + proj["away_ppg"])
            self.assertGreater(proj["win_prob_home"], 0)
            self.assertLess(proj["win_prob_home"], 1)

    def test_win_probability_is_monotone_and_centred(self):
        self.assertAlmostEqual(m.normal_win_probability(0.0), 0.5)
        self.assertGreater(m.normal_win_probability(3), m.normal_win_probability(1))
        self.assertLess(m.normal_win_probability(-3), m.normal_win_probability(-1))
        with self.assertRaises(ValueError):
            m.normal_win_probability(1, sd=0)

    def test_fair_price_round_trip(self):
        for p in (0.25, 0.5, 0.61, 0.9):
            price = m.american_from_probability(p)
            self.assertAlmostEqual(m.break_even_probability(price), p, delta=0.01)
        with self.assertRaises(ValueError):
            m.american_from_probability(0)

    def test_break_even_known_values(self):
        self.assertAlmostEqual(m.break_even_probability(-110), 110 / 210)
        self.assertAlmostEqual(m.break_even_probability(100), 0.5)

    def test_kelly_can_recommend_no_bet(self):
        self.assertLess(m.kelly_fraction(0.45, -110), 0)
        self.assertGreater(m.kelly_fraction(0.60, -110), 0)

    def test_degenerate_correlation_returns_none_not_zero(self):
        self.assertIsNone(m.pearson([1, 2, 3, 4], [5, 5, 5, 5]))
        with self.assertRaises(ValueError):
            m.pearson([1, 2], [3, 4])


class ResultContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = engine.build()

    def test_run_reproduces_exactly(self):
        import json as _json
        text = _json.dumps(self.result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        self.assertEqual((ROOT / "research/nfl/results.json").read_text(encoding="utf-8"), text)

    def test_no_market_value_is_invented(self):
        for game in self.result["games"]:
            for field in ("market_spread", "market_total", "market_prices", "clv", "closing_price"):
                self.assertIsNone(game[field], f"{game['matchup']} {field}")
            self.assertIsNotNone(game["originated_total"])

    def test_no_strategy_is_qualified_or_rewarded(self):
        self.assertEqual(self.result["leaderboard"]["entries"], [])
        self.assertIsNone(self.result["leaderboard"]["cash_reward"])
        for row in self.result["evaluations"]:
            self.assertFalse(row["qualified"])
            self.assertIsNone(row["roi"])
            self.assertIsNone(row["clv"])
            self.assertEqual(row["merit_points"], 0)
            self.assertEqual(row["status"], "Blocked")

    def test_qualified_requires_every_applicable_gate(self):
        for row in self.result["evaluations"]:
            applicable = sum(1 for v in row["gates"].values() if v != "n/a")
            passed = sum(1 for v in row["gates"].values() if v == "pass")
            self.assertEqual(row["passed"], passed)
            self.assertEqual(row["applicable"], applicable)
            self.assertEqual(row["qualified"], passed == applicable)

    def test_tautological_pairs_are_flagged_not_hidden(self):
        flagged = [c for c in self.result["correlations"] if not c["counts_as_independent_evidence"]]
        self.assertEqual(len(flagged), 5)
        for row in flagged:
            self.assertTrue(row["caveat"])
            self.assertIn("not independent", row["evidence"])
        self.assertEqual(sum(c["counts_as_independent_evidence"] for c in self.result["correlations"]), 5)

    def test_uncollected_structures_are_blank(self):
        self.assertEqual(len(self.result["not_collected"]), 4)
        for row in self.result["not_collected"]:
            for field in ("n", "pearson", "raw_p", "holm_p"):
                self.assertIsNone(row[field])
            self.assertEqual(row["evidence"], "Unverified · blank")

    def test_home_adjustment_is_declared_an_assumption(self):
        assumptions = self.result["assumptions"]
        self.assertEqual(assumptions["home_adjustment_points"], 2.0)
        self.assertIn("assumption", assumptions["home_adjustment_source"].lower())
        self.assertIn("not fitted", assumptions["pythagorean_source"].lower())


class DecisionDossierTests(unittest.TestCase):
    def test_every_missing_item_names_a_suggestion_that_exists(self):
        decisions = json.loads((ROOT / "research/nfl/decisions.json").read_text(encoding="utf-8"))
        ids = {s["id"] for s in decisions["suggestions"]}
        self.assertEqual(len(ids), len(decisions["suggestions"]))
        for row in decisions["missing_information"]:
            self.assertIn(row["suggestion"], ids)
            self.assertTrue(row["why_it_matters"])
        for row in decisions["blocking_before_any_reward"]:
            self.assertIn(row, {r["id"] for r in decisions["missing_information"]})

    def test_suggestions_are_ranked_without_gaps(self):
        decisions = json.loads((ROOT / "research/nfl/decisions.json").read_text(encoding="utf-8"))
        ranks = [s["rank"] for s in decisions["suggestions"]]
        self.assertEqual(ranks, list(range(1, len(ranks) + 1)))

    def test_every_question_has_known_and_missing_parts(self):
        questions = json.loads((ROOT / "research/nfl/questions.json").read_text(encoding="utf-8"))
        self.assertEqual(len(questions["questions"]), 14)
        for row in questions["questions"]:
            for field in ("known", "missing", "resolves_if"):
                self.assertTrue(row[field].strip(), row["id"])
            self.assertTrue(row["source_ids"])

    def test_every_flag_publishes_a_blank_not_a_guess(self):
        flags = json.loads((ROOT / "research/nfl/flags.json").read_text(encoding="utf-8"))["flags"]
        self.assertEqual(len(flags), 12)
        for row in flags:
            self.assertIsNone(row["unverified_value"])
            self.assertIn(row["status"], ("Needs review", "Corrected"))
            self.assertTrue(row["source_ids"])


if __name__ == "__main__":
    unittest.main()
