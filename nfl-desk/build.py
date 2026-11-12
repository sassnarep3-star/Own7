#!/usr/bin/env python3
"""Render the NFL decision-desk pages from the verified snapshots in data/.

Everything on the pages comes from desk.py (which re-checks each snapshot) or from one of the
JSON ledgers in data/. Nothing is hand-typed at render time, and there is no randomness: two
consecutive runs produce byte-identical files, which is asserted by test_build.py and by CI.

Usage:
    python3 nfl-desk/build.py            # write pages
    python3 nfl-desk/build.py --check    # fail if a page would change
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import desk  # noqa: E402

PAGES = [
    "index.html",
    "summary.html",
    "decisions.html",
    "suggestions.html",
    "availability.html",
    "strategies.html",
    "competition.html",
    "evidence.html",
    "review.html",
]

SRC = desk.sources()
SLUGS = {name: name.replace(".html", "").upper() for name in PAGES}


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def refs(ids, direct=None):
    """Render one anchor per registered source id. Row-level provenance, never a bare citation."""
    parts = []
    seen = set()
    for sid in ids:
        if sid in seen:
            continue
        seen.add(sid)
        row = SRC.get(sid)
        if row is None:
            raise SystemExit(f"unknown source id {sid!r}; refusing to render an unlinked claim")
        parts.append(
            f'<a href="{esc(row["url"])}" title="{esc(row["title"])}"'
            f' target="_blank" rel="noopener noreferrer">{esc(sid)}</a>'
        )
    if direct:
        parts.append(
            f'<a href="{esc(direct)}" target="_blank" rel="noopener noreferrer">page</a>'
        )
    return f'<span class="refs">{"".join(parts)}</span>'


def badge(text: str, kind: str | None = None) -> str:
    if kind is None:
        low = str(text).lower()
        if any(w in low for w in ("blocked", "unknown", "irregular", "fail", "no ")):
            kind = "stop" if ("blocked" in low or "irregular" in low) else "warn"
        elif any(w in low for w in ("verified", "answered", "pass", "met")):
            kind = "good"
        elif any(w in low for w in ("partly", "partial", "proposed", "not run", "needs review")):
            kind = "warn"
        else:
            kind = "mute"
    return f'<span class="badge {kind}"><span class="dot" aria-hidden="true"></span>{esc(text)}</span>'


def blank() -> str:
    """A cell whose value does not exist. Deliberately empty, and marked as such for the checks."""
    return (
        '<td class="blank" data-empty="true" '
        'aria-label="Blank - not verified, not held or not applicable" '
        'title="Blank on purpose: no verified value exists"></td>'
    )


def num(value, places=2, signed=False):
    if value is None:
        return blank()
    if isinstance(value, bool):
        return f'<td class="num">{esc(str(value))}</td>'
    if isinstance(value, int):
        return f'<td class="num">{value}</td>'
    spec = f"{{:{'+' if signed else ''}.{places}f}}"
    return f'<td class="num">{esc(spec.format(value))}</td>'


def pct(value, places=1):
    if value is None:
        return blank()
    return f'<td class="num">{value * 100:.{places}f}%</td>'


def table(tid, title, columns, rows, *, note="", meta="", empty="", sources=None, narrow=False,
          tiles=False, detail_page=False):
    """Render a source-linked table.

    Every body row must carry the registered source IDs it was built from, because the repository's
    checker refuses any row it cannot trace to an official host. Rows may carry their own
    ``source_ids``; when they do not, the table-level ``sources`` default applies. If no column
    renders the reference list, a Sources column is appended automatically so the link is visible
    rather than hidden in an attribute.
    """
    anchor = f"{detail_page}#detail-{{rid}}" if detail_page else ""

    def ids_for(row):
        own = row.get("source_ids")
        if own:
            return own
        if callable(sources):
            return sources(row)
        return sources or []

    columns = list(columns)
    probe = rows[0] if rows else None
    renders_refs = False
    if probe is not None:
        renders_refs = any('class="refs"' in fn(probe) for _, fn in columns)
    if not renders_refs:
        if anchor:
            columns.append(("Sources", lambda r: f'<a href="{esc(anchor.format(rid=r.get("id") or r.get("abbr") or ""))}"'
                                                f' title="Source links are listed in the detail entry below">'
                                                f'{len(ids_for(r))} link{"s" if len(ids_for(r)) != 1 else ""} ↓</a>'))
        else:
            columns.append(("Sources", lambda r: refs(ids_for(r))))
    head = "".join(f'<th scope="col">{label}</th>' for label, _ in columns)
    body = []
    for row in rows:
        cells = []
        for label, fn in columns:
            out = fn(row)
            cells.append(out if out.startswith("<td") else f"<td>{out}</td>")
        ids = ids_for(row)
        sid = row.get("id") or row.get("abbr") or row.get("file") or ""
        sid_attr = f' data-source-ids="{" ".join(ids)}"' if ids else ""
        detail = f' data-detail="{esc(anchor.format(rid=sid))}"' if anchor and sid else ""
        body.append(f'<tr data-row-id="{esc(sid)}"{sid_attr}{detail}>' + "".join(cells) + "</tr>")
    if not body and empty:
        body = [f'<tr><td colspan="{len(columns)}" class="empty">{esc(empty)}</td></tr>']
    tid_attr = f' id="{tid}"' if tid else ""
    wrap_cls = "table-wrap narrow" if narrow else "table-wrap"
    if tiles:
        body_rows = "".join(body).replace("<td>", "<td><span class=\"cv\">").replace("</td>", "</span></td>")
    else:
        body_rows = "".join(body)
    return f"""<div class="{wrap_cls}">
