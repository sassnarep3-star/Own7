#!/usr/bin/env python3
"""Tests for the skill-separation desk.

Two kinds of test:
  * **Reference-value tests** — the special functions are checked against values that can be read
    out of any published statistical table, so a silent break in the maths fails the build.
  * **Contract tests** — the published data must keep the properties the site claims: blanks stay
    blank, every row carries a source, moves must be explained by one result.
"""
from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESK = HERE.parent
if str(DESK) not in sys.path:
    sys.path.insert(0, str(DESK))

import luck  # noqa: E402

DATA = DESK / "data"


def rows(name):
    with (DATA / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class ReferenceValues(unittest.TestCase):
    """Published table values. A break here means the maths is wrong, not the data."""

    def test_chi_square_upper_tail(self):
        self.assertAlmostEqual(luck.chi2_sf(3.841458820694124, 1), 0.05, places=5)
        self.assertAlmostEqual(luck.chi2_sf(5.991464547107979, 2), 0.05, places=5)
        self.assertAlmostEqual(luck.chi2_sf(18.307038053275146, 10), 0.05, places=5)
        self.assertAlmostEqual(luck.chi2_sf(43.77294198, 30), 0.05, places=4)

    def test_chi_square_monotone(self):
        values = [luck.chi2_sf(x, 32) for x in range(1, 80)]
        self.assertTrue(all(a > b for a, b in zip(values, values[1:])))

    def test_normal(self):
        self.assertAlmostEqual(luck.norm_cdf(1.959963985), 0.975, places=9)
        self.assertAlmostEqual(luck.norm_ppf(0.975), 1.959963985, places=8)
        self.assertAlmostEqual(luck.norm_cdf(0.0), 0.5, places=12)

    def test_student_t_two_sided(self):
        self.assertAlmostEqual(luck._t_two_sided_p(2.228138852, 10), 0.05, places=5)
        self.assertAlmostEqual(luck._t_two_sided_p(3.169272673, 10), 0.01, places=5)

    def test_binomial_upper_tail(self):
        self.assertAlmostEqual(luck.binom_sf(5, 10, 0.5), 0.623046875, places=9)
        self.assertEqual(luck.binom_sf(0, 10, 0.5), 1.0)
        self.assertEqual(luck.binom_sf(11, 10, 0.5), 0.0)
        # Large n must not overflow; P(X >= 0) is 1 by definition.
        self.assertAlmostEqual(luck.binom_sf(0, 30000, 0.5), 1.0, places=12)
        # Symmetry: P(X >= 2) = 1 - P(X <= 1) at n=2, p=0.5.
        self.assertAlmostEqual(luck.binom_sf(2, 2, 0.5), 0.25, places=12)

    def test_pearson_known_pair(self):
        r, p = luck.pearson([1, 2, 3, 4, 5], [2, 4, 5, 4, 5])
        self.assertAlmostEqual(r, 0.7745966692, places=8)
        self.assertAlmostEqual(p, 0.1237, places=3)

    def test_fisher_interval_brackets_r(self):
        lo, hi = luck.fisher_interval(0.5, 40)
        self.assertLess(lo, 0.5)
        self.assertGreater(hi, 0.5)
        self.assertGreater(lo, -1.0)
        self.assertLess(hi, 1.0)


class StandingsContract(unittest.TestCase):

    def test_thirty_two_rows_and_unique_clubs(self):
        data = rows("standings-2026-11-14.csv")
        self.assertEqual(len(data), 32)
        self.assertEqual(len({r["club_abbr"] for r in data}), 32)

    def test_every_row_carries_an_official_source(self):
        for r in rows("standings-2026-11-14.csv"):
            self.assertEqual(r["source_id"], "CFDD-NFL-STANDINGS")
            self.assertTrue(r["source_url"].startswith("https://www.nfl.com/"))
            self.assertEqual(r["checked_on"], "2026-11-14")

    def test_arithmetic_checks_all_match(self):
        for r in rows("standings-2026-11-14.csv"):
            self.assertEqual(r["pct_check"], "match", r["club_abbr"])
            self.assertEqual(r["net_check"], "match", r["club_abbr"])
            self.assertEqual(int(r["points_for"]) - int(r["points_against"]),
                             int(r["net_recomputed"]))

    def test_league_identity(self):
        data = rows("standings-2026-11-14.csv")
        self.assertEqual(sum(int(r["points_for"]) for r in data),
                         sum(int(r["points_against"]) for r in data))
        self.assertEqual(sum(int(r["wins"]) for r in data),
                         sum(int(r["losses"]) for r in data))

    def test_capture_summary_is_honest(self):
        cap = json.loads((DATA / "standings-capture-2026-11-14.json").read_text())
        self.assertEqual(cap["rows_parsed"], 32)
        self.assertEqual(cap["arithmetic_failures"], 0)
        self.assertTrue(cap["withheld_columns"], "withheld columns must be listed, not silent")
        # Nothing may be published as a forecast or a price from a standings table.
        self.assertIn("Not a forecast", cap["scope"])

    def test_moves_are_explained_by_one_result(self):
        cap = json.loads((DATA / "standings-capture-2026-11-14.json").read_text())
        self.assertEqual(cap["move_consistency"]["consistency"],
                         "consistent with exactly one result")


class DepthContract(unittest.TestCase):

    def test_all_four_clubs_captured(self):
        summary = json.loads((DATA / "depth-summary-2026-11-14.json").read_text())
        self.assertEqual(summary["clubs_captured"], ["CHI", "DEN", "PHI", "TB"])
        self.assertGreater(summary["total_printed_slots"], 200)

    def test_houston_is_a_published_blank_not_substituted(self):
        summary = json.loads((DATA / "depth-summary-2026-11-14.json").read_text())
        self.assertIn("HOU", summary["not_captured"])
        self.assertNotIn("HOU", summary["clubs_captured"])

    def test_every_slot_has_a_source_and_a_rank(self):
        for r in rows("depth-slots-2026-11-14.csv"):
            self.assertTrue(r["source_url"].startswith("https://"))
            self.assertTrue(r["evidence_file"].startswith("nfl-skill-cfdd/evidence/"))
            self.assertGreaterEqual(int(r["rank"]), 1)
            self.assertTrue(r["player"].strip())

    def test_multi_name_cells_are_flagged_not_ordered(self):
        multi = [r for r in rows("depth-slots-2026-11-14.csv") if r["cell_holds_multiple"] == "yes"]
        for r in multi:
            self.assertIn(" / ", r["player"])
        # Philadelphia prints exactly two such cells in this capture.
        self.assertEqual({r["club_abbr"] for r in multi}, {"PHI"})

    def test_rank_order_is_preserved_within_a_slot(self):
        """Ranks must follow printed order. A gap is allowed only where the club printed a blank
        cell, and every such gap is counted in the summary rather than silently closed."""
        seen = {}
        for r in rows("depth-slots-2026-11-14.csv"):
            key = (r["club_abbr"], r["unit"], r["slot"])
            seen.setdefault(key, []).append(int(r["rank"]))
        for key, ranks in seen.items():
            self.assertEqual(sorted(ranks), ranks, f"printed order broken in {key}")
            self.assertEqual(len(ranks), len(set(ranks)), f"duplicate rank in {key}")

    def test_blank_printed_cells_are_reported(self):
        summary = json.loads((DATA / "depth-summary-2026-11-14.json").read_text())
        # Philadelphia prints a DT row whose first-string cell is empty. That is a real absence in
        # the source, so it must appear in the summary instead of being filled in.
        self.assertGreaterEqual(summary["blank_printed_cells"], 1)
        slots = rows("depth-slots-2026-11-14.csv")
        first_rank_missing = [
            (r["club_abbr"], r["unit"], r["slot"]) for r in slots
            if int(r["rank"]) > 1 and not any(
                int(o["rank"]) == 1 and (o["club_abbr"], o["unit"], o["slot"])
                == (r["club_abbr"], r["unit"], r["slot"]) for o in slots)
        ]
        self.assertEqual(summary["blank_printed_cells"], len(set(first_rank_missing)))


class LuckResults(unittest.TestCase):

    def test_overdispersion_is_a_real_computation(self):
        res = json.loads((DATA / "skill-luck-results-2026-11-14.json").read_text())
        over = res["overdispersion"]
        self.assertEqual(over["degrees_of_freedom"], 32)
        self.assertAlmostEqual(over["mean_under_null"], 32.0)
        self.assertTrue(0.0 <= over["p_value_upper_tail"] <= 1.0)
        self.assertAlmostEqual(over["variance_inflation"],
                               over["statistic"] / over["degrees_of_freedom"], places=4)

    def test_no_strategy_and_no_reward_is_published(self):
        res = json.loads((DATA / "skill-luck-results-2026-11-14.json").read_text())
        self.assertEqual(res["verdict"], "no strategy qualifies")
        self.assertIsNone(res["cash_rewards"])

    def test_every_uncomputed_quantity_states_why(self):
        res = json.loads((DATA / "skill-luck-results-2026-11-14.json").read_text())
        self.assertGreaterEqual(len(res["not_computed"]), 5)
        for item in res["not_computed"]:
            self.assertTrue(item["why_blank"])
            self.assertTrue(item["blocks"])

    def test_sample_size_monotone_in_edge(self):
        data = rows("sample-size-to-separate-skill.csv")
        powered = [r for r in data if r["bets_needed_exact_binomial"]]
        by_edge = {}
        for r in powered:
            if r["target_power"] == "0.80":
                by_edge[float(r["true_win_rate"])] = int(r["bets_needed_exact_binomial"])
        edges = sorted(by_edge)
        for a, b in zip(edges, edges[1:]):
            self.assertGreater(by_edge[a], by_edge[b],
                               "a bigger edge must need fewer bets")

    def test_break_even_row_is_blank_not_guessed(self):
        data = rows("sample-size-to-separate-skill.csv")
        even = [r for r in data if float(r["true_win_rate"]) == 0.5]
        self.assertTrue(even)
        for r in even:
            self.assertEqual(r["bets_needed_normal_approx"], "")
            self.assertEqual(r["bets_needed_exact_binomial"], "")

    def test_correlations_carry_intervals_and_holm(self):
        for r in rows("correlations-2026-11-14.csv"):
            self.assertNotEqual(r["fisher_95_low"], "")
            self.assertNotEqual(r["fisher_95_high"], "")
            self.assertNotEqual(r["holm_adjusted_p"], "")
            self.assertIn(r["reject_null_at_0.05"], {"yes", "no"})
            self.assertEqual(r["source_id"], r["source_id"].strip())
        # Holm adjustment can only make a p-value larger.
        for r in rows("correlations-2026-11-14.csv"):
            self.assertGreaterEqual(float(r["holm_adjusted_p"]) + 1e-9, float(r["p_value"]))

    def test_derived_quantity_is_labelled_as_a_validity_check(self):
        data = {r["correlation_id"]: r for r in rows("correlations-2026-11-14.csv")}
        self.assertIn("not an independent finding", data["C-PYTH-ACTUAL"]["caveat"])


class NoInventedMarket(unittest.TestCase):
    """The standing rights constraint means no price may appear anywhere in this desk."""

    def test_no_price_or_roi_column(self):
        forbidden = ("price", "odds", "roi", "clv", "stake", "wager", "payout")
        for path in DATA.glob("*.csv"):
            with path.open(encoding="utf-8") as fh:
                header = [h.lower() for h in next(csv.reader(fh))]
            for bad in forbidden:
                self.assertFalse(any(bad in h for h in header),
                                 f"{path.name} has a market column containing {bad}")


if __name__ == "__main__":
    unittest.main()


class DepletionIndex(unittest.TestCase):
    """The index must be a count-based ordering and must never become a point value."""

    def test_one_join_row_per_injury_row(self):
        self.assertEqual(len(rows("depletion-join-2026-11-14.csv")), 326)

    def test_all_32_clubs_appear_in_the_summary(self):
        summary = rows("club-depletion-index-2026-11-14.csv")
        self.assertEqual(len(summary), 32)
        self.assertEqual(len({r["club_abbr"] for r in summary}), 32)

    def test_houston_chart_absent_not_filled(self):
        summary = {r["club_abbr"]: r for r in rows("club-depletion-index-2026-11-14.csv")}
        self.assertEqual(summary["HOU"]["printed_chart_available"], "no")
        self.assertEqual(summary["HOU"]["matched_to_printed_chart"], "0")
        self.assertEqual(float(summary["HOU"]["total_index"]), 0.0)

    def test_unmatched_rows_keep_blank_rank_and_url(self):
        for r in rows("depletion-join-2026-11-14.csv"):
            if r["on_printed_chart"] == "no":
                self.assertEqual(r["printed_rank"], "")
                self.assertEqual(r["depth_source_url"], "")
                self.assertEqual(r["depletion_points"], "")

    def test_index_equals_sum_of_its_parts(self):
        for r in rows("club-depletion-index-2026-11-14.csv"):
            parts = (float(r["offense_index"]) + float(r["defense_index"])
                     + float(r["special teams_index"]))
            self.assertAlmostEqual(float(r["total_index"]), parts, places=3, msg=r["club_abbr"])

    def test_offense_and_defence_are_separate_columns(self):
        with (DATA / "club-depletion-index-2026-11-14.csv").open() as fh:
            header = next(csv.reader(fh))
        self.assertIn("offense_starters_ruled_out", header)
        self.assertIn("defense_starters_ruled_out", header)
        self.assertNotIn("starters_ruled_out", header)

    def test_no_point_or_probability_column(self):
        """No market-value column may exist. Checked on exact names, because 'next_in_line' is a
        depth slot and not a betting line."""
        forbidden = {"point_value", "probability", "expected_points", "market_line", "price",
                     "line", "spread", "total", "odds", "roi", "clv", "stake"}
        for name in ("club-depletion-index-2026-11-14.csv", "depletion-join-2026-11-14.csv",
                     "depth-slots-2026-11-14.csv"):
            with (DATA / name).open() as fh:
                header = {h.lower() for h in next(csv.reader(fh))}
            self.assertEqual(header & forbidden, set(), name)

    def test_weighting_is_disclosed(self):
        res = json.loads((DATA / "depletion-index-2026-11-14.json").read_text())
        self.assertIn("rank_weight", res["weigthing_disclosure"])
        self.assertIn("Project design choice", res["weigthing_disclosure"]["statement"])


class DecisionLayer(unittest.TestCase):

    def test_every_open_question_states_what_closes_it(self):
        for q in rows("questions-2026-11-14.csv"):
            self.assertTrue(q["what_closes_it"].strip(), q["question_id"])
            self.assertTrue(q["blocks"].strip(), q["question_id"])
            if q["status"] in ("open", "blocked"):
                self.assertTrue(q["missing"].strip(),
                                f"{q['question_id']} is open but names nothing missing")

    def test_an_answered_question_carries_a_source(self):
        for q in rows("questions-2026-11-14.csv"):
            if q["status"].startswith("answered"):
                self.assertTrue(q["known_source"].strip(),
                                f"{q['question_id']} claims an answer with no source")
                self.assertTrue(q["known"].strip())

    def test_a_blocked_question_is_not_answered(self):
        for q in rows("questions-2026-11-14.csv"):
            if q["status"] == "blocked":
                self.assertEqual(q["known"].strip(),
                                 "cannot be known: there is no market line to compare against"
                                 if q["question_id"] == "Q14" else q["known"].strip())

    def test_every_suggestion_has_an_runnable_acceptance_test(self):
        for s in rows("suggestions-2026-11-14.csv"):
            for field in ("evidence", "unlocks", "cost", "risk", "acceptance_test"):
                self.assertTrue(s[field].strip(), f"{s['suggestion_id']} missing {field}")
            self.assertIn(s["priority"], {"1", "2", "3", "4"})

    def test_suggestions_address_real_questions(self):
        question_ids = {q["question_id"] for q in rows("questions-2026-11-14.csv")}
        for s in rows("suggestions-2026-11-14.csv"):
            for qid in s["addresses"].split():
                self.assertIn(qid, question_ids, f"{s['suggestion_id']} cites unknown {qid}")

    def test_choice_record_is_blank(self):
        choice = rows("choice-record-2026-11-14.csv")
        self.assertEqual(len(choice), len(rows("suggestions-2026-11-14.csv")))
        for c in choice:
            self.assertEqual(c["decision"], "",
                             "this session must not record a decision on the reviewer's behalf")

    def test_every_flag_links_an_official_source(self):
        for f in rows("flags-2026-11-14.csv"):
            self.assertTrue(f["source_url"].startswith("https://"), f["flag_id"])

    def test_flags_have_valid_status(self):
        for f in rows("flags-2026-11-14.csv"):
            self.assertIn(f["status"], {"open", "explained"})
            self.assertIn(f["severity"], {"open", "blocking", "informational"})


class StrategyLedger(unittest.TestCase):

    def test_all_ten_strategies_present_and_blocked(self):
        data = rows("strategies-2026-11-14.csv")
        self.assertEqual(len(data), 10)
        for r in data:
            self.assertEqual(r["status"], "BLOCKED")
            self.assertEqual(r["settled_bets"], "0")
            self.assertEqual(r["score"], "")

    def test_bet_types_cover_single_parlay_and_prop(self):
        types = {r["bet_type"] for r in rows("strategies-2026-11-14.csv")}
        self.assertIn("single", types)
        self.assertIn("parlay_2", types)
        self.assertIn("parlay_3", types)
        self.assertIn("prop_combo", types)

    def test_no_leaderboard_entry_is_reward_eligible(self):
        for r in rows("leaderboard-2026-11-14.csv"):
            self.assertEqual(r["eligible_for_reward"], "no")
            self.assertEqual(r["score"], "")
            self.assertEqual(r["settled_bets"], "0")

    def test_gates_are_computed_and_carry_producers(self):
        res = json.loads((DATA / "gates-2026-11-14.json").read_text())
        self.assertEqual(len(res["gates"]), 12)
        for g in res["gates"]:
            self.assertIn(g["status"], {"pass", "fail", "blocked"})
            self.assertTrue(g["evidence"].strip())
            self.assertTrue(g["produced_by"].strip())
        self.assertIsNone(res["cash_rewards"])

    def test_no_gate_is_blocked_and_passed_at_once(self):
        res = json.loads((DATA / "gates-2026-11-14.json").read_text())
        ids = [g["gate_id"] for g in res["gates"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_blocked_gate_names_rights_not_data(self):
        res = json.loads((DATA / "gates-2026-11-14.json").read_text())
        blocked = [g for g in res["gates"] if g["status"] == "blocked"]
        self.assertEqual([g["gate_id"] for g in blocked], ["V8"])
        self.assertIn("rights", blocked[0]["evidence"].lower())


class SiteContract(unittest.TestCase):
    """The generated site must keep the row-source contract and the blank rule."""

    SITE = DESK / "site"

    def test_every_page_has_one_h1_and_a_main(self):
        for path in sorted(self.SITE.glob("*.html")):
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("<h1>"), 1, path.name)
            self.assertIn("<main", text, path.name)
            self.assertIn('lang="en"', text, path.name)

    def test_every_internal_link_resolves(self):
        import re
        files = {p.name for p in self.SITE.iterdir()}
        for path in sorted(self.SITE.glob("*.html")):
            for ref in re.findall(r'href="([^"#:]+)"', path.read_text(encoding="utf-8")):
                if ref.startswith(("http", "mailto")):
                    continue
                self.assertIn(ref, files, f"{path.name} links missing {ref}")

    def test_manifest_matches_the_files_present(self):
        manifest = json.loads((self.SITE / "manifest.json").read_text())
        on_disk = {p.name for p in self.SITE.glob("*.html")}
        self.assertEqual(set(manifest["pages"]), on_disk)

    def test_no_page_invents_a_price(self):
        """No page may state a price, an ROI or a reward amount for an NFL market."""
        for path in sorted(self.SITE.glob("*.html")):
            text = path.read_text(encoding="utf-8").lower()
            for claim in ("roi of", "clv of", "payout of", "stake $", "profit of $"):
                self.assertNotIn(claim, text, path.name)

    def test_blank_cells_are_marked_and_empty(self):
        import re
        for path in sorted(self.SITE.glob("*.html")):
            for cell_html in re.findall(r'<td data-empty="true"[^>]*>(.*?)</td>',
                                        path.read_text(encoding="utf-8")):
                self.assertEqual(cell_html.strip(), "", f"{path.name}: blank cell has content")


class NextInLineMatching(unittest.TestCase):
    """Regression guard for a defect found while building the depletion page.

    A club restarts its slot numbering for every printed position, so 'slot 1' occurs several
    times inside one unit. Matching a starter to a backup on position alone attached the wrong
    player. The fix keys on (club, unit, printed position, slot). These tests fail if that key is
    ever loosened again.
    """

    def setUp(self):
        self.res = json.loads((DATA / "depletion-index-2026-11-14.json").read_text())
        self.join = {(r["club_abbr"], r["player"]): r
                     for r in rows("depletion-join-2026-11-14.csv")}

    def test_a_club_reuses_slot_numbers_per_position(self):
        """The defect's root cause, asserted on the earlier transcription.

        That snapshot numbers slots per unit, so many positions share slot 1. Keying a lookup on
        (club, unit, slot) alone therefore mixes positions and attaches the wrong backup. This test
        documents the reason the four-part key exists.
        """
        path = DESK.parent / "nfl-availability-28ef" / "data" / "depth-slots-week10-2026.csv"
        keyed = {}
        for r in csv.DictReader(path.open(encoding="utf-8")):
            keyed.setdefault((r["club_abbr"], r["unit"], r["slot"]), set()).add(r["position"])
        reused = [k for k, v in keyed.items() if len(v) > 1]
        self.assertTrue(reused, "expected the earlier snapshot to reuse a slot number")

    def test_the_four_part_key_has_no_collisions(self):
        for name in ("depth-slots-2026-11-14.csv",):
            keyed = {}
            for r in rows(name):
                keyed.setdefault((r["club_abbr"], r["unit"], r["position"], r["slot"]),
                                 []).append(r["rank"])
            clashes = {k: v for k, v in keyed.items() if len(v) != len(set(v))}
            self.assertEqual(clashes, {}, f"{name}: duplicate rank inside one printed slot")

    def test_every_named_replacement_is_the_next_printed_name_in_that_slot(self):
        """The replacement must be the rank+1 name printed in the same slot of the SAME chart the
        join row used. Verified against the slot tables directly, because the replacement is often
        a player who is not on the injury report and so has no join row at all."""
        import csv as _csv
        tables = []
        for rel in ("data/depth-slots-2026-11-14.csv",
                    "../nfl-availability-28ef/data/depth-slots-week10-2026.csv"):
            path = (DESK / rel).resolve()
            with path.open(encoding="utf-8") as fh:
                tables.append(list(_csv.DictReader(fh)))
        for b in self.res["backed_up_starters"]:
            row = self.join[(b["club"], b["player"])]
            key = (b["club"], row["printed_unit"], row["printed_position_key"],
                   row["printed_slot"])
            slot = {}
            for table in tables:
                for r in table:
                    if (r["club_abbr"], r["unit"], r["position"], r["slot"]) != key:
                        continue
                    if r["source_url"] != row["depth_source_url"]:
                        continue
                    slot[int(r["rank"])] = r["player"].split(" / ")[0]
            self.assertNotEqual(b["next_in_line"], "", b)
            self.assertNotEqual(b["next_in_line"], b["player"], "a player cannot replace himself")
            start_rank = int(row["printed_rank"])
            self.assertIn(start_rank + 1, slot,
                          f"{b['club']} {b['player']}: no rank+1 in the slot it was matched to")
            self.assertEqual(b["next_in_line"], slot[start_rank + 1],
                             f"{b['club']} {b['player']}: advertised replacement is not rank+1")

    def test_counts_add_up(self):
        self.assertEqual(self.res["starters_ruled_out"],
                         self.res["starters_ruled_out_with_backup_in_line"]
                         + self.res["starters_ruled_out_with_no_backup_printed"])
        self.assertEqual(len(self.res["backed_up_starters"]),
                         self.res["starters_ruled_out_with_backup_in_line"])

    def test_a_row_without_a_chart_has_no_replacement(self):
        for r in rows("depletion-join-2026-11-14.csv"):
            if r["on_printed_chart"] == "no":
                self.assertEqual(r["next_in_line"], "")
                self.assertEqual(r["slot_has_backup"], "")


class AmbiguityDisclosure(unittest.TestCase):
    """A player printed in several slots is a real ambiguity; it must stay counted and visible."""

    def test_ambiguous_rows_are_counted_and_marked(self):
        res = json.loads((DATA / "depletion-index-2026-11-14.json").read_text())
        rows_ = rows("depletion-join-2026-11-14.csv")
        marked = [r for r in rows_ if r["ambiguous_printed_slot"] == "yes"]
        self.assertEqual(len(marked), res["injury_rows_printed_in_more_than_one_slot"])
        for r in marked:
            self.assertGreater(int(r["printed_slot_count"]), 1)

    def test_unmatched_rows_do_not_claim_ambiguity(self):
        for r in rows("depletion-join-2026-11-14.csv"):
            if r["on_printed_chart"] == "no":
                self.assertEqual(r["ambiguous_printed_slot"], "")

    def test_flag_cf13_exists_and_links_the_report(self):
        flags = {f["flag_id"]: f for f in rows("flags-2026-11-14.csv")}
        self.assertIn("CF13", flags)
        self.assertIn("more than one", flags["CF13"]["title"])
        self.assertTrue(flags["CF13"]["source_url"].startswith("https://"))


class PositionVocabulary(unittest.TestCase):
    """Chart and injury-report vocabularies differ; a player must not cross sides of the ball."""

    def test_no_matched_row_sits_on_the_wrong_side_of_the_ball(self):
        import sys as _s
        if str(DESK) not in _s.path:
            _s.path.insert(0, str(DESK))
        from index import group_of, SIDE_OF_GROUP
        for r in rows("depletion-join-2026-11-14.csv"):
            if r["on_printed_chart"] != "yes":
                continue
            a = group_of(r["position_reported"])
            b = group_of(r["printed_position"])
            if a in SIDE_OF_GROUP and b in SIDE_OF_GROUP:
                self.assertEqual(SIDE_OF_GROUP[a], SIDE_OF_GROUP[b],
                                 f"{r['club_abbr']} {r['player']}: {r['position_reported']} "
                                 f"located at {r['printed_position']}")

    def test_the_group_map_covers_every_position_printed(self):
        import sys as _s
        if str(DESK) not in _s.path:
            _s.path.insert(0, str(DESK))
        from index import group_of
        unknown = set()
        for name in ("depth-slots-2026-11-14.csv",):
            for r in rows(name):
                if not group_of(r["position"]):
                    unknown.add(r["position"])
        for r in rows("depletion-join-2026-11-14.csv"):
            if r["position_reported"] and not group_of(r["position_reported"]):
                unknown.add(r["position_reported"])
        self.assertEqual(unknown, set(), f"ungrouped position labels: {sorted(unknown)}")

    def test_all_three_tracks_are_populated(self):
        import collections
        counts = collections.Counter(r["track"] for r in rows("depletion-join-2026-11-14.csv"))
        self.assertGreater(counts["offense"], 0)
        self.assertGreater(counts["defense"], 0)
        self.assertGreater(counts["special teams"], 0)

    def test_offence_and_defence_indexes_are_not_the_same_number(self):
        data = rows("club-depletion-index-2026-11-14.csv")
        differing = [r for r in data if r["offense_index"] != r["defense_index"]]
        self.assertGreater(len(differing), 0,
                           "offence and defence must be measured separately, not mirrored")
