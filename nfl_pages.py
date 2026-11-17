"""NFL research pages. Imported by scripts/build_site.py.

Every row built here carries registered source IDs and an official URL. Derived numbers
come from research/nfl/results.json and are labelled as derived; missing values stay blank.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NFL = json.loads((ROOT / "research/nfl/results.json").read_text(encoding="utf-8"))
DECISIONS = json.loads((ROOT / "research/nfl/decisions.json").read_text(encoding="utf-8"))
QUESTIONS = json.loads((ROOT / "research/nfl/questions.json").read_text(encoding="utf-8"))
FLAGS = json.loads((ROOT / "research/nfl/flags.json").read_text(encoding="utf-8"))
RECEIPTS = json.loads((ROOT / "research/nfl/receipts.json").read_text(encoding="utf-8"))
RECHECK = json.loads((ROOT / "research/nfl/verification-2026-11-13.json").read_text(encoding="utf-8"))
SUB_SUGGESTIONS = json.loads((ROOT / "research/nfl-suggestions.json").read_text(encoding="utf-8"))["suggestions"]
REQUIREMENTS = json.loads((ROOT / "research/nfl-requirements.json").read_text(encoding="utf-8"))
SOURCES = {s["id"]: s for s in json.loads((ROOT / "research/sources.json").read_text(encoding="utf-8"))}
# A-RR17: the origination section's own page count, kept next to the pages it counts.
ORIGINATION_PAGES = 13
# A-RR18: the badge on the landing page counts open items, not total items.
NFL_OPEN_FLAGS = sum(1 for f in FLAGS["flags"] if f["status"] == "Needs review")


def esc(value):
    return html.escape(str(value), quote=True)


class _FallbackMarkup(str):
    """Stands in for build_site.Markup so cells are not escaped as text."""


_Markup = _FallbackMarkup


def refs(row):
    """Official-link cell built from the row's own registered source IDs."""
    pieces, direct = [], row.get("source_url")
    if direct:
        pieces.append(f'<a href="{esc(direct)}" target="_blank" rel="noopener noreferrer">Source row ↗</a>')
    for sid in row.get("source_ids", ["REPO"]):
        source = SOURCES[sid]
        if source["url"] == direct:
            continue
        pieces.append(f'<a href="{esc(source["url"])}" title="{esc(source["title"])}" '
                      f'target="_blank" rel="noopener noreferrer">{esc(sid)} ↗</a>')
    return "".join(pieces)


def num(value, places=1, signed=False):
    if value is None:
        return None
    pattern = f"{{:+.{places}f}}" if signed else f"{{:.{places}f}}"
    return pattern.format(value)


def pct(value, places=1):
    return None if value is None else f"{value * 100:.{places}f}%"


def price(value):
    if value is None:
        return None
    return f"+{value}" if value > 0 else str(value)


def lines(items):
    return "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in items) + "</ul>"


def pn(value):
    """Positive / negative formatting for residuals, kept explicit rather than coloured."""
    return None if value is None else f"{value:+.2f}"


# ---------------------------------------------------------------------------
# Page bodies. Each returns HTML that is wrapped by build_site.page().
# ---------------------------------------------------------------------------

def suggestions():
    """The decision hub: what to change, what it costs, what closes it, and how to choose."""
    ranked = sorted(DECISIONS["suggestions"], key=lambda r: -r["priority_index"])
    rows = [{"id": s["id"], "pr": s["priority_index"], "title": s["title"],
             "category": s["category"], "problem": s["problem"], "unlocks": s["unlocks"],
             "dv": s["decision_value_score"], "effort": s["effort_score"], "cost": s["cost_score"],
             "gain": s["confidence_gain"], "rev": s["reversibility"],
             "pre": s["prerequisite"],
             "state": s["review_state"], "evidence": s["evidence_status"],
             "cw": ", ".join(s["crosswalk"]) or "No equivalent in the sub-site register",
             "source_ids": ["REPO", "NFL-TERMS-LEGAL"] if s["category"] == "Rights" else ["REPO"]}
            for s in ranked]
    blocking = [q for q in DECISIONS["missing_information"]
                if q["id"] in DECISIONS["blocking_before_any_reward"]]
    body = notice(
        "Ten proposals, ranked by what they unlock rather than by how easy they are.",
        "Each row states the question it closes, the score it earns, what it depends on, and the "
        "test it must pass before anyone may call it done. Nothing here is implemented, and the "
        "page has no approve button: a decision is recorded by editing the register and rebuilding, "
        "which leaves an auditable commit.")
    body += metrics([
        ('Proposals on the table', len(DECISIONS["suggestions"]), 'Nothing implemented', 'signals'),
        ('Questions to answer', len(QUESTIONS["questions"]), 'Sourced part versus open part', 'validation'),
        ('Blocking a reward', len(blocking), 'All four are data gaps', 'leaderboard'),
        ('Approved today', 0, 'No reviewer decision recorded', 'requirements'),
    ])

    body += section('How to choose: one page, four columns', '<div class="grid-2">'
        '<div class="panel body-text"><h3>Read a row in this order</h3>'
        '<ol><li><strong>What it closes</strong> — the named missing item. If a proposal closes no '
        'named gap, reject it.</li><li><strong>Priority index</strong> — decision value times '
        'confidence gain, divided by effort plus cost. It is a judgement, published so you can '
        'disagree with it.</li><li><strong>What it unlocks</strong> — the decision that becomes '
        'possible.</li><li><strong>Acceptance test</strong> — what must exist before it counts as '
        'done.</li></ol></div>'
        '<div class="panel body-text"><h3>Read the scores as opinions</h3>'
        + lines([f'{k}: {v}' for k, v in DECISIONS["scoring"].items() if k != "note"]) +
        f'<p class="footnote">{esc(DECISIONS["scoring"]["note"])}</p></div></div>',
        eyebrow='DECISION PROCEDURE')

    body += section('The register, ranked by decision value', table(
        'suggestion-register', 'Suggestions register',
        [('Suggestion', lambda r: rich(r['title'], r['id'])),
         ('Priority', 'pr'), ('Closes', 'problem'), ('Unlocks', 'unlocks'),
         ('Value', 'dv'), ('Effort', 'effort'), ('Cost', 'cost'),
         ('Confidence gain', 'gain'), ('Reversible', 'rev'), ('Depends on', 'pre'),
         ('Review state', lambda r: badge(r['state'], 'blue')),
         ('Evidence today', 'evidence')],
        rows,
        note='Scores are 1-5 and are not measurements. "Depends on" means the proposal cannot be '
             'completed first; it does not mean it cannot be started. A priority index is a sorting '
             'aid, not a recommendation to spend money.'))

    body += section('Acceptance test per proposal', table(
        'acceptance-register', 'Acceptance tests',
        [('Suggestion', lambda r: rich(r['title'], r['id'])), ('Evidence that must exist', 'test'),
         ('Crosswalk to the sub-site register', 'cw')],
        [{"id": s["id"], "title": s["title"], "test": s["acceptance_test"],
          "cw": ", ".join(s["crosswalk"]) or None, "source_ids": ["REPO"]}
         for s in DECISIONS["suggestions"]],
        note='A proposal that produces a number without producing this evidence is rejected by the '
             'rule below, regardless of how good the number looks.'))

    body += section('Two registers exist; here is how to read them', '<div class="panel body-text">'
        '<p>This page ranks ten proposals as <strong>S01-S10</strong>. The NFL research lab, a '
        'separately built section, publishes twelve proposals as <strong>SU-01-SU-12</strong>. They '
        'overlap: depth charts are <span class="mono">S02</span> here and '
        '<span class="mono">SU-03</span> plus <span class="mono">SU-07</span> there. Neither was '
        'deleted, because deleting another workstream\'s register would lose its reasoning.</p>'
        '<p><strong>The decision you are asked to make:</strong> adopt this register, adopt the '
        'sub-site register, or ask for a merged one. Until one is chosen, follow the crosswalk column '
        'above rather than assuming two identifiers mean two different pieces of work.</p></div>',
        eyebrow='CROSSWALK')

    body += section('Status of the twelve sub-site proposals', table(
        'subsite-register', 'Sub-site suggestions',
        [('Proposal', lambda r: rich(r['title'], r['id'])), ('What it closes', 'missing_info'),
         ('Decision needed', 'decision_needed'), ('State', lambda r: badge(r['status'], 'blue')),
         ('Main-register equivalent', lambda r: r['equiv'])],
        [{"id": s["id"], "title": s["title"], "missing_info": s["missing_info"],
          "decision_needed": s["decision_needed"], "status": s["status"],
          "equiv": next((m["id"] for m in DECISIONS["suggestions"] if s["id"] in m["crosswalk"]), None),
          "source_ids": s["source_ids"]}
         for s in SUB_SUGGESTIONS],
        note='Read-only mirror of research/nfl-suggestions.json, so both registers are visible in one '
             'place. A blank equivalence cell means the proposal has no counterpart in the main '
             'register yet — not that it is unimportant.'))
    body += section('Sub-site proposals with no equivalent here, and why', table(
        'subsite-only', 'Unmapped proposals',
        [('Proposal', lambda r: rich(r['title'], r['id'])), ('Reason it is not in the main register', 'why')],
        [{"id": r["id"], "title": r["title"], "why": r["why"], "source_ids": r["source_ids"]}
         for r in DECISIONS["subsite_only"]],
        note='Each of these is either folded into a larger proposal, already published by another '
             'section, or impossible to source officially today. None was quietly dropped.'))

    body += section('Review workflow and what an approval must contain', '<div class="grid-2">'
        '<div class="panel body-text"><h3>The states</h3>'
        + lines(DECISIONS["review_workflow"]["states"]) +
        f'<p>{esc(DECISIONS["review_workflow"]["rule"])}</p></div>'
        '<div class="panel body-text"><h3>Required at approval</h3>'
        + lines(DECISIONS["review_workflow"]["required_at_approval"]) +
        f'<p>{esc(DECISIONS["review_workflow"]["rejection_rule"])}</p></div></div>',
        eyebrow='REVIEW, NOT IMPLEMENTATION')

    body += section('Sequence: what to do first', '<div class="panel body-text">'
                    + lines(DECISIONS["sequence"]) + '</div>',
                    eyebrow='CHEAPEST BLOCKING ITEM FIRST')
    body += section('Acceptance tests for any proposal at all', '<div class="panel body-text">'
                    + lines(DECISIONS["acceptance_tests"]) + '</div>',
                    eyebrow='HOW TO JUDGE A CHANGE')
    body += section('What is blocking a reward decision', table(
        'reward-blockers', 'Blocking gaps',
        [('Question', lambda r: rich(r['question'], r['id'])), ('Why it matters', 'why_it_matters'),
         ('Blocks', 'blocks'), ('Resolved by', 'suggestion')],
        blocking,
        note='These four are the reason no strategy is ranked and no reward is awarded. None of them '
             'is a matter of opinion or of better modelling.'))
    body += '<div class="download-list">' + ''.join([
        '<a class="button" href="nfl-decisions.html">Decision brief →</a>',
        '<a class="button" href="nfl-questions.html">All questions →</a>',
        '<a class="button" href="nfl-verification-2026-11-13.html">Re-verification 13 Nov →</a>',
        '<a class="button" href="research/nfl/decisions.json">Register JSON</a>',
    ]) + '</div>'
    return body


