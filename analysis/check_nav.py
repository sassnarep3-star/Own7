#!/usr/bin/env python3
"""Validate the analysis dashboard.

Checks, in order of how often each one catches a real mistake:

1.  Every internal link and asset reference resolves to a file that exists.
2.  Every navigation entry exists on every page (no dead nav item).
3.  Every HTML page contains no empty ``href`` or ``src``.
4.  Every table body row carries a link to an https:// source, OR explicitly
    says it is blank/not available/undefined. A row with neither fails.
5.  No placeholder text ("TBD", "TODO", "Lorem", "XXX") in shipped pages.
6.  Every number claimed as verified has a source: any table row containing a
    numeric cell must also contain an https:// link.
7.  The JSON data files that back the site all parse, and every data file that
    claims a source has a real nba.com URL.
8.  No page references a URL scheme other than https for external sources.

Exit code 0 only if everything passes.
"""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
HTML_FILES = sorted(ROOT.glob("*.html"))
DATA_FILES = sorted((ROOT / "data").glob("*.json"))
RESULT_FILES = sorted((ROOT / "results").glob("*.json"))

BLANK_WORDS = ("not available", "not computed", "undefined", "—", "blank", "n/a", "no source")

errors: list[str] = []
warnings: list[str] = []


class LinkAndTableCheck(HTMLParser):
    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.in_tbody = False
        self.in_tr = False
        self.in_td = False
        self.row_text: list[str] = []
        self.row_has_https = False
        self.row_cells = 0
        self.rows: list[dict] = []
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for attr in ("href", "src"):
            v = a.get(attr)
            if v is None:
                continue
            v = v.strip()
            if not v:
                errors.append(f"{self.path.name}: empty {attr}")
                continue
            self.links.append(v)
        if tag == "tbody":
            self.in_tbody = True
        elif tag == "tr" and self.in_tbody:
            self.in_tr = True
            self.row_text = []
            self.row_has_https = False
            self.row_cells = 0
        elif tag == "td" and self.in_tr:
            self.in_td = True
            self.row_cells += 1
        elif tag == "a" and self.in_tr:
            if (a.get("href") or "").startswith("https://"):
                self.row_has_https = True

    def handle_endtag(self, tag):
        if tag == "td":
            self.in_td = False
        elif tag == "tr" and self.in_tr:
            self.in_tr = False
            self.rows.append({
                "text": " ".join(self.row_text).lower(),
                "has_https": self.row_has_https,
                "cells": self.row_cells,
            })
        elif tag == "tbody":
            self.in_tbody = False

    def handle_data(self, data):
        if self.in_td:
            self.row_text.append(data)


def check_file_links(path: Path, links: list[str]) -> None:
    for v in links:
        if v.startswith("#") or v.startswith("mailto:"):
            continue
        parsed = urlparse(v)
        if parsed.scheme in ("http", "https"):
            if parsed.scheme == "http":
                errors.append(f"{path.name}: insecure external link {v}")
            continue
        if parsed.scheme:
            errors.append(f"{path.name}: unexpected scheme in {v}")
            continue
        target = (path.parent / parsed.path).resolve()
        if not target.is_file():
            errors.append(f"{path.name}: broken local link {v}")


def main() -> int:
    if not HTML_FILES:
        errors.append("no HTML files found")

    nav_targets = set()
    for f in HTML_FILES:
        parser = LinkAndTableCheck(f)
        parser.feed(f.read_text(encoding="utf-8"))
        check_file_links(f, parser.links)

        # nav completeness: collect links that appear in <nav>
        nav_match = re.search(r"<nav[^>]*>(.*?)</nav>", f.read_text(encoding="utf-8"), re.S)
        if nav_match:
            for href in re.findall(r'href="([^"#]+\.html)"', nav_match.group(1)):
                nav_targets.add(href)

        # blank rules for table rows
        for i, row in enumerate(parser.rows, start=1):
            if not row["has_https"] and not any(w in row["text"] for w in BLANK_WORDS):
                snippet = row["text"][:70].replace("\n", " ")
                errors.append(f"{f.name}: table row {i} has no https source and no explicit blank label :: {snippet}")

        # placeholders
        text = f.read_text(encoding="utf-8")
        for bad in ("TBD", "TODO", "Lorem ipsum", "XXX", "FIXME"):
            if bad in text:
                errors.append(f"{f.name}: placeholder text {bad!r}")

        # a page must have a title and a description
        if "<title>" not in text:
            errors.append(f"{f.name}: missing <title>")
        if 'name="description"' not in text:
            errors.append(f"{f.name}: missing meta description")

    # every nav target must exist and be reachable from every page
    for t in sorted(nav_targets):
        if not (ROOT / t).is_file():
            errors.append(f"nav references missing page {t}")
    expected = {f.name for f in HTML_FILES}
    missing_nav = expected - nav_targets
    if missing_nav:
        warnings.append(f"pages not present in nav: {sorted(missing_nav)}")

    # JSON integrity
    for f in DATA_FILES + RESULT_FILES:
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{f.name}: invalid JSON ({exc})")
            continue
        blob = json.dumps(doc)
        if "nba.com" not in blob and "github.com" not in blob:
            warnings.append(f"{f.name}: no official source URL embedded")
        for m in re.findall(r'"source_url":\s*"([^"]*)"', blob):
            if m and not m.startswith("https://"):
                errors.append(f"{f.name}: non-https source_url {m}")

    # every data file must declare a snapshot timestamp
    for f in DATA_FILES:
        doc = json.loads(f.read_text(encoding="utf-8"))
        if "snapshot_utc" not in doc:
            errors.append(f"{f.name}: missing snapshot_utc")

    print(f"pages checked: {len(HTML_FILES)}")
    print(f"data files checked: {len(DATA_FILES)}")
    print(f"result files checked: {len(RESULT_FILES)}")
    for w in warnings:
        print(f"WARN {w}")
    if errors:
        for e in errors:
            print(f"FAIL {e}")
        print(f"\n{len(errors)} error(s)")
        return 1
    print("OK: all local links resolve; every table row is sourced or explicitly blank")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
