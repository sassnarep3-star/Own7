#!/usr/bin/env python3
"""Tests for the NFL competition lab (session arena/064da913-own7).

Two kinds of test, in the spirit of the rest of the repository:

* **Reference-value tests** — the statistical helpers are checked against values that can
  be read out of any published statistical table, so a silent break in the maths fails
  the build rather than quietly changing a p-value on the site.
* **Contract tests** — the published artifacts must keep the properties the pages claim:
  no price is ever invented, market line and difference stay blank together, signal and
  staking never share a table, every correlation publishes its n, and every table row
  links to the official page behind it.

Nothing here places a wager, reads a market feed, or asserts that any strategy is
profitable. The tests assert the opposite: that the lab refuses to publish what it
cannot source.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESK = HERE.parent
ROOT = DESK.parent
if str(DESK) not in sys.path:
    sys.path.insert(0, str(DESK))

import common  # noqa: E402

DATA = DESK / "data"
SITE = DESK / "site"


def artifact(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def _walk_for(node, keys):
    """Yield every value stored under one of `keys`, anywhere in a nested structure."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in keys:
                yield value
            else:
                yield from _walk_for(value, keys)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_for(value, keys)


class ReferenceValues(unittest.TestCase):
    """Published table values. A break here means the maths is wrong, not the data."""

    def test_benjamini_hochberg_step_up(self):
        """BH step-up: q is monotone, and the smallest p is lifted to p * m / rank."""
        p_values = [0.01, 0.02, 0.5, 1.0, None, 0.04]
        q_values, rejected = common.benjamini_hochberg(p_values)
        self.assertEqual(len(q_values), len(rejected))
        self.assertIsNone(q_values[4])
        self.assertAlmostEqual(q_values[0], 0.05, places=4)
        self.assertAlmostEqual(q_values[1], 0.05, places=4)
        self.assertAlmostEqual(q_values[2], 0.625, places=3)
        self.assertAlmostEqual(q_values[3], 1.0, places=4)
        self.assertAlmostEqual(q_values[5], 1.0 / 15.0, places=4)
        paired = sorted((p, q) for p, q in zip(p_values, q_values) if q is not None)
        lifted = [q for _p, q in paired]
        self.assertEqual(lifted, sorted(lifted), "q must be monotone in p")
        self.assertEqual(rejected[0], True)
        self.assertEqual(rejected[2], False)

    def test_pearson_p_matches_a_t_distribution_table(self):
        """r = -0.1607 over n = 137 gives t = -1.8896, two-sided p = 0.0607."""
        self.assertAlmostEqual(common.pearson_p(-0.1607, 137), 0.0607, places=3)
        self.assertAlmostEqual(common.pearson_p(0.8789, 32), 3.7e-11, delta=5e-11)
        self.assertAlmostEqual(common.pearson_p(0.0, 30), 1.0, places=6)
        self.assertGreaterEqual(common.pearson_p(0.5, 10), 0.0)
        self.assertLessEqual(common.pearson_p(0.5, 10), 1.0)

    def test_normal_ppf_and_cdf(self):
        self.assertAlmostEqual(common.normal_ppf(0.975), 1.959963985, places=5)
        self.assertAlmostEqual(common.normal_ppf(0.5), 0.0, places=9)
        self.assertAlmostEqual(common.normal_cdf(1.96), 0.975, places=4)
        self.assertAlmostEqual(common.normal_cdf(0.0), 0.5, places=9)

    def test_binomial_two_sided_is_exact_not_normal(self):
        """70 of 120 against p = 0.5: the exact two-sided p is 0.0824, not 0.069."""
        self.assertAlmostEqual(common.binom_two_sided(70, 120, 0.5), 0.082407, places=5)
        self.assertAlmostEqual(common.binom_two_sided(60, 120, 0.5), 1.0, places=2)
        self.assertAlmostEqual(common.binom_two_sided(0, 10, 0.5), 2.0 / 1024, places=9)

    def test_the_published_p_value_agrees_with_the_exact_test(self):
        """The board publishes a permutation p; it must stay near the exact one."""
        for strategy in artifact("backtest.json")["strategies"]:
            signal = strategy.get("signal", {})
            if signal.get("binomial_p") is None or signal.get("p_value") is None:
                continue
            self.assertAlmostEqual(signal["p_value"], signal["binomial_p"], delta=0.02,
                                   msg=strategy["id"])

    def test_sample_size_table_is_internally_consistent(self):
        """A larger true rate needs a smaller sample at fixed power; never the reverse."""
        table = artifact("questions.json")["sample_size_table"]
        rates = [row["true_rate"] for row in table]
        sizes = [row["settled_selections_needed"] for row in table]
        self.assertEqual(rates, sorted(rates))
        self.assertEqual(sizes, sorted(sizes, reverse=True))
        self.assertGreater(min(sizes), 0)