def nfl_verification():
    """Same-week re-check of every published NFL value against the publisher."""
    st = RECHECK["standings_recheck"]
    h = RECHECK["headline"]
    body = notice(
        f"Re-checked {RECHECK['checked_on']}: {h['standings_agreement']} standings rows, "
        f"{h['injury_agreement']} injury rows, {h['fixtures_agreement']} fixtures agree with the snapshot.",
        "This page exists because an internal check can pass while a published value has gone stale. "
        "It re-reads the publisher and shows every row, including the two that moved.")
    body += metrics([
        ('Standings rows identical', h['standings_agreement'], 'of 32, field by field', 'data'),
        ('Injury rows identical', h['injury_agreement'], 'of 20, same game', 'validation'),
        ('Fixtures identical', h['fixtures_agreement'], 'of 14, plus 4 byes', 'lab'),
        ('Rows that moved', h['moved'], 'Both explained by one result', 'review'),
    ])
    body += section('How the publisher was reached', '<div class="panel body-text">'
        f'<p>{esc(h["access_note"])}</p>'
        '<p>Evidence class: rendered page text through a page reader. Not an HTTP archive, and not a '
        'second independent source. Every value on this site is single-source and says so.</p>'
        '<p>The verbatim captures are committed under '
        '<span class="mono">research/nfl/evidence-2026-11-13/</span>, so this comparison can be '
        're-run without trusting this page.</p></div>', eyebrow='EVIDENCE CLASS')
    body += section('Standings, all 32 rows, snapshot beside today', table(
        'recheck-standings', 'Standings re-check',
        [('Club', lambda r: rich(r['team'], r['id'])),
         ('Published snapshot 2026-11-12', 'snapshot'),
         ('Read again 2026-11-13', 'recheck'),
         ('Delta', lambda r: badge(r['delta'], 'warn' if r['delta'] != 'Identical' else 'good'))],
        st, filter_options=['Identical', 'Moved — fixture played'],
        note='Fields compared: W, L, T, PF, PA. PCT, NET PTS, home and road records and the streak '
             'were also re-derived arithmetically on today\'s capture and all agree. Division and '
             'conference columns remain withheld, because even today the rendered table has no '
             'header row and its field order contradicts its own legend.'))

    inj = RECHECK["injury_recheck"]
    body += section('Injury report, one game, twenty rows', '<div class="grid-2">'
        '<div class="panel body-text"><h3>What agrees</h3>'
        + lines([f'{inj["rows_read"]} rows read, {inj["identical"]} identical to the snapshot',
                 f'{inj["blank_game_status"]} game-status cells still blank',
                 f'{inj["out"]} Out, {inj["doubtful"]} Doubtful, {inj["questionable"]} Questionable',
                 inj["detail"]]) +
        '</div><div class="panel body-text"><h3>What the source still does not contain</h3>'
        + lines(inj["not_in_source"]) +
        '<p class="footnote">These are the fields the starter-versus-backup requirement needs. None '
        'was inferred, and every one stays blank.</p></div></div>',
        eyebrow='INJURIES AND AVAILABILITY')

    fix = RECHECK["fixture_recheck"]
    body += section('Fixtures, and one contradiction worth reading', '<div class="panel body-text">'
        f'<p>{esc(fix["result_text"])}</p><p>{esc(fix["handling"])}</p>'
        '<p>Byes as printed today: ' + esc(", ".join(fix["byes"])) + '.</p></div>',
        eyebrow='SCHEDULE')

    body += section('Irregularities found by this re-check', table(
        'recheck-irregularities', 'Re-check irregularities',
        [('Item', lambda r: rich(r['item'], r['id'])), ('Finding', 'detail'), ('Handling', 'handling'),
         ('State', lambda r: badge('Needs review', 'warn'))],
        RECHECK["irregularities"],
        note='All four are published rather than resolved. None of them changes a value on this site '
             'without a source saying so.'))

    body += section('What was not re-checked', '<div class="panel body-text">'
        + lines(RECHECK["not_rechecked"]) +
        '<p>These are marked <strong>not re-checked</strong>, not "unchanged". A value nobody read '
        'today cannot be called current.</p></div>', eyebrow='HONEST LIMITS')
    body += '<div class="download-list">' + ''.join([
        '<a class="button" href="nfl-review.html">Flagged for review →</a>',
        '<a class="button" href="nfl-standings.html">Standings snapshot →</a>',
        '<a class="button" href="research/nfl/verification-2026-11-13.json">Re-check JSON</a>',
    ]) + '</div>'
    return body


