#!/usr/bin/env python3
"""Build a self-contained, source-linked settlement-rules research page.

No network is used. Verifying live documents is a separate research step; this
script verifies the stored evidence schema, source hosts, and build freshness.
"""
import argparse
import html
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "evidence.json"
OUT = ROOT / "index.html"
OFFICIAL_HOSTS = {
    "portal-spa-api.toto.nl", "www.toto.nl", "extra.toto.nl",
    "help.betmgm.nl", "sportsbook.fanatics.com", "oneidacasinohotel.com",
    "support.draftkings.com", "www.gamblingcommission.gov.uk", "cruksregister.nl",
}


def esc(value):
    return html.escape(str(value), quote=True)


def validate(data):
    sources = data["sources"]
    seen = set()
    for key, source in sources.items():
        address = urlsplit(source["url"])
        if address.scheme != "https" or address.hostname not in OFFICIAL_HOSTS:
            raise ValueError(f"Unapproved source for {key}: {source['url']}")
        for field in ("publisher", "title", "locator"):
            if not source.get(field, "").strip():
                raise ValueError(f"Missing {field} for {key}")
    for collection, required in (
        ("findings", ("id", "category", "operator_scope", "finding", "research_implication", "source_location", "sources")),
        ("flags", ("id", "issue", "evidence", "resolution", "source_location", "sources")),
    ):
        if not data.get(collection):
            raise ValueError(f"Empty {collection}")
        for row in data[collection]:
            for field in required:
                if not row.get(field):
                    raise ValueError(f"Missing {field} in {row}")
            if row["id"] in seen:
                raise ValueError(f"Duplicate id {row['id']}")
            seen.add(row["id"])
            if not isinstance(row["sources"], list) or not set(row["sources"]).issubset(sources):
                raise ValueError(f"Missing or unknown sources in {row['id']}")
            if collection == "flags" and row.get("unverified_value") != "":
                raise ValueError(f"Unverified value must be blank: {row['id']}")


def source_links(ids, sources):
    links = []
    for key in ids:
        source = sources[key]
        label = f"{source['publisher']} — {source['title']}"
        links.append(f'<a href="{esc(source["url"])}">{esc(label)}</a>')
    return "<br>".join(links)


def render(data):
    sources = data["sources"]
    finding_rows = []
    for row in data["findings"]:
        finding_rows.append(
            f'<article class="evidence-card finding-row" data-record="{esc(row["id"])}">'
            f'<p class="row-id">{esc(row["id"])} · {esc(row["category"])}</p>'
            f'<h3>{esc(row["operator_scope"])}</h3>'
            f'<p>{esc(row["finding"])}</p>'
            f'<p class="implication"><strong>Research implication:</strong> {esc(row["research_implication"])}</p>'
            f'<div class="source"><strong>Official source</strong><br>{source_links(row["sources"], sources)}<span class="locator">{esc(row["source_location"])}</span></div></article>'
        )
    flag_rows = []
    for row in data["flags"]:
        flag_rows.append(
            f'<article class="evidence-card flag-card" data-record="{esc(row["id"])}">'
            f'<p class="row-id">{esc(row["id"])}</p>'
            f'<h3>{esc(row["issue"])}</h3>'
            '<p><span class="badge">Unverified</span><span class="sr-only">; value intentionally blank</span></p>'
            f'<p>{esc(row["evidence"])}</p>'
            f'<p class="implication"><strong>Handling:</strong> {esc(row["resolution"])}</p>'
            f'<div class="source"><strong>Official sources</strong><br>{source_links(row["sources"], sources)}<span class="locator">{esc(row["source_location"])}</span></div></article>'
        )
    templates = {
        "reviewed": esc(data["reviewed_utc"]),
        "finding_rows": "\n".join(finding_rows),
        "flag_rows": "\n".join(flag_rows),
    }
    page = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Source-linked evidence on basketball wagering settlement rules and unresolved discrepancies.">
