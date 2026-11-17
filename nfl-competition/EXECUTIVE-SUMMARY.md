# NFL competition lab — executive summary

Built 2026-11-14. Research only: no wager is placed, no price is published, and nothing here is an offered market.

The short version: the parts of the brief that need only official league data are built and verified. The parts that need a market price are built, tested and left empty, because no official source this project read prints one.

## What is verified

- **137 official final scores**, re-derived into club records and reconciled against the NFL.com standings: **192 of 192 club fields match**, with 6291 points scored and the same number allowed.
- **13 Week 10 games originated** in three stages in a fixed order: side, then total, then moneyline. 1 game had already finished when the schedule was read and is carried in the results feed instead of the board.
- **78 markets published** as 78 board rows, each with a model fair line and a blank market line and difference.
- **8 starters ruled out** on a printed depth chart; 7 are replaced from the second string and 1 slot has no printed replacement at all.
- **8 correlations computed from official numbers**, every one published with its sample size; 2 are left blank rather than estimated.
- **20 questions catalogued** (8 answered, 4 open, 1 blocked on source rights).
- **15 irregularities flagged** (6 open, 7 explained, 2 corrected before publication).

## What is deliberately blank

- **The price store holds 0 rows** across 78 registered markets. nfl.com returns HTTP 404 at `/odds/` and prints no price, spread, total or operator on any page this project read.
- **Return on investment, stake, drawdown and closing-line value are blank everywhere.** They need an executable price, and there is none. Zero is not a value for these cells.
- **No reward is paid.** 0 merit points awarded; cash reward and prize pool are both null.
- **The staking half of the leaderboard has 0 rows.** Signal and staking are two tables that never touch, so a lucky staking run cannot promote a bad signal.
- **No point value is attached to an injury or to a replacement.** A printed rank is an ordering, not a measurement.

## What the evidence actually shows

- The strongest directional record is **74-46 over 120 settled selections (61.7%)**, exact binomial p = 0.0134, Benjamini-Hochberg q = 0.1152. It does **not** survive multiplicity control at a 10% false-discovery rate, so nothing is promoted to live.
- The highest hit rate on the board is 66.7%, on a sample too small to separate skill from luck. Percentage alone is not a finding.
- The measured home allowance is **-0.0219 points** over 137 games (SD 13.23), with a 95% interval of [-2.24, 2.19]. That interval contains both zero and the conventional two points: this season does not separate them.
- League scoring measures 22.9599 points per team-game over 274 team-games. It is measured from the feed, not assumed.
- **0 strategies are live, 0 provisional, 14 paper, 2 blocked on data, 2 control.**
- The demotion gate publishes 10 triggers with today's reading on each (7 computable, 3 blocked on price, 1 firing now). 0 strategy has ever reached the live tier, so no demotion has fired.
- Only 1 of 18 strategies reject their null after multiplicity control: PB-02. The one rejection is a control whose null rate is 34.0% rather than a coin flip, so it measures the test, not an edge.

## The three things that block everything

- **SG-01 — Capture an executable price: opening and closing, for every market the lab originates.** Unlocks Return on investment, Closing-line value, The staking half of the leaderboard, Gate G06, Every reward, Demotion triggers D04, D05 and D06. Priority 5 of 5. Done when: At least one market in price-snapshots.csv carries both an OPEN and a CLOSE row, verified yes, with an operator, a pre-kickoff capture timestamp and a source URL on a registered host; and the leaderboard staking table has at least one row.
- **SG-12 — Settle the source-rights question before building any price capture.** Unlocks SG-01, SG-02, Gate G10, Any dataset release. Priority 2 of 5. Done when: A written answer on record: consent obtained, a different source used, or the price work formally declined.
- **SG-05 — Extend the results feed every week and re-run the reconciliation.** Unlocks Question Q03, Question Q13, Any eventual promotion. Priority 4 of 5. Done when: The feed extends by the newly published week and the reconciliation still reports 192 of 192 club fields matching.

Sample size is the quiet one. Detecting a true 60% rate at 80% power and a two-sided 5% test needs 273 for a true rate of 57.5%, 153 for a true rate of 60.0%, 67 for a true rate of 65.0%. The largest sample available today is 121.

## Injuries and defensive deficiencies

- 25 of 326 injury rows carry an official game status. The rest state a practice status only, so no replacement is implied for them and none is computed. A replacement is implied only where the league prints a game status. It prints one on 25 of 326 rows.
- 8 slots need a replacement: DET CB; DET C; IND MLB; IND WLB; IND RT; IND LS; NE CB; NE LG.
- 1815 printed depth-chart slots across 31 clubs. HOU renders its chart as an image and stays blank rather than guessed.

## Where to look next

- `site/index.html` — the desk landing page.
- `site/suggestions.html` — the ranked proposals and the decision board. Nothing is implemented until a choice is recorded.
- `site/questions.html` — what is held, what is missing, and what closes each gap.
- `site/review.html` — the flagged irregularities with their official links.
- `site/method.html` — the method, the formulas and the limits.

Every table row on every page links to the official source it came from. A value that no official source confirms is published blank and flagged, never inferred.