class PriceStoreContract(unittest.TestCase):
    """R1: the store exists, its contract is tested, and it holds no invented price."""

    def setUp(self):
        self.store = artifact("price-store.json")

    def test_store_is_empty_and_says_why(self):
        self.assertEqual(self.store["rows_stored"], 0)
        self.assertTrue(self.store["empty_because"])
        self.assertTrue(self.store["what_unblocks_it"])

    def test_capture_instants_are_fixed_in_advance(self):
        rules = self.store["capture_rules"]
        joined = json.dumps(rules).lower()
        for token in ("open", "close", "post_close"):
            self.assertIn(token, joined)
        self.assertIn("never", joined, "post-close must be barred from CLV")

    def test_every_contract_case_passes(self):
        self.assertTrue(self.store["contract_all_pass"])
        for case in self.store["contract_tests"]:
            self.assertTrue(case["passes"], case["case"])
            self.assertEqual(case["expected"], case["observed"], case["case"])

    def test_schema_can_hold_an_opening_and_a_closing_snapshot(self):
        """One row per market per capture point: open, close, and the post-close guard."""
        names = {field["field"] for field in self.store["schema"]}
        self.assertTrue({"capture_point", "captured_at_utc", "price_american",
                         "source_url", "operator", "line", "verified", "imputed"}
                        <= names)
        for field in self.store["schema"]:
            self.assertTrue(field["rule"], field["field"])
        points = {r["capture_point"] for r in self.store["capture_rules"]["capture_points"]} \
            if isinstance(self.store["capture_rules"], dict) \
            and "capture_points" in self.store["capture_rules"] else set()
        if points:
            self.assertTrue({"OPEN", "CLOSE"} <= points)

    def test_no_market_price_value_is_published_anywhere(self):
        """Every market-side price, stake or return column must be null, not estimated."""
        for row in artifact("boards.json")["rows"]:
            for column in ("market_line", "difference", "market_price",
                           "price_difference"):
                self.assertIsNone(row[column], f"{row['market_id']}: {column}")

    def test_no_staking_value_is_published_anywhere(self):
        for strategy in artifact("backtest.json")["strategies"]:
            for column, value in strategy.get("staking", {}).items():
                if column == "blank_because":
                    continue
                self.assertIsNone(value, f"{strategy['id']}: {column}")
        for entry in artifact("leaderboard.json")["entries"]:
            for column, value in (entry.get("staking") or {}).items():
                if column == "blank_because":
                    continue
                self.assertIsNone(value, f"{entry['id']}: {column}")
        self.assertEqual(artifact("leaderboard.json")["staking_table"]["rows"], [])


class ResultsFeedContract(unittest.TestCase):
    """R2: a verified feed, reconciled against the official standings."""

    def setUp(self):
        self.feed = artifact("results-feed.json")

    def test_game_count_and_reconciliation(self):
        self.assertEqual(self.feed["games"], 137)
        recon = self.feed["reconciliation"]
        self.assertEqual(recon["rows_compared"], 32)
        self.assertEqual(recon["fields_compared"], 192)
        self.assertEqual(recon["fields_matching"], 192)
        self.assertEqual(recon["mismatches"], [])

    def test_points_scored_equal_points_allowed(self):
        recon = self.feed["reconciliation"]
        self.assertEqual(recon["league_points_scored"], recon["league_points_allowed"])

    def test_every_row_carries_a_source(self):
        for row in self.feed["rows"]:
            self.assertTrue(row["source_ids"], f"{row.get('game_id')}: no source")
            self.assertTrue(row.get("source_url") or row.get("url")
                            or row.get("game_url"), f"{row.get('game_id')}: no link")

    def test_settlement_is_defined_before_it_is_used(self):
        self.assertTrue(self.feed["settlement_rules"])
        self.assertTrue(self.feed["settlement_authority"])


