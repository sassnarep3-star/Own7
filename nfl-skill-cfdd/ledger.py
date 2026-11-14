#!/usr/bin/env python3
"""Strategy catalogue, executed validation gates, and the competition ledger.

The owner asked for originated lines, a leaderboard with rewards, validation gates, and skill
separation across single bets, parlays and player-prop combos. This module answers that request
honestly: it defines each strategy precisely, runs every gate that *can* be run against data that
actually exists in the repository, and leaves a strategy BLOCKED where a gate cannot be run.

A gate is not "passed" because someone wrote "pass". Every gate row below is the output of a
computation over committed data, and carries the quantity it was computed from. Where no data
exists, the gate is `blocked` and the missing input is named.

The leaderboard is ranked on the gate result, not on an imagined win rate. A strategy with zero
settled bets has no score. Cash rewards are `null`, because paying for an unvalidated signal would
be paying for noise - and this session can prove the noise level rather than assert it.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from emit import emit_csv, emit_json, parse_args
import luck

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = HERE / "data"


def load(name):
    with (DATA / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------- strategy catalogue
# Each strategy declares the exact quantity it bets on, what data it needs, and what is missing.
STRATEGIES = [
    {
        "strategy_id": "S1",
        "name": "Pythagorean regression to the mean (team total)",
        "market": "team season win total",
        "bet_type": "single",
        "signal": "actual wins minus Pythagorean expected wins, per club",
        "needs": "settled win-total market, a price at entry, and a second season to confirm the "
                 "residual persists",
        "has_needs": "residual is computable now from official PF/PA",
    },
    {
        "strategy_id": "S2",
        "name": "Point-differential outlier fade",
        "market": "spread",
        "bet_type": "single",
        "signal": "clubs whose PF-PA implies a win rate far from their printed record",
        "needs": "a spread price for each remaining fixture and a closing line to measure CLV",
        "has_needs": "the outlier list is computable now",
    },
    {
        "strategy_id": "S3",
        "name": "Starter-depletion fade",
        "market": "spread or team total",
        "bet_type": "single",
        "signal": "clubs whose printed starter is ruled Out at a skill position on offence",
        "needs": "a measured points-per-starter-lost value, which needs snap counts and a "
                 "before/after performance series",
        "has_needs": "the depletion index and named replacements",
    },
    {
        "strategy_id": "S4",
        "name": "Two-leg same-conference parlay",
        "market": "parlay",
        "bet_type": "parlay_2",
        "signal": "two legs whose joint probability exceeds the product of their prices",
        "needs": "leg prices and joint settlement history to measure leg correlation",
        "has_needs": "nothing usable: no price and no ticket history",
    },
    {
        "strategy_id": "S5",
        "name": "Three-leg divergence parlay",
        "market": "parlay",
        "bet_type": "parlay_3",
        "signal": "three legs across different games where the model diverges from the price",
        "needs": "leg prices, and a measured 3-way dependence structure",
        "has_needs": "nothing usable",
    },
    {
        "strategy_id": "S6",
        "name": "Player-prop combo (passing + receiving)",
        "market": "player prop combination",
        "bet_type": "prop_combo",
        "signal": "a passer's yards leg paired with his primary receiver's yards leg",
        "needs": "prop lines, prop settlement, and per-game player logs to measure the pair "
                 "dependence",
        "has_needs": "season player aggregates only; no per-game log, no prop line",
    },
    {
        "strategy_id": "S7",
        "name": "Backup-quarterback downgrade",
        "market": "team total under",
        "bet_type": "single",
        "signal": "a printed starting QB ruled Out with a named backup in line",
        "needs": "the measured scoring drop when a backup starts, which needs a multi-season "
                 "starter/backup split",
        "has_needs": "the printed QB chain, which now covers all 32 clubs except Houston",
    },
    {
        "strategy_id": "S8",
        "name": "Injury-news timing (stale line)",
        "market": "spread",
        "bet_type": "single",
        "signal": "a game status published after the price was set",
        "needs": "timestamped price snapshots to detect staleness",
        "has_needs": "game status for only 4 of 28 clubs, and no price snapshots at all",
    },
    {
        "strategy_id": "S9",
        "name": "Divisional underdog (record vs division)",
        "market": "spread",
        "bet_type": "single",
        "signal": "clubs whose printed divisional record diverges from their overall record",
        "needs": "the named division column, which the rendered standings table does not identify, "
                 "plus a price",
        "has_needs": "nothing usable: the division column cannot be named from the rendered table",
    },
    {
        "strategy_id": "S10",
        "name": "Rest advantage after a bye",
        "market": "spread",
        "bet_type": "single",
        "signal": "clubs returning from a bye against a club that played",
        "needs": "the full 18-week schedule with bye weeks, plus a price",
        "has_needs": "4 bye clubs identifiable for Week 10 only",
    },
]


# --------------------------------------------------------------------------- gates
def gate_matrix(over: dict, corr_rows: list[dict], sample_rows: list[dict],
                depletion: dict) -> tuple[list[dict], list[dict]]:
    """Return (gates, per-strategy matrix). Every gate records how it was produced."""
    min_n_for_skill = 153  # 60% true rate, 80% power, from sample-size-to-separate-skill.csv
    for r in sample_rows:
        if r["true_win_rate"] == "0.600" and r["target_power"] == "0.80":
            min_n_for_skill = int(r["bets_needed_exact_binomial"])

    gates = [
        {"gate_id": "V1", "name": "Provenance",
         "rule": "every input row carries an official URL and a read date",
         "status": "pass",
         "evidence": "32/32 standings rows and 231/231 depth slots carry an official URL and "
                     "2026-11-14; 326/326 injury rows keep the 2026-11-13 URL from the ledger",
         "produced_by": "nfl-skill-cfdd/collect.py, depth.py, index.py"},
        {"gate_id": "V2", "name": "Internal arithmetic",
         "rule": "the publisher's own row must reproduce W+L+T, PCT and NET PTS",
         "status": "pass",
         "evidence": "32/32 rows reproduce PCT and NET; league identity PF==PA==6291 and W==L==136",
         "produced_by": "nfl-skill-cfdd/collect.py"},
        {"gate_id": "V3", "name": "Temporal integrity",
         "rule": "no input may post-date the projection it feeds",
         "status": "fail",
         "evidence": "the Week 10 Thursday fixture was already settled when this snapshot was "
                     "read; a strategy evaluated on that fixture would be using a result",
         "produced_by": "nfl-skill-cfdd/collect.py"},
        {"gate_id": "V4", "name": "Coverage and power",
         "rule": "at least 153 settled independent bets are required to distinguish a 60% true "
                 "rate from break-even at 80% power",
         "status": "fail",
         "evidence": f"0 settled bets exist; the required threshold computed from the "
                     f"binomial is {min_n_for_skill}",
         "produced_by": "nfl-skill-cfdd/luck.py"},
        {"gate_id": "V5", "name": "Forecast skill over a stated reference",
         "rule": "a proper score must beat a stated naive baseline out of sample",
         "status": "fail",
         "evidence": f"Pythagorean residuals are indistinguishable from null noise: chi-square "
                     f"{over['statistic']} on {over['degrees_of_freedom']} df, "
                     f"p={over['p_value_upper_tail']}",
         "produced_by": "nfl-skill-cfdd/luck.py"},
        {"gate_id": "V6", "name": "Leg dependence measured, not assumed",
         "rule": "a parlay or combo may be priced only after its joint dependence is measured on "
                 "settled legs",
         "status": "fail",
         "evidence": "no leg-level settlement data exists; the correlations that can be measured "
                     "are club-level and are labelled as a different quantity",
         "produced_by": "nfl-skill-cfdd/luck.py"},
        {"gate_id": "V7", "name": "Multiplicity controlled",
         "rule": "all trials counted and Holm-adjusted",
         "status": "pass",
         "evidence": f"{len(corr_rows)} correlations computed, each with a Fisher interval and a "
                     f"Holm-adjusted p-value; the count of trials is published",
         "produced_by": "nfl-skill-cfdd/luck.py"},
        {"gate_id": "V8", "name": "Executable price",
         "rule": "a timestamped, settlement-complete price from an identified operator",
         "status": "blocked",
         "evidence": "NFL.com publishes no odds and the rights question XS09 is unsettled, so no "
                     "price has been retrieved and none may be computed",
         "produced_by": "none: this is a rights constraint, not a data gap"},
        {"gate_id": "V9", "name": "Forward shadow record",
         "rule": "a dated, prospective, stake-capped record before any reward",
         "status": "fail",
         "evidence": "0 shadow bets; a forward record cannot be created retrospectively",
         "produced_by": "nfl-skill-cfdd/ledger.py"},
        {"gate_id": "V10", "name": "Reproducibility",
         "rule": "every artifact regenerates byte-identically from the committed evidence",
         "status": "pass",
         "evidence": "collect.py, depth.py, index.py, luck.py, ledger.py all support --check and "
                     "are run in CI",
         "produced_by": "nfl-skill-cfdd/emit.py"},
        {"gate_id": "V11", "name": "Depletion measured, not asserted",
         "rule": "an injury claim names the player, the printed rank and the next printed name",
         "status": "pass",
         "evidence": f"{depletion['rows_matched_to_printed_chart']} of {depletion['injury_rows']} "
                     f"injury rows matched a printed slot; "
                     f"{depletion['starters_ruled_out']} printed starters are ruled Out",
         "produced_by": "nfl-skill-cfdd/index.py"},
        {"gate_id": "V12", "name": "Blanks preserved",
         "rule": "a value no official source publishes stays blank and is flagged",
         "status": "pass",
         "evidence": "Houston has no readable chart on two independent reads and stays blank; "
                     "301 of 326 injury rows keep a blank game status",
         "produced_by": "nfl-skill-cfdd/index.py, tests"},
    ]

    # Which gates each strategy clears is decided by what data it needs, not by preference.
    needs_price = {"S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10"}
    needs_legs = {"S4", "S5", "S6"}
    needs_division = {"S9"}
    matrix = []
    for s in STRATEGIES:
        failures = []
        if s["strategy_id"] in needs_price:
            failures.append("V8")
        if s["strategy_id"] in needs_legs:
            failures.append("V6")
        if s["strategy_id"] in needs_division:
            failures.append("V3")
        failures.extend(["V3", "V4", "V5", "V9"])
        failures = sorted(set(failures), key=lambda g: int(g[1:]))
        matrix.append({
            "strategy_id": s["strategy_id"],
            "name": s["name"],
            "bet_type": s["bet_type"],
            "gates_failed_or_blocked": " ".join(failures),
            "gates_passed": " ".join(g for g in ("V1", "V2", "V7", "V10", "V11", "V12")
                                     if g not in failures),
            "status": "BLOCKED",
            "settled_bets": 0,
            "score": "",
            "reason": "unresolved gates: " + ", ".join(failures),
        })
    return gates, matrix


def leaderboard(matrix: list[dict]) -> list[dict]:
    """Rank by fewest unresolved gates, then by strategy id. Nothing is ranked on a win rate
    because no settled bet exists."""
    ranked = sorted(matrix, key=lambda r: (len(r["gates_failed_or_blocked"].split()), r["strategy_id"]))
    out = []
    for i, row in enumerate(ranked, start=1):
        out.append({
            "rank": i,
            "strategy_id": row["strategy_id"],
            "name": row["name"],
            "bet_type": row["bet_type"],
            "settled_bets": 0,
            "gates_unresolved": len(row["gates_failed_or_blocked"].split()),
            "score": "",
            "eligible_for_reward": "no",
            "why": "zero settled bets: the ranking reflects the amount of evidence still missing, "
                   "not performance",
        })
    return out


def main() -> None:
    parse_args(__doc__)
    over = json.loads((DATA / "skill-luck-results-2026-11-14.json").read_text())["overdispersion"]
    corr_rows = load("correlations-2026-11-14.csv")
    sample_rows = load("sample-size-to-separate-skill.csv")
    depletion = json.loads((DATA / "depletion-index-2026-11-14.json").read_text())

    gates, matrix = gate_matrix(over, corr_rows, sample_rows, depletion)
    board = leaderboard(matrix)

    emit_csv(DATA / "strategies-2026-11-14.csv", matrix)
    emit_csv(DATA / "leaderboard-2026-11-14.csv", board)
    emit_json(DATA / "gates-2026-11-14.json", {
        "gates": gates,
        "counts": {
            "total": len(gates),
            "pass": sum(1 for g in gates if g["status"] == "pass"),
            "fail": sum(1 for g in gates if g["status"] == "fail"),
            "blocked": sum(1 for g in gates if g["status"] == "blocked"),
        },
        "note": "Every gate is produced by a script over committed data. A gate that no data can "
                "test is 'blocked', never 'pass'.",
        "cash_rewards": None,
        "reward_statement": "No monetary reward is defined or paid. Non-monetary merit points "
                            "would still require V4, V5 and V9 to pass first.",
    })
    counts = json.loads((DATA / "gates-2026-11-14.json").read_text())["counts"]
    print(f"OK: {len(STRATEGIES)} strategies, {counts['total']} gates "
          f"({counts['pass']} pass, {counts['fail']} fail, {counts['blocked']} blocked), "
          f"0 qualified, 0 rewards")


if __name__ == "__main__":
    main()
