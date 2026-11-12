#!/usr/bin/env python3
"""Full baseline file coverage, exact line hashes and reproducible static checks.
A repository permalink proves file contents, not the truth of statements inside it.
"""
import ast
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
BASE = 'a989d67d9155b43ee2b93c39cbfdde54d8dd0b09'
OUT = ROOT / 'nfl-assurance-9580ac3f/audit'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run():
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE], cwd=ROOT, text=True).splitlines()
    records, errors = [], []
    for path in paths:
        raw = subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)
        rec = {'path': path, 'bytes': len(raw), 'sha256': sha(raw),
               'source_url': f'https://github.com/sassnarep3-star/Own7/blob/{BASE}/{path}',
               'scope': 'Every byte and every text line in the frozen baseline',
               'status': 'Repository checked', 'evidence_class': 'Repository contents; not independent factual verification'}
        try:
            text = raw.decode('utf-8')
            lines = text.splitlines()
            rec.update({'lines': len(lines), 'line_scope': f'1-{len(lines)}' if lines else 'empty',
                        'line_sha256': [sha(line.encode()) for line in lines],
                        'trailing_newline': text.endswith('\n')})
            if path.endswith('.json'):
                json.loads(text)
                rec['syntax'] = 'JSON parsed'
            elif path.endswith('.py'):
                ast.parse(text, filename=path)
                rec['syntax'] = 'Python AST parsed'
            elif path.endswith('.csv'):
                rows = list(csv.reader(io.StringIO(text)))
                widths = sorted({len(r) for r in rows})
                rec['syntax'] = f'CSV parsed; {len(rows)} records including header; widths {widths}'
                if len(widths) > 1:
                    errors.append(path + ': inconsistent CSV widths')
            elif path.endswith(('.yml', '.yaml')):
                rec['syntax'] = 'Text inventoried; YAML semantics exercised by GitHub Actions'
            elif path.endswith('.html'):
                rec['syntax'] = 'Text inventoried; recursive HTML checks run separately'
            else:
                rec['syntax'] = 'UTF-8 text inventoried'
        except UnicodeDecodeError:
            rec.update({'lines': None, 'line_scope': 'Binary bytes', 'line_sha256': [], 'syntax': 'Binary asset; byte hash only'})
        except (ValueError, SyntaxError, csv.Error) as exc:
            errors.append(path + ': ' + str(exc))
            rec['syntax'] = 'Failed'
        records.append(rec)
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'baseline_commit': BASE, 'files': len(records),
              'text_lines': sum(r.get('lines') or 0 for r in records),
              'bytes': sum(r['bytes'] for r in records), 'errors': errors,
              'files_review': records,
              'scope_boundary': 'Full line coverage means inventory/hash/syntax coverage, not independent scientific or legal verification of every assertion. Existing NBA/rental claims are preserved and not promoted to NFL evidence.'}
    (OUT / 'baseline-lines.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    report = run()
    print(json.dumps({k: v for k, v in report.items() if k != 'files_review'}, indent=2))
    if report['errors']:
        raise SystemExit(1)
