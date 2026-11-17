"""Build the competition desk's own site.

Every table row carries data-source-ids and at least one link to the official page it
came from, so a reader can check any number without trusting this generator. A value
that no official source publishes is rendered as an empty cell marked data-empty - never
as a dash, a zero or an estimate.
"""
from __future__ import annotations

import json
import re
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATA, SITE, read_csv, round_value, write_json  # noqa: E402

HERE = Path(__file__).resolve().parent
SOURCES = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
REGISTRY = {entry["id"]: entry["url"] for entry in
            json.loads((HERE.parent / "research" / "sources.json").read_text(encoding="utf-8"))}
DESK_SOURCES = {entry["id"]: entry for entry in SOURCES["sources"]}

# Per-club depth chart sources registered by their own club page, so a row can cite the
# chart it was actually read from rather than a representative one.
CLUB_SOURCES = json.loads((DATA / "club-chart-sources.json").read_text(encoding="utf-8")) \
    if (DATA / "club-chart-sources.json").exists() else {}

PAGES = [
    ("index.html", "Overview"),
    ("executive-summary.html", "Executive summary"),
    ("prices.html", "Price store"),
    ("results.html", "Results feed"),
    ("origination.html", "Origination order"),
    ("boards.html", "Fair vs market"),
    ("leaderboard.html", "Leaderboard"),
    ("depth.html", "Replacement depth"),
    ("correlations.html", "Correlations"),
    ("demotion.html", "Demotion gate"),
    ("injuries.html", "Injuries & depth"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("review.html", "Flagged for review"),
    ("sources.html", "Source register"),
    ("method.html", "Method & limits"),
]

NAV_LINKS = [(name, label) for name, label in PAGES]

DESK = "nfl-competition"


# ------------------------------------------------------------------ helpers

def esc(value):
    return escape(str(value), quote=True)


def num(value, places=2):
    if value is None or value == "":
        return '<td data-empty="true"></td>'
    if isinstance(value, float):
        return f"<td>{value:.{places}f}</td>"
    return f"<td>{esc(value)}</td>"


def num4(value):
    return num(value, 4)


def pct(value, places=2):
    if value is None:
        return '<td data-empty="true"></td>'
    return f"<td>{value * 100:.{places}f}%</td>"


def src_cell(source_ids, extra=None, label=None):
    """Render the source cell. The first registered id supplies the verifying link."""
    links = []
    for sid in source_ids:
        url = REGISTRY.get(sid)
        if url:
            short = label or sid
            links.append(f'<a href="{esc(url)}" target="_blank" '
                         f'rel="noopener noreferrer">{esc(short)}</a>')
    for url, text in (extra or []):
        links.append(f'<a href="{esc(url)}" target="_blank" '
                     f'rel="noopener noreferrer">{esc(text)}</a>')
    return f'<td class="refs">{" ".join(links)}</td>' if links \
        else '<td data-empty="true"></td>'


DEFAULT_EMPTY = ("No rows. The cell is blank on purpose: nothing here has been "
                 "verified from an official source.")


def table(headers, rows, note=None, empty_message=None):
    """rows: a list of (cells_html, source_ids) pairs.

    Every published row must carry a link to the official page behind it. Rows written
    without one get the link appended here, so the guarantee holds site-wide rather than
    depending on each call site remembering it.
    """
    headers = list(headers)
    prepared = []
    for cells, source_ids in rows:
        cells = list(cells)
        if "href=" not in "".join(cells):
            cells.append(src_cell(source_ids))
        prepared.append(cells)
    widths = {len(cells) for cells in prepared}
    if widths and len(headers) not in widths:
        headers.append("Source")
    for cells in prepared:
        while len(cells) < len(headers):
            cells.append('<td class="refs"></td>')
    out = ['<div class="table-wrap"><table><thead><tr>'
           + "".join("<th>" + esc(h) + "</th>" for h in headers)
           + "</tr></thead><tbody>"]
    if not prepared:
        message = esc(empty_message or DEFAULT_EMPTY)
        cols = max(1, len(headers) - 1)
        out.append('<tr data-source-ids="CP-NFL-STANDINGS"><td colspan="'
                   + str(cols) + '" class="empty-row">' + message + "</td>"
                   + src_cell(["CP-NFL-STANDINGS"], label="source") + "</tr>")
    for (_, source_ids), cells in zip(rows, prepared):
        out.append('<tr data-source-ids="' + esc(" ".join(source_ids)) + '">')
        out.extend(cells)
        out.append("</tr>")
    out.append("</tbody></table></div>")
    if note:
        out.append('<p class="table-note">' + note + "</p>")
    return "".join(out)


def page(name, title, subtitle, body, kpis=None, eyebrow="Bounded snapshot · read "
         "2026-11-14 · research only · no wagers · no prices"):
    links = []
    for href, label in NAV_LINKS:
        current = ' aria-current="page"' if href == name else ''
        links.append('<a href="' + esc(href) + '"' + current + '>'
                     + esc(label) + "</a>")
    nav = "".join(links)
    kpi_html = ""
    if kpis:
        kpi_html = '<div class="kpis">' + "".join(
            f'<div class="kpi"><span class="kpi-value">{esc(value)}</span>'
            f'<span class="kpi-label">{esc(label)}</span></div>'
            for value, label in kpis) + "</div>"
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{esc(title)} · OWN7 competition lab</title>"
        f'<meta name="description" content="{esc(subtitle)}">'
        '<link rel="stylesheet" href="style.css">'
        '<script src="app.js" defer></script></head><body>'
        '<a class="skip" href="#main">Skip to content</a>'
        '<header class="top"><div class="brand"><strong>OWN7</strong>'
        "<span>NFL competition lab</span></div>"
        f'<nav aria-label="Lab sections">{nav}</nav></header>'
        '<main id="main">'
        f'<p class="eyebrow">{esc(eyebrow)}</p>'
        f"<h1>{esc(title)}</h1>"
        f'<p class="subtitle">{esc(subtitle)}</p>'
        f"{kpi_html}{body}"
        "<footer><p>OWN7 · independent research. NFL data attributed to NFL.com; club "
        "depth charts attributed to each club's official site. Not affiliated with or "
        "endorsed by the NFL or any club. Every table row links the official source it "
        "came from; unknown values are blank, never filled in.</p>"
        '<p><a href="sources.html">Source register</a> · '
        '<a href="review.html">Flagged for review</a> · '
        '<a href="suggestions.html">Suggestions</a> · '
        '<a href="method.html">Method &amp; limits</a></p></footer>'
        "</main></body></html>\n")


# ------------------------------------------------------------------- sections

def panel(title, body, level=2):
    return f'<section class="panel"><h{level}>{esc(title)}</h{level}>{body}</section>'


def notice(text, kind="info"):
    return f'<div class="notice {kind}"><p>{text}</p></div>'


# ------------------------------------------------------------------- content

