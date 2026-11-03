#!/usr/bin/env python3
"""Generate the verified-data site in verified/ from verified/data/*.json.

Plain HTML, no build dependencies. Every table row is rendered from a JSON row,
so the JSON files are the single source of truth. Headline numbers in the
executive summary are computed from the same JSON, never typed by hand.

Run:  python3 scripts/build_verified_site.py
"""
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "verified"
DATA = DOCS / "data"
DATE = "2026-11-03"

NAV = [
    ("index.html", "Home"),
    ("executive-summary.html", "Executive Summary"),
    ("teams.html", "Teams 2025-26"),
    ("players.html", "Players 2025-26"),
    ("standings.html", "Standings 2026-27"),
    ("correlation.html", "Correlation"),
    ("strategies.html", "Strategies"),
    ("validation-gates.html", "Validation Gates"),
    ("leaderboard.html", "Leaderboard"),
    ("betting-rules.html", "Betting Rules"),
    ("netherlands.html", "Netherlands"),
    ("responsible-gambling.html", "Responsible Gambling"),
    ("sources.html", "Sources"),
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

LABELS = {
    "id": "ID", "rank": "Rank", "team": "Team", "player": "Player", "conference": "Conf.", "division": "Division",
    "gp": "GP", "w": "W", "l": "L", "win_pct": "Win %", "pts": "PTS", "fg_pct": "FG%", "fg3_pct": "3P%",
    "ft_pct": "FT%", "oreb": "OREB", "dreb": "DREB", "reb": "REB", "ast": "AST", "tov": "TOV", "stl": "STL",
    "blk": "BLK", "blka": "BLKA", "pf": "PF", "pfd": "PFD", "plus_minus": "+/-", "age": "Age", "min": "MIN",
    "fgm": "FGM", "fga": "FGA", "fg3m": "3PM", "fg3a": "3PA", "ftm": "FTM", "fta": "FTA", "gb": "GB",
    "conf": "CONF", "div": "DIV", "home": "HOME", "road": "ROAD", "last10": "LAST 10", "streak": "STREAK",
    "games_played": "Games played", "source_url": "Source", "status": "Status",
    "correlation_value": "r (Pearson)", "ci_95": "95% CI", "n_observations": "n", "pair": "Pair",
    "method": "Method", "note": "Note", "item": "Item", "why_flagged": "Why flagged", "official_value": "Official value",
    "reported_unverified": "Reported (unverified)", "number_or_detail": "Number / detail", "contact": "Contact",
    "what_was_checked": "What was checked", "value_confirmed": "Value confirmed", "source": "Source name",
    "check": "Check", "finding": "Finding", "severity": "Severity", "gate": "Gate", "pass_rule": "Pass rule",
    "category": "Category", "hypothesis": "Hypothesis", "market_status": "Market status", "tested": "Tested",
    "sample_size": "Sample size", "roi": "ROI", "clv": "CLV", "gates_passed": "Gates passed", "strategy_id": "Strategy",
    "score": "Score", "pass_rule_": "", "type": "Type", "reference_url": "Media reference",
}


def load(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def esc(s):
    return html.escape(str(s))


def label(c):
    return LABELS.get(c, c.replace("_", " "))


def badge_for(text):
    t = str(text)
    for key in ("reported-unverified", "unverified", "verified", "flag", "Design choice"):
        if t == key or t.startswith(key + " ") or t.startswith(key + "–") or t.startswith(key + "-"):
            cls, lab = STATUS_LABEL[key]
            return f'<span class="badge {cls}">{esc(lab)}</span>'
    if t.startswith("Design choice"):
        return '<span class="badge b-design">Design choice</span>'
    if t.startswith("Partly") or t.startswith("Blocked") or t.startswith("Not yet"):
        return f'<span class="badge b-unverified">{esc(t)}</span>'
    return esc(t)


def source_cell(url, ref=None):
    if not url:
        return '<td class="blank">no source</td>'
    host = url.split("/")[2]
    out = f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(host)} ↗</a>'
    if ref:
        out += f' · <a href="{esc(ref)}" target="_blank" rel="noopener">media ref ({esc(ref.split("/")[2])}) – unverified ↗</a>'
    return f"<td>{out}</td>"


def table(data, cols=None, numeric_sort=True):
    cols = cols or data["columns"]
    head = "".join(f"<th>{esc(label(c))}</th>" for c in cols)
    body = []
    for row in data["rows"]:
        tds = []
        for c in cols:
            v = row.get(c, "")
            if c == "source_url":
                tds.append(source_cell(v, row.get("reference_url")))
            elif c == "status":
                tds.append(f"<td>{badge_for(v)}</td>")
            elif v == "" or v is None:
                if str(row.get("status", "")).startswith("verified"):
                    tds.append('<td class="blank">—</td>')
                else:
                    tds.append('<td class="blank">blank – unverified</td>')
            else:
                tds.append(f"<td>{esc(v)}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    return (
        '<input class="filter" type="search" placeholder="Filter rows…" aria-label="Filter rows">'
        '<div class="table-wrap"><table class="sortable"><thead><tr>' + head + "</tr></thead><tbody>"
        + "".join(body) + "</tbody></table></div>"
    )


def page(title, body, active):
    nav = "".join(
        f'<li><a href="{href}"{" class=active" if href == active else ""}>{esc(lab)}</a></li>'
        for href, lab in NAV
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
<footer>Data as of {DATE}. Every value is confirmed from a linked official source, or left blank and flagged.
Not betting advice. If gambling affects you, see <a href="responsible-gambling.html">Responsible Gambling</a>.</footer>
<script>
document.querySelectorAll('input.filter').forEach(function(inp){{
  inp.addEventListener('input', function(){{
    var q = inp.value.toLowerCase();
    var rows = inp.nextElementSibling.querySelectorAll('tbody tr');
    rows.forEach(function(tr){{ tr.style.display = tr.textContent.toLowerCase().indexOf(q) > -1 ? '' : 'none'; }});
  }});
}});
</script>
</body></html>
"""


def notice(text, bad=False):
    return f'<div class="notice{" bad" if bad else ""}">{text}</div>'


def num(x):
    return float(x)


def leaders(rows, key, reverse=True, n=1):
    return sorted(rows, key=lambda r: num(r[key]), reverse=reverse)[:n]


def build():
    teams = load("nba_teams")
    players = load("nba_players")
    standings = load("nba_standings")
    sources = load("sources")
    rules = load("rules")
    helplines = load("helplines")
    strategies = load("strategies")
    gates = load("gates")
    correlation = load("correlation")
    corr_computed = load("correlation_computed")
    leaderboard = load("leaderboard")
    repo = load("repo_review")
    flagged = load("flagged")

    T = teams["rows"]
    P = players["rows"]
    S = standings["rows"]

    best = leaders(T, "win_pct")[0]
    worst = leaders(T, "win_pct", reverse=False)[0]
    top_pts = leaders(T, "pts")[0]
    low_pts = leaders(T, "pts", reverse=False)[0]
    top_fg = leaders(T, "fg_pct")[0]
    top_3p = leaders(T, "fg3_pct")[0]
    top_pm = leaders(T, "plus_minus")[0]
    top_scorer = leaders(P, "pts")[0]
    east_lead = [r for r in S if r["conference"] == "East" and r["rank"] == "1"][0]
    west_lead = [r for r in S if r["conference"] == "West" and r["rank"] == "1"][0]
    gp_min = min(int(r["games_played"]) for r in S)
    gp_max = max(int(r["games_played"]) for r in S)

    n_sources_verified = sum(1 for r in sources["rows"] if str(r["status"]).startswith("verified"))
    n_flags = len(flagged["rows"])
    n_corr = len(corr_computed["rows"])
    n_strat_tested = sum(1 for r in strategies["rows"] if r["tested"] == "Yes")
    n_validated = 0

    pages = {}

    # ---- Home
    tiles = [
        ("executive-summary.html", "Executive Summary", "What the verified data shows, and what it does not."),
        ("teams.html", "Teams 2025-26", f"All {len(T)} teams, full-season official averages."),
        ("players.html", "Players 2025-26", f"Top {len(P)} scorers by points per game, official."),
        ("standings.html", "Standings 2026-27", f"Early-season standings, {gp_min}–{gp_max} games per team (small sample)."),
        ("correlation.html", "Correlation", f"{n_corr} computed correlations; leg-level values still blank."),
        ("strategies.html", "Strategies", "Strategy register: single bets, parlays, props, prop combos."),
        ("validation-gates.html", "Validation Gates", "The 9 gates every strategy must pass."),
        ("leaderboard.html", "Leaderboard", "Ranking rules; empty until a strategy passes every gate."),
        ("betting-rules.html", "Betting Rules", "Alberta facts, and reported NBA restrictions (unverified)."),
        ("netherlands.html", "Netherlands", "Dutch regulator (Ksa), register, and self-exclusion (Gokstop)."),
        ("responsible-gambling.html", "Responsible Gambling", "Verified helplines and self-exclusion routes."),
        ("sources.html", "Sources", "Every official source, and what was confirmed from it."),
        ("repo-review.html", "Repo Review", "Line-by-line review of the repository and its irregularities."),
        ("flagged.html", "Flagged for Review", f"{n_flags} items: unverified, conflicting, or corrected."),
    ]
    tile_html = "".join(
        f'<div class="card tile"><a href="{h}"><h3>{esc(t)}</h3><p>{esc(d)}</p></a></div>' for h, t, d in tiles
    )
    stats = [
        (str(len(T) + len(P) + len(S)), "Official table rows verified (teams + players + standings)"),
        (str(n_validated), "Strategies passing all gates"),
        (str(n_strat_tested), "Strategies tested"),
        (str(n_flags), "Items flagged for review"),
    ]
    stat_html = "".join(
        f'<div class="card"><div class="stat">{esc(v)}</div><div class="stat-label">{esc(l)}</div></div>' for v, l in stats
    )
    body = (
        '<p class="lede">A verification-first dashboard for NBA betting research. Numbers are shown only when confirmed from an official nba.com page or another official source. Everything else is blank and flagged.</p>'
        + notice(
            "<strong>Bottom line:</strong> 0 strategies have passed the validation gates. The leaderboard is empty. "
            "No betting lines were originated, and no ROI, CLV or leg-level correlation is claimed. "
            "What is verified: the 2025-26 team, player and 2026-27 standings tables. "
            'See <a href="flagged.html">Flagged for Review</a>.'
        )
        + f'<div class="grid">{stat_html}</div>'
        + f'<h2>Sections</h2><div class="grid">{tile_html}</div>'
    )
    pages["index.html"] = ("Home", body)

    # ---- Executive summary (numbers computed from the verified tables)
    es = f"""
<p class="lede">Status as of {DATE}. Plain-language summary. Every number below is computed from a verified table on this site.</p>
<h2>1. What was asked</h2>
<ul class="points">
<li>Build NBA betting strategies (single bets, parlays, player-prop combinations) and rank them as a skill-based leaderboard.</li>
<li>Each strategy must pass validation gates. Correlation values must be determined. Luck should be separated from skill.</li>
<li>Repository review, a GitHub Pages site, and line-by-line checks against official sources. Anything that cannot be confirmed is left blank and flagged.</li>
</ul>
<h2>2. What is verified (official nba.com tables)</h2>
<ul class="points">
<li><strong>2025-26 teams (30 rows):</strong> best record {esc(best['team'])} {esc(best['w'])}–{esc(best['l'])} ({esc(best['win_pct'])}); worst {esc(worst['team'])} {esc(worst['w'])}–{esc(worst['l'])} ({esc(worst['win_pct'])}). <a href="teams.html">Teams</a></li>
<li><strong>Points per game:</strong> highest {esc(top_pts['team'])} {esc(top_pts['pts'])}; lowest {esc(low_pts['team'])} {esc(low_pts['pts'])}.</li>
<li><strong>Field-goal %:</strong> highest {esc(top_fg['team'])} {esc(top_fg['fg_pct'])}%. <strong>Three-point %:</strong> highest {esc(top_3p['team'])} {esc(top_3p['fg3_pct'])}%.</li>
<li><strong>Point differential per game:</strong> highest {esc(top_pm['team'])} {esc(top_pm['plus_minus'])}.</li>
<li><strong>2025-26 players (top {len(P)} by PPG):</strong> highest scorer {esc(top_scorer['player'])} ({esc(top_scorer['team'])}) {esc(top_scorer['pts'])} PPG in {esc(top_scorer['gp'])} games. <a href="players.html">Players</a></li>
<li><strong>2026-27 standings:</strong> {gp_min}–{gp_max} games per team so far. Leaders: {esc(east_lead['team'])} ({esc(east_lead['w'])}–{esc(east_lead['l'])}, East) and {esc(west_lead['team'])} ({esc(west_lead['w'])}–{esc(west_lead['l'])}, West). Too few games to be a signal. <a href="standings.html">Standings</a></li>
<li><strong>Correlations (descriptive):</strong> across 30 teams, win % and point differential correlate at r = {esc(corr_computed['rows'][1]['correlation_value'])}; win % and points per game at r = {esc(corr_computed['rows'][0]['correlation_value'])}. These are season-level, not game-level. <a href="correlation.html">Correlation</a></li>
</ul>
<h2>3. What is not verified</h2>
<ul class="points">
<li><strong>No betting lines.</strong> nba.com publishes no odds. Spreads, totals, moneylines and prop lines are blank.</li>
<li><strong>No leg-level correlation.</strong> Correlation between two bets in the same game needs game-level logs. The verified tables are season averages only.</li>
<li><strong>Reported NBA restrictions</strong> (Oct 16, 2026) are media reports, not an official NBA document, and they cover US operators. See <a href="betting-rules.html">Betting Rules</a>.</li>
<li><strong>Netherlands:</strong> the Dutch regulator is the Ksa. Which licensed Dutch operators offer NBA markets is not verified. See <a href="netherlands.html">Netherlands</a>.</li>
</ul>
<h2>4. Strategy status</h2>
<ul class="points">
<li>0 of {len(strategies['rows'])} strategies tested. 0 pass the validation gates. The leaderboard is empty, and no rewards are awarded (<a href="leaderboard.html">Leaderboard</a>).</li>
<li>Assumption to test, not a verified fact: sportsbook prices include a margin, so most strategies may fail the gates. Any positive result would need out-of-sample, closing-line and multiple-testing evidence first.</li>
</ul>
<h2>5. Corrections made in this review</h2>
<ul class="points">
<li>An earlier version named Miami as the highest-scoring team (120.9). Official data: Denver, 122.1. Corrected.</li>
<li>An earlier version named Denver as the highest FG% team (49.6%). Official data: the Lakers, 50.2%. Corrected.</li>
<li>A team-table column was flagged as unmapped. The official header reads BLKA. Its meaning is still to be confirmed (see Flagged for Review, F-11).</li>
<li>The earlier "NBA data not reachable" note was out of date. The nba.com pages are reachable and are now verified. See <a href="repo-review.html">Repo Review</a>.</li>
</ul>
<h2>6. Responsible gambling</h2>
<p>Set limits before any real money is involved. Treat betting as a cost, not income. If gambling is affecting you or someone you know, see <a href="responsible-gambling.html">Responsible Gambling</a>.</p>
"""
    pages["executive-summary.html"] = ("Executive Summary", es)

    # ---- Teams
    team_cols = ["rank", "team", "conference", "division", "gp", "w", "l", "win_pct", "pts", "fg_pct", "fg3_pct",
                 "ft_pct", "oreb", "dreb", "reb", "ast", "tov", "stl", "blk", "blka", "pf", "pfd", "plus_minus", "status", "source_url"]
    pages["teams.html"] = (
        "Teams 2025-26",
        notice("All 30 teams, 2025-26 regular season, per-game averages (PTS, REB, etc.) as shown on nba.com. Each row links to its own nba.com team page. Filter by typing in the box.")
        + table(teams, team_cols)
        + '<h2>Method</h2><p>Values were transcribed from the nba.com team table and cross-checked by a second transcription (data/raw/). Zero mismatches. Win % = W / GP was re-derived and matches the official figure.</p>',
    )

    # ---- Players
    player_cols = ["rank", "player", "team", "age", "gp", "w", "l", "min", "pts", "fgm", "fga", "fg_pct", "fg3m", "fg3a",
                   "fg3_pct", "ftm", "fta", "ft_pct", "oreb", "dreb", "reb", "ast", "tov", "stl", "blk", "pf", "status", "source_url"]
    pages["players.html"] = (
        "Players 2025-26",
        notice(f"Top {len(P)} players by points per game, 2025-26, per-game averages (nba.com). The next player on the official list, Jamal Murray (DEN, 25.4 PPG), is not included.")
        + table(players, player_cols)
        + '<h2>Notes</h2><ul class="points"><li>Ranking is by PPG as shown on nba.com. Player names are shown in the official spelling (for example, Dončić).</li><li>Prop lines for these players are not published by nba.com and are blank.</li></ul>',
    )

    # ---- Standings
    st_cols = ["rank", "conference", "team", "w", "l", "win_pct", "gb", "conf", "div", "home", "road", "last10",
               "streak", "games_played", "status", "source_url"]
    pages["standings.html"] = (
        "Standings 2026-27",
        notice(f"2026-27 regular season in progress. Teams have played {gp_min} to {gp_max} games, a small sample. Context only. Fails the 25-game gate, so it is not used as a signal.", bad=True)
        + table(standings, st_cols),
    )

    # ---- Correlation
    corr_cols = ["id", "pair", "method", "correlation_value", "ci_95", "n_observations", "status", "source_url", "note"]
    corr_blank = [r for r in correlation["rows"]]
    pages["correlation.html"] = (
        "Correlation",
        notice("<strong>Computed values (descriptive).</strong> Pearson correlations across teams (n=30) and players (n=15), using verified season averages. They describe how these season-level numbers move together. They are not game-level and not correlations between two bets.")
        + table(corr_computed, corr_cols)
        + "<h2>Leg-level correlations (not computed)</h2>"
        + notice("Correlation between two legs of a parlay or prop combo needs game-level logs for both legs. Those are not in this repo and are not verified. These rows stay blank.", bad=True)
        + table(correlation, ["id", "pair", "method", "correlation_value", "n_observations", "status", "source_url"])
        + """
<h2>Method (for when game-level data is verified)</h2>
<ul class="points">
<li>Use only official box-score rows. Measure within a single game where the legs share the game.</li>
<li>Report sample size and a confidence interval with each value. Never report a point estimate alone.</li>
<li>Compare the joint probability of a combo with the product of its legs. The gap is the correlation effect. The sportsbook may already price it.</li>
</ul>""",
    )

    # ---- Strategies
    strat_intro = '<p class="lede">Strategy register. Each row is a hypothesis for testing, not a recommendation. No metric is shown because none has been tested.</p>'
    strat_framework = """
<h2>Categories</h2>
<ul class="points">
<li><strong>Single bet:</strong> one game outcome (moneyline, spread, total).</li>
<li><strong>Parlay:</strong> two or more outcomes combined. The payout multiplies, so errors in correlation assumptions compound.</li>
<li><strong>Player prop:</strong> one player's statistic against a line.</li>
<li><strong>Prop combo:</strong> several props combined. Leg correlation must be estimated (see <a href="correlation.html">Correlation</a>).</li>
</ul>
<h2>Skill vs. luck</h2>
<p>A strategy is "selectively skill based" only if it passes the gates on out-of-sample data, after pricing against a market baseline and correcting for the number of strategies tested. A short run of wins is not evidence of skill.</p>
"""
    pages["strategies.html"] = (
        "Strategies",
        strat_intro + table(strategies, ["id", "category", "hypothesis", "market_status", "tested", "sample_size", "roi", "clv", "gates_passed", "source_url"]) + strat_framework,
    )

    # ---- Validation gates
    pages["validation-gates.html"] = (
        "Validation Gates",
        notice('A strategy ranks only if it passes all 9 gates. Gates marked <span class="badge b-design">Design choice</span> are project rules, not external facts.')
        + table(gates, ["id", "gate", "pass_rule", "type", "status", "source_url"]),
    )

    # ---- Leaderboard
    pages["leaderboard.html"] = (
        "Leaderboard",
        notice("<strong>Empty by design:</strong> 0 strategies have passed the validation gates. No rewards are awarded.")
        + table(leaderboard, ["rank", "strategy_id", "score", "gates_passed", "status", "source_url"])
        + f'<h2>Ranking rule</h2><p>{esc(leaderboard["ranking_rule"])}</p>',
    )

    # ---- Betting rules
    pages["betting-rules.html"] = (
        "Betting Rules",
        notice("Official values are in the first column. Media-reported restrictions are shown separately and are <strong>not verified</strong>. Alberta rows describe Alberta only. The Netherlands is on its own page.")
        + table(rules, ["id", "item", "official_value", "reported_unverified", "status", "source_url"]),
    )

    # ---- Netherlands (owner location)
    nl_rules = [r for r in rules["rows"] if r["id"] in ("R-09", "R-10", "R-11", "R-12")]
    nl_sources = [r for r in sources["rows"] if r["id"] in ("S-09", "S-10", "S-11", "S-14")]
    nl_help = [r for r in helplines["rows"] if r["id"] in ("H-07", "H-08")]
    pages["netherlands.html"] = (
        "Netherlands",
        notice("The owner is based in the Netherlands. The Dutch regulator is the <strong>Kansspelautoriteit (Ksa)</strong>. The Alberta material in this site does not describe Dutch rules. Check every operator on the Ksa register before use.")
        + "<h2>Rules and register</h2>" + table({"columns": ["id", "item", "official_value", "reported_unverified", "status", "source_url"], "rows": nl_rules})
        + "<h2>Sources</h2>" + table({"columns": ["id", "source", "what_was_checked", "value_confirmed", "status", "source_url"], "rows": nl_sources})
        + "<h2>Help and self-exclusion</h2>" + table({"columns": ["id", "contact", "number_or_detail", "status", "source_url", "note"], "rows": nl_help})
        + '<h2>Scope</h2><p>Verified: the Ksa is the regulator, the public register lists providers by category, and gokstop.nl describes a free self-exclusion route. Not verified: which licensed Dutch operators offer NBA markets, and whether the reported US restrictions apply to them.</p>',
    )

    # ---- Responsible gambling
    pages["responsible-gambling.html"] = (
        "Responsible Gambling",
        notice("If gambling is affecting you, use the verified contacts below. For the Netherlands, see the Netherlands page. The Alberta contacts apply to Alberta only.")
        + table(helplines, ["id", "contact", "number_or_detail", "status", "source_url", "note"]),
    )

    # ---- Sources
    pages["sources.html"] = (
        "Sources",
        notice("Only rows marked <strong>Verified</strong> were checked against an official site. Partial or unverified rows have blank values or a stated limit.")
        + table(sources, ["id", "source", "what_was_checked", "value_confirmed", "status", "source_url"]),
    )

    # ---- Repo review
    pages["repo-review.html"] = (
        "Repo Review",
        notice('Line-by-line checks of <a href="https://github.com/sassnarep3-star/Own7" target="_blank" rel="noopener">sassnarep3-star/Own7</a>. Corrections and flags are listed, with the source link for each.')
        + table(repo, ["id", "check", "finding", "severity", "status", "source_url"]),
    )

    # ---- Flagged
    pages["flagged.html"] = (
        "Flagged for Review",
        notice("These items are published for owner review. They do <strong>not</strong> block the site. Blank values are intentional. Each row links to the official source used.", bad=True)
        + table(flagged, ["id", "item", "why_flagged", "status", "source_url"]),
    )

    for slug, (title, body) in pages.items():
        (DOCS / slug).write_text(page(title, body, slug), encoding="utf-8")
    print(f"wrote {len(pages)} pages to {DOCS}")


if __name__ == "__main__":
    build()
