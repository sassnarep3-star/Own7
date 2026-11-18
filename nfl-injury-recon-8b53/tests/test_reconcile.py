"""Checks for the Patriots-Lions reconciliation desk. Run: python -m unittest discover -s nfl-injury-recon-8b53/tests"""
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

DESK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DESK))
import build  # noqa: E402


class ReconcileTests(unittest.TestCase):
    def test_official_block_has_24_rows_15_ne_9_det(self):
        rows = build.parse_official()
        self.assertEqual(len(rows), 24)
        self.assertEqual(sum(r["club"] == "NE" for r in rows), 15)
        self.assertEqual(sum(r["club"] == "DET" for r in rows), 9)

    def test_evidence_hash_matches_recorded_sha256(self):
        sums = (DESK / "evidence" / "SHA256SUMS.txt").read_text().split()
        recorded = sums[0]
        actual = hashlib.sha256(build.EVIDENCE.read_bytes()).hexdigest()
        self.assertEqual(recorded, actual)

    def test_every_official_row_is_compared_with_both_desks(self):
        rows = build.build_rows()
        for r in rows:
            self.assertIn(r["a_verdict"], {"agree", "differs"})
            self.assertIn(r["b_verdict"], {"agree", "differs"})

    def test_lions_out_rows_are_out_on_official_page(self):
        rows = {r["player"]: r for r in build.parse_official()}
        for name in ("Kerby Joseph", "Cade Mays", "D.J. Reed"):
            self.assertEqual(rows[name]["game"], "Out")
        self.assertEqual(rows["Kerby Joseph"]["practice"], "Did Not Participate In Practice")

    def test_desk_b_lions_blanks_are_reported_not_filled(self):
        summ = build.summary(build.build_rows())
        self.assertEqual(sorted(summ["desk_b_out_blank_on_official"]),
                         ["Cade Mays", "D.J. Reed", "Kerby Joseph"])

    def test_rendered_rows_each_link_to_the_official_page(self):
        html = build.outputs()[build.ROOT / "site" / "index.html"]
        tbody = html.split("<tbody>")[1].split("</tbody>")[0]
        trs = re.findall(r"<tr[^>]*>.*?</tr>", tbody, re.S)
        self.assertEqual(len(trs), 24)
        for tr in trs:
            self.assertIn(build.OFFICIAL_URL, tr)

    def test_summary_counts_are_consistent(self):
        out = build.outputs()
        summ = json.loads(out[build.ROOT / "data" / "summary.json"])
        self.assertEqual(summ["desk_a"]["rows_agree"] + summ["desk_a"]["rows_differ"], 24)
        self.assertEqual(summ["desk_b"]["rows_agree"] + summ["desk_b"]["rows_differ"], 24)

    def test_build_is_deterministic(self):
        self.assertEqual(build.outputs(), build.outputs())


if __name__ == "__main__":
    unittest.main()
