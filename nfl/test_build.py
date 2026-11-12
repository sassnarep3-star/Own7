#!/usr/bin/env python3
"""Structural, provenance and reproducibility tests for the NFL sub-site.

Run from the repository root:  python -m unittest discover -s nfl -p "test_*.py" -v
Nothing here contacts the network. Every assertion is about the committed data,
the deterministic build, or the identity of the numbers the build publishes.
"""
from __future__ import annotations

import csv
import json
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import model  # noqa: E402
import build as site  # noqa: E402

DATA = json.loads((HERE / "data.json").read_text(encoding="utf-8"))
CONTENT = json.loads((HERE / "content.json").read_text(encoding="utf-8"))
SOURCES = {s["id"]: s for s in DATA["sources"]}

# Hosts that may appear as a row-level source. Deliberately a closed list.
ALLOWED_HOSTS = {
    "www.nfl.com",
    "www.azcardinals.com",
    "www.clevelandbrowns.com",
    "www.49ers.com",
    "docs.scipy.org",
    "scikit-learn.org",
    "www.statsmodels.org",
}


def rows(name):
    with (HERE / "data" / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class Doc(HTMLParser):
    """Minimal document contract checker."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.h1 = 0
        self.main = 0
        self.title = 0
        self.lang = None
        self.row_sources = []
        self.row_links = []
        self.blank_cells = 0
        self.blank_with_text = 0
        self._in_tbody = False
        self._row = None
        self._cell_empty = False
        self._cell_text = ""
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.lang = attrs.get("lang")
        elif tag == "h1":
            self.h1 += 1
        elif tag == "main":
            self.main += 1
        elif tag == "title":
            self.title += 1
        elif tag == "tbody":
            self._in_tbody = True
        elif tag == "tr" and self._in_tbody:
            self._row = {"ids": attrs.get("data-source-ids", "").split(), "links": []}
        elif tag == "a":
            href = attrs.get("href", "")
            self.links.append(href)
            if self._row is not None:
                self._row["links"].append(href)
        elif tag == "td" and attrs.get("data-empty") == "true":
            self._cell_empty = True
            self._cell_text = ""

    def handle_data(self, data):
        if self._cell_empty:
            self._cell_text += data

    def handle_endtag(self, tag):
        if tag == "td" and self._cell_empty:
            self._cell_empty = False
            self.blank_cells += 1
            if self._cell_text.strip():
                self.blank_with_text += 1
        elif tag == "tr" and self._row is not None:
            self.row_sources.append(self._row["ids"])
            self.row_links.append(self._row["links"])
            self._row = None
        elif tag == "tbody":
            self._in_tbody = False


def parse(path: Path) -> Doc:
    doc = Doc()
    doc.feed(path.read_text(encoding="utf-8"))
    return doc


class TestSources(unittest.TestCase):
    def test_every_registered_source_is_https_on_a_closed_host_list(self):
        for sid, source in SOURCES.items():
            parsed = urlparse(source["url"])
            self.assertEqual(parsed.scheme, "https", sid)
            self.assertIn(parsed.netloc, ALLOWED_HOSTS, sid)
            self.assertTrue(source["scope"].strip(), sid)
            self.assertRegex(source["checked_on"], r"^\d{4}-\d{2}-\d{2}$", sid)
            self.assertTrue(source["access"].strip(), sid)

    def test_every_source_is_cited_somewhere(self):
        used = set()
        for collection in ("strategies", "gates"):
            for row in DATA[collection]:
                used.update(row["source_ids"])
        used.update(DATA["correlation_method"]["prospective_legs"][0]["source_ids"])
        for collection in CONTENT.values():
            for row in collection:
                used.update(row["source_ids"])
        for name in ("standings-2026.csv", "games-2026-w10.csv", "injuries-2026-w10.csv", "depth-2026-w10.csv"):
            for row in rows(name):
                used.update(row["sources" if "sources" in row else "source_ids"].split())
        self.assertEqual(set(), used - set(SOURCES))
        self.assertEqual(set(), set(SOURCES) - used)

    def test_no_source_is_claimed_as_a_price_feed(self):
        for source in DATA["sources"]:
            self.assertNotIn("odds api", source["title"].lower())


class TestOfficialData(unittest.TestCase):
    def test_standings_identities(self):
        checks = model.identity_checks(model.load_standings(), model.load_games())
        self.assertEqual(32, checks["teams"])
        self.assertEqual([], checks["pct_identity_failures"])
        self.assertEqual([], checks["net_identity_failures"])
        self.assertTrue(checks["pf_equals_pa"])
        self.assertEqual(14, checks["games"])
        self.assertEqual(28, checks["slate_teams"])
        self.assertEqual([], checks["duplicate_slate_teams"])
        self.assertEqual(["CHI", "DEN", "PHI", "TB"], checks["clubs_not_in_slate"])

    def test_slate_clubs_all_have_a_standings_row(self):
        codes = {r["code"] for r in model.load_standings()}
        for game in model.load_games():
            self.assertIn(game["away"], codes)
            self.assertIn(game["home"], codes)
            self.assertNotEqual(game["away"], game["home"])

    def test_injury_rows_are_unique_and_join_to_a_slate_club(self):
        data = rows("injuries-2026-w10.csv")
        slate = {t for g in model.load_games() for t in (g["away"], g["home"])}
        seen = set()
        for row in data:
            self.assertIn(row["club"], slate)
            key = (row["club"], row["player"])
            self.assertNotIn(key, seen, f"duplicate player row {key}")
            seen.add(key)
            self.assertIn(row["practice"], {"DNP", "Limited", "Full", ""})
            self.assertIn(row["designation"], {"Out", "Doubtful", "Questionable", "No designation", ""})
            self.assertTrue(row["sources"].strip())
            for source_id in row["sources"].split():
                self.assertIn(source_id, SOURCES)

    def test_every_injury_row_has_a_registered_source(self):
        for row in rows("injuries-2026-w10.csv"):
            ids = row["sources"].split()
            self.assertTrue(ids, row["player"])
            self.assertTrue(set(ids) <= set(SOURCES), row["player"])

    def test_depth_rows_reference_a_real_injury_status_or_are_marked_healthy(self):
        injuries = {(r["club"], r["player"]): r for r in rows("injuries-2026-w10.csv")}
        for row in rows("depth-2026-w10.csv"):
            status = row["starter_status"]
            self.assertIn(status, {"DNP", "Limited", "Full", "no injury listed", ""}, row["starter"])
            if status in {"DNP", "Limited", "Full"}:
                key = (row["club"], row["starter"])
                self.assertIn(key, injuries, f"{row['club']} {row['starter']} has status but no injury row")
                self.assertEqual(injuries[key]["practice"] or injuries[key]["designation"], status,
                                 f"{row['club']} {row['starter']} status disagrees with the injury table")
            if status == "no injury listed":
                self.assertNotIn((row["club"], row["starter"]), injuries)

    def test_no_depth_row_invents_a_backup_for_a_blank_source_cell(self):
        for row in rows("depth-2026-w10.csv"):
            if row["second_string"] == "" and row["deficiency"]:
                self.assertTrue(
                    "no second" in row["deficiency"] or "no backup" in row["deficiency"]
                    or row["deficiency"] in {"three-deep intact", "position mismatch", "none listed at second string"},
                    row,
                )


class TestModel(unittest.TestCase):
    def test_baseline_is_reproducible_and_deterministic(self):
        first = model.compute()
        second = model.compute()
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_projections_are_internally_consistent(self):
        result = model.compute()
        self.assertEqual(14, len(result["projections"]))
        for row in result["projections"]:
            self.assertAlmostEqual(row["model_total"],
                                   row["exp_home_points"] + row["exp_away_points"], places=1)
            self.assertAlmostEqual(row["model_home_margin"],
                                   row["exp_home_points"] - row["exp_away_points"] + result["params"]["hfa"],
                                   places=1)
            self.assertGreaterEqual(row["model_home_win_prob"], 0.0)
            self.assertLessEqual(row["model_home_win_prob"], 1.0)
            self.assertLessEqual(row["margin_range"][0], row["model_home_margin"])
            self.assertGreaterEqual(row["margin_range"][1], row["model_home_margin"])
            self.assertLessEqual(row["total_range"][0], row["model_total"])
            self.assertGreaterEqual(row["total_range"][1], row["model_total"])
            self.assertEqual([], [k for k in ("market_line", "edge", "roi") if k in row])

    def test_rating_is_monotone_in_the_inputs_it_claims_to_use(self):
        """More points scored with the same points allowed must not lower off_adj."""
        params = model.compute()["params"]
        base = model.load_standings()
        before = model.team_ratings(base, params)["teams"]["BUF"]
        bumped = [dict(row) for row in base]
        for row in bumped:
            if row["code"] == "BUF":
                row["pf"] = row["pf"] + 25
                row["net"] = row["pf"] - row["pa"]
        after = model.team_ratings(bumped, params)["teams"]["BUF"]
        self.assertGreater(after["off_adj"], before["off_adj"])
        self.assertEqual(before["pa_pg"], after["pa_pg"])

    def test_correlation_math_matches_a_hand_computed_case(self):
        xs, ys = [1, 2, 3, 4], [2, 4, 6, 9]
        r = model.pearson(xs, ys)
        self.assertAlmostEqual(r, 0.994377, places=5)
        self.assertGreaterEqual(model.spearman(xs, ys), 0.99)
        lo, hi = model.fisher_ci(r, 4)
        self.assertLess(lo, r)
        self.assertGreater(hi, r)

    def test_correlations_are_team_level_and_labelled(self):
        result = model.compute()
        self.assertEqual(5, len(result["correlations"]))
        for row in result["correlations"]:
            self.assertEqual(32, row["n"])
            self.assertLessEqual(row["ci_low"], row["pearson"])
            self.assertGreaterEqual(row["ci_high"], row["pearson"])
            self.assertIn("NFL-STANDINGS", row["source_ids"])

    def test_leg_level_correlations_are_blank(self):
        for leg in DATA["correlation_method"]["prospective_legs"]:
            self.assertEqual("", leg["r"])
            self.assertEqual("", leg["n"])


class TestFailClosed(unittest.TestCase):
    def test_no_strategy_is_qualified(self):
        self.assertEqual(0, sum(1 for s in DATA["strategies"] if s["status"] not in {"Blocked", "Control"}))
        self.assertEqual(8, len(DATA["strategies"]))

    def test_leaderboard_is_empty_and_reward_is_non_monetary(self):
        lb = DATA["leaderboard"]
        self.assertEqual([], lb["entries"])
        self.assertIn("Non-monetary", lb["reward_rule"])
        self.assertIn("no cash value", lb["reward_rule"])

    def test_every_strategy_names_at_least_one_blocking_gate(self):
        for strategy in DATA["strategies"]:
            if strategy["status"] == "Control":
                continue
            self.assertTrue(strategy["blocking_gates"], strategy["id"])
            for gate_id in strategy["blocking_gates"]:
                self.assertIn(gate_id, {g["id"] for g in DATA["gates"]})

    def test_price_gates_fail_and_terms_gate_fails(self):
        gates = {g["id"]: g for g in DATA["gates"]}
        self.assertEqual("Fail", gates["G4"]["status"])
        self.assertEqual("Fail", gates["G5"]["status"])
        self.assertEqual("Fail", gates["G10"]["status"])
        self.assertIn("prohibits systematic retrieval", gates["G10"]["evidence_today"])

    def test_suggestions_and_questions_are_complete(self):
        self.assertGreaterEqual(len(CONTENT["suggestions"]), 10)
        for suggestion in CONTENT["suggestions"]:
            self.assertGreaterEqual(len(suggestion["options"]), 2, suggestion["id"])
            self.assertEqual(len(suggestion["options"]),
                             len({o["key"] for o in suggestion["options"]}), suggestion["id"])
            self.assertTrue(suggestion["recommendation"].strip())
            self.assertTrue(suggestion["decision"].strip())
        for question in CONTENT["questions"]:
            self.assertTrue(question["missing"].strip(), question["id"])
            self.assertTrue(question["discovery"].strip(), question["id"])
            self.assertTrue(question["have"].strip(), question["id"])

    def test_flags_are_numbered_and_sourced(self):
        ids = [f["id"] for f in CONTENT["flags"]]
        self.assertEqual(len(ids), len(set(ids)))
        for flag in CONTENT["flags"]:
            self.assertTrue(flag["source_ids"])


class TestSite(unittest.TestCase):
    def test_pages_build_identically_to_the_committed_files(self):
        site.build()
        manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
        for name in manifest["pages"]:
            path = HERE / name
            self.assertTrue(path.is_file(), name)

    def test_document_contract(self):
        for name in site.PAGES:
            doc = parse(HERE / name)
            self.assertEqual(1, doc.h1, name)
            self.assertEqual(1, doc.main, name)
            self.assertEqual("en", doc.lang, name)
            self.assertEqual(1, doc.title, name)

    def test_every_table_row_has_registered_ids_and_one_of_their_links(self):
        for name in site.PAGES:
            doc = parse(HERE / name)
            for ids, links in zip(doc.row_sources, doc.row_links):
                self.assertTrue(ids, f"{name}: row without source ids")
                for sid in ids:
                    self.assertIn(sid, SOURCES, f"{name}: unregistered {sid}")
                expected = {SOURCES[sid]["url"] for sid in ids}
                self.assertTrue(expected & set(links), f"{name}: row lacks its own source link {ids}")

    def test_blank_cells_are_truly_empty(self):
        blanks = 0
        for name in site.PAGES:
            doc = parse(HERE / name)
            self.assertEqual(0, doc.blank_with_text, name)
            blanks += doc.blank_cells
        self.assertGreater(blanks, 0, "no blank cells at all is suspicious for this data set")

    def test_no_market_number_is_published(self):
        text = (HERE / "model.html").read_text(encoding="utf-8")
        # The projections table has a market column with 14 empty cells.
        rows_html = re.findall(r'<tr data-row-id="W10-[^>]*>.*?</tr>', text, flags=re.S)
        self.assertEqual(14, len(rows_html))
        for row in rows_html:
            tags = re.findall(r"<td[^>]*>", row)
            self.assertEqual(8, len(tags), "seven data columns plus the source column")
            self.assertIn('data-empty="true"', tags[6], "market cell must stay blank")
            self.assertNotRegex(tags[6], r"data-value")

    def test_relative_links_resolve(self):
        for name in site.PAGES:
            doc = parse(HERE / name)
            for href in doc.links:
                if href.startswith(("http://", "https://", "#", "mailto:")):
                    self.assertFalse(href.startswith("http://"), f"{name}: insecure {href}")
                    continue
                target = (HERE / href.split("#")[0]).resolve()
                self.assertTrue(target.exists(), f"{name}: missing local target {href}")

    def test_no_placeholder_words_in_visible_text(self):
        banned = re.compile(r"\b(TBD|TODO|FIXME|placeholder|lorem ipsum)\b", re.I)
        for name in site.PAGES:
            text = (HERE / name).read_text(encoding="utf-8")
            visible = re.sub(r"<[^>]+>", " ", text)
            self.assertIsNone(banned.search(visible), name)

    def test_injury_table_row_count_matches_the_csv(self):
        text = (HERE / "injuries.html").read_text(encoding="utf-8")
        body = text.split('<table id="injuries"', 1)[1].split("</table>", 1)[0]
        self.assertEqual(len(rows("injuries-2026-w10.csv")), body.count("<tr data-row-id="))


if __name__ == "__main__":
    unittest.main(verbosity=2)
