"""Final NFL integration-audit inventory and source-link contracts."""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("own7_build_site", ROOT / "scripts" / "build_site.py")
build_site = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = build_site
spec.loader.exec_module(build_site)
nfl_final_audit = build_site.nfl_final_audit


class FinalNFLAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use the exact site render helpers so this tests the generated table contract,
        # while avoiding a full multi-desk rebuild for every unit-test run.
        page_helpers = build_site.nfl_pages
        for helper in ("notice", "metrics", "section", "table", "rich", "badge", "link", "Markup"):
            setattr(page_helpers, helper, getattr(build_site, helper))
        page_helpers._Markup = build_site.Markup
        cls.body = nfl_final_audit.render()

    def test_counts_are_read_from_distinct_registers(self):
        counts = nfl_final_audit.inventory()
        self.assertEqual(counts["origination_scope"], 16)
        self.assertEqual(counts["landing"], 70)
        self.assertEqual(counts["readiness"], 81)
        self.assertEqual(counts["readiness_1467"], 79)
        self.assertEqual(counts["readiness_e7ef"], 80)
        self.assertEqual(counts["assurance_subset"], 20)
        self.assertEqual(counts["saved_result_rows"], 149)
        self.assertEqual(counts["published_nfl_leaderboards"], 10)
        self.assertEqual(counts["published_backtest_leaderboard_conflicts"], 4)
        self.assertEqual(counts["unpublished_backtest_leaderboard_proposals"], 1)

    def test_every_current_nfl_leaderboard_route_is_in_the_inventory(self):
        published_nfl = [
            row for row in nfl_final_audit.LEADERBOARDS
            if row["published"] and row["id"] not in {"LB-NBA-EXCLUDED", "LB-VERIFIED-REDIRECT"}
        ]
        self.assertEqual(len(published_nfl), 10)
        self.assertEqual(sum(row["published"] and row["conflict"] for row in published_nfl), 4)
        self.assertTrue(all((ROOT / row["path"]).is_file() for row in published_nfl))
        self.assertIn("nfl-readiness/site/leaderboard.html", {
            row["path"] for row in nfl_final_audit.LEADERBOARDS if not row["published"]
        })
        self.assertFalse((ROOT / "nfl-readiness/site/leaderboard.html").exists())

        discovered = {
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*leaderboard*.html")
            if path.is_file()
        }
        self.assertEqual(discovered, {row["path"] for row in nfl_final_audit.LEADERBOARDS if row["published"]})

    def test_all_audit_table_rows_have_registered_source_ids(self):
        registry = {row["id"] for row in json.loads((ROOT / "research/sources.json").read_text())[0:]}
        for row in nfl_final_audit.LEADERBOARDS:
            self.assertTrue(row["source_ids"])
            self.assertTrue(set(row["source_ids"]).issubset(registry), row["id"])
        for row_id in ("LB-COMPETITION", "LB-LIFECYCLE", "LB-MARKET", "LB-PRICING", "LB-PR57"):
            self.assertIn(f'data-row-id="{row_id}"', self.body)
        self.assertIn("Unmerged PR file", self.body)
        self.assertIn("Source links are attached to every row", self.body)

    def test_current_published_conflicts_are_not_mislabeled_as_qualification(self):
        current_conflicts = {
            row["id"] for row in nfl_final_audit.LEADERBOARDS
            if row["published"] and row["conflict"]
        }
        self.assertEqual(current_conflicts, {
            "LB-COMPETITION", "LB-LIFECYCLE", "LB-MARKET", "LB-PRICING"
        })
        self.assertIn("Published backtest leaderboard conflicts", self.body)
        self.assertIn("zero qualified does not make it prospective", self.body)  # only describes the unmerged PR proposal

    def test_page_links_the_unreconciled_ledgers_and_live_spot_checks(self):
        for fragment in (
            "requirement-ledger-inventory",
            "final-audit-live-checks",
            "nfl-leaderboard-publication-audit",
            "decision-questions",
            "audit-suggestions",
        ):
            self.assertIn(f'id="{fragment}"', self.body)
        for source_id in (
            "C756-NFL-TERMS-1118", "C756-NFL-INJ-W10-1118",
            "C756-NFL-SCHED-W10-1118", "C756-PR57",
        ):
            self.assertIn(source_id, {row["id"] for row in json.loads((ROOT / "research/sources.json").read_text())})


if __name__ == "__main__":
    unittest.main()
