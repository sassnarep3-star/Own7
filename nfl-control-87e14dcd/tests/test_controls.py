"""Contract tests for NFL price snapshots, signal/staking separation and demotion."""
from __future__ import annotations

import copy
import csv
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))

import build as controls_build
import demotion
import store as price_store


class PriceStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = price_store.build_store()
        cls.model = json.loads((ROOT / "research/nfl/results.json").read_text(encoding="utf-8"))

    def test_every_originated_game_has_side_then_total_then_moneyline(self):
        self.assertEqual(len(self.store["markets"]), len(self.model["games"]) * 3)
        for index in range(0, len(self.store["markets"]), 3):
            group = self.store["markets"][index:index + 3]
            self.assertEqual([r["market_type"] for r in group], ["side", "total", "moneyline"])
            self.assertEqual([r["market_order"] for r in group], [1, 2, 3])

    def test_each_market_has_distinct_open_and_close_slots(self):
        markets = self.store["markets"]
        snapshots = self.store["snapshots"]
        self.assertEqual(len(snapshots), len(markets) * 2)
        self.assertEqual(len({r["snapshot_id"] for r in snapshots}), len(snapshots))
        for market in markets:
            rows = [r for r in snapshots if r["market_id"] == market["market_id"]]
            self.assertEqual([r["phase"] for r in rows], ["opening", "closing"])
            self.assertEqual(market["opening_snapshot_id"], rows[0]["snapshot_id"])
            self.assertEqual(market["closing_snapshot_id"], rows[1]["snapshot_id"])

    def test_market_value_difference_and_quotes_are_blank_not_zero(self):
        self.assertEqual(self.store["counts"]["quotes_collected"], 0)
        self.assertEqual(self.store["counts"]["market_values_filled"], 0)
        self.assertEqual(self.store["counts"]["differences_filled"], 0)
        for row in self.store["markets"]:
            for field in (
                "market_value", "difference", "opening_value", "closing_value",
                "opening_home_price_american", "opening_away_price_american",
                "opening_over_price_american", "opening_under_price_american",
                "closing_home_price_american", "closing_away_price_american",
                "closing_over_price_american", "closing_under_price_american",
            ):
                self.assertIsNone(row[field], f"{row['market_id']} {field}")
        for row in self.store["snapshots"]:
            for field in (
                *price_store.PRICE_FIELDS, "captured_at_utc", "market_open_at_utc",
                "quote_sequence_basis", "operator", "source_id", "source_url",
                "authorization_ref", "settlement_contract_id",
            ):
                self.assertIsNone(row[field], f"{row['snapshot_id']} {field}")

    def test_model_estimates_reproduce_existing_originator_fields(self):
        by_game = {g["id"]: g for g in self.model["games"]}
        by_market = {(r["game_id"], r["market_type"]): r for r in self.store["markets"]}
        for game_id, game in by_game.items():
            self.assertEqual(by_market[(game_id, "side")]["model_fair_value"], game["originated_spread_home"])
            self.assertEqual(by_market[(game_id, "total")]["model_fair_value"], game["originated_total"])
            ml = by_market[(game_id, "moneyline")]
            self.assertEqual(ml["model_fair_value"], game["model_p_home"])
            self.assertEqual(ml["model_fair_home_price_american"], game["fair_home_price"])
            self.assertEqual(ml["model_fair_away_price_american"], game["fair_away_price"])
            self.assertIn("not established", ml["model_fair_value_status"])

    def test_derived_lines_keep_temporal_caveat_and_official_game_link(self):
        for row in self.store["markets"]:
            self.assertIsNone(row["model_capture_time_utc"])
            self.assertIn("unverified", row["temporal_status"].lower())
            self.assertTrue(row["source_url"].startswith("https://www.nfl.com/games/"))
            self.assertIn(price_store.CURRENT_ODDS_SOURCE_ID, row["source_ids"])
            self.assertIn(price_store.CURRENT_TERMS_SOURCE_ID, row["source_ids"])

    def test_rights_and_price_source_are_not_claimed(self):
        self.assertEqual(self.store["source_status"]["authorized_price_source_ids"], [])
        self.assertFalse(self.store["source_status"]["nfl_derived_betting_use_authorized"])
        self.assertIn("does not establish", self.store["source_status"]["odds_route_scope"])

    def test_snapshot_contract_defines_phases_cutoff_and_non_overwrite_rule(self):
        contract = self.store["snapshot_contract"]
        self.assertIn("provider-identified", contract["opening_definition"])
        self.assertIn("15-minute", contract["closing_definition"])
        self.assertIn("do not splice", contract["reference_source_rule"].lower())
        self.assertIn("never overwrite", contract["write_rule"])
        self.assertEqual(contract["closing_window_minutes"], 15)

    def test_snapshot_csv_uses_empty_cells_not_literal_null_or_zero(self):
        text = price_store._csv_text(self.store["snapshots"])
        self.assertNotIn(",None,", text)
        rows = list(csv.DictReader(text.splitlines()))
        self.assertEqual(len(rows), len(self.store["snapshots"]))
        self.assertTrue(all(r["market_number"] == "" for r in rows))
        self.assertTrue(all(r["home_price_american"] == "" for r in rows))
        self.assertTrue(all(r["settlement_contract_id"] == "" for r in rows))

    def _candidate(self):
        return {
            "snapshot_id": "GAME-SIDE-OPEN-1",
            "market_id": "GAME-SIDE",
            "game_id": "GAME",
            "phase": "opening",
            "market_type": "side",
            "source_id": "LICENSED-QUOTE",
            "source_url": "https://quotes.example.test/game",
            "authorization_ref": "license-document-1",
            "operator": "LicensedBook",
            "settlement_contract_id": "spread-regulation-v1",
            "captured_at_utc": "2026-11-10T18:00:00Z",
            "market_open_at_utc": "2026-11-10T17:00:00Z",
            "quote_sequence_basis": "provider_market_open_record",
            "market_number": -2.5,
            "home_price_american": -110,
            "away_price_american": -110,
        }

    @staticmethod
    def _registry(record):
        return {"LICENSED-QUOTE": {
            "id": "LICENSED-QUOTE",
            "url": record["source_url"],
            "kind": "odds",
            "authorization_status": "Approved",
            "authorization_ref": "license-document-1",
        }}

    def _validate(self, record, *, kickoff="2026-11-10T18:15:00Z", allowed=True, existing=None, opening=None, registry=None):
        existing_ids = set() if existing is None else set(existing)
        if existing is None and isinstance(opening, dict):
            existing_ids.add(opening["snapshot_id"])
        price_store.validate_snapshot(
            record,
            registry=registry or self._registry(record),
            authorized_price_source_ids={"LICENSED-QUOTE"} if allowed else set(),
            nfl_data_use_authorized=allowed,
            kickoff_at_utc=kickoff,
            existing_snapshot_ids=existing_ids,
            opening_snapshot=opening,
        )

    def _derive_market_value(self, market, closing, opening):
        return price_store.market_value_and_difference(
            market,
            closing,
            registry=self._registry(closing),
            authorized_price_source_ids={"LICENSED-QUOTE"},
            nfl_data_use_authorized=True,
            kickoff_at_utc="2026-11-10T18:15:00Z",
            existing_snapshot_ids={opening["snapshot_id"]},
            opening_snapshot=opening,
        )

    def test_future_ingest_accepts_authorized_complete_pre_kickoff_open(self):
        self._validate(self._candidate())

    def test_future_ingest_rejects_unapproved_source(self):
        with self.assertRaisesRegex(ValueError, "not explicitly authorized"):
            self._validate(self._candidate(), allowed=False)

    def test_registry_source_must_have_explicit_approved_authorization(self):
        record = self._candidate()
        registry = self._registry(record)
        registry["LICENSED-QUOTE"]["authorization_status"] = "Pending"
        with self.assertRaisesRegex(ValueError, "explicit approved authorization"):
            self._validate(record, registry=registry)

    def test_snapshot_authorization_reference_must_match_registered_source(self):
        record = self._candidate()
        record["authorization_ref"] = "unrelated-document"
        with self.assertRaisesRegex(ValueError, "must match the registered source"):
            self._validate(record)

    def test_existing_snapshot_id_index_is_required(self):
        record = self._candidate()
        with self.assertRaisesRegex(ValueError, "complete existing snapshot-ID set"):
            price_store.validate_snapshot(
                record,
                registry=self._registry(record),
                authorized_price_source_ids={"LICENSED-QUOTE"},
                nfl_data_use_authorized=True,
                kickoff_at_utc="2026-11-10T18:15:00Z",
                existing_snapshot_ids=None,
            )

    def test_future_ingest_rejects_duplicate_snapshot_id(self):
        record = self._candidate()
        with self.assertRaisesRegex(ValueError, "may not be overwritten"):
            self._validate(record, existing={record["snapshot_id"]})

    def test_future_ingest_rejects_incomplete_two_sided_quote(self):
        record = self._candidate()
        record["away_price_american"] = None
        with self.assertRaisesRegex(ValueError, "complete two-outcome"):
            self._validate(record)

    def test_future_ingest_rejects_non_utc_timestamp(self):
        record = self._candidate()
        record["captured_at_utc"] = "2026-11-10T18:00:00-05:00"
        with self.assertRaisesRegex(ValueError, "UTC timezone"):
            self._validate(record)

    def test_opening_quote_must_follow_source_attested_open(self):
        record = self._candidate()
        record["market_open_at_utc"] = "2026-11-10T18:01:00Z"
        with self.assertRaisesRegex(ValueError, "predate"):
            self._validate(record)

    def test_opening_quote_basis_must_distinguish_true_open_from_first_seen(self):
        record = self._candidate()
        record["quote_sequence_basis"] = "assumed_open"
        with self.assertRaisesRegex(ValueError, "basis must distinguish"):
            self._validate(record)

    def test_first_observed_opening_is_accepted_only_with_blank_true_open_time(self):
        record = self._candidate()
        record["quote_sequence_basis"] = "first_observed_by_own_capture"
        record["market_open_at_utc"] = None
        self._validate(record)
        record["market_open_at_utc"] = "2026-11-10T17:00:00Z"
        with self.assertRaisesRegex(ValueError, "leave market_open_at_utc blank"):
            self._validate(record)

    def test_future_ingest_rejects_post_kickoff_quote(self):
        record = self._candidate()
        record["captured_at_utc"] = "2026-11-10T18:16:00Z"
        with self.assertRaisesRegex(ValueError, "before kickoff"):
            self._validate(record)

    def test_closing_quote_must_be_inside_fixed_15_minute_window(self):
        opening = self._candidate()
        opening["captured_at_utc"] = "2026-11-10T17:45:00Z"
        record = dict(opening)
        record.update({
            "snapshot_id": "GAME-SIDE-CLOSE-1",
            "phase": "closing",
            "captured_at_utc": "2026-11-10T17:59:59Z",
        })
        with self.assertRaisesRegex(ValueError, "outside the fixed 15-minute"):
            self._validate(record, opening=opening)

    def test_valid_closing_quote_must_pair_to_same_source_contract(self):
        opening = self._candidate()
        opening["captured_at_utc"] = "2026-11-10T17:45:00Z"
        closing = dict(opening)
        closing.update({
            "snapshot_id": "GAME-SIDE-CLOSE-1",
            "phase": "closing",
            "captured_at_utc": "2026-11-10T18:05:00Z",
        })
        self._validate(closing, opening=opening)

    def test_closing_quote_requires_opening_snapshot_already_in_store(self):
        opening = self._candidate()
        opening["captured_at_utc"] = "2026-11-10T17:45:00Z"
        closing = dict(opening)
        closing.update({
            "snapshot_id": "GAME-SIDE-CLOSE-1",
            "phase": "closing",
            "captured_at_utc": "2026-11-10T18:05:00Z",
        })
        with self.assertRaisesRegex(ValueError, "must already exist"):
            self._validate(closing, opening=opening, existing=set())

    def test_closing_quote_must_match_opening_game_identity(self):
        opening = self._candidate()
        opening["captured_at_utc"] = "2026-11-10T17:45:00Z"
        closing = dict(opening)
        closing.update({
            "snapshot_id": "GAME-SIDE-CLOSE-1",
            "phase": "closing",
            "captured_at_utc": "2026-11-10T18:05:00Z",
            "game_id": "OTHER-GAME",
        })
        with self.assertRaisesRegex(ValueError, "game_id does not match"):
            self._validate(closing, opening=opening)

    def test_closing_quote_must_match_opening_operator_source_and_contract(self):
        opening = self._candidate()
        closing = dict(opening)
        closing.update({
            "snapshot_id": "GAME-SIDE-CLOSE-1",
            "phase": "closing",
            "captured_at_utc": "2026-11-10T18:05:00Z",
            "operator": "OtherBook",
        })
        with self.assertRaisesRegex(ValueError, "same operator"):
            self._validate(closing, opening=opening)

    def test_american_price_conversion_and_moneyline_devig(self):
        self.assertAlmostEqual(price_store.american_implied_probability(-110), 110 / 210)
        self.assertAlmostEqual(price_store.american_implied_probability(+110), 100 / 210)
        self.assertAlmostEqual(price_store.moneyline_home_probability(-110, -110), 0.5)
        with self.assertRaisesRegex(ValueError, "nonzero integer"):
            price_store.american_implied_probability(0)

    def test_close_market_value_and_difference_are_separate_and_do_not_mutate_history(self):
        market = {"market_id": "GAME-SIDE", "game_id": "GAME", "market_type": "side", "model_fair_value": -2.5,
                  "market_value": None, "difference": None, "closing_value": None}
        opening = self._candidate()
        opening["captured_at_utc"] = "2026-11-10T17:45:00Z"
        snapshot = dict(opening)
        snapshot.update({
            "snapshot_id": "GAME-SIDE-CLOSE",
            "phase": "closing",
            "captured_at_utc": "2026-11-10T18:10:00Z",
            "market_number": -3.5,
        })
        derived = self._derive_market_value(market, snapshot, opening)
        self.assertEqual(derived["market_value"], -3.5)
        self.assertEqual(derived["difference"], 1.0)
        self.assertEqual(derived["closing_value"], -3.5)
        self.assertIsNone(market["market_value"])
        self.assertIsNone(market["difference"])

    def test_moneyline_market_value_is_devigged_probability_not_american_odds(self):
        market = {"market_id": "GAME-ML", "game_id": "GAME", "market_type": "moneyline", "model_fair_value": 0.6}
        opening = self._candidate()
        opening.update({
            "snapshot_id": "GAME-ML-OPEN",
            "market_id": "GAME-ML",
            "market_type": "moneyline",
            "market_number": None,
            "captured_at_utc": "2026-11-10T17:45:00Z",
        })
        snapshot = dict(opening)
        snapshot.update({
            "snapshot_id": "GAME-ML-CLOSE",
            "phase": "closing",
            "captured_at_utc": "2026-11-10T18:10:00Z",
        })
        derived = self._derive_market_value(market, snapshot, opening)
        self.assertEqual(derived["market_value"], 0.5)
        self.assertAlmostEqual(derived["difference"], 0.1)


