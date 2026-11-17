"""Session arena/34a52a38-own7 (2026-11-17): readiness rows, luck panel, Lions read-back, leaderboard rule.

These tests check integrity and the stated rules. They do not establish that any source page is true.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import nfl_readiness as nr  # noqa: E402


class ReadinessTests(unittest.TestCase):
    def test_every_row_has_registered_sources_and_numbers(self):
        sources = {s["id"] for s in json.loads((ROOT / "research/sources.json").read_text(encoding="utf-8"))}
        rows = nr.readiness_rows()
        self.assertEqual(len({r["id"] for r in rows}), len(rows), "row ids must be unique")
        for r in rows:
            with self.subTest(row=r["id"]):
                self.assertTrue(r["source_ids"], "every row needs a source")
                for sid in r["source_ids"]:
                    self.assertIn(sid, sources)
                self.assertIn(r["status"], {"Done", "Partial", "Blocked", "Not started"})
                self.assertTrue(r["gate"] and r["now"] and r["clears"])

    def test_evidence_links_point_to_existing_pages(self):
        for r in nr.readiness_rows():
            href = r["href"]
            if href.startswith("#") or href.startswith("http"):
                continue
            with self.subTest(row=r["id"], href=href):
                self.assertTrue((ROOT / href.split("#")[0]).exists())

    def test_luck_arithmetic_is_consistent(self):
        lp = nr.luck_panel()
        self.assertEqual((lp["wins"], lp["losses"], lp["bets"]), (77, 43, 120))
        self.assertAlmostEqual(lp["fw_stated_recomputed"], lp["fw_stated"], places=4)
        self.assertAlmostEqual(lp["fw_graded"], 1 - (1 - lp["p_single"]) ** 30, places=12)
        self.assertLess(lp["fw_graded"], 0.05)

    def test_lions_official_out_confirmed_and_delta_detected(self):
        delta = {d["player"]: d for d in nr.lions_delta()}
        self.assertEqual(len(delta), 9)
        for name in ("Kerby Joseph", "Cade Mays", "D.J. Reed"):
            self.assertEqual(delta[name]["official"][2], "Out")
        # The desk capture shows Joseph as Full Participation; the official read shows Did Not Participate.
        self.assertIn("practice", delta["Kerby Joseph"]["availability_diff"])

    def test_price_store_reports_no_market_line(self):
        rq01 = next(r for r in nr.readiness_rows() if r["id"] == "RQ01")
        self.assertIn("0 with a market line", rq01["now"])


class LeaderboardRuleTests(unittest.TestCase):
    """Brief rule: backtest numbers must never appear on the leaderboard."""

    BACKTEST_TOKENS = ("64.2%", "77–43", "0.0012", "55.8%", "72.5%", "0.0220", "58.3%", "70.0%")

    def test_results_leaderboard_page_shows_no_backtest_numbers(self):
        page = (ROOT / "nfl-results-leaderboard.html").read_text(encoding="utf-8")
        for token in self.BACKTEST_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(token, page)
        self.assertIn("Backtests are not leaderboard entries", page)

    def test_skill_page_still_carries_the_labelled_analysis(self):
        page = (ROOT / "nfl-results-skill.html").read_text(encoding="utf-8")
        self.assertIn("64.2%", page)


class LandingPageTests(unittest.TestCase):
    def test_landing_page_has_luck_panel_delta_and_readiness_table(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        for anchor in ('id="luck-panel"', 'id="lions-delta"', 'id="readiness-table"'):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, page)


if __name__ == "__main__":
    unittest.main()