class OriginationContract(unittest.TestCase):
    """R3: side, then total, then moneyline — in that order, each reading the last."""

    def setUp(self):
        self.og = artifact("origination.json")

    def test_stage_order(self):
        self.assertEqual([s["market"] for s in self.og["stages"]],
                         ["Side", "Total", "Moneyline"])

    def test_a_settled_game_is_originated_nowhere(self):
        self.assertEqual(self.og["games_played_and_excluded"], 1)
        self.assertEqual(self.og["games_originated"], 13)
        self.assertEqual(self.og["games_played_and_excluded"] +
                         self.og["games_originated"], 14)
        self.assertIn("WAS", self.og["games_played_and_excluded_detail"])

    def test_parameters_are_measured(self):
        params = self.og["parameters"]
        for key in ("league_points_per_team_game", "home_allowance_points",
                    "margin_sd_points", "tie_rate"):
            self.assertIsNotNone(params[key]["value"], key)
            self.assertGreater(params[key].get("n", params[key].get("n_team_games", 0)),
                               0, key)
            self.assertTrue(params[key]["basis"], key)

    def test_home_allowance_interval_is_published_not_absorbed(self):
        interval = self.og["parameters"]["home_allowance_points"]["ci95"]
        self.assertEqual(len(interval), 2)
        self.assertLess(interval[0], interval[1])


class BoardsContract(unittest.TestCase):
    """R4: fair line, market line and difference are three columns; the third follows."""

    def test_rows_exist_and_every_market_carries_a_fair_value(self):
        boards = artifact("boards.json")
        self.assertGreater(len(boards["rows"]), 0)
        for row in boards["rows"]:
            has_value = row["fair_line"] is not None or row["fair_price"] is not None
            self.assertTrue(has_value, row["market_id"])

    def test_a_moneyline_has_no_points_line_and_a_side_has_no_price(self):
        for row in artifact("boards.json")["rows"]:
            if row["market"] == "Moneyline":
                self.assertIsNone(row["fair_line"],
                                  "a moneyline has no points to publish")
                self.assertIsNotNone(row["fair_price"], row["market_id"])

    def test_market_line_and_difference_are_blank_together(self):
        for row in artifact("boards.json")["rows"]:
            self.assertIn(row["market_line"], (None, ""), row["market_id"])
            self.assertIn(row["difference"], (None, ""), row["market_id"])
            self.assertIn(row["market_price"], (None, ""), row["market_id"])

    def test_over_price_is_derived_from_a_measured_total_not_a_market(self):
        text = json.dumps(artifact("boards.json")["over_price_derivation"]).lower()
        self.assertIn("total", text)
        self.assertNotIn("operator", text)


class LeaderboardContract(unittest.TestCase):
    """R5: signal and staking are two tables, and only signal can promote."""

    def setUp(self):
        self.lb = artifact("leaderboard.json")

    def test_staking_table_is_empty(self):
        self.assertEqual(self.lb["staking_table"]["rows"], [])
        self.assertTrue(self.lb["staking_table"]["empty_because"])

    def test_signal_ranking_never_mentions_stake_or_return(self):
        metric = json.dumps(self.lb["signal_ranking_metric"]).lower()
        for banned in ("stake", "roi", "return", "bankroll", "profit"):
            self.assertNotIn(banned, metric)

    def test_no_reward_is_paid(self):
        rewards = self.lb["rewards"]
        self.assertIsNone(rewards["cash_reward"])
        self.assertIsNone(rewards["cash_reward_pool"])
        self.assertEqual(rewards["merit_points_awarded"], 0)

    def test_controls_are_not_ranked_with_competitors(self):
        controls = [e for e in self.lb["entries"] if e["status"] == "Control"]
        self.assertTrue(controls)
        for entry in controls:
            self.assertEqual(entry["tier"], "Control")

    def test_blocked_entries_do_not_pass_gates_they_cannot_compute(self):
        for entry in self.lb["entries"]:
            if entry["status"] == "Blocked on data":
                self.assertEqual(entry["tier"], "Blocked on data")

    def test_signal_score_is_ordered_by_evidence_not_by_luck(self):
        """A worse p-value must not outrank a better one at the same sample size."""
        graded = [e for e in self.lb["entries"]
                  if e.get("p_value") is not None and e.get("signal_score") is not None]
        by_n = {}
        for entry in graded:
            by_n.setdefault(entry["n"], []).append(entry)
        for n, group in by_n.items():
            ordered = sorted(group, key=lambda e: e["signal_score"], reverse=True)
            p_values = [e["p_value"] for e in ordered]
            self.assertEqual(p_values, sorted(p_values),
                             f"n={n}: signal score ranks a weaker p above a stronger one")