class DemotionGateTests(unittest.TestCase):
    def setUp(self):
        self.policy = demotion.project_policy()
        self.good = {
            "rights_authorized": True,
            "price_source_authorized": True,
            "source_integrity_ok": True,
            "quote_fresh": True,
            "settlement_contract_match": True,
            "model_hash_matches": True,
            "all_required_gates_pass": True,
            "evaluation_window_frozen": True,
            "attempt_registry_complete": True,
            "risk_telemetry_complete": True,
            "settled_selections": self.policy["minimum_settled_selections"],
            "distinct_games": self.policy["minimum_distinct_games"],
            "distinct_dates": self.policy["minimum_distinct_dates"],
            "shadow_games": self.policy["minimum_shadow_games"],
            "shadow_calendar_days": self.policy["minimum_shadow_calendar_days"],
            "signal_skill_lower_95": 0.01,
            "familywise_adjusted_p": self.policy["familywise_alpha"],
            "net_return_lower_95": 0.01,
            "max_units_per_game_observed": self.policy["maximum_units_per_game"],
            "max_units_per_day_observed": self.policy["maximum_units_per_day"],
            "drawdown_units_observed": self.policy["maximum_drawdown_units"],
            "stake_roi": 0.0,
        }

    def test_paper_state_has_no_live_demotion_event(self):
        decision = demotion.evaluate_demotion("paper", self.good)
        self.assertEqual(decision["decision"], "not_applicable")
        self.assertFalse(decision["demoted"])

    def test_all_required_evidence_keeps_live_state(self):
        decision = demotion.evaluate_demotion("live", self.good)
        self.assertEqual(decision["decision"], "remain_live")
        self.assertFalse(decision["demoted"])
        self.assertTrue(decision["operational_gate_pass"])
        self.assertTrue(decision["signal_gate_pass"])
        self.assertTrue(decision["economics_gate_pass"])
        self.assertTrue(decision["risk_gate_pass"])

    def test_missing_evidence_fails_closed_to_paper(self):
        decision = demotion.evaluate_demotion("live", {})
        self.assertEqual(decision["decision"], "demote_to_paper")
        self.assertTrue(decision["demoted"])
        self.assertTrue(decision["reasons"])

    def test_bad_signal_is_not_rescued_by_a_lucky_staking_roi(self):
        evidence = dict(self.good, signal_skill_lower_95=-0.01, stake_roi=1000.0)
        decision = demotion.evaluate_demotion("live", evidence)
        self.assertTrue(decision["demoted"])
        self.assertFalse(decision["signal_gate_pass"])
        self.assertFalse(decision["stake_roi_used_for_signal"])

    def test_changing_stake_roi_does_not_change_signal_gate_or_decision(self):
        low = dict(self.good, signal_skill_lower_95=-0.01, stake_roi=-100.0)
        high = dict(self.good, signal_skill_lower_95=-0.01, stake_roi=1e9)
        a = demotion.evaluate_demotion("live", low)
        b = demotion.evaluate_demotion("live", high)
        self.assertEqual(a["signal_gate_pass"], b["signal_gate_pass"])
        self.assertEqual(a["decision"], b["decision"])
        self.assertEqual(a["reasons"], b["reasons"])

    def test_negative_economics_is_a_distinct_gate_not_a_signal_score(self):
        evidence = dict(self.good, net_return_lower_95=-0.02)
        decision = demotion.evaluate_demotion("live", evidence)
        self.assertTrue(decision["demoted"])
        self.assertTrue(decision["signal_gate_pass"])
        self.assertFalse(decision["economics_gate_pass"])

    def test_exposure_breach_demotes_even_with_positive_signal_and_return(self):
        evidence = dict(self.good, max_units_per_day_observed=self.policy["maximum_units_per_day"] + 1)
        decision = demotion.evaluate_demotion("live", evidence)
        self.assertTrue(decision["demoted"])
        self.assertFalse(decision["risk_gate_pass"])
        self.assertTrue(decision["signal_gate_pass"])

    def test_familywise_p_above_policy_alpha_demotes(self):
        evidence = dict(self.good, familywise_adjusted_p=self.policy["familywise_alpha"] + 0.001)
        decision = demotion.evaluate_demotion("live", evidence)
        self.assertTrue(decision["demoted"])
        self.assertFalse(decision["signal_gate_pass"])

    def test_insufficient_prospective_shadow_games_demotes(self):
        evidence = dict(self.good, shadow_games=self.policy["minimum_shadow_games"] - 1)
        decision = demotion.evaluate_demotion("live", evidence)
        self.assertTrue(decision["demoted"])
        self.assertFalse(decision["signal_gate_pass"])

    def test_unfrozen_window_and_incomplete_attempt_registry_fail_operational_gate(self):
        evidence = dict(self.good, evaluation_window_frozen=False, attempt_registry_complete=False)
        decision = demotion.evaluate_demotion("live", evidence)
        self.assertTrue(decision["demoted"])
        self.assertFalse(decision["operational_gate_pass"])

    def test_current_repository_state_has_no_actual_demotion_but_fails_counterfactual_live_gate(self):
        current = demotion.current_status(price_store.build_store())
        self.assertEqual(current["actual_project_state"]["mode"], "paper research only")
        self.assertFalse(current["actual_project_state"]["demotion_event_executed"])
        self.assertEqual(current["counterfactual_live_check"]["decision"], "demote_to_paper")


class SignalStakingSeparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analysis = json.loads((ROOT / "nfl-results/analysis.json").read_text(encoding="utf-8"))
        cls.store = price_store.build_store()

    def test_signal_and_staking_are_separate_and_current_stakes_unmeasured(self):
        result = controls_build.build_signal_staking(self.analysis, self.store)
        self.assertEqual(result["signal_policy"]["strategies_tested"], 30)
        self.assertEqual(result["signal_policy"]["qualified"], 0)
        self.assertEqual(result["signal_policy"]["provisional"], 1)
        self.assertTrue(result["staking_policy"]["ranking_separate"])
        self.assertFalse(result["staking_policy"]["roi_is_signal_input"])
        self.assertTrue(result["staking_rows"])
        for row in result["staking_rows"]:
            for field in ("roi", "clv", "net_return_lower_95", "stake_units", "cash_reward"):
                self.assertIsNone(row[field], f'{row["id"]}.{field}')
            self.assertEqual(row["authorized_price_snapshots"], 0)

    def test_signal_order_does_not_change_when_staking_roi_is_added(self):
        original = controls_build.build_signal_staking(self.analysis, self.store)
        changed = copy.deepcopy(self.analysis)
        for index, candidate in enumerate(changed["candidates"]):
            candidate["stake_roi"] = 1e9 if index % 2 else -1e9
        rerun = controls_build.build_signal_staking(changed, self.store)
        self.assertEqual([r["id"] for r in original["signal_rows"]], [r["id"] for r in rerun["signal_rows"]])
        self.assertEqual([r["rank"] for r in original["signal_rows"]], [r["rank"] for r in rerun["signal_rows"]])

    def test_signal_result_is_explicitly_not_a_market_edge(self):
        result = controls_build.build_signal_staking(self.analysis, self.store)
        self.assertIn("not a sportsbook", result["signal_policy"]["meaning"])

    def test_generated_market_pages_have_rows_and_registered_source_ids(self):
        signal_data = controls_build.build_signal_staking(self.analysis, self.store)
        demotion_data = demotion.current_status(self.store)
        pages = controls_build.build_pages(self.store, signal_data, demotion_data, controls_build.build_flags())
        market_page = pages[HERE.parent / "site" / "prices.html"]
        self.assertIn('data-source-ids="NFL-STANDINGS PYTH-NFL NFL-SCHED-W10 X87-NFL-W10-1414 X87-NFL-ODDS-1414 X87-NFL-TERMS-1414 REPO"', market_page)
        self.assertEqual(market_page.count('<tr data-row-id='), len(self.store["markets"]))
        snapshot_page = pages[HERE.parent / "site" / "snapshots.html"]
        self.assertEqual(snapshot_page.count('<tr data-row-id='), len(self.store["snapshots"]))
        self.assertNotIn('data-row-id="0"', snapshot_page)
        self.assertIn('aria-label="Blank: not verified, not collected, or not applicable"', snapshot_page)


if __name__ == "__main__":
    unittest.main()
