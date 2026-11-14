"""NFL market snapshots and release controls.

This package is deliberately fail-closed. It can store a quote only when the source is
registered, the observation is time-stamped, and documented use rights are supplied.
The committed quote ledger is empty; model outputs never stand in for market prices.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SITE = HERE / "site"

MARKET_SEQUENCE = [
    {
        "priority": 1,
        "key": "spread",
        "label": "Side · point spread",
        "selections": ["home", "away"],
        "units": "points",
    },
    {
        "priority": 2,
        "key": "total",
        "label": "Total",
        "selections": ["over", "under"],
        "units": "points",
    },
    {
        "priority": 3,
        "key": "moneyline",
        "label": "Moneyline",
        "selections": ["home", "away"],
        "units": "probability",
    },
]
MARKET_BY_KEY = {row["key"]: row for row in MARKET_SEQUENCE}
SELECTIONS = {key: set(row["selections"]) for key, row in MARKET_BY_KEY.items()}
QUOTE_FIELDS = (
    "snapshot_id", "game_id", "market", "market_variant", "selection", "phase", "operator",
    "line", "american_odds", "captured_at_utc", "source_id", "source_url",
    "rights_status", "rights_reference", "verification_status", "evidence_sha256",
)
VALID_PHASES = {"opening", "closing"}
HARD_DEMOTION_TRIGGERS = {
    "provenance_failure",
    "rights_invalid_or_revoked",
    "price_snapshot_missing_or_stale",
    "settlement_mismatch",
    "risk_limit_exceeded",
    "model_or_input_version_changed_without_revalidation",
    "non_reproducible_build",
}
MIN_SETTLED_FOR_STATISTICAL_DEMOTION = 100
ROI_LOWER_BOUND_TRIGGER = 0.0


def read_json(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path: Path | str) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON line") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: quote record must be an object")
        rows.append(value)
    return rows


def read_csv(path: Path | str) -> list[dict]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sources_by_id() -> dict[str, dict]:
    sources = read_json(ROOT / "research/sources.json")
    result = {row["id"]: row for row in sources}
    if len(result) != len(sources):
        raise ValueError("Duplicate source ID in research/sources.json")
    return result


def utc_datetime(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("captured_at_utc must be an ISO-8601 timestamp with timezone")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("captured_at_utc must be an ISO-8601 timestamp with timezone") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("captured_at_utc must include a timezone offset")
    return parsed.astimezone(timezone.utc)


def implied_probability_american(odds: int | float) -> float:
    """Raw break-even probability including vig; not a no-vig market estimate."""
    if isinstance(odds, bool) or not isinstance(odds, (int, float)) or not math.isfinite(odds) or odds == 0:
        raise ValueError("American odds must be a finite, non-zero number")
    if odds < 0:
        return -odds / (-odds + 100.0)
    return 100.0 / (odds + 100.0)


def validate_quote(
    quote: dict,
    *,
    sources: dict[str, dict] | None = None,
    game_ids: set[str] | None = None,
) -> dict:
    """Validate one official, licensed opening or closing quote without filling gaps."""
    if not isinstance(quote, dict):
        raise ValueError("quote must be an object")
    missing = [field for field in QUOTE_FIELDS if field not in quote]
    if missing:
        raise ValueError("missing quote fields: " + ", ".join(missing))
    for field in ("snapshot_id", "game_id", "market_variant", "operator", "source_id", "source_url",
                  "rights_reference", "evidence_sha256"):
        if not isinstance(quote[field], str) or not quote[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    if quote["market"] not in MARKET_BY_KEY:
        raise ValueError(f"unsupported market: {quote['market']!r}")
    if quote["selection"] not in SELECTIONS[quote["market"]]:
        raise ValueError("selection does not belong to the selected market")
    if quote["phase"] not in VALID_PHASES:
        raise ValueError("phase must be opening or closing")
    if quote["market_variant"] != "mainline":
        raise ValueError("only the model's registered mainline is in this snapshot matrix")
    if quote["market"] == "moneyline":
        if quote.get("line") is not None:
            raise ValueError("moneyline records have no point line")
    else:
        line = quote.get("line")
        if isinstance(line, bool) or not isinstance(line, (int, float)) or not math.isfinite(line):
            raise ValueError("spread and total records require a finite market line")
    odds = quote.get("american_odds")
    if isinstance(odds, bool) or not isinstance(odds, (int, float)) or not math.isfinite(odds) or not float(odds).is_integer():
        raise ValueError("American odds must be an integer")
    implied_probability_american(odds)
    if quote["rights_status"] != "authorized":
        raise ValueError("quote is not publishable without documented authorized use rights")
    if quote["verification_status"] != "verified":
        raise ValueError("quote is not publishable until its source row is verified")
    if not re.fullmatch(r"[0-9a-f]{64}", quote["evidence_sha256"]):
        raise ValueError("evidence_sha256 must be a 64-character lowercase SHA-256 hex digest")
    captured = utc_datetime(quote["captured_at_utc"])
    parsed = urlparse(quote["source_url"])
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("quote source must be an HTTPS URL")
    sources = sources if sources is not None else sources_by_id()
    source = sources.get(quote["source_id"])
    if not source:
        raise ValueError(f"unregistered quote source ID: {quote['source_id']}")
    kind = str(source.get("kind", "")).lower()
    if not any(token in kind for token in ("market", "odds", "price", "sportsbook", "operator")):
        raise ValueError("registered source is not identified as a market-price publisher")
    if not all(source.get(field) for field in ("scope", "checked_on", "access")):
        raise ValueError("registered market source lacks checked scope, date or access record")
    if source.get("rights_status") != "authorized" or not all(
        isinstance(source.get(field), str) and source[field].strip()
        for field in ("rights_scope", "rights_reference")
    ):
        raise ValueError("registered market source lacks documented authorized-use scope and reference")
    if quote["rights_reference"] != source["rights_reference"]:
        raise ValueError("quote rights reference does not match the registered authorization")
    registered = urlparse(source.get("url", ""))
    if registered.scheme != "https" or not registered.hostname:
        raise ValueError("registered market source must have a valid HTTPS URL")
    if parsed.hostname.lower() != registered.hostname.lower():
        raise ValueError("quote URL host does not match the registered publisher")
    registered_path = registered.path.rstrip("/")
    if parsed.path.rstrip("/") != registered_path and not parsed.path.startswith(registered_path + "/"):
        raise ValueError("quote URL path is outside the registered source scope")
    if game_ids is not None and quote["game_id"] not in game_ids:
        raise ValueError("quote references a game outside the originated fixture set")
    normalized = dict(quote)
    normalized["captured_at_utc"] = captured.isoformat().replace("+00:00", "Z")
    normalized["american_odds"] = int(odds) if int(odds) == odds else float(odds)
    if quote["market"] != "moneyline":
        normalized["line"] = float(quote["line"])
    return normalized


def validate_quote_ledger(
    rows: list[dict], *, sources: dict[str, dict] | None = None, game_ids: set[str] | None = None
) -> list[dict]:
    sources = sources if sources is not None else sources_by_id()
    ids: set[str] = set()
    slots: set[tuple[str, str, str, str, str, str]] = set()
    normalized = []
    for row in rows:
        clean = validate_quote(row, sources=sources, game_ids=game_ids)
        if clean["snapshot_id"] in ids:
            raise ValueError(f"duplicate snapshot_id: {clean['snapshot_id']}")
        ids.add(clean["snapshot_id"])
        slot = (clean["game_id"], clean["market"], clean["market_variant"], clean["selection"], clean["phase"], clean["operator"])
        if slot in slots:
            raise ValueError(f"duplicate quote slot: {slot}")
        slots.add(slot)
        normalized.append(clean)
    by_key: dict[tuple[str, str, str, str], dict[str, dict]] = {}
    for row in normalized:
        key = (row["game_id"], row["market"], row["selection"], row["operator"])
        by_key.setdefault(key, {})[row["phase"]] = row
    for key, phases in by_key.items():
        opening, closing = phases.get("opening"), phases.get("closing")
        if opening and closing and utc_datetime(closing["captured_at_utc"]) < utc_datetime(opening["captured_at_utc"]):
            raise ValueError(f"closing timestamp precedes opening for {key}")
    return normalized


def append_quote(
    path: Path | str,
    quote: dict,
    *,
    sources: dict[str, dict] | None = None,
    game_ids: set[str] | None = None,
) -> dict:
    """Append exactly one validated observation; duplicate slot updates are refused."""
    path = Path(path)
    existing = read_jsonl(path)
    normalized = validate_quote(quote, sources=sources, game_ids=game_ids)
    validate_quote_ledger(existing + [normalized], sources=sources, game_ids=game_ids)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(normalized, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
    return normalized


def load_originations() -> list[dict]:
    path = ROOT / "research/nfl/results.json"
    rows = read_json(path).get("games", [])
    if not rows:
        raise ValueError("no originated games found in research/nfl/results.json")
    ids = [row.get("id") for row in rows]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("originated game IDs are missing or duplicated")
    for row in rows:
        if not row.get("game_source_url", "").startswith("https://www.nfl.com/"):
            raise ValueError(f"{row.get('id')}: official NFL game URL missing")
        for field in ("originated_spread_home", "originated_total", "model_p_home",
                      "fair_home_price", "fair_away_price"):
            value = row.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{row['id']}: invalid or missing model field {field}")
    schedule = read_csv(ROOT / "data/nfl-schedule-2026-w10.csv")
    schedule_by_id = {row["id"]: row for row in schedule}
    if set(schedule_by_id) != set(ids):
        raise ValueError("originated games do not match the official Week 10 fixture set")
    for row in rows:
        fixture = schedule_by_id[row["id"]]
        if row["game_source_url"] != fixture["GameURL"]:
            raise ValueError(f"{row['id']}: originated game URL differs from the fixture receipt")
    return rows


def game_ids() -> set[str]:
    return {row["id"] for row in load_originations()}


def _moneyline_values(game: dict, selection: str) -> tuple[float, int]:
    if selection == "home":
        return float(game["model_p_home"]), int(game["fair_home_price"])
    return 1.0 - float(game["model_p_home"]), int(game["fair_away_price"])


def _fair_line(game: dict, market: str, selection: str) -> float | None:
    if market == "spread":
        value = float(game["originated_spread_home"])
        return value if selection == "home" else -value
    if market == "total":
        return float(game["originated_total"])
    return None


def market_matrix(quotes: list[dict] | None = None) -> list[dict]:
    """One display row per game/market/selection/operator; absent values stay None.

    With no quotes, this is a matrix of expected opening/closing slots, not a claim that a
    market quote was ever offered. Multiple operators remain separate rather than selecting
    a best price after the fact.
    """
    games = load_originations()
    quotes = validate_quote_ledger(quotes if quotes is not None else read_jsonl(DATA / "quote_snapshots.jsonl"),
                                   game_ids={row["id"] for row in games})
    grouped: dict[tuple[str, str, str, str], dict[str, dict]] = {}
    for quote in quotes:
        key = (quote["game_id"], quote["market"], quote["selection"], quote["operator"])
        grouped.setdefault(key, {})[quote["phase"]] = quote
    rows = []
    source_ids = ["NFL-SCHED-W10", "NFL-STANDINGS", "REPO"]
    for market in MARKET_SEQUENCE:
        for game in games:
            for selection in market["selections"]:
                operators = sorted({key[3] for key in grouped
                                    if key[:3] == (game["id"], market["key"], selection)})
                if not operators:
                    operators = [None]
                for operator in operators:
                    group = grouped.get((game["id"], market["key"], selection, operator), {}) if operator else {}
                    opening, closing = group.get("opening"), group.get("closing")
                    fair_line = _fair_line(game, market["key"], selection)
                    fair_probability = fair_american = None
                    if market["key"] == "moneyline":
                        fair_probability, fair_american = _moneyline_values(game, selection)
                    open_market_value = None
                    close_market_value = None
                    open_diff = close_diff = None
                    if market["key"] == "moneyline":
                        if opening:
                            open_market_value = implied_probability_american(opening["american_odds"])
                            open_diff = fair_probability - open_market_value
                        if closing:
                            close_market_value = implied_probability_american(closing["american_odds"])
                            close_diff = fair_probability - close_market_value
                    else:
                        if opening:
                            open_market_value = float(opening["line"])
                            open_diff = fair_line - open_market_value
                        if closing:
                            close_market_value = float(closing["line"])
                            close_diff = fair_line - close_market_value
                    row_sources = list(source_ids)
                    for quote in (opening, closing):
                        if quote and quote["source_id"] not in row_sources:
                            row_sources.append(quote["source_id"])
                    rows.append({
                        "id": f"{game['id']}-{market['key']}-{selection}-{operator or 'no-quote'}",
                        "game_id": game["id"],
                        "game": game["matchup"],
                        "kickoff": game["kickoff"],
                        "market": market["label"],
                        "market_key": market["key"],
                        "market_order": market["priority"],
                        "selection": selection,
                        "operator": operator,
                        "units": market["units"],
                        "fair_line": fair_line,
                        "fair_probability": fair_probability,
                        "fair_american_odds": fair_american,
                        "opening_market_value": open_market_value,
                        "opening_market_line": open_market_value if market["key"] != "moneyline" else None,
                        "opening_implied_probability": open_market_value if market["key"] == "moneyline" else None,
                        "opening_american_odds": opening["american_odds"] if opening else None,
                        "opening_line_difference": open_diff if market["key"] != "moneyline" else None,
                        "opening_probability_difference": open_diff if market["key"] == "moneyline" else None,
                        "opening_timestamp_utc": opening["captured_at_utc"] if opening else None,
                        "closing_market_value": close_market_value,
                        "closing_market_line": close_market_value if market["key"] != "moneyline" else None,
                        "closing_implied_probability": close_market_value if market["key"] == "moneyline" else None,
                        "closing_american_odds": closing["american_odds"] if closing else None,
                        "closing_line_difference": close_diff if market["key"] != "moneyline" else None,
                        "closing_probability_difference": close_diff if market["key"] == "moneyline" else None,
                        "closing_timestamp_utc": closing["captured_at_utc"] if closing else None,
                        "status": ("Opening and closing captured" if opening and closing else
                                   "Partial quote capture" if opening or closing else
                                   "Expected slot only · no authorized quote in repository"),
                        "event_source_url": game["game_source_url"],
                        "source_url": "https://www.nfl.com/schedules/",
                        "source_ids": row_sources,
                    })
    return rows


def signal_rows() -> list[dict]:
    analysis = read_json(ROOT / "nfl-results/analysis.json")
    provisional = {row["id"] for row in analysis.get("leaderboard", [])
                   if row.get("tier") == "provisional"}
    rows = []
    for candidate in analysis.get("candidates", []):
        stat = candidate.get("stat", {})
        bets = int(stat.get("bets", 0))
        wins, losses, pushes = (int(stat.get(key, 0)) for key in ("wins", "losses", "pushes"))
        ci_low, ci_high = stat.get("ci_low"), stat.get("ci_high")
        rows.append({
            "id": candidate["id"],
            "strategy": candidate["name"],
            "market": candidate["market"],
            "variant": "Selective" if candidate.get("selective") else "All eligible games",
            "bets": bets if bets else None,
            "wins": wins if bets else None,
            "losses": losses if bets else None,
            "pushes": pushes if bets else None,
            "record": (f"{wins}–{losses}–{pushes}" if bets else None),
            "hit_rate": stat.get("hit_rate"),
            "first_half_hit_rate": stat.get("first_half_hit_rate"),
            "second_half_hit_rate": stat.get("second_half_hit_rate"),
            "chance_p": stat.get("p_value"),
            "bh_q": candidate.get("q_value"),
            "ci_low": ci_low,
            "ci_high": ci_high,
            "signal_status": "Provisional · not qualified" if candidate["id"] in provisional else "Not qualified",
            "source_url": "https://www.nfl.com/schedules/2026/by-week/week-1",
            "source_ids": ["X29-NFL-SCHEDULE", "REPO"],
        })
    if len(rows) != 30:
        raise ValueError(f"expected the frozen 30-variant results family; found {len(rows)}")
    return rows


def staking_rows(signals: list[dict] | None = None) -> list[dict]:
    """Economics ledger. No value is borrowed from signal performance."""
    signals = signals if signals is not None else signal_rows()
    return [{
        "id": row["id"],
        "strategy": row["strategy"],
        "market": row["market"],
        "opening_price": None,
        "closing_price": None,
        "stake": None,
        "net_roi": None,
        "clv": None,
        "reward": None,
        "staking_status": "Blocked · no authorized opening/closing quote",
        "source_url": row["source_url"],
        "source_ids": list(row["source_ids"]),
    } for row in signals]


def sequence_rows() -> list[dict]:
    analysis = read_json(ROOT / "nfl-results/analysis.json")
    board = {row["market"]: row for row in analysis.get("leaderboard", [])}
    benchmark = analysis.get("benchmarks", {})
    rows = []
    for market in MARKET_SEQUENCE:
        key = "spread" if market["key"] == "spread" else market["key"]
        if market["key"] in board:
            entry = board[market["key"]]
            state = "Provisional signal only; no price or live release" if entry.get("tier") == "provisional" else "Not qualified; paper research only"
            evidence = f"{entry.get('wins', 0)}–{entry.get('losses', 0)}; {entry.get('bets', 0)} scored games"
        elif market["key"] in benchmark:
            direction = benchmark[market["key"]].get("directional", {})
            evidence = f"{direction.get('wins', 0)}–{direction.get('losses', 0)}; {direction.get('bets', 0)} scored games"
            state = "Tested; signal status is not a market or staking qualification"
        else:
            evidence = "No comparable market test retrieved"
            state = "Model-only; historical price/outcome test not available"
        if market["key"] == "moneyline":
            evidence = "Model fair win probability / odds only; no historical operator quote"
            state = "Third; do not rank before side and total evidence gates"
        rows.append({
            "id": f"ORDER-{market['priority']}",
            "priority": market["priority"],
            "market": market["label"],
            "definition": "ATS point spread" if market["key"] == "spread" else market["units"],
            "evidence": evidence,
            "state": state,
            "next_gate": ("Independent prospective side shadow + authorized price snapshots" if market["key"] == "spread" else
                          "Side-stage review, then pace/drive inputs and prospective total test" if market["key"] == "total" else
                          "Side and total gates first; then calibrate win probabilities and benchmark prices"),
            "source_url": "https://www.nfl.com/schedules/2026/by-week/week-1",
            "source_ids": ["X29-NFL-SCHEDULE", "NFL-STANDINGS", "REPO"],
        })
    return rows


def demotion_decision(
    *,
    current_state: str,
    hard_triggers: list[str] | tuple[str, ...] = (),
    settled_bets: int = 0,
    roi_lower_bound_95: float | None = None,
) -> dict:
    """Fail-closed transition from live to paper; does not promote a strategy."""
    if current_state not in {"paper", "live"}:
        raise ValueError("current_state must be paper or live")
    unknown = set(hard_triggers) - HARD_DEMOTION_TRIGGERS
    if unknown:
        raise ValueError("unknown hard demotion trigger(s): " + ", ".join(sorted(unknown)))
    if isinstance(settled_bets, bool) or not isinstance(settled_bets, int) or settled_bets < 0:
        raise ValueError("settled_bets must be a non-negative integer")
    if roi_lower_bound_95 is not None and (
        isinstance(roi_lower_bound_95, bool) or not isinstance(roi_lower_bound_95, (int, float))
        or not math.isfinite(roi_lower_bound_95)
    ):
        raise ValueError("roi_lower_bound_95 must be finite or None")
    if current_state == "paper":
        return {"state": "paper", "action": "no_change", "reasons": [], "promotion": "never automatic"}
    if hard_triggers:
        return {
            "state": "paper",
            "action": "demote",
            "reasons": sorted(set(hard_triggers)),
            "promotion": "never automatic; all paper-entry gates must be repeated",
        }
    if settled_bets >= MIN_SETTLED_FOR_STATISTICAL_DEMOTION and roi_lower_bound_95 is not None \
            and roi_lower_bound_95 <= ROI_LOWER_BOUND_TRIGGER:
        return {
            "state": "paper",
            "action": "demote",
            "reasons": ["net_roi_lower_95_not_positive_after_minimum_sample"],
            "promotion": "never automatic; all paper-entry gates must be repeated",
        }
    return {"state": "live", "action": "remain_live", "reasons": [], "promotion": "not applicable"}


def result_summary() -> dict:
    analysis = read_json(ROOT / "nfl-results/analysis.json")
    games = read_csv(ROOT / "nfl-results/data/games-2026-w1-9.csv")
    spreads = analysis["benchmarks"]["spread"]["directional"]
    totals = analysis["benchmarks"]["total"]["directional"]
    return {
        "result_games": len(games),
        "result_game_source": "https://www.nfl.com/schedules/2026/by-week/week-1",
        "results_check": "136 NFL schedule rows; extraction reconciles W-L-T, PF and PA to the official standings",
        "spread_bets": spreads["bets"],
        "spread_wins": spreads["wins"],
        "spread_losses": spreads["losses"],
        "spread_hit_rate": spreads["hit_rate"],
        "spread_p": analysis["benchmarks"]["spread"].get("permutation_p_value"),
        "total_bets": totals["bets"],
        "total_wins": totals["wins"],
        "total_losses": totals["losses"],
        "total_hit_rate": totals["hit_rate"],
        "provisional": len([row for row in analysis["leaderboard"] if row.get("tier") == "provisional"]),
        "qualified": len([row for row in analysis["leaderboard"] if row.get("tier") == "qualified"]),
        "variants_tested": len(analysis["candidates"]),
        "correlation_n": analysis["correlations"]["leg_dependence"]["n_games"],
        "correlation_phi": analysis["correlations"]["leg_dependence"]["phi"],
        "correlation_p": analysis["correlations"]["leg_dependence"]["p_value"],
    }


def review_register() -> dict:
    return read_json(DATA / "review-register.json")


def validate_register() -> None:
    register = review_register()
    source_ids = set(sources_by_id())
    question_ids = [row["id"] for row in register["questions"]]
    suggestion_ids = [row["id"] for row in register["suggestions"]]
    flag_ids = [row["id"] for row in register["flags"]]
    for label, ids in (("question", question_ids), ("suggestion", suggestion_ids), ("flag", flag_ids)):
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate {label} ID in review-register.json")
    if [row["rank"] for row in register["suggestions"]] != list(range(1, len(suggestion_ids) + 1)):
        raise ValueError("suggestion ranks must be contiguous and ordered")
    for kind in ("questions", "suggestions", "flags"):
        for row in register[kind]:
            for field in ("evidence", "missing", "next_step", "source_ids") if kind == "questions" else \
                         ("evidence", "cost", "risk", "acceptance_test", "review_state", "source_ids") if kind == "suggestions" else \
                         ("evidence", "impact", "status", "source_ids"):
                value = row.get(field)
                if value is None or value == "" or value == []:
                    raise ValueError(f"{kind}:{row['id']}: missing {field}")
            if any(source_id not in source_ids for source_id in row["source_ids"]):
                raise ValueError(f"{kind}:{row['id']}: unknown source ID")
    for flag in register["flags"]:
        if flag.get("unverified_value") is not None:
            raise ValueError(f"{flag['id']}: unverified value must remain blank")


def input_manifest() -> dict:
    paths = [
        HERE / "policy.json",
        DATA / "review-register.json",
        DATA / "quote_snapshots.jsonl",
        ROOT / "research/nfl/results.json",
        ROOT / "research/nfl/receipts.json",
        ROOT / "research/sources.json",
        ROOT / "data/nfl-schedule-2026-w10.csv",
        ROOT / "nfl-results/analysis.json",
        ROOT / "nfl-results/data/games-2026-w1-9.csv",
    ]
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def validate_policy() -> dict:
    policy = read_json(HERE / "policy.json")
    expected = ["spread", "total", "moneyline"]
    actual = [row["market"] for row in policy.get("origination_order", [])]
    if actual != expected:
        raise ValueError("origination_order must be side/spread, total, then moneyline")
    contract = policy.get("price_snapshot_contract", {})
    if contract.get("store") != "data/quote_snapshots.jsonl":
        raise ValueError("price snapshot store path differs from the implementation")
    if contract.get("required_fields") != list(QUOTE_FIELDS):
        raise ValueError("policy quote fields differ from the append-only store schema")
    if contract.get("phases") != ["opening", "closing"]:
        raise ValueError("policy snapshot phases differ from the quote validator")
    configured_markets = contract.get("markets", {})
    if set(configured_markets) != set(MARKET_BY_KEY):
        raise ValueError("policy markets differ from the market matrix")
    for row in MARKET_SEQUENCE:
        if configured_markets[row["key"]].get("selections") != row["selections"]:
            raise ValueError(f"policy selections differ for {row['key']}")
    demotion = policy.get("demotion_gate", {})
    if demotion.get("automatic_promotion") is not False:
        raise ValueError("demotion policy must not enable automatic promotion")
    if demotion.get("minimum_settled_bets") != MIN_SETTLED_FOR_STATISTICAL_DEMOTION:
        raise ValueError("demotion sample threshold must match the executable gate")
    if demotion.get("roi_lower_bound_trigger") != ROI_LOWER_BOUND_TRIGGER:
        raise ValueError("demotion ROI threshold must match the executable gate")
    if demotion.get("confidence_level") != 0.95:
        raise ValueError("demotion confidence level must be 95%")
    if set(demotion.get("immediate_triggers", [])) != HARD_DEMOTION_TRIGGERS:
        raise ValueError("demotion hard-trigger list differs from the executable gate")
    return policy


def build_data() -> dict:
    validate_policy()
    validate_register()
    games = load_originations()
    quotes = validate_quote_ledger(read_jsonl(DATA / "quote_snapshots.jsonl"), game_ids={row["id"] for row in games})
    matrix = market_matrix(quotes)
    signals = signal_rows()
    stakes = staking_rows(signals)
    order = sequence_rows()
    summary = result_summary()
    expected_rows = len(games) * sum(len(row["selections"]) for row in MARKET_SEQUENCE)
    expected_slots = expected_rows * 2
    if len(matrix) != expected_rows:
        raise ValueError(f"market matrix coverage mismatch: expected {expected_rows}, got {len(matrix)}")
    if summary["result_games"] != 136:
        raise ValueError("official result feed row count changed; inspect before updating this desk")
    return {
        "markets": matrix,
        "signals": signals,
        "staking": stakes,
        "sequence": order,
        "summary": {
            **summary,
            "originated_games": len(games),
            "market_selection_rows": len(matrix),
            "expected_open_close_slots": expected_slots,
            "captured_quote_records": len(quotes),
            "opening_records": sum(row["phase"] == "opening" for row in quotes),
            "closing_records": sum(row["phase"] == "closing" for row in quotes),
            "price_status": "No authorized quote records in the repository; all market values remain blank",
        },
        "policy": validate_policy(),
        "register": review_register(),
        "source_ids": sorted(sources_by_id()),
        "input_sha256": input_manifest(),
    }
