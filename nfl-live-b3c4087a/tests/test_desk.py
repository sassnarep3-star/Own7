"""Tests for the live Week 11 injury-check desk (session arena/b3c4087a-own7)."""
import csv
import importlib.util
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
spec = importlib.util.spec_from_file_location("desk", HERE / "build.py")
desk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desk)


class DeskTests(unittest.TestCase):
    def setUp(self):
        self.data = desk.compute()
        self.pages = desk.render(self.data)

    def test_club_counts_reconcile(self):
        self.assertEqual(self.data["total_live_rows"], 253)
        self.assertEqual(len(self.data["clubs"]), 26)
        self.assertEqual(self.data["clubs_no_injuries_live"], 2)
        self.assertEqual(self.data["clubs_no_injuries_repo"], 24)

    def test_thursday_rows_match_club_count(self):
        ind = [r for r in self.data["thursday"] if r["club_code"] == "IND"]
        hou = [r for r in self.data["thursday"] if r["club_code"] == "HOU"]
        self.assertEqual((len(ind), len(hou)), (11, 15))

    def test_repo_baseline_is_stale_for_known_fields(self):
        by = {(r["club_code"], r["player"]): r for r in self.data["thursday"]}
        mallory = by[("IND", "Will Mallory")]
        self.assertEqual(mallory["repo"]["game_status_printed"], "")
        self.assertIn("Game status", mallory["diffs"])
        self.assertEqual(mallory["game_status_printed"], "Out")
        self.assertEqual(mallory["injuries_printed"], "Hamstring")

    def test_blank_stays_blank(self):
        carlies = next(r for r in self.data["thursday"] if r["player"] == "Jaylon Carlies")
        self.assertEqual(carlies["game_status_printed"], "")
        self.assertEqual(carlies["injuries_printed"], "")
        self.assertEqual(self.data["game_status_live"], 16)

    def test_every_table_row_links_registered_official_source(self):
        for name, text in self.pages.items():
            rows = re.findall(r'<tr data-source-ids="([^"]+)">(.*?)</tr>', text, flags=re.S)
            for sid, body in rows:
                self.assertIn(desk.INJURY_URL if sid == desk.SRC_INJ else desk.TERMS_URL, body, name)

    def test_no_empty_value_is_filled(self):
        for row in self.data["thursday"]:
            for k in ("injuries_printed", "practice_status_printed", "game_status_printed"):
                self.assertEqual(row[k], row[k].strip())

    def test_check_reproduces(self):
        for name, text in self.pages.items():
            self.assertTrue(text.startswith("<!doctype html>"))
            self.assertEqual(len(re.findall(r"<h1[ >]", text)), 1, name)

    def test_build_site_registers_sources(self):
        import json
        reg = {r["id"]: r["url"] for r in json.loads((ROOT / "research" / "sources.json").read_text())}
        self.assertEqual(reg[desk.SRC_INJ], desk.INJURY_URL)
        self.assertEqual(reg[desk.SRC_TERMS], desk.TERMS_URL)
        self.assertEqual(reg[desk.SRC_REPO], desk.REPO_URL)


if __name__ == "__main__":
    unittest.main()
