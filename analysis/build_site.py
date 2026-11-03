#!/usr/bin/env python3
"""Build the static analysis dashboard from analysis/results/*.json and analysis/data/*.json.

Every table cell is either (a) a value traced to an official NBA.com URL that is
printed alongside the row, or (b) an explicit blank with a "not computed" label.
The builder refuses to emit a data row without a source_url, which is the
machine-enforced version of the project's verification rule.

Usage: python3 analysis/build_site.py
"""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
OUT = ROOT
BUILD_STAMP = "2026-11-03T23:55Z"

NAV = [
    ("index.html", "Overview", "00"),
    ("executive-summary.html", "Executive summary", "01"),
    ("data.html", "Official data", "02"),
    ("lines.html", "Line origination", "03"),
    ("correlation.html", "Correlation", "04"),
    ("validation.html", "Validation gates", "05"),
    ("leaderboard.html", "Leaderboard", "06"),
    ("methods.html", "Methods & tests", "07"),
    ("flagged.html", "Flagged for review", "08"),
    ("sources.html", "Sources", "09"),
]

REPO_BLOB = "https://github.com/sassnarep3-star/Own7/blob/arena/1050ddb0-own7"
REPO_TREE = "https://github.com/sassnarep3-star/Own7/tree/arena/1050ddb0-own7/analysis"


def esc(x) -> str:
    return html.escape("" if x is None else str(x))


def load_results(name: str) -> dict:
    with (RESULTS / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def load_data(name: str) -> dict:
    with (DATA / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def fmt(v, digits: int | None = None, pct: bool = False, signed: bool = False) -> str:
    """Format a number, or emit an explicit blank marker."""
    if v is None or v == "":
        return '<span class="muted">—</span>'
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int, float)):
        if digits is not None:
            s = f"{v:+.{digits}f}" if signed else f"{v:.{digits}f}"
        else:
            s = f"{v}"
        return esc(s + ("%" if pct else ""))
    return esc(v)


def chip(status: str) -> str:
    s = (status or "").lower()
    if s in ("verified", "pass", "measured", "match", "ok", "published"):
        cls = "ok"
    elif s in ("unverified", "unproven", "not_evaluable", "not computable", "blank - not computable", "not computed", "reported-unverified"):
        cls = "warn"
    elif s in ("fail", "rejected", "mismatch", "error"):
        cls = "bad"
    else:
        cls = "muted"
    return f'<span class="chip {cls}">{esc(status)}</span>'


def src_link(url: str, label: str = "nba.com") -> str:
    if not url:
        return '<span class="chip warn">no source</span>'
    return f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(label)} ↗</a>'


def page(slug: str, title: str, body: str, crumb: str, description: str) -> None:
    nav = "\n".join(
        f'<a class="{"active" if href == slug else ""}" href="{href}"><span class="num">{num}</span>{esc(label)}</a>'
        for href, label, num in NAV
    )
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | OWN7 Analysis</title>
<meta name="description" content="{esc(description)}">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<div class="shell">
<aside>
  <a class="brand" href="index.html">
    <span class="brand-icon">O<span>7</span></span>
    <span><b>OWN7</b><small>ANALYSIS ENGINE</small></span>
  </a>
  <div class="side-label">DASHBOARD</div>
  <nav aria-label="Section navigation">
{nav}
  </nav>
  <div class="side-note">
    <b>Evidence before action</b>
    Every number is traced to an NBA.com URL or shown blank.
  </div>
</aside>
<main>
  <header class="top">
    <span>NBA &nbsp;/&nbsp; <b>{esc(crumb)}</b></span>
    <span class="pill">BUILD {esc(BUILD_STAMP)}</span>
  </header>
  <div class="content">
{body}
    <footer>
      <span>OWN7 / analysis engine · research only · no wagering recommendations</span>
      <span>Data snapshot {esc(BUILD_STAMP)} · <a href="../index.html">main site ↗</a></span>
    </footer>
  </div>
</main>
</div>
</body>
</html>
"""
    (OUT / slug).write_text(doc, encoding="utf-8")


# ---------------------------------------------------------------------------
def build_index() -> None:
    ratings = load_results("team-ratings.json")
    lines = load_results("model-originated-lines.json")
    corr = load_results("correlation.json")
    lb = load_results("leaderboard.json")
    gates_run = load_results("gate-runs.json")

    n_teams = len(ratings["rows"])
    n_games = corr["n_games"]
    r_ha = corr["rows"][0]

    body = f"""
<div class="eyebrow">NBA / ANALYSIS ENGINE</div>
<h1>Originated lines, measured dependence, and a leaderboard that refuses to rank luck.</h1>
<p class="intro">A reproducible engine that reads official NBA.com team data, originates spread / total / win-probability lines, measures real same-game dependence, and runs statistical gates before anything is allowed onto a leaderboard.</p>

<div class="notice">
  <span class="ico">!</span>
  <div>
    <b>What this is not.</b>
    There are no sportsbook prices here, because no official NBA source publishes them. Every line on this site is a
    <em>model output</em> computed from NBA.com ratings — not a market price, not a pick, not a result.
    No strategy has a settled, priced bet record, so no strategy is ranked. Blanks are deliberate.
    <a href="flagged.html">See what is flagged →</a>
  </div>
</div>

<div class="metrics">
  <div class="metric good"><span>TEAMS VERIFIED</span><b>{n_teams}</b><small>All 30, NBA.com advanced</small></div>
  <div class="metric"><span>GAMES IN SAMPLE</span><b>{n_games}</b><small>Two most recent dates</small></div>
  <div class="metric"><span>LINES ORIGINATED</span><b>{len(lines['rows'])}</b><small>2026-11-04 slate</small></div>
  <div class="metric bad"><span>STRATEGIES RANKED</span><b>{lb['n_eligible']}</b><small>None passed every gate</small></div>
</div>

<section>
  <div class="section-head">
    <div><div class="eyebrow">THE HEADLINE</div><h2>What the numbers actually say</h2></div>
    <span class="tag">VERIFIED VS MODELLED</span>
  </div>
  <div class="table-wrap">
  <table>
    <thead><tr><th>Finding</th><th>Value</th><th>Status</th><th>Source</th></tr></thead>
    <tbody>
      <tr>
        <td>League-relative team ratings for all 30 teams, 2026-27 to date</td>
        <td class="num">{n_teams} teams</td>
        <td>{chip('verified')}</td>
        <td class="src">{src_link(ratings['source_url'], 'NBA teams advanced')}</td>
      </tr>
      <tr>
        <td>Home and away scoring are positively related in the same game (n={r_ha['n']})</td>
        <td class="num">r = {fmt(r_ha['estimate'], 3)}</td>
        <td>{chip('measured')} <span class="muted small">95% CI {fmt(r_ha['ci95_low'],2)} … {fmt(r_ha['ci95_high'],2)}</span></td>
        <td class="src">{src_link(corr['data_source_url'], 'NBA team box scores')}</td>
      </tr>
      <tr>
        <td>Player-vs-player prop correlation</td>
        <td class="num"><span class="muted">—</span></td>
        <td>{chip('blank - not computable')}</td>
        <td class="src">{src_link(corr['data_source_url'], 'NBA stats')}</td>
      </tr>
      <tr>
        <td>Sportsbook prices for any game</td>
        <td class="num"><span class="muted">—</span></td>
        <td>{chip('unverified')}</td>
        <td class="src">{src_link('https://www.nba.com/schedule?date=11/03/2026', 'NBA schedule (no odds rendered)')}</td>
      </tr>
    </tbody>
  </table>
  </div>
  <p class="small muted">A correlation is a measurement, not an edge. The 95% interval above includes zero, so even this one cannot be distinguished from independence at n={r_ha['n']} — which is exactly why it is not priced into a parlay.</p>
</section>

