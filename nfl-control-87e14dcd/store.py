"""Fail-closed NFL market snapshot store.

The store creates one market record for every market the existing Week 10 model emits,
and two append-only snapshot slots (opening and closing) for each market. It does NOT
manufacture quote values: the current source/rights registry has no authorized odds feed,
so quote numbers, prices, timestamps and quote URLs remain null.

The checked NFL odds route is evidence only for that route, not proof that no operator feed
exists elsewhere. A later licensed-feed adapter must pass ``validate_snapshot`` before it
may derive a market value. This module never makes a network request or scrapes odds.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data"

MARKET_ORDER = ("side", "total", "moneyline")
MARKET_LABELS = {
    "side": "Side / spread",
    "total": "Game total",
    "moneyline": "Moneyline",
}
SNAPSHOT_PHASES = ("opening", "closing")
CLOSING_WINDOW_MINUTES = 15
PRICE_FIELDS = (
    "market_number",
    "home_price_american",
    "away_price_american",
    "over_price_american",
    "under_price_american",
)
SNAPSHOT_COLUMNS = (
    "snapshot_id", "market_id", "game_id", "matchup", "market_order",
    "market_type", "phase", *PRICE_FIELDS, "captured_at_utc",
    "market_open_at_utc", "quote_sequence_basis", "operator", "source_id",
    "source_url", "authorization_ref", "settlement_contract_id", "status",
    "absence_evidence_source_id", "official_game_url",
)
CURRENT_ODDS_SOURCE_ID = "X87-NFL-ODDS-1414"
CURRENT_TERMS_SOURCE_ID = "X87-NFL-TERMS-1414"
CURRENT_SCHEDULE_SOURCE_ID = "X87-NFL-W10-1414"


def load_json(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _approved_price_sources(registry: list[dict], rights: dict) -> list[str]:
    """Return only explicitly licensed quote sources; none is currently registered."""
    if rights.get("nfl_gambling_use_authorized") is not True:
        return []
    approved = []
    for source in registry:
        if not isinstance(source.get("id"), str) or not source["id"].strip():
            continue
        if source.get("kind") not in {"odds", "market quote", "sportsbook quote"}:
            continue
        if source.get("authorization_status") != "Approved":
            continue
        authorization_ref = source.get("authorization_ref")
        if not isinstance(authorization_ref, str) or not authorization_ref.strip():
            continue
        approved.append(source["id"])
    return sorted(approved)


def _market_specs(game: dict) -> list[dict]:
    """Translate existing model outputs into ordered model-only market estimates."""
    return [
        {
            "market_type": "side",
            "model_fair_value": game.get("originated_spread_home"),
            "model_fair_value_unit": "home spread points",
            "model_fair_home_probability": None,
            "model_fair_home_price_american": None,
            "model_fair_away_price_american": None,
            "market_value_unit": "closing home spread points",
            "difference_unit": "points (model home line minus closing home line)",
        },
        {
            "market_type": "total",
            "model_fair_value": game.get("originated_total"),
            "model_fair_value_unit": "expected game points",
            "model_fair_home_probability": None,
            "model_fair_home_price_american": None,
            "model_fair_away_price_american": None,
            "market_value_unit": "closing total points",
            "difference_unit": "points (model total minus closing total)",
        },
        {
            "market_type": "moneyline",
            "model_fair_value": game.get("model_p_home"),
            "model_fair_value_unit": "home win probability",
            "model_fair_home_probability": game.get("model_p_home"),
            "model_fair_home_price_american": game.get("fair_home_price"),
            "model_fair_away_price_american": game.get("fair_away_price"),
            "market_value_unit": "de-vigged closing home win probability",
            "difference_unit": "probability points (model home probability minus closing de-vigged probability)",
        },
    ]


def build_store() -> dict:
    result = load_json("research/nfl/results.json")
    protocol = load_json("research/nfl-protocol.json")
    registry = load_json("research/sources.json")
    registry_by_id = {row["id"]: row for row in registry}
    for source_id in (CURRENT_ODDS_SOURCE_ID, CURRENT_TERMS_SOURCE_ID, CURRENT_SCHEDULE_SOURCE_ID):
        if source_id not in registry_by_id:
            raise ValueError(f"required current source record is missing: {source_id}")
    odds_evidence = registry_by_id[CURRENT_ODDS_SOURCE_ID]
    if "NFL-TERMS-LEGAL" not in registry_by_id:
        raise ValueError("NFL-TERMS-LEGAL must remain registered as the rights reference")

    rights = protocol.get("source_rights", {})
    approved_ids = _approved_price_sources(registry, rights)
    games = result.get("games", [])
    if not games:
        raise ValueError("the model has no originated games to index")

    market_rows: list[dict] = []
    snapshots: list[dict] = []
    for game in games:
        game_id = game.get("id")
        game_url = game.get("game_url")
        if not game_id or not isinstance(game_url, str) or not game_url.startswith("https://www.nfl.com/games/"):
            raise ValueError(f"game row lacks an official NFL game URL: {game_id!r}")
        matchup = game.get("matchup") or ""
        for order, spec in enumerate(_market_specs(game), start=1):
            market_type = spec["market_type"]
            if market_type != MARKET_ORDER[order - 1]:
                raise ValueError("market order must remain side, total, moneyline")
            fair_value = spec["model_fair_value"]
            if isinstance(fair_value, bool) or not isinstance(fair_value, (int, float)) or not math.isfinite(float(fair_value)):
                raise ValueError(f"model fair output missing/invalid for {game_id}/{market_type}")
            market_id = f"{game_id}-{market_type.upper()}"
            market_rows.append({
                "market_id": market_id,
                "game_id": game_id,
                "matchup": matchup,
                "kickoff": game.get("kickoff"),
                "market_order": order,
                "market_type": market_type,
                "market_label": MARKET_LABELS[market_type],
                "model_fair_value": fair_value,
                "model_fair_value_unit": spec["model_fair_value_unit"],
                "model_fair_value_status": "Model-only estimate; calibration against an authorized market/price source is not established.",
                "model_fair_home_probability": spec["model_fair_home_probability"],
                "model_fair_home_price_american": spec["model_fair_home_price_american"],
                "model_fair_away_price_american": spec["model_fair_away_price_american"],
                # `market_value` is the closing value under the matching contract below.
                # For moneyline it is de-vigged home win probability, not American odds.
                "market_value": None,
                "market_value_unit": spec["market_value_unit"],
                "difference": None,
                "difference_unit": spec["difference_unit"],
                "opening_value": None,
                "closing_value": None,
                "opening_home_price_american": None,
                "opening_away_price_american": None,
                "opening_over_price_american": None,
                "opening_under_price_american": None,
                "closing_home_price_american": None,
                "closing_away_price_american": None,
                "closing_over_price_american": None,
                "closing_under_price_american": None,
                "opening_snapshot_id": f"{market_id}-OPEN",
                "closing_snapshot_id": f"{market_id}-CLOSE",
                "model_snapshot_date": result.get("snapshot_date"),
                "model_capture_time_utc": None,
                "temporal_status": "Model is date-only; exact capture time and a complete pre-kickoff information cutoff are unverified.",
                "status": "No authorized quote source is registered; opening/closing market values are not collected.",
                "source_url": game_url,
                "source_ids": [
                    "NFL-STANDINGS", "PYTH-NFL", "NFL-SCHED-W10", CURRENT_SCHEDULE_SOURCE_ID,
                    CURRENT_ODDS_SOURCE_ID, CURRENT_TERMS_SOURCE_ID, "REPO",
                ],
            })
            for phase in SNAPSHOT_PHASES:
                phase_suffix = "OPEN" if phase == "opening" else "CLOSE"
                snapshot_id = f"{market_id}-{phase_suffix}"
                snapshots.append({
                    "snapshot_id": snapshot_id,
                    "market_id": market_id,
                    "game_id": game_id,
                    "matchup": matchup,
                    "market_order": order,
                    "market_type": market_type,
                    "phase": phase,
                    "market_number": None,
                    "home_price_american": None,
                    "away_price_american": None,
                    "over_price_american": None,
                    "under_price_american": None,
                    "captured_at_utc": None,
                    "market_open_at_utc": None,
                    "quote_sequence_basis": None,
                    "operator": None,
                    "source_id": None,
                    "source_url": None,
                    "authorization_ref": None,
                    "settlement_contract_id": None,
                    "status": "not_collected",
                    "absence_evidence_source_id": CURRENT_ODDS_SOURCE_ID,
                    "official_game_url": game_url,
                })

    if [r["market_type"] for r in market_rows[:3]] != list(MARKET_ORDER):
        raise ValueError("first market group must be side, total, moneyline")
    if len(market_rows) != len(games) * len(MARKET_ORDER):
        raise ValueError("not every originated game has exactly three market records")
    if len(snapshots) != len(market_rows) * len(SNAPSHOT_PHASES):
        raise ValueError("each originated market must have opening and closing slots")

    return {
        "schema_version": 1,
        "checked_on": "2026-11-14",
        "market_order": list(MARKET_ORDER),
        "market_value_contract": {
            "side": "Home spread line, in points; negative means the home team is favored. The difference is model_fair_value minus closing market_value.",
            "total": "Game total, in points. The difference is model_fair_value minus closing market_value.",
            "moneyline": "Home win probability. market_value must be de-vigged from a complete paired home/away closing quote; difference is a probability-point difference.",
            "fair_value_boundary": "These are existing model-originated estimates, not independently calibrated or validated fair prices.",
        },
        "market_number_semantics": {
            "side": "Market number is the home-side spread in points; negative means home favored.",
            "total": "Market number is the game total in points.",
            "moneyline": "Market number is not used; the closing value is the normalized home win probability derived from a paired quote.",
        },
        "snapshot_contract": {
            "phases": list(SNAPSHOT_PHASES),
            "opening_definition": "Use the provider-identified opening quote and market-open timestamp when available. If the provider does not expose the true open, record only its first observed quote, mark the basis as first_quote_in_provider_archive or first_observed_by_own_capture, and leave market_open_at_utc blank; never relabel first observed as true market open.",
            "closing_definition": f"Last authorized quote captured in the fixed {CLOSING_WINDOW_MINUTES}-minute pre-kickoff interval [kickoff minus {CLOSING_WINDOW_MINUTES} minutes, kickoff). Exact UTC kickoff and capture timestamps are required.",
            "reference_source_rule": "Predeclare one operator/source and settlement contract for the market; opening and closing rows must match. Do not splice prices across operators.",
            "required_quote_fields": {
                "side": ["market_number", "home_price_american", "away_price_american"],
                "total": ["market_number", "over_price_american", "under_price_american"],
                "moneyline": ["home_price_american", "away_price_american"],
            },
            "provenance_required": ["captured_at_utc", "market_open_at_utc (opening only)", "quote_sequence_basis (opening only)", "operator", "source_id", "source_url", "authorization_ref", "settlement_contract_id"],
            "write_rule": "Append-only. Reject a duplicate snapshot ID; never overwrite an opening or closing row.",
            "unknown_rule": "Missing values serialize as null/empty cells, never as zero or an inferred quote.",
            "closing_window_minutes": CLOSING_WINDOW_MINUTES,
        },
        "source_status": {
            "authorized_price_source_ids": approved_ids,
            "nfl_derived_betting_use_authorized": rights.get("nfl_gambling_use_authorized") is True,
            "odds_route_status": odds_evidence.get("status"),
            "odds_route_scope": "The checked NFL odds path only; a 404 does not establish that no operator feed exists.",
        },
        "counts": {
            "games_originated": len(games),
            "markets_originated": len(market_rows),
            "market_types_per_game": len(MARKET_ORDER),
            "opening_closing_slots": len(snapshots),
            "quotes_collected": sum(1 for r in snapshots if r["source_url"] and r["captured_at_utc"]),
            "market_values_filled": sum(1 for r in market_rows if r["market_value"] is not None),
            "differences_filled": sum(1 for r in market_rows if r["difference"] is not None),
        },
        "markets": market_rows,
        "snapshots": snapshots,
    }


def _parse_aware_utc(value: str, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError(f"{field} must include a UTC timezone")
    return parsed.astimezone(timezone.utc)


def _valid_american_price(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value != 0 and abs(value) <= 10000


def american_implied_probability(price: int) -> float:
    """Convert a nonzero American price to its raw implied probability (before de-vigging)."""
    if not _valid_american_price(price):
        raise ValueError("American price must be a nonzero integer with absolute value <= 10000")
    if price > 0:
        return 100.0 / (price + 100.0)
    return abs(price) / (abs(price) + 100.0)


def moneyline_home_probability(home_price_american: int, away_price_american: int) -> float:
    """Normalize a complete two-sided American moneyline quote to de-vigged home probability."""
    home = american_implied_probability(home_price_american)
    away = american_implied_probability(away_price_american)
    total = home + away
    if not math.isfinite(total) or total <= 0:
        raise ValueError("invalid paired moneyline implied probabilities")
    return home / total


def market_value_and_difference(
    market: dict,
    closing_snapshot: dict,
    *,
    registry: dict[str, dict],
    authorized_price_source_ids: set[str],
    nfl_data_use_authorized: bool,
    kickoff_at_utc: str,
    existing_snapshot_ids: set[str],
    opening_snapshot: dict,
) -> dict:
    """Derive close value/difference only after strict quote-contract validation.

    The existing-ID set is the append-only store immediately before the candidate close is
    written and must already contain the paired opening snapshot ID.
    """
    validate_snapshot(
        closing_snapshot,
        registry=registry,
        authorized_price_source_ids=authorized_price_source_ids,
        nfl_data_use_authorized=nfl_data_use_authorized,
        kickoff_at_utc=kickoff_at_utc,
        existing_snapshot_ids=existing_snapshot_ids,
        opening_snapshot=opening_snapshot,
    )
    for field in ("market_id", "game_id", "market_type"):
        if closing_snapshot.get(field) != market.get(field):
            raise ValueError(f"closing snapshot {field} does not match the market")
    kind = market.get("market_type")
    if kind in {"side", "total"}:
        line = closing_snapshot.get("market_number")
        if isinstance(line, bool) or not isinstance(line, (int, float)) or not math.isfinite(float(line)):
            raise ValueError("closing line number is required")
        market_value = float(line)
    elif kind == "moneyline":
        market_value = moneyline_home_probability(
            closing_snapshot.get("home_price_american"),
            closing_snapshot.get("away_price_american"),
        )
    else:
        raise ValueError(f"unsupported market type: {kind!r}")
    fair_value = market.get("model_fair_value")
    if isinstance(fair_value, bool) or not isinstance(fair_value, (int, float)) or not math.isfinite(float(fair_value)):
        raise ValueError("model fair value is missing or invalid")
    result = dict(market)
    result["market_value"] = market_value
    result["difference"] = float(fair_value) - market_value
    result["closing_value"] = market_value
    for field in ("home_price_american", "away_price_american", "over_price_american", "under_price_american"):
        result[f"closing_{field}"] = closing_snapshot.get(field)
    result["closing_snapshot_id"] = closing_snapshot.get("snapshot_id")
    result["market_value_source_id"] = closing_snapshot.get("source_id")
    result["market_value_source_url"] = closing_snapshot.get("source_url")
    result["market_value_captured_at_utc"] = closing_snapshot.get("captured_at_utc")
    return result


def validate_snapshot(
    row: dict,
    *,
    registry: dict[str, dict],
    authorized_price_source_ids: set[str],
    nfl_data_use_authorized: bool,
    kickoff_at_utc: str,
    existing_snapshot_ids: set[str],
    opening_snapshot: dict | None = None,
) -> None:
    """Validate a future machine-ingested quote; all failures are fail-closed.

    This is not a collector. It defines what a licensed feed adapter would have to prove
    before adding a quote to the append-only store.
    """
    if not isinstance(row, dict):
        raise ValueError("snapshot row must be a mapping")
    if not isinstance(existing_snapshot_ids, set):
        raise ValueError("a complete existing snapshot-ID set is required for append-only validation")
    snapshot_id = row.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        raise ValueError("snapshot ID is required")
    if snapshot_id in existing_snapshot_ids:
        raise ValueError("snapshot IDs are append-only and may not be overwritten")
    for field in ("market_id", "game_id"):
        value = row.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} is required")
    if row.get("phase") not in SNAPSHOT_PHASES:
        raise ValueError("snapshot phase must be opening or closing")
    if row.get("market_type") not in MARKET_ORDER:
        raise ValueError("unsupported market type")
    if not isinstance(registry, dict):
        raise ValueError("registered quote-source registry is required")
    if not isinstance(authorized_price_source_ids, (set, frozenset)):
        raise ValueError("explicit authorized price-source IDs are required")
    source_id = row.get("source_id")
    if not isinstance(source_id, str) or source_id not in authorized_price_source_ids:
        raise ValueError("price source is not explicitly authorized")
    source = registry.get(source_id)
    if not isinstance(source, dict) or source.get("id") != source_id or source.get("kind") not in {"odds", "market quote", "sportsbook quote"}:
        raise ValueError("price source is not registered as an odds/quote source")
    if source.get("authorization_status") != "Approved":
        raise ValueError("registered price source does not have explicit approved authorization")
    if nfl_data_use_authorized is not True:
        raise ValueError("NFL-data use for this market workflow is not authorized")
    expected_authorization_ref = source.get("authorization_ref")
    if not isinstance(expected_authorization_ref, str) or not expected_authorization_ref.strip():
        raise ValueError("registered source lacks a documented authorization reference")
    if row.get("authorization_ref") != expected_authorization_ref:
        raise ValueError("snapshot authorization reference must match the registered source")
    for field in ("operator", "settlement_contract_id"):
        value = row.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("operator and settlement contract are required")
    source_url = row.get("source_url")
    if not isinstance(source_url, str) or source_url != source.get("url") or not source_url.startswith("https://"):
        raise ValueError("quote URL must match the registered HTTPS source")
    captured_dt = _parse_aware_utc(row.get("captured_at_utc"), "captured_at_utc")
    kickoff_dt = _parse_aware_utc(kickoff_at_utc, "kickoff_at_utc")
    if captured_dt >= kickoff_dt:
        raise ValueError("market quote must be captured before kickoff")

    if row["phase"] == "opening":
        basis = row.get("quote_sequence_basis")
        if basis == "provider_market_open_record":
            opened_dt = _parse_aware_utc(row.get("market_open_at_utc"), "market_open_at_utc")
            if captured_dt < opened_dt:
                raise ValueError("opening quote cannot predate the source-attested market-open time")
        elif basis in {"first_quote_in_provider_archive", "first_observed_by_own_capture"}:
            if row.get("market_open_at_utc") not in (None, ""):
                raise ValueError("first-observed opening must leave market_open_at_utc blank")
        else:
            raise ValueError("opening quote basis must distinguish provider opening from first observed")
    else:
        if not isinstance(opening_snapshot, dict):
            raise ValueError("closing snapshot requires a matching opening snapshot")
        opening_id = opening_snapshot.get("snapshot_id")
        if not isinstance(opening_id, str) or not opening_id.strip():
            raise ValueError("paired opening snapshot ID is required")
        if opening_id == snapshot_id:
            raise ValueError("opening and closing snapshots must have distinct IDs")
        if opening_id not in existing_snapshot_ids:
            raise ValueError("paired opening snapshot must already exist in the append-only store")
        if opening_snapshot.get("phase") != "opening":
            raise ValueError("paired opening snapshot must have opening phase")
        validate_snapshot(
            opening_snapshot,
            registry=registry,
            authorized_price_source_ids=set(authorized_price_source_ids),
            nfl_data_use_authorized=nfl_data_use_authorized,
            kickoff_at_utc=kickoff_at_utc,
            existing_snapshot_ids=set(),
        )
        if captured_dt < kickoff_dt - timedelta(minutes=CLOSING_WINDOW_MINUTES):
            raise ValueError(f"closing quote is outside the fixed {CLOSING_WINDOW_MINUTES}-minute pre-kickoff window")
        for field in ("market_id", "game_id", "market_type"):
            if opening_snapshot.get(field) != row.get(field):
                raise ValueError(f"paired opening snapshot {field} does not match the closing market")
        opened_capture = _parse_aware_utc(opening_snapshot.get("captured_at_utc"), "opening_snapshot.captured_at_utc")
        if opened_capture > captured_dt:
            raise ValueError("closing quote cannot predate its paired opening snapshot")
        for field in ("operator", "source_id", "source_url", "authorization_ref", "settlement_contract_id"):
            if opening_snapshot.get(field) != row.get(field):
                raise ValueError(f"opening and closing snapshots must share the same {field}")

    required = {
        "side": ("market_number", "home_price_american", "away_price_american"),
        "total": ("market_number", "over_price_american", "under_price_american"),
        "moneyline": ("home_price_american", "away_price_american"),
    }[row["market_type"]]
    irrelevant_fields = set(PRICE_FIELDS) - set(required)
    if any(row.get(field) not in (None, "") for field in irrelevant_fields):
        raise ValueError("quote fields for a different market type must remain blank")
    if any(row.get(field) in (None, "") for field in required):
        raise ValueError("a complete two-outcome quote is required for the market type")
    if row["market_type"] in {"side", "total"}:
        line = row.get("market_number")
        if isinstance(line, bool) or not isinstance(line, (int, float)) or not math.isfinite(float(line)):
            raise ValueError("market_number must be a finite numeric line")
    for field in (f for f in required if f.endswith("price_american")):
        if not _valid_american_price(row.get(field)):
            raise ValueError(f"invalid American price in {field}")


def _csv_text(rows: list[dict]) -> str:
    from io import StringIO
    out = StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=SNAPSHOT_COLUMNS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: "" if row.get(k) is None else row.get(k) for k in SNAPSHOT_COLUMNS})
    return out.getvalue()


def generated_files() -> dict[Path, str]:
    store = build_store()
    json_text = json.dumps(store, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    csv_text = _csv_text(store["snapshots"])
    return {
        DATA / "price-store-2026-11-14.json": json_text,
        DATA / "price-snapshots-2026-11-14.csv": csv_text,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail unless committed store is byte-identical")
    args = parser.parse_args()
    changed = []
    for path, content in generated_files().items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                changed.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if changed:
        raise SystemExit("stale price-store artifacts: " + ", ".join(changed))
    store = build_store()
    print(f"OK: {store['counts']['markets_originated']} markets, "
          f"{store['counts']['opening_closing_slots']} open/close slots, "
          f"{store['counts']['quotes_collected']} quotes collected; unavailable values remain blank.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
