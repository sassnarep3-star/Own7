# NFL independent re-verification — session arena/81ddda65-own7 (2026-11-14)

This session re-checked the **current committed NFL observations** against official
NFL.com sources retrieved fresh on **2026-11-14**. It does **not** inherit any earlier
session's verification. Every source link below was opened this session through the
Arena page reader.

**Method / limitation.** Direct sandbox HTTPS to `nfl.com` is blocked, so all retrieval
used the Arena page reader and returned **rendered text**. The captured values are
normalized transcriptions, not raw HTTP archives. The captured evidence is stored in
`research/nfl/evidence-81ddda65/official-nfl-2026-11-14.json`.

## Official sources read (2026-11-14)

| Dataset | Official source | Result |
|---|---|---|
| Standings (32 rows) | https://www.nfl.com/standings/ | 30/32 rows match exactly; NYG & WAS diverge by the TNF result (see 81-01) |
| Player passing (top 25) | https://www.nfl.com/stats/player-stats/ | 22/25 players match; ranks 23–25 diverge by the TNF result (see 81-01); NF12 persists (see 81-02) |
| Team defense passing (32) | https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all | 30/32 match; NYG & WAS diverge by the TNF result |
| Team offense passing (32) | https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all | 30/32 match; NYG & WAS diverge by the TNF result |
| Injuries — Week 10 TNF block (20) | https://www.nfl.com/injuries/ | 20/20 match exactly |
| Terms §1.3 | https://www.nfl.com/legal/terms/ | Confirmed verbatim ("non-commercial and informational purposes"; "Systematic retrieval … is prohibited") |

## Result summary

- **Injuries: 0 mismatches.** All 20 Thursday TNF rows match the official report cell for cell.
- **All other mismatches are explained by a single time-stamp divergence** (flag **81-01**):
  the committed snapshot is dated **2026-11-12** and predates the Thursday Night Football
  result (**Commanders 24, Giants 21**, played 2026-11-12). The official source retrieved
  2026-11-14 reflects the completed game:
  - Standings: Giants 5-2-1 → 5-3-1; Commanders 2-5-1 → 3-5-1.
  - Team defense/offense passing for Giants and Commanders: pre-game attempts/yards vs post-game.
  - Player passing ranks 23–25: committed = Cam Ward 23, Sam Darnold 24, Michael Penix Jr. 25;
    official = **Jayden Daniels 23**, Cam Ward 24, Sam Darnold 25. Jayden Daniels (Commanders QB)
    is absent from the committed top-25; Michael Penix Jr. (1,444 yds) is present. This is
    consistent with the snapshot pre-dating Daniels' TNF passing total.
- **No unexplained transcription errors were found.** Every non-injury mismatch is confined to
  the TNF-affected keys (Giants, Commanders, Jayden Daniels, Michael Penix Jr., Cam Ward,
  Sam Darnold). This is enforced by `tests/test_nfl_verification_81ddda65.py`.

## Flags raised (published for review; non-blocking)

Registered in `research/nfl/flags-81ddda65.json`:

- **81-01 — snapshot-dating.** The 2026-11-12 snapshot predates the TNF result; the official
  source now reflects it. Recommended action: publish a dated post-TNF refresh; retain the
  2026-11-12 snapshot as a dated historical transcription. Sources:
  https://www.nfl.com/standings/ · https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all ·
  https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all ·
  https://www.nfl.com/stats/player-stats/ · https://www.nfl.com/games/commanders-at-giants-2026-reg-10
- **81-02 — publisher column disagreement (NF12, re-confirmed).** Mahomes 2,037/263 prints 7.8
  (exact 7.7452); Watson 1,806/249 prints 7.2 (exact 7.2530). No rounding convention reconciles
  them; the publisher's own columns disagree. Source: https://www.nfl.com/stats/player-stats/
- **81-03 — provenance.** The player/team-stats snapshot CSVs carry no explicit retrieval date;
  their snapshot date is inferred. Recommended action: add a retrieval-date column to all NFL
  snapshot CSVs. Sources: https://www.nfl.com/stats/player-stats/ ·
  https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all ·
  https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all

## Rights boundary (re-confirmed)

NFL.com Terms §1.3 restricts use to individual non-commercial, informational purposes and
prohibits systematic retrieval absent express prior written consent; §12 prohibits using the
Services to gamble/wager on NFL games. No permission is inferred. This deliverable is a bounded
informational snapshot and a fail-closed research/verification harness, not an unauthorized
live betting-price feed. No NFL line, edge, ROI, CLV, cash prize or winning strategy is claimed.

## Reproducibility

- Evidence: `research/nfl/evidence-81ddda65/official-nfl-2026-11-14.json`
- Verifier: `scripts/verify_nfl_81ddda65.py` (report mode; `--check` exits non-zero on any mismatch)
- Tests: `tests/test_nfl_verification_81ddda65.py` (6 tests; enforces injuries-exact and
  no-unexplained-mismatches)

No value was inferred or filled in. Blanks remain blank where no official source confirms a value.