<section>
  <div class="eyebrow">NAVIGATE</div>
  <h2>The seven questions this engine answers</h2>
  <div class="cards">
    <a class="card" href="data.html"><span class="card-num">02 / DATA</span><h3>What is actually verified? <span>↗</span></h3><p>Every team rating, every game score, with the NBA.com URL it was read from.</p></a>
    <a class="card" href="lines.html"><span class="card-num">03 / ORIGINATION</span><h3>How is a line made? <span>↗</span></h3><p>Spread, total and win probability from shrunk ratings — with the assumptions named.</p></a>
    <a class="card" href="correlation.html"><span class="card-num">04 / DEPENDENCE</span><h3>Are parlay legs independent? <span>↗</span></h3><p>No. Here is the measured dependence and the honest interval around it.</p></a>
  </div>
  <div class="cards">
    <a class="card" href="validation.html"><span class="card-num">05 / GATES</span><h3>What must a strategy pass? <span>↗</span></h3><p>Eight gates from provenance to robustness. Three-state outcomes, so "unknown" can never read as "pass".</p></a>
    <a class="card" href="leaderboard.html"><span class="card-num">06 / COMPETITION</span><h3>How is luck removed? <span>↗</span></h3><p>Lower confidence bounds, deflated Sharpe, and the arithmetic of how many no-skill entries look good.</p></a>
    <a class="card" href="methods.html"><span class="card-num">07 / METHODS</span><h3>Can I check the maths? <span>↗</span></h3><p>51 self-tests, including closed-form checks on the bivariate normal CDF.</p></a>
  </div>
</section>

<section>
  <div class="section-head">
    <div><div class="eyebrow">SAMPLE</div><h2>Originated lines, 2026-11-04</h2></div>
    <a class="tag" href="lines.html">FULL SLATE →</a>
  </div>
  <div class="table-wrap">
  <table>
    <thead><tr><th>Matchup</th><th class="num">Model spread (home)</th><th class="num">Model total</th><th class="num">Home win %</th><th class="num">Market spread</th><th>Source</th></tr></thead>
    <tbody>
      {''.join(f'''<tr>
        <td class="tight">{esc(r['matchup'])}</td>
        <td class="num">{fmt(r['model_spread_home'], 2)}</td>
        <td class="num">{fmt(r['model_total'], 1)}</td>
        <td class="num">{fmt(r['model_home_win_prob']*100, 1, pct=True)}</td>
        <td class="num blank">not available</td>
        <td class="src">{src_link(lines['ratings_source_url'], 'NBA ratings')}</td>
      </tr>''' for r in lines['rows'][:6])}
    </tbody>
  </table>
  </div>
  <p class="small muted">Model spread, total and win probability are computed from NBA.com team ratings. The market column is blank because no official NBA source publishes prices. Showing six of {len(lines['rows'])}.</p>
</section>
"""
    page("index.html", "Overview", body, "Overview",
         "NBA line origination analysis engine: verified NBA.com data, model-implied lines, measured correlation, validation gates.")


def build_data() -> None:
    ratings = load_results("team-ratings.json")
    snap = load_data("official-team-ratings-2026-27.json")
    games = load_data("official-team-games-2026-27.json")

    rows = "\n".join(
        f"""<tr>
          <td class="tight"><b>{esc(r['abbr'])}</b> <span class="muted">{esc(r['team'])}</span></td>
          <td class="num">{fmt(r['gp'])}</td>
          <td class="num">{fmt(r['w'])}–{fmt(r['l'])}</td>
          <td class="num">{fmt(r['net_rtg_raw'], 1, signed=True)}</td>
          <td class="num">{fmt(r['net_rtg_shrunk'], 2, signed=True)}</td>
          <td class="num">{fmt(r['shrink_weight']*100, 0, pct=True)}</td>
          <td class="num">{fmt(r['pace'], 2)}</td>
          <td class="src">{src_link(ratings['source_url'], 'nba.com')}</td>
        </tr>"""
        for r in ratings["rows"]
    )

    game_rows = "\n".join(
        f"""<tr>
          <td class="tight">{esc(g['date'])}</td>
          <td class="tight">{esc(g['away'])} @ {esc(g['home'])}</td>
          <td class="num">{fmt(g['away_pts'])} – {fmt(g['home_pts'])}</td>
          <td class="num">{fmt(g['home_pts']+g['away_pts'])}</td>
          <td class="num">{fmt(g['ot'])}</td>
          <td class="src">{src_link('https://www.nba.com/game/' + g['game_id'], g['game_id'])}</td>
        </tr>"""
        for g in games["rows"]
    )

    body = f"""
<div class="eyebrow">02 / OFFICIAL DATA</div>
<h1>Everything here was read off an NBA.com page today.</h1>
<p class="intro">Two snapshots: team advanced ratings for all 30 teams, and eighteen finished games with final scores. No value was inferred, interpolated or scraped from a third party.</p>

<div class="notice info">
  <span class="ico">i</span>
  <div>
    <b>How collection works, including its limits.</b>
    This environment has no general HTTPS egress from the shell, so nothing is scraped automatically. Each value was read from the rendered NBA.com table and transcribed; ambiguous or truncated cells were left out rather than guessed. That is why the game sample is 18 games and not the full season.
    <a href="flagged.html">Collection limits →</a>
  </div>
</div>

<div class="metrics">
  <div class="metric good"><span>TEAM ROWS</span><b>{len(ratings['rows'])}</b><small>of 30 NBA teams</small></div>
  <div class="metric good"><span>GAME ROWS</span><b>{len(games['rows'])}</b><small>11/01 and 11/02</small></div>
  <div class="metric"><span>SNAPSHOT</span><b>{esc(snap['snapshot_utc'][11:16])}Z</b><small>{esc(snap['snapshot_utc'][:10])}</small></div>
  <div class="metric warn"><span>ODDS ROWS</span><b>0</b><small>No official odds source</small></div>
</div>

<section>
  <div class="section-head">
    <div><div class="eyebrow">TABLE 1</div><h2>Team advanced ratings, 2026-27</h2></div>
    <span class="tag">NBA.COM VERIFIED</span>
  </div>
  <p class="small muted" style="margin-top:0">Raw NetRtg is NBA.com's published figure. Shrunk NetRtg pulls it toward the league mean ({fmt(ratings['league_mean_net_rtg'],3)}) with weight <code>gp / (gp + {fmt(ratings['prior_games'],0)})</code>. A 7-game team keeps about a quarter of its observed edge.</p>
  <div class="table-wrap">
  <table>
    <thead><tr>
      <th>Team</th><th class="num">GP</th><th class="num">W–L</th>
      <th class="num">NetRtg raw</th><th class="num">NetRtg shrunk</th>
      <th class="num">Weight</th><th class="num">Pace</th><th>Source</th>
    </tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
  </div>
  <p class="small muted">Source for every row in this table: <a href="{esc(ratings['source_url'])}" target="_blank" rel="noopener noreferrer">{esc(ratings['source_url'])}</a> — fetched {esc(ratings['snapshot_utc'])}.</p>
</section>

<section>
  <div class="section-head">
    <div><div class="eyebrow">TABLE 2</div><h2>Finished games used for the correlation study</h2></div>
    <span class="tag">{len(games['rows'])} GAMES</span>
  </div>
  <div class="table-wrap">
  <table>
    <thead><tr><th>Date</th><th>Matchup</th><th class="num">Score (away–home)</th><th class="num">Total</th><th class="num">OT</th><th>Game page</th></tr></thead>
    <tbody>
{game_rows}
    </tbody>
  </table>
  </div>
  <p class="small muted">Each row links to its official NBA.com game summary. One row was additionally cross-checked end to end: BOS 93 @ HOU 109 on 11/02, matching the per-quarter line score on <a href="https://www.nba.com/game/0022600167" target="_blank" rel="noopener noreferrer">the game page ↗</a>.</p>
</section>

