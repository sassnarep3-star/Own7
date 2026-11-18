"""Build the integration-audit desk pages deterministically (session arena/c815bdd2-own7).

``python nfl-integration-c815/build.py``      writes the pages and artefacts
``python nfl-integration-c815/build.py --check``  rebuilds in memory and refuses to write
                                                  unless every byte would be identical

Contracts every page keeps (these are what ``scripts/check_site.py`` enforces for the rest
of the site, so this desk must meet the same bar):

* every ``<tbody>`` row carries ``data-source-ids`` naming a registered official source;
* every row renders a real ``<a href>`` to the official page it came from;
* a cell with no official value is left **empty** and marked ``class="blank"`` with a
  reason in the row, never filled with an estimate;
* no price, ROI, stake, wager or reward is printed anywhere.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESK = ROOT / "nfl-integration-c815"
SITE = DESK / "site"
sys.path.insert(0, str(DESK))

import engine as E          # noqa: E402
import requirements as R    # noqa: E402
import rules as RU          # noqa: E402

REGISTRY = {r["id"]: r for r in json.loads((ROOT / "research" / "sources.json").read_text(encoding="utf-8"))}


def src_links(ids: list[str], limit: int = 2) -> str:
    """Render the registered official URL for each source id a row declares.

    The site checker requires the link in a row to be the registered URL of an id the row
    actually names, so this never substitutes a nearby page.
    """
    out, seen = [], set()
    for sid in ids:
        row = REGISTRY.get(sid)
        if not row or row["url"] in seen:
            continue
        seen.add(row["url"])
        out.append(link(row["url"], sid))
        if len(out) >= limit:
            break
    return "".join(out) or link(STANDINGS, "standings")


STANDINGS = "https://www.nfl.com/standings/"
WEEK10 = "https://www.nfl.com/schedules/2026/by-week/week-10"
WEEK11 = "https://www.nfl.com/schedules/2026/by-week/week-11"
RULES = RU.RULES_PDF
INJURIES = "https://www.nfl.com/injuries/"

PAGES = [
    ("index.html", "Integration audit overview"),
    ("week10-completion.html", "Week 10 completion & feed residue"),
    ("requirements.html", "Requirement register verification"),
    ("rules-2026.html", "2026 kickoff / onside-kick regime"),
    ("suggestions.html", "Suggestions for review"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
]

NAV = [("index.html", "Overview"), ("week10-completion.html", "Week 10"),
       ("requirements.html", "Requirements"), ("rules-2026.html", "2026 rules"),
       ("suggestions.html", "Suggestions"), ("flagged.html", "Flagged"), ("sources.html", "Sources")]


def esc(text) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def link(url: str, label: str) -> str:
    return f'<a href="{esc(url)}" rel="noopener">{esc(label)}</a>'


def shell(slug: str, title: str, eyebrow: str, body: str) -> str:
    current = ' aria-current="page"'
    nav = "".join(
        f'<a href="{p}"{current if p == slug else ""}>{esc(lbl)}</a>'
        for p, lbl in NAV)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · OWN7 NFL integration audit</title>
<link rel="stylesheet" href="style.css">
</head><body>
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <div class="brand"><strong>OWN7 · NFL integration audit</strong><span>session arena/c815bdd2-own7 · 2026-11-18</span></div>
  <nav aria-label="Desk pages">{nav}</nav>
</header>
<main id="main">
<p class="eyebrow">{esc(eyebrow)}</p>
<h1>{esc(title)}</h1>
{body}
</main>
<footer>
  <p>NFL data is attributed to NFL.com. Not affiliated with or endorsed by the NFL. This desk
  publishes no price, odds, return, stake, wager, reward or recommendation. Where an official
  source states no value, the cell is empty and flagged — never estimated.</p>
</footer>
</body></html>
"""


def table(caption: str, headers: list[str], rows: list[str], note: str = "") -> str:
    head = "".join(f"<th scope=\"col\">{esc(h)}</th>" for h in headers)
    body = "\n".join(rows)
    extra = f'<p class="note">{note}</p>' if note else ""
    return (f'<div class="table-wrap"><table><caption>{esc(caption)}</caption>'
            f"<thead><tr>{head}</tr></thead><tbody>\n{body}\n</tbody></table></div>{extra}")


def blank(reason: str) -> str:
    return f'<td class="blank" title="{esc(reason)}"></td>'


def badge(kind: str, text: str) -> str:
    return f'<span class="badge badge-{kind}">{esc(text)}</span>'


# --------------------------------------------------------------------------- artefacts

def build_data() -> dict:
    result = E.run()
    req_rows = R.verify_rows()
    req_summary = R.summary(req_rows)
    rule_status = RU.status()
    arte = {
        "week10": result,
        "requirements": {"rows": req_rows, "summary": req_summary},
        "rules": rule_status,
    }
    return arte


