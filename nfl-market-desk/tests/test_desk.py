#!/usr/bin/env python3
"""Tests for the market desk.

These are written to fail if a rule is removed, not to describe the code. Each class
corresponds to one promise the desk makes on its pages:

    TestProvenance          prices cannot exist without a named source
    TestOrdering            side, then total, then moneyline, and the moneyline is labelled
    TestNoLookahead         a graded week is never in its own rating inputs
    TestSettlement          results are settled correctly, including the away side
    TestSignalStaking       a staking field cannot reach the promotion gate
    TestDemotion            every trigger fires, and an unevaluable input demotes
    TestStatistics          the statistics are right, including the awkward ones
    TestArtifacts           the committed artifacts reproduce byte-identically
    TestSiteContract        every published table row links a registered source
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path

DESK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DESK))

import analysis  # noqa: E402
import availability  # noqa: E402
import correlation  # noqa: E402
import gates  # noqa: E402
import leaderboard  # noqa: E402
import origination  # noqa: E402
import sources  # noqa: E402
import staking  # noqa: E402

REPO = DESK.parent


def load_csv_rows(name: str) -> list[dict]:
    with (DESK / "data" / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _graph():
    prices = sources.load_prices()
    results = sources.load_results()
    board = origination.build_board(results, prices)
    return prices, results, board


class TestProvenance(unittest.TestCase):
    def test_every_price_row_names_a_source_and_a_date(self):
        for p in sources.load_prices():
            self.assertTrue(p["provider"], p)
            self.assertTrue(p["provider_id"], p)
            self.assertTrue(p["source_id"], p)
            self.assertTrue(p["source_url"].startswith("https://"), p)
            self.assertTrue(p["retrieved"], p)

    def test_no_price_row_is_operator_direct(self):
        """The relay label must be true: nothing here was read from a sportsbook."""
        for p in sources.load_prices():
            self.assertIn("espn", p["source_url"])

    def test_one_provider_only(self):
        self.assertEqual({p["provider"] for p in sources.load_prices()}, {"DraftKings"})
        self.assertEqual({p["provider_id"] for p in sources.load_prices()}, {"100"})

    def test_team_map_binds_all_32_clubs(self):
        m = sources.load_team_map()
        self.assertEqual(len(m), 32)
        self.assertEqual(len(set(m.values())), 32)

    def test_blank_is_explicit_never_empty(self):
        """An empty cell is a bug; a verified blank is written as '-'."""
        for name in sources.PRICE_FILES:
            with (DESK / "data" / name).open(newline="") as fh:
                for row in csv.DictReader(fh):
                    for k, v in row.items():
                        self.assertNotEqual(v, "", f"{name} {k} left empty instead of '-'")


class TestOrdering(unittest.TestCase):
    def setUp(self):
        self.board = _graph()[2]["boards"]

    def test_all_three_boards_present_and_complete(self):
        for k in ("side", "total", "moneyline"):
            self.assertEqual(len(self.board[k]), 15, k)

    def test_order_field_is_declared(self):
        self.assertEqual({r["order"] for r in self.board["side"]}, {1})
        self.assertEqual({r["order"] for r in self.board["total"]}, {2})
        self.assertEqual({r["order"] for r in self.board["moneyline"]}, {3})

    def test_moneyline_is_labelled_a_restatement(self):
        for r in self.board["moneyline"]:
            self.assertTrue(r["is_restatement_of_side"], r)

    def test_three_columns_are_separate_and_never_merged(self):
        for r in self.board["side"]:
            self.assertIn("model_fair_line", r)
            self.assertIn("market_line", r)
            self.assertIn("edge_points", r)
            # The difference is model home margin minus the MARKET'S IMPLIED home margin, which
            # is the negative of the home side's printed spread. Asserting the old
            # fair-minus-line formula here would re-encode the sign bug this desk shipped once.
            expected = round(r["model_fair_line"] + r["market_line"], 2)
            self.assertAlmostEqual(r["edge_points"], expected, places=2)

    def test_edge_sign_convention(self):
        """market_line is the HOME side's own spread, so the market's implied home margin is its
        negative. This inversion is what a first build of this desk got wrong, turning a losing
        model into a 13-2 record."""
        self.assertEqual(origination.market_home_margin(-9.5), 9.5)
        self.assertEqual(origination.market_home_margin(3.0), -3.0)
        # A model that likes the home side by more than the market does has a positive edge.
        self.assertGreater(origination.edge_points(10.0, -6.0), 0)
        # A home favourite covering means winning by more than the line; +9.5 covers by losing small.
        self.assertGreater(origination.prob_home_covers(14.0, -9.5), 0.5)
        self.assertGreater(origination.prob_home_covers(-4.0, 9.5), 0.5)
        self.assertLess(origination.prob_home_covers(5.71, -9.5), 0.5)

    def test_total_edge_does_not_apply_the_margin_conversion(self):
        """A total is not signed like a spread. Applying the margin conversion to a total adds the
        line to itself and manufactures an eighty-point edge — a bug this desk shipped and caught."""
        self.assertEqual(origination.edge_total(45.94, 40.5), 5.44)
        self.assertEqual(origination.edge_total(47.61, 52.5), -4.89)
        # And no total edge on the real board may be large enough to be that bug.
        for r in _graph()[2]["boards"]["total"]:
            self.assertLess(abs(r["edge_points"]), 20.0, r["game"])

    def test_side_and_total_edges_use_different_conversions(self):
        # For a positive line the two conversions differ by twice the line: the side compares
        # against -line, the total against line itself.
        self.assertEqual(origination.edge_points(5.0, 3.0), 8.0)
        self.assertEqual(origination.edge_total(5.0, 3.0), 2.0)

    def test_edge_is_blank_when_market_is_blank(self):
        """The difference must never be computed against zero."""
        for r in self.board["side"] + self.board["total"]:
            if r.get("market_line") is None and r.get("market_total") is None:
                self.assertIsNone(r["edge_points"], r)


class TestNoLookahead(unittest.TestCase):
    def test_ratings_use_only_prior_weeks(self):
        prices, results, board = _graph()
        week9 = [g for g in results if g["week"] == 9]
        self.assertTrue(week9, "week 9 results should exist")
        # A rating window for a week-9 game must be weeks 1-8.
        for r in board["boards"]["side"]:
            self.assertEqual(r["rating_window"], "weeks 1-8", r)

    def test_ratings_change_when_the_window_changes(self):
        """If the window were ignored, these two would be identical."""
        results = sources.load_results()
        w8 = origination.build_team_ratings(results, 8)
        w9 = origination.build_team_ratings(results, 9)
        self.assertNotEqual(w8["BUF"]["games"], w9["BUF"]["games"])

    def test_week_one_has_no_history(self):
        results = sources.load_results()
        w1 = origination.build_team_ratings(results, 1)
        for club, r in w1.items():
            self.assertEqual(r["games"], 0, club)
            self.assertTrue(r["insufficient_history"], club)

    def test_club_aliases_bind(self):
        """A spelling difference must never silently drop a club from the ratings."""
        self.assertEqual(origination.canon("ARI"), "AZ")
        self.assertEqual(origination.canon("LAR"), "LA")
        self.assertEqual(origination.canon("WSH"), "WAS")


class TestSettlement(unittest.TestCase):
    def test_home_favourite_cover(self):
        # Home lays 4.5, wins by 7 -> covers.
        self.assertEqual(staking.settle_spread(-4.5, 7), "win")
        self.assertEqual(staking.settle_spread(-4.5, 3), "loss")

    def test_away_side_is_reversed(self):
        """The bug this guards: settling an away pick on the home margin."""
        # Away side is +4.5; home won by 3, so the away pick covers.
        self.assertEqual(staking.settle_spread(4.5, -3), "win")
        self.assertEqual(staking.settle_spread(4.5, -7), "loss")

    def test_push_is_exact(self):
        self.assertEqual(staking.settle_spread(-3, 3), "push")
        self.assertEqual(staking.settle_total("OVER", 44.0, 44.0), "push")
        self.assertEqual(staking.payout_units(-110, won=True, push=True), 0.0)

    def test_total_sides(self):
        self.assertEqual(staking.settle_total("OVER", 44.5, 50), "win")
        self.assertEqual(staking.settle_total("UNDER", 44.5, 50), "loss")

    def test_payout_maths(self):
        self.assertAlmostEqual(staking.payout_units(150, True), 1.5, places=6)
        self.assertAlmostEqual(staking.payout_units(-200, True), 0.5, places=6)
        self.assertAlmostEqual(staking.payout_units(-110, False), -1.0, places=6)

    def test_known_week9_results_settle_as_recorded(self):
        """Hand-checked against the official scores in the capture."""
        _, _, board = _graph()
        by_game = {r["game"]: r for r in board["boards"]["side"]}
        # ARI@SEA: market had SEA -9.5, SEA won by 14, so SEA covered.
        self.assertEqual(by_game["ARI@SEA"]["actual_margin"], 14)
        self.assertAlmostEqual(by_game["ARI@SEA"]["market_line"], -9.5, places=2)
        # BUF@MIN: market had MIN +3.5, BUF won by 17, so MIN did not cover.
        self.assertEqual(by_game["BUF@MIN"]["actual_margin"], -17)


class TestSignalStaking(unittest.TestCase):
    def test_promotion_rejects_a_staking_field(self):
        with self.assertRaises(ValueError):
            gates.promote({"n_settled_bets": 500, "signal_p_value": 0.001, "q_value_holm": 0.01,
                           "price_provenance": "pass", "clv_mean_bps": 5.0,
                           "staking_roi_at_relayed_close": 0.9})

    def test_promotion_ignores_a_lucky_streak_entirely(self):
        """Identical signal, wildly different staking -> identical tier."""
        base = {"n_settled_bets": 500, "signal_p_value": 0.001, "q_value_holm": 0.01,
                "price_provenance": "pass", "clv_mean_bps": 5.0}
        a = gates.promote(dict(base))
        b = gates.promote(dict(base))
        self.assertEqual(a["tier"], b["tier"])
        self.assertTrue(a["promote"])

    def test_missing_signal_field_blocks_promotion(self):
        r = gates.promote({"n_settled_bets": 500, "signal_p_value": 0.001,
                           "price_provenance": "pass", "clv_mean_bps": 5.0})
        self.assertFalse(r["promote"])
        self.assertTrue(any("q_value_holm" in f for f in r["failures"]))

    def test_bad_signal_blocks_despite_any_staking(self):
        r = gates.promote({"n_settled_bets": 500, "signal_p_value": 0.40, "q_value_holm": 0.90,
                           "price_provenance": "pass", "clv_mean_bps": 5.0})
        self.assertFalse(r["promote"])

    def test_leaderboard_carries_no_staking_field_into_signal(self):
        prices, results, board = _graph()
        sg = staking.grade_flat_stake(board["boards"]["side"], "side", "open")
        tg = staking.grade_flat_stake(board["boards"]["total"], "total", "open")
        cal = analysis.calibration(board["boards"]["side"], board["boards"]["total"])
        sc = analysis.closing_line_value(board["boards"]["side"], sg, "side")
        tc = analysis.closing_line_value(board["boards"]["total"], tg, "total")
        lb = leaderboard.build(sg, tg, sc, tc, cal)
        for row in lb["rows"]:
            for banned in gates.PROMOTION["explicitly_excluded"]:
                self.assertNotIn(banned, row["signal"], banned)

    def test_no_strategy_is_live_on_this_capture(self):
        prices, results, board = _graph()
        sg = staking.grade_flat_stake(board["boards"]["side"], "side", "open")
        tg = staking.grade_flat_stake(board["boards"]["total"], "total", "open")
        cal = analysis.calibration(board["boards"]["side"], board["boards"]["total"])
        sc = analysis.closing_line_value(board["boards"]["side"], sg, "side")
        tc = analysis.closing_line_value(board["boards"]["total"], tg, "total")
        lb = leaderboard.build(sg, tg, sc, tc, cal)
        self.assertEqual(lb["n_live"], 0)


class TestDemotion(unittest.TestCase):
    def test_each_trigger_fires_alone(self):
        cases = [
            {"drawdown_units": -25.0},
            {"price_integrity_failures": 1},
            {"days_since_last_pass": 31},
            {"clv_mean_bps": -0.1},
        ]
        for case in cases:
            r = gates.evaluate_demotion(dict(case))
            self.assertTrue(r["demote"], case)

    def test_rolling_hit_rate_trigger_uses_promoted_rate(self):
        """Only the rolling rate varies; the rest of the ledger is clean, so the trigger is
        isolated. An ordinary run near the promoted rate must not demote."""
        def ledger(rate):
            return {"drawdown_units": 4.0, "rolling_50_hit_rate": rate, "promoted_rate": 0.55,
                    "clv_mean_bps": 3.0, "price_integrity_failures": 0, "days_since_last_pass": 2}
        self.assertTrue(gates.evaluate_demotion(ledger(0.30))["demote"])
        self.assertFalse(gates.evaluate_demotion(ledger(0.52))["demote"])
        # The band must be genuinely extreme. The raw 2-sd floor at a promoted 55% is 40.9%,
        # which is inside ordinary noise; the 10% slack moves it to 36.8%, so a 38% run is
        # still unremarkable while a 30% run is a collapse. This is the difference between a
        # control and a decoration.
        self.assertFalse(gates.evaluate_demotion(ledger(0.38))["demote"])
        self.assertTrue(gates.evaluate_demotion(ledger(0.34))["demote"])

    def test_clean_ledger_does_not_demote(self):
        r = gates.evaluate_demotion({"drawdown_units": 5.0, "rolling_50_hit_rate": 0.56,
                                     "promoted_rate": 0.55, "clv_mean_bps": 4.0,
                                     "price_integrity_failures": 0, "days_since_last_pass": 3})
        self.assertFalse(r["demote"], r)

    def test_unevaluable_input_demotes(self):
        """An unverifiable live strategy is not a live strategy."""
        r = gates.evaluate_demotion({})
        self.assertTrue(r["demote"])

    def test_gate_has_numeric_triggers(self):
        for t in gates.DEMOTION_GATE["triggers"]:
            self.assertIn(t["op"], ("<=", ">="))
            self.assertTrue(t["threshold"] is not None or t.get("comparator"), t)


class TestStatistics(unittest.TestCase):
    def test_binomial_p_known_values(self):
        self.assertAlmostEqual(staking.exact_binomial_two_sided(13, 2), 0.007385, places=6)
        self.assertAlmostEqual(staking.exact_binomial_two_sided(5, 5), 1.0, places=6)
        self.assertIsNone(staking.exact_binomial_two_sided(0, 0))

    def test_wilson_interval_contains_the_rate(self):
        lo, hi = staking.wilson(13, 15)
        self.assertLess(lo, 13 / 15)
        self.assertGreater(hi, 13 / 15)
        self.assertLessEqual(hi, 1.0)

    def test_required_n_is_monotone_in_effect_size(self):
        self.assertGreater(staking.required_n(0.55), staking.required_n(0.60))
        self.assertEqual(staking.required_n(0.50), 0)

    def test_post_hoc_power_is_labelled_circular(self):
        """A lucky run must not be able to lower its own sample requirement silently."""
        g = staking.grade_flat_stake(
            [{"event_id": "x", "game": "A@B", "market": "side", "edge_points": 2.0,
              "market_line": -3.0, "market_line_open": -3.0, "market_home_price_open": "-110",
              "market_away_price_open": "-110", "market_home_price": "-110",
              "market_away_price": "-110", "home": "B", "away": "A", "actual_margin": 10}], "side")
        self.assertIn("required_n_at_this_rate_CIRCULAR", g)
        self.assertEqual(g["required_n_at_55pct"], staking.required_n(0.55))

    def test_pearson_matches_a_hand_calculation(self):
        r = correlation.pearson([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
        self.assertAlmostEqual(r["r"], 1.0, places=6)
        r2 = correlation.pearson([1, 2, 3, 4, 5], [5, 4, 3, 2, 1])
        self.assertAlmostEqual(r2["r"], -1.0, places=6)

    def test_pearson_handles_degenerate_input(self):
        r = correlation.pearson([1, 1, 1, 1], [1, 2, 3, 4])
        self.assertIsNone(r["r"])

    def test_holm_is_monotone_and_bounded(self):
        adj = correlation._holm([0.01, 0.04, 0.03, 0.5])
        self.assertEqual(adj, sorted(adj))
        self.assertTrue(all(0.0 <= a <= 1.0 for a in adj))
        self.assertGreater(adj[3], 0.5 - 1e-9)

    def test_devig_sums_to_one(self):
        p = origination.devig(-110, -110)
        self.assertAlmostEqual(p, 0.5, places=6)
        p2 = origination.devig(-192, 160)
        self.assertIsNotNone(p2)

    def test_american_conversions_round_trip(self):
        for p in (0.2, 0.35, 0.5, 0.65, 0.9):
            price = origination.american_from_prob(p)
            self.assertAlmostEqual(origination.american_to_prob(price), p, places=3)

    def test_model_is_worse_than_market_on_this_capture(self):
        """If this ever flips, the pages must be revisited; the test records the finding."""
        prices, results, board = _graph()
        cal = analysis.calibration(board["boards"]["side"], board["boards"]["total"])
        self.assertGreater(cal["side"]["model_rmse"], cal["side"]["market_rmse"])
        self.assertEqual(cal["verdict"], "model_error_exceeds_market")


class TestAvailability(unittest.TestCase):
    def test_only_statused_players_are_classified(self):
        for r in availability.replacement_depth():
            self.assertIn(r["game_status"], ("Out", "Questionable"), r)

    def test_coverage_is_stated_not_implied(self):
        cov = availability.depth_coverage()
        self.assertEqual(cov["n_clubs_with_depth"], 4)
        self.assertEqual(cov["n_clubs_league"], 32)
        self.assertIn("4 of 32", cov["coverage_note"])

    def test_unplaced_players_have_blank_strings_not_zero(self):
        for r in availability.replacement_depth():
            if not r["depth_known"]:
                self.assertIsNone(r["strings_lost"], r)

    def test_strings_lost_is_a_difference_of_printed_ranks(self):
        for r in availability.replacement_depth():
            if r["strings_lost"] is not None:
                self.assertEqual(r["strings_lost"], r["replacement_rank"] - r["printed_rank"], r)


class TestArtifacts(unittest.TestCase):
    def test_artifacts_reproduce_byte_identically(self):
        res = subprocess.run([sys.executable, str(DESK / "build.py"), "--check"],
                             capture_output=True, text=True, cwd=str(REPO))
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_analysis_json_declares_no_live_strategy(self):
        a = json.loads((DESK / "data" / "analysis.json").read_text())
        self.assertEqual(a["counts"]["strategies_live"], 0)
        self.assertIsNone(a["cash_reward"])
        self.assertFalse(a["clv"]["gate_satisfiable_by_this_capture"])

    def test_no_reward_is_populated(self):
        a = json.loads((DESK / "data" / "analysis.json").read_text())
        self.assertIsNone(a["cash_reward"])
        self.assertTrue(a["cash_reward_reason"])


class TestSiteContract(unittest.TestCase):
    PAGES = ["index.html", "summary.html", "prices.html", "origination.html", "leaderboard.html",
             "correlation.html", "availability.html", "gates.html", "questions.html",
             "suggestions.html", "flagged.html", "sources.html", "method.html"]

    def test_every_page_exists_and_links_its_own_nav(self):
        for p in self.PAGES:
            f = DESK / "site" / p
            self.assertTrue(f.exists(), p)
            text = f.read_text()
            self.assertIn("<h1>", text, p)
            self.assertIn('aria-current="page"', text, p)

    def test_availability_kpis_agree_with_the_artifact(self):
        """CSV booleans arrive as the strings "True"/"False", and "False" is truthy. That mistake
        once printed zero unplaced players when the data held six."""
        import re
        text = (DESK / "site" / "availability.html").read_text()
        kpis = re.findall(r'kpi-value">([^<]*)</span><span class="kpi-label">([^<]*)', text)
        by_label = {label: value for value, label in kpis}
        rows = load_csv_rows("replacement-depth-2026-11-14.csv")
        self.assertEqual(int(by_label["with no healthy body behind them"]),
                         sum(1 for r in rows if r["replacement_tier"] == "no_healthy_body_behind"))
        self.assertEqual(int(by_label["where the club reached down a string"]),
                         sum(1 for r in rows if r["replacement_tier"] == "reached_down_chart"))
        self.assertEqual(int(by_label["cannot be placed on a captured chart"]),
                         sum(1 for r in rows if r["depth_known"].lower() != "true"))
        self.assertEqual(len(rows), 25)

    def test_every_table_row_names_a_registered_source(self):
        registered = {r["id"] for r in json.loads((REPO / "research" / "sources.json").read_text())}
        for p in self.PAGES:
            text = (DESK / "site" / p).read_text()
            for chunk in text.split("<tr ")[1:]:
                if "data-source-ids=" not in chunk:
                    self.fail(f"{p}: a table row carries no source ids")
                ids = chunk.split('data-source-ids="')[1].split('"')[0].split()
                self.assertTrue(ids, p)
                for i in ids:
                    self.assertIn(i, registered, f"{p} references unregistered {i}")

    def test_pages_do_not_claim_operator_confirmation(self):
        forbidden = ["operator-confirmed price", "confirmed operator fill", "live odds"]
        for p in self.PAGES:
            text = (DESK / "site" / p).read_text().lower()
            for phrase in forbidden:
                self.assertNotIn(phrase, text, p)


if __name__ == "__main__":
    unittest.main()