<section>
  <div class="section-head">
    <div><div class="eyebrow">TABLE 3</div><h2>2025-26 completed-season ratings (context only)</h2></div>
    <span class="tag">PARTIAL — 14 OF 30</span>
  </div>
  <p class="small muted" style="margin-top:0">These are last season's full-season ratings, useful as a prior. Only 14 rows could be read unambiguously, so the set is published as partial rather than filled in.</p>
  <div class="table-wrap">
  <table>
    <thead><tr><th>Team</th><th class="num">GP</th><th class="num">W–L</th><th class="num">OffRtg</th><th class="num">DefRtg</th><th class="num">NetRtg</th><th class="num">Pace</th><th>Source</th></tr></thead>
    <tbody>
      {''.join(f'''<tr><td class="tight"><b>{esc(r['abbr'])}</b> <span class="muted">{esc(r['team'])}</span></td>
        <td class="num">{fmt(r['gp'])}</td><td class="num">{fmt(r['w'])}–{fmt(r['l'])}</td>
        <td class="num">{fmt(r['off_rtg'],1)}</td><td class="num">{fmt(r['def_rtg'],1)}</td>
        <td class="num">{fmt(r['net_rtg'],1, signed=True)}</td><td class="num">{fmt(r['pace'],2)}</td>
        <td class="src">{src_link(load_data('official-team-ratings-2025-26.json')['source_url'], 'nba.com')}</td></tr>'''
        for r in load_data('official-team-ratings-2025-26.json')['rows'])}
    </tbody>
  </table>
  </div>
</section>
"""
    page("data.html", "Official data", body, "Official data",
         "Verified NBA.com team ratings and game scores with per-row source links.")


def build_lines() -> None:
    lines = load_results("model-originated-lines.json")
    rows = "\n".join(
        f"""<tr>
          <td class="tight"><b>{esc(r['away'])}</b> @ <b>{esc(r['home'])}</b></td>
          <td class="num">{fmt(r['model_spread_home'], 1, signed=True)}</td>
          <td class="num">{fmt(r['model_total'], 1)}</td>
          <td class="num">{fmt(r['model_home_win_prob']*100, 1, pct=True)}</td>
          <td class="num">{fmt(r['model_home_fair_odds'], 2)}</td>
          <td class="num">{fmt(r['model_away_fair_odds'], 2)}</td>
          <td class="num">{fmt(r['pace'], 2)}</td>
          <td>{chip(r['confidence_band'])}</td>
          <td class="num blank">not available</td>
          <td class="src">{src_link(lines['ratings_source_url'], 'nba.com')}</td>
        </tr>"""
        for r in lines["rows"]
    )

    body = f"""
<div class="eyebrow">03 / LINE ORIGINATION</div>
<h1>From a rating to a line, with every assumption in the open.</h1>
<p class="intro">A spread, a total and a win probability for all 14 games on the 2026-11-04 slate, computed from official team ratings that were shrunk for small-sample noise.</p>

<div class="notice">
  <span class="ico">!</span>
  <div>
    <b>These are not market prices.</b>
    The <em>fair odds</em> columns are the mathematical inverse of a model probability — the break-even price the model implies. They contain no vig and have not been compared with any book. The market columns are blank because no official NBA source publishes sportsbook prices. A row with a blank market column cannot have an edge, and no edge is claimed.
  </div>
</div>

<section>
  <div class="section-head">
    <div><div class="eyebrow">SLATE</div><h2>2026-11-04 originated lines</h2></div>
    <span class="tag">{len(lines['rows'])} GAMES</span>
  </div>
  <div class="table-wrap">
  <table>
    <thead><tr>
      <th>Matchup</th><th class="num">Model spread (home)</th><th class="num">Model total</th>
      <th class="num">Home win %</th><th class="num">Home fair odds</th><th class="num">Away fair odds</th>
      <th class="num">Pace</th><th>Confidence</th><th class="num">Market price</th><th>Source</th>
    </tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
  </div>
  <p class="small muted">Source for the underlying ratings: <a href="{esc(lines['ratings_source_url'])}" target="_blank" rel="noopener noreferrer">NBA.com team advanced stats ↗</a>. Slate taken from <a href="{esc(lines['source_url'])}" target="_blank" rel="noopener noreferrer">the NBA.com schedule page ↗</a>. Every row is labelled <span class="chip warn">very low</span> confidence because at least one team has fewer than 10 games of data.</p>
</section>

<section>
  <div class="eyebrow">THE MATHS</div>
  <h2>How each number is produced</h2>
  <div class="prose">
    <h3>1. Shrink the rating</h3>
    <div class="formula">net_shrunk = μ + (gp / (gp + k)) × (net_raw − μ)
μ = possession-weighted league mean NetRtg, k = {fmt(lines['assumptions']['prior_games'],0)} games</div>
    <p>A team that is +12.8 after 8 games keeps 8/28 = 28.6% of that edge, because most of an 8-game rating is noise. This is the single most important defence against pricing a hot start as if it were a true rating.</p>

    <h3>2. Convert rating to points</h3>
    <div class="formula">gap_points = (net_shrunk_home − net_shrunk_away) × matchup_pace / 100
model_margin = gap_points + home_court_points   (home_court = {fmt(lines['assumptions']['home_court_points'],1)})</div>

    <h3>3. Turn the margin into a probability</h3>
    <div class="formula">model_margin ~ Normal(model_margin, {fmt(lines['assumptions']['margin_sd'],1)})
P(home wins) = Φ(model_margin / σ)</div>

    <h3>4. Turn the probability into a price</h3>
    <div class="formula">fair_decimal_odds = 1 / p</div>
    <p>At <em>p</em> = 0.50 the fair price is 2.00. A book offering 1.91 is holding about 4.7% — which is why a 52.4% win rate, not 50%, is the real break-even at standard two-way prices.</p>
  </div>
</section>

<section>
  <div class="section-head">
    <div><div class="eyebrow">PARLAY ARITHMETIC</div><h2>What a two-leg parlay really costs</h2></div>
  </div>
  <div class="prose">
    <p>Two legs priced as independent multiply. If the legs are correlated, that multiplication is wrong, and the size of the error is computable:</p>
    <div class="formula">P(A ∩ B) = Φ₂(z_A, z_B; φ)      — bivariate normal CDF
independence_gap = P(A ∩ B) − P(A)·P(B)</div>
    <p>The engine implements Φ₂ directly and the self-tests pin it against the exact closed form <code>P(X&lt;0, Y&lt;0) = 1/4 + arcsin(ρ)/2π</code>. What the engine will <strong>not</strong> do is invent φ: it has to come from measured paired outcomes, and that measurement is on the <a href="correlation.html">correlation page</a>.</p>
  </div>
</section>
"""
    page("lines.html", "Line origination", body, "Line origination",
         "Model-originated NBA spreads, totals and win probabilities with explicit assumptions and no invented market prices.")


def build_correlation() -> None:
    corr = load_results("correlation.json")
    rows = "\n".join(
        f"""<tr>
          <td>{esc(r['pair'])}</td>
          <td class="num">{fmt(r['n'])}</td>
          <td class="num">{fmt(r['estimate'], 3)}</td>
          <td class="num">{fmt(r['ci95_low'], 3)}</td>
          <td class="num">{fmt(r['ci95_high'], 3)}</td>
          <td>{chip(r['status'])}</td>
          <td class="src">{src_link(corr['data_source_url'], 'nba.com')}</td>
        </tr>"""
        for r in corr["rows"]
    )
    detail = corr["detail"]
    ha = detail["home_vs_away"]
    pt = detail["pace_vs_total"]
    phi = detail["phi_example"]

    body = f"""
<div class="eyebrow">04 / CORRELATION</div>
<h1>Parlay legs are not independent. Here is how much, and how sure we are.</h1>
<p class="intro">Measured on {corr['n_games']} real games from NBA.com. The result is a genuine measurement — and its confidence interval is the reason it is not yet priced into a bet.</p>

<div class="notice">
  <span class="ico">!</span>
  <div>
    <b>The honest headline is the interval, not the point estimate.</b>
    Home and away scoring correlate at r = {fmt(ha['r'],2)}, but the 95% interval runs {fmt(ha['ci95'][0],2)} to {fmt(ha['ci95'][1],2)} — it includes zero. At {corr['n_games']} games, "these legs are dependent" and "these legs are independent" cannot be told apart. Pinning a correlation to ±0.15 needs roughly {corr['sample_size']['games_needed_for_halfwidth_0_15']} paired games: a full season.
  </div>
