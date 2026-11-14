"""Tests for the consolidated NFL decision dossier (session arena/81ddda65-own7).

Validates that the dossier consolidates the three registers, that every question
carries a group/question, that the blocking set is exactly M01-M04, and that the
NF16 duplication is recorded with a cross-map.
"""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER = os.path.join(ROOT, "research", "nfl", "decision-dossier-81ddda65.json")


class TestDecisionDossier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DOSSIER, encoding="utf-8") as f:
            cls.d = json.load(f)

    def test_registers_audited(self):
        regs = self.d["registers_audited"]
        self.assertEqual(len(regs), 3)
        files = {r["file"] for r in regs}
        self.assertIn("research/nfl/decisions.json", files)
        self.assertIn("research/nfl/questions.json", files)
        self.assertIn("research/nfl-suggestions.json", files)

    def test_questions_complete(self):
        qs = self.d["questions_to_answer_before_any_decision"]
        self.assertEqual(len(qs), 17)
        ids = [q["id"] for q in qs]
        self.assertEqual(ids, [f"DQ{i:02d}" for i in range(1, 18)])
        for q in qs:
            self.assertTrue(q["group"], f"{q['id']} missing group")
            self.assertTrue(q["question"], f"{q['id']} missing question text")

    def test_known_and_missing_counts(self):
        self.assertEqual(len(self.d["information_held"]), 10)
        self.assertEqual(len(self.d["information_missing"]), 10)
        known_ids = [k["id"] for k in self.d["information_held"]]
        missing_ids = [m["id"] for m in self.d["information_missing"]]
        self.assertEqual(known_ids, [f"K{i:02d}" for i in range(1, 11)])
        self.assertEqual(missing_ids, [f"M{i:02d}" for i in range(1, 11)])

    def test_blocking_is_m01_m04(self):
        self.assertEqual(self.d["blocking_before_any_reward"],
                         ["M01", "M02", "M03", "M04"])

    def test_every_missing_maps_to_a_suggestion(self):
        sug_ids = {s["id"] for s in self.d["suggestions_to_discover_missing_information"]}
        for m in self.d["information_missing"]:
            if m["suggestion"]:
                self.assertIn(m["suggestion"], sug_ids,
                              f"{m['id']} references unknown suggestion {m['suggestion']}")

    def test_nf16_recorded(self):
        nf16 = self.d["irregularity_NF16"]
        self.assertIn("S01-S10", nf16["summary"])
        self.assertIn("SU-01", nf16["summary"])
        self.assertEqual(self.d["canonical_register"], "research/nfl/decisions.json")
        # every SU maps to an S or 'new'
        for su, s in nf16["cross_map_su_to_s"].items():
            self.assertTrue(s.startswith("S") or s == "new", f"{su} -> {s}")

    def test_review_workflow_states(self):
        states = self.d["review_workflow"]["states"]
        self.assertEqual(states, ["Proposed", "Under review", "Approved", "Rejected", "Implemented"])


if __name__ == "__main__":
    unittest.main()
