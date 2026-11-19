"""Integrity tests for the walk-forward calibration desk."""
import csv
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import build as B  # noqa: E402


class CalibrationAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = B.build_model()
        cls.official_games = B.read_csv(B.RESULTS_FEED)

    def test_expected_sample_and_weeks(self):
        self.assertEqual(self.model["n"], len(self.model["games"]))
        self.assertEqual(self.model["target_weeks"], list(range(2, 11)))
        target_rows = [g for g in self.official_games if 2 <= int(g["week"]) <= 10]
        target_ties = [g for g in target_rows if g["away_score"] == g["home_score"]]
        self.assertEqual((len(target_rows), len(target_ties)), (134, 1))
        self.assertEqual(self.model["n"], 134)
        self.assertEqual(self.model["binary_n"], 133)

    def test_each_row_has_official_registered_source_and_prior_inputs(self):
        reg = B.registry_map()
        for row in self.model["games"]:
            self.assertTrue(row["source_ids"], row["game_id"])
            self.assertTrue(row["source_url"].startswith("https://www.nfl.com/"), row["game_id"])
            expected_prior = sum(int(g["week"]) < row["target_week"] for g in self.official_games)
            self.assertEqual(row["prior_games"], expected_prior, row["game_id"])
            self.assertGreater(row["prior_home_games"], 0)
            self.assertGreater(row["prior_away_games"], 0)
            for sid in row["source_ids"]:
                self.assertIn(sid, reg, row["game_id"])
            self.assertEqual(row["sources"][0]["url"], row["source_url"])

    def test_probability_and_outcome_domains(self):
        import math
        for row in self.model["games"]:
            self.assertGreater(row["p_home"], 0)
            self.assertLess(row["p_home"], 1)
            self.assertGreaterEqual(row["p_away"], 0)
            self.assertGreaterEqual(row["p_tie"], 0)
            self.assertAlmostEqual(row["p_home"] + row["p_away"] + row["p_tie"], 1.0, places=12)
            self.assertIn(row["outcome"], ("HOME_WIN", "AWAY_WIN", "TIE"))
            if row["outcome"] == "TIE":
                self.assertIsNone(row["outcome_home_win"])
            else:
                self.assertIn(row["outcome_home_win"], (0, 1))
            inputs = row["probability_inputs"]
            z = inputs["projected_home_margin"] / inputs["margin_sd"]
            expected = 0.5 * (1 + math.erf(z / math.sqrt(2))) * (1 - inputs["tie_rate_prior"])
            self.assertAlmostEqual(row["p_home"], expected, places=12)
            self.assertAlmostEqual(row["p_home_given_no_tie"], 0.5 * (1 + math.erf(z / math.sqrt(2))), places=12)

    def test_brier_skill_is_recomputed(self):
        games = self.model["games"]
        binary = [r for r in games if r["outcome_home_win"] is not None]
        expected = sum((r["p_home_given_no_tie"] - r["outcome_home_win"]) ** 2 for r in binary) / len(binary)
        self.assertAlmostEqual(self.model["binary_brier_given_no_tie"], expected, places=6)
        self.assertAlmostEqual(self.model["binary_brier_skill_vs_50pct"], 1 - expected / 0.25, places=6)
        multi = sum(sum((r[p] - (1.0 if r["outcome"] == label else 0.0)) ** 2
                        for p, label in (("p_home", "HOME_WIN"), ("p_away", "AWAY_WIN"), ("p_tie", "TIE")))
                    for r in games) / len(games)
        self.assertAlmostEqual(self.model["multiclass_brier"], multi, places=6)
        self.assertAlmostEqual(self.model["multiclass_brier_skill_vs_uniform"], 1 - multi / (2 / 3), places=6)

    def test_calibration_bins_partition_the_scored_rows(self):
        bins = self.model["bins"]
        self.assertEqual(len(bins), 5)
        self.assertEqual(sum(b["n"] for b in bins), self.model["binary_n"])
        self.assertTrue(any(b["flag"] for b in bins))

    def test_cluster_uncertainty_is_seeded_and_caveated(self):
        boot = self.model["bootstrap"]
        self.assertEqual(boot["clusters"], len(self.model["target_weeks"]))
        self.assertEqual(boot["reps"], 5000)
        self.assertLess(boot["brier_skill_ci95"][0], boot["brier_skill_ci95"][1])
        self.assertLess(boot["multiclass_brier_skill_ci95"][0], boot["multiclass_brier_skill_ci95"][1])
        self.assertIn("exploratory", boot["flag"])

    def test_no_prices_or_staking_are_in_scope(self):
        self.assertNotIn("staking", self.model)
        self.assertNotIn("roi", self.model)
        self.assertIn("no market prices", self.model["scope"])

    def test_artifacts_reproduce_byte_identically(self):
        self.assertEqual(B.main(["--check"]), 0)

    def test_csv_is_one_row_per_published_game(self):
        with (HERE / "data/game-probabilities.csv").open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), self.model["n"])
        self.assertTrue(all(row["source_url"].startswith("https://www.nfl.com/") for row in rows))
        self.assertTrue({"p_home", "p_away", "p_tie", "p_home_given_no_tie",
                         "projected_home_margin", "margin_sd", "tie_rate_prior", "outcome"} <= set(rows[0]))

    def test_manifest_lists_all_published_site_files(self):
        manifest = json.loads((HERE / "site/manifest.json").read_text(encoding="utf-8"))
        disk = sorted(p.name for p in (HERE / "site").iterdir())
        self.assertEqual(sorted(manifest["pages"]), disk)


if __name__ == "__main__":
    unittest.main()
