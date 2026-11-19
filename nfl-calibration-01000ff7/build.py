"""Walk-forward calibration audit for the existing NFL moneyline probability model.

This desk consumes the already-frozen origination model and official-result feed. It does
not fit or alter a model, import market prices, or rank wagers. Game rows are prequential:
only results from weeks strictly before the target game are used to originate its p(home).
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SITE = HERE / "site"
MODEL_DIR = ROOT / "nfl-competition"
MODEL = MODEL_DIR / "backtest.py"
RESULTS_FEED = ROOT / "nfl-results" / "data" / "games-2026-w1-10-complete.csv"
REGISTRY = ROOT / "research" / "sources.json"
OUT_JSON = DATA / "calibration.json"
OUT_CSV = DATA / "game-probabilities.csv"
BOOTSTRAP_REPS = 5000
BOOTSTRAP_SEED = 20261119
BIN_COUNT = 5
LOW_BIN_N = 10

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_backtest_module():
    sys.path.insert(0, str(MODEL_DIR))
    spec = importlib.util.spec_from_file_location("own7_calibration_backtest", MODEL)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load the registered competition backtest module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def registry_map() -> dict[str, dict[str, Any]]:
    rows = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {row["id"]: row for row in rows}


def clamp_bin(p: float) -> int:
    return min(BIN_COUNT - 1, max(0, int(p * BIN_COUNT)))


def brier(rows: list[dict[str, Any]]) -> float | None:
    binary = [r for r in rows if r["outcome_home_win"] is not None]
    return (sum((r["p_home_given_no_tie"] - r["outcome_home_win"]) ** 2 for r in binary) / len(binary)) if binary else None


def multiclass_brier(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    scores = []
    for row in rows:
        outcome = row["outcome"]
        y = {"HOME_WIN": 1.0 if outcome == "HOME_WIN" else 0.0,
             "AWAY_WIN": 1.0 if outcome == "AWAY_WIN" else 0.0,
             "TIE": 1.0 if outcome == "TIE" else 0.0}
        probabilities = {"HOME_WIN": row["p_home"], "AWAY_WIN": row["p_away"], "TIE": row["p_tie"]}
        scores.append(sum((probabilities[key] - y[key]) ** 2 for key in y))
    return sum(scores) / len(scores)


def calibration_error(rows: list[dict[str, Any]]) -> float | None:
    rows = [r for r in rows if r["outcome_home_win"] is not None]
    if not rows:
        return None
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[clamp_bin(row["p_home_given_no_tie"])].append(row)
    return sum(len(group) / len(rows) * abs(
        sum(r["p_home_given_no_tie"] for r in group) / len(group) -
        sum(r["outcome_home_win"] for r in group) / len(group))
        for group in grouped.values())


def bootstrap(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_week: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_week[row["week"]].append(row)
    weeks = sorted(by_week)
    if len(weeks) < 2:
        return {"cluster": "target week", "clusters": len(weeks), "reps": 0,
                "seed": BOOTSTRAP_SEED, "brier_skill_ci95": [None, None],
                "multiclass_brier_skill_ci95": [None, None],
                "calibration_error_ci95": [None, None], "flag": "fewer than two target-week clusters"}
    rng = random.Random(BOOTSTRAP_SEED)
    skills: list[float] = []
    multiclass_skills: list[float] = []
    errors: list[float] = []
    for _ in range(BOOTSTRAP_REPS):
        chosen = [rng.choice(weeks) for __ in weeks]
        sample = [row for week in chosen for row in by_week[week]]
        score = brier(sample)
        if score is not None:
            skills.append(1.0 - score / 0.25)
        multi_score = multiclass_brier(sample)
        if multi_score is not None:
            multiclass_skills.append(1.0 - multi_score / (2.0 / 3.0))
        err = calibration_error(sample)
        if err is not None:
            errors.append(err)
    def interval(values: list[float]) -> list[float | None]:
        values.sort()
        if not values:
            return [None, None]
        return [round(values[int(0.025 * (len(values) - 1))], 6),
                round(values[int(0.975 * (len(values) - 1))], 6)]
    return {"cluster": "target week", "clusters": len(weeks), "reps": len(skills),
            "seed": BOOTSTRAP_SEED, "brier_skill_ci95": interval(skills),
            "multiclass_brier_skill_ci95": interval(multiclass_skills),
            "calibration_error_ci95": interval(errors),
            "flag": "Only a small number of weekly clusters; percentile interval is exploratory, not a qualification test."}


def build_model() -> dict[str, Any]:
    module = load_backtest_module()
    registry = registry_map()
    official_rows = read_csv(RESULTS_FEED)
    if len(official_rows) != 150:
        raise ValueError(f"Completed official result corpus drift: expected 150 rows, got {len(official_rows)}")
    feed_by_id = {}
    normalized = []
    for index, row in enumerate(official_rows, start=1):
        game_id = f"G{index:03d}"
        week = int(row["week"])
        home_score, away_score = int(row["home_score"]), int(row["away_score"])
        if week < 10:
            primary_id = f"CAL-RESULTS-W{week:02d}-1114"
            source_url = row["source_url"]
        elif row["away"] == "LAC" and row["home"] == "BAL":
            # This final was appended from the Nov 18 completion re-read; cite that exact read.
            primary_id = "FRESH-NFL-W10-COMPLETE-1118"
            source_url = registry[primary_id]["url"]
        else:
            primary_id = "E15-NFL-SCHED-REG10-1117"
            source_url = row["source_url"]
        normalized.append({
            "game_id": game_id, "week": week, "date": row["date"],
            "home": row["home"], "away": row["away"],
            "home_score": home_score, "away_score": away_score,
            "home_margin": home_score - away_score,
            "total_points": home_score + away_score,
            "source_url": source_url,
        })
        feed_by_id[game_id] = {**row, "game_id": game_id,
                               "source_url": source_url, "source_ids": primary_id}
    # Use the unchanged competition model with the completed official result corpus.
    # The model's own forecasts() enforces `week < target_week` for each forecast.
    module.load_feed = lambda: normalized
    forecasts = module.forecasts()
    scored = []
    flags = []
    for forecast in forecasts:
        source = feed_by_id.get(forecast["game_id"])
        if not source:
            flags.append({"code": "MISSING_FEED_ROW", "game_id": forecast["game_id"],
                          "detail": "Forecast has no row in the official completed result feed."})
            continue
        source_ids = [s.strip() for s in source.get("source_ids", "").split(";") if s.strip()]
        if len(source_ids) != 1:
            flags.append({"code": "NO_UNIQUE_PRIMARY_SOURCE", "game_id": forecast["game_id"],
                          "detail": "No unique registered source ID was assigned to the exact by-week page."})
            continue
        sid = source_ids[0]
        registration = registry.get(sid)
        if not registration:
            flags.append({"code": "UNREGISTERED_SOURCE", "game_id": forecast["game_id"],
                          "detail": f"Primary source ID {sid} is not registered."})
            continue
        if registration["url"] != source["source_url"]:
            flags.append({"code": "SOURCE_URL_MISMATCH", "game_id": forecast["game_id"],
                          "detail": f"Primary source {sid} URL does not match the exact result URL."})
            continue
        links = [{"id": sid, "url": registration["url"], "title": registration["title"]}]
        target_week = int(forecast["week"])
        prior_rows = [r for r in normalized if int(r["week"]) < target_week]
        margin_stats = module.measured_home_margin(prior_rows)
        tie_rate_prior = (sum(1 for r in prior_rows if r["home_margin"] == 0) / len(prior_rows)) if prior_rows else 0.0
        z = float(forecast["proj_margin"]) / margin_stats["sd"]
        recomputed_probability = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0))) * (1.0 - tie_rate_prior)
        if abs(recomputed_probability - float(forecast["p_home"])) > 1e-12:
            raise ValueError(f"Probability input mismatch for {forecast['game_id']}")
        if tie_rate_prior >= 1.0:
            raise ValueError(f"Cannot condition on no tie when prior tie rate is 1 for {forecast['game_id']}")
        p_home = float(forecast["p_home"])
        p_tie = float(tie_rate_prior)
        p_away = 1.0 - p_home - p_tie
        outcome_home_win = forecast["home_win"]
        outcome = "TIE" if outcome_home_win is None else ("HOME_WIN" if outcome_home_win else "AWAY_WIN")
        p_home_given_no_tie = p_home / (1.0 - p_tie)
        if abs(p_home + p_away + p_tie - 1.0) > 1e-12 or min(p_home, p_away, p_tie) < 0:
            raise ValueError(f"Moneyline probability vector is invalid for {forecast['game_id']}")
        scored.append({
            "game_id": forecast["game_id"], "week": int(forecast["week"]),
            "date": source["date"], "matchup": f'{forecast["away"]} @ {forecast["home"]}',
            "home": forecast["home"], "away": forecast["away"],
            "p_home": p_home, "p_away": p_away, "p_tie": p_tie,
            "p_home_given_no_tie": p_home_given_no_tie,
            "outcome": outcome,
            "outcome_home_win": None if outcome_home_win is None else int(outcome_home_win),
            "probability_inputs": {"projected_home_margin": float(forecast["proj_margin"]),
                                   "margin_sd": float(margin_stats["sd"]),
                                   "tie_rate_prior": float(tie_rate_prior)},
            "prior_games": int(forecast["prior_games"]),
            "prior_home_games": int(forecast["prior_home_games"]),
            "prior_away_games": int(forecast["prior_away_games"]),
            "target_week": int(forecast["week"]),
            "source_url": source["source_url"], "source_ids": source_ids,
            "sources": links,
        })

    if flags:
        # A source-integrity failure must not silently reduce the sample and still publish.
        raise ValueError("Source-integrity flags prevent publication: " + json.dumps(flags[:5]))
    if not scored:
        raise ValueError("No non-tie forecasts with verified official result sources")
    if any(r["prior_games"] < 1 or r["prior_home_games"] < 1 or r["prior_away_games"] < 1 for r in scored):
        raise ValueError("Look-ahead/eligibility invariant failed: forecast lacks prior games")
    if any(not (0.0 < r["p_home"] < 1.0) for r in scored):
        raise ValueError("Model probability outside open interval (0, 1)")

    bins = []
    for idx in range(BIN_COUNT):
        lower, upper = idx / BIN_COUNT, (idx + 1) / BIN_COUNT
        group = [r for r in scored if r["outcome_home_win"] is not None and
                 clamp_bin(r["p_home_given_no_tie"]) == idx]
        bins.append({
            "bin": idx + 1, "range": f"[{lower:.1f}, {upper:.1f}{']' if idx == BIN_COUNT-1 else ')'}",
            "n": len(group),
            "mean_predicted_home_win": round(sum(r["p_home_given_no_tie"] for r in group) / len(group), 6) if group else None,
            "observed_home_win_rate": round(sum(r["outcome_home_win"] for r in group) / len(group), 6) if group else None,
            "absolute_gap": round(abs(sum(r["p_home"] for r in group) / len(group) -
                                      sum(r["outcome_home_win"] for r in group) / len(group)), 6) if group else None,
            "flag": "Low n; descriptive only" if len(group) < LOW_BIN_N else None,
            "game_ids": [r["game_id"] for r in group],
            "source_ids": sorted({sid for r in group for sid in r["source_ids"]}),
            "sources": sorted({(s["id"], s["url"], s["title"])
                               for r in group for s in r["sources"]}),
        })

    score = brier(scored)
    baseline = 0.25
    multi_score = multiclass_brier(scored)
    multi_baseline = 2.0 / 3.0
    binary_n = sum(r["outcome_home_win"] is not None for r in scored)
    summary = {
        "desk": "nfl-calibration-01000ff7", "as_of": "2026-11-19",
        "model": "Existing nfl-competition three-stage origination; unchanged.",
        "scope": "Walk-forward three-outcome moneyline probability assessment; binary calibration is conditional on no tie; no market prices or staking.",
        "n": len(scored), "binary_n": binary_n,
        "target_weeks": sorted({r["week"] for r in scored}),
        "binary_brier_given_no_tie": round(score, 6), "constant_50pct_binary_brier": baseline,
        "binary_brier_skill_vs_50pct": round(1 - score / baseline, 6),
        "multiclass_brier": round(multi_score, 6), "uniform_three_outcome_brier": round(multi_baseline, 6),
        "multiclass_brier_skill_vs_uniform": round(1 - multi_score / multi_baseline, 6),
        "weighted_calibration_error_5_bins": round(calibration_error(scored), 6),
        "bootstrap": bootstrap(scored), "bins": bins, "games": scored,
        "interpretation": [
            "Binary Brier skill is 1 - conditional-on-no-tie model Brier / 0.25; positive values beat a constant 50% probability on this sample, not a market or an investable benchmark.",
            "The three-outcome Brier scores home win, away win and tie probabilities for every game; its uniform no-skill reference is 2/3 and its skill value is not a market benchmark.",
            "For binary scoring, p(home | no tie) is derived as p(home) / (1 - p(tie)); ties remain in the separate three-outcome score and are not recoded as losses or wins.",
            "Five-bin binary calibration gaps are descriptive. Bins with fewer than 10 games are flagged and should not support a stand-alone claim.",
            "The percentile intervals resample target weeks (not independent games) to acknowledge within-week dependence. With few weeks, intervals are exploratory and cannot qualify a strategy.",
            "These are repository-recomputed model outputs paired with official NFL final-result sources. The results feed is not proof of permission for systematic future collection; no capture automation is introduced.",
        ],
        "flags": [],
        "input_sha256": {str(RESULTS_FEED.relative_to(ROOT)): sha256(RESULTS_FEED),
                         str(MODEL.relative_to(ROOT)): sha256(MODEL),
                         str(REGISTRY.relative_to(ROOT)): sha256(REGISTRY)},
    }
    return summary


def render_page(model: dict[str, Any]) -> str:
    cards = "".join(f'<div class="card"><b>{value}</b><span>{label}</span></div>' for value, label in [
        (model["n"], "forecast games, including ties"), (model["binary_n"], "non-tie games in binary score"),
        (model["binary_brier_given_no_tie"], "binary Brier, conditional on no tie"),
        (model["multiclass_brier_skill_vs_uniform"], "3-outcome Brier skill vs uniform"),
        (model["weighted_calibration_error_5_bins"], "5-bin conditional calibration gap")])
    rows = []
    for r in model["games"]:
        sources = " ".join(f'<a href="{esc(s["url"])}" rel="noopener">{esc(s["id"])}</a>' for s in r["sources"])
        inputs = r["probability_inputs"]
        rows.append(f'<tr data-source-ids="{esc(" ".join(r["source_ids"]))}"><td>{r["game_id"]}</td><td>Week {r["week"]}</td><td>{esc(r["date"])}</td><td>{esc(r["matchup"])}</td><td>{r["p_home"]:.4f}</td><td>{r["p_away"]:.4f}</td><td>{r["p_tie"]:.4f}</td><td>{r["p_home_given_no_tie"]:.4f}</td><td>{inputs["projected_home_margin"]:.3f}</td><td>{inputs["margin_sd"]:.3f}</td><td>{inputs["tie_rate_prior"]:.4f}</td><td>{r["outcome"]}</td><td>{r["prior_games"]}</td><td>{sources}<div><a href="{esc(r["source_url"])}" rel="noopener">Official NFL result page</a></div></td></tr>')
    bin_rows = []
    for b in model["bins"]:
        if not b["n"]:
            continue
        source_links = " ".join(f'<a href="{esc(url)}" rel="noopener">{esc(sid)}</a>'
                                for sid, url, title in b["sources"])
        bin_rows.append(f'<tr data-source-ids="{esc(" ".join(b["source_ids"]))}"><td>{b["range"]}</td><td>{b["n"]}</td><td>{fmt(b["mean_predicted_home_win"])}</td><td>{fmt(b["observed_home_win_rate"])}</td><td>{fmt(b["absolute_gap"])}</td><td>{esc(b["flag"] or "—")}</td><td>{source_links}</td></tr>')
    ci = model["bootstrap"]["brier_skill_ci95"]
    ci_text = f"[{fmt(ci[0])}, {fmt(ci[1])}]" if ci[0] is not None else "not estimable"
    multi_ci = model["bootstrap"]["multiclass_brier_skill_ci95"]
    multi_ci_text = f"[{fmt(multi_ci[0])}, {fmt(multi_ci[1])}]" if multi_ci[0] is not None else "not estimable"
    interpretation = "".join(f"<li>{esc(x)}</li>" for x in model["interpretation"])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Probability calibration audit · OWN7</title><link rel="stylesheet" href="style.css"></head><body><header><div class="brand"><a href="index.html">OWN7 · Probability calibration audit</a></div><nav aria-label="Desk pages"><a href="index.html" aria-current="page">Audit</a> <a href="../../index.html">Site home</a></nav></header><main><h1>Walk-forward probability calibration</h1><p class="lede">Independent scoring of the existing three-stage model's home-win probabilities. Each forecast uses only results from earlier weeks. This is model-quality analysis—not a market comparison, betting recommendation, or reward qualification.</p><div class="cards">{cards}</div><section class="note"><b>Binary Brier-skill 95% interval:</b> {ci_text}; <b>three-outcome Brier-skill interval:</b> {multi_ci_text}. Week-cluster bootstrap: {model["bootstrap"]["clusters"]} weekly clusters, {model["bootstrap"]["reps"]} resamples. {esc(model["bootstrap"]["flag"])}<br><b>No market claim:</b> no operator prices, ROI, CLV, stakes, or rewards are present.</section><h2>Reliability by forecast-probability range</h2><div class="table-card"><table><thead><tr><th>p(home | no tie) range</th><th>n</th><th>Mean p(home | no tie)</th><th>Observed home-win rate</th><th>Absolute gap</th><th>Note</th><th>Official sources</th></tr></thead><tbody>{''.join(bin_rows)}</tbody></table></div><p class="small">A tie is excluded from this binary outcome table. Ranges are descriptive; low-count rows are flagged. Empty ranges are omitted. Each populated row links the official results pages for its games.</p><h2>Method and limitations</h2><ul>{interpretation}</ul><p>Inputs: <a href="../data/calibration.json">machine-readable summary</a> · <a href="../data/game-probabilities.csv">game-level rows</a> · <a href="manifest.json">manifest and input hashes</a>.</p><h2>Scored games</h2><p class="small">Each row cites the registered official NFL schedule page that carries the final. Probabilities and prior-game counts are recomputed from the model; final outcomes are from the linked official source.</p><div class="table-card" tabindex="0" role="region" aria-label="Game-level probability and official result rows"><table><thead><tr><th>Game</th><th>Week</th><th>Date</th><th>Matchup</th><th>p(home win)</th><th>p(away win)</th><th>p(tie)</th><th>p(home | no tie)</th><th>Input: projected margin</th><th>Input: prior margin SD</th><th>Input: prior tie rate</th><th>Actual outcome</th><th>Prior games in training set</th><th>Official source(s)</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div><h2>What would change the conclusion?</h2><p>More chronological holdout seasons, a pre-registered model-vs-control comparison with game-cluster uncertainty, and permitted operator prices captured under documented rights would be needed before any claim about market edge or rewards.</p></main><footer>Research audit only. As of 2026-11-19. Model was not changed. No staking or operator market data used.</footer></body></html>'''


def fmt(value: Any) -> str:
    return "—" if value is None else f"{value:.4f}"


def esc(value: Any) -> str:
    import html
    return html.escape(str(value), quote=True)


def render_css() -> str:
    return ":root{--ink:#1d2430;--muted:#5b6575;--line:#d9dee7;--bg:#f6f8fb;--card:#fff;--accent:#1f4e79}*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}header{background:var(--accent);color:#fff;padding:14px 22px}header a{color:#fff}.brand{font-weight:700}nav{margin-top:8px}nav a{margin-right:12px}main{max-width:1280px;margin:0 auto;padding:22px}h1{font-size:27px;margin:4px 0}.lede{color:var(--muted);max-width:950px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin:15px 0}.card,.note,.table-card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}.card b{display:block;font-size:24px}.card span,.small{color:var(--muted);font-size:13px}.note{background:#fffbea;border-color:#e8d37a;margin:12px 0}.table-card{overflow:auto;padding:0;margin:10px 0}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--line)}th{background:#eef2f7;position:sticky;top:0}footer{max-width:1280px;margin:20px auto;padding:0 22px 30px;color:var(--muted);font-size:13px}.table-card a{display:inline-block;min-height:24px;padding:4px 3px;overflow-wrap:anywhere}li{margin:6px 0}"


def render_all(model: dict[str, Any]) -> dict[str, str]:
    return {"index.html": render_page(model), "style.css": render_css(),
            "manifest.json": json.dumps({"desk": "nfl-calibration-01000ff7", "as_of": "2026-11-19",
                                          "pages": ["index.html", "style.css", "manifest.json"],
                                          "n": model["n"], "target_weeks": model["target_weeks"],
                                          "input_sha256": model["input_sha256"]}, indent=2) + "\n"}


def render_csv(model: dict[str, Any]) -> str:
    cols = ["game_id", "week", "date", "matchup", "p_home", "p_away", "p_tie",
            "p_home_given_no_tie", "projected_home_margin", "margin_sd", "tie_rate_prior",
            "outcome", "outcome_home_win", "prior_games",
            "prior_home_games", "prior_away_games", "source_url", "source_ids"]
    fh = io.StringIO(newline="")
    writer = csv.DictWriter(fh, fieldnames=cols)
    writer.writeheader()
    for row in model["games"]:
        values = {c: row[c] for c in cols if c not in (
            "source_ids", "projected_home_margin", "margin_sd", "tie_rate_prior")}
        values.update(row["probability_inputs"])
        values["source_ids"] = ";".join(row["source_ids"])
        writer.writerow(values)
    return fh.getvalue()


def write_data(model: dict[str, Any]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(model, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_CSV.write_text(render_csv(model), encoding="utf-8", newline="")


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    check = "--check" in argv
    model = build_model()
    outputs = render_all(model)
    if check:
        failures = []
        for name, text in outputs.items():
            path = SITE / name
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                failures.append(name)
        if not OUT_JSON.exists() or OUT_JSON.read_text(encoding="utf-8") != json.dumps(model, indent=2, ensure_ascii=False) + "\n":
            failures.append(str(OUT_JSON.relative_to(ROOT)))
        if not OUT_CSV.exists() or OUT_CSV.read_bytes() != render_csv(model).encode("utf-8"):
            failures.append(str(OUT_CSV.relative_to(ROOT)))
        if failures:
            print("DRIFT:", ", ".join(failures))
            return 1
        print(f"OK: {model['n']} game rows; {model['bootstrap']['clusters']} weekly clusters; outputs reproduce.")
        return 0
    write_data(model)
    SITE.mkdir(parents=True, exist_ok=True)
    for name, text in outputs.items():
        (SITE / name).write_text(text, encoding="utf-8")
    print(f"Wrote calibration audit: games={model['n']}, binary_n={model['binary_n']}, "
          f"binary BSS={model['binary_brier_skill_vs_50pct']}, "
          f"multiclass BSS={model['multiclass_brier_skill_vs_uniform']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
