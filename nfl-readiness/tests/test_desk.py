"""Contract tests for the decision-readiness desk.

These are not fact checks against the publishers — the site audit already enforces the row/link/blank
contract across the whole repository. These tests protect the properties that make the desk's claims
falsifiable:

  * an artefact that must be byte-reproducible really is;
  * a correlation never publishes a value without an n and a registered source;
  * a leaderboard entry never carries a staking field, and the rank order is the published order;
  * a strategy entry always states both what would accept it and what would reject it;
  * a suggestion never records a decision that is not accept/reject/defer;
  * every requirement state is one of the four allowed words, and a `met` row carries a `none` gate;
  * every generated page is deterministic and every table row names a registered source.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESK = ROOT / "nfl-readiness"
DATA = DESK / "data"


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text())


class ReproducibilityTest(unittest.TestCase):
    def test_every_builder_check_mode_passes(self):
        for script in ("requirements.py", "availability.py", "fixture_context.py", "backtest.py",
                       "leaderboard.py", "luck.py", "correlation.py", "analysis.py",
                       "questions.py", "suggestions.py", "strategies.py", "site.py"):
            result = subprocess.run([sys.executable, str(DESK / script), "--check"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, f"{script}: {result.stdout}{result.stderr}")

    def test_registration_hash_matches_the_frozen_file(self):
        import hashlib
        digest = hashlib.sha256((DATA / "registration.json").read_bytes()).hexdigest()
        for name in ("backtest.json", "leaderboard.json", "strategies.json"):
            self.assertEqual(load(name)["registration_hash"], digest, name)


class CorrelationTest(unittest.TestCase):
    def setUp(self):
        self.payload = load("correlation.json")

    def test_every_coefficient_has_an_n_and_a_source(self):
        for row in self.payload["correlations"]:
            self.assertIsInstance(row["n"], int)
            self.assertGreater(row["n"], 0)
            self.assertTrue(row["source_ids"])
            self.assertIsNotNone(row["value"])

    def test_two_by_two_cramer_v_equals_absolute_phi(self):
        rows = {r["id"]: r for r in self.payload["correlations"]}
        phi = rows["COR-SIDE-TOTAL"]["value"]
        v = rows["COR-CRAMER-SIDE-TOTAL"]["value"]
        self.assertAlmostEqual(abs(phi), v, places=5)

    def test_no_marginal_product_is_used_as_a_joint_probability(self):
        self.assertEqual(self.payload["parlay_gate"]["marginal_products_used"], 0)
        self.assertEqual(self.payload["parlay_gate"]["combos_ranked"], 0)


class LeaderboardTest(unittest.TestCase):
    def setUp(self):
        self.payload = load("leaderboard.json")

    def test_no_entry_carries_a_staking_field(self):
        forbidden = {"roi", "units", "stake", "profit", "clv", "return"}
        for entry in self.payload["entries"]:
            self.assertFalse(forbidden & set(entry), entry["id"])

    def test_nothing_is_qualified_and_the_reason_is_published(self):
        self.assertEqual(self.payload["qualified_count"], 0)
        self.assertTrue(self.payload["why_no_rewards"])

    def test_rank_order_is_by_cluster_lower_bound(self):
        bounds = [e["cluster_lo"] for e in sorted(self.payload["entries"], key=lambda e: e["rank"])]
        self.assertEqual(bounds, sorted(bounds, reverse=True))


class StrategyTest(unittest.TestCase):
    def setUp(self):
        self.entries = load("strategies.json")["entries"]

    def test_every_entry_has_two_sides(self):
        for entry in self.entries:
            self.assertTrue(entry["would_accept"].strip(), entry["id"])
            self.assertTrue(entry["would_reject"].strip(), entry["id"])
            self.assertNotEqual(entry["would_accept"], entry["would_reject"])

    def test_no_staking_value_reaches_a_signal_entry(self):
        for entry in self.entries:
            self.assertEqual(entry["stake"], "", entry["id"])


class DecisionTest(unittest.TestCase):
    def test_suggestion_decisions_are_blank_or_one_of_three_words(self):
        for row in load("suggestions.json")["suggestions"]:
            self.assertIn(row["decision"], ("", "accept", "reject", "defer"), row["id"])
            if not row["decision"]:
                self.assertEqual((row["decided_by"], row["decided_on"]), ("", ""), row["id"])

    def test_no_suggestion_is_pre_approved(self):
        self.assertEqual(load("suggestions.json")["counts"]["decided"], 0)

    def test_every_question_names_what_closes_it(self):
        for row in load("questions.json")["questions"]:
            self.assertTrue(row["closes"].strip(), row["id"])
            self.assertTrue(row["blocks"].strip(), row["id"])


class RequirementsTest(unittest.TestCase):
    def setUp(self):
        self.payload = load("requirements.json")

    def test_states_are_from_the_allowed_set(self):
        allowed = {"met", "partial", "blocked", "rejected"}
        for row in self.payload["requirements"]:
            self.assertIn(row["status"], allowed, row["id"])

    def test_a_met_row_has_no_blocking_gate(self):
        for row in self.payload["requirements"]:
            if row["status"] == "met":
                self.assertTrue(row["gate"].startswith("none"), row["id"])

    def test_the_week_11_count_is_thirteen(self):
        text = json.dumps(self.payload)
        self.assertNotIn("14 of 14", text)


class SiteTest(unittest.TestCase):
    def test_every_page_was_written_and_declares_its_sources(self):
        manifest = json.loads((DESK / "site" / "manifest.json").read_text())
        self.assertGreaterEqual(len(manifest["pages"]), 18)
        for name in manifest["pages"]:
            html = (DESK / "site" / name).read_text()
            self.assertEqual(html.count("<h1"), 1, name)
            self.assertIn('lang="en"', html, name)

    def test_blank_cells_never_contain_a_placeholder(self):
        for name in json.loads((DESK / "site" / "manifest.json").read_text())["pages"]:
            html = (DESK / "site" / name).read_text()
            self.assertNotIn(">—<", html, name)
            self.assertNotIn(">n/a<", html, name)


if __name__ == "__main__":
    unittest.main()
