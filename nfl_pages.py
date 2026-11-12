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
SOURCES = {s["id"]: s for s in json.loads((ROOT / "research/sources.json").read_text(encoding="utf-8"))}


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
    rows = [{"id": s["id"], "rank": s["rank"], "title": s["title"], "category": s["category"],
             "problem": s["problem"], "proposal": s["proposal"], "unlocks": s["unlocks"],
             "effort": s["effort"], "risk": s["risk_if_skipped"], "status": s["status"],
             "source_ids": ["REPO", "NFL-TERMS-LEGAL"] if s["category"] == "Rights" else ["REPO"]}
            for s in DECISIONS["suggestions"]]
    blocking = [q for q in DECISIONS["missing_information"]
                if q["id"] in DECISIONS["blocking_before_any_reward"]]
    body = notice(
        "Ranked by decision value, not by effort.",
        "Each suggestion exists to close a named gap. A change that adds a number without adding "
        "verification is rejected by the acceptance tests at the bottom of this page.")
    body += metrics([
        ('Suggestions on the table', len(DECISIONS["suggestions"]), 'Each closes a named gap', 'signals'),
        ('Open questions', len(QUESTIONS["questions"]), 'Answered or explicitly unresolved', 'validation'),
        ('Blocking before any reward', len(blocking), 'All four are data gaps, not opinions', 'leaderboard'),
        ('Suggestions completed', 0, 'Proposals only; nothing implemented', 'requirements'),
    ])
    body += section('Review the options before changing anything', table(
        'suggestion-register', 'Suggestions register',
        [('Suggestion', lambda r: rich(r['title'], r['id'])), ('Effort', 'effort'),
         ('What it closes', 'problem'), ('What it unlocks', 'unlocks'),
         ('Risk if skipped', 'risk'), ('Status', lambda r: badge(r['status'], 'blue'))],
        rows,
        note='Reading order is the "Sequence" section below. None of these proposals changes a '
             'published value; each one adds evidence that does not yet exist.')) 
    body += section('Sequence: what to do first', '<div class="panel body-text">'
                    + lines(DECISIONS["sequence"]) + '</div>',
                    eyebrow='CHEAPEST BLOCKING ITEM FIRST')
    body += section('Acceptance tests for any proposal', '<div class="panel body-text">'
                    + lines(DECISIONS["acceptance_tests"]) + '</div>',
                    eyebrow='HOW TO JUDGE A CHANGE')
    body += section('What is blocking a reward decision', table(
        'reward-blockers', 'Blocking gaps',
        [('Question', lambda r: rich(r['question'], r['id'])), ('Why it matters', 'why_it_matters'),
         ('Blocks', 'blocks'), ('Resolved by', 'suggestion')],
        blocking,
        note='These four are the reason no strategy is ranked and no reward is awarded.'))
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
    body = notice('Fourteen questions; none of them is answered by guessing.',
                  'Each row separates the sourced part of the answer from the part that is still '
                  'open, and names what would settle it. Only one question needs the owner: DQ14.')
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
                  'NFL.com on 2026-11-12. Every line on this site is an originated model number, not '
                  'a market price, and nothing here is a recommendation.')
    body += metrics([
        ('Verified rows', NFL['verified_rows']['total'], 'Standings, injuries, fixtures', 'data'),
        ('Originated games', len(NFL['games']), 'Week 10, model only', 'lab'),
        ('Qualified strategies', 0, 'All eight blocked', 'validation'),
        ('Open review items', len(FLAGS['flags']), 'All published', 'review'),
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
    body = notice('Twelve NFL items for review. None blocks publication.',
                  'Review items block unsupported claims and rewards, not an honest research page. '
                  'Each row links to the official source that produced it.')
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
    """NFL executive summary: five findings, four blockers, one decision."""
    cal = NFL["calibration"]["scores"]
    pyth = cal["Pythagorean (PF/PA, x=2.37)"]["brier"]
    flat = cal["Flat .500 (no information)"]["brier"]
    widest = sorted(NFL["teams"], key=lambda t: -abs(t["luck_residual"]))[:2]
    findings = [
        {"id": "E1", "headline": "The record now rests on official NFL sources, not inherited claims",
         "detail": f"{NFL['verified_rows']['total']} rows were parsed from saved NFL.com text on "
                   f"2026-11-12: 32 club standings rows, 20 injury-report rows and 14 Week 10 fixtures. "
                   f"Every value is re-derived arithmetically before publication and the build aborts "
                   f"on any contradiction.",
         "state": "Verified snapshot", "kind": "good",
         "source_ids": ["NFL-STANDINGS", "NFL-INJ-W10", "NFL-SCHED-W10"]},
        {"id": "E2", "headline": "Points-based expectation carried real information in this snapshot",
         "detail": f"Scored against the displayed records of all 32 clubs, the Pythagorean baseline "
                   f"returned a Brier score of {pyth:.4f} against {flat:.2f} for a flat .500 guess. "
                   f"The exponent is the published NFL convention, not fitted here, but the comparison "
                   f"is inside one partial season and is not a forward test.",
         "state": "Derived · exploratory", "kind": "blue",
         "source_ids": ["NFL-STANDINGS", "PYTH-NFL"]},
        {"id": "E3", "headline": "No club is far from its scoring expectation",
         "detail": f"The widest record-versus-scoring gaps are {widest[0]['id']} at "
                   f"{widest[0]['luck_residual']:+.2f} wins and {widest[1]['id']} at "
                   f"{widest[1]['luck_residual']:+.2f} wins. In an eight- or nine-game sample that is "
                   f"ordinary variation, not evidence of a mispriced market.",
         "state": "Derived · exploratory", "kind": "blue",
         "source_ids": ["NFL-STANDINGS", "PYTH-NFL"]},
        {"id": "E4", "headline": "Fourteen originated lines exist and cannot yet be judged",
         "detail": "Each Week 10 game has a model spread, total and fair price from one coherent score "
                   "pair. No sportsbook quote was retrieved, so every market cell, ROI and closing-line "
                   "value is blank rather than zero.",
         "state": "Blocked", "kind": "warn",
         "source_ids": ["NFL-SCHED-W10", "NFL-STANDINGS", "NFL-TERMS-LEGAL"]},
        {"id": "E5", "headline": "The injury requirement is documented but not measured",
         "detail": "Official statuses are published for 20 players in one game. Starter and "
                   "second-, third- and fourth-string impact is blank because no depth chart and no "
                   "snap share was retrieved. The gap is published with a proposed fix.",
         "state": "Unverified", "kind": "warn",
         "source_ids": ["NFL-INJ-W10", "NFL-INJURY-POLICY"]},
        {"id": "E6", "headline": "Nothing is ranked, rewarded or recommended",
         "detail": "All eight strategies are blocked, two of ten gates pass, the leaderboard is empty "
                   "and no cash reward exists. The four blocking gaps are a dated market price, depth "
                   "and snap data, and a measured leg dependence.",
         "state": "Blocked", "kind": "warn",
         "source_ids": ["REPO"]},
    ]
    body = notice('One paragraph, if you read nothing else.',
                  'The NFL section is built, sourced and reproducible, and it overturns nothing: the '
                  'scoring information is real, the originated lines are coherent, and the market '
                  'comparison is simply absent. Until a dated price, depth and snap data, and a '
                  'leg-dependence estimate exist, no NFL strategy may be ranked or rewarded.')
    body += metrics([
        ('Verified NFL rows', NFL['verified_rows']['total'], 'Official, re-derived', 'data'),
        ('Originated games', len(NFL['games']), 'Model only', 'lab'),
        ('Gates passing', 2, 'Of ten; one partial, one open', 'validation'),
        ('Qualified strategies', 0, 'Of eight candidates', 'leaderboard'),
    ])
    body += section('Findings', table(
        'nfl-exec-findings', 'Executive findings',
        [('Finding', lambda r: rich(r['headline'], r['id'])), ('Detail', 'detail'),
         ('Evidence class', lambda r: badge(r['state'], r['kind']))],
        findings, note='A row marked Derived is a calculation over the snapshot, not an external fact. '
                       'A row marked Blocked is missing an input, not a negative result.'))
    body += '<div class="grid-2"><div class="panel body-text"><h3>The decision that is ready</h3>' \
            '<p>Publish this as a non-commercial research note with every blank visible.</p>' \
            + lines(DECISIONS["decision_frame"]["what_can_be_decided_today"]) + \
            '</div><div class="panel body-text"><h3>The decisions that are not ready</h3>' \
            + lines(DECISIONS["decision_frame"]["what_cannot_be_decided_today"]) + '</div></div>'
    body += section('Four gaps blocking any reward decision', table(
        'nfl-exec-blockers', 'Blocking gaps',
        [('Gap', lambda r: rich(r['question'], r['id'])), ('Why it blocks', 'why_it_matters'),
         ('Proposed fix', 'suggestion')],
        [m for m in DECISIONS["missing_information"] if m["id"] in DECISIONS["blocking_before_any_reward"]],
        note='These are data gaps with named fixes, not disagreements about method.'))
    body += '<div class="download-list">' + ''.join([
        '<a class="button" href="nfl-decisions.html">Full decision brief →</a>',
        '<a class="button" href="nfl-suggestions.html">Suggestions to review →</a>',
        '<a class="button" href="research/nfl/results.json">Reproducible results</a>',
        '<a class="button" href="research/nfl/receipts.json">Source receipts</a>',
        '<a class="button" href="nfl-review.html">Flagged for review</a>',
    ]) + '</div>'
    return body
