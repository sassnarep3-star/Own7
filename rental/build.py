#!/usr/bin/env python3
"""Deterministic builder for the anonymized SF rent-increase research sub-site.

No network is used. All content comes from rental/data.json; every table row
carries registered official source IDs and links. Blank cells stay truly blank
(unverified values are never filled in). `--check` verifies committed output.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data.json"
MANIFEST = ROOT / "manifest.json"

PAGES = [
    "index.html",
    "executive-summary.html",
    "units.html",
    "law.html",
    "process.html",
    "practice.html",
    "sources.html",
    "flagged.html",
]

NAV = [
    ("index.html", "Overview"),
    ("executive-summary.html", "Executive summary"),
    ("units.html", "Units & calculations"),
    ("law.html", "Law: local / state / federal"),
    ("process.html", "Notice & reasons"),
    ("practice.html", "Owner practice & fairness"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flagged for Review"),
]


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def load_data():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    ids = {s["id"] for s in data["sources"]}
    if len(ids) != len(data["sources"]):
        raise ValueError("duplicate source id")
    for collection in ("property", "units", "calculations", "law_rows", "process_rows", "practice_rows", "qa", "flags"):
        for row in data[collection]:
            if not row.get("source_ids") or not set(row["source_ids"]).issubset(ids):
                raise ValueError(f"{collection}:{row.get('id')}: missing/unknown source ids")
            if row.get("value", "x") == "" and not any(
                k in row.get("status", "") for k in ("Unverified", "Not found", "blank")
            ):
                raise ValueError(f"{collection}:{row.get('id')}: blank value without unverified status")
    return data


def src_urls(data):
    return {s["id"]: s["url"] for s in data["sources"]}


def refs_cell(source_ids, urls):
    links = " ".join(
        f'<a href="{esc(urls[s])}" title="{esc(s)}" target="_blank" rel="noopener noreferrer">{esc(s)} &#8599;</a>'
        for s in source_ids
    )
    return f'<td class="refs">{links}</td>'


def cell(row, key):
    if key not in row or row[key] is None:
        return "<td></td>"
    value = row[key]
    if value == "":
        status = row.get("status", "")
        label = f"Blank - {status}" if status else "Blank - not supplied"
        return f'<td class="blank" data-empty="true" aria-label="{esc(label)}" title="{esc(label)}"></td>'
    return f"<td>{esc(value)}</td>"


def table(table_id, caption, columns, rows, urls):
    """columns: list of (header, key). Every body row gets data-source-ids + refs."""
    head = "".join(f'<th scope="col">{esc(h)}</th>' for h, _ in columns)
    head += '<th scope="col">Sources / references</th>'
    body = []
    for i, row in enumerate(rows):
        rid = row.get("id", f"row-{i}")
        cells = "".join(cell(row, key) for _, key in columns)
        body.append(
            f'<tr data-row-id="{esc(rid)}" data-source-ids="{esc(" ".join(row["source_ids"]))}">'
            + cells + refs_cell(row["source_ids"], urls) + "</tr>"
        )
    return (
        f'<div class="table-scroll" role="region" aria-label="{esc(caption)}" tabindex="0">'
        f'<table id="{esc(table_id)}"><caption class="sr-only">{esc(caption)}. Blank cells are intentional; sources are supplied per row.</caption>'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )


def page(data, slug, title, lead, body):
    nav_items = []
    for href, label in NAV:
        current = ' aria-current="page"' if href == slug else ""
        nav_items.append(f'<a href="{href}"{current}>{esc(label)}</a>')
    nav = "".join(nav_items)
    p = data["project"]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{esc(p['title'])} - source-linked, anonymized research. Checked {esc(p['checked_on'])}.">
<title>{esc(title)} | SF rent-increase research</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<a class="skip-link" href="#main-content">Skip to content</a>
<header class="site-header">
<div class="topline">
<a class="brand" href="index.html">OWN7 &middot; SF RENT RESEARCH</a>
<nav aria-label="Rental research sections">{nav}<a href="../index.html">Main site &#8599;</a></nav>
</div>
</header>
<main id="main-content">
<div class="page-heading">
<p class="eyebrow">SAN FRANCISCO / OUTER SUNSET 94122 / RENT-CONTROLLED 1940 BUILDING</p>
<h1>{esc(title)}</h1>
<p class="lead">{esc(lead)}</p>
</div>
{body}
</main>
<footer class="site-footer">
<p><strong>OWN7</strong> / anonymized informational research &middot; checked {esc(p['checked_on'])} &middot; not legal advice &middot; <a href="flagged.html">Flagged for Review</a> &middot; <a href="sources.html">Sources</a> &middot; <a href="../index.html">Main site</a></p>
</footer>
</body>
</html>
"""


