"""Pre-registration for the readiness desk (nfl-readiness-1467fdf7).

This file is the registration. It is committed BEFORE controls.py is run on the results, so the
commit that adds it is the freeze point. Changing a rule here after the control results exist
requires a new registration entry (new id, new commit), not an edit.

Every strategy entry carries a two-sided "what would change our mind" field:
  - confirm: the evidence that would make us take the signal more seriously;
  - refute:  the evidence that would demote it back to paper or drop it.
No reward, staking or ROI is defined here: the price-data policy is undecided (see requirements.py).
"""

REGISTRATION_ID = "NR-PREREG-1"
FROZEN_ON = "2026-11-17"

SAMPLE = {
    "season": "2026 regular season",
    "weeks": [1, 2, 3, 4, 5, 6, 7, 8, 9],
    "universe": "136 official final scores in nfl-results/data/games-2026-w1-9.csv",
    "tie_rule": "A tied final is not graded straight-up and is excluded from n (pre-registered).",
    "halves": {"first": [1, 2, 3, 4], "second": [5, 6, 7, 8, 9]},
    "outcome": "Straight-up winner only. No spread, total, moneyline price, ROI or CLV is used.",
    "information_rule": "A pick for week w may use only games in weeks < w (no leakage).",
}

RANDOM_SEED = 20261117
RANDOM_REPLICATES = 10000
RECORD_TIE_CREDIT = 0.5  # a tie counts as half a win when computing prior win %
HOME_MARGIN_MIN_PP = 5.0  # percentage points C-REC must beat C-HOME by to be a candidate

GATES = [
    {"id": "G1", "name": "Provenance", "rule": "Every graded game has an https nfl.com source URL and a saved evidence file."},
    {"id": "G2", "name": "No leakage", "rule": "Each pick uses only games in earlier weeks; tested in code."},
    {"id": "G3", "name": "Sample size", "rule": "n graded >= 153 before any skill claim (the desk's 80%-power figure for a 60% rate)."},
    {"id": "G4", "name": "Beats chance band", "rule": "Lower bound of the 95% Wilson interval exceeds the 97.5th percentile of the seeded random-pick band at the same n."},
    {"id": "G5", "name": "Both halves agree", "rule": "The hit rate is above 50% in both halves (weeks 1-4 and 5-9) and in the same direction."},
    {"id": "G6", "name": "Multiplicity", "rule": "Family of registered strategies in this file; a Holm correction is applied when more than one candidate is tested."},
    {"id": "G7", "name": "Executable price", "rule": "ROI, CLV and reward are blocked until an executable, licensed price series exists. Blocked here."},
]

STRATEGIES = [
    {
        "id": "C-RAND",
        "division": "Singles (control)",
        "kind": "control",
        "name": "Random pick (seeded)",
        "definition": "For each graded game, pick home or away with a seeded uniform draw.",
        "benchmark": "Is itself the chance benchmark. Reported as one draw plus a 10,000-replicate band.",
        "confirm": "The single draw falls outside the band, which would mean the seed or the grading is wrong: investigate before trusting any other row.",
        "refute": "Not applicable: this entry is a yardstick, not a strategy. It is retired if the band is shown to be miscalibrated.",
    },
    {
        "id": "C-HOME",
        "division": "Singles (control)",
        "kind": "control",
        "name": "Always home team",
        "definition": "Pick the home team in every graded game.",
        "benchmark": "Tests whether home-side alone carries skill. A non-skill control for any home-side idea.",
        "confirm": "Lower 95% Wilson bound above the chance band (G4), above 50% in both halves (G5), and n >= 153 (G3). Then home-side becomes a candidate for a full validation run.",
        "refute": "Point estimate at or below 50% with n >= 75, or the two halves disagree in sign. Home-side is then dropped as a standalone idea.",
    },
    {
        "id": "C-REC",
        "division": "Singles (control)",
        "kind": "control",
        "name": "Higher prior win % (record favourite proxy)",
        "definition": "Pick the team with the higher win % (wins + 0.5 x ties) / games played, counting only games in weeks before the pick. Ties in win % go to the home team. Week 1 has no prior games, so week 1 picks go to the home team.",
        "benchmark": "Stands in for the favourite-only control. A market favourite needs a line; no official line exists in the repo, so this is labelled a proxy.",
        "confirm": "Passes G3 and G4, is above 50% in both halves (G5), and beats C-HOME by at least HOME_MARGIN_MIN_PP on the same games. Then record-based picks become the next benchmark to beat.",
        "refute": "At or below C-HOME in both halves, or dropping any single week takes it inside the chance band.",
    },
    {
        "id": "S-BOARD-SA",
        "division": "Singles (candidate, cross-reference only)",
        "kind": "candidate",
        "name": "Originated spread board (directional)",
        "definition": "Owned by nfl-results (nfl-results/analysis.json). Cross-referenced here, NOT re-scored, NOT re-registered.",
        "benchmark": "Chance band and permutation null are taken from nfl-results/analysis.json.",
        "confirm": "Out-of-sample results (weeks 10 onward, scored only after kickoff) keep the spread-direction lower 95% bound above 50%, pass G3-G6, and an executable price exists for G7.",
        "refute": "Out-of-sample lower bound at or below 50%, or the out-of-sample hit rate falls inside the 95th-percentile null band of the in-sample permutation test.",
    },
]

DIVISIONS = [
    {"division": "Singles", "status": "Populated: 3 controls + 1 cross-reference", "blocked_by": "No proper-score (Brier) forecast is stored for any row; Brier skill is blank."},
    {"division": "Game parlays", "status": "Blocked", "blocked_by": "Joint-evidence gate: no directly validated joint probability and no operator void/push rules are in the repo."},
    {"division": "Same-game parlays", "status": "Blocked", "blocked_by": "No per-player game logs for the joint distribution (nfl-results analysis.json NM01)."},
    {"division": "Prop combos", "status": "Blocked", "blocked_by": "No per-player game logs captured; no prop prices (NM01, NM02)."},
]
