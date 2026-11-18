"""Unit tests for the nfl-slate-03dcea07 desk.

The tests import the desk's build module, re-run its parses and checks, and assert
the no-inference contract: blanks stay blank, no price/stake/reward field exists, and
every published table row carries a registered official source id.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = ROOT.parent

_spec = importlib.util.spec_from_file_location("slate_build", ROOT / "build.py")
build = importlib.util.module_from_spec(_spec)
sys.modules["slate_build"] = build
_spec.loader.exec_module(build)


class ParseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fresh = build.parse_standings("standings-2026-11-18.md")
        cls.final14 = build.parse_week10_schedule()
        cls.byes = build.parse_byes()
        cls.gb = build.parse_gamebook()
        cls.rules = build.parse_rules()

    def test_standings_32_clubs_canonical_set(self):
        self.assertEqual(len(self.fresh), 32)
        self.assertEqual(set(self.fresh), set(build.AFC) | set(build.NFC))

    def test_standings_arithmetic(self):
        for c, r in self.fresh.items():
            self.assertEqual(r["net"], r["pf"] - r["pa"], c)
            self.assertEqual(r["pct"], build.pct_str(r["w"], r["l"], r["t"]), c)

    def test_lac_bal_final_recorded(self):
        f = next(x for x in self.final14 if x["away"] == "LAC" and x["home"] == "BAL")
        self.assertEqual((f["as"], f["hs"]), (23, 20))

    def test_slate_covers_32_clubs_once(self):
        slate = [f["away"] for f in self.final14] + [f["home"] for f in self.final14] + self.byes
        self.assertEqual(sorted(slate), sorted(build.AFC + build.NFC))

    def test_gamebook_structure(self):
        self.assertEqual(len(self.gb["lineups"]), 44)
        self.assertEqual(sum(1 for x in self.gb["lineups"] if x["club"] == "LAC"), 22)
        self.assertEqual(sum(1 for x in self.gb["inactives"] if x["club"] == "BAL"), 6)
        self.assertEqual(self.gb["stadium"], "M&T Bank Stadium")
        self.assertEqual(self.gb["away_quarters"][-1], 23)
        self.assertEqual(self.gb["home_quarters"][-1], 20)
        self.assertEqual(sum(self.gb["away_quarters"][:4]), 23)

    def test_rules_verbatim_onside_text(self):
        r616 = next(r for r in self.rules if r["article"] == "6-1-6")
        self.assertEqual(
            r616["description"],
            "Permits the kicking team to declare an onside kick at any time during the game.")
        self.assertEqual(len(self.rules), 4)


class ReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fresh = build.parse_standings("standings-2026-11-18.md")
        cls.frozen = build.load_frozen()
        cls.nov17 = build.load_nov17(build.load_name_map())
        cls.divisions = build.load_divisions(build.load_name_map())
        cls.final14 = build.parse_week10_schedule()
        corpus, sched = build.load_corpus_w10()
        cls.corpus, cls.sched = corpus, sched

    def test_corpus_shape(self):
        full = build.read_repo_csv("nfl-results/data/games-2026-w1-10.csv")
        self.assertEqual(len(full), 149)  # weeks 1-10 with 13 Week 10 finals
        self.assertEqual(len(self.corpus), 13)  # this desk loads the Week 10 finals only
        self.assertEqual([(r["away"], r["home"]) for r in self.sched], [("LAC", "BAL")])

    def test_frozen_plus_week10_equals_fresh(self):
        w10 = list(self.corpus) + [{"away": "LAC", "home": "BAL",
                                    "away_score": "23", "home_score": "20"}]
        derived = build.derived_view(build.apply_finals(self.frozen, w10, self.divisions))
        for c in self.fresh:
            for k in ("w", "l", "t", "pct", "pf", "pa", "net", "home", "road"):
                self.assertEqual(str(derived[c][k]), str(self.fresh[c][k]), f"{c}.{k}")

    def test_nov17_plus_monday_equals_fresh(self):
        derived = build.derived_view(build.apply_finals(
            self.nov17, [{"away": "LAC", "home": "BAL",
                          "away_score": "23", "home_score": "20"}], self.divisions))
        for c in self.fresh:
            for k in ("w", "l", "t", "pct", "pf", "pa", "net", "home", "road", "div", "conf"):
                self.assertEqual(str(derived[c][k]), str(self.fresh[c][k]), f"{c}.{k}")
        self.assertEqual(build.streak_after(self.nov17["LAC"]["streak"], True, False),
                         self.fresh["LAC"]["streak"])
        self.assertEqual(build.streak_after(self.nov17["BAL"]["streak"], False, True),
                         self.fresh["BAL"]["streak"])

    def test_full_check_suite_passes(self):
        checks, _ = build.run_checks(
            self.fresh, self.frozen, self.nov17, self.divisions, self.final14,
            self.corpus, self.sched, build.parse_gamebook(), build.parse_byes(),
            build.parse_rules())
        self.assertEqual(len(checks), 9)
        for c in checks:
            self.assertEqual(c["result"], "pass", c["id"] + ": " + c["detail"])


class OutputContractTests(unittest.TestCase):
    """The generated desk must honour the repository's publication contract."""

    @classmethod
    def setUpClass(cls):
        # regenerate data + site deterministically (build was already run by CI/build_site)
        cls.fresh = build.parse_standings("standings-2026-11-18.md")
        cls.final14 = build.parse_week10_schedule()
        corpus, sched = build.load_corpus_w10()
        frozen = build.load_frozen()
        nov17 = build.load_nov17(build.load_name_map())
        divisions = build.load_divisions(build.load_name_map())
        checks, diffs = build.run_checks(
            cls.fresh, frozen, nov17, divisions, cls.final14, corpus, sched,
            build.parse_gamebook(), build.parse_byes(), build.parse_rules())
        build.build_data(cls.fresh, diffs, build.parse_gamebook(), build.parse_rules(), checks)
        cls.pages = build.build_site(cls.fresh, diffs, build.parse_gamebook(),
                                     build.parse_rules(), checks, build.parse_byes(),
                                     cls.final14)

    def test_no_price_stake_reward_field_anywhere(self):
        forbidden = ("decimal odds", "american odds", "stake", "wager", "roi", "clv",
                     "bankroll", "cash reward", "price")
        # the only legitimate occurrence is the desk's own negation disclaimer
        disclaimers = ("no price, stake, wager, reward or betting recommendation",
                       "no wager, stake, bankroll, price or monetary reward")
        import re as _re
        blob = " ".join(html.lower() for _, html in self.pages)
        blob = _re.sub(r"\s+", " ", blob)
        for d in disclaimers:
            blob = blob.replace(d, "")
        for word in forbidden:
            self.assertIsNone(_re.search(rf"\b{_re.escape(word)}\b", blob),
                              f"forbidden token {word!r} on desk pages")
        # and the data artefacts must not carry any such column or value either
        for name in ("standings-2026-11-18.csv", "standings-diff-frozen-2026-11-12_to_2026-11-18.csv",
                     "standings-diff-2026-11-17_to_2026-11-18.csv", "gamebook-w10-14-lac-bal.csv",
                     "lineups-w10-14.csv", "inactives-w10-14.csv", "rules-2026-changes.csv"):
            text = (build.DATA / name).read_text(encoding="utf-8").lower()
            for word in forbidden:
                self.assertIsNone(_re.search(rf"\b{_re.escape(word)}\b", text),
                                  f"{name}: forbidden token {word!r}")
        for name in ("verification.json", "flags.json"):
            text = (build.DATA / name).read_text(encoding="utf-8").lower()
            for word in forbidden:
                self.assertIsNone(_re.search(rf"\b{_re.escape(word)}\b", text),
                                  f"{name}: forbidden token {word!r}")

    def test_every_tbody_row_cites_registered_sources_and_links_them(self):
        registry = {r["id"]: r["url"] for r in json.loads(
            (REPO / "research" / "sources.json").read_text(encoding="utf-8"))}
        import html.parser

        class Rows(html.parser.HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.rows, self.cur, self.in_body = [], None, False

            def handle_starttag(self, tag, attrs):
                a = dict(attrs)
                if tag == "tbody":
                    self.in_body = True
                if tag == "tr" and self.in_body:
                    self.cur = {"ids": a.get("data-source-ids", "").split(), "refs": []}
                if tag == "a" and self.cur is not None:
                    self.cur["refs"].append(a.get("href"))

            def handle_endtag(self, tag):
                if tag == "tr" and self.cur is not None:
                    self.rows.append(self.cur)
                    self.cur = None
                if tag == "tbody":
                    self.in_body = False

        for name, html_text in self.pages:
            if not name.endswith(".html"):
                continue
            p = Rows()
            p.feed(html_text)
            self.assertTrue(p.rows, name)
            for r in p.rows:
                self.assertTrue(r["ids"], f"{name}: row without data-source-ids")
                for sid in r["ids"]:
                    self.assertIn(sid, registry, f"{name}: unregistered source id {sid}")
                self.assertTrue(any(registry.get(s) in r["refs"] for s in r["ids"]),
                                f"{name}: row lacks its official registered source link")

    def test_generated_csvs_exist_and_are_deterministic(self):
        for name in ("standings-2026-11-18.csv", "standings-diff-frozen-2026-11-12_to_2026-11-18.csv",
                     "standings-diff-2026-11-17_to_2026-11-18.csv", "gamebook-w10-14-lac-bal.csv",
                     "lineups-w10-14.csv", "inactives-w10-14.csv", "rules-2026-changes.csv",
                     "verification.json", "flags.json"):
            self.assertTrue((build.DATA / name).exists(), name)
        with (build.DATA / "standings-2026-11-18.csv").open() as fh:
            rows = list(csv.reader(fh))
        self.assertEqual(len(rows), 33)  # header + 32 clubs
        with (build.DATA / "lineups-w10-14.csv").open() as fh:
            self.assertEqual(len(list(csv.reader(fh))), 45)  # header + 44 starters

    def test_diff_rows_blanks_stay_blank_for_unplayed(self):
        with (build.DATA / "standings-diff-2026-11-17_to_2026-11-18.csv").open() as fh:
            rows = list(csv.DictReader(fh))
        moved = [r for r in rows if r["Week10"] != "no game"]
        self.assertEqual({r["Code"] for r in moved}, {"LAC", "BAL"})


if __name__ == "__main__":
    unittest.main()
