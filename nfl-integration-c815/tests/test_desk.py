"""Tests for the integration-audit desk (session arena/c815bdd2-own7).

These tests exist to make the desk's guarantee *checkable* rather than asserted:

* the engine must refuse to publish a standings row that fails PCT, NET or HOME+ROAD;
* the completion proof must refuse a delta that the settled headline does not imply;
* the rule extractor must fail if the official wording is altered;
* every generated page must keep its source-link and blank-cell contracts;
* the build must reproduce byte for byte.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESK = ROOT / "nfl-integration-c815"
sys.path.insert(0, str(DESK))

import build as B     # noqa: E402
import engine as E    # noqa: E402
import requirements as R  # noqa: E402
import rules as RU    # noqa: E402


class TestStandingsArithmetic(unittest.TestCase):
    def test_capture_parses_32_rows_and_every_identity_holds(self):
        rows = E.parse_standings_capture()
        self.assertEqual(len(rows), 32)
        self.assertEqual(len({r["code"] for r in rows}), 32)
        for row in rows:
            games = row["w"] + row["l"] + row["t"]
            self.assertAlmostEqual((row["w"] + row["t"] / 2) / games, row["pct"], places=3)
            self.assertEqual(row["net"], row["pf"] - row["pa"])

    def test_league_arithmetic_closes(self):
        league = E.league_arithmetic(E.parse_standings_capture())
        self.assertEqual(league["sum_w"], league["sum_l"])
        self.assertEqual(league["sum_pf"], league["sum_pa"])
        self.assertEqual(league["club_games"] % 2, 0)
        self.assertEqual(league["games_played"], league["club_games"] // 2)

    def test_a_pct_that_does_not_match_is_refused(self):
        text = (DESK / "evidence" / "standings-2026-11-18.retrieved.md").read_text()
        broken = text.replace("| Buffalo Bills | 8 | 1 | 0 | 0.889 |", "| Buffalo Bills | 8 | 1 | 0 | 0.500 |")
        self.assertNotEqual(text, broken)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture.md"
            path.write_text(broken)
            with self.assertRaises(SystemExit):
                E.parse_standings_capture(path)

    def test_a_home_road_mismatch_is_refused(self):
        text = (DESK / "evidence" / "standings-2026-11-18.retrieved.md").read_text()
        broken = text.replace("| Buffalo Bills | 8 | 1 | 0 | 0.889 | 287 | 199 | 3 - 1 - 0 | 5 - 0 - 0 |",
                              "| Buffalo Bills | 8 | 1 | 0 | 0.889 | 287 | 199 | 4 - 1 - 0 | 5 - 0 - 0 |")
        self.assertNotEqual(text, broken)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture.md"
            path.write_text(broken)
            with self.assertRaises(SystemExit):
                E.parse_standings_capture(path)


class TestCompletionProof(unittest.TestCase):
    def test_delta_equals_the_settled_headline(self):
        current = E.parse_standings_capture()
        previous = E.load_csv(E.STANDINGS_1117_CSV)
        settled = E.parse_week10_completion()["settled"]
        proof = E.prove_completion(E.delta_between(previous, current), settled)
        self.assertEqual(proof["settled_fixture"], "LAC at BAL")
        self.assertEqual(proof["settled_score"], "LAC 23, BAL 20")
        self.assertEqual(proof["clubs_whose_records_changed"], 2)

    def test_a_wrong_score_is_refused(self):
        current = E.parse_standings_capture()
        previous = E.load_csv(E.STANDINGS_1117_CSV)
        deltas = E.delta_between(previous, current)
        wrong = {"away": "LAC", "home": "BAL", "away_score": 24, "home_score": 20,
                 "weekday": "Monday", "date": "November 16"}
        with self.assertRaises(SystemExit):
            E.prove_completion(deltas, wrong)

    def test_the_feed_is_exactly_one_game_behind(self):
        residue = E.feed_residue(E.parse_standings_capture())
        self.assertEqual(residue["official_games_played"] - residue["feed_games"], 1)
        self.assertEqual(sorted(residue["clubs_affected"]),
                         ["Baltimore Ravens", "Los Angeles Chargers"])
        # one win, one loss, four point cells: exactly one game
        self.assertEqual(residue["residue_cells"], 6)


class TestRulesExtraction(unittest.TestCase):
    def test_every_2026_value_is_extracted_from_the_capture(self):
        values = RU.extract()
        self.assertEqual(values["declaration_clock_seconds"], 25)
        self.assertEqual(values["onside_restraining_line"], 35)
        self.assertEqual(values["onside_safety_kick_line"], 20)
        self.assertEqual(values["setup_zone_yards"], 5)
        self.assertEqual(values["setup_zone_receiving_lines"], [35, 30])
        self.assertEqual(values["touchback_from_50_dead_ball"], 20)
        self.assertEqual(values["kickoff_restraining_line"], 35)
        self.assertTrue(values["legal_at_any_time"])
        self.assertTrue(values["is_a_2026_change"])

    def test_altered_wording_breaks_extraction_instead_of_publishing(self):
        text = (DESK / "evidence" / "rules-2026-kickoff-onside.retrieved.md").read_text()
        # "At any time during the game" is wrapped across two lines in the capture, so
        # remove the clause on both sides of the wrap instead of matching one raw line.
        broken = (text.replace("At any time during the game, the kicking team may declare an", "")
                      .replace("onside kick by notifying the Referee", "The kicking team notifies the Referee"))
        self.assertNotEqual(text, broken)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rules.md"
            path.write_text(broken)
            original = RU.CAPTURE
            try:
                RU.CAPTURE = path
                with self.assertRaises(SystemExit):
                    RU.extract()
            finally:
                RU.CAPTURE = original

    def test_no_frequency_or_probability_is_published(self):
        """Prose may say a frequency is not held; no numeric frequency may be emitted."""
        import re
        status = RU.status()
        for row in status["regime_rows"]:
            self.assertNotIn("%", str(row["value"]))
        for note in status["model_notes"]:
            self.assertEqual(note["priced_here"].split("—")[0].strip(), "not priced")
            self.assertNotRegex(note["bias_if_ignored"], r"\b\d+(\.\d+)?\s?(%|percent)")
        self.assertNotRegex(status["what_is_still_open"], r"\b\d+(\.\d+)?%")


class TestRequirementRegister(unittest.TestCase):
    def test_every_named_artefact_resolves(self):
        rows = R.verify_rows()
        self.assertGreater(len(rows), 0)
        missing = [r["id"] for r in rows if not r["artifact_resolves"]]
        self.assertEqual(missing, [])

    def test_published_status_is_carried_through_unchanged(self):
        register = json.loads((ROOT / "research" / "nfl-decision-readiness.json").read_text())
        published = {r["id"]: r["status"] for r in register["requirements"]}
        for row in R.verify_rows():
            self.assertEqual(row["published_status"], published[row["id"]])

    def test_summary_counts_add_up(self):
        summary = R.summary(R.verify_rows())
        self.assertEqual(summary["implemented"] + summary["partial"] + summary["open"]
                         + summary["blocked"] + summary["rejected"], summary["rows"])


class TestPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = B.build(write=False)

    def test_every_page_is_generated(self):
        for name, _ in B.PAGES:
            self.assertIn(name, self.pages)

    def test_every_tbody_row_declares_a_source(self):
        import re
        for name, _ in B.PAGES:
            html = self.pages[name]
            body = "".join(re.findall(r"<tbody>(.*?)</tbody>", html, re.S))
            body_rows = re.findall(r"<tr\b", body)
            sourced = re.findall(r"<tr[^>]*\bdata-source-ids=\"[^\"]+\"", body)
            self.assertEqual(len(body_rows), len(sourced),
                             f"{name}: {len(body_rows) - len(sourced)} body row(s) declare no source")

    def test_every_row_links_to_a_registered_source(self):
        """Each row must link to the registered URL of a source id it actually declares."""
        import re
        registry = {r["id"]: r["url"] for r in
                    json.loads((ROOT / "research" / "sources.json").read_text())}
        for name, _ in B.PAGES:
            for attrs, row in re.findall(
                    r"<tr[^>]*data-source-ids=\"([^\"]+)\"[^>]*>(.*?)</tr>", self.pages[name], re.S):
                ids = attrs.split()
                hrefs = re.findall(r'href="([^"]+)"', row)
                self.assertTrue(any(registry.get(i) in hrefs for i in ids),
                                f"{name}: row {ids} does not link its own registered source")

    def test_no_price_roi_or_wager_language(self):
        """The desk may *mention* that no price exists; it must never print one."""
        import re
        for name, _ in B.PAGES:
            html = self.pages[name]
            text = re.sub(r"<[^>]+>", " ", html).lower()
            for forbidden in ("profit", "bankroll", "stake $", "guaranteed", "expected value of",
                              "win rate of", "roi of"):
                self.assertNotIn(forbidden, text, f"{name}: prints {forbidden!r}")
            # No currency amount anywhere.
            self.assertIsNone(re.search(r"[\u00a3$\u20ac]\s?\d", text), f"{name}: prints a money amount")

    def test_blank_cells_are_truly_empty(self):
        import re
        for name, _ in B.PAGES:
            for cell in re.findall(r'<td class="blank" title="[^"]*">(.*?)</td>', self.pages[name], re.S):
                self.assertEqual(cell.strip(), "", f"{name}: a blank cell carries content")


class TestDeterministicBuild(unittest.TestCase):
    def test_rebuild_is_byte_identical(self):
        result = subprocess.run([sys.executable, str(DESK / "build.py"), "--check"],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("reproduce byte-identically", result.stdout)


if __name__ == "__main__":
    unittest.main()
