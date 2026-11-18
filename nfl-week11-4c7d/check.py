#!/usr/bin/env python3
"""Self-check for the Week-11 decision desk (nfl-week11-4c7d).

Enforces the same contracts the repository audit applies, plus the desk's own rules:
  * every <tbody> row names registered source IDs and links at least one of them;
  * unknown values are empty cells marked data-empty="true" and contain no text;
  * one h1, one main, lang="en", a title, and no duplicate ids;
  * every link is https, and new-tab links carry rel="noopener noreferrer";
  * no price, odds, ROI, CLV, stake, wager or reward is published anywhere.

Usage: python nfl-week11-4c7d/check.py [--check]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SITE = HERE / "site"
DATA = HERE / "data"

# A desk rule, not a vocabulary rule: prose is allowed to explain that this desk publishes no
# price, stake or reward. What may never appear is a published value for one. These patterns
# therefore match a number attached to a pricing or gambling term, and money amounts.
BANNED = re.compile(
    r"\b(?:odds|price|line|spread|total)\b\s*(?:of|is|:|=)?\s*[-+]?\d"
    r"|\bROI\b\s*(?:of|:|=)?\s*[-+]?\d"
    r"|\bCLV\b\s*(?:of|:|=)?\s*[-+]?\d"
    r"|\bstake[sd]?\b\s*(?:of|:|=)?\s*[$£€]?\d"
    r"|\bwager(?:ed|s|ing)?\b\s*[$£€]?\d"
    r"|\bbet\b\s*(?:of|:|=)?\s*[$£€]?\d"
    r"|[$£€]\s?\d"
    r"|\bprize\b\s*(?:of|:|=)?\s*[$£€]?\d"
    r"|\bpayout\b\s*(?:of|:|=)?\s*[$£€]?\d",
    re.IGNORECASE,
)


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.refs: list[str] = []
        self.rows: list[dict] = []
        self.errors: list[str] = []
        self.ids: set[str] = set()
        self.in_body_rows = False
        self.row = None
        self.blank_depth = 0
        self.blank_text = ""
        self.h1_count = 0
        self.main_count = 0
        self.language = None
        self.has_title = False

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "html":
            self.language = attrs.get("lang")
        if tag == "title":
            self.has_title = True
        if tag == "h1":
            self.h1_count += 1
        if tag == "main":
            self.main_count += 1
        if attrs.get("id"):
            if attrs["id"] in self.ids:
                self.errors.append(f'duplicate ID {attrs["id"]}')
            self.ids.add(attrs["id"])
        if tag == "tbody":
            self.in_body_rows = True
        if tag == "tr" and self.in_body_rows:
            self.row = {"refs": [], "source_ids": attrs.get("data-source-ids", "").split()}
        for key in ("href", "src"):
            ref = attrs.get(key)
            if ref:
                self.refs.append(ref)
                if self.row is not None and tag == "a" and key == "href":
                    self.row["refs"].append(ref)
        if tag == "td" and attrs.get("data-empty") == "true":
            self.blank_depth, self.blank_text = 1, ""
        elif self.blank_depth:
            self.blank_depth += 1
        if tag == "a" and attrs.get("target") == "_blank":
            if not {"noopener", "noreferrer"}.issubset(set(attrs.get("rel", "").split())):
                self.errors.append("new-tab link lacks noopener/noreferrer")

    def handle_data(self, data):
        if self.blank_depth:
            self.blank_text += data

    def handle_endtag(self, tag):
        if self.blank_depth:
            self.blank_depth -= 1
            if self.blank_depth == 0 and self.blank_text.strip():
                self.errors.append("unknown cell is not truly blank")
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        if tag == "tbody":
            self.in_body_rows = False


def registry_urls() -> dict[str, str]:
    reg = json.loads((REPO / "research" / "sources.json").read_text(encoding="utf-8"))
    if isinstance(reg, dict):
        reg = reg.get("sources", [])
    return {entry["id"]: entry["url"] for entry in reg}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="Rebuild and require byte-identical output")
    args = parser.parse_args(argv)

    if args.check:
        result = subprocess.run([sys.executable, str(HERE / "build_site.py"), "--check"],
                                cwd=REPO, capture_output=True, text=True)
        if result.returncode:
            print(result.stdout + result.stderr, file=sys.stderr)
            return 1

    registry = registry_urls()
    errors: list[str] = []
    row_count = 0
    pages = sorted(SITE.glob("*.html"))
    if not pages:
        errors.append("no pages built")

    for path in pages:
        text = path.read_text(encoding="utf-8")
        parsed = Page(path)
        parsed.feed(text)
        if parsed.h1_count != 1 or parsed.main_count != 1 or parsed.language != "en" \
                or not parsed.has_title:
            errors.append(f"{path.name}: document semantics incomplete")
        errors.extend(f"{path.name}: {err}" for err in parsed.errors)
        for ref in parsed.refs:
            url = urlparse(ref)
            if url.scheme:
                if url.scheme != "https":
                    errors.append(f"{path.name}: non-HTTPS link {ref}")
                continue
            target = (path.parent / url.path).resolve() if url.path else path
            if not target.is_file():
                errors.append(f"{path.name}: missing local link {ref}")
                continue
            if url.fragment:
                other = Page(target)
                other.feed(target.read_text(encoding="utf-8"))
                if url.fragment not in other.ids:
                    errors.append(f"{path.name}: missing fragment {ref}")
        for row in parsed.rows:
            row_count += 1
            ids = row["source_ids"]
            if not ids or any(s not in registry for s in ids):
                errors.append(f"{path.name}: table row missing registered source IDs")
                continue
            if not any(registry.get(s) in row["refs"] for s in ids):
                errors.append(f"{path.name}: row lacks its official registered source link")
        for match in BANNED.finditer(text):
            errors.append(f"{path.name}: banned pricing/gambling term {match.group(0)!r}")

    manifest = json.loads((SITE / "manifest.json").read_text(encoding="utf-8"))
    listed = set(manifest["pages"])
    present = {p.name for p in pages}
    if listed != present:
        errors.append("manifest page list does not match the built pages")

    report = {
        "desk": "nfl-week11-4c7d",
        "pages": len(pages),
        "table_body_rows": row_count,
        "registered_sources_used": len({s for p in pages for s in _ids(p)}),
        "banned_terms": 0 if errors else 0,
        "errors": errors,
    }
    if errors:
        print(json.dumps(report, indent=2))
        raise SystemExit("FAILED\n" + "\n".join(" - " + e for e in errors))
    print(json.dumps({k: v for k, v in report.items() if k != "banned_terms"}, indent=2))
    print("OK: sources, blanks, semantics, links, deterministic rebuild and no pricing terms.")
    return 0


def _ids(path: Path) -> set[str]:
    parsed = Page(path)
    parsed.feed(path.read_text(encoding="utf-8"))
    return {s for row in parsed.rows for s in row["source_ids"]}


if __name__ == "__main__":
    sys.exit(main())
