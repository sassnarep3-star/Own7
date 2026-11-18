"""Unit tests for the fresh-reads desk (session arena/6c72a9fa-own7)."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
DATA = HERE / "data"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


class DeskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = load("official-2026-11-18.json")
        cls.ver = load("verification.json")
        cls.chg = load("whatchanged.json")
        cls.srcs = {s["id"] for s in json.loads(
            (ROOT / "research" / "sources.json").read_text(encoding="utf-8"))}

    def test_standings_fully_verified(self):
        self.assertEqual(len(self.out["standings"]), 32)
        self.assertEqual(self.ver["V1_standings"]["failed"], 0)
        self.assertEqual(self.ver["V1b_frozen_plus_14_finals"]["failed"], 0)

    def test_only_bal_lac_moved(self):
        moved = [r for r in self.chg["standings_2026_11_17_to_2026_11_18"] if r["changed"]]
        self.assertEqual({r["code"] for r in moved}, {"BAL", "LAC"})
        bal = next(r for r in moved if r["code"] == "BAL")
        lac = next(r for r in moved if r["code"] == "LAC")
        self.assertEqual((bal["dW"], bal["dL"], bal["dPF"], bal["dPA"]), (0, 1, 20, 23))
        self.assertEqual((lac["dW"], lac["dL"], lac["dPF"], lac["dPA"]), (1, 0, 23, 20))

    def test_final_join(self):
        fin = self.out["week10_pending_final"]
        self.assertEqual((fin["away"], fin["home"], fin["away_score"], fin["home_score"], fin["state"]),
                         ("LAC", "BAL", 23, 20, "Final"))
        gb = self.out["gamebook_14"]
        self.assertEqual(gb["source"], fin["gamebook_url"])
        self.assertTrue(gb["source"].startswith("https://static.www.nfl.com/"))

    def test_week11_slate_completes_32(self):
        fxs = self.out["week11_fixtures"]
        self.assertEqual(len(fxs), 13)
        codes = [CLUB for f in fxs for CLUB in (f["away_code"], f["home_code"])]
        self.assertEqual(len(codes), 26)
        self.assertEqual(len(set(codes)), 26)
        byes = {b["code"] for b in self.out["week11_byes"]}
        self.assertEqual(len(byes), 6)
        all_codes = {r["code"] for r in self.out["standings"]}
        self.assertEqual(byes | set(codes), all_codes)
        self.assertEqual(byes & set(codes), set())
        for f in fxs:
            self.assertTrue(f["venue"], f"fixture {f['slot']} has no venue")

    def test_reserve_series_delta(self):
        s = self.chg["reserve_series"]
        self.assertEqual(len(s["added"]), 8)
        self.assertEqual({a[1] for a in s["added"]}, {"11/17"})
        self.assertEqual(len(s["scrolled_off"]), 8)
        nov_names = {r["name"] for r in self.out["reserve_november"]}
        self.assertIn("Malik Willis", nov_names)
        self.assertNotIn("Lamar Jackson", nov_names)
        oct_names = {r["name"] for r in self.out["reserve_october"]}
        self.assertNotIn("Lamar Jackson", oct_names)
        self.assertNotIn("Tyler Huntley", oct_names | nov_names)
        # every scrolled-off row must exist verbatim in the committed 2026-11-17 capture
        prev_text = (ROOT / "nfl-brief-77b1" / "evidence" / "nfl-reserve-list-2026-11.md").read_text(encoding="utf-8")
        for code, date, name in s["scrolled_off"]:
            self.assertIn(name, prev_text, name)

    def test_gamebook_counts(self):
        gb = self.out["gamebook_14"]
        self.assertEqual((len(gb["off"]), len(gb["def"]), len(gb["ina"])), (22, 22, 12))
        self.assertEqual({r["player"] for r in gb["off"] if r["pos"] == "QB"}, {"J.Herbert", "J.Brissett"})
        self.assertEqual(gb["game"]["attendance"], "69,679")
        self.assertEqual(gb["game"]["stadium"], "M&T Bank Stadium")
        self.assertEqual(gb["game"]["id"], "W10-14")

    def test_venue_completion_14_of_14(self):
        self.assertEqual(self.ver["V5_venue_completion"]["week10_venues"], 14)
        self.assertEqual(self.ver["V5_venue_completion"]["of"], 14)

    def test_injuries_stable(self):
        v8 = self.ver["V8_injuries_state"]
        self.assertEqual(v8["diffs"], 0)
        self.assertEqual(v8["rows_compared"], 50)
        self.assertIn("Week 10", v8["title"])
        sched = self.chg["week11_schedule_2026_11_17_to_2026_11_18"]
        self.assertTrue(sched["stable"])
        self.assertEqual(sched["fixtures_compared"], 13)

    def test_every_flag_names_registered_source(self):
        sys.path.insert(0, str(HERE))
        import build  # noqa: plc0415 — desk build module
        self.assertEqual(len(build.FLAGS), 7)
        for fid, _, _, where, _, _ in build.FLAGS:
            self.assertIn(where, {n for n, _ in build.PAGES}, fid)
        for sid in build.REG_URLS:
            self.assertIn(sid, self.srcs, sid)

    def test_build_reproduces_byte_identically(self):
        r = subprocess.run([sys.executable, str(HERE / "build.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
