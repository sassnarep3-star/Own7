#!/usr/bin/env python3
"""Offline structural tests for the NFL sub-site. Not a fact check."""
import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

import build

ROOT = Path(__file__).resolve().parent
OFFICIAL_HOSTS = {"www.nfl.com", "support.nfl.com"}


class RowParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.in_body, self.row, self.links = [], False, None, []
        self.h1 = 0
        self.main = 0
        self.lang = None
        self.titles = 0
        self.blank_text = ""
        self.blank_depth = 0
        self.errors = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "title":
            self.titles += 1
        if tag == "h1":
            self.h1 += 1
        if tag == "main":
            self.main += 1
        if tag == "tbody":
            self.in_body = True
        if tag == "tr" and self.in_body:
            self.row = {"ids": a.get("data-source-ids", "").split(), "refs": []}
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
            if self.row is not None:
                self.row["refs"].append(a["href"])
        if tag == "td" and a.get("data-empty") == "true":
            self.blank_depth, self.blank_text = 1, ""
        elif self.blank_depth:
            self.blank_depth += 1

    def handle_data(self, data):
        if self.blank_depth:
            self.blank_text += data

    def handle_endtag(self, tag):
        if self.blank_depth:
            self.blank_depth -= 1
            if self.blank_depth == 0 and self.blank_text.strip():
                self.errors.append("blank cell not truly blank")
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        if tag == "tbody":
            self.in_body = False


class NflBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = build.render()
        cls.urls = build.src_urls()

    def test_page_inventory(self):
        self.assertEqual(set(self.pages), set(build.PAGES))
        self.assertEqual(len(build.PAGES), 15)

    def test_every_row_has_registered_source(self):
        for name, text in self.pages.items():
            p = RowParser()
            p.feed(text)
            self.assertEqual(p.errors, [], f"{name}: {p.errors}")
            for row in p.rows:
                self.assertTrue(row["ids"], f"{name}: row missing source ids")
                for sid in row["ids"]:
                    self.assertIn(sid, self.urls, f"{name}: unknown source {sid}")
                self.assertTrue(any(self.urls[s] in row["refs"] for s in row["ids"]), f"{name}: row lacks official link")

    def test_document_semantics(self):
        for name, text in self.pages.items():
            p = RowParser()
            p.feed(text)
            self.assertEqual(p.h1, 1, f"{name}: h1 count")
            self.assertEqual(p.main, 1, f"{name}: main count")
            self.assertEqual(p.lang, "en", f"{name}: lang")
            self.assertEqual(p.titles, 1, f"{name}: title")

    def test_no_invented_lines(self):
        catalog = json.loads((ROOT.parent / "research/nfl-catalog.json").read_text())
        for s in catalog["strategies"]:
            for k in ("market_line", "p_model", "roi", "clv", "correlation"):
                self.assertIsNone(s[k], f"{s['id']}: {k} must stay blank")
        results = json.loads((ROOT.parent / "research/nfl-results.json").read_text())
        self.assertEqual(results["leaderboard"], [])
        self.assertIsNone(results["cash_rewards"])

    def test_blanks_stay_blank(self):
        for name, text in self.pages.items():
            self.assertNotIn("TODO", text)
            self.assertNotIn("Lorem", text)

    def test_source_hosts_official(self):
        for sid, url in self.urls.items():
            if sid.startswith("NFL-"):
                from urllib.parse import urlparse
                self.assertIn(urlparse(url).netloc, OFFICIAL_HOSTS, f"{sid}: non-official host")


if __name__ == "__main__":
    unittest.main()
