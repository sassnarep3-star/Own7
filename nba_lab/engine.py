"""Build the frozen, deterministic research result from checked official snapshots."""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
from pathlib import Path
from statistics import fmean

from .math import circular_block_interval, joint_hit_rate, pearson, spearman
from .models import walk_forward_demo
from .validation import GATE_IDS, rank_entries

ROOT = Path(__file__).resolve().parent.parent


def load_json(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def load_csv(relative: str) -> list[dict]:
    with (ROOT / relative).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rounded(value):
    if isinstance(value, float):
        return round(value, 8)
    if isinstance(value, list):
        return [rounded(v) for v in value]
    if isinstance(value, dict):
        return {k: rounded(v) for k, v in value.items()}
    return value


def encode(value) -> str:
    return json.dumps(rounded(value), indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def verify_receipts() -> None:
    for receipt in load_json("research/evidence/receipts.json"):
        path = ROOT / receipt["data_file"]
        rows = load_csv(receipt["data_file"])
        if len(rows) != receipt["retained_rows"] or digest(path) != receipt["sha256"]:
            raise ValueError(f"Receipt mismatch: {path.name}; no result can be published")
        if any(r.get("Verified") != "verified snapshot" for r in rows):
            raise ValueError(f"Unverified input in {path.name}")


def validate_source_rights(settings: dict) -> None:
    """Do not silently enable operations absent verified source authorization.

    This frozen NBA audit has no gambling-use permission. A different mode would
    require a separate rights-reviewed implementation, not a configuration toggle.
    """
    rights = settings.get("source_rights", {})
    if not isinstance(rights, dict):
        raise ValueError("Explicit source-rights no-go policy required")
    for field in ("nba_gambling_use_authorized", "nba_derived_betting_prices_enabled", "bulk_collection_enabled"):
        if rights.get(field) is not False:
            raise ValueError(f"Source-rights no-go: {field} must remain explicitly false")
    if settings.get("competition", {}).get("cash_payments_enabled") is not False:
        raise ValueError("Cash operations are disabled for this frozen audit")


def compute() -> dict:
    verify_receipts()
    settings = load_json("research/protocol.json")
    validate_source_rights(settings)
    catalog = load_json("research/catalog.json")
    games = load_csv("data/jokic-games-2025-26.csv")
    if len(games) != 32 or games[0]["Date"] != settings["demo"]["window_start"] or games[-1]["Date"] != settings["demo"]["window_end"]:
        raise ValueError("Cohort scope mismatch")
    thresholds = settings["demo"]["thresholds"]
    correlations, joint_events = [], []
    for a, b in itertools.combinations(thresholds, 2):
        x, y = [float(g[a]) for g in games], [float(g[b]) for g in games]
        common = {"pair": f"{a} / {b}", "n": len(games), "start": games[0]["Date"],
                  "end": games[-1]["Date"], "source_ids": ["NBA-GAMES", "SCIPY-CORR"],
                  "status": "Derived · exploratory"}
        params = {k: settings["bootstrap"][k] for k in ("draws", "block_length", "seed", "confidence")}
        correlations.append({**common, "kind": "Raw statistics", "pearson": pearson(x, y),
                             "spearman": spearman(x, y),
                             "interval": circular_block_interval(x, y, **params)})
        hx = [int(v > thresholds[a]) for v in x]
        hy = [int(v > thresholds[b]) for v in y]
        params = {k: settings["bootstrap"][k] for k in ("draws", "block_length", "seed", "confidence")}
        phi = pearson(hx, hy)
        label = f"{a} > {thresholds[a]:g} & {b} > {thresholds[b]:g}"
        correlations.append({**common, "pair": label, "kind": "Binary hit indicators",
                             "pearson": phi, "spearman": None,
                             "interval": circular_block_interval(hx, hy, **params)})
        joint_events.append({**common, "pair": label, "hits_a": sum(hx), "hits_b": sum(hy),
                             "joint_hits": sum(v * w for v, w in zip(hx, hy)),
                             "p_a": fmean(hx), "p_b": fmean(hy), "p_independent": fmean(hx) * fmean(hy),
                             "p_joint": joint_hit_rate(hx, hy),
                             "difference": joint_hit_rate(hx, hy) - fmean(hx) * fmean(hy),
                             "phi": phi,
                             "joint_interval": circular_block_interval(hx, hy, statistic=joint_hit_rate, **params)})
    for label in ("Player A / teammate B", "Cross-game leg A / leg B", "Three-or-more-leg joint distribution"):
        correlations.append({"pair": label, "kind": "Not collected", "n": None,
                             "pearson": None, "spearman": None,
                             "interval": {"low": None, "high": None, "valid_resamples": None, "draws": None},
                             "start": None, "end": None, "status": "Unverified · blank",
                             "source_ids": ["NBA-GAMES", "SCIPY-CORR"]})
    evaluations = []
    for strategy in catalog["strategies"]:
        evidence = {g: {"status": "blocked", "artifact_url": None} for g in GATE_IDS}
        if strategy["category"] == "Single bets":
            evidence["G05"] = {"status": "not applicable", "artifact_url": "https://github.com/sassnarep3-star/Own7/blob/main/research/protocol.json"}
        evaluations.append({"strategy_id": strategy["id"], "name": strategy["name"],
                            "category": strategy["category"], "gate_evidence": evidence,
                            "passed_gates": 0, "status": "Blocked", "roi_lcb95": None,
                            "roi": None, "clv": None, "rank": None, "reward": None,
                            "source_ids": strategy["source_ids"]})
    input_paths = sorted([x for x in (ROOT / "data").glob("*.csv") if not x.name.startswith("nfl-")] + list((ROOT / "nba_lab").glob("*.py"))
                         + [ROOT / f"research/{name}.json" for name in ("protocol", "catalog", "sources")]
                         + [ROOT / "research/evidence/receipts.json"])
    manifest = {str(path.relative_to(ROOT)): digest(path) for path in input_paths}
    run_hash = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    return rounded({
        "schema_version": 1, "snapshot_date": settings["snapshot_date"],
        "mode": "Frozen statistical/methods audit; no betting-price release or gambling service",
        "source_rights": settings["source_rights"],
        "verified_observation_rows": sum(r["retained_rows"] for r in load_json("research/evidence/receipts.json")),
        "source_verification": "Agent row-by-row comparison to rendered official tables; normalized evidence, not a raw archive",
        "cohort": {"player": "Nikola Jokić", "player_id": "203999", "games": len(games),
                   "start": games[0]["Date"], "end": games[-1]["Date"],
                   "complete_for_explicit_window": True, "complete_season": False, "preregistered": False},
        "bootstrap": settings["bootstrap"], "correlations": correlations, "joint_events": joint_events,
        "demo": walk_forward_demo(games, settings["demo"]), "evaluations": evaluations,
        "leaderboard": rank_entries(evaluations), "cash_rewards": None,
        "input_sha256": manifest, "run_hash": run_hash,
        "limitations": ["No operator prices or pregame timestamp archive", "No untouched confirmatory or prospective shadow evaluation",
                        "One retrospectively selected player/window", "Not selection-adjusted or powered for strategy validation",
                        "No verified edge, ROI, CLV, prize payment or live recommendation"]})


def run(check: bool = False) -> None:
    target = ROOT / "research/results.json"
    text = encode(compute())
    if check:
        if not target.exists() or target.read_text(encoding="utf-8") != text:
            raise SystemExit("Research results are stale. Run: python -m nba_lab run")
        print("OK: results reproduce exactly from receipt-checked inputs")
    else:
        target.write_text(text, encoding="utf-8")
        print("Built research/results.json; no market values inferred; leaderboard empty")
