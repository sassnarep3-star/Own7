#!/usr/bin/env python3
"""Price-snapshot store: one row per originated market, opening and closing, provenance optional.

The brief asks for a store that records the opening and closing number for *every market we
originate*. The store is built here in full. What it cannot do is invent the numbers.

Why every price cell is empty today, stated as a fact rather than an excuse:

  * NFL.com, the only publisher this repository reads, publishes **no price** for any game. Its
    Week 10 schedule page, read 2026-11-14 for this desk, lists date, kick-off time, network,
    venue and tickets for all 14 fixtures and not one spread, total or moneyline. That read is
    saved in ``evidence/nfl-week10-schedule-no-price.md`` and is the only evidence used to
    support the claim.
  * No sportsbook or odds vendor is registered in ``research/sources.json``, so no price can be
    cited under this repository's own rule that every table row names a registered official
    source.
  * NFL.com Terms §1.3 (read 2026-11-14) prohibits systematic retrieval to compile a database
    and permits individual non-commercial informational use only, so a scraped multi-book price
    history would not be releasable from here even if it were reachable.

So the store is *complete in shape and empty in price*: every market gets a row with its
``price_state`` set to a named reason, never to ``null`` that could be mistaken for "zero" or
"not looked at". Adding a licensed feed later means filling the same columns; nothing about the
schema changes, and no downstream consumer has to be rewritten.

Measurement contract (enforced by tests, not prose):

  * ``open_*`` and ``close_*`` are separate columns and never collapsed.
  * ``clv_points`` is computed only when both a price and a close exist, and is otherwise blank.
  * ``price_state`` must be one of PRICE_STATES; ``unpriced`` must carry a reason string.
  * A row whose ``price_state`` is ``priced`` must have every price field populated, so a partial
    capture cannot masquerade as a complete one.
"""
from __future__ import annotations

import csv
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent

# --------------------------------------------------------------------------- price states
PRICE_STATES = {
    "priced": "an opening and a closing number, both from a registered licensed source",
    "unpriced": "no price was retrieved; the reason is named in price_state_reason",
    "pending": "the market is originated but has not yet been quoted by any licensed source",
}
DEFAULT_REASON = (
    "NFL.com publishes no price for any fixture (verified on the Week 10 schedule page, "
    "2026-11-14); no sportsbook is a registered source in this repository; and NFL.com Terms "
    "§1.3 prohibits systematic compilation. The market therefore has no executable number."
)

MARKETS = ("spread", "total", "moneyline")


def originated_markets() -> list[dict]:
    """Every market this repository originates, in the required origination order.

    Order is a property of the desk, not of this function: side first, then total, then
    moneyline. ``originate.py`` enforces it; this store publishes one row per market so the
    snapshot covers 100% of what is originated, and the ``origination_order`` column on every row
    makes the sequence checkable from the CSV alone.
    """
    from originate import originated_board  # local import keeps this module runnable alone

    rows = []
    for entry in originated_board():
        game = entry["game"]
        for order, market in enumerate(MARKETS, start=1):
            built = entry["markets"][market]
            rows.append({
                "snapshot_id": f"{game['id']}-{market}",
                "origination_order": order,
                "market": market,
                "game_id": game["id"],
                "matchup": game["matchup"],
                "kickoff": game["kickoff"],
                # The desk's own fair number. Never a market number.
                "originated_line": built["model_fair"],
                "originated_side": built.get("side", ""),
                "originated_probability": built.get("p_home_win", ""),
                # Opening snapshot.
                "open_line": "", "open_price": "", "open_book": "", "open_taken_at": "",
                # Closing snapshot.
                "close_line": "", "close_price": "", "close_book": "", "close_taken_at": "",
                # Movement and closing value, computable only when both ends exist.
                "line_move": "", "clv_points": "",
                "price_state": "unpriced",
                "price_state_reason": DEFAULT_REASON,
                "source_ids": "NFL-STANDINGS NFL-SCHED-W10",
                "source_url": game["source_url"],
            })
    return rows


def validate(rows: list[dict]) -> list[str]:
    """Return a list of contract violations. Empty means the store is internally consistent."""
    problems = []
    for row in rows:
        state = row.get("price_state")
        if state not in PRICE_STATES:
            problems.append(f"{row['snapshot_id']}: unknown price_state {state!r}")
        priced_fields = [k for k in row if k.startswith(("open_", "close_")) and k != "openbook"]
        if state == "priced":
            missing = [k for k in priced_fields if row.get(k) in ("", None)]
            if missing:
                problems.append(
                    f"{row['snapshot_id']}: marked priced but {', '.join(sorted(missing))} blank")
            if not row.get("open_line") or not row.get("close_line"):
                problems.append(f"{row['snapshot_id']}: priced row requires an open and a close")
            if not (row.get("open_book") and row.get("close_book")):
                problems.append(f"{row['snapshot_id']}: priced row requires a named book")
        else:
            filled = [k for k in priced_fields if row.get(k) not in ("", None)]
            if filled:
                problems.append(
                    f"{row['snapshot_id']}: unpriced row must not carry a price value "
                    f"({', '.join(sorted(filled))})")
            if not row.get("price_state_reason"):
                problems.append(f"{row['snapshot_id']}: unpriced row must name its reason")
        if row.get("clv_points") not in ("", None):
            problems.append(f"{row['snapshot_id']}: CLV present without a captured closing price")
    return problems


def coverage(rows: list[dict]) -> dict:
    priced = [r for r in rows if r["price_state"] == "priced"]
    return {
        "markets_originated": len(rows),
        "markets_priced": len(priced),
        "markets_unpriced": len(rows) - len(priced),
        "coverage_pct": round(100 * len(priced) / len(rows), 1) if rows else 0.0,
        "by_market": {m: sum(1 for r in rows if r["market"] == m) for m in MARKETS},
        "clv_computable": sum(1 for r in rows if r.get("clv_points") not in ("", None)),
        "note": "Coverage counts rows that carry a real opening AND closing number. A row exists "
                "for every originated market so that adding a licensed feed fills the table "
                "rather than changing its shape.",
    }
