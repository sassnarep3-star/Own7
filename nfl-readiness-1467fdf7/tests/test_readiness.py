"""Tests for the decision-readiness desk. Run: python -m unittest discover -s nfl-readiness-1467fdf7/tests -v"""
import hashlib
import json
import re
import sys
import unittest
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
import controls  # noqa: E402
import injury_check  # noqa: E402
import requirements as REQ  # noqa: E402
import strategies as REG  # noqa: E402


class RequirementRegister(unittest.TestCase):
    def test_status_vocabulary_and_unique_ids(self):
        ids = [r["id"] for r in REQ.R]
        self.assertEqual(len(ids), len(set(ids)))
        for r in REQ.R:
            self.assertIn(r["status"], REQ.STATUSES, r["id"])

    def test_every_row_has_gate_clears_and_current(self):
        for r in REQ.R:
            for k in ("text", "gate", "clears", "current"):
                self.assertTrue(r[k].strip(), f'{r["id"]} empty {k}')
            # Evidence may be blank only when the row is flagged; a blank never points at this register.
            if not r["evidence"].strip():
                self.assertTrue(r["flags"], f'{r["id"]} has no evidence and no flag')
            self.assertNotIn("nfl-readiness-1467fdf7/requirements.py", r["evidence"], r["id"])

    def test_official_links_are_nfl_com_only(self):
        for r in REQ.R:
            for u in r["official"]:
                self.assertTrue(u.startswith("https://www.nfl.com/"), f'{r["id"]} {u}')

    def test_rejected_rows_are_marked_as_brief_rejections(self):
        rej = [r["id"] for r in REQ.R if r["status"].startswith("Rejected")]
        self.assertEqual(rej, ["D02", "F03"])

    def test_no_row_claims_built_without_evidence(self):
        for r in REQ.R:
            if r["status"] in ("Built", "Built here"):
                self.assertTrue(r["evidence"], r["id"])


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = controls.build()
        cls.games = controls.load_games()

    def test_universe_and_tie_exclusion(self):
        self.assertEqual(self.c["universe"]["games"], 136)
        self.assertEqual(self.c["universe"]["graded_straight_up"], 135)
        ties = self.c["universe"]["ties_excluded"]
        self.assertEqual(len(ties), 1)
        self.assertEqual((ties[0]["week"], ties[0]["score"]), (5, "NYG 27 - WAS 27"))

    def test_record_pick_uses_only_earlier_weeks(self):
        # Removing every game from the pick week or later must not change any C-REC pick.
        for row in self.c["rows"]:
            earlier = [g for g in self.games if g["week"] < row["week"]]
            rh = controls.record_before(earlier, row["home"], row["week"])
            ra = controls.record_before(earlier, row["away"], row["week"])
            if rh is None and ra is None:
                pick = row["home"]
            elif ra is None:
                pick = row["home"]
            elif rh is None:
                pick = row["away"]
            else:
                pick = row["away"] if ra > rh else row["home"]
            self.assertEqual(pick, row["C-REC"], (row["week"], row["home"], row["away"]))

    def test_week_one_has_no_prior_record(self):
        for row in self.c["rows"]:
            if row["week"] == 1:
                self.assertIsNone(row["rec_pct_home"])
                self.assertEqual(row["C-REC"], row["home"])

    def test_gates_match_preregistration(self):
        g = self.c["gates"]
        for cid in ("C-RAND", "C-HOME", "C-REC"):
            self.assertFalse(g[cid]["G3_sample"], cid)  # n = 135 < 153
        self.assertFalse(g["C-REC"]["G4_beats_chance_band"])
        self.assertTrue(g["C-REC"]["G_margin_vs_C-HOME"])

    def test_chance_band_is_reproducible(self):
        a = controls.random_band(
            [r for r in self.c["rows"] if r["graded"]], REG.RANDOM_SEED, 2000)
        b = controls.random_band(
            [r for r in self.c["rows"] if r["graded"]], REG.RANDOM_SEED, 2000)
        self.assertEqual(a, b)

    def test_stored_file_matches_fresh_build(self):
        stored = (HERE / "data" / "controls.json").read_text(encoding="utf-8")
        self.assertEqual(stored, controls.to_text(self.c))

    def test_wilson_interval_bounds(self):
        lo, hi = controls.wilson(0, 10)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0)
        lo, hi = controls.wilson(5, 10)
        self.assertLess(lo, 0.5)
        self.assertGreater(hi, 0.5)


