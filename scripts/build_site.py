#!/usr/bin/env python3
"""One deterministic, dependency-free site. Data and source contracts are canonical."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nba_lab.engine import encode, load_csv, load_json, verify_receipts

SOURCES = {s["id"]: s for s in load_json("research/sources.json")}
CATALOG = load_json("research/catalog.json")
RESULTS = load_json("research/results.json")
PROTOCOL = load_json("research/protocol.json")
INTEGRATION = load_json("research/integration.json")
MARKET = load_json("market-evidence/evidence.json")
OPEN_FLAGS = sum(x["status"] == "Needs review" for x in CATALOG["flags"])


class Markup(str):
    pass


def esc(value):
    return html.escape(str(value), quote=True)


def icon(name="arrow"):
    paths = {
        "overview": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
        "brief": '<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 12h7M9 16h7"/>',
        "data": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v7c0 4 16 4 16 0V5M4 12v7c0 4 16 4 16 0v-7"/>',
        "signals": '<path d="M3 13h4l3-8 4 14 3-8h4"/>',
        "lab": '<path d="M9 3v6l-5 9a2 2 0 002 3h12a2 2 0 002-3l-5-9V3M8 3h8M7 15h10"/>',
        "correlation": '<path d="M4 3v17h17M8 15l4-5 4 2 5-7"/><circle cx="8" cy="15" r="1"/><circle cx="16" cy="12" r="1"/>',
        "validation": '<path d="M12 3l8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6"/>',
        "leaderboard": '<path d="M8 3h8v7a4 4 0 01-8 0zM8 5H4v3a4 4 0 004 4M16 5h4v3a4 4 0 01-4 4M12 14v6M8 21h8"/>',
        "sources": '<path d="M9 15l6-6M8 17l-2 2a4 4 0 01-5-5l5-5a4 4 0 015 0M16 7l2-2a4 4 0 015 5l-5 5a4 4 0 01-5 0" transform="translate(0 -1)"/>',
        "review": '<path d="M5 22V3M5 4c5-4 9 4 15 0v10c-6 4-10-4-15 0"/>',
        "audit": '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 2h6v4H9zM8 11l2 2 4-4M8 17h8"/>',
        "requirements": '<path d="M9 6h12M9 12h12M9 18h12M3 6h1M3 12h1M3 18h1"/>',
        "care": '<path d="M12 21S3 15 3 9a5 5 0 019-3 5 5 0 019 3c0 6-9 12-9 12z"/>',
        "method": '<path d="M8 3H3v18h5M16 3h5v18h-5M14 7l-4 10"/>',
        "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
        "external": '<path d="M14 3h7v7M21 3l-9 9M10 3H4v17h17v-6"/>',
        "download": '<path d="M12 3v12M7 10l5 5 5-5M4 16v5h16v-5"/>',
        "search": '<circle cx="10" cy="10" r="6"/><path d="M15 15l6 6"/>',
        "info": '<circle cx="12" cy="12" r="9"/><path d="M12 10v7M12 6v1"/>',
        "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    }
    return f'<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{paths.get(name, paths["arrow"])}</svg>'


def badge(text, kind=None):
    if kind is None:
        kind = ("warn" if any(s in text.lower() for s in ("blocked", "unverified", "needs review", "withheld", "not possible", "limited", "testing", "progress"))
                else "good" if text.lower() in ("complete", "corrected", "verified snapshot", "content checked", "repository checked")
                else "blue" if "derived" in text.lower() or "design" in text.lower() else "neutral")
    return Markup(f'<span class="badge {kind}"><span class="tiny-dot"></span>{esc(text)}</span>')


def rich(title, sub=""):
    return Markup(f'<span class="row-title">{esc(title)}</span>' + (f'<span class="row-sub">{esc(sub)}</span>' if sub else ""))


def link(url, label, external=False, css=""):
    attr = ' target="_blank" rel="noopener noreferrer"' if external else ""
    return f'<a href="{esc(url)}"{attr}' + (f' class="{css}"' if css else "") + f'>{label}</a>'


def refs(row):
    pieces = []
    direct = row.get("source_url")
    if direct:
        pieces.append(link(direct, "Source row ↗", True))
    for sid in row.get("source_ids", ["REPO"]):
        src = SOURCES[sid]
        if src["url"] == direct:
            continue
        pieces.append(f'<a href="{esc(src["url"])}" title="{esc(src["title"])}" target="_blank" rel="noopener noreferrer">{esc(sid)} ↗</a>')
    return Markup("".join(pieces))


def table(table_id, title, columns, rows, *, note="", filter_options=None, export=True):
    """All body rows include registered official sources. Nulls stay empty."""
    headers = "".join(f'<th scope="col" aria-sort="none"><button type="button" data-sort="{i}">{esc(label)}<span class="sort-mark" aria-hidden="true">↕</span></button></th>' for i, (label, _) in enumerate(columns + [("Sources / references", "__refs")]))
    body = []
    for index, row in enumerate(rows):
        cells = []
        for _, field in columns:
            value = field(row) if callable(field) else row.get(field)
            if value is None or value == "":
                cells.append('<td class="blank" data-empty="true" aria-label="Blank — unverified, withheld or not applicable" title="Not supplied; see status and limitations"></td>')
            elif isinstance(value, Markup):
                cells.append(f'<td>{value}</td>')
            elif isinstance(value, (int, float)):
                text = str(value) if isinstance(value, int) else f"{value:.4f}".rstrip("0").rstrip(".")
                cells.append(f'<td class="num" data-value="{value}">{text}</td>')
            else:
                cells.append(f'<td>{esc(value)}</td>')
        cells.append(f'<td class="refs">{refs(row)}</td>')
        status = row.get("status", "")
        sources = " ".join(row.get("source_ids", ["REPO"]))
        body.append(f'<tr data-row-id="{esc(row.get("id", index))}" data-source-ids="{esc(sources)}" data-status="{esc(status)}">' + "".join(cells) + '</tr>')
    select = ""
    if filter_options:
        select = f'<label><span class="sr-only">Filter {esc(title)} by status</span><select data-status-filter="{table_id}"><option value="">All statuses</option>' + "".join(f'<option value="{esc(x)}">{esc(x)}</option>' for x in filter_options) + '</select></label>'
    exporting = f'<button class="export-button" type="button" data-export="{table_id}">{icon("download")} CSV<span class="sr-only">: {esc(title)}</span></button>' if export else ""
    return f'''<div class="table-card" data-table-card="{table_id}">
<div class="table-toolbar"><span class="row-count" data-count-for="{table_id}" aria-live="polite">{len(rows)} entries</span><div class="table-tools">{select}<label class="table-search">{icon("search")}<span class="sr-only">Search {esc(title)}</span><input type="search" placeholder="Filter rows…" data-search-for="{table_id}" autocomplete="off"></label>{exporting}</div></div>
<div class="table-scroll" role="region" aria-label="{esc(title)} table, scroll horizontally for more columns" tabindex="0"><table id="{table_id}" data-research-table><caption class="sr-only">{esc(title)}. Blank cells are intentional; sources and limitations are supplied per row.</caption><thead><tr>{headers}</tr></thead><tbody>{''.join(body)}</tbody></table></div><p class="table-empty" data-empty-for="{table_id}" hidden>No matching entries. Clear the filters to see all rows.</p></div>''' + (f'<p class="table-note">{note}</p>' if note else "")


def section(title, body, eyebrow="", subtitle="", action="", sid=""):
    attrs = f' id="{sid}"' if sid else ""
    return f'<section class="section"{attrs}><div class="section-head"><div>{f"<div class=eyebrow>{esc(eyebrow)}</div>" if eyebrow else ""}<h2>{title}</h2>{f"<p>{subtitle}</p>" if subtitle else ""}</div>{action}</div>{body}</section>'


def notice(title, text, info=False, action=True):
    return f'<div class="notice{" info" if info else ""}">{icon("info")}<div><strong>{title}</strong><p>{text}</p></div>' + (link("review.html", "Review limitations →") if action else "") + '</div>'


def metrics(items):
    return '<div class="metric-grid">' + ''.join(f'<div class="metric"><div class="metric-top">{esc(label)}<span class="metric-icon">{icon(i)}</span></div><div class="metric-value">{esc(value)}</div><small>{esc(note)}</small></div>' for label, value, note, i in items) + '</div>'


def chart():
    raw = [r for r in RESULTS["correlations"] if r["kind"] == "Raw statistics"]
    parts = ['<svg class="corr-chart" role="img" aria-labelledby="corr-plot-title corr-plot-desc" viewBox="0 0 460 190"><title id="corr-plot-title">Exploratory raw-stat Pearson correlations</title><desc id="corr-plot-desc">32 Nikola Jokić games. Points and rebounds: 0.035. Points and assists: -0.110. Rebounds and assists: 0.430. Horizontal bars are exploratory 95 percent block-bootstrap intervals, not evidence of betting skill.</desc>']
    for val in (-1, -0.5, 0, 0.5, 1):
        x = 117 + (val + 1) * 145
        parts.append(f'<line x1="{x}" x2="{x}" y1="10" y2="151" stroke="{"#afc2b0" if val == 0 else "#edf2eb"}" stroke-dasharray="{"3 3" if val == 0 else "0"}"/><text x="{x}" y="177" text-anchor="middle">{val:g}</text>')
    for i, row in enumerate(raw):
        y = 32 + i * 49
        point = 117 + (row["pearson"] + 1) * 145
        low, high = (117 + (row["interval"][k] + 1) * 145 for k in ("low", "high"))
        parts.append(f'<text x="0" y="{y+4}">{esc(row["pair"])}</text><line x1="{low}" x2="{high}" y1="{y}" y2="{y}" stroke="#c9d9c8" stroke-width="6" stroke-linecap="round"/><circle cx="{point}" cy="{y}" r="4" fill="#376a48"/><text class="estimate" x="456" y="{y+4}" text-anchor="end">{row["pearson"]:+.3f}</text>')
    parts.append('</svg><div class="chart-legend"><div><span></span>Pearson estimate</div><div><i></i>Exploratory 95% interval</div></div>')
    return ''.join(parts)


NAV = [
    ("Workspace", [("index.html", "Overview", "overview"), ("executive-summary.html", "Executive brief", "brief"), ("data.html", "Data library", "data")]),
    ("Research", [("signals.html", "Signal library", "signals"), ("lines.html", "Probability lab", "lab"), ("correlation.html", "Correlation", "correlation"), ("methodology.html", "Methodology", "method"), ("settlement.html", "Market evidence", "sources"), ("validation.html", "Validation gates", "validation"), ("leaderboard.html", "Leaderboard", "leaderboard")]),
    ("Transparency", [("sources.html", "Source register", "sources"), ("review.html", "Flagged for Review", "review"), ("audit.html", "Repository audit", "audit"), ("requirements.html", "Requirements", "requirements"), ("responsible-gambling.html", "Responsible use", "care")]),
    ("Housing research", [("rental/index.html", "SF rent research", "info")]),
]


def page(slug, title, subtitle, body, eyebrow="NBA / RESEARCH WORKSPACE"):
    navigation = ''
    for group, entries in NAV:
        navigation += f'<div class="nav-group"><div class="nav-label">{group}</div>'
        for href, label, ico in entries:
            current = ' aria-current="page"' if href == slug else ''
            count = f'<span class="nav-count">{OPEN_FLAGS}</span>' if href == 'review.html' else ''
            navigation += f'<a href="{href}"{current}>{icon(ico)}{label}{count}</a>'
        navigation += '</div>'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="OWN7 NBA research: source-linked observations, exploratory models, validation and transparent limitations."><meta name="referrer" content="strict-origin-when-cross-origin"><title>{esc(title)} · OWN7 Research</title><link rel="icon" href="assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="assets/style.css"><script src="js/app.js" defer></script></head>
<body><a class="skip-link" href="#main-content">Skip to content</a><aside class="sidebar" id="sidebar" aria-label="Research workspace"><a class="brand" href="index.html" aria-label="OWN7 Research Lab home"><span class="brand-mark" aria-hidden="true">7</span><span class="brand-name">OWN7<small>NBA RESEARCH LAB</small></span></a><nav aria-label="Main navigation">{navigation}</nav><div class="sidebar-bottom">{link(SOURCES['REPO']['url'], icon('external')+' View repository', True)}<div class="mode"><span class="dot"></span>NON-COMMERCIAL RESEARCH</div><p>No live lines. No wagers placed.</p></div></aside><button class="nav-backdrop" aria-label="Close navigation" tabindex="-1" hidden></button>
<div class="layout"><header class="topbar"><button type="button" class="menu-button" aria-label="Open navigation" aria-expanded="false" aria-controls="sidebar">{icon('menu')}</button><div class="breadcrumb"><span class="crumb-parent">Workspace</span><span class="divider">/</span><strong>{esc(title)}</strong></div><div class="top-right"><label class="search-field">{icon('search')}<span class="sr-only">Search tables on this page</span><input type="search" id="page-search" placeholder="Search this page…" autocomplete="off"><kbd aria-hidden="true">/</kbd></label><div class="snapshot">SNAPSHOT CHECKED<span>03 Nov 2026</span></div></div></header>
<main class="content" id="main-content"><div class="page-heading"><div><div class="eyebrow">{esc(eyebrow)}</div><h1>{esc(title)}</h1><p>{subtitle}</p></div><div class="heading-actions">{link('research/results.json', icon('download')+' Research JSON', css='button')}{badge('Research only', 'neutral')}</div></div>{body}
<footer class="footer"><div><strong>OWN7</strong> / INDEPENDENT RESEARCH<br>NBA statistics attributed to NBA.com. Not affiliated with or endorsed by the NBA.</div><div>Frozen snapshots · not a live feed<br>{link('review.html','Limitations')} &nbsp;·&nbsp; {link('sources.html','Sources')} &nbsp;·&nbsp; {link('responsible-gambling.html','Responsible use')}</div></footer></main></div></body></html>\n'''


def overview():
    body = notice('Evidence is available. A betting edge is not.', '107 official snapshot rows checked; six descriptive correlations calculated. No strategy has cleared all validation gates. Source rights and market-data gaps block betting-price release.')
    body += metrics([('Official snapshot rows', 107, '4 scoped datasets · source-linked', 'data'), ('Research hypotheses', 8, 'Singles, parlays & prop combinations', 'signals'), ('Paired-game estimates', 6, 'Plus separate aggregate studies', 'correlation'), ('Strategies approved', 0, 'No live lines or cash awards', 'validation')])
    body += f'''<section class="hero-panel"><div><div class="eyebrow">EVIDENCE BEFORE ACTION</div><h2>Better questions.<br>Stronger evidence.</h2><p>Build independent probability models. Test on information the model could actually have known. Reward repeatable evidence—not a run of fortunate results.</p>{link('executive-summary.html','Read the executive brief '+icon('arrow'),css='button primary')}</div><div class="hero-visual"><svg class="court" aria-hidden="true" viewBox="0 0 360 200" fill="none" stroke="currentColor" stroke-width="1.1"><rect x="4" y="4" width="350" height="190" rx="5"/><path d="M179 4v190M4 41h58v116H4M354 41h-58v116h58M4 70h20v58H4M354 70h-20v58h20"/><circle cx="179" cy="99" r="32"/><circle cx="62" cy="99" r="29"/><circle cx="296" cy="99" r="29"/><path d="M4 14a118 118 0 010 170M354 14a118 118 0 000 170"/><circle cx="18" cy="99" r="5"/><circle cx="340" cy="99" r="5"/></svg><div class="court-label"><span></span>Observe → test → qualify</div></div></section>'''
    cards = [('01 / ORIGINATE', 'signals', 'Start with a hypothesis', 'Eight model contracts, with their inputs, outputs and failure modes. No unsupported edge claims.', 'signals.html', 'Explore signal library'), ('02 / CHALLENGE', 'correlation', 'Measure the dependence', 'Paired observations, threshold-specific joint rates and honest uncertainty—not assumed correlation.', 'correlation.html', 'Inspect the calculations'), ('03 / QUALIFY', 'validation', 'Earn a place on the board', 'Ten fail-closed gates. Separate skill evidence from sample size, selection effects and luck.', 'validation.html', 'Review the gates')]
    body += '<div class="grid-3">' + ''.join(f'<a class="path-card" href="{href}"><span class="step">{step}</span><span class="card-icon">{icon(ico)}</span><h3>{title}</h3><p>{description}</p><span class="card-link">{cta} →</span></a>' for step,ico,title,description,href,cta in cards) + '</div>'
    chart_panel = f'<div class="panel"><div class="panel-title"><h3>A first look at correlation</h3>{badge("Exploratory", "blue")}</div><p class="footnote">Jokić · 32 games · 01 Feb–12 Apr 2026</p>{chart()}<p class="source-line">Calculated from {link(SOURCES["NBA-GAMES"]["url"],"official NBA game rows ↗",True)}. {link("correlation.html","Full methods & limitations →")}</p></div>'
    process = '<div class="panel"><div class="panel-title"><h3>The evidence pipeline</h3>'+badge('Paper only')+'</div><ol class="method-list">' + ''.join(f'<li><span class="step-number">{i:02d}</span><div><strong>{h}</strong><p>{p}</p></div></li>' for i,h,p in [(1,'Collect & attribute','Frozen official-source snapshots with exact scope, row checks and integrity receipts.'),(2,'Calculate & reproduce','Six correlations and 88 chronological probability demonstrations. No market values invented.'),(3,'Challenge & abstain','No pregame quote archive, data-use permission or untouched test: no strategy qualifies.')]) + '</ol><p class="source-line">'+link('methodology.html','How the pipeline works →')+'</p></div>'
    body += '<div class="grid-2">'+chart_panel+process+'</div>'
    rows = CATALOG['strategies']
    body += section('Research queue',table('overview-strategies','Research queue',[('Strategy',lambda r: rich(r['name'],r['id'])),('Category','category'),('State',lambda r: badge('Blocked')),('Passed gates',lambda r: '0 / 9 applicable' if r['category']=='Single bets' else '0 / 10 applicable')],rows,note='Hypotheses are project research designs. NBA and method links identify inputs/references, not evidence of profitability.'),eyebrow='8 HYPOTHESES · 0 QUALIFIED',action=link('signals.html','View all signal details →'))
    body += '<p class=source-line>'+link('settlement.html','Operator settlement evidence →')+' &nbsp;·&nbsp; '+link('responsible-gambling.html#netherlands','Netherlands scope →')+' &nbsp;·&nbsp; '+link('handoff/f58e9526/netherlands-scope.md','Original attributed Netherlands handoff')+'</p>'
    return body


def executive():
    findings = [
        {'finding':'Official historical team context','detail':'Denver led the checked 2025–26 table with 122.1 PTS per game; Lakers led FG% at 50.2. Earlier summaries were incorrect.','status':'Verified snapshot','source_ids':['NBA-TEAMS']},
        {'finding':'Observed data, not a live data service','detail':'30 team rows, 15 scoring-filtered players, 30 current-season standings rows and a complete explicit 32-game player window were checked.','status':'Verified snapshot','source_ids':['NBA-TEAMS','NBA-PLAYERS','NBA-GAMES']},
        {'finding':'Dependence must be measured, not narrated','detail':'Raw PTS/REB r=0.0345; PTS/AST r=−0.1096; REB/AST r=0.4296 in this cohort. These are sample estimates, not guarantees or betting edges.','status':'Derived · exploratory','source_ids':['NBA-GAMES','SCIPY-CORR']},
        {'finding':'Probability demonstration runs, but is not validation','detail':'Four base-rate event models use ten warmup games and earlier-game inputs for 22 later games each (88 rows). No pregame registration or market baseline exists.','status':'Derived · exploratory','source_ids':['NBA-GAMES','SK-TIME','SK-CAL']},
        {'finding':'A confirmed rights restriction changes the release','detail':'NBA terms §9(iv) prohibits using NBA Statistics in connection with gambling activity, including legal gambling. Separate permission is not evidenced. Betting-price release and bulk data collection are disabled.','status':'Needs review','source_ids':['NBA-TERMS']},
        {'finding':'No demonstrated profitable strategy','detail':'No operator quotes, qualified ROI, CLV, untouched test, prospective shadow record, funded cash pool or eligible winner. Those values stay blank.','status':'Blocked','source_ids':['REPO']},
    ]
    body = notice('Decision: research may be inspected; no betting system is approved.', 'No live lines, wagers, cash payouts or assertions that luck has been removed. The practical deliverable is an auditable research lab with explicit no-go gates.')
    body += metrics([('Checked observations',107,'Attribution and receipts retained','data'),('Candidate strategies',8,'All blocked from promotion','signals'),('Distinct game cohort',32,'One player, one selected window','correlation'),('Qualified strategies',0,'No demonstrated market edge','validation')])
    body += section('What matters',table('brief-findings','Executive findings',[('Finding','finding'),('Detail','detail'),('Evidence class',lambda r: badge(r['status']))],findings),eyebrow='EXECUTIVE SUMMARY')
    body += '<div class="grid-2"><div class="panel body-text"><h3>What the project now does</h3><p>Preserves source scope, verifies retained observations, calculates paired statistics, demonstrates chronological probability estimation, and rejects unsupported leaderboard entries. Each model family has a testable contract; every table row has an official input, method, or project-artifact link.</p><p>Pricing primitives, proper scores, multiple-testing adjustment, gate contracts and deterministic ranking are implemented and tested. The website builds without runtime dependencies, credentials or manual data entry.</p>'+link('requirements.html','Full requirements traceability →')+'</div><div class="panel body-text"><h3>What it does not establish</h3><p>No skill-based wagering edge, actual historical pregame availability, operator permission, current offer, correctly priced multi-leg bet or future profit. The small retrospective study is not a substitute for independent forward validation.</p><p>Luck cannot be eliminated. Reward rules use non-monetary merit points only, and no strategy currently qualifies. Unresolved rights and data items are published rather than silently filled in.</p>'+link('review.html',f'{OPEN_FLAGS} open review items →')+'</div></div>'
    body += '<div class="download-list">'+link('docs/executive-summary.md',icon('download')+' Markdown brief',css='button')+link('research/results.json',icon('download')+' Reproducible results',css='button')+link('research/evidence/receipts.json',icon('download')+' Verification receipts',css='button')+'</div>'
    return body


def data_library():
    body = notice('Snapshot verification is not a data license.', 'These are attributed, frozen statistical-audit observations from NBA.com, checked 03 Nov 2026. No live prices or gambling-use permission is inferred. See the confirmed source-use restriction.', action=True)
    body += '<div class="tabs" data-tabs aria-label="Data category">'+''.join(f'<a href="#{slug}">{label}<span>{n}</span></a>' for slug,label,n in [('team-data','Teams',30),('player-data','Players',15),('standings-data','Standings',30),('game-data','Game log',32)])+'</div>'
    specs = [
        ('team-data','Team traditional statistics','teams-2025-26',['Rank','Team','GP','W','L','WIN%','PTS','FG%','3P%','FT%','OREB','DREB','REB','AST','TOV','STL','BLK','PF','PFD','+/-'],'NBA-TEAMS','2025–26 regular season · per game. All 30 official rows. Percent columns preserve NBA display units (e.g. 50.2 means 50.2%). Rank is the official displayed tie rank, not a new sort order.'),
        ('player-data','Player scoring snapshot','players-2025-26-top15',['Rank','Player','Team','Age','GP','W','L','MIN','PTS','FGM','FGA','FG%','3PM','3PA','3P%','FTM','FTA','FT%','OREB','DREB','REB','AST','TOV','STL','BLK','PF'],'NBA-PLAYERS','2025–26 regular season · PTS ≥ 26 filter · 15 rows. This is a scoring-selected subset, not the whole player universe or an unbiased modeling sample. Age is the displayed snapshot field.'),
        ('standings-data','Standings snapshot','standings-2026-27',['Rank','Conference','Team','W','L','WIN%','GB','CONF','DIV','HOME','ROAD','LAST10','STREAK'],'NBA-STANDINGS','2026–27 snapshot checked 03 Nov 2026. Games played vary from 5 to 8 (W+L); too early for skill claims. “--” in GB is the official display, not an invented zero.'),
        ('game-data','Paired player game log','jokic-games-2025-26',['Date','GameID','Matchup','WL','MIN','PTS','REB','AST'],'NBA-GAMES','Nikola Jokić · 01 Feb–12 Apr 2026 · all 32 rows in the explicit one-page date window. MIN is the displayed integer value; no exact seconds inferred. Current-season profile-header averages are excluded.')]
    for sid,title,stem,fields,source_id,note in specs:
        rows=load_csv('data/'+stem+'.csv')
        for r in rows:r['source_ids']=[source_id];r['source_url']=r['Source']
        def value(field):
            def get(r):
                v=r.get(field)
                if field not in ('Team','Player','Date','GameID','Matchup','WL','Conference','CONF','DIV','HOME','ROAD','LAST10','STREAK','GB'):
                    try:return int(v) if '.' not in v and '%' not in v else float(v)
                    except (ValueError,TypeError):pass
                return v
            return get
        columns=[(f,value(f)) for f in fields]+[('Status',lambda r:badge('Verified snapshot','good'))]
        body += section(title,table(sid+'-table',title,columns,rows,note=esc(note)),subtitle=esc(note),action=link('data/'+stem+'.csv','Download source CSV ↓'),sid=sid)
    body += '<p class="footnote">'+link('research/evidence/README.md','How verification was performed')+' · '+link('research/evidence/receipts.json','Receipt hashes and exact source scopes')+'. Checksums prove integrity, not independent source truth.</p>'
    return body


def signals():
    body = notice('A plausible mechanism is a hypothesis—not an edge.', 'All eight candidates remain blocked. The 32-game probability demonstration is separate from a qualified market test. No strategy has verified quotes, returns or all-gate evidence.')
    body += '<div class="tabs"><a href="#single-bets">Single bets<span>3</span></a><a href="#parlays">Parlays<span>1</span></a><a href="#player-props">Player props & combos<span>4</span></a></div>'
    for category,sid,title in [('Single bets','single-bets','Single bets'),('Parlays','parlays','Parlays'),('Player props / combos','player-props','Player props & combinations')]:
        rows=[r for r in CATALOG['strategies'] if r['category']==category]
        def output(r):
            return Markup(f'<div class="row-detail">{esc(r["output"])}</div><details><summary>Failure modes</summary><p>{esc(r["risk"])}</p></details>')
        body += section(title,table(sid+'-table',title,[('Candidate',lambda r:rich(r['name'],r['id'])),('Research hypothesis','hypothesis'),('Model contract / limitations',output),('Status',lambda r:badge('Blocked'))],rows,note='Project design. Sources identify statistical inputs/methods; none validates the predictive value of this hypothesis.'),sid=sid)
    return body


def probability_lab():
    body = notice('Retrospective probability demo—not a live line.', 'Fixed illustrative thresholds and one selected historical player. No actual pregame timestamps, untouched test, sportsbook lines or participation forecast. NBA-derived betting prices are withheld by the source-rights gate.')
    body += '<div class="grid-2"><div class="panel body-text"><h3>A deliberately simple baseline</h3><p>For each event: take only games before the target date, count threshold hits, and use a Beta(1,1) prior. Start after ten warmup games. A combo uses paired <em>joint hits</em>, never a product of single-leg probabilities.</p><div class="formula">p_demo = (earlier hits + 1) / (earlier games + 2)</div><p>Thresholds: PTS &gt; 27.5, REB &gt; 12.5, AST &gt; 10.5; combo PTS &gt; 27.5 and AST &gt; 10.5. These are project choices, not verified offered lines or pre-registered selections.</p></div><div class="panel body-text"><h3>Read these results conservatively</h3><p>Each event has 22 chronological demonstrations, not 88 independent games. Lower scores against neutral p=0.5 do not establish skill: a rare combo can beat that baseline by its base rate alone.</p><p>No model tuning, market-relative skill, ROI, CLV or confirmatory p-value is claimed. Probabilities are calculated demonstration outputs, <strong>not official NBA values</strong>. Prices stay blank.</p>'+link('research/results.json','Download exact probabilities and run hashes →')+'</div></div>'
    body += section('Exploratory scoring',table('demo-scores','Demo proper scores',[('Event','event'),('Later games','forecasts'),('Log loss','log_loss'),('Brier score','brier'),('Neutral log loss','neutral_log_loss'),('Neutral Brier','neutral_brier'),('ROI','roi'),('CLV','clv')],RESULTS['demo']['summaries'],note='Neutral p=0.5 is an illustrative reference, not a market or competitive skill baseline. Do not compare raw log loss across events with different prevalence. All four variants are exploratory trials.'))
    body += section('Chronological probability ledger',table('forecast-ledger','Retrospective probability ledger',[('Date','date'),('Event','event'),('Illustrative threshold','threshold'),('History through','train_end'),('Prior games','training_games'),('Prior hits','training_hits'),('Calculated p','p_model'),('Observed hit','outcome'),('Betting price (withheld)','fair_model_decimal'),('Market odds','market_decimal'),('Edge','edge')],RESULTS['demo']['forecasts'],note='Observed hit is the settled historical threshold event from NBA rows. No contemporaneous prediction is alleged. Blanks are intentional; pricing is blocked, not zero.'))
    return body


def correlation_page():
    body = notice('Correlation values are sample estimates—not a betting recommendation.', 'Raw-stat Pearson r and threshold-hit φ are different quantities. All estimates here use the same 32 paired game rows, not season averages. Missing structures remain blank.',info=True)
    body += '<div class="grid-2"><div class="panel"><h3>Raw-stat relationships</h3><p class="footnote">Jokić · 01 Feb–12 Apr 2026 · n=32</p>'+chart()+'</div><div class="panel body-text"><h3>Uncertainty & scope</h3><p>10,000 paired circular moving-block resamples, five-game blocks, seed 20261103; percentile 95% intervals. Within-game pairs stay aligned; the finite block horizon is an assumption.</p><p>These exploratory intervals are not adjusted for selecting the player, dates, thresholds or comparisons. No formal significance or edge claim follows. A constant series produces a blank coefficient—not zero.</p><p>Actual multi-leg strategy validation additionally needs conditional pregame-model residuals, later joint calibration and an executable operator quote.</p>'+refs({'source_ids':['NBA-GAMES','SCIPY-CORR']})+'</div></div>'
    def interval(r):
        a,b=r['interval']['low'],r['interval']['high']
        return None if a is None or b is None else f'[{a:.4f}, {b:.4f}]'
    body += section('Correlation register',table('correlation-register','Correlation register',[('Pair','pair'),('Measurement','kind'),('Paired games','n'),('Pearson r / φ','pearson'),('Spearman ρ','spearman'),('Exploratory 95% CI',interval),('Evidence class',lambda r:badge(r['status']))],RESULTS['correlations'],note='Spearman is not additionally reported for binary indicators. Uncollected teammate, cross-game and three-plus-leg structures have no estimate, sample size or interval. No inferred zeroes.'))
    body += section('Threshold-event joint outcomes',table('joint-rates','Threshold-event joint rates',[('Hypothetical pair','pair'),('Games','n'),('Joint hits','joint_hits'),('P(A)','p_a'),('P(B)','p_b'),('P(A)×P(B)','p_independent'),('Observed P(A∩B)','p_joint'),('Difference','difference'),('φ','phi'),('Joint-rate 95% CI',lambda r:f'[{r["joint_interval"]["low"]:.4f}, {r["joint_interval"]["high"]:.4f}]')],RESULTS['joint_events'],note='Thresholds are hypothetical project choices, not sportsbook lines. Joint rates are empirical frequencies, not forecast probabilities. A dependence difference does not establish a price advantage.'))
    body += '<div class="panel body-text"><h3>Use the right identity</h3><div class="formula">P(A ∩ B) = p_A p_B + φ √[p_A(1−p_A)p_B(1−p_B)]</div><p>This identity applies to <strong>two Bernoulli hit indicators</strong> with their matching marginals. Check max(0, p_A+p_B−1) ≤ joint ≤ min(p_A,p_B). Do not insert a continuous points/assists correlation into this formula. Pairwise correlations do not identify a three-or-more-leg joint distribution. Zero continuous correlation does not imply independence.</p>'+refs({'source_ids':['SCIPY-CORR','REPO']})+'</div>'
    aggregate=[]
    for i,r in enumerate(load_csv('data/team-correlations-2025-26.csv')):
        aggregate.append({'id':'TEAM-'+str(i+1),'pair':r['Pair'],'n':int(r['n_teams']),'r':float(r['r']),'interval':None,'scope':'30 team-season averages; descriptive','source_ids':['NBA-TEAMS','SCIPY-CORR']})
    for r in load_json('handoff/f58e9526/correlation-computed-2025-26.json')['rows']:
        aggregate.append({'id':r['id'],'pair':r['pair'],'n':int(r['n_observations']),'r':r['_r'],'interval':r['ci_95'],'scope':'15 scoring-selected players' if int(r['n_observations'])==15 else '30 team-season averages','source_ids':['NBA-PLAYERS' if int(r['n_observations'])==15 else 'NBA-TEAMS','SCIPY-CORR']})
    body += section('Contributed aggregate studies',table('aggregate-correlations','Contributed aggregate correlations',[('Pair',lambda r:rich(r['pair'],r['id'])),('Population / scope','scope'),('Rows','n'),('Calculated r','r'),('Nominal Fisher interval','interval')],aggregate,note='17 contributed rows, including overlapping pairs; not 17 unique independent discoveries. Aggregate correlations are not game-leg correlations. Fisher intervals assume independent, approximately bivariate-normal observations; teams play one another and players were scoring-selected, so these nominal intervals are not established coverage for a population or betting strategy. No multiple-testing or predictive significance claim.'),action=link('handoff/f58e9526/correlation-computed-2025-26.json','Attributed handoff JSON ↓'))
    return body


def validation_page():
    body=notice('All ten gates must clear before ranking.', 'No current strategy qualifies. Gate checks enforce the absence of evidence rather than turning a source URL or a small winning sample into a pass. Thresholds below are project design choices, not NBA or scientific standards.')
    body+=section('Validation policy',table('gate-policy','Validation gates',[('Gate',lambda r:rich(r['name'],r['id'])),('Pass rule','pass_rule'),('Current evidence','current'),('State',lambda r:badge('Blocked'))],CATALOG['gates'],note='For single bets only, G05 is explicitly not applicable with a recorded artifact; it is not counted as a pass. Structural eligibility validation does not itself conduct the scientific tests.'))
    rows=RESULTS['evaluations']
    body+=section('Per-strategy gate matrix',table('gate-matrix','Per strategy gate evidence',[('Strategy',lambda r:rich(r['name'],r['strategy_id'])),('Category','category')]+[(g,lambda r,g=g:'N/A · single' if r['gate_evidence'][g]['status']=='not applicable' else 'Blocked') for g in [f'G{i:02d}' for i in range(1,11)]]+[('Eligible',lambda r:'No')],rows,note='No pass is manufactured. All missing or blocked gate artifacts prevent leaderboard eligibility; the full machine-readable evidence is in research/results.json.'))
    body+='<div class="panel body-text"><h3>Luck is not removable</h3><p>Separate development, calibration, validation and a sealed common final test in time. Keep all legs of a game together. Use pregame publication/capture timestamps, log every attempted model and rejected offer, and check dependence across dates and seasons.</p><p>A minimum count is merely a screen. Power depends on the expected effect, variance, stake policy and dependence. Positive CLV, a low p-value or a favorable short-run return alone does not establish transferable skill. A new frozen forward test is required after exploration.</p>'+refs({'source_ids':['SK-TIME','SK-CAL','SM-HOLM']})+'</div>'
    return body


def leaderboard():
    body=notice('No eligible strategies. No rewards awarded.', 'The competition framework is implemented, not populated with fictional winners. All eight candidates are blocked. Cash payments and entry fees are disabled; funding and cash prize amounts are unverified.')
    body+='<div class="table-card"><div class="empty-state"><span class="empty-icon">'+icon('leaderboard')+'</span><h3>A place on the board has to be earned.</h3><p>Only source-backed, pre-registered strategies that pass every applicable gate may rank. Current observations and exploratory model demos are not entries.</p>'+link('validation.html','Inspect validation evidence →',css='button')+'</div></div>'
    rules=[('Separate divisions','Single bets, parlays, and player props/combos. No combined risk-obscuring league table.'),('Primary ranking','Within a common future window, offer universe and flat-paper exposure policy: rank by lower 95% date-block-bootstrap bound of net return per unit, after costs. Must be positive.'),('Ties','Lower log loss on the same evaluation events, then earlier frozen submission, then strategy ID. No comparison across different event universes.'),('Evidence floor','500 settled selections, 200 distinct games, 60 dates, declared power calculation; plus prospective shadow at least 60 calendar days and 200 games. Floors are project policy, not guarantees.'),('Multiplicity','All variants, rejected attempts and this exploratory work are counted before a new sealed contest. Holm familywise α=0.05 with valid predeclared null tests.'),('Paper exposure','Flat one unit per selection; at most one unit/game, five/day; stop at ten-unit drawdown. Reserve exposure before outcomes; log abstentions.'),('Non-cash rewards','Top eligible ranks receive 3 / 2 / 1 non-transferable merit points. No winner means no points. No cash, tokens, credits or monetary value.'),('Release conditions','No betting-price release or commercial data use without rights review and lawful operator contracts. NBA source restriction is confirmed; no separate permission established.')]
    rows=[{'component':a,'rule':b,'status':'Project design','source_ids':['REPO','NBA-TERMS'] if a=='Release conditions' else ['REPO']} for a,b in rules]
    body+=section('Competition charter',table('competition-charter','Competition rules',[('Component','component'),('Rule','rule'),('Evidence class',lambda r:badge('Project design','blue'))],rows),eyebrow='RULES BEFORE RESULTS')
    body+=section('Candidate status—not rankings',table('candidate-status','Candidate qualification status',[('Candidate',lambda r:rich(r['name'],r['strategy_id'])),('Category','category'),('Passes','passed_gates'),('Rank','rank'),('ROI','roi'),('ROI lower bound','roi_lcb95'),('CLV','clv'),('Reward','reward'),('State',lambda r:badge('Blocked'))],RESULTS['evaluations'],note='Zero gate passes is known from local evidence; null ranks/ROI/CLV/rewards are not zero performance. There are no qualifying wagers or cash rewards.'))
    return body


def methodology():
    formulas=[
        ('Fair price','For win probability p and no push/void: fair decimal d=1/p. With push probability q: d=(1−q)/p; undefined when p=0.','Mathematical identity; generic implementation tested on synthetic inputs.'),
        ('Executable expected value','EV per unit = p_win(d_quote−1) − p_lose. Push returns stake (net zero). Evaluate the full actual settlement/void matrix for combos.','Do not substitute a de-vigged fair price for an actual executable quote.'),
        ('Proportional de-vig','q_i=(1/d_i) / Σ_j(1/d_j) across a complete mutually exclusive outcome set at the same operator, line and timestamp.','Modeling convention, not identification of true probabilities; other margin allocations differ.'),
        ('Multi-leg pricing','Use P(all requested legs) and the actual combined operator price. Multiplying probabilities assumes full independence; multiplying listed odds is not a general SGP rule.','Pairwise dependence alone is insufficient for three or more legs.'),
        ('Proper scoring','Log loss = −mean[y log p+(1−y)log(1−p)]; Brier = mean[(p−y)²]. Examine reliability separately.','Lower aggregate score is not solely better calibration, and scores across different event prevalences are not comparable.'),
        ('Multiple tests','Holm-adjust all valid raw p-values across the complete registered attempt family; freeze the family before confirmatory analysis.','No confirmatory p-values are generated from this small selected cohort.')]
    rows=[{'method':a,'formula':b,'limitation':c,'source_ids':['SK-CAL'] if a=='Proper scoring' else ['SM-HOLM'] if a=='Multiple tests' else ['REPO','SCIPY-CORR']} for a,b,c in formulas]
    body=notice('Generic pricing math exists; NBA betting-price release is blocked.', 'NBA terms §9(iv) is a confirmed restriction. No separate gambling-use permission or market contract is evidenced. Frozen statistical audit and methods demonstration only.')
    body+=section('From probabilities to a price',table('method-formulas','Pricing and scoring definitions',[('Method','method'),('Definition / procedure','formula'),('Boundary','limitation')],rows,note='These are mathematical definitions and project implementations, not externally verified performance or permission to wager.'),sid='settlement')
    body+='<div class="grid-2"><div class="panel body-text"><h3>Team line-origination contract</h3><p>Fit lagged opponent-adjusted offense, defense, possessions, home court, rest and known availability. Estimate a coherent joint final-score distribution. Derive margin cover, total and moneyline probabilities from that same distribution, including overtime/push rules.</p><p>No fitted team model or current game price is claimed. The season summary is context, not a substitute for pregame game-level training data. Hyperparameters and model choice belong inside development folds.</p>'+refs({'source_ids':['NBA-GLOSSARY','NBA-TEAMS','SK-TIME']})+'</div><div class="panel body-text"><h3>Player / combination contract</h3><p>Model participation and minutes before per-minute role/opportunities and count outcomes. Use only information published by the decision cutoff. For teammates, model shared possessions and role constraints; for all combinations, validate the joint predictive distribution.</p><p>No same-team correlation sign is presumed. Final observed minutes are outcomes, not available pregame features. The complete player universe is needed to audit selection bias.</p>'+refs({'source_ids':['NBA-INJURY','NBA-GAMES','SCIPY-CORR']})+'</div></div>'
    body+=section('Reproduce without manual entry','<div class="panel body-text"><div class="formula">python -m nba_lab run<br>python -m unittest discover -s tests -v<br>python scripts/build_site.py<br>python scripts/check_site.py<br>npm ci &amp;&amp; npm run test:browser</div><p>The build is offline and deterministic from committed, receipt-checked snapshots. The analysis manifest contains input/code hashes and a run hash. No accounts, API keys, price entry, real-money wagers or source-data scraping is required.</p><p>Scheduled source-health checks only inspect source availability and save an audit artifact; they never promote facts, mutate data, harvest NBA game feeds, or place bets. A URL health check is not line-by-line factual verification. New data cannot silently overwrite this historical snapshot.</p>'+refs({'source_ids':['REPO','GH-PAGES','NBA-TERMS']})+'</div>',sid='automation')
    return body


def settlement_page():
    rows=[]
    for r in MARKET['findings']:
        rows.append({**r,'source_ids':[INTEGRATION['market_source_map'][k] for k in r['sources']]})
    body=notice('Operator rules differ. These are document examples—not available bets.', 'All 24 contributed findings and six MF discrepancies were retained and the relevant official paragraphs independently re-read. Dates, market labels and jurisdictions matter. No quote, current product availability, governing wager contract or personal eligibility is inferred.')
    body+=section('Settlement evidence register',table('settlement-evidence','Official settlement examples',[('Record',lambda r:rich(r['category'],r['id'])),('Operator / jurisdiction','operator_scope'),('Documented finding','finding'),('Research handling','research_implication'),('Exact source locator','source_location')],rows,note='TOTO April 2026 PDF is a dated version, not confirmed current governing terms. Fanatics Ohio and Oneida Wisconsin examples do not establish Dutch law. The UK code is scoped to its stated licensees. MF01–MF06 remain visible on the central review register.'))
    body+='<div class="download-list">'+link('market-evidence/index.html','Original attributed evidence dossier →',css='button')+link('market-evidence/evidence.json',icon('download')+' Source evidence JSON',css='button')+link('research/evidence/settlement-recheck.json','Independent recheck scope',css='button')+link('review.html','All unresolved MF flags →',css='button')+'</div>'
    return body


def source_page():
    rows=[{**s,'source_ids':[s['id']]} for s in SOURCES.values()]
    body=notice('A citation supports a specific scope—not every nearby claim.', 'NBA rows are verified snapshots; statistical results are labeled derived; model and competition rules are project designs. Official methodology documentation is a primary source for the method, not proof of an NBA edge.',info=True,action=False)
    body+=section('Primary and project references',table('source-register','Source register',[('Source',lambda r:rich(r['title'],r['id'])),('Authority','authority'),('What was actually checked','scope'),('Checked','checked_on'),('State',lambda r:badge(r['status']))],rows,note=f'{len(SOURCES)-1} external primary sources plus the official project repository. All external records were content-checked through fetch_page, not asserted as direct HTTP 200 checks. Terms and glossary checks are explicitly scoped in the source JSON.'))
    receipts=load_json('research/evidence/receipts.json')
    for r in receipts:r['source_ids']=[{'teams-2025-26':'NBA-TEAMS','players-2025-26-top15':'NBA-PLAYERS','standings-2026-27':'NBA-STANDINGS','jokic-games-2025-26':'NBA-GAMES'}[r['id']]]
    body+=section('Observation receipts',table('source-receipts','Source receipts',[('Dataset','data_file'),('Rows','retained_rows'),('Evidence method','method'),('Scope / corrections','note'),('SHA-256',lambda r:Markup(f'<span class="audit-hash">{r["sha256"]}</span>'))],receipts,note='Evidence is a normalized transcription reviewed against rendered official content, not a raw response archive. Integrity hashes do not independently prove truth.'))
    body+='<div class="download-list">'+link('research/sources.json',icon('download')+' Source registry JSON',css='button')+link('research/evidence/receipts.json',icon('download')+' Receipts JSON',css='button')+link('research/evidence/README.md','Verification boundary',css='button')+'</div>'
    return body


def review_page():
    body=notice(f'{OPEN_FLAGS} open items. All are visible; none is silently filled in.', 'Review flags do not block publishing an honest research website. They do block unsupported strategy promotion, NBA-derived betting-price release and cash operations. Corrected historical irregularities remain in the register.',action=False)
    body+=metrics([('Open review items',OPEN_FLAGS,'Rights, market evidence & limits','review'),('Historical corrections',len(CATALOG['flags'])-OPEN_FLAGS,'Kept in the audit trail','audit'),('Executable lines',0,'No unsupported release','validation'),('Cash awards',0,'No funding or winner inferred','leaderboard')])
    body+=section('Flagged for Review',table('review-register','Flagged for Review',[('Item',lambda r:rich(r['item'],r['id'])),('Finding / disposition','finding'),('Unverified value','unverified_value'),('State',lambda r:badge(r['status']))],CATALOG['flags'],filter_options=['Needs review','Corrected'],note='Blank unverified-value cells are intentional. Context or method links do not verify missing prices, permissions, contact numbers, cash funds or performance. No manual input is required to reproduce this release.'))
    return body


def audit_page():
    rows=load_json('research/audit/file-review.json')
    body=notice('Review coverage is not a claim that every old assertion was true.', '54 baseline files / 2,630 text lines were inventoried and reviewed by scope. Retained NBA observations were rechecked; unverifiable or stale historical statements were withdrawn. Code and links are checked mechanically, not certified as external facts.',info=True)
    body+='<div class="grid-2"><div class="panel body-text"><h3>What changed</h3><ul><li>One generated dashboard replaces three inconsistent public views.</li><li>Incorrect team-summary maxima and Utah rank corrected.</li><li>Unfounded correlation signs, independence and payout claims removed.</li><li>Stale Alberta/helpline/media claims retired from active facts.</li><li>Root-only link checks replaced with recursive source, blank, receipt, build and browser tests.</li></ul></div><div class="panel body-text"><h3>Preservation & coordination</h3><p>Original contents remain at baseline commit <code>14c5f50</code>. Inventory hashes, full line scopes and per-file dispositions make the re-audit inspectable. Historical coordination boards were retained; no other session branch was changed.</p><p>Work is integrated only on <code>arena/a934e8c3-own7</code>, the session’s fixed branch. Historical documentation PR #4 was left untouched and is now closed.</p>'+link('COORDINATION.md','Read the coordination and release record →')+'</div></div>'
    body+=section('Full baseline file review',table('file-audit','Baseline file audit',[('Baseline file','path'),('Lines reviewed','review_scope'),('Line count','lines'),('Disposition','disposition'),('Review result','finding'),('Original SHA-256',lambda r:Markup(f'<span class="audit-hash">{r["sha256"]}</span>'))],rows,note='Each row links to the exact official GitHub baseline artifact. NBA input links are added where facts were reconciled. “Reviewed” means the stated technical/factual scope, not verification of superseded external claims.'))
    body+='<div class="download-list">'+link('research/audit/file-review.json',icon('download')+' Full file audit',css='button')+link('research/audit/baseline-inventory.json','Baseline integrity inventory',css='button')+link('research/audit/check-results.json','Automated verification evidence',css='button')+'</div>'
    incoming=load_json('research/audit/parallel-review.json')
    body += section('Parallel contributions reconciled',table('parallel-audit','Incoming main file review',[('Incoming path','path'),('Lines reviewed','review_scope'),('Disposition','disposition'),('Review / reconciliation','finding')],incoming,note='Incoming main commit 37e1bbd: all 77 files inventoried. Source dossiers, numeric transcriptions, correlation calculations and append-only boards retained. Shared canonical views regenerated. Superseded claims remain inspectable in immutable GitHub history, not silently republished as verified.'),action=link('research/audit/parallel-review.json','Incoming-main audit JSON ↓'))
    return body


def requirements_page():
    rows=load_json('research/requirements.json')
    for r in rows:r['artifact_link']=Markup(link(r['artifact'],'Inspect artifact →'))
    return notice('A requirements ledger, not a blanket completion claim.', 'Blocked scientific, legal or market requirements remain explicitly blocked; a live website does not turn an unverified model into a qualified strategy.',info=True)+section('Request-to-evidence traceability',table('requirements-ledger','Requirements traceability',[('Requirement',lambda r:rich(r['requirement'],r['id'])),('Disposition / evidence','evidence'),('Artifact','artifact_link'),('Status',lambda r:badge(r['status']))],rows,note='All project design defaults are distinguished from external facts. Release evidence and deployment status are recorded in COORDINATION.md.'))


def responsible_use():
    rows=[{'topic':'Research boundary','detail':'No wagers, gambling accounts, live signals, prize payments or paid-data subscriptions are operated. Generic math does not make a strategy safe.','source_ids':['REPO']},{'topic':'Source rights','detail':'NBA terms §9(iv) prohibits NBA Statistics use connected with gambling activity. Separate permission is not evidenced; no gambling data service is claimed.','source_ids':['NBA-TERMS']},{'topic':'Dutch regulator register','detail':'Kansspelwijzer exists and lists Online sportweddenschap. An entry or a help page is not proof of current NBA markets, offered lines or your eligibility. No complete operator audit was performed.','source_ids':['KSA-REGISTER']},{'topic':'Free self-exclusion','detail':'Gokstop links to Cruks for safe, easy, free self-exclusion. Cruks says the stop covers Dutch-licensed sites, casinos and gaming arcades and lasts at least six months.','source_ids':['NL-GOKSTOP','MKT-CRUKS']},{'topic':'Support independently confirmed','detail':'Open over Gokken: free and anonymous support. The official Cruks contact page lists 0800 24 000 22, available 24/7. Earlier H-08 unknown is now resolved for this source/snapshot only.','source_ids':['MKT-CRUKS-CONTACT']},{'topic':'Dutch NBA offer universe','detail':None,'status':'Unverified · blank','source_ids':['KSA-REGISTER']},{'topic':'US memo applicability in the Netherlands','detail':None,'status':'Unverified · blank','source_ids':['KSA-REGISTER','NBA-TERMS']},{'topic':'Outcome uncertainty','detail':'Past scores, correlations, positive CLV and lower proper scores do not remove luck or guarantee future profit. No validated edge is claimed.','source_ids':['SK-CAL','REPO']},{'topic':'Rewards','detail':'Merit points have no monetary/transferable value. No entry fee, funded cash pool or eligible winner.','source_ids':['REPO']}]
    body=notice('This is a research website—not a gambling product.', 'Source-use limits and incomplete validation are substantive no-go conditions. Dutch context is not advice on your eligibility; foreign operator examples are not Dutch law.',info=True,action=False)
    body+=section('Netherlands & responsible-use boundaries',table('responsible-use','Netherlands and responsible-use scope',[('Topic','topic'),('Confirmed scope / value','detail'),('State',lambda r:badge(r.get('status','Source / project scope')))],rows,note='NL01/NL02 keep operator NBA availability and foreign-rule applicability blank. NL03 resolves the previous phone-number gap using the official Cruks contact. No Alberta number is inferred.'),sid='netherlands')
    body+='<div class="panel body-text"><h3>If gambling is affecting you</h3><p>For current Dutch support and self-exclusion, use the official '+link(SOURCES['MKT-CRUKS-CONTACT']['url'],'Cruks contact page ↗',True)+' and '+link(SOURCES['KSA-PLAYERS']['url'],'Kansspelautoriteit player page ↗',True)+'. The checked Cruks page lists Open over Gokken at <strong>0800 24 000 22</strong>, 24/7, free and anonymous.</p><p>'+link('handoff/f58e9526/netherlands-scope.md','Original attributed Netherlands handoff')+' (historical; its blank H-08 is superseded by the independent contact-page check above).</p></div>'
    return body


ALIASES = {
    'findings.html':'data.html','pages/dashboard.html':'index.html','pages/executive-summary.html':'executive-summary.html','pages/single-bets.html':'signals.html#single-bets','pages/parlays.html':'signals.html#parlays','pages/player-props.html':'signals.html#player-props','pages/correlation.html':'correlation.html','pages/validation-gates.html':'validation.html','pages/flagged.html':'review.html',
    'verified/index.html':'index.html','verified/executive-summary.html':'executive-summary.html','verified/sources.html':'sources.html','verified/betting-rules.html':'methodology.html#settlement','verified/strategies.html':'signals.html','verified/validation-gates.html':'validation.html','verified/correlation.html':'correlation.html','verified/leaderboard.html':'leaderboard.html','verified/repo-review.html':'audit.html','verified/flagged.html':'review.html','verified/responsible-gambling.html':'responsible-gambling.html',
}


def build():
    verify_receipts()
    pages = {
        'index.html':('Research overview','An evidence-first workspace for independent NBA probability research. Observe carefully. Test honestly. Know when not to act.',overview()),
        'executive-summary.html':('Executive brief','The important findings, verified observations, research progress and non-negotiable limits—in one place.',executive()),
        'data.html':('Data library','Four frozen official-source datasets. Every retained row is attributed, scoped and checked; nothing here is a live market feed.',data_library()),
        'signals.html':('Signal library','Eight testable research hypotheses across singles, parlays and player-prop combinations. None is a proven edge.',signals()),
        'lines.html':('Probability lab','A small, reproducible chronological demonstration. Calculated probabilities—not official forecasts, market lines or evidence of skill.',probability_lab()),
        'correlation.html':('Correlation','Replace correlation stories with paired measurements, threshold-specific joint outcomes and uncertainty.',correlation_page()),
        'methodology.html':('Methodology','Clear model contracts, correct pricing mathematics and a reproducible pipeline—with explicit release boundaries.',methodology()),
        'validation.html':('Validation gates','Evidence earns eligibility. Missing data, source restrictions and inconclusive tests never count as a pass.',validation_page()),
        'leaderboard.html':('Leaderboard','Reward qualified evidence, not a hot streak. Separate divisions, frozen rules and no fictional winners.',leaderboard()),
        'settlement.html':('Market evidence','Operator-specific settlement examples and unresolved discrepancies. A document example is not proof of a current offered wager.',settlement_page()),
        'sources.html':('Source register','Follow every observation and method to its primary source. A link is a reference—not blanket verification.',source_page()),
        'review.html':('Flagged for Review','Unverified values, confirmed restrictions and corrected irregularities—published plainly for review.',review_page()),
        'audit.html':('Repository audit','A scoped, line-by-line review of the inherited repository, with original hashes, source links and dispositions.',audit_page()),
        'requirements.html':('Requirements','A traceable ledger from the full request to the evidence, deliverables and honest remaining constraints.',requirements_page()),
        'responsible-gambling.html':('Responsible use','Research boundaries, source rights and official player-protection information. No wagering service is operated here.',responsible_use()),
    }
    generated=['market-evidence/index.html']
    # Auxiliary sub-site (session arena/cab077aa-own7): anonymized SF rent-increase research.
    rental_result=subprocess.run([sys.executable,str(ROOT/'rental'/'build.py')],cwd=ROOT,capture_output=True,text=True)
    if rental_result.returncode: raise SystemExit(rental_result.stdout+rental_result.stderr)
    rental_pages=load_json('rental/manifest.json')['pages']
    for name in rental_pages:
        generated.append(f'rental/{name}')
    for slug,(title,subtitle,body) in pages.items():
        (ROOT/slug).write_text(page(slug,title,subtitle,body),encoding='utf-8');generated.append(slug)
    for old,target in ALIASES.items():
        href=('../' if '/' in old else '')+target
        text=f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url={esc(href)}"><title>Page moved · OWN7</title></head><body><main><h1>This research page has moved.</h1><p>The parallel legacy sites have been reconciled. <a href="{esc(href)}">Continue to the current source-linked dashboard</a>.</p><p>Old claims are not republished as verified. See the current audit and review register.</p></main></body></html>\n'
        (ROOT/old).write_text(text,encoding='utf-8');generated.append(old)
    canonical={
        'sources':'research/sources.json','rules':'research/protocol.json','helplines':'responsible-gambling.html','strategies':'research/catalog.json','gates':'research/catalog.json','correlation':'research/results.json','leaderboard':'research/results.json','repo_review':'research/audit/file-review.json','flagged':'research/catalog.json'}
    for name,target in canonical.items():
        path=ROOT/f'verified/data/{name}.json'
        path.write_text(encode({'deprecated':True,'canonical':'../../'+target,'rows':[],'note':'Superseded parallel schema. Original assertions preserved only in the baseline git commit; do not treat as current verified facts.'}),encoding='utf-8')
    for file in ('.nojekyll','verified/.nojekyll'):(ROOT/file).write_text('',encoding='utf-8')
    manifest={'canonical_pages':list(pages),'auxiliary_pages':['market-evidence/index.html']+[f'rental/{n}' for n in rental_pages],'legacy_redirects':ALIASES,'generated_html':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sorted(generated)},'research_run_hash':RESULTS['run_hash']}
    (ROOT/'research/site-manifest.json').write_text(encode(manifest),encoding='utf-8')
    print(f'Built {len(pages)} canonical pages + {len(ALIASES)} compatibility redirects; single source of truth.')


if __name__=='__main__':
    build()
