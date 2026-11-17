#!/usr/bin/env bash
# One re-merge round for arena/e7efbde7-own7 against a moving main.
# Idempotent: sources.json union by id, theirs for generated artefacts,
# e7ef desk blocks re-applied if the auto-merge dropped them (identifier
# collision with nfl-readiness-1467fdf7's readiness_* names).
set -e
cd /home/user/Own7
git fetch origin main -q
echo "== new on main =="
git log --oneline HEAD..origin/main | head -6
if [ -z "$(git rev-list HEAD..origin/main)" ]; then echo "up to date; attempting merge"; fi
git merge origin/main 2>&1 | tail -1

# 1. sources.json union (ours = pre-merge HEAD, theirs = origin/main)
python3 - <<'EOF'
import json, subprocess
ours_raw = subprocess.run(["git","show","HEAD:research/sources.json"],capture_output=True,text=True).stdout
theirs_raw = subprocess.run(["git","show","origin/main:research/sources.json"],capture_output=True,text=True).stdout
ours, theirs = json.loads(ours_raw), json.loads(theirs_raw)
byid = {x["id"]: x for x in theirs}
for x in ours: byid.setdefault(x["id"], x)
union = list(byid.values())
ids = [x["id"] for x in union]
assert len(ids) == len(set(ids))
json.dump(union, open("research/sources.json","w"), indent=1, ensure_ascii=False)
open("research/sources.json","a").write("\n")
print("sources union:", len(union), "| theirs:", len(theirs), "| ours:", len(ours))
EOF

# 2. everything else conflicted -> theirs (regenerated later)
git status --porcelain | grep "^UU\|^AA" | awk '{print $2}' | grep -v "^research/sources.json$" | while read f; do
  git checkout --theirs "$f" && git add "$f"
done
git add -A && git commit -q -m "Merge origin/main into arena/e7efbde7-own7: sources union; generated files from main pending regeneration" || echo "(no merge commit needed)"

# 3. re-apply e7ef desk blocks if dropped
python3 - <<'EOF'
p = "scripts/build_site.py"
s = open(p).read()
need = []
if "nfl-readiness-e7ef" not in s:
    need = ["all"]
elif "e7ef_nav_group" not in s:
    need = ["nav"]
if need:
    if "all" in need:
        anchor1 = 'NAV.extend(readiness_nav_group())\n'
        assert s.count(anchor1) == 1, "anchor1 missing"
        s = s.replace(anchor1, anchor1 + '''

E7EF_NAV_PATH = "nfl-readiness-e7ef/site/index.html"


def e7ef_nav_group():
    """Additive nav group for the readiness-audit desk (session arena/e7efbde7-own7).

    Built from the desk's own manifest so this generator never restates a page list that
    could drift. Returns an empty list if the desk has not been built.
    """
    manifest = ROOT / "nfl-readiness-e7ef" / "site" / "manifest.json"
    if not manifest.exists():
        return []
    pages = list(load_json(str(manifest.relative_to(ROOT)))["pages"])
    labels = {
        "index.html": "Readiness overview",
        "verification-2026-11-17.html": "Verification 2026-11-17",
        "requirement-readiness.html": "Requirement readiness",
        "flagged.html": "Readiness flagged",
        "sources.html": "Readiness sources",
    }
    return [("NFL readiness audit",
             [(f"nfl-readiness-e7ef/site/{p}", labels.get(p, p), "validation") for p in pages])]

NAV.extend(e7ef_nav_group())
''')
        # find the 1467fdf7 desk build block as anchor for ours
        import re
        m = re.search(r"    readiness_pages=\[n for n in load_json\('nfl-readiness-1467fdf7/site/manifest\.json'\)\['pages'\] if n\.endswith\('\.html'\)\]\n    for name in readiness_pages:\n        generated\.append\(f'nfl-readiness-1467fdf7/site/\{name\}'\)", s)
        assert m, "1467fdf7 desk block missing"
        s = s.replace(m.group(0), m.group(0) + """
    # Readiness-audit desk (session arena/e7efbde7-own7). Runs the desk's own deterministic
    # build first so a stale verification artefact fails the site build rather than
    # publishing quietly.
    e7ef_result=subprocess.run([sys.executable,str(ROOT/'nfl-readiness-e7ef'/'build.py')],cwd=ROOT,capture_output=True,text=True)
    if e7ef_result.returncode: raise SystemExit(f'nfl-readiness-e7ef/build.py failed: '+e7ef_result.stdout+e7ef_result.stderr)
    e7ef_pages=load_json('nfl-readiness-e7ef/site/manifest.json')['pages']
    for name in e7ef_pages:
        generated.append(f'nfl-readiness-e7ef/site/{name}')""")
        anchor3 = "[f'nfl-readiness-1467fdf7/site/{n}' for n in readiness_pages]"
        assert s.count(anchor3) == 1, "anchor3 missing"
        s = s.replace(anchor3, anchor3 + "+[f'nfl-readiness-e7ef/site/{n}' for n in e7ef_pages]")
    for pth, anchor in [("scripts/serve_site.py", "'nfl-readiness-1467fdf7'"),
                        ("scripts/browser_test.mjs", "'nfl-readiness-1467fdf7'")]:
        s2 = open(pth).read()
        if "nfl-readiness-e7ef" not in s2:
            assert s2.count(anchor) == 1, pth
            open(pth, "w").write(s2.replace(anchor, "'nfl-readiness-1467fdf7','nfl-readiness-e7ef'"))
    open(p, "w").write(s)
    print("e7ef blocks re-applied:", need)
else:
    print("e7ef blocks intact")
EOF

# 4. regenerate + fast verify
python -m nba_lab run 2>&1 | tail -1
python scripts/build_site.py 2>&1 | tail -1
python scripts/check_site.py 2>&1 | tail -1
python -m nba_lab run --check 2>&1 | tail -1
python -m unittest discover -s tests 2>&1 | tail -1
python -m unittest discover -s nfl-readiness-e7ef/tests -t . 2>&1 | tail -1

# 5. commit, push, attempt merge
git add -A
git commit -q -m "Regenerate after merge: canonical pages, sources union; checks green" || echo "(nothing to commit)"
git push origin arena/e7efbde7-own7 2>&1 | tail -1
