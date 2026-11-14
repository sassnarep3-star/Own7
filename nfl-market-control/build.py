#!/usr/bin/env python3
"""Build the deterministic NFL price-snapshot and release-control desk."""
from __future__ import annotations

import csv
import hashlib
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import engine  # noqa: E402

OUT = HERE / "site"
DATA_OUT = HERE / "data"


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def load_sources() -> dict[str, dict]:
    return engine.sources_by_id()


def fmt(value, places: int = 4):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        text = f"{value:.{places}f}".rstrip("0").rstrip(".")
        return text or "0"
    return value


def percent(value, places: int = 1):
    return None if value is None else f"{value * 100:.{places}f}%"


def pvalue(value):
    return None if value is None else f"{value:.4f}"


def source_links(row: dict, sources: dict[str, dict]) -> str:
    links = []
    direct = row.get("event_source_url")
    if direct:
        links.append(f'<a href="{esc(direct)}" target="_blank" rel="noopener noreferrer">Official game ↗</a>')
    else:
        direct = row.get("source_url")
        if direct:
            links.append(f'<a href="{esc(direct)}" target="_blank" rel="noopener noreferrer">Official source ↗</a>')
    seen = {direct} if direct else set()
    for source_id in row.get("source_ids", []):
        source = sources[source_id]
        if source["url"] in seen:
            continue
        seen.add(source["url"])
        links.append(
            f'<a href="{esc(source["url"])}" title="{esc(source["title"])}" '
            f'target="_blank" rel="noopener noreferrer">{esc(source_id)} ↗</a>'
        )
    return '<td class="source-links">' + "".join(links) + "</td>"


def empty_reason(row: dict, key: str) -> str:
    if key == "fair_line" and row.get("market_key") == "moneyline":
        return "Not applicable: a moneyline has no point line."
    if key == "fair_probability" and row.get("market_key") != "moneyline":
        return "Not collected: no calibrated spread-cover or total probability is present."
    if key in {"fair_american_odds"} and row.get("market_key") != "moneyline":
        return "Not collected: no fair spread/total price is present."
    if key == "operator" and row.get("operator") is None:
        return "Unverified: no quote operator is recorded."
    if key.startswith("opening") or key.startswith("closing"):
        return "Unverified: no authorized, source-checked quote is stored for this slot."
    return "Blank: not supplied or not applicable; do not infer a value."


def cell(value, row: dict, key: str) -> str:
    if value is None or value == "":
        return f'<td class="blank" data-empty="true" title="{esc(empty_reason(row, key))}" aria-label="Blank; unverified or not applicable"></td>'
    raw = value
    if isinstance(value, float):
        value = fmt(value)
    if isinstance(value, int) or isinstance(value, float):
        return f'<td class="numeric" data-value="{esc(raw)}">{esc(value)}</td>'
    return f'<td>{esc(value)}</td>'


def table(table_id: str, title: str, columns: list[tuple[str, str]], rows: list[dict], sources: dict[str, dict]) -> str:
    headers = "".join(
        f'<th scope="col" aria-sort="none"><button type="button" data-sort="{i}">{esc(label)} <span aria-hidden="true">↕</span></button></th>'
        for i, (label, _key) in enumerate(columns)
    )
    body = []
    for row in rows:
        ids = " ".join(row.get("source_ids", []))
        cells = "".join(cell(row.get(key), row, key) for _label, key in columns)
        status = esc(row.get("status", row.get("signal_status", row.get("staking_status", ""))))
        body.append(
            f'<tr data-row-id="{esc(row.get("id", ""))}" data-source-ids="{esc(ids)}" data-status="{status}">'
            + cells + source_links(row, sources) + "</tr>"
        )
    return f'''<div class="table-card" data-table-card="{esc(table_id)}">
      <div class="table-toolbar"><span class="row-count" data-count-for="{esc(table_id)}" aria-live="polite">{len(rows)} rows</span>
        <label class="search"><span class="sr-only">Filter {esc(title)}</span><input type="search" data-search-for="{esc(table_id)}" placeholder="Filter rows…" autocomplete="off"></label>
        <button class="export" type="button" data-export="{esc(table_id)}">Export visible CSV</button>
      </div>
      <div class="table-scroll" role="region" aria-label="{esc(title)} table; scroll horizontally for more columns" tabindex="0">
        <table id="{esc(table_id)}"><caption class="sr-only">{esc(title)}; blank cells are unknown or not applicable, not zero. Every row links to a registered source.</caption>
          <thead><tr>{headers}<th scope="col">Sources</th></tr></thead><tbody>{''.join(body)}</tbody>
        </table>
      </div><p class="empty-state" data-empty-for="{esc(table_id)}" hidden>No matching rows. Clear the filter to see the full list.</p>
    </div>'''