def decisions():
    known = [{"id": k["id"], "statement": k["statement"], "value": k["value"],
              "verification": k["verification"], "source_ids": k["source_ids"]} for k in DECISIONS["known_information"]]
    missing = [{"id": m["id"], "question": m["question"], "why": m["why_it_matters"],
                "blocks": m["blocks"], "suggestion": m["suggestion"], "status": m["status"],
                "source_ids": ["REPO"]} for m in DECISIONS["missing_information"]]
    body = notice("Three columns: what we know, what we do not know, and what closes the gap.",
                  "Nothing in the missing column is estimated on this site. Those cells are blank "
                  "everywhere they appear, including on the line origination page.")
    body += '<div class="grid-2"><div class="panel body-text"><h3>Reasonable today</h3>' \
            + lines(DECISIONS["decision_frame"]["what_can_be_decided_today"]) + \
            '</div><div class="panel body-text"><h3>Not reasonable today</h3>' \
            + lines(DECISIONS["decision_frame"]["what_cannot_be_decided_today"]) + '</div></div>'
    body += section('Information we have, with its check', table(
        'known-register', 'Known information',
        [('ID', 'id'), ('What we know', 'statement'), ('Value in this snapshot', 'value'),
         ('How it was checked', 'verification')],
        known, note='Every row was re-derived from saved official text by the extractor; a failed '
                    'arithmetic check aborts the build rather than publishing the number.'))
    body += section('Information we do not have', table(
        'missing-register', 'Missing information',
        [('ID', 'id'), ('Question that must be answered', 'question'), ('Why it matters', 'why'),
         ('Blocks', 'blocks'), ('Closing suggestion', 'suggestion'),
         ('State', lambda r: badge(r['status'], 'warn'))],
        missing, note='These are the questions a reader must have answered before trusting any '
                      'line, ranking or reward on this site.'))
    body += section('Default recommendation', '<div class="panel body-text"><p><strong>'
                    + esc(DECISIONS["decision_frame"]["default_recommendation"]) + '</strong></p></div>',
                    eyebrow='IF NOTHING ELSE CHANGES')
    return body


def nfl_questions():
    rows = [{"id": q["id"], "group": q["group"], "q": q["q"], "known": q["known"],
             "missing": q["missing"], "resolves": q["resolves_if"], "blocks": q["blocks"],
             "source_ids": q["source_ids"]} for q in QUESTIONS["questions"]]
    owner = sum(1 for q in QUESTIONS["questions"] if q["owner_needed"] == "Yes")
    body = notice(f'{len(QUESTIONS["questions"])} questions; none of them is answered by guessing.',
                  'Each row separates the sourced part of the answer from the part that is still '
                  f'open, and names what would settle it. {owner} of them needs a decision from you; '
                  'the rest are research tasks.')
    body += section('Questions that must be answered before a decision', table(
        'question-register', 'Decision questions',
        [('Question', lambda r: rich(r['q'], r['id'])), ('Group', 'group'),
         ('What we know, with a source', 'known'), ('What we still need', 'missing'),
         ('What would resolve it', 'resolves'), ('Blocks', 'blocks')],
        rows, filter_options=sorted({q["group"] for q in QUESTIONS["questions"]}),
        note='Filter by group. "What we know" is sourced; "what we still need" is deliberately '
             'left as a question rather than filled with an estimate.'))
    return body


def nfl_lines():
    games = [{"id": g["id"], "matchup": g["matchup"], "kickoff": g["kickoff"], "tv": g["tv"],
              "spread": num(g["originated_spread_home"], 1, signed=True),
              "total": num(g["originated_total"], 1),
              "p_home": pct(g["model_p_home"]), "fair_home": price(g["fair_home_price"]),
              "fair_away": price(g["fair_away_price"]),
              "market_spread": None, "market_total": None, "clv": None,
              "status": "Model only",
              "source_url": g["game_source_url"],
              "source_ids": g["source_ids"]} for g in NFL["games"]]
    body = notice('Originated numbers, not market prices, and not recommendations.',
                  'Each game below has one conditional score pair; the spread and total both come '
                  'from that pair, so they cannot contradict each other. No sportsbook price was '
                  'retrieved, so no comparison is claimed and every market cell is blank.')
    body += metrics([
        ('Originated games', len(NFL["games"]), 'Week 10 fixtures', 'lab'),
        ('Market prices retrieved', 0, 'No quote exists in the record', 'validation'),
        ('Qualified strategies', 0, 'Nothing cleared its gates', 'leaderboard'),
        ('Live recommendations', 0, 'Research output only', 'care'),
    ])
    body += section('How a number here is produced', '<div class="grid-2">'
                    '<div class="panel body-text"><h3>Team strength from scoring</h3>'
                    '<div class="formula">pyth_pct = PF^2.37 / (PF^2.37 + PA^2.37)</div>'
                    '<p>The exponent 2.37 is the published NFL convention, not a value fitted here. '
                    'It converts a club\'s points for and against into an expected win rate, which is '
                    'then compared with its actual record to produce a residual.</p>'
                    '<p class="footnote">Source: a tertiary summary of the method, used for the method '
                    'only. No NFL observation is taken from it.</p>' + refs({"source_ids": ["PYTH-NFL", "PFR-GLOSSARY"]}) +
                    '</div><div class="panel body-text"><h3>One score pair per game</h3>'
                    '<div class="formula">home = (home_off + away_def + league)/3 + hfa<br>'
                    'away = (away_off + home_def + league)/3</div>'
                    '<p>The spread is the negated home margin and the total is their sum. The home '
                    'adjustment is a project assumption of 2.0 points applied to every game, including '
                    'the Munich fixture, and that is flagged rather than hidden.</p>'
                    '</div></div>', eyebrow='ORIGINATION')
    body += section('Originated Week 10 board', table(
        'originated-lines', 'Originated lines',
        [('Game', lambda r: rich(r['matchup'], r['id'])),
         ('Kickoff', lambda r: _Markup(f'<span class="nowrap">{esc(r["kickoff"])}</span>')),
         ('TV', 'tv'),
         ('Model spread (home)', 'spread'), ('Model total', 'total'),
         ('Model P(home win)', 'p_home'), ('Fair home', 'fair_home'), ('Fair away', 'fair_away'),
         ('Market spread', 'market_spread'), ('Market total', 'market_total'), ('CLV', 'clv'),
         ('State', lambda r: badge(r['status'], 'warn'))],
        games,
        note='Spread is stated from the home club\'s point of view; a negative number means the '
             'model favours the home club. "Fair" prices are zero-hold conversions of the model '
             'probability, not prices anyone offers. Market cells are blank because no quote exists.'))
    body += section('Model assumptions, stated as assumptions', table(
        'assumptions', 'Assumptions',
        [('Assumption', lambda r: rich(r['name'], r['id'])), ('Value', 'value'),
         ('Source / status', 'status')],
        [{"id": "A1", "name": "Pythagorean exponent", "value": "2.37",
          "status": NFL["assumptions"]["pythagorean_source"], "source_ids": ["PYTH-NFL"]},
         {"id": "A2", "name": "Home-field adjustment",
          "value": f'{NFL["assumptions"]["home_adjustment_points"]:.1f} points',
          "status": NFL["assumptions"]["home_adjustment_source"], "source_ids": ["REPO"]},
         {"id": "A3", "name": "Win-probability spread",
          "value": f'{NFL["assumptions"]["win_probability_sd"]:.2f} points',
          "status": NFL["assumptions"]["win_probability_source"], "source_ids": ["REPO"]},
         {"id": "A4", "name": "Scoring rates",
          "value": "Season to date, unadjusted for opponent",
          "status": "Derived from the official standings snapshot. Opponent strength is not removed.",
          "source_ids": ["NFL-STANDINGS"]}],
        note='A2 and A3 are the two numbers on this site that are chosen rather than sourced. They '
             'are disclosed here and proposed for replacement (S08).'))
    return body


