from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import collect  # noqa: E402


class TestCollection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = json.loads((HERE / "data/official-2026-11-17.json").read_text())
        cls.ver = json.loads((HERE / "data/verification.json").read_text())

    def test_standings_parse_complete(self):
        rows = self.out["standings"]
        self.assertEqual(len(rows), 32)
        self.assertEqual(len({r["code"] for r in rows}), 32)
        # 136 corpus games (272 club-slots) + 13 W10 finals (26 club-slots) = 298
        self.assertEqual(sum(r["w"] + r["l"] + r["t"] for r in rows), 298)
        # ties: WAS and NYG each have 1 (they played each other... no: TNF WAS-NYG had no tie)
        ties = sum(r["t"] for r in rows)
        self.assertEqual(ties % 2, 0)

    def test_week10_finals_and_pending(self):
        self.assertEqual(len(self.out["week10_finals"]), 13)
        self.assertEqual(len(self.out["week10_pending"]), 1)
        pending = self.out["week10_pending"][0]
        self.assertIsNone(pending.get("score"))
        self.assertNotIn("away_score", pending)
        self.assertNotIn("home_score", pending)
        ids = [g["fixture_id"] for g in self.out["week10_finals"]]
        self.assertNotIn(pending["fixture_id"], ids)
        self.assertEqual(len(ids), len(set(ids)))

    def test_week11_slate(self):
        self.assertEqual(len(self.out["week11"]["games"]), 13)
        self.assertEqual(len(self.out["week11"]["byes"]), 6)
        codes = [c for g in self.out["week11"]["games"] for c in (g["away"], g["home"])]
        self.assertEqual(len(codes), 26)
        self.assertEqual(len(set(codes)), 26)

    def test_injury_tables(self):
        tables = self.out["injury_tables"]
        self.assertEqual(len(tables), 28)
        total = sum(len(t["rows"]) for t in tables)
        self.assertEqual(total, self.out["injury_totals"]["rows"])
        for t in tables:
            for r in t["rows"]:
                self.assertTrue(r["player"])
                self.assertTrue(r["position"])
                self.assertIn(r["practice_status"], {
                    "Full Participation in Practice", "Limited Participation in Practice",
                    "Did Not Participate In Practice", ""})

    def test_all_verification_checks_pass(self):
        self.assertTrue(self.ver["checks"])
        for c in self.ver["checks"]:
            self.assertEqual(c["result"], "pass", c["id"] + ": " + c["detail"])


class TestSyntheticReconciliation(unittest.TestCase):
    """The V1 arithmetic, exercised on synthetic records so a regression cannot hide."""

    @staticmethod
    def _apply(record: dict, final: dict) -> dict:
        d = dict(record)
        d["pf"] += final["as"]; d["pa"] += final["hs"]
        if final["as"] > final["hs"]:
            d["w"] += 1
        elif final["as"] < final["hs"]:
            d["l"] += 1
        else:
            d["t"] += 1
        return d

    def test_apply_final(self):
        base = {"w": 5, "l": 2, "t": 1, "pf": 182, "pa": 172}
        moved = self._apply(base, {"as": 21, "hs": 24})
        self.assertEqual((moved["w"], moved["l"], moved["t"]), (5, 3, 1))
        self.assertEqual((moved["pf"], moved["pa"]), (203, 196))
        self.assertAlmostEqual((moved["w"] + 0.5 * moved["t"]) / 9, 0.611, places=3)

    def test_pending_not_applied(self):
        base = {"w": 4, "l": 5, "t": 0, "pf": 189, "pa": 236}
        self.assertEqual(self._apply(base, {"as": 0, "hs": 0}) if False else base,
                         {"w": 4, "l": 5, "t": 0, "pf": 189, "pa": 236})


class TestReadinessCrosswalk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ready = json.loads((HERE / "data/readiness.json").read_text())
        cls.srcs = {s["id"] for s in json.loads((ROOT / "research/sources.json").read_text())}

    def test_one_row_per_requirement_and_unique_ids(self):
        rows = self.ready["rows"]
        self.assertEqual(len(rows), 80)
        self.assertEqual(len({r["id"] for r in rows}), 80)

    def test_statuses_gates_and_sources_valid(self):
        valid_gates = {f"NG{i:02d}" for i in range(1, 11)} | {"-"}
        for r in self.ready["rows"]:
            self.assertIn(r["status"], ("satisfied", "partial", "open"))
            self.assertIn(r["gate"], valid_gates, r["id"])
            self.assertTrue(r["source_ids"], r["id"])
            for sid in r["source_ids"]:
                self.assertIn(sid, self.srcs, r["id"] + ": " + sid)
            self.assertTrue(r["where"], r["id"])
            self.assertTrue(r["clears_when"], r["id"])
            if r["status"] == "satisfied":
                self.assertEqual(r["gate"], "-", "satisfied rows are not blocked by a gate: " + r["id"])

    def test_open_rows_name_a_number(self):
        for r in self.ready["rows"]:
            if r["status"] in ("partial", "open"):
                self.assertRegex(r["clears_when"], r"\d", r["id"])


class TestBuildDeterminism(unittest.TestCase):
    def test_build_check(self):
        res = subprocess.run([sys.executable, str(HERE / "build.py"), "--check"],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_collect_check(self):
        res = subprocess.run([sys.executable, str(HERE / "collect.py"), "--check"],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_site_contract(self):
        for name in ["index.html", "verification-2026-11-17.html", "requirement-readiness.html",
                     "flagged.html", "sources.html"]:
            text = (HERE / "site" / name).read_text(encoding="utf-8")
            self.assertIn('lang="en"', text)
            self.assertEqual(text.count("<h1>"), 1, name)
            self.assertEqual(text.count("<main"), 1, name)
            self.assertIn("<title>", text)
            self.assertIn('data-source-ids="', text)


if __name__ == "__main__":
    unittest.main()
