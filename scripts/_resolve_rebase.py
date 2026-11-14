"""Resolve this branch's recurring rebase conflicts against origin/main.

Every conflict this branch hits is one of three kinds, so they are handled by rule
rather than by hand each time:

1. Append-only boards (COORDINATION.md): keep main's lines, then mine.
2. Generated files (*.html, research/results.json, research/site-manifest.json):
   take main's side; scripts/build_site.py regenerates them from the merged registry.
3. Additive source edits (research/sources.json, scripts/*.py, *.mjs): merge by
   meaning - for the JSON registry, union by ID; for code, keep both sides' blocks.
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

GENERATED = re.compile(r"^(?:[a-z0-9-]+\.html|research/(?:results|site-manifest)\.json)$")


def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=check)


def conflicted():
    out = git("diff", "--name-only", "--diff-filter=U").stdout.split()
    return out


def take(ref, path):
    git("checkout", ref, "--", path)


def split_markers(text):
    """Yield (before, main_side, my_side, after) for each conflict block, in order."""
    pattern = re.compile(r"<<<<<<< [^\n]*\n(.*?)\n=======\n(.*?)\n>>>>>>> [^\n]*\n", re.S)
    return pattern


def resolve_append_only(path):
    text = (ROOT / path).read_text()
    pattern = split_markers(text)
    resolved = pattern.sub(lambda m: m.group(1) + "\n\n" + m.group(2) + "\n", text)
    (ROOT / path).write_text(resolved)


def resolve_code(path):
    """Keep both sides of every conflict block: main first, then mine."""
    text = (ROOT / path).read_text()
    pattern = split_markers(text)
    resolved = pattern.sub(lambda m: m.group(1) + "\n" + m.group(2) + "\n", text)
    (ROOT / path).write_text(resolved)


def resolve_sources_json(path):
    """Union by ID: main's entries, plus any CFDD entry main does not already carry."""
    main = json.loads(git("show", "origin/main:research/sources.json").stdout)
    ours_text = (ROOT / path).read_text()
    # Recover our own entries from the last commit that had a clean, parseable registry.
    prev = None
    for ref in ("MERGE_HEAD", "ORIG_HEAD", "HEAD"):
        res = git("show", f"{ref}:research/sources.json", check=False)
        if res.returncode == 0:
            try:
                prev = json.loads(res.stdout)
                break
            except json.JSONDecodeError:
                continue
    if prev is None:
        prev = main
    main_ids = {r["id"] for r in main}
    merged = list(main)
    for row in prev:
        if row["id"].startswith("CFDD") and row["id"] not in main_ids:
            merged.append(row)
    ids = [r["id"] for r in merged]
    assert len(ids) == len(set(ids)), "duplicate source IDs after union"
    (ROOT / path).write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
    return len(main), len(merged)


def main():
    paths = conflicted()
    if not paths:
        print("no conflicts")
        return 0
    report = []
    for path in paths:
        if GENERATED.match(path):
            take("--ours", path)
            report.append((path, "main's generated copy (regenerated next)"))
        elif path == "COORDINATION.md":
            resolve_append_only(path)
            report.append((path, "append-only: main then mine"))
        elif path == "research/sources.json":
            before, after = resolve_sources_json(path)
            report.append((path, f"union by ID: {before} -> {after}"))
        else:
            resolve_code(path)
            report.append((path, "union: both sides kept"))
    git("add", "-A")
    for path, how in report:
        print(f"  {path}: {how}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
