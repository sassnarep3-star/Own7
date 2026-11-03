#!/usr/bin/env python3
"""Generate the static GitHub Pages site in docs/ from docs/data/*.json.

Pages are plain HTML (no build dependencies). Every table row is rendered from
a JSON row, so the data file is the single source of truth.
"""
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DATA = DOCS / "data"
DATE = "2026-11-03"

NAV = [
    ("index.html", "Home"),
    ("executive-summary.html", "Executive Summary"),
    ("sources.html", "Sources"),
    ("betting-rules.html", "Betting Rules"),
    ("strategies.html", "Strategies"),
    ("validation-gates.html", "Validation Gates"),
    ("correlation.html", "Correlation"),
    ("leaderboard.html", "Leaderboard"),
    ("responsible-gambling.html", "Responsible Gambling"),
    ("repo-review.html", "Repo Review"),
    ("flagged.html", "Flagged for Review"),
]

STATUS_LABEL = {
    "verified": ("b-verified", "Verified"),
    "unverified": ("b-unverified", "Unverified"),
    "reported-unverified": ("b-reported-unverified", "Reported – unverified"),
    "flag": ("b-flag", "Flag"),
    "Design choice": ("b-design", "Design choice"),
}


def load(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def esc(s):
    return html.escape(str(s))


def badge_for(text):
    t = str(text)
    for key in ("reported-unverified", "unverified", "verified", "flag"):
        if t == key or t.startswith(key + " "):
            cls, label = STATUS_LABEL[key]
            return f'<span class="badge {cls}">{esc(label)}</span>'
    if t.startswith("Design choice"):
        return f'<span class="badge b-design">Design choice</span>'
    return esc(t)


def cell(col, value):
    if col == "status":
        return badge_for(value)
    if col in ("source_url",):
        if not value:
            return '<td class="blank">no source</td>'
        host = value.split("/")[2]
        return f'<td><a href="{esc(value)}" target="_blank" rel="noopener">{esc(host)} ↗</a></td>'
    if value == "" or value is None:
        return '<td class="blank">blank – unverified</td>'
    return f"<td>{esc(value)}</td>"


def table(data, cols=None):
    cols = cols or data["columns"]
    head = "".join(f"<th>{esc(c.replace('_', ' '))}</th>" for c in cols)
    body = []
    for row in data["rows"]:
        tds = []
        for c in cols:
            v = row.get(c, "")
            if c == "source_url":
                link = cell(c, v)
                ref = row.get("reference_url")
                if ref:
                    host = ref.split("/")[2]
                    link = link[:-5] + f' · <a href="{esc(ref)}" target="_blank" rel="noopener">media ref ({esc(host)}) – unverified ↗</a></td>'
                tds.append(link)
            elif c == "status":
                tds.append(f"<td>{badge_for(v)}</td>")
            elif v == "" or v is None:
                if row.get("status") == "verified":
                    tds.append('<td class="blank">—</td>')
                else:
                    tds.append('<td class="blank">blank – unverified</td>')
            else:
                tds.append(f"<td>{esc(v)}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    return (
        '<div class="table-wrap"><table><thead><tr>'
        + head
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def page(slug, title, body, active):
    nav = "".join(
        f'<li><a href="{href}"{" class=active" if href == active else ""}>{esc(label)}</a></li>'
        for href, label in NAV
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · NBA Lines Research</title>
<link rel="stylesheet" href="assets/style.css">
</head><body>
<header><a class="brand" href="index.html">NBA Lines Research</a>
<nav><ul>{nav}</ul></nav></header>
<main>
<h1>{esc(title)}</h1>
{body}
</main>
<footer>Data as of {DATE}. Every value is verified against a linked official source or left blank and flagged.
Not betting advice. If gambling affects you, see <a href="responsible-gambling.html">Responsible Gambling</a>.</footer>
</body></html>
"""


def notice(text, bad=False):
    return f'<div class="notice{" bad" if bad else ""}">{text}</div>'


def build():
    sources = load("sources")
    rules = load("rules")
    helplines = load("helplines")
    strategies = load("strategies")
    gates = load("gates")
    correlation = load("correlation")
    leaderboard = load("leaderboard")
    repo = load("repo_review")
    flagged = load("flagged")

    n_verified = sum(1 for r in sources["rows"] if r["status"] == "verified")
    n_flag_total = len(flagged["rows"])
    n_strat_tested = sum(1 for r in strategies["rows"] if r["tested"] == "Yes")
    n_validated = 0

    pages = {}

    # ---- Home
    tiles = [
        ("executive-summary.html", "Executive Summary", "What the research found, and what it did not."),
        ("sources.html", "Sources", "Official sources and what was confirmed from each."),
        ("betting-rules.html", "Betting Rules", "Alberta market facts, and reported NBA restrictions (unverified)."),
        ("strategies.html", "Strategies", "Strategy register: single bets, parlays, player props, prop combos."),
        ("validation-gates.html", "Validation Gates", "The 9 gates every strategy must pass."),
        ("correlation.html", "Correlation", "Correlation method and status of each pair."),
        ("leaderboard.html", "Leaderboard", "Ranking rules and current standings."),
        ("responsible-gambling.html", "Responsible Gambling", "Verified Alberta helplines and self-exclusion."),
        ("repo-review.html", "Repo Review", "Line-by-line repository review and irregularities."),
        ("flagged.html", "Flagged for Review", "Everything unverified or conflicting, with links."),
    ]
    tile_html = "".join(
        f'<div class="card tile"><a href="{h}"><h3>{esc(t)}</h3><p>{esc(d)}</p></a></div>'
        for h, t, d in tiles
    )
    stats = [
        (str(n_verified), "Official sources verified"),
        (str(n_validated), "Strategies passing all gates"),
        (str(n_strat_tested), "Strategies tested"),
        (str(n_flag_total), "Items flagged for review"),
    ]
    stat_html = "".join(
        f'<div class="card"><div class="stat">{esc(v)}</div><div class="stat-label">{esc(l)}</div></div>'
        for v, l in stats
    )
    body = (
        '<p class="lede">A verification-first dashboard for NBA betting research. '
        "No strategy has passed validation, and no numeric NBA statistic or betting-line value is shown unless it is confirmed from an official source.</p>"
        + notice(
            "<strong>Bottom line:</strong> 0 strategies have passed the validation gates. "
            "The leaderboard is empty. No betting lines were originated and no performance (ROI, CLV, or correlation) is claimed. "
            "Official NBA statistics could not be retrieved from this environment, so the quantitative work is blocked. "
            "See <a href=\"flagged.html\">Flagged for Review</a>."
        )
        + f'<div class="grid">{stat_html}</div>'
        + f'<h2>Sections</h2><div class="grid">{tile_html}</div>'
    )
    pages["index.html"] = ("Home", body)

    # ---- Executive summary
    es = f"""
<p class="lede">Status as of {DATE}. Plain-language summary for review.</p>
<h2>1. What was asked</h2>
<ul class="points">
<li>Research and develop NBA betting strategies (single bets, parlays, player prop combinations), treated as a leaderboard competition.</li>
<li>Each strategy must pass validation gates, determine correlation values, and separate skill from luck.</li>
<li>Repo review, a GitHub Pages site, and line-by-line verification against official sources. Unverifiable values left blank and flagged.</li>
</ul>
<h2>2. What was delivered</h2>
<ul class="points">
<li>A verified source registry with {n_verified} official sources confirmed (<a href="sources.html">Sources</a>).</li>
<li>A strategy register of 8 hypotheses. None has been tested (<a href="strategies.html">Strategies</a>).</li>
<li>Nine validation gates, the correlation method, and an empty leaderboard with ranking rules (<a href="validation-gates.html">Gates</a>, <a href="correlation.html">Correlation</a>, <a href="leaderboard.html">Leaderboard</a>).</li>
<li>Repo review with 12 checks, including irregularities (<a href="repo-review.html">Repo Review</a>).</li>
</ul>
<h2>3. Key findings (verified)</h2>
<ul class="points">
<li>Play Alberta, the AGLC-run platform, shows an NBA betting tile (<a href="https://playalberta.ca/" target="_blank" rel="noopener">playalberta.ca ↗</a>).</li>
<li>Alberta iGaming operators may conduct registered activity from July 13, 2026. Registration and a commercial agreement are required (<a href="https://aglc.ca/gaming/igaming" target="_blank" rel="noopener">aglc.ca ↗</a>).</li>
<li>Registered iGaming advertising must reference responsible-gambling information, including 211 Alberta (<a href="https://aglc.ca/gaming/igaming" target="_blank" rel="noopener">aglc.ca ↗</a>).</li>
<li>Official helplines are confirmed: GameSense 1-833-447-7523; Self-Exclusion 1-844-468-8034; Addiction Helpline 1-866-332-2322 (<a href="responsible-gambling.html">details</a>).</li>
</ul>
<h2>4. Reported but NOT verified</h2>
<ul class="points">
<li>Media reports (October 16, 2026) say the NBA told sportsbooks to stop several bet types, including parlays with the under on the same player's stats, opening-tip winners, and unders for players expected to play under 12 minutes. No official NBA document was found, so these are flagged, not confirmed (<a href="betting-rules.html">Betting Rules</a>).</li>
</ul>
<h2>5. Limits of this work</h2>
<ul class="points">
<li><strong>No official NBA numeric data.</strong> The NBA stats and data endpoints did not return data from this environment. Correlation values and strategy metrics are blank.</li>
<li><strong>No odds or closing-line data.</strong> Without verified market prices, line origination and CLV tests cannot be run. Nothing here is a line or a pick.</li>
<li><strong>No edge is shown.</strong> No strategy has passed a single gate. Assumption to test, not a verified fact: sportsbook prices include a margin, so most strategies may fail the gates. A positive result would need out-of-sample, CLV, and multiple-testing evidence first.</li>
<li><strong>Rewards undefined.</strong> The brief asks for rewards for top strategies. No amount or funding is defined, and none is inferred (<a href="flagged.html">F-05</a>).</li>
</ul>
<h2>6. Decisions for the owner (flagged, not blocking)</h2>
<ul class="points">
<li>Provide an approved data path for official NBA data (for example, an accessible stats export), so the data gates can be run.</li>
<li>Add a license (none exists) and confirm reuse terms.</li>
<li>Confirm the conflicting Alberta statement (<a href="flagged.html">F-03</a>) and the unverified helpline (<a href="flagged.html">F-04</a>).</li>
</ul>
<h2>7. Responsible gambling</h2>
<p>Set limits before any real money is involved. Treat any betting as a cost, not income. If gambling is affecting you or someone you know, see <a href="responsible-gambling.html">Responsible Gambling</a>.</p>
"""
    pages["executive-summary.html"] = ("Executive Summary", es)

    # ---- Sources
    pages["sources.html"] = (
        "Sources",
        notice("Only rows marked <strong>Verified</strong> were checked against an official site. Unverified rows have blank values.")
        + table(sources),
    )

    # ---- Betting rules
    pages["betting-rules.html"] = (
        "Betting Rules",
        notice("Official values are in the first column. Media-reported restrictions are shown separately and are <strong>not verified</strong>.", bad=False)
        + table(rules, ["id", "item", "official_value", "reported_unverified", "status", "source_url"]),
    )

    # ---- Responsible gambling
    pages["responsible-gambling.html"] = (
        "Responsible Gambling",
        notice(
            "If gambling is affecting you, call the verified Alberta contacts below. "
            "Self-exclusion for AGLC-regulated casinos, racing centres, and registered iGaming platforms is available at selfexclusion.ca."
        )
        + table(helplines, ["id", "contact", "number_or_detail", "status", "source_url", "note"]),
    )

    # ---- Strategies
    strat_intro = (
        '<p class="lede">Strategy register. Each row is a hypothesis for testing, not a recommendation. '
        "No metric is shown because none has been tested.</p>"
    )
    strat_framework = """
<h2>Categories</h2>
<ul class="points">
<li><strong>Single bet:</strong> one game outcome (moneyline, spread, total).</li>
<li><strong>Parlay:</strong> two or more outcomes combined. Payout multiplies, so errors in correlation assumptions compound.</li>
<li><strong>Player prop:</strong> one player's statistic against a line.</li>
<li><strong>Prop combo:</strong> several props combined. Correlation between legs must be estimated (see <a href="correlation.html">Correlation</a>).</li>
</ul>
<h2>Skill vs. luck</h2>
<p>A strategy is "selectively skill based" only if it passes the gates on out-of-sample data, after pricing against a market baseline and correcting for the number of strategies tested. A short run of wins is not evidence of skill.</p>
"""
    pages["strategies.html"] = ("Strategies", strat_intro + table(strategies, ["id", "category", "hypothesis", "market_status", "tested", "sample_size", "roi", "clv", "gates_passed", "source_url"]) + strat_framework)

    # ---- Validation gates
    pages["validation-gates.html"] = (
        "Validation Gates",
        notice("A strategy ranks only if it passes all 9 gates. "
               "Gates marked <span class=\"badge b-design\">Design choice</span> are project rules, not external facts. "
               "Their thresholds are set by this project.")
        + table(gates),
    )

    # ---- Correlation
    pages["correlation.html"] = (
        "Correlation",
        notice("No correlation value has been computed. The data needed (official box scores) was not available.")
        + table(correlation)
        + """
<h2>Method (to run once verified data is available)</h2>
<ul class="points">
<li>Use only official box-score rows; measure correlations within a single game where the legs share the game.</li>
<li>Report sample size and a confidence interval with each value. Do not report a point estimate alone.</li>
<li>Compare the joint probability of a combo with the product of its legs. Any gap is the correlation effect that the sportsbook may already price.</li>
</ul>""",
    )

    # ---- Leaderboard
    lb_rows = table(leaderboard, ["rank", "strategy_id", "score", "gates_passed", "status", "source_url"])
    pages["leaderboard.html"] = (
        "Leaderboard",
        notice("<strong>Empty by design:</strong> 0 strategies have passed the validation gates. No rewards are awarded.")
        + lb_rows
        + f'<h2>Ranking rule</h2><p>{esc(leaderboard["ranking_rule"])}</p>',
    )

    # ---- Repo review
    pages["repo-review.html"] = (
        "Repo Review",
        notice("Line-by-line checks of <a href=\"https://github.com/sassnarep3-star/Own7\" target=\"_blank\" rel=\"noopener\">sassnarep3-star/Own7</a>. Irregularities are flagged.")
        + table(repo),
    )

    # ---- Flagged
    pages["flagged.html"] = (
        "Flagged for Review",
        notice("These items are published for owner review. They do <strong>not</strong> block the site. Blank values are intentional.", bad=True)
        + table(flagged),
    )

    for slug, (title, body) in pages.items():
        (DOCS / slug).write_text(page(slug, title, body, slug), encoding="utf-8")
    print(f"wrote {len(pages)} pages to {DOCS}")


if __name__ == "__main__":
    build()