def cards():
    items = [
        ("executive-summary.html", "Executive summary", "The important details and direct answers to each question, with sources."),
        ("units.html", "Units & calculations", "Anonymized unit facts (dates and amounts unchanged) and the 1.6% calculations."),
        ("law.html", "Law by layer", "Local SF Rent Ordinance, state AB 1482 / Costa-Hawkins / Civ. Code 827, federal Fair Housing Act."),
        ("process.html", "Notice & reasons", "Correct notice procedure and the reasonable, lawful bases for an increase."),
        ("practice.html", "Owner practice & fairness", "Corporations vs individual owners; raising one unit vs both (discrimination risk)."),
        ("sources.html", "Sources", "Every official source used, with check date and scope."),
        ("flagged.html", "Flagged for Review", "Unverified values left blank and items needing manual review."),
    ]
    return '<div class="cards">' + "".join(
        f'<a class="card" href="{href}"><h2>{esc(t)}</h2><p>{esc(d)}</p><span class="card-link">Open &rarr;</span></a>'
        for href, t, d in items
    ) + "</div>"


def metrics(data):
    urls = src_urls(data)
    items = [
        ("Allowable increase 3/1/26-2/28/27", "1.6%", "of base rent, once per 12 months, SF Rent Board", "SFGOV-ANNUAL-26"),
        ("Written notice", "30 / 90 days", "30 days if 10% or less (combined over 12 months); 90 days if more; +5 if mailed", "CA-CC827"),
        ("Units covered", "2", "1940 two-unit building, Outer Sunset 94122, rent controlled", "SFGOV-RENTAL-LAWS"),
        ("Flagged items", str(len(data["flags"])), "unverified values left blank for review", "SFGOV-RENT-INC"),
    ]
    return '<div class="metric-grid">' + "".join(
        f'<div class="metric"><div class="metric-label">{esc(a)}</div><div class="metric-value">{esc(b)}</div>'
        f'<p class="metric-note">{esc(c)} &middot; <a href="{esc(urls[s])}" target="_blank" rel="noopener noreferrer">{esc(s)} &#8599;</a></p></div>'
        for a, b, c, s in items
    ) + "</div>"


