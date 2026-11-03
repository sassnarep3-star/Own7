#!/usr/bin/env python3
"""Verification gate for the verified-data site (verified/). Exit code 1 on any failure.

Checks:
  1. Every data row has an official source_url (allow-listed host).
  2. Rows with status 'verified' have non-empty values and an official source.
  3. Rows with status 'unverified' / 'reported-unverified' have blank value columns.
  4. Every internal link/asset in verified/*.html resolves to a file.
  5. Generated pages are up to date with data (rebuild and diff).
"""
import html.parser
import json
import pathlib
import re
import subprocess
import sys
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "verified"
DATA = DOCS / "data"

OFFICIAL_HOSTS = {
    "www.nba.com", "nba.com",
    "aglc.ca", "gamesenseab.ca", "www.selfexclusion.ca", "selfexclusion.ca",
    "playalberta.ca", "myhealth.alberta.ca", "www.albertahealthservices.ca",
    "github.com",
    "sassnarep3-star.github.io",  # this project's own Pages URL
}
VALUE_COLS = {"value_confirmed", "official_value", "number_or_detail", "correlation_value", "score", "roi", "clv", "sample_size", "n_observations"}
FILES = ["sources", "rules", "helplines", "strategies", "gates", "correlation", "leaderboard", "repo_review", "flagged"]
ALLOWED_STATUS = {"verified", "unverified", "reported-unverified", "Design choice"}

errors, warnings = [], []


def err(msg):
    errors.append(msg)


def check_data():
    for name in FILES:
        d = json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))
        cols = d["columns"]
        for row in d["rows"]:
            rid = row.get("id", row.get("rank", row.get("strategy_id", "?")))
            src = row.get("source_url", "")
            if not src:
                err(f"{name}:{rid} missing source_url")
            else:
                u = urlparse(src)
                if u.scheme != "https" or u.netloc not in OFFICIAL_HOSTS:
                    err(f"{name}:{rid} source_url not official: {src}")
            ref = row.get("reference_url")
            if ref and urlparse(ref).scheme != "https":
                err(f"{name}:{rid} reference_url not https")
            st = row.get("status", "")
            if st and st not in ALLOWED_STATUS and not st.startswith(("verified", "unverified", "reported", "Design", "Blocked", "Partly", "Not yet", "No ", "Unverified")):
                err(f"{name}:{rid} unknown status '{st}'")
            status_key = st.split(" ")[0] if st else ""
            if st == "verified":
                for c in cols:
                    if c in ("value_confirmed", "official_value", "number_or_detail") and not row.get(c):
                        err(f"{name}:{rid} verified but '{c}' is blank")
            if st.startswith("unverified") or st.startswith("reported-unverified"):
                for c in cols:
                    if c in VALUE_COLS and row.get(c, "") not in ("", None):
                        err(f"{name}:{rid} unverified row has value in '{c}'")
            if name == "strategies" and row.get("tested") == "No":
                for c in ("sample_size", "roi", "clv"):
                    if row.get(c, "") not in ("",):
                        err(f"{name}:{rid} untested strategy has metric '{c}'")
            if name == "correlation":
                if row.get("correlation_value", "") not in ("",):
                    err(f"{name}:{rid} correlation value present without verified computation")
        if name == "leaderboard":
            for row in d["rows"]:
                if row.get("status", "").startswith("No strategy") is False and row.get("strategy_id") != "(none)":
                    warnings.append(f"leaderboard row {row.get('strategy_id')} present; ensure gates passed")
    print(f"data files checked: {len(FILES)}")


class LinkParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in ("href", "src") and v:
                self.refs.append(v)


def check_links():
    pages = sorted(DOCS.glob("*.html"))
    checked = 0
    for page in pages:
        p = LinkParser()
        p.feed(page.read_text(encoding="utf-8"))
        for ref in p.refs:
            if ref.startswith(("http://", "https://", "mailto:", "tel:", "#")):
                continue
            target = ref.split("#")[0]
            if not target:
                continue
            path = (page.parent / target).resolve()
            checked += 1
            if not path.exists():
                err(f"{page.name}: broken link -> {ref}")
    print(f"pages: {len(pages)}, internal links checked: {checked}")


def check_rebuild_matches():
    before = {p: p.read_bytes() for p in DOCS.glob("*.html")}
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_verified_site.py")], check=True, capture_output=True)
    for p, b in before.items():
        if p.read_bytes() != b:
            err(f"{p.name} was stale; rebuild changed it")


def check_external_hosts():
    external = set()
    for page in DOCS.glob("*.html"):
        for m in re.finditer(r'href="(https?://[^"]+)"', page.read_text(encoding="utf-8")):
            external.add(urlparse(m.group(1)).netloc)
    print("external hosts linked from site:", ", ".join(sorted(external)))


if __name__ == "__main__":
    check_data()
    check_links()
    check_rebuild_matches()
    check_external_hosts()
    for w in warnings:
        print("WARN", w)
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    print("OK: all checks passed")
