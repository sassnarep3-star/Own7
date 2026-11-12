#!/usr/bin/env python3
"""Deterministic static assurance dashboard. No network, no inferred values."""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import io
import json
from pathlib import Path
import availability
import engine

ROOT = Path(__file__).resolve().parent
SITE = ROOT / 'site'
PAGES = [
    ('index.html', 'NFL assurance overview'),
    ('executive-summary.html', 'Executive summary'),
    ('requirements.html', 'Requirements ledger'),
    ('injuries.html', 'Injury report'),
    ('depth.html', 'Printed depth chains'),
    ('availability.html', 'Availability & replacement exposure'),
    ('lines.html', 'Line origination'),
    ('strategies.html', 'Signal strategies'),
    ('correlation.html', 'Correlation'),
    ('validation.html', 'Validation gates'),
    ('leaderboard.html', 'Leaderboard'),
    ('suggestions.html', 'Suggestions'),
    ('questions.html', 'Questions & answers'),
    ('sources.html', 'Source register'),
    ('flagged.html', 'Flagged for review'),
    ('methodology.html', 'Methodology'),
    ('repo-review.html', 'Repository review'),
    ('data.html', 'Data library'),
    ('responsible-use.html', 'Responsible use'),
]


def esc(value):
    return html.escape('' if value is None else str(value), quote=True)


def load(name):
    return json.loads((ROOT / name).read_text())


def sources():
    return {s['id']: s for s in load('sources/registry.json')}


def source_links(ids, reg=None):
    reg = reg or sources()
    return ' '.join(f'<a href="{esc(reg[i]["url"])}" rel="noopener noreferrer">{esc(i)}</a>' for i in ids if i in reg)


def blank():
    return '<td data-empty></td>'


def cell(value, *, empty=False, cls=None):
    if empty or value is None:
        return blank()
    attr = f' class="{esc(cls)}"' if cls else ''
    return f'<td{attr}>{esc(value)}</td>'


def row(cells, ids, reg=None, attrs=''):
    reg = reg or sources()
    return f'<tr data-source-ids="{esc(" ".join(ids))}"{attrs}>{"".join(cells)}<td class="src">{source_links(ids, reg)}</td></tr>'


def table(table_id, caption, headers, rows, *, note=None, filters=None):
    controls = ''
    if filters:
        controls += f'<div class="controls"><label>Search <input type="search" data-search="{table_id}" placeholder="Filter rows…"></label>'
        for key, label, options in filters:
            controls += f'<label>{esc(label)} <select data-filter="{table_id}" data-filter-key="{esc(key)}"><option value="">All</option>' + ''.join(f'<option value="{esc(o)}">{esc(o)}</option>' for o in options) + '</select></label>'
        controls += f'<button type="button" data-export="{table_id}">Export visible CSV</button><span class="count" data-count="{table_id}"></span></div>'
    head = ''.join(f'<th scope="col">{esc(h)}</th>' for h in headers) + '<th scope="col">Official source</th>'
    note_html = f'<p class="note">{note}</p>' if note else ''
    return f'''{controls}{note_html}<div class="table-wrap"><table id="{table_id}"><caption>{esc(caption)}</caption><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div><p class="empty-state" data-empty-for="{table_id}" hidden>No rows match the current filters.</p>'''


def layout(slug, title, body, subtitle=''):
    nav = ''
    for name, label in PAGES:
        current = ' aria-current="page"' if name == slug else ''
        nav += f'<a href="{esc(name)}"{current}>{esc(label)}</a>'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · NFL assurance</title><link rel="stylesheet" href="style.css"></head>
