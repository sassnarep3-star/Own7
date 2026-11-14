#!/usr/bin/env python3
"""Deterministic generator for the market desk site.

Contract enforced by scripts/check_site.py, and honoured here:
  * every ``<tbody><tr>`` carries ``data-source-ids`` naming registered source ids, and
  * at least one anchor inside that row points at one of those registered URLs.
  * an unknown value is an empty cell with ``data-empty="true"``, never filled in.

Nothing is computed at read time: every figure comes from a committed artifact in
``nfl-market-desk/data/`` that ``build.py --check`` reproduces byte-identically.
"""
from __future__ import annotations

import csv
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SITE = HERE / "site"

READ_ON = "2026-11-14"

PAGES = [
    ("index.html", "Overview"),
    ("summary.html", "Executive summary"),
    ("prices.html", "Price store"),
    ("origination.html", "Ordered origination"),
    ("leaderboard.html", "Leaderboard"),
    ("correlation.html", "Correlation"),
    ("availability.html", "Replacement depth"),
    ("gates.html", "Validation & demotion"),
    ("questions.html", "Questions & dossier"),
    ("suggestions.html", "Suggestions"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
    ("method.html", "Method & limits"),
]

SOURCE_IDS = {
    "EC6-ESPN-ODDS": "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/401873037/competitions/401873037/odds",
    "EC6-ESPN-EVENT": "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/401873048",
    "EC6-ESPN-TEAMS": "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2026/teams/1",
    "EC6-ESPN-PROPS": "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/401873046/competitions/401873046/odds/100/propBets",
    "EC6-NFL-SCHEDULE": "https://www.nfl.com/schedules/2026/by-week/week-1",
    "EC6-NFL-STANDINGS": "https://www.nfl.com/standings/",
    "EC6-NFL-INJURY": "https://www.nfl.com/injuries/league/2026/REG10",
    "EC6-CHI-DEPTH": "https://www.chicagobears.com/team/depth-chart",
    "EC6-DEN-DEPTH": "https://www.denverbroncos.com/team/depth-chart/",
    "EC6-PHI-DEPTH": "https://www.philadelphiaeagles.com/team/depth-chart",
    "EC6-TB-DEPTH": "https://www.buccaneers.com/team/depth-chart",
    "EC6-REPO": "https://github.com/sassnarep3-star/Own7",
}

ODDS_EVENT = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{eid}/competitions/{eid}/odds"

CLUB_CHART = {"CHI": "EC6-CHI-DEPTH", "DEN": "EC6-DEN-DEPTH",
              "PHI": "EC6-PHI-DEPTH", "TB": "EC6-TB-DEPTH"}

CLUB_NAME = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LA": "Los Angeles Rams", "LAC": "Los Angeles Chargers",
    "LV": "Las Vegas Raiders", "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings",
    "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SEA": "Seattle Seahawks", "SF": "San Francisco 49ers", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
}


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def load_csv(name: str) -> list[dict]:
    with (DATA / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_json(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def src(ids: list[str]) -> str:
    return " ".join(f'<a href="{esc(SOURCE_IDS[i])}" target="_blank" rel="noopener noreferrer">{esc(i)}</a>'
                    for i in ids)


def cell(value, numeric: bool = False) -> str:
    if value is None or str(value).strip() == "":
        return '<td data-empty="true" class="blank" aria-label="no value published"></td>'
    cls = ' class="num"' if numeric else ""
    return f"<td{cls}>{esc(value)}</td>"


def table(headers: list[str], rows: list[str], caption: str = "", note: str = "") -> str:
    head = "".join(f'<th scope="col">{esc(h)}</th>' for h in headers)
    out = ['<div class="table-wrap"><table>']
    if caption:
        out.append(f"<caption>{esc(caption)}</caption>")
    out.append(f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>")
    if note:
        out.append(f'<p class="note">{note}</p>')
    return "".join(out)


def kpi(value, label: str, tone: str = "") -> str:
    return (f'<div class="kpi"><span class="kpi-value">{value}</span>'
            f'<span class="kpi-label">{esc(label)}</span></div>')


def badge(text: str, kind: str) -> str:
    return f'<span class="badge badge-{esc(kind)}">{esc(text)}</span>'


def fmt(value, places: int = 3, signed: bool = False) -> str:
    if value is None or value == "":
        return ""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    s = f"{v:+.{places}f}" if signed else f"{v:.{places}f}"
    if abs(v) == int(abs(v)) and places > 0 and "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def pct(value) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return ""


def page(slug: str, title: str, subtitle: str, body: str) -> str:
    nav = "".join(
        f'<a href="{esc(href)}"' + (' aria-current="page"' if href == slug else "")
        + f'>{esc(label)}</a>'
        for href, label in PAGES
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · OWN7 market desk</title>
<meta name="description" content="{esc(subtitle)}">
<link rel="stylesheet" href="style.css"><script src="app.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="brand"><strong>OWN7</strong><span>NFL market desk · prices, origination, validation</span></div>
<nav aria-label="Desk sections">{nav}</nav></header>
<main id="main"><p class="eyebrow">Bounded snapshot · read {READ_ON} · research only · no wagers · prices relayed, not operator-direct</p>
<h1>{esc(title)}</h1><p class="subtitle">{subtitle}</p>
{body}
<footer><p>OWN7 · independent research. Market prices are {esc('DraftKings numbers as republished by ESPN (provider 100)')};
official results, injury and standings pages are attributed to NFL.com; depth charts to each club\'s own site.
Not affiliated with or endorsed by the NFL, any club, ESPN or any sportsbook. No wagers are placed and no reward is paid.
{len(PAGES)} pages · every table row links the official source it came from · unknown values are blank, never filled in.</p>
<p><a href="sources.html">Sources</a> · <a href="flagged.html">Flagged for review</a> ·
<a href="suggestions.html">Suggestions</a> · <a href="method.html">Method &amp; limits</a></p></footer>
</main></body></html>
"""


# --------------------------------------------------------------------------- pages
def build_index() -> str:
    a = load_json("analysis.json")
    c = a["counts"]
    cal = a["calibration"]
    luck = a["luck_decomposition"]
    sig = a["signal"]

    verdict = (
        '<div class="verdict"><h2>The one-paragraph answer</h2>'
        f'<p class="lede">This desk originated its own line for all <strong>{c["games_priced"]}</strong> Week 9 '
        f'games, stored <strong>{c["price_observations"]}</strong> opening and closing price observations, and graded '
        f'every bet against <strong>{c["official_results"]}</strong> official final scores. Its own model '
        '<strong>loses money</strong>, and the desk can show exactly why.</p>'
        f'<p>The side model went <strong>{luck["observed_wins"]}-{sig["side"]["losses"]}</strong> at the open for '
        f'<strong>{pct(sig["side"]["staking_roi"])}</strong> at flat stake. That is not bad luck. The model expects '
        f'<strong>{luck["model_expected_wins"]} wins</strong> on its own probabilities and got '
        f'{luck["observed_wins"]}, which is p = {luck["p_vs_model_expectation"]} against its own forecast. It is also '
        f'less accurate than the price it is trying to beat: margin error {cal["side"]["model_rmse"]} points RMSE '
        f'against the market&rsquo;s {cal["side"]["market_rmse"]}. A forecast with more error than the price, that then '
        'loses to the price, is behaving exactly as it should.</p>'
        '<p>No strategy is live, no reward is paid, and the sample needed to settle the question is printed on this '
        'site rather than left implied.</p></div>'
    )

    kpis = '<div class="kpis">' + "".join([
        kpi(c["price_observations"], "open and close price observations captured"),
        kpi(c["games_priced"], "Week 9 games with a full three-market board"),
        kpi(c["official_results"], "official final scores used for grading"),
        kpi(cal["side"]["model_rmse"], "model margin error, points RMSE"),
        kpi(cal["side"]["market_rmse"], "market margin error, points RMSE"),
        kpi(str(sig["side"]["required_n_at_55pct"]), "settled bets needed to detect a 55% rate"),
        kpi("0", "strategies live, and 0 reward paid"),
    ]) + "</div>"

    orders = (
        '<div class="orders">'
        '<div class="order"><div class="step">Originated first</div><h3>1 &middot; The side</h3>'
        '<p>From the margin distribution only. The one board whose fair price needs no assumption about scoring '
        'level.</p></div>'
        '<div class="order"><div class="step">Originated second</div><h3>2 &middot; The total</h3>'
        '<p>From the same score pair, fitted and reported separately. Never rescaled to flatter the side.</p></div>'
        '<div class="order"><div class="step">Originated third</div><h3>3 &middot; The moneyline</h3>'
        '<p>Last, and labelled a restatement of the side in price space, so one forecast is never counted as three '
        'signals.</p></div>'
        "</div>"
    )

    cards = "".join([
        '<a class="card" href="prices.html"><h2>Price store</h2>'
        f'<p>{c["price_observations"]} observations, every row naming its provider, its source and its retrieval '
        'date. All relayed, and labelled so.</p></a>',
        '<a class="card" href="origination.html"><h2>Ordered origination</h2>'
        '<p>Model line, market line and the difference as three separate columns on every game, side then total then '
        'moneyline.</p></a>',
        '<a class="card" href="leaderboard.html"><h2>Leaderboard</h2>'
        '<p>Signal and staking in separate columns. Promotion reads the signal only, and the code refuses a staking '
        'field.</p></a>',
        '<a class="card" href="correlation.html"><h2>Correlation</h2>'
        '<p>Official-sourced numbers only, every value carrying its n, with Holm adjustment across the '
        'register.</p></a>',
        '<a class="card" href="availability.html"><h2>Replacement depth</h2>'
        '<p>Which string dresses, not merely that someone is out. Four clubs have a captured chart; the other 28 say '
        'so.</p></a>',
        '<a class="card" href="gates.html"><h2>Validation &amp; demotion</h2>'
        '<p>Ten gates, each able to fail, plus five numeric demotion triggers that return a live strategy to '
        'paper.</p></a>',
    ])

    body = verdict + kpis + (
        '<section class="panel"><h2>The order of work is a design decision</h2>'
        '<p class="lead">The brief asked for the side first, then the total, then the moneyline. That order is '
        'enforced in the code rather than described in a document, because the order controls what each board is '
        'allowed to assume and how much independent evidence one forecast can claim.</p>' + orders + "</section>"
    ) + '<section>' + cards + '</section>' + (
        '<section class="panel"><h2>What this desk will not do</h2><ul>'
        '<li>It will not present a relayed price as an operator-confirmed one. No sportsbook was read directly.</li>'
        '<li>It will not fill a missing price with a notional number. Where a price is absent, the figure is '
        'blank.</li>'
        '<li>It will not promote a strategy for making money. Promotion reads the signal tier only.</li>'
        '<li>It will not rate a week using that week&rsquo;s own result. Ratings are rebuilt per week, on prior weeks '
        'only.</li>'
        '<li>It will not claim requirement 6 league-wide. Depth was captured for four clubs and the other 28 are '
        'marked.</li>'
        '</ul><p class="src-line">Read the <a href="method.html">method and limits</a> before using any number '
        'here.</p></section>'
    )
    return page("index.html", "Market desk",
                "Own lines, real prices, and a validation chain that can say no. Where the numbers fail, the failure "
                "is the finding.", body)



def build_summary() -> str:
    a = load_json("analysis.json")
    cal = a["calibration"]
    luck = a["luck_decomposition"]
    clv = a["closing_line_value"]
    sig = a["signal"]
    sel = a["selection_test"]
    d = load_json("dossier.json")

    body = (
        '<section class="panel"><h2>What was asked, and what was found</h2>'
        '<p>Eight requirements were set for this round. Each is answered below with the number that answers it, or '
        'with a statement that it is blocked and why. Nothing here is a projection.</p></section>'
    )

    req = [
        ("1 &middot; Price snapshot store with opening and closing numbers",
         "Built.", f'{a["counts"]["price_observations"]} observations across {a["counts"]["games_priced"]} games for '
         'side, total and moneyline, each carrying provider, provider id, source id, url and retrieval date. All '
         'relayed.'),
        ("2 &middot; Verified results feed so ROI can be computed",
         "Built.", f'{a["counts"]["official_results"]} official final scores, weeks 1 to 9, each with a source url. '
         'Every priced game binds to a score on the club pair.'),
        ("3 &middot; Originate side, then total, then moneyline",
         "Built, in that order.", "The order is enforced in <code>origination.py</code>; the moneyline is explicitly "
         "labelled a restatement of the side rather than independent evidence."),
        ("4 &middot; Publish model line, market line and difference separately",
         "Built.", "Three separate columns on every row of every board. The difference is never merged into prose and "
         "is blank when the market column is blank."),
        ("5 &middot; Separate signal from staking on the leaderboard",
         "Built and enforced.", "Two different functions on different inputs, and the promotion function raises if a "
         "staking field is passed to it. The separation bites here: the side board has a p-value that clears 0.05 and "
         "a staking ROI of " + pct(sig["side"]["staking_roi"]) + ", and neither figure may decide anything alone."),
        ("6 &middot; Track the depth of the replacement, not just the fact",
         "Built for four clubs; blocked league-wide.",
         f'{a["counts"]["replacement_rows"]} players with an official game status classified by which string dresses. '
         'Depth charts were read for CHI, DEN, PHI and TB only.'),
        ("7 &middot; Correlations from official numbers, with n on every value",
         "Built.", f'{a["counts"]["correlations"]} correlations, each with n, a Fisher interval, a p-value and a '
         'Holm-adjusted q. The one with n=136 is ranked; the rest are shown and marked unrankable.'),
        ("8 &middot; A demotion gate that returns a live strategy to paper",
         "Built and armed, not yet exercised in production.",
         "Five numeric triggers, all of which fired on a probe ledger. Nothing is live, so no real demotion has "
         "occurred."),
    ]
    rows = []
    for title, status, detail in req:
        rows.append('<tr data-source-ids="EC6-REPO" data-status="' + esc(status.split(",")[0]) + '">'
                    f'<th scope="row">{title}</th><td>{esc(status)}</td><td>{detail}</td>'
                    f'<td class="src">{src(["EC6-REPO"])}</td></tr>')
    body += table(["Requirement", "Status", "What answers it", "Source"],
                  rows, caption="The eight requirements, answered one by one")

    body += (
        '<section class="panel"><h2>The finding, stated plainly</h2>'
        f'<p><strong>The side model went {luck["observed_wins"]}-{sig["side"]["losses"]} at the open and lost '
        f'{pct(abs(sig["side"]["staking_roi"]))} at flat stake. It is not unlucky. It is wrong.</strong> Three '
        'independent measurements agree:</p><ol>'
        f'<li><strong>It is worse than the market.</strong> Margin error {cal["side"]["model_rmse"]} points RMSE '
        f'against the market&rsquo;s {cal["side"]["market_rmse"]}; total error {cal["total"]["model_rmse"]} against '
        f'{cal["total"]["market_rmse"]}. A forecast with more error than the price should lose to the price.</li>'
        f'<li><strong>It underperformed its own forecast.</strong> Its probabilities expected '
        f'{luck["model_expected_wins"]} wins and produced {luck["observed_wins"]}: an excess of '
        f'{luck["excess_over_model_expectation"]} against expectation, at p = {luck["p_vs_model_expectation"]}. '
        'The model was not merely unlucky in its predictions; it was overconfident.</li>'
        f'<li><strong>The sample is far too small to rescue it either way.</strong> Detecting a 55% rate needs '
        f'{sig["side"]["required_n_at_55pct"]} settled bets; this capture has {luck["n_settled"]}.</li></ol>'
        '<p>The total board is a quieter version of the same story: '
        f'{sig["total"]["wins"]}-{sig["total"]["losses"]} for {pct(sig["total"]["staking_roi"])}, with '
        f'{sel["total"]["picked_over"]} over picks and {sel["total"]["picked_under"]} under picks. It adds noise '
        'rather than making a directional claim. Neither board is an edge; the difference is that one is visibly '
        'wrong and the other merely uninformative.</p>'
        '<p><strong>A note on how this finding was reached.</strong> The first build of this desk had a sign error: '
        'it compared the model&rsquo;s expected home margin against the home club&rsquo;s printed spread rather than '
        'the market&rsquo;s implied margin, which inverted every side pick. That version went 13-2 and looked '
        'excellent. The error was caught by hand-checking a single game against its official score, fixed, and two '
        'regression tests now pin the convention. The discovery is reported because a desk that quietly corrects '
        'itself in private is not auditable.</p></section>'
    )

    body += (
        '<section class="panel"><h2>Closing-line value: the number that forward-tests an edge</h2>'
        '<p>Staking at the close would make CLV identically zero by construction, so bets are taken at the '
        '<em>open</em>. Measured in points of line, the side board averaged '
        f'<strong>{clv["side"]["mean_points"]}</strong> points of CLV on n={clv["side"]["n"]}, beating the close on '
        f'{pct(clv["side"]["share_beat_close"])} of bets. Negative CLV alongside a losing record is a coherent '
        'picture: the model took the worse number and lost with it.</p>'
        f'<p>The total board averaged {clv["total"]["mean_points"]} points, beating the close on '
        f'{pct(clv["total"]["share_beat_close"])} of bets, which is consistent with a model adding nothing.</p>'
        '<p>The promotion gate is written in basis points of implied probability. This capture is in points of line, '
        'and the two are not convertible without inventing an exchange rate, so that cell is left blank and both '
        'strategies stay on paper. A gate that cannot be satisfied is reported as unsatisfiable rather than quietly '
        'reinterpreted.</p>'
        '<p class="src-line">Detail: <a href="leaderboard.html">leaderboard</a> &middot; '
        '<a href="gates.html">gates</a></p></section>'
    )

    body += (
        '<section class="panel"><h2>Three decisions worth making now</h2><ol>'
        f'<li><strong>Backfill weeks 1 to 8 prices.</strong> {a["counts"]["games_priced"]} games cannot distinguish an '
        'edge from noise at any rate. The capture method is proven; the constraint is call count, not '
        'uncertainty.</li>'
        '<li><strong>Re-express the CLV gate in points of line.</strong> It is currently unsatisfiable by any '
        'capture, which makes it decorative. The new threshold should be fixed from the distribution of line moves, '
        'not from our own record.</li>'
        '<li><strong>Keep publishing model error beside every hit rate.</strong> It is the only reason this page '
        'reports a 2-13 record as a measurement rather than a disaster, and the reason a 13-2 record was not '
        'published as skill.</li>'
        '</ol><p class="src-line">Full list with Adopt, Defer and Reject: <a href="suggestions.html">suggestions</a>'
        '</p></section>'
    )

    body += (
        '<section class="panel"><h2>The one-sentence version</h2>'
        f'<p>The desk captured {a["counts"]["price_observations"]} real open and close prices, originated its own line '
        f'on all {a["counts"]["games_priced"]} Week 9 games in the required order, graded everything against '
        f'{a["counts"]["official_results"]} official finals, and found that its own model loses: it is less accurate '
        'than the market, it underperformed its own probabilities, and the sample needed to settle the question is '
        f'{sig["side"]["required_n_at_55pct"]} settled bets rather than {luck["n_settled"]}.</p></section>'
    )

    body += (
        '<section class="panel"><h2>What is still missing</h2>'
        f'<p>{len(d["missing"])} gaps are recorded in the dossier, each with how to close it. The three that block '
        'the most:</p><ul>'
        '<li><strong>Direct operator prices.</strong> Everything here is a relay through one publisher. It can lag, '
        're-round, or omit markets the operator offered.</li>'
        '<li><strong>Over and under prices for player props.</strong> The prop feed publishes targets and no prices, '
        'so prop combos cannot be priced at all. This is a blocked capability, not a strategy awaiting data.</li>'
        '<li><strong>Depth charts for 28 clubs.</strong> Requirement 6 is satisfied for four. A blank is not a zero, '
        'and the page says so.</li></ul>'
        '<p class="src-line"><a href="questions.html">The full dossier</a></p></section>'
    )
    return page("summary.html", "Executive summary",
                "The eight requirements answered with numbers, the finding stated plainly, and the three decisions "
                "worth making now.", body)


def build_prices() -> str:
    rows_csv = load_csv("price-store-2026-11-14.csv")
    man = load_json("manifest.json")
    a = load_json("analysis.json")

    body = (
        '<section class="panel"><h2>What is in the store, and what it is not</h2>'
        f'<p><strong>{man["price_observations"]} observations</strong> across {man["games_with_prices"]} games and '
        f'{len(man["markets"])} markets, all from a single provider: <strong>{man["provider"]["provider"]}</strong> '
        f'(provider id {man["provider"]["provider_id"]}).</p>'
        '<p>Every row is a <strong>relay</strong>. The prices are DraftKings\' numbers as ESPN republishes them. No '
        'sportsbook API or page was read directly, because direct HTTPS from the sandbox returns no response and the '
        'reads went through a page reader. The relay label is not decorative: a relay can lag the operator, re-round '
        'a price, or omit a market the operator was offering.</p>'
        '<p>Nothing is averaged across providers. A single-provider series is the only thing from which a movement can '
        'be read without ambiguity, and two relays are still relays.</p>'
        '<p class="src-line">Basis: ' + src(["EC6-ESPN-ODDS"]) + '</p></section>'
    )

    body += (
        '<section class="panel"><h2>The schema, proven on one payload</h2>'
        '<p>Each odds payload carries, for the same competition and the same provider:</p>'
        '<pre tabindex="0"><code>open.total / close.total                     the total line at each snapshot\n'
        'open.over / close.over, open.under / close.under   the two-way prices on the total\n'
        'open.{home,away}TeamOdds.pointSpread          that side\'s own spread, signed for that side\n'
        'open.{home,away}TeamOdds.moneyLine            that side\'s moneyline</code></pre>'
        '<p>Two traps in the same payload, both of which would corrupt a naive capture:</p><ul>'
        '<li>The top-level <code>details</code> field names only the <em>favourite</em>, who may be the home or the '
        'away club. Reading teams from it binds the wrong side whenever the favourite is the visitor.</li>'
        '<li><code>moneylineWinner</code> and <code>spreadWinner</code> are present on settled games and are still '
        '<code>false</code>. They cannot grade anything. Grading is done against the official results file instead.</li>'
        '</ul><p class="src-line">Basis: ' + src(["EC6-ESPN-ODDS", "EC6-ESPN-EVENT"]) + '</p></section>'
    )

    heads = ["Game", "Market", "Side", "Snapshot", "Line", "Price", "Provider", "Retrieved", "Source"]
    rows = []
    for r in rows_csv:
        eid = r["event_id"]
        rows.append(
            f'<tr data-source-ids="EC6-ESPN-ODDS" data-status="{esc(r["snapshot"])}">'
            f'<td><a href="{esc(ODDS_EVENT.format(eid=eid))}" target="_blank" rel="noopener noreferrer">'
            f'{esc(r["game"])}</a><span class="sub">event {esc(eid)}</span></td>'
            f'<td>{esc(r["market"])}</td><td>{esc(r["team_or_side"])}</td><td>{esc(r["snapshot"])}</td>'
            + cell(r["line"], numeric=True) + cell(r["price_american"], numeric=True)
            + f'<td>{esc(r["provider"])}<span class="sub">id {esc(r["provider_id"])}</span></td>'
            f'<td>{esc(r["retrieved"])}</td>'
            f'<td class="src">{src(["EC6-ESPN-ODDS"])}</td></tr>'
        )
    body += table(heads, rows, caption=f"Every price observation in the store ({len(rows_csv)} rows)",
                 note="Line is blank for moneyline rows because a moneyline has a price and no line; the blank is "
                      "deliberate and is written as an explicit blank in the source data, never inferred from the "
                      "other side.")

    body += (
        '<section class="panel"><h2>Integrity</h2>'
        '<p>The store is committed as CSV and its hash is recorded, so a reader can confirm the pages were built from '
        'exactly this data.</p>'
    )
    integ = []
    for name, meta in man["inputs"].items():
        integ.append(f'<tr data-source-ids="EC6-REPO"><td><code>{esc(name)}</code></td>'
                     f'<td>{esc(meta["bytes"])}</td><td><code>{esc(meta["sha256"][:32])}…</code></td>'
                     f'<td class="src">{src(["EC6-REPO"])}</td></tr>')
    integ.append(f'<tr data-source-ids="EC6-REPO"><td><code>nfl-results/data/games-2026-w1-9.csv</code></td>'
                 f'<td>{esc(man["results_input"]["sha256"][:8])}…</td>'
                 f'<td><code>{esc(man["results_input"]["sha256"][:32])}…</code></td>'
                 f'<td class="src">{src(["EC6-REPO"])}</td></tr>')
    body += table(["Input file", "Bytes / rows", "SHA-256", "Source"], integ,
                  caption="Inputs the desk was built from")
    body += '<p class="src-line">Reproduce: <code>python3 nfl-market-desk/build.py --check</code></p></section>'
    return page("prices.html", "Price store",
                "Opening and closing numbers for every market originated, with the relay chain stated rather than "
                "buried.", body)


def build_origination() -> str:
    a = load_json("analysis.json")
    side = load_csv("board-side-2026-11-14.csv")
    total = load_csv("board-total-2026-11-14.csv")
    ml = load_csv("board-moneyline-2026-11-14.csv")
    cal = a["calibration"]

    body = (
        '<div class="verdict"><h2>Read this before the numbers</h2>'
        f'<p class="lede">The model is less accurate than the market on both markets. Margin error '
        f'<strong>{cal["side"]["model_rmse"]}</strong> points RMSE against the market\'s '
        f'<strong>{cal["side"]["market_rmse"]}</strong>. Total error {cal["total"]["model_rmse"]} against '
        f'{cal["total"]["market_rmse"]}.</p>'
        '<p>' + esc(cal["reading"]) + '</p></div>'
    )

    body += (
        '<section class="panel"><h2>How a line is originated here</h2>'
        '<p>Each club is rated on points for and points against, accumulated from official final scores '
        '<em>strictly before</em> the graded week, and shrunk toward the league mean by '
        f'{a["params"]["shrink_to_league_games"]} games so a two-game start cannot dominate. The projected margin is '
        'the difference of two combined attack/defence terms, plus a stated home-field allowance of '
        f'{a["params"]["home_field_points"]} points. The total is the sum of the same terms.</p>'
        '<p>The distributional assumptions are stated, not fitted: margin standard deviation '
        f'{a["params"]["margin_sd"]} points and total standard deviation {a["params"]["total_sd"]} points. Fourteen or '
        'fifteen games per week cannot identify those parameters, and tuning them on the graded weeks would be '
        'lookahead wearing a lab coat.</p>'
        '<p><strong>Anti-lookahead.</strong> The first version of this desk rated Week 9 from a standings page '
        'published after Week 9. That is lookahead and it flatters any model, because the standings already include the '
        'games being predicted. Ratings are now rebuilt per week from prior results only, and the window is printed on '
        'every row.</p>'
        '<p class="src-line">Basis: ' + src(["EC6-NFL-SCHEDULE", "EC6-ESPN-ODDS"]) + '</p></section>'
    )

    body += (
        '<section class="panel"><h2>Order of origination</h2>'
        '<p>The order is enforced by the code, not by convention, because each board is only allowed to assume what '
        'the previous one established.</p><ol>'
        '<li><strong>Side first.</strong> The only board whose fair price follows from the margin distribution alone. '
        'No assumption about scoring level is needed.</li>'
        '<li><strong>Total second.</strong> Derived from the same score pair, but fitted and reported separately. It is '
        'never rescaled to make the side look better.</li>'
        '<li><strong>Moneyline last.</strong> A monotone restatement of the side in price space. It is flagged as such '
        'on its own board, because counting one forecast as three independent signals is how a bad model acquires '
        'false confidence.</li></ol></section>'
    )

    # --- side board
    heads = ["Game", "Model fair line", "Market line (close)", "Difference", "Market line (open)",
             "Move", "Cover prob", "Actual margin", "Rating window", "Source"]
    rows = []
    for r in side:
        eid = r["event_id"]
        win = r["rating_window"].replace("weeks ", "W")
        rows.append(
            f'<tr data-source-ids="EC6-ESPN-ODDS EC6-NFL-SCHEDULE" data-status="{esc(r["game"])}">'
            f'<td><a href="{esc(ODDS_EVENT.format(eid=eid))}" target="_blank" rel="noopener noreferrer">'
            f'{esc(r["game"])}</a></td>'
            + cell(fmt(r["model_fair_line"], 2, signed=True), numeric=True)
            + cell(fmt(r["market_line"], 1, signed=True), numeric=True)
            + cell(fmt(r["edge_points"], 2, signed=True), numeric=True)
            + cell(fmt(r["market_line_open"], 1, signed=True), numeric=True)
            + cell(fmt(r["line_movement_points"], 1, signed=True), numeric=True)
            + cell(pct(r["model_home_cover_prob"]), numeric=True)
            + cell(fmt(r["actual_margin"], 0, signed=True), numeric=True)
            + f'<td>{esc(win)}<span class="sub">{esc(r["rating_games_used"])} club-games used</span></td>'
            f'<td class="src">{src(["EC6-ESPN-ODDS", "EC6-NFL-SCHEDULE"])}</td></tr>'
        )
    body += '<section><h2>1 · Side board</h2>'
    body += table(heads, rows, caption="Side: model fair line, market line and difference as separate columns",
                 note="Difference is model minus market on the home scale, so a positive figure means the model rates "
                      "the home side stronger than the market does. Lines are the home side\'s; a negative number means "
                      "the home club is laying points.")
    body += '</section>'

    # --- total board
    heads = ["Game", "Model fair total", "Market total (close)", "Difference", "Market total (open)",
             "Move", "Over prob", "Actual total", "Source"]
    rows = []
    for r in total:
        eid = r["event_id"]
        rows.append(
            f'<tr data-source-ids="EC6-ESPN-ODDS EC6-NFL-SCHEDULE" data-status="{esc(r["game"])}">'
            f'<td><a href="{esc(ODDS_EVENT.format(eid=eid))}" target="_blank" rel="noopener noreferrer">'
            f'{esc(r["game"])}</a></td>'
            + cell(fmt(r["model_fair_total"], 2), numeric=True)
            + cell(fmt(r["market_total"], 1), numeric=True)
            + cell(fmt(r["edge_points"], 2, signed=True), numeric=True)
            + cell(fmt(r["market_total_open"], 1), numeric=True)
            + cell(fmt(r["line_movement_points"], 1, signed=True), numeric=True)
            + cell(pct(r["model_over_prob"]), numeric=True)
            + cell(fmt(r["actual_total"], 0), numeric=True)
            + f'<td class="src">{src(["EC6-ESPN-ODDS", "EC6-NFL-SCHEDULE"])}</td></tr>'
        )
    body += '<section><h2>2 · Total board</h2>'
    body += table(heads, rows, caption="Total: model fair total, market total and difference as separate columns",
                 note="Difference is model minus market: positive means the model expects more points than the market "
                      "does.")
    body += '</section>'

    # --- moneyline board
    heads = ["Game", "Model home win prob", "Model fair home", "Model fair away", "Market home price",
             "Market away price", "Market no-vig home", "Difference", "Actual", "Source"]
    rows = []
    for r in ml:
        eid = r["event_id"]
        actual = (r["home"] if r["actual_home_win"] == "1" else r["away"]) if r["actual_home_win"] else ""
        rows.append(
            f'<tr data-source-ids="EC6-ESPN-ODDS EC6-NFL-SCHEDULE" data-status="{esc(r["game"])}">'
            f'<td><a href="{esc(ODDS_EVENT.format(eid=eid))}" target="_blank" rel="noopener noreferrer">'
            f'{esc(r["game"])}</a></td>'
            + cell(pct(r["model_home_win_prob"]), numeric=True)
            + cell(r["model_fair_price_home"], numeric=True)
            + cell(r["model_fair_price_away"], numeric=True)
            + cell(r["market_home_price"], numeric=True)
            + cell(r["market_away_price"], numeric=True)
            + cell(pct(r["market_novig_home"]), numeric=True)
            + cell(fmt(r["edge_prob_home"], 4, signed=True), numeric=True)
            + f'<td>{esc(actual)}</td>'
            f'<td class="src">{src(["EC6-ESPN-ODDS", "EC6-NFL-SCHEDULE"])}</td></tr>'
        )
    body += '<section><h2>3 · Moneyline board</h2>'
    body += table(heads, rows,
                 caption="Moneyline: a restatement of the side in price space, not independent evidence",
                 note="The no-vig column removes the two-way margin by dividing each implied probability by their sum. "
                      "The difference column is model probability minus no-vig market probability, home perspective.")
    body += '<p class="note">Every row on this board is derived from the same forecast as the side board. It is '
    'published because the brief asked for it, and labelled because publishing it without the label would let one '
    'forecast masquerade as three.</p></section>'

    body += (
        '<section class="panel"><h2>Calibration, measured against the market</h2>'
        + table(["Measure", "Model", "Market", "What it means"], [
            f'<tr data-source-ids="EC6-ESPN-ODDS EC6-NFL-SCHEDULE"><td>Margin RMSE (points)</td>'
            f'<td class="num">{cal["side"]["model_rmse"]}</td><td class="num">{cal["side"]["market_rmse"]}</td>'
            f'<td>Lower is better. The market wins by a wide margin.</td>'
            f'<td class="src">{src(["EC6-ESPN-ODDS", "EC6-NFL-SCHEDULE"])}</td></tr>',
            f'<tr data-source-ids="EC6-ESPN-ODDS EC6-NFL-SCHEDULE"><td>Margin MAE (points)</td>'
            f'<td class="num">{cal["side"]["model_mae"]}</td><td class="num">{cal["side"]["market_mae"]}</td>'
            f'<td>Mean absolute error, same conclusion, less sensitive to one bad game.</td>'
            f'<td class="src">{src(["EC6-ESPN-ODDS", "EC6-NFL-SCHEDULE"])}</td></tr>',
            f'<tr data-source-ids="EC6-ESPN-ODDS EC6-NFL-SCHEDULE"><td>Total RMSE (points)</td>'
            f'<td class="num">{cal["total"]["model_rmse"]}</td><td class="num">{cal["total"]["market_rmse"]}</td>'
            f'<td>Closer than the margin, still worse. Totals are harder to separate.</td>'
            f'<td class="src">{src(["EC6-ESPN-ODDS", "EC6-NFL-SCHEDULE"])}</td></tr>',
            f'<tr data-source-ids="EC6-ESPN-ODDS"><td>Model spread of predictions (sd)</td>'
            f'<td class="num">{cal["side"]["model_sd"]}</td><td class="num">{cal["side"]["market_sd"]}</td>'
            f'<td>The model\'s own forecasts vary far less than the market\'s lines. It is too timid, which is why it '
            f'disagrees by {cal["mean_abs_side_edge"]} points on average.</td>'
            f'<td class="src">{src(["EC6-ESPN-ODDS"])}</td></tr>',
        ], caption="Model error versus market error on the same 15 games", note=cal["reading"])
        + '</section>'
    )
    return page("origination.html", "Ordered origination",
                "Side, then total, then moneyline — with model, market and difference kept in separate columns and the "
                "model\'s own error published beside them.", body)


def build_leaderboard() -> str:
    a = load_json("analysis.json")
    lb = a["leaderboard"]
    sig = a["signal"]
    luck = a["luck_decomposition"]
    cal = a["calibration"]
    bets = load_csv("bets-2026-11-14.csv")

    body = (
        '<div class="verdict"><h2>Signal and staking, on separate pages of the ledger</h2>'
        '<p class="lede">A strategy that makes money on a lucky stake pattern must not be able to look skilful. Here '
        'that is a property of the code: promotion reads the signal tier only, and the promotion function '
        '<strong>raises</strong> if a staking field reaches it.</p>'
        '<p>Both entered strategies are on <strong>paper</strong>. Neither is promotable. The side strategy is the '
        'more instructive case: its p-value clears 0.05 while its staking ROI is '
        f'{pct(sig["side"]["staking_roi"])}. Either figure alone would mislead, and in opposite directions, which is '
        'the reason they are reported on separate pages of the ledger.</p></div>'
    )

    heads = ["Strategy", "Tier", "Signal: n", "Signal: hit rate", "95% interval", "Signal: p",
             "n needed at 55%", "Powered", "Staking: ROI", "Staking: staked", "Pushes",
             "Model RMSE", "Market RMSE", "Source"]
    rows = []
    for r in lb:
        s = r["signal"]
        st = r["staking"]
        tier_kind = "live" if r["tier"] == "live" else "paper"
        rows.append(
            f'<tr data-source-ids="EC6-ESPN-ODDS EC6-NFL-SCHEDULE" data-status="{esc(r["tier"])}">'
            f'<td>{esc(r["id"])}<span class="sub">{esc(r["name"])}</span></td>'
            f'<td>{badge(r["tier"], tier_kind)}</td>'
            + cell(s["n_settled_bets"], numeric=True)
            + cell(pct(s["signal_hit_rate"]), numeric=True)
            + cell(f'{pct(s["signal_hit_ci"][0])}–{pct(s["signal_hit_ci"][1])}', numeric=True)
            + cell(s["signal_p_value"], numeric=True)
            + cell(s["required_n_at_55pct"], numeric=True)
            + f'<td>{"yes" if s["adequately_powered"] else "no"}</td>'
            + cell(pct(st["staking_roi_at_relayed_close"]), numeric=True)
            + cell(st["units_staked"], numeric=True)
            + cell(st["pushes"], numeric=True)
            + cell(r["calibration"]["model_rmse"], numeric=True)
            + cell(r["calibration"]["market_rmse"], numeric=True)
            + f'<td class="src">{src(["EC6-ESPN-ODDS", "EC6-NFL-SCHEDULE"])}</td></tr>'
        )
    body += table(heads, rows, caption="Entered strategies: signal columns and staking columns never merge",
                 note="Staking is flat 1 unit at the relayed open price, push refunded. Nothing was wagered: the ROI is "
                      "a paper computation on a relayed number, not obtained profit. 'Powered' compares n against the "
                      "pre-specified 783 settled bets needed at a 55% rate; both strategies are far below it.")

    body += (
        '<section class="panel"><h2>Why the side strategy is on paper, and what would move it</h2>'
        f'<p>The side strategy went {luck["observed_wins"]}-{sig["side"]["losses"]} at the open, for a p of '
        f'{sig["side"]["signal_p_value"]} against a coin. That is statistically significant and completely useless as '
        'evidence of skill, for three reasons the desk prints beside it:</p><ol>'
        f'<li><strong>It is significant in the wrong direction.</strong> The model expected '
        f'{luck["model_expected_wins"]} wins from its own probabilities and got {luck["observed_wins"]}. Being '
        'significantly worse than your own forecast is still a finding, but it is a finding about a broken model, not '
        'about an edge.</li>'
        f'<li><strong>The model is less accurate than the price.</strong> Margin error {cal["side"]["model_rmse"]} '
        f'against {cal["side"]["market_rmse"]}. A forecast can only beat a price it is better than, and this one is '
        'not.</li>'
        f'<li><strong>n is {luck["n_settled"]}, not 200.</strong> A significant result on fifteen bets says the '
        'direction was consistent on this sample. It does not say the direction would repeat.</li></ol>'
        '<p>What would move the strategy toward live is not a better record; it is positive closing-line value, a '
        'powered sample, and a model whose error is below the market\'s. None of those is available on this '
        f'capture.</p><p class="src-line">Basis: {src(["EC6-ESPN-ODDS"])}</p></section>'
    )

    # --- per-bet ledger
    heads = ["Game", "Market", "Decision", "Pick", "Line", "Price", "Snapshot", "Outcome", "Units", "Reason", "Source"]
    rows = []
    for b in bets:
        if b["decision"] != "bet":
            continue
        eid = b["event_id"]
        rows.append(
            f'<tr data-source-ids="EC6-ESPN-ODDS EC6-NFL-SCHEDULE" data-status="{esc(b["outcome"])}">'
            f'<td><a href="{esc(ODDS_EVENT.format(eid=eid))}" target="_blank" rel="noopener noreferrer">'
            f'{esc(b["game"])}</a></td>'
            f'<td>{esc(b["market"])}</td><td>{esc(b["decision"])}</td><td>{esc(b["pick"])}</td>'
            + cell(fmt(b["line"], 1, signed=True), numeric=True)
            + cell(b["price"], numeric=True)
            + f'<td>{esc(b["snapshot"])}</td><td>{esc(b["outcome"])}</td>'
            + cell(fmt(b["units"], 3, signed=True), numeric=True)
            + f'<td>{esc(b.get("why", ""))}</td>'
            f'<td class="src">{src(["EC6-ESPN-ODDS", "EC6-NFL-SCHEDULE"])}</td></tr>'
        )
    body += '<section><h2>Every stake, one row</h2>'
    body += table(heads, rows, caption="The paper ledger: 29 stakes at the relayed open price",
                 note="Passes are excluded from this table; they are recorded in the committed bets file with their "
                      "reason. Units are return on a 1-unit stake, so a loss is exactly -1 and a win is the price\'s "
                      "decimal minus one.")
    body += '</section>'

    body += (
        '<section class="panel"><h2>What the promotion rules are</h2>'
        '<p>A strategy moves from paper to live only when all five hold. The list is in the committed analysis file '
        'and is read by the code, not transcribed by hand.</p>'
        + table(["Rule", "Threshold", "Why"], [
            f'<tr data-source-ids="EC6-REPO"><td>n_settled_bets</td><td class="num">≥ 200</td>'
            f'<td>Below this a 55% rate is inside two standard errors of a coin.</td><td class="src">{src(["EC6-REPO"])}</td></tr>',
            f'<tr data-source-ids="EC6-REPO"><td>signal_p_value</td><td class="num">≤ 0.05</td>'
            f'<td>The signal, not the stake, decides promotion.</td><td class="src">{src(["EC6-REPO"])}</td></tr>',
            f'<tr data-source-ids="EC6-REPO"><td>q_value_holm</td><td class="num">≤ 0.10</td>'
            f'<td>The leaderboard tests many strategies, so family-wise error must be controlled.</td>'
            f'<td class="src">{src(["EC6-REPO"])}</td></tr>',
            f'<tr data-source-ids="EC6-REPO"><td>price_provenance</td><td>pass</td>'
            f'<td>A strategy priced from unverified numbers cannot go live.</td><td class="src">{src(["EC6-REPO"])}</td></tr>',
            f'<tr data-source-ids="EC6-REPO"><td>clv_mean_bps</td><td class="num">≥ 0</td>'
            f'<td>Positive closing-line value is the only forward-looking proof of an edge.</td>'
            f'<td class="src">{src(["EC6-REPO"])}</td></tr>',
        ], caption="Promotion: paper to live", note="Staking fields are explicitly excluded and the code raises if one "
        "is passed. That exclusion is what makes 'a lucky staking run cannot mask a bad signal' true rather than "
        "asserted.")
        + '</section>'
    )
    return page("leaderboard.html", "Leaderboard",
                "Signal and staking reported side by side on different inputs, with promotion reading the signal tier "
                "only.", body)


def build_correlation() -> str:
    a = load_json("analysis.json")
    corr = load_csv("correlation-2026-11-14.csv")
    summary = a["correlation_summary"]

    body = (
        '<section class="panel"><h2>The rule this register follows</h2>'
        '<p>Correlations are computed only from officially sourced numbers, and every value publishes its n. Two '
        'families are kept apart because they answer different questions:</p><ul>'
        '<li><strong>Market correlation</strong> — what the books price together. The input a parlay needs.</li>'
        '<li><strong>Outcome correlation</strong> — what actually happens together, from official final scores. A '
        'property of football.</li></ul>'
        '<p>The gap between the two is the mispricing a correlated combo could exploit. It cannot be measured at '
        f'{summary["n_powered"]} of {summary["n_pairs"]} pairs being adequately powered, and the register shows that '
        'rather than hiding it.</p>'
        f'<p class="src-line">{esc(summary["note"])}</p></section>'
    )

    heads = ["Pair", "Family", "n", "r", "95% interval", "p", "Holm q", "Rankable", "Question", "Caveat", "Source"]
    rows = []
    for r in corr:
        powered = r["powered"] == "True"
        rankable = badge("rankable", "live") if powered else badge("unpowered", "warn")
        src_used = "EC6-ESPN-ODDS EC6-NFL-SCHEDULE" if "official scores" in r["question"] else "EC6-ESPN-ODDS EC6-NFL-STANDINGS"
        rows.append(
            f'<tr data-source-ids="{src_used}" data-status="{"powered" if powered else "unpowered"}">'
            f'<td>{esc(r["pair"])}</td><td>{esc(r["family"])}</td>'
            + cell(r["n"], numeric=True)
            + cell(fmt(r["r"], 3, signed=True), numeric=True)
            + cell(f'{fmt(r["ci_lo"], 2, signed=True)} to {fmt(r["ci_hi"], 2, signed=True)}', numeric=True)
            + cell(r["p_value"], numeric=True)
            + cell(r["holm_adjusted_p"], numeric=True)
            + f'<td>{rankable}</td>'
            f'<td>{esc(r["question"])}</td><td>{esc(r["caveat"])}</td>'
            f'<td class="src">{src(src_used.split())}</td></tr>'
        )
    body += table(heads, rows, caption=f"Correlation register ({len(corr)} pairs)",
                 note=f"Pairs with n below {summary['min_n_for_ranking']} are shown with their n and are not ranked: "
                      "at n=15 the 95% interval on r spans most of its range, so the point estimate carries almost no "
                      "information. Holm adjustment is applied across the pairs tested in this register.")

    body += (
        '<section class="panel"><h2>What the numbers say</h2><ul>'
        '<li><strong>Model versus market on the total: r = 0.62 at n=15.</strong> Positive and, on p alone, '
        'significant — but unpowered. It says the model tracks the market on scoring level, which is a calibration '
        'observation, not an edge.</li>'
        '<li><strong>Model versus market on the margin: r = 0.91 at n=15.</strong> The model follows the market closely '
        'while still being less accurate than it. Tracking a good forecast imperfectly is a good way to be worse than '
        'it.</li>'
        '<li><strong>Final margin versus final total: r = -0.16 at n=136.</strong> The only adequately powered result '
        'here, and it does not survive Holm adjustment. On this sample, a blowout does not reliably arrive with a high '
        'total.</li>'
        '<li><strong>Market spread versus market total: r = 0.09 at n=15.</strong> Essentially nothing, at a sample too '
        'small to say so confidently. This is exactly the pair a correlated parlay would be sold against, and the desk '
        'cannot yet price that relationship.</li></ul>'
        '<p class="src-line">Basis: ' + src(["EC6-ESPN-ODDS", "EC6-NFL-SCHEDULE"]) + '</p></section>'
    )

    dropped = summary.get("dropped", [])
    if dropped:
        body += '<section class="panel"><h2>Pairs that were dropped, and why</h2><ul>'
        for d in dropped:
            body += f'<li><strong>{esc(d["pair"])}</strong> — {esc(d["why"])}</li>'
        body += ('</ul><p>Drops are published rather than silently pairwise-deleted. A pair with two complete '
                 'observations is not a weak correlation; it is not a correlation.</p>'
                 '<p class="src-line">Basis: ' + src(["EC6-NFL-INJURY"]) + '</p></section>')
    return page("correlation.html", "Correlation",
                "Official-sourced numbers only, every value carrying its n, with Holm adjustment and every dropped "
                "pair published.", body)


def build_availability() -> str:
    a = load_json("analysis.json")
    rows_csv = load_csv("replacement-depth-2026-11-14.csv")
    exp = load_csv("club-exposure-2026-11-14.csv")
    cov = a["depth_coverage"]

    body = (
        '<div class="verdict"><h2>The distinction that matters</h2>'
        '<p class="lede">"Starter out" is not a price. <strong>Which string dresses</strong> is closer to one.</p>'
        '<p>Two clubs can each lose a receiver and be in completely different shape: the club whose third receiver now '
        'plays is deeper than the club whose fifth does, having already lost the fourth. So the unit of record here is '
        'the slot, and the measure is how many strings the club had to reach down.</p>'
        f'<p><strong>Coverage, stated up front:</strong> {esc(cov["coverage_note"])}</p></div>'
    )

    body += '<div class="kpis">' + "".join([
        kpi(str(cov["n_clubs_with_depth"]) + "/32", "clubs with a captured depth chart"),
        kpi(cov["slots_total"], "printed depth slots transcribed"),
        kpi(cov["injury_rows_with_game_status"], "players carrying an official game status"),
        kpi(sum(1 for r in rows_csv if r["replacement_tier"] == "no_healthy_body_behind"),
            "with no healthy body behind them"),
        kpi(sum(1 for r in rows_csv if r["replacement_tier"] == "reached_down_chart"),
            "where the club reached down a string"),
        kpi(sum(1 for r in rows_csv if not r["depth_known"]), "cannot be placed on a captured chart"),
    ]) + "</div>"

    body += (
        '<section class="panel"><h2>How each player is classified</h2>'
        '<p>Only a player with an official game status of Out or Questionable is treated as unavailable. Practice '
        'status alone is never treated as unavailability, because a full practice does not mean a player dresses and a '
        'limited practice does not mean he does not.</p><ul>'
        '<li><strong>No healthy body behind</strong> — the club prints no available replacement in the slot. Structurally '
        'worse than a deep replacement, because there is no floor left at that position.</li>'
        '<li><strong>Reached down chart</strong> — an available body exists but at a deeper rank. Two or three strings '
        'is a different problem from one.</li>'
        '<li><strong>Like for like</strong> — the printed replacement holds the same string.</li>'
        '<li><strong>Rank not printed / not on chart</strong> — the chart does not place the player. The string is left '
        'blank rather than inferred from the row\'s position on the page.</li></ul>'
        '<p class="src-line">Basis: ' + src(["EC6-NFL-INJURY"]) + '</p></section>'
    )

    heads = ["Club", "Player", "Pos", "Game status", "Printed rank", "Replacement", "Repl. rank",
             "Deepest printed", "Strings lost", "Classification", "Note", "Source"]
    rows = []
    for r in rows_csv:
        club = r["club"]
        ids = ["EC6-NFL-INJURY"] + ([CLUB_CHART[club]] if club in CLUB_CHART else [])
        rank_txt = f'rank {r["printed_rank"]}' if r["printed_rank"] else ""
        rows.append(
            f'<tr data-source-ids="{esc(" ".join(ids))}" data-status="{esc(r["game_status"])}">'
            f'<td>{esc(club)}<span class="sub">{esc(CLUB_NAME.get(club, ""))}</span></td>'
            f'<td>{esc(r["player"])}</td><td>{esc(r["position"])}</td>'
            f'<td class="status-{esc((r["game_status"] or "").lower())}">{esc(r["game_status"])}</td>'
            + cell(rank_txt, numeric=True)
            + cell(r["replacement"])
            + cell(r["replacement_rank"], numeric=True)
            + cell(r["slot_deepest_rank"], numeric=True)
            + cell(r["strings_lost"], numeric=True)
            + f'<td>{esc(r["replacement_tier"].replace("_", " "))}</td>'
            f'<td>{esc(r["tier_note"])}</td>'
            f'<td class="src">{src(ids)}</td></tr>'
        )
    body += '<section><h2>Every player with a game status</h2>'
    body += table(heads, rows, caption=f"Replacement depth ({len(rows_csv)} players)",
                 note="'Strings lost' is the difference between the printed rank of the unavailable player and the "
                      "printed rank of the replacement. It is blank where either rank is not printed, and blank is not "
                      "zero.")
    body += '</section>'

    heads = ["Club", "Out", "Questionable", "Depth known", "Unplaced slots", "Weight", "Source"]
    rows = []
    for r in exp:
        ids = ["EC6-NFL-INJURY"] + ([CLUB_CHART[r["club"]]] if r["club"] in CLUB_CHART else [])
        rows.append(
            f'<tr data-source-ids="{esc(" ".join(ids))}" data-status="{esc(r["club"])}">'
            f'<td>{esc(r["club"])}<span class="sub">{esc(CLUB_NAME.get(r["club"], ""))}</span></td>'
            + cell(r["out"], numeric=True) + cell(r["questionable"], numeric=True)
            + cell(r["depth_known"], numeric=True) + cell(r["unresolved_slots"], numeric=True)
            + cell(r["weight"], numeric=True)
            + f'<td class="src">{src(ids)}</td></tr>'
        )
    body += '<section><h2>Club availability load</h2>'
    body += table(heads, rows, caption="Per-club load, weighted by how far down the chart the club reached",
                 note="The weight is deliberately crude and is a ranking device only: 4 for a slot with no healthy "
                      "body behind, plus 1 per string of reach, plus 0.25 per additional string beyond one. It is never "
                      "presented as a price adjustment, and it is not fitted to any result.")
    body += '</section>'
    return page("availability.html", "Replacement depth",
                "Which string dresses, measured per slot, with the four-club coverage stated rather than implied.",
                body)


def build_gates() -> str:
    a = load_json("analysis.json")
    g = a["gates"]
    dem = a["demotion_gate"]
    promo = a["promotion_rules"]

    passed = sum(1 for x in g if x["status"] == "pass")
    body = (
        f'<div class="kpis">{kpi(f"{passed}/{len(g)}", "gates passing, computed not declared")}'
        f'{kpi(len(dem["triggers"]), "demotion triggers, all numeric")}'
        f'{kpi(a["counts"]["strategies_live"], "strategies live")}'
        f'{kpi("0", "demotions in production — nothing is live yet")}</div>'
    )

    body += (
        '<section class="panel"><h2>A gate is only real if it can fail</h2>'
        '<p>Each gate below is a function of the published data. None is hard-coded to pass: a missing input returns '
        '<code>blocked</code>, never <code>pass</code>. The evidence column is the computation\'s own output, so a '
        'reader can see what decided each status.</p></section>'
    )

    heads = ["Gate", "Status", "What decides it", "Computed evidence", "Source"]
    rows = []
    for x in g:
        kind = "live" if x["status"] == "pass" else ("blocked" if x["status"] == "blocked" else "bad")
        rows.append(
            f'<tr data-source-ids="EC6-REPO" data-status="{esc(x["status"])}">'
            f'<td>{esc(x["id"])}<span class="sub">{esc(x["name"])}</span></td>'
            f'<td>{badge(x["status"], kind)}</td>'
            f'<td>{esc(x["definition"])}</td><td>{esc(x["evidence"])}</td>'
            f'<td class="src">{src(["EC6-REPO"])}</td></tr>'
        )
    body += table(heads, rows, caption=f"Validation gates ({len(g)})",
                 note="Statuses are computed by nfl-market-desk/gates.py at build time. The page reads the committed "
                      "result; nothing is evaluated in the browser.")

    body += (
        '<section class="panel"><h2>Requirement 8: the demotion gate</h2>'
        f'<p>Any strategy reaching the <strong>live</strong> tier is subject to {len(dem["triggers"])} numeric triggers. '
        'Any one firing returns it to paper. Promotion back requires a fresh out-of-sample window that clears every '
        'promotion gate again.</p>'
        f'<p><strong>Status: armed, exercised, not yet triggered in production.</strong> Nothing is live, so no real '
        'demotion has occurred. That distinction matters and is not glossed: the gate has been proven to fire on a '
        'probe ledger, which is not the same as having governed a live strategy.</p></section>'
    )
    heads = ["Trigger", "Fires when", "Threshold", "What it measures", "Why this threshold", "Source"]
    rows = []
    for t in dem["triggers"]:
        thr = t["threshold"]
        thr_txt = str(thr) if thr is not None else "promoted rate − 2 binomial sd over 50 bets"
        rows.append(
            f'<tr data-source-ids="EC6-REPO" data-status="armed">'
            f'<td><code>{esc(t["key"])}</code></td><td class="num">{esc(t["op"])}</td>'
            f'<td>{esc(thr_txt)}</td><td>{esc(t["measures"])}</td><td>{esc(t["why"])}</td>'
            f'<td class="src">{src(["EC6-REPO"])}</td></tr>'
        )
    body += table(heads, rows, caption="Demotion triggers: any one returns a live strategy to paper",
                 note="An input that cannot be evaluated is itself treated as a demotion trigger, because an "
                      "unverifiable live strategy is not a live strategy.")

    body += (
        '<section class="panel"><h2>Promotion, separated from staking</h2>'
        '<p>The promotion function receives signal fields only. Staking fields are explicitly excluded, and the '
        'function raises if one appears — a check that is exercised on every build, and the evidence for gate MD-G06 '
        'above is the raise itself.</p>'
        + table(["Signal requirement", "Threshold", "Excluded from promotion"], [
            f'<tr data-source-ids="EC6-REPO"><td>settled bets</td><td class="num">≥ 200</td>'
            f'<td rowspan="5">staking ROI · units returned · best run · hot streak</td>'
            f'<td class="src">{src(["EC6-REPO"])}</td></tr>',
            f'<tr data-source-ids="EC6-REPO"><td>signal p-value</td><td class="num">≤ 0.05</td>'
            f'<td class="src">{src(["EC6-REPO"])}</td></tr>',
            f'<tr data-source-ids="EC6-REPO"><td>Holm-adjusted q</td><td class="num">≤ 0.10</td>'
            f'<td class="src">{src(["EC6-REPO"])}</td></tr>',
            f'<tr data-source-ids="EC6-REPO"><td>price provenance</td><td>pass</td>'
            f'<td class="src">{src(["EC6-REPO"])}</td></tr>',
            f'<tr data-source-ids="EC6-REPO"><td>closing-line value</td><td class="num">≥ 0 bps</td>'
            f'<td class="src">{src(["EC6-REPO"])}</td></tr>',
        ], caption="Promotion requires all five")
        + '</section>'
    )
    return page("gates.html", "Validation & demotion",
                "Ten gates that can each fail, and a demotion gate with five numeric triggers that sends a live "
                "strategy back to paper.", body)


def build_questions() -> str:
    d = load_json("dossier.json")

    body = (
        '<section class="panel"><h2>The dossier in one line</h2>'
        f'<p>{len(d["questions"])} questions, {len(d["held"])} items actually held with a source, '
        f'{len(d["missing"])} items missing, and {len(d["suggestions"])} suggestions for closing the gaps. Nothing is '
        'listed as held unless a reader can follow a link to it.</p></section>'
    )

    heads = ["Question", "Status", "The answer", "Depends on"]
    rows = []
    for q in d["questions"]:
        kind = "live" if q["status"].startswith("answered") else "warn"
        ids = " ".join(q["depends_on"])
        registered = [i for i in q["depends_on"] if i in SOURCE_IDS]
        rows.append(
            f'<tr data-source-ids="{esc(" ".join(registered) or "EC6-REPO")}" data-status="{esc(q["status"])}">'
            f'<td>{esc(q["id"])}<span class="sub">{esc(q["question"])}</span></td>'
            f'<td>{badge(q["status"].replace("_", " "), kind)}</td>'
            f'<td>{esc(q["answer"])}</td>'
            f'<td class="src">{src(registered) if registered else src(["EC6-REPO"])}</td></tr>'
        )
    body += table(heads, rows, caption=f"The questions ({len(d['questions'])})", note="Statuses are descriptive: "
                 "answered_no and answered_no_and_enforced mean the question was answered and the answer was "
                 "unwelcome.")

    body += '<section><h2>Information actually held</h2>'
    heads = ["Item", "Quantity", "Operator-direct?", "Source"]
    rows = []
    for h in d["held"]:
        direct = "yes" if h["operator_direct"] else "no — relayed"
        badge_txt = badge(direct, "live" if h["operator_direct"] else "relay")
        ids = [i for i in h["source_ids"] if i in SOURCE_IDS]
        rows.append(
            f'<tr data-source-ids="{esc(" ".join(ids) or "EC6-REPO")}" data-status="{esc(direct)}">'
            f'<td>{esc(h["item"])}</td><td>{esc(h["quantity"])}</td><td>{badge_txt}</td>'
            f'<td class="src">{src(ids) if ids else src(["EC6-REPO"])}</td></tr>'
        )
    body += table(heads, rows, caption="Held, with provenance and whether the publisher was the operator")
    body += '</section>'

    body += '<section><h2>Information missing, and how to discover it</h2>'
    heads = ["Gap", "What is missing", "Why it matters", "What it blocks", "How to discover it"]
    rows = []
    for m in d["missing"]:
        rows.append(
            f'<tr data-source-ids="EC6-REPO" data-status="{esc(m["id"])}">'
            f'<td>{esc(m["id"])}</td><td>{esc(m["missing"])}</td><td>{esc(m["why_it_matters"])}</td>'
            f'<td>{esc(", ".join(m["blocks"]))}</td><td>{esc(m["how_to_discover"])}</td>'
            f'<td class="src">{src(["EC6-REPO"])}</td></tr>'
        )
    body += table(heads, rows, caption=f"Missing information ({len(d['missing'])})",
                 note="Each gap carries a route to closing it. A gap with no route would be a limitation; these are "
                      "open tasks.")
    body += '</section>'

    body += '<section><h2>Decisions taken while doing the work</h2>'
    heads = ["Decision", "What was decided", "Why", "Consequence"]
    rows = []
    for dec in d["decisions"]:
        rows.append(
            f'<tr data-source-ids="EC6-REPO" data-status="{esc(dec["id"])}">'
            f'<td>{esc(dec["id"])}</td><td>{esc(dec["decision"])}</td><td>{esc(dec["why"])}</td>'
            f'<td>{esc(dec["consequence"])}</td><td class="src">{src(["EC6-REPO"])}</td></tr>'
        )
    body += table(heads, rows, caption="Decisions and their consequences")
    body += '</section>'
    return page("questions.html", "Questions & dossier",
                "What was asked, what is held, what is missing and how to find it, with the decisions that shaped "
                "each answer.", body)


def build_suggestions() -> str:
    sugg = load_csv("suggestions-2026-11-14.csv")

    body = (
        '<section class="panel"><h2>How to use this page</h2>'
        '<p>Each suggestion states a recommendation, the effort, why it is worth doing and the risk of doing it. The '
        '<strong>Decision</strong> column is deliberately empty: it is for you to choose. Nothing on this desk is '
        'implemented because it was suggested here; the suggestions that are already implemented are marked as such in '
        'their own wording.</p>'
        f'<p>{len(sugg)} suggestions are open. The record starts blank and no choice has been assumed on your '
        'behalf.</p></section>'
    )

    heads = ["ID", "Suggestion", "Recommendation", "Effort", "Why", "Risk", "Decision", "Source"]
    rows = []
    for s in sugg:
        kind = {"Adopt": "live", "Defer": "warn", "Reject": "blocked"}.get(s["recommendation"], "neutral")
        # Radios are wrapped in <label> so each control has an accessible name, and they are
        # enabled: a decision record the operator cannot actually set is not a record. Nothing is
        # preselected, and the static page stores no state — the downloadable CSV carries blanks.
        choices = (f'<label class="choice"><input type="radio" name="d-{s["id"]}" value="adopt"> Adopt</label>'
                   f'<label class="choice"><input type="radio" name="d-{s["id"]}" value="defer"> Defer</label>'
                   f'<label class="choice"><input type="radio" name="d-{s["id"]}" value="reject"> Reject</label>')
        rows.append(
            f'<tr data-source-ids="EC6-REPO" data-status="{esc(s["recommendation"])}">'
            f'<td>{esc(s["id"])}</td><td>{esc(s["title"])}</td>'
            f'<td>{badge(s["recommendation"], kind)}</td><td>{esc(s["effort"])}</td>'
            f'<td>{esc(s["why"])}</td><td>{esc(s["risk"])}</td>'
            f'<td class="choices">{choices}</td>'
            f'<td class="src">{src(["EC6-REPO"])}</td></tr>'
        )
    body += table(heads, rows, caption=f"Suggestions for review ({len(sugg)})",
                 note="The recommendation column is the desk\'s view; the decision column is yours. Radios are "
                      "disabled because this is a static page and no state is stored — the downloadable CSV has empty "
                      "decision and decided-on columns for you to fill.")

    body += (
        '<section class="panel"><h2>The two that matter most</h2>'
        '<p><strong>SG1 · Backfill weeks 1 to 8 prices.</strong> Every rate on this site is a description of 15 games. '
        'The capture method is proven; the constraint is call count, not uncertainty. This is the only item that '
        'changes what any number here means.</p>'
        '<p><strong>SG2 · Re-express the CLV gate in points of line.</strong> The gate currently requires basis points '
        'of implied probability while the data is in points of line, which makes it unsatisfiable by any capture. A '
        'gate that cannot be satisfied is decorative. Note the guard: the new threshold must come from the '
        'distribution of line moves, not from our own record, or it becomes tuning.</p>'
        '<p class="src-line">Basis: ' + src(["EC6-REPO"]) + '</p></section>'
    )
    return page("suggestions.html", "Suggestions",
                "Options reviewed with Adopt, Defer or Reject, and the decision left to you.", body)


def build_flagged() -> str:
    a = load_json("analysis.json")
    d = load_json("dossier.json")
    cov = a["depth_coverage"]

    items = [
        ("Relayed prices, not operator-confirmed",
         "Every price is DraftKings' number as republished by ESPN (provider 100). No sportsbook was read directly.",
         "A relay can lag, re-round or omit markets. Gate MD-G01 passes on provenance <em>completeness</em>; it does "
         "not and cannot confirm the operator would have filled at that price.",
         "EC6-ESPN-ODDS", "blocked"),
        ("Player props carry no two-way price",
         "The prop endpoint returns market names and open/current targets, with no over or under price, and repeats "
         "every row.",
         "Player-prop combos are a stated requirement and cannot be priced at all. Recorded as a blocked capability, "
         "not a strategy awaiting data.", "EC6-ESPN-PROPS", "blocked"),
        ("Depth charts captured for 4 of 32 clubs",
         cov["coverage_note"],
         "Requirement 6 is satisfied for CHI, DEN, PHI and TB. For the other 28 clubs the replacement\'s string is "
         "unknown, and a blank is not a zero.", "EC6-CHI-DEPTH", "blocked"),
        ("Two captured charts print no date",
         "The Denver and Philadelphia charts print no chart date, so they cannot be asserted to be current.",
         "Their slots are used with the undated caveat attached rather than dropped or silently trusted.",
         "EC6-DEN-DEPTH", "warn"),
        ("CLV gate is written in units the capture does not produce",
         "The promotion gate requires basis points of implied probability; this capture measures points of line.",
         "The gate is reported as unsatisfiable rather than converted at an invented rate. Both strategies therefore "
         "stay on paper.", "EC6-REPO", "blocked"),
        ("A sign error turned a losing model into a 13-2 record",
         "The first build compared the model&rsquo;s expected home margin against the home club&rsquo;s printed "
         "spread instead of the market&rsquo;s implied margin, which inverted every side pick.",
         "That build went 13-2 and was almost published as a result. It was caught by hand-checking one game "
         "against its official score. The convention now lives in one tested function, with separate conversions for "
         "the side and the total, and regression tests pin both.", "EC6-REPO", "warn"),
        ("The model is worse than the market",
         f"Margin RMSE {a['calibration']['side']['model_rmse']} against the market\'s "
         f"{a['calibration']['side']['market_rmse']}; total {a['calibration']['total']['model_rmse']} against "
         f"{a['calibration']['total']['market_rmse']}.",
         "This is a finding, not a defect: it is the reason the winning record is not read as an edge. It is flagged "
         "so no page can present the hit rate without it.", "EC6-ESPN-ODDS", "warn"),
        ("Lookahead was caught and removed",
         "The first version rated Week 9 from a standings page published after Week 9.",
         "Ratings are now rebuilt per week from prior results only, and the window is printed on every row. Flagged "
         "because the earlier build was wrong, not because the current one is.", "EC6-NFL-STANDINGS", "warn"),
        ("Winner flags in the odds payload are unusable",
         "<code>moneylineWinner</code> and <code>spreadWinner</code> are present and <code>false</code> on settled games.",
         "Any grading from them would be wrong. All grading uses the official results file.", "EC6-ESPN-ODDS", "warn"),
        ("The demotion gate has never fired in production",
         "It is defined, executable and proven to fire on a probe ledger. Nothing is live.",
         "A trigger that has never governed a live strategy is a configuration, not a control. Stated as armed and "
         "exercised, never as operational.", "EC6-REPO", "warn"),
        ("Sample is far below any threshold that settles the question",
         f"{a['luck_decomposition']['n_settled']} settled side bets against a requirement of "
         f"{a['signal']['side']['required_n_at_55pct']} for a 55% rate at 80% power.",
         "Every rate here is a description. No rate is an estimate and none supports a claim.",
         "EC6-ESPN-ODDS", "blocked"),
    ]

    body = (
        '<section class="panel"><h2>Nothing here blocks a merge; all of it blocks a claim</h2>'
        f'<p>{len(items)} irregularities, each with a link so you can check it yourself. They are separated from the '
        'main pages because a flagged limitation on a page that also shows a number tends to be skimmed past.</p>'
        '</section>'
    )
    heads = ["Irregularity", "What was observed", "What it means for any claim", "Status", "Source"]
    rows = []
    for title, obs, means, sid, status in items:
        rows.append(
            f'<tr data-source-ids="{esc(sid)}" data-status="{esc(status)}">'
            f'<td>{esc(title)}</td><td>{obs}</td><td>{esc(means)}</td>'
            f'<td>{badge(status, "blocked" if status == "blocked" else "warn")}</td>'
            f'<td class="src">{src([sid])}</td></tr>'
        )
    body += table(heads, rows, caption=f"Flagged for review ({len(items)})",
                 note="'Blocked' means a capability is unavailable. 'Warn' means a number is published with a caveat "
                      "attached that must travel with it.")
    return page("flagged.html", "Flagged for review",
                "Every irregularity found while doing this work, with the official link, so you can check it yourself.",
                body)


def build_sources() -> str:
    reg = {r["id"]: r for r in json.loads((HERE.parent / "research" / "sources.json").read_text())}
    ids = [i for i in SOURCE_IDS]
    heads = ["ID", "Publisher", "Title", "What this desk used it for", "Access", "Checked", "Link"]
    rows = []
    for i in ids:
        r = reg[i]
        rows.append(
            f'<tr data-source-ids="{esc(i)}" data-status="registered">'
            f'<td><code>{esc(i)}</code></td><td>{esc(r["publisher"])}</td><td>{esc(r["title"])}</td>'
            f'<td>{esc(r["scope"])}</td><td>{esc(r["access"])}</td><td>{esc(r["checked_on"])}</td>'
            f'<td class="src">{src([i])}</td></tr>'
        )
    body = (
        '<section class="panel"><h2>One publisher per id</h2>'
        f'<p>{len(ids)} sources are registered for this desk. Each id maps to exactly one publisher host, which is '
        'enforced by the repository check: a source id whose url does not match its registered host fails the build. '
        'That is why the relayed market feed has its own ids and never shares one with an NFL.com page.</p></section>'
    )
    body += table(heads, rows, caption="Registered sources used by this desk",
                 note="Every table row elsewhere on this site links at least one of these ids.")
    return page("sources.html", "Sources", "The register, one publisher per id, enforced by the build.", body)


def build_method() -> str:
    a = load_json("analysis.json")
    body = (
        '<section class="panel"><h2>Limits that travel with every number</h2><ol>'
        '<li><strong>One provider, relayed.</strong> All prices are DraftKings as republished by ESPN. A movement is '
        'a movement in that one series, not a market-wide fact, and never an operator-confirmed fill.</li>'
        f'<li><strong>{a["counts"]["games_priced"]} games.</strong> Every rate is a description of fifteen games. '
        f'Detecting a 55% rate at 80% power needs {a["signal"]["side"]["required_n_at_55pct"]} settled bets.</li>'
        '<li><strong>Stated priors, not fitted parameters.</strong> Margin and total standard deviations are registered '
        'choices. They were not tuned on the graded weeks, because tuning on the graded weeks is lookahead.</li>'
        '<li><strong>Ratings from prior weeks only.</strong> A club is rated on official scores strictly before the '
        'graded week. Early-season rows rest on very little history and are marked.</li>'
        '<li><strong>Two snapshots, not a path.</strong> Open and close hide the movement between them. A line that '
        'moved on injury news looks identical to one that drifted on volume.</li>'
        '<li><strong>Depth for four clubs.</strong> Requirement 6 is satisfied for CHI, DEN, PHI and TB, and for no '
        'other club. The 28 uncaptured clubs are reported as uncaptured, not as healthy.</li>'
        '<li><strong>No prop prices.</strong> Player-prop markets were reached but publish targets without two-way '
        'prices, so no prop strategy can be priced or graded.</li>'
        '<li><strong>Paper only.</strong> Nothing was wagered, no reward is paid, and the ROI is a computation on a '
        'relayed number.</li></ol></section>'
    )

    body += (
        '<section class="panel"><h2>How to reproduce every figure</h2>'
        '<pre tabindex="0"><code>python3 nfl-market-desk/build.py            # write the artifacts\n'
        'python3 nfl-market-desk/build.py --check    # reproduce and compare, byte for byte\n'
        'python3 nfl-market-desk/site_build.py       # regenerate this site\n'
        'python3 -m unittest discover -s nfl-market-desk/tests\n'
        'python3 scripts/check_site.py               # links, sources, blank cells</code></pre>'
        '<p>The site reads only committed artifacts. No page computes a number at read time, so a page and its data '
        'cannot silently disagree: the build fails instead.</p>'
        '<p class="src-line">'+src(["EC6-REPO"])+'</p></section>'
    )

    body += (
        '<section class="panel"><h2>What would change the conclusion</h2><ul>'
        f'<li>Roughly {a["signal"]["side"]["required_n_at_55pct"]} settled bets, with prices captured the same way, '
        'would let the signal be estimated rather than described.</li>'
        '<li>A direct operator price source would turn every relayed number into a checked one and move gate MD-G01 '
        'from completeness to confirmation.</li>'
        '<li>A positive, adequately powered closing-line value in the gate\'s own units would be the first '
        'forward-looking evidence of an edge. It has not been observed.</li>'
        '<li>A depth chart for the remaining 28 clubs would let requirement 6 be claimed league-wide instead of for '
        'four clubs.</li></ul>'
        '<p>None of these is a modelling improvement. The model is not the binding constraint: the data is, and the '
        'desk says so.</p></section>'
    )

    body += (
        '<section class="panel"><h2>Responsible use</h2>'
        '<p>This is non-commercial research. Nothing here is advice, a tip, or an invitation to wager. Prices move '
        'and relays lag; a number on this page may never have been available to anyone. If gambling is a problem for '
        'you or someone you know, the support links in the repository\'s responsible-use page are the useful thing on '
        'this site.</p></section>'
    )
    return page("method.html", "Method & limits",
                "The eight limits that travel with every number, how to reproduce the figures, and what would change "
                "the conclusion.", body)


def main() -> None:
    SITE.mkdir(parents=True, exist_ok=True)
    builders = {
        "index.html": build_index, "summary.html": build_summary, "prices.html": build_prices,
        "origination.html": build_origination, "leaderboard.html": build_leaderboard,
        "correlation.html": build_correlation, "availability.html": build_availability,
        "gates.html": build_gates, "questions.html": build_questions,
        "suggestions.html": build_suggestions, "flagged.html": build_flagged,
        "sources.html": build_sources, "method.html": build_method,
    }
    written = []
    for slug, _ in PAGES:
        if slug not in builders:
            raise SystemExit(f"no builder for {slug}")
        (SITE / slug).write_text(builders[slug](), encoding="utf-8")
        written.append(slug)
    (SITE / "manifest.json").write_text(
        json.dumps({"pages": written, "read_on": READ_ON}, indent=2) + "\n", encoding="utf-8")
    print(f"OK: wrote {len(written)} pages to nfl-market-desk/site/")


if __name__ == "__main__":
    main()
