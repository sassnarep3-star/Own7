# Executive Summary — NBA Line Origination Engine

**Prepared:** 2026-11-03 (UTC)
**Data snapshot:** 2026-11-03T23:45Z, transcribed from NBA.com
**Author session:** `session-arena-1050ddb0-own7`
**Scope:** `analysis/**` only (see `COORDINATION.md`)
**Dashboard:** [`analysis/index.html`](index.html) → published at `/analysis/`

---

## 1. The one-paragraph version

A reproducible engine now originates NBA spread, total and win-probability lines from
official NBA.com team ratings, with explicit small-sample shrinkage so a hot start is
not mistaken for a true rating. It measures real same-game dependence instead of
assuming parlay legs are independent, and it runs eight validation gates with
three-state outcomes before anything reaches a leaderboard. On the current evidence
the honest reading is: **the machinery is sound and independently testable, but the
evidence base is too thin to rank any strategy.** Eighteen games cannot pin a
correlation, no official source publishes sportsbook prices, and player-level prop
data could not be collected at all. The leaderboard therefore ranks nothing —
deliberately, not by omission.

---

## 2. What was built

| Component | What it does | Where |
|---|---|---|
| Verified data layer | 30 team advanced-stat rows + 18 finished games, each traceable to an NBA.com URL and a read timestamp | `data/official-*.json` |
| Line origination | Model spread, total, win probability and fair odds for the 2026-11-04 slate | `engine/markets.py`, `results/model-originated-lines.json` |
| Ratings | Raw vs. shrunk NetRtg with declared prior strength | `engine/ratings.py` |
| Correlation | Pearson + phi with Fisher z intervals; refuses what it cannot measure | `engine/correlation.py` |
| Skill vs. luck | Exact binomial, probabilistic Sharpe, deflated Sharpe, min track record, block bootstrap | `engine/skill.py` |
| Validation gates | G0–G7, pass / fail / not-evaluable | `engine/gates.py` |
| Leaderboard | ROI lower confidence bound; unranked unless all gates pass | `engine/leaderboard.py` |
| Tests | 51 self-tests incl. closed-form bivariate normal + determinism | `tests/test_engine.py` |
| Dashboard | 10 self-contained pages, every row sourced or explicitly blank | `build_site.py` |
| Checker | Links, nav, per-row provenance, placeholders, JSON integrity | `check_nav.py` |

Run it: `python3 analysis/run.py && python3 analysis/build_site.py`, then
`python3 -m unittest discover -s analysis/tests -t analysis`.

---

## 3. Findings

**F1 — Raw small-sample ratings massively overstate quality.**
Houston is +12.8 after 8 games. The shrinkage estimator keeps 8/(8+20) = 28.6% of
that edge, giving +3.66. Using the raw number would price every Houston game as if
they were a 65-win team. This is the single largest error source in naive line
origination.
Source: <https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular%20Season>

**F2 — Same-game parlay legs are positively dependent, but unmeasurable at n = 18.**
Home vs. away scoring: r = 0.42, 95% CI [−0.06, 0.74]. The interval includes zero,
so "dependent" and "independent" cannot be distinguished. An honest parlay model must
carry that uncertainty rather than quote the point estimate.
Source: <https://www.nba.com/stats/teams/boxscores?Season=2026-27&SeasonType=Regular%20Season>

**F3 — Pre-game pace vs. realised total is the most promising real signal — and still
too wide to trade.** r = 0.56, 95% CI [0.12, 0.81]. This uses only published team
PACE, so it is a genuine forecast check rather than a same-game identity.

**F4 — There is no market to beat.** No official NBA source publishes sportsbook
prices; the NBA.com games list has a "HIDE ODDS" toggle but renders no numbers.
Without a timestamped price there is no vig, no edge, and no settlement to evaluate.
Every `market_*` and `edge_vs_market` field is `null` by design.
Source: <https://www.nba.com/schedule?date=11/03/2026>

