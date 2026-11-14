#!/usr/bin/env python3
"""Tests for the market-lifecycle desk.

Reference tests pin the maths against hand-checkable values; contract tests enforce the
published properties: blanks stay blank with reasons, the leaderboard rank cannot see staking,
the gate never fires on an empty live book, and every site row keeps a registered source.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESK = HERE.parent
REPO = DESK.parent
if str(DESK) not in sys.path:
    sys.path.insert(0, str(DESK))

import corr_audit  # noqa: E402
import demotion  # noqa: E402
import depth  # noqa: E402
import leaderboard  # noqa: E402
import snapshots  # noqa: E402
import stages  # noqa: E402
import vintages  # noqa: E402

DATA = DESK / "data"
SITE = DESK / "site"


def registry() -> dict:
    register = json.loads((REPO / "research" / "sources.json").read_text(encoding="utf-8"))
    return {r["id"]: r["url"] for r in register}


class TestVintages(unittest.TestCase):
    def test_both_vintages_load_with_32_consistent_rows(self):
        for vintage in (vintages.VINTAGE_A, vintages.VINTAGE_B):
            data = vintages.load_vintage(vintage)
            self.assertEqual(len(data["rows"]), 32)
            self.assertRegex(data["sha256"], r"^[0-9a-f]{64}$")

    def test_transition_moves_exactly_nyg_and_was(self):
        result = vintages.check_vintage_transition()
        self.assertEqual(set(result["moved"]), {"NYG", "WAS"})

    def test_publisher_half_up_rounding_is_documented_and_used(self):
        # 2.5/8 = 0.3125 must round half-up to 0.313 (the publisher's printed value).
        import math
        self.assertEqual(math.floor(0.3125 * 1000 + 0.5) / 1000, 0.313)


class TestStages(unittest.TestCase):
    def test_order_is_side_total_moneyline(self):
        self.assertEqual([s["id"] for s in stages.STAGES], ["side", "total", "moneyline"])
        self.assertEqual(stages.STAGES[1]["depends_on"], ["side"])
        self.assertEqual(stages.STAGES[2]["depends_on"], ["side"])

    def test_reconciles_with_canonical_engine(self):
        rec = stages.reconcile_with_canonical()
        self.assertEqual(rec["status"], "PASS")
        self.assertEqual(rec["checked_games"], 14)
        self.assertEqual(rec["mismatches"], [])

    def test_stage_invariants_hold(self):
        for game in stages.originate_staged(vintages.VINTAGE_B):
            self.assertIsInstance(game["stage_fair_home_price"], int)
            self.assertIsInstance(game["stage_fair_away_price"], int)
            self.assertEqual(game["stage_fair_home_price"], -game["stage_fair_away_price"])

    def test_league_anchor_moves_total_but_not_side(self):
        """The league scoring mean cancels in the margin, so games whose clubs' own inputs did
        not change keep the same side and moneyline across vintages; only their totals move.
        W10-01 is the exception: its two clubs (NYG, WAS) gained a played game, which moves
        their own scoring rates and therefore that game's side."""
        a = {g["id"]: g for g in stages.originate_staged(vintages.VINTAGE_A)}
        b = {g["id"]: g for g in stages.originate_staged(vintages.VINTAGE_B)}
        for gid, ga in a.items():
            gb = b[gid]
            if gid == "W10-01":
                self.assertNotAlmostEqual(ga["stage_side_spread_home"],
                                          gb["stage_side_spread_home"], places=6)
                continue
            self.assertAlmostEqual(ga["stage_side_spread_home"], gb["stage_side_spread_home"],
                                   places=9, msg=f"side moved for {gid}")
            self.assertAlmostEqual(ga["stage_model_p_home"], gb["stage_model_p_home"], places=9)
            self.assertNotAlmostEqual(ga["stage_total"], gb["stage_total"], places=6)


