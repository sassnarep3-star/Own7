#!/usr/bin/env python3
"""Tests for the Week 11 live decision desk (session arena/9388352a-own7).

The tests re-derive the facts from the committed artefacts rather than restating them, so a
fact that was transcribed wrongly and then baked into a JSON file still fails here.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = ROOT / "nfl-week11-9388"
DATA = HERE / "data"
SITE = HERE / "site"
EVIDENCE = HERE / "evidence"

REGISTRY = json.loads((ROOT / "research" / "sources.json").read_text())
IDS = {r["id"] for r in REGISTRY}
URLS = {r["id"]: r["url"] for r in REGISTRY}


def load(name):
    return json.loads((DATA / name).read_text())


class Artefacts(unittest.TestCase):
    def test_collect_reproduces(self):
        r = subprocess.run(["python", str(HERE / "collect.py"), "--check"], cwd=ROOT,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_build_reproduces(self):
        r = subprocess.run(["python", str(HERE / "build.py"), "--check"], cwd=ROOT,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_every_evidence_file_is_hashed(self):
        cap = load("captures.json")
        self.assertEqual(len(cap["evidence_sha256"]), len(list(EVIDENCE.glob("*.md"))))
        for name, digest in cap["evidence_sha256"].items():
            self.assertEqual(len(digest), 64, name)
            self.assertTrue((EVIDENCE / name).is_file(), name)


class Verification(unittest.TestCase):
    def setUp(self):
        self.ver = load("verification.json")

    def test_all_checks_pass(self):
        for c in self.ver["checks"]:
            self.assertEqual(c["status"], "pass", f"{c['id']}: {c['detail']}")

    def test_check_ids_are_v1_to_v8(self):
        self.assertEqual([c["id"] for c in self.ver["checks"]],
                         [f"V{i}" for i in range(1, 9)])

    def test_flags_carry_registered_sources(self):
        for f in self.ver["flags"]:
            self.assertTrue(f["sources"], f["id"])
            for s in f["sources"]:
                self.assertIn(s, IDS, f"{f['id']} cites unregistered source {s}")

    def test_monday_result_reconciles_independently(self):
        off = load("official-2026-11-18.json")
        mnf = off["week10_monday_result"]
        self.assertEqual((mnf["away"], mnf["away_score"], mnf["home"], mnf["home_score"]),
                         ("LAC", 23, "BAL", 20))
        with (ROOT / "data" / "nfl-standings-2026-11-17.csv").open(newline="") as fh:
            frozen = {r["Team"]: r for r in csv.DictReader(fh)}
        bal_before = frozen["Baltimore Ravens"]
        bal_after = next(s for s in off["standings"] if s["club"] == "Baltimore Ravens")
        lac_before = frozen["Los Angeles Chargers"]
        lac_after = next(s for s in off["standings"] if s["club"] == "Los Angeles Chargers")
        self.assertEqual(int(bal_after["l"]) - int(bal_before["L"]), 1)
        self.assertEqual(int(lac_after["w"]) - int(lac_before["W"]), 1)
        self.assertEqual(int(bal_after["pf"]) - int(bal_before["PF"]), 20)
        self.assertEqual(int(bal_after["pa"]) - int(bal_before["PA"]), 23)
        self.assertEqual(int(lac_after["pf"]) - int(lac_before["PF"]), 23)
        self.assertEqual(int(lac_after["pa"]) - int(lac_before["PA"]), 20)

    def test_points_close(self):
        off = load("official-2026-11-18.json")
        t = off["league_totals"]
        self.assertEqual(t["points_for"], t["points_against"])
        self.assertEqual(t["wins"], t["losses"])
        self.assertEqual(t["points_for"], t["corpus_points"] + 43)


class Venues(unittest.TestCase):
    def setUp(self):
        self.ven = load("venues.json")
        self.off = load("official-2026-11-18.json")

    def test_thirteen_venues_all_populated(self):
        self.assertEqual(len(self.ven["venues"]), 13)
        for v in self.ven["venues"]:
            self.assertTrue(v["location"].strip(), v["url"])
            self.assertTrue(v["stadium"].strip(), v["url"])
            self.assertTrue(v["network"].strip(), v["url"])

    def test_one_venue_per_fixture(self):
        urls = {f["url"] for f in self.off["week11_fixtures"]}
        self.assertEqual({v["url"] for v in self.ven["venues"]}, urls)

    def test_cross_check_covers_every_fixture(self):
        self.assertEqual(len(self.ven["cross_check"]), 13)
        for c in self.ven["cross_check"]:
            self.assertTrue(c["game_centre"].strip())
            self.assertTrue(c["fixture"].strip())

    def test_known_disagreements_are_recorded_not_resolved(self):
        diffs = {c["fixture"] for c in self.ven["cross_check"]
                 if not c["schedule_page"].startswith("(")
                 and re.sub(r"[^a-z0-9]", "", c["game_centre"].lower())
                 != re.sub(r"[^a-z0-9]", "", c["schedule_page"].lower())}
        self.assertEqual(diffs, {"Colts at Texans", "Cardinals at Chiefs",
                                 "Bengals at Commanders"})


class Availability(unittest.TestCase):
    def setUp(self):
        self.off = load("official-2026-11-18.json")

    def test_week11_report_is_absent(self):
        inj = self.off["week11_injury_report"]
        self.assertFalse(inj["published"])
        self.assertGreaterEqual(len(inj["reads"]), 3)
        for r in inj["reads"]:
            self.assertIn("Week 10", r["result"])

    def test_twelve_empty_modules_and_one_with_rows(self):
        ven = load("venues.json")
        states = [v["injury_module_state"] for v in ven["venues"]]
        self.assertEqual(states.count("empty"), 12)
        self.assertEqual(states.count("rows"), 1)

    def test_eight_player_rows_on_the_thursday_game_only(self):
        self.assertEqual(len(self.off["game_centre_players"]), 8)
        clubs = {p["club"] for p in self.off["game_centre_players"]}
        self.assertEqual(clubs, {"IND", "HOU"})

    def test_deltas_publish_a_direction_not_a_blank(self):
        for d in self.off["availability_deltas"]:
            self.assertTrue(d["delta"], d["player"])
            self.assertIn(d["delta"], {"unchanged", "not on the Week 10 report (new listing)"}
                          | {f"changed: {x} -> {d['week11_status']}" for x in
                             ("Did not participate", "Limited participation", "Full participation")})

    def test_empty_module_is_not_read_as_healthy(self):
        text = (SITE / "availability.html").read_text()
        self.assertIn("empty module rather than a clean bill of health", text)


class Pages(unittest.TestCase):
    pages = sorted(SITE.glob("*.html"))

    def test_ten_pages_built(self):
        self.assertEqual(len(self.pages), 10)

    def test_rows_carry_registered_sources_and_their_link(self):
        row_re = re.compile(r'<tr data-source-ids="([^"]*)">(.*?)</tr>', re.S)
        link_re = re.compile(r'<a href="(https://[^"]+)"')
        for path in self.pages:
            body = path.read_text()
            rows = row_re.findall(body)
            self.assertTrue(rows, f"{path.name}: no source-linked rows")
            for ids, inner in rows:
                names = ids.split()
                self.assertTrue(names, f"{path.name}: row without source ids")
                for n in names:
                    self.assertIn(n, IDS, f"{path.name}: unregistered source {n}")
                links = set(link_re.findall(inner))
                self.assertTrue(any(URLS[n] in links for n in names),
                                f"{path.name}: row lacks its official link")

    def test_every_cell_is_inside_a_td(self):
        # Text or links placed directly inside a <tr> is invalid table markup: browsers hoist it
        # out of the table, which both breaks the layout and fails the accessibility audit.
        for path in self.pages:
            body = path.read_text()
            self.assertIsNone(re.search(r'<tr data-source-ids="[^"]*">(?!<td)', body), path.name)
            for table_html in re.findall(r"<table>.*?</table>", body, re.S):
                heads = len(re.findall(r"<th ", table_html))
                for tr in re.findall(r"<tr data-source-ids=.*?</tr>", table_html, re.S):
                    self.assertEqual(len(re.findall(r"<td[ >]", tr)), heads,
                                     f"{path.name}: a row has a different cell count to its header")

    def test_blank_cells_are_truly_blank(self):
        for path in self.pages:
            for cell in re.findall(r'<td data-empty="true"[^>]*>(.*?)</td>', path.read_text(), re.S):
                self.assertEqual(cell.strip(), "", path.name)

    def test_no_price_odds_or_stake_values_are_published(self):
        # the lookbehind keeps hash names such as SHA-256 out of the price pattern
        banned = re.compile(r"(?<![\w-])(\$\s?\d|\u20ac\s?\d|\u00a3\s?\d|\+\d{3}|-\d{3})\b")
        banned = re.compile(banned.pattern + r"|(?<![\w.])\d\.\d{2}\s?x\b")
        for path in self.pages:
            hits = banned.findall(path.read_text())
            self.assertEqual(hits, [], f"{path.name}: {hits[:5]}")

    def test_external_links_are_safe(self):
        for path in self.pages:
            for tag in re.findall(r"<a [^>]*>", path.read_text()):
                if 'target="_blank"' in tag:
                    self.assertIn("noopener", tag, path.name)
                    self.assertIn("noreferrer", tag, path.name)


class Readiness(unittest.TestCase):
    def setUp(self):
        self.readi = load("readiness.json")

    def test_rows_are_complete(self):
        for r in self.readi["rows"]:
            for field in ("id", "requirement", "have", "blocking_gate",
                          "number_that_clears_it", "state"):
                self.assertTrue(str(r[field]).strip(), f"{r['id']}.{field}")
            self.assertIn(r["state"], {"clear", "blocked"}, r["id"])
            for s in r["source_ids"]:
                self.assertIn(s, IDS, f"{r['id']} cites unregistered source {s}")

    def test_every_row_names_the_number_that_clears_it(self):
        for r in self.readi["rows"]:
            self.assertTrue(re.search(r"\d", r["number_that_clears_it"]), r["id"])
            self.assertTrue(re.search(r"\d", r["have"]), r["id"])

    def test_clear_rows_are_the_verified_facts_only(self):
        clear = {r["id"] for r in self.readi["rows"] if r["state"] == "clear"}
        self.assertTrue({"W11-R01", "W11-R02", "W11-R03", "W11-R12"} <= clear)
        self.assertNotIn("W11-R05", clear)

    def test_readiness_table_is_on_the_landing_page(self):
        body = (SITE / "index.html").read_text()
        for r in self.readi["rows"]:
            self.assertIn(r["id"], body)
        self.assertIn("Decision readiness for Week 11", body)


class Decisions(unittest.TestCase):
    def setUp(self):
        self.dec = load("decisions.json")

    def test_questions_are_complete(self):
        self.assertGreaterEqual(len(self.dec["questions"]), 8)
        for q in self.dec["questions"]:
            for field in ("question", "we_hold", "what_is_missing", "how_to_discover",
                          "blocking_gate", "priority", "status"):
                self.assertTrue(str(q[field]).strip(), f"{q['id']}.{field}")
            for s in q["source_ids"]:
                self.assertIn(s, IDS, f"{q['id']} cites unregistered source {s}")

    def test_suggestions_are_complete_and_undecided(self):
        self.assertGreaterEqual(len(self.dec["suggestions"]), 8)
        for s in self.dec["suggestions"]:
            for field in ("title", "evidence", "cost", "risk", "acceptance_test"):
                self.assertTrue(str(s[field]).strip(), f"{s['id']}.{field}")
            self.assertEqual(s["decision"], "")
            for sid in s["source_ids"]:
                self.assertIn(sid, IDS, f"{s['id']} cites unregistered source {sid}")

    def test_each_suggestion_names_a_measurable_acceptance_test(self):
        for s in self.dec["suggestions"]:
            self.assertTrue(re.search(r"\d", s["acceptance_test"]),
                            f"{s['id']}: acceptance test has no number")


if __name__ == "__main__":
    unittest.main(verbosity=2)
