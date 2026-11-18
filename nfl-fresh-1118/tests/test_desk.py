"""Tests for the fresh-read desk (session arena/92cad499-own7).

The desk's own build.py re-derives every number from committed artefacts and aborts
on mismatch; these tests pin the contracts that keep it honest: frozen artefacts
untouched, provenance per row, scheduled fixtures never results, and pages that
carry only registered sources.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent.parent


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class FrozenArtefacts(unittest.TestCase):
    def test_frozen_2026_11_17_feed_is_unchanged(self):
        games = read_csv(ROOT / "nfl-results/data/games-2026-w1-10.csv")
        self.assertEqual(len(games), 149)
        w10 = [g for g in games if g["week"] == "10"]
        self.assertEqual(len(w10), 13)
        self.assertTrue(all(g["retrieved"] == "2026-11-17" for g in w10))
        self.assertTrue(all(g["source_url"] == "https://www.nfl.com/schedules/2026/REG10"
                            for g in w10))
        sched = read_csv(ROOT / "nfl-results/data/scheduled-2026-w10.csv")
        self.assertEqual([(r["away"], r["home"]) for r in sched], [("LAC", "BAL")])

    def test_completed_feed_has_150_finals_and_correct_provenance(self):
        games = read_csv(ROOT / "nfl-results/data/games-2026-w1-10-complete.csv")
        self.assertEqual(len(games), 150)
        added = [g for g in games if g["source_url"] == "https://www.nfl.com/schedules/2026/by-week/week-10"]
        self.assertEqual(len(added), 1)
        row = added[0]
        self.assertEqual((row["away"], row["home"], int(row["away_score"]), int(row["home_score"])),
                         ("LAC", "BAL", 23, 20))
        self.assertEqual(row["retrieved"], "2026-11-18")
        self.assertEqual(row["evidence"], "nfl-results/evidence/week-10.complete.md")
        for g in games:
            self.assertIn(g["evidence"].split("/")[-1],
                          {"week-10.schedule.md", "week-10.complete.md"} |
                          {f"week-{n}.schedule.md" for n in range(1, 10)})

    def test_weeks_11_12_never_enter_the_results_feed(self):
        games = read_csv(ROOT / "nfl-results/data/games-2026-w1-10-complete.csv")
        self.assertEqual({g["week"] for g in games}, {str(n) for n in range(1, 11)})
        for name, expected in (("scheduled-2026-w11.csv", 13), ("scheduled-2026-w12.csv", 16)):
            rows = read_csv(ROOT / f"nfl-results/data/{name}")
            self.assertEqual(len(rows), expected)
            for r in rows:
                self.assertTrue(r["kickoff"], "a scheduled fixture must carry a kickoff time")
                self.assertNotIn("FINAL", r["evidence"])

    def test_snapshot_chain_holds_on_the_re_read(self):
        """Independently re-derive the 1118 snapshot from 1117 + the completion final."""
        s1117 = {r["Team"]: r for r in read_csv(ROOT / "data/nfl-standings-2026-11-17.csv")}
        s1118 = {r["Team"]: r for r in read_csv(ROOT / "data/nfl-standings-2026-11-18.csv")}
        self.assertEqual(len(s1117), 32)
        self.assertEqual(len(s1118), 32)
        games = read_csv(ROOT / "nfl-results/data/games-2026-w1-10-complete.csv")
        delta = {}
        for g in games:
            if g["retrieved"] != "2026-11-18":
                continue
            a, h = int(g["away_score"]), int(g["home_score"])
            for club, scored, allowed in ((g["away"], a, h), (g["home"], h, a)):
                delta[club] = (int(scored > allowed), int(scored < allowed),
                               int(scored == allowed), scored, allowed)
        checked = 0
        for team, row in s1118.items():
            code = {"Arizona Cardinals": "AZ", "Atlanta Falcons": "ATL",
                    "Baltimore Ravens": "BAL", "Buffalo Bills": "BUF",
                    "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
                    "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE",
                    "Dallas Cowboys": "DAL", "Denver Broncos": "DEN",
                    "Detroit Lions": "DET", "Green Bay Packers": "GB",
                    "Houston Texans": "HOU", "Indianapolis Colts": "IND",
                    "Jacksonville Jaguars": "JAX", "Kansas City Chiefs": "KC",
                    "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC",
                    "Los Angeles Rams": "LA", "Miami Dolphins": "MIA",
                    "Minnesota Vikings": "MIN", "New England Patriots": "NE",
                    "New Orleans Saints": "NO", "New York Giants": "NYG",
                    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI",
                    "Pittsburgh Steelers": "PIT", "San Francisco 49ers": "SF",
                    "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB",
                    "Tennessee Titans": "TEN", "Washington Commanders": "WAS"}[team]
            d = delta.get(code, (0, 0, 0, 0, 0))
            for field, col in zip(d, ("W", "L", "T", "PF", "PA")):
                self.assertEqual(int(s1117[team][col]) + field, int(row[col]),
                                 f"{team}: {col} chain identity broke")
                checked += 1
        self.assertEqual(checked, 160)


class DeskPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((HERE / "site" / "manifest.json").read_text(encoding="utf-8"))
        for page in cls.manifest["pages"]:
            if not (HERE / "site" / page).exists():
                raise AssertionError(f"missing desk page {page}")

    def test_build_reproduces_byte_identically(self):
        proc = subprocess.run([sys.executable, str(HERE / "build.py"), "--check"],
                              capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_every_page_row_carries_a_registered_source(self):
        registry = {r["id"] for r in json.loads(
            (ROOT / "research" / "sources.json").read_text(encoding="utf-8"))}
        desk_ids = set(self.manifest["source_ids"])
        self.assertTrue(desk_ids <= registry,
                        f"desk source ids not registered: {desk_ids - registry}")
        for page in self.manifest["pages"]:
            text = (HERE / "site" / page).read_text(encoding="utf-8")
            self.assertIn("<tbody>", text, f"{page} has no data table")
            self.assertIn('data-source-ids="', text, f"{page} rows lack source ids")
            for chunk in text.split('data-source-ids="')[1:]:
                sid = chunk.split('"')[0]
                self.assertTrue(sid, f"{page}: empty source id")
                self.assertTrue(sid.split() and all(s in registry for s in sid.split()),
                                f"{page}: unregistered source id {sid}")

    def test_no_market_values_anywhere(self):
        for page in self.manifest["pages"]:
            text = (HERE / "site" / page).read_text(encoding="utf-8").lower()
            for banned in ("closing line", "roi", "clv", "stake", "bankroll"):
                self.assertNotIn(banned, text, f"{page} mentions {banned}")

    def test_flagged_page_publishes_the_partial_capture(self):
        text = (HERE / "site" / "flagged.html").read_text(encoding="utf-8")
        self.assertIn("FF01", text)
        self.assertIn("chunks 4-7 were not", text)
        self.assertIn("delta is published", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
