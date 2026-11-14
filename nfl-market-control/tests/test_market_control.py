"""Contracts for NFL quote storage, signal/staking separation and demotion controls."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "nfl-market-control"))
import engine  # noqa: E402
from scripts.serve_site import Handler


TEST_SOURCES = {
    "TEST-ODDS": {
        "id": "TEST-ODDS",
        "publisher": "Synthetic test publisher",
        "title": "Synthetic test odds fixture (not real data)",
        "url": "https://odds.example/feed",
        "kind": "market prices",
        "scope": "Synthetic unit-test input only; never published.",
        "checked_on": "2026-11-14",
        "access": "Synthetic unit-test fixture.",
        "rights_status": "authorized",
        "rights_scope": "Synthetic data only; not a real licence.",
        "rights_reference": "synthetic-unit-test-license-reference",
    },
}


def quote(**overrides):
    row = {
        "snapshot_id": "TEST-W10-01-SPREAD-HOME-OPEN",
        "game_id": "W10-01",
        "market": "spread",
        "market_variant": "mainline",
        "selection": "home",
        "phase": "opening",
        "operator": "Synthetic Test Book",
        "line": -3.5,
        "american_odds": -110,
        "captured_at_utc": "2026-11-14T08:00:00Z",
        "source_id": "TEST-ODDS",
        "source_url": "https://odds.example/feed/game/W10-01",
        "rights_status": "authorized",
        "rights_reference": "synthetic-unit-test-license-reference",
        "verification_status": "verified",
        "evidence_sha256": "a" * 64,
    }
    row.update(overrides)
    return row


class MarketControlPreviewTests(unittest.TestCase):
    def test_public_preview_allows_control_pages_assets_and_empty_jsonl(self):
        paths = (
            "nfl-market-control/site/index.html",
            "nfl-market-control/site/style.css",
            "nfl-market-control/site/app.js",
            "nfl-market-control/site/manifest.json",
            "nfl-market-control/data/quote_snapshots.jsonl",
        )
        for relative in paths:
            with self.subTest(path=relative):
                handler = object.__new__(Handler)
                handler.path = "/" + relative
                self.assertEqual(handler.public_path(), (ROOT / relative).resolve())
        handler = object.__new__(Handler)
        self.assertEqual(handler.guess_type("quote_snapshots.jsonl"), "application/x-ndjson")


class MarketMatrixTests(unittest.TestCase):
    def test_origination_sequence_is_side_total_moneyline(self):
        policy = engine.validate_policy()
        self.assertEqual([row["market"] for row in policy["origination_order"]],
                         ["spread", "total", "moneyline"])
        rows = engine.market_matrix([])
        self.assertEqual([row["market_key"] for row in rows[:28]], ["spread"] * 28)
        self.assertEqual([row["market_key"] for row in rows[28:56]], ["total"] * 28)
        self.assertEqual([row["market_key"] for row in rows[56:]], ["moneyline"] * 28)

    def test_expected_opening_and_closing_slots_cover_every_market_selection(self):
        rows = engine.market_matrix([])
        self.assertEqual(len(rows), 84)  # 14 games × 3 markets × 2 selections
        self.assertEqual(len({row["id"] for row in rows}), 84)
        self.assertEqual(len(rows) * 2, 168)  # opening + closing per selection
        for row in rows:
            self.assertTrue(row["event_source_url"].startswith("https://www.nfl.com/games/"))
            self.assertIn("NFL-SCHED-W10", row["source_ids"])
            self.assertIn(row["market_key"], {"spread", "total", "moneyline"})

    def test_market_values_and_differences_stay_blank_without_quotes(self):
        rows = engine.market_matrix([])
        for row in rows:
            for field in (
                "opening_market_value", "opening_market_line", "opening_implied_probability",
                "opening_american_odds", "opening_line_difference", "opening_probability_difference",
                "opening_timestamp_utc", "closing_market_value", "closing_market_line",
                "closing_implied_probability", "closing_american_odds", "closing_line_difference",
                "closing_probability_difference",
                "closing_timestamp_utc",
            ):
                self.assertIsNone(row[field], f"{row['id']} {field}")
            self.assertEqual(row["status"], "Expected slot only · no authorized quote in repository")
        for row in rows:
            if row["market_key"] == "spread":
                self.assertIsNotNone(row["fair_line"])
                self.assertIsNone(row["fair_probability"], "win probability is not spread-cover probability")
            elif row["market_key"] == "total":
                self.assertIsNotNone(row["fair_line"])
                self.assertIsNone(row["fair_probability"], "no calibrated over/under probability exists")
                self.assertIsNone(row["fair_american_odds"])
            else:
                self.assertIsNone(row["fair_line"], "moneyline has no point line")
                self.assertIsNotNone(row["fair_probability"])
                self.assertIsNotNone(row["fair_american_odds"])

    def test_fair_market_and_difference_fields_are_distinct_and_unit_consistent(self):
        with patch.object(engine, "sources_by_id", return_value=TEST_SOURCES):
            spread = next(row for row in engine.market_matrix([quote()])
                          if row["game_id"] == "W10-01" and row["market_key"] == "spread"
                          and row["selection"] == "home")
            moneyline = next(row for row in engine.market_matrix([
                quote(market="moneyline", line=None, american_odds=-150)
            ]) if row["game_id"] == "W10-01" and row["market_key"] == "moneyline"
                 and row["selection"] == "home")
        self.assertEqual(spread["opening_market_value"], -3.5)
        self.assertEqual(spread["opening_market_line"], -3.5)
        self.assertIsNone(spread["opening_implied_probability"])
        self.assertAlmostEqual(spread["opening_line_difference"], spread["fair_line"] - (-3.5))
        self.assertIsNone(spread["opening_probability_difference"])
        self.assertAlmostEqual(moneyline["opening_market_value"], 0.6)
        self.assertIsNone(moneyline["opening_market_line"])
        self.assertEqual(moneyline["opening_implied_probability"], 0.6)
        self.assertAlmostEqual(moneyline["opening_probability_difference"],
                               moneyline["fair_probability"] - 0.6)
        self.assertIsNone(moneyline["opening_line_difference"])

    def test_export_headers_keep_model_market_and_difference_fields_distinct(self):
        rows = engine.read_csv(ROOT / "nfl-market-control/data/price-slot-matrix.csv")
        fields = set(rows[0])
        self.assertTrue({
            "model_fair_line", "opening_market_line", "opening_line_difference",
            "closing_market_line", "closing_line_difference",
        }.issubset(fields))
        self.assertNotIn("opening_market_value", fields)
        self.assertNotIn("closing_market_value", fields)

    def test_no_authorized_price_record_is_committed(self):
        self.assertEqual(engine.read_jsonl(ROOT / "nfl-market-control/data/quote_snapshots.jsonl"), [])
        data = engine.build_data()
        self.assertEqual(data["summary"]["captured_quote_records"], 0)
        self.assertEqual(data["summary"]["expected_open_close_slots"], 168)

    def test_official_results_summary_comes_from_existing_analysis(self):
        data = engine.build_data()
        analysis = engine.read_json(ROOT / "nfl-results/analysis.json")
        leg = analysis["correlations"]["leg_dependence"]
        self.assertEqual(data["summary"]["result_games"], 136)
        self.assertEqual(data["summary"]["correlation_n"], leg["n_games"])
        self.assertEqual(data["summary"]["correlation_phi"], leg["phi"])
        self.assertEqual(data["summary"]["correlation_p"], leg["p_value"])


class QuoteStoreTests(unittest.TestCase):
    def test_american_implied_probability_is_raw_and_vigged(self):
        self.assertAlmostEqual(engine.implied_probability_american(-110), 110 / 210)
        self.assertAlmostEqual(engine.implied_probability_american(100), 0.5)
        with self.assertRaises(ValueError):
            engine.implied_probability_american(0)

    def test_quote_normalizes_timestamp_and_requires_a_market_source(self):
        clean = engine.validate_quote(quote(captured_at_utc="2026-11-14T03:00:00-05:00"),
                                      sources=TEST_SOURCES, game_ids={"W10-01"})
        self.assertEqual(clean["captured_at_utc"], "2026-11-14T08:00:00Z")
        bad_source = {"TEST-ODDS": {**TEST_SOURCES["TEST-ODDS"], "kind": "schedule"}}
        with self.assertRaisesRegex(ValueError, "not identified as a market-price"):
            engine.validate_quote(quote(), sources=bad_source, game_ids={"W10-01"})

    def test_quote_rejects_unknown_source_rights_or_unverified_status(self):
        with self.assertRaisesRegex(ValueError, "unregistered quote source"):
            engine.validate_quote(quote(source_id="MISSING"), sources={}, game_ids={"W10-01"})
        with self.assertRaisesRegex(ValueError, "authorized use rights"):
            engine.validate_quote(quote(rights_status="unknown"), sources=TEST_SOURCES, game_ids={"W10-01"})
        with self.assertRaisesRegex(ValueError, "source row is verified"):
            engine.validate_quote(quote(verification_status="unverified"), sources=TEST_SOURCES, game_ids={"W10-01"})
        unauthorized_source = {"TEST-ODDS": {**TEST_SOURCES["TEST-ODDS"], "rights_status": "unknown"}}
        with self.assertRaisesRegex(ValueError, "authorized-use scope"):
            engine.validate_quote(quote(), sources=unauthorized_source, game_ids={"W10-01"})
        with self.assertRaisesRegex(ValueError, "does not match the registered authorization"):
            engine.validate_quote(quote(rights_reference="not-the-registered-reference"),
                                  sources=TEST_SOURCES, game_ids={"W10-01"})

    def test_quote_rejects_non_https_wrong_host_bad_odds_and_bad_evidence(self):
        for overrides, message in (
            ({"source_url": "http://odds.example/feed"}, "HTTPS"),
            ({"source_url": "https://other.example/feed"}, "host does not match"),
            ({"source_url": "https://odds.example/other-feed/game/W10-01"}, "outside the registered source scope"),
            ({"american_odds": 0}, "non-zero"),
            ({"american_odds": -110.5}, "must be an integer"),
            ({"evidence_sha256": "not-a-hash"}, "SHA-256"),
            ({"captured_at_utc": "2026-11-14T08:00:00"}, "timezone"),
        ):
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, message):
                engine.validate_quote(quote(**overrides), sources=TEST_SOURCES, game_ids={"W10-01"})

    def test_moneyline_rejects_point_line_and_spread_requires_one(self):
        with self.assertRaisesRegex(ValueError, "no point line"):
            engine.validate_quote(quote(market="moneyline", selection="home", line=-2),
                                  sources=TEST_SOURCES, game_ids={"W10-01"})
        with self.assertRaisesRegex(ValueError, "require a finite market line"):
            engine.validate_quote(quote(line=None), sources=TEST_SOURCES, game_ids={"W10-01"})

    def test_wrong_market_variant_or_game_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "registered mainline"):
            engine.validate_quote(quote(market_variant="alternate"), sources=TEST_SOURCES, game_ids={"W10-01"})
        with self.assertRaisesRegex(ValueError, "outside the originated"):
            engine.validate_quote(quote(game_id="NOT-A-GAME"), sources=TEST_SOURCES, game_ids={"W10-01"})

    def test_closing_must_not_precede_opening(self):
        opening = quote()
        closing = quote(snapshot_id="TEST-CLOSE", phase="closing", captured_at_utc="2026-11-14T07:59:00Z")
        with self.assertRaisesRegex(ValueError, "closing timestamp precedes opening"):
            engine.validate_quote_ledger([opening, closing], sources=TEST_SOURCES, game_ids={"W10-01"})

    def test_duplicate_snapshot_and_slot_are_rejected(self):
        first = quote()
        with self.assertRaisesRegex(ValueError, "duplicate snapshot_id"):
            engine.validate_quote_ledger([first, first], sources=TEST_SOURCES, game_ids={"W10-01"})
        second = quote(snapshot_id="OTHER-ID")
        with self.assertRaisesRegex(ValueError, "duplicate quote slot"):
            engine.validate_quote_ledger([first, second], sources=TEST_SOURCES, game_ids={"W10-01"})

    def test_append_quote_appends_once_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "quotes.jsonl"
            engine.append_quote(path, quote(), sources=TEST_SOURCES, game_ids={"W10-01"})
            self.assertEqual(len(engine.read_jsonl(path)), 1)
            with self.assertRaisesRegex(ValueError, "duplicate"):
                engine.append_quote(path, quote(snapshot_id="SECOND-ID"), sources=TEST_SOURCES,
                                    game_ids={"W10-01"})
            self.assertEqual(len(engine.read_jsonl(path)), 1)


class SeparationAndDemotionTests(unittest.TestCase):
    def test_signal_and_staking_rows_are_separate(self):
        signals = engine.signal_rows()
        stakes = engine.staking_rows(signals)
        self.assertEqual(len(signals), 30)
        self.assertEqual(len(stakes), 30)
        board = next(row for row in signals if row["id"] == "BOARD-SA")
        self.assertEqual((board["bets"], board["record"]), (120, "77–43–0"))
        self.assertEqual(board["signal_status"], "Provisional · not qualified")
        pushed = next(row for row in signals if row["id"] == "M00-SA")
        self.assertEqual((pushed["wins"], pushed["losses"], pushed["pushes"]), (46, 59, 2))
        self.assertEqual(pushed["bets"], pushed["wins"] + pushed["losses"])
        self.assertEqual(pushed["record"], "46–59–2")
        for row in stakes:
            for field in ("opening_price", "closing_price", "stake", "net_roi", "clv", "reward"):
                self.assertIsNone(row[field], f"{row['id']} {field}")
            self.assertNotIn("hit_rate", row)
            self.assertNotIn("signal_status", row)
            self.assertIn("Blocked", row["staking_status"])

    def test_paper_state_does_not_auto_promote_or_demote(self):
        result = engine.demotion_decision(current_state="paper", hard_triggers=["provenance_failure"])
        self.assertEqual(result["state"], "paper")
        self.assertEqual(result["action"], "no_change")

    def test_any_hard_trigger_immediately_demotes_live_to_paper(self):
        result = engine.demotion_decision(current_state="live", hard_triggers=["rights_invalid_or_revoked"])
        self.assertEqual(result["state"], "paper")
        self.assertEqual(result["action"], "demote")
        self.assertEqual(result["reasons"], ["rights_invalid_or_revoked"])
        self.assertIn("never automatic", result["promotion"])

    def test_statistical_trigger_uses_minimum_sample_and_nonpositive_bound(self):
        below = engine.demotion_decision(current_state="live", settled_bets=99, roi_lower_bound_95=-0.5)
        self.assertEqual(below["state"], "live")
        at_floor = engine.demotion_decision(current_state="live", settled_bets=100, roi_lower_bound_95=0.0)
        self.assertEqual(at_floor["state"], "paper")
        positive = engine.demotion_decision(current_state="live", settled_bets=100, roi_lower_bound_95=0.01)
        self.assertEqual(positive["state"], "live")
        missing = engine.demotion_decision(current_state="live", settled_bets=100, roi_lower_bound_95=None)
        self.assertEqual(missing["state"], "live")

    def test_invalid_demotion_inputs_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "unknown hard demotion"):
            engine.demotion_decision(current_state="live", hard_triggers=["bad_trigger"])
        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            engine.demotion_decision(current_state="live", settled_bets=-1)
        with self.assertRaisesRegex(ValueError, "finite or None"):
            engine.demotion_decision(current_state="live", roi_lower_bound_95=float("nan"))

    def test_review_register_has_complete_questions_and_unselected_suggestions(self):
        engine.validate_register()
        register = engine.review_register()
        self.assertEqual(len(register["questions"]), 8)
        self.assertEqual(len(register["suggestions"]), 6)
        self.assertEqual(len(register["flags"]), 8)
        self.assertTrue(all(row["review_state"] == "Unselected" for row in register["suggestions"]))
        self.assertTrue(all(row["unverified_value"] is None for row in register["flags"]))


if __name__ == "__main__":
    unittest.main()
