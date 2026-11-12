# NFL line origination — executive summary

**Session:** `arena/20394b77-own7` · **Branch:** `arena/20394b77-own7` · **Snapshot checked:** 12 November 2026 (Week 10, 2026 season)
**Live section:** [`nfl/index.html`](../nfl/index.html) · **Flagged items:** [`nfl/flagged.html`](../nfl/flagged.html) · **Board:** [`COORDINATION.md`](../COORDINATION.md)

---

## 1. The one-paragraph version

The data plumbing is verified; the decision inputs are not. All 32 official standings rows pass three independent arithmetic checks, 210 injury rows for the Week 10 slate were read twice from two official NFL.com pages and agree on every overlapping player, and three club depth charts were joined to that injury report to show who actually replaces whom. Fourteen Week 10 games now have model-implied spreads and totals with a published sensitivity range. **No market price exists anywhere on this site, no strategy has passed validation, and no reward is paid.** Two decisions — data rights (S-01) and a timestamped price source (S-02) — unblock almost everything else.

## 2. What was actually verified (and how)

| Item | Rows | Verification performed | Source |
|---|---|---|---|
| 2026 standings | 32 clubs | PCT = (W + 0.5T)/(W+L+T) on 32/32; NET = PF − PA on 32/32; league-wide PF = PA at 6,246 over 272 team-games | [NFL.com standings](https://www.nfl.com/standings/) |
| Week 10 injury report | 210 rows, 28 clubs | Practice status read from the injury page **and** the official Wednesday roundup; every overlapping player agrees | [Injuries](https://www.nfl.com/injuries/), [roundup](https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-wednesday-nov-11) |
| Week 10 slate | 14 games | Kickoff, network and both clubs from the injury page; 28 distinct clubs, no duplicates, 4 clubs absent | [Injuries](https://www.nfl.com/injuries/) |
| Depth charts | 3 clubs, 36 rows | Club-published order joined by exact player name to the injury report; one label mismatch found and published | [AZ](https://www.azcardinals.com/team/depth-chart), [CLE](https://www.clevelandbrowns.com/team/depth-chart), [SF](https://www.49ers.com/team/depth-chart) |
| Injury-report policy | quoted | Practice-report and Game Status Report deadlines read verbatim | [NFL important dates](https://www.nfl.com/news/2026-27-national-football-league-important-dates) |
| Rights position | quoted | Section 1.3 Permitted Uses read in full | [NFL.com Terms](https://www.nfl.com/legal/terms/) |

## 3. The three findings that matter

1. **Depth, not injury, is the missing variable.** Five first-string players in this slate have **no replacement listed at all** on their club's depth chart — San Francisco's left corner and nickel back, Cleveland's WILL linebacker, and two Arizona positions. "Next man up" cannot be evaluated for them at any price.
2. **The injury picture is incomplete by rule, not by omission.** Wednesday participation is verified; Sunday game designations do not exist yet because the policy deadline is Friday 4 p.m. New York time. A price built today is stale by construction — gate G2 fails on that basis alone.
3. **Every strategy is blocked for the same reason.** Six of ten gates fail on the absence of a verified price. The protocol is implemented and specified; the input is missing.

## 4. Model output (derived, not a market)

The model is a multiplicative offence/defence rating built from official points for and against, shrunk toward the league mean (4 pseudo-games), plus a 2.0-point home-field term; a logistic map with a 13.0-point scale converts margin to win probability. League average is **23.0104 points per team-game**. Every projection is published with a range across nine parameter combinations.

These are **design choices, not NFL facts**, and every range is shown because of that. The market column is blank in every row — no verified price exists.

## 5. Correlation values

Five team-level correlations across the 32 club rows (n = 32), with Fisher 95 % intervals:

| Relationship | Pearson r | Spearman ρ | 95 % interval |
|---|---|---|---|
| Points for per game vs win % | 0.694 | 0.686 | 0.455 to 0.839 |
| Points against per game vs win % | −0.666 | −0.681 | −0.824 to −0.414 |
| Net points per game vs win % | 0.876 | 0.869 | 0.759 to 0.938 |
| Points for vs points against | −0.206 | −0.272 | −0.518 to 0.154 |
| Pythagorean expectation vs win % | 0.877 | 0.862 | 0.761 to 0.939 |

**These are not leg correlations.** A parlay needs the joint behaviour of two legs in the same game. Those cells are blank, flagged, and gated by G9. Assuming zero correlation for same-game legs is the specific error the gate exists to prevent.

## 6. Why the leaderboard is empty

Eight strategies are registered and all are blocked; one is an explicit control that cannot win. Ranking blocked strategies would manufacture a winner out of luck. The competition rules are fixed in advance: Brier skill score against the control, circular block bootstrap interval, Holm adjustment across the declared family of eight, minimum 100 settled observations, and **non-monetary merit points only** — cash rewards are blocked by the rights gate and have had no legal review.

## 7. What to decide first (see `nfl/suggestions.html`)

| ID | Decision | Recommendation |
|---|---|---|
| S-01 | Data-rights path | Stay personal and non-commercial now; ask in writing in parallel; buy a licensed feed only if this becomes public or commercial |
| S-02 | Price source | Manual, timestamped quotes from one operator as a pilot; licensed feed for anything real |
| S-06 | Competition rules | Brier as the qualifier, ROI as a displayed diagnostic — never rank on ROI at this sample size |
| S-07 | Leg-level correlation | Build a settled-leg dataset before publishing any correlation number |
| S-11 | Site structure | Label sections by status (NBA archived / rental / NFL active) before splitting repositories |

The remaining seven suggestions (role weights, depth coverage, prop pipeline, injury delta, decision log, responsible-use block, prefixed naming) are all lower cost and can proceed regardless of S-01 and S-02.

## 8. What is still unknown (see `nfl/questions.html`)

Fifteen questions are logged with what we have, what is missing, and how to obtain it. The blocking ones are: (Q-01) actual market prices, (Q-02) starter identity for 25 of 28 clubs, (Q-07) permitted use, (Q-10) settlement rules for the operator whose prices would be used, and (Q-11) whether any reward is lawful.

## 9. Honest limits

- One dated snapshot, not a feed. Nothing here is a live system.
- Two source typos were transcribed and preserved ('limted', 'hamtring'); statuses are normalised to the policy's three categories and the typo is noted.
- 21 injury rows have no published injury type; those cells are blank, never guessed.
- Depth charts are club publications updated on their own schedule; only San Francisco prints an update date.
- No game-level archive exists, so no backtest exists, so no skill claim exists.
- The NFL.com Terms permit individual, non-commercial, informational use and prohibit systematic retrieval and compilation. This repository is a dated teaching sample under that limit, not a data product.

*Not betting advice, not a licensed data product, not legal advice.*