class TestSnapshots(unittest.TestCase):
    def setUp(self):
        self.store = snapshots.build_store()

    def test_store_has_42_markets_for_14_games(self):
        self.assertEqual(self.store["counts"]["markets"], 42)
        self.assertEqual(self.store["counts"]["games"], 14)
        ids = [m["market_id"] for m in self.store["markets"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_market_has_opening_and_closing(self):
        for market in self.store["markets"]:
            self.assertEqual(market["opening"]["vintage"], "v2026-11-12")
            self.assertEqual(market["opening"]["captured_on"], "2026-11-12")
            self.assertIn(market["closing"]["vintage"], ("v2026-11-12", "v2026-11-14"))

    def test_market_cells_blank_with_reason_and_diff_blank_rule(self):
        for market in self.store["markets"]:
            self.assertIsNone(market["market_line"])
            self.assertTrue(market["market_reason"])
            self.assertIsNone(market["fair_minus_market"])
            for phase in ("opening", "closing"):
                self.assertIsNone(market[phase]["market_line"])
                self.assertTrue(market[phase]["market_reason"])

    def test_played_game_is_terminal(self):
        terminal = [m for m in self.store["markets"] if m["game_id"] == "W10-01"]
        self.assertEqual(len(terminal), 3)
        for market in terminal:
            self.assertIn("terminal", market["closing"]["status"])

    def test_invariants_check_passes(self):
        self.assertEqual(snapshots.check_store(self.store), [])

    def test_rebuild_is_byte_identical(self):
        again = snapshots.build_store()
        self.assertEqual(json.dumps(self.store, sort_keys=True),
                         json.dumps(again, sort_keys=True))


class TestLeaderboard(unittest.TestCase):
    def setUp(self):
        self.board = leaderboard.build()

    def test_rank_uses_signal_fields_only(self):
        analysis = leaderboard.load_analysis()
        entries = [c["stat"] | {"id": c["id"]} for c in analysis["candidates"]]
        entries = [{"id": c["id"], "name": c["name"], "market": c["market"],
                    "selective": c["selective"], **c["stat"]} for c in analysis["candidates"]]
        ranked = leaderboard.rank_by_signal([dict(e) for e in entries])
        base_order = [e["id"] for e in ranked]
        # Corrupt or permute every conceivable staking field; the order must not move.
        for corruptor in ({"stake_plan": "all-in"}, {"realized_units": 999.0},
                          {"stake_plan": None, "realized_units": None}):
            poisoned = []
            for e in entries:
                row = dict(e)
                row.update(corruptor)
                row["stakes_placed"] = 10 ** 6
                poisoned.append(row)
            self.assertEqual([e["id"] for e in leaderboard.rank_by_signal(poisoned)],
                             base_order)

    def test_ranking_refuses_rows_without_signal(self):
        with self.assertRaises(KeyError):
            leaderboard.rank_by_signal([{"id": "X", "stake_plan": "flat"}])

    def test_signal_table_has_no_staking_keys_and_vice_versa(self):
        for row in self.board["signal"]:
            self.assertFalse({"stake_plan", "stakes_placed", "realized_units"} & set(row))
        for row in self.board["staking"]:
            self.assertFalse({"hit_rate", "p_value", "q_value", "signal_rank"} & set(row))
            self.assertIsNone(row["stake_plan"])
            self.assertEqual(row["stakes_placed"], 0)
            self.assertTrue(row["blocked_by"])

    def test_counts_match_the_engine(self):
        self.assertEqual(self.board["counts"]["graded"], 30)
        self.assertEqual(self.board["counts"]["provisional"], 1)
        self.assertEqual(self.board["counts"]["qualified"], 0)
        self.assertEqual(self.board["signal"][0]["signal_rank"], 1)
        self.assertEqual(self.board["signal"][0]["id"], "BOARD-SA")

    def test_tiers_inherited_not_recomputed(self):
        analysis = leaderboard.load_analysis()
        tiers = {row["id"]: row["tier"] for row in analysis["leaderboard"]}
        for row in self.board["signal"]:
            if row["id"] in tiers:
                self.assertEqual(row["tier"], tiers[row["id"]])


class TestDemotion(unittest.TestCase):
    def test_binomial_reference_values(self):
        self.assertAlmostEqual(demotion.binomial_p_at_most(0, 10, 0.5), 0.5 ** 10, places=12)
        self.assertAlmostEqual(demotion.binomial_p_at_most(20, 20, 0.5), 1.0, places=12)
        self.assertAlmostEqual(demotion.binomial_p_at_most(5, 10, 0.5), 0.623046875, places=9)
        with self.assertRaises(ValueError):
            demotion.binomial_p_at_most(5, 0, 0.5)
        with self.assertRaises(ValueError):
            demotion.binomial_p_at_most(5, 10, 1.0)

    def test_d1_fires_on_collapse_and_retains_on_variance(self):
        fired = demotion.evaluate_d1(window_wins=6, window_n=20, baseline=0.6)
        self.assertTrue(fired["evaluated"] and fired["fired"])
        retained = demotion.evaluate_d1(window_wins=11, window_n=20, baseline=0.6)
        self.assertTrue(retained["evaluated"] and not retained["fired"])

    def test_d1_refuses_to_judge_small_windows(self):
        verdict = demotion.evaluate_d1(window_wins=0, window_n=9, baseline=0.6)
        self.assertFalse(verdict["evaluated"])

    def test_d2_needs_two_consecutive_failures(self):
        fired = demotion.evaluate_d2([(7, 20), (7, 20)], 0.6)
        self.assertTrue(fired["fired"])
        once = demotion.evaluate_d2([(9, 20), (7, 20)], 0.6)
        self.assertFalse(once["fired"])

    def test_d3_d4_d5(self):
        self.assertTrue(demotion.evaluate_d3(0.30, 0.24)["fired"])
        self.assertFalse(demotion.evaluate_d3(0.26, 0.24)["fired"])
        self.assertTrue(demotion.evaluate_d4(1)["fired"])
        self.assertFalse(demotion.evaluate_d4(0)["fired"])
        self.assertTrue(demotion.evaluate_d5(2)["fired"])
        self.assertFalse(demotion.evaluate_d5(0)["fired"])

    def test_gate_on_empty_live_book_is_armed_and_idle(self):
        gate = demotion.build()
        self.assertTrue(gate["armed"])
        self.assertEqual(gate["applied_to"]["live_entries"], 0)
        self.assertEqual(gate["demotions"], [])

    def test_gate_demotes_a_synthetic_live_entry(self):
        verdict = demotion.run_gate({"id": "SYN-1", "window_wins": 4, "window_n": 20,
                                     "baseline": 0.6, "window_brier": 0.24,
                                     "promotion_brier": 0.24,
                                     "untraceable_settlements": 0, "off_plan_stakes": 0})
        self.assertTrue(verdict["demote"])
        self.assertEqual(verdict["fired_trigger"], "D1")


class TestDepth(unittest.TestCase):
    def setUp(self):
        self.view = depth.build()

    def test_counts_match_the_join(self):
        c = self.view["counts"]
        self.assertEqual(c["injury_rows"], 326)
        self.assertEqual(c["on_printed_chart"], 265)
        self.assertEqual(c["named_backup"] + c["no_named_backup"], c["on_printed_chart"])
        self.assertEqual(c["not_on_chart"], 61)

    def test_distribution_covers_every_row(self):
        self.assertEqual(sum(r["n"] for r in self.view["distribution"]), 326)

    def test_starter_losses_are_rank_one(self):
        self.assertTrue(self.view["starter_losses"])
        named = [s for s in self.view["starter_losses"] if s["slot_has_backup"]]
        self.assertGreater(len(named), 100)
        for s in named:
            self.assertTrue(s["replacement"])
            self.assertGreaterEqual(int(s["replacement_rank"]), 2)

    def test_no_replacement_name_is_invented(self):
        for s in self.view["starter_losses"]:
            if not s["slot_has_backup"]:
                self.assertIsNone(s["replacement"])
                self.assertIsNone(s["replacement_rank"])

    def test_spot_verification_traces_all_sampled_rows(self):
        spot = self.view["spot_verification"]
        self.assertEqual(spot["sample_size"], depth.SPOT_SAMPLE)
        self.assertEqual(spot["not_traced"], 0)


class TestCorrelationAudit(unittest.TestCase):
    def test_audit_passes_with_n_on_every_coefficient(self):
        result = corr_audit.build()
        self.assertEqual(result["failed"], 0)
        self.assertGreater(result["audited_rows"], 15)
        rows = [r for section in result["sections"] for r in section["rows"]]
        for row in rows:
            if row["coefficient"] is not None:
                self.assertIsNotNone(row["n"])
                self.assertGreaterEqual(row["n"], 3)
            else:
                self.assertTrue(row["reason"])


class _RowParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self._row, self._in_a, self._href = [], None, False, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr" and "data-source-ids" in attrs:
            self._row = {"ids": attrs["data-source-ids"].split(), "refs": []}
        elif tag == "a" and self._row is not None:
            href = attrs.get("href")
            if href and href.startswith("https://"):
                self._row["refs"].append(href)

    def handle_endtag(self, tag):
        if tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


class TestSiteContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((SITE / "manifest.json").read_text(encoding="utf-8"))
        cls.registry = registry()

    def test_all_pages_present(self):
        self.assertEqual(len(self.manifest["pages"]), 14)
        for name in self.manifest["pages"]:
            self.assertTrue((SITE / name).exists(), name)

    def test_every_row_has_registered_source_and_link(self):
        total_rows = 0
        for name in self.manifest["pages"]:
            parser = _RowParser()
            parser.feed((SITE / name).read_text(encoding="utf-8"))
            for row in parser.rows:
                total_rows += 1
                self.assertTrue(row["ids"], f"{name}: row without source ids")
                for sid in row["ids"]:
                    self.assertIn(sid, self.registry, f"{name}: unregistered id {sid}")
                self.assertTrue(any(self.registry.get(sid) in row["refs"] for sid in row["ids"]),
                                f"{name}: row lacks its registered source link")
        self.assertGreater(total_rows, 400)

    def test_blanks_are_marked_not_faked(self):
        for name in self.manifest["pages"]:
            text = (SITE / name).read_text(encoding="utf-8")
            self.assertNotIn("<td></td>", text, f"{name}: raw empty cell")
            self.assertNotIn("<td>None</td>", text, f"{name}: python None leaked")

    def test_snapshot_page_marks_market_cells_blank(self):
        text = (SITE / "price-snapshots.html").read_text(encoding="utf-8")
        self.assertEqual(text.count('data-empty="true"'), 42)  # one blank market-line cell per record
        self.assertIn("XS09/CF10", text)

    def test_fair_market_diff_page_has_three_columns_with_blanks(self):
        text = (SITE / "fair-market-diff.html").read_text(encoding="utf-8")
        self.assertIn("Model fair line", text)
        self.assertIn("Market line", text)
        self.assertIn("Difference", text)
        self.assertEqual(text.count('data-empty="true"'), 42 * 2)

    def test_leaderboard_pages_state_the_separation(self):
        text = (SITE / "leaderboard.html").read_text(encoding="utf-8")
        self.assertIn("Signal table", text)
        self.assertIn("Staking table", text)
        self.assertIn("cannot mask a bad signal", text)


if __name__ == "__main__":
    unittest.main()
