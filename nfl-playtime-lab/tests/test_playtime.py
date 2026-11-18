"""Tests for the official playing-time desk.

The point of these tests is the grammar, not the numbers: the publisher prints a
six-cell grid whose empty cells are semantic, and every published percentage is
an arithmetic consequence of the unit total printed beside it. If either of
those properties stops holding, the desk is publishing something it cannot
verify, and these tests fail.
"""

from __future__ import annotations

import csv
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
DESK = HERE.parent
sys.path.insert(0, str(DESK))

import build  # noqa: E402  (path is set above)

DATA = DESK / "data"
UNITS = ("OFF", "DEF", "ST")


def read(name):
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class DecoderTests(unittest.TestCase):
    """The six-cell grid must decode to exactly one unit assignment."""

    def test_full_offense_row(self):
        # B.Coleman | T/G | 69 100% | (empty) | 4 | 15%
        found = build.decode_cells(["69", "100", "", "4", "15"])
        self.assertEqual(found, [{"OFF": (69, 100), "DEF": None, "ST": (4, 15)}])

    def test_offense_only_row(self):
        # J.Daniels | QB | 69 100% | (empty) | (empty) | (empty)
        found = build.decode_cells(["69", "100", "", "", ""])
        self.assertEqual(found, [{"OFF": (69, 100), "DEF": None, "ST": None}])

    def test_defense_only_row(self):
        found = build.decode_cells(["", "65", "100", "", ""])
        self.assertEqual(found, [{"OFF": None, "DEF": (65, 100), "ST": None}])

    def test_special_teams_only_row(self):
        found = build.decode_cells(["", "", "", "22", "85"])
        self.assertEqual(found, [{"OFF": None, "DEF": None, "ST": (22, 85)}])

    def test_all_three_units(self):
        found = build.decode_cells(["10", "15", "20", "30", "5", "19"])
        self.assertEqual(found, [{"OFF": (10, 15), "DEF": (20, 30), "ST": (5, 19)}])

    def test_share_without_snaps(self):
        # The capture writes this shape as "- <pct>": the share is published
        # evidence, the snap count is not, so it stays None rather than being
        # back-solved from the unit total.
        found = build.decode_cells(["", "", "-", "70"])
        self.assertEqual(found, [{"OFF": None, "DEF": None, "ST": (None, 70)}])

    def test_empty_grid_is_not_a_guess(self):
        found = build.decode_cells(["", "", ""])
        self.assertEqual(found, [{"OFF": None, "DEF": None, "ST": None}])


class DenominatorTests(unittest.TestCase):
    """A declared total is kept unless the printed shares contradict it."""

    def test_confirmed_total(self):
        pairs = [(69, 100), (59, 86), (3, 4)]
        value, verdict = build.resolve_denominator(69, pairs)
        self.assertEqual(value, 69)
        self.assertEqual(verdict, "declared-total-confirmed")

    def test_one_bad_cell_does_not_move_the_total(self):
        # A single mangled capture must not drag the denominator with it.
        pairs = [(69, 100), (59, 86), (44, 64), (999, 12)]
        value, _ = build.resolve_denominator(69, pairs)
        self.assertEqual(value, 69)

    def test_missing_total_is_recovered(self):
        pairs = [(69, 100), (69, 100), (59, 86)]
        value, verdict = build.resolve_denominator(None, pairs)
        self.assertEqual(value, 69)
        self.assertEqual(verdict, "declared-total-missing")


