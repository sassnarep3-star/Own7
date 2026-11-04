#!/usr/bin/env python3
"""Non-mutating link availability, NOT content verification or NBA data harvesting."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
LIMIT=65536


def inspect(source):
    result={'id':source['id'],'url':source['url'],'http_status':None,
            'availability':'unverified','content_verified':False,'data_updated':False}
    try:
        req=urllib.request.Request(source['url'],headers={'User-Agent':'Own7-Source-Health/1.0 (+https://github.com/sassnarep3-star/Own7)','Accept':'text/html'})
        with urllib.request.urlopen(req,timeout=25) as response:
            raw=response.read(LIMIT)
            body=raw.decode('utf-8',errors='replace')
            result.update(http_status=response.status,final_url=response.url,inspected_bytes=len(raw),body_limit_bytes=LIMIT)
            if 'Content Unavailable' in body or '<title>404' in body:
                result.update(availability='needs review',note='Possible soft 404 in limited response; manual official-source review needed.')
            else:
                result.update(availability='HTTP reachable',note='Limited availability check only. No numerical content, license or strategy evidence verified.')
    except urllib.error.HTTPError as exc:
        result.update(http_status=exc.code,availability='restricted / unverified' if exc.code in (401,403,429) else 'needs review',note=str(exc))
    except (OSError,TimeoutError,urllib.error.URLError) as exc:
        result.update(availability='unverified',note=str(exc))
    return result


def main():
    sources=json.loads((ROOT/'research/sources.json').read_text())
    with ThreadPoolExecutor(max_workers=3) as executor:
        rows=list(executor.map(inspect,sources))
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'mode':'Non-mutating primary-link availability only',
            'publication_blocking':False,'updates_source_facts':False,'bulk_collection':False,'rows':rows}
    out=ROOT/'.artifacts';out.mkdir(exist_ok=True)
    (out/'source-health.json').write_text(json.dumps(report,indent=2)+'\n')
    for row in rows:print(row['id'],row['http_status'],row['availability'])
    print('Saved .artifacts/source-health.json. Restrictions/failures remain unverified; no data/promotions/bets were made.')


if __name__=='__main__':main()