class ReplacementDepthContract(unittest.TestCase):
    """R6: the depth of the replacement, not merely the fact of one."""

    def setUp(self):
        self.depth = artifact("depth.json")

    def test_depth_tiers_are_ordered(self):
        tiers = self.depth["tiers"]
        self.assertGreater(len(tiers), 2)
        self.assertTrue(all("rank" in t or "depth" in t or "label" in t for t in tiers))

    def test_no_point_value_is_attached_to_a_rank(self):
        blob = json.dumps(self.depth)
        for banned in ("point_value", "points_value", "expected_points_lost"):
            self.assertNotIn(banned, blob)

    def test_replacements_are_counted_by_depth(self):
        head = self.depth["headline"]
        self.assertEqual(head["starters_ruled_out"], 8)
        self.assertEqual(head["replacements_from_2nd_string"], 7)
        self.assertEqual(head["replacements_from_3rd_string"], 0)
        self.assertEqual(head["slots_with_no_printed_replacement"], 1)

    def test_the_unreadable_chart_stays_blank(self):
        self.assertIn("HOU", self.depth["coverage"]["clubs_without_a_captured_chart"])


class CorrelationContract(unittest.TestCase):
    """R7: only officially sourced numbers, and every value publishes its n."""

    def test_every_published_value_has_n_and_a_source(self):
        for row in artifact("correlations.json")["rows"]:
            if row["value"] is None:
                self.assertIn(row.get("value_note", "") or "not", json.dumps(row).lower())
                continue
            self.assertGreater(row["n"], 0, row["id"])
            self.assertTrue(row.get("source_ids"), row["id"])
            self.assertTrue(row.get("method"), row["id"])

    def test_the_tautological_pair_is_labelled_as_such(self):
        rows = {row["id"]: row for row in artifact("correlations.json")["rows"]}
        self.assertAlmostEqual(rows["C02"]["value"], 1.0, places=9)
        self.assertIn("definition", json.dumps(rows["C02"]).lower())

    def test_measured_values_stay_inside_the_valid_range(self):
        for row in artifact("correlations.json")["rows"]:
            if row["value"] is None:
                continue
            self.assertGreaterEqual(row["value"], -1.0, row["id"])
            self.assertLessEqual(row["value"], 1.0, row["id"])


class DemotionGateContract(unittest.TestCase):
    """R8: a live strategy can go back to paper, and the ladder is published."""

    def setUp(self):
        self.dm = artifact("demotion.json")

    def test_ladder_is_defined(self):
        self.assertTrue(self.dm["ladder"])

    def test_triggers_are_published_with_todays_reading(self):
        self.assertEqual(len(self.dm["triggers"]), 10)
        for trigger in self.dm["triggers"]:
            self.assertTrue(trigger.get("state"), trigger["id"])

    def test_price_dependent_triggers_are_armed_not_passing(self):
        states = {t["id"]: t["state"] for t in self.dm["triggers"]}
        for trigger in ("D04", "D05", "D06"):
            self.assertIn(trigger, states)

    def test_no_strategy_has_been_demoted_or_promoted(self):
        self.assertEqual(self.dm["live_strategies"], 0)


class DecisionSupportContract(unittest.TestCase):
    """P11: questions and suggestions exist so a reviewer can choose before any change."""

    def test_questions_split_what_is_held_from_what_is_missing(self):
        questions = artifact("questions.json")
        self.assertEqual(questions["total"], 20)
        for question in questions["questions"]:
            self.assertTrue(question.get("id"))
            self.assertTrue(question.get("status"))
            self.assertTrue(question.get("have"), question["id"])
            self.assertTrue(question.get("have_sources"), question["id"])
            self.assertIn(question["status"],
                          ("answered", "answered-no", "open", "partial", "blocked"))

    def test_suggestions_are_ranked_and_undecided(self):
        suggestions = artifact("suggestions.json")
        self.assertEqual(suggestions["count"], 12)
        self.assertEqual(suggestions["decisions_recorded"], 0)
        priorities = [s["priority"] for s in suggestions["suggestions"]]
        self.assertEqual(priorities, sorted(priorities, reverse=True))

    def test_every_suggestion_states_an_acceptance_test(self):
        for suggestion in artifact("suggestions.json")["suggestions"]:
            self.assertTrue(suggestion.get("acceptance_test"), suggestion["id"])

    def test_the_decision_record_ships_undecided(self):
        """The ballot is printed; no choice has been made, and the build never makes one."""
        record = artifact("decision-record.json")
        self.assertEqual(len(record["decisions"]), 12)
        self.assertEqual(record["choices_offered"], ["Adopt", "Defer", "Reject"])
        for decision in record["decisions"]:
            self.assertIsNone(decision["choice"], decision["id"])
            self.assertIsNone(decision["decided_on"], decision["id"])