class Injury(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = injury_check.build_result()

    def test_evidence_hash_matches_saved_text(self):
        raw = injury_check.EVIDENCE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), self.r["evidence_sha256"])

    def test_counts_for_complete_clubs(self):
        self.assertEqual(self.r["official_rows_parsed"], 50)
        self.assertEqual(self.r["rows_compared"], 44)
        self.assertEqual(sorted(self.r["complete_clubs_compared"]), ["DET", "NE", "NYG", "WAS"])
        self.assertEqual(self.r["official_rows_missing_from_desk"], [])

    def test_known_disagreements_are_reported_not_corrected(self):
        bad = {x["player"]: x["mismatch_fields"] for x in self.r["rows"] if x["mismatch_fields"]}
        self.assertEqual(bad, {
            "Kerby Joseph": ["practice"],
            "Amon-Ra St. Brown": ["injury", "game_status"],
            "Sione Vaki": ["injury", "practice", "game_status"],
        })
        # the desk file itself must be untouched by this desk
        desk = (REPO / "nfl-availability-28ef/data/injuries-week10-2026.csv").read_text(encoding="utf-8")
        self.assertIn("Kerby Joseph", desk)

    def test_kc_is_not_compared(self):
        self.assertTrue(any("KC" in x for x in self.r["not_compared"]))


class Pages(unittest.TestCase):
    def test_no_unfilled_placeholders(self):
        for p in (HERE / "site").glob("*.html"):
            self.assertIsNone(re.search(r"\{[a-z_]+\}", p.read_text(encoding="utf-8")), p.name)

    def test_relative_links_resolve(self):
        bad = []
        for p in (HERE / "site").glob("*.html"):
            t = p.read_text(encoding="utf-8")
            for href in re.findall(r'href="([^"]+)"', t):
                if href.startswith(("http", "#", "mailto")):
                    continue
                target = (p.parent / href.split("#")[0]).resolve()
                if not target.exists():
                    bad.append((p.name, href))
        self.assertEqual(bad, [])

    def test_every_readiness_row_has_official_link_or_is_marked_internal(self):
        t = (HERE / "site" / "index.html").read_text(encoding="utf-8")
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t)
        ready = [r for r in rows if "Gate that blocks it" not in r and re.search(r"<td>[A-G]\d\d</td>", r)]
        self.assertEqual(len(ready), len(REQ.R))
        for r in ready:
            self.assertTrue("nfl.com" in r or "none (internal)" in r, r[:120])

    def test_every_row_is_tagged_with_registered_ids(self):
        import build as B
        for name in ("index.html", "controls.html", "strategies.html", "injury-check.html", "flagged.html", "sources.html"):
            t = (HERE / "site" / name).read_text(encoding="utf-8")
            for ids in re.findall(r'<tr data-source-ids="([^"]*)">', t):
                parts = ids.split()
                self.assertTrue(parts, name)
                for sid in parts:
                    self.assertIn(sid, B.REGISTRY, name)

    def test_flags_have_evidence_and_status(self):
        flags = json.loads((HERE / "data" / "flags.json").read_text(encoding="utf-8"))
        self.assertEqual(len(flags), 20)
        for f in flags:
            self.assertTrue(f["evidence"], f["id"])
            self.assertTrue(f["close"], f["id"])


class Strategies(unittest.TestCase):
    def test_every_entry_has_both_sides(self):
        for s in REG.STRATEGIES:
            self.assertTrue(s["confirm"].strip(), s["id"])
            self.assertTrue(s["refute"].strip(), s["id"])

    def test_no_reward_or_roi_field(self):
        for s in REG.STRATEGIES:
            self.assertFalse({"reward", "roi", "stake"} & set(s), s["id"])

    def test_registered_gate_ids_are_complete(self):
        self.assertEqual([g["id"] for g in REG.GATES], [f"G{i}" for i in range(1, 8)])


if __name__ == "__main__":
    unittest.main()