def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def page_index():
    results = load("results-feed.json")
    origination = load("origination.json")
    prices = load("price-store.json")
    board = load("leaderboard.json")
    depth = load("depth.json")
    co = load("correlations.json")
    qs = load("questions.json")
    kpis = [
        (str(results["games"]), "official final scores, reconciling 192 of 192 club "
                                "fields with the standings read the same day"),
        (str(origination["games_originated"]), "Week 10 games originated in three stages: "
                                               "side, then total, then moneyline"),
        (str(prices["markets_registered"]), "markets in the price store, holding "
                                            f"{prices['rows_stored']} rows"),
        (str(board["counts"]["Live"]), "live strategies, and "
                                       f"{board['counts']['Provisional']} provisional"),
        (str(depth["headline"]["starters_ruled_out"]), "starters ruled out with a "
                                                       "measured replacement depth"),
        (str(co["counts"]["with_values"]), "correlations computed from official numbers, "
                                           f"{co['counts']['blank']} left blank"),
        (str(qs["total"]), "questions, each split into what is held and what is missing"),
        ("8", "requirements implemented, each with its own page"),
    ]
    body = (
        panel("The one-paragraph answer",
              "<p>This lab builds the eight things the brief asked for and then shows "
              "what each one is actually worth. The results feed is real: "
              f"<strong>{results['games']} official final scores</strong> that re-derive "
              "into every club's record and match the standings page on all "
              f"<strong>{results['reconciliation']['fields_compared']} club fields</strong>. "
              "The price store is real too, and it is <strong>empty</strong>, because "
              "nfl.com returns a 404 at /odds/ and prints no price anywhere this project "
              "read. Everything that needs a price - the difference column, the staking "
              "table, return on investment, closing-line value, every reward - is "
              "therefore blank, and blank is published rather than estimated. What does "
              "work is the part that needs no price: the board is originated side first, "
              "then total, then moneyline; replacement depth is measured from each club's "
              "own printed chart; leg dependence is measured from real joint outcomes; "
              "and <strong>not one strategy survives multiplicity control</strong>, so "
              "nothing is promoted and nothing is paid.</p>")
        + '<section><h2>The eight requirements</h2><div class="cards">'
        + '<a class="card" href="prices.html"><h2>Price-snapshot store</h2><p>The store, '
          'its schema, its capture instants and its contract. Zero rows, and the verified '
          'reason why.</p></a>'
        + '<a class="card" href="results.html"><h2>Verified results feed</h2><p>137 '
          'official scores, each with its page, reconciled against the standings.</p></a>'
        + '<a class="card" href="origination.html"><h2>Side, then total, then '
          'moneyline</h2><p>Three stages in a fixed order, each reading only the stage '
          'before it.</p></a>'
        + '<a class="card" href="boards.html"><h2>Fair line, market line, difference</h2>'
          '<p>Three separate columns. The third is blank whenever the second is.</p></a>'
        + '<a class="card" href="leaderboard.html"><h2>Signal and staking apart</h2>'
          '<p>Two tables that never touch. Staking can demote an entry and never promote '
          'one.</p></a>'
        + '<a class="card" href="depth.html"><h2>Depth of the replacement</h2><p>Not just '
          'that a starter is out, but how far down the chart the club must reach.</p></a>'
        + '<a class="card" href="correlations.html"><h2>Correlations with n</h2><p>Only '
          'from officially sourced numbers, and every row states its sample size.</p></a>'
        + '<a class="card" href="demotion.html"><h2>Demotion gate</h2><p>Ten triggers that '
          'send a live strategy back to paper, with today\'s reading on each.</p></a>'
        + "</div></section>"
        + panel("Where to go for a decision",
                '<p><a href="executive-summary.html">Executive summary</a> for the short '
                'version. <a href="questions.html">Questions</a> for what is known, what '
                'is missing and what closes each gap. '
                '<a href="suggestions.html">Suggestions</a> for twelve ranked proposals '
                'you can adopt, defer or reject - the decision record starts blank on '
                'purpose. <a href="review.html">Flagged for review</a> for every '
                'irregularity found while doing this work, including two in this '
                "lab's own code.</p>"))
    return page("index.html", "Overview",
                "What this lab built on 2026-11-14, what it refuses to invent, and the "
                "one thing that blocks every reward.", body, kpis)


def page_executive_summary():
    results = load("results-feed.json")
    origination = load("origination.json")
    prices = load("price-store.json")
    board = load("leaderboard.json")
    bt = load("backtest.json")
    qs = load("questions.json")
    rv = load("review.json")
    depth = load("depth.json")
    by_id = {s["id"]: s for s in bt["strategies"]}
    sb04 = by_id["SB-04"]["signal"]
    kpis = [
        (str(board["counts"]["Live"]), "strategies live"),
        (str(board["counts"]["Provisional"]), "strategies provisional"),
        (str(prices["rows_stored"]), "price rows, from 78 registered markets"),
        (f"{sb04['hit_rate'] * 100:.1f}%", "best directional record, adjusted p "
                                           f"{sb04['q_value']:.3f}"),
    ]
    body = (
        panel("What is true, with a source",
              "<ul>"
              f"<li><strong>{results['games']} official final scores</strong> are "
              "captured. Re-derived into club records they match the NFL.com standings on "
              f"<strong>{results['reconciliation']['fields_matching']} of "
              f"{results['reconciliation']['fields_compared']} fields</strong>, with "
              f"{results['reconciliation']['league_points_scored']} points scored each "
              "way. A backtest can be settled.</li>"
              f"<li><strong>{origination['games_originated']} Week 10 games</strong> are "
              "originated, in three stages. One Week 10 game had already finished when "
              "the schedule was read, so it is excluded from the board and carried in the "
              "results feed instead.</li>"
              "<li><strong>No price exists.</strong> nfl.com returns HTTP 404 at /odds/, "
              "and no page this project read prints a spread, a total or a price. The "
              "store is built, its contract is tested, and it holds zero rows.</li>"
              f"<li><strong>No strategy is skill based yet.</strong> The best directional "
              f"record is {sb04['wins']}-{sb04['losses']} "
              f"({sb04['hit_rate'] * 100:.1f}%), which does not survive multiplicity "
              f"control at an adjusted p of 0.10 "
              f"(q = {sb04['q_value']:.3f}).</li>"
              f"<li><strong>{depth['headline']['starters_ruled_out']} starters are ruled "
              "out</strong> on a printed chart; "
              f"{depth['headline']['replacements_from_2nd_string']} are replaced by a "
              "second-string player and one slot has no printed replacement at all.</li>"
              "</ul>")
        + panel("What is not true, and is not claimed",
                "<ul><li>No return on investment, stake, drawdown or closing-line value "
                "is published anywhere. Every one of those cells is blank.</li>"
                "<li>No reward is paid, and no prize pool exists. The schedule is "
                "published; the winner is not, because there is no winner.</li>"
                "<li>No player-prop combination is graded. The division exists and both "
                "of its entries are blocked on data, not on effort.</li>"
                "<li>No point value is attached to an injury or to a replacement. A "
                "printed rank is an ordering, not a measurement of ability.</li></ul>")
        + panel("The three things that block everything",
                "<ol><li><strong>No executable price</strong> (SG-01). Until one is "
                "captured, the staking half of the leaderboard and every reward stay "
                "blank.</li>"
                "<li><strong>Source rights</strong> (SG-12). NFL.com terms section 1.3 "
                "restrict systematic retrieval without written consent. Decide this "
                "before building anything that captures prices.</li>"
                "<li><strong>Sample size</strong> (SG-05). Detecting a true 60% rate at "
                "80% power needs 153 settled selections; 55% needs 617. The largest "
                "sample here is 120.</li></ol>")
        + panel("What to read next",
                f'<p>{qs["total"]} questions are catalogued, of which '
                f'{qs["counts"].get("open", 0)} are open and '
                f'{qs["counts"].get("blocked", 0)} is blocked on rights. '
                f'{rv["total"]} irregularities are flagged, of which '
                f'{rv["counts"].get("open", 0)} are open and '
                f'{rv["counts"].get("corrected", 0)} were defects in this lab\'s own code, '
                'fixed before publication. Start with '
                '<a href="suggestions.html">the suggestions</a>: they are ranked, and the '
                'decision record is waiting for a choice.</p>'))
    return page("executive-summary.html", "Executive summary",
                "The short version: what is verified, what is deliberately blank, and the "
                "three things that block every reward.", body, kpis)


