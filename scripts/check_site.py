from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

OFFICIAL_HOSTS = {'www.nba.com', 'github.com', 'scikit-learn.org', 'docs.scipy.org'}

class Check(HTMLParser):
    def __init__(self, path):
        super().__init__(); self.path = path; self.errors = []; self.row = None; self.tbody = False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'tbody': self.tbody = True
        if tag == 'tr' and self.tbody: self.row = False
        if tag == 'a' and self.row is not None:
            source = urlparse(attrs.get('href', ''))
            if source.scheme == 'https' and source.hostname in OFFICIAL_HOSTS: self.row = True
        for attr in ('href','src'):
            value = attrs.get(attr, '')
            if value and not urlparse(value).scheme and not value.startswith(('#','//')):
                target = (self.path.parent / value.split('#')[0]).resolve()
                if not target.is_file(): self.errors.append(f'{self.path}: missing {value}')
    def handle_endtag(self, tag):
        if tag == 'tr' and self.row is not None:
            if not self.row: self.errors.append(f'{self.path}: table row lacks allowlisted primary HTTPS source')
            self.row = None
        if tag == 'tbody': self.tbody = False
errors=[]
for path in Path('.').rglob('*.html'):
    checker=Check(path); checker.feed(path.read_text()); errors.extend(checker.errors)
if errors: raise SystemExit('\n'.join(errors))
print('All local HTML links resolve and every table row has an allowlisted primary HTTPS source. Host checks do not verify claims.')
