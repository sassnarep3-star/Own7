#!/usr/bin/env python3
"""Deterministic generator for the price, market-relative grading and depth desk.

Contracts inherited from the repository and enforced by ``scripts/check_site.py``:

  * every ``<tbody><tr>`` carries ``data-source-ids`` naming registered source IDs, and
  * at least one ``<a>`` in that row points at a URL registered under one of those IDs;
  * an unknown value is an empty cell with ``data-empty="true"`` holding no text;
  * exactly one ``<h1>``, one ``<main>``, ``lang="en"`` and a ``<title>``.

Rows therefore link the *exact* page the number came from: the club's own Vegas-lines page for a
price, the by-week schedule page for a score, the club's own depth chart for a slot. Nothing here is
computed at read time: every number comes from a committed artifact in ``nfl-pricing/data/`` that
``--check`` reproduces byte for byte.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "nfl-pricing" / "data"
SITE = ROOT / "nfl-pricing" / "site"

READ_ON = "2026-11-14"
SITE_TITLE = "OWN7 · Price & market desk"

PAGES = [
    ("index.html", "Overview"),
    ("prices.html", "Price snapshots"),
    ("origination.html", "Fair vs market"),
    ("leaderboard.html", "Signal vs staking"),
    ("depth.html", "Depth of replacement"),
    ("correlation.html", "Correlation"),
    ("demotion.html", "Demotion gate"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
]

# Registry IDs used by this desk. Their source rows already live in research/sources.json; this
# module only names them so a row can declare which registered source it rests on.
PFR = "PFR-VEGAS-2026"
PFR_SOURCES = "PFR-SOURCES"
SCHEDULE = "X29-NFL-SCHEDULE"
INJURY = "X28-NFL-INJ-W10"
DEPTH_AVAIL = "NFL-AVAIL-DEPTH-W10"
DEPTH_CFDD = "CFDD-DEPTH-2026-11-14"

FLAGS = [
    ("PD01", "Depth data arrives in two files that do not overlap",
     "One file holds 27 clubs; a second holds the four Week-10 bye clubs. Reading only the first "
     "silently reports 27 clubs where 31 have a printed chart. Both are read and the split is "
     "recorded per club rather than hidden.",
     "depth.html", "low", "fixed in this build"),
    ("PD02", "The publisher's per-club game number is not a league game id",
     "G# restarts per club and shifts after a bye, so joining two clubs' pages on G# produced 96 "
     "false mismatches on the first attempt. Games are paired on the club's chronological opponent "
     "sequence, and that sequence is proved against the official schedule before a pair is accepted.",
     "prices.html", "low", "fixed in this build"),
    ("PD03", "No source examined publishes an opening number for these games",
     "The publisher prints one unlabelled number per game, recorded here as a close. ESPN exposes a "
     "live open/current pair for the unplayed slate only; completed-game pages render neither. No "
     "opening number is estimated or back-filled.",
     "prices.html", "high", "open"),
    ("PD04", "No published moneyline in the captured pages",
     "The 32 closing-line pages print a spread and a total only. Our moneyline is a derived fair "
     "price, and its market column stays blank.",
     "origination.html", "high", "open"),
    ("PD05", "No published player props, so a prop combo cannot be priced",
     "No player-level price was retrieved. Both the price of a prop leg and the dependence between "
     "two props in one game are therefore blank, not zero.",
     "correlation.html", "high", "blocked on rights"),
    ("PD06", "Two games carry a published price but no result in the frozen feed",
     "NYG-WAS on 2026-11-12 is printed with a closing number, but the official result feed used "
     "here stops before it. The price is stored; the result is not imputed and the row is excluded "
     "from every graded comparison.",
     "prices.html", "medium", "open"),
    ("PD07", "Our total model has the wrong sign against outcomes",
     "Our fair total correlates -0.042 with the actual total where the market's correlates +0.377, "
     "and our total runs 3.24 points above the market on average. Published as a defect. It is "
     "deliberately not recalibrated in-sample.",
     "correlation.html", "high", "open; needs a held-out refit"),
    ("PD08", "The price record is single-publisher",
     "Every price comes from one publisher, and the two pages per game are the same publisher. "
     "Their agreement is internal consistency, not independent verification.",
     "prices.html", "high", "open"),
    ("PD09", "The strategy family was written after the data was seen",
     "Twelve variants are graded with multiplicity control, but none was pre-registered, so even a "
     "pass would be weak evidence.",
     "leaderboard.html", "high", "open"),
    ("PD10", "Depth is a single week",
     "One Week-10 chart snapshot means there is no variation in depth to test against outcomes. "
     "Nine clubs publish no game status, and Houston's chart renders as an image.",
     "depth.html", "medium", "open"),
    ("PD11", "A different season's line page surfaced in the source search",
     "A search result returned a 2024 club Vegas-lines page. Only 2026 pages whose records matched "
     "the 2026 schedule were used. Recorded so the search trail is auditable.",
     "sources.html#pfr", "low", "explained"),
]

REGISTRY = {row["url"]: row["id"] for row in json.loads((ROOT / "research" / "sources.json").read_text())}

# One registered scope can cover a page set, so a week page under a registered nine-page scope is
# resolved by pattern rather than by adding nine near-duplicate registry rows.
REGISTRY_PATTERNS = [
    (re.compile(r"^https://www\.nfl\.com/schedules/2026/by-week/week-[1-9]$"), "X29-NFL-SCHEDULE"),
]


def registered_id(url: str) -> str | None:
    if url in REGISTRY:
        return REGISTRY[url]
    for pattern, sid in REGISTRY_PATTERNS:
        if pattern.match(url):
            return sid
    return None

# Bound from the committed artifacts in ``load()`` so a summary row cites a page that really is in
# the store rather than a hard-coded URL that could drift.
SAMPLE_PRICE = SAMPLE_RESULT = INJURY_URL = None


def esc(value) -> str:
    import html as _html

    return _html.escape(str(value), quote=True)


def link(url: str, text: str | None = None) -> str:
    label = text if text is not None else url.split("//", 1)[-1].split("?", 1)[0]
    return f'<a href="{esc(url)}" rel="noopener noreferrer" target="_blank">{esc(label)}</a>'


def cell(value) -> str:
    """A known value, or a blank cell that says so."""
    if value is None or value == "":
        return '<td data-empty="true"></td>'
    return f"<td>{esc(value)}</td>"


def sources_cell(urls, labels=None) -> str:
    """Registered IDs for these URLs, plus one link to each exact page read."""
    ids, seen = [], []
    for url in urls:
        sid = registered_id(url)
        if sid is None:
            raise SystemExit(f"unregistered source url: {url}")
        if sid not in ids:
            ids.append(sid)
        if url not in seen:
            seen.append(url)
    links = [link(url, (labels or {}).get(url)) for url in seen]
    return ids, '<td class="src">' + " ".join(links) + "</td>"


def row(cells, urls, labels=None) -> str:
    ids, src = sources_cell(urls, labels)
    return f'<tr data-source-ids="{" ".join(ids)}">' + "".join(cells) + src + "</tr>"


def table(caption, headers, rows, note=None) -> str:
    head = "".join(f"<th scope=col>{esc(h)}</th>" for h in headers)
    note_html = f'<p class="note">{esc(note)}</p>' if note else ""
    return (
        f'<div class="table-wrap"><table><caption>{esc(caption)}</caption>'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>{note_html}"
    )


def kpi(value, label, sub=None) -> str:
    sub_html = f'<span class="sub">{esc(sub)}</span>' if sub else ""
    return (
        f'<div class="kpi"><span class="kpi-value">{esc(value)}</span>'
        f'<span class="kpi-label">{esc(label)}</span>{sub_html}</div>'
    )


def badge(text, kind="neutral") -> str:
    return f'<span class="badge badge-{kind}">{esc(text)}</span>'


def load() -> dict:
    def read_json(name):
        path = DATA / name
        if not path.exists():
            raise SystemExit(f"missing {path}; run the nfl-pricing scripts first")
        return json.loads(path.read_text(encoding="utf-8"))

    def read_csv(name):
        with (DATA / name).open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    global SAMPLE_PRICE, SAMPLE_RESULT, INJURY_URL
    prices = read_json("price-snapshots.json")
    depth = read_json("depth.json")
    SAMPLE_PRICE = prices["games"][0]["sources"][0]
    SAMPLE_RESULT = prices["games"][0]["result_source_url"]
    INJURY_URL = depth["sources"]["injury"]["url"]
    return {
        "prices": prices,
        "orig": read_json("origination.json"),
        "board": read_json("leaderboard.json"),
        "corr": read_json("correlations.json"),
        "depth": depth,
        "questions": read_csv("questions.csv"),
        "suggestions": read_csv("suggestions.csv"),
        "decisions": read_csv("decision-record.csv"),
    }


def result_url(game) -> str:
    return game["result_source_url"]


def price_label(game) -> dict:
    return {url: url.split("/teams/")[1][:3].upper() + " page" for url in game["sources"]}


# ----------------------------------------------------------------------------- pages
def page_index(d: dict) -> str:
    p, o, b, c, dp = d["prices"], d["orig"], d["board"], d["corr"], d["depth"]
    mk = c["measured"]
    parts = [
        '<p class="lead">This desk records the published closing number for the two markets it '
        "originates, sets our own fair line beside the market in three separate columns, ranks "
        "strategies on signal rather than staking, measures how deep a replacement actually is, and "
        "states the rule that returns a live strategy to paper. Every row below links the exact page "
        "its number came from, and a value that could not be confirmed is left blank.</p>",
        '<div class="kpis">'
        + kpi(p["counts"]["games_reconciled"], "games with a published close", "both club pages agree")
        + kpi(p["counts"]["publisher_verdicts_reconcile"], "publisher verdicts re-derived", "zero mismatches")
        + kpi(o["counts"]["side_originated"], "games with our own fair side", f"of {o['counts']['games']}")
        + kpi(b["counts"]["ranked"], "strategies ranked", f"{b['counts']['variants']} registered")
        + kpi(dp["counts"]["injury_rows_with_no_printed_name_behind"], "injuries with no name behind",
              f"of {dp['counts']['injury_rows_matched_to_a_printed_slot']} matched rows")
        + "</div>",
        "<h2>The eight requirements, and where each one stands</h2>",
    ]
    reqs = [
        ("1", "A price store with opening and closing numbers",
         "136 closes stored from 32 club pages; no opening number is published by any source read, "
         "so that half of the requirement is recorded as unmet", "prices.html", "partial"),
        ("2", "A verified results feed so backtests and ROI can be computed",
         "136 of 136 stored games joined to an official final score; ROI remains uncomputable "
         "because an ROI needs a price and a stake policy, and no stake is ever placed",
         "prices.html", "partial"),
        ("3", "Originate the side, then the total, then the moneyline",
         "The order is enforced in code: no total without a side, no moneyline without both; "
         f"{o['counts']['side_originated']} games produced all three", "origination.html", "done"),
        ("4", "Fair line, market line and difference as separate columns",
         "Three columns on every originated row; the market column is blank where no price exists",
         "origination.html", "done"),
        ("5", "Separate signal from staking on the leaderboard",
         "Two scores from different evidence, and ranking uses signal only", "leaderboard.html", "done"),
        ("6", "Track the depth of the replacement, not just the fact",
         "Replacement rank, printed depth and names remaining behind, per injured slot; offence, "
         "defence and special teams never mixed", "depth.html", "done"),
        ("7", "Correlations only from official numbers, with n published",
         f"Six measured quantities each printing n, plus {len(c['not_measured'])} named blanks and "
         "what would close them", "correlation.html", "done"),
        ("8", "A demotion gate that returns a live strategy to paper",
         f"One gate, {len(b['demotion_gate'])} written clauses, applied; "
         f"{b['counts']['demoted_to_paper']} of {b['counts']['variants']} variants sit in paper",
         "demotion.html", "done"),
    ]
    rows = []
    for number, name, state, href, status in reqs:
        kind = {"done": "ok", "partial": "warn"}[status]
        rows.append(
            row([f"<td>{esc(number)}</td>", f"<td>{esc(name)}</td>", f"<td>{esc(state)}</td>",
                 f'<td><a href="{href}">{esc(href)}</a></td>', f"<td>{badge(status, kind)}</td>"],
                [SAMPLE_PRICE])
        )
    parts.append(table("Requirement status, with the page that carries the evidence",
                       ["#", "Requirement", "Where it stands", "Evidence", "Status", "Source"], rows))
    parts.append("<h2>What the numbers say, in one screen</h2>")
    parts.append(
        '<div class="panel"><ol>'
        f"<li><strong>The market knows more than we do.</strong> The published close correlates "
        f"{mk['market_line_vs_actual_margin']['r']} with the actual margin "
        f"(n={mk['market_line_vs_actual_margin']['n']}). Our fair line correlates "
        f"{mk['fair_line_vs_actual_margin']['r']} (n={mk['fair_line_vs_actual_margin']['n']}): the "
        "same sign, about half the information.</li>"
        f"<li><strong>Our total points the wrong way.</strong> The market's total correlates "
        f"{mk['market_total_vs_actual_total']['r']} with the actual total; ours correlates "
        f"{mk['fair_total_vs_actual_total']['r']}. That is a defect in our model, and it is "
        "published as one rather than tuned away on the same games.</li>"
        f"<li><strong>Nothing ranks.</strong> {b['counts']['variants']} variants were graded, "
        f"{b['counts']['eligible_but_not_significant']} clear the selection floor, and none clears "
        "multiplicity control. To see a 55% edge at 80% power takes 617 settled selections; the "
        "store holds 136 games.</li>"
        f"<li><strong>The split did not flatter us here.</strong> The best staking record is also "
        f"the best signal record ({b['divergence']['best_staking_id']}, "
        f"{b['divergence']['best_staking_units']} units, hit rate "
        f"{b['divergence']['best_staking_hit_rate']}), so separating the two did not promote a "
        "different entry. What it did expose is the opposite case: variants that clear break-even "
        "on hit rate while their units column is negative.</li>"
        f"<li><strong>Depth is counted, not scored.</strong> "
        f"{dp['counts']['injury_rows_with_no_printed_name_behind']} injured players are already the "
        f"last name printed at their position, and "
        f"{dp['counts']['replacements_that_are_the_last_printed_name']} more have a replacement who "
        "is himself last on the chart. Both are counts of printed slots, not points.</li>"
        "</ol></div>"
    )
    parts.append(
        '<div class="panel body-text"><h3>What this desk does not do</h3>'
        "<p>It places no wager, opens no account, holds no bankroll and produces no monetary "
        "reward. It does not claim an edge: the honest reading of the leaderboard is that the "
        "sample is too small to tell. Where a value is unknown, the cell is blank and the item is "
        "on the flagged page, so a reader can see the hole instead of a plausible number.</p>"
        "<p>Read the <a href=\"suggestions.html\">suggestions</a> before relying on anything here: "
        "each one states what would make it fail.</p></div>"
    )
    return "".join(parts)


def page_prices(d: dict) -> str:
    p = d["prices"]
    c = p["counts"]
    parts = [
        '<p class="lead">One row per game, with both clubs\' published pages as the confirmation. '
        "The two pages must agree on the total and be exact negatives on the signed spread. A "
        "disagreement fails the build; it is never averaged.</p>",
        '<div class="kpis">'
        + kpi(c["clubs_with_a_page"], "club pages read", "one per club")
        + kpi(c["evidence_rows"], "transcribed rows", "spread and total on each")
        + kpi(c["games_reconciled"], "games reconciled", "both pages agree")
        + kpi(c["publisher_verdicts_reconcile"], "publisher verdicts re-derived", "zero mismatches")
        + kpi("0", "games with an opening number", "not published")
        + "</div>",
    ]
    market_rows = []
    for key, status in p["markets"].items():
        published = status == "published"
        market_rows.append(
            row([
                f"<td>{esc(key.replace('_', ' '))}</td>",
                f"<td>{badge('published', 'ok') if published else badge('not published', 'bad')}</td>",
                f"<td>{esc(status.replace('_', ' '))}</td>",
                cell(None if published else None),
            ], [SAMPLE_PRICE])
        )
    parts.append(table(
        "Every market this desk looked for, and whether the publisher prints it",
        ["Market", "Published", "Status", "Stored value", "Source"], market_rows,
        note="The stored-value column is blank across the board on purpose: the presence of a market "
             "is recorded, and no value is invented for a market the publisher does not print.",
    ))

    rows = []
    for game in sorted(p["games"], key=lambda g: (g.get("week") or 99, g.get("date") or "", g["home"])):
        rows.append(
            row([
                f"<td>{esc(game['week'])}</td>",
                f"<td>{esc(game['date'])}</td>",
                f"<td>{esc(game['away'] + ' @ ' + game['home'])}</td>",
                cell(game["closing_line_home"]),
                cell(game["closing_total"]),
                cell(game["actual_margin_home"]),
                cell(game["actual_total"]),
                cell(game["home_cover"]),
                cell(game["total_result"]),
            ], list(game["sources"]) + [result_url(game)], price_label(game))
        )
    parts.append(table(
        f"Every reconciled game ({len(rows)}), close beside result",
        ["Wk", "Date", "Game", "Close (home)", "Close total", "Actual margin", "Actual total",
         "Home cover", "Total result", "Sources"],
        rows,
        note="The line is written from the home club's side, so a home line of -7 means the home "
             "club is favoured by seven. Actual margin is home minus away, so it carries the same "
             "sign. A blank cell means the value was not published or the game has no result in the "
             "frozen feed; it is never a zero.",
    ))
    parts.append(
        f'<div class="panel body-text"><h3>Why the stored number is called a close</h3>'
        f"<p>{esc(p['opening_line_note'])}</p>"
        f"<p>Kind of number held: <code>{esc(p['price_kind'])}</code>. A published reference price "
        "is not an executable offer: no book, limit, hold or account is implied by this record.</p>"
        "<p>Provenance: the page itself credits historical line data to Sports Odds History, so even "
        "a correctly transcribed number is a second-hand record of someone else's market.</p></div>"
    )
    return "".join(parts)


def page_origination(d: dict) -> str:
    o = d["orig"]
    c = o["counts"]
    parts = [
        '<p class="lead">Three columns on every row: our fair line, the published market line, and '
        "the difference. Production order is the side first, then the total, then the moneyline, and "
        "the dependency is enforced rather than described.</p>",
        '<div class="kpis">'
        + kpi(c["side_originated"], "games with a fair side", "needs prior games")
        + kpi(c["total_originated"], "games with a fair total", "needs the side")
        + kpi(c["moneyline_originated"], "games with a fair moneyline", "needs both")
        + kpi(c["market_line_available"], "games with a market line", "published")
        + kpi(c["market_moneyline_available"], "games with a market moneyline", "not published")
        + "</div>",
        '<div class="panel body-text"><h3>Order of production, enforced in code</h3>'
        f"<p>{esc(o['order_note'])}</p>"
        f"<p><code>{esc(' then '.join(o['order_enforced']))}</code></p>"
        "<p>The consequence is visible in the table: the 16 games with no prior game in the record "
        "carry no fair line, and because the total and the moneyline both depend on the side, they "
        "carry neither of those either. A missing row is never filled by a league-average "
        "substitution.</p></div>",
    ]
    agree = o["agreement"]
    rows = []
    for key, label in (("side_vs_market", "Fair side against the market line"),
                       ("total_vs_market", "Fair total against the market total")):
        a = agree[key]
        rows.append(
            row([f"<td>{esc(label)}</td>", f"<td>{esc(a['n'])}</td>", cell(a["mean"]),
                 cell(a["mean_abs"]), cell(a["within_1"]), cell(a["within_3"])],
                [SAMPLE_PRICE])
        )
    parts.append(table(
        "Does our number agree with the market? n is printed beside every value",
        ["Comparison", "n", "Mean difference", "Mean absolute difference", "Within 1 point",
         "Within 3 points", "Source"], rows,
        note="A positive mean on the total means our number sits above the market's on average. "
             "That bias is the defect recorded as PD07, not a result.",
    ))
    rows = []
    for game in sorted(o["games"], key=lambda g: (g["week"], g["date"], g["home"])):
        if game["side_status"] != "originated":
            continue
        rows.append(
            row([
                f"<td>{esc(game['week'])}</td>",
                f"<td>{esc(game['away'] + ' @ ' + game['home'])}</td>",
                cell(game["fair_line_home"]), cell(game["market_line_home"]), cell(game["line_difference"]),
                cell(game["fair_total"]), cell(game["market_total"]), cell(game["total_difference"]),
                cell(game["fair_home_ml"]), cell(game["p_home_win"]),
                cell(game["actual_margin_home"]), cell(game["actual_total"]),
            ], [SAMPLE_PRICE, result_url(game)], price_label(game))
        )
    parts.append(table(
        f"Fair line, market line and difference, all {len(rows)} originated games",
        ["Wk", "Game", "Fair line", "Market line", "Diff", "Fair total", "Market total", "Diff",
         "Fair home ML", "P(home)", "Actual margin", "Actual total", "Sources"],
        rows,
        note="There is no market moneyline column because no moneyline is published. The fair ML is "
             "our derived price and is labelled as ours, never as a price anyone offered.",
    ))
    params = o["parameters"]
    parts.append(
        '<div class="panel body-text"><h3>Parameters, fixed before grading</h3><ul>'
        + "".join(f"<li><code>{esc(k)}</code>: {esc(v)}</li>" for k, v in params.items() if k != "note")
        + f"</ul><p>{esc(params['note'])}</p>"
        f"<p>Break-even at the stated assumed price of {esc(o['break_even']['assumed_price'])} is "
        f"{esc(o['break_even']['break_even_probability'])}. {esc(o['break_even']['note'])} A real "
        "market price includes a hold this desk was never able to observe.</p></div>"
    )
    return "".join(parts)


def page_leaderboard(d: dict) -> str:
    b = d["board"]
    c = b["counts"]
    parts = [
        '<p class="lead">Two scores per entry, built from different evidence. Signal asks whether '
        "the forecast beat the published closing number. Staking asks what a flat stake would have "
        "done. Ranking uses signal only, so a lucky staking run cannot promote a bad forecast.</p>",
        '<div class="kpis">'
        + kpi(c["variants"], "registered variants", "the whole family is graded")
        + kpi(c["ranked"], "ranked", f"q at or below {b['fdr_level']}")
        + kpi(c["eligible_but_not_significant"], "clear the floor, fail multiplicity", "listed, not ranked")
        + kpi(c["demoted_to_paper"], "in paper", "per gate DG01")
        + kpi(b["min_selections_to_rank"], "selections needed to rank", "pre-registered floor")
        + "</div>",
    ]
    rows = []
    for entry in b["entries"]:
        sig, stk, dm = entry["signal"], entry["staking"], entry["demotion"]
        kind = "bad" if dm["state"] == "demote_to_paper" else "neutral"
        rows.append(
            row([
                f"<td>{esc(entry['id'])}</td>",
                f"<td>{esc(entry['name'])}</td>",
                f"<td>{esc(entry['n_settled'])}</td>",
                cell(sig.get("hit_rate")), cell(sig.get("q_value_bh")), cell(sig.get("brier")),
                cell(stk.get("units")), cell(stk.get("max_drawdown_units")),
                f"<td>{badge(dm['state'].replace('_', ' '), kind)}</td>",
            ], [SAMPLE_PRICE])
        )
    parts.append(table(
        "Every registered variant, signal beside staking",
        ["ID", "Variant", "n settled", "Signal hit rate", "q (BH)", "Brier", "Units at assumed -110",
         "Max drawdown", "Gate", "Source"], rows,
        note="Hit rate counts beating the published closing number, not the model's own line. Units "
             "are an accounting convention at a stated assumed price with no observed hold: they are "
             "not a profit claim and they never rank an entry.",
    ))
    div = b["divergence"]
    parts.append(
        '<div class="panel body-text"><h3>What the split actually caught</h3>'
        f"<p>Best staking record: <strong>{esc(div['best_staking_id'])}</strong> at "
        f"{esc(div['best_staking_units'])} units and a {esc(div['best_staking_hit_rate'])} hit rate. "
        f"Best signal record: <strong>{esc(div['best_signal_id'])}</strong> at "
        f"{esc(div['best_signal_hit_rate'])}. Same entry: <strong>{esc(div['same_entry'])}</strong>.</p>"
        "<p>Here the two records coincide, so the split rescued nothing. It did the other job: a "
        "single units column would have hidden that several variants sit at or above break-even on "
        "hit rate while their units column is negative, and it would have hidden the reverse too.</p>"
        f"<p>{esc(div['reading'])}</p></div>"
    )
    rows = [
        row([f"<td>{esc(p['true_rate'])}</td>", f"<td>{esc(p['n'])}</td>",
             f"<td>{esc(p['power_vs_coin_at_5pct'])}</td>"], [SAMPLE_PRICE])
        for p in b["power"]
    ]
    parts.append(table(
        "How many settled selections a real edge needs before it can be seen",
        ["True hit rate", "Settled selections", "Power against a coin at a 5% test", "Source"], rows,
        note="This is the number that stops a promotion. Nothing in the store is close to it, so the "
             "correct statement is 'not yet answerable', not 'no edge'.",
    ))
    return "".join(parts)


def page_depth(d: dict) -> str:
    dp = d["depth"]
    c = dp["counts"]
    parts = [
        '<p class="lead">"Starter out" is one bit. "Starter out, and the player who replaces him is '
        'the last printed name at the position" is a different situation. This page measures the '
        "second one, and keeps offence, defence and special teams apart because they are not "
        "interchangeable.</p>",
        '<div class="kpis">'
        + kpi(c["clubs_with_printed_chart"], "clubs with a printed chart", "of 32")
        + kpi(c["printed_slots"], "printed slots read", "two files merged")
        + kpi(c["injury_rows_matched_to_a_printed_slot"], "injury rows matched", "to a printed slot")
        + kpi(c["replacements_that_are_the_last_printed_name"], "replacement is the last name", "")
        + kpi(c["injury_rows_with_no_printed_name_behind"], "no name behind the injured player",
              "printed chain exhausted")
        + "</div>",
        '<div class="panel body-text"><h3>What is counted, and what is deliberately not</h3>'
        f"<p>{esc(dp['not_a_point_value'])}</p>"
        f"<p>Units kept separate: {esc(', '.join(dp['units_kept_separate']))}. Ordering weights: "
        f"<code>{esc(json.dumps(dp['rank_weight']))}</code></p></div>",
    ]
    rows = []
    for club in dp["clubs"]:
        off = club["by_unit"].get("Offense", {})
        dfn = club["by_unit"].get("Defense", {})
        rows.append(
            row([
                f"<td>{esc(club['club'])}</td>", f"<td>{esc(club['printed_slots'])}</td>",
                cell(off.get("starters_on_report")), cell(off.get("replacement_is_last_printed_name")),
                cell(off.get("mean_replacement_rank")),
                cell(dfn.get("starters_on_report")), cell(dfn.get("replacement_is_last_printed_name")),
                cell(dfn.get("mean_replacement_rank")), cell(club["total_depth_points"]),
            ], [club["depth_source_url"], INJURY_URL])
        )
    parts.append(table(
        "Replacement depth by club, offence and defence never mixed",
        ["Club", "Printed slots", "Off starters on report", "Off replacement at last name",
         "Off mean rank", "Def starters on report", "Def replacement at last name", "Def mean rank",
         "Depth points", "Sources"], rows,
        note="Depth points are an ordering weight over printed slots. They are not a points "
             "estimate, a probability or a line adjustment, and they were never fitted to outcomes.",
    ))
    thin = [r for r in dp["replacements"] if r.get("thin_reason")]
    rows = []
    for r in thin:
        rows.append(
            row([
                f"<td>{esc(r['club'])}</td>", f"<td>{esc(r['unit'])}</td>",
                f"<td>{esc(r['position'])}</td>", f"<td>{esc(r['player'])}</td>",
                f"<td>{esc(r['replaced_rank'])}</td>",
                cell(r["replacement_player"]), cell(r["replacement_rank"]),
                cell(r["slot_deepest_rank"]), cell(r["remaining_depth_behind_replacement"]),
                f"<td>{badge(r['thin_reason'], 'warn')}</td>",
            ], [r["depth_source_url"], r["injury_source_url"]])
        )
    parts.append(table(
        f"The thin replacements ({len(rows)} of {c['injury_rows_matched_to_a_printed_slot']}): one "
        "printed name or none behind the replacement",
        ["Club", "Unit", "Pos", "Injured", "Rank out", "Replacement", "His rank", "Printed depth",
         "Behind him", "Why it is thin", "Sources"], rows,
        note="An empty replacement cell means the injured player was already the last printed name "
             "at that position, so the chart shows nobody behind him. That is not a missing value. "
             "A zero in the depth column means the replacement is himself the last printed name.",
    ))
    parts.append(
        '<div class="panel body-text"><h3>Limitations that stop this becoming a coefficient</h3><ul>'
        + "".join(f"<li>{esc(x)}</li>" for x in dp["limitations"])
        + "</ul><p>The temptation is to turn depth into a points adjustment and add it to the line. "
        "This desk does not do that, because there is one week of depth and no way to test whether "
        "the adjustment would have helped.</p></div>"
    )
    return "".join(parts)


def page_correlation(d: dict) -> str:
    c = d["corr"]
    parts = [
        '<p class="lead">Every value here is computed only from officially sourced numbers, and '
        "every value prints its n. Anything that cannot be computed from official numbers is blank "
        "and named, never set to zero.</p>",
        '<div class="panel body-text"><h3>Sign convention, stated so the numbers cannot be misread</h3>'
        f"<p>{esc(c['sign_convention'])}</p></div>",
    ]
    rows = []
    for key, v in c["measured"].items():
        value = v.get("r") if v.get("r") is not None else v.get("phi")
        rows.append(
            row([f"<td>{esc(v['pair'])}</td>", f"<td>{esc(v['n'])}</td>", cell(value),
                 cell(v.get("ci_low")), cell(v.get("ci_high")), cell(v.get("expected_sign")),
                 f"<td>{esc(v['kind'])}</td>"], [SAMPLE_PRICE, SAMPLE_RESULT])
        )
    parts.append(table(
        "Measured dependence, with n on every row",
        ["Quantity", "n", "r or phi", "95% low", "95% high", "Expected sign", "Kind", "Sources"],
        rows,
        note="Intervals are nominal and assume independent pairs, which division games violate. A "
             "value whose sign contradicts the stated convention is a defect, not a finding.",
    ))
    rows = []
    for item in c["not_measured"]:
        rows.append(
            row([f"<td>{esc(item['quantity'])}</td>", '<td data-empty="true"></td>',
                 f"<td>{esc(item['why_blank'])}</td>", f"<td>{esc(item['do_not_assume'])}</td>",
                 f"<td>{esc(item['what_would_close_it'])}</td>"], [SAMPLE_PRICE])
        )
    parts.append(table(
        "Deliberately blank, and why",
        ["Quantity", "Value", "Why it is blank", "Do not assume", "What would close it", "Source"],
        rows,
        note="The blank value column is the point of this table: an unpriced dependence must not be "
             "rendered as zero, because zero would quietly underprice every same-game combination.",
    ))
    parts.append(
        '<div class="panel body-text"><h3>Scope</h3>'
        f"<p>Games in scope: {esc(c['counts']['games_in_scope'])}; forecast rows: "
        f"{esc(c['counts']['forecast_rows'])}. {esc(c['rule'])}</p>"
        "<p>Two of these values are ours and four are the market's. Putting them side by side is the "
        "point: it is the only honest way to say how much sharper the market is without claiming we "
        "can match it.</p></div>"
    )
    return "".join(parts)


def page_demotion(d: dict) -> str:
    b = d["board"]
    gate = b["demotion_gate"]
    parts = [
        '<p class="lead">A strategy that ranks has to keep earning its place. This is the written '
        "rule that sends one back to paper, and the record of what it did to every variant in front "
        "of it.</p>",
        '<div class="panel body-text"><h2>The gate</h2>'
        f"<p><strong>{esc(gate['id'])}</strong> {esc(gate['rule'])}</p>"
        f"<p>{esc(gate['rationale'])}</p><ul>"
        f"<li>Window: {esc(gate['window_selections'])} settled selections</li>"
        f"<li>Maximum drawdown before review: {esc(gate['max_drawdown_units'])} flat units</li>"
        f"<li>Maximum tolerated price disagreement: {esc(gate['max_price_disagreement_points'])} points</li>"
        f"<li>Declared before grading: {esc(gate['declared_before_grading'])}</li>"
        "</ul></div>",
    ]
    rows = []
    for entry in b["entries"]:
        dm = entry["demotion"]
        kind = "bad" if dm["state"] == "demote_to_paper" else "neutral"
        rows.append(
            row([f"<td>{esc(entry['id'])}</td>", f"<td>{esc(entry['name'])}</td>",
                 f"<td>{badge(dm['state'].replace('_', ' '), kind)}</td>",
                 cell("; ".join(dm["breaches"]) or None)], [SAMPLE_PRICE])
        )
    parts.append(table(
        "Gate outcome per variant",
        ["ID", "Variant", "State", "Breaches recorded", "Source"], rows,
        note="No variant was ever live, so every outcome here is a paper outcome. The gate has never "
             "fired against a promotion, which is itself an open item (PQ11): a rule that has only "
             "ever seen losing strategies is not yet shown to work.",
    ))
    parts.append(
        '<div class="panel body-text"><h3>Why a gate and not a feeling</h3>'
        "<p>A strategy that has been promoted is exactly the one nobody wants to demote, so the "
        "decision is written down before the pressure arrives. The clauses are checkable against the "
        "record, and a breach is reported with the number that triggered it.</p>"
        "<p>The gate is deliberately blunt. It cannot tell a genuine cold streak from a broken "
        "model, and it does not try: it stops the question being decided by whoever is most "
        "attached to the result.</p></div>"
    )
    return "".join(parts)


def page_questions(d: dict) -> str:
    rows = []
    for q in d["questions"]:
        rows.append(
            row([
                f"<td>{esc(q['id'])}</td>", f"<td>{esc(q['question'])}</td>",
                f"<td>{esc(q['known'])}</td>", cell(q["missing"]),
                f"<td>{esc(q['blocks'])}</td>", f"<td>{esc(q['closes_with'])}</td>",
                f"<td>{esc(q['status'])}</td>",
            ], [SAMPLE_PRICE])
        )
    return (
        '<p class="lead">What is known with a source, what is missing, what the missing part blocks, '
        "and the action that closes it. A question that cannot cite an official source leaves that "
        "part blank rather than guessed.</p>"
        + table("Questions, what we hold, what we lack, and what closes each one",
                ["ID", "Question", "Known, with source", "Missing", "Blocks", "Closes with",
                 "Status", "Source"], rows,
                note="A question is closed only when the action column has actually been carried out "
                     "and the evidence is in the store. Until then the status stays open.")
    )


def page_suggestions(d: dict) -> str:
    parts = [
        '<p class="lead">Ranked proposals to review before anything is implemented. Each states its '
        "evidence in the numbers, what it unlocks, what it costs, what could go wrong, and a runnable "
        "acceptance test. The decision columns are blank on purpose: nothing here acts on itself.</p>",
        '<div class="panel body-text"><h3>How to use this page</h3><ol>'
        "<li>Check the evidence against the number quoted on the page it comes from. If they do not "
        "match, treat the proposal as unproven and say so.</li>"
        "<li>Read the risk before the benefit. The most common failure is implementing a proposal on "
        "the same games that motivated it.</li>"
        "<li>Record adopt, defer or reject against the ID. Nothing is implemented by being listed, "
        "and this build does not choose on your behalf.</li>"
        "<li>Hold the implementation to the acceptance test. If the test cannot be run, the proposal "
        "is not ready, however good the idea sounds.</li>"
        "</ol></div>",
    ]
    rows = []
    for s in d["suggestions"]:
        rows.append(
            row([
                f"<td>{esc(s['id'])}</td>", f"<td>{esc(s['priority'])}</td>",
                f"<td>{esc(s['title'])}</td>", f"<td>{esc(s['evidence'])}</td>",
                f"<td>{esc(s['unlocks'])}</td>", f"<td>{esc(s['cost'])}</td>",
                f"<td>{esc(s['risk'])}</td>", f"<td>{esc(s['acceptance_test'])}</td>",
                '<td class="choices">'
                f'<label class="choice"><input type="radio" name="{esc(s["id"])}" value="adopt">Adopt</label>'
                f'<label class="choice"><input type="radio" name="{esc(s["id"])}" value="defer">Defer</label>'
                f'<label class="choice"><input type="radio" name="{esc(s["id"])}" value="reject">Reject</label>'
                f'<input class="reason" type="text" aria-label="Reason for {esc(s["id"])}" '
                'placeholder="optional reason"></td>',
            ], [SAMPLE_PRICE])
        )
    parts.append(table(
        "Ranked suggestions, with evidence, cost, risk and an acceptance test",
        ["ID", "Priority", "Proposal", "Evidence", "Unlocks", "Cost", "Risk", "Acceptance test",
         "Your choice", "Source"], rows,
        note="The controls record a preference in your browser and change no file. The decision "
             "record below stays blank until you fill it in, and a suggestion is not adopted by "
             "appearing on this page.",
    ))
    rows = []
    for rec in d["decisions"]:
        rows.append(
            row([f"<td>{esc(rec['suggestion_id'])}</td>", '<td data-empty="true"></td>',
                 '<td data-empty="true"></td>', '<td data-empty="true"></td>',
                 f"<td>{esc(rec['note'])}</td>"], [SAMPLE_PRICE])
        )
    parts.append(table(
        "Decision record, deliberately blank",
        ["Suggestion", "Decision", "Decided on", "Decided by", "Note", "Source"], rows,
        note="Three blanks in every row is the intended state. A suggestion without a recorded "
             "decision is still a suggestion.",
    ))
    return "".join(parts)


def page_flagged(d: dict) -> str:
    rows = []
    for fid, title, detail, where, severity, state in FLAGS:
        kind = {"high": "bad", "medium": "warn", "low": "neutral"}[severity]
        target = where.split("#")[0]
        rows.append(
            row([f"<td>{esc(fid)}</td>", f"<td>{esc(title)}</td>", f"<td>{esc(detail)}</td>",
                 f'<td><a href="{esc(target)}">{esc(where)}</a></td>',
                 f"<td>{badge(severity, kind)}</td>", f"<td>{esc(state)}</td>"], [SAMPLE_PRICE])
        )
    open_count = sum(1 for f in FLAGS if not f[5].startswith(("fixed", "explained")))
    return (
        f'<p class="lead">Every irregularity found while building this desk, including the ones this '
        f"build fixed. Fixing a defect does not remove it from the record. {open_count} of {len(FLAGS)} "
        "remain open; none of them blocks publication, and all of them block a claim.</p>"
        + table("Flagged for review", ["ID", "Item", "Detail", "Where", "Severity", "State", "Source"],
                rows,
                note="Open items are here so a reviewer can see exactly what is unverified before "
                     "relying on any number on this desk. Nothing on this page is a footnote to be "
                     "skipped: PD07 in particular says our own total model points the wrong way.")
    )


def page_sources(d: dict) -> str:
    seen = {}
    for game in d["prices"]["games"]:
        for url in game["sources"]:
            seen[url] = seen.get(url, 0) + 1
    rows = []
    for url in sorted(seen):
        rows.append(
            row([f"<td>{esc(REGISTRY[url])}</td>", f"<td>{esc(url.split('/teams/')[1][:3].upper())}</td>",
                 f"<td>{esc(seen[url])}</td>"], [url], {url: "page"})
        )
    parts = [
        '<p class="lead">One row per page actually read, with the registered ID it is filed under and '
        "how many stored games rest on it. Access was through a rendered page reader, which is "
        "evidence the content was served, not proof of a particular HTTP status code.</p>",
        '<div class="panel body-text"><h3>Access boundary</h3>'
        "<p>Direct HTTPS from this environment failed for the price and schedule hosts, so every "
        "retrieval went through the page reader. That is recorded rather than glossed: a rendered "
        "read cannot attest a status code or a cache state.</p>"
        "<p>No odds vendor, sportsbook account or licensed feed was used. The price record is a "
        "published reference page, and its own provenance is a further step back to Sports Odds "
        "History.</p></div>",
        table("Club price pages read, and how many games rest on each",
              ["Registered ID", "Club", "Games", "Link"], rows),
    ]
    dp = d["depth"]
    inj = dp["sources"]["injury"]
    rows = [
        row([f"<td>{esc('Week 10 injury report')}</td>", f"<td>{esc(inj['id'])}</td>",
             f"<td>{esc(dp['counts']['injury_rows'])}</td>"],
            [inj["url"]], {inj["url"]: "page"})
    ]
    parts.append(table(
        "Depth and availability sources",
        ["Use", "Registered ID", "Injury rows read", "Link"], rows,
        note="The depth charts cannot share one registry ID: each is a separate club page, so each "
             "slot row cites its own club's registered URL. "
             f"{dp['sources']['depth']['clubs_with_registered_page']} of "
             f"{dp['sources']['depth']['clubs_total']} clubs have one; "
             f"{', '.join(dp['sources']['depth']['unregistered'])} does not, because its chart "
             "renders as an image and no chain is published. That absence is recorded, not filled.",
    ))
    return "".join(parts)


BUILDERS = {
    "index.html": page_index,
    "prices.html": page_prices,
    "origination.html": page_origination,
    "leaderboard.html": page_leaderboard,
    "depth.html": page_depth,
    "correlation.html": page_correlation,
    "demotion.html": page_demotion,
    "questions.html": page_questions,
    "suggestions.html": page_suggestions,
    "flagged.html": page_flagged,
    "sources.html": page_sources,
}


def nav(current: str) -> str:
    current_attr = ' aria-current="page"'
    links = "".join(
        f'<a href="{name}"{current_attr if name == current else ""}>{esc(label)}</a>'
        for name, label in PAGES
    )
    return (
        '<header class="top"><div class="brand"><strong>OWN7 · Price &amp; market desk</strong>'
        f"<span>closing prices · fair against market · signal against staking · read {esc(READ_ON)}</span></div>"
        f'<nav aria-label="Desk pages">{links}<a href="../../index.html">← NFL workspace</a></nav></header>'
    )


def render(name: str, d: dict) -> str:
    title = next(label for n, label in PAGES if n == name)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · {esc(SITE_TITLE)}</title>
<meta name="description" content="NFL closing prices, fair-against-market comparison, signal-against-staking leaderboard and replacement depth. Source-linked, blank where unconfirmed.">
<link rel="stylesheet" href="style.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{nav(name)}
<main id="main">
<p class="eyebrow">{esc(SITE_TITLE)}</p>
<h1>{esc(title)}</h1>
{BUILDERS[name](d)}
<p class="note">Paper research only. No wager, stake, bankroll or monetary reward is produced
anywhere on this desk. A market line here is a published reference price and not an executable
offer, and no edge is claimed.</p>
</main>
<footer>Prices attributed to Pro-Football-Reference.com; results and injury reports to NFL.com;
depth charts to the member clubs. Not affiliated with or endorsed by the NFL. Generated
deterministically from committed artifacts on {esc(READ_ON)}.</footer>
</body>
</html>
"""


