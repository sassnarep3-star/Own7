#!/usr/bin/env python3
"""Offline structural checks, not verification of current rule text or prices."""
import copy
import json
import unittest
from html.parser import HTMLParser
from urllib.parse import urlsplit

import build


class SourcesInCards(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.cards = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and "data-record" in attrs:
            self.current = attrs["data-record"]
            if self.current in self.cards:
                raise ValueError(f"Duplicate rendered card: {self.current}")
            self.cards[self.current] = []
        elif tag == "a" and self.current is not None:
            self.cards[self.current].append(attrs.get("href", ""))

    def handle_endtag(self, tag):
        if tag == "article":
            self.current = None


class EvidenceBuildTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(build.DATA.read_text(encoding="utf-8"))

    def test_every_card_links_its_exact_official_sources(self):
        parser = SourcesInCards()
        parser.feed(build.render(self.data))
        rows = self.data["findings"] + self.data["flags"]
        self.assertEqual(set(parser.cards), {row["id"] for row in rows})
        for row in rows:
            expected = {self.data["sources"][key]["url"] for key in row["sources"]}
            self.assertEqual(set(parser.cards[row["id"]]), expected, row["id"])
            self.assertTrue(all(urlsplit(url).scheme == "https" and urlsplit(url).hostname in build.OFFICIAL_HOSTS for url in expected))

    def test_committed_html_is_reproducible(self):
        self.assertEqual(build.OUT.read_text(encoding="utf-8"), build.render(self.data))

    def test_missing_source_is_rejected(self):
        invalid = copy.deepcopy(self.data)
        invalid["findings"][0]["sources"] = []
        with self.assertRaises(ValueError):
            build.validate(invalid)

    def test_unknown_source_is_rejected(self):
        invalid = copy.deepcopy(self.data)
        invalid["findings"][0]["sources"] = ["not_a_source"]
        with self.assertRaises(ValueError):
            build.validate(invalid)

    def test_malicious_lookalike_domain_is_rejected(self):
        invalid = copy.deepcopy(self.data)
        invalid["sources"]["toto_builder"]["url"] = "https://www.toto.nl.example.org/"
        with self.assertRaises(ValueError):
            build.validate(invalid)

    def test_duplicate_id_is_rejected(self):
        invalid = copy.deepcopy(self.data)
        invalid["flags"][0]["id"] = invalid["findings"][0]["id"]
        with self.assertRaises(ValueError):
            build.validate(invalid)

    def test_unverified_value_must_remain_blank(self):
        invalid = copy.deepcopy(self.data)
        invalid["flags"][0]["unverified_value"] = "guessed"
        with self.assertRaises(ValueError):
            build.validate(invalid)

    def test_statement_text_is_html_escaped(self):
        invalid = copy.deepcopy(self.data)
        invalid["findings"][0]["finding"] = '<script>alert("x")</script>'
        page = build.render(invalid)
        self.assertNotIn('<script>alert("x")</script>', page)
        self.assertIn('&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;', page)


if __name__ == "__main__":
    unittest.main()
