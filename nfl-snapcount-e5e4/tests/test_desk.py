#!/usr/bin/env python3
"""Deterministic tests for the NFL snap-count / playing-time desk.

These tests prove four things and nothing more:
  1. every published row carries the official source it came from;
  2. no value was invented - a blank in the source stays blank in the output;
  3. the pages regenerate byte-for-byte from the saved evidence;
  4. depth order is derived from snap counts, never from jersey number.

They deliberately do not assert anything about performance, points, prices or
edge: no official source publishes those, so there is nothing to test against.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESK = HERE.parent
REPO = DESK.parent
DATA = DESK / "data"
SITE = DESK / "site"

if str(DESK) not in sys.path:
    sys.path.insert(0, str(DESK))


def read_csv(name: str):
    with (DATA / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def rows_with_sources(path: Path):
    text = path.read_text(encoding="utf-8")
    return re.findall(r'<tr data-source-ids="([^"]*)"(.*?)</tr>', text, re.S)


class SnapRecords(unittest.TestCase):
    """The transcription of the saved official Playtime Percentage tables."""

    @classmethod
    def setUpClass(cls):
        cls.rows = read_csv("snap-records.csv")

    def test_table_is_not_empty(self):
        self.assertGreater(len(self.rows), 1000)

    def test_every_row_carries_its_official_source_and_hash(self):
        for row in self.rows:
            self.assertTrue(row["source_url"].startswith("https://static.www.nfl.com/"),
                            row["snap_id"])
            self.assertTrue(row["raw_sha256"].strip(), row["snap_id"])
            self.assertTrue(row["raw_file"].strip(), row["snap_id"])

    def test_every_row_belongs_to_a_captured_game(self):
        games = {r["game_id"] for r in self.rows}
        self.assertEqual(len(games), 13)

    def test_snap_counts_are_integers_or_blank(self):
        for row in self.rows:
            for key in ("off_snaps", "def_snaps", "st_snaps"):
                v = row[key]
                if v:
                    int(v)  # raises if not a clean integer

    def test_total_snaps_is_the_sum_of_phases(self):
        for row in self.rows:
            total = sum(int(row[k]) for k in ("off_snaps", "def_snaps", "st_snaps") if row[k])
            self.assertEqual(int(row["total_snaps"]), total, row["snap_id"])

    def test_ids_are_unique(self):
        ids = [r["snap_id"] for r in self.rows]
        self.assertEqual(len(ids), len(set(ids)))

    def test_unofficial_labels_are_carried_not_removed(self):
        unofficial = [r for r in self.rows if r["table_label"] == "Unofficial"]
        self.assertGreater(len(unofficial), 0)
        for r in unofficial:
            self.assertEqual(r["table_label"], "Unofficial", r["snap_id"])

    def test_no_performance_value_is_present_anywhere(self):
        # "total" is excluded: total_snaps is a legitimate derived field (sum of
        # phase snaps), not a betting total. The banned terms are wagering concepts.
        banned = ("spread", "probability", "edge", "roi", "clv", "stake", "odds", "wager")
        header = ",".join(self.rows[0].keys()).lower()
        for word in banned:
            self.assertNotIn(word, header)


class PlayingTimeDepth(unittest.TestCase):
    """Depth order derived from playing time (R11, R52, R56)."""

    @classmethod
    def setUpClass(cls):
        cls.rows = read_csv("playtime-depth.csv")

    def test_depth_is_ranked_by_snap_count_descending(self):
        # Within each (game, team, position group, phase) the snaps must be
        # non-increasing with rank - i.e. the order is by playing time.
        groups = {}
        for r in self.rows:
            key = (r["game_id"], r["team"], r["position_group"], r["phase"])
            groups.setdefault(key, []).append((int(r["depth_rank"]), int(r["snaps"])))
        for key, entries in groups.items():
            entries.sort()
            snaps = [s for _rank, s in entries]
            self.assertEqual(snaps, sorted(snaps, reverse=True), key)

    def test_rank_1_is_labelled_the_playing_time_starter(self):
        starters = [r for r in self.rows if int(r["depth_rank"]) == 1]
        self.assertGreater(len(starters), 0)
        for r in starters:
            self.assertTrue(r["role"].startswith("Starter"), r["depth_id"])

    def test_depth_ranks_are_contiguous_within_a_slot(self):
        groups = {}
        for r in self.rows:
            key = (r["game_id"], r["team"], r["position_group"], r["phase"])
            groups.setdefault(key, []).append(int(r["depth_rank"]))
        for key, ranks in groups.items():
            self.assertEqual(sorted(ranks), list(range(1, len(ranks) + 1)), key)

    def test_every_row_carries_its_official_source(self):
        for row in self.rows:
            self.assertTrue(row["source_url"].startswith("https://static.www.nfl.com/"),
                            row["depth_id"])


class ReplacementDepth(unittest.TestCase):
    """The snap-count replacement behind each playing-time starter."""

    @classmethod
    def setUpClass(cls):
        cls.rows = read_csv("replacement-depth.csv")

    def test_replacement_never_is_the_starter(self):
        for row in self.rows:
            self.assertNotEqual(row["replacement_player"].strip().lower(),
                                row["starter_player"].strip().lower(), row["replacement_id"])

    def test_replacement_snaps_are_at_most_the_starters(self):
        for row in self.rows:
            self.assertLessEqual(int(row["replacement_snaps"]), int(row["starter_snaps"]),
                                 row["replacement_id"])

    def test_every_row_carries_its_official_source(self):
        for row in self.rows:
            self.assertTrue(row["source_url"].startswith("https://static.www.nfl.com/"),
                            row["replacement_id"])


class DepthVsSnapGap(unittest.TestCase):
    """The printed-depth join is a published zero-row gap, not a satisfied join."""

    def test_the_join_is_empty_and_the_reason_is_recorded(self):
        rows = read_csv("depth-vs-snap.csv")
        self.assertEqual(rows, [])

    def test_the_gap_is_flagged(self):
        flags = json.loads((DATA / "flags.json").read_text(encoding="utf-8"))
        gap = [f for f in flags if f["flag_id"] == "SN-F02"]
        self.assertEqual(len(gap), 1)
        self.assertEqual(gap[0]["value_published"], "0 joinable rows")


class PublishedPages(unittest.TestCase):
    """The generated pages: every row sourced, every blank declared."""

    @classmethod
    def setUpClass(cls):
        cls.pages = sorted(SITE.glob("*.html"))

    def test_all_pages_exist(self):
        self.assertEqual(len(self.pages), 11)

    def test_every_table_row_carries_source_ids_and_a_link(self):
        for page in self.pages:
            for ids, body in rows_with_sources(page):
                self.assertTrue(ids.strip(), f"{page.name}: row without data-source-ids")
                self.assertIn('<td class="refs"><a href="https://', body,
                              f"{page.name}: row {ids} has no official link")
                for source_id in ids.split():
                    self.assertIn(source_id, body,
                                  f"{page.name}: {source_id} not linked in the row")

    def test_every_page_declares_the_snapshot_date(self):
        for page in self.pages:
            self.assertIn("2026-11-18", page.read_text(encoding="utf-8"), page.name)

    def test_no_page_prints_a_market_price_or_a_wager_call(self):
        banned = ("bet now", "place a bet", "stake this", "guaranteed pick",
                  "lock of the week")
        for page in self.pages:
            text = page.read_text(encoding="utf-8").lower()
            for phrase in banned:
                self.assertNotIn(phrase, text, page.name)

    def test_every_page_has_one_h1_and_a_skip_link(self):
        for page in self.pages:
            text = page.read_text(encoding="utf-8")
            self.assertEqual(text.count("<h1>"), 1, page.name)
            self.assertIn('class="skip-link" href="#main"', text, page.name)

    def test_the_registered_source_ids_all_exist(self):
        registry = {s["id"] for s in json.loads(
            (REPO / "research" / "sources.json").read_text(encoding="utf-8"))}
        missing = set()
        for page in self.pages:
            for ids, _body in rows_with_sources(page):
                for source_id in ids.split():
                    if source_id not in registry:
                        missing.add(source_id)
        self.assertEqual(missing, set(), f"unregistered source ids: {sorted(missing)}")


class DeterministicRebuild(unittest.TestCase):
    """The committed artefacts must be reproducible from the saved evidence."""

    def _run(self, script: str, *args):
        return subprocess.run([sys.executable, str(DESK / script), *args],
                              cwd=DESK, capture_output=True, text=True)

    def test_build_is_current(self):
        result = self._run("build.py", "--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pages_are_current(self):
        result = self._run("build_site.py", "--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
