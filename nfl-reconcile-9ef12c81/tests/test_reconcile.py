"""Contract tests for the decision-readiness reconciliation desk (session arena/9ef12c81-own7).

The build itself aborts on drift; these tests pin what the published desk must say so that a
later edit cannot quietly change a status, drop a source link, or publish an unsourced row.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import build  # noqa: E402  (the desk's own generator, imported for its validators)


class Register(unittest.TestCase):
    def setUp(self):
        self.register = json.loads((ROOT / "research/nfl-decision-readiness.json").read_text())
        self.adj = json.loads((HERE / "adjudications.json").read_text())
        self.rows = {r["id"]: r for r in self.register["requirements"]}

    def test_register_has_70_rows_and_expected_mix(self):
        self.assertEqual(len(self.rows), 70)
        counts = {}
        for r in self.register["requirements"]:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        self.assertEqual(counts, {"Implemented": 30, "Partial": 23, "Open": 11, "Blocked": 4, "Rejected": 2})

    def test_every_re_read_row_matches_the_register_it_was_written_against(self):
        for a in self.adj["adjudications"]:
            self.assertIn(a["id"], self.rows, a["id"])
            self.assertEqual(self.rows[a["id"]]["status"], a["register_status"], a["id"])

    def test_only_three_status_changes_are_proposed_and_they_are_open_to_partial(self):
        changes = {a["id"]: (a["register_status"], a["proposed_status"])
                   for a in self.adj["adjudications"] if a["proposed_status"] != a["register_status"]}
        self.assertEqual(changes, {"DR-61": ("Open", "Partial"), "DR-64": ("Open", "Partial"),
                                   "DR-68": ("Open", "Partial")})

    def test_rights_rows_stay_blocked(self):
        for rid in ("DR-29", "DR-54", "DR-66"):
            a = next(x for x in self.adj["adjudications"] if x["id"] == rid)
            self.assertEqual(a["proposed_status"], "Blocked", rid)

    def test_all_statuses_in_the_adjudications_use_the_register_vocabulary(self):
        allowed = set(self.adj["allowed_statuses"])
        for a in self.adj["adjudications"]:
            self.assertIn(a["proposed_status"], allowed)
            self.assertIn(a["register_status"], allowed)

    def test_every_cited_evidence_file_exists(self):
        for a in self.adj["adjudications"]:
            for e in a["evidence"]:
                self.assertTrue((ROOT / e).is_file(), f'{a["id"]}: {e}')
        for i in self.adj["irregularities"]:
            for e in i["evidence"]:
                self.assertTrue((ROOT / e).is_file(), f'{i["id"]}: {e}')

    def test_validators_report_no_errors(self):
        errors: list[str] = []
        sources = json.loads((ROOT / "research/sources.json").read_text())
        build.validate(self.register, sources, self.adj, errors)
        self.assertEqual(errors, [])

    def test_live_numbers_quoted_in_reasons_still_hold(self):
        errors: list[str] = []
        facts = build.live_checks(errors)
        self.assertEqual(errors, [])
        self.assertEqual((facts["snap_rows"], facts["snap_teams"], facts["snap_games"]), (1217, 26, 13))
        self.assertEqual(facts["snap_unofficial_rows"], 371)
        self.assertEqual(facts["depth_clubs_union"], 31)
        self.assertEqual(facts["w10_byes"], ["CHI", "DEN", "PHI", "TB"])
        self.assertEqual(facts["whatchanged_changed_standings"], ["BAL", "LAC"])
        self.assertTrue(facts["willis_nov_row"])


class Evidence(unittest.TestCase):
    def test_terms_excerpt_keeps_the_verbatim_section_1_3_sentence(self):
        raw = (HERE / "evidence/nfl-terms-1-3-2026-11-18.md").read_text(encoding="utf-8")
        # Quoted lines are wrapped with '> ' markers; normalise to one sentence stream.
        text = " ".join(line.lstrip("> ").strip() for line in raw.splitlines())
        self.assertIn("Systematic retrieval of data or other content from the Services, whether to create or "
                      "compile, directly or indirectly, a collection, compilation, database, or directory, is "
                      "prohibited absent our express prior written consent.", text)
        self.assertIn("https://www.nfl.com/legal/terms/", text)
        self.assertIn("Updated: May 16, 2024", text)


class Pages(unittest.TestCase):
    def setUp(self):
        self.out = build.build()

    def test_index_has_one_row_per_register_requirement(self):
        html = self.out["index.html"]
        self.assertEqual(len(re.findall(r"<tr data-source-ids=", html)), 70)

    def test_every_row_carries_a_registered_official_source_id(self):
        registry = {s["id"] for s in json.loads((ROOT / "research/sources.json").read_text())}
        for name in ("index.html", "questions.html", "flagged.html"):
            for ids in re.findall(r'<tr data-source-ids="([^"]*)"', self.out[name]):
                self.assertTrue(ids.strip(), name)
                for sid in ids.split():
                    self.assertIn(sid, registry, name)

    def test_pages_are_deterministic(self):
        again = build.build()
        self.assertEqual(again, self.out)

    def test_no_value_is_populated_beyond_what_is_sourced(self):
        # A carried-forward row must not show a new outcome label or evidence link.
        html = self.out["index.html"]
        self.assertEqual(html.count("Carried forward (not re-read)"), 58)

    def test_manifest_lists_only_html_pages_that_exist(self):
        manifest = json.loads(self.out["manifest.json"])
        for name in manifest["pages"]:
            self.assertTrue((HERE / "site" / name).is_file() or name in self.out, name)


if __name__ == "__main__":
    unittest.main()