class PublishedEvidenceTests(unittest.TestCase):
    """Properties the published tables must have, checked on the real outputs."""

    @classmethod
    def setUpClass(cls):
        cls.playtime = read("playtime.csv")
        cls.totals = read("team-totals.csv")
        cls.players = read("players.csv")
        cls.depth = read("depth.csv")
        cls.flags = json.loads((DATA / "flags.json").read_text(encoding="utf-8"))
        cls.summary = json.loads(
            (DATA / "capture-summary.json").read_text(encoding="utf-8"))

    def test_captures_were_found(self):
        self.assertGreaterEqual(self.summary["captures"], 11)

    def test_every_row_names_a_registered_source(self):
        registry = json.loads(
            (DESK.parent / "research" / "sources.json").read_text(encoding="utf-8"))
        by_id = {entry["id"]: entry["url"] for entry in registry}
        self.assertIn("PT-NFL-GAMEBOOK-PDF", by_id)
        official = {g["source"] for g in self.summary["games"]}
        self.assertTrue(official)
        for row in self.playtime:
            self.assertIn(row["source"], official)

    def test_no_percentage_outside_zero_to_one_hundred(self):
        for row in self.playtime:
            if row["pct"]:
                self.assertGreaterEqual(int(row["pct"]), 0)
                self.assertLessEqual(int(row["pct"]), 100)

    def test_no_published_snap_count_exceeds_its_unit_total(self):
        for row in self.playtime:
            if row["snaps"] and row["denominator"]:
                self.assertLessEqual(int(row["snaps"]), int(row["denominator"]),
                                     f"{row['player']} {row['unit']}")

    def test_every_verified_percentage_re_derives(self):
        for row in self.playtime:
            if row["pct_status"] == "verified":
                want = build.pct_of(int(row["snaps"]), int(row["denominator"]))
                self.assertLessEqual(abs(want - int(row["pct"])),
                                     build.PCT_TOLERANCE)

    def test_unit_totals_are_positive(self):
        for row in self.totals:
            self.assertGreater(int(row["denominator"]), 0)

    def test_every_captured_club_states_all_three_units(self):
        seen = {}
        for row in self.totals:
            seen.setdefault((row["game_id"], row["club"]), set()).add(row["unit"])
        for key, units in seen.items():
            self.assertEqual(units, set(UNITS), key)

    def test_players_never_hold_negative_snaps(self):
        for row in self.players:
            for field in ("OFF", "DEF", "ST", "total_snaps"):
                self.assertGreaterEqual(int(row[field]), 0)

    def test_depth_ranks_are_contiguous_within_a_group(self):
        groups = {}
        for row in self.depth:
            groups.setdefault((row["game_id"], row["club"], row["group"]), []).append(
                int(row["rank"]))
        for key, ranks in groups.items():
            self.assertEqual(sorted(ranks), list(range(1, len(ranks) + 1)), key)

    def test_depth_is_ordered_by_snaps(self):
        groups = {}
        for row in self.depth:
            groups.setdefault((row["game_id"], row["club"], row["group"]), []).append(
                (int(row["rank"]), int(row["snaps"])))
        for key, pairs in groups.items():
            ordered = [snaps for _, snaps in sorted(pairs)]
            self.assertEqual(ordered, sorted(ordered, reverse=True), key)

    def test_nothing_is_published_for_a_withheld_cell(self):
        withheld = {(f.get("game_id"), f.get("club"), f.get("player"), f.get("unit"))
                    for f in self.flags
                    if f["reason"] in {"pct-mismatch", "snaps-exceed-total",
                                       "published-pct-over-100"}}
        published = {(r["game_id"], r["club"], r["player"], r["unit"])
                     for r in self.playtime}
        self.assertFalse(withheld & published)

    def test_every_flag_has_a_reason_and_a_detail(self):
        for flag in self.flags:
            self.assertTrue(flag.get("reason"))
            self.assertTrue(flag.get("detail"))

    def test_summary_counts_match_the_tables(self):
        self.assertEqual(self.summary["playtime_rows"], len(self.playtime))
        self.assertEqual(self.summary["players"], len(self.players))
        self.assertEqual(self.summary["depth_rows"], len(self.depth))
        self.assertEqual(self.summary["flags"], len(self.flags))


if __name__ == "__main__":
    unittest.main()
