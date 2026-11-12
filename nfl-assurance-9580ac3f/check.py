#!/usr/bin/env python3
"""Static assurance-site contract checks. Not external factual verification."""
from __future__ import annotations
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlparse
import build

ROOT = Path(__file__).resolve().parent


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs, self.ids, self.rows, self.errors = [], set(), [], []
        self.in_tbody = False
        self.row = None
        self.blank_depth = 0
        self.blank_text = ''
        self.h1 = self.main = 0
        self.lang = None
        self.title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html': self.lang = a.get('lang')
        if tag == 'title': self.title = True
        if tag == 'h1': self.h1 += 1
        if tag == 'main': self.main += 1
        if a.get('id'):
            if a['id'] in self.ids: self.errors.append('duplicate id ' + a['id'])
            self.ids.add(a['id'])
        if tag == 'tbody': self.in_tbody = True
        if tag == 'tr' and self.in_tbody:
            self.row = {'refs': [], 'ids': a.get('data-source-ids', '').split()}
        for key in ('href', 'src'):
            if a.get(key):
                self.refs.append(a[key])
                if self.row is not None and tag == 'a' and key == 'href': self.row['refs'].append(a[key])
        if tag == 'td' and 'data-empty' in a:
            self.blank_depth += 1
            self.blank_text = ''

    def handle_data(self, data):
        if self.blank_depth: self.blank_text += data

    def handle_endtag(self, tag):
        if tag == 'td' and self.blank_depth:
            self.blank_depth -= 1
            if self.blank_depth == 0 and self.blank_text.strip(): self.errors.append('data-empty cell is not blank')
        if tag == 'tr' and self.row is not None:
            self.rows.append(self.row); self.row = None
        if tag == 'tbody': self.in_tbody = False


def run():
    errors = []
    reg = build.sources()
    manifest = json.loads((ROOT / 'site/manifest.json').read_text())
    pages = {}
    for name in manifest['pages']:
        path = ROOT / 'site' / name
        if not path.is_file():
            errors.append('missing page ' + name); continue
        parsed = Page(); parsed.feed(path.read_text()); pages[name] = (path, parsed)
        if parsed.h1 != 1 or parsed.main != 1 or parsed.lang != 'en' or not parsed.title:
            errors.append(name + ': document semantics incomplete')
        errors.extend(name + ': ' + e for e in parsed.errors)
    row_count = 0
    for name, (path, parsed) in pages.items():
        for ref in parsed.refs:
            url = urlparse(ref)
            if url.scheme:
                if url.scheme != 'https': errors.append(name + ': non-HTTPS link ' + ref)
                continue
            if url.netloc or ref.startswith('//'):
                errors.append(name + ': protocol-relative link'); continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if target.is_dir(): target /= 'index.html'
            if not target.is_relative_to(ROOT.parent) or not target.is_file():
                errors.append(name + ': missing/unsafe link ' + ref); continue
            if url.fragment and target.suffix == '.html':
                other = pages.get(target.name)
                if other and unquote(url.fragment) not in other[1].ids:
                    errors.append(name + ': missing fragment ' + ref)
        for row in parsed.rows:
            row_count += 1
            ids = row['ids']
            if not ids or any(i not in reg for i in ids):
                errors.append(name + ': row missing registered source IDs')
            if not any(reg.get(i, {}).get('url') in row['refs'] for i in ids):
                errors.append(name + ': row lacks official registered source link')
    try:
        build.write_all(check=True)
    except SystemExit as exc:
        errors.append(str(exc))
    return {'status': 'passed' if not errors else 'failed', 'pages': len(pages), 'table_rows': row_count,
            'sources': len(reg), 'errors': errors,
            'scope': 'Local routing, row-source contract, blank cells and determinism; not external truth or rights.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', action='store_true')
    args = parser.parse_args()
    result = run()
    if args.report:
        (ROOT / 'audit').mkdir(exist_ok=True)
        (ROOT / 'audit/site-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    if result['errors']: raise SystemExit(1)
