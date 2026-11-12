"""Build the frozen NFL research result from checked official snapshots."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nba_lab.math import pearson, spearman

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


def verify_nfl_receipts() -> None:
    for receipt in load_json("research/evidence/nfl-receipts.json"):
        path = ROOT / receipt["data_file"]
        rows = load_csv(receipt["data_file"])
        if len(rows) != receipt["retained_rows"] or digest(path) != receipt["sha256"]:
            raise ValueError(f"NFL receipt mismatch: {path.name}; no result can be published")
        if any(r.get("Verified") != "verified snapshot" for r in rows):
            raise ValueError(f"Unverified input in {path.name}")


def validate_nfl_rights(settings: dict) -> None:
    rights = settings.get("source_rights", {})
    if not isinstance(rights, dict):
        raise ValueError("Explicit NFL source-rights no-go policy required")
    for field in ("nfl_gambling_use_authorized", "nfl_derived_betting_prices_enabled", "bulk_collection_enabled"):
        if rights.get(field) is not False:
            raise ValueError(f"NFL source-rights no-go: {field} must remain explicitly false")
    if settings.get("competition", {}).get("cash_payments_enabled") is not False:
        raise ValueError("Cash operations are disabled for this frozen audit")


def _corr(rows, a, b):
    x = [float(r[a]) for r in rows]
    y = [float(r[b]) for r in rows]
    r = pearson(x, y)
    s = spearman(x, y)
    return r, s


def compute() -> dict:
    verify_nfl_receipts()
    settings = load_json("research/nfl-protocol.json")
    validate_nfl_rights(settings)
    catalog = load_json("research/nfl-catalog.json")
    standings = load_csv("data/nfl-standings-2026.csv")
    passing = load_csv("data/nfl-players-passing-2026.csv")
    off = load_csv("data/nfl-team-offense-passing-2026.csv")
    dfn = load_csv("data/nfl-team-defense-passing-2026.csv")

    correlations = []
    # Team cross-sectional (32 teams) — descriptive only
    team_pairs = [
        ("W vs NetPts (standings)", standings, "W", "NetPts"),
        ("PF vs PA (standings)", standings, "PF", "PA"),
        ("PCT vs NetPts (standings)", standings, "PCT", "NetPts"),
    ]
    for label, rows, a, b in team_pairs:
        r, s = _corr(rows, a, b)
        correlations.append({"pair": label, "n": len(rows), "kind": "Team cross-sectional", "pearson": r, "spearman": s, "status": "Derived · descriptive", "source_ids": ["NFL-STANDINGS"]})
    # Unconfirmed team-offense headers cannot support named correlations (NF11).
    for label in ("Off Yds vs Def Yds Allowed", "Off Rate vs Def Rate Allowed", "Off TD vs Def TD Allowed"):
        correlations.append({"pair": label, "n": None, "kind": "Not collected", "pearson": None, "spearman": None, "status": "Unverified · blank (NF11)", "source_ids": ["NFL-TEAM-OFF", "NFL-TEAM-DEF"]})
    # Player passing cross-sectional (25 QBs)
    for label, a, b in [("Pass Yds vs TD (QBs)", "PassYds", "TD"), ("Pass Yds vs INT (QBs)", "PassYds", "INT"), ("Yds/Att vs Rate (QBs)", "YdsPerAtt", "Rate"), ("Cmp% vs Rate (QBs)", "CmpPct", "Rate")]:
        r, s = _corr(passing, a, b)
        correlations.append({"pair": label, "n": len(passing), "kind": "Player cross-sectional", "pearson": r, "spearman": s, "status": "Derived · descriptive", "source_ids": ["NFL-PASSING"]})
    # Bet-leg correlations: not collected
    for label in ("Teammate leg A / leg B", "Cross-game leg A / leg B", "Three-or-more-leg joint distribution"):
        correlations.append({"pair": label, "kind": "Not collected", "n": None, "pearson": None, "spearman": None, "status": "Unverified · blank", "source_ids": ["NFL-PASSING", "NFL-RUSHING"]})

    evaluations = []
    for strategy in catalog["strategies"]:
        evidence = {g["id"]: {"status": "blocked", "artifact_url": None} for g in catalog["gates"]}
        if strategy["category"] == "Single bets":
            evidence["NG05"] = {"status": "not applicable", "artifact_url": "https://github.com/sassnarep3-star/Own7/blob/main/research/nfl-protocol.json"}
        evaluations.append({"strategy_id": strategy["id"], "name": strategy["name"], "category": strategy["category"], "gate_evidence": evidence, "passed_gates": 0, "status": "Blocked", "roi_lcb95": None, "roi": None, "clv": None, "rank": None, "reward": None, "source_ids": strategy["source_ids"]})

    input_paths = sorted(list((ROOT / "data").glob("nfl-*.csv")) + list((ROOT / "nfl_lab").glob("*.py")) + [ROOT / "research/nfl-protocol.json", ROOT / "research/nfl-catalog.json", ROOT / "research/evidence/nfl-receipts.json"])
    manifest = {str(path.relative_to(ROOT)): digest(path) for path in input_paths}
    run_hash = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    return rounded({
        "schema_version": 1, "snapshot_date": settings["snapshot_date"],
        "mode": "Frozen statistical/methods audit; no betting-price release or gambling service",
        "source_rights": settings["source_rights"],
        "verified_observation_rows": sum(r["retained_rows"] for r in load_json("research/evidence/nfl-receipts.json")),
        "source_verification": "Agent row-by-row comparison to rendered official tables; normalized evidence, not a raw archive",
        "correlations": correlations,
        "evaluations": evaluations,
        "leaderboard": [],
        "cash_rewards": None,
        "input_sha256": manifest, "run_hash": run_hash,
        "limitations": ["No operator prices or pregame timestamp archive", "No untouched confirmatory or prospective shadow evaluation", "Season aggregates only; no game logs", "Not selection-adjusted or powered for strategy validation", "No verified edge, ROI, CLV, prize payment or live recommendation"]})


def run(check: bool = False) -> None:
    target = ROOT / "research/nfl-results.json"
    text = encode(compute())
    if check:
        if not target.exists() or target.read_text(encoding="utf-8") != text:
            raise SystemExit("NFL research results are stale. Run: python -m nfl_lab run")
        print("OK: NFL results reproduce exactly from receipt-checked inputs")
    else:
        target.write_text(text, encoding="utf-8")
        print("Built research/nfl-results.json; no market values inferred; leaderboard empty")


if __name__ == "__main__":
    run()