def nfl_correlation():
    rows = [{"id": c["id"], "pair": c["pair"], "n": c["n"], "r": c["pearson"],
             "raw_p": c["raw_p"], "holm": c["holm_p"],
             "evidence": c["evidence"], "caveat": c.get("caveat"),
             "source_ids": c["source_ids"]} for c in NFL["correlations"]]
    blanks = [{"id": c["id"], "pair": c["pair"], "why": c["kind"], "n": None, "r": None,
               "source_ids": c["source_ids"]} for c in NFL["not_collected"]]
    body = notice('Team-level correlation is not leg-level dependence.',
                  'These are 32 clubs measured once each. A parlay needs the joint behaviour of two '
                  'bets on the same games, which is a different quantity and is not estimated here.')
    body += metrics([
        ('Team-level pairs', len(rows), '32 clubs, one snapshot', 'correlation'),
        ('Independent pairs', sum(1 for c in NFL['correlations'] if c['counts_as_independent_evidence']),
         'Five are arithmetic artefacts', 'validation'),
        ('Joint-dependence estimates', 0, 'None collected', 'signals'),
        ('Multi-leg estimates', 0, 'Not identifiable from pairs', 'lab'),
    ])
    body += section('Team-level correlations', table(
        'nfl-correlations', 'Team-level correlations',
        [('Pair', lambda r: rich(r['pair'], r['id'])), ('Clubs', 'n'),
         ('Pearson r', lambda r: num(r['r'], 3, signed=True)),
         ('Raw p (5,000 permutations)', lambda r: num(r['raw_p'], 4)),
         ('Holm-adjusted p', lambda r: num(r['holm'], 4)),
         ('Evidence class', lambda r: badge(r['evidence'], 'blue' if 'exploratory' in r['evidence'] else 'warn')),
         ('Why it is not independent', 'caveat')],
        rows,
        note='Holm adjustment covers all ten pairs. Five pairs share inputs by construction and are '
             'labelled rather than deleted, so the arithmetic is visible. A small p-value on a '
             'structurally induced pair is not a discovery.'))
    body += section('Deliberately not estimated', table(
        'not-collected', 'Uncollected dependence structures',
        [('Structure', lambda r: rich(r['pair'], r['id'])), ('Clubs', 'n'), ('r', 'r'),
         ('Why it is blank', 'why')],
        blanks, note='No value, no sample size and no interval. A blank here is not a zero '
                     'correlation and must not be read as independence.'))
    body += ('<div class="panel body-text"><h3>Why parlays need their own measurement</h3>'
             '<div class="formula">P(A and B) = p_A p_B + rho * sqrt(p_A(1-p_A) p_B(1-p_B))</div>'
             '<p>This identity holds for two binary legs with matching marginals. Multiplying two '
             'prices silently sets rho to zero. For three or more legs even a full pairwise matrix is '
             'insufficient, which is why no combination product is priced on this site.</p>'
             + refs({"source_ids": ["REPO", "NFL-SCHED-W10"]}) + '</div>')
    return body


def nfl_validation():
    rows = [{"id": g["id"], "name": g["name"], "rule": g["rule"], "current": g["current"],
             "state": "PASS" if g["current"].startswith("PASS") else
                      ("PARTIAL" if g["current"].startswith("PARTIAL") else
                       ("OPEN" if g["current"].startswith("PASS for") else "FAIL")),
             "source_ids": ["REPO", "NFL-STANDINGS"]} for g in NFL["gates"]]
    body = notice('Ten gates. Two pass, one is partial, and one is open on rights.',
                  'A gate passes only when a cited artifact supports it. Nothing on this site is '
                  'allowed to move from blocked to qualified without an artifact URL for every '
                  'applicable gate.')
    body += section('Validation gates', table(
        'nfl-gates', 'NFL validation gates',
        [('Gate', lambda r: rich(r['name'], r['id'])), ('Pass rule', 'rule'),
         ('Current evidence', 'current'), ('State', lambda r: badge(r['state'], 'good' if r['state'] == 'PASS' else 'warn'))],
        rows, filter_options=['PASS', 'PARTIAL', 'FAIL', 'OPEN'],
        note='G03, G06, G07, G08 and G09 fail on missing data rather than on a negative result. A '
             'missing input is never counted as a pass.'))
    body += section('Strategy status by gate', table(
        'nfl-strategy-gates', 'Strategy gate matrix',
        [('Strategy', lambda r: rich(r['name'], r['id'])), ('Category', 'category')] +
        [(g, (lambda r, g=g: {'pass': 'Pass', 'blocked': 'Blocked', 'n/a': 'N/A', 'open': 'Open'}[r['gates'][g]]))
         for g in [f'G{i:02d}' for i in range(1, 11)]] +
        [('Passed', lambda r: f"{r['passed']} / {r['applicable']}"),
         ('State', lambda r: badge(r['status']))],
        NFL['evaluations'],
        note='N/A means the gate does not apply to that category and is not counted as a pass. '
             'Qualified status requires every applicable gate to pass.'))
    return body


def nfl_leaderboard():
    board = NFL["leaderboard"]
    ledger = board["shadow_ledger"]
    body = notice('No entries. No rankings. No rewards.',
                  'The competition format is defined and frozen. It is empty because nothing has '
                  'earned a place, not because nothing was measured.')
    body += metrics([
        ('Single-bet entries', board['counts']['Single bets'], 'All blocked', 'signals'),
        ('Parlay entries', board['counts']['Parlays'], 'No dependence measured', 'correlation'),
        ('Prop / combo entries', board['counts']['Player props / combos'], 'No usage data', 'data'),
        ('Cash rewards', 0, 'No prize pool exists', 'leaderboard'),
    ])
    body += ('<div class="table-card"><div class="empty-state"><span class="empty-icon">'
             + '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
               'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
               '<path d="M8 3h8v7a4 4 0 01-8 0zM8 5H4v3a4 4 0 004 4M16 5h4v3a4 4 0 01-4 4M12 14v6M8 21h8"/></svg>'
             '</span><h3>The board opens when a strategy qualifies.</h3><p>'
             + esc(board['empty_because']) + '</p></div></div>')
    body += section('How a place is earned', table(
        'nfl-scoring', 'Ranking rules',
        [('Rule', 'rule'), ('Why', 'why')],
        [{"id": "R1", "rule": "Rank by the lower 95% bound of net return on a frozen common window.",
          "why": "A point estimate hides how much of the result is noise.", "source_ids": ["REPO"]},
         {"id": "R2", "rule": "Separate divisions for singles, parlays and props/combos.",
          "why": "Combination risk is not comparable with a single straight bet.", "source_ids": ["REPO"]},
         {"id": "R3", "rule": "Merit points of 3/2/1 with no cash value.",
          "why": "No prize pool, funding or payment mechanism exists.", "source_ids": ["REPO"]},
         {"id": "R4", "rule": "Every losing row stays in the record.",
          "why": "Deleting rows is the easiest way to fake a winning record.", "source_ids": ["REPO"]},
         {"id": "R5", "rule": "Score only after settlement under the operator's published rule.",
          "why": "Pushes and voids change results; see the market evidence section.", "source_ids": ["REPO", "NFL-TERMS-LEGAL"]}],
        note='These are project rules, not an offer of a prize.'))
    body += section('The shadow ledger is open and empty', '<div class="panel body-text"><p>'
                    + esc(ledger["status"]) + '.</p>' + lines(ledger["rules"]) + '</div>',
                    eyebrow='PROSPECTIVE BY DESIGN')
    return body