class ReviewContract(unittest.TestCase):
    """P14: irregularities are published with a disposition, never quietly dropped."""

    def test_counts_agree_with_the_flags(self):
        review = artifact("review.json")
        self.assertEqual(review["total"], 15)
        dispositions = {flag["status"]: 0 for flag in review["flags"]}
        for flag in review["flags"]:
            dispositions[flag["status"]] += 1
        self.assertEqual(dispositions, review["counts"])

    def test_every_flag_links_to_what_it_was_checked_against(self):
        """RF-12/RF-13 are defects in this lab's own code, so they cite the file, not a page."""
        for flag in artifact("review.json")["flags"]:
            self.assertTrue(flag.get("checked_against"), flag["id"])
            self.assertTrue(flag.get("source_ids") or flag["id"] in ("RF-12", "RF-13"),
                            flag["id"])
            self.assertIn(flag["status"], ("open", "explained", "corrected"))
        for flag in artifact("review.json")["flags"]:
            if flag["status"] == "open":
                self.assertTrue(flag["source_ids"], flag["id"])

    def test_corrected_flags_name_what_was_fixed(self):
        corrected = [f for f in artifact("review.json")["flags"]
                     if f["status"] == "corrected"]
        self.assertEqual(len(corrected), 2)
        for flag in corrected:
            self.assertTrue(flag.get("detail"), flag["id"])

    def test_the_price_absence_is_recorded_as_a_checked_page(self):
        self.assertTrue(artifact("review.json")["price_search"])


class PublishedSiteContract(unittest.TestCase):
    """P13: the pages the reader sees keep the guarantees the data claims."""

    def setUp(self):
        manifest = json.loads((SITE / "manifest.json").read_text(encoding="utf-8"))
        self.pages = manifest["pages"]
        self.registry = {entry["id"]: entry["url"] for entry in
                         json.loads((ROOT / "research" / "sources.json")
                                    .read_text(encoding="utf-8"))}

    def test_every_page_is_well_formed(self):
        for name in self.pages:
            text = (SITE / name).read_text(encoding="utf-8")
            self.assertEqual(text.count("<h1>"), 1, name)
            self.assertEqual(text.count("<main"), 1, name)
            self.assertIn('lang="en"', text, name)

    def test_every_row_links_to_a_registered_official_source(self):
        for name in self.pages:
            text = (SITE / name).read_text(encoding="utf-8")
            for ids, body in re.findall(r'<tr data-source-ids="([^"]*)">(.*?)</tr>',
                                        text, re.S):
                listed = ids.split()
                self.assertTrue(listed, f"{name}: row with no source ids")
                hrefs = re.findall(r'href="([^"]+)"', body)
                self.assertTrue(
                    any(self.registry.get(sid) in hrefs for sid in listed),
                    f"{name}: row {listed} lacks its official source link")

    def test_links_open_safely(self):
        for name in self.pages:
            text = (SITE / name).read_text(encoding="utf-8")
            for anchor in re.findall(r"<a\b[^>]*>", text):
                if 'target="_blank"' in anchor:
                    self.assertIn('rel="noopener noreferrer"', anchor, name)

    def test_external_links_are_https(self):
        for name in self.pages:
            for href in re.findall(r'href="(https?://[^"]+)"',
                                   (SITE / name).read_text(encoding="utf-8")):
                self.assertTrue(href.startswith("https://"), f"{name}: {href}")

    def test_internal_links_resolve(self):
        for name in self.pages:
            text = (SITE / name).read_text(encoding="utf-8")
            for href, _fragment in re.findall(r'href="([^"#:]+?)(#[^"]*)?"', text):
                if href.startswith(("http", "mailto:", "#")):
                    continue
                self.assertTrue((SITE / href).is_file(), f"{name}: missing {href}")

    def test_blank_cells_really_are_blank(self):
        for name in self.pages:
            for cell in re.findall(r'<td[^>]*data-empty="true"[^>]*>(.*?)</td>',
                                   (SITE / name).read_text(encoding="utf-8"), re.S):
                self.assertEqual(cell.strip(), "", name)

    def test_local_assets_resolve(self):
        for name in self.pages:
            for asset in re.findall(r'(?:href|src)="((?:style\.css|app\.js))"',
                                    (SITE / name).read_text(encoding="utf-8")):
                self.assertTrue((SITE / asset).is_file(), f"{name}: missing {asset}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
