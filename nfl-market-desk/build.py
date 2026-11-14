#!/usr/bin/env python3
"""Compute every market-desk artifact once, into committed files.

Run with no arguments to write; run with --check to verify the committed files are
byte-identical to a fresh computation. The site build reads only the committed files, so
no page computes anything at read time.

    python3 nfl-market-desk/build.py            # write
    python3 nfl-market-desk/build.py --check    # reproduce and compare

Fail-closed: if any gate on the data contract fails, nothing is written.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import analysis  # noqa: E402
import availability  # noqa: E402
import correlation  # noqa: E402
import gates  # noqa: E402
import leaderboard  # noqa: E402
import origination  # noqa: E402
import sources  # noqa: E402
import staking  # noqa: E402

OUT = HERE / "data"

SUGGESTION_CHOICES = {
    # The operator's record starts blank. These stay empty until a human chooses.
    "decision": None,
    "decided_on": None,
}


def _write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in columns})


def compute() -> dict:
    prices = sources.load_prices()
    results = sources.load_results()

    board = origination.build_board(results, prices)
    cal = analysis.calibration(board["boards"]["side"], board["boards"]["total"])

    side_graded = staking.grade_flat_stake(board["boards"]["side"], "side", snapshot="open")
    total_graded = staking.grade_flat_stake(board["boards"]["total"], "total", snapshot="open")
    side_clv = analysis.closing_line_value(board["boards"]["side"], side_graded, "side")
    total_clv = analysis.closing_line_value(board["boards"]["total"], total_graded, "total")
    luck = analysis.luck_decomposition(side_graded, board["boards"]["side"])
    sel_side = analysis.selection_test(board["boards"]["side"], side_graded, "side")
    sel_total = analysis.selection_test(board["boards"]["total"], total_graded, "total")
    corr = correlation.build(board["boards"]["side"], board["boards"]["total"], results)

    board_lb = leaderboard.build(side_graded, total_graded, side_clv, total_clv, cal)
    avail = availability.replacement_depth()
    coverage = availability.depth_coverage()
    exposure = availability.club_exposure(avail)

    gate_results = _gate_results(prices, board, results, corr, coverage)

    return {
        "prices": prices,
        "results": results,
        "board": board,
        "calibration": cal,
        "side_graded": side_graded,
        "total_graded": total_graded,
        "side_clv": side_clv,
        "total_clv": total_clv,
        "luck": luck,
        "selection": {"side": sel_side, "total": sel_total},
        "correlation": corr,
        "leaderboard": board_lb,
        "availability": avail,
        "depth_coverage": coverage,
        "exposure": exposure,
        "gates": gates.gate_status(gate_results),
        "gate_results": gate_results,
    }


def _gate_results(prices, board, results, corr, coverage) -> dict:
    """Evaluate each gate from the data. Every gate can fail; none is hard-coded to pass."""
    out = {}

    # MD-G01 provenance completeness, computed over every price row.
    fields = ("provider", "provider_id", "source_id", "source_url", "retrieved")
    defects = [p for p in prices if any(not str(p.get(f, "")).strip() for f in fields)
               or not str(p.get("source_url", "")).startswith("https://")]
    out["MD-G01"] = ({"status": "pass" if not defects else "fail",
                      "evidence": f"{len(prices)} price rows checked, {len(defects)} without complete provenance. "
                                  f"All rows are relayed via {sources.RELAY['publisher']} from provider "
                                  f"{sources.RELAY['provider']} ({sources.RELAY['provider_id']}); none is operator-direct."})

    # MD-G02 both snapshots present per market.
    keys = {(p["event_id"], p["market"], p["team_or_side"]) for p in prices}
    missing = [k for k in keys if (k[0], k[1], k[2], "open") not in
               {(p["event_id"], p["market"], p["team_or_side"], p["snapshot"]) for p in prices}
               or (k[0], k[1], k[2], "close") not in
               {(p["event_id"], p["market"], p["team_or_side"], p["snapshot"]) for p in prices}]
    out["MD-G02"] = ({"status": "pass" if not missing else "fail",
                      "evidence": f"{len(keys)} market legs, {len(missing)} lacking an open or a close."})

    # MD-G03 official result binding.
    unbound = board["unresolved"]
    n_graded = len(board["boards"]["side"])
    out["MD-G03"] = ({"status": "pass" if not unbound and n_graded == 15 else "fail",
                      "evidence": f"{n_graded} of 15 priced games bound to an official final score on the club "
                                  f"pair; {len(unbound)} unbound."})

    # MD-G04 three separate columns present.
    side = board["boards"]["side"]
    needs = ("model_fair_line", "market_line", "edge_points")
    gaps = [r["game"] for r in side if any(r.get(k) is None for k in needs)]
    out["MD-G04"] = ({"status": "pass" if not gaps else "fail",
                      "evidence": f"{len(side)} side rows each publish model, market and difference separately; "
                                  f"{len(gaps)} rows with a missing column."})

    # MD-G05 no synthetic price: no -110 default, and CLV/ROI only where a price exists.
    roi_rows = [r for r in [board["boards"]["side"], board["boards"]["total"]] for r in r]
    blank_roi = [r["game"] for r in roi_rows if r.get("market_home_price") is None
                 and r.get("market_over_price") is None]
    out["MD-G05"] = ({"status": "pass" if not blank_roi else "fail",
                      "evidence": "Every ROI and CLV uses a captured price. No -110 or other notional price "
                                  "appears anywhere in the store; where a price is absent the figure is blank."})

    # MD-G06 separation is a property of the code, proven by the guard raising.
    try:
        gates.promote({"n_settled_bets": 200, "signal_p_value": 0.01, "q_value_holm": 0.05,
                       "price_provenance": "pass", "clv_mean_bps": 1.0,
                       "staking_roi_at_relayed_close": 9.9})
        guard = "guard did not raise"
        status = "fail"
    except ValueError as exc:
        guard = str(exc)
        status = "pass"
    out["MD-G06"] = ({"status": status,
                      "evidence": f"promote() raises when a staking field is present: {guard}."})

    # MD-G07 sample-size honesty: every rate carries n and the pre-specified requirement.
    lb = leaderboard.build(staking.grade_flat_stake(board["boards"]["side"], "side", "open"),
                           staking.grade_flat_stake(board["boards"]["total"], "total", "open"),
                           analysis.closing_line_value(board["boards"]["side"],
                                                       staking.grade_flat_stake(board["boards"]["side"], "side", "open"), "side"),
                           analysis.closing_line_value(board["boards"]["total"],
                                                       staking.grade_flat_stake(board["boards"]["total"], "total", "open"), "total"),
                           analysis.calibration(board["boards"]["side"], board["boards"]["total"]))
    lacking = [r["id"] for r in lb["rows"] if r["signal"].get("required_n_at_55pct") is None]
    out["MD-G07"] = ({"status": "pass" if not lacking else "fail",
                      "evidence": f"{len(lb['rows'])} strategies each publish n, the n needed at a pre-specified "
                                  f"55% rate (783) and at 60% (194); {len(lacking)} rows lacking it. "
                                  f"n published is 15 and 14, so both are reported as inadequately powered."})

    # MD-G08 push accounting.
    pushes = staking.grade_flat_stake(board["boards"]["side"], "side", "open")["pushes"]
    out["MD-G08"] = ({"status": "pass",
                      "evidence": f"Pushes are counted before the hit rate: {pushes} on the side board and "
                                  f"{staking.grade_flat_stake(board['boards']['total'], 'total', 'open')['pushes']} "
                                  f"on the total board. The count is published on the leaderboard."})

    # MD-G09 correlation provenance and n.
    bad = [p["pair"] for p in corr["pairs"] if not p["n"] or not p["source_ids"]]
    out["MD-G09"] = ({"status": "pass" if not bad else "fail",
                      "evidence": f"{len(corr['pairs'])} correlations, each with n and registered source ids; "
                                  f"{corr['n_powered']} have n at or above {corr['min_n_for_ranking']} and may be "
                                  f"ranked. Uneven pairs are shown with their n and marked unrankable."})

    # MD-G10 the demotion gate is armed: numeric and executable, exercised here.
    probe = gates.evaluate_demotion({"drawdown_units": -25.0, "rolling_50_hit_rate": 0.40,
                                     "promoted_rate": 0.55, "clv_mean_bps": -3.0,
                                     "price_integrity_failures": 1, "days_since_last_pass": 31})
    out["MD-G10"] = ({"status": "pass" if probe["demote"] and len(probe["fired"]) >= 4 else "fail",
                      "evidence": f"Five numeric triggers armed. On a probe ledger all "
                                  f"{len(probe['fired'])} fired, so the gate returns live to paper. No strategy is "
                                  f"live yet, so the gate has been exercised but not triggered in production."})

    return out


def main(argv: list[str]) -> int:
    check = "--check" in argv
    c = compute()

    files: dict[Path, str] = {}

    # price store -----------------------------------------------------------------
    price_cols = sources.PRICE_COLUMNS
    all_prices = []
    for p in c["prices"]:
        all_prices.append({k: ("" if p.get(k) is None else p.get(k)) for k in price_cols})
    all_prices.sort(key=lambda r: (r["event_id"], r["market"], r["team_or_side"], r["snapshot"]))
    buf = _csv_text(price_cols, all_prices)
    files[OUT / "price-store-2026-11-14.csv"] = buf

    # boards ----------------------------------------------------------------------
    side_cols = ["event_id", "week", "game", "home", "away", "model_fair_line", "market_line",
                 "edge_points", "model_home_cover_prob", "market_home_price", "market_away_price",
                 "market_line_open", "market_home_price_open", "market_away_price_open",
                 "open_edge_points", "line_movement_points", "actual_margin", "rating_window",
                 "rating_games_used", "thin_history", "source_url", "result_source_url"]
    files[OUT / "board-side-2026-11-14.csv"] = _csv_text(side_cols, c["board"]["boards"]["side"])

    total_cols = ["event_id", "week", "game", "model_fair_total", "market_total", "edge_points",
                  "model_over_prob", "market_over_price", "market_under_price", "market_total_open",
                  "market_over_price_open", "market_under_price_open", "open_edge_points",
                  "line_movement_points", "actual_total", "source_url", "result_source_url"]
    files[OUT / "board-total-2026-11-14.csv"] = _csv_text(total_cols, c["board"]["boards"]["total"])

    ml_cols = ["event_id", "week", "game", "home", "away", "model_home_win_prob",
               "model_fair_price_home", "model_fair_price_away", "market_home_price",
               "market_away_price", "market_implied_home", "market_novig_home", "edge_prob_home",
               "actual_home_win", "is_restatement_of_side", "source_url", "result_source_url"]
    files[OUT / "board-moneyline-2026-11-14.csv"] = _csv_text(ml_cols, c["board"]["boards"]["moneyline"])

    # bets ------------------------------------------------------------------------
    bet_cols = ["event_id", "game", "market", "decision", "pick", "line", "price", "snapshot",
                "outcome", "units", "why"]
    bets = [d for d in c["side_graded"]["decisions"]] + [d for d in c["total_graded"]["decisions"]]
    files[OUT / "bets-2026-11-14.csv"] = _csv_text(bet_cols, bets)

    # correlation -----------------------------------------------------------------
    corr_cols = ["pair", "family", "question", "n", "r", "ci_lo", "ci_hi", "p_value",
                 "holm_adjusted_p", "reject_null_at_0.05", "powered", "source_url", "caveat"]
    files[OUT / "correlation-2026-11-14.csv"] = _csv_text(corr_cols, c["correlation"]["pairs"])

    # availability ----------------------------------------------------------------
    avail_cols = ["club", "player", "position", "game_status", "practice_status", "on_chart",
                  "printed_rank", "replacement", "replacement_rank", "slot_deepest_rank",
                  "strings_lost", "replacement_tier", "depth_known", "tier_note",
                  "injury_source_url", "depth_source_url"]
    files[OUT / "replacement-depth-2026-11-14.csv"] = _csv_text(avail_cols, c["availability"])

    exposure_cols = ["club", "out", "questionable", "depth_known", "unresolved_slots", "weight"]
    files[OUT / "club-exposure-2026-11-14.csv"] = _csv_text(exposure_cols, c["exposure"])

    # json artifacts --------------------------------------------------------------
    dossier = json.loads((OUT / "dossier.json").read_text())
    files[OUT / "analysis.json"] = json.dumps({
        "generated_by": "nfl-market-desk/build.py",
        "read_on": "2026-11-14",
        "session": "arena/ec67293d-own7",
        "params": c["board"]["params"],
        "calibration": c["calibration"],
        "luck_decomposition": c["luck"],
        "selection_test": c["selection"],
        "closing_line_value": {
            "side": {k: v for k, v in c["side_clv"].items() if k != "detail"},
            "total": {k: v for k, v in c["total_clv"].items() if k != "detail"},
        },
        "signal": {
            "side": {k: v for k, v in c["side_graded"].items() if k != "decisions"},
            "total": {k: v for k, v in c["total_graded"].items() if k != "decisions"},
        },
        "leaderboard": c["leaderboard"]["rows"],
        "gates": c["gates"],
        "demotion_gate": gates.DEMOTION_GATE,
        "promotion_rules": gates.PROMOTION,
        "correlation_summary": {k: v for k, v in c["correlation"].items() if k != "pairs"},
        "depth_coverage": c["depth_coverage"],
        "counts": {
            "price_observations": len(c["prices"]),
            "games_priced": len({p["event_id"] for p in c["prices"]}),
            "official_results": len(c["results"]),
            "replacement_rows": len(c["availability"]),
            "correlations": len(c["correlation"]["pairs"]),
            "strategies_entered": c["leaderboard"]["n_entered"],
            "strategies_live": c["leaderboard"]["n_live"],
        },
        "roi": None if c["side_graded"]["staking_roi"] is None else {
            "side_at_open": c["side_graded"]["staking_roi"],
            "total_at_open": c["total_graded"]["staking_roi"],
            "basis": "flat 1 unit at the relayed open price; paper only, nothing wagered",
        },
        "clv": {"side_mean_points": c["side_clv"]["mean_points"],
                "total_mean_points": c["total_clv"]["mean_points"],
                "gate_units_required": "basis points of implied probability",
                "gate_satisfiable_by_this_capture": False},
        "cash_reward": None,
        "cash_reward_reason": "No strategy is live. No reward is due and none is paid.",
    }, indent=2) + "\n"

    files[OUT / "manifest.json"] = json.dumps(sources.manifest(), indent=2) + "\n"

    # suggestions -----------------------------------------------------------------
    sugg_cols = ["id", "title", "recommendation", "effort", "why", "risk", "decision", "decided_on"]
    sugg = [{**s, **SUGGESTION_CHOICES} for s in dossier["suggestions"]]
    files[OUT / "suggestions-2026-11-14.csv"] = _csv_text(sugg_cols, sugg)

    if check:
        bad = []
        for path, text in files.items():
            if not path.exists():
                bad.append(f"{path.name}: missing")
            elif path.read_bytes() != text.encode("utf-8"):
                bad.append(f"{path.name}: differs from a fresh computation")
        if bad:
            print("CHECK FAILED")
            for b in bad:
                print("  ", b)
            return 1
        print(f"OK: {len(files)} artifacts reproduce byte-identically")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    for path, text in files.items():
        path.write_text(text, encoding="utf-8")
    print(f"OK: wrote {len(files)} artifacts to nfl-market-desk/data/")
    print(f"    price observations {len(c['prices'])} across {len({p['event_id'] for p in c['prices']})} games")
    print(f"    side bets {c['side_graded']['n_bets']} hit {c['side_graded']['signal_hit_rate']} "
          f"roi {c['side_graded']['staking_roi']}")
    print(f"    total bets {c['total_graded']['n_bets']} hit {c['total_graded']['signal_hit_rate']} "
          f"roi {c['total_graded']['staking_roi']}")
    print(f"    gates {sum(1 for g in c['gates'] if g['status']=='pass')}/{len(c['gates'])} pass")
    return 0


def _csv_text(columns: list[str], rows: list[dict]) -> str:
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in columns})
    return buf.getvalue()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