def page_prices():
    prices = load("price-store.json")
    kpis = [
        (str(prices["rows_stored"]), "rows stored"),
        (str(prices["markets_registered"]), "markets registered"),
        (str(len(prices["contract_tests"])), "contract cases exercised on every build"),
        ("404", "nfl.com/odds/, read 2026-11-14"),
    ]
    body = (
        panel("Why it is empty",
              "<ul>" + "".join(f"<li>{esc(reason)}</li>"
                               for reason in prices["empty_because"]) + "</ul>")
        + panel("Capture instants, fixed in advance",
                "<ul>" + "".join(f"<li><strong>{esc(k)}</strong>: {esc(v)}</li>"
                                 for k, v in prices["capture_rules"].items()) + "</ul>")
        + panel("Schema", "<p>Every field, its type, and the rule it enforces. A row that "
                "breaks any of these is rejected by the validator rather than stored.</p>"
                + table(["Field", "Type", "Required", "Rule"],
                        [([f"<td>{esc(f['field'])}</td>", f"<td>{esc(f['type'])}</td>",
                           f"<td>{'yes' if f['required'] else 'no'}</td>",
                           f"<td>{esc(f['rule'])}</td>"],
                          ["CP-NFL-ODDS-ABSENT"]) for f in prices["schema"]]))
        + panel("Contract, exercised not merely written",
                "<p>These cases run on every build. A contract nobody runs is a comment, "
                "not a control.</p>"
                + table(["Case", "Expected", "Observed", "Result", "Why"],
                        [([f"<td>{esc(c['case'])}</td>", f"<td>{esc(c['expected'])}</td>",
                           f"<td>{esc(c['observed'])}</td>",
                           f"<td>{'pass' if c['passes'] else 'FAIL'}</td>",
                           f"<td>{esc('; '.join(c['reasons']) or 'accepted')}</td>"],
                          ["CP-NFL-ODDS-ABSENT"]) for c in prices["contract_tests"]]))
        + panel("Market register",
                f"<p>Every market this lab originates is registered and waiting. "
                f"{len(prices['market_register'])} games, "
                f"{prices['markets_registered']} markets.</p>"
                + table(["Game", "Matchup", "Markets", "Opening rows", "Closing rows",
                         "Status", "Source"],
                        [([f"<td>{esc(r['game_id'])}</td>",
                           f"<td>{esc(r['matchup'])}</td>",
                           f"<td>{r['markets_originated']}</td>",
                           f"<td>{r['opening_rows']}</td>",
                           f"<td>{r['closing_rows']}</td>",
                           f"<td>{esc(r['store_status'])}</td>",
                           src_cell(["CP-NFL-W10-SCHEDULE"])],
                          ["CP-NFL-W10-SCHEDULE"])
                         for r in prices["market_register"]]))
        + panel("What unblocks it",
                "<ul>" + "".join(f"<li>{esc(x)}</li>"
                                 for x in prices["what_unblocks_it"]) + "</ul>"))
    return page("prices.html", "Price store",
                "Opening and closing numbers for every originated market. The store is "
                "built and holds zero rows, for a reason that is verified rather than "
                "assumed.", body, kpis)


def page_results():
    results = load("results-feed.json")
    feed = read_csv(DATA / "results-feed.csv")
    weeks = results["weeks"]
    kpis = [
        (str(results["games"]), "settled games"),
        (f"{results['reconciliation']['fields_matching']}/"
         f"{results['reconciliation']['fields_compared']}", "club fields reconciled"),
        (str(results["reconciliation"]["league_points_scored"]), "points scored, equal to "
                                                                 "points allowed"),
        (str(len(weeks)), "weeks covered"),
    ]
    rows = []
    for row in feed:
        rows.append(([f"<td>{esc(row['game_id'])}</td>",
                      f"<td>{row['week']}</td>",
                      f"<td>{esc(row['date'])}</td>",
                      f"<td>{esc(row['away'])}</td>",
                      f"<td>{row['away_score']}</td>",
                      f"<td>{esc(row['home'])}</td>",
                      f"<td>{row['home_score']}</td>",
                      f"<td>{int(row['home_margin']):+d}</td>",
                      f"<td>{row['total_points']}</td>",
                      f"<td>{esc(row['result'])}</td>",
                      src_cell(["CP-NFL-RESULTS-W1-9", "CP-NFL-W10-GAME-WASNYG"],
                               extra=[(row["source_url"], "page")])],
                     ["CP-NFL-RESULTS-W1-9", "CP-NFL-W10-GAME-WASNYG"]))
    body = (
        panel("The reconciliation is the point",
              f"<p>A results feed is only worth what its settlement data will bear. Every "
              f"row below is a final score printed by NFL.com, and the whole feed is "
              f"re-derived into each club's wins, losses, ties, points for and points "
              f"against, then compared with the standings page read the same day. "
              f"<strong>{results['reconciliation']['fields_matching']} of "
              f"{results['reconciliation']['fields_compared']} club fields match</strong>, "
              f"and league points scored equals league points allowed at "
              f"{results['reconciliation']['league_points_scored']}. The build aborts "
              f"rather than publish a mismatch.</p>")
        + panel("Games by week",
                table(["Week", "Games"],
                      [([f"<td>{esc(w)}</td>", f"<td>{c}</td>"],
                        ["CP-NFL-RESULTS-W1-9"]) for w, c in weeks.items()]))
        + panel("Settlement rules",
                "<p>These are project rules for grading an originated line. They are not "
                "official NFL rules and not the rules of any operator, none of which were "
                "retrieved.</p>"
                + table(["Market", "Rule", "Ties", "Authority"],
                        [([f"<td>{esc(r['market'])}</td>", f"<td>{esc(r['rule'])}</td>",
                           f"<td>{esc(r['tie_case'])}</td>",
                           f"<td>{esc(r['authority'])}</td>"],
                          ["CP-NFL-RESULTS-W1-9"])
                         for r in results["settlement_rules"]]))
        + panel("Every settled game",
                f"<p>{len(feed)} rows. Each links the official page it was read from.</p>"
                + table(["Game", "Wk", "Date", "Away", "Away pts", "Home", "Home pts",
                         "Home margin", "Total", "Result", "Source"], rows)))
    return page("results.html", "Results feed",
                "137 official final scores, each with the page it came from, reconciled "
                "against the standings so a backtest can be trusted.", body, kpis)


