#!/usr/bin/env python3
"""Recursive integrity/link/source-contract audit; NOT a renewed external fact check."""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nba_lab.engine import load_json, verify_receipts

EXCLUDED = {'.git', 'node_modules', '.artifacts', '__pycache__', '.venv'}
SOURCE_HOSTS = {
    'NBA-TEAMS': 'www.nba.com', 'NBA-PLAYERS': 'www.nba.com', 'NBA-STANDINGS': 'www.nba.com',
    'NBA-GAMES': 'www.nba.com', 'NBA-GLOSSARY': 'www.nba.com', 'NBA-INJURY': 'official.nba.com',
    'NBA-TERMS': 'www.nba.com', 'SCIPY-CORR': 'docs.scipy.org', 'SK-CAL': 'scikit-learn.org',
    'SK-TIME': 'scikit-learn.org', 'SM-HOLM': 'www.statsmodels.org',
    'KSA-PLAYERS': 'kansspelautoriteit.nl', 'GH-PAGES': 'docs.github.com', 'REPO': 'github.com',
}

SOURCE_HOSTS.update({'MKT-TOTO-RULES': 'portal-spa-api.toto.nl', 'MKT-TOTO-BUILDER': 'www.toto.nl', 'MKT-TOTO-BLOG': 'extra.toto.nl', 'MKT-BETMGM-BUILDER': 'help.betmgm.nl', 'MKT-BETMGM-QUOTES': 'help.betmgm.nl', 'MKT-FANATICS-OH': 'sportsbook.fanatics.com', 'MKT-ONEIDA': 'oneidacasinohotel.com', 'MKT-DK-PARLAY': 'support.draftkings.com', 'MKT-DK-ODDS': 'support.draftkings.com', 'MKT-UKGC': 'www.gamblingcommission.gov.uk', 'MKT-CRUKS': 'cruksregister.nl', 'MKT-CRUKS-CONTACT': 'cruksregister.nl', 'KSA-REGISTER': 'kansspelautoriteit.nl', 'NL-GOKSTOP': 'gokstop.nl'})

SOURCE_HOSTS.update({'SF-RATES': 'www.sf.gov', 'SF-RENT-INCREASES': 'www.sf.gov', 'SF-AB1482': 'www.sf.gov', 'SF-TENANT-RESOURCES': 'www.sf.gov', 'SF-DISCRIMINATION': 'www.sf.gov', 'CA-CIVIL-1947': 'leginfo.legislature.ca.gov', 'CA-CIVIL-827': 'leginfo.legislature.ca.gov', 'CA-COSTA-HAWKINS': 'leginfo.legislature.ca.gov', 'HUD-FHEO': 'www.hud.gov'})

# Rental sub-site (session arena/cab077aa-own7) — official government/legal hosts only.
SOURCE_HOSTS.update({
    'SFGOV-ANNUAL-26': 'www.sf.gov', 'SFGOV-RATES': 'www.sf.gov', 'SFGOV-RENT-INC': 'www.sf.gov',
    'SFGOV-RENTAL-LAWS': 'www.sf.gov', 'SFGOV-BANKED': 'www.sf.gov', 'SFGOV-PETITIONS': 'www.sf.gov',
    'SFGOV-RENTBOARD': 'www.sf.gov', 'SFGOV-RB-ABOUT': 'www.sf.gov', 'SFGOV-COUNSEL': 'www.sf.gov',
    'SFGOV-EVICTIONS': 'www.sf.gov',
    'CA-CC827': 'leginfo.legislature.ca.gov', 'CA-CC1947-12': 'leginfo.legislature.ca.gov',
    'CA-CC1954-52': 'leginfo.legislature.ca.gov', 'CA-CC1954-53': 'leginfo.legislature.ca.gov',
    'FHA-3604': 'uscode.house.gov',
})

# NFL research lab (session arena/a4e560bc-own7) — official NFL hosts only.
SOURCE_HOSTS.update({'NFL-STANDINGS': 'www.nfl.com', 'NFL-PASSING': 'www.nfl.com', 'NFL-RUSHING': 'www.nfl.com', 'NFL-RECEIVING': 'www.nfl.com', 'NFL-TEAM-OFF': 'www.nfl.com', 'NFL-TEAM-DEF': 'www.nfl.com', 'NFL-INJURY': 'www.nfl.com', 'NFL-SCHEDULE': 'www.nfl.com', 'NFL-TERMS': 'support.nfl.com', 'NFL-ROSTER': 'www.nfl.com'})