def nfl_injuries():
    availability = NFL["availability"]
    injury_rows = [{"id": r["id"], "team": r["Team"], "player": r["Player"], "pos": r["Position"],
                    "injury": r["Injury"] or None, "practice": r["PracticeStatus"],
                    "game": r["GameStatus"] or None, "player_url": r["PlayerURL"],
                    "source_url": r["PlayerURL"],
                    "source_ids": ["NFL-INJ-W10", "NFL-INJURY-POLICY"]}
                   for r in _injury_csv()]
    body = notice('Status is published. Impact is not measured.',
                  'The official report gives participation and game status. It does not say who is a '
                  'starter, who replaces him, or how much the replacement plays. Those three fields '
                  'are blank on this page and on the site.')
    body += metrics([
        ('Listed players in scope', len(injury_rows), 'One game: WAS at NYG', 'data'),
        ('Listed Out', sum(1 for r in injury_rows if r['game'] == 'Out'), 'With a stated reason', 'validation'),
        ('Starters identified', 0, 'No depth chart retrieved', 'review'),
        ('Backup replacement estimates', 0, 'No snap data retrieved', 'signals'),
    ])
    body += section('Availability snapshot, from the official categories only', table(
        'nfl-availability', 'Team availability counts',
        [('Club', lambda r: rich(r['team'], r['id'])), ('Listed', 'listed_players'),
         ('Out', 'out'), ('Doubtful', 'doubtful'), ('Questionable', 'questionable'),
         ('Full practice', 'full_practice'), ('Limited', 'limited'), ('Did not practice', 'did_not_practice'),
         ('Starters affected', 'starters_affected'),
         ('Second/third-string replacements', 'backup_replacement_count'),
         ('Lost on-field value', 'talent_lost')],
        availability,
        note='The three right-hand columns are blank on purpose. Converting "Out" into lost points '
             'requires a depth chart and snap shares that were not retrieved; see suggestion S02.'))
    body += section('Injury report rows', table(
        'nfl-injury-rows', 'Injury report',
        [('Player', lambda r: rich(r['player'], r['id'])), ('Club', 'team'), ('Pos', 'pos'),
         ('Injury as published', 'injury'), ('Practice participation', 'practice'),
         ('Game status', 'game')],
        injury_rows,
        note='Blank injury and game-status cells are blank on the official page. They are not '
             'converted into "available" anywhere in this project.'))
    body += ('<div class="grid-2"><div class="panel body-text"><h3>What the official categories mean</h3>'
             '<p>Practice participation is Did Not Participate, Limited (less than 100% of normal reps) '
             'or Full (100% of normal reps). Game status is Out, Doubtful or Questionable. The '
             '"Probable" category was eliminated, so a player certain to play is not listed on the '
             'game status report at all.</p>'
             + refs({"source_ids": ["NFL-INJURY-POLICY"]}) +
             '</div><div class="panel body-text"><h3>What is missing for the owner requirement</h3>'
             '<p>The request asks for second-, third- and fourth-string exposure on both sides of the '
             'ball. Meeting it needs a published depth order per position plus recent snap share, so '
             'that a listed absence can be converted into a change in expected output.</p>'
             '<p>Neither was retrieved. The depth-chart address on NFL.com returned a 404 to the '
             'reader, and no snap-count page was obtained. Rather than estimate, the fields stay '
             'blank and the gap is published.</p>'
             + refs({"source_ids": ["REPO", "NFL-INJ-W10"]}) + '</div></div>')
    return body


