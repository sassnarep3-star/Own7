p = 'nfl-forward-desk/build.py'
s = open(p).read()
old = '(see drift page."))'
new = '(see drift page.")))'
assert old in s, 'old not found'
s = s.replace(old, new, 1)
open(p, 'w').write(s)
import ast
ast.parse(open(p).read())
print('parses OK')
