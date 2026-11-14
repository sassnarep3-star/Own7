"""Build decision-grade price, signal/staking and demotion artifacts and pages.

All generated HTML is static and source-linked. Unknown values are rendered as truly blank
cells and remain null in JSON/CSV. No network request, account access, odds scraping or bet
execution occurs here.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data"
SITE = HERE / "site"

sys.path.insert(0, str(HERE))
import demotion
import store as price_store

PAGES = [
    ("index.html", "Decision summary"),
    ("prices.html", "Fair / market / difference"),
    ("snapshots.html", "Opening & closing store"),
    ("leaderboard.html", "Signal vs staking"),
    ("demotion.html", "Live-to-paper gate"),
    ("flagged.html", "Flagged for Review"),
    ("sources.html", "Official sources"),
]

CSS = r""":root{color-scheme:light;--bg:#f5f7f5;--panel:#fff;--ink:#17241d;--muted:#5d6e63;--line:#d8e1d9;--accent:#285b3a;--accent-dark:#183d28;--warn:#80500b;--bad:#8b2f2f;--soft:#edf4ee}*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink);line-height:1.55}.skip{position:absolute;left:-9999px;top:0;background:var(--accent);color:#fff;padding:.55rem;z-index:20}.skip:focus{left:.75rem;top:.75rem}.top{background:#14251b;color:#fff;padding:1rem max(1rem,calc((100% - 1320px)/2))}.brand{display:flex;gap:.7rem;align-items:baseline;flex-wrap:wrap}.brand strong{font-size:1.15rem;letter-spacing:.06em}.brand span{color:#d3e2d5}.top nav{display:flex;gap:.35rem;flex-wrap:wrap;margin-top:.75rem}.top nav a{color:#e3eee4;text-decoration:none;padding:.42rem .58rem;border-radius:.35rem;font-size:.86rem;min-height:2rem;display:inline-flex;align-items:center}.top nav a:hover,.top nav a:focus,.top nav a[aria-current=page]{background:#315f3d;color:#fff}.top nav a:focus,a:focus,button:focus{outline:3px solid #e0aa3f;outline-offset:2px}main{max-width:1320px;margin:0 auto;padding:1.25rem}.eyebrow{font-size:.78rem;color:var(--muted);letter-spacing:.09em;text-transform:uppercase}h1{margin:.2rem 0 .35rem;font-size:clamp(1.65rem,3vw,2.3rem);letter-spacing:-.025em}h2{font-size:1.25rem;margin:1.5rem 0 .55rem}h3{font-size:1.05rem;margin:1.1rem 0 .4rem}.subtitle,.note{color:var(--muted);max-width:85ch}.notice{border-left:4px solid var(--warn);background:#fff8e9;border-radius:.4rem;padding:.85rem 1rem;margin:1rem 0}.notice strong{display:block}.notice p{margin:.3rem 0 0}.notice.good{border-color:var(--accent);background:var(--soft)}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:.7rem;margin:1rem 0}.metric{background:var(--panel);border:1px solid var(--line);border-radius:.65rem;padding:.8rem}.metric strong{display:block;font-size:1.5rem;color:var(--accent)}.metric span{display:block;color:var(--muted);font-size:.82rem}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:.7rem;margin:1rem 0}.card{display:block;background:var(--panel);border:1px solid var(--line);border-radius:.65rem;padding:.85rem 1rem;text-decoration:none;color:inherit}.card:hover,.card:focus{border-color:var(--accent)}.card h2{margin:0 0 .3rem;font-size:1.03rem;color:var(--accent)}.card p{margin:0;color:var(--muted);font-size:.88rem}.table-wrap{overflow:auto;max-width:100%;border:1px solid var(--line);border-radius:.55rem;background:var(--panel);margin:.7rem 0}table{border-collapse:collapse;width:100%;min-width:850px;font-size:.84rem}caption{text-align:left;padding:.65rem;font-weight:650;color:var(--muted)}th,td{border-top:1px solid var(--line);padding:.5rem .55rem;text-align:left;vertical-align:top}thead th{background:#eaf0eb;position:sticky;top:0;z-index:1}tbody tr:nth-child(even){background:#fafcf9}tbody tr:hover{background:#f2f7f2}td.num{font-variant-numeric:tabular-nums;white-space:nowrap}td.refs{min-width:140px;max-width:300px}td.refs a{display:inline-block;margin:0 .35rem .15rem 0;font-size:.78rem;white-space:nowrap}.table-wrap td a{display:inline-flex;align-items:center;min-height:24px;padding:.2rem .3rem;margin:.08rem .12rem;border-radius:.25rem}a{color:#235c38;overflow-wrap:anywhere}p a{text-decoration:underline;text-underline-offset:2px}.blank{min-width:70px;background:repeating-linear-gradient(135deg,#fff,#fff 6px,#f4f6f3 6px,#f4f6f3 12px)}.badge{display:inline-block;border-radius:.3rem;padding:.12rem .42rem;font-size:.76rem;font-weight:650;background:#edf1ee;color:#354a3a}.badge.warn{background:#fff2d7;color:#80500b}.badge.bad{background:#fbe8e8;color:#8b2f2f}.badge.good{background:#e5f2e8;color:#235c38}.panel{background:var(--panel);border:1px solid var(--line);border-radius:.65rem;padding:.9rem 1rem;margin:1rem 0}.panel ul,.panel ol{padding-left:1.2rem}.panel li{margin:.35rem 0}.section{margin:1.5rem 0}.source-line{display:flex;gap:.4rem;flex-wrap:wrap;margin:1rem 0}.source-line a{display:inline-block;padding:.25rem .4rem;border:1px solid var(--line);border-radius:.3rem;font-size:.78rem;background:#fff}.download-list{display:flex;gap:.5rem;flex-wrap:wrap;margin:.8rem 0}.button{display:inline-block;border:1px solid var(--accent);border-radius:.35rem;padding:.4rem .65rem;text-decoration:none;background:#fff}.button.primary{background:var(--accent);color:#fff}details{background:#fff;border:1px solid var(--line);border-radius:.55rem;padding:.75rem .9rem;margin:.85rem 0}summary{font-weight:650;cursor:pointer}footer{border-top:1px solid var(--line);margin-top:2rem;padding:1rem 0 1.5rem;color:var(--muted);font-size:.82rem}footer p{margin:.3rem 0}@media(max-width:640px){main{padding:1rem}.top{padding:1rem}.top nav a{font-size:.78rem;padding:.4rem}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}table{min-width:780px}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}"""


def load_json(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _price(value: Any) -> str | None:
    if value is None:
        return None
    number = int(value)
    return f"+{number}" if number > 0 else str(number)


def _fmt(value: Any, places: int = 4) -> str | None:
    if value is None:
        return None
    if isinstance(value, float):
        return f"{value:.{places}f}".rstrip("0").rstrip(".")
    return str(value)


def build_signal_staking(analysis: dict, store_data: dict) -> dict:
    """Keep signal ranking and stake/economic outcomes in separate data structures."""
    leaderboard_tier = {r["id"]: r["tier"] for r in analysis.get("leaderboard", [])}
    candidates = analysis.get("candidates", [])
    tier_order = {"qualified": 0, "provisional": 1, "rejected": 2}
    ordered = sorted(
        candidates,
        key=lambda c: (
            tier_order.get(leaderboard_tier.get(c["id"], "rejected"), 2),
            c.get("q_value") if isinstance(c.get("q_value"), (int, float)) else 1.0,
            c.get("stat", {}).get("p_value") if c.get("stat", {}).get("p_value") is not None else 1.0,
            -(c.get("stat", {}).get("hit_rate") or 0.0),
            c["id"],
        ),
    )
    signal_rows = []
    staking_rows = []
    for rank, candidate in enumerate(ordered, start=1):
        stat = candidate["stat"]
        tier = leaderboard_tier.get(candidate["id"], "rejected")
        signal_rows.append({
            "id": candidate["id"],
            "rank": rank,
            "strategy": candidate["name"],
            "market": candidate["market"],
            "variant": "selective" if candidate.get("selective") else "all games",
            "reference": candidate.get("reference") or "walk-forward model benchmark",
            "n": stat.get("bets"),
            "wins": stat.get("wins"),
            "losses": stat.get("losses"),
            "hit_rate": stat.get("hit_rate"),
            "p_value": stat.get("p_value"),
            "q_value": candidate.get("q_value"),
            "ci_low": stat.get("ci_low"),
            "ci_high": stat.get("ci_high"),
            "tier": tier,
            "qualified": candidate.get("qualified") is True,
            "merit_points": next((r["merit_points"] for r in analysis.get("leaderboard", []) if r["id"] == candidate["id"]), 0),
            "source_url": "https://www.nfl.com/schedules/2026/by-week/week-9",
            "source_ids": ["X29-NFL-SCHEDULE", "NFL-STANDINGS", "REPO"],
        })
        staking_rows.append({
            "id": candidate["id"],
            "strategy": candidate["name"],
            "market": candidate["market"],
            "authorized_price_snapshots": 0,
            "roi": None,
            "clv": None,
            "net_return_lower_95": None,
            "stake_units": None,
            "cash_reward": None,
            "status": "Not measured: no authorized quote/settlement record.",
            "source_url": "https://www.nfl.com/odds/",
            "source_ids": ["X87-NFL-ODDS-1414", "X87-NFL-TERMS-1414", "REPO"],
        })
    counts = analysis.get("leaderboard_counts", {})
    return {
        "schema_version": 1,
        "checked_on": "2026-11-14",
        "signal_policy": {
            "sort_rule": "Signal-only diagnostic ordering: qualification tier first, then Benjamini-Hochberg q ascending, exact p ascending, hit rate descending, and stable strategy ID. Stake/ROI fields are not read; ranks are not a qualification claim.",
            "meaning": "A directional backtest against the stated neutral league-mean reference is not a sportsbook market edge or a profit claim.",
            "official_result_games": analysis.get("inputs", {}).get("games"),
            "historically_scored_games": analysis.get("inputs", {}).get("rows_scored"),
            "strategies_tested": len(candidates),
            "qualified": counts.get("qualified", 0),
            "provisional": counts.get("provisional", 0),
            "rejected": counts.get("rejected", 0),
        },
        "staking_policy": {
            "ranking_separate": True,
            "roi_is_signal_input": False,
            "authorized_price_snapshots": store_data["counts"]["quotes_collected"],
            "roi": None,
            "clv": None,
            "net_return_lower_95": None,
            "status": "No staking leaderboard can be ranked until authorized prices and settlement records exist.",
        },
        "signal_rows": signal_rows,
        "staking_rows": staking_rows,
    }


def build_flags() -> dict:
    return {
        "schema_version": 1,
        "checked_on": "2026-11-14",
        "flags": [
            {
                "id": "PC01",
                "item": "No odds at the checked NFL odds route",
                "finding": "The official NFL.com /odds/ path returned the NFL 404 page on 2026-11-14. This says nothing definitive about every independent operator feed.",
                "unverified_value": None,
                "status": "Needs review",
                "impact": "No verified opening/closing market line or price; market values, differences, ROI and CLV stay blank.",
                "source_url": "https://www.nfl.com/odds/",
                "source_ids": ["X87-NFL-ODDS-1414", "X87-NFL-TERMS-1414"],
            },
            {
                "id": "PC02",
                "item": "No documented NFL-data permission for a betting/market feed",
                "finding": "The current NFL.com Terms §1.3 page limits use to individual non-commercial informational purposes and bars systematic collection absent express prior written consent. No separate permission is evidenced in the repository.",
                "unverified_value": None,
                "status": "Blocked",
                "impact": "A new quote provider alone does not authorize combining NFL.com-derived features with betting use.",
                "source_url": "https://www.nfl.com/legal/terms/",
                "source_ids": ["X87-NFL-TERMS-1414", "REPO"],
            },
            {
                "id": "PC03",
                "item": "Week 10 model snapshot lacks an exact capture/cutoff timestamp",
                "finding": "The saved model result has a snapshot date only. The official Week 10 schedule page displayed WAS–NYG as FINAL on the current re-read; the historical model output is therefore not treated as a live or fully pregame-verified quote.",
                "unverified_value": None,
                "status": "Needs review",
                "impact": "Existing model numbers are reproducible historical outputs, not executable opening lines.",
                "source_url": "https://www.nfl.com/schedules/2026/by-week/week-10",
                "source_ids": ["X87-NFL-W10-1414", "NFL-STANDINGS", "REPO"],
            },
            {
                "id": "PC04",
                "item": "No qualified strategy or live strategy exists in the project record",
                "finding": "The NFL project protocol is paper research only and disables cash payments. Separately, the 30-candidate NFL results pipeline has zero qualified entries; one provisional result is not a live strategy.",
                "unverified_value": None,
                "status": "Research-only",
                "impact": "The demotion policy is defined and tested but has not executed against an actual live strategy.",
                "source_url": "https://www.nfl.com/legal/terms/",
                "source_ids": ["X87-NFL-TERMS-1414", "REPO"],
            },
            {
                "id": "PC05",
                "item": "Model-originated estimates are not independently market-calibrated fair values",
                "finding": "The stored Week 10 output contains model-originated spread, total and win-probability estimates, but no corresponding authorized quote snapshot or independently verified market calibration.",
                "unverified_value": None,
                "status": "Needs validation",
                "impact": "These model-only numbers are displayed as derived estimates and are not presented as validated fair prices or an edge.",
                "source_url": "https://www.nfl.com/schedules/2026/by-week/week-10",
                "source_ids": ["X87-NFL-W10-1414", "NFL-STANDINGS", "REPO"],
            },
        ],
    }


@lru_cache(maxsize=1)
def source_registry() -> dict[str, dict]:
    return {row["id"]: row for row in load_json("research/sources.json")}


def source_links(source_ids: list[str], direct_url: str | None = None) -> str:
    registry = source_registry()
    parts = []
    if direct_url:
        parts.append(f'<a href="{esc(direct_url)}" target="_blank" rel="noopener noreferrer">Official page ↗</a>')
    for source_id in source_ids:
        source = registry[source_id]
        if source["url"] == direct_url:
            continue
        parts.append(
            f'<a href="{esc(source["url"])}" title="{esc(source["title"])}" '
            f'target="_blank" rel="noopener noreferrer">{esc(source_id)} ↗</a>'
        )
    return " ".join(parts)


def cell(value: Any, *, raw: bool = False, numeric: bool = False) -> str:
    if value is None or value == "":
        return '<td class="blank" data-empty="true" aria-label="Blank: not verified, not collected, or not applicable"></td>'
    cls = ' class="num"' if numeric else ""
    contents = str(value) if raw else esc(value)
    return f"<td{cls}>{contents}</td>"


def data_table(
    table_id: str,
    caption: str,
    columns: list[tuple[str, str]],
    rows: list[dict],
    *,
    note: str = "",
) -> str:
    head = "".join(f"<th scope=\"col\">{esc(label)}</th>" for label, _ in columns)
    body = []
    for index, row in enumerate(rows):
        ids = row.get("source_ids", ["REPO"])
        if not ids:
            raise ValueError(f"{table_id} row {row.get('id', index)} has no source IDs")
        cells = []
        for _, field in columns:
            if field == "__sources":
                value = source_links(ids, row.get("citation_url", row.get("source_url")))
                cells.append(cell(value, raw=True))
            else:
                value = row.get(field)
                cells.append(cell(value, numeric=isinstance(value, (int, float)) and not isinstance(value, bool)))
        body.append(
            f'<tr data-row-id="{esc(row.get("id", index))}" '
            f'data-source-ids="{esc(" ".join(ids))}" data-status="{esc(row.get("status", ""))}">'
            + "".join(cells) + "</tr>"
        )
    return (
        f'<div class="table-wrap" role="region" aria-label="{esc(caption)}, scroll horizontally for more columns" tabindex="0">'
        f'<table id="{esc(table_id)}"><caption>{esc(caption)}</caption><thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div>'
        + (f'<p class="note">{note}</p>' if note else "")
    )


def page(slug: str, title: str, subtitle: str, body: str) -> str:
    nav = "".join(
        f'<a href="{esc(href)}"' + (' aria-current="page"' if href == slug else "")
        + f'>{esc(label)}</a>'
        for href, label in PAGES
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · OWN7 NFL market controls</title>
<meta name="description" content="{esc(subtitle)}">
<link rel="stylesheet" href="style.css"></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="brand"><strong>OWN7</strong><span>NFL market &amp; risk controls · research only</span></div>
<nav aria-label="NFL market control sections">{nav}</nav></header>
<main id="main"><p class="eyebrow">Snapshot review · 2026-11-14 · no live feed · no wagers</p>
<h1>{esc(title)}</h1><p class="subtitle">{subtitle}</p>
{body}
<footer><p>OWN7 independent research; NFL data links to NFL.com. Not affiliated with or endorsed by the NFL.
Unknown market values remain blank. A repository status is not an account-status check.</p>
<p><a href="../../nfl-results-games.html">Official results &amp; backtest source table</a> ·
<a href="../../nfl-results-suggestions.html">Suggestions for review</a> ·
<a href="../../nfl-skill-cfdd/site/questions.html">Open questions</a></p></footer>
</main></body></html>
'''


def build_pages(store_data: dict, signal_data: dict, demotion_data: dict, flags_data: dict) -> dict[Path, str]:
    analysis = load_json("nfl-results/analysis.json")
    result_feed = analysis["inputs"]
    leg_corr = analysis["correlations"]["leg_dependence"]

    market_rows = []
    for row in store_data["markets"]:
        if row["market_type"] == "moneyline":
            model_value = f'{row["model_fair_value"] * 100:.2f}% home win probability'
            fair_price = f'Home {_price(row["model_fair_home_price_american"])} / away {_price(row["model_fair_away_price_american"])}'
        else:
            model_value = f'{_fmt(row["model_fair_value"])} {row["model_fair_value_unit"]}'
            fair_price = None
        market_rows.append({
            **row,
            "id": row["market_id"],
            "order_label": f'{row["market_order"]} · {row["market_label"]}',
            "model_display": model_value,
            "fair_price_display": fair_price,
            "market_display": row["market_value"],
            "difference_display": row["difference"],
            "opening_display": row["opening_value"],
            "closing_display": row["closing_value"],
            "opening_prices_display": None,
            "closing_prices_display": None,
            "status_display": "No authorized quote; not collected",
        })

    page_index_body = (
        '<div class="notice"><strong>Decision: keep every strategy in paper/research mode.</strong>'
        '<p>The repository has no authorized market-quote source, and its NFL data-use protocol does not authorize betting use. Opening/closing market numbers, market differences, ROI and CLV are blank—not zero. The NFL odds URL checked here returned 404; that finding is limited to that path and does not establish whether another operator feed exists.</p></div>'
        f'<div class="metrics"><div class="metric"><strong>{store_data["counts"]["games_originated"]}</strong><span>Week 10 model game records (date-only cutoff)</span></div>'
        f'<div class="metric"><strong>{store_data["counts"]["markets_originated"]}</strong><span>markets indexed in order: side, total, moneyline</span></div>'
        f'<div class="metric"><strong>{store_data["counts"]["opening_closing_slots"]}</strong><span>opening/closing snapshot slots, all unfilled</span></div>'
        f'<div class="metric"><strong>{store_data["counts"]["quotes_collected"]}</strong><span>source-authorized market quotes captured</span></div>'
        f'<div class="metric"><strong>{signal_data["signal_policy"]["strategies_tested"]}</strong><span>signal variants evaluated on official results</span></div>'
        f'<div class="metric"><strong>{signal_data["signal_policy"]["qualified"]}</strong><span>qualified strategies in the results pipeline</span></div>'
        f'<div class="metric"><strong>{signal_data["signal_policy"]["provisional"]}</strong><span>provisional result; not a live or profitable strategy</span></div></div>'
        '<div class="cards">'
        '<a class="card" href="prices.html"><h2>Fair / market / difference</h2><p>Separate columns for all three markets. Model values are derived; market values and differences stay blank until an authorized quote exists.</p></a>'
        '<a class="card" href="snapshots.html"><h2>Opening &amp; closing store</h2><p>Two append-only slots for every originated market, with explicit provenance and rights requirements.</p></a>'
        '<a class="card" href="leaderboard.html"><h2>Signal vs staking</h2><p>Forecast evidence is ranked independently. ROI, CLV and stake returns cannot mask signal quality.</p></a>'
        '<a class="card" href="demotion.html"><h2>Live-to-paper gate</h2><p>Defined fail-closed checks and project thresholds; no live strategy is claimed or demoted here.</p></a>'
        '<a class="card" href="flagged.html"><h2>Flagged for Review</h2><p>Open price, rights and timing questions are explicit, with official links for manual review.</p></a>'
        '<a class="card" href="sources.html"><h2>Official sources</h2><p>Read the NFL schedule, results, odds-path check and terms directly.</p></a></div>'
        '<section class="section"><h2>What the evidence allows today</h2>'
    )
    requirements = [
        {"id": "R01", "requirement": "Opening and closing snapshots", "status": f'{store_data["counts"]["opening_closing_slots"]} explicit slots exist; all are unfilled because no authorized quote values are available.', "source_url": "https://www.nfl.com/odds/", "source_ids": ["X87-NFL-ODDS-1414", "X87-NFL-TERMS-1414", "REPO"]},
        {"id": "R02", "requirement": "Model fair, market, difference", "status": "Separate fields exist. Model values are uncalibrated derived estimates; market and difference remain null.", "source_url": "https://www.nfl.com/standings/", "source_ids": ["NFL-STANDINGS", "X87-NFL-W10-1414", "X87-NFL-ODDS-1414", "REPO"]},
        {"id": "R03", "requirement": "Order: side → total → moneyline", "status": "The ledger stores every originated game in this order; no market value is implied by order.", "source_url": "https://www.nfl.com/schedules/2026/by-week/week-10", "source_ids": ["NFL-SCHED-W10", "X87-NFL-W10-1414", "NFL-STANDINGS"]},
        {"id": "R04", "requirement": "Verified results for backtests", "status": f'{result_feed["games"]} NFL schedule/result rows are saved for Weeks 1–9; {result_feed["rows_scored"]} walk-forward games were scored. ROI remains unavailable without authorized prices.', "source_url": "https://www.nfl.com/schedules/2026/by-week/week-9", "source_ids": ["X29-NFL-SCHEDULE", "NFL-STANDINGS"]},
        {"id": "R05", "requirement": "Separate signal and staking", "status": f'{signal_data["signal_policy"]["qualified"]} qualified, {signal_data["signal_policy"]["provisional"]} provisional, {signal_data["signal_policy"]["rejected"]} rejected in the separate 30-variant results pipeline; staking economics are blank for every candidate.', "source_url": "https://www.nfl.com/schedules/2026/by-week/week-9", "source_ids": ["X29-NFL-SCHEDULE", "X87-NFL-ODDS-1414", "REPO"]},
        {"id": "R06", "requirement": "Demote a live strategy to paper", "status": "Fail-closed policy and executable pure function are tested; no live deployment was inspected and none is recorded by this repository.", "source_url": "https://www.nfl.com/legal/terms/", "source_ids": ["X87-NFL-TERMS-1414", "REPO"]},
        {"id": "R07", "requirement": "Keep NFL workstream metrics scoped", "status": "The W1 overview's 0 qualified / eight blocked and this results pipeline's 0 qualified / one provisional are separate evaluations; they are not merged into a single metric.", "source_url": "https://www.nfl.com/schedules/2026/by-week/week-9", "source_ids": ["X29-NFL-SCHEDULE", "REPO"]},
    ]
    page_index_body += data_table("requirements", "Requirement status", [
        ("Requirement", "requirement"), ("Current evidence / limit", "status"), ("Sources", "__sources")
    ], requirements, note="A source link supports only the stated scope; a project rule is labeled as project policy, not an NFL standard.")
    page_index_body += (
        f'<div class="panel"><h2>Official results and correlations</h2><p>The results pipeline stores {result_feed["games"]} official score rows (Weeks 1–9), scores {result_feed["rows_scored"]} games in Weeks 2–9, and preserves source URLs per row. Same-game side/total outcome dependence on the originated board is φ={leg_corr["phi"]:.4f}, n={leg_corr["n_games"]}, p={leg_corr["p_value"]:.4f}; it uses model-originated legs and NFL.com final scores, not a sportsbook line. This is not a market correlation or market-edge result.</p>'
        '<p><a href="../../nfl-results-games.html">Review the official results rows</a> · '
        '<a href="../../nfl-results-correlation.html">Review correlation methods and limitations</a> · '
        '<a href="../../nfl-results-suggestions.html">Review suggestions before choosing an implementation path</a></p>'
        '<p>The separate W1 line-origination overview reports 0 qualified / eight blocked. This 30-candidate results pipeline has its own scope and is not reconciled into that metric. <a href="../../index.html">Review the W1 overview</a>.</p></div>'
    )
    page_index_body += "</section>"

    page_prices_body = (
        '<div class="notice good"><strong>Three columns mean three different things.</strong>'
        '<p>Model fair value is an existing model-originated estimate, not an independently calibrated price. Market value is the matching closing market number (or the de-vigged home probability for moneyline); difference is model fair minus market. Because no authorized quote is present, market and difference cells are blank.</p></div>'
        + data_table("market-ledger", "Every originated Week 10 game-market row", [
            ("Game", "matchup"), ("Order / market", "order_label"),
            ("Model fair value", "model_display"), ("Model fair moneyline prices", "fair_price_display"),
            ("Market value (close)", "market_display"), ("Difference", "difference_display"),
            ("Opening value", "opening_display"), ("Closing value", "closing_display"),
            ("Status", "status_display"), ("Official sources", "__sources"),
        ], market_rows, note="Moneyline model estimates are home win probability plus the model's derived home/away American prices; these have not been independently market-calibrated. No market probability is available. The Week 10 values are date-only model outputs, not verified pre-kickoff lines. See Flagged for Review." )
        + '<details><summary>Definitions and future capture contract</summary><ul>'
        '<li>Side: home spread points (negative means the home team is favored); total: game points; moneyline: home win probability.</li>'
        '<li>Difference is defined only for a matching market/settlement contract. For moneyline, it is model home probability minus de-vigged market home probability from a complete paired quote.</li>'
        '<li>Each market has an opening and a closing quote slot in the linked append-only store. Required fields include operator, capture time, exact source URL, authorization reference and settlement contract.</li>'
        '<li>There are no values to fill from the checked NFL odds route, so no market line, price or difference is inferred.</li></ul></details>'
    )

    snapshot_rows = []
    for row in store_data["snapshots"]:
        snapshot_rows.append({
            **row,
            "id": row["snapshot_id"],
            "phase_label": row["phase"].title(),
            "market_label": f'{row["market_order"]} · {row["market_type"].title()}',
            "line_display": row["market_number"],
            "home_price_display": _price(row["home_price_american"]),
            "away_price_display": _price(row["away_price_american"]),
            "over_price_display": _price(row["over_price_american"]),
            "under_price_display": _price(row["under_price_american"]),
            "status_display": "Not collected — source/rights gate closed",
            "source_url": None,
            "citation_url": row["official_game_url"],
            "source_ids": ["X87-NFL-ODDS-1414", "X87-NFL-TERMS-1414", "NFL-SCHED-W10", "X87-NFL-W10-1414"],
        })
    page_snapshots_body = (
        '<div class="notice"><strong>Opening/closing slots are present; quoted numbers are not.</strong>'
        '<p>Every originated market has one opening and one closing row in the store. All price fields, line values, capture times, operator names and quote-provider URLs remain empty because no authorized provider is registered. The project contract defines opening as a source-attested market-open quote (or explicitly first observed), and closing as the last quote in the 15-minute pre-kickoff window. A blank is not zero or consensus.</p></div>'
        + data_table("snapshot-store", "Append-only opening and closing snapshot slots", [
            ("Game", "matchup"), ("Market", "market_label"), ("Phase", "phase_label"),
            ("Number", "line_display"), ("Home price", "home_price_display"),
            ("Away price", "away_price_display"), ("Over price", "over_price_display"),
            ("Under price", "under_price_display"), ("Captured at UTC", "captured_at_utc"),
            ("Market open at UTC", "market_open_at_utc"), ("Opening basis", "quote_sequence_basis"),
            ("Operator", "operator"), ("Quote source", "source_url"),
            ("Authorization ref", "authorization_ref"), ("Settlement contract", "settlement_contract_id"),
            ("Status", "status_display"), ("Official game / absence sources", "__sources"),
        ], snapshot_rows, note=f'{len(snapshot_rows)} explicit slots = {len(store_data["markets"])} originated markets × 2 phases. `price-snapshots-2026-11-14.csv` is the downloadable machine-readable register.')
        + '<p><a class="button" href="../data/price-snapshots-2026-11-14.csv">Download the opening/closing CSV</a> · '
        '<a class="button" href="../data/price-store-2026-11-14.json">Download the JSON store</a></p>'
    )

    signal_rows = []
    for row in signal_data["signal_rows"]:
        stat_ci = None if row["ci_low"] is None else f'{row["ci_low"] * 100:.1f}%–{row["ci_high"] * 100:.1f}%'
        signal_rows.append({
            **row,
            "record": None if row["wins"] is None else f'{row["wins"]}–{row["losses"]}',
            "hit_display": None if row["hit_rate"] is None else f'{row["hit_rate"] * 100:.1f}%',
            "p_display": _fmt(row["p_value"], 6),
            "q_display": _fmt(row["q_value"], 6),
            "ci_display": stat_ci,
            "tier_display": row["tier"].title(),
        })
    staking_rows = [{
        **row,
        "quote_count_display": row["authorized_price_snapshots"],
        "roi_display": row["roi"],
        "clv_display": row["clv"],
        "return_display": row["net_return_lower_95"],
        "stake_status_display": row["status"],
    } for row in signal_data["staking_rows"]]
    page_leaderboard_body = (
        '<div class="notice good"><strong>Signal rank and staking results are independent.</strong>'
        '<p>The signal ordering reads only the registered signal test statistics. ROI, CLV, stake size, drawdown and realized return are stored in a separate table and never enter the signal sort key. No qualified entry receives merit points; cash rewards are disabled.</p></div>'
        f'<p class="panel">Results feed: {result_feed["games"]} official Week 1–9 results; {result_feed["rows_scored"]} games evaluated walk-forward. The current signal board has {signal_data["signal_policy"]["qualified"]} qualified, {signal_data["signal_policy"]["provisional"]} provisional and {signal_data["signal_policy"]["rejected"]} rejected variants out of {signal_data["signal_policy"]["strategies_tested"]} tests. The single provisional entry is not a market edge or a reward winner.</p>'
        + data_table("signal-leaderboard", "Signal-only diagnostic order (tier, BH q, exact p, hit rate)", [
            ("Signal rank", "rank"), ("Strategy", "strategy"), ("Market", "market"),
            ("Variant", "variant"), ("n", "n"), ("Record", "record"),
            ("Hit rate", "hit_display"), ("Exact p", "p_display"),
            ("BH q", "q_display"), ("95% interval", "ci_display"),
            ("Gate tier", "tier_display"), ("Official results sources", "__sources"),
        ], signal_rows, note="Hit-rate confidence intervals are the stored binomial intervals from the retrospective walk-forward analysis. They are not date-block intervals, market ROI or proof of future skill.")
        + data_table("staking-ledger", "Separate staking / market-economics ledger", [
            ("Strategy", "strategy"), ("Market", "market"),
            ("Authorized quote snapshots", "quote_count_display"), ("ROI", "roi_display"),
            ("CLV", "clv_display"), ("Net return lower 95%", "return_display"),
            ("Cash reward", "cash_reward"), ("State", "stake_status_display"),
            ("Official price / rights sources", "__sources"),
        ], staking_rows, note="Blank ROI/CLV/return values mean not measurable. They are not zero. Stake outcomes do not change signal ranks; a profitable staking run cannot repair a failed signal gate.")
        + '<p><a href="../../nfl-results-skill.html">Open the full 30-variant skill-vs-luck analysis</a> · '
        '<a href="../../nfl-results-leaderboard.html">Open the results leaderboard and reward withholding</a></p>'
    )

    policy_rows = [
        {"id": "DG01", "gate": "Rights and authorized source", "trigger": "NFL-data-use permission or a registered licensed quote source is missing or withdrawn", "action": "Immediate return to paper; stop market output", "source_ids": ["X87-NFL-TERMS-1414", "X87-NFL-ODDS-1414"]},
        {"id": "DG02", "gate": "Feed integrity / freshness", "trigger": "Quote, source, capture time, frozen model/data hash or reproducibility check is missing, stale or mismatched", "action": "Immediate return to paper; quarantine affected rows", "source_ids": ["X87-NFL-ODDS-1414", "REPO"]},
        {"id": "DG03", "gate": "Settlement contract", "trigger": "Market, operator, line, settlement or closing contract differs or is unknown", "action": "Immediate return to paper; do not grade ROI/CLV", "source_ids": ["X87-NFL-TERMS-1414", "REPO"]},
        {"id": "DG04", "gate": "Evidence maturity", "trigger": f'Fewer than {demotion_data["policy"]["minimum_settled_selections"]} settled selections, {demotion_data["policy"]["minimum_distinct_games"]} distinct games, {demotion_data["policy"]["minimum_distinct_dates"]} dates, {demotion_data["policy"]["minimum_shadow_games"]} prospective shadow games or {demotion_data["policy"]["minimum_shadow_calendar_days"]} shadow days', "action": "Remain/demote to paper until every frozen sample floor is met", "source_ids": ["REPO", "X29-NFL-SCHEDULE"]},
        {"id": "DG05", "gate": "Signal skill (independent of stakes)", "trigger": f'95% lower bound on skill vs the frozen baseline is not >0, or familywise-adjusted p exceeds {demotion_data["policy"]["familywise_alpha"]}', "action": "Return to paper; realized stake ROI cannot override this gate", "source_ids": ["REPO", "X29-NFL-SCHEDULE"]},
        {"id": "DG06", "gate": "Economics (separate from signal)", "trigger": "Net-return lower 95% bound after costs is blank or not >0", "action": "Return to paper; no live economic qualification", "source_ids": ["X87-NFL-ODDS-1414", "X87-NFL-TERMS-1414", "REPO"]},
        {"id": "DG07", "gate": "Exposure controls", "trigger": f'Exceeds {demotion_data["policy"]["maximum_units_per_game"]} unit/game, {demotion_data["policy"]["maximum_units_per_day"]} units/day or {demotion_data["policy"]["maximum_drawdown_units"]} units drawdown; missing telemetry fails closed', "action": "Immediate return to paper and risk review", "source_ids": ["REPO"]},
        {"id": "DG08", "gate": "Frozen window and multiplicity registry", "trigger": "The evaluation window is not frozen or every attempted variant is not registered before familywise correction", "action": "No promotion; restart prospectively with the complete attempt registry", "source_ids": ["REPO", "X29-NFL-SCHEDULE"]},
    ]
    current_state = [
        {"id": "STATE01", "item": "Repository mode", "state": demotion_data["actual_project_state"]["mode"], "interpretation": "Paper/research-only protocol; this is repository policy, not an external account check.", "source_ids": ["REPO", "X87-NFL-TERMS-1414"]},
        {"id": "STATE02", "item": "Live strategy record", "state": demotion_data["actual_project_state"]["live_strategy_records"], "interpretation": "No live strategy record or live execution was inspected; demotion has not actually run.", "source_ids": ["REPO"]},
        {"id": "STATE03", "item": "Counterfactual live evaluation", "state": demotion_data["counterfactual_live_check"]["decision"], "interpretation": "Under current known missing rights/price/evidence, a strategy marked live would be sent back to paper.", "source_ids": ["X87-NFL-TERMS-1414", "X87-NFL-ODDS-1414", "REPO"]},
    ]
    page_demotion_body = (
        '<div class="notice"><strong>The demotion rule is active as policy, not as a live betting control.</strong>'
        '<p>No live account or live strategy exists in the project record. The code exposes a tested deterministic transition function; the current assessment is counterfactual and does not claim an actual wager was stopped.</p></div>'
        + data_table("demotion-policy", "Predeclared fail-closed demotion conditions", [
            ("ID", "id"), ("Gate", "gate"), ("Demotion trigger", "trigger"),
            ("Action", "action"), ("Sources / project policy", "__sources"),
        ], policy_rows, note="Thresholds are OWN7 project choices copied from the NFL protocol. They are not official NFL standards or legal advice.")
        + data_table("demotion-state", "Current repository state", [
            ("Item", "item"), ("Evidence", "state"), ("Interpretation", "interpretation"),
            ("Sources", "__sources"),
        ], current_state)
        + '<details><summary>How signal, economics and staking are kept apart</summary><ul>'
        '<li>Signal gate: minimum forward sample, lower 95% skill bound over the frozen baseline, and familywise multiplicity control.</li>'
        '<li>Economics gate: independently requires a positive lower 95% net-return bound after actual costs and a matching settlement contract.</li>'
        '<li>Risk gate: checks per-game/day units and drawdown separately. Stake ROI is not used to rank or rescue the signal.</li>'
        '<li>Any missing field is a failure for a live strategy; the default state is paper.</li></ul></details>'
    )

    flags_rows = []
    for row in flags_data["flags"]:
        flags_rows.append({
            **row,
            "value_display": row["unverified_value"],
            "status_display": row["status"],
        })
    page_flags_body = (
        '<div class="notice"><strong>Flagged for Review — gaps are visible and do not block publishing this research-only site.</strong>'
        '<p>Each row links to the official source that supports the narrow finding. An official page that returned 404 does not prove there is no separate licensed provider.</p></div>'
        + data_table("market-flags", "Price, rights and operational limitations", [
            ("ID / item", "item"), ("Finding", "finding"), ("Unverified value", "value_display"),
            ("State", "status_display"), ("Decision impact", "impact"), ("Official sources", "__sources"),
        ], flags_rows, note="The blank unverified-value cells are intentional. See the Questions and Suggestions pages for exact discovery actions and acceptance tests.")
        + '<p><a href="../../nfl-results-decisions.html">Questions &amp; missing information</a> · '
        '<a href="../../nfl-results-suggestions.html">Review the prioritized suggestions</a> · '
        '<a href="../../nfl-skill-cfdd/site/suggestions.html">Review Adopt / Defer / Reject choices</a></p>'
    )

    source_ids = ["X87-NFL-ODDS-1414", "X87-NFL-TERMS-1414", "NFL-SCHED-W10", "X87-NFL-W10-1414", "NFL-STANDINGS", "PYTH-NFL", "X29-NFL-SCHEDULE", "REPO"]
    source_rows = []
    registry = source_registry()
    for source_id in source_ids:
        source = registry[source_id]
        source_rows.append({
            "id": source_id,
            "publisher": source["publisher"],
            "title": source["title"],
            "checked_on": source["checked_on"],
            "scope": source["scope"],
            "access": source["access"],
            "status": source["status"],
            "source_url": source["url"],
            "source_ids": [source_id],
        })
    page_sources_body = (
        '<div class="notice good"><strong>Source links are review paths, not a blanket fact-check.</strong>'
        '<p>Official NFL results and schedule rows support the game records; the Pythagorean formula is a separate method reference. NFL terms and the checked odds route define the narrow price/rights boundary. No licensed sportsbook feed is registered or fetched.</p></div>'
        + data_table("source-register", "Registered official sources, method reference and exact scope", [
            ("Source ID", "id"), ("Publisher", "publisher"), ("Page", "title"),
            ("Checked", "checked_on"), ("Scope", "scope"), ("Access / status", "access"),
            ("Status", "status"), ("Official link", "__sources"),
        ], source_rows, note="The current terms page visibly states §1.3 in the first retrieved chunk. The route check is limited to /odds/. The 136-row historic result evidence remains published on the Official game results page.")
        + '<p><a href="../../nfl-results-games.html">Open the 136 source-linked official results</a> · '
        '<a href="../../nfl-results-correlation.html">Open published correlation n and methods</a></p>'
    )

    bodies = {
        "index.html": page_index_body,
        "prices.html": page_prices_body,
        "snapshots.html": page_snapshots_body,
        "leaderboard.html": page_leaderboard_body,
        "demotion.html": page_demotion_body,
        "flagged.html": page_flags_body,
        "sources.html": page_sources_body,
    }
    descriptions = {
        "index.html": "Executive decision summary: NFL model markets, verified results, source limits and safety gates.",
        "prices.html": "Separate model fair values, market values and differences for every model-originated market.",
        "snapshots.html": "Opening and closing snapshot slots for every originated market, with unknown quotes kept blank.",
        "leaderboard.html": "Separate signal evidence from staking outcomes, ROI and closing-line value.",
        "demotion.html": "Fail-closed project policy for returning a live strategy to paper.",
        "flagged.html": "Officially linked NFL price, rights and timing gaps for review.",
        "sources.html": "Official NFL sources, scope, access class and verification boundaries.",
    }
    pages = {}
    for slug, label in PAGES:
        pages[SITE / slug] = page(slug, label, descriptions[slug], bodies[slug])
    pages[SITE / "style.css"] = CSS + "\n"
    pages[SITE / "manifest.json"] = json.dumps({"pages": [name for name, _ in PAGES], "checked_on": "2026-11-14"}, indent=2) + "\n"
    return pages


def generated_files() -> dict[Path, str]:
    store_data = price_store.build_store()
    analysis = load_json("nfl-results/analysis.json")
    signal_data = build_signal_staking(analysis, store_data)
    demotion_data = demotion.current_status(store_data)
    flags_data = build_flags()
    files = {}
    files.update(price_store.generated_files())
    files[DATA / "signal-staking-2026-11-14.json"] = json.dumps(signal_data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    files[DATA / "demotion-status-2026-11-14.json"] = json.dumps(demotion_data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    files[DATA / "flags-2026-11-14.json"] = json.dumps(flags_data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    files.update(build_pages(store_data, signal_data, demotion_data, flags_data))
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail unless every generated artifact is byte-identical")
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
        raise SystemExit("stale NFL market-control artifacts: " + ", ".join(changed))
    store_data = price_store.build_store()
    signal_data = build_signal_staking(load_json("nfl-results/analysis.json"), store_data)
    print(f"OK: {store_data['counts']['markets_originated']} market rows, "
          f"{store_data['counts']['opening_closing_slots']} snapshot slots, "
          f"{store_data['counts']['quotes_collected']} quotes, "
          f"{signal_data['signal_policy']['strategies_tested']} signal variants; all missing values blank.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