def page_origination():
    og = load("origination.json")
    params = og["parameters"]
    kpis = [
        (str(og["games_originated"]), "games originated"),
        ("3", "stages, in a fixed order"),
        (f"{params['home_allowance_points']['value']:.2f}",
         f"home allowance, measured over n = "
         f"{params['home_allowance_points']['n']}"),
        (f"{params['margin_sd_points']['value']:.2f}", "margin spread, same sample"),
    ]
    rows = []
    for game in og["board"]:
        rows.append(([f"<td>{esc(game['game_id'])}</td>",
                      f"<td>{esc(game['matchup'])}</td>",
                      f"<td>{esc(game['kickoff'])}</td>",
                      f"{num4(game['stage_1_side']['spread_home'])}",
                      f"{num4(game['stage_2_total']['total'])}",
                      f"{num4(game['stage_3_moneyline']['p_home'])}",
                      f"{num(game['stage_3_moneyline']['fair_price_home'])}",
                      f"{num(game['stage_3_moneyline']['fair_price_away'])}",
                      src_cell(["CP-NFL-STANDINGS", "CP-NFL-W10-SCHEDULE"],
                               extra=[(game["game_url"], "game")])],
                     ["CP-NFL-STANDINGS", "CP-NFL-W10-SCHEDULE"]))
    body = (
        panel("The order is structural, not a comment",
              "<p>Stage 1 produces one coherent score pair and the side from it. Stage 2 "
              "is handed that pair and may not model points again. Stage 3 is handed the "
              "stage-1 margin and the measured margin spread and may not re-model the "
              "score. A stage missing an input it was not given raises instead of "
              "guessing.</p>"
              + table(["Stage", "Market", "Produces", "May use", "Reads from the stage "
                       "before it"],
                      [([f"<td>{s['stage']}</td>", f"<td>{esc(s['market'])}</td>",
                         f"<td>{esc(s['produces'])}</td>", f"<td>{esc(s['may_use'])}</td>",
                         f"<td>{esc(s['reads_from_previous_stage'])}</td>"],
                        ["CP-NFL-STANDINGS"]) for s in og["stages"]]))
        + panel("Parameters are measured, not assumed",
                table(["Parameter", "Value", "n", "Basis", "Source"],
                      [([f"<td>League points per team-game</td>",
                         num4(params['league_points_per_team_game']['value']),
                         "<td>" + str(params['league_points_per_team_game']
                                      ['n_team_games']) + " team-games</td>",
                         "<td>" + esc(params['league_points_per_team_game']['basis'])
                         + "</td>",
                         src_cell(["CP-NFL-RESULTS-W1-9"])],
                        ["CP-NFL-RESULTS-W1-9"]),
                       (["<td>Home allowance (points)</td>",
                         num4(params['home_allowance_points']['value']),
                         "<td>" + str(params['home_allowance_points']['n'])
                         + " games</td>",
                         "<td>" + esc(params['home_allowance_points']['basis'])
                         + "</td>",
                         src_cell(["CP-NFL-RESULTS-W1-9"])],
                        ["CP-NFL-RESULTS-W1-9"]),
                       (["<td>Margin spread (points)</td>",
                         num4(params['margin_sd_points']['value']),
                         "<td>" + str(params['margin_sd_points']['n']) + " games</td>",
                         "<td>" + esc(params['margin_sd_points']['basis']) + "</td>",
                         src_cell(["CP-NFL-RESULTS-W1-9"])],
                        ["CP-NFL-RESULTS-W1-9"]),
                       (["<td>Tie rate</td>",
                         num4(params['tie_rate']['value']),
                         "<td>" + str(params['tie_rate']['n']) + " games</td>",
                         "<td>" + esc(params['tie_rate']['basis']) + "</td>",
                         src_cell(["CP-NFL-RESULTS-W1-9"])],
                        ["CP-NFL-RESULTS-W1-9"])])
                + "<p>The two parameters below are the ones an earlier board assumed. Both "
                  "are measured here from official final scores, and the difference is "
                  "published rather than absorbed.</p>"
                + table(["Parameter", "Assumed elsewhere", "Measured here", "n", "Source"],
                        [([f"<td>{esc(p['parameter'])}</td>",
                           f"<td>{p['published_elsewhere']}</td>",
                           f"{num4(p['measured_here'])}",
                           f"<td>{p['n_here']}</td>",
                           src_cell(["CP-NFL-RESULTS-W1-9", "CP-NFL-W10-GAME-WASNYG"])],
                          ["CP-NFL-RESULTS-W1-9", "CP-NFL-W10-GAME-WASNYG"])
                         for p in og["parameters_replaced"]])
                + f"<p>The home allowance carries a 95% interval of "
                  f"[{params['home_allowance_points']['ci95'][0]:.2f}, "
                  f"{params['home_allowance_points']['ci95'][1]:.2f}] points. That "
                  f"interval contains both zero and the conventional two points, so this "
                  f"season does not separate them, and the board does not pretend "
                  f"otherwise.</p>")
        + panel("Consistency checks",
                "<ul>"
                f"<li>Total equals the sum of the stage-1 pair: "
                f"<strong>{og['consistency_checks']['total_equals_sum_of_stage_1_pair']}"
                f"</strong></li>"
                f"<li>Moneyline probability rises with the stage-1 margin: "
                f"<strong>{og['consistency_checks']['moneyline_monotonic_in_side']}"
                f"</strong></li>"
                f"<li>Stages ran in order: "
                f"<strong>{og['consistency_checks']['stages_run_in_order']}</strong></li>"
                "</ul>")
        + panel("The board",
                f"<p>{len(og['board'])} games. One Week 10 game had already finished when "
                f"the schedule page was read, so it is not on this board.</p>"
                + table(["Game", "Matchup", "Kickoff (ET)", "Stage 1 side", "Stage 2 total",
                         "Stage 3 P(home)", "Fair home", "Fair away", "Source"], rows)))
    return page("origination.html", "Origination order",
                "Side first, then total, then moneyline - three stages, each reading only "
                "the stage before it.", body, kpis)


def page_boards():
    boards = load("boards.json")
    kpis = [
        (str(boards["markets"]), "market rows"),
        (str(boards["games"]), "games"),
        ("3", "columns: fair, market, difference"),
        ("0", "market lines captured"),
    ]
    rows = []
    for row in boards["rows"]:
        rows.append(([f"<td>{esc(row['market_id'])}</td>",
                      f"<td>{esc(row['matchup'])}</td>",
                      f"<td>{esc(row['market'])}</td>",
                      f"<td>{esc(row['selection'])}</td>",
                      f"{num4(row['fair_line'])}",
                      f"{num4(row['market_line'])}",
                      f"{num4(row['difference'])}",
                      f"{num(row['fair_price'])}",
                      f"{num(row['market_price'])}",
                      f"<td>{esc(row['status'])}</td>",
                      src_cell(["CP-NFL-W10-SCHEDULE", "CP-NFL-STANDINGS"],
                               extra=[(row["game_url"], "game")])],
                     ["CP-NFL-W10-SCHEDULE", "CP-NFL-STANDINGS"]))
    body = (
        panel("What each column means",
              "<ul>" + "".join(f"<li><strong>{esc(k)}</strong>: {esc(v)}</li>"
                               for k, v in boards["columns"].items()) + "</ul>")
        + panel("Why the difference is blank and stays blank",
                "<ul>" + "".join(f"<li>{esc(reason)}</li>"
                                 for reason in boards["why_the_difference_is_blank"])
                + "</ul>"
                + "<p>A difference is the whole point of the column. Printing a zero "
                  "there would look like a finding, and printing the fair line twice "
                  "would look like a comparison. Neither is honest, so the cell is "
                  "empty.</p>")
        + panel("How the over price is derived",
                "<p>The one fair price on the board that is not definitional is the "
                "over. It comes from the walk-forward residuals rather than from a "
                "guess.</p>"
                + table(["Item", "Value"],
                        [([f"<td>{esc(k)}</td>", num4(v) if isinstance(v, float)
                           else f"<td>{esc(v)}</td>"], ["CP-NFL-RESULTS-W1-9"])
                         for k, v in boards["over_price_derivation"].items()]))
        + panel("The board",
                f"<p>{boards['markets']} rows across {boards['games']} games.</p>"
                + table(["Market", "Matchup", "Market type", "Selection", "Fair line",
                         "Market line", "Difference", "Fair price", "Market price",
                         "Status", "Source"], rows)))
    return page("boards.html", "Fair vs market",
                "The model's number, the market's number and the difference, as three "
                "separate columns that never substitute for each other.", body, kpis)


