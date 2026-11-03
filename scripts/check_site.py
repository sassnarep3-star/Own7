"""Check the GitHub Pages site (root *.html and pages/*.html).

1. Every local href/src resolves to a file in the repo (no broken internal links).
2. Every table row in a <tbody> contains at least one HTTPS source link, except
   rows explicitly marked class="method" (project-defined methodology, no data values).
3. Every local link resolves relative to the page that contains it.

Run: python3 scripts/check_site.py
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
PAGES = sorted(list(ROOT.glob("*.html")) + list((ROOT / "pages").glob("*.html")))


class Check(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.errors = []
        self.row = None  # None = not in a body row; True/False = has https source
        self.tbody = False
        self.method_row = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tbody":
            self.tbody = True
        if tag == "tr" and self.tbody:
            # Project-defined methodology rows (class="method") carry no data values.
            self.method_row = "method" in (attrs.get("class") or "").split()
            self.row = None if self.method_row else False
        if tag == "a" and self.row is not None and attrs.get("href", "").startswith("https://"):
            self.row = True
        for attr in ("href", "src"):
            value = attrs.get(attr, "")
            if not value or value.startswith(("#", "mailto:", "tel:")):
                continue
            if urlparse(value).scheme:
                continue
            target = (self.path.parent / value.split("#")[0]).resolve()
            if not target.is_file():
                self.errors.append(f"{self.path.relative_to(ROOT)}: broken link {value}")

    def handle_endtag(self, tag):
        if tag == "tr" and self.row is not None and not self.method_row:
            if not self.row:
                self.errors.append(f"{self.path.relative_to(ROOT)}: table body row lacks an HTTPS source link")
            self.row = None
        if tag == "tbody":
            self.tbody = False


errors = []
for path in PAGES:
    checker = Check(path)
    checker.feed(path.read_text(encoding="utf-8"))
    errors.extend(checker.errors)
if errors:
    raise SystemExit("\n".join(errors))
print(f"OK: {len(PAGES)} pages; all local links resolve; every table body row has an HTTPS source link.")