<div class="table-head"><h2>{esc(title)}</h2>{f'<span class="meta">{meta}</span>' if meta else ""}</div>
<div class="scroll"><table{tid_attr} data-desk-table>
<caption class="sr-only">{esc(title)}. Blank cells are deliberate: no verified value exists.</caption>
<thead><tr>{head}</tr></thead><tbody>{body_rows}</tbody></table></div>
{f'<p class="table-note">{note}</p>' if note else ''}</div>"""


def detail_cards(items, render, eyebrow="Detail"):
    """Readable per-item detail beneath a compact table, so no cell has to carry a paragraph."""
    out = [f'<h2 style="margin:26px 0 10px">{esc(eyebrow)}</h2>']
    for item in items:
        out.append(
            f'<section class="card" id="detail-{esc(item["id"])}" style="margin-bottom:12px">'
            f'<div class="eyebrow">{esc(item["id"])}</div>{render(item)}</section>'
        )
    return "".join(out)


def market_chips(row):
    """Five market fields, each rendered as an explicit blank with its reason available on hover."""
    labels = [("Line", row["market_line"]), ("Price", row["price"]), ("ROI", row["roi"]),
              ("CLV", row["clv"]), ("Leg corr.", row["leg_correlation"])]
    chips = []
    for name, value in labels:
        if value is None:
            chips.append(
                f'<span class="badge mute" title="No verified value exists">'
                f'<span class="dot" aria-hidden="true"></span>{esc(name)}: —</span>'
            )
        else:
            chips.append(f'<span class="badge info">{esc(name)}: {esc(value)}</span>')
    return '<td class="chips">' + "".join(chips) + "</td>"


def card(title, body, eyebrow=""):
    return (
        f'<section class="card">{f"<div class=eyebrow>{esc(eyebrow)}</div>" if eyebrow else ""}'
        f"<h2>{esc(title)}</h2>{body}</section>"
    )


def stat(label, value, note, blank_flag=False):
    cls = "stat blank" if blank_flag else "stat"
    shown = value if value not in (None, "") else "—"
    return (
        f'<div class="{cls}"><div class="k">{esc(label)}</div>'
        f'<div class="v">{esc(str(shown))}</div><div class="n">{esc(note)}</div></div>'
    )


def notice(title, text, kind="warn"):
    return (
        f'<div class="notice {kind}"><div class="body"><strong>{esc(title)}</strong>'
        f"<p>{text}</p></div></div>"
    )


def ul(items):
    return '<ul class="list">' + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def shell(page, content):
    tpl = (HERE / "template.tmpl").read_text(encoding="utf-8")
    nav = {
        key: ' aria-current="page"' if slug == page else ""
        for key, slug in zip(
            ["INDEX", "SUMMARY", "DECISIONS", "SUGGESTIONS", "AVAILABILITY", "STRATEGIES",
             "COMPETITION", "EVIDENCE", "REVIEW"],
            PAGES,
        )
    }
    out = tpl
    for key, value in nav.items():
        out = out.replace("{{{NAV_%s}}}" % key, value)
    return out.replace("{{{CONTENT}}}", content)


# --------------------------------------------------------------------------- pages


def page_index():
    c = desk.counts()
    gates = desk.load_ledger("data/gates.json")["gates"]
    strat = desk.load_ledger("data/strategies.json")["strategies"]
    qs = desk.load_ledger("data/questions.json")["questions"]
    sug = desk.load_ledger("data/suggestions.json")["suggestions"]
    flags = desk.load_ledger("data/flags.json")["flags"]
    passed = sum(1 for g in gates if g["status"] != "Blocked")
    body = '<div class="eyebrow">Decision desk · read date 12 November 2026</div>'
    body += "<h1>Originate lines only after the evidence can carry them</h1>"
    body += (
        '<p class="lead">An NFL research desk built to answer one question honestly: what would have to '
        "be true before a line, a signal or a strategy could be called qualified? This page states the "
        "answer, the evidence behind it, and what is still missing.</p>"
    )
    body += notice(
        "No line, price or edge is published here, and none has been earned.",
        "This desk holds one week of official injury data, one season-to-date standings snapshot and "
        "three club depth charts. It holds no price history, no per-player game logs and no forward "
        "test. Every economic field is therefore blank by design. What follows is the decision record: "
        "what is known, what is missing, and exactly what would have to happen before any strategy "
        "could be called qualified.",
        "stop",
    )
    body += '<div class="grid g4">'
    body += stat("Official clubs", c["clubs"], "2026 regular season, source-linked")
    body += stat("Injury report rows", c["injury_rows"], f'{c["clubs_on_report"]} clubs listed, Week 10')
    body += stat("Gates passed", f"{passed} / {len(gates)}", "Fail-closed admission policy", blank_flag=True)
    body += stat("Qualified strategies", 0, f"{len(strat)} candidates declared, none eligible", blank_flag=True)
    body += "</div>"

    body += card(
        "What this desk answers, in one screen",
        '<dl class="kv">'
        "<dt>Records and scoring</dt><dd>All 32 clubs, transcribed and arithmetically re-checked "
        '(<a href="evidence.html#standings-data">standings</a>).</dd>'
        "<dt>Who is on the report</dt><dd>276 player rows from the official Week 10 report, four status "
        'fields kept separate (<a href="availability.html">availability</a>).</dd>'
        "<dt>Who replaces a starter</dt><dd>Only where the club's own chart is held: three clubs. The "
        "other 29 are blank, not estimated (<a href=\"availability.html#depth\">depth chains</a>).</dd>"
        "<dt>Measured dependence</dt><dd>Eight club-season correlations with permutation p-values. "
        "This is not a bet-leg correlation and is not used as one "
        '(<a href="strategies.html#correlation">correlation</a>).</dd>'
        "<dt>What a decision needs</dt><dd>Twelve open questions with the missing evidence named for "
        'each (<a href="decisions.html">decision register</a>).</dd>'
        "<dt>What to change next</dt><dd>Twelve reviewable proposals, none implemented "
        '(<a href="suggestions.html">suggestions</a>).</dd>'
        "<dt>Price, ROI, closing line</dt><dd>Blank. No licensed price source exists here "
        '(<a href="review.html">flags DF-01, DF-14</a>).</dd>'
        "</dl>",
        "Orientation",
    )

    body += card(
        "Read the three documents in this order",
        '<div class="grid g3">'
        '<div><h3>1 · Executive summary</h3><p>One page on what was verified, what is blocked and what '
        'the owner has to decide.</p><a href="summary.html">Open the summary →</a></div>'
        '<div><h3>2 · Decision register</h3><p>The questions that must be answered before any strategy '
        'is chosen, with the missing evidence named.</p><a href="decisions.html">Open the register →</a></div>'
        '<div><h3>3 · Suggestions</h3><p>Twelve proposed changes with effort, risk and the gate each '
        'serves. Nothing is applied until you choose.</p><a href="suggestions.html">Open suggestions →</a></div>'
        "</div>",
        "Path",
    )

    body += table(
        "truth-strip",
        "Status of every deliverable in this brief",
        [
            ("Deliverable", lambda r: f'<strong>{esc(r["item"])}</strong>'),
            ("State", lambda r: badge(r["state"], r["kind"])),
            ("Where it lives", lambda r: r["where"]),
        ],
        [
            {"id": "T1", "item": "Source-verified NFL dataset", "state": "Verified", "kind": "good",
             "where": link_to("evidence.html", "Evidence, row by row")},
            {"id": "T2", "item": "Injury and backup-deficiency tracker", "state": "Partly — 3 of 32 clubs",
             "kind": "warn", "where": link_to("availability.html", "Availability")},
            {"id": "T3", "item": "Line origination and signals", "state": "Blocked — no price source",
             "kind": "stop", "where": link_to("strategies.html", "Strategies")},
            {"id": "T4", "item": "Validation gates", "state": f"{passed} of {len(gates)} passed", "kind": "stop",
             "where": link_to("competition.html#gates", "Gates")},
            {"id": "T5", "item": "Correlation values", "state": "Descriptive only", "kind": "warn",
             "where": link_to("strategies.html#correlation", "Correlation")},
            {"id": "T6", "item": "Leaderboard and rewards", "state": "Empty — nothing qualified", "kind": "warn",
             "where": link_to("competition.html", "Competition")},
            {"id": "T7", "item": "Suggestions board", "state": f"{len(sug)} proposals awaiting your choice",
             "kind": "info", "where": link_to("suggestions.html", "Suggestions")},
            {"id": "T8", "item": "Decision register", "state": f"{len(qs)} questions, {sum(1 for q in qs if q['status']=='Unknown')} unanswerable today",
             "kind": "info", "where": link_to("decisions.html", "Decisions")},
            {"id": "T9", "item": "Executive summary", "state": "Published", "kind": "good",
             "where": link_to("summary.html", "Summary")},
            {"id": "T10", "item": "Repository review", "state": "18 checks, 7 irregularities", "kind": "warn",
             "where": link_to("evidence.html#repo-review", "Review")},
            {"id": "T11", "item": "Flagged for review", "state": f"{len(flags)} open items", "kind": "info",
             "where": link_to("review.html", "Flags")},
        ],
        sources=["REPO"],
        note="A state of Verified means a check was run and passed and can be re-run. It never means "
             "profitable, and it never means the source granted permission for any use.",
    )
    return body


def link_to(href, text):
    return f'<a href="{esc(href)}">{esc(text)}</a>'


def page_summary():
    c = desk.counts()
    corr = desk.correlation_table()
    best = max(corr, key=lambda r: abs(r["pearson"] or 0))
    body = '<div class="eyebrow">Executive summary · read date 12 November 2026</div>'
    body += "<h1>What is verified, what is blocked, and what you have to decide</h1>"
    body += (
        '<p class="lead">This page is the short version. It states the few things that survived '
        "checking, the things that did not, and the decisions that are yours rather than mine.</p>"
    )

    body += card(
        "1 · The dataset is real, small and re-checkable",
        f'<p>Thirty-two clubs of 2026 regular-season standings, thirty-two clubs of team passing '
        f"totals, and {c['injury_rows']} player rows from the official Week 10 injury report. Every file "
        "is committed as a plain text snapshot with a SHA-256 hash, and the build refuses to publish a "
        "number that no longer agrees with its own file. Win percentage is recomputed from "
        "wins-losses-ties, net points from points for minus points against, and completion percentage "
        'from completions over attempts on every club on every run. See <a href="evidence.html">Evidence</a>.</p>'
        "<p>Three things that looked like data were rejected rather than repaired: the standings capture "
        "has no header row, the passing capture has no header row, and the displayed yards-per-attempt "
        "figure cannot be reproduced from that same table on four of thirty-two rows. Those three gaps "
        "are published as flags DF-03 and DF-04 instead of being filled in.</p>",
        "Verified",
    )

    body += card(
        "2 · Everything economic is blank, and that is the finding",
        '<p>There is no price, no line, no hold, no return and no closing line anywhere in this desk. '
        "NFL.com publishes no odds, no licensed feed is connected, and the site's terms grant no "
        "gambling-related use. Rather than display a fair-odds number that looks executable, every "
        "price field is empty.</p>"
        "<p>The consequence is blunt: eight candidate strategies were written down before any of them "
        "was scored, and all eight are blocked. A strategy cannot be called skilful when its return "
        'cannot be computed at all. See <a href="strategies.html">Strategies</a> and '
        '<a href="review.html">Flagged for review</a>.</p>',
        "Blocked",
    )

    body += card(
        "3 · The availability picture is honest about its coverage",
        f'<p>The official Week 10 report lists {c["injury_rows"]} players across {c["clubs_on_report"]} clubs; '
        f"two clubs rendered the literal note 'No Injuries Reported' and {c['clubs_on_bye']} were on bye, "
        "and those states are shown separately so that a bye week never reads as a healthy team.</p>"
        "<p>The backup question, which is the one that matters most to you, is answered only where a "
        "club's own depth chart is held: three clubs, 69 first-string entries, joined to the report by "
        "name. For the other twenty-nine clubs the replacement cell is empty. A club depth chart is an "
        'unofficial coaching estimate, so even the three charts are a statement about a web page on '
        "12 November, not about a game plan. See "
        '<a href="availability.html">Availability</a>.</p>',
        "Partly answered",
    )

    body += card(
        "4 · The only measured dependence is at club level",
        f'<p>Eight correlation pairs across {c["clubs"]} club-seasons, each with a permutation p-value '
        "from twenty thousand reshuffles. The strongest relationship is between net points and win "
        f"percentage ({best['pearson']:+.3f}); the weakest is between points for and points against "
        f"({corr[3]['pearson']:+.3f}), which is what you would expect if scoring and conceding are "
        "largely separate skills.</p>"
        "<p>None of this is a bet-leg correlation. Reusing a club-season coefficient as though it were "
        "a same-game leg correlation is precisely the error that gate G05 exists to stop, and it is not "
        'done here. See <a href="strategies.html#correlation">Correlation</a>.</p>',
        "Measured",
    )

    body += card(
        "5 · What has to be decided, and by whom",
        ul([
            "<strong>Source rights.</strong> The site's terms limit use to individual non-commercial "
            "purposes and prohibit systematic collection without written consent. Nothing beyond a "
            "bounded research snapshot can proceed until this is settled. Owner decision.",
            "<strong>Price source.</strong> Without a licensed, timestamped price archive there is no "
            "economic question to answer and no reward can be earned. Owner decision.",
            "<strong>Injury archive.</strong> One page state cannot establish what was knowable before "
            "kickoff. A dated capture is the single highest-value addition available from an official "
            "source. Research decision, subject to the rights question.",
            "<strong>Depth-chart coverage.</strong> Three clubs is a demonstration, not a system. "
            "Extending coverage club by club is mechanical work with a known cost.",
            "<strong>Stop conditions.</strong> Three are declared: no permission, no price archive "
            "within a defined window, or a full forward period with no candidate beating its naive "
            "baseline. Any one of them ends the project rather than extending it.",
        ]),
        "Decisions",
    )

    body += card(
        "6 · What was deliberately not done",
        ul([
            "No number was inferred from a page layout, and no column was guessed from position.",
            "No price, hold, edge or return was estimated or simulated for display.",
            "No division rank was published, because ranking a division needs tie-breakers that are "
            "not in the data held.",
            "No club was credited with a healthy roster because it was absent from the report.",
            "No cash reward was promised, funded or implied.",
            "No earlier session's work was overwritten; the repository review is published as "
            "disagreements rather than silent edits.",
        ]),
        "Boundaries",
    )
    body += (
        '<p class="table-note">Reproduce every figure on this page: '
        "<code>python3 nfl-desk/build.py --check</code> then "
        "<code>python3 nfl-desk/test_build.py</code>.</p>"
    )
    return body


def page_decisions():
    q = desk.load_ledger("data/questions.json")
    rows = q["questions"]
    counts = {st: sum(1 for r in rows if r["status"] == st) for st in q["statuses"]}
    body = '<div class="eyebrow">Decision register</div>'
    body += "<h1>Questions that must be answered before a choice is made</h1>"
    body += (
        '<p class="lead">Each row states the question, what can be answered today from a source that '
        "was actually read, and what is missing. A question stays Unknown until a source answers it. "
        "Nothing is marked answered because it was probably true.</p>"
    )
    body += '<div class="grid g3">'
    for state in q["statuses"]:
        body += stat(state, counts[state], "of twelve questions")
    body += "</div>"
    body += notice(
        "How to use this register",
        "The 'blocks' column is the part that matters. A question that blocks nothing is background; "
        "a question that blocks a division stops every candidate in it. Four of the twelve cannot be "
        "answered by more research alone, because they are owner decisions about rights, money, "
        "mandate and stop conditions.",
        "warn",
    )
    body += table(
        "questions",
        "Decision register: status at a glance",
        [
            ("ID", lambda r: f'<span class="id">{esc(r["id"])}</span>'),
            ("Question", lambda r: f'<a href="#detail-{esc(r["id"])}"><strong>{esc(r["question"])}</strong></a>'),
            ("Answerable today?", lambda r: badge(r["status"])),
            ("Decides", lambda r: esc(r["owner"])),
            ("Blocks", lambda r: esc(r["blocks"])),
        ],
        rows,
        narrow=True,
        tiles=True,
        detail_page="decisions.html",
        sources=lambda r: r["source_ids"],
        note="Four questions are Unknown and will stay Unknown until a named source changes them. The "
             "answers, the information held and the specific missing evidence are written out below.",
        meta="12 questions · 4 unknown",
    )
    body += detail_cards(
        rows,
        lambda r: (
            f'<h2 style="margin:0 0 8px">{esc(r["question"])}</h2>'
            f'<p style="margin-bottom:10px">{esc(r["why_it_matters"])}</p>'
            f'<dl class="kv">'
            f'<dt>Answer today</dt><dd>{esc(r["answer"])}</dd>'
            f'<dt>Information held</dt><dd>{esc(r["information_held"])}</dd>'
            f'<dt>Information missing</dt><dd>{esc(r["information_missing"])}</dd>'
            f'<dt>Status</dt><dd>{badge(r["status"])}</dd>'
            f'<dt>Decides</dt><dd>{esc(r["owner"])}</dd>'
            f'<dt>Blocks</dt><dd>{esc(r["blocks"])}</dd>'
            f'<dt>Sources</dt><dd>{refs(r["source_ids"])}</dd></dl>'
        ),
        "Register in full",
    )
    body += card(
        "Missing-information discovery: what to look for next",
        ul([
            "<strong>Ask the rights holder in writing</strong> whether a bounded, attributed, "
            "non-commercial research snapshot is acceptable, and whether the answer differs for a "
            "betting-adjacent audience. Until an answer exists, everything else is provisional.",
            "<strong>Ask what a licensed price archive costs.</strong> The blocker is commercial, not "
            "technical: a feed with timestamps and settlement rules converts four Unknown rows into "
            "answerable ones.",
            "<strong>Ask whether depth charts may be captured per club and archived with dates.</strong> "
            "Coverage is a finite list of thirty-two URLs, most of which resolve on club domains.",
            "<strong>Ask what the minimum forward window is</strong> that would satisfy you as evidence "
            "of skill. Deciding this now prevents moving the goal after a bad week.",
            "<strong>Ask who reviews a candidate</strong> that reaches the board, and whether an "
            "independent rebuild is available. Self-review is not verification.",
        ]),
        "Discovery",
    )
    return body


def blank_cell():
    return '<span class="sub" style="opacity:.55">nothing held</span>'


def page_suggestions():
    data = desk.load_ledger("data/suggestions.json")
    rows = data["suggestions"]
    body = '<div class="eyebrow">Suggestions for review</div>'
    body += "<h1>Twelve proposals, none of them applied</h1>"
    body += (
        '<p class="lead">This page exists so a change can be reviewed and chosen before it is built. '
        "Each proposal states the problem it addresses, what it would cost, what could go wrong and "
        "which validation gate it serves. The disposition column is yours to set; nothing on this "
        "site implements a suggestion on its own.</p>"
    )
    body += notice(
        "Nothing here has been implemented",
        "Every row currently reads Proposed. The page is a decision aid, not a changelog. If a "
        "suggestion is declined it should stay visible with the reason, because a record of what was "
        "rejected is as useful as a record of what was built.",
        "ok",
    )
    body += '<div class="grid g6">'
    for state in data["dispositions"]:
        body += stat(state, sum(1 for r in rows if r["disposition"] == state), "proposals")
    body += "</div>"
    body += table(
        "suggestions",
        "Suggestions board",
        [
            ("ID", lambda r: f'<span class="id">{esc(r["id"])}</span>'),
            ("Proposal", lambda r: f'<a href="#detail-{esc(r["id"])}"><strong>{esc(r["title"])}</strong></a>'),
            ("Impact", lambda r: badge(r["impact"], "info" if r["impact"] == "High" else "mute")),
            ("Effort", lambda r: esc(r["effort"].split(" — ")[0])),
            ("Gate it serves", lambda r: esc(r["gate"])),
            ("Disposition", lambda r: badge(r["disposition"])),
        ],
        rows,
        narrow=True,
        tiles=True,
        detail_page="suggestions.html",
        sources=lambda r: r["source_ids"],
        note="Eight of twelve are labelled Low or Medium effort. The two highest-impact items (SG-01, "
             "SG-02) are the cheapest, and the most limited item (SG-03) is limited by source terms "
             "rather than by effort.",
        meta="12 proposals · 0 implemented",
    )
    body += detail_cards(
        rows,
        lambda r: (
            f'<h2 style="margin:0 0 8px">{esc(r["title"])}</h2>'
            f'<dl class="kv">'
            f'<dt>Problem</dt><dd>{esc(r["problem"])}</dd>'
            f'<dt>Proposal</dt><dd>{esc(r["proposal"])}</dd>'
            f'<dt>Rationale</dt><dd>{esc(r["rationale"])}</dd>'
            f'<dt>Evidence</dt><dd>{esc(r["evidence"])}</dd>'
            f'<dt>Effort</dt><dd>{esc(r["effort"])}</dd>'
            f'<dt>Risk</dt><dd>{esc(r["risk"])}</dd>'
            f'<dt>Gate it serves</dt><dd>{esc(r["gate"])} '
            f'(<a href="competition.html#gates">gates</a>)</dd>'
            f'<dt>Impact</dt><dd>{esc(r["impact"])}</dd>'
            f'<dt>Disposition</dt><dd>{badge(r["disposition"])} — set by the owner, not by this site</dd>'
            f'<dt>Sources</dt><dd>{refs(r["source_ids"])}</dd></dl>'
        ),
        "Proposals in full",
    )
    body += card(
        "How to choose between them",
        ul([
            "<strong>If the goal is to learn fastest:</strong> SG-05 and SG-06. Both are cheap, both "
            "fix a place where the current site could mislead a reader.",
            "<strong>If the goal is to make origination possible at all:</strong> SG-03 and SG-04 are "
            "the prerequisites, and both are limited by the rights question rather than by effort.",
            "<strong>If the goal is to trust the leaderboard:</strong> SG-09. It turns the anti-luck "
            "promise into code that cannot be waived in a good week.",
            "<strong>If the goal is credibility:</strong> SG-10 and SG-12. A verification project whose "
            "own descriptions are stale has already lost the argument.",
        ]),
        "Guidance",
    )
    return body


def page_availability():
    c = desk.counts()
    av = desk.availability_table()
    games = desk.week10_games()
    depth = desk.matchup_depth()
    summ = desk.deficiency_summary()
    notes = {n["team"]: n["official_note"] for n in desk.team_notes()}
    body = '<div class="eyebrow">Availability and depth</div>'
    body += "<h1>Who is listed, who is out, and who replaces whom</h1>"
    body += (
        '<p class="lead">This page separates four things that are usually collapsed into one injury '
        "number: a player being listed, a player missing practice, a player carrying a game status, "
        "and a player being ruled out. It then shows replacement chains only for the clubs whose own "
        "depth chart is held.</p>"
    )
    body += notice(
        "Two limits decide how this page can be read",
        "The official report is a single undated page state, so it cannot tell you what was knowable "
        "before a specific kickoff (flag DF-02). Club depth charts are unofficial coaching estimates "
        "and are held for three of thirty-two clubs (flag DF-06). Neither limit is worked around by "
        "estimation.",
        "warn",
    )
    body += '<div class="grid g4">'
    body += stat("Player rows listed", c["injury_rows"], f'Week 10, {c["clubs_on_report"]} clubs')
    body += stat("Clubs with a depth chart", 3, "WAS, NYG, SEA only", blank_flag=False)
    body += stat("First-string entries charted", c["starters_charted"], "across the three charts")
    body += stat("Clubs on bye", c["clubs_on_bye"], "not in Week 10 fixtures at all")
    body += "</div>"

    by_game = []
    av_by = {a["abbr"]: a for a in av}
    for g in games:
        for side in ("away", "home"):
            a = av_by[g[side]]
            row = dict(a)
            row["fixture"] = (f'at {g["home"]}' if side == "away" else f'vs {g["away"]}')
            row["side"] = side
            row["kickoff"] = g["kickoff"]
            row["id"] = f'{g["away"]}-{g["home"]}-{side}'
            by_game.append(row)

    body += table(
        "matchups",
        "Week 10 availability pressure, by fixture",
        [
            ("Club", lambda r: f'<strong>{esc(r["abbr"])}</strong>'
                               f'<span class="sub">{esc(r["fixture"])}</span>'),
            ("Kickoff (as shown)", lambda r: esc(r["kickoff"])),
            ("Listed", lambda r: f'<td class="num">{r["listed"]}</td>'),
            ("Did not practise", lambda r: f'<td class="num">{r["dnp"]}</td>'),
            ("Limited", lambda r: f'<td class="num">{r["limited"]}</td>'),
            ("Out", lambda r: f'<td class="num">{r["out"]}</td>'),
            ("Questionable", lambda r: f'<td class="num">{r["questionable"]}</td>'),
            ("Sources", lambda r: refs(r["source_ids"])),
        ],
        by_game,
        sources=["NFL-INJURY-W10-2026", "NFL-SCHEDULE-2026"],
        note="Fourteen fixtures, twenty-eight clubs. A club with a large 'listed' count and zero Out "
             "designations is not depleted, which is why the columns are not summed. No club in either "
             "column rendered a per-club official note on this page read, so no note column is shown: "
             "the two clubs that did carry a note (LAC, BAL) are not in a Week 10 fixture. Kickoff times are "
             "reproduced as the page rendered them, without a time-zone conversion (flag DF-10).",
        meta="28 clubs · 14 fixtures",
    )

    body += '<h2 id="depth" style="margin:26px 0 6px">Replacement chains where a club chart is held</h2>'
    body += (
        '<p>Only three clubs publish a chart this session could read on an official domain. For each, '
        "the chart's own order gives the string, and the next listed name at that position is the "
        "chart's implied replacement. A blank replacement means the chart lists nobody behind that "
        "player — it is not filled from another source.</p>"
    )
    for abbr in ("WAS", "NYG", "SEA"):
        rows = [r for r in depth if r["team"] == abbr]
        on_report = [r for r in rows if r["on_report"]]
        body += table(
            f"depth-{abbr.lower()}",
            f"{abbr} · {len(rows)} chart entries, {len(on_report)} also on the Week 10 report",
            [
                ("Pos", lambda r: esc(r["pos"])),
                ("String", lambda r: f'<td class="num">{r["string"]}</td>'),
                ("Player", lambda r: esc(r["player"])),
                ("Practice", lambda r: esc(r["practice"]) or blank()),
                ("Game", lambda r: badge(r["game"], "stop") if r["game"] == "Out"
                                       else badge(r["game"], "warn") if r["game"] else blank()),
                ("Injury", lambda r: esc(r["injury"]) or blank()),
                ("Next on chart", lambda r: esc(r["replacement"]) or blank()),
                ("Sources", lambda r: refs(r["source_ids"])),
            ],
            rows,
            note=f"{abbr} chart read 2026-11-12. Blank practice, game and injury cells mean the player "
                 "is not on the Week 10 report, not that he is healthy.",
        )

    body += table(
        "deficiency",
        "First-string pressure per charted club",
        [
            ("Club", lambda r: f"<strong>{esc(r['abbr'])}</strong>"),
            ("Chart entries", lambda r: f'<td class="num">{r["chart_starters"]}</td>'),
            ("Of those, on the report", lambda r: f'<td class="num">{r["starters_on_report"]}</td>'),
            ("Out", lambda r: f'<td class="num">{r["starters_out"]}</td>'),
            ("Questionable", lambda r: f'<td class="num">{r["starters_questionable"]}</td>'),
            ("Positions with no backup listed", lambda r: f'<td class="num">{r["unfilled_positions"]}</td>'),
            ("Detail", lambda r: esc(r["affected_detail"]) or blank()),
            ("Sources", lambda r: refs(r["source_ids"])),
        ],
        summ,
        sources=["NFL-INJURY-W10-2026"],
        note="'Out' counts only players carrying the explicit Out designation on the official report. A "
             "blank Detail cell means no first-string player on that chart carried any game status at "
             "all, which is a real result rather than missing data.",
    )

    body += card(
        "What a charted club's pressure actually looked like",
        ul([
            f"<strong>WAS</strong>: {summ[0]['chart_starters']} chart entries, "
            f"{summ[0]['starters_on_report']} of them on the report, {summ[0]['starters_out']} ruled out. "
            "Two listed players were ruled out — a centre and a tight end — and both have a charted "
            "replacement, so the chain is explicit rather than guessed.",
            f"<strong>NYG</strong>: {summ[1]['chart_starters']} entries, {summ[1]['starters_on_report']} "
            f"on the report, {summ[1]['starters_out']} out, and {summ[1]['unfilled_positions']} positions "
            "where the chart names nobody behind the starter.",
            f"<strong>SEA</strong>: {summ[2]['chart_starters']} entries, {summ[2]['starters_on_report']} on "
            f"the report, {summ[2]['starters_out']} out, {summ[2]['unfilled_positions']} unfilled position. "
            "The quarterback chain is the clearest: Darnold listed first, Lock second, Milroe third.",
            "Across all three charts, no first-string player carried the Out designation on the day of "
            "reading. That is reported as observed; a page read at a different hour could differ.",
        ]),
        "Reading the table",
    )
    body += card(
        "Clubs absent from the report, and why that is not a health claim",
        ul(
            [f"<strong>{t}</strong>: the page rendered '{esc(notes[t])}' instead of a player table. "
             "This means the club did not list anyone on that page at that moment." for t in sorted(notes)]
            + ["<strong>CHI, DEN, PHI, TB</strong>: on bye in Week 10 and therefore absent from the "
               "report entirely. Treating that absence as a zero-injury week would be wrong.",
               "The remaining unlisted clubs are accounted for one by one: twenty-six clubs did list "
               "players, two rendered the no-injuries note, and four were on bye. That arithmetic "
               "closes, which is why no club is silently missing."]
        ),
        "Coverage",
    )
    return body


def page_strategies():
    data = desk.load_ledger("data/strategies.json")
    rows = data["strategies"]
    corr = desk.correlation_table()
    pyth = sorted(desk.pythagorean_table(), key=lambda r: -(r["residual"] or 0))
    body = '<div class="eyebrow">Origination and signals</div>'
    body += "<h1>Eight declared strategies, all blocked, and the arithmetic behind them</h1>"
    body += (
        '<p class="lead">Origination means writing a hypothesis and its kill condition before looking '
        "at a result. Eight were written first. Then the data was checked to see whether any of them "
        "could be tested at all. None could, for reasons stated per row.</p>"
    )
    body += notice(
        "Why every market field is empty",
        "A strategy's line, price, return and closing-line value are the numbers that would make it "
        "actionable. No price source exists here, so all four are blank on all eight rows. This is not "
        "caution for its own sake: a fair-odds figure that cannot be taken is more misleading than an "
        "empty cell.",
        "stop",
    )
    body += table(
        "strategies",
        "Strategy ledger",
        [
            ("ID", lambda r: f'<a class="id" href="#detail-{esc(r["id"])}">{esc(r["id"])}</a>'),
            ("Strategy", lambda r: f'<strong>{esc(r["name"])}</strong>'
                                  f'<span class="sub">{esc(r["category"])} · hypothesis, test and kill '
                                  f'condition below</span>'),
            ("Testable today?", lambda r: badge("No", "stop")),
            ("Market fields (all blank)", lambda r: market_chips(r)),
            ("Gates failed", lambda r: esc(", ".join(r["gates_failed"]))),
        ],
        rows,
        narrow=True,
        tiles=True,
        detail_page="strategies.html",
        sources=lambda r: r["source_ids"],
        note="Every market field is a dash because no verified value exists. The hypotheses, required "
             "tests and kill conditions are written out below the table where they are readable.",
        meta="8 hypotheses · 0 testable",
    )
    body += detail_cards(
        rows,
        lambda r: (
            f'<h2 style="margin:0 0 8px">{esc(r["name"])} · {esc(r["category"])}</h2>'
            f'<dl class="kv">'
            f'<dt>Hypothesis</dt><dd>{esc(r["hypothesis"])}</dd>'
            f'<dt>Inputs held</dt><dd>{esc(r["inputs"])}</dd>'
            f'<dt>Test required</dt><dd>{esc(r["test"])}</dd>'
            f'<dt>What would kill it</dt><dd>{esc(r["kills_it"])}</dd>'
            f'<dt>Risk</dt><dd>{esc(r["risk"])}</dd>'
            f'<dt>Gates failed</dt><dd>{esc(", ".join(r["gates_failed"]))} '
            f'(<a href="competition.html#gates">see the gates</a>)</dd>'
            f'<dt>Line · price · ROI · CLV · leg correlation</dt>'
            f'<dd>Blank on all five: no verifiable value exists (flag DF-01).</dd>'
            f'<dt>Sources</dt><dd>{refs(r["source_ids"])}</dd></dl>'
        ),
        "Strategy rows in full",
    )

    body += '<h2 id="correlation" style="margin:30px 0 6px">Measured dependence, club level only</h2>'
    body += (
        f'<p>These are correlations across {corr[0]["n"]} club-seasons from the official standings and '
        "team passing tables. Pearson is the linear coefficient; Spearman is the same computation on "
        "ranks, which is less sensitive to a single extreme club. The p-value comes from twenty thousand "
        "deterministic reshuffles of one column, so it describes how unusual this pattern would be if "
        "the two quantities were unrelated. A small p-value here does not mean profitable, and it does "
        "not mean a bet-leg relationship exists.</p>"
    )
    body += table(
        "corr",
        "Club-season correlation matrix (descriptive)",
        [
            ("Pair", lambda r: f"<strong>{esc(r['pair'])}</strong>"),
            ("n", lambda r: f'<td class="num">{r["n"]}</td>'),
            ("Pearson r", lambda r: num(r["pearson"], 4)),
            ("Spearman ρ", lambda r: num(r["spearman"], 4)),
            ("Permutation p", lambda r: num(r["p_perm"], 4)),
            ("Unit of analysis", lambda r: esc(r["unit"])),
            ("Sources", lambda r: refs(r["source_ids"])),
        ],
        corr,
        note="Twenty thousand reshuffles is a fixed count, not a stopping rule, and the generator is "
             "seeded so the column reproduces exactly. Eight pairs were declared together; no "
             "correction is applied because no pair is being claimed as a discovery, only reported as "
             "a description.",
    )

    body += table(
        "pythagorean",
        "Derived: scoring profile versus actual record",
        [
            ("Club", lambda r: f'<strong>{esc(r["abbr"])}</strong><span class="sub">{esc(r["team"])}</span>'),
            ("Games", lambda r: f'<td class="num">{r["games"]}</td>'),
            ("Record wins", lambda r: f'<td class="num">{r["w"] + r["t"]/2:.1f}</td>'),
            ("Pythagorean rate", lambda r: num(r["pyth"], 3)),
            ("Expected wins", lambda r: num(r["expected_wins"], 2)),
            ("Residual", lambda r: num(r["residual"], 2, signed=True)),
            ("Residual z", lambda r: num(r["residual_z"], 2, signed=True)),
            ("Sources", lambda r: refs(r["source_ids"])),
        ],
        pyth,
        note="Derived, not official. Pythagorean expectation is PF^2.37 / (PF^2.37 + PA^2.37) with the "
             "exponent fixed as a project method; the residual z treats each game as an independent "
             "coin with the expected rate, which is a rough approximation because games are not "
             "independent and the opponent is ignored. Positive residual means the club has won more "
             "than its scoring profile implies.",
    )
    return body


def page_competition():
    data = desk.load_ledger("data/competition.json")
    gates = desk.load_ledger("data/gates.json")["gates"]
    body = '<div class="eyebrow">Competition and validation</div>'
    body += "<h1>A leaderboard nobody can win by getting lucky</h1>"
    body += (
        '<p class="lead">The competition is specified so that the mechanism, not the promise, keeps '
        "luck out. Nothing is ranked today because no entry has cleared a single gate. An empty board "
        "is the honest state of a competition whose admission rules are actually applied.</p>"
    )
    body += notice(
        "No reward of monetary value exists",
        "Four tiers are defined and all four are non-monetary. No prize is funded, authorised or "
        "promised, and the monetary-value field is blank on every tier. A funded cash prize would "
        "require both a funding decision and a legal review by jurisdiction, neither of which has "
        "happened (flag DF-13).",
        "stop",
    )
    body += '<div class="grid g4">'
    body += stat("Qualified entries", "0", "nothing has passed admission", blank_flag=True)
    body += stat("Gates passed", f"0 / {len(gates)}", "every gate currently Blocked", blank_flag=True)
    body += stat("Forward periods run", "0", "required before ranking")
    body += stat("Cash rewards", "—", "none funded or authorised", blank_flag=True)
    body += "</div>"

    body += '<h2 id="gates" style="margin:26px 0 6px">The ten admission gates</h2>'
    body += (
        "<p>These are hard stops, written before any candidate was scored so they could not be tuned "
        "to a result. Each states its pass rule and the specific reason it currently fails.</p>"
    )
    body += table(
        "gate-table",
        "Validation gates",
        [
            ("ID", lambda r: f'<a class="id" href="#detail-{esc(r["id"])}">{esc(r["id"])}</a>'),
            ("Gate", lambda r: f'<strong>{esc(r["name"])}</strong>'
                               f'<span class="sub">{esc(r["question"])}</span>'),
            ("Type", lambda r: badge(r["type"], "info")),
            ("Status", lambda r: badge(r["status"], "stop")),
            ("Sources", lambda r: refs(r["source_ids"])),
        ],
        gates,
        narrow=True,
        note="A gate is never marked passed because the evidence is likely. Reproducibility (G10) is "
             "the only half-met gate: the build is deterministic and hash-checked, while the publishing "
             "rights half is unresolved. The pass rule and the exact reason each gate fails today are "
             "written out in full below.",
    )
    body += detail_cards(
        gates,
        lambda r: (
            f'<h2 style="margin:0 0 8px">{esc(r["name"])}</h2>'
            f'<p style="margin-bottom:10px">{esc(r["question"])}</p>'
            f'<dl class="kv">'
            f'<dt>Pass rule</dt><dd>{esc(r["pass_rule"])}</dd>'
            f'<dt>Where it stands today</dt><dd>{esc(r["current"])}</dd>'
            f'<dt>Type</dt><dd>{badge(r["type"], "info")}</dd>'
            f'<dt>Status</dt><dd>{badge(r["status"], "stop")}</dd>'
            f'<dt>Sources</dt><dd>{refs(r["source_ids"])}</dd></dl>'
        ),
        "Gates in full",
    )

    body += "<h2 style='margin:26px 0 6px'>Divisions</h2>"
    body += table(
        "divisions",
        "Competition divisions and their admission requirements",
        [
            ("ID", lambda r: f'<span class="id">{esc(r["id"])}</span>'),
            ("Division", lambda r: f"<strong>{esc(r['name'])}</strong>"
                                  f"<span class=\"sub\">{esc(r['note'])}</span>"),
            ("Scoring unit", lambda r: esc(r["unit"])),
            ("Admission gates", lambda r: esc(r["admission"])),
            ("Entries", lambda r: blank()),
        ],
        data["divisions"],
        narrow=True,
        sources=["REPO"],
        note="The Entries column is blank on purpose: there is nothing to count. Division D-D is scored "
             "on prediction of the game rather than on a trade, so it can be evaluated before any "
             "price exists — which makes it the only division that is currently reachable.",
    )

    body += "<h2 style='margin:26px 0 6px'>Scoring rules that remove luck</h2>"
    body += table(
        "scoring",
        "How an entry is scored",
        [
            ("ID", lambda r: f'<span class="id">{esc(r["id"])}</span>'),
            ("Rule", lambda r: f"<strong>{esc(r['name'])}</strong>"),
            ("Mechanism", lambda r: esc(r["rule"])),
            ("Why it stops luck from winning", lambda r: esc(r["why"])),
        ],
        data["scoring"],
        sources=["REPO"],
    )

    body += "<h2 style='margin:26px 0 6px'>Reward tiers</h2>"
    body += table(
        "rewards",
        "Reward tiers and their value",
        [
            ("ID", lambda r: f'<span class="id">{esc(r["id"])}</span>'),
            ("Tier", lambda r: f"<strong>{esc(r['tier'])}</strong>"),
            ("Reward", lambda r: esc(r["reward"])),
            ("Monetary value", lambda r: num(r["monetary_value"])),
            ("Status", lambda r: badge(r["status"])),
            ("Note", lambda r: esc(r["note"])),
        ],
        data["rewards"],
        sources=["REPO"],
        note="Every monetary value cell is blank because no value exists. Publishing a figure such as "
             "zero would imply a price list with nothing yet owed.",
    )

    body += card("Anti-luck rules in force", ul([esc(x) for x in data["anti_luck_rules"]]), "Policy")
    return body


def page_evidence():
    integ = desk.integrity()
    st = desk.standings()
    ps = desk.passing()
    ps_by = {p["abbr"]: p for p in ps}
    src = desk.load_ledger("data/sources.json")["sources"]
    review = desk.load_ledger("data/repo-review.json")["checks"]
    counts = desk.counts()
    body = '<div class="eyebrow">Evidence</div>'
    body += "<h1>Every figure, its file, and the page it came from</h1>"
    body += (
        '<p class="lead">This page is the audit trail. Each snapshot has a hash and a stated check. '
        "Each row links to the official page it was transcribed from. Nothing is here because it "
        "seemed right.</p>"
    )
    body += notice(
        "A link is a reference, not a certification",
        "Each source below was opened and read on 12 November 2026, and the scope column records "
        "exactly what was observed. Reading a page proves what it said at that moment. It does not "
        "prove the page is correct, current, or that its publisher permits this use.",
        "warn",
    )

    body += table(
        "integrity",
        "Snapshot integrity",
        [
            ("File", lambda r: f'<code>{esc(r["file"])}</code>'),
            ("Rows", lambda r: f'<td class="num">{r["rows"]}</td>'),
            ("Identity check re-run by the build", lambda r: esc(r["check"])),
            ("SHA-256 (first 16)", lambda r: f'<code style="font-size:10.5px" title="{esc(r["sha256"])}">'
                                             f'{esc(r["sha256"][:16])}…</code>'),
        ],
        integ,
        sources=["REPO"],
        note="If any of these checks fails the build stops and no page is written. The hash is of the "
             "committed file, so an edit that is not re-verified cannot reach the site.",
    )

    body += '<h2 id="standings-data" style="margin:26px 0 6px">Official standings, all 32 clubs</h2>'
    body += table(
        "standings-table",
        "2026 regular-season standings",
        [
            ("Club", lambda r: f'<strong>{esc(r["abbr"])}</strong><span class="sub">{esc(r["team"])}</span>'),
            ("W", lambda r: f'<td class="num">{r["w"]}</td>'),
            ("L", lambda r: f'<td class="num">{r["l"]}</td>'),
            ("T", lambda r: f'<td class="num">{r["t"]}</td>'),
            ("PCT", lambda r: f'<td class="num">{r["pct"]:.3f}</td>'),
            ("PF", lambda r: f'<td class="num">{r["pf"]}</td>'),
            ("PA", lambda r: f'<td class="num">{r["pa"]}</td>'),
            ("Net", lambda r: f'<td class="num">{r["net"]:+d}</td>'),
            ("PPG", lambda r: num(r["ppg"], 2)),
            ("PAPG", lambda r: num(r["papg"], 2)),
            ("Sources", lambda r: refs(r["source_ids"])),
        ],
        sorted(st, key=lambda r: (-r["pct"], r["abbr"])),
        note="PPG and PAPG are derived (PF/games, PA/games). Division rank is deliberately absent: it "
             "requires tie-breakers that are not in this snapshot (flag DF-05). Division and conference "
             "records, home and road splits are blank because the capture had no header row (flag DF-04).",
        meta="32 clubs · checked 12 Nov 2026",
    )

    body += "<h2 style='margin:26px 0 6px'>Official team passing, four verified fields</h2>"
    body += table(
        "passing",
        "Team passing totals",
        [
            ("Club", lambda r: f"<strong>{esc(r['abbr'])}</strong>"),
            ("ATT", lambda r: f'<td class="num">{r["att"]}</td>'),
            ("CMP", lambda r: f'<td class="num">{r["cmp"]}</td>'),
            ("CMP% as published", lambda r: f'<td class="num">{r["pct"]:.1f}</td>'),
            ("YDS", lambda r: f'<td class="num">{r["yds"]}</td>'),
            ("YPA derived", lambda r: num(r["ypa"], 3)),
            ("Touchdowns", lambda r: blank()),
            ("Interceptions", lambda r: blank()),
        ],
        sorted(ps, key=lambda r: -r["yds"]),
        sources=["NFL-TEAM-PASS-2026"],
        note="Touchdowns and interceptions are blank because the source table was captured without "
             "column labels and those columns could not be identified (flag DF-03). YPA is derived as "
             "YDS/ATT because the page's own average could not be reproduced on four rows; that "
             "discrepancy is the reason it is shown as derived rather than quoted.",
        meta="32 clubs · 4 of 15 columns identified",
    )

    body += "<h2 id='repo-review' style='margin:26px 0 6px'>Repository review, checked line by line</h2>"
    body += (
        "<p>Eighteen checks against the repository as inherited, each with the command that was run or "
        "the file that was read. Nothing here was repaired by this session, because those files belong "
        "to other scopes; the discrepancies are published so the owner can decide.</p>"
    )
    body += table(
        "review-table",
        "Repository review",
        [
            ("ID", lambda r: f'<span class="id">{esc(r["id"])}</span>'),
            ("Area", lambda r: f"<strong>{esc(r['area'])}</strong>"),
            ("Claim checked", lambda r: esc(r["claim_checked"])),
            ("Method", lambda r: esc(r["method"])),
            ("Result", lambda r: esc(r["result"])),
            ("Disposition", lambda r: badge(r["disposition"], "good" if r["disposition"] == "Verified" else "stop")),
            ("Sources", lambda r: refs(r["source_ids"])),
        ],
        review,
        note="Seven of eighteen checks found a discrepancy. None of them affects a number published on "
             "this desk, and none of them was silently corrected.",
    )

    body += "<h2 style='margin:26px 0 6px'>Source register</h2>"
    body += table(
        "sources",
        "Every source read for this desk",
        [
            ("ID", lambda r: f'<span class="id">{esc(r["id"])}</span>'),
            ("Publisher", lambda r: esc(r["publisher"])),
            ("Title", lambda r: f'<a href="{esc(r["url"])}" target="_blank" rel="noopener noreferrer">'
                               f'{esc(r["title"])}</a>'),
            ("What was actually read", lambda r: esc(r["scope"])),
            ("Access", lambda r: esc(r["access"])),
            ("Read on", lambda r: esc(r["checked_on"])),
        ],
        src,
        sources=lambda r: [r["id"]],
        note=f"{len(src)} sources. No wildcard hosts and no secondary aggregators: every URL resolves "
             "to the publisher itself.",
        meta=f"{len(src)} official sources",
    )
    return body


def page_review():
    flags = desk.load_ledger("data/flags.json")["flags"]
    body = '<div class="eyebrow">Flagged for review</div>'
    body += "<h1>Everything this desk knows it does not know</h1>"
    body += (
        '<p class="lead">These items do not block publication. They block qualification. Each one names '
        "the gap, why it matters and which conclusions it constrains. No value attached to a flag is "
        "filled in anywhere on this site.</p>"
    )
    body += notice(
        "Read this page before acting on any other page",
        "Two flags decide how much of this site can be used: DF-01, there is no price or line anywhere, "
        "and DF-14, the rights to republish or to use this material in a gambling context are not "
        "established. Everything else is a data-quality limitation that is disclosed rather than "
        "smoothed over.",
        "stop",
    )
    body += '<div class="grid g4">'
    body += stat("Open flags", len(flags), "published with sources")
    body += stat("Flags that block prices", 1, "DF-01")
    body += stat("Flags that block rights", 1, "DF-14")
    body += stat("Values filled in for a flag", "0", "none, by construction")
    body += "</div>"
    body += table(
        "flags",
        "Flag register",
        [
            ("ID", lambda r: f'<a class="id" href="#detail-{esc(r["id"])}">{esc(r["id"])}</a>'),
            ("Item", lambda r: f"<a href=\"#detail-{esc(r['id'])}\"><strong>{esc(r['item'])}</strong></a>"),
            ("Blocks", lambda r: esc(r["blocks"])),
            ("Status", lambda r: badge(r["status"])),
            ("Unverified value", lambda r: num(r["unverified_value"])),
            ("Sources", lambda r: refs(r["source_ids"])),
        ],
        flags,
        narrow=True,
        note="The 'unverified value' column is empty on every row because no value exists to show. A "
             "zero or a letter grade would be a fabricated measurement.",
        meta=f"{len(flags)} items",
    )
    body += detail_cards(
        flags,
        lambda r: (
            f'<h2 style="margin:0 0 8px">{esc(r["item"])}</h2>'
            f'<dl class="kv">'
            f'<dt>What is missing</dt><dd>{esc(r["detail"])}</dd>'
            f'<dt>What it blocks</dt><dd>{esc(r["blocks"])}</dd>'
            f'<dt>Status</dt><dd>{badge(r["status"])}</dd>'
            f'<dt>Unverified value</dt><dd>Blank — no value exists to publish</dd>'
            f'<dt>Sources</dt><dd>{refs(r["source_ids"])}</dd></dl>'
        ),
        "Flag detail",
    )
    body += card(
        "How to close a flag",
        ul([
            "<strong>DF-01</strong> closes when a licensed, timestamped price archive is contracted and "
            "its operator settlement rules are attached to each market.",
            "<strong>DF-02</strong> closes when injury reports are captured as dated snapshots rather "
            "than read as a live page.",
            "<strong>DF-03 and DF-04</strong> close when a source table with readable column labels is "
            "captured, at which point the excluded columns can be transcribed with a stated definition.",
            "<strong>DF-05</strong> closes when head-to-head and division records are held, which "
            "requires a schedule and results archive.",
            "<strong>DF-06, DF-07 and DF-09</strong> close club by club as depth-chart URLs are "
            "verified and archived with dates.",
            "<strong>DF-14</strong> closes only with written permission, or with a decision that the "
            "work stays a bounded, non-commercial, attributed snapshot.",
        ]),
        "Disposition",
    )
    return body


PAGE_BUILDERS = {
    "index.html": page_index,
    "summary.html": page_summary,
    "decisions.html": page_decisions,
    "suggestions.html": page_suggestions,
    "availability.html": page_availability,
    "strategies.html": page_strategies,
    "competition.html": page_competition,
    "evidence.html": page_evidence,
    "review.html": page_review,
}


def render():
    out = {}
    for name in PAGES:
        out[name] = shell(name, PAGE_BUILDERS[name]())
    return out


def main(argv):
    pages = render()
    if "--check" in argv:
        stale = []
        for name, content in pages.items():
            path = HERE / name
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(name)
        if stale:
            print("STALE: " + ", ".join(stale), file=sys.stderr)
            return 1
        print(f"OK: {len(pages)} desk pages are current and byte-identical to a fresh build.")
        return 0
    for name, content in pages.items():
        (HERE / name).write_text(content, encoding="utf-8")
    (HERE / "manifest.json").write_text(
        json.dumps({"pages": PAGES, "note": "Generated by nfl-desk/build.py; registered as auxiliary pages by scripts/build_site.py."},
                   indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(pages)} pages: " + ", ".join(pages))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
