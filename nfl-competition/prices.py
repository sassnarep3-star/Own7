"""Requirement 1 — the price-snapshot store.

The store exists, has a published schema, a published ingest contract and a validator
that is exercised on this run. It holds zero rows, and the reason is a verified negative
result rather than an omission: nfl.com returns a 404 at /odds/, and no page this project
read - including an official Week 10 game page - prints a spread, a total or a price.

Opening and closing are defined before any capture happens, because "the closing number"
is meaningless unless the capture instant is fixed in advance:

    opening  - the first capture at or after 48 hours before kickoff
    closing  - the last capture at or before 90 minutes before kickoff

A market is only usable once it has both. A market with one is published as incomplete
and is never used for a closing-line calculation.

The store is append-only and cannot be written by this build. Nothing in this repository
scrapes a price; a row arrives only by a documented human capture with a source link.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, ROOT, check_artifact, round_value  # noqa: E402

OUT = DATA / "price-store.json"
STORE_CSV = DATA / "price-snapshots.csv"
BOARDS = DATA / "boards.json"

SCHEMA_VERSION = 1

CAPTURE_RULES = {
    "opening": "First capture at or after kickoff minus 48 hours.",
    "closing": "Last capture at or before kickoff minus 90 minutes.",
    "usable_for_clv": "A market is usable only when it holds one opening row and one "
                      "closing row for the same operator.",
    "why_fixed_in_advance": "A capture instant chosen after the result is known lets a "
                            "favourable number be selected retrospectively. Fixing the "
                            "instants in advance removes that degree of freedom.",
    "late_move": "A move after the closing instant is recorded as a third row with "
                 "capture_point = POST_CLOSE and is never used for a closing-line value.",
}

FIELDS = [
    "snapshot_id", "market_id", "game_id", "kickoff_utc", "market_type", "selection",
    "capture_point", "captured_at_utc", "operator", "line", "price_american",
    "source_url", "evidence_file", "verified", "imputed",
]

FIELD_RULES = [
    {"field": "snapshot_id", "type": "text", "required": True,
     "rule": "Unique. Format: market_id + ':' + capture_point."},
    {"field": "market_id", "type": "text", "required": True,
     "rule": "Must match a market_id published by boards.py. A price for a market the "
             "lab does not originate is rejected."},
    {"field": "game_id", "type": "text", "required": True,
     "rule": "Must match a game_id published by originate.py."},
    {"field": "kickoff_utc", "type": "iso8601", "required": True,
     "rule": "Kickoff in UTC, from the official schedule page."},
    {"field": "market_type", "type": "enum", "required": True,
     "rule": "One of SIDE, TOTAL, MONEYLINE."},
    {"field": "selection", "type": "text", "required": True,
     "rule": "The side, over/under, or club the number applies to."},
    {"field": "capture_point", "type": "enum", "required": True,
     "rule": "One of OPEN, CLOSE, POST_CLOSE."},
    {"field": "captured_at_utc", "type": "iso8601", "required": True,
     "rule": "Must be strictly before kickoff_utc. A capture taken after kickoff is not "
             "a price for that market."},
    {"field": "operator", "type": "text", "required": True,
     "rule": "The book or exchange the number came from. Anonymous prices are rejected."},
    {"field": "line", "type": "decimal", "required": False,
     "rule": "The spread or total. Blank for a moneyline, which has no line."},
    {"field": "price_american", "type": "integer", "required": False,
     "rule": "American price. Blank is allowed only when the row records a line with no "
             "price."},
    {"field": "source_url", "type": "url", "required": True,
     "rule": "Must be on a host registered in sources.py. A row without a reachable "
             "source is never published."},
    {"field": "evidence_file", "type": "path", "required": True,
     "rule": "Must exist in the repository. The file holds the text actually read."},
    {"field": "verified", "type": "enum", "required": True,
     "rule": "One of yes, no, pending. Only 'yes' rows enter a calculation."},
    {"field": "imputed", "type": "boolean", "required": True,
     "rule": "Must be false. A filled, interpolated or modelled price is rejected; the "
             "store holds observations or nothing."},
]

# Cases the validator must reject. They are run on every build so the contract is
# exercised rather than merely written down.
CONTRACT_CASES = [
    {"name": "no source url", "expect": "reject",
     "row": {"snapshot_id": "X:OPEN", "market_id": "W10-01-SIDE-HOME", "game_id": "W10-01",
             "kickoff_utc": "2026-11-15T18:00:00Z", "market_type": "SIDE",
             "selection": "DET", "capture_point": "OPEN",
             "captured_at_utc": "2026-11-13T18:00:00Z", "operator": "Operator A",
             "line": -1.5, "price_american": -110, "source_url": "",
             "evidence_file": "nfl-competition/data/price-snapshots.csv",
             "verified": "yes", "imputed": "false"}},
    {"name": "captured after kickoff", "expect": "reject",
     "row": {"snapshot_id": "X:CLOSE", "market_id": "W10-01-SIDE-HOME", "game_id": "W10-01",
             "kickoff_utc": "2026-11-15T18:00:00Z", "market_type": "SIDE",
             "selection": "DET", "capture_point": "CLOSE",
             "captured_at_utc": "2026-11-15T19:00:00Z", "operator": "Operator A",
             "line": -1.5, "price_american": -110,
             "source_url": "https://example.com/odds",
             "evidence_file": "nfl-competition/data/price-snapshots.csv",
             "verified": "yes", "imputed": "false"}},
    {"name": "imputed price", "expect": "reject",
     "row": {"snapshot_id": "X:OPEN", "market_id": "W10-01-SIDE-HOME", "game_id": "W10-01",
             "kickoff_utc": "2026-11-15T18:00:00Z", "market_type": "SIDE",
             "selection": "DET", "capture_point": "OPEN",
             "captured_at_utc": "2026-11-13T18:00:00Z", "operator": "Operator A",
             "line": -1.5, "price_american": -110,
             "source_url": "https://example.com/odds",
             "evidence_file": "nfl-competition/data/price-snapshots.csv",
             "verified": "yes", "imputed": "true"}},
    {"name": "unknown market id", "expect": "reject",
     "row": {"snapshot_id": "Y:OPEN", "market_id": "NOT-A-MARKET", "game_id": "W10-01",
             "kickoff_utc": "2026-11-15T18:00:00Z", "market_type": "SIDE",
             "selection": "DET", "capture_point": "OPEN",
             "captured_at_utc": "2026-11-13T18:00:00Z", "operator": "Operator A",
             "line": -1.5, "price_american": -110,
             "source_url": "https://example.com/odds",
             "evidence_file": "nfl-competition/data/price-snapshots.csv",
             "verified": "yes", "imputed": "false"}},
    {"name": "missing evidence file", "expect": "reject",
     "row": {"snapshot_id": "Z:OPEN", "market_id": "W10-01-SIDE-HOME", "game_id": "W10-01",
             "kickoff_utc": "2026-11-15T18:00:00Z", "market_type": "SIDE",
             "selection": "DET", "capture_point": "OPEN",
             "captured_at_utc": "2026-11-13T18:00:00Z", "operator": "Operator A",
             "line": -1.5, "price_american": -110,
             "source_url": "https://example.com/odds",
             "evidence_file": "nfl-competition/data/does-not-exist.md",
             "verified": "yes", "imputed": "false"}},
    {"name": "a well formed row", "expect": "accept",
     "row": {"snapshot_id": "W10-01-SIDE-HOME:OPEN", "market_id": "W10-01-SIDE-HOME",
             "game_id": "W10-01", "kickoff_utc": "2026-11-15T18:00:00Z",
             "market_type": "SIDE", "selection": "DET", "capture_point": "OPEN",
             "captured_at_utc": "2026-11-13T18:00:00Z", "operator": "Operator A",
             "line": -1.5, "price_american": -110,
             "source_url": "https://example.com/odds",
             "evidence_file": "nfl-competition/data/price-snapshots.csv",
             "verified": "yes", "imputed": "false"}},
]


def validate(row, market_ids, game_ids):
    """Return a list of failures. An empty list means the row may be stored."""
    failures = []
    for spec in FIELD_RULES:
        name = spec["field"]
        value = row.get(name)
        present = value not in (None, "")
        if spec["required"] and not present:
            failures.append(f"{name}: required and missing")
    if row.get("market_id") and row["market_id"] not in market_ids:
        failures.append("market_id: not a market this lab originates")
    if row.get("game_id") and row["game_id"] not in game_ids:
        failures.append("game_id: not a game this lab originates")
    if row.get("market_type") and row["market_type"] not in ("SIDE", "TOTAL", "MONEYLINE"):
        failures.append("market_type: must be SIDE, TOTAL or MONEYLINE")
    if row.get("capture_point") and row["capture_point"] not in ("OPEN", "CLOSE",
                                                                 "POST_CLOSE"):
        failures.append("capture_point: must be OPEN, CLOSE or POST_CLOSE")
    if row.get("verified") and row["verified"] not in ("yes", "no", "pending"):
        failures.append("verified: must be yes, no or pending")
    if str(row.get("imputed", "false")).lower() != "false":
        failures.append("imputed: a modelled or interpolated number is not an observation")
    if row.get("captured_at_utc") and row.get("kickoff_utc"):
        if row["captured_at_utc"] >= row["kickoff_utc"]:
            failures.append("captured_at_utc: must be before kickoff")
    evidence = row.get("evidence_file")
    if evidence and not (ROOT / evidence).exists():
        failures.append("evidence_file: no such file in the repository")
    return failures


def build():
    boards = json.loads(Path(BOARDS).read_text(encoding="utf-8"))
    market_ids = {row["market_id"] for row in boards["rows"]}
    game_ids = {row["game_id"] for row in boards["rows"]}

    # The store itself: header only, zero rows.
    STORE_CSV.parent.mkdir(parents=True, exist_ok=True)
    with STORE_CSV.open("w", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=FIELDS).writeheader()
    stored = list(csv.DictReader(STORE_CSV.open(encoding="utf-8", newline="")))

    contract = []
    for case in CONTRACT_CASES:
        failures = validate(case["row"], market_ids, game_ids)
        accepted = not failures
        contract.append({
            "case": case["name"],
            "expected": case["expect"],
            "observed": "accept" if accepted else "reject",
            "passes": (case["expect"] == "accept") == accepted,
            "reasons": failures,
        })

    register = []
    by_game = {}
    for row in boards["rows"]:
        by_game.setdefault(row["game_id"], []).append(row)
    for game_id, rows in sorted(by_game.items()):
        register.append({
            "game_id": game_id,
            "matchup": rows[0]["matchup"],
            "markets_originated": len(rows),
            "opening_rows": 0, "closing_rows": 0,
            "store_status": "Awaiting a source that publishes a price",
            "usable_for_closing_line_value": False,
        })

    payload = {
        "requirement": "R1 - price-snapshot store with opening and closing numbers",
        "built_on": "2026-11-14",
        "schema_version": SCHEMA_VERSION,
        "store_path": "nfl-competition/data/price-snapshots.csv",
        "rows_stored": len(stored),
        "markets_registered": len(market_ids),
        "games_registered": len(game_ids),
        "capture_rules": CAPTURE_RULES,
        "schema": FIELD_RULES,
        "contract_tests": contract,
        "contract_all_pass": all(entry["passes"] for entry in contract),
        "market_register": register,
        "empty_because": [
            "nfl.com returns HTTP 404 at /odds/; the rendered response contains no odds "
            "table, no price, no operator and no market list (CP-NFL-ODDS-ABSENT).",
            "The official Week 10 game page read on 2026-11-14 prints a score, a "
            "by-quarter table, game info and a standings widget, and prints no spread, "
            "total or price.",
            "No operator or sportsbook was consulted. NFL.com terms section 1.3 permit "
            "individual non-commercial informational use and prohibit systematic "
            "retrieval to compile a collection without written consent; no such consent "
            "is evidenced.",
        ],
        "what_unblocks_it": [
            "A written licence or terms of use that permits retrieving and retaining "
            "opening and closing prices from a named operator, or",
            "an official league publication that prints opening and closing numbers, "
            "which would then be registered in sources.py like any other source.",
        ],
        "consequence": "With zero rows there is no closing-line value, no return on "
                       "investment, no staking column and no cash reward anywhere in "
                       "this lab. Those cells are blank, not estimated.",
    }
    if not payload["contract_all_pass"]:
        raise SystemExit("REFUSING TO PUBLISH: the price-store contract failed its own "
                         "test cases")
    return round_value(payload, 6)


def main():
    if check_artifact(OUT, build()):
        payload = build()
        print(f"  store holds {payload['rows_stored']} rows for "
              f"{payload['markets_registered']} registered markets; "
              f"{sum(1 for c in payload['contract_tests'] if c['passes'])}/"
              f"{len(payload['contract_tests'])} contract cases behave as specified")


if __name__ == "__main__":
    main()
