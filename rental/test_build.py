#!/usr/bin/env python3
"""Offline structural tests for the rental sub-site. Not a legal or fact check."""
import json
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import build

ROOT = Path(__file__).resolve().parent
OFFICIAL_HOSTS = {
    "www.sf.gov", "leginfo.legislature.ca.gov", "uscode.house.gov", "www.hud.gov",
}


class RowParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.in_body, self.row, self.links = [], False, None, []
        self.h1 = 0
        self.main = 0
        self.lang = None
        self.titles = 0

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

    def handle_endtag(self, tag):
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        if tag == "tbody":
            self.in_body = False


class RentalBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build.load_data()
        cls.pages = build.render(cls.data)
        cls.urls = build.src_urls(cls.data)

    def test_sources_are_official_https(self):
        for s in self.data["sources"]:
            parts = urlsplit(s["url"])
            self.assertEqual(parts.scheme, "https", s["id"])
            self.assertIn(parts.hostname, OFFICIAL_HOSTS, s["id"])
            for field in ("publisher", "title", "checked_on", "scope", "access"):
                self.assertTrue(s.get(field), f"{s['id']} missing {field}")

    def test_pages_have_required_semantics(self):
        for name, content in self.pages.items():
            parser = RowParser()
            parser.feed(content)
            self.assertEqual(parser.lang, "en", name)
            self.assertEqual(parser.titles, 1, name)
            self.assertEqual(parser.h1, 1, name)
            self.assertEqual(parser.main, 1, name)

    def test_every_table_row_links_registered_sources(self):
        for name, content in self.pages.items():
            parser = RowParser()
            parser.feed(content)
            if name != "index.html":
                self.assertTrue(parser.rows, name)
            for row in parser.rows:
                self.assertTrue(row["ids"], name)
                for sid in row["ids"]:
                    self.assertIn(sid, self.urls, f"{name}: unknown {sid}")
                self.assertTrue(
                    any(self.urls[sid] in row["refs"] for sid in row["ids"]),
                    f"{name}: row lacks link to a registered source",
                )

    def test_internal_links_resolve(self):
        for name, content in self.pages.items():
            parser = RowParser()
            parser.feed(content)
            for href in parser.links:
                parts = urlsplit(href)
                if parts.scheme or parts.netloc:
                    self.assertEqual(parts.scheme, "https", f"{name}: non-https {href}")
                    continue
                if not parts.path:
                    self.assertIn(parts.fragment, content, f"{name}: missing fragment {href}")
                    continue
                target = (ROOT / parts.path).resolve()
                if parts.path.endswith("/"):
                    target = target / "index.html"
                self.assertTrue(target.is_file(), f"{name}: broken {href}")

    def test_no_real_names_only_placeholders(self):
        blob = json.dumps(self.data)
        for initials in ("L O", "V N", "JP", "M T", "E R", "I S"):
            self.assertNotIn(initials, blob)

    def test_build_is_deterministic(self):
        again = build.render(build.load_data())
        self.assertEqual(again, self.pages)


if __name__ == "__main__":
    unittest.main(verbosity=2)
