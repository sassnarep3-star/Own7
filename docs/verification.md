# Verification boundary and audit record

## What was actually rechecked

On 2026-11-03 this session compared retained input fields against official rendered NBA tables returned by `fetch_page`. All relevant chunks of the three inherited data tables and the explicitly filtered new game-log table were read. The checked data total is **107 rows**: 30 team, 15 scoring-filtered player, 30 standings and 32 game-log rows.

Exact URLs, check method, chunk scopes, official displayed row counts, retained counts, normalized data files and SHA-256 receipts are in [`research/evidence/receipts.json`](../research/evidence/receipts.json). See [`research/evidence/README.md`](../research/evidence/README.md) for limits. These are normalized transcriptions, **not raw HTTP response archives or independent sources**. Later equality/hash checks establish consistency and integrity, not renewed factual verification.

## Corrections and non-verifications

- Official team table: Denver PTS 122.1, Lakers FG% 50.2; older executive maxima were incorrect. Utah tied display rank is 26, not 27. BLKA is explicitly identified. Team conference/division fields not shown by that table were removed, not assumed.
- Player names restored to official spelling. Expanded names use NBA-linked team IDs. The fifteen-player scoring filter cannot be treated as a full player universe; displayed age is snapshot metadata.
- Standings are a frozen snapshot; W+L ranges 5–8, not uniformly eight games. NBA per-game rounding is preserved, not recomputed to force component sums.
- An ignored LastNGames parameter/paginated player log was rejected. The accepted explicit 2026-02-01–2026-04-12 filter displayed exactly 32 rows on one page. Current-season profile headline values were not used for historical data.
- Old unsupported correlation signs, zero-correlation independence, universal product payouts and play-by-play-only assertions were withdrawn.
- Stale one-file repo history, blanket verification statements and unrelated Alberta/helpline/media-policy claims were withdrawn from active facts. Original wording is retained in git at baseline `14c5f50`.
- No operator quote, closing price, existing gambling-use permission, live line, ROI, CLV, cash pool or winner is verified. Those fields stay blank.
- Confirmed official source restriction: [NBA terms §9(iv)](https://www.nba.com/termsofuse) prohibits NBA Statistics use connected with gambling activity, including legal gambling. Source access is not a license. Price release, bulk collection and cash use are disabled.

## Full repository scope

[`research/audit/baseline-inventory.json`](../research/audit/baseline-inventory.json) hashes all **54 baseline tracked files / 2,630 text lines**. [`file-review.json`](../research/audit/file-review.json) records complete line ranges and dispositions for each. Technical/code review is not external factual verification. Superseded external assertions are explicitly not reconfirmed; local repository facts cite exact official GitHub baseline files.

## Automated verification

- Receipt hashes/counts, normalized row equality, NBA game IDs/date scope, row arithmetic and corrected extrema.
- Pricing/statistical identities, undefined/constant inputs, Fréchet feasibility, probability validity, proper scoring, Holm correction, tied ranks and deterministic block resampling.
- Chronological input isolation: modifying target/future outcomes does not change that target’s probability. Duplicate/unsorted games rejected.
- Rights fail-closed defaults; actual candidates remain ineligible; cash/reward/performance blanks enforced.
- Recursive HTML, assets, relative links, fragments and redirect targets, not just root pages.
- Every body row has registered official input/method/project links; arbitrary HTTPS presence is insufficient. All unknown metrics stay empty, not zero.
- Byte-identical site/results regeneration; a single canonical site with compatibility redirects/deprecation pointers.
- Browser checks for desktop/mobile rendering, keyboard navigation/sorting/search, filters, blank preservation, CSV download, legacy redirects, console/network errors, responsive overflow and automated accessibility checks.

The tools do **not** certify future source accuracy, independent data rights, real operator availability, skill, profit or legality. Scheduled source-health requests check availability only, save non-mutating artifacts and never promote a URL into a factual verification. Current check/deploy evidence is recorded in [`COORDINATION.md`](../COORDINATION.md) and [`research/audit/check-results.json`](../research/audit/check-results.json).

## Incoming-main re-verification

Incoming main `37e1bbd` added parallel source and calculation work after the original baseline. All 77 files have scoped dispositions in `research/audit/parallel-review.json`. All append-only boards and independently authored dossiers were preserved. B1 has 24 findings and six flags; the exact checked operator/regulator sections are in `research/evidence/settlement-recheck.json`. Current wager terms are still unverified.

Historical NBA transcription files remain unaltered. Their numeric fields match the current checked CSVs; historical ASCII names are explicitly matched as identity aliases, not silently called verbatim official spelling. The newer receipts preserve Dončić/Jokić. The contributed snapshot checker now includes the formerly omitted PF field. Six team coefficients and all 11 handoff coefficients/intervals are independently checked; the canonical UI labels them derived and flags nominal Fisher-interval assumptions. Original historical no-game-log statements predate the new 32-row cohort and are not current claims.

PR #4 was open at initial claim but later closed by another session. F15 is corrected based on the official GitHub record; this session did not modify that PR. Canonical review also includes all MF/NL/BLKA/aggregate-coverage flags. Automated checks are repeated on the combined integration, not assumed from an earlier independent branch.