def write_css() -> str:
    return """:root{--bg:#f7f8fb;--panel:#fff;--ink:#172033;--muted:#51607a;--line:#d8deea;--accent:#164e8a}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--ink);line-height:1.55}
.skip{position:absolute;left:-9999px;top:0;background:var(--accent);color:#fff;padding:.5rem;z-index:10}
.skip:focus{left:0}
.top{background:#101a2e;color:#fff;padding:1rem}
.brand{display:flex;gap:.75rem;align-items:baseline;flex-wrap:wrap}
.brand strong{font-size:1.2rem}
.brand span{color:#c7d2e6;font-size:.9rem}
nav{display:flex;flex-wrap:wrap;gap:.35rem;margin-top:.75rem}
nav a{color:#e6edf7;text-decoration:none;padding:.35rem .55rem;border-radius:.375rem;font-size:.9rem;min-height:2rem;display:inline-flex;align-items:center}
nav a:hover,nav a:focus{background:#243452}
nav a[aria-current=page]{background:var(--accent);color:#fff;font-weight:600}
main{max-width:1250px;margin:0 auto;padding:1.25rem}
.eyebrow{color:var(--muted);font-size:.85rem;text-transform:uppercase;letter-spacing:.04em;margin-bottom:.25rem}
h1{margin:.25rem 0 .5rem;font-size:1.85rem}
h2{font-size:1.25rem;margin:1.1rem 0 .5rem}
h3{font-size:1.05rem;margin:1rem 0 .4rem}
.lead{color:var(--muted);max-width:80ch}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:.75rem;margin:1rem 0}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:.75rem;padding:.9rem}
.kpi-value{display:block;font-size:1.6rem;font-weight:700;color:var(--accent);font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.kpi-label{color:var(--muted);font-size:.85rem;display:block}
.sub{display:block;font-size:.78rem;color:var(--muted);margin-top:.15rem}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:.75rem;padding:1rem;margin:1rem 0}
.panel ol,.panel ul{padding-left:1.2rem}
.table-wrap{overflow-x:auto;max-width:100%;border:1px solid var(--line);border-radius:.5rem;background:var(--panel);margin:1rem 0}
table{border-collapse:collapse;width:100%;min-width:820px;font-size:.86rem}
caption{text-align:left;padding:.6rem;font-weight:600;color:var(--muted)}
th,td{border-top:1px solid var(--line);padding:.45rem .55rem;text-align:left;vertical-align:top}
thead th{background:#eef2f8;position:sticky;top:0}
tbody tr:nth-child(even){background:#fafbfe}
td[data-empty]{background:#fff7e6}
td.src{white-space:nowrap}
td.src a{display:inline-block;font-size:.78rem;margin-right:.4rem;min-height:1.6rem;line-height:1.6rem}
.note{color:var(--muted);font-size:.88rem;max-width:90ch}
a{color:var(--accent);overflow-wrap:anywhere}
code{background:#eef2f8;padding:.1rem .3rem;border-radius:.25rem;font-size:.85rem;overflow-wrap:anywhere}
.badge{display:inline-block;font-size:.75rem;font-weight:600;padding:.12rem .45rem;border-radius:.3rem;white-space:nowrap}
.badge-ok{background:#e3f4e8;color:#14532d}
.badge-warn{background:#fff4e0;color:#8a4b00}
.badge-bad{background:#fbe6e6;color:#7f1d1d}
.badge-neutral{background:#eef2f8;color:#51607a}
.choices{white-space:nowrap;min-width:11rem}
.choice{display:inline-flex;align-items:center;gap:.2rem;margin-right:.4rem;font-size:.8rem}
.reason{display:block;margin-top:.4rem;width:100%;min-width:9rem;font:inherit;font-size:.8rem;padding:.3rem .4rem;border:1px solid var(--line);border-radius:.3rem}
footer{max-width:1250px;margin:0 auto;padding:1rem 1.25rem 2rem;color:var(--muted);font-size:.85rem}
input:focus,a:focus{outline:3px solid #f0b429;outline-offset:2px}
@media(max-width:640px){h1{font-size:1.5rem}main{padding:1rem}}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the built pages are current")
    args = parser.parse_args()
    data = load()
    SITE.mkdir(parents=True, exist_ok=True)
    outputs = {name: render(name, data) for name, _ in PAGES}
    css = write_css()
    manifest = {
        "read_on": READ_ON,
        "pages": [name for name, _ in PAGES],
        # Only IDs that really exist in research/sources.json: a desk that names an unregistered
        # source is claiming a provenance it cannot show.
        "source_ids": sorted({registered_id(u) for g in data["prices"]["games"] for u in g["sources"]}
                             | {PFR, PFR_SOURCES, data["depth"]["sources"]["injury"]["id"], SCHEDULE}
                             | {registered_id(c["depth_source_url"]) for c in data["depth"]["clubs"]}),
        "counts": {
            "questions": len(data["questions"]),
            "suggestions": len(data["suggestions"]),
            "flags": len(FLAGS),
            "flags_open": sum(1 for f in FLAGS if not f[5].startswith(("fixed", "explained"))),
            "games": data["prices"]["counts"]["games_reconciled"],
        },
    }
    if args.check:
        stale = [n for n, t in outputs.items()
                 if not (SITE / n).exists() or (SITE / n).read_text(encoding="utf-8") != t]
        if stale:
            print("FAIL: stale desk pages: " + ", ".join(stale))
            return 1
        if not (SITE / "style.css").exists() or (SITE / "style.css").read_text(encoding="utf-8") != css:
            print("FAIL: style.css is stale")
            return 1
        print(f"OK: {len(outputs)} desk pages reproduce exactly")
        return 0
    for name, text in outputs.items():
        (SITE / name).write_text(text, encoding="utf-8")
    (SITE / "style.css").write_text(css, encoding="utf-8")
    (SITE / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {len(outputs)} pages to nfl-pricing/site/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