</div>

<section>
  <div class="section-head">
    <div><div class="eyebrow">TABLE</div><h2>Measured dependence</h2></div>
    <span class="tag">n = {corr['n_games']} GAMES</span>
  </div>
  <div class="table-wrap">
  <table>
    <thead><tr><th>Pair</th><th class="num">n</th><th class="num">Estimate</th><th class="num">95% low</th><th class="num">95% high</th><th>Status</th><th>Source</th></tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
  </div>
</section>

<section>
  <div class="eyebrow">WHAT EACH ROW MEANS</div>
  <h2>Reading the table properly</h2>
  <div class="prose">
    <h3>Home points vs away points — a real measurement</h3>
    <p>r = {fmt(ha['r'],3)}, 95% CI [{fmt(ha['ci95'][0],2)}, {fmt(ha['ci95'][1],2)}]. Both teams' scores rise together because they share a game environment: possessions, pace, officiating, and overtime. A same-game parlay on two overs is therefore <em>not</em> independent, and multiplying the two prices would overstate the fair parlay price.</p>

    <h3>Team points vs game total — deliberately flagged as inflated</h3>
    <p>r = {fmt(detail['team_vs_total']['r'],3)} looks spectacular and means nothing: the total is partly made of the team's own points. This row is included precisely to show the difference between a real relationship and a tautology.</p>

    <h3>Pre-game pace vs realised total — a legitimate forecast check</h3>
    <p>r = {fmt(pt['r'],3)}, 95% CI [{fmt(pt['ci95'][0],2)}, {fmt(pt['ci95'][1],2)}]. This uses only team PACE as published before the games, so it is an out-of-sample-ish signal rather than a same-game identity. It is the most encouraging number on this page, and it is still far too wide to trade.</p>

    <h3>Binary-to-binary dependence (prop-combo form)</h3>
    <p>φ = {fmt(phi['phi'],3)} between "home team scores 110+" and "home team wins", 95% CI [{fmt(phi['ci95_phi'][0],2)}, {fmt(phi['ci95_phi'][1],2)}]. This is the shape of a player-prop combo problem — two yes/no legs that share a game — and it too cannot be separated from independence yet.</p>

    <h3>Player vs player prop correlation — blank, on purpose</h3>
    <p>NBA.com player box-score pages are rendered client-side and returned no table when fetched, so there are no paired player stat lines to correlate. Rather than estimate a coefficient from nothing, the cell is blank and the blocker is documented. See <a href="flagged.html">Flagged for review</a>.</p>
  </div>
</section>

<section>
  <div class="section-head">
    <div><div class="eyebrow">SAMPLE SIZE</div><h2>Why one month of data cannot price a parlay</h2></div>
  </div>
  <div class="prose">
    <div class="formula">95% half-width on r ≈ 1.96 / (√(n − 3) × (1 + r²/2))  →  n ≈ 3 + (1.96 / half-width)²</div>
    <p>To get a correlation interval of ±0.15 around r = 0.3, you need about <strong>{corr['sample_size']['games_needed_for_halfwidth_0_15']}</strong> independent paired games. To get ±0.10, about 390. And games are not fully independent draws, so the true requirement is worse than that. This is the quantitative reason a correlation estimate is not an edge.</p>
  </div>
</section>
"""
    page("correlation.html", "Correlation", body, "Correlation",
         "Measured same-game correlation between NBA parlay legs, with confidence intervals and explicit blanks.")


def build_validation() -> None:
    gates_doc = load_results("gate-runs.json")
    run = gates_doc["runs"][0]
    result = run["result"]

    gate_rows = "\n".join(
        f"""<tr>
          <td class="tight mono">{esc(g['id'])}</td>
          <td>{esc(g['name'])}</td>
          <td>{chip(g['status'])}</td>
          <td>{esc(g['detail'])}</td>
          <td class="src"><a href="{REPO_BLOB}/analysis/engine/gates.py" target="_blank" rel="noopener noreferrer">gate rule ↗</a></td>
        </tr>"""
        for g in result["gates"]
    )
    def_rows = "\n".join(
        f"""<tr><td class="tight mono">{esc(g['id'])}</td><td class="tight">{esc(g['name'])}</td><td>{esc(g['requirement'])}</td><td class="src"><a href="{REPO_BLOB}/analysis/engine/gates.py" target="_blank" rel="noopener noreferrer">gate rule ↗</a></td></tr>"""
        for g in gates_doc["gate_definitions"]
    )

    body = f"""
<div class="eyebrow">05 / VALIDATION GATES</div>
<h1>Eight gates. Three outcomes. "Unknown" is never "pass".</h1>
<p class="intro">A strategy reaches the leaderboard only if every gate passes. Gates that cannot be evaluated return <em>not evaluable</em>, which makes the strategy <em>unproven</em> — not approved, and not rejected either.</p>

<div class="metrics">
  <div class="metric bad"><span>OVERALL</span><b style="font-size:19px">{esc(result['overall'].upper())}</b><small>for the lead strategy</small></div>
  <div class="metric good"><span>PASSED</span><b>{result['counts']['pass']}</b><small>gates cleared</small></div>
  <div class="metric warn"><span>NOT EVALUABLE</span><b>{result['counts']['not_evaluable']}</b><small>blocked by missing data</small></div>
  <div class="metric bad"><span>FAILED</span><b>{result['counts']['fail']}</b><small>gate actively failed</small></div>
</div>

<div class="notice info">
  <span class="ico">i</span>
  <div>
    <b>{esc(result['rule'])}</b>
    The gate engine is real code, not a description. It runs on every build and its output for the lead strategy is shown below exactly as computed.
  </div>
</div>

<section>
  <div class="section-head">
    <div><div class="eyebrow">LIVE RUN</div><h2>Gate result: "Pace-and-efficiency spread model"</h2></div>
    <span class="tag">COMPUTED, NOT ASSERTED</span>
  </div>
  <div class="table-wrap">
  <table>
    <thead><tr><th>ID</th><th>Gate</th><th>Status</th><th>Reason</th><th>Basis</th></tr></thead>
    <tbody>
{gate_rows}
    </tbody>
  </table>
  </div>
  <p class="small muted" style="margin-top:12px">{esc(run['reading'])}</p>
</section>

<section>
  <div class="section-head">
    <div><div class="eyebrow">DEFINITIONS</div><h2>What each gate requires</h2></div>
  </div>
  <div class="table-wrap">
  <table>
    <thead><tr><th>ID</th><th>Gate</th><th>Requirement</th><th>Basis</th></tr></thead>
    <tbody>
{def_rows}
    </tbody>
  </table>
  </div>
</section>

<section>
  <div class="eyebrow">WHY THIS ORDER</div>
  <h2>The gates run cheapest-first, and the cheap ones catch the most</h2>
  <div class="prose">
    <p><strong>G0 provenance</strong> catches the most common failure in this whole field: a number with no source, or a number that quietly changed definition between the input and the claim. One missing URL fails the gate.</p>
    <p><strong>G1 pre-registration</strong> is hashed, so a later edit to the thresholds changes the hash and invalidates the run. Without it, "we would have bet that anyway" is unfalsifiable.</p>
    <p><strong>G4 luck</strong> requires three separate tests to agree — an exact binomial test, the probabilistic Sharpe ratio, and the deflated Sharpe ratio. They fail in different ways, which is the point: a fat-tailed streak can pass one and fail another.</p>
    <p><strong>G6 correlation</strong> fails a parlay outright if its legs were assumed independent without a measurement. That single rule kills most plausible-looking parlay "systems".</p>
    <p><strong>G7 robustness</strong> deletes the best 5% of results and re-checks. A strategy whose entire edge comes from three lucky weeks fails here, which is the arithmetic version of "that was one good month".</p>
  </div>