# NFL line-origination lab (session arena/20394b77-own7) — Week 10 snapshot sources.
SOURCE_HOSTS.update({'NFL-INJURIES': 'www.nfl.com', 'NFL-ROUNDUP': 'www.nfl.com', 'NFL-NEWS-WILLIS': 'www.nfl.com', 'NFL-DATES': 'www.nfl.com', 'NFL-LEGAL-TERMS': 'www.nfl.com', 'NFL-ODDS-PATH': 'www.nfl.com', 'NFL-DEPTH-PATH': 'www.nfl.com', 'AZ-DEPTH': 'www.azcardinals.com', 'CLE-DEPTH': 'www.clevelandbrowns.com', 'SF-DEPTH': 'www.49ers.com'})

# Rental pages from session arena/692da006-own7 (PR #19) — official government/legal hosts only.
SOURCE_HOSTS.update({'SF-RENTAL-LAWS': 'www.sf.gov', 'SF-RENT-INC': 'www.sf.gov', 'SF-NEWS-AGA': 'www.sf.gov', 'SF-BANKED': 'www.sf.gov', 'SF-HI-LICENSE': 'www.sf.gov', 'CA-AG-RENTCAPS': 'oag.ca.gov', 'CA-AG-TENANTS': 'oag.ca.gov', 'LEGINFO-CIV827': 'leginfo.legislature.ca.gov', 'LEGINFO-CIV1947-12': 'leginfo.legislature.ca.gov', 'LEGINFO-AB1482': 'leginfo.legislature.ca.gov', 'BLS-SF-CPI': 'blsmon1.bls.gov', 'GOVINFO-FHA': 'www.govinfo.gov', 'SF-RTC-EDC': 'evictiondefense.org'})


# NFL decision desk (session arena/382a833e-own7). It keeps its own source ledger so that the
# canonical NBA registry above is not rewritten by this scope; both ledgers are validated here.
DESK_SOURCE_FILE = 'nfl-desk/data/sources.json'
DESK_HOSTS = {
    'NFL-STANDINGS-2026': 'www.nfl.com', 'NFL-STANDINGS-DIV-2026': 'www.nfl.com',
    'NFL-TEAM-PASS-2026': 'www.nfl.com', 'NFL-INJURY-W10-2026': 'www.nfl.com',
    'NFL-SCHEDULE-2026': 'www.nfl.com', 'NFL-TIEBREAK-2026': 'www.nfl.com',
    'NFL-TERMS-LEGAL': 'www.nfl.com', 'NFL-NEWS-W10-ROUNDUP': 'www.nfl.com',
    'NFL-NEWS-WILLIS-IR': 'www.nfl.com', 'NFL-NEWS-NACUA-IR': 'www.nfl.com',
    'NFL-NEWS-DARNOLD': 'www.nfl.com', 'NFL-OPS': 'operations.nfl.com',
    'NFL-CLUB-DC-WAS': 'www.commanders.com', 'NFL-CLUB-DC-NYG': 'www.giants.com',
    'NFL-CLUB-DC-SEA': 'www.seahawks.com', 'SCIPY-PEARSON': 'docs.scipy.org',
    # Shared with the canonical registry; the desk cites the repository itself for project policy.
    'REPO': 'github.com',
}


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.refs, self.ids, self.rows, self.errors = [], set(), [], []
        self.in_body_rows = False
        self.row = None
        self.blank_depth = 0
        self.blank_text = ''
        self.h1_count = 0
        self.language = None
        self.title = False
        self.main_count = 0

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == 'html': self.language = attrs.get('lang')
        if tag == 'title': self.title = True
        if tag == 'h1': self.h1_count += 1
        if tag == 'main': self.main_count += 1
        if attrs.get('id'):
            if attrs['id'] in self.ids: self.errors.append(f'duplicate ID {attrs["id"]}')
            self.ids.add(attrs['id'])
        if tag == 'tbody': self.in_body_rows = True
        if tag == 'tr' and self.in_body_rows:
            self.row = {'refs': [], 'source_ids': attrs.get('data-source-ids', '').split(),
                        'detail': attrs.get('data-detail', '')}
        for key in ('href', 'src'):
            ref = attrs.get(key)
            if ref:
                self.refs.append(ref)
                if self.row is not None and tag == 'a' and key == 'href': self.row['refs'].append(ref)
        if tag == 'meta' and attrs.get('http-equiv', '').lower() == 'refresh':
            content = attrs.get('content', '')
            if ';url=' in content: self.refs.append(content.split(';url=', 1)[1])
        if tag == 'td' and attrs.get('data-empty') == 'true':
            self.blank_depth, self.blank_text = 1, ''
        elif self.blank_depth:
            self.blank_depth += 1
        if tag == 'a' and attrs.get('target') == '_blank':
            if not {'noopener', 'noreferrer'}.issubset(set(attrs.get('rel', '').split())):
                self.errors.append('new-tab link lacks noopener/noreferrer')

    def handle_data(self, data):
        if self.blank_depth: self.blank_text += data

    def handle_endtag(self, tag):
        if self.blank_depth:
            self.blank_depth -= 1
            if self.blank_depth == 0 and self.blank_text.strip(): self.errors.append('unknown cell is not truly blank')
        if tag == 'tr' and self.row is not None:
            self.rows.append(self.row); self.row = None
        if tag == 'tbody': self.in_body_rows = False