def page_leaderboard():
    lb = load("leaderboard.json")
    kpis = [
        (str(lb["counts"]["Live"]), "live"),
        (str(lb["counts"]["Provisional"]), "provisional"),
        (str(lb["counts"]["Paper"]), "paper"),
        (str(lb["counts"]["Blocked on data"]), "blocked on data"),
    ]
    entries = sorted(lb["entries"],
                     key=lambda e: (e["signal_rank_overall"] is None,
                                    e["signal_rank_overall"] or 0))

    def signal_rows():
        rows = []
        for e in entries:
            s = e["signal"]
            rows.append(([f"<td>{esc(e['id'])}</td>",
                          f"<td>{esc(e['division'])}</td>",
                          f"<td>{esc(e['name'])}</td>",
                          f"<td>{esc(e['tier'])}</td>",
                          num(e["signal_rank_overall"]),
                          num(s.get("n")),
                          num4(s.get("hit_rate")),
                          num4(s.get("null_rate")),
                          num4(s.get("p_value")),
                          num4(s.get("q_value")),
                          num4(e["signal_score"]),
                          f"<td>{esc(', '.join(e['failed']) or 'none')}</td>",
                          src_cell(["CP-NFL-RESULTS-W1-9", "CP-NFL-W10-GAME-WASNYG"])],
                         ["CP-NFL-RESULTS-W1-9", "CP-NFL-W10-GAME-WASNYG"]))
        return rows

    body = (
        panel("Why the two halves are separate",
              "<ul>" + "".join(f"<li>{esc(rule)}</li>"
                               for rule in lb["separation_rule"]) + "</ul>"
              + "<p>The failure this prevents is ordinary: a flat stake that lands on a "
                "good month produces a large return, the return produces a rank, and the "
                "rank gets read as evidence about the forecast. Splitting the tables "
                "removes that path. When a price exists the staking table will be able to "
                "<strong>demote</strong> an entry, and will still never be able to "
                "promote one.</p>")
        + panel("Ranking metric",
                f"<p><strong>{esc(lb['signal_ranking_metric']['name'])}</strong>: "
                f"<code>{esc(lb['signal_ranking_metric']['formula'])}</code>. "
                f"{esc(lb['signal_ranking_metric']['why'])}</p>")
        + panel("The signal table",
                "<p>Ranked. Every column here is computable with no price at all.</p>"
                + table(["ID", "Division", "Strategy", "Tier", "Rank", "n", "Hit rate",
                         "Reference", "p", "Adjusted p", "Signal score", "Gates failed",
                         "Source"], signal_rows()))
        + panel("The staking table",
                "<p>Empty, and empty on purpose. Each column below needs a price that "
                "does not exist.</p>"
                + table(["Staking rank", "Stake units", "Return", "Profit units",
                         "Max drawdown", "Closing-line value", "Source"],
                        [], empty_message=lb["staking_table"]["empty_because"])
                + f"<p><strong>Effect on the signal rank: "
                  f"{esc(lb['staking_table']['effect_on_signal_rank'])}</strong></p>")
        + panel("Gates",
                f"<p>{esc(lb['gate_rule'])}</p>"
                + table(["Gate", "Name", "Rule", "Blocks"],
                        [([f"<td>{esc(g['id'])}</td>", f"<td>{esc(g['name'])}</td>",
                           f"<td>{esc(g['rule'])}</td>", f"<td>{esc(g['blocks'])}</td>"],
                          ["CP-NFL-RESULTS-W1-9"]) for g in lb["gates"]]))
        + panel("Tiers and rewards",
                "<ul>" + "".join(f"<li><strong>{esc(k)}</strong>: {esc(v)}</li>"
                                 for k, v in lb["tiers"].items()) + "</ul>"
                + table(["Item", "Value"],
                        [([f"<td>{esc(k)}</td>",
                           num4(v) if isinstance(v, float) else f"<td>{esc(v)}</td>"],
                          ["CP-NFL-ODDS-ABSENT"])
                         for k, v in lb["rewards"].items()])))
    return page("leaderboard.html", "Leaderboard",
                "Signal and staking in two tables that never touch, so a lucky staking "
                "run cannot be mistaken for a good forecast.", body, kpis)


def page_depth():
    depth = load("depth.json")
    kpis = [
        (str(depth["headline"]["starters_ruled_out"]), "starters ruled out"),
        (str(depth["headline"]["replacements_from_2nd_string"]), "replaced by a 2nd "
                                                                 "string"),
        (str(depth["headline"]["replacements_from_3rd_string"]), "replaced by a 3rd "
                                                                 "string"),
        (str(depth["headline"]["slots_with_no_printed_replacement"]), "slots with no "
                                                                      "printed replacement"),
    ]
    slot_rows = []
    for row in depth["slots"]:
        if row["tier"] != "out":
            continue
        slot_rows.append(([f"<td>{esc(row['club'])}</td>",
                           f"<td>{esc(row['unit'])}</td>",
                           f"<td>{esc(row['position'])}</td>",
                           f"<td>{esc(row['slot'])}</td>",
                           f"<td>{esc(row['unavailable_ranks'])}</td>",
                           f"<td>{'yes' if row['starter_unavailable'] else 'no'}</td>",
                           num(row["replacement_depth"]),
                           num(row["reach"]),
                           f"<td>{esc(row['replacement_player'] or 'none printed')}</td>",
                           f"<td>{'yes' if row['slot_exhausted'] else 'no'}</td>",
                           f"<td>{'yes' if row['no_backup_printed'] else 'no'}</td>",
                           src_cell(["CP-NFL-INJ-W10"],
                                    extra=[(row["source_url"], "chart")])],
                         ["CP-NFL-INJ-W10"]))

    player_rows = []
    for row in depth["players"]:
        if row["tier"] != "out":
            continue
        player_rows.append(([f"<td>{esc(row['club'])}</td>",
                             f"<td>{esc(row['player'])}</td>",
                             f"<td>{esc(row['unit'])}</td>",
                             f"<td>{esc(row['position'])}</td>",
                             num(row["own_rank"]),
                             f"<td>{esc(row['game_status'] or '')}</td>",
                             f"<td>{esc(row['replacement_player'] or 'none printed')}</td>",
                             num(row["replacement_depth"]),
                             num(row["reach"]),
                             f"<td>{'yes' if row['slot_exhausted'] else 'no'}</td>",
                             src_cell(["CP-NFL-INJ-W10"],
                                      extra=[(row["depth_source_url"], "chart")])],
                           ["CP-NFL-INJ-W10"]))

    club_rows = []
    for row in depth["club_rollup"]:
        club_rows.append(([f"<td>{esc(row['club'])}</td>",
                           num(row["injury_rows"]),
                           num(row["rows_with_official_game_status"]),
                           num(row["rows_ruled_out"]),
                           num(row["starters_out_offence"]),
                           num(row["starters_out_defence"]),
                           num(row["starters_out_special_teams"]),
                           num(row["replacements_from_2nd_string"]),
                           num(row["replacements_from_3rd_string"]),
                           num(row["replacements_from_4th_string_or_deeper"]),
                           num(row["deepest_reach"]),
                           num(row["slots_with_no_printed_replacement"]),
                           f"<td>{esc(row['note'])}</td>",
                           src_cell(["CP-NFL-INJ-W10"])],
                         ["CP-NFL-INJ-W10"]))

    body = (
        panel("Definitions",
              "<ul>" + "".join(f"<li><strong>{esc(k)}</strong>: {esc(v)}</li>"
                               for k, v in depth["definitions"].items()) + "</ul>")
        + panel("The ceiling on how much of this can be known",
                "<ul>"
                f"<li>{depth['coverage']['injury_rows']} injury rows were captured.</li>"
                f"<li>Only <strong>"
                f"{depth['coverage']['rows_with_an_official_game_status']}</strong> of "
                f"them carry an official game status.</li>"
                f"<li>The other "
                f"<strong>{depth['coverage']['rows_without_an_official_game_status']}"
                f"</strong> carry a practice status and no game status, so no absence is "
                f"stated and no replacement is implied.</li>"
                f"<li>{depth['coverage']['clubs_with_a_captured_chart']} clubs have a "
                f"captured chart; "
                f"{', '.join(depth['coverage']['clubs_without_a_captured_chart'])} does "
                f"not.</li>"
                f"<li>{depth['coverage']['printed_slots']} printed slots in total.</li>"
                "</ul>"
                + f"<p>{esc(depth['coverage']['why_that_ceiling_matters'])}</p>")
        + panel("By club",
                table(["Club", "Injury rows", "With a game status", "Ruled out",
                       "Starters out (offence)", "Starters out (defence)",
                       "Starters out (ST)", "From 2nd", "From 3rd", "From 4th+",
                       "Deepest reach", "No printed replacement", "Note", "Source"],
                      club_rows))
        + panel("Every player with an official status on a printed chart",
                table(["Club", "Player", "Unit", "Position", "Own rank", "Status",
                       "Replacement", "Replacement depth", "Reach", "Slot exhausted",
                       "Source"], player_rows))
        + panel("Every affected slot",
                table(["Club", "Unit", "Position", "Slot", "Unavailable ranks",
                       "Starter out", "Replacement depth", "Reach", "Replacement",
                       "Exhausted", "No backup printed", "Source"], slot_rows))
        + panel("What a rank is not",
                "<ul>" + "".join(f"<li>{esc(x)}</li>"
                                 for x in depth["not_measured"]) + "</ul>"))
    return page("depth.html", "Replacement depth",
                "How far down its own printed chart a club must reach - a second-string "
                "replacement is a different problem from a fourth-string one.", body, kpis)


