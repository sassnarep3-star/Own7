#!/usr/bin/env python3
"""Unit tests for the Week-11 decision desk (nfl-week11-4c7d).

Every assertion is against a value computed from the retained official evidence, never
against a number typed in by hand. Run with:
    python -m unittest discover -s nfl-week11-4c7d/tests -v
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESK = HERE.parent
REPO = DESK.parent
sys.path.insert(0, str(DESK))

import build as desk  # noqa: E402

DATA = DESK / "data"
EVIDENCE = DESK / "evidence"
SITE = DESK / "site"


def rows(name: str) -> list[dict]:
    with (DATA / name).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


class EvidenceTests(unittest.TestCase):
    def test_every_evidence_file_is_hashed_and_unchanged(self):
        sums = (EVIDENCE / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
        checked = 0
        for line in sums:
            digest, name = line.split()
            path = EVIDENCE / name
            self.assertTrue(path.is_file(), f"missing evidence {name}")
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest,
                             f"evidence {name} changed without re-hashing")
            checked += 1
        self.assertGreaterEqual(checked, 5)

    def test_evidence_states_its_source_and_read_method(self):
        for path in sorted(EVIDENCE.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            self.assertTrue("https://www.nfl.com" in text or "https://static.www.nfl.com" in text,
                            f"{path.name}: no official source url")
            self.assertIn("READ_UTC_DATE|2026-11-18", text, f"{path.name}: no read date")

    def test_raw_gamebook_retained_with_source(self):
        text = (DESK / "raw" / "g14-LAC-BAL.txt").read_text(encoding="utf-8")
        self.assertIn("SOURCE|https://static.www.nfl.com/", text)
        self.assertIn("CAPTURED_UTC|2026-11-18", text)


class StandingsTests(unittest.TestCase):
    def setUp(self):
        self.rows = rows("standings-reconciliation.csv")

    def test_all_32_clubs_and_no_mismatch(self):
        self.assertEqual(len(self.rows), 32)
        bad = [r["club"] for r in self.rows if r["all_seven_fields_match"] != "yes"]
        self.assertEqual(bad, [])

    def test_only_the_two_clubs_that_played_carry_a_result(self):
        applied = {r["club"] for r in self.rows if r["mnf_result_applies"].startswith("yes")}
        self.assertEqual(applied, {"Los Angeles Chargers", "Baltimore Ravens"})

    def test_the_monday_result_moves_only_those_two_clubs(self):
        by_club = {r["club"]: r for r in self.rows}
        lac, bal = by_club["Los Angeles Chargers"], by_club["Baltimore Ravens"]
        self.assertEqual(int(lac["read_2026_11_18_W"]) - int(lac["snapshot_W"]), 1)
        self.assertEqual(int(bal["read_2026_11_18_L"]) - int(bal["snapshot_L"]), 1)
        self.assertEqual(int(lac["read_2026_11_18_PF"]) - int(lac["snapshot_PF"]), 23)
        self.assertEqual(int(lac["read_2026_11_18_PA"]) - int(lac["snapshot_PA"]), 20)
        self.assertEqual(int(bal["read_2026_11_18_PF"]) - int(bal["snapshot_PF"]), 20)
        self.assertEqual(int(bal["read_2026_11_18_PA"]) - int(bal["snapshot_PA"]), 23)
        for club, row in by_club.items():
            if club in ("Los Angeles Chargers", "Baltimore Ravens"):
                continue
            self.assertEqual(row["read_2026_11_18_W"], row["snapshot_W"], club)
            self.assertEqual(row["read_2026_11_18_PF"], row["snapshot_PF"], club)

    def test_percentage_is_recomputed_not_copied(self):
        for row in self.rows:
            self.assertEqual(row["expected_PCT"], desk.pct(int(row["expected_W"]),
                                                           int(row["expected_L"]),
                                                           int(row["expected_T"])))
            self.assertEqual(row["read_2026_11_18_PCT"], row["expected_PCT"])


class FixtureTests(unittest.TestCase):
    def test_thirteen_fixtures_and_six_byes_cover_the_league(self):
        games, byes = rows("fixtures-week11.csv"), rows("byes-week11.csv")
        self.assertEqual(len(games), 13)
        self.assertEqual(len(byes), 6)
        clubs = [c for g in games for c in (g["away"], g["home"])] + [b["club"] for b in byes]
        self.assertEqual(len(set(clubs)), 32)
        self.assertEqual(len(clubs), 32)

    def test_no_fixture_is_marked_played(self):
        for game in rows("fixtures-week11.csv"):
            self.assertIn("not yet played", game["status"])

    def test_kickoff_timezone_is_blank_not_assumed(self):
        for game in rows("fixtures-week11.csv"):
            self.assertIn("not printed", game["kickoff_timezone"])


class GameBookTests(unittest.TestCase):
    def test_week_ten_is_closed(self):
        closure = rows("week10-gamebook-closure.csv")
        self.assertEqual(len(closure), 14)
        clubs = {c for r in closure for c in (r["away"], r["home"])}
        self.assertEqual(len(clubs), 28)

    def test_every_game_carries_venue_roof_and_attendance(self):
        for row in rows("week10-gamebook-closure.csv"):
            for field in ("stadium", "city", "roof_and_surface", "attendance"):
                self.assertTrue(row[field].strip(), f"{row['game_id']} missing {field}")

    def test_weather_is_blank_for_exactly_the_two_games_with_none_printed(self):
        closure = rows("week10-gamebook-closure.csv")
        without = sorted(r["game_id"] for r in closure if not r["weather"].strip())
        self.assertEqual(without, ["W10-04", "W10-08"])
        self.assertEqual(sum(1 for r in closure if r["weather"].strip()), 12)
        by_id = {r["game_id"]: r for r in closure}
        self.assertIn("Retractable Roof - Closed", by_id["W10-04"]["roof_and_surface"])
        self.assertIn("Closed Stadium", by_id["W10-08"]["roof_and_surface"])

    def test_official_status_counts_for_the_monday_game(self):
        people = rows("mnf-lineups-and-inactives.csv")
        counts = {}
        for person in people:
            counts[person["status"]] = counts.get(person["status"], 0) + 1
        self.assertEqual(counts["Official starter (offence)"], 22)
        self.assertEqual(counts["Official starter (defence)"], 22)
        self.assertEqual(counts["Official Not Active"], 12)
        self.assertEqual(counts["Dressed but Did Not Play"], 5)


class JoinTests(unittest.TestCase):
    def setUp(self):
        self.join = rows("availability-delta-mnf.csv")

    def test_twenty_nine_rows_from_two_clubs(self):
        self.assertEqual(len(self.join), 29)
        self.assertEqual({r["club"] for r in self.join}, {"LAC", "BAL"})

    def test_designation_counts(self):
        counts = {}
        for r in self.join:
            counts[r["designation"]] = counts.get(r["designation"], 0) + 1
        self.assertEqual(counts["Out"], 4)
        self.assertEqual(counts["Questionable"], 7)
        self.assertEqual(counts["Doubtful"], 1)
        self.assertEqual(counts["(none published)"], 17)

    def test_the_official_not_active_outcomes(self):
        deactivated = [r for r in self.join
                       if r["outcome_from_gamebook"].startswith("deactivated")]
        self.assertEqual(len(deactivated), 7)
        for r in deactivated:
            self.assertIn(r["player"].split()[-1],
                          ("McConkey", "Williamson", "Waxter", "Dupree", "Thompson",
                           "Eboigbe", "Hawkins"))

    def test_suffix_and_initial_handling(self):
        self.assertEqual(desk.surname("Carlton Davis III"), "davis")
        self.assertEqual(desk.surname("Anthony Hill Jr."), "hill")
        self.assertEqual(desk.surname("A.Kaliakmanis"), "kaliakmanis")
        self.assertEqual(desk.initial("A.J. Brown"), "a")
        self.assertEqual(desk.initial("Ben Brown"), "b")
        self.assertNotEqual(desk.join_key("NE", "A.J. Brown"), desk.join_key("NE", "Ben Brown"))


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.rows = rows("designation-reliability.csv")

    def test_sample_sizes_and_totals(self):
        total = sum(int(r["n_rows_joined"]) for r in self.rows)
        self.assertEqual(total, 329)
        by = {r["published_designation"]: r for r in self.rows}
        self.assertEqual(int(by["Out"]["n_rows_joined"]), 18)
        self.assertEqual(int(by["Out"]["n_on_official_not_active"]), 13)
        self.assertEqual(int(by["Questionable"]["n_rows_joined"]), 18)
        self.assertEqual(int(by["Questionable"]["n_on_official_not_active"]), 5)

    def test_intervals_are_valid_and_bracket_the_rate(self):
        for r in self.rows:
            n, k = int(r["n_rows_joined"]), int(r["n_on_official_not_active"])
            low, high = float(r["wilson_95_low"]), float(r["wilson_95_high"])
            self.assertGreaterEqual(low, 0.0)
            self.assertLessEqual(high, 1.0)
            self.assertLess(low, high)
            self.assertAlmostEqual(float(r["observed_inactive_rate"]), k / n, places=4)
            self.assertLessEqual(low, k / n + 1e-9)
            self.assertGreaterEqual(high, k / n - 1e-9)

    def test_nothing_is_declared_usable_on_one_season(self):
        for r in self.rows:
            if int(r["n_rows_joined"]) < 200:
                self.assertIn("no", r["usable_as_model_feature"])


class CoverageTests(unittest.TestCase):
    def test_the_reserve_gap_is_measured(self):
        coverage = rows("inactive-coverage.csv")
        total = coverage[-1]
        self.assertEqual(int(total["official_not_active_count"]), 158)
        self.assertEqual(int(total["absent_from_the_report"]), 86)
        self.assertEqual(int(total["matched_to_a_report_row"]), 72)
        self.assertEqual(total["share_absent"], "0.5443")

    def test_every_game_row_adds_up(self):
        for r in rows("inactive-coverage.csv"):
            self.assertEqual(int(r["official_not_active_count"]),
                             int(r["matched_to_a_report_row"]) + int(r["absent_from_the_report"]))


class ProbeTests(unittest.TestCase):
    def test_six_probes_each_with_a_verdict(self):
        probes = rows("source-probes.csv")
        self.assertEqual(len(probes), 6)
        for probe in probes:
            self.assertTrue(probe["question"].strip())
            url = probe["url"]
            self.assertTrue(url.startswith("https://") or url.endswith("(read-only)"),
                            f"{probe['probe_id']}: url is neither an https link nor a noted "
                            "repository path")
            self.assertTrue(probe["verdict"].strip())
            self.assertEqual(probe["read_utc"], "2026-11-18")

    def test_snap_count_probes_conclude_none_found(self):
        verdicts = " ".join(p["verdict"] for p in rows("source-probes.csv")
                            if p["probe_id"] in ("SP-01", "SP-02", "SP-03", "SP-04"))
        self.assertIn("no official", verdicts.lower())
        self.assertIn("no snap counts", verdicts.lower())


class DecisionContentTests(unittest.TestCase):
    def test_requirements_name_a_gate_and_a_clearing_number(self):
        req = rows("requirements-delta.csv")
        self.assertGreaterEqual(len(req), 8)
        for r in req:
            self.assertTrue(r["blocking_gate"].strip(), r["req_id"])
            self.assertTrue(r["gate_meaning"].strip(), r["req_id"])
            self.assertTrue(r["number_that_would_clear_it"].strip(), r["req_id"])
            self.assertTrue(r["what_this_desk_did"].strip(), r["req_id"])
        ids = [r["req_id"] for r in req]
        self.assertEqual(len(ids), len(set(ids)))

    def test_questions_split_held_missing_and_what_closes_it(self):
        questions = rows("questions.csv")
        self.assertEqual(len(questions), 10)
        for q in questions:
            for field in ("information_we_hold", "information_missing", "what_would_close_it",
                          "decision_it_blocks"):
                self.assertTrue(q[field].strip(), f"{q['q_id']}: {field}")

    def test_suggestions_carry_three_paths(self):
        suggestions = rows("suggestions.csv")
        self.assertEqual(len(suggestions), 8)
        ranks = sorted(int(s["rank"]) for s in suggestions)
        self.assertEqual(ranks, list(range(1, 9)))
        for s in suggestions:
            for field in ("adopt_path", "defer_path", "reject_path", "why", "cost", "unblocks"):
                self.assertTrue(s[field].strip(), f"{s['s_id']}: {field}")

    def test_flags_are_numbered_and_sourced(self):
        flags = rows("flags.csv")
        self.assertEqual(len(flags), 8)
        for f in flags:
            self.assertIn(f["severity"], ("high", "medium", "low"))
            self.assertTrue(f["source_url"].startswith("https://"))
            self.assertTrue(f["action"].strip())

    def test_summary_matches_the_generated_tables(self):
        summary = json.loads((DATA / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["counts"]["standings_rows"], 32)
        self.assertEqual(summary["counts"]["standings_mismatches"], 0)
        self.assertEqual(summary["counts"]["week10_gamebooks"], 14)
        self.assertEqual(summary["counts"]["joined_rows_total"], 329)
        self.assertEqual(summary["counts"]["week10_inactives"], 158)
        self.assertEqual(summary["counts"]["week10_inactives_absent_from_report"], 86)


class SiteTests(unittest.TestCase):
    def setUp(self):
        registry = json.loads((REPO / "research" / "sources.json").read_text(encoding="utf-8"))
        if isinstance(registry, dict):
            registry = registry.get("sources", [])
        self.registry = {r["id"]: r["url"] for r in registry}
        self.pages = sorted(SITE.glob("*.html"))

    def test_pages_built(self):
        self.assertEqual(len(self.pages), 13)

    def test_every_row_has_registered_sources_and_a_link(self):
        import re
        tr_re = re.compile(r"<tr[^>]*data-source-ids=\"([^\"]+)\"[^>]*>(.*?)</tr>", re.S)
        href_re = re.compile(r'href="([^"]+)"')
        for path in self.pages:
            text = path.read_text(encoding="utf-8")
            body = text.split("<tbody>")[1:] or []
            for chunk in body:
                for ids, inner in tr_re.findall(chunk):
                    id_list = ids.split()
                    self.assertTrue(id_list, f"{path.name}: row without source ids")
                    for sid in id_list:
                        self.assertIn(sid, self.registry, f"{path.name}: unregistered {sid}")
                    urls = set(href_re.findall(inner))
                    self.assertTrue(any(self.registry[s] in urls for s in id_list),
                                    f"{path.name}: row lacks its registered source link")

    def test_blank_cells_are_truly_blank(self):
        import re
        blank_re = re.compile(r'<td[^>]*data-empty="true"[^>]*>(.*?)</td>', re.S)
        for path in self.pages:
            for content in blank_re.findall(path.read_text(encoding="utf-8")):
                self.assertEqual(content.strip(), "", f"{path.name}: blank cell has content")

    def test_no_pricing_or_wagering_values_published(self):
        import re
        banned = re.compile(
            r"\b(?:odds|price|line|spread|total)\b\s*(?:of|is|:|=)?\s*[-+]?\d"
            r"|\bROI\b\s*(?:of|:|=)?\s*[-+]?\d"
            r"|\bstake[sd]?\b\s*(?:of|:|=)?\s*[$£€]?\d"
            r"|\bwager(?:ed|s|ing)?\b\s*[$£€]?\d"
            r"|[$£€]\s?\d",
            re.IGNORECASE,
        )
        for path in self.pages:
            self.assertIsNone(banned.search(path.read_text(encoding="utf-8")),
                              f"{path.name}: published a pricing or wagering value")

    def test_document_semantics(self):
        for path in self.pages:
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("<h1"), 1, path.name)
            self.assertIn('<main id="main">', text, path.name)
            self.assertIn('<html lang="en">', text, path.name)
            self.assertIn("<title>", text, path.name)


if __name__ == "__main__":
    unittest.main()