def source_link(source_id: str, sources: dict[str, dict], label: str | None = None) -> str:
    source = sources[source_id]
    return (
        f'<a href="{esc(source["url"])}" target="_blank" rel="noopener noreferrer">'
        f'{esc(label or source["title"])} ↗</a>'
    )


def base_page(slug: str, title: str, subtitle: str, content: str) -> str:
    nav = [
        ("index.html", "Executive summary"),
        ("prices.html", "Price snapshots"),
        ("leaderboard.html", "Signal vs staking"),
        ("sequence.html", "Origination order"),
        ("demotion.html", "Live → paper gate"),
        ("questions.html", "Questions & answers"),
        ("suggestions.html", "Suggestions to review"),
        ("flagged.html", "Flagged for review"),
        ("sources.html", "Sources & method"),
    ]
    nav_parts = []
    for href, label in nav:
        current = ' aria-current="page"' if slug == href else ""
        nav_parts.append(f'<a href="{href}"{current}>{esc(label)}</a>')
    nav_html = "".join(nav_parts)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="NFL price snapshot store, market sequencing, separate signal and staking boards, and a fail-closed demotion gate.">
<meta name="referrer" content="strict-origin-when-cross-origin"><title>{esc(title)} · OWN7 NFL</title>
<link rel="stylesheet" href="style.css"><script src="app.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="site-header"><a class="brand" href="index.html">OWN7 <span>NFL MARKET CONTROL</span></a>
<nav aria-label="NFL market controls">{nav_html}</nav><a class="back" href="../../index.html">Main research site ↗</a></header>
<main id="main"><div class="page-heading"><p class="eyebrow">NFL / PRICE, SIGNAL &amp; RISK CONTROLS</p><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>
{content}
<footer><p>Frozen research artifacts; not a live odds feed, betting product, advice or endorsement.</p>
<p>{source_link('NFL-TERMS', load_sources(), 'NFL.com terms')} · <a href="../../nfl-results.html">Verified results lab ↗</a> · <a href="../../nfl-skill-cfdd/site/depletion.html">Depth / replacement desk ↗</a></p>
</footer></main></body></html>'''


def metric(label: str, value, note: str) -> str:
    return f'<div class="metric"><span>{esc(label)}</span><strong>{esc(value)}</strong><small>{esc(note)}</small></div>'


def notice(title: str, text: str, kind: str = "info") -> str:
    return f'<aside class="notice {esc(kind)}"><strong>{esc(title)}</strong><p>{esc(text)}</p></aside>'


def section(title: str, body: str, kicker: str = "") -> str:
    prefix = f'<p class="kicker">{esc(kicker)}</p>' if kicker else ""
    return f'<section class="section">{prefix}<h2>{esc(title)}</h2>{body}</section>'


def market_rows_for_page(rows: list[dict]) -> list[dict]:
    output = []
    for row in rows:
        output.append({
            **row,
            "fair_value": row["fair_line"] if row["fair_line"] is not None else row["fair_probability"],
            "opening_difference": row["opening_line_difference"] if row["market_key"] != "moneyline" else row["opening_probability_difference"],
            "closing_difference": row["closing_line_difference"] if row["market_key"] != "moneyline" else row["closing_probability_difference"],
            "units_label": "points" if row["market_key"] != "moneyline" else "raw probability",
            "fair_price_label": row["fair_american_odds"],
            "opening_market_value_label": row["opening_market_value"],
            "closing_market_value_label": row["closing_market_value"],
        })
    return output


def index_content(data: dict, sources: dict[str, dict]) -> str:
    s = data["summary"]
    body = notice(
        "Decision: keep every strategy in research/paper mode.",
        "The existing NFL results feed is reproducible, but a signal is not a profitable wager. The quote store has no authorized market observations, so opening/closing prices, market differences, ROI, CLV, stakes and rewards remain blank.",
    )
    body += '<div class="metrics">' + "".join([
        metric("Week 10 model games", s["originated_games"], "Frozen snapshot; not live"),
        metric("Expected quote slots", s["expected_open_close_slots"], "Open + close × 3 markets × 2 sides"),
        metric("Captured quote records", s["captured_quote_records"], "No authorized observations"),
        metric("Verified result rows", s["result_games"], "Weeks 1–9; reconciliation reruns"),
    ]) + '</div>'
    spread = f'{s["spread_wins"]}–{s["spread_losses"]} ({percent(s["spread_hit_rate"])})'
    total = f'{s["total_wins"]}–{s["total_losses"]} ({percent(s["total_hit_rate"])})'
    body += section("Executive summary", f'''<div class="callout-grid">
      <article class="callout"><h3>What is known</h3><p>{esc(s['results_check'])}. The existing skill lab tests 30 variants; one is provisional and none is qualified.</p>
        <p>Spread board: <strong>{esc(spread)}</strong>. Total board: <strong>{esc(total)}</strong>. These are signal statistics, not returns.</p>
        <p>Same-game spread/total dependence was measured separately in the results lab (phi {s['correlation_phi']:+.4f}, p={s['correlation_p']:.4f}, n={s['correlation_n']}); player-prop dependence remains unmeasured.</p></article>
      <article class="callout warning"><h3>What is not known</h3><p>No authorized opening/closing quote, operator, odds, stake, ROI, CLV, cash reward or live strategy exists in this repository.</p>
        <p>The model's fair values are not market prices. The total model has no calibrated over/under probability; the moneyline fair price is not a tested executable edge.</p></article>
    </div>''', "READ FIRST")
    body += section("Release sequence", '<ol class="steps"><li><strong>Side · point spread</strong><span>First research priority. The historical directional signal is provisional and stays paper-only.</span></li><li><strong>Total</strong><span>Second. The existing score is 60–60; do not infer a fair over/under price.</span></li><li><strong>Moneyline</strong><span>Third. Model fair win probabilities exist for the frozen snapshot; no market comparison exists.</span></li></ol><p class="links"><a class="button" href="sequence.html">Review the three stages →</a> <a class="button" href="prices.html">Inspect every expected quote slot →</a></p>', "ORIGINATION ORDER")
    body += section("Decision gates", '<div class="callout-grid"><article class="callout"><h3>Signal plane</h3><p>Score prediction quality on a frozen, leakage-free test family with uncertainty, multiplicity control and stability. Do not use bankroll growth to promote a signal.</p><a href="leaderboard.html">Open signal board →</a></article><article class="callout"><h3>Staking plane</h3><p>Requires a rights-cleared, timestamped price, settlement mapping and a pre-registered stake policy. Every economics field is blank today.</p><a href="leaderboard.html#staking">Open staking ledger →</a></article></div><p class="links"><a class="button" href="demotion.html">Read the live-to-paper gate →</a> <a class="button" href="questions.html">Open questions →</a> <a class="button" href="suggestions.html">Suggestions for review →</a> <a class="button" href="flagged.html">Flagged items →</a></p>', "CONTROL MODEL")
    manual_links = (
        '<ul class="source-list"><li>' + source_link("NFL-SCHED-W10", sources, "NFL Week 10 schedule") + ' — fixture identity for the frozen line board.</li>'
        + '<li>' + source_link("X29-NFL-SCHEDULE", sources, "NFL by-week schedules") + ' — published final scores used by the existing results feed.</li>'
        + '<li>' + source_link("NFL-STANDINGS", sources, "NFL standings") + ' — reconciliation and frozen model inputs.</li>'
        + '<li>' + source_link("NFL-TERMS", sources, "NFL.com Terms") + ' — review before any systematic collection or publication.</li></ul>'
        + "<p class=\"muted\">This session re-ran the repository's local receipt and arithmetic checks; it did not make a fresh external NFL.com fetch. Links are provided for manual review.</p>"
    )
    body += section("Official manual-review links", manual_links, "SOURCES")
    return body


def prices_content(data: dict, sources: dict[str, dict]) -> str:
    rows = market_rows_for_page(data["markets"])
    body = notice(
        "Blank is unknown — not zero, not a market consensus, and not a price.",
        f"This page shows {data['summary']['market_selection_rows']} expected game/market/selection rows and {data['summary']['expected_open_close_slots']} opening/closing slots. The append-only quote store currently contains {data['summary']['captured_quote_records']} authorized quote records.",
        "warning",
    )
    body += '<p class="muted">Model fair line/probability, opening market line/implied probability, opening difference, closing market line/implied probability and closing difference are separate columns. Spread and total values are points; moneyline market probabilities are raw implied probabilities and include vig. Moneyline American odds appear in separate price columns. No no-vig probability, ROI or CLV is inferred.</p>'
    body += table("snapshot-matrix", "Expected opening and closing quote slots", [
        ("Game", "game"), ("Order", "market_order"), ("Market", "market"),
        ("Selection", "selection"), ("Operator", "operator"), ("Value units", "units_label"),
        ("Model fair line / probability", "fair_value"), ("Fair ML odds", "fair_price_label"),
        ("Opening market line / implied probability", "opening_market_value_label"), ("Opening difference", "opening_difference"),
        ("Opening American odds", "opening_american_odds"), ("Opening timestamp UTC", "opening_timestamp_utc"),
        ("Closing market line / implied probability", "closing_market_value_label"), ("Closing difference", "closing_difference"),
        ("Closing American odds", "closing_american_odds"), ("Closing timestamp UTC", "closing_timestamp_utc"),
        ("Snapshot status", "status"),
    ], rows, sources)
    body += section("Store contract", '<p>The machine-readable append-only store is <code>data/quote_snapshots.jsonl</code>. The 84-row matrix represents every originated game/market/selection; each row expects an opening and a closing observation. It is not evidence that an operator offered a line. Future records are rejected unless their market/selection is valid, source ID is registered, HTTPS host matches that source, timestamp includes a timezone, rights are documented as authorized, source status is verified, and an evidence SHA-256 is present.</p><p>Opening and closing are stored per operator, not averaged across books. A duplicated slot or a closing timestamp earlier than opening is rejected. The exact timestamp cutoff, settlement/void rules, feed provider and use-rights still require a documented decision before any quote can be ingested.</p><p class="links"><a class="button" href="../data/price-slot-matrix.csv">Download expected slot matrix CSV</a> <a class="button" href="../data/quote_snapshots.jsonl">View quote store (JSONL)</a></p>', "DATA CONTRACT")
    return body


def leaderboard_content(data: dict, sources: dict[str, dict]) -> str:
    signals = []
    for row in data["signals"]:
        signals.append({
            **row,
            "hit_rate_display": percent(row["hit_rate"]),
            "first_half_hit_rate_display": percent(row["first_half_hit_rate"]),
            "second_half_hit_rate_display": percent(row["second_half_hit_rate"]),
            "p_display": pvalue(row["chance_p"]),
            "q_display": pvalue(row["bh_q"]),
            "interval": (f"{percent(row['ci_low'])} – {percent(row['ci_high'])}" if row["ci_low"] is not None else None),
        })
    body = notice(
        "One provisional signal is not one qualified strategy.",
        "The signal table reports forecast evidence only. Its graded-bet count excludes pushes; the record shows wins–losses–pushes and hit rate uses decisive bets. The staking table is a separate economics ledger; no odds, stake, ROI, CLV or reward is populated. A lucky staking run cannot change the signal status.",
    )
    body += section("Signal leaderboard · forecast evidence only", table("signal-board", "Signal leaderboard", [
        ("Strategy", "strategy"), ("Market", "market"), ("Variant", "variant"),
        ("Decisive bets (no pushes)", "bets"), ("Record (W–L–P)", "record"), ("Hit rate", "hit_rate_display"),
        ("First-half hit rate", "first_half_hit_rate_display"), ("Second-half hit rate", "second_half_hit_rate_display"),
        ("Chance p", "p_display"), ("BH q", "q_display"), ("95% interval", "interval"),
        ("Signal state", "signal_status"),
    ], signals, sources), "SKILL / SIGNAL")
    body += section("Staking leaderboard · economics only", table("staking-board", "Staking leaderboard", [
        ("Strategy", "strategy"), ("Market", "market"), ("Opening price", "opening_price"),
        ("Closing price", "closing_price"), ("Stake", "stake"), ("Net ROI", "net_roi"),
        ("CLV", "clv"), ("Reward", "reward"), ("Economics state", "staking_status"),
    ], data["staking"], sources), "PRICES / STAKING")
    body += '<p id="staking" class="muted">Every blank economics cell is unverified/withheld, never a zero. The result feed contains final scores, not the operator quote and settlement terms needed to compute return.</p>'
    body += section("What the board does not mean", '<ul><li>A hit rate is not profit: prices, vig, settlement, timing and stake determine net return.</li><li>Signal selection must be fixed before the test. All 30 tested variants remain visible so a top row is not cherry-picked.</li><li>Only the existing result-analysis status is reused: one row is provisional, none qualified. This page introduces no new ranking or reward.</li><li>Parlay and player-prop combinations require joint outcome data; the correlation page publishes n for the measured spread/total pair and leaves missing prop values blank.</li></ul><p class="links"><a class="button" href="../../nfl-results-skill.html">Review skill tests and nulls →</a> <a class="button" href="../../nfl-results-correlation.html">Review correlation with n →</a></p>', "INTERPRETATION")
    return body


def sequence_content(data: dict, sources: dict[str, dict]) -> str:
    body = notice("Sequence is a research priority, not permission to publish a live price.",
                  "The board is deliberately ordered side/spread first, total second and moneyline third. All three remain paper-only until source, validation and rights gates pass.")
    body += table("market-sequence", "Ordered origination stages", [
        ("Priority", "priority"), ("Market", "market"), ("Definition", "definition"),
        ("Observed evidence", "evidence"), ("Current state", "state"), ("Next gate", "next_gate"),
    ], data["sequence"], sources)
    body += section("Fair line, market line and difference", '<p>For spread and total, the comparison is <strong>model fair point line − market point line</strong>, shown separately for opening and closing. For moneyline, the model fair probability is compared with the raw probability implied by a captured American price; it includes vig and is not labelled an edge. If either input is absent, the difference is blank.</p><p>The Week 10 model values are derived from the checked standings and the project model. The official NFL schedule verifies the event identity, not a market quote or the model assumptions. See the source-linked line board and price-slot matrix.</p><p class="links"><a class="button" href="../../nfl-lines.html">Existing model-only Week 10 lines →</a> <a class="button" href="prices.html">Full opening/closing matrix →</a></p>', "PRESENTATION RULE")
    return body


def demotion_content(data: dict, sources: dict[str, dict]) -> str:
    policy = data["policy"]["demotion_gate"]
    body = notice("Gate defined; no live strategy exists to demote today.",
                  "This control is an inactive project policy. It makes no claim that a strategy is live, profitable or currently staked.", "warning")
    body += '<div class="state-flow"><span>paper</span><b aria-hidden="true">→</b><span>live only after all gates</span><b aria-hidden="true">→</b><span class="paper">paper on any demotion trigger</span></div>'
    body += section("Immediate fail-safe triggers", '<ul class="trigger-list">' + "".join(
        f'<li><code>{esc(trigger)}</code><span>Any occurrence returns a live strategy to paper immediately; the strategy cannot auto-promote.</span></li>'
        for trigger in policy["immediate_triggers"]
    ) + '</ul>', "HARD STOP")
    body += section("Statistical performance trigger", f'''<div class="callout"><h3>Conservative non-positive lower bound</h3>
      <p>After <strong>{policy['minimum_settled_bets']} settled bets</strong> in the locked evaluation cohort, demote from live to paper when the pre-registered one-sided <strong>{int(policy['confidence_level']*100)}% lower confidence bound for net ROI is at or below {policy['roi_lower_bound_trigger']:.0%}</strong>.</p>
      <p>{esc(policy['performance_rule'])}</p><p class="muted">The 100-bet floor is an explicit project-policy choice carried from the existing results gate, not an NFL rule or universal power claim. The gate remains inactive until the ROI method accounts for dependence, the full trial family, authorized prices and complete settlement.</p>
    </div>''', "PERFORMANCE STOP")
    body += section("Re-entry rule", '<ol><li>Demotion always returns the strategy to paper; it never deletes losing or missing rows.</li><li>Fix the triggering integrity, rights, settlement, risk or performance issue and freeze a new model/data version.</li><li>Repeat every relevant provenance, temporal, sample, calibration, multiplicity, price, rights and risk gate on a new prospective shadow record.</li><li>Require a human review decision in the decision register before any future live designation. There is no automatic promotion in this repository.</li></ol>', "NO AUTOMATIC RE-PROMOTION")
    body += '<p class="source-note">Design is owned by this project; NFL.com does not prescribe these thresholds. Official data/rights context: ' + source_link("NFL-TERMS", sources, "NFL.com terms") + ' and ' + source_link("X29-NFL-SCHEDULE", sources, "official results schedule") + '.</p>'
    return body


def questions_content(data: dict, sources: dict[str, dict]) -> str:
    rows = [{**row, "status": row["status"]} for row in data["register"]["questions"]]
    body = notice("Questions with no answer stay open.",
                  "Known values below are limited to the saved, receipt-checked artifacts. A blank or missing field is not filled by assumption; every question names what is missing and how it can be discovered.")
    body += table("question-register", "Questions, known evidence and next discovery step", [
        ("Question", "question"), ("Known / verified in repository", "evidence"),
        ("Missing information", "missing"), ("Discovery / closure test", "next_step"), ("State", "status"),
    ], rows, sources)
    body += '<p class="muted">A value that cannot be confirmed remains blank on the price and staking pages. Source links identify the official context reviewed; project artifacts are separately listed on the source page.</p>'
    return body


def suggestions_content(data: dict, sources: dict[str, dict]) -> str:
    body = notice("Suggestions are options to review, not silently adopted changes.",
                  "No suggestion has been selected. Each proposal states the evidence, cost, risk and a test that could accept or reject the path.")
    body += table("suggestion-register", "Reviewable suggestions", [
        ("Rank", "rank"), ("Suggestion", "title"), ("Evidence", "evidence"),
        ("Cost", "cost"), ("Risk", "risk"), ("Acceptance test", "acceptance_test"),
        ("Review state", "review_state"),
    ], data["register"]["suggestions"], sources)
    body += '<p class="links"><a class="button" href="../../nfl-suggestions.html">Open the main NFL suggestion desk →</a> <a class="button" href="../../nfl-skill-cfdd/site/suggestions.html">Review skill / depth proposals →</a></p>'
    return body


def flagged_content(data: dict, sources: dict[str, dict]) -> str:
    body = notice("Flags do not block publication; they block unsupported claims.",
                  "All unverified-value fields remain blank. Items are listed so an independent reviewer can inspect the official source and decide what information would close the gap.", "warning")
    body += table("flag-register", "Flagged items", [
        ("Item", "item"), ("Evidence found", "evidence"), ("Unverified value", "unverified_value"),
        ("Decision impact", "impact"), ("Status", "status"),
    ], data["register"]["flags"], sources)
    return body


def sources_content(sources: dict[str, dict]) -> str:
    refs = ["NFL-SCHED-W10", "X29-NFL-SCHEDULE", "NFL-STANDINGS", "NFL-TERMS", "REPO"]
    cards = []
    for source_id in refs:
        source = sources[source_id]
        cards.append(f'''<li><strong>{esc(source_id)} · {esc(source['title'])}</strong>
          <span>{esc(source.get('scope', ''))}</span><a href="{esc(source['url'])}" target="_blank" rel="noopener noreferrer">{esc(source['url'])} ↗</a>
          <small>Checked in inherited source record: {esc(source.get('checked_on', ''))}; access: {esc(source.get('access', ''))}</small></li>''')
    commands = """python nfl-market-control/build.py --check
python -m unittest discover -s nfl-market-control/tests -v
python nfl-results/extract.py
python nfl-results/engine.py --check
python -m nfl_origination run --check
python scripts/build_site.py
python scripts/check_site.py"""
    return (
        '<ul class="source-cards">' + "".join(cards)
        + '</ul><p class="muted">Local checks in this session re-parsed saved evidence and regenerated derived artifacts; they do not independently attest that an external page is reachable today. No external NFL fetch was made during this session. The official links above are provided for manual review.</p>'
        + '<h2>Reproduce the local checks</h2><pre><code>' + esc(commands) + '</code></pre>'
    )


def csv_text(rows: list[dict], fields: list[str]) -> str:
    import io
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        record = {}
        for field in fields:
            value = row.get(field)
            record[field] = "" if value is None else value
        writer.writerow(record)
    return handle.getvalue()


def expected_outputs() -> dict[Path, bytes]:
    sources = load_sources()
    data = engine.build_data()
    sequence = data["sequence"]
    raw_market_rows = market_rows_for_page(data["markets"])
    pages = {
        "index.html": ("Executive summary", "The current decision, evidence, unknowns and release order.", index_content(data, sources)),
        "prices.html": ("Price snapshots", "Append-only opening and closing quote slots for every originated market; unverified market values stay blank.", prices_content(data, sources)),
        "leaderboard.html": ("Signal vs staking", "Separate skill evidence from price, staking, ROI, CLV and rewards.", leaderboard_content(data, sources)),
        "sequence.html": ("Origination order", "Side / point spread first, total second, moneyline third.", sequence_content(data, sources)),
        "demotion.html": ("Live-to-paper gate", "A fail-closed demotion control for any future strategy; currently inactive.", demotion_content(data, sources)),
        "questions.html": ("Questions & answers", "Known, missing and how to discover the information that can close each gap.", questions_content(data, sources)),
        "suggestions.html": ("Suggestions to review", "Ranked options with evidence, cost, risk and acceptance tests; nothing is selected.", suggestions_content(data, sources)),
        "flagged.html": ("Flagged for review", "Unverified prices, scope limits and project-policy choices, with official context links.", flagged_content(data, sources)),
        "sources.html": ("Sources & method", "Official NFL links and project artifacts used for this control desk.", sources_content(sources)),
    }
    output: dict[Path, bytes] = {}
    for slug, (title, subtitle, content) in pages.items():
        rendered = base_page(slug, title, subtitle, content)
        output[OUT / slug] = (rendered + "\n").encode("utf-8")

    market_fields = [
        "id", "game_id", "game", "kickoff", "market_order", "market", "market_key", "selection", "operator", "units",
        "model_fair_line", "model_fair_probability", "fair_american_odds",
        "opening_market_line", "opening_implied_probability", "opening_american_odds",
        "opening_line_difference", "opening_probability_difference", "opening_timestamp_utc",
        "closing_market_line", "closing_implied_probability", "closing_american_odds",
        "closing_line_difference", "closing_probability_difference", "closing_timestamp_utc",
        "status", "event_source_url", "source_url", "source_ids",
    ]
    matrix_csv_rows = [{
        **row,
        "model_fair_line": row["fair_line"],
        "model_fair_probability": row["fair_probability"],
        "source_ids": " ".join(row["source_ids"]),
    } for row in data["markets"]]
    output[DATA_OUT / "price-slot-matrix.csv"] = csv_text(matrix_csv_rows, market_fields).encode("utf-8")
    signal_fields = [
        "id", "strategy", "market", "variant", "bets", "wins", "losses", "pushes", "record",
        "hit_rate", "first_half_hit_rate", "second_half_hit_rate", "chance_p", "bh_q", "ci_low", "ci_high",
        "signal_status", "source_url", "source_ids",
    ]
    signals_csv = [{**row, "source_ids": " ".join(row["source_ids"])} for row in data["signals"]]
    output[DATA_OUT / "signal-leaderboard.csv"] = csv_text(signals_csv, signal_fields).encode("utf-8")
    staking_fields = [
        "id", "strategy", "market", "opening_price", "closing_price", "stake", "net_roi", "clv", "reward", "staking_status", "source_url", "source_ids",
    ]
    staking_csv = [{**row, "source_ids": " ".join(row["source_ids"])} for row in data["staking"]]
    output[DATA_OUT / "staking-ledger.csv"] = csv_text(staking_csv, staking_fields).encode("utf-8")

    manifest = {
        "schema_version": 1,
        "pages": sorted(pages),
        "data_files": ["price-slot-matrix.csv", "signal-leaderboard.csv", "staking-ledger.csv", "quote_snapshots.jsonl"],
        "input_sha256": data["input_sha256"],
        "page_sha256": {slug: hashlib.sha256(output[OUT / slug]).hexdigest() for slug in sorted(pages)},
        "summary": data["summary"],
    }
    output[OUT / "manifest.json"] = (json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    return output


def build(check: bool = False) -> None:
    outputs = expected_outputs()
    mismatches = []
    for path, content in outputs.items():
        if check:
            if not path.is_file() or path.read_bytes() != content:
                mismatches.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    if mismatches:
        raise SystemExit("STALE: regenerate NFL market-control artifacts: " + ", ".join(mismatches))
    pages = sum(path.parent == OUT and path.suffix == ".html" for path in outputs)
    if check:
        print(f"OK: {pages} market-control pages and slot/ledger exports reproduce exactly")
    else:
        print(f"Built {pages} NFL market-control pages; no market quote values inferred")


if __name__ == "__main__":
    build(check="--check" in sys.argv)