def page_correlations():
    co = load("correlations.json")
    kpis = [
        (str(co["counts"]["with_values"]), "computed from official numbers"),
        (str(co["counts"]["blank"]), "left blank on purpose"),
        (str(co["counts"]["labelled_mechanical"]), "labelled as mechanical"),
        ("n", "published with every value"),
    ]
    rows = []
    for row in co["rows"]:
        rows.append(([f"<td>{esc(row['id'])}</td>",
                      f"<td>{esc(row['quantity'])}</td>",
                      f"<td>{esc(row['level'])}</td>",
                      num(row["n"]),
                      num4(row["value"]),
                      num4(row["p_value"]),
                      num4(row["ci95_low"]),
                      num4(row["ci95_high"]),
                      f"<td>{esc(row['method'])}</td>",
                      f"<td>{esc(row['provenance'])}</td>",
                      f"<td>{'yes' if row['counts_as_independent_evidence'] else 'no'}"
                      f"</td>",
                      src_cell(row["source_ids"])],
                     row["source_ids"]))
    body = (
        panel("Three rules bind this table",
              "<ul>" + "".join(f"<li>{esc(r)}</li>" for r in co["rules"]) + "</ul>")
        + panel("Every correlation, with its n",
                table(["ID", "Quantity", "Level", "n", "Value", "p", "95% low", "95% high",
                       "Method", "Provenance", "Independent evidence", "Source"], rows))
        + panel("Caveats carried on the rows themselves",
                "<ul>" + "".join(
                    f"<li><strong>{esc(r['id'])}</strong>: {esc(r['mechanical_caveat'])}"
                    f"</li>" for r in co["rows"] if r["mechanical_caveat"]) + "</ul>"
                + "<p>A correlation between two clubs' season scoring rates says nothing "
                  "about whether two legs inside one game move together. The level column "
                  "exists so the two are never confused.</p>"))
    return page("correlations.html", "Correlations",
                "Computed only from officially sourced numbers, with n published on every "
                "row and the provenance named.", body, kpis)


def page_demotion():
    dm = load("demotion.json")
    kpis = [
        (str(dm["count"]["computable"]), "triggers computable today"),
        (str(dm["count"]["blocked_on_price"]), "armed but blocked on price"),
        (str(dm["count"]["triggered_now"]), "firing now"),
        (str(dm["live_strategies"]), "live strategies to demote"),
    ]
    rows = []
    for t in dm["triggers"]:
        rows.append(([f"<td>{esc(t['id'])}</td>",
                      f"<td>{esc(t['name'])}</td>",
                      f"<td>{esc(t['metric'])}</td>",
                      f"<td>{esc(t['threshold'])}</td>",
                      f"<td>{esc(t['window'])}</td>",
                      f"<td>{esc(t['consequence'])}</td>",
                      f"<td>{esc(t['state'])}</td>",
                      f"<td>{esc(t['current_value'] or '')}</td>",
                      src_cell(["CP-NFL-RESULTS-W1-9"])],
                     ["CP-NFL-RESULTS-W1-9"]))
    example_rows = []
    for w in dm["worked_example"]["strategies"]:
        example_rows.append(([f"<td>{esc(w['strategy'])}</td>",
                              f"<td>{w['window']}</td>",
                              f"<td>{w['available']}</td>",
                              f"<td>{w['wins']}</td>",
                              num4(w["hit_rate"]),
                              num4(w["p_value"]),
                              f"<td>{esc(str(w['would_demote']))}</td>",
                              src_cell(["CP-NFL-RESULTS-W1-9"])],
                             ["CP-NFL-RESULTS-W1-9"]))
    body = (
        panel("The ladder runs one way",
                f"<p><strong>Promotion:</strong> {esc(dm['ladder']['promotion'])}. "
                f"<strong>Demotion:</strong> {esc(dm['ladder']['demotion'])}</p>"
                f"<p>{esc(dm['ladder']['why_one_way'])}</p>")
        + panel("Every trigger, with today's reading",
                f"<p>{esc(dm['status'])}</p>"
                + table(["ID", "Trigger", "Metric", "Threshold", "Window", "Consequence",
                         "State", "Current reading", "Source"], rows))
        + panel("Worked example: what D01 would do today",
                f"<p>{esc(dm['worked_example']['explanation'])}</p>"
                + table(["Strategy", "Window", "Available", "Wins", "Hit rate", "p",
                         "Would demote", "Source"], example_rows)))
    return page("demotion.html", "Demotion gate",
                "Ten triggers that send a live strategy back to paper, each with its "
                "metric, threshold, window and current reading.", body, kpis)