def site_paths():
    return sorted(p for p in ROOT.rglob('*.html') if not (set(p.relative_to(ROOT).parts) & EXCLUDED))


def validate_data(errors):
    registry = load_json('research/sources.json')
    ids = [r['id'] for r in registry]
    if len(ids) != len(set(ids)) or set(ids) != set(SOURCE_HOSTS):
        errors.append('primary-source registry IDs changed or duplicated')
    for row in registry:
        parsed = urlparse(row['url'])
        if parsed.scheme != 'https' or parsed.netloc != SOURCE_HOSTS.get(row['id']):
            errors.append(f'{row["id"]}: incorrect official primary source host')
        if not row.get('scope') or not row.get('checked_on') or not row.get('access'):
            errors.append(f'{row["id"]}: missing verification scope/date/access boundary')
        if row['id'] == 'REPO' and parsed.path != '/sassnarep3-star/Own7':
            errors.append('project source is not this repository')
    catalog, results, protocol = (load_json('research/'+x+'.json') for x in ('catalog','results','protocol'))
    if len(catalog['strategies']) != 8 or len(catalog['gates']) != 10:
        errors.append('strategy/gate inventory changed without an audit update')
    for kind in ('strategies','gates','flags'):
        for row in catalog[kind]:
            if not row.get('source_ids') or any(s not in ids for s in row['source_ids']):
                errors.append(f'{kind}:{row["id"]}: missing/unknown official reference')
    for row in catalog['strategies']:
        for metric in ('market_line','p_model','roi','clv','correlation'):
            if row.get(metric) is not None: errors.append(f'{row["id"]}: untested metric {metric} filled in')
    for row in catalog['flags']:
        if row.get('unverified_value') is not None: errors.append(f'{row["id"]}: unknown value is populated')
    if results['leaderboard'] or results['cash_rewards'] is not None:
        errors.append('unqualified leaderboard or cash rewards published')
    for forecast in results['demo']['forecasts']:
        if forecast['train_end'] >= forecast['date']: errors.append('chronology violation in ledger')
        for metric in ('market_decimal','edge','roi','clv','fair_model_decimal'):
            if forecast.get(metric) is not None: errors.append(f'unverified/withheld {metric} populated')
    if protocol['source_rights']['nba_derived_betting_prices_enabled'] or protocol['source_rights']['bulk_collection_enabled']:
        errors.append('source-rights no-go was bypassed')
    for row in results['correlations']:
        if row['kind'] == 'Not collected' and any(row.get(k) is not None for k in ('n','pearson','spearman')):
            errors.append('uncollected correlation inferred')
    try: verify_receipts()
    except ValueError as exc: errors.append(str(exc))
    for file in (ROOT/'verified/data').glob('*.json'):
        data=json.loads(file.read_text())
        if data.get('deprecated') is not True or data.get('rows') != []:
            errors.append(f'{file.name}: stale legacy source of truth still active')
        target=(file.parent/data.get('canonical','')).resolve()
        if not target.is_file(): errors.append(f'{file.name}: missing canonical pointer')
    urls = {r['id']: r['url'] for r in registry}
    # NFL desk ledger: separate file, separate exact-host map, merged only for row-link checking.
    try:
        desk_registry = json.loads((ROOT/DESK_SOURCE_FILE).read_text(encoding='utf-8'))['sources']
    except (OSError, ValueError) as exc:
        errors.append(f'{DESK_SOURCE_FILE}: unreadable ({exc})')
        desk_registry = []
    desk_ids = [r['id'] for r in desk_registry]
    if len(desk_ids) != len(set(desk_ids)):
        errors.append('nfl-desk: duplicate source IDs')
    if set(desk_ids) != set(DESK_HOSTS):
        errors.append('nfl-desk: source IDs do not match the registered official host map')
    for row in desk_registry:
        parsed = urlparse(row['url'])
        if parsed.scheme != 'https' or parsed.netloc != DESK_HOSTS.get(row['id']):
            errors.append(f'nfl-desk:{row["id"]}: incorrect official primary source host')
        if not row.get('scope') or not row.get('checked_on'):
            errors.append(f'nfl-desk:{row["id"]}: missing verification scope/date')
        if row.get('id') in urls and urls[row['id']] != row['url']:
            errors.append(f'nfl-desk:{row["id"]}: disagrees with the canonical registry URL')
    urls.update({r['id']: r['url'] for r in desk_registry})
    return urls


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-rebuild', action='store_true', help='Only for debugging; CI uses the full audit')
    parser.add_argument('--report', action='store_true', help='Write the local static-check evidence artifact')
    args=parser.parse_args()
    errors=[]
    registry=validate_data(errors)
    pages={path:Page(path) for path in site_paths()}
    for path, parsed in pages.items():
        parsed.feed(path.read_text(encoding='utf-8'))
        if parsed.h1_count != 1 or parsed.main_count != 1 or parsed.language != 'en' or not parsed.title:
            errors.append(f'{path.relative_to(ROOT)}: document semantics incomplete')
        errors.extend(f'{path.relative_to(ROOT)}: {err}' for err in parsed.errors)
    manifest=load_json('research/site-manifest.json')
    discovered={str(p.relative_to(ROOT)) for p in pages}
    if discovered != set(manifest['generated_html']): errors.append('unmanaged/missing HTML page outside canonical build')
    for name, digest in manifest['generated_html'].items():
        p=ROOT/name
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:
            errors.append(f'{name}: generated page hash mismatch')
    internal=external=row_count=0
    for path, parsed in pages.items():
        for ref in parsed.refs:
            url=urlparse(ref)
            if url.scheme:
                external+=1
                if url.scheme!='https': errors.append(f'{path.name}: non-HTTPS link {ref}')
                continue
            if url.netloc or ref.startswith('//'):
                errors.append(f'{path.name}: protocol-relative link');continue
            target=(path.parent/unquote(url.path)).resolve() if url.path else path
            if target.is_dir(): target/= 'index.html'
            internal+=1
            if not target.is_relative_to(ROOT) or not target.is_file():
                errors.append(f'{path.relative_to(ROOT)}: missing/unsafe link {ref}');continue
            if url.fragment and target.suffix=='.html':
                other=pages.get(target)
                if other is None or unquote(url.fragment) not in other.ids:
                    errors.append(f'{path.relative_to(ROOT)}: missing fragment {ref}')
        for row in parsed.rows:
            row_count+=1
            ids=row['source_ids']
            if not ids or any(s not in registry for s in ids):
                errors.append(f'{path.name}: table row missing registered primary source IDs')
                continue
            if any(registry.get(s) in row['refs'] for s in ids):
                continue
            # A row may delegate its link to a detail anchor, but only if that anchor renders the
            # same registered source URLs. Provenance stays visible; it is one click away instead
            # of repeated in every wide table.
            detail = row.get('detail') or ''
            detail_path = detail.split('#')[0]
            target = pages.get((ROOT/path.parent/detail_path).resolve()) if detail_path else None
            if not (detail and target is not None
                    and any(registry[s] in target.refs for s in ids)):
                errors.append(f'{path.name}: row lacks its official registered source link')
    # Local CSS dependencies, including the retired compatibility imports.
    for path in (ROOT/'assets/style.css',ROOT/'css/style.css',ROOT/'verified/assets/style.css'):
        for ref in re.findall(r'url\([\'"]?([^\)\'\"]+)',path.read_text()):
            if not urlparse(ref).scheme and not (path.parent/ref).resolve().is_file():
                errors.append(f'{path.name}: unresolved CSS asset {ref}')
    result=subprocess.run([sys.executable,'-m','nba_lab','run','--check'],cwd=ROOT,capture_output=True,text=True)
    research_ok = result.returncode == 0
    if not research_ok: errors.append(result.stdout+result.stderr)
    if not args.skip_rebuild:
        tracked=list(pages)+list((ROOT/'verified/data').glob('*.json'))+[ROOT/'research/site-manifest.json']
        before={p:p.read_bytes() for p in tracked}
        result=subprocess.run([sys.executable,str(ROOT/'scripts/build_site.py')],cwd=ROOT,capture_output=True,text=True)
        if result.returncode:errors.append(result.stdout+result.stderr)
        for p,content in before.items():
            if p.read_bytes()!=content:errors.append(f'{p.relative_to(ROOT)}: stale; deterministic rebuild changed file')
    report={'status':'passed' if not errors else 'failed','canonical_pages':len(manifest['canonical_pages']),
            'legacy_redirects':len(manifest['legacy_redirects']),'auxiliary_pages':len(manifest.get('auxiliary_pages',[])),'recursive_html_pages':len(pages),
            'table_body_rows':row_count,'internal_link_references':internal,'external_references':external,
            'registered_sources':len(registry),'unknown_values_blank':True if not errors else None,
            'research_reproduction':'passed' if research_ok else 'failed','errors':errors,
            'scope':'Integrity, contracts, semantics and local routing. Not external factual truth, source rights or profitability.'}
    if args.report:
        (ROOT/'research/audit/static-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    if errors:
        raise SystemExit('FAILED\n'+'\n'.join(' - '+e for e in errors))
    print(json.dumps(report,indent=2))
    print('OK: recursive site, fragments, registered row sources, blank rules, receipts and deterministic builds.')


if __name__=='__main__':
    main()
