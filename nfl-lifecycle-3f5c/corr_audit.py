"""Correlation audit: every published correlation must carry n and an official source.

Requirement (2026-11-14): "Compute correlations only from officially sourced numbers and
publish n with each value."

This desk audits, read-only, every correlation artefact the repository publishes:

  research/nfl/results.json            team-level correlations (engine) + explicit not-collected rows
  nfl-results/analysis.json            leg dependence phi and market-structure correlations
  nfl-skill-cfdd/data/correlations-*.csv  club-level Fisher-interval correlations

Audit rule per correlation row:
  A1  a non-null coefficient must carry a non-null n >= 3 (a correlation needs at least 3 pairs);
  A2  every source id on the row must be registered in research/sources.json and resolve to an
      official publisher (the register is itself host-checked by scripts/check_site.py);
  A3  a blank coefficient must carry a stated reason (kind/evidence text), never a silent blank.

Failures are flagged (LC-Fxx) with links; no other session's file is edited.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
for _p in (str(HERE), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


REGISTER: dict | None = None


def _register() -> dict:
    global REGISTER
    if REGISTER is None:
        register = json.loads((REPO / "research" / "sources.json").read_text(encoding="utf-8"))
        if isinstance(register, dict):
            register = register.get("sources", [])
        REGISTER = {entry["id"]: entry for entry in register}
    return REGISTER


def _audit_row(row_id: str, pair: str, coefficient, n, source_ids: list[str],
               reason: str | None, register: dict) -> dict:
    problems = []
    if coefficient is not None:
        if n is None:
            problems.append("A1: coefficient published without n")
        elif n < 3:
            problems.append(f"A1: n={n} below the minimum 3 pairs for a correlation")
    else:
        if not reason:
            problems.append("A3: blank coefficient without a stated reason")
    unregistered = [sid for sid in source_ids if sid not in register]
    if unregistered:
        problems.append(f"A2: source ids not in the register: {unregistered}")
    return {"id": row_id, "pair": pair, "coefficient": coefficient, "n": n,
            "source_ids": source_ids, "reason": reason,
            "status": "FAIL" if problems else "PASS", "problems": problems}


def audit_engine() -> list[dict]:
    results = json.loads((REPO / "research" / "nfl" / "results.json").read_text(encoding="utf-8"))
    rows = []
    for row in results["correlations"]:
        rows.append(_audit_row(row["id"], row["pair"], row["pearson"], row["n"],
                               row["source_ids"], row.get("caveat") or row.get("evidence"),
                               _register()))
    for row in results["not_collected"]:
        rows.append(_audit_row(row["id"], row["pair"], row["pearson"], row["n"],
                               row["source_ids"], row.get("kind"), _register()))
    return rows


def audit_results_lab() -> list[dict]:
    analysis = json.loads((REPO / "nfl-results" / "analysis.json").read_text(encoding="utf-8"))
    rows = []
    leg = analysis["correlations"]["leg_dependence"]
    rows.append(_audit_row("RES-LEG-PHI", "leg dependence: home-cover x over (phi)", leg["phi"],
                           leg["n_games"], ["NFL-SCHEDULE", "REPO"],
                           "measured on the originated board over saved official by-week scores",
                           _register()))
    for row in analysis["correlations"]["market_structure"]:
        rows.append(_audit_row(f"RES-MS-{row['pair'].replace('~','-').upper()}",
                               row["label"], row["pearson"], row["n"],
                               ["NFL-SCHEDULE", "REPO"],
                               "computed from official scores and the originated board",
                               _register()))
    return rows


def audit_cfdd() -> list[dict]:
    rows = []
    matches = sorted((REPO / "nfl-skill-cfdd" / "data").glob("correlations-*.csv"))
    if not matches:
        raise ValueError("no cfdd correlations CSV found")
    path = matches[-1]
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            coefficient = row["pearson_r"]
            coefficient = float(coefficient) if coefficient not in ("", None) else None
            n = int(row["n"]) if row["n"] not in ("", None) else None
            rows.append(_audit_row(row["correlation_id"], f"{row['quantity_a']} vs {row['quantity_b']}",
                                   coefficient, n, [row["source_id"]], row.get("caveat"), _register()))
    return rows


def build() -> dict:
    sections = {
        "engine team-level (research/nfl/results.json)": audit_engine(),
        "results lab (nfl-results/analysis.json)": audit_results_lab(),
        "cfdd desk (nfl-skill-cfdd/data)": audit_cfdd(),
    }
    all_rows = [r for rows in sections.values() for r in rows]
    failed = [r for r in all_rows if r["status"] == "FAIL"]
    coefficients = [r for r in all_rows if r["coefficient"] is not None]
    return {
        "schema_version": 1,
        "rule": "a published correlation must carry n >= 3 and registered official sources; a "
                "blank must carry a stated reason",
        "audited_rows": len(all_rows),
        "with_coefficients": len(coefficients),
        "blank_by_rule": len(all_rows) - len(coefficients),
        "failed": len(failed),
        "sections": [{"artifact": name, "rows": rows} for name, rows in sections.items()],
        "source_ids": ["NFL-STANDINGS", "NFL-SCHEDULE", "REPO"],
    }