<title>Market & settlement evidence | Own7 NBA Research</title>
<style>
:root{color-scheme:light;--ink:#172337;--muted:#52637a;--line:#dce5ef;--blue:#244b95;--bg:#f4f7fb;--amber:#8b4e06}
*{box-sizing:border-box}body{margin:0;color:var(--ink);background:var(--bg);font:16px/1.55 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:#214f9c;text-decoration-thickness:.08em;text-underline-offset:.15em}a:hover{color:#122f61}a:focus-visible,input:focus-visible{outline:3px solid #ed9a20;outline-offset:3px}
header{background:#122641;color:#fff;padding:1rem max(1rem,calc((100vw - 1280px)/2));}header a{color:#cfe1ff}.topline{display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap}.brand{font-weight:750;letter-spacing:.025em;text-decoration:none}.topline nav{display:flex;gap:1.25rem;flex-wrap:wrap;font-size:.92rem}
main{max-width:1320px;margin:auto;padding:2.8rem 1.2rem 4rem}h1{font-size:clamp(2rem,4.4vw,3.2rem);line-height:1.12;letter-spacing:-.04em;margin:.4rem 0 1rem}h2{font-size:1.55rem;line-height:1.2;margin:2.4rem 0 .45rem}.eyebrow{text-transform:uppercase;color:#47669b;font-size:.75rem;font-weight:750;letter-spacing:.12em;margin:0}.lead{max-width:76ch;color:var(--muted);font-size:1.06rem}.callout{background:#eef4ff;border:1px solid #cbdaf2;border-left:4px solid #3f70bf;border-radius:8px;padding:1rem 1.2rem;margin:1.6rem 0}.callout p{margin:.25rem 0}.warning{background:#fff8ea;border:1px solid #f0dfbf;border-left:4px solid #bb7913}.small{font-size:.9rem;color:var(--muted)}
.toolbar{display:flex;align-items:end;justify-content:space-between;gap:1rem;flex-wrap:wrap;margin:1rem 0}.field{display:grid;gap:.35rem;font-weight:650;font-size:.9rem}.field input{width:min(26rem,85vw);border:1px solid #aabbd0;border-radius:7px;padding:.7rem .8rem;font:inherit;background:white;color:var(--ink)}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,350px),1fr));gap:1rem}.evidence-card{border:1px solid var(--line);border-radius:10px;padding:1.15rem 1.25rem;background:#fff}.evidence-card[hidden]{display:none}.evidence-card h3{font-size:1.03rem;line-height:1.35;margin:.3rem 0 .8rem}.evidence-card p{font-size:.92rem;margin:.7rem 0}.evidence-card .row-id{color:#59739c;font-size:.75rem;font-weight:750;text-transform:uppercase;letter-spacing:.04em;margin:0}.implication{color:#43556d}.source{font-size:.84rem;margin-top:1rem;padding-top:.8rem;border-top:1px solid var(--line)}.source a{display:inline-block;margin-top:.3rem;overflow-wrap:anywhere}.locator{display:block;color:#52637a;font-size:.8rem;margin-top:.35rem}.badge{display:inline-block;background:#fff0d2;color:var(--amber);border:1px solid #edcf99;border-radius:999px;padding:.17rem .5rem;font-size:.75rem;font-weight:700}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}footer{border-top:1px solid var(--line);padding-top:1.5rem;margin-top:2.6rem;color:var(--muted);font-size:.9rem}@media(max-width:650px){main{padding-top:2rem}header{padding:1rem}}

</style>
</head>
<body>
<header><div class="topline"><a class="brand" href="../index.html">OWN7 / NBA RESEARCH</a><nav aria-label="Page navigation"><a href="../index.html">Dashboard</a><a href="#evidence">Rule evidence</a><a href="#review">Flagged for Review</a><a href="../review.html">Project review</a></nav></div></header>
<main>
<p class="eyebrow">Primary-source research · reviewed {{reviewed}} UTC</p>
<h1>Market &amp; settlement evidence</h1>
<p class="lead">A practical, source-linked reference for singles, player props and parlays. Contract details differ across operators, jurisdictions, market labels and rule versions.</p>
<div class="callout"><p><strong>Research only.</strong> Findings report what the cited documents say, not what is currently offered or what applies to a particular wager. Operator examples are not recommendations or legal advice.</p><p>There are no NBA odds, measured correlations, performance results or proven profitable strategies in this register. No method removes luck.</p></div>
<section id="evidence" aria-labelledby="evidence-heading"><h2 id="evidence-heading">Documented rule findings</h2>
<p class="small">Each finding was compared with its linked operator or regulator document. The research implications are proposed safeguards, not claims of proven predictive skill. Select a source to inspect the original text and context.</p>
<div class="toolbar"><label class="field" for="filter">Filter findings<input id="filter" type="search" placeholder="e.g. overtime, player, TOTO"></label><p class="small" id="count" role="status" aria-live="polite"></p></div>
<div class="cards" aria-label="Source-linked market and settlement findings">
{{finding_rows}}
</div><p class="small">TOTO and BetMGM examples are Netherlands-specific; Fanatics and Oneida examples are US jurisdiction-specific. The UK regulator entry is an example of a disclosure framework, not Dutch law. A dated source may have been amended or superseded.</p></section>
<section id="review" aria-labelledby="review-heading"><h2 id="review-heading">Flagged for Review</h2><div class="callout warning"><p><strong>Do not fill the gaps.</strong> These are unresolved source discrepancies or missing rules, not settled facts. The applicable value is intentionally left unverified.</p></div>
<div class="cards" aria-label="Unverified market and settlement items">
{{flag_rows}}
</div></section>
<footer><p>Gambling involves risk. Dutch support: <a href="https://cruksregister.nl/contact">Open over Gokken via Cruks</a>; self-exclusion: <a href="https://cruksregister.nl/">Cruks</a>. No bets are placed by this page.</p><p>Evidence is stored in <a href="evidence.json">machine-readable JSON</a>; see the <a href="README.md">verification notes</a>. <a href="../index.html">Return to the dashboard</a>.</p></footer>
</main>
<script>
(function(){const input=document.querySelector('#filter'),rows=[...document.querySelectorAll('.finding-row')],count=document.querySelector('#count');function update(){const term=input.value.trim().toLocaleLowerCase();let shown=0;for(const row of rows){const matches=row.textContent.toLocaleLowerCase().includes(term);row.hidden=!matches;if(matches)shown++;}count.textContent=shown+' of '+rows.length+' findings shown';}input.addEventListener('input',update);update();})();
</script>
</body>
</html>
'''
    for key, value in templates.items():
        page = page.replace("{{" + key + "}}", value)
    return page


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if HTML is not reproducibly built")
    args = parser.parse_args()
    data = json.loads(DATA.read_text(encoding="utf-8"))
    validate(data)
    page = render(data)
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != page:
            raise SystemExit("market-evidence/index.html is missing or stale; run python3 market-evidence/build.py")
        print(f"OK: {len(data['findings'])} sourced findings and {len(data['flags'])} blank/unverified flags; HTML current")
    else:
        OUT.write_text(page, encoding="utf-8")
        print(f"Built {OUT.relative_to(ROOT.parent)}")


if __name__ == "__main__":
    main()
