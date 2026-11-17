#!/usr/bin/env python3
"""Origination, ablation, matchup exposure, week diff and settlement from the stored corpus.

Builds five artefacts, all deterministic and all derived from files already committed:

  origination.json   the three stages in the registered order (side, then total, then moneyline),
                     each with fair line, benchmark line and the residual as separate columns, plus
                     the two total estimators published side by side with their gap.
  ablation.json      the same model with and without a personnel feature. The feature cannot be
                     built (no verified availability), so the "with" arm is empty *by construction*
                     and that is itself the finding — stated with the interval that would be
                     required to call it either way.
  matchup.json       station-by-station deficiency exposure: who is printed at rank 1, who is
                     printed behind them, whether either is on this week's report. One side only;
                     the cross-side matrix needs both clubs' charts and is gated.
  diff.json          what changed between the prior desk's capture and this one, per club.
  settlement.json    what a selection would have paid, and why no payment is claimed.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = HERE / "data"


def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def brier(p: float, o: bool) -> float:
    return (p - (1.0 if o else 0.0)) ** 2


def cluster_se(pairs: list[tuple[int, float]]) -> float:
    """Bootstrap-free cluster-robust SE over kickoff weeks for a mean of per-observation values."""
    weeks: dict[int, list[float]] = {}
    for w, v in pairs:
        weeks.setdefault(w, []).append(v)
    n = len(pairs)
    groups = len(weeks)
    if groups < 2:
        return float("nan")
    grand = sum(v for _, v in pairs) / n
    var = sum((sum(vals) - grand * len(vals)) ** 2 for vals in weeks.values())
    return math.sqrt(var / (n * n) * groups / (groups - 1))


def origination(backtest: dict) -> dict:
    games = backtest["games"]
    stages = []
    for market, key_fair, key_bench, key_res, key_actual, key_p, key_o in (
            ("side", "fair_margin", "benchmark_side_line", "residual_side", "actual_margin",
             "p_home_cover", "home_covered"),
            ("total", "fair_total", "benchmark_total_line", "residual_total", "actual_total",
             "p_over", "went_over"),
            ("moneyline", "fair_margin", "benchmark_side_line", "residual_side", None,
             "p_home_win", "home_won")):
        rows = []
        for g in games:
            f = g["forecasts"]["M04"]
            rows.append({
                "id": g["id"], "week": g["week"],
                "fair": f[key_fair], "benchmark": g[key_bench], "residual": f[key_res],
                "probability": f[key_p], "actual": g[key_actual] if key_actual else "",
                "outcome": g[key_o], "source_url": g["source_url"],
                "source_ids": ["X29-NFL-SCHEDULE"],
            })
        ordered = sorted(rows, key=lambda r: (-abs(r["residual"]), r["id"]))
        stages.append({
            "stage": market, "order": len(stages) + 1,
            "depends_on": "" if not stages else stages[-1]["stage"],
            "rows": len(rows),
            "mean_abs_residual": round(sum(abs(r["residual"]) for r in rows) / len(rows), 6),
            "largest": ordered[:5],
            "all": rows,
            "market_column": "",
            "market_column_reason": ("The market line is blank: no registered publisher of NFL prices is "
                                     "licensed for this use, so the difference column cannot be computed "
                                     "against a market number. The residual shown is against the frozen "
                                     "benchmark, which is a model number, not a market number."),
        })
    # Two total estimators, published side by side until one wins a walk-forward comparison.
    totals = []
    for g in games:
        a = g["forecasts"]["M01"]["fair_total"]
        b = g["forecasts"]["M03"]["fair_total"]
        totals.append({"id": g["id"], "m01": a, "m03": round(b, 6), "gap": round(b - a, 6),
                       "actual": g["actual_total"], "source_ids": ["X29-NFL-SCHEDULE"]})
    err1 = [abs(t["m01"] - t["actual"]) for t in totals]
    err2 = [abs(t["m03"] - t["actual"]) for t in totals]
    diff_sd = (sum((t["gap"] - sum(x["gap"] for x in totals) / len(totals)) ** 2 for t in totals)
               / (len(totals) - 1)) ** 0.5
    actual_sd = (sum((t["actual"] - sum(x["actual"] for x in totals) / len(totals)) ** 2
                     for t in totals) / (len(totals) - 1)) ** 0.5
    wins_m03 = sum(1 for a, b_ in zip(err1, err2) if b_ < a)
    wins_m01 = sum(1 for a, b_ in zip(err1, err2) if a < b_)
    return {
        "schema_version": 1,
        "order": ["side", "total", "moneyline"],
        "order_note": ("The stages are run in this order because a side price comes from the margin "
                       "distribution, a total from the same distribution's scoring level, and a "
                       "moneyline from the margin distribution without a line. Running the total first "
                       "would let a total assumption leak into the margin."),
        "model": "M04",
        "stages": stages,
        "two_total_estimators": {
            "rule": "Both estimators stay visible with a gap column until a walk-forward comparison picks one. No estimator has been retired.",
            "rows": totals,
            "mae_m01": round(sum(err1) / len(err1), 6),
            "mae_m03": round(sum(err2) / len(err2), 6),
            "games_m03_closer": wins_m03, "games_m01_closer": wins_m01,
            "mean_gap": round(sum(t["gap"] for t in totals) / len(totals), 6),
            "gap_sd": round(diff_sd, 6),
            "actual_total_sd": round(actual_sd, 6),
            "verdict": (
                f"M03 is {round(sum(err1) / len(err1) - sum(err2) / len(err2), 4)} points of mean "
                f"absolute error closer to the truth and wins {wins_m03} of {len(totals)} games against "
                f"M01's {wins_m01}. The two lines differ by a standard deviation of {diff_sd:.2f} points "
                f"against an actual-total spread of {actual_sd:.2f}, so the disagreement is small but "
                f"not zero. Neither is retired: a win on 120 retrospective games is not a walk-forward "
                f"result, and the registration forbids collapsing the pair on the evaluation window."),
        },
        "fixture_level_forecast": {
            "note": ("No Week 11 fixture forecast is published as a numeric line: the only official "
                     "inputs held for Week 11 are the schedule and the injury report, and the model's "
                     "inputs are prior results, which do not exist for a future week. Publishing a "
                     "number here would require the model to be re-specified on incomplete inputs. "
                     "The gate that blocks it is V8 (no prospective record)."),
            "rows": 0,
        },
    }


def ablation(backtest: dict, availability: dict) -> dict:
    games = backtest["games"]
    with_arm = []
    without_arm = []
    for g in games:
        f = g["forecasts"]["M04"]["p_home_cover"]
        without_arm.append((g["week"], brier(f, g["home_covered"])))
        # The personnel arm would add a term for a confirmed absence. No absence in this corpus is
        # confirmed (no inactive list, no Game Book), so the arm cannot be populated.
        with_arm.append((g["week"], None))
    populated = [x for _, x in with_arm if x is not None]
    base = [x for _, x in without_arm]
    bs = sum(base) / len(base)
    se = cluster_se(without_arm)
    # The interval a difference would need before the ablation could be read either way.
    needed = 1.96 * se * math.sqrt(2)
    return {
        "schema_version": 1,
        "question": "Does adding verified availability information change the model, and by how much?",
        "design": ("Identical model, identical games, identical holdout. Only the personnel feature "
                   "changes. This is the alternative to subtracting a fixed number of points for a "
                   "missing starter, which no test in this repository supports."),
        "arms": {
            "without_personnel": {
                "rows": len(base), "brier": round(bs, 6), "cluster_se": round(se, 6),
                "interval": [round(bs - 1.96 * se, 6), round(bs + 1.96 * se, 6)],
            },
            "with_personnel": {
                "rows": len(populated), "brier": "", "cluster_se": "",
                "interval": ["", ""],
                "empty_because": ("No absence in the corpus is confirmed. A depth-chart rank is not "
                                  "participation, and no inactive list, Game Book or snap count is "
                                  "captured (gates PG-ACTUAL-STARTER and PG-INACTIVE)."),
            },
        },
        "difference": {"value": "", "interval": ["", ""],
                       "would_be_readable_if": f"the paired 95% interval excluded zero; at this n the cluster SE of one arm is {se:.4f}, so a difference smaller than about {needed:.4f} Brier would be indistinguishable from noise"},
        "fixed_point_penalties_in_pipeline": 0,
        "why_not_a_penalty": [
            "A fixed penalty encodes a belief about a player's value that has not been measured.",
            "The measurement needs (a) a confirmed absence and (b) the same model run twice. (a) is missing.",
            "Publishing the penalty anyway would make the model look informed while resting on an unmeasured assumption.",
        ],
        "what_would_fill_the_arm": ("One season of official inactive lists joined to the corpus, so each "
                                    "game carries the set of confirmed absent starters. That is 136 "
                                    "inactive lists, of which 0 are captured."),
        "source_ids": ["X29-NFL-SCHEDULE", "RD-NFL-INJ-W10"],
    }


def matchup(availability: dict) -> dict:
    chains = availability["replacement_chains"]
    slots = availability["depth_slots"]
    rows = []
    for club in sorted({s["club"] for s in slots}):
        club_chains = {(c["player"], c.get("slot")): c for c in chains if c["club"] == club}
        for s in [x for x in slots if x["club"] == club]:
            for i, name in enumerate(s["rank1"]):
                chain = next((c for c in chains if c["club"] == club and c["player"] == name), None)
                backup = s["deeper"][0] if s["deeper"] else ""
                backup_row = next((c for c in chains if c["club"] == club and c["player"] == backup), None)
                rows.append({
                    "id": f"{club}-{s['unit'][:3]}-{s['slot']}-{i+1}",
                    "club": club, "unit": s["unit"], "slot": s["slot"], "depth": 1,
                    "player": name,
                    "on_report": "yes" if chain else "no",
                    "game_status": chain["status"] if chain else "",
                    "printed_backup": backup,
                    "backup_on_report": ("yes" if backup_row else "no") if backup else "",
                    "backup_status": backup_row["status"] if backup_row else "",
                    "exposure": ("starter out, backup available" if chain and chain["status"] == "Out" and backup
                                 else "starter out, no printed backup" if chain and chain["status"] == "Out"
                                 else "starter doubtful, backup available" if chain and chain["status"] == "Doubtful" and backup
                                 else "starter questionable" if chain and chain["status"] == "Questionable"
                                 else "no confirmed absence"),
                    "cross_side_matrix": "",
                    "cross_side_reason": ("Pairing this slot against an opponent's slot needs the "
                                          "opponent's chart. This desk holds 6 charts and none of the 6 "
                                          "clubs' Week 10 opponents is among them."),
                    "source_ids": s["source_ids"] + (["RD-NFL-INJ-W10"] if chain else []),
                })
    exposures = {}
    for r in rows:
        exposures[r["exposure"]] = exposures.get(r["exposure"], 0) + 1
    by_unit = {}
    for r in rows:
        key = f"{r['unit']}-{r['exposure']}"
        by_unit[key] = by_unit.get(key, 0) + 1
    return {
        "schema_version": 1,
        "question": "Which printed starters are replaced, and by whom, at each station?",
        "rows": rows,
        "counts": {"rows": len(rows), "by_exposure": exposures, "by_unit_and_exposure": by_unit,
                   "clubs_covered": len({r['club'] for r in rows}), "clubs_without_chart": 32 - len({r['club'] for r in rows})},
        "truth_depths": {"rank_1_groups": sum(1 for r in rows if r["depth"] == 1),
                         "multi_player_rank_1": availability["totals"]["multi_rank1_cells"],
                         "slots_with_2_plus_printed_ranks": len({(r['club'], r['slot']) for r in rows if r['printed_backup']})},
        "limits": [
            "A printed rank is not playing time. The 1st-to-4th string claim in the brief needs snap counts.",
            "Houston publishes an image, so the Texans have no row here.",
            "Six of 32 clubs are covered by this desk's own read; the cross-side offence-versus-defence matrix needs both clubs' charts.",
        ],
        "source_ids": ["RD-DET-CHART", "RD-GB-CHART", "RD-SEA-CHART", "RD-BAL-CHART",
                       "RD-WAS-CHART", "RD-IND-CHART", "RD-NFL-INJ-W10"],
    }


def diff(availability: dict) -> dict:
    """What changed between the inherited 2026-11-12 capture and this 2026-11-17 read."""
    # The inherited capture holds 20 rows from the Thursday game only (verified by reading the file).
    inherited_rows = 20
    live_rows = availability["totals"]["injury_rows"]
    clubs_now = availability["totals"]["clubs_with_report"]
    per_club = availability["clubs"]
    rows = []
    for club in per_club:
        if not club["rows"]:
            rows.append({"id": club["id"], "club": club["club"], "rows_prior": "", "rows_now": 0,
                         "change": "", "note": "On bye in Week 10, so the live report prints no section for this club.",
                         "source_ids": club["source_ids"]})
            continue
        rows.append({"id": club["id"], "club": club["club"], "rows_prior": "",
                     "rows_now": club["rows"], "change": "",
                     "note": ("The prior capture is a single-game sample and a club-level comparison is not "
                              "like for like, so the prior value stays blank rather than being assumed equal."),
                     "source_ids": club["source_ids"]})
    return {
        "schema_version": 1,
        "prior_capture": {"read": "2026-11-12", "file": "data/nfl-injuries-2026-w10.csv",
                          "rows": inherited_rows, "scope": "one game (Thursday), two clubs",
                          "source_ids": ["RD-NFL-INJ-W10"]},
        "this_capture": {"read": "2026-11-17", "file": "nfl-readiness/evidence/injury-report-2026-reg10-2026-11-17.md",
                         "rows": live_rows, "scope": f"all {clubs_now} clubs with a Week 10 game",
                         "source_ids": ["RD-NFL-INJ-W10"]},
        "row_delta": live_rows - inherited_rows,
        "delta_is_not_an_injury_trend": ("The two captures cover different scopes, so their row difference "
                                        "measures coverage, not injuries. A trend needs two reads of the "
                                        "same scope (PG-SERIES)."),
        "per_club": rows,
        "practice_trend": {
            "rows": 0,
            "why": ("A practice trend needs the same player read on two dates (DNP then LP then FP). This "
                    "desk holds one dated read, so the trend column is empty."),
            "would_need": "the Wednesday, Thursday and Friday reports of the same week",
        },
        "source_ids": ["RD-NFL-INJ-W10"],
    }


def settlement() -> dict:
    return {
        "schema_version": 1,
        "question": "If a selection had been made, what would it have paid?",
        "answer": "",
        "why_blank": ("A payout needs a price. No price is registered, and inventing a standard -110 "
                      "would be an assumption about an operator that this repository has not read."),
        "what_is_published_instead": {
            "probabilities": "in backtest.json, one per market per game",
            "outcomes": "the official final score of every game",
            "what_would_be_needed": "1 registered price per selection, with the operator's void and push rules",
        },
        "breakeven_arithmetic": [
            {"price": "-110", "breakeven_probability": round(1.1 / 2.1, 6),
             "note": "Printed as arithmetic only. It is not a price this project claims to have been offered."},
            {"price": "-105", "breakeven_probability": round(1.05 / 2.05, 6), "note": "Same caveat."},
        ],
        "source_ids": ["RD-NFL-TERMS"],
    }


def main() -> int:
    DATA.mkdir(exist_ok=True)
    backtest = json.loads((DATA / "backtest.json").read_text())
    availability = json.loads((DATA / "availability.json").read_text())
    targets = {
        "origination.json": origination(backtest),
        "ablation.json": ablation(backtest, availability),
        "matchup.json": matchup(availability),
        "diff.json": diff(availability),
        "settlement.json": settlement(),
    }
    stale = []
    for name, payload in targets.items():
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        path = DATA / name
        if "--check" in sys.argv:
            if not path.exists() or path.read_text() != text:
                stale.append(name)
        else:
            path.write_text(text)
    if stale:
        raise SystemExit("stale analysis artefacts: " + ", ".join(stale))
    print("OK: origination, ablation, matchup, diff, settlement" if "--check" in sys.argv
          else "Wrote origination, ablation, matchup, diff, settlement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
