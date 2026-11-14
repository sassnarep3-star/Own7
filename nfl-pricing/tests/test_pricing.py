"""Contracts for the price, market-relative grading and depth desk.

These are the properties a reader is entitled to rely on without re-reading the pipeline: a blank
means unknown, a row cites the page it came from, the leaderboard cannot be ranked by staking, and
the demotion gate is written down. Everything here is computed from the committed artifacts, so a
regression in any upstream script fails this suite rather than publishing quietly.
"""
from __future__ import annotations

import csv
import json
from decimal import Decimal
import subprocess
import sys
import unittest
from pathlib import Path

DESK = Path(__file__).resolve().parent.parent
ROOT = DESK.parent
DATA = DESK / "data"
SCRIPTS = ("collect", "originate", "leaderboard", "correlations", "depth", "questions")


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def rows(name: str):
    with (DATA / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class PriceStore(unittest.TestCase):
    """Requirement 1: one price per game, two independent club pages agreeing."""

    @classmethod
    def setUpClass(cls):
        cls.store = load("price-snapshots.json")

    def test_every_stored_game_had_both_pages_agree(self):
        for game in self.store["games"]:
            self.assertTrue(game["sides_agree"], game["home"])
            self.assertTrue(game["totals_agree"], game["home"])
            self.assertEqual(len(game["sources"]), 2, "a price rests on two club pages")

    def test_mirrored_club_prices_are_exact_negatives(self):
        # Provenance check on the transcription: the away row and the home row must mirror.
        for game in self.store["games"]:
            away, home = game["closing_line_away"], game["closing_line_home"]
            if away is None or home is None:
                continue
            # Stored as exact decimal strings so a half point never becomes 4.4999999.
            self.assertEqual(Decimal(away), -Decimal(home), game["home"])

    def test_opening_price_is_absent_not_zero(self):
        self.assertFalse(self.store["opening_line_available"])
        self.assertEqual(self.store["counts"]["rows_flagged"], 0)
        for game in self.store["games"]:
            self.assertNotIn("opening_line_home", game)

    def test_no_recorded_problem(self):
        self.assertEqual(self.store["problems"], [])

    def test_publisher_verdicts_were_reconciled_not_copied(self):
        self.assertEqual(
            self.store["counts"]["publisher_verdicts_reconcile"],
            2 * self.store["counts"]["games_reconciled"],
        )


class Origination(unittest.TestCase):
    """Requirements 3 and 4: side, then total, then moneyline, with separate columns."""

    @classmethod
    def setUpClass(cls):
        cls.orig = load("origination.json")

    def test_order_is_enforced_downstream_of_the_side(self):
        for game in self.orig["games"]:
            if game["side_status"] != "originated":
                self.assertIsNone(game["fair_total"], "a total exists without a side")
                self.assertIsNone(game["fair_home_ml"], "a moneyline exists without a side")
            if game["total_status"] != "originated":
                self.assertIsNone(game["fair_home_ml"], "a moneyline exists without a total")

    def test_every_row_carries_three_separate_columns(self):
        for game in self.orig["games"]:
            for field in ("fair_line_home", "market_line_home", "line_difference"):
                self.assertIn(field, game, "the three columns must exist on every row")
            # The difference is only defined when BOTH numbers exist. A withheld game has no fair
            # line, so its difference is blank rather than a mirror of the market number.
            if game["fair_line_home"] is None:
                self.assertIsNone(game["line_difference"])
            else:
                # The market column stays an exact decimal string; the fair line is a float.
                self.assertAlmostEqual(
                    game["line_difference"],
                    game["fair_line_home"] - float(Decimal(game["market_line_home"])),
                    places=6,
                )

    def test_market_moneyline_is_never_invented(self):
        self.assertEqual(self.orig["counts"]["market_moneyline_available"], 0)

    def test_withheld_rows_are_counted_with_a_reason(self):
        withheld = [g for g in self.orig["games"] if g["side_status"] != "originated"]
        self.assertEqual(
            len(withheld), self.orig["counts"]["games"] - self.orig["counts"]["side_originated"]
        )
        self.assertTrue(all(g["side_status"] == "withheld_no_prior_games" for g in withheld))

    def test_parameters_were_fixed_before_grading(self):
        note = self.orig["parameters"]["note"].lower()
        self.assertIn("before grading", note)


class LeaderboardAndGate(unittest.TestCase):
    """Requirements 5 and 8: signal apart from staking, and a written demotion rule."""

    @classmethod
    def setUpClass(cls):
        cls.board = load("leaderboard.json")

    def test_ranking_uses_signal_never_units(self):
        self.assertEqual(self.board["ranking"], [])
        ranked = [e for e in self.board["entries"] if e.get("rank") is not None]
        self.assertEqual(ranked, [])
        self.assertIn("signal", self.board["ranking_rule"].lower())

    def test_signal_and_staking_are_different_quantities(self):
        for entry in self.board["entries"]:
            self.assertIn("hit_rate", entry["signal"])
            self.assertIn("units", entry["staking"])
            self.assertNotEqual(entry["signal"]["note"], "", "signal states its own benchmark")

    def test_no_entry_is_ranked_without_clearing_multiplicity(self):
        for entry in self.board["entries"]:
            if entry["demotion"]["state"] == "ranked":
                self.assertLessEqual(entry["signal"]["q_value_bh"], self.board["fdr_level"])

    def test_gate_is_written_down_with_its_thresholds(self):
        gate = self.board["demotion_gate"]
        for field in ("id", "rule", "window_selections", "max_drawdown_units",
                      "max_price_disagreement_points"):
            self.assertTrue(gate[field], f"gate is missing {field}")
        self.assertTrue(gate["declared_before_grading"])

    def test_every_demoted_entry_names_its_breach(self):
        for entry in self.board["entries"]:
            if entry["demotion"]["state"] == "demote_to_paper":
                self.assertTrue(entry["demotion"]["breaches"], entry["id"])

    def test_nothing_here_is_presented_as_a_paid_result(self):
        self.assertIn("no wager", self.board["mode"].lower())
        self.assertNotIn("reward_amount", self.board)


class Correlations(unittest.TestCase):
    """Requirement 7: official numbers only, n on every value, blanks named."""

    @classmethod
    def setUpClass(cls):
        cls.corr = load("correlations.json")

    def test_every_measured_value_publishes_n(self):
        for name, value in self.corr["measured"].items():
            self.assertIsInstance(value["n"], int, name)
            self.assertGreater(value["n"], 0, name)

    def test_a_value_is_either_present_with_n_or_absent_with_a_reason(self):
        for name, value in self.corr["measured"].items():
            present = value.get("r") if "r" in value else value.get("phi")
            self.assertIsNotNone(present, f"{name} reports neither r nor phi")
        for item in self.corr["not_measured"]:
            self.assertTrue(item["quantity"])
            self.assertTrue(item["why_blank"])
            self.assertTrue(item["do_not_assume"])
            self.assertTrue(item["what_would_close_it"])

    def test_expected_sign_is_declared_so_a_wrong_sign_reads_as_a_defect(self):
        self.assertIn("negative", self.corr["sign_convention"].lower())
        for name in ("market_line_vs_actual_margin", "fair_line_vs_actual_margin"):
            self.assertIsNotNone(self.corr["measured"][name]["expected_sign"])

    def test_unpriced_dependence_is_never_rendered_as_zero(self):
        for item in self.corr["not_measured"]:
            self.assertNotIn("value", item)


class Depth(unittest.TestCase):
    """Requirement 6: the depth of the replacement, not merely its existence."""

    @classmethod
    def setUpClass(cls):
        cls.depth = load("depth.json")

    def test_both_non_overlapping_slot_files_are_read(self):
        files = {row["file"] for row in self.depth["slot_sources"]}
        self.assertEqual(len(files), 2, "PD01: the second slot file is being dropped again")
        self.assertEqual(len(self.depth["clubs"]), 31)

    def test_units_are_never_mixed_in_one_figure(self):
        self.assertEqual(self.depth["units_kept_separate"], ["Offense", "Defense", "Special Teams"])
        for club in self.depth["clubs"]:
            for unit in club["by_unit"]:
                self.assertIn(unit, self.depth["units_kept_separate"])

    def test_depth_points_are_declared_not_fitted(self):
        note = self.depth["not_a_point_value"].lower()
        self.assertIn("not", note)
        self.assertIn("not fitted", note)
        self.assertEqual(set(self.depth["rank_weight"]), {"1", "2", "3", "4", "5", "6"})

    def test_the_two_thin_situations_are_counted_separately(self):
        # "No name behind the injured player" and "the replacement is himself last" are different
        # facts. Collapsing them was a real labelling defect found by this test.
        no_name = [r for r in self.depth["replacements"] if r["no_printed_name_behind"]]
        rep_last = [r for r in self.depth["replacements"] if r["replacement_is_last"]]
        self.assertEqual(len(no_name), self.depth["counts"]["injury_rows_with_no_printed_name_behind"])
        self.assertEqual(len(rep_last), self.depth["counts"]["replacements_that_are_the_last_printed_name"])
        self.assertFalse(set(r["injury_id"] for r in no_name) & set(r["injury_id"] for r in rep_last))
        for r in no_name:
            self.assertIsNone(r["replacement_rank"])
            self.assertEqual(r["thin_reason"], "no printed name behind the injured player")
        for r in rep_last:
            self.assertEqual(r["replacement_rank"], r["slot_deepest_rank"])

    def test_every_replacement_row_cites_both_its_pages(self):
        for r in self.depth["replacements"]:
            self.assertTrue(r["injury_source_url"].startswith("https://"))
            self.assertTrue(r["depth_source_url"].startswith("https://"))

    def test_depth_source_is_not_a_placeholder_id(self):
        # A pattern such as "https://www.<club>.com/..." cannot be resolved to a registered URL,
        # so it must not be presented as a source ID.
        self.assertIsNone(self.depth["sources"]["depth"]["id"])
        self.assertIsNotNone(self.depth["sources"]["injury"]["id"])


class QuestionsAndSuggestions(unittest.TestCase):
    """Suggestions are reviewed before implementation and never act on themselves."""

    def test_questions_separate_known_from_missing(self):
        questions = rows("questions.csv")
        self.assertGreaterEqual(len(questions), 10)
        for q in questions:
            self.assertTrue(q["known"], q["id"])
            self.assertTrue(q["closes_with"], q["id"])
            self.assertTrue(
                q["status"].split(" - ")[0].split(" on ")[0]
                in {"open", "partly answered", "answered", "blocked"},
                f"{q['id']} has an unreadable status: {q['status']}",
            )

    def test_every_suggestion_states_its_evidence_and_its_failure_test(self):
        for s in rows("suggestions.csv"):
            for field in ("evidence", "unlocks", "cost", "risk", "acceptance_test"):
                self.assertTrue(s[field], f"{s['id']} is missing {field}")

    def test_decision_record_is_deliberately_blank(self):
        decisions = rows("decision-record.csv")
        self.assertEqual(len(decisions), len(rows("suggestions.csv")))
        for d in decisions:
            self.assertEqual(d["decision"], "", "a suggestion implemented itself")
            self.assertEqual(d["decided_on"], "")
            self.assertEqual(d["decision_by"], "")


class Reproducibility(unittest.TestCase):
    """The published pages and every artifact regenerate byte for byte."""

    def test_desk_pages_reproduce(self):
        result = subprocess.run([sys.executable, str(DESK / "build.py"), "--check"],
                                capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pipeline_scripts_reproduce_their_artifacts(self):
        for name in SCRIPTS:
            result = subprocess.run([sys.executable, str(DESK / f"{name}.py"), "--check"],
                                    capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(result.returncode, 0, f"{name}.py --check failed: {result.stdout}{result.stderr}")

    def test_every_linked_source_is_registered(self):
        registry = json.loads((ROOT / "research" / "sources.json").read_text())
        ids = {row["id"] for row in registry}
        manifest = json.loads((DESK / "site" / "manifest.json").read_text())
        self.assertTrue(set(manifest["source_ids"]) <= ids)


if __name__ == "__main__":
    unittest.main()
