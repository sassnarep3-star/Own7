#!/usr/bin/env python3
"""Bounded, explicitly dispatched official-source snapshot collector.

No scheduler, recursive crawl, odds collection, authentication bypass or wagering.
Run only after reviewing publisher terms/rights. Raw responses stay in the CI
artifact, not the public site. Public outputs are small factual transcriptions
with a response hash, UTC retrieval time, source URL and explicit parser scope.
A successful HTTP request alone never establishes factual verification.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
import urllib.request
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / 'nfl/sources/registry.json'
ALLOWED_HOSTS = {'www.nfl.com', 'operations.nfl.com', 'www.patriots.com', 'www.detroitlions.com',
                 'www.giants.com', 'www.seahawks.com', 'www.baltimoreravens.com',
                 'www.miamidolphins.com', 'www.clevelandbrowns.com', 'www.azcardinals.com', 'www.commanders.com'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


class Tables(HTMLParser):
    """Read rendered HTML tables only; never execute scripts or infer missing cells."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None
        self.skip = 0
        self.headings = []
        self.heading = None

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.skip += 1
        if self.skip:
            return
        if tag == 'table':
            self.table = []
        elif tag == 'tr' and self.table is not None:
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = {'text': [], 'links': [], 'header': tag == 'th'}
        elif tag == 'a' and self.cell is not None:
            href = dict(attrs).get('href')
            if href:
                self.cell['links'].append(href)
        elif tag in ('h1', 'h2', 'h3'):
            self.heading = []

    def handle_data(self, data):
        if self.skip:
            return
        if self.cell is not None:
            self.cell['text'].append(data)
        if self.heading is not None:
            self.heading.append(data)

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in ('td', 'th') and self.cell is not None:
            self.cell['text'] = re.sub(r'\s+', ' ', ''.join(self.cell['text'])).strip()
            self.row.append(self.cell)
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            if self.row:
                self.table.append(self.row)
            self.row = None
        elif tag == 'table' and self.table is not None:
            self.tables.append(self.table)
            self.table = None
        elif tag in ('h1', 'h2', 'h3') and self.heading is not None:
            self.headings.append(re.sub(r'\s+', ' ', ''.join(self.heading)).strip())
            self.heading = None


class HttpFinal:
    """Keep every redirect on the original exact official host."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme != 'https' or urlparse(newurl).hostname != urlparse(req.full_url).hostname:
            raise ValueError(f'Off-host or non-HTTPS redirect: {newurl}')
        return urllib.request.Request(newurl, headers={'User-Agent': 'Own7-SourceAudit/1.0'})


def fetch(source):
    url = urlparse(source['url'])
    if url.scheme != 'https' or url.hostname not in ALLOWED_HOSTS:
        raise ValueError('Source host is not on the reviewed allowlist')
    request = urllib.request.Request(source['url'], headers={
        'User-Agent': 'Own7-SourceAudit/1.0 (bounded source verification; no wagering)',
        'Accept': 'text/html,application/xhtml+xml', 'Accept-Encoding': 'identity'})
    opener = urllib.request.build_opener(HttpFinal())
    with opener.open(request, timeout=45) as response:
        raw = response.read(12_000_001)
        if len(raw) > 12_000_000:
            raise ValueError('Response exceeds bounded audit limit')
        return raw, response.status, response.headers.get('Content-Type', ''), response.geturl()


def injury_rows(tables):
    rows = []
    for table in tables:
        header = [c['text'] for c in table[0]]
        if header != ['Player', 'Position', 'Injuries', 'Practice Status', 'Game Status']:
            continue
        for row in table[1:]:
            values = [c['text'] for c in row]
            if len(values) != 5:
                raise ValueError(f'Unexpected injury table width: {values}')
            rows.append(dict(zip(('player', 'position', 'injury', 'practice_status', 'game_status'), values)))
    return rows


def depth_rows(tables):
    rows = []
    for table in tables:
        for row in table:
            if len(row) < 2 or row[0]['header'] or not row[0]['text']:
                continue
            position = row[0]['text']
            if not re.fullmatch(r'[A-Z0-9 /-]{1,12}', position):
                continue
            # Preserve multi-player printed cells (including OR), with no invented rank.
            ranks = []
            for rank, cell in enumerate(row[1:], 1):
                if cell['text']:
                    ranks.append({'printed_column': rank, 'players': [cell['text']],
                                  'player_links': cell['links'], 'shared_listing': len(cell['links']) > 1})
            if ranks:
                rows.append({'position': position, 'listings': ranks})
    return rows


def collect(output, only=None, delay=1.0):
    output.mkdir(parents=True, exist_ok=True)
    registry = json.loads(REGISTRY.read_text())
    receipts, errors = [], []
    for source in registry:
        if only and source['id'] not in only:
            continue
        if source['kind'] not in ('injuries', 'depth'):
            continue
        record = {**source, 'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
                  'method': 'Single official HTTPS request; rendered HTML table parser',
                  'status': 'Unverified'}
        try:
            raw, status, content_type, final_url = fetch(source)
            parser = Tables()
            parser.feed(raw.decode('utf-8'))
            record.update({'http_status': status, 'content_type': content_type, 'final_url': final_url,
                           'response_sha256': digest(raw), 'response_bytes': len(raw), 'headings': parser.headings})
            if source['kind'] == 'injuries':
                rows = injury_rows(parser.tables)
                record['row_count'] = len(rows)
                if not rows:
                    raise ValueError('No injury rows: page access may be restricted or markup changed')
                (output / 'injuries.json').write_text(canonical(rows))
            else:
                rows = depth_rows(parser.tables)
                record['row_count'] = len(rows)
                if not rows:
                    raise ValueError('No depth rows: page access may be restricted or markup changed')
                (output / (source['id'].lower() + '.json')).write_text(canonical(rows))
            record['status'] = 'Captured; awaiting independent rendered-source comparison'
            (output / (source['id'].lower() + '.html')).write_bytes(raw)
        except Exception as exc:
            record['error'] = str(exc)
            errors.append(source['id'] + ': ' + str(exc))
        receipts.append(record)
        time.sleep(delay)
    (output / 'receipts.json').write_text(canonical(receipts))
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=ROOT / '.artifacts/nfl-sources')
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--check', action='store_true', help='Offline registry and artifact integrity only')
    args = ap.parse_args()
    if args.check:
        errors = validate(args.output)
    else:
        errors = collect(args.output, args.only)
    if errors:
        raise SystemExit('\n'.join(errors))
    print('OK: bounded source operation completed; read receipts for actual verification scope.')


def validate(directory):
    registry = json.loads(REGISTRY.read_text())
    ids = [s['id'] for s in registry]
    errors = []
    if len(ids) != len(set(ids)):
        errors.append('Duplicate source ID')
    for s in registry:
        u = urlparse(s['url'])
        if u.scheme != 'https' or u.hostname not in ALLOWED_HOSTS:
            errors.append(s['id'] + ': invalid official source host')
    receipts = directory / 'receipts.json'
    if receipts.exists():
        for r in json.loads(receipts.read_text()):
            raw = directory / (r['id'].lower() + '.html')
            if raw.exists() and digest(raw.read_bytes()) != r.get('response_sha256'):
                errors.append(r['id'] + ': response hash mismatch')
    return errors


if __name__ == '__main__':
    main()
