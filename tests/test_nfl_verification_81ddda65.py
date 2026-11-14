"""Tests for the independent NFL re-verification (session arena/81ddda65-own7).

The verifier compares committed NFL CSVs against freshly retrieved official
NFL.com evidence. Every mismatch observed on 2026-11-14 is explained by the
single 2026-11-12 Commanders-Giants TNF result that the committed snapshot
predates. This test enforces that claim: injuries must be exact, and every
non-injury mismatch must be confined to the TNF-affected keys. Any mismatch on
an unaffected key fails the test, so a genuine transcription error cannot hide
behind the known divergence.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import verify_nfl_81ddda65 as V  # noqa: E402

# Keys that are legitimately divergent because the snapshot predates the
# 2026-11-12 Commanders-Giants TNF result.
TNF_AFFECTED = {
    "New York Giants", "Washington Commanders",
    "Jayden Daniels", "Michael Penix Jr.", "Cam Ward", "Sam Darnold",
}


class TestNflReVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = V.run_all()

    def test_injuries_exact(self):
        self.assertEqual(self.results["injuries"], [],
                         "Week-10 Thursday injury block must match the official report exactly")

    def test_no_unexplained_mismatches(self):
        unexplained = []
        for name, mism in self.results.items():
            for m in mism:
                if not any(key in m for key in TNF_AFFECTED):
                    unexplained.append(f"{name}: {m}")
        self.assertEqual(unexplained, [],
                         "Mismatches outside the known TNF time-stamp divergence:\n"
                         + "\n".join(unexplained))

    def test_standings_divergence_is_tnf_only(self):
        # Standings mismatches must mention Giants/Commanders only.
        for m in self.results["standings"]:
            self.assertTrue(("Giants" in m) or ("Commanders" in m), m)

    def test_player_ranking_divergence(self):
        # The player divergence is exactly: Cam Ward / Sam Darnold ranks and
        # Michael Penix Jr. presence (Jayden Daniels absent from committed).
        player_mismatches = self.results["player_passing"]
        self.assertTrue(player_mismatches, "expected the known player ranking divergence")
        joined = " ".join(player_mismatches)
        self.assertIn("Michael Penix Jr.", joined)

    def test_evidence_file_present_and_dated(self):
        ev = V.load_evidence()
        self.assertEqual(ev["retrieved_on"], "2026-11-14")
        self.assertEqual(len(ev["standings"]), 32)
        self.assertEqual(len(ev["team_defense_passing"]), 32)
        self.assertEqual(len(ev["team_offense_passing"]), 32)
        self.assertEqual(len(ev["player_passing"]), 25)
        self.assertEqual(len(ev["injuries_thursday_tnf"]), 20)

    def test_terms_section_1_3(self):
        ev = V.load_evidence()
        text = ev["terms"]["section_1_3"]
        self.assertIn("non-commercial and informational purposes", text)
        self.assertIn("Systematic retrieval", text)


if __name__ == "__main__":
    unittest.main()