def _injury_csv():
    import csv
    with (ROOT / "data/nfl-injuries-2026-w10.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def nfl_stands():
    teams = sorted(NFL["teams"], key=lambda t: (t["conference"], -t["pct"], -t["net"]))
    rows = [{"id": t["id"], "team": t["team"], "conf": t["conference"], "w": t["w"], "l": t["l"],
             "t": t["t"], "pct": f'{t["pct"]:.3f}', "pf": t["pf"], "pa": t["pa"], "net": t["net"],
             "off": num(t["off_ppg"], 1), "dfn": num(t["def_ppa"], 1),
             "pyth": f'{t["pyth_pct"]:.3f}', "exp": num(t["expected_wins"], 2),
             "resid": pn(t["luck_residual"]), "source_ids": t["source_ids"]} for t in teams]
    body = notice('A snapshot, not a live table.',
                  'All 32 rows were parsed from saved official text on 2026-11-12 and each value was '
                  're-derived from the others before publication. Division and conference record '
                  'fields are deliberately absent: division record, conference record and four middle columns that could not be identified from the rendered table.')
    body += metrics([
        ('Clubs checked', len(rows), 'All 32 league clubs', 'data'),
        ('Team-games in scope', NFL['league']['team_games'], 'Eight or nine per club', 'brief'),
        ('League scoring', f"{NFL['league']['league_points_per_team_game']:.2f}",
         'Points per team-game', 'signals'),
        ('Fields withheld', 6, 'Of 16 displayed; no header to confirm them', 'review'),
    ])
    body += section('Standings and derived strength', table(
        'nfl-standings', 'Standings snapshot',
        [('Club', lambda r: rich(r['team'], r['id'])), ('Conf', 'conf'), ('W', 'w'), ('L', 'l'),
         ('T', 't'), ('PCT', 'pct'), ('PF', 'pf'), ('PA', 'pa'), ('NET', 'net'),
         ('Off PPG', 'off'), ('Def PPG', 'dfn'), ('Pyth PCT', 'pyth'),
         ('Expected W', 'exp'), ('Actual − expected', 'resid')],
        rows, filter_options=['AFC', 'NFC'],
        note='PF/PA are season totals. Off and Def are per game. Pyth PCT and Expected W are derived '
             'with a published exponent. The residual is descriptive and is not proof of luck.'))
    body += section('Record versus scoring', table(
        'nfl-residuals', 'Record-versus-scoring gap',
        [('Club', lambda r: rich(r['team'], r['id'])), ('Actual W', 'w'),
         ('Expected W', 'exp'), ('Gap', 'resid')],
        sorted(rows, key=lambda r: -abs(float(r["resid"])))[:8],
        note='Largest absolute gaps only. A positive gap means the record is better than the scoring '
             'profile implies. Nothing here is adjusted for opponent strength.'))
    return body


def nfl_overview():
    body = notice('NFL research workspace: sourced observations, originated numbers, and honest blanks.',
                  'Thirty-two club rows, twenty injury rows and fourteen fixtures were read from '
                  'NFL.com on 2026-11-12. Two separately built labs add 216 and 210 further verified rows. '
                  'Every line in this section is an originated model number, not a market price, and '
                  'nothing here is a recommendation.')
    body += metrics([
        ('Verified rows here', NFL['verified_rows']['total'], 'Plus 216 and 210 in the two labs', 'data'),
        ('Originated games', len(NFL['games']), 'Week 10, model only', 'lab'),
        ('Qualified strategies', 0, 'All eight blocked', 'validation'),
        ('Open review items', f'{NFL_OPEN_FLAGS} of {len(FLAGS["flags"])}', 'All published for review', 'review'),
    ])
    body += ('<section class="hero-panel"><div><div class="eyebrow">ORIGINATE, THEN VERIFY</div>'
             '<h2>Own the number.<br>Show your work.</h2>'
             '<p>Build a line from official scoring data, check it against the record it came from, '
             'and keep every assumption visible. A number you cannot defend is not a signal.</p>'
             + '<a class="button primary" href="nfl-decisions.html">Read the decision brief '
               '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" '
               'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
               '<path d="M5 12h14M13 6l6 6-6 6"/></svg></a></div>'
             '<div class="hero-visual"><svg class="court" aria-hidden="true" viewBox="0 0 360 200" '
             'fill="none" stroke="currentColor" stroke-width="1.1">'
             '<rect x="4" y="4" width="350" height="192" rx="4"/>'
             '<path d="M4 52h350M4 148h350M60 4v48M300 4v48M60 148v48M300 148v48"/>'
             '<path d="M120 4v10h120V4M120 196v-10h120v10"/>'
             '<circle cx="180" cy="100" r="26"/><path d="M154 100h52"/></svg>'
             '<div class="court-label"><span></span>Observe, price, verify</div></div></section>')
    cards = [
        ('01 / DECIDE', 'Signals', 'Choose with the gaps in view',
         'Ranked suggestions, the questions they close, and the four gaps blocking any reward decision.',
         'nfl-suggestions.html', 'Review the suggestions'),
        ('02 / ORIGINATE', 'Lab', 'A line you can reproduce',
         'One score pair per game drives the spread and the total. Market cells stay blank because no price exists.',
         'nfl-lines.html', 'See the originated board'),
        ('03 / QUALIFY', 'Validation', 'Evidence earns the rank',
         'Ten gates, eight blocked strategies and an empty leaderboard. A missing input never counts as a pass.',
         'nfl-validation.html', 'Inspect the gates'),
    ]
    body += '<div class="grid-3">' + "".join(
        f'<a class="path-card" href="{href}"><span class="step">{step}</span>'
        f'<span class="card-icon">{_svg_icon(ico)}</span><h3>{title}</h3><p>{description}</p>'
        f'<span class="card-link">{cta} →</span></a>'
        for step, ico, title, description, href, cta in cards) + '</div>'

    # Decision-readiness table (brief requirement): one row per requirement, the gate that
    # blocks it, and the number that would clear it. Data: research/nfl-requirements.json.
    gate_names = {g["id"]: g["name"] for g in NFL["gates"]}

    def _gate_cell(row):
        gid = row.get("gate")
        if not gid:
            return esc(row.get("gate_note") or "None")
        name = gate_names.get(gid, "")
        label = f"{gid} — {name}" if name else gid
        return _Markup(f'<a href="nfl-validation.html">{esc(label)}</a>'
                       f'<span class="row-sub">{esc(row.get("gate_note", ""))}</span>')

    body += section('Decision readiness — one row per requirement', table(
        'nfl-decision-readiness', 'Requirement, blocking gate, and the number that would clear it',
        [('Requirement', lambda r: rich(r['requirement'], r['id'])),
         ('State', lambda r: badge(r['status'], {'Implemented': 'good', 'Blocked': 'warn',
                                                 'In progress': 'blue'}.get(r['status'], 'warn'))),
         ('Blocking gate', _gate_cell),
         ('Number that would clear it', 'clear_number')],
        REQUIREMENTS['requirements'],
        filter_options=['Implemented', 'Partial', 'In progress', 'Blocked'],
        note='One row per NFL requirement. Gate IDs G01–G10 are this project\'s own validation '
             'contracts, published on the validation gates page; naming one binding gate per '
             'requirement is a documented project mapping from that requirement\'s recorded evidence '
             'to the gate whose pass rule it currently fails, not an official fact. The clearing '
             'numbers are pre-registered project design choices (research/nfl-protocol.json, '
             'research/nfl-catalog.json), not official standards, and none of them is a promise that '
             'the requirement becomes awardable. The Sources column carries the official evidence '
             'behind each requirement\'s current state.'))

    body += section('Three NFL workstreams are published here', table(
        'nfl-workstreams', 'Which page answers which question',
        [('Workstream', lambda r: rich(r['lab'], r['id'])), ('Size', 'size'),
         ('What it holds', 'content'), ('Read it when', 'when'), ('Open', 'where')],
        [
            {"id": "W1", "lab": "NFL origination lab — this section",
             "size": f"{ORIGINATION_PAGES} pages · {NFL['verified_rows']['total']} verified rows",
             "content": "Originated Week 10 spreads and totals, the decision brief, ranked suggestions, "
                        f"{len(QUESTIONS['questions'])} remaining questions, ten validation gates, the "
                        "competition format, the review register, a decision-readiness table and a dated "
                        "re-verification log.",
             "when": "You want to decide what to do next, or to originate and challenge a number.",
             "where": _Markup('<a href="nfl-suggestions.html">Suggestions and decision brief</a>'),
             "source_ids": ["REPO"]},
            {"id": "W2", "lab": "NFL research lab — sub-site",
             "size": "15 pages · 216 verified rows",
             "content": "Standings, passing, rushing, receiving, team offense and defense, and a bounded "
                        "Week 7 injury report, each row source-linked, plus its own audit and receipts.",
             "when": "You want the wider statistical record behind the numbers.",
             "where": _Markup('<a href="nfl/index.html">NFL research lab</a>'),
             "source_ids": ["REPO"]},
            {"id": "W3", "lab": "NFL line-origination lab — sub-site",
             "size": "14 pages · 210 injury rows",
             "content": "Week 10 injuries and depth deficiencies read twice from two official pages, a "
                        "documented spread and total model, a fail-closed validation protocol and a competition "
                        "that cannot yet be entered.",
             "when": "You want the fullest Week 10 injury and depth picture, or the model's sensitivity range.",
             "where": _Markup('<a href="nfl/origination/index.html">Line-origination dashboard</a>'),
             "source_ids": ["REPO"]},
        ],
        note='All three use the same 2026-11-12 snapshot and the same official league sources, and all three '
             'report zero qualified strategies and an empty leaderboard. They were built independently by three '
             'workstreams and are kept separate and attributed rather than folded into one narrative, because '
             'they differ in scope: W1 covers one matchup in depth, W2 the full statistical record, W3 the '
             'widest injury and depth read. Row counts are what each workstream verified, and they are not additive.'))
    body += section('What the numbers say, and what they do not', table(
        'nfl-headlines', 'Headline findings',
        [('Finding', 'finding'), ('Reading', 'reading'), ('Evidence', lambda r: badge(r['state'], r['kind']))],
        [
            {"id": "H1", "finding": "Points-based expectation beat a flat guess on the displayed record",
             "reading": f"Brier {NFL['calibration']['scores']['Pythagorean (PF/PA, x=2.37)']['brier']:.4f} "
                        f"versus 0.25 across 32 clubs. The scoring profile carried information inside the snapshot.",
             "state": "Derived", "kind": "blue", "source_ids": ["NFL-STANDINGS", "PYTH-NFL"]},
            {"id": "H2", "finding": "No club is more than about 2.2 wins from its scoring expectation",
             "reading": "Denver and Tampa Bay are the widest gaps. In a nine-game sample that is a normal "
                        "spread, not a market error.",
             "state": "Derived", "kind": "blue", "source_ids": ["NFL-STANDINGS", "PYTH-NFL"]},
            {"id": "H3", "finding": "Five of ten team correlations are arithmetic artefacts",
             "reading": "Net points, wins and the record residual share inputs. They are labelled, not "
                        "presented as discoveries.",
             "state": "Corrected", "kind": "good", "source_ids": ["NFL-STANDINGS"]},
            {"id": "H4", "finding": "The injury snapshot covers one game and names no starters",
             "reading": "Twenty players are listed with official statuses. Converting that into lost "
                        "on-field value needs data that was not retrieved.",
             "state": "Unverified", "kind": "warn", "source_ids": ["NFL-INJ-W10", "NFL-INJURY-POLICY"]},
            {"id": "H5", "finding": "No priced market, so no performance claim",
             "reading": "ROI, closing-line value and break-even tests are blank by rule rather than zero.",
             "state": "Blocked", "kind": "warn", "source_ids": ["NFL-TERMS-LEGAL", "REPO"]},
        ],
        note='Each row is either a re-derived calculation or an explicit statement of a limit.'))
    readiness = [
        {'req': 'Official provenance and receipts for every number', 'gate': 'G01',
         'clears': 'Every row carries an NFL.com URL and a check date',
         'current': '66 verified rows: 32 standings, 20 injury rows, 14 fixtures',
         'state': 'Clear', 'source_ids': ['NFL-STANDINGS', 'NFL-INJ-W10', 'NFL-SCHED-W10', 'REPO']},
        {'req': 'Pre-kickoff information only, no lookahead', 'gate': 'G02',
         'clears': 'Features frozen before kickoff for every line',
         'current': 'Originated lines pass; probability calibration FAILs (scores against the same snapshot)',
         'state': 'Blocked', 'source_ids': ['REPO', 'NFL-SCHED-W10']},
        {'req': 'Coverage and statistical power', 'gate': 'G03',
         'clears': '500 settled selections, 200 distinct games, 60 dates',
         'current': '0 settled selections; 136 captured results (retrospective); 14 originated games',
         'state': 'Blocked', 'source_ids': ['REPO', 'NFL-STANDINGS']},
        {'req': 'Forecast quality versus a frozen benchmark', 'gate': 'G04',
         'clears': 'Sequential, multi-season out-of-sample evaluation',
         'current': 'PARTIAL: Brier vs a flat 0.500 reference exists for the 32-club record only',
         'state': 'Partial', 'source_ids': ['REPO', 'NFL-STANDINGS', 'PYTH-NFL']},
        {'req': 'Joint leg dependence for parlays and prop combos', 'gate': 'G05',
         'clears': 'Aligned threshold-hit observations at the offered line, with n',
         'current': '0 joint estimates; 10 team-level cross-sectional pairs only (a different quantity)',
         'state': 'Blocked', 'source_ids': ['REPO', 'NFL-STANDINGS']},
        {'req': 'Executable economics: quote, hold, settlement rules', 'gate': 'G06',
         'clears': 'A captured, actually available operator quote with published void/push rules',
         'current': '0 prices retrieved; no NFL market quote exists in the record',
         'state': 'Blocked', 'source_ids': ['REPO', 'NFL-TERMS-LEGAL']},
        {'req': 'Uncertainty intervals and robustness sweeps', 'gate': 'G07',
         'clears': 'Intervals on every assumed constant and a published sensitivity sweep',
         'current': 'No interval published; the 2.0-point home adjustment is an assumption, not a sourced value',
         'state': 'Blocked', 'source_ids': ['REPO']},
        {'req': 'Pre-registered trials and multiple-testing control', 'gate': 'G08',
         'clears': 'A frozen trial family declared before results are seen',
         'current': '0 pre-registered families; 10 correlations are Holm-adjusted but labelled exploratory',
         'state': 'Blocked', 'source_ids': ['REPO', 'NFL-STANDINGS']},
        {'req': 'Forward shadow ledger before any live use', 'gate': 'G09',
         'clears': 'A shadow record in a frozen common future window',
         'current': '0 live entries; shadow ledger is specified but empty',
         'state': 'Blocked', 'source_ids': ['REPO']},
        {'req': 'Reproducibility and source-use rights', 'gate': 'G10',
         'clears': 'A rights decision confirming non-commercial, in-scope publication',
         'current': 'Reproducibility PASS (byte-identical rebuilds); rights OPEN — NFL.com §1.3 restricts systematic retrieval',
         'state': 'Open', 'source_ids': ['REPO', 'NFL-TERMS-LEGAL']},
        {'req': 'Starters identified and replacements named, offence and defence', 'gate': 'M02',
         'clears': 'Official depth chart joined to inactives/Game Books, dated and hashed',
         'current': '0 starters identified; the NFL.com depth path returned a 404',
         'state': 'Blocked', 'source_ids': ['REPO', 'NFL-INJ-W10']},
        {'req': 'Playing time: snaps, targets and carries per player', 'gate': 'M03',
         'clears': 'Official snap-count evidence per player',
         'current': 'Not retrieved; every cell is blank and flagged',
         'state': 'Blocked', 'source_ids': ['REPO']},
        {'req': 'Blank game status does not mean available', 'gate': 'M09',
         'clears': 'Designation-to-play rates with confidence intervals',
         'current': 'Undocumented on the retrieved page; blank everywhere it appears',
         'state': 'Blocked', 'source_ids': ['REPO', 'NFL-INJURY-POLICY', 'NFL-INJ-W10']},
        {'req': 'Home-field value sourced, not assumed', 'gate': 'M10',
         'clears': 'An official or multi-season sourced home-field range',
         'current': '2.0 points assumed for all 14 games; flagged, not hidden',
         'state': 'Blocked', 'source_ids': ['REPO']},
        {'req': 'Settlement rules: pushes, voids and overtime', 'gate': 'M06',
         'clears': 'Operator rule documented per bet type before scoring',
         'current': 'Documented for other sports; nothing confirmed for NFL',
         'state': 'Blocked', 'source_ids': ['REPO']},
        {'req': 'Publication rights for compiled NFL.com data', 'gate': 'M07',
         'clears': 'A rights determination covering this snapshot and its reuse',
         'current': 'Restricted · open; no dataset or redistribution release',
         'state': 'Open', 'source_ids': ['REPO', 'NFL-TERMS-LEGAL']},
        {'req': 'Venue of every fixture transcribed from the game centre', 'gate': '—',
         'clears': 'A venue column sourced to the official game centre page',
         'current': 'Not retrieved; blank and flagged',
         'state': 'Blocked', 'source_ids': ['REPO', 'NFL-SCHED-W10']},
        {'req': "League's dated schedule announcement beside the live schedule", 'gate': '—',
         'clears': 'The dated announcement published adjacent to the live page',
         'current': 'Not published; blank and flagged',
         'state': 'Blocked', 'source_ids': ['REPO', 'NFL-SCHED-W10']},
        {'req': 'Official Game Books for starters and game-day status', 'gate': '—',
         'clears': 'Game Book evidence used; depth rank never inferred',
         'current': 'Not used; no starter or snap value is inferred anywhere',
         'state': 'Blocked', 'source_ids': ['REPO', 'NFL-INJ-W10']},
        {'req': 'Roster/IR sweep across all 32 clubs before trusting a model', 'gate': '—',
         'clears': 'A completed 32-club roster and injured-reserve sweep',
         'current': 'Not run; treated as a blocking precondition, not evidence',
         'state': 'Blocked', 'source_ids': ['REPO']},
    ]
    body += section('Decision readiness: one row per requirement', table(
        'decision-readiness', 'Decision-readiness table',
        [('Requirement', 'req'), ('Gate', 'gate'), ('Clears when', 'clears'),
         ('Now', 'current'), ('State', lambda r: badge(r['state'],
             'good' if r['state'] == 'Clear' else ('neutral' if r['state'] == 'Open' else 'warn')))],
        readiness,
        note='“Now” figures come from this repository’s own registers and saved snapshots, not from estimates. '
             'Rows marked Blocked or Open are preconditions: nothing ranked, priced or rewarded passes them. '
             'Gate IDs are the project’s own validation gates (G) and missing-information items (M); “—” means '
             'no project gate has been defined for that requirement yet — which is itself a gap.'))
    body += '<p class="source-line">' + refs({"source_ids": ["NFL-STANDINGS", "NFL-INJ-W10", "NFL-SCHED-W10",
                                                              "NFL-INJURY-POLICY", "NFL-TERMS-LEGAL", "PYTH-NFL"]}) + '</p>'
    return body


def _svg_icon(name):
    paths = {
        "Signals": '<path d="M3 13h4l3-8 4 14 3-8h4"/>',
        "Lab": '<path d="M9 3v6l-5 9a2 2 0 002 3h12a2 2 0 002-3l-5-9V3M8 3h8M7 15h10"/>',
        "Validation": '<path d="M12 3l8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6"/>',
    }
    return ('<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' + paths.get(name, "") + '</svg>')


def nfl_review():
    rows = [{"id": f["id"], "item": f["item"], "finding": f["finding"],
             "unverified": f["unverified_value"], "impact": f["impact"],
             "status": f["status"], "source_ids": f["source_ids"]} for f in FLAGS["flags"]]
    open_n = sum(1 for f in FLAGS["flags"] if f["status"] == "Needs review")
    body = notice(f'{len(FLAGS["flags"])} NFL items for review; {open_n} are open and '
                  f'{len(FLAGS["flags"]) - open_n} are corrected. None blocks publication.',
                  'Review items block unsupported claims and rewards, not an honest research page. '
                  'Each row links to the official source that produced it. The navigation badge on '
                  'this site counts open items only, which is why it is smaller than the row count.')
    body += section('Flagged for review — NFL', table(
        'nfl-flags', 'NFL review register',
        [('Item', lambda r: rich(r['item'], r['id'])), ('Finding', 'finding'),
         ('Unverified value', 'unverified'), ('Impact on this site', 'impact'),
         ('State', lambda r: badge(r['status'], 'good' if r['status'] == 'Corrected' else 'warn'))],
        rows, filter_options=['Needs review', 'Corrected'],
        note='Blank unverified-value cells are intentional. Nothing in this register is filled in '
             'with an estimate.'))
    body += section('What was checked, and with what', table(
        'nfl-receipts', 'Source receipts',
        [('Dataset', lambda r: rich(r['file'], r['file'])), ('Rows', 'rows'),
         ('Official source', 'source_url'), ('Checks applied', lambda r: ", ".join(r['checks'])),
         ('Saved retrieval', 'retrieval')],
        RECEIPTS["datasets"],
        note='Each dataset is regenerated from the saved page text on every build. If a check fails '
             'the extractor refuses to publish rather than writing a contradiction.'))
    return body


def executive():
    """Reconciled NFL executive brief; links distinguish official evidence from project analyses."""
    body = notice(
        'Do not treat this research as a validated live wagering edge or reward decision.',
        'The repository now contains separate results, market-price, and availability research desks. '
        'Their samples and price policies are not yet one governed prospective evaluation. A historical '
        'spread finding is promising but retrospective; totals are null. No strategy is qualified for '
        'live deployment or reward. Compiled 2026-11-15 from source reads dated through 2026-11-14; '
        'this reconciliation did not perform a new live fetch.')
    body += section('Executive findings',
        '<div class="grid-2">'
        '<article class="panel body-text"><h3>Official results make retrospective tests possible</h3>'
        '<p>The results desk records 136 final scores (weeks 1–9 of 2026) and reconciles 160 standings '
        'fields. This is a saved-results pipeline, not a multi-season or prospective test. '
        '<a href="https://www.nfl.com/schedules/2026/by-week/week-1" target="_blank" rel="noopener noreferrer">Official NFL schedule/results ↗</a> · '
        '<a href="nfl-results-games.html">Results audit</a></p></article>'
        '<article class="panel body-text"><h3>Signal is not yet deployment evidence</h3>'
        '<p>One bounded retrospective spread board reports 77–43 (64.2%; permutation p=0.0021; '
        'BH q=0.022) over 120 scored games; its total board reports 60–60 (50%). These are analyses, '
        'not official NFL statistics, proof of future skill, or profit. Read the complete selection, '
        'holdout and uncertainty limits. '
        '<a href="https://www.nfl.com/schedules/2026/by-week/week-1" target="_blank" rel="noopener noreferrer">Official outcome source ↗</a> · '
        '<a href="nfl-results-skill.html">Skill and luck analysis</a></p></article>'
        '<article class="panel body-text"><h3>Market prices exist in separate research desks</h3>'
        '<p>A price desk contains 136 historical closing-line observations attributed to Pro-Football-Reference, '
        'not an official NFL source. The lifecycle desk leaves its market cells blank pending its own '
        'price-policy gate. Do not combine these as a canonical price feed or claim unified ROI/CLV. '
        '<a href="https://www.pro-football-reference.com/about/sources.htm" target="_blank" rel="noopener noreferrer">Publisher source information ↗</a> · '
        '<a href="nfl-pricing/site/prices.html">Pricing desk</a> · '
        '<a href="nfl-lifecycle-3f5c/site/price-snapshots.html">Lifecycle policy and ledger</a></p></article>'
        '<article class="panel body-text"><h3>Injury reports are not participation evidence</h3>'
        '<p>Dated reports and club depth transcriptions support a preliminary replacement analysis, '
        'but chart rank is not playing time. Chart freshness, shared/empty slots, roster changes, '
        'and Houston’s image chart remain flagged. Official inactives, Game Books and snap counts '
        'are needed before confirming who replaced whom. '
        '<a href="https://www.nfl.com/injuries/league/2026/REG10" target="_blank" rel="noopener noreferrer">Official NFL injury report ↗</a> · '
        '<a href="nfl-lifecycle-3f5c/site/replacement-depth.html">Replacement-depth analysis</a> · '
        '<a href="nfl-availability-28ef/site/flagged.html">Availability flags</a></p></article>'
        '<article class="panel body-text"><h3>Correlation is narrowly measured</h3>'
        '<p>The results desk reports spread/total phi −0.068 (p=0.47, n=114) for its bounded same-game '
        'sample. This neither validates independence nor supports player-prop combo pricing. Parlays '
        'and combos stay blocked until direct joint probabilities and settlement rules are validated. '
        '<a href="https://www.nfl.com/schedules/2026/by-week/week-1" target="_blank" rel="noopener noreferrer">Official outcome source ↗</a> · '
        '<a href="nfl-results-correlation.html">Correlation analysis</a></p></article>'
        '<article class="panel body-text"><h3>Leaderboard and demotion gates are research controls</h3>'
        '<p>There are no strategies qualified for live use or rewards. Signal and staking are separated; '
        'the documented demotion gate has not been exercised on a live entry. '
        '<a href="nfl-results-leaderboard.html">Results leaderboard</a> · '
        '<a href="nfl-lifecycle-3f5c/site/leaderboard.html">Signal vs staking</a> · '
        '<a href="nfl-lifecycle-3f5c/site/demotion.html">Demotion gate</a></p></article>'
        '</div>')
    body += section('Questions that block a reasonable decision',
        '<div class="panel body-text"><ol>'
        '<li><strong>Which price source is permitted?</strong> Missing: recorded rights decision, '
        'one market universe, opening/closing timestamp convention, vig and settlement/void rules. '
        'Clear with an authorized provider, frozen policy and field-level coverage validation. '
        '<a href="https://www.nfl.com/legal/terms/" target="_blank" rel="noopener noreferrer">NFL Terms ↗</a></li>'
        '<li><strong>Does the signal generalize?</strong> Missing: a pre-registered model, multiple '
        'chronological seasons, untouched final holdout and prospective shadow forecasts. Clear with '
        'version-frozen rules, benchmark-relative proper scores, uncertainty and multiple-testing control. '
        '<a href="https://www.nfl.com/schedules/2026/by-week/week-1" target="_blank" rel="noopener noreferrer">Official result source ↗</a></li>'
        '<li><strong>Who actually replaced the starter?</strong> Missing: point-in-time official '
        'inactives/Game Books, transaction-aware roster evidence and snap counts. Clear by joining '
        'expected starters to actual participation and playing-time evidence; do not infer from jersey number. '
        '<a href="https://www.nfl.com/injuries/league/2026/REG10" target="_blank" rel="noopener noreferrer">Official injury report ↗</a></li>'
        '<li><strong>Do injury labels add information?</strong> Missing: multi-season designation-to-play '
        'rates and uncertainty. Clear with chronological, identical-model ablations with and without '
        'verified availability; use surprise/change features rather than fixed penalties. <a href=\"https://www.nfl.com/injuries/league/2026/REG10\" target=\"_blank\" rel=\"noopener noreferrer\">Official NFL injury report ↗</a></li>'
        '<li><strong>Can parlays or player-prop combos qualify?</strong> Missing: calibrated joint '
        'probabilities at the relevant thresholds and operator-specific push/void rules. Clear with '
        'prospective joint calibration; do not multiply marginal probabilities. <a href=\"https://www.nfl.com/schedules/2026/by-week/week-1\" target=\"_blank\" rel=\"noopener noreferrer\">Official NFL outcome source ↗</a></li>'
        '<li><strong>What sends a live strategy back to paper?</strong> Gate rules exist but have no '
        'live operational history. Clear by shadow-testing alerts/rollback, freezing thresholds and '
        'publishing trigger counts before any candidate is considered live. <a href=\"https://www.nfl.com/legal/terms/\" target=\"_blank\" rel=\"noopener noreferrer\">Official NFL Terms ↗</a></li>'
        '</ol></div>')
    body += section('Suggested sequence — review before implementation',
        '<ol class="body-text">'
        '<li>Resolve source rights and price policy; do not publish unified market residual, ROI, CLV or rewards before that gate.</li>'
        '<li>Pre-register one singles-only shadow baseline, benchmarks, sample windows and gates before the evaluation window.</li>'
        '<li>Build permissible point-in-time availability evidence with dates, hashes and conflicts; capture inactives and snap counts only from authorized sources.</li>'
        '<li>Run chronological injury/personnel and fixture-context ablations with uncertainty; keep totals visible beside competing estimators until walk-forward comparison.</li>'
        '<li>Keep parlays and prop combos blocked pending validated joint evidence and settlement rules.</li>'
        '</ol><p class="body-text">Review the <a href="nfl-suggestions.html">ranked Suggestions register</a>, '
        '<a href="nfl-questions.html">Questions &amp; Answers</a>, <a href="nfl-decisions.html">decision-readiness brief</a> '
        'and <a href="nfl-review.html">Flagged for Review</a>. No proposal is approved by this summary.</p>')
    body += section('Provenance and limits',
        '<p class="body-text">This page consolidates existing repository records; it does not claim a fresh official-source read '
        'on its compile date. Linked NFL pages are the official publishers for schedules, reports and terms. '
        'The findings are calculated project outputs, not official NFL statistics. Saved rendered text is not a raw HTTP archive; '
        'integrity hashes establish file integrity, not truth. Price observations from non-NFL publishers remain separately '
        'attributed. No automated NFL-site scraper is enabled. See <a href="https://www.nfl.com/legal/terms/" '
        'target="_blank" rel="noopener noreferrer">NFL Terms ↗</a>, the <a href="sources.html">source register</a> '
        'and <a href="nfl-review.html">Flagged for Review</a>.</p>')
    return body