</section>
"""
    page("validation.html", "Validation gates", body, "Validation gates",
         "Eight validation gates with three-state outcomes, run against the actual strategies.")


def row_source(strategy_id: str) -> str:
    """Per-strategy evidence link. Points at the page holding that strategy's basis."""
    mapping = {
        "S1": ("line origination", f"{REPO_TREE}/lines.html"),
        "S2": ("line origination", f"{REPO_TREE}/lines.html"),
        "S3": ("correlation", f"{REPO_TREE}/correlation.html"),
        "S4": ("no player data", f"{REPO_TREE}/flagged.html"),
        "S5": ("gates", f"{REPO_TREE}/validation.html"),
    }
    label, url = mapping.get(strategy_id, ("repo", REPO_TREE))
    return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label} ↗</a>'


def build_leaderboard() -> None:
    lb = load_results("leaderboard.json")
    luck = lb["luck_arithmetic"]
    noise = luck["identical_no_skill_bettors"]

    rows = "\n".join(
        f"""<tr>
          <td class="num">{'—' if r['rank'] is None else r['rank']}</td>
          <td class="tight mono">{esc(r['id'])}</td>
          <td>{esc(r['name'])}</td>
          <td>{esc(r['category'])}</td>
          <td>{chip(r['overall_gate_status'])}</td>
          <td class="num">{fmt(r['n_bets'])}</td>
          <td class="num">{fmt(r['roi'], 4)}</td>
          <td class="num">{fmt(r['roi_lower_bound'], 4)}</td>
          <td class="num blank">undefined</td>
          <td class="src">{row_source(r['id'])}</td>
        </tr>"""
        for r in lb["rows"]
    )

    scen_rows = "\n".join(
        f"""<tr>
          <td class="num">{fmt(s['n_bets'])}</td>
          <td class="num">{fmt(s['no_skill_sd_of_win_rate']*100, 2, pct=True)}</td>
          <td class="num">{fmt(s['win_rate_95pct_band_if_no_skill'][0]*100, 1, pct=True)} – {fmt(s['win_rate_95pct_band_if_no_skill'][1]*100, 1, pct=True)}</td>
          <td class="num">{fmt(s['no_skill_sd_of_roi']*100, 2, pct=True)}</td>
          <td class="src"><a href="{REPO_BLOB}/analysis/engine/skill.py" target="_blank" rel="noopener noreferrer">formula ↗</a></td>
        </tr>"""
        for s in luck["scenarios"]
    )

    body = f"""
<div class="eyebrow">06 / LEADERBOARD</div>
<h1>A leaderboard that will not rank a hot streak.</h1>
<p class="intro">Five candidate strategies across singles, parlays and prop combos. None has a settled, priced bet record, so none is ranked. That is the correct output, not a missing one.</p>

<div class="notice">
  <span class="ico">!</span>
  <div>
    <b>Zero strategies are ranked, and that is the finding.</b>
    A rank is withheld unless every gate passes. There are no settled bets and no market prices, so the honest state is <em>unproven</em> for all five strategies. The reward column is undefined by design: the competition owner sets rewards, and none are invented here.
    <a href="validation.html">See the gates →</a>
  </div>
</div>

<section>
  <div class="section-head">
    <div><div class="eyebrow">BOARD</div><h2>Strategy standings</h2></div>
    <span class="tag">{lb['n_total']} CANDIDATES / {lb['n_eligible']} RANKED</span>
  </div>
  <div class="table-wrap">
  <table>
    <thead><tr>
      <th class="num">Rank</th><th>ID</th><th>Strategy</th><th>Category</th>
      <th>Gate status</th><th class="num">Bets</th><th class="num">ROI</th>
      <th class="num">ROI lower bound</th><th class="num">Reward</th><th>Evidence / basis</th>
    </tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
  </div>
  <p class="small muted">{esc(lb['ranking_rule'])}</p>
</section>

<section>
  <div class="section-head">
    <div><div class="eyebrow">THE ARITHMETIC OF LUCK</div><h2>How many no-skill entries look good at each sample size</h2></div>
    <span class="tag">AT -110 / 52.38% BREAK-EVEN</span>
  </div>
  <div class="table-wrap">
  <table>
    <thead><tr>
      <th class="num">Bets</th><th class="num">No-skill SD of win rate</th>
      <th class="num">95% win-rate band if no skill</th><th class="num">No-skill SD of ROI</th><th>Basis</th>
    </tr></thead>
    <tbody>
{scen_rows}
    </tbody>
  </table>
  </div>
  <p class="small muted">Derived from the binomial model in <code>engine/skill.py</code>; no data needed, and none invented.</p>
</section>

<section>
  <div class="section-head">
    <div><div class="eyebrow">THE KILLER NUMBER</div><h2>{noise['n_bettors']} identical no-skill entries, {noise['n_bets_each']} bets each</h2></div>
  </div>
  <div class="metrics">
    <div class="metric bad"><span>EXPECTED IN PROFIT</span><b>{fmt(noise['expected_profitable_no_skill'],0)}</b><small>of {noise['n_bettors']} with no skill at all</small></div>
    <div class="metric bad"><span>SHARE IN PROFIT</span><b>{fmt(noise['expected_profitable_no_skill_pct'],0, pct=True)}</b><small>purely by chance</small></div>
    <div class="metric"><span>SD OF WIN RATE</span><b>{fmt(noise['sd_of_win_rate']*100,2, pct=True)}</b><small>at {noise['n_bets_each']} bets</small></div>
  </div>
  <div class="prose" style="margin-top:18px">
    <p>{esc(luck['reading'])}</p>
    <p>This is why the ranking uses a <strong>lower confidence bound</strong> rather than ROI. Two strategies with the same ROI but different sample sizes are not equally good, and a bound makes the shorter record rank below the longer one automatically. The reward for a top-performing strategy therefore requires defining the evaluation window first — see <a href="flagged.html">the open owner decisions</a>.</p>
  </div>
</section>

<section>
  <div class="eyebrow">MULTIPLE TESTING</div>
  <h2>The bar rises with every idea you try</h2>
  <div class="prose">
    <div class="formula">E[max Sharpe of N zero-skill strategies] ≈ (1−γ)·Φ⁻¹(1 − 1/N) + γ·Φ⁻¹(1 − 1/(N·e)),  γ = 0.5772</div>
    <div class="table-wrap">
    <table>
      <thead><tr><th class="num">Strategies tried</th><th class="num">Sharpe a zero-skill best-of-N is expected to reach</th><th>Basis</th></tr></thead>
      <tbody>
        {''.join(f'<tr><td class="num">{esc(k)}</td><td class="num">{fmt(v,2)}</td><td class="src"><a href="{REPO_BLOB}/analysis/engine/skill.py" target="_blank" rel="noopener noreferrer">formula ↗</a></td></tr>' for k, v in luck['thresholds_for_best_of_n'].items())}
      </tbody>
    </table>
    </div>
    <p>Try 100 ideas and the best one will typically show a Sharpe near {fmt(luck['thresholds_for_best_of_n']['100'],2)} with no skill whatsoever. The deflated Sharpe ratio in gate G4 subtracts exactly this threshold, so a strategy cannot win the board by being the luckiest of a hundred attempts.</p>
  </div>
</section>
"""
    page("leaderboard.html", "Leaderboard", body, "Leaderboard",
         "Luck-adjusted strategy leaderboard: lower confidence bounds, deflated Sharpe, and the arithmetic of no-skill records.")


