"""Tests for the Week 11 injury-hub first read (session arena/20226569-own7).

These pin the drift alarm: the parser must reproduce the committed CSVs, and any tampered
transcript (a dropped row, an unknown designation, a changed count, a mismatched record or a
missing profile link) must raise instead of publishing a blank or a guess.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import injury_w11 as m  # noqa: E402

TEXT = m.EVIDENCE.read_text(encoding="utf-8")


def _build_with(text: str):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "transcript.md"
        path.write_text(text, encoding="utf-8")
        with mock.patch.object(m, "EVIDENCE", path):
            return m.build()


class Week11Read(unittest.TestCase):
    def test_pinned_counts_hold_on_the_retained_transcript(self):
        r = m.build()
        self.assertEqual(len(r["games"]), 13)
        self.assertEqual(len(r["players"]), 26)
        self.assertEqual(r["nir_clubs"], 24)
        self.assertEqual(r["table_counts"], {"Colts": 11, "Texans": 15})
        self.assertEqual(len(r["byes"]), 6)

    def test_committed_csvs_are_current(self):
        r = m.build()
        self.assertEqual(m.GAMES_CSV.read_text(encoding="utf-8"), r["games_csv"])
        self.assertFalse((HERE / "data" / "injury-w11-2026-11-18-players.csv").exists(),
                         "player-level rows must not be written to a CSV (raw data, flag FI09)")

    def test_every_player_row_has_source_and_profile_link(self):
        for row in m.build()["players"]:
            self.assertEqual(row["source_url"], "https://www.nfl.com/injuries/")
            self.assertTrue(row["player_profile_url"].startswith("https://www.nfl.com/players/"))
            self.assertEqual(row["source_id"], "FRESH-NFL-INJHUB-W11-1118")

    def test_blank_game_status_stays_blank(self):
        # At this read no designation is printed. The desk must not fill one in.
        self.assertTrue(all(row["game_status"] == "" for row in m.build()["players"]))
        self.assertTrue(all(row["injuries"] == "" for row in m.build()["players"]))

    def test_schedule_and_standings_agree(self):
        games = m.build()["games"]
        self.assertEqual([(g["away_abbr"], g["home_abbr"]) for g in games][0], ("IND", "HOU"))
        self.assertEqual(games[2]["away_abbr"], "AZ")  # printed abbreviation, kept as printed


class DriftAlarm(unittest.TestCase):
    def test_dropped_player_row_fails(self):
        lines = [l for l in TEXT.splitlines() if not l.startswith("| Wyatt Teller |")]
        with self.assertRaises(SystemExit) as ctx:
            _build_with("\n".join(lines) + "\n")
        self.assertIn("player rows 25", str(ctx.exception))

    def test_unknown_practice_status_fails(self):
        text = TEXT.replace("| Dalton Tucker | G |  | Full Participation in Practice |  |",
                            "| Dalton Tucker | G |  | Maybe Practicing |  |")
        with self.assertRaises(SystemExit) as ctx:
            _build_with(text)
        self.assertIn("unknown practice status", str(ctx.exception))

    def test_unknown_game_status_fails(self):
        text = TEXT.replace("| Dalton Tucker | G |  | Full Participation in Practice |  |",
                            "| Dalton Tucker | G |  | Full Participation in Practice | Doubtful |")
        with self.assertRaises(SystemExit) as ctx:
            _build_with(text)
        self.assertIn("unknown game status 'Doubtful'", str(ctx.exception))

    def test_a_record_that_disagrees_with_standings_fails(self):
        text = TEXT.replace("- IND Colts (3-7)", "- IND Colts (4-6)")
        with self.assertRaises(SystemExit) as ctx:
            _build_with(text)
        self.assertIn("record 4-6", str(ctx.exception))

    def test_a_missing_profile_link_fails(self):
        text = TEXT.replace("- Wyatt Teller — https://www.nfl.com/players/wyatt-teller/\n", "")
        with self.assertRaises(SystemExit) as ctx:
            _build_with(text)
        self.assertIn("no profile link", str(ctx.exception))

    def test_a_row_with_a_missing_cell_fails(self):
        text = TEXT.replace("| Wyatt Teller | G |  | Full Participation in Practice |  |",
                            "| Wyatt Teller | G | Full Participation in Practice |  |")
        with self.assertRaises(SystemExit) as ctx:
            _build_with(text)
        self.assertIn("expected 5", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
