"""Tests for the brief tracker (session arena/77b177da-own7). Run: python -m unittest discover -s nfl-brief-77b1/tests"""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import checks as C  # noqa: E402
import content as T  # noqa: E402


class EvidenceReceipts(unittest.TestCase):
    def test_evidence_tables_parse_with_fixed_widths(self):
        self.assertEqual(len(C.parse_md_table(HERE / "evidence/nfl-transactions-2026-11.md")), 12)
        self.assertEqual(len(C.parse_md_table(HERE / "evidence/nfl-reserve-list-2026-11.md")), 25)
        self.assertEqual(len(C.parse_md_table(HERE / "evidence/nfl-injuries-2026-11-17.md")), 9)

    def test_receipts_cover_every_evidence_file(self):
        self.assertEqual(len(C.receipts()), len(list((HERE / "evidence").glob("*.md"))))


class StaleDepth(unittest.TestCase):
    def test_henley_is_the_only_stale_row(self):
        stale = [r for r in C.stale_depth_check() if r["class"] == "STALE"]
        self.assertEqual([r["name"] for r in stale], ["Daiyan Henley"])

    def test_every_trade_is_classified(self):
        classes = {r["class"] for r in C.stale_depth_check()}
        self.assertLessEqual(classes, {"STALE", "PRINTED NEW", "NOT PRINTED", "NO CHART"})


class LionsCheck(unittest.TestCase):
    def test_availability_desk_matches_official_page(self):
        self.assertTrue(C.lions_check()["nfl-availability-28ef (Week 10, 14 games)"]["matches_official"])

    def test_files_without_detroit_rows_are_out_of_scope_not_mismatched(self):
        res = C.lions_check()
        self.assertIsNone(res["data/ Week 7"]["matches_official"])


def _facts():
    import build as B
    return B.facts()


class RegisterContract(unittest.TestCase):
    def test_every_cited_repository_path_exists(self):
        keys = [f[2] for f in T.FLAGS] + [f[3] for f in T.FLAGS] + [q[2] for q in T.QUESTIONS]
        for key in keys:
            if key.startswith("repo:"):
                self.assertTrue((HERE.parent / key[5:]).exists(), key)

    def test_register_rows_have_unique_ids(self):
        ids = [r["id"] for r in T.register(_facts())]
        self.assertEqual(len(ids), len(set(ids)))

    def test_flags_do_not_block_and_have_status(self):
        self.assertTrue(all(f[4] for f in T.FLAGS))
        self.assertEqual(len({f[0] for f in T.FLAGS}), len(T.FLAGS))

    def test_suggestions_leave_owner_decision_blank(self):
        html = (HERE / "site/suggestions.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('<td data-empty="true"></td>'), len(T.SUGGESTIONS))

    def test_no_row_without_registered_source(self):
        registry = {r["id"] for r in json.loads((HERE.parent / "research/sources.json").read_text(encoding="utf-8"))}
        for page in (HERE / "site").glob("*.html"):
            for ids in re.findall(r'<tr data-source-ids="([^"]*)"', page.read_text(encoding="utf-8")):
                self.assertTrue(ids.strip(), f"{page.name}: row without source IDs")
                for sid in ids.split():
                    self.assertIn(sid, registry, f"{page.name}: unknown source {sid}")


if __name__ == "__main__":
    unittest.main()