<body><a class="skip" href="#main">Skip to content</a><header class="top"><div class="brand"><strong>OWN7</strong><span>NFL assurance handoff</span></div><nav aria-label="Assurance sections">{nav}</nav></header>
<main id="main"><p class="eyebrow">Bounded snapshot · checked 2026-11-12 · informational only</p><h1>{esc(title)}</h1>{f'<p class="subtitle">{esc(subtitle)}</p>' if subtitle else ''}{body}</main>
<footer><p>No wagers are placed. Unknown values stay blank. <a href="../../nfl/index.html">Canonical NFL research</a> · <a href="../../nfl/origination/index.html">NFL line origination</a> · <a href="sources.html">Sources</a> · <a href="flagged.html">Flagged for review</a></p></footer>
<script src="app.js"></script></body></html>'''


def cards(items):
    return '<div class="cards">' + ''.join(f'<a class="card" href="{esc(href)}"><h2>{esc(title)}</h2><p>{esc(text)}</p></a>' for href, title, text in items) + '</div>'


def kpis(items):
    return '<div class="kpis">' + ''.join(f'<div class="kpi"><span class="kpi-value">{esc(value)}</span><span class="kpi-label">{esc(label)}</span></div>' for value, label in items) + '</div>'


def build_pages():
    reg = sources()
    data = availability.build()
    decisions = load('decisions.json')
    strategies = load('strategies.json')
    findings = load('data/findings.json')
    audit = load('audit/baseline-lines.json')
    receipts = load('sources/receipts.json')
    s = data['summary']
    pages = {}

    index_body = kpis([(s['injury_rows'], 'official injury rows'), (s['depth_slots'], 'printed club slots'), (s['depth_teams'], 'club charts'), (0, 'qualified strategies'), (len(findings), 'published flags'), (len(decisions['suggestions']), 'reviewable proposals')])
    index_body += '<p class="lead">This is an independent assurance supplement to the canonical NFL research and line-origination labs. It preserves a bounded Week 10 injury/depth snapshot, a full frozen-repository line/hash inventory, executable fail-closed research gates, and a decision queue. It does not publish betting prices, claim an edge, or infer missing values.</p>'
    index_body += cards([(href, label, desc) for href, label, desc in [
        ('executive-summary.html', 'Executive summary', 'What is known, blocked and next.'),
        ('injuries.html', 'Injuries', '276 official rows; blanks are not availability.'),
        ('depth.html', 'Depth chains', '289 printed slots; shared cells and gaps preserved.'),
        ('availability.html', 'Replacement exposure', 'Out starters and later-listed absences; no confirmed replacement.'),
        ('strategies.html', 'Strategies', 'Eight testable hypotheses across singles, parlays and props.'),
        ('validation.html', 'Validation gates', 'Twelve fail-closed gates; no real candidate qualifies.'),
        ('suggestions.html', 'Suggestions', 'Proposals with benefit, tradeoff and acceptance tests.'),
        ('questions.html', 'Questions', 'Known information, answers and missing-information discovery.'),
        ('flagged.html', 'Flagged for review', 'Irregularities and unverified values, published plainly.'),
        ('repo-review.html', 'Repository review', '150 files / 14,244 lines inventoried at the frozen baseline.'),
        ('sources.html', 'Sources', 'Every row links to an official source actually checked.'),
        ('data.html', 'Data library', 'Download CSV/JSON with source URLs and boundaries.'),
    ]])
    index_body += '<section class="panel"><h2>Hard boundaries</h2><ul><li>NFL.com terms restrict systematic retrieval/commercial use and prohibit using Services to wager on NFL games; no separate license is evidenced.</li><li>Club depth charts can be unofficial; printed order is not a confirmed starting lineup.</li><li>No authorized market offers, fitted scoring panel or aligned settled prop thresholds are present; actual lines, correlations, ROI and CLV remain blank.</li><li>Luck cannot be removed. No strategy is qualified and no cash reward is funded.</li></ul><p>' + source_links(['A958-NFL-TERMS', 'A958-NE-DEPTH', 'A958-REPO'], reg) + '</p></section>'
    pages['index.html'] = layout('index.html', 'NFL assurance overview', index_body, 'Evidence, gates and decisions without fabricated certainty')

    exec_body = '<section class="panel"><h2>Bottom line</h2><p>The repository now has a bounded, source-linked NFL assurance handoff: 276 official Week 10 injury rows, 289 club-published positional slots across ten clubs, a full frozen-baseline line/hash inventory, executable research gates and a reviewable decision queue. It is enough to audit evidence and block unsupported claims; it is not enough to originate verified NFL betting lines, estimate leg correlations, qualify a strategy or award a prize.</p><p>' + source_links(['A958-NFL-INJURIES', 'A958-NE-DEPTH', 'A958-REPO'], reg) + '</p></section>'
    exec_rows = []
    exec_items = [
        ('Evidence', '276 injury rows / 26 teams; 289 depth slots / 10 clubs; 565 row comparison receipts.', ['A958-NFL-INJURIES', 'A958-NE-DEPTH']),
        ('Availability', '5 Out and 1 Questionable game status; 270 blank game-status cells. Blank is not healthy/available.', ['A958-NFL-INJURIES', 'A958-NFL-REPORT-POLICY']),
        ('Depth', '2 first-string Out slots; 3 slots with a later-listed Out; shared cells and interior blanks preserved. Actual replacement and performance deficit are null.', ['A958-NE-DEPTH', 'A958-WAS-DEPTH']),
        ('Rights', 'NFL terms §1.3/§12 block unauthorized collection/wagering use; informational audit only.', ['A958-NFL-TERMS']),
        ('Markets', 'No authorized offers or settled prop panel; lines/correlations/ROI/CLV blank.', ['A958-REPO']),
        ('Validation', '12 gates implemented; all real candidates unqualified; leaderboard empty; merit-only design.', ['A958-SM-HOLM', 'A958-SK-CAL', 'A958-REPO']),
        ('Next decisions', 'Review P01/P02/P04 first, then P03/P05/P06, then seal P07/P08. Proposals are not approved implementations.', ['A958-REPO']),
    ]
    for topic, finding, ids in exec_items:
        exec_rows.append(row([cell(topic), cell(finding)], ids, reg))
    exec_body += table('exec-findings', 'Executive findings', ['Topic', 'Finding'], exec_rows)
    pages['executive-summary.html'] = layout('executive-summary.html', 'Executive summary', exec_body, 'Important details, limits and the next reviewable decisions')

    req_rows = []
    for r in decisions['requirements']:
        req_rows.append(row([cell(r['id']), cell(r['requirement']), cell(r['status']), cell(r['artifact']), cell(r['gap'])], r['source_ids'], reg, f' data-status="{esc(r["status"])}"'))
    pages['requirements.html'] = layout('requirements.html', 'Requirements ledger', table('requirements-table', 'Full request mapped to artifacts and honest gaps', ['ID', 'Requirement', 'Status', 'Artifact', 'Gap / boundary'], req_rows, filters=[('status', 'Status', sorted({r['status'] for r in decisions['requirements']}))]), 'Complete means the artifact exists and is checked; blocked/partial items keep unknown values blank.')

    inj_rows = []
    for r in data['injuries']:
        inj_rows.append(row([cell(r['team']), cell(r['player']), cell(r['position']), cell(r['injury'], empty=r['injury'] is None), cell(r['practice_status']), cell(r['game_status'], empty=r['game_status'] is None), cell(r['availability']), cell('Source blank; not a clean bill of health or final active list.')], r['source_ids'], reg, f' data-team="{esc(r["team"])}" data-status="{esc(r["game_status"] or "Blank")}"'))
    pages['injuries.html'] = layout('injuries.html', 'Injury report', kpis([(s['injury_rows'], 'rows'), (s['teams_with_injury_rows'], 'teams with rows'), (s['game_status_counts'].get('Out', 0), 'Out'), (s['game_status_counts'].get('Questionable', 0), 'Questionable'), (s['game_status_counts'].get('Blank', 0), 'blank game status')]) + table('injuries-table', 'Official NFL Week 10 injury transcription', ['Team', 'Player', 'Pos', 'Injury', 'Practice', 'Game status', 'Availability', 'Boundary'], inj_rows, note='Practice participation and game status are separate. LAC/BAL display No Injuries Reported for this early-week view; that is not a verified zero-injury roster.', filters=[('team', 'Team', sorted({r['team'] for r in data['injuries']})), ('status', 'Game status', ['Blank', 'Out', 'Questionable'])]), 'Rendered-source comparison, not a raw archive or medical diagnosis.')

    depth_rows = []
    for r in data['depth']:
        cells = [cell(r['team']), cell(r['unit']), cell(r['position']), cell(r['slot'])]
        for entry in r['entries']:
            if entry is None:
                cells.append(blank())
            elif entry['shared_listing']:
                cells.append(cell(' / '.join(entry['players']) + ' (shared cell)', cls='shared'))
            else:
                cells.append(cell(entry['players'][0]))
        cells += [cell(r['decision_state']), cell(r['actual_replacement'], empty=True), cell(r['performance_deficit'], empty=True)]
        depth_rows.append(row(cells, r['source_ids'], reg, f' data-team="{esc(r["team"])}" data-unit="{esc(r["unit"])}"'))
    pages['depth.html'] = layout('depth.html', 'Printed depth chains', kpis([(s['depth_slots'], 'slots'), (s['offense_slots'], 'offense'), (s['defense_slots'], 'defense'), (s['special_teams_slots'], 'special teams')]) + table('depth-table', 'Club-published printed order, not confirmed starters', ['Team', 'Unit', 'Pos', 'Slot', 'First', 'Second', 'Third', 'Fourth', 'Fifth', 'Decision state', 'Actual replacement', 'Performance deficit'], depth_rows, note='A shared printed cell has no individual rank. Interior blank columns are preserved. Actual replacement and performance deficit are never inferred from injury status.', filters=[('team', 'Team', sorted({r['team'] for r in data['depth']})), ('unit', 'Unit', ['Offense', 'Defense', 'Special Teams'])]), 'Official club publication can still be explicitly unofficial; evidence class is retained.')

    exposure = [r for r in data['depth'] if r['first_string_out'] or r['later_listed_out'] or r['blank_backup_columns'] or any(e and e['shared_listing'] for e in r['entries'])]
    exp_rows = []
    for r in exposure:
        exp_rows.append(row([cell(r['team']), cell(r['unit']), cell(r['position']), cell(' / '.join(p for p in r['players'] if p)), cell('Yes' if r['first_string_out'] else 'No'), cell(', '.join(r['later_listed_out']) or None, empty=not r['later_listed_out']), cell('Yes' if r['blank_backup_columns'] else 'No'), cell(r['decision_state']), cell(r['actual_replacement'], empty=True), cell(r['performance_deficit'], empty=True)], r['source_ids'], reg))
    news_rows = []
    news = [
        ('SEA', 'Sam Darnold Out; Drew Lock expected to start; Jalen Milroe QB2', 'Coach expectation, not final inactives', ['A958-NFL-SEA-QB', 'A958-SEA-DEPTH']),
        ('MIA', 'Malik Willis to IR (groin); Kyle McCord expected to fill in', 'Minimum four-week absence; return timestamp not guessed', ['A958-NFL-MIA-QB', 'A958-MIA-DEPTH']),
        ('CLE', 'Deshaun Watson set to start Week 10 vs HOU', 'Club announcement; cleared protocol Nov 7', ['A958-CLE-QB', 'A958-CLE-DEPTH']),
        ('AZ', 'Carson Beck first Arizona start vs LAR', 'League roundup; not a depth-chain reconstruction', ['A958-NFL-ROUNDUP', 'A958-AZ-DEPTH']),
    ]
    for team, item, boundary, ids in news:
        news_rows.append(row([cell(team), cell(item), cell(boundary)], ids, reg))
    avail_body = kpis([(s['first_string_out_slots'], 'first-string Out slots'), (s['slots_with_later_out'], 'slots with later Out'), (len(exposure), 'exposure/gap/shared rows'), (s['unmatched_depth_names'], 'unmatched unique depth names')])
    avail_body += table('exposure-table', 'Printed-depth exposure requiring separate lineup/participation evidence', ['Team', 'Unit', 'Pos', 'Printed names', 'First Out', 'Later Out', 'Blank backup col', 'Decision state', 'Actual replacement', 'Performance deficit'], exp_rows)
    avail_body += '<h2>Expected-start news</h2>' + table('news-table', 'Announcements are not final participation', ['Team', 'Reported expectation', 'Boundary'], news_rows)
    pages['availability.html'] = layout('availability.html', 'Availability & replacement exposure', avail_body, 'Injury report + printed depth join; no replacement or deficiency is inferred')

    line_rows = []
    for market, contract, inputs, boundary in [
        ('Moneyline', 'Home/away win; tie push', 'p_home, p_away, p_tie summing to one', 'Tie-push operator rule must confirm; no actual probabilities supplied'),
        ('Spread', 'Home margin vs signed half-point spread', 'margin_mean, margin_sd, half-point spread', 'Normal margin assumption; integer lines abstain because discrete pushes need a score model'),
        ('Total', 'Combined points vs half-point total', 'total_mean, total_sd, half-point total', 'Normal total approximation; overtime/discrete scores matter'),
    ]:
        line_rows.append(row([cell(market), cell(contract), cell(inputs), cell(boundary), blank(), blank()], ['A958-NFL-RULES', 'A958-REPO'], reg))
    lines_body = '<section class="panel"><h2>Actual NFL lines are blocked</h2><p>The engine can transform explicit probability inputs into fair research prices, but this snapshot contains no fitted scoring panel, authorized market offers or rights grant. No actual NFL line is published. Synthetic unit tests are not NFL observations.</p><p>' + source_links(['A958-NFL-TERMS', 'A958-NFL-RULES', 'A958-REPO'], reg) + '</p></section>'
    lines_body += table('lines-table', 'Pricing primitives and missing inputs', ['Market', 'Contract', 'Required explicit inputs', 'Boundary', 'Fair decimal', 'Fair American'], line_rows)
    pages['lines.html'] = layout('lines.html', 'Line origination', lines_body, 'Mathematical primitives are implemented; actual verified lines remain blank')

    strat_rows = []
    for r in strategies['strategies']:
        strat_rows.append(row([cell(r['id']), cell(r['name']), cell(r['market']), cell(r['contract']), cell(r['signal']), cell(r['required']), cell(r['failure']), cell(r['correlation_method']), blank(), blank(), blank(), blank(), blank()], r['source_ids'], reg, f' data-market="{esc(r["market"])}"'))
    pages['strategies.html'] = layout('strategies.html', 'Signal strategies', table('strategies-table', 'Eight research hypotheses; none is a demonstrated profitable strategy', ['ID', 'Name', 'Market', 'Contract', 'Signal', 'Required evidence', 'Failure mode', 'Correlation method', 'Model p', 'Fair line', 'Correlation', 'ROI', 'CLV'], strat_rows, filters=[('market', 'Market', sorted({r['market'] for r in strategies['strategies']}))]), 'Every candidate must pass all validation gates before qualification; unknown metrics stay blank.')

    corr_rows = []
    for r in strategies['correlations']:
        corr_rows.append(row([cell(r['id']), cell(r['pair']), cell(r['scope']), blank(), blank(), blank(), blank(), blank(), cell(r['status']), cell(r['discovery'])], r['source_ids'], reg))
    corr_body = '<section class="panel"><h2>No verified NFL leg correlation is published</h2><p>Pearson/Spearman, binary hit-event phi, empirical joint rates, Fréchet bounds and paired/date-block bootstrap primitives are implemented and tested on synthetic inputs. Actual NFL values require aligned settled legs, exact thresholds and operator settlement rules. Pairwise correlations do not identify three-plus-leg joint probabilities.</p><p>' + source_links(['A958-PY-STATS', 'A958-REPO'], reg) + '</p></section>'
    corr_body += table('correlation-table', 'Correlation families and missing-information discovery', ['ID', 'Pair', 'Scope', 'n', 'Pearson', 'Phi', 'Joint rate', 'Interval', 'Status', 'Discovery'], corr_rows)
    pages['correlation.html'] = layout('correlation.html', 'Correlation', corr_body, 'Dependence is estimated from aligned outcomes, never assumed away')

    gate_eval = engine.evaluate_gates({})
    gate_rows = []
    method_ids = {'G01': ['A958-NFL-TERMS', 'A958-REPO'], 'G02': ['A958-REPO'], 'G03': ['A958-SK-TIME', 'A958-REPO'], 'G04': ['A958-SM-HOLM', 'A958-REPO'], 'G05': ['A958-SK-CAL', 'A958-REPO'], 'G06': ['A958-PY-STATS', 'A958-NFL-RULES', 'A958-REPO'], 'G07': ['A958-REPO'], 'G08': ['A958-SM-HOLM', 'A958-REPO'], 'G09': ['A958-REPO'], 'G10': ['A958-REPO'], 'G11': ['A958-REPO'], 'G12': ['A958-REPO']}
    for g in gate_eval['gates']:
        gate_rows.append(row([cell(g['id']), cell(g['name']), cell(g['rule']), cell(g['reported_status']), cell(g['status']), cell(g['reason'])], method_ids[g['id']], reg))
    pages['validation.html'] = layout('validation.html', 'Validation gates', kpis([(gate_eval['passed'], 'gates passed'), (gate_eval['total'], 'gates required'), ('No', 'qualified strategy')]) + table('gates-table', 'Fail-closed gate evaluation with no verified artifacts supplied', ['ID', 'Gate', 'Rule', 'Reported', 'Result', 'Reason'], gate_rows), 'A Pass requires a verified artifact hash and source IDs; missing evidence fails closed.')

    comp = strategies['competition']
    lb_body = '<section class="panel"><h2>No eligible strategies</h2><p>The real leaderboard is empty. No strategy has verified all-gate evidence, market economics or a prospective record. No cash prize is funded or promised; the design awards non-transferable merit points only after qualification.</p><p>' + source_links(['A958-REPO'], reg) + '</p></section>'
    lb_body += '<div class="table-wrap"><table id="leaderboard-table"><caption>Qualified entries</caption><thead><tr><th scope="col">Rank</th><th scope="col">Strategy</th><th scope="col">Market</th><th scope="col">Lower 95% ROI</th><th scope="col">Log loss</th><th scope="col">Merit</th><th scope="col">Official source</th></tr></thead><tbody></tbody></table></div>'
    rule_rows = [row([cell('Divisions'), cell(', '.join(comp['divisions']))], comp['source_ids'], reg), row([cell('Ranking'), cell(comp['ranking'])], comp['source_ids'], reg), row([cell('Tie-breaks'), cell('; '.join(comp['ties']))], comp['source_ids'], reg), row([cell('Rewards'), cell(comp['reward_type'] + '; 3/2/1 for top three')], comp['source_ids'], reg), row([cell('Cash pool'), blank()], comp['source_ids'], reg), row([cell('Policy'), cell(comp['policy'])], comp['source_ids'], reg)]
    lb_body += table('leaderboard-rules', 'Competition design', ['Rule', 'Value'], rule_rows)
    pages['leaderboard.html'] = layout('leaderboard.html', 'Leaderboard', lb_body, 'Evidence-ranked competition design; empty until strategies qualify')

    sug_rows = []
    for r in decisions['suggestions']:
        sug_rows.append(row([f'<td><label class="sr-only" for="short-{esc(r["id"])}">Shortlist {esc(r["id"])}</label><input id="short-{esc(r["id"])}" type="checkbox" data-shortlist="{esc(r["id"])}"></td>', cell(r['id']), cell(r['priority']), cell(r['title']), cell(r['proposal']), cell(r['known']), cell(r['unknown']), cell(r['benefit']), cell(r['tradeoff']), cell(r['acceptance']), cell(r['decision']), cell(r['effort']), cell(r['risk'])], r['source_ids'], reg, f' data-priority="{esc(r["priority"])}"'))
    sug_body = '<section class="panel"><h2>Review before implementation</h2><p>All proposals start Proposed. A browser-local shortlist is a preference, not shared approval. Export a shortlist and record a versioned approve/defer/reject decision with rationale before implementing anything.</p><button type="button" id="export-shortlist">Export shortlist JSON</button> <span id="shortlist-status" role="status"></span><p>' + source_links(['A958-REPO'], reg) + '</p></section>'
    sug_body += table('suggestions-table', 'Reviewable proposals', ['Shortlist', 'ID', 'Priority', 'Title', 'Proposal', 'Known', 'Unknown', 'Benefit', 'Tradeoff', 'Acceptance', 'Decision', 'Effort', 'Risk'], sug_rows, filters=[('priority', 'Priority', ['Critical', 'High', 'Medium'])])
    pages['suggestions.html'] = layout('suggestions.html', 'Suggestions', sug_body, 'Known/missing information, benefit, tradeoff and acceptance tests')

    q_rows = []
    for r in decisions['questions']:
        q_rows.append(row([cell(r['id']), cell(r['question']), cell(r['known']), cell(r['answer'], empty=r['answer'] is None), cell(r['missing']), cell(r['discovery']), cell(r['decision_gate']), cell(r['status'])], r['source_ids'], reg, f' data-status="{esc(r["status"])}"'))
    pages['questions.html'] = layout('questions.html', 'Questions & answers', table('questions-table', 'Questions, known information, answers and missing-information discovery', ['ID', 'Question', 'Known', 'Answer', 'Missing', 'Discovery', 'Decision gate', 'Status'], q_rows, filters=[('status', 'Status', sorted({r['status'] for r in decisions['questions']}))]), 'Unanswerable items stay blank/flagged rather than guessed.')

    src_rows = []
    for r in reg.values():
        src_rows.append(row([cell(r['id']), cell(r['publisher']), f'<td><a href="{esc(r["url"])}" rel="noopener noreferrer">{esc(r["title"])}</a></td>', cell(r['kind']), cell(r['authority']), cell(r['scope']), cell(r['checked_on']), cell(r['access']), cell(r['status'])], [r['id']], reg))
    pages['sources.html'] = layout('sources.html', 'Source register', table('sources-table', 'Official sources actually checked, with scope and access boundary', ['ID', 'Publisher', 'Title', 'Kind', 'Authority', 'Scope', 'Checked', 'Access', 'Status'], src_rows), 'A link is a reference, not blanket verification. Rendered-content checks are not raw HTTP archives.')

    flag_rows = []
    for r in findings:
        flag_rows.append(row([cell(r['id']), cell(r['title']), cell(r['finding']), cell(r['action']), cell(r['status']), cell(r['unverified_value'], empty=True)], r['source_ids'], reg, f' data-status="{esc(r["status"])}"'))
    pages['flagged.html'] = layout('flagged.html', 'Flagged for review', table('flagged-table', 'Irregularities and unverified values published for manual review', ['ID', 'Title', 'Finding', 'Action', 'Status', 'Unverified value'], flag_rows, filters=[('status', 'Status', sorted({r['status'] for r in findings}))]), 'Flags block unsupported prices/skill/rewards, not transparent limitation disclosure.')

    method_rows = []
    methods = [
        ('Proper scores', 'Brier and log loss evaluate probability quality; calibration bins inspect reliability. Accuracy alone is insufficient.', ['A958-SK-CAL']),
        ('Chronology', 'Features must be known before seal; training labels need explicit availability timestamps and embargo before test kickoff.', ['A958-SK-TIME']),
        ('Multiplicity', 'Holm correction over the registered attempt family; unlogged experiments cannot be recovered.', ['A958-SM-HOLM']),
        ('Dependence', 'Hit-event phi, empirical joint rates and Fréchet bounds; date-block bootstrap preserves whole-date dependence.', ['A958-PY-STATS', 'A958-SM-HOLM']),
        ('Pricing', 'Explicit probabilities transform to fair decimal/American research prices; integer lines abstain without a discrete push model.', ['A958-NFL-RULES', 'A958-REPO']),
        ('Luck', 'Random outcomes remain random. Reduce avoidable bias and quantify uncertainty; never claim luck-free or guaranteed skill.', ['A958-SK-TIME', 'A958-SK-CAL', 'A958-SM-HOLM']),
    ]
    for name, desc, ids in methods:
        method_rows.append(row([cell(name), cell(desc)], ids, reg))
    pages['methodology.html'] = layout('methodology.html', 'Methodology', '<section class="panel"><h2>Skill selection, honestly</h2><p>The goal is to reduce avoidable evaluation error and select strategies that survive untouched forward evidence, not to eliminate luck. Minimum sample floors are project policy, not official skill standards; a dependence-aware power analysis can require more.</p><p>' + source_links(['A958-SK-TIME', 'A958-SK-CAL', 'A958-SM-HOLM', 'A958-REPO'], reg) + '</p></section>' + table('method-table', 'Methods and limits', ['Method', 'Description'], method_rows), 'Executable primitives are tested on synthetic inputs; real NFL metrics remain blank.')

    audit_rows = []
    for f in audit['files_review']:
        audit_rows.append(row([f'<td><a href="{esc(f["source_url"])}" rel="noopener noreferrer">{esc(f["path"])}</a></td>', cell(f.get('line_scope')), cell(f.get('lines')), cell(f['bytes']), cell(f['syntax']), cell(f['status']), f'<td><a href="{esc(reg["A958-REPO"]["url"])}" rel="noopener noreferrer">Baseline repo</a></td>'], ['A958-REPO'], reg))
    repo_body = kpis([(audit['files'], 'files'), (audit['text_lines'], 'text lines'), (audit['bytes'], 'bytes'), (len(audit['errors']), 'syntax errors')])
    repo_body += '<section class="panel"><h2>Coverage boundary</h2><p>Every byte and text line in frozen baseline <code>a989d67</code> was inventoried and hashed; JSON/Python/CSV syntax was checked. This is full mechanical line coverage, not independent factual verification of every old NBA/rental assertion. Existing claims are preserved and not promoted to NFL evidence. Irregularities are published on the flagged page.</p><p>' + source_links(['A958-REPO'], reg) + '</p></section>'
    repo_body += table('repo-table', 'Frozen baseline file/line inventory', ['Path', 'Lines', 'Line count', 'Bytes', 'Syntax', 'Status', 'Repository'], audit_rows, note='Path links are exact blob permalinks; the repository column links the registered baseline source.')
    pages['repo-review.html'] = layout('repo-review.html', 'Repository review', repo_body, 'Line-by-line mechanical coverage with official repository permalinks')

    data_rows = []
    artifacts = [
        ('data/injuries.csv', '276 injury rows with source_url', ['A958-NFL-INJURIES']),
        ('data/depth.csv', '289 printed depth slots with source_url', ['A958-NE-DEPTH']),
        ('data/availability.json', 'Joined evidence, unmatched names and summary', ['A958-NFL-INJURIES', 'A958-NE-DEPTH']),
        ('sources/registry.json', '26 namespaced official sources', ['A958-REPO']),
        ('sources/receipts.json', '565 row comparison receipts and recheck boundary', ['A958-REPO']),
        ('audit/baseline-lines.json', '150-file / 14,244-line frozen inventory', ['A958-REPO']),
        ('strategies.json', 'Eight hypotheses and correlation families', ['A958-REPO']),
        ('decisions.json', 'Suggestions, questions and requirements', ['A958-REPO']),
        ('data/findings.json', 'Published irregularities and flags', ['A958-REPO']),
    ]
    for path, desc, ids in artifacts:
        data_rows.append(row([f'<td><a href="../{esc(path)}">{esc(path)}</a></td>', cell(desc)], ids, reg))
    pages['data.html'] = layout('data.html', 'Data library', table('data-table', 'Downloadable artifacts', ['Artifact', 'Description'], data_rows), 'CSV/JSON are normalized transcriptions and project policy, not raw archives or licensed market feeds.')

    resp_body = '<section class="panel"><h2>No wagering service</h2><p>This site is informational research and assurance. It does not accept bets, publish executable NFL prices, or encourage wagering. NFL.com terms prohibit using its Services to gamble or wager on NFL games; no separate permission is evidenced. If gambling is causing harm, official support is available.</p><p>' + source_links(['A958-NFL-TERMS', 'A958-AB-HELP'], reg) + '</p></section>'
    resp_rows = [row([cell('Alberta 24-Hour Addiction Helpline'), cell('1-866-332-2322 (Alberta only)'), cell('Recovery Alberta / Government of Alberta')], ['A958-AB-HELP'], reg), row([cell('NFL terms boundary'), cell('§1.3 systematic retrieval/commercial use; §12 wagering prohibition'), cell('No license inferred')], ['A958-NFL-TERMS'], reg)]
    resp_body += table('responsible-table', 'Official support and rights boundary', ['Item', 'Value', 'Boundary'], resp_rows)
    pages['responsible-use.html'] = layout('responsible-use.html', 'Responsible use', resp_body, 'Research boundaries and official player-protection information')

    return pages


CSS = '''
:root{color-scheme:light;--bg:#f7f8fb;--panel:#fff;--ink:#172033;--muted:#51607a;--line:#d8deea;--accent:#164e8a;--accent-ink:#fff;--warn:#8a4b00;--ok:#14532d;--bad:#7f1d1d}*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink);line-height:1.5}.skip{position:absolute;left:-9999px;top:0;background:var(--accent);color:#fff;padding:.5rem;z-index:10}.skip:focus{left:0}.top{background:#101a2e;color:#fff;padding:1rem}.brand{display:flex;gap:.75rem;align-items:baseline;flex-wrap:wrap}.brand strong{font-size:1.25rem}.brand span{color:#c7d2e6}nav{display:flex;flex-wrap:wrap;gap:.35rem;margin-top:.75rem}nav a{color:#e6edf7;text-decoration:none;padding:.25rem .5rem;border-radius:.375rem;font-size:.9rem}nav a:hover,nav a:focus{background:#243452}nav a[aria-current=page]{background:var(--accent);color:var(--accent-ink);font-weight:600}main{max-width:1200px;margin:0 auto;padding:1.25rem}.eyebrow{color:var(--muted);font-size:.85rem;text-transform:uppercase;letter-spacing:.04em}h1{margin:.25rem 0 .5rem;font-size:1.9rem}h2{font-size:1.25rem;margin:1rem 0 .5rem}.subtitle,.lead{color:var(--muted);max-width:75ch}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.75rem;margin:1rem 0}.kpi{background:var(--panel);border:1px solid var(--line);border-radius:.75rem;padding:.9rem}.kpi-value{display:block;font-size:1.6rem;font-weight:700;color:var(--accent)}.kpi-label{color:var(--muted);font-size:.85rem}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:.75rem;margin:1rem 0}.card{display:block;background:var(--panel);border:1px solid var(--line);border-radius:.75rem;padding:1rem;text-decoration:none;color:inherit}.card:hover,.card:focus{border-color:var(--accent)}.card h2{margin:0 0 .35rem;font-size:1.05rem;color:var(--accent)}.card p{margin:0;color:var(--muted);font-size:.9rem}.panel{background:var(--panel);border:1px solid var(--line);border-radius:.75rem;padding:1rem;margin:1rem 0}.controls{display:flex;flex-wrap:wrap;gap:.75rem;align-items:end;margin:.75rem 0}.controls label{display:flex;flex-direction:column;font-size:.85rem;color:var(--muted)}input[type=search],select,button{font:inherit;padding:.4rem .55rem;border:1px solid var(--line);border-radius:.375rem;background:#fff;color:var(--ink)}button{cursor:pointer;background:var(--accent);color:#fff;border-color:var(--accent)}button:focus,input:focus,select:focus,a:focus{outline:3px solid #f0b429;outline-offset:2px}.count{color:var(--muted);font-size:.85rem}.table-wrap{overflow-x:auto;max-width:100%;border:1px solid var(--line);border-radius:.5rem;background:var(--panel)}table{border-collapse:collapse;width:100%;min-width:640px;font-size:.88rem}caption{text-align:left;padding:.6rem;font-weight:600;color:var(--muted)}th,td{border-top:1px solid var(--line);padding:.45rem .55rem;text-align:left;vertical-align:top}thead th{background:#eef2f8;position:sticky;top:0}tbody tr:nth-child(even){background:#fafbfe}td.src{white-space:nowrap}td.src a{margin-right:.35rem}.shared{color:var(--warn)}td[data-empty]{background:#fff7e6}.note,.empty-state{color:var(--muted);font-size:.9rem}a{color:var(--accent);overflow-wrap:anywhere}footer{max-width:1200px;margin:0 auto;padding:1rem 1.25rem 2rem;color:var(--muted);font-size:.85rem}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}code{background:#eef2f8;padding:.1rem .3rem;border-radius:.25rem}@media(max-width:640px){h1{font-size:1.5rem}main{padding:1rem}.controls{flex-direction:column;align-items:stretch}}
'''

JS = '''
(function(){
  function rows(table){return Array.from(table.tBodies[0]?table.tBodies[0].rows:[]);}
  function apply(table){
    var search=document.querySelector('[data-search="'+table.id+'"]');
    var filters=Array.from(document.querySelectorAll('[data-filter="'+table.id+'"]'));
    var q=search?search.value.trim().toLowerCase():'';
    var visible=0;
    rows(table).forEach(function(tr){
      var ok=!q||tr.textContent.toLowerCase().indexOf(q)>=0;
      filters.forEach(function(sel){var key=sel.getAttribute('data-filter-key');var val=sel.value;if(val&&tr.getAttribute('data-'+key)!==val)ok=false;});
      tr.hidden=!ok;if(ok)visible++;
    });
    var count=document.querySelector('[data-count="'+table.id+'"]');if(count)count.textContent=visible+' / '+rows(table).length+' rows';
    var empty=document.querySelector('[data-empty-for="'+table.id+'"]');if(empty)empty.hidden=visible!==0;
  }
  document.querySelectorAll('table[id]').forEach(function(table){
    var search=document.querySelector('[data-search="'+table.id+'"]');if(search)search.addEventListener('input',function(){apply(table);});
    document.querySelectorAll('[data-filter="'+table.id+'"]').forEach(function(sel){sel.addEventListener('change',function(){apply(table);});});
    var exportBtn=document.querySelector('[data-export="'+table.id+'"]');
    if(exportBtn)exportBtn.addEventListener('click',function(){
      var headers=Array.from(table.tHead.rows[0].cells).map(function(th){return th.textContent.trim();});
      var lines=[headers.map(csv).join(',')];
      rows(table).filter(function(tr){return !tr.hidden;}).forEach(function(tr){lines.push(Array.from(tr.cells).map(function(td){return csv(td.textContent.trim());}).join(','));});
      download(table.id+'-visible.csv',lines.join('\\r\\n'),'text/csv');
    });
    apply(table);
  });
  function csv(value){return '"'+value.replace(/"/g,'""')+'"';}
  function download(name,text,type){var blob=new Blob([text],{type:type});var url=URL.createObjectURL(blob);var a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);}
  var key='nfl-assurance-shortlist-v1';
  function loadShortlist(){try{return JSON.parse(localStorage.getItem(key)||'[]');}catch(e){return [];}}
  function saveShortlist(list){try{localStorage.setItem(key,JSON.stringify(list));}catch(e){}}
  var boxes=Array.from(document.querySelectorAll('[data-shortlist]'));
  if(boxes.length){
    var list=loadShortlist();boxes.forEach(function(box){box.checked=list.indexOf(box.getAttribute('data-shortlist'))>=0;box.addEventListener('change',function(){var current=loadShortlist();var id=box.getAttribute('data-shortlist');if(box.checked&&current.indexOf(id)<0)current.push(id);if(!box.checked)current=current.filter(function(x){return x!==id;});saveShortlist(current);status();});});
    function status(){var el=document.getElementById('shortlist-status');if(el)el.textContent=loadShortlist().length+' shortlisted locally (not approval)';}
    var btn=document.getElementById('export-shortlist');if(btn)btn.addEventListener('click',function(){download('nfl-assurance-shortlist.json',JSON.stringify({shortlist:loadShortlist(),note:'Local preference only; not shared approval or implementation authorization.'},null,2),'application/json');});
    status();
  }
})();
'''


def write_all(check=False):
    pages = build_pages()
    SITE.mkdir(parents=True, exist_ok=True)
    outputs = {f'site/{name}': content for name, content in pages.items()}
    outputs['site/style.css'] = CSS
    outputs['site/app.js'] = JS
    outputs['site/manifest.json'] = json.dumps({'pages': [name for name, _ in PAGES], 'generated': True, 'boundary': 'Static assurance supplement; no network or inferred values.'}, indent=2) + '\n'
    changed = []
    for rel, content in outputs.items():
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        data = content.encode('utf-8')
        if not path.exists() or path.read_bytes() != data:
            changed.append(rel)
            if not check:
                path.write_bytes(data)
    if check and changed:
        raise SystemExit('Stale generated files: ' + ', '.join(changed))
    return {'pages': len(pages), 'changed': changed, 'sha256': {rel: hashlib.sha256(content.encode()).hexdigest() for rel, content in outputs.items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = write_all(check=args.check)
    print(json.dumps({k: v for k, v in result.items() if k != 'sha256'}, indent=2))