def render(data):
    urls = src_urls(data)
    p = data["project"]
    pages = {}

    landing_body = (
        metrics(data) + cards()
        + "<section><h2>What this project covers</h2><p>" + esc(p["subtitle"]) + "</p>"
        + "<p><strong>Privacy:</strong> " + esc(p["privacy"]) + "</p>"
        + '<p><strong>Disclaimer:</strong> ' + esc(p["disclaimer"]) + "</p></section>"
    )
    pages["index.html"] = page(data, "index.html", "SF Outer Sunset rent-increase research",
                               "Reasonable and normal rent increases for a rent-controlled 1940 two-unit building in 94122, verified line by line against official sources.",
                               landing_body)

    qa_body = (
        '<div class="notice"><strong>Bottom line:</strong> the normal, lawful increase for both units is the SF Rent Board annual allowable increase '
        "(1.6% of each unit's base rent for 3/1/2026-2/28/2027), once per 12 months, plus any properly banked amounts, with 30/90-day written notice "
        "and a current rent increase license - applied uniformly to both units.</div>"
        + table("qa-table", "Questions and verified answers",
                [("Question", "question"), ("Answer", "answer")], data["qa"], urls)
    )
    pages["executive-summary.html"] = page(data, "executive-summary.html", "Executive summary",
                                           "Important details and direct answers to each inquiry, every row linked to official sources.", qa_body)

    units_body = (
        "<section><h2>Property</h2>"
        + table("property-table", "Property facts", [("ID", "id"), ("Field", "field"), ("Value", "value"), ("Status / note", "status")], data["property"], urls)
        + "</section><section><h2>Units (anonymized)</h2><p>Personal information is replaced with placeholder labels; dates and amounts are unchanged.</p>"
        + table("units-table", "Unit facts", [("Unit", "id"), ("Field", "field"), ("Value", "value"), ("Rent", "rent"), ("Status / note", "status")], data["units"], urls)
        + "</section><section><h2>Calculations</h2><p>Arithmetic on the user-supplied rents using the official 1.6% rate. Unverified values are left blank.</p>"
        + table("calc-table", "Allowable increase calculations", [("ID", "id"), ("Calculation", "field"), ("Result", "value"), ("Status / note", "status")], data["calculations"], urls)
        + "</section>"
    )
    pages["units.html"] = page(data, "units.html", "Units & calculations",
                               "Anonymized unit facts with dates and amounts unchanged, plus the allowable-increase math.", units_body)

    law_body = (
        '<div class="notice"><strong>Layer order:</strong> for this 1940 two-unit building the San Francisco Rent Ordinance controls the amount (1.6% cap). '
        "The statewide AB 1482 cap does not apply where stricter local rent control exists (Civ. Code 1947.12(d)(3)); the state notice statute and the federal Fair Housing Act still apply.</div>"
        + table("law-table", "Law by layer", [("Layer", "layer"), ("Topic", "topic"), ("Rule", "rule"), ("Status / note", "status")], data["law_rows"], urls)
    )
    pages["law.html"] = page(data, "law.html", "Law: local / state / federal",
                             "What each legal layer actually says about rent increases for this building.", law_body)

    proc_body = table("process-table", "Notice procedure and reasonable reasons",
                      [("Step", "step"), ("Requirement", "requirement"), ("Status / note", "status")], data["process_rows"], urls)
    pages["process.html"] = page(data, "process.html", "Notice & reasonable reasons",
                                 "The correct way to inform tenants and the lawful bases for an increase.", proc_body)

    prac_body = table("practice-table", "Owner practice and fairness",
                      [("Topic", "topic"), ("Answer", "answer"), ("Status / note", "status")], data["practice_rows"], urls)
    pages["practice.html"] = page(data, "practice.html", "Owner practice & fairness",
                                  "Corporations vs individual owners, and raising one unit vs both.", prac_body)

    src_rows = [
        {"id": s["id"], "publisher": s["publisher"], "title": s["title"], "url": s["url"],
         "checked": s["checked_on"], "scope": s["scope"], "source_ids": [s["id"]]}
        for s in data["sources"]
    ]
    src_body = table("sources-table", "Official source register",
                     [("ID", "id"), ("Publisher", "publisher"), ("Title", "title"), ("URL", "url"), ("Checked on", "checked"), ("Scope verified", "scope")],
                     src_rows, urls)
    pages["sources.html"] = page(data, "sources.html", "Official sources",
                                 "Every source used on this sub-site, with check date and verified scope. A link is a reference for manual review, not a blanket certification.", src_body)

    flag_body = (
        '<div class="notice warning"><strong>Flagged for Review:</strong> values that could not be confirmed from an official source are left blank - never inferred - and are listed here for manual review.</div>'
        + table("flags-table", "Flagged for Review",
                [("ID", "id"), ("Item", "item"), ("Detail", "detail"), ("Status", "status")], data["flags"], urls)
    )
    pages["flagged.html"] = page(data, "flagged.html", "Flagged for Review",
                                 "Unverified and needs-review items, with source links for manual review.", flag_body)

    return pages


def build():
    data = load_data()
    pages = render(data)
    for name, content in pages.items():
        (ROOT / name).write_text(content, encoding="utf-8")
    MANIFEST.write_text(json.dumps({"pages": PAGES}, indent=2) + "\n", encoding="utf-8")
    return pages


def check():
    data = load_data()
    pages = render(data)
    bad = [name for name, content in pages.items()
           if not (ROOT / name).is_file() or (ROOT / name).read_text(encoding="utf-8") != content]
    if bad:
        raise SystemExit("STALE rental pages (rerun rental/build.py): " + ", ".join(bad))
    print(f"OK: {len(pages)} rental pages match the deterministic build.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify committed pages match the build")
    args = parser.parse_args()
    if args.check:
        check()
    else:
        pages = build()
        print(f"Built {len(pages)} rental pages: " + ", ".join(sorted(pages)))
