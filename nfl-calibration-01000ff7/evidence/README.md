# Calibration audit evidence and provenance

Read date for this desk: 2026-11-19. This desk adds no new web capture and no automated retrieval.
It uses the completed 150-game, Week 1–10 official results corpus and the existing, unchanged
three-stage origination model, then independently re-derives all 134 game forecasts for Weeks
2–10 and their proper scores. For every target week, the model's existing walk-forward logic trains
only on rows whose week is strictly less than the target week. Week 1 is not scored because there is
no prior-season training data. The single tie is retained in the three-outcome Brier score; binary
Brier and reliability bins use 133 non-tie games and the conditional home-win probability.

Each published game row carries its by-week official NFL schedule/results URL and a matching
exact-URL source ID. Weeks 2–9 use `CAL-RESULTS-Wxx-1114` registrations whose official pages are
preserved in `nfl-results/evidence/week-X.schedule.md`; 13 Week 10 finals link to
`E15-NFL-SCHED-REG10-1117`, while the later LAC–BAL final links to
`FRESH-NFL-W10-COMPLETE-1118`. `nfl-results/extract.py --check` re-derives the 150-row corpus from
its dated official page evidence. The build requires exact URL equality with the primary registry
row.

Manual review links:

- [NFL Week 1 schedule](https://www.nfl.com/schedules/2026/by-week/week-1)
- [NFL Week 10 schedule and results](https://www.nfl.com/schedules/2026/by-week/week-10)
- [Official result corpus registration in this repository](https://github.com/sassnarep3-star/Own7/blob/main/research/sources.json)

The generated `site/manifest.json` contains SHA-256 hashes of the result CSV, model code and
source registry used for the report. The report is only an evaluation of a fixed 2026 sample. It
does not assert permission for systematic future collection, and it makes no market-edge, ROI,
CLV, staking, or payout claim. Week-cluster bootstrap bounds are explicitly exploratory because
there are only nine scored weeks.