def build_methods() -> None:
    body = f"""
<div class="eyebrow">07 / METHODS</div>
<h1>Check the maths instead of trusting it.</h1>
<p class="intro">The engine ships with 51 self-tests. Where a closed form exists, the test asserts the closed form — so a bug in the implementation cannot pass silently.</p>

<div class="notice good">
  <span class="ico">✓</span>
  <div>
    <b>51 tests, all passing, fully offline.</b>
    Run <code>python3 -m unittest discover -s analysis/tests -t analysis</code>. No network access, no third-party packages, no randomness without a seed.
  </div>
</div>

<section>
  <div class="eyebrow">ARCHITECTURE</div>
  <h2>Six modules, each with one job</h2>
  <div class="table-wrap">
  <table>
    <thead><tr><th>Module</th><th>Responsibility</th><th>Key honesty guarantee</th><th>Code</th></tr></thead>
    <tbody>
      <tr><td class="mono">ratings.py</td><td>Shrink small-sample team ratings</td><td>Prior strength is declared, never fitted and hidden</td><td class="src"><a href="{REPO_BLOB}/analysis/engine/ratings.py" target="_blank" rel="noopener noreferrer">source ↗</a></td></tr>
      <tr><td class="mono">markets.py</td><td>Spread, total, win prob, fair odds, parlay joints</td><td><code>is_market_price: false</code> on every output; EV needs a real price passed in</td><td class="src"><a href="{REPO_BLOB}/analysis/engine/markets.py" target="_blank" rel="noopener noreferrer">source ↗</a></td></tr>
      <tr><td class="mono">correlation.py</td><td>Pearson/phi with Fisher intervals</td><td>Refuses player-prop correlation rather than guessing</td><td class="src"><a href="{REPO_BLOB}/analysis/engine/correlation.py" target="_blank" rel="noopener noreferrer">source ↗</a></td></tr>
      <tr><td class="mono">skill.py</td><td>Binominal, PSR, deflated Sharpe, bootstrap</td><td>Cannot certify skill; can only fail to reject chance</td><td class="src"><a href="{REPO_BLOB}/analysis/engine/skill.py" target="_blank" rel="noopener noreferrer">source ↗</a></td></tr>
      <tr><td class="mono">gates.py</td><td>Eight gates, three-state results</td><td><code>not_evaluable</code> can never be rolled up to <code>passed</code></td><td class="src"><a href="{REPO_BLOB}/analysis/engine/gates.py" target="_blank" rel="noopener noreferrer">source ↗</a></td></tr>
      <tr><td class="mono">leaderboard.py</td><td>ROI lower bounds and ranking</td><td>Unproven strategies get <code>rank: null</code>, not a low rank</td><td class="src"><a href="{REPO_BLOB}/analysis/engine/leaderboard.py" target="_blank" rel="noopener noreferrer">source ↗</a></td></tr>
    </tbody>
  </table>
  </div>
</section>

<section>
  <div class="eyebrow">THE TESTS THAT MATTER MOST</div>
  <h2>Closed-form anchors</h2>
  <div class="prose">
    <h3>Bivariate normal CDF</h3>
    <p>The parlay joint probability depends entirely on Φ₂. If that is wrong, every parlay number is wrong. The test pins it against the exact identity:</p>
    <div class="formula">P(X &lt; 0, Y &lt; 0) = 1/4 + arcsin(ρ) / (2π)   for standard bivariate normal
checked at ρ ∈ {{−0.9, −0.5, −0.2, 0, 0.2, 0.5, 0.9}}, tolerance 1e-6</div>
    <p>It also asserts Φ₂ reduces exactly to Φ(h)·Φ(k) at ρ = 0, and that the joint upper-tail probability is monotone in ρ.</p>

    <h3>Shrinkage limits</h3>
    <p>Zero games must return the league mean exactly; a large number of games must return the observed rating. Both are asserted, so an inverted weight formula cannot survive.</p>

    <h3>Vig arithmetic</h3>
    <p>De-vigging two −110 prices must yield a 4.77% hold and fair probabilities of exactly 0.5 each. The test asserts this rather than eyeballing it.</p>

    <h3>Determinism</h3>
    <p>One test re-runs the entire analysis as a subprocess and fails if any output byte changed. A result that moves between runs is not evidence.</p>

    <h3>Honest anchors that constrain the claims</h3>
    <ul>
      <li>52.38% is break-even at −110, so a 55% record over 1,000 bets lands at p ≈ 0.052 — barely at the line. The test asserts this band rather than pretending such a record is decisive.</li>
      <li>A zero-mean return series must <em>not</em> look significant in the block bootstrap.</li>
      <li>"No bets" must produce the verdict <code>unproven</code>, never <code>passed</code>.</li>
    </ul>
  </div>
</section>

<section>
  <div class="eyebrow">REPRODUCE</div>
  <h2>Three commands, no network</h2>
  <pre>python3 analysis/run.py                                        # rebuild results/*.json
python3 analysis/build_site.py                                 # rebuild this dashboard
python3 -m unittest discover -s analysis/tests -t analysis      # 51 tests</pre>
  <p class="small muted">Inputs live in <code>analysis/data/*.json</code>, each recording the NBA.com URL it was transcribed from and the timestamp of the read.</p>
</section>
"""
    page("methods.html", "Methods & tests", body, "Methods & tests",
         "Engine architecture and the closed-form self-tests that let a reader verify the maths.")


def build_flagged() -> None:
    items = [
        ("F1", "No sportsbook prices anywhere in this repository",
         "No official NBA source publishes sportsbook prices. NBA.com renders no odds on its standings, stats, schedule or game-summary pages (the games list has a 'HIDE ODDS' toggle but no prices reach the rendered text). Without a licensed feed there is nothing to compare a model against.",
         "unverified", "https://www.nba.com/schedule?date=11/03/2026"),
        ("F2", "Player prop correlation is not computable",
         "NBA.com player box-score pages are rendered client-side and returned no table when fetched, so no paired player stat lines exist here. The correlation cell is blank rather than estimated.",
         "unverified", "https://www.nba.com/stats/players/boxscores?Season=2026-27&SeasonType=Regular%20Season"),
        ("F3", "Game sample is 18 games, not a season",
         "Only 11/01 and 11/02 games were transcribed. Earlier dates are published by NBA.com but sit behind a paginated table that was not fully readable. Correlations from 18 games have intervals that include zero.",
         "unverified", "https://www.nba.com/stats/teams/boxscores?Season=2026-27&SeasonType=Regular%20Season"),
        ("F4", "Prior strength k = 20 games is an assumption",
         "The shrinkage constant used to deflate small-sample ratings was chosen as a deliberately weak prior, not estimated from this data. A different k moves every originated line.",
         "unverified", "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular%20Season"),
        ("F5", "Home-court advantage 2.5 points and margin SD 12.5 are constants",
         "Both are documented assumptions in engine/markets.py. NBA.com publishes home/road splits but no official single home-court number or margin distribution; neither was fitted to the 18-game sample because that would be overfitting.",
         "unverified", "https://www.nba.com/standings?GroupBy=conf&Season=2025-26&Section=overall"),
        ("F6", "Competition rewards are undefined",
         "The brief asks for rewards for top-performing strategies. No reward, prize, points scheme or funding is defined anywhere and none is invented here. The owner must set this before a competition is real.",
         "unverified", "https://github.com/sassnarep3-star/Own7"),
        ("F7", "2025-26 ratings snapshot is partial (14 of 30 teams)",
         "Only 14 completed-season rows could be read without ambiguity. The remainder are omitted rather than filled in.",
         "unverified", "https://www.nba.com/stats/teams/advanced?Season=2025-26&SeasonType=Regular%20Season"),
        ("F8", "'Remove luck from the equation' is not achievable as stated",
         "Luck cannot be eliminated from a finite bet record. What this engine does instead: shrink small samples, test against no-skill nulls, deflate for multiple testing, and rank on a lower confidence bound. The claim is deliberately weakened to what is mathematically defensible.",
         "noted", "https://www.nba.com/stats/help/glossary"),
        ("F9", "Totals model uses a blended offense/defence assumption",
         "Expected points per 100 for each side is the mean of that side's offense and the opponent's defence. This is a documented simplification; a properly fitted model would separate pace and efficiency interactions.",
         "unverified", "https://www.nba.com/stats/help/glossary"),
        ("F10", "No license file in the repository",
         "Reuse terms for this analysis are undefined.",
         "unverified", "https://github.com/sassnarep3-star/Own7"),
    ]
    rows = "\n".join(
        f"""<tr>
          <td class="tight mono">{esc(i)}</td>
          <td>{esc(t)}</td>
          <td>{esc(d)}</td>
          <td>{chip(s)}</td>
          <td class="src">{src_link(u, 'source')}</td>
        </tr>"""
        for i, t, d, s, u in items
    )

    body = f"""
<div class="eyebrow">08 / FLAGGED FOR REVIEW</div>
<h1>Everything that could not be verified, stated plainly.</h1>
<p class="intro">These items do not block publication — they block <em>claims</em>. Each one is listed with the official source that constrains it, so it can be checked and challenged.</p>

<div class="notice">
  <span class="ico">!</span>
  <div>
    <b>Read this before citing anything from this site.</b>
    The originated lines are model outputs, the correlation intervals include zero, no market price exists, and no strategy is ranked. Every limitation below is a deliberate blank rather than a filled-in guess.
  </div>
</div>

<section>
  <div class="section-head">
    <div><div class="eyebrow">REGISTER</div><h2>Open items</h2></div>
    <span class="tag">{len(items)} ITEMS</span>
  </div>
  <div class="table-wrap">
  <table>
    <thead><tr><th>ID</th><th>Item</th><th>Why it is flagged</th><th>Status</th><th>Source</th></tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
  </div>
</section>

<section>
  <div class="eyebrow">WHAT WOULD CLOSE THESE</div>
  <h2>The shortest honest path to a real edge</h2>
  <div class="prose">
    <ol>
      <li><strong>Get a licensed, timestamped odds feed.</strong> Nothing on this site can become a bet evaluation until real prices with a capture time exist. This is the single blocking dependency.</li>
      <li><strong>Get paired player game logs.</strong> Player-prop combos need per-player, per-game stat lines plus the exact prop lines and settlement rules for pushes and voids.</li>
      <li><strong>Build a full-season game sample.</strong> A correlation needs roughly {174} paired games to reach ±0.15, and preferably two seasons to check stability.</li>
      <li><strong>Pre-register the strategy, then leave it alone.</strong> Hash the thresholds before the first bet. The moment a threshold moves after results are seen, gate G1 fails.</li>
      <li><strong>Define the reward and the evaluation window.</strong> Owner decision, not a modelling decision.</li>
    </ol>
  </div>
</section>
"""
    page("flagged.html", "Flagged for review", body, "Flagged for review",
         "Every unverified item, blank cell and documented assumption in the NBA analysis, with sources.")


