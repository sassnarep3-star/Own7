"""Tests for the decision-ledger re-grade audit (session arena/aedccbe5-own7).

Run from the repository root:  python -m unittest discover -s nfl-ledger-aedccbe5/tests -v
"""
import hashlib
import importlib.util
import json
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent
spec = importlib.util.spec_from_file_location("ledger_build", HERE / "build.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)

DATA = json.loads((HERE / "data" / "ledger-audit.json").read_text(encoding="utf-8"))
REGISTER = json.loads((ROOT / "research" / "nfl-decision-readiness.json").read_text(encoding="utf-8"))
SOURCES = {s["id"]: s for s in json.loads((ROOT / "research" / "sources.json").read_text(encoding="utf-8"))}


class RegisterTests(unittest.TestCase):
    def test_register_has_70_unique_rows(self):
        ids = [r["id"] for r in REGISTER["requirements"]]
        self.assertEqual(len(ids), 70)
        self.assertEqual(len(set(ids)), 70)
        self.assertEqual(DATA["counts"]["rows"], 70)

    def test_every_artifact_exists_and_every_source_resolves(self):
        for r in DATA["rows"]:
            self.assertTrue(r["artifact_exists"], r["id"])
            self.assertEqual(r["unresolved_source_ids"], [], r["id"])
            self.assertTrue(r["artifact_sha256"], r["id"])

    def test_official_link_is_registered_and_non_repository(self):
        for r in DATA["rows"]:
            if r["official_url"]:
                self.assertIn(r["official_source_id"], SOURCES)
                self.assertEqual(SOURCES[r["official_source_id"]]["url"], r["official_url"])
                self.assertNotIn("github.com", r["official_url"])
            else:
                self.assertTrue(r["repo_only"], r["id"])
        self.assertEqual(DATA["counts"]["official_link"] + DATA["counts"]["repo_only"], 70)

    def test_repo_only_rows_are_exactly_the_process_rows(self):
        repo_only = sorted(r["id"] for r in DATA["rows"] if r["repo_only"])
        self.assertEqual(repo_only, ["DR-08", "DR-09", "DR-17", "DR-37", "DR-39", "DR-47",
                                     "DR-50", "DR-57", "DR-63", "DR-65", "DR-67", "DR-69"])


class RegradeEvidenceTests(unittest.TestCase):
    def test_every_proposed_regrade_quote_is_found_in_its_artifact(self):
        for g in DATA["regrades"]:
            if g["id"] == "DR-22":
                continue  # counted from the landing page, tested separately
            text = B.read_text(ROOT / g["evidence"])
            self.assertIsNotNone(B.first_hit(text, next(x["pattern"] for x in B.REGRADES if x["id"] == g["id"])), g["id"])
            self.assertIn(g["quote"].strip("…").split(" …")[0][:40], text.replace("…", ""), g["id"])

    def test_regrades_change_only_the_status_they_name(self):
        ids = {g["id"]: g for g in DATA["regrades"]}
        self.assertEqual(sorted(ids), ["DR-22", "DR-61", "DR-64", "DR-68"])
        reg = {r["id"]: r for r in REGISTER["requirements"]}
        for rid, g in ids.items():
            self.assertEqual(reg[rid]["status"], g["ledger_status"])
            self.assertEqual(g["proposed"], "Partial")
        self.assertEqual(DATA["counts"]["regrades"], 4)

    def test_landing_table_is_not_the_register(self):
        self.assertEqual(DATA["landing_table_rows"], 16)
        self.assertEqual(DATA["landing_table_ids"], [f"NR{i:02d}" for i in range(1, 17)])
        self.assertNotEqual(DATA["landing_table_rows"], len(REGISTER["requirements"]))

    def test_blocked_gates_match_official_reads_and_hashes(self):
        for b in DATA["blocked_checks"]:
            path = ROOT / b["evidence"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), b["evidence_sha256"], b["id"])
            self.assertIsNotNone(re.search(r"Systematic retrieval|404 - Flag on the Play", path.read_text(encoding="utf-8")))
        self.assertEqual({b["id"] for b in DATA["blocked_checks"]}, {"DR-01", "DR-18", "DR-29", "DR-54", "DR-66"})

    def test_evidence_files_match_their_recorded_hashes(self):
        lines = (HERE / "evidence" / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        for line in lines:
            digest, name = line.split(maxsplit=1)
            self.assertEqual(hashlib.sha256((HERE / "evidence" / name).read_bytes()).hexdigest(), digest, name)


class PageTests(unittest.TestCase):
    def test_every_register_row_appears_on_the_ledger_page(self):
        html = (HERE / "site" / "ledger.html").read_text(encoding="utf-8")
        for r in REGISTER["requirements"]:
            self.assertIn(f">{r['id']}<", html, r["id"])

    def test_every_table_row_names_registered_sources_and_links_one(self):
        for name in ["ledger.html", "regrades.html", "blocked.html", "flagged.html", "index.html"]:
            html = (HERE / "site" / name).read_text(encoding="utf-8")
            for tr in re.findall(r"<tbody>(.*?)</tbody>", html, flags=re.S):
                for row in re.findall(r"<tr[^>]*>.*?</tr>", tr, flags=re.S):
                    m = re.search(r'data-source-ids="([^"]+)"', row)
                    self.assertIsNotNone(m, f"{name}: row without data-source-ids")
                    ids = m.group(1).split()
                    self.assertTrue(all(i in SOURCES for i in ids), name)
                    self.assertTrue(any(SOURCES[i]["url"] in row for i in ids), f"{name}: no registered link")

    def test_no_monetary_figures_are_published(self):
        for p in (HERE / "site").glob("*.html"):
            self.assertNotIn("$", p.read_text(encoding="utf-8"), p.name)

    def test_build_reproduces_byte_identically(self):
        self.assertEqual(B.write_all(check=True), 0)


if __name__ == "__main__":
    unittest.main()
