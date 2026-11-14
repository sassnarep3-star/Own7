#!/usr/bin/env python3
"""Preview public static files only; no Git metadata, dependencies or directory listings."""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parent.parent
FOLDERS={'assets','css','js','data','research','docs','pages','verified','handoff','market-evidence','rental','nfl','nfl_origination','nfl_lab','nfl-availability-28ef','nfl-assurance-9580ac3f'}
EXTENSIONS={'.html','.css','.js','.svg','.json','.csv','.md','.py'}
ROOT_FILES={'README.md','COORDINATION.md'}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)

    def public_path(self):
        local=unquote(urlsplit(self.path).path)
        if local.startswith('/Own7/'):local=local[len('/Own7/'):]
        else:local=local.lstrip('/')
        if not local:local='index.html'
        target=(ROOT/local).resolve()
        manifest=json.loads((ROOT/'research/site-manifest.json').read_text())
        known=set(manifest['canonical_pages'])|set(manifest['legacy_redirects'])|ROOT_FILES
        if not target.is_relative_to(ROOT) or not target.is_file() or target.suffix not in EXTENSIONS:return None
        if local.split('/')[0] not in FOLDERS and local not in known:return None
        return target

    def translate_path(self,path):
        target=self.public_path()
        return str(target) if target else str(ROOT/'__not_a_public_file__')

    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        super().end_headers()

    def do_GET(self):
        if not self.public_path():self.send_error(404);return
        super().do_GET()

    def do_HEAD(self):
        if not self.public_path():self.send_error(404);return
        super().do_HEAD()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host',default='0.0.0.0');p.add_argument('--port',type=int,default=8080)
    args=p.parse_args();server=ThreadingHTTPServer((args.host,args.port),Handler)
    print(f'OWN7 public preview listening on {args.host}:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()