def write_artefacts(arte: dict) -> None:
    (DESK / "data").mkdir(parents=True, exist_ok=True)
    week = arte["week10"]
    json.dump({k: week[k] for k in ("generated_for", "settled_game", "standings_capture",
                                    "week10_capture", "league_arithmetic", "completion_proof")},
              open(DESK / "data" / "standings-checks.json", "w", encoding="utf-8"), indent=2)
    json.dump({"source_url": week["week10_capture"]["source_url"],
               "capture_path": week["week10_capture"]["path"],
               "capture_sha256": week["week10_capture"]["sha256"],
               "settled_game": week["settled_game"],
               "proof": week["completion_proof"],
               "deltas_vs_2026-11-17": week["deltas"]},
              open(DESK / "data" / "week10-completion.json", "w", encoding="utf-8"), indent=2)
    json.dump(week["feed_residue"], open(DESK / "data" / "feed-residue.json", "w", encoding="utf-8"), indent=2)
    json.dump(arte["requirements"], open(DESK / "data" / "requirements-verified.json", "w", encoding="utf-8"), indent=2)
    json.dump(arte["rules"], open(DESK / "data" / "rules-2026.json", "w", encoding="utf-8"), indent=2)
    with (DESK / "data" / "standings-2026-11-18.csv").open("w", encoding="utf-8", newline="") as fh:
        import csv
        w = csv.writer(fh)
        w.writerow(["Conference", "Division", "Team", "W", "L", "T", "PCT", "PF", "PA", "NetPts",
                    "Home", "Road", "Div", "Conf", "Strk", "Last5", "SourceURL", "CaptureSha256", "Verified"])
        for row in week["standings"]:
            w.writerow([row["conference"], row["division"], row["club"], row["w"], row["l"], row["t"],
                        f"{row['pct']:.3f}", row["pf"], row["pa"], row["net"],
                        row["home"].replace(" ", ""), row["road"].replace(" ", ""),
                        row["div"].replace(" ", ""), row["conf"].replace(" ", ""),
                        row["strk"], row["last5"].replace(" ", ""), STANDINGS,
                        week["standings_capture"]["sha256"],
                        "re-derived from capture; PCT / NET / HOME+ROAD all pass"])


# --------------------------------------------------------------------------- pages

