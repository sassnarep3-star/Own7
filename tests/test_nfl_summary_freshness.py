"""Guard generated executive/results pages against known stale figures."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SummaryFreshnessTests(unittest.TestCase):
    def test_executive_summary_does_not_publish_superseded_results(self):
        rendered = (ROOT / "executive-summary.html").read_text(encoding="utf-8")
        for expected in (
            "150 final scores through Week 10",
            "134 walk-forward-scored games",
            "30 strategy variants",
            "−0.0318 (p=0.7209, n=128)",
        ):
            self.assertIn(expected, rendered)
        for stale in ("77–43", "64.2%", "n=114", "Compiled 2026-11-15"):
            self.assertNotIn(stale, rendered)

    def test_results_summary_uses_current_correlation_sample_and_window(self):
        rendered = (ROOT / "nfl-results.html").read_text(encoding="utf-8")
        self.assertIn("Weeks 1–10, complete", rendered)
        self.assertNotIn("Weeks 1–9, reconciled", rendered)
        self.assertIn("128 games; phi −0.0318, two-sided p=0.7209", rendered)
        self.assertNotIn("over 114 games", rendered)


if __name__ == "__main__":
    unittest.main()
