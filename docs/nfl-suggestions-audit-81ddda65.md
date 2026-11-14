# NFL Suggestions / Questions / Decisions — audit and consolidated dossier
### Session arena/81ddda65-own7 — 2026-11-14

The owner asked for a clear list of **questions, information held and information missing**
that must be settled before any decision, plus **suggestions to discover the missing
information**, and a dedicated **Suggestions** section where a reviewer can compare and choose a
path *before* anything is implemented. This audit consolidates the three existing registers into
one review-before-decision dossier. Values are copied verbatim from the source registers; nothing
was inferred or retyped.

## 1. Registers audited

| Register | File | IDs | Counts |
|---|---|---|---|
| Decisions (known / missing / suggestions) | `research/nfl/decisions.json` | K01–K10, M01–M10, S01–S10 | 10 known, 10 missing, 10 suggestions |
| Questions | `research/nfl/questions.json` | DQ01–DQ17 | 17 questions |
| Suggestions (parallel list) | `research/nfl-suggestions.json` | SU-01–SU-12 | 12 suggestions |

**Irregularity NF16 (confirmed this session).** Two parallel suggestion registers with different
ID schemes coexist (S01–S10 and SU-01–SU-12), and a third question register (DQ01–DQ17) overlaps
both. The same ideas appear under different IDs, which makes "which suggestion is approved"
ambiguous. **Recommendation:** treat `research/nfl/decisions.json` as the canonical register;
the consolidated dossier below cross-maps SU-* and DQ-* to it. Do not maintain a second independent
suggestion list.

## 2. What blocks any reward (must be settled first)

`blocking_before_any_reward` = **M01, M02, M03, M04**. No strategy is ranked, and no reward is
paid, until these are resolved:

| ID | Missing question | Why it matters | Closes with |
|---|---|---|---|
| M01 | What price, limit and hold does any operator actually offer on these Week 10 markets? | No timestamped quote → no ROI, no closing-line value, no break-even test, nothing to rank. | S01 |
| M02 | Which listed player is a starter, and who replaces him? | A game status alone cannot tell you whether a starter is out; the owner names 2nd/3rd/4th-string exposure. | S02 |
| M03 | How many snaps, targets and carries does each player normally take? | Converts an absence into an expected output change; without it "Out" is a label, not a number. | S02 |
| M04 | How do same-game legs actually depend on one another? | A parlay price assumes a joint distribution; multiplying probabilities assumes zero dependence, which this project will not assume. | S03 |

## 3. Questions that must be answered before any decision (DQ01–DQ17)

Full text and per-question known/missing/resolves fields are in
`research/nfl/decision-dossier-81ddda65.json`. Summary by area:

| ID | Area | Question | Status |
|---|---|---|---|
| DQ01 | Scope & rights | May this research be published at all, in this form? | Known (NFL.com terms §1.3) |
| DQ02 | Line origination | Are the originated Week 10 numbers internally consistent and reproducible? | Yes, narrowly (test-enforced) |
| DQ03 | Line origination | Is a 2.0-point home adjustment defensible for all 14 games? | Assumption only; no official HFA retrieved (M10) |
| DQ04 | Injuries & backups | Do we know which clubs are starting 2nd/3rd-string players? | No (M02) |
| DQ05 | Injuries & backups | What does a blank game status mean? | Blank = unknown; not "will play" (M09) |
| DQ06 | Correlation & parlays | How much do two same-game legs move together? | Nothing measured (M04) |
| DQ07 | Correlation & parlays | Can 3+ legs be priced from pairwise numbers? | No; pairwise dependence does not identify a joint distribution |
| DQ08 | Skill vs luck | Is anything skill-based rather than luck? | Scoring model scores (K07/K08); no edge claimed |
| DQ09 | Skill vs luck | How much of each club's record is luck? | Every club within ~2.2 wins of expectation (M08) |
| DQ10 | Market & economics | Is any strategy profitable? | No; zero qualified, no price retrieved (M01) |
| DQ11 | Market & economics | What would make a reward decision reasonable? | The blocked list M01–M04 plus forward out-of-sample test |
| DQ12 | Verification | How much confidence does a single official page support? | Arithmetic re-derived; extractor refuses contradictions |
| DQ13 | Verification | What did we choose not to transcribe, and why? | Columns with no rendered header left blank, not inferred |
| DQ14 | Scope & rights | Should the NBA material stay on the site? | Separate scope; its own source terms apply |
| DQ15 | Skill vs luck | Can luck be removed from the equation at all? | Not from a single result; only stated and measured, never claimed removed |
| DQ16 | Verification | Does the site's own check suite prove values are true? | No; it proves internal integrity and row-source links, not external truth |
| DQ17 | Injuries & backups | Which official source names the replacement for an injured starter? | Neither injury report nor league depth-chart path supplies it (M02) |

## 4. Information held (with sources)

K01–K10 in the dossier; highlights: 32-club standings snapshot (272 team-games); league scoring
22.963 pts/team-game; mandatory injury categories; Week-10 TNF block = 20 players; Week 10 = 14
fixtures + 4 byes; points-based expectation Brier 0.1575 vs 0.25 flat; only 5 of 10 team
correlations are independent evidence; NFL.com terms restrict use; largest record-vs-expectation
gap ≈ 2.17 wins. Each item carries its `source_ids` and a verification note.

## 5. Information missing (and the suggestion that discovers it)

M01–M10 in the dossier. Each missing item names the suggestion (S01–S10) that would close it and
what it blocks. The discovery sequence proposed by the register is: **S06 rights check → S01
market capture → S02 depth & snaps → S03 dependence → S04 two-season history → S05/S07/S08
hygiene → S09 ledger / S10 second source.**

## 6. Suggestions section (review-before-implement)

The site already publishes dedicated Suggestions pages where a reviewer can compare proposals and
choose a path before implementation (no approval control exists on the static site; a decision is
recorded by editing the register and rebuilding, leaving an auditable commit):

- `nfl/origination/suggestions.html` — line-lab suggestions
- `nfl-availability-28ef/site/suggestions.html` — availability/depletion desk proposals with Adopt / Defer / Reject controls
- `nfl-assurance-9580ac3f/site/suggestions.html` — assurance proposals

The canonical review workflow (states: Proposed → Under review → Approved → Rejected → Implemented)
requires at approval: a reviewer role, a decision date, an accepted acceptance test, and the
question it closes. A rejected suggestion keeps its row and gains a reason; nothing is deleted.

## 7. Recommended next actions (for the owner to choose from)

1. **Adopt `decisions.json` as the single canonical register** and retire the duplicate SU-* list
   (resolves NF16). Cross-reference DQ-* as the question view.
2. **Close M01 first** (licensed, timestamped price capture) — it unblocks every ranked decision
   and reward. Source rights (S06 / NFL.com terms §1.3) must be settled before any scaled
   collection.
3. **Close M02 + M03 together** (printed depth charts + snap share) — directly serves the owner's
   requirement to know 2nd/3rd/4th-string replacements on offense and defense.
4. **Close M04** (same-game leg dependence) before pricing any parlay or player-prop combo.
5. **Refresh the dated snapshots** per flag 81-01 so the published numbers reflect the
   2026-11-12 TNF result.

## Sources

NFL.com standings, player stats, team offense/defense passing, injuries and terms — see
`docs/nfl-verification-81ddda65.md` for the full 2026-11-14 re-verification and links.
Registers: `research/nfl/decisions.json`, `research/nfl/questions.json`,
`research/nfl-suggestions.json`. Consolidated dossier: `research/nfl/decision-dossier-81ddda65.json`.
No value was inferred or filled in.