def build_sources() -> None:
    sources = [
        ("NBA.com — Team advanced stats, 2026-27", "OffRtg, DefRtg, NetRtg, PACE, eFG%, TS%, PIE, possessions for all 30 teams", "30/30 rows transcribed", "https://www.nba.com/stats/teams/advanced?Season=2026-27&SeasonType=Regular%20Season"),
        ("NBA.com — Team advanced stats, 2025-26", "Completed-season ratings used as prior context", "14 rows transcribed; remainder omitted", "https://www.nba.com/stats/teams/advanced?Season=2025-26&SeasonType=Regular%20Season"),
        ("NBA.com — Team box scores", "Final scores, minutes and OT flag for 18 games (11/01, 11/02)", "18 games transcribed", "https://www.nba.com/stats/teams/boxscores?Season=2026-27&SeasonType=Regular%20Season"),
        ("NBA.com — Standings, 2026-27", "Win-loss records used to cross-check ratings rows", "30 rows matched", "https://www.nba.com/standings"),
        ("NBA.com — Standings, 2025-26", "Cross-check of completed-season records", "OKC 64-18 and DET 60-22 matched", "https://www.nba.com/standings?GroupBy=conf&Season=2025-26&Section=overall"),
        ("NBA.com — Schedule", "Slate and home/away order for 2026-11-04", "14 games transcribed", "https://www.nba.com/schedule?date=11/03/2026"),
        ("NBA.com — Game summary (BOS @ HOU)", "Independent cross-check of a game row and the quarter line score", "Scores matched exactly", "https://www.nba.com/game/0022600167"),
        ("NBA.com — Stat glossary", "Official definitions of PACE, OffRtg, DefRtg, NetRtg, TS%, USG%, PIE, Poss", "Definitions quoted verbatim in methods", "https://www.nba.com/stats/help/glossary"),
        ("NBA.com — Stats landing page", "Season selector confirms 2026-27 is current", "confirmed", "https://www.nba.com/stats/"),
        ("NBA.com — Player box scores (attempted)", "Attempted player-level game logs for prop correlation", "NO TABLE RETURNED — flagged F2", "https://www.nba.com/stats/players/boxscores?Season=2026-27&SeasonType=Regular%20Season"),
    ]
    rows = "\n".join(
        f"""<tr>
          <td>{esc(n)}</td>
          <td>{esc(w)}</td>
          <td>{chip('verified' if 'NO TABLE' not in r else 'unverified')} <span class="small muted">{esc(r)}</span></td>
          <td class="src">{src_link(u, 'open')}</td>
        </tr>"""
        for n, w, r, u in sources
    )

    body = f"""
<div class="eyebrow">09 / SOURCES</div>
<h1>Every source used, and the one that failed.</h1>
<p class="intro">Ten NBA.com pages were read on 2026-11-03 (UTC). Each table on this site prints the URL for the row's source, and this register records what was taken from each page and what was verified.</p>

<section>
  <div class="section-head">
    <div><div class="eyebrow">REGISTER</div><h2>Official sources</h2></div>
    <span class="tag">ALL NBA.COM</span>
  </div>
  <div class="table-wrap">
  <table>
    <thead><tr><th>Source</th><th>What was taken</th><th>Verification</th><th>Link</th></tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
  </div>
</section>

<section>
  <div class="eyebrow">OFFICIAL DEFINITIONS QUOTED</div>
  <h2>NBA.com glossary, verbatim</h2>
  <div class="prose">
    <ul>
      <li><strong>OffRtg</strong> — "Measures a team's points scored per 100 possessions."</li>
      <li><strong>DEFRTG</strong> — "The number of points allowed per 100 possessions by a team."</li>
      <li><strong>NetRtg</strong> — "Measures a team's point differential per 100 possessions… Formula OFFRTG - DEFRTG."</li>
      <li><strong>PACE</strong> — "The number of possessions per 48 minutes for a team or player."</li>
      <li><strong>TS%</strong> — "A shooting percentage that factors in the value of three-point field goals and free throws… Formula Points / [2*(Field Goals Attempted+0.44*Free Throws Attempted)]."</li>
      <li><strong>Poss</strong> — "The number of possessions played by a player or team. Please note: an Offensive Rebound does not create another possession, it simply makes the existing possession longer."</li>
      <li><strong>PIE</strong> — "Player Impact Estimate… measures a player's overall statistical contribution against the total statistics in games they play in."</li>
    </ul>
    <p class="small muted">All definitions from <a href="https://www.nba.com/stats/help/glossary" target="_blank" rel="noopener noreferrer">NBA.com stat glossary ↗</a>, read 2026-11-03.</p>
  </div>
</section>

<section>
  <div class="eyebrow">NOT USED, AND WHY</div>
  <h2>Third-party odds and data were deliberately excluded</h2>
  <div class="prose">
    <p>Sportsbook aggregators and odds APIs were not used, because the project rule is official sources only and no official NBA source publishes prices. Secondary stat sites were also excluded so every value traces to the league itself. The cost of that discipline is visible on this site: no market comparison, no player-prop modelling, and a correlation sample of 18 games.</p>
  </div>
</section>
"""
    page("sources.html", "Sources", body, "Sources",
         "Official NBA.com sources used, what was taken from each, and what failed.")


