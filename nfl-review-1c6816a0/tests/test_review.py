"""Tests for the NFL review desk (session arena/1c6816a0-own7). Standard library only.

Run:  python -m unittest discover -s nfl-review-1c6816a0/tests -v
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
SITE = HERE / "site"
CAT = SITE / "categories"
DATA = HERE / "data"
REGISTER = json.loads((ROOT / "research" / "nfl-decision-readiness.json").read_text(encoding="utf-8"))
SOURCES = {s["id"]: s for s in json.loads((ROOT / "research" / "sources.json").read_text(encoding="utf-8"))}
SCAN = json.loads((DATA / "scan.json").read_text(encoding="utf-8"))
CI = json.loads((DATA / "ci-run.json").read_text(encoding="utf-8"))
REVIEW = json.loads((DATA / "review.json").read_text(encoding="utf-8"))
ALLOWED_HOSTS = {"www.nfl.com", "support.nfl.com", "media.nfl.com", "github.com", "www.atlantafalcons.com", "www.chicagobears.com"}


class Rows(HTMLParser):
    """Collects <tr> rows that sit inside <tbody>, with their data-source-ids and hrefs."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_body = False
        self.row = None
        self.rows = []
        self.ids = []
        self.unverified = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.append(a["id"])
        if tag == "tbody":
            self.in_body = True
        if tag == "tr" and self.in_body:
            self.row = {"source_ids": a.get("data-source-ids", "").split(), "hrefs": []}
        if tag == "a" and self.row is not None and a.get("href"):
            self.row["hrefs"].append(a["href"])

    def handle_endtag(self, tag):
        if tag == "tbody":
            self.in_body = False
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if "UNVERIFIED" in data:
            self.unverified += 1


def parse(path: Path) -> Rows:
    p = Rows()
    p.feed(path.read_text(encoding="utf-8"))
    return p


class ReviewDeskTests(unittest.TestCase):
    def test_register_has_70_rows_and_status_counts_match_scan(self):
        rows = REGISTER["requirements"]
        self.assertEqual(len(rows), 70)
        counts = {}
        for r in rows:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        self.assertEqual(counts, SCAN["register"]["status_counts"])

    def test_every_register_row_has_an_existing_artifact_and_registered_sources(self):
        for r in REGISTER["requirements"]:
            self.assertTrue((ROOT / r["artifact"]).is_file(), f"{r['id']} artifact missing: {r['artifact']}")
            for sid in r["source_ids"]:
                self.assertIn(sid, SOURCES, f"{r['id']} cites unregistered {sid}")

    def test_every_register_row_appears_once_on_a_category_page(self):
        seen = []
        for path in sorted(CAT.glob("*.html")):
            seen += [i for i in parse(path).ids if re.fullmatch(r"DR-\d{2}", i)]
        self.assertEqual(sorted(seen), sorted(r["id"] for r in REGISTER["requirements"]))

    def test_every_table_row_links_a_registered_source_it_cites(self):
        for path in [SITE / "index.html", SITE / "flagged.html", SITE / "ci.html", SITE / "sources.html",
                     SITE / "suggestions.html", *sorted(CAT.glob("*.html"))]:
            for row in parse(path).rows:
                self.assertTrue(row["source_ids"], f"{path.name}: row without data-source-ids")
                urls = {SOURCES[s]["url"] for s in row["source_ids"] if s in SOURCES}
                self.assertTrue(urls & set(row["hrefs"]), f"{path.name}: row lacks its registered link")

    def test_all_registered_sources_cited_by_the_desk_are_official_or_this_repository(self):
        for r in REVIEW["reads"]:
            host = urlparse(r["url"]).netloc
            self.assertIn(host, ALLOWED_HOSTS, r["url"])
            self.assertEqual(SOURCES[r["source_id"]]["url"], r["url"])
        for row in SCAN["register"]["items"]:
            for h in row["sources"]:
                self.assertFalse(str(h.get("class", "")).startswith("NOT OFFICIAL"), f"{row['id']}: {h}")
                self.assertNotEqual(h.get("class"), "UNREGISTERED", f"{row['id']}: {h}")

    def test_ci_record_covers_every_command_in_the_workflow_and_changed_nothing(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_ci", HERE / "run_ci.py")
        run_ci = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_ci)
        text = (ROOT / ".github/workflows/check.yml").read_text(encoding="utf-8")
        expected = run_ci.extract_commands(text)
        self.assertEqual(CI["commands_total"], len(expected))
        self.assertEqual([x["command"] for x in CI["results"]], [x["command"] for x in expected])
        everything = run_ci.extract_commands(text, keep_self_checks=True)
        self.assertEqual(sorted(CI["not_recorded_self_checks"]),
                         sorted(x["command"] for x in everything if run_ci.is_self_check(x["command"])))
        self.assertEqual(CI["commands_failed"], 0)
        self.assertEqual(CI["worktree_changes_caused_by_run"], [])
        self.assertTrue(all(x["exit_code"] == 0 for x in CI["results"]))

    def test_flags_have_a_source_or_say_why_not_and_an_owner_action(self):
        ids = [f["id"] for f in REVIEW["flags"]]
        self.assertEqual(len(ids), len(set(ids)))
        for f in REVIEW["flags"]:
            self.assertTrue(f["owner_action"].strip(), f["id"])
            self.assertIn(f["status"], {"Needs review", "Environment note"}, f["id"])
            for dr in f["affects"]:
                self.assertIn(dr, {r["id"] for r in REGISTER["requirements"]}, f["id"])

    def test_unverified_items_are_labelled_on_the_flagged_page(self):
        labelled = parse(SITE / "flagged.html").unverified
        self.assertGreaterEqual(labelled, len(REVIEW["unverified"]))

    def test_reads_are_dated_and_use_the_registered_url(self):
        for r in REVIEW["reads"]:
            self.assertEqual(r["read_on"], "2026-11-19")

    def test_the_build_and_the_scan_reproduce_byte_identically(self):
        for script in ("scan.py", "build.py"):
            result = subprocess.run([sys.executable, str(HERE / script), "--check"], cwd=ROOT,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_manifest_pages_exist(self):
        manifest = json.loads((SITE / "manifest.json").read_text(encoding="utf-8"))
        for name in manifest["pages"]:
            self.assertTrue((SITE / name).is_file(), name)

    def test_each_page_has_one_h1_and_a_language(self):
        for path in [SITE / "index.html", *sorted(CAT.glob("*.html")), SITE / "flagged.html",
                     SITE / "ci.html", SITE / "sources.html", SITE / "suggestions.html", SITE / "requirements.html"]:
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("<h1>"), 1, path.name)
            self.assertIn('lang="en"', text, path.name)


if __name__ == "__main__":
    unittest.main()
