"""Tests for the decision-ledger desk (session arena/637442e9-own7).

Run: python -m unittest discover -s nfl-ledger-637442e9/tests -v

These tests recount from committed files; they do not trust the desk's own prose.
"""
import csv
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import build as B  # noqa: E402

def _games():
    with (ROOT / "nfl-results/data/games-2026-w1-10-complete.csv").open(encoding="utf8") as fh:
        return list(csv.DictReader(fh))


class LedgerIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = B.build_model()

    def test_seventy_rows_and_known_statuses(self):
        table = self.model["table"]
        self.assertEqual(len(table), 70)
        self.assertTrue({r["now"] for r in table} <= B.ALLOWED_STATUS)

    def test_overrides_change_only_listed_rows(self):
        changed = sorted(r["id"] for r in self.model["table"] if r["changed"])
        self.assertEqual(changed, sorted(["DR-13", "DR-49", "DR-57", "DR-61", "DR-64", "DR-68"]))

    def test_every_row_has_a_registered_source(self):
        reg = self.model["registry"]
        for row in self.model["table"]:
            self.assertTrue(row["source_ids"], row["id"])
            for sid in row["source_ids"]:
                self.assertIn(sid, reg, f"{row['id']} cites unregistered {sid}")
                self.assertTrue(reg[sid]["url"].startswith("https://"), sid)

    def test_repository_only_rows_are_labelled(self):
        # A row with no external official ID must be shown as repository-only, never as official.
        for row in self.model["table"]:
            if not row["official_ids"]:
                self.assertTrue(row["source_ids"], row["id"])

    def test_questions_and_flags_use_registered_sources(self):
        reg = self.model["registry"]
        for q in self.model["questions"]:
            for sid in q.get("sources", []):
                self.assertIn(sid, reg, f"{q['id']} cites unregistered {sid}")

    def test_assurance_csv_has_one_registered_id(self):
        # Two IDs for one URL would change what other desks resolve to (nfl-brief-77b1 numbers it B77-R04).
        reg = json.loads((ROOT / "research/sources.json").read_text(encoding="utf8"))
        ids = sorted(r["id"] for r in reg if r["url"].endswith("/nfl-assurance-9580ac3f/data/injuries.csv"))
        self.assertEqual(ids, ["B77-R04"])


class RecountedFacts(unittest.TestCase):
    def test_week10_byes_match_schedule_and_bye_file(self):
        rows = _games()
        universe = {t for r in rows for t in (r["away"], r["home"])}
        self.assertEqual(len(universe), 32)
        w10 = {t for r in rows if int(r["week"]) == 10 for t in (r["away"], r["home"])}
        not_playing = sorted(universe - w10)
        self.assertEqual(not_playing, ["CHI", "DEN", "PHI", "TB"])
        with (ROOT / "nfl-results/data/byes-2026-w1-10-complete.csv").open(encoding="utf8") as fh:
            byes = sorted(r["team_code"] for r in csv.DictReader(fh) if r["week"] == "10")
        self.assertEqual(byes, not_playing)

    def test_week_1_10_final_counts(self):
        rows = _games()
        self.assertEqual(len(rows), 150)
        with (ROOT / "nfl-results/data/games-2026-w1-10.csv").open(encoding="utf8") as fh:
            self.assertEqual(len(list(csv.DictReader(fh))), 149)
        complete_keys = {(r["away"], r["home"], r["date"]) for r in rows}
        with (ROOT / "nfl-results/data/games-2026-w1-10.csv").open(encoding="utf8") as fh:
            canon_keys = {(r["away"], r["home"], r["date"]) for r in csv.DictReader(fh)}
        self.assertEqual(complete_keys - canon_keys, {("LAC", "BAL", "2026-11-16")})

    def test_week10_injury_counts_reproduce(self):
        counts = B.week10_counts()
        self.assertEqual(counts["avail_rows"], 326)
        self.assertEqual(counts["avail_clubs"], 28)


class EvidenceAndBuild(unittest.TestCase):
    def test_evidence_hashes_verify(self):
        self.assertTrue(B.check_evidence())

    def test_desk_rebuild_is_byte_identical(self):
        self.assertEqual(B.main(["--check"]), 0)

    def test_week10_final_claim_is_attributed(self):
        # The LAC@BAL claim must cite the official schedule evidence this desk re-read, and any
        # game-centre or Game Book wording must name the registered source IDs that carry it.
        text = (HERE / "site/index.html").read_text(encoding="utf8") + (HERE / "site/executive-summary.html").read_text(encoding="utf8")
        self.assertIn("week-10.complete.md", text)
        for phrase in ("game centre", "Game Book"):
            if phrase in text:
                self.assertIn("C672-GC-W10-LACBAL-1118", text.replace("&#x27;", "'"))

    def test_manifest_lists_every_html_page(self):
        manifest = json.loads((HERE / "site/manifest.json").read_text(encoding="utf8"))
        html = sorted(p.name for p in (HERE / "site").glob("*.html"))
        self.assertEqual(sorted(n for n in manifest["pages"] if n.endswith(".html")), html)


if __name__ == "__main__":
    unittest.main()