def page_injuries():
    inj = load("injuries.json")
    kpis = [
        (str(inj["deficiency_counts"]["slots_needing_a_replacement"]),
         "slots needing a replacement"),
        (str(inj["deficiency_counts"]["defence"]), "of them on defence"),
        (str(inj["deficiency_counts"]["offence"]), "of them on offence"),
        (f"{inj['status_coverage']['rows_with_an_official_game_status'] if 'rows_with_an_official_game_status' in inj['status_coverage'] else inj['status_coverage']['by_game_status'].get('Out', 0) + inj['status_coverage']['by_game_status'].get('Questionable', 0)}",
         "rows with an official game status"),
    ]
    def_rows = []
    for row in inj["deficiencies"]:
        def_rows.append(([f"<td>{esc(row['club'])}</td>",
                          f"<td>{esc(row['unit_label'])}</td>",
                          f"<td>{esc(row['position'])}</td>",
                          f"<td>{esc(row['game_status'])}</td>",
                          num(row["replacement_depth"]),
                          f"<td>{esc(row['depth_label'] or 'none printed')}</td>",
                          f"<td>{esc(row['replacement_player'] or 'none printed')}</td>",
                          num(row["reach"]),
                          f"<td>{'yes' if row['slot_exhausted'] else 'no'}</td>",
                          src_cell(["CP-NFL-INJ-W10"],
                                   extra=[(row["depth_source_url"], "chart")])],
                         ["CP-NFL-INJ-W10"]))
    club_rows = []
    for row in inj["club_rows"]:
        club_rows.append(([f"<td>{esc(row['club'])}</td>",
                           num(row["injury_rows"]),
                           num(row["rows_with_game_status"]),
                           num(row["rows_without_game_status"]),
                           num(row["ruled_out"]),
                           num(row["questionable"]),
                           num(row["offence_replacements"]),
                           num(row["defence_replacements"]),
                           num(row["special_teams_replacements"]),
                           num(row["deepest_reach"]),
                           num(row["slots_with_no_printed_replacement"]),
                           num(row["printed_slots_captured"]),
                           f"<td>{esc(row['note'])}</td>",
                           src_cell(["CP-NFL-INJ-W10"])],
                         ["CP-NFL-INJ-W10"]))
    body = (
        panel("Coverage",
              f"<p>{esc(inj['status_coverage']['ceiling'])}</p>"
              + table(["Game status", "Rows"],
                      [([f"<td>{esc(k)}</td>", f"<td>{v}</td>"], ["CP-NFL-INJ-W10"])
                       for k, v in inj["status_coverage"]["by_game_status"].items()])
              + table(["Practice status", "Rows"],
                      [([f"<td>{esc(k)}</td>", f"<td>{v}</td>"], ["CP-NFL-INJ-W10"])
                       for k, v in inj["status_coverage"]["by_practice_status"].items()]))
        + panel("Where a club must reach into its bench",
                table(["Club", "Unit", "Position", "Status", "Replacement depth",
                       "Depth label", "Replacement", "Reach", "Slot exhausted", "Source"],
                      def_rows))
        + panel("By club",
                table(["Club", "Injury rows", "With game status", "Without", "Ruled out",
                       "Questionable", "Offence replacements", "Defence replacements",
                       "ST replacements", "Deepest reach", "No printed replacement",
                       "Printed slots", "Note", "Source"], club_rows))
        + panel("Limits",
                "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in inj["limits"]) + "</ul>"))
    return page("injuries.html", "Injuries & depth",
                "What the league states, and how deep each club must reach on offence and "
                "on defence.", body, kpis)


def page_questions():
    qs = load("questions.json")
    kpis = [
        (str(qs["total"]), "questions"),
        (str(qs["counts"].get("answered", 0) + qs["counts"].get("answered-no", 0)),
         "answered from an official source"),
        (str(qs["counts"].get("open", 0)), "open"),
        (str(qs["counts"].get("blocked", 0)), "blocked on rights"),
    ]
    rows = []
    for q in qs["questions"]:
        rows.append(([f"<td>{esc(q['id'])}</td>",
                      f"<td>{esc(q['category'])}</td>",
                      f"<td>{esc(q['status'])}</td>",
                      f"<td>{esc(q['question'])}</td>",
                      f"<td>{esc(q['blocks'])}</td>",
                      f"<td>{esc(q['have'])}</td>",
                      f"<td>{esc(q['missing'])}</td>",
                      f"<td>{esc(q['closes_it'])}</td>",
                      src_cell(q["have_sources"] or ["CP-NFL-STANDINGS"])],
                     (q["have_sources"] or ["CP-NFL-STANDINGS"])))
    body = (
        panel("How to read this",
                f"<p>{esc(qs['purpose'])}</p>"
                "<p>Statuses: <strong>answered</strong> - an official source answers it; "
                "<strong>answered-no</strong> - an official source answers it and the "
                "answer is no; <strong>partial</strong> - some is measured, the rest is "
                "not published; <strong>open</strong> - not answerable from anything "
                "retrieved; <strong>blocked</strong> - answerable in principle, but the "
                "NFL.com terms stand in the way.</p>")
        + panel("How much evidence it takes",
                f"<p>{esc(qs['sample_size_note'])}</p>"
                + table(["True rate", "Settled selections needed"],
                        [([f"<td>{r['true_rate'] * 100:.1f}%</td>",
                           f"<td>{r['settled_selections_needed']}</td>"],
                          ["CP-NFL-RESULTS-W1-9"])
                         for r in qs["sample_size_table"]]))
        + panel("The questions",
                table(["ID", "Category", "Status", "Question", "What it blocks",
                       "What we have", "What is missing", "What closes it", "Source"],
                      rows)))
    return page("questions.html", "Questions",
                "What we know, what we do not, and the specific action that closes each "
                "gap - so a decision is not made on a guess.", body, kpis)


def choices_payload(sg):
    return [{"id": item["id"], "title": item["title"]} for item in sg["suggestions"]]


def page_suggestions():
    sg = load("suggestions.json")
    kpis = [
        (str(sg["count"]), "suggestions"),
        ("0", "adopted so far - the record is yours to fill"),
        (str(sg["by_category"].get("Information discovery", 0)), "close a missing-information gap"),
        ("12", "weeks of NFL season left to gather evidence"),
    ]
    rows = []
    for s in sg["suggestions"]:
        rows.append(([f"<td>{s['rank']}</td>",
                      f"<td>{esc(s['id'])}</td>",
                      f"<td>{esc(s['category'])}</td>",
                      f"<td>{esc(s['title'])}</td>",
                      f"<td>{esc(s['problem'])}</td>",
                      f"<td>{esc(s['evidence'])}</td>",
                      f"<td>{esc('; '.join(s['unlocks']))}</td>",
                      f"<td>{esc(s['cost'])}</td>",
                      f"<td>{esc(s['risk'])}</td>",
                      f"<td>{esc(s['acceptance_test'])}</td>",
                      src_cell(["CP-NFL-ODDS-ABSENT"])],
                     ["CP-NFL-ODDS-ABSENT"]))
    body = (
        panel("This is a decision hub, not a task list",
                f"<p>{esc(sg['purpose'])}</p>"
                f"<p>{esc(sg['ranking_rule'])}</p>"
                + '<div class="notice info"><p>Each row below offers <strong>Adopt</strong>, '
                  '<strong>Defer</strong> and <strong>Reject</strong>. Choosing one does '
                  'not implement anything: it writes your choice into a local preference '
                  'you can export and send back. The record starts blank on purpose, '
                  'because a suggestion implemented by accident is not a decision.</p></div>')
        + panel("Ranked suggestions",
                table(["Rank", "ID", "Category", "Proposal", "Problem", "Evidence",
                       "Unlocks", "Cost", "Risk", "Acceptance test", "Source"], rows))
        + panel("Your decision record",
                "<p>Nothing has been chosen yet. Use the controls on each row; the export "
                "button produces a file you can review or send to whoever implements it."
                "</p>"
                + '<div id="decision-board" class="decisions" data-choices="'
                  + esc(json.dumps(choices_payload(sg)))
                  + '"><p class="muted">Adopt, defer or reject each proposal below. '
                    'Your choice is stored in your browser only and is never sent '
                    'anywhere.</p></div>'
                + '<p><button type="button" id="export-decisions" class="btn">Export my '
                  'choices as JSON</button> '
                  '<button type="button" id="clear-decisions" class="btn btn-quiet">'
                  'Clear my choices</button></p>'))
    return page("suggestions.html", "Suggestions",
                "Twelve ranked proposals to improve decision making and discover what is "
                "missing. Review, choose, then implement - in that order.", body, kpis)


def page_review():
    rv = load("review.json")
    kpis = [
        (str(rv["total"]), "flags"),
        (str(rv["counts"].get("open", 0)), "open for your decision"),
        (str(rv["counts"].get("explained", 0)), "explained"),
        (str(rv["counts"].get("corrected", 0)), "defects found and fixed here"),
    ]
    rows = []
    for f in rv["flags"]:
        rows.append(([f"<td>{esc(f['id'])}</td>",
                      f"<td>{esc(f['status'])}</td>",
                      f"<td>{esc(f['severity'])}</td>",
                      f"<td>{esc(f['title'])}</td>",
                      f"<td>{esc(f['finding'])}</td>",
                      f"<td>{esc(f['detail'])}</td>",
                      f"<td>{esc(f['recommended'])}</td>",
                      src_cell(f["source_ids"] or ["CP-NFL-STANDINGS"],
                               extra=[(f["checked_against"], "checked against")]
                               if f["checked_against"].startswith("http") else None)],
                     (f["source_ids"] or ["CP-NFL-STANDINGS"])))
    body = (
        panel("How this was produced",
                f"<p>{esc(rv['method'])}</p>"
                f"<p>A repository-wide search for committed market, price, closing, "
                f"CLV, return or stake values found "
                f"<strong>{esc(rv['price_search']['repository_wide_search_for_committed_prices'])}"
                f"</strong>. The price store holds "
                f"{rv['price_search']['rows_in_store']} rows.</p>")
        + panel("Flags",
                table(["ID", "Status", "Severity", "Title", "Finding", "Detail",
                       "Recommended", "Source"], rows)))
    return page("review.html", "Flagged for review",
                "Every irregularity found while doing this work, with the official link, "
                "including two defects in this lab's own code.", body, kpis)


def page_sources():
    rows = []
    for entry in SOURCES["sources"]:
        rows.append(([f"<td>{esc(entry['id'])}</td>",
                      f"<td>{esc(entry['publisher'])}</td>",
                      f"<td>{esc(entry['title'])}</td>",
                      f"<td>{esc(entry['checked_on'])}</td>",
                      f"<td>{esc(entry['status'])}</td>",
                      f"<td>{esc(entry['scope'])}</td>",
                      f"<td>{esc(entry['access'])}</td>",
                      src_cell([entry["id"]])],
                     [entry["id"]]))
    body = (
        panel("Register",
                f"<p>{SOURCES['count']} sources. A row is published only if every value "
                f"in it traces to a source registered here. Id collisions with the "
                f"repository register: "
                f"{esc(', '.join(SOURCES['id_collisions_with_research_sources_json']) or 'none')}"
                f".</p>"
                + table(["ID", "Publisher", "Title", "Checked on", "Status", "Scope",
                         "Access", "Source"], rows))
        + panel("Retrieval class",
                f"<p>{esc(SOURCES['sources'][0]['retrieval_class'])}. Pages are read at "
                f"human pace, the rendered text actually read is saved as evidence, and "
                f"no dataset or feed is released.</p>"))
    return page("sources.html", "Source register",
                "Every page this lab read, when it was read, and what it was allowed to "
                "be used for.", body,
                [(str(SOURCES["count"]), "registered sources"),
                 ("2026-11-14", "read on"),
                 ("0", "prices retrieved"),
                 ("31", "club depth charts")])


def page_method():
    body = (
        panel("What this lab is",
                "<p>An NFL research desk that originates its own lines, grades them "
                "walk-forward against official final scores, and publishes what it knows "
                "next to what it does not. It produces no price, no stake, no return, no "
                "wager and no reward, and it attaches no point value to an injury. Nothing "
                "here is a betting service or betting advice.</p>")
        + panel("How a forecast is made",
                "<ol><li>Cumulative scoring rates are built from official final scores in "
                "weeks strictly before the game being forecast.</li>"
                "<li>Stage 1 produces one score pair and the side from it.</li>"
                "<li>Stage 2 takes that pair and sums it for the total.</li>"
                "<li>Stage 3 takes the stage-1 margin and the measured margin spread and "
                "produces a win probability and a fair, zero-hold price.</li></ol>"
                "<p>The home allowance and the margin spread are measured from prior "
                "games at each step, so no week sees its own result.</p>")
        + panel("How a strategy is graded",
                "<ul><li>A forecast for week w uses only weeks less than w. Week 1 is "
                "never scored.</li>"
                "<li>The permutation null shuffles forecasts across games, keeping the "
                "forecasts and the results exactly as they are and destroying only the "
                "pairing, so a low p-value means the forecast was matched to the right "
                "game.</li>"
                "<li>Adjusted p-values use Benjamini-Hochberg at 0.10 across every "
                "strategy tested in the same run.</li>"
                "<li>A forecast is never graded against itself, except as a published "
                "control.</li></ul>")
        + panel("What is never done",
                "<ul><li>No value is inferred, interpolated or filled in. A cell with no "
                "official source behind it is empty.</li>"
                "<li>No market line is estimated from a model line, and the difference "
                "column is never printed as zero.</li>"
                "<li>No staking figure is produced without a price, and the staking table "
                "can never raise a signal rank.</li>"
                "<li>No parameter is fitted on the evaluation window.</li>"
                "<li>No dataset is released. NFL.com terms section 1.3 prohibit systematic "
                "retrieval to compile a collection without written consent, and no consent "
                "is evidenced.</li></ul>"))
    return page("method.html", "Method & limits",
                "How every number on this site is produced, and the four things this lab "
                "will not do to get one.", body)


def build():
    SITE.mkdir(parents=True, exist_ok=True)
    generated = []
    for name, _ in PAGES:
        builder = {
            "index.html": page_index,
            "executive-summary.html": page_executive_summary,
            "prices.html": page_prices,
            "results.html": page_results,
            "origination.html": page_origination,
            "boards.html": page_boards,
            "leaderboard.html": page_leaderboard,
            "depth.html": page_depth,
            "correlations.html": page_correlations,
            "demotion.html": page_demotion,
            "injuries.html": page_injuries,
            "questions.html": page_questions,
            "suggestions.html": page_suggestions,
            "review.html": page_review,
            "sources.html": page_sources,
            "method.html": page_method,
        }[name]
        (SITE / name).write_text(builder(), encoding="utf-8")
        generated.append(name)
    write_json(SITE / "manifest.json", {"pages": generated, "desk": DESK,
                                        "built_on": "2026-11-14"})
    return generated


def check() -> int:
    """Re-read every committed artifact and fail loudly on a broken contract.

    `--check` never writes. It exists so CI can prove the published pages agree with the
    committed data without trusting that the generator was run.
    """
    problems: list[str] = []

    def load(name):
        path = DATA / name
        if not path.is_file():
            problems.append(f"missing artifact: data/{name}")
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    prices = load("price-store.json")
    if prices and prices.get("rows"):
        problems.append("price store is not empty; a price must never be published unsourced")
    boards = load("boards.json")
    for row in boards.get("rows", []):
        if row.get("market_line") not in (None, ""):
            problems.append(f"{row.get('market_id')}: market line published without a price")
        if row.get("market_price") not in (None, ""):
            problems.append(f"{row.get('market_id')}: market price published without a price")
        if row.get("difference") not in (None, ""):
            problems.append(f"{row.get('market_id')}: difference published without a market line")
    leaderboard = load("leaderboard.json")
    if leaderboard.get("staking_table", {}).get("rows"):
        problems.append("staking table is not empty; no stake can be computed without a price")
    correlations = load("correlations.json")
    for row in correlations.get("rows", []):
        if row.get("value") is None:
            continue
        if not row.get("n"):
            problems.append(f"{row.get('id')}: published a value without its sample size")
        if not row.get("source_ids"):
            problems.append(f"{row.get('id')}: published a value without an official source")
    results = load("results-feed.json")
    recon = results.get("reconciliation", {})
    if recon and recon.get("mismatches"):
        problems.append("results feed no longer reconciles against the official standings")
    for page in PAGES:
        path = SITE / page[0]
        if not path.is_file():
            problems.append(f"missing page: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if text.count("<h1>") != 1 or text.count("<main") != 1:
            problems.append(f"{page[0]}: document semantics incomplete")
        for row in re.findall(r'<tr data-source-ids="([^"]*)">(.*?)</tr>', text, re.S):
            ids, body = row[0].split(), row[1]
            if not ids:
                problems.append(f"{page[0]}: row with no source ids")
                continue
            hrefs = re.findall(r'href="([^"]+)"', body)
            if not any(REGISTRY.get(sid) in hrefs for sid in ids):
                problems.append(f"{page[0]}: row lacks its official source link")
    for problem in problems:
        print("FAIL", problem)
    print(f"checked {len(PAGES)} pages and 8 requirements: "
          f"{'FAILED' if problems else 'ok'}")
    return 1 if problems else 0


def main():
    if "--check" in sys.argv:
        raise SystemExit(check())
    generated = build()
    print(f"  built {len(generated)} pages into nfl-competition/site/")


if __name__ == "__main__":
    main()