**F5 — Short-horizon leaderboards rank luck.** Among 100 identical no-skill entries
at 200 bets each and −110 prices, roughly **44 show a profit**. A board that ranks on
ROI at that sample size is ranking noise.

**F6 — Multiplicity is the dominant hidden risk.** The expected best Sharpe of
*N* zero-skill strategies is 1.57 at N=10, 2.53 at N=100, 3.26 at N=1,000. Trying 100
ideas guarantees a good-looking winner. Gate G4 deflates for exactly this.

---

## 4. What is deliberately not here

| Missing | Why it blocks | What would fix it |
|---|---|---|
| Market prices | No edge can exist without a real price | Licensed, timestamped odds feed |
| Player-prop correlation | NBA.com player box-score pages render client-side and returned no table | Paired per-player game logs + exact prop lines and void/push rules |
| Full-season sample | At 18 games, correlation CIs include zero | ~174 paired games for ±0.15, ideally two seasons |
| Competition rewards | Inventing amounts would be fabrication | Owner decision on reward, window, eligibility |

Every one of these is on the **Flagged for Review** page with its source link.

---

## 5. Validation gates

A strategy is ranked only if **all eight** gates pass. `not_evaluable` never rolls up
to `passed`.

| Gate | Requirement |
|---|---|
| G0 Provenance | every input carries an official source URL |
| G1 Pre-registration | thresholds, universe, stopping rule, window declared and hashed before results |
| G2 Sample size | settled bets ≥ declared minimum |
| G3 Out-of-sample | OOS edge retains ≥ 50% of in-sample edge |
| G4 Luck | binomial p < 0.05 **and** PSR > 0.95 **and** deflated Sharpe > 0.95 |
| G5 Price realism | every bet priced from a timestamped, attributed, sourced executable price |
| G6 Correlation | parlay dependence measured, interval excluding zero |
| G7 Robustness | mean return stays positive after dropping the best 5% of results |

Current outcome for the lead strategy: **unproven**. G0 and G1 pass; G2–G5 and G7 are
not evaluable without a bet record; G6 fails outright while legs are assumed
independent. No rank is issued.

---

## 6. How the maths is verifiable

The engine asserts closed forms rather than trusting the implementation:

- Bivariate normal CDF pinned to `P(X<0, Y<0) = 1/4 + arcsin(ρ)/(2π)` at seven values
  of ρ, tolerance 1e-6 — this is the function every parlay number depends on.
- Φ₂ must reduce exactly to Φ(h)·Φ(k) at ρ = 0.
- Shrinkage must hit the league mean at 0 games and the observed rating in the limit.
- De-vigging two −110 lines must give exactly 4.77% hold and fair p = 0.5.
- A byte-for-byte determinism test re-runs the whole analysis as a subprocess.
- Honest anchors: 55% over 1,000 bets is only p ≈ 0.052; "no bets" must yield
  `unproven`, never `passed`.

51 tests, all passing, no network, no third-party packages.

---

## 7. What to trust, doubt, reject

**Trust** — the data (per-row NBA.com URLs), the arithmetic (51 closed-form-anchored
tests), and the gate logic (three-state).

**Doubt** — the originated lines. They are a state model over a partial season using
three documented constants (k = 20 games, home court = 2.5 pts, margin SD = 12.5), and
no market exists to check them against. They are a starting point for line
origination, not prices.

**Reject** — any reading of this as a profitable system. Zero strategies are ranked
because zero could be shown to be skill rather than luck. That is the correct
mathematical conclusion, not a shortfall of effort.

---

## 8. Bottom line

The brief asked to originate lines, generate useful signals, quantify correlation,
remove luck, and reward top performers through a validated competition.

Delivered: line origination that works and names its assumptions; a correlation
measurement that reports its own uncertainty honestly; a luck-removal battery built on
published statistical methods; and a gate system that refuses to rank unproven work.

Not delivered, and not fakeable: market-comparable edges, player-prop combos, and
rewards. Each requires an input that does not exist in this environment, and each is
documented on the Flagged for Review page rather than estimated.

The engine is ready. The evidence is not yet there, and saying so is the most useful
result available today.
