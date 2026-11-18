"""Tests for the Week 11 injury desk (session arena/3e6166df-own7).

The desk's build.py re-derives every number from the verbatim transcript and aborts on any
contradiction. These tests pin the contracts that keep the desk honest: the transcript is
unchanged, the printed counts hold, blank cells stay blank, every row links a registered
official source, and the register grades that depend on this read are consistent.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import build  # noqa: E402  (the desk's own parser and derivation)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class Transcript(unittest.TestCase):
    def setUp(self):
        self.text = build.EVIDENCE.read_text(encoding="utf-8")
        self.parsed = build.parse_evidence(self.text)

    def test_hash_recorded_in_checks_matches_file(self):
        recorded = json.loads((HERE / "data" / "checks.json").read_text())["evidence_sha256"]
        self.assertEqual(recorded, hashlib.sha256(build.EVIDENCE.read_bytes()).hexdigest())

    def test_printed_counts_are_pinned(self):
        ev = self.parsed
        self.assertEqual(len(ev["games"]), 13)
        self.assertEqual(len(ev["clubs"]), 26)
        self.assertEqual(len(ev["rows"]), 26)
        rows_by_club = {c["code"]: len(c["rows"]) for c in ev["clubs"] if c["rows"]}
        self.assertEqual(rows_by_club, {"IND": 11, "HOU": 15})
        self.assertEqual(sum(1 for c in ev["clubs"] if c["status"] == build.NO_INJURY), 24)

    def test_every_club_has_rows_xor_no_injury_line(self):
        for club in self.parsed["clubs"]:
            self.assertNotEqual(bool(club["rows"]), club["status"] == build.NO_INJURY, club["code"])

    def test_blank_cells_stay_blank(self):
        for r in self.parsed["rows"]:
            self.assertEqual(r["game_status_printed"], "")
            self.assertEqual(r["injuries_printed"], "")

    def test_every_row_links_an_nfl_player_page(self):
        for r in self.parsed["rows"]:
            self.assertTrue(r["player_page_printed"].startswith("https://www.nfl.com/players/"))

    def test_reader_refuses_a_truncated_row(self):
        bad = self.text.replace("| Wyatt Teller | G |  | Full Participation in Practice |  |",
                                "| Wyatt Teller | G |  |")
        with self.assertRaises(SystemExit):
            build.parse_evidence(bad)

    def test_reader_refuses_a_changed_count(self):
        # Dropping one IND row must fail the pinned-count derivation.
        lines = self.text.splitlines()
        drop = next(i for i, l in enumerate(lines) if l.startswith("| Dalton Tucker"))
        del lines[drop]
        with self.assertRaises(SystemExit):
            build.derive("\n".join(lines), (ROOT / "nfl-results/evidence/week-11.schedule.md").read_text())


class Derived(unittest.TestCase):
    def test_all_sixteen_checks_pass(self):
        checks = json.loads((HERE / "data" / "checks.json").read_text())["checks"]
        self.assertEqual(len(checks), 16)
        self.assertTrue(all(c["result"] == "pass" for c in checks))

    def test_slate_matches_official_schedule_transcript(self):
        rows = read_csv(HERE / "data" / "slate-week11.csv")
        self.assertEqual(len(rows), 13)
        self.assertTrue(all(r["schedule_check"] == "match" for r in rows))

    def test_printed_records_match_official_standings_read(self):
        rows = read_csv(HERE / "data" / "clubs-week11.csv")
        self.assertEqual(len(rows), 26)
        self.assertTrue(all(r["record_check"] == "match" for r in rows))

    def test_playing_clubs_and_byes_partition_the_league(self):
        playing = {r["club_code"] for r in read_csv(HERE / "data" / "clubs-week11.csv")}
        sched = build.parse_schedule((ROOT / "nfl-results/evidence/week-11.schedule.md").read_text())
        bye_codes = {b["code"] for b in sched["byes"]}
        self.assertEqual(len(bye_codes), 6)
        self.assertFalse(playing & bye_codes)
        self.assertEqual(len(playing | bye_codes), 32)


class Pages(unittest.TestCase):
    class _Rows(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.rows, self.row, self.refs, self.blank, self.in_tbody = [], None, [], 0, False
            self.blank_text, self.blank_errors = "", []

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if tag == "tbody":
                self.in_tbody = True
            if tag == "tr" and self.in_tbody:
                self.row = {"ids": a.get("data-source-ids", "").split(), "refs": []}
            if tag == "a" and self.row is not None and a.get("href"):
                self.row["refs"].append(a["href"])
            if tag == "td" and a.get("data-empty") == "true":
                self.blank, self.blank_text = 1, ""
            elif self.blank:
                self.blank += 1

        def handle_data(self, data):
            if self.blank:
                self.blank_text += data

        def handle_endtag(self, tag):
            if self.blank:
                self.blank -= 1
                if self.blank == 0 and self.blank_text.strip():
                    self.blank_errors.append(self.blank_text)
            if tag == "tr" and self.row is not None:
                self.rows.append(self.row)
                self.row = None
            if tag == "tbody":
                self.in_tbody = False

    def test_every_table_row_links_its_registered_official_source(self):
        registry = {r["id"]: r["url"] for r in json.loads((ROOT / "research/sources.json").read_text())}
        for page in sorted((HERE / "site").glob("*.html")):
            parser = self._Rows()
            parser.feed(page.read_text(encoding="utf-8"))
            self.assertEqual(parser.blank_errors, [], page.name)
            for row in parser.rows:
                self.assertTrue(row["ids"], page.name)
                for sid in row["ids"]:
                    self.assertIn(sid, registry)
                self.assertTrue(any(registry[s] in row["refs"] for s in row["ids"]), page.name)

    def test_injury_page_has_26_rows(self):
        parser = self._Rows()
        parser.feed((HERE / "site" / "injuries.html").read_text(encoding="utf-8"))
        self.assertEqual(len(parser.rows), 26)


class Register(unittest.TestCase):
    def setUp(self):
        self.reg = {r["id"]: r for r in json.loads(
            (ROOT / "research/nfl-decision-readiness.json").read_text())["requirements"]}
        self.sources = {r["id"]: r for r in json.loads((ROOT / "research/sources.json").read_text())}

    def test_week11_sources_are_registered_on_nfl_hosts(self):
        for sid in ("W11-NFL-INJ-1118", "W11-NFL-TERMS-1118"):
            self.assertIn(sid, self.sources)
            self.assertEqual(self.sources[sid]["url"].split("/")[2], "www.nfl.com")
            self.assertEqual(self.sources[sid]["checked_on"], "2026-11-18")

    def test_terms_gate_stays_blocked_and_cites_the_read(self):
        self.assertEqual(self.reg["DR-54"]["status"], "Blocked")
        self.assertIn("W11-NFL-TERMS-1118", self.reg["DR-54"]["source_ids"])

    def test_regraded_rows_cite_existing_artifacts(self):
        for rid in ("DR-61", "DR-64", "DR-68", "DR-54"):
            artifact = self.reg[rid]["artifact"]
            self.assertTrue((ROOT / artifact).is_file(), (rid, artifact))
            for sid in self.reg[rid]["source_ids"]:
                self.assertIn(sid, self.sources, (rid, sid))


class Reproduce(unittest.TestCase):
    def test_build_check_reproduces_byte_identically(self):
        result = subprocess.run([sys.executable, str(HERE / "build.py"), "--check"],
                                capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