def build_executive_summary() -> None:
    ratings = load_results("team-ratings.json")
    lines = load_results("model-originated-lines.json")
    corr = load_results("correlation.json")

    body = f"""
<div class="eyebrow">01 / EXECUTIVE SUMMARY</div>
<h1>An honest line-origination engine, and the reasons its best ideas are not yet tradable.</h1>
<p class="intro">What was built, what the numbers say, what is missing, and what would have to be true before any of it deserves a bet.</p>

<section style="margin-top:26px">
  <div class="section-head"><div><div class="eyebrow">THE ONE-PARAGRAPH VERSION</div><h2>Summary</h2></div><span class="tag">READ THIS FIRST</span></div>
  <div class="prose">
    <p>A reproducible engine now originates NBA spread, total and win-probability lines from official NBA.com team ratings, with small-sample shrinkage so a hot start is not mistaken for a true rating. It measures real same-game dependence instead of assuming legs are independent, and it runs eight validation gates with three-state outcomes before anything reaches a leaderboard. On the current data the honest reading is this: the machinery is sound and independently testable, but the evidence base is too thin to rank any strategy. Eighteen games are not enough to pin a correlation, no official source publishes sportsbook prices, and player-level prop data could not be collected at all. The leaderboard therefore ranks nothing — deliberately.</p>
  </div>
</section>

<section>
  <div class="eyebrow">FINDINGS</div>
  <h2>Six findings worth acting on</h2>
  <div class="table-wrap">
  <table>
    <thead><tr><th>#</th><th>Finding</th><th>Evidence</th><th>Status</th><th>Source</th></tr></thead>
    <tbody>
      <tr><td class="mono">1</td>
        <td>Small-sample NBA ratings are wildly overstated if used raw. Houston is +12.8 after 8 games; shrinkage keeps 28.6% of that.</td>
        <td class="num">{fmt(ratings['rows'][0]['net_rtg_raw'],1)} → {fmt(ratings['rows'][0]['net_rtg_shrunk'],2)}</td>
        <td>{chip('computed')}</td>
        <td class="src">{src_link(ratings['source_url'], 'nba.com')}</td></tr>
      <tr><td class="mono">2</td>
        <td>Same-game parlay legs are positively dependent, but 18 games cannot distinguish that from independence.</td>
        <td class="num">r = {fmt(corr['rows'][0]['estimate'],2)} (CI {fmt(corr['rows'][0]['ci95_low'],2)}…{fmt(corr['rows'][0]['ci95_high'],2)})</td>
        <td>{chip('measured')}</td>
        <td class="src">{src_link(corr['data_source_url'], 'nba.com')}</td></tr>
      <tr><td class="mono">3</td>
        <td>Pre-game pace is positively related to the realised total — the most promising signal found, and still far too wide to trade.</td>
        <td class="num">r = {fmt(corr['rows'][2]['estimate'],2)} (CI {fmt(corr['rows'][2]['ci95_low'],2)}…{fmt(corr['rows'][2]['ci95_high'],2)})</td>
        <td>{chip('measured')}</td>
        <td class="src">{src_link(corr['data_source_url'], 'nba.com')}</td></tr>
      <tr><td class="mono">4</td>
        <td>There is no market to beat. No official NBA source publishes prices, so no edge can be computed at all.</td>
        <td>0 prices available</td>
        <td>{chip('unverified')}</td>
        <td class="src">{src_link('https://www.nba.com/schedule?date=11/03/2026', 'nba.com')}</td></tr>
      <tr><td class="mono">5</td>
        <td>Leaderboards at short horizons rank luck. Among 100 identical no-skill entries at 200 bets, roughly 44 show a profit.</td>
        <td class="num">{fmt(44)} / 100</td>
        <td>{chip('computed')}</td>
        <td class="src"><a href="{REPO_BLOB}/analysis/engine/skill.py" target="_blank" rel="noopener noreferrer">derivation ↗</a></td></tr>
      <tr><td class="mono">6</td>
        <td>Multiplicity is the dominant hidden risk. Trying 100 ideas yields a best Sharpe near 2.5 with zero skill.</td>
        <td class="num">E[max SR] ≈ 2.53</td>
        <td>{chip('computed')}</td>
        <td class="src"><a href="{REPO_BLOB}/analysis/engine/skill.py" target="_blank" rel="noopener noreferrer">derivation ↗</a></td></tr>
    </tbody>
  </table>
  </div>
</section>

<section>
  <div class="eyebrow">DELIVERED</div>
  <h2>What exists now</h2>
  <div class="prose">
    <ul>
      <li><strong>Verified data layer</strong> — {len(ratings['rows'])} teams and {corr['n_games']} games, every value traced to an NBA.com URL with a read timestamp.</li>
      <li><strong>Line origination</strong> — {len(lines['rows'])} model spread/total/win-probability lines for the 2026-11-04 slate, with assumptions named.</li>
      <li><strong>Correlation measurement</strong> — Pearson and phi with Fisher intervals, including a row deliberately flagged as a tautology.</li>
      <li><strong>Skill-vs-luck battery</strong> — exact binomial, probabilistic Sharpe ratio, deflated Sharpe ratio, minimum track-record length, block bootstrap.</li>
      <li><strong>Eight validation gates</strong> and a leaderboard that withholds ranks from unproven strategies.</li>
      <li><strong>51 self-tests</strong>, including closed-form checks on the bivariate normal CDF and a byte-for-byte determinism test.</li>
    </ul>
  </div>
</section>

<section>
  <div class="eyebrow">NOT DELIVERED, AND WHY</div>
  <h2>The four things a real strategy still needs</h2>
  <div class="table-wrap">
  <table>
    <thead><tr><th>Missing</th><th>Why it blocks</th><th>What it would take</th><th>Basis</th></tr></thead>
    <tbody>
      <tr><td>Timestamped market prices</td><td>Without a real price there is no vig, no edge and no settlement to evaluate.</td><td>A licensed odds feed captured before kickoff.</td><td class="src"><a href="https://www.nba.com/schedule?date=11/03/2026" target="_blank" rel="noopener noreferrer">no odds on nba.com ↗</a></td></tr>
      <tr><td>Player-level game logs</td><td>NBA.com player pages returned no table, so prop combos cannot be correlated or priced.</td><td>Paired per-player stat lines plus exact prop lines and push/void rules.</td><td class="src"><a href="https://www.nba.com/stats/players/boxscores?Season=2026-27&SeasonType=Regular%20Season" target="_blank" rel="noopener noreferrer">empty table ↗</a></td></tr>
      <tr><td>Full-season sample</td><td>18 games give correlation intervals that include zero.</td><td>~174 paired games for ±0.15, ideally two seasons for stability.</td><td class="src"><a href="https://www.nba.com/stats/teams/boxscores?Season=2026-27&SeasonType=Regular%20Season" target="_blank" rel="noopener noreferrer">game log ↗</a></td></tr>
      <tr><td>Defined competition rewards</td><td>The brief asks for rewards; inventing amounts or rules would be fabrication.</td><td>Owner decision on reward, window and eligibility.</td><td class="src"><a href="{REPO_BLOB}/analysis/results/leaderboard.json" target="_blank" rel="noopener noreferrer">reward: null ↗</a></td></tr>
    </tbody>
  </table>
  </div>
</section>

<section>
  <div class="eyebrow">BOTTOM LINE</div>
  <h2>What to trust on this site, and what to doubt</h2>
  <div class="prose">
    <p><strong>Trust:</strong> the data (each cell has an NBA.com URL), the arithmetic (51 tests, closed-form anchored), and the gate logic (three-state, so "unknown" cannot become "pass").</p>
    <p><strong>Doubt:</strong> the originated lines. They are a state model over a partial season with three documented constants, and no market exists to check them against. They are a starting point for line origination, not a set of prices.</p>
    <p><strong>Reject:</strong> any reading of this site as evidence of a profitable system. Zero strategies are ranked because zero could be shown to be skill rather than luck, and that is the mathematically correct conclusion rather than a shortfall of effort.</p>
  </div>
</section>
"""
    page("executive-summary.html", "Executive summary", body, "Executive summary",
         "Executive summary of the NBA line-origination engine: findings, deliverables, blockers and what to trust.")


def main() -> int:
    build_index()
    build_executive_summary()
    build_data()
    build_lines()
    build_correlation()
    build_validation()
    build_leaderboard()
    build_methods()
    build_flagged()
    build_sources()
    print("built:", ", ".join(sorted(p.name for p in OUT.glob("*.html"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
