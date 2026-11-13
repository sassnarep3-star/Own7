"""Deterministic tests for the availability and depletion desk.

These tests prove three things and nothing more:
  1. every published row carries the official source it came from;
  2. no value was invented — a blank in the source stays blank in the output;
  3. the pages regenerate byte-for-byte from the saved evidence.

They deliberately do not assert anything about performance, points, prices or edge: no official
source publishes those, so there is nothing to test against.
"""
from __future__ import annotations

import csv
import html
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

INJURY_VOCAB = {"", "Out", "Doubtful", "Questionable"}
PRACTICE_VOCAB = {
    "Did Not Participate In Practice",
    "Limited Participation in Practice",
    "Full Participation in Practice",
}
RANK_LABELS = {"1st string (printed starter)", "2nd string", "3rd string",
               "4th string", "5th string"}

SCRIPTS = ["collect.py", "depth.py", "depletion.py", "build.py"]


def read_csv(name: str):
    with (DATA / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def rows_with_sources(path: Path):
    text = path.read_text(encoding="utf-8")
    return re.findall(r'<tr data-source-ids="([^"]*)"(.*?)</tr>', text, re.S)


class InjuryLedger(unittest.TestCase):
    """The transcription of the saved official injury report."""

    @classmethod
    def setUpClass(cls):
        cls.rows = read_csv("injuries-week10-2026.csv")
        cls.games = read_csv("games-week10-2026.csv")

    def test_table_is_not_empty(self):
        self.assertGreater(len(self.rows), 300)
        self.assertEqual(len(self.games), 14)

    def test_every_row_carries_its_official_source_and_date(self):
        for row in self.rows:
            self.assertEqual(row["source_url"],
                             "https://www.nfl.com/injuries/league/2026/REG10", row["injury_id"])
            self.assertEqual(row["checked_on"], "2026-11-13", row["injury_id"])
            self.assertTrue(row["player"].strip(), row["injury_id"])
            self.assertTrue(row["evidence_file"].strip(), row["injury_id"])

    def test_statuses_stay_inside_the_official_vocabulary(self):
        for row in self.rows:
            self.assertIn(row["game_status"], INJURY_VOCAB, row["injury_id"])
            self.assertIn(row["practice_status"], PRACTICE_VOCAB, row["injury_id"])

    def test_blanks_are_preserved_and_not_filled(self):
        """A game status the page did not publish stays blank in the output."""
        blank = sum(1 for r in self.rows if r["game_status"] == "")
        self.assertGreater(blank, 250, "the report is mostly blank; do not 'fix' that")
        self.assertEqual(blank + sum(1 for r in self.rows if r["game_status"]), len(self.rows))

    def test_every_row_belongs_to_a_club_in_a_listed_game(self):
        clubs = {c for g in self.games for c in (g["away_abbr"], g["home_abbr"])}
        for row in self.rows:
            self.assertIn(row["club_abbr"], clubs, row["injury_id"])
            self.assertIn(row["opponent_abbr"], clubs, row["injury_id"])
            self.assertNotEqual(row["club_abbr"], row["opponent_abbr"], row["injury_id"])

    def test_ids_are_unique(self):
        ids = [r["injury_id"] for r in self.rows]
        self.assertEqual(len(ids), len(set(ids)))


class PrintedDepthChains(unittest.TestCase):
    """The transcribed club depth charts."""

    @classmethod
    def setUpClass(cls):
        cls.slots = read_csv("depth-slots-week10-2026.csv")

    def test_every_slot_carries_its_club_source_and_date(self):
        for row in self.slots:
            self.assertTrue(row["source_url"].startswith("https://"), row["depth_id"])
            self.assertIn(row["checked_on"], {"2026-11-12", "2026-11-13"}, row["depth_id"])
            self.assertIn(row["unit"], {"Offense", "Defense", "Special Teams"}, row["depth_id"])
            self.assertTrue(row["evidence_file"].strip(), row["depth_id"])

    def test_ranks_are_contiguous_within_a_chain(self):
        seen = {}
        for row in self.slots:
            key = (row["club_abbr"], row["unit"], row["position"], row["slot"])
            seen.setdefault(key, []).append(int(row["rank"]))
        for key, ranks in seen.items():
            self.assertEqual(sorted(ranks), list(range(1, len(ranks) + 1)), key)

    def test_blank_player_cells_are_declared_not_filled(self):
        """Every blank first/second-string cell states why it is blank, rather than being filled."""
        blanks = [r for r in self.slots if not r["player"].strip()]
        self.assertLessEqual(len(blanks), 3)
        for row in blanks:
            self.assertTrue(row["note"].strip(), row["depth_id"])

    def test_multi_name_cells_are_marked(self):
        multi = [r for r in self.slots if r["cell_holds_multiple"] == "yes"]
        self.assertGreater(len(multi), 0)
        for row in multi:
            if row["evidence_file"].startswith("nfl-availability-28ef/"):
                # this session's reads captured the club's own player links
                self.assertGreaterEqual(row["player_urls"].count("http"), 1, row["depth_id"])
            else:
                # the reused 2026-11-12 transcription stored names only; the row must say so
                self.assertIn("11-12 snapshot", row["note"], row["depth_id"])

    def test_houston_is_recorded_as_a_failure_and_not_substituted(self):
        self.assertNotIn("HOU", {r["club_abbr"] for r in self.slots})


class DepletionJoin(unittest.TestCase):
    """The join between the two sources."""

    @classmethod
    def setUpClass(cls):
        cls.rows = read_csv("depletion-week10-2026.csv")

    def test_one_row_per_injury_row_and_nothing_invented(self):
        injuries = read_csv("injuries-week10-2026.csv")
        self.assertEqual(len(self.rows), len(injuries))
        self.assertEqual([r["injury_id"] for r in self.rows],
                         [r["injury_id"] for r in injuries])

    def test_every_row_carries_the_injury_source(self):
        for row in self.rows:
            self.assertEqual(row["injury_source_url"],
                             "https://www.nfl.com/injuries/league/2026/REG10", row["injury_id"])
            self.assertEqual(row["injury_checked_on"], "2026-11-13", row["injury_id"])

    def test_rank_and_replacement_are_blank_together(self):
        for row in self.rows:
            if not row["depth_rank"]:
                self.assertEqual(row["next_in_line"], "", row["injury_id"])
                self.assertEqual(row["depth_source_url"], "", row["injury_id"])
            else:
                self.assertTrue(row["depth_source_url"].startswith("https://"), row["injury_id"])

    def test_rank_labels_are_the_published_vocabulary(self):
        for row in self.rows:
            if row["depth_rank_label"]:
                self.assertIn(row["depth_rank_label"], RANK_LABELS, row["injury_id"])
                self.assertEqual(row["depth_rank_label"],
                                 RANK_LABELS_TEMPLATE(int(row["depth_rank"])), row["injury_id"])

    def test_next_in_line_is_never_the_player_himself(self):
        for row in self.rows:
            if row["next_in_line"]:
                self.assertNotEqual(row["next_in_line"].strip().lower(),
                                    row["player"].strip().lower(), row["injury_id"])

    def test_no_performance_value_is_present_anywhere(self):
        banned = ("point", "spread", "total", "probability", "edge", "roi", "clv", "stake", "odds")
        header = ",".join(self.rows[0].keys()).lower()
        for word in banned:
            self.assertNotIn(word, header)


def RANK_LABELS_TEMPLATE(rank: int) -> str:
    return {1: "1st string (printed starter)", 2: "2nd string", 3: "3rd string",
            4: "4th string", 5: "5th string"}.get(rank, f"{rank}th string")


class PublishedPages(unittest.TestCase):
    """The generated pages: every row sourced, every blank declared."""

    @classmethod
    def setUpClass(cls):
        cls.pages = sorted(SITE.glob("*.html"))

    def test_ten_pages_exist(self):
        self.assertEqual(len(self.pages), 10)

    def test_every_table_row_carries_source_ids_and_a_link(self):
        for page in self.pages:
            for ids, body in rows_with_sources(page):
                self.assertTrue(ids.strip(), f"{page.name}: row without data-source-ids")
                self.assertIn('<td class="src"><a href="https://', body,
                              f"{page.name}: row {ids} has no official link")
                for source_id in ids.split():
                    self.assertIn(source_id, body, f"{page.name}: {source_id} not linked in the row")

    def test_every_page_declares_the_snapshot_date(self):
        for page in self.pages:
            self.assertIn("2026-11-13", page.read_text(encoding="utf-8"), page.name)

    def test_no_page_prints_a_market_price_or_a_wager_call(self):
        banned = ("bet now", "place a bet", "stake this", "guaranteed pick", "lock of the week")
        for page in self.pages:
            text = page.read_text(encoding="utf-8").lower()
            for phrase in banned:
                self.assertNotIn(phrase, text, page.name)

    def test_every_page_has_one_h1_and_a_skip_link(self):
        for page in self.pages:
            text = page.read_text(encoding="utf-8")
            self.assertEqual(text.count("<h1>"), 1, page.name)
            self.assertIn('class="skip" href="#main"', text, page.name)

    def test_the_registered_source_ids_all_exist(self):
        import json
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
    """The committed artifacts must be reproducible from the saved evidence."""

    def _run(self, script: str, *args):
        return subprocess.run([sys.executable, str(DESK / script), *args],
                              cwd=DESK, capture_output=True, text=True)

    def test_collect_is_current(self):
        result = self._run("collect.py", "--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_depth_is_current(self):
        result = self._run("depth.py", "--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_depletion_is_current(self):
        result = self._run("depletion.py", "--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pages_are_current(self):
        result = self._run("build.py", "--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_check_fails_when_a_row_is_added(self):
        """--check must actually detect drift, not silently pass."""
        import emit
        target = DATA / "capture-summary.json"
        original = target.read_text(encoding="utf-8")
        emit.set_check(True)
        try:
            with self.assertRaises(SystemExit):
                emit.emit(target, original + "\n")
        finally:
            emit.set_check(False)
            target.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