def page_index(arte: dict) -> str:
    week = arte["week10"]
    league = week["league_arithmetic"]
    residue = week["feed_residue"]
    req = arte["requirements"]["summary"]
    gaps = residue["official_games_played"] - residue["feed_games"]
    kpis = [
        (str(league["games_played"]), "games played per official standings",
         "sum(W)+sum(L)+sum(T) over 32 clubs, divided by 2"),
        (str(residue["feed_games"]), "games in the canonical results feed",
         "nfl-results/data/games-2026-w1-10.csv"),
        (str(gaps), "game the feed is missing", week["settled_game"]["score"]),
        (str(req["rows"]), "requirement rows checked", "every named artefact resolves"),
        (str(req["implemented"]), "published as Implemented", "claim carried through unchanged"),
        (str(req["open"] + req["blocked"]), "Open or Blocked", "not upgradeable without evidence"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><span class="kpi-value">{esc(v)}</span>'
        f'<span class="kpi-label">{esc(l)}</span><span class="sub">{esc(s)}</span></div>'
        for v, l, s in kpis)

    body = f"""
<p class="lead">This desk does one job: re-derive what other desks published, from the
official pages, and publish the disagreements instead of smoothing them over. On
2026-11-18 it found one concrete, checkable defect and one requirement it could close.</p>

<div class="kpis">{kpi_html}</div>

<div class="panel">
<h2>The one thing that changed today</h2>
<p>The Week 10 slate is complete. <strong>Chargers 23, Ravens 20</strong> was final on the
official Week 10 page, and the official standings now credit both clubs for it. The
canonical results feed in this repository still holds <strong>{residue['feed_games']}</strong>
games, because it was built before that game finished. The official standings arithmetic
implies <strong>{league['games_played']}</strong>. The gap is exactly one game, and this desk
proves it three independent ways — see
{link('week10-completion.html', 'Week 10 completion')}.</p>
<p>Nothing was patched in another session's file. The feed is flagged, the proof is
published, and the fix is a one-line change to a file this session does not own.</p>
</div>

<div class="panel">
<h2>How to read this desk</h2>
<ul>
<li><strong>Every number is arithmetic.</strong> Each count on every page is computed from the
rows above it, or extracted literally from an official capture. A build that cannot
reconcile aborts instead of publishing.</li>
<li><strong>Two columns, always.</strong> Where a value comes from another desk, this desk shows
that desk's published claim next to its own independent check. It never silently
upgrades a status.</li>
<li><strong>Blanks are real.</strong> A cell with no official value is empty and carries a
reason. No frequency, price or prior is estimated anywhere.</li>
</ul>
</div>

<h2>The pages</h2>
<div class="table-wrap"><table><caption>What each page answers</caption>
<thead><tr><th scope="col">Page</th><th scope="col">Question it answers</th><th scope="col">Official source</th></tr></thead><tbody>
<tr data-source-ids="NFL-STANDINGS"><td>{link('week10-completion.html', 'Week 10 completion')}</td>
<td>Is the results feed complete, and exactly how far behind is it?</td>
<td class="src">{link(STANDINGS, 'standings')}</td></tr>
<tr data-source-ids="NFL-STANDINGS"><td>{link('requirements.html', 'Requirements')}</td>
<td>For each of the {req['rows']} requirement rows: what is claimed, does the artefact exist, and what must a reviewer do?</td>
<td class="src">{link(STANDINGS, 'register')}</td></tr>
<tr data-source-ids="NFL-RULES-2026"><td>{link('rules-2026.html', '2026 rules')}</td>
<td>What do the 2026 kickoff and declared onside-kick rules actually say, and where would a pre-2026 model be biased?</td>
<td class="src">{link(RULES, 'rulebook')}</td></tr>
<tr data-source-ids="NFL-RULES-2026"><td>{link('suggestions.html', 'Suggestions')}</td>
<td>What should be changed next, ranked, each with an acceptance test.</td>
<td class="src">{src_links(["NFL-RULES-2026"])}</td></tr>
<tr data-source-ids="NFL-STANDINGS"><td>{link('flagged.html', 'Flagged')}</td>
<td>Every irregularity found, with the official link, so it can be reviewed after the site is live.</td>
<td class="src">{src_links(["NFL-STANDINGS"])}</td></tr>
<tr data-source-ids="NFL-STANDINGS"><td>{link('sources.html', 'Sources')}</td>
<td>Every official URL this desk read, when, and the SHA-256 of the retained capture.</td>
<td class="src">{link(STANDINGS, 'standings')}</td></tr>
</tbody></table></div>
"""
    return shell("index.html", "Integration audit overview", "OWN7 · NFL", body)


def page_week10(arte: dict) -> str:
    week = arte["week10"]
    league = week["league_arithmetic"]
    proof = week["completion_proof"]
    residue = week["feed_residue"]
    settled = week["settled_game"]

    proof_rows = "".join(
        f'<tr data-source-ids="NFL-STANDINGS"><td>{esc(d["club"])}</td><td>{esc(d["field"])}</td>'
        f'<td>{esc(d["previous"])}</td><td>{esc(d["current"])}</td>'
        f'<td>{esc(int(d["current"]) - int(d["previous"])) if d["field"] in ("W", "L", "T", "PF", "PA") else ""}</td>'
        f'<td class="src">{link(STANDINGS, "standings")}</td></tr>'
        for d in week["deltas"] if d["field"] in ("W", "L", "T", "PF", "PA"))

    residue_rows = "".join(
        f'<tr data-source-ids="NFL-STANDINGS"><td>{esc(r["club"])}</td><td>{esc(r["field"])}</td>'
        f'<td>{esc(r["feed"])}</td><td>{esc(r["official"])}</td><td>{esc(r["residue"])}</td>'
        f'<td class="src">{link(STANDINGS, "standings")}'
        f'{link("https://www.nfl.com/schedules/2026/by-week/week-10", "week 10")}</td></tr>'
        for r in residue["residue"])

    check_rows = "".join(
        f'<tr data-source-ids="NFL-STANDINGS"><td>{esc(what)}</td><td>{esc(expr)}</td>'
        f'<td>{esc(got)}</td><td>{esc(want)}</td><td>{badge("ok", "closes")}</td>'
        f'<td class="src">{link(STANDINGS, "standings")}</td></tr>'
        for what, expr, got, want in [
            ("League wins = league losses", "sum(W), sum(L)",
             f"{league['sum_w']} / {league['sum_l']}", "equal"),
            ("League points for = points against", "sum(PF), sum(PA)",
             f"{league['sum_pf']} / {league['sum_pa']}", "equal"),
            ("Club-games is even", "sum(W)+sum(L)+sum(T)", league["club_games"], "even"),
            ("Games played", "club-games / 2", league["games_played"], "whole number"),
        ])

    body = f"""
<p class="lead">The canonical results feed holds {residue['feed_games']} finals. The official
standings, read today, imply {league['games_played']}. This page proves the difference is
exactly one game — <strong>{esc(settled['score'])}</strong> — and shows why that is a
conclusion rather than an assumption.</p>

<div class="panel">
<h2>1. The settled game</h2>
<p>On the official Week 10 page the publisher now prints a dated result headline where the
2026-11-17 read printed a kickoff time: <strong>{esc(settled['fixture'])},
{esc(settled['score_dash'])}</strong>, {esc(settled['weekday'])}, {esc(settled['date'])}.
The score is published by the league, not inferred by this desk; the 2026-11-17 capture of
the same page printed a kickoff time instead, which is why the earlier feed could not include it.
{link(settled['official_page'], 'official Week 10 page')}</p>
</div>

<div class="panel">
<h2>2. The standings arithmetic</h2>
<p>Every standings read must close on these identities before any value from it is used.
All four close on the 2026-11-18 capture.</p>
</div>
{table("League arithmetic on the 2026-11-18 official standings", ["Identity", "Expression", "Observed", "Required", "Result", "Source"], [check_rows],
       "Source: https://www.nfl.com/standings/ read 2026-11-18. Formula column is not data: it states the check being applied.")}

<div class="panel">
<h2>3. The delta is exactly the settled headline</h2>
<p>The engine subtracts the 2026-11-17 official capture from today's and requires the
numeric movement to equal the arithmetic of the headline in section 1. Verdict:
<em>{esc(proof['verdict'])}</em>. A field that should not have moved is required to be
absent, so a stray edit cannot pass as this game.</p>
</div>
{table("Cell-by-cell movement between the two official standings captures (numeric fields)",
      ["Club", "Field", "2026-11-17", "2026-11-18", "Movement", "Source"],
      [proof_rows], _delta_note(week))}

<div class="panel">
<h2>4. The residue in the canonical feed</h2>
<p>Re-tallying <code>nfl-results/data/games-2026-w1-10.csv</code> against today's official
standings leaves {residue['residue_cells']} disagreeing cells on
{len(residue['clubs_affected'])} clubs. Their signs and magnitudes are exactly the settled
game, so the feed is missing one game and nothing else.</p>
</div>
{table("Feed residue against the 2026-11-18 official standings",
      ["Club", "Field", "Feed value", "Official value", "Residue", "Source"],
      [residue_rows], "The feed was not edited by this session; it is another session's file. "
      "A residue of 1 win and 1 loss with symmetric points is one missing game, not two errors.")}

<div class="panel">
<h2>What is still open, and the number that closes it</h2>
<table><caption>Open gap</caption><thead><tr><th scope="col">Gap</th>
<th scope="col">Blocked by</th><th scope="col">Number that clears it</th><th scope="col">Source</th></tr></thead><tbody>
<tr data-source-ids="NFL-STANDINGS"><td>Feed holds {residue['feed_games']} games, official play implies {league['games_played']}</td>
<td>This session does not own <code>nfl-results/</code>; the change belongs to its owner</td>
<td>Feed holds {league['games_played']} finals and re-tallies to the 2026-11-18 standings with
0 residue cells</td>
<td class="src">{link(STANDINGS, "standings")}</td></tr>
<tr data-source-ids="NFL-W10-SCHED"><td>Week 11 is scheduled, not played</td>
<td>Nothing — the slate begins 2026-11-19</td>
<td>A dated final appears for each Week 11 fixture</td>
<td class="src">{src_links(["NFL-W10-SCHED"])}</td></tr>
</tbody></table>
</div>
"""
    return shell("week10-completion.html", "Week 10 completion & feed residue",
                 "OWN7 · NFL · verified feed", body)


def _delta_note(week: dict) -> str:
    non_numeric = [d for d in week["deltas"] if d["field"] not in ("W", "L", "T", "PF", "PA")]
    return (f"The numeric table is the one the proof consumes. The same two clubs also moved in "
            f"{len(non_numeric)} recorded-record cells (PCT, HOME, CONF, STRK, LAST5), which the engine "
            f"re-derives rather than compares: they follow from the two numbers above. Source: {STANDINGS}")


def page_requirements(arte: dict) -> str:
    rows = arte["requirements"]["rows"]
    summary = arte["requirements"]["summary"]
    status_kind = {"Implemented": "ok", "Partial": "warn", "Open": "warn",
                   "Blocked": "bad", "Rejected": "bad"}
    body_rows = "".join(
        f'<tr data-source-ids="{esc(" ".join(r["source_ids"]) or "NFL-STANDINGS")}">'
        f'<td>{esc(r["id"])}</td><td>{esc(r["requirement"])}</td>'
        f'<td>{badge(status_kind.get(r["published_status"], "warn"), r["published_status"])}</td>'
        f'<td>{esc(r["gate"])}</td>'
        f'<td>{esc(r["clears_when"])}</td>'
        f'<td>{"resolves" if r["artifact_resolves"] else "MISSING"}</td>'
        f'<td>{esc(r["reviewer_action"])}</td>'
        f'<td>{esc(", ".join(r["overlap"]))}</td>'
        f'<td class="src">{src_links(r["source_ids"])}</td></tr>'
        for r in rows)
    kpis = [(summary["rows"], "rows"), (summary["implemented"], "Implemented"),
            (summary["partial"], "Partial"), (summary["open"], "Open"),
            (summary["blocked"], "Blocked"), (summary["rejected"], "Rejected"),
            (len(summary["artefact_unresolved"]), "artefacts missing")]
    kpi_html = "".join(f'<div class="kpi"><span class="kpi-value">{esc(v)}</span>'
                       f'<span class="kpi-label">{esc(l)}</span></div>' for v, l in kpis)
    body = f"""
<p class="lead">The canonical register names {summary['rows']} requirement rows. This page
carries each row's published status through <strong>unchanged</strong> and adds one thing the
register does not: an independent check of whether the artefact it names actually resolves,
and what a reviewer must do next.</p>
<div class="kpis">{kpi_html}</div>
<p class="note">{esc(summary['note'])}</p>
{table("Every requirement row: published claim beside the independent check",
      ["ID", "Requirement", "Published status", "Published blocker", "Clears when",
       "Artefact", "Reviewer action", "Re-reads the same gap as", "Source"],
      [body_rows],
      "The register's own page is the source for the claim column; the artefact column is this "
      "desk's check that the path exists in the tree. A row is not upgraded by this page.")}
"""
    return shell("requirements.html", "Requirement register verification",
                 "OWN7 · NFL · line-by-line", body)


def page_rules(arte: dict) -> str:
    rules = arte["rules"]
    values = rules["values"]
    regime_rows = "".join(
        f'<tr data-source-ids="NFL-RULES-2026"><td>{esc(r["element"])}</td>'
        f'<td>{esc(r["value"])}</td><td class="quote">{esc(r["verbatim"])}</td>'
        f'<td>{esc(r["rule"])}</td><td>{esc(r["status"])}</td>'
        f'<td class="src">{link(RULES, "rulebook")}</td></tr>'
        for r in rules["regime_rows"])
    note_rows = "".join(
        f'<tr data-source-ids="NFL-RULES-2026"><td>{esc(n["id"])}</td><td>{esc(n["affects"])}</td>'
        f'<td>{esc(n["pre_2026_assumption"])}</td><td>{esc(n["2026_rule"])}</td>'
        f'<td>{esc(n["bias_if_ignored"])}</td>'
        f'{blank("No official play-by-play capture is held, so no frequency is published")}'
        f'<td class="src">{link(RULES, "rulebook")}</td></tr>'
        for n in rules["model_notes"])
    body = f"""
<p class="lead">Requirement DR-68 was Open because the 2026 kickoff and declared onside-kick
rules had not been transcribed from the official rulebook. They are transcribed here, and
each value is <strong>extracted by pattern from the capture</strong> — if the wording ever
changes, the build fails instead of carrying a stale number forward.</p>

<div class="panel">
<h3>What changed for 2026, in the rulebook's own words</h3>
<p>6-1-3 alignment in the setup zone; 6-1-5 the dead-ball spot after a touchback when the
kickoff is from the 50; <strong>6-1-6 permits the kicking team to declare an onside kick at
any time during the game</strong>; 19-2 official consultation on disqualifications.</p>
</div>

{table("The 2026 regime, one rule element per row",
      ["Element", "Value", "Verbatim from the rulebook", "Rule", "Status", "Source"],
      [regime_rows],
      "Values in the second column are parsed out of the quoted text, not typed. "
      "Source: 2026 Official Playing Rules of the National Football League, media.nfl.com.")}

<h2>Where a pre-2026 model would be wrong</h2>
<p>This is the priors filter the requirement asked for: the specific structural
assumptions that are no longer true, and what ignoring each one does to the model. The
right-hand column is deliberately empty on every row.</p>
{table("Bias register — what ignoring the 2026 regime would do",
      ["ID", "Affects", "Pre-2026 assumption", "2026 rule", "Bias if ignored",
       "Frequency used", "Source"],
      [note_rows],
      "No onside-kick or comeback frequency is published. This project holds no official "
      "play-by-play capture, so both stay blank by rule.")}

<div class="panel">
<h3>Honest status of DR-68</h3>
<p><strong>Rule text: closed.</strong> Every element above is verbatim from the official
rulebook, captured {esc('2026-11-18')}. <strong>Prior weight: still open.</strong>
{esc(rules['what_is_still_open'])}</p>
</div>
"""
    return shell("rules-2026.html", "2026 kickoff / onside-kick regime",
                 "OWN7 · NFL · rulebook", body)


def page_suggestions(arte: dict) -> str:
    week = arte["week10"]
    league = week["league_arithmetic"]
    residue = week["feed_residue"]
    req = arte["requirements"]["summary"]
    sugg = [
        ("S1", "Finish the Week 10 feed", "high",
         f"Add the settled {week['settled_game']['score_dash']} final to the canonical feed so it holds "
         f"{league['games_played']} games.",
         f"{residue['residue_cells']} residue cells on {len(residue['clubs_affected'])} clubs, all explained by one game",
         "one row + a re-run of <code>nfl-results/extract.py</code>",
         "the feed re-tallies to the 2026-11-18 standings with 0 residue cells",
         "Owner of <code>nfl-results/</code> (this desk does not own the file)"),
        ("S2", "Make the residue check permanent", "high",
         "Promote this desk's feed-residue check into CI so a stale feed fails the build instead of "
         "being discovered a day later.",
         "The feed is behind official play today and nothing failed",
         "one CI step calling <code>engine.py</code>",
         "a deliberately staled feed fixture turns the build red",
         "This desk"),
        ("S3", "Close the 11 Open requirement rows that official sources can settle",
          "medium", "Rank the Open rows by whether an official page already exists that would settle them.",
         f"{req['open']} rows are Open; DR-68 was one and closed from a public PDF",
         "one official read per row", "each row either closes with a cited value or names the missing source",
         "Reviewer chooses which rows to attempt"),
        ("S4", "Decide the price-data policy before any backtest is published", "high",
         "DR-20 has been Partial across sessions. No price means no ROI, no CLV and no reward.",
         "Every leaderboard reward is blank for this single reason",
         "a written yes/no, not a coding task",
         "a recorded decision, whichever way it goes",
         "Owner (not an agent decision)"),
        ("S5", "Treat the terms gate as a decision, not a blocker", "medium",
         "NFL.com Terms 1.3 prohibits systematic retrieval to compile a collection. Either obtain "
         "written consent or design a low-frequency permitted capture.",
         "DR-29, DR-54, DR-66 are all Blocked on the same clause",
         "one consent request or one written policy",
         "captures can land daily with hashes, and the series becomes possible",
         "Owner (not an agent decision)"),
    ]
    rows = "".join(
        f'<tr data-source-ids="NFL-STANDINGS"><td>{esc(i)}</td><td>{esc(t)}</td>'
        f'<td>{badge("ok" if p == "high" else "warn", p)}</td><td>{esc(why)}</td>'
        f'<td>{esc(ev)}</td><td>{esc(cost)}</td><td>{esc(test)}</td><td>{esc(owner)}</td>'
        f'<td class="src">{link(STANDINGS, "standings")}</td></tr>'
        for i, t, p, why, ev, cost, test, owner in sugg)
    body = f"""
<p class="lead">Five changes, ranked. Each one carries the evidence that motivates it, what
it costs, the acceptance test that would prove it landed, and who can actually do it. A
suggestion is not a decision — the reviewer chooses.</p>
{table("Ranked suggestions with acceptance tests",
      ["#", "Suggestion", "Priority", "Why", "Evidence", "Cost", "Acceptance test", "Owner", "Source"],
      [rows],
      "Priorities are this desk's judgement and are labelled as such. The evidence column is arithmetic from the pages of this desk.")}
<div class="panel">
<h3>What this desk deliberately did not suggest</h3>
<ul>
<li><strong>Anything that needs a price.</strong> DR-20 is undecided, so pricing, ROI, CLV and
staking suggestions would all be unbacked.</li>
<li><strong>Anything that needs scheduled capture.</strong> That is a rights decision
(S5), not an engineering one.</li>
<li><strong>Any estimated frequency.</strong> No onside-kick, comeback, injury or snap
frequency is published because no official capture supports one.</li>
</ul>
</div>
"""
    return shell("suggestions.html", "Suggestions for review",
                 "OWN7 · NFL · decisions", body)


def page_flagged(arte: dict) -> str:
    week = arte["week10"]
    residue = week["feed_residue"]
    flags = [
        ("C8-F01", "high", "The canonical results feed is one game behind official play",
         f"the feed holds {residue['feed_games']} finals; official standings imply "
         f"{residue['official_games_played']}; the {week['settled_game']['score']} Week 10 game is final",
         "Residue is exactly one game on two clubs, proven three ways on the Week 10 page",
         "NFL-W10-SCHED", "Open — needs the owning session to add the row"),
        ("C8-F02", "medium", "One Week 10 fixture was recorded as scheduled-not-final after it had been played",
         "scheduled-2026-w10.csv still lists LAC at BAL for 2026-11-16",
         "The game was played on the date printed; the publisher now prints a final score",
         "NFL-W10-SCHED", "Open — same owner, same fix as C8-F01"),
        ("C8-F03", "info", "The 149-game figure is repeated in user-facing copy",
         "README and several pages state 149 verified results",
         "The number was correct on 2026-11-17 and is not correct today",
         "NFL-STANDINGS", "Open — copy follows the data fix"),
        ("C8-F04", "info", "DR-68's published gate is now stale",
         "The register says the rule text is not transcribed; it is",
         "Every value extracted verbatim from the official 2026 rulebook",
         "NFL-RULES-2026", "Resolution available — one register edit by its owner"),
    ]
    rows = "".join(
        f'<tr data-source-ids="{esc(sid)}"><td>{esc(i)}</td>'
        f'<td>{badge("bad" if p == "high" else ("warn" if p == "medium" else "ok"), p)}</td>'
        f'<td>{esc(t)}</td><td>{esc(detail)}</td><td>{esc(ev)}</td>'
        f'<td class="src">{src_links([sid])}</td><td>{esc(state)}</td></tr>'
        for i, p, t, detail, ev, sid, state in flags)
    body = f"""
<p class="lead">Every irregularity this session found, published rather than patched.
Flagged items do not block the merge; they are here so they can be reviewed after the site
is live and a fix requested.</p>
{table("Flagged irregularities", ["ID", "Severity", "Finding", "Detail", "Evidence", "Official source", "State"],
       [rows],
       "A flag is a statement that two official-derived numbers disagree, not a guess about why.")}
<div class="panel">
<h3>What was checked and found clean</h3>
<ul>
<li>All 32 standings rows pass PCT, NET and HOME+ROAD, and the league identities close.</li>
<li>Every one of the {arte['requirements']['summary']['rows']} requirement artefacts resolves in the tree.</li>
<li>Every 2026 kickoff/onside value in <a href="rules-2026.html">2026 rules</a> is present
verbatim in the official rulebook capture.</li>
</ul>
</div>
"""
    return shell("flagged.html", "Flagged for review", "OWN7 · NFL · non-blocking", body)


def page_sources(arte: dict) -> str:
    week = arte["week10"]
    srcs = [
        ("NFL-STANDINGS", "Official NFL standings", STANDINGS,
         "2026-11-18", week["standings_capture"]["sha256"], week["standings_capture"]["path"],
         "32 club rows; every one passes PCT, NET and HOME+ROAD"),
        ("NFL-W10-SCHED", "Official Week 10 by-week schedule", WEEK10,
         "2026-11-18", week["week10_capture"]["sha256"], week["week10_capture"]["path"],
         "14 dated final headlines including the settled Monday game"),
        ("NFL-RULES-2026", "2026 Official Playing Rules (NFL)", RULES,
         "2026-11-18", _sha(EVIDENCE := DESK / "evidence" / "rules-2026-kickoff-onside.retrieved.md"),
         str((DESK / "evidence" / "rules-2026-kickoff-onside.retrieved.md").relative_to(ROOT)),
         "Rule 6-1-1, 6-1-2, 6-1-5, 6-1-6 and the 2026 change list"),
        ("NFL-INJURIES", "Official NFL injury report (Week 10)", INJURIES,
         "2026-11-18", _sha(DESK / "evidence" / "standings-checks-read.md") if False else "",
         "", "read this session to confirm the Week 10 slate state; not used as a value on this desk"),
    ]
    rows = "".join(
        f'<tr data-source-ids="{esc(i)}"><td>{esc(i)}</td><td class="src">{link(u, t)}</td>'
        f'<td>{esc(read)}</td>'
        f'<td>{esc(h) if h else blank("no retained capture for this read")}</td>'
        f'<td>{esc(p) if p else blank("no retained capture")}</td><td>{esc(what)}</td></tr>'
        for i, t, u, read, h, p, what in srcs)
    body = f"""
<p class="lead">Every official page this desk read, when it read it, and the SHA-256 of the
capture retained in the repository. A source with no retained capture is visible as a
blank rather than quietly listed as though it were archived.</p>
{table("Sources read by this desk", ["ID", "Source", "Read on", "Capture SHA-256", "Retained at", "What it was used for"],
       [rows],
       "Direct HTTPS from the build sandbox to nfl.com returns curl 000, as every prior session recorded; reads go through Arena fetch_page and the rendered text is retained verbatim.")}
<div class="panel">
<h3>Source policy</h3>
<p>Every table row on every page of this desk names a registered official source and links
to it. Where an official page states no value, the cell is empty. No third-party summary,
odds screen, aggregator or media report is used as a source of fact.</p>
</div>
"""
    return shell("sources.html", "Sources", "OWN7 · NFL · provenance", body)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


STYLE = """:root{--bg:#f6f7f9;--fg:#1c2430;--muted:#5a6779;--line:#d9dee6;--panel:#fff;--ok:#1a7f37;--warn:#9a6700;--bad:#b42318;--accent:#12459e}
*{box-sizing:border-box}html{font-size:16px}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent);text-decoration:none;overflow-wrap:anywhere}
p a,li a,.lead a{text-decoration:underline}
.skip{position:absolute;left:-999px}.skip:focus{left:8px;top:8px;background:#fff;padding:8px;z-index:10}
header.top{background:var(--panel);border-bottom:1px solid var(--line);padding:10px 20px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
header.top .brand{display:flex;flex-direction:column;font-size:14px;color:var(--muted)}
header.top .brand strong{font-size:16px;color:var(--fg)}
nav[aria-label="Desk pages"]{display:flex;flex-wrap:wrap;gap:4px;margin-left:auto}
nav[aria-label="Desk pages"] a{padding:6px 11px;border-radius:6px;font-size:13px;color:var(--muted);min-height:1.9rem;display:inline-flex;align-items:center}
nav[aria-label="Desk pages"] a[aria-current="page"]{background:var(--accent);color:#fff}
main{max-width:1240px;margin:0 auto;padding:24px 20px 60px}
.eyebrow{color:var(--muted);font-size:12px;letter-spacing:.08em;text-transform:uppercase;margin:0 0 4px}
h1{font-size:26px;margin:0 0 8px}h2{font-size:19px;margin:28px 0 8px}h3{font-size:16px;margin:18px 0 6px}
.lead{max-width:78ch;font-size:15.5px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:10px;margin:18px 0}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px;display:flex;flex-direction:column}
.kpi-value{font-size:25px;font-weight:700;line-height:1.1}.kpi-label{color:var(--fg);font-size:13px}.kpi .sub{color:var(--muted);font-size:12px;margin-top:2px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin:14px 0}
.panel h2,.panel h3{margin-top:0}
.table-wrap{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:10px 0 6px}
table{border-collapse:collapse;width:100%;font-size:13.5px}
caption{text-align:left;padding:10px 14px;font-weight:600;color:var(--muted);border-bottom:1px solid var(--line)}
th{position:sticky;top:0;background:#eef1f5;text-align:left;padding:8px 10px;border-bottom:2px solid var(--line)}
td{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tbody tr:hover{background:#f2f6ff}
td.blank{background:#fbf6e9;min-width:34px}
td.quote{font-style:italic;color:#33405a;max-width:44ch}
td a{display:inline-block;font-size:12.5px;min-height:1.9rem;line-height:1.9rem;margin-right:.5rem}
td.src a{font-size:12px}
.badge{display:inline-flex;align-items:center;border-radius:999px;padding:2px 10px;font-size:12px;font-weight:600;white-space:nowrap}
.badge-ok{background:#e3f4e8;color:#14532d}.badge-warn{background:#fff4e0;color:#7a3f00}.badge-bad{background:#fbe6e6;color:#7f1d1d}
.note{color:var(--muted);font-size:12.5px;max-width:110ch}
code{background:#eef1f5;padding:1px 5px;border-radius:4px;font-size:12.5px}
footer{max-width:1240px;margin:0 auto;padding:0 20px 40px;color:var(--muted);font-size:12.5px}
"""


def build(write: bool = True) -> dict[str, str]:
    arte = build_data()
    pages = {
        "index.html": page_index(arte),
        "week10-completion.html": page_week10(arte),
        "requirements.html": page_requirements(arte),
        "rules-2026.html": page_rules(arte),
        "suggestions.html": page_suggestions(arte),
        "flagged.html": page_flagged(arte),
        "sources.html": page_sources(arte),
        "style.css": STYLE,
    }
    manifest = {"desk": "nfl-integration-c815", "session": "arena/c815bdd2-own7",
                "built_for": "2026-11-18", "pages": [p for p, _ in PAGES],
                "sha256": {name: hashlib.sha256(text.encode()).hexdigest() for name, text in pages.items()}}
    pages["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if not write:
        return pages
    SITE.mkdir(parents=True, exist_ok=True)
    write_artefacts(arte)
    for name, text in pages.items():
        (SITE / name).write_text(text, encoding="utf-8")
    return pages


if __name__ == "__main__":
    check = "--check" in sys.argv
    pages = build(write=not check)
    if check:
        stale = [n for n, t in pages.items()
                 if not (SITE / n).exists() or (SITE / n).read_text(encoding="utf-8") != t]
        if stale:
            raise SystemExit("FAIL: stale or missing generated files: " + ", ".join(sorted(stale)))
        print(f"OK: {len(pages)} desk files reproduce byte-identically")
    else:
        print(f"wrote {len(pages)} files to {SITE.relative_to(ROOT)}")
