"""Append-only price-snapshot store for every market this project originates.

Requirement (2026-11-14): "Add a price-snapshot store that records opening and closing numbers
for every market we originate."

Scope and semantics
-------------------
A *market* here is one originated line for one game. The project originates exactly three
markets per game: the side (spread, home point of view), the total, and the moneyline
(two-sided fair prices). Week 10 has 14 fixtures, so the store holds 14 x 3 = 42 market records.

* opening  = the first snapshot ever recorded for the market (vintage v2026-11-12, captured
             2026-11-12 by the canonical origination);
* closing  = the last snapshot recorded before the game's kickoff. For the 13 games that had
             not kicked off as of the 2026-11-14 read, closing is this desk's v2026-11-14
             re-origination from the fresh standings vintage. For the one game already played
             (W10-01, kicked off 2026-11-12 8:15 PM ET) no post-kickoff origination is ever
             recorded, so closing is terminal and equals opening, with the capture-hour caveat
             published as flag LC-F01.

Market-side fields (the price an operator actually offers) are null everywhere with a stated
reason: no sportsbook price is licensed or retrieved in this repository (standing constraint
XS09/CF10). The difference column is null whenever the market line is null. Nothing is inferred.

Append-only guarantee
---------------------
snapshots lists may only grow. Each entry is identified by (captured_on, vintage) and carries the
inputs hash; two entries with the same identity must have identical values. Rebuilding from the
same inputs is byte-identical (enforced by build.py --check and the desk's tests). A snapshot's
values are never mutated once committed; a correction is a new entry with a note.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
for _p in (str(HERE), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import json  # noqa: E402

from stages import originate_staged, load_fixtures  # noqa: E402
from vintages import (  # noqa: E402
    VINTAGE_A, VINTAGE_B, READ_ON, STANDINGS_URL, SCHEDULE_URL,
)

MARKET_BLANK_REASON = (
    "No sportsbook price is licensed or retrieved in this repository (standing constraints "
    "XS09/CF10). The column exists so a rights-cleared source can fill it later; it is never "
    "inferred.")

MARKETS = (
    ("side", "Originated spread, stated from the home club's point of view "
             "(negative = home favoured)", "spread"),
    ("total", "Originated total (expected combined points)", "total"),
    ("moneyline", "Two-sided model fair prices (zero-hold), home and away", "price"),
)


def _kickoff_state(fixture: dict) -> dict:
    if fixture["Date"] <= READ_ON:
        return {"status": "kickoff passed",
                "detail": f"kickoff {fixture['Date']} {fixture['KickoffET']} ET precedes the "
                          f"{READ_ON} read; no post-kickoff origination is recorded"}
    return {"status": "pre-kickoff as of " + READ_ON,
            "detail": f"kickoff {fixture['Date']} {fixture['KickoffET']} ET is after the "
                      f"{READ_ON} read"}


def _market_value(game: dict, market: str) -> dict:
    if market == "side":
        return {"fair_line": game["stage_side_spread_home"], "unit": "points (home POV)"}
    if market == "total":
        return {"fair_line": game["stage_total"], "unit": "points"}
    return {"fair_home_price": game["stage_fair_home_price"],
            "fair_away_price": game["stage_fair_away_price"], "unit": "American odds (fair, zero-hold)"}


def build_store() -> dict:
    """Build the full store from the two vintages. Deterministic; no wall-clock input."""
    fixtures = {f["id"]: f for f in load_fixtures()}
    opening = {g["id"]: g for g in originate_staged(VINTAGE_A)}
    closing = {g["id"]: g for g in originate_staged(VINTAGE_B)}

    markets = []
    for game_id in sorted(fixtures):
        fixture = fixtures[game_id]
        state = _kickoff_state(fixture)
        terminal = state["status"].startswith("kickoff passed")
        for market, definition, kind in MARKETS:
            open_snap = {"captured_on": "2026-11-12", "vintage": VINTAGE_A,
                         **_market_value(opening[game_id], market),
                         "market_line": None, "market_reason": MARKET_BLANK_REASON}
            close_snap = {"captured_on": READ_ON, "vintage": VINTAGE_B,
                          **_market_value(closing[game_id], market),
                          "market_line": None, "market_reason": MARKET_BLANK_REASON}
            if terminal:
                # Terminal: the close is the last pre-kickoff snapshot, which is the opening
                # one; it is repeated as a pointer, never as a new invented number.
                close_snap = dict(open_snap)
                close_snap["status"] = "terminal - equals opening; no post-kickoff origination"
            else:
                close_snap["status"] = "current - last pre-kickoff origination to date"
            open_snap["status"] = "opening - first origination recorded"
            diff = None
            if market in ("side", "total"):
                if open_snap.get("fair_line") is not None and close_snap.get("fair_line") is not None:
                    diff = round(close_snap["fair_line"] - open_snap["fair_line"], 4)
            else:  # moneyline: move of the home fair price (away is its negative)
                if open_snap.get("fair_home_price") is not None \
                        and close_snap.get("fair_home_price") is not None:
                    diff = round(close_snap["fair_home_price"] - open_snap["fair_home_price"], 4)
            markets.append({
                "market_id": f"{game_id}:{market}",
                "game_id": game_id,
                "matchup": opening[game_id]["matchup"],
                "kickoff": opening[game_id]["kickoff"],
                "market": market,
                "kind": kind,
                "definition": definition,
                "kickoff_state": state,
                "opening": open_snap,
                "closing": close_snap,
                "open_to_close_move": diff,
                "market_line": None,
                "market_reason": MARKET_BLANK_REASON,
                "fair_minus_market": None,
                "source_ids": ["NFL-STANDINGS", "NFL-SCHED-W10", "PYTH-NFL", "REPO",
                               "LC-NFL-STANDINGS-1114", "LC-NFL-SCHED-REG10-1114"],
                "game_source_url": fixture["GameURL"],
                "source_url": fixture["SourceURL"],
            })
    return {
        "schema_version": 1,
        "store": "nfl-lifecycle-3f5c/price-snapshots",
        "built_from": [
            {"vintage": VINTAGE_A, "purpose": "opening snapshots", "checked_on": "2026-11-12",
             "source_url": STANDINGS_URL},
            {"vintage": VINTAGE_B, "purpose": "closing snapshots (pre-kickoff games)",
             "checked_on": READ_ON, "source_url": STANDINGS_URL},
        ],
        "schedule_source": SCHEDULE_URL,
        "policy": {
            "append_only": "snapshot entries are identified by (captured_on, vintage); entries "
                           "are never mutated or removed; a correction is a new entry",
            "closing_rule": "the closing number is the last origination recorded before kickoff; "
                            "after kickoff a market is terminal and its close is frozen",
            "market_fields": MARKET_BLANK_REASON,
            "difference_rule": "fair minus market is published only when both exist; otherwise "
                               "it stays blank (never inferred)",
            "reconciliation": "the ordered pipeline reproduces the canonical engine's numbers "
                              "exactly on the frozen vintage (stages.reconcile_with_canonical)",
        },
        "counts": {"markets": len(markets), "games": len(fixtures),
                   "markets_per_game": len(MARKETS)},
        "markets": markets,
    }


def check_store(store: dict) -> list[str]:
    """Invariants that must hold for the store to be publishable. Returns violation strings."""
    problems = []
    for market in store["markets"]:
        mid = market["market_id"]
        for phase in ("opening", "closing"):
            snap = market[phase]
            if snap["market_line"] is not None:
                problems.append(f"{mid}/{phase}: market_line filled without a rights-cleared source")
            if (snap["market_line"] is None
                    and snap.get("market_reason") != MARKET_BLANK_REASON):
                problems.append(f"{mid}/{phase}: blank market cell without its stated reason")
        # Difference column may only exist when both sides exist.
        if market["market_line"] is None and market["fair_minus_market"] is not None:
            problems.append(f"{mid}: difference published while the market line is blank")
        if market["opening"]["vintage"] != VINTAGE_A:
            problems.append(f"{mid}: opening snapshot is not on the opening vintage")
    if store["counts"]["markets"] != 42:
        problems.append(f"expected 42 market records, found {store['counts']['markets']}")
    return problems
