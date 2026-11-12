#!/usr/bin/env python3
"""Structural tests for the NFL decision desk. Offline checks; not an external fact re-check.

Run:  python3 nfl-desk/test_build.py -v
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build  # noqa: E402
import desk  # noqa: E402

OFFICIAL_HOSTS = {
    "www.nfl.com",
    "official.nfl.com",
    "operations.nfl.com",
    "www.commanders.com",
    "www.giants.com",
    "www.seahawks.com",
    "docs.scipy.org",
    "github.com",
}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.h1 = 0
        self.main = 0
        self.lang = None
        self.title = False
        self.ids: set[str] = set()
        self.duplicate_ids: list[str] = []
        self.links: list[str] = []
        self.rows: list[dict] = []
        self.in_body = False
        self.row = None
        self.in_empty_cell = 0
        self.empty_text: list[str] = []
        self.missing_noopener = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "title":
            self.title = True
        if tag == "h1":
            self.h1 += 1
        if tag == "main":
            self.main += 1
        if a.get("id"):
            if a["id"] in self.ids:
                self.duplicate_ids.append(a["id"])
            self.ids.add(a["id"])
        if tag == "tbody":
            self.in_body = True
        if tag == "tr" and self.in_body:
            self.row = {"source_ids": a.get("data-source-ids", "").split(), "refs": [], "cells": 0}
        if tag in ("a",) and a.get("href"):
            self.links.append(a["href"])
            if self.row is not None:
                self.row["refs"].append(a["href"])
        if tag == "a" and a.get("target") == "_blank":
            rel = set(a.get("rel", "").split())
            if not {"noopener", "noreferrer"} <= rel:
                self.missing_noopener += 1
        if tag == "td":
            if self.row is not None:
                self.row["cells"] += 1
            if a.get("data-empty") == "true":
                self.in_empty_cell = 1
            elif self.in_empty_cell:
                self.in_empty_cell += 1
        elif self.in_empty_cell:
            self.in_empty_cell += 1

    def handle_data(self, data):
        if self.in_empty_cell and data.strip():
            self.empty_text.append(data.strip())

    def handle_endtag(self, tag):
        if self.in_empty_cell:
            self.in_empty_cell -= 1
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        if tag == "tbody":
            self.in_body = False


def parse(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


class SnapshotIntegrityTests(unittest.TestCase):
    """The snapshots must satisfy their own arithmetic identities."""

    def test_standings_identity_holds_for_all_32_clubs(self):
        rows = desk.standings()
        self.assertEqual(len(rows), 32)
        for r in rows:
            self.assertAlmostEqual(r["pct"], (r["w"] + r["t"] / 2) / r["games"], places=2)
            self.assertEqual(r["net"], r["pf"] - r["pa"])

    def test_standings_reject_a_tampered_value(self):
        original = (desk.DATA / "standings-2026.psv").read_text(encoding="utf-8")
        try:
            tampered = original.replace("BUF|Buffalo Bills|7|1|0|0.875|256", "BUF|Buffalo Bills|7|1|0|0.900|256")
            (desk.DATA / "standings-2026.psv").write_text(tampered, encoding="utf-8")
            with self.assertRaises(desk.DataError):
                desk.standings()
        finally:
            (desk.DATA / "standings-2026.psv").write_text(original, encoding="utf-8")

    def test_passing_percentage_is_reproducible_from_integers(self):
        for r in desk.passing():
            self.assertLess(abs(round(r["cmp"] / r["att"] * 100, 2) - r["pct"]), 0.06, r["abbr"])

    def test_passing_snapshot_does_not_publish_the_unreproducible_average(self):
        text = (desk.DATA / "passing-2026.psv").read_text(encoding="utf-8")
        header = [line for line in text.splitlines() if not line.startswith("#")][0]
        self.assertEqual(header, "abbr|att|cmp|pct|yds")
        self.assertNotIn("avg", header)

    def test_injury_statuses_are_within_the_rendered_vocabulary(self):
        rows = desk.injuries()
        self.assertEqual(len(rows), 276)
        for r in rows:
            self.assertIn(r["practice"], desk.PRACTICE_VOCAB)
            self.assertIn(r["game"], desk.GAME_VOCAB)

    def test_injury_snapshot_rejects_an_invented_status(self):
        original = (desk.DATA / "injury-week10-2026.psv").read_text(encoding="utf-8")
        try:
            tampered = original.replace("WAS|Lucas Patrick|C|Concussion|Did Not Participate In Practice|Out",
                                        "WAS|Lucas Patrick|C|Concussion|Did Not Participate In Practice|Probable")
            (desk.DATA / "injury-week10-2026.psv").write_text(tampered, encoding="utf-8")
            with self.assertRaises(desk.DataError):
                desk.injuries()
        finally:
            (desk.DATA / "injury-week10-2026.psv").write_text(original, encoding="utf-8")

    def test_week10_fixtures_cover_28_clubs_once_each(self):
        games = desk.week10_games()
        self.assertEqual(len(games), 14)
        clubs = [g[side] for g in games for side in ("away", "home")]
        self.assertEqual(len(clubs), 28)
        self.assertEqual(len(set(clubs)), 28)
        self.assertFalse(set(clubs) & {"CHI", "DEN", "PHI", "TB"})

    def test_every_snapshot_has_a_hash_and_a_stated_check(self):
        for row in desk.integrity():
            self.assertRegex(row["sha256"], r"^[a-f0-9]{64}$")
            self.assertTrue(row["check"])


class StatisticsTests(unittest.TestCase):
    def test_pearson_and_spearman_match_known_values(self):
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 11]
        self.assertAlmostEqual(desk.pearson(x, y), 0.9958932064677039, places=10)
        self.assertAlmostEqual(desk.spearman(x, y), 1.0, places=10)
        self.assertAlmostEqual(desk.spearman([1, 2, 3, 4, 5], [1, 2, 3, 5, 4]), 0.9, places=10)

    def test_permutation_test_is_deterministic(self):
        x = [r["pf"] for r in desk.standings()]
        y = [r["pct"] for r in desk.standings()]
        first = desk.permutation_p(x, y, desk.pearson(x, y), iterations=2000)
        second = desk.permutation_p(x, y, desk.pearson(x, y), iterations=2000)
        self.assertEqual(first, second)

    def test_wilson_interval_brackets_the_estimate(self):
        low, high = desk.wilson(6, 8)
        self.assertLess(low, 0.75)
        self.assertGreater(high, 0.75)
        self.assertAlmostEqual(low, 0.4093, places=3)

    def test_pythagorean_is_monotone_and_bounded(self):
        self.assertGreater(desk.pythagorean(300, 200), desk.pythagorean(200, 300))
        self.assertAlmostEqual(desk.pythagorean(250, 250), 0.5, places=10)

    def test_correlation_table_reports_unit_of_analysis(self):
        rows = desk.correlation_table()
        self.assertEqual(len(rows), 8)
        for r in rows:
            self.assertEqual(r["unit"], "club-season (n=32)")
            self.assertTrue(-1 <= r["pearson"] <= 1)
            self.assertTrue(0 <= r["p_perm"] <= 1)


class LedgerTests(unittest.TestCase):
    def test_sources_are_official_https_domains_with_scope(self):
        for row in desk.load_ledger("data/sources.json")["sources"]:
            self.assertTrue(row["url"].startswith("https://"), row["id"])
            host = re.sub(r"^https://", "", row["url"]).split("/")[0]
            self.assertIn(host, OFFICIAL_HOSTS, row["id"])
            self.assertTrue(row["scope"].strip())
            self.assertEqual(row["checked_on"], "2026-11-12")

    def test_every_referenced_source_id_exists(self):
        known = set(desk.sources())
        for name in ("gates", "strategies", "questions", "suggestions", "flags", "repo-review"):
            data = desk.load_ledger(f"data/{name}.json")
            key = {"repo-review": "checks"}.get(name, name)
            for row in data[key]:
                for sid in row.get("source_ids", []):
                    self.assertIn(sid, known, f"{name}:{row.get('id')} -> {sid}")

    def test_every_strategy_market_field_is_null(self):
        for row in desk.load_ledger("data/strategies.json")["strategies"]:
            for field in ("market_line", "price", "roi", "clv", "leg_correlation"):
                self.assertIsNone(row[field], f'{row["id"]}.{field}')

    def test_every_flag_has_no_filled_value(self):
        for row in desk.load_ledger("data/flags.json")["flags"]:
            self.assertIsNone(row["unverified_value"], row["id"])

    def test_every_reward_has_no_monetary_value(self):
        for row in desk.load_ledger("data/competition.json")["rewards"]:
            self.assertIsNone(row["monetary_value"], row["id"])
            self.assertEqual(row["status"], "Not awarded")

    def test_every_gate_is_blocked_and_states_why(self):
        gates = desk.load_ledger("data/gates.json")["gates"]
        self.assertEqual(len(gates), 10)
        for g in gates:
            self.assertEqual(g["status"], "Blocked")
            self.assertGreater(len(g["current"]), 40, g["id"])

    def test_every_question_states_held_and_missing_information(self):
        for q in desk.load_ledger("data/questions.json")["questions"]:
            self.assertIn(q["status"], ("Answered", "Partly answered", "Unknown"))
            self.assertTrue(q["answer"].strip())
            self.assertTrue(q["information_missing"].strip())

    def test_every_suggestion_is_unimplemented_and_reviewable(self):
        rows = desk.load_ledger("data/suggestions.json")["suggestions"]
        self.assertEqual(len(rows), 12)
        for r in rows:
            self.assertEqual(r["disposition"], "Proposed", r["id"])
            for field in ("problem", "proposal", "rationale", "evidence", "effort", "risk", "gate"):
                self.assertTrue(r[field].strip(), f'{r["id"]}.{field}')

    def test_repository_review_has_no_unclassified_rows(self):
        rows = desk.load_ledger("data/repo-review.json")["checks"]
        self.assertEqual(len(rows), 18)
        for r in rows:
            self.assertIn(r["disposition"], ("Verified", "Irregular"))
            self.assertTrue(r["method"].strip())


class PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rendered = build.render()
        cls.parsed = {name: parse(HERE / name) for name in build.PAGES}

    def test_build_is_deterministic(self):
        again = build.render()
        self.assertEqual(self.rendered, again)

    def test_committed_pages_match_a_fresh_build(self):
        for name in build.PAGES:
            on_disk = (HERE / name).read_text(encoding="utf-8")
            self.assertEqual(on_disk, self.rendered[name], f"{name} is stale; run build.py")

    def test_document_semantics(self):
        for name, p in self.parsed.items():
            self.assertEqual(p.h1, 1, f"{name}: one h1")
            self.assertEqual(p.main, 1, f"{name}: one main")
            self.assertEqual(p.lang, "en", f"{name}: lang")
            self.assertTrue(p.title, f"{name}: title")
            self.assertEqual(p.duplicate_ids, [], f"{name}: duplicate ids")

    def test_blank_cells_are_genuinely_empty(self):
        for name, p in self.parsed.items():
            self.assertEqual(p.empty_text, [], f"{name}: an unknown cell contains text")

    def test_every_table_row_carries_a_registered_source_link(self):
        """Each row either links its sources directly or links an in-page detail entry that does.

        Wide ledgers would be unreadable if every row repeated four long source links, so a row may
        delegate to a detail anchor. The delegation is only accepted when that anchor renders the very
        same registered URLs, which keeps provenance visible one click away instead of hidden.
        """
        registry = desk.sources()
        sections = {}
        for name, content in self.rendered.items():
            for sid, body in re.findall(r'id="(detail-[^"]+)"[^>]*>(.*?)</section>', content, re.S):
                sections[(name, sid)] = set(re.findall(r'href="(https://[^"]+)"', body))
        total = 0
        delegated = 0
        for name, p in self.parsed.items():
            for row in p.rows:
                total += 1
                ids = row["source_ids"]
                if not ids:
                    continue
                for sid in ids:
                    self.assertIn(sid, registry, f"{name}: unregistered id {sid}")
                    url = registry[sid]["url"]
                    if url in row["refs"]:
                        continue
                    anchors = [r.split("#", 1)[-1] for r in row["refs"] if "#detail-" in r]
                    self.assertTrue(anchors, f"{name}: row links neither its source nor a detail entry")
                    for anchor in anchors:
                        self.assertIn(url, sections.get((name, anchor), set()),
                                      f"{name}: #{anchor} does not render {sid}")
                    delegated += 1
        self.assertGreater(total, 400, "expected a substantial number of body rows")
        self.assertGreater(delegated, 0, "the delegation path should be exercised")
        self.assertLess(delegated, total, "most rows should still link their sources directly")

    def test_delegated_rows_still_declare_their_source_ids(self):
        for name, p in self.parsed.items():
            for row in p.rows:
                if any("#detail-" in ref for ref in row["refs"]):
                    self.assertTrue(row["source_ids"], f"{name}: delegated row without source IDs")

    def test_external_links_open_safely(self):
        for name, p in self.parsed.items():
            self.assertEqual(p.missing_noopener, 0, f"{name}: target=_blank without rel")

    def test_every_external_link_is_https(self):
        for name, p in self.parsed.items():
            for href in p.links:
                if href.startswith("http"):
                    self.assertTrue(href.startswith("https://"), f"{name}: {href}")

    def test_internal_links_and_fragments_resolve(self):
        for name, p in self.parsed.items():
            for href in p.links:
                if href.startswith(("http", "mailto:")):
                    continue
                target, _, fragment = href.partition("#")
                target = target or name
                path = HERE / target
                self.assertTrue(path.is_file(), f"{name}: missing {target}")
                if fragment:
                    other = self.parsed.get(target) or parse(path)
                    self.assertIn(fragment, other.ids, f"{name}: missing #{fragment} in {target}")

    def test_no_page_claims_a_price_or_return(self):
        forbidden = re.compile(r"(?i)(expected value|\bROI\b\s*[:=]\s*[-+]?\d|closing line value\s*[:=]\s*\d)")
        for name, content in self.rendered.items():
            self.assertIsNone(forbidden.search(content), f"{name}: looks like a price claim")

    def test_required_pages_exist_in_navigation(self):
        for name in build.PAGES:
            self.assertIn(f'href="{name}"', self.rendered["index.html"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
