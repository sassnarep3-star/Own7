#!/usr/bin/env python3
"""Reproduce the research-static job of .github/workflows/check.yml and record the results.

The command list is read from the workflow file itself (single source of truth), so this
desk cannot drift from CI. Each step is run sequentially in the repository root. The result
is written to nfl-review-1c6816a0/data/ci-run.json. The static build (build.py) only READS
that file; it never re-runs the checks, so `build.py --check` stays deterministic.

Usage: python nfl-review-1c6816a0/run_ci.py            (runs everything, ~minutes)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "check.yml"
OUT = ROOT / "nfl-review-1c6816a0" / "data" / "ci-run.json"
JOB = "research-static"
TIMEOUT_S = 900


def extract_commands(text: str, keep_self_checks: bool = False) -> list[dict]:
    """Parse the research-static job's run: blocks (step name + each command line)."""
    lines = text.splitlines()
    in_job = False
    steps: list[dict] = []
    name = ""
    in_run = False
    block_indent = None
    for ln in lines:
        if ln.startswith("  ") and not ln.startswith("   ") and ln.strip().endswith(":"):
            in_job = ln.strip()[:-1] == JOB
            in_run = False
            continue
        if not in_job:
            continue
        s = ln.strip()
        if s.startswith("- name:"):
            name = s[len("- name:"):].strip()
            in_run = False
            continue
        if s.startswith("run:"):
            rest = s[4:].strip()
            if rest.startswith("|"):
                in_run, block_indent = True, None
            elif rest:
                steps.append({"step": name, "command": rest})
            continue
        if in_run:
            if not s:
                continue
            indent = len(ln) - len(ln.lstrip())
            if block_indent is None:
                block_indent = indent
            if indent < block_indent or s.startswith("- name") or s.startswith("name:"):
                in_run = False
                continue
            steps.append({"step": name, "command": s})
    # Only the reproduction steps: stop before the git-cleanliness check.
    cut = next((i for i, x in enumerate(steps) if x["command"].startswith("git status")), len(steps))
    return [x for x in steps[:cut] if keep_self_checks or not is_self_check(x["command"])]


# The desk's own build check and unit tests READ this record. They cannot see their own result, so
# they are not recorded here; the CI job runs them after this record is written.
SELF_CHECK_MARKERS = ("nfl-review-1c6816a0/build.py", "nfl-review-1c6816a0/tests")


def is_self_check(command: str) -> bool:
    return any(marker in command for marker in SELF_CHECK_MARKERS)


def git_status() -> list[str]:
    out = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout
    return sorted(x for x in out.splitlines() if "nfl-review-1c6816a0" not in x)


def main() -> None:
    commands = extract_commands(WORKFLOW.read_text(encoding="utf-8"))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    before = git_status()
    results = []
    for i, item in enumerate(commands, 1):
        t0 = time.time()
        try:
            proc = subprocess.run(item["command"], shell=True, cwd=ROOT, env=env,
                                  capture_output=True, text=True, timeout=TIMEOUT_S)
            code, output = proc.returncode, (proc.stdout + proc.stderr)
        except subprocess.TimeoutExpired as exc:  # record, do not hide
            code, output = 124, f"TIMEOUT after {TIMEOUT_S}s " + str(exc.stdout or "")[-500:]
        tail = [x for x in output.strip().splitlines() if x.strip()][-1:] or [""]
        results.append({
            "n": i,
            "step": item["step"],
            "command": item["command"],
            "exit_code": code,
            "seconds": round(time.time() - t0, 1),
            "last_line": tail[0][:300],
        })
        print(f"[{i:02d}] exit={code} {item['command']}", flush=True)
    after = git_status()
    changed = sorted(set(after) ^ set(before))
    all_steps = extract_commands(WORKFLOW.read_text(encoding="utf-8"), keep_self_checks=True)
    doc = {
        "run_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "not_recorded_self_checks": [x["command"] for x in all_steps if is_self_check(x["command"])],
        "source_workflow": ".github/workflows/check.yml",
        "source_job": JOB,
        "commands_total": len(results),
        "commands_passed": sum(r["exit_code"] == 0 for r in results),
        "commands_failed": sum(r["exit_code"] != 0 for r in results),
        "worktree_changes_caused_by_run": changed,
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"passed={doc['commands_passed']} failed={doc['commands_failed']} worktree_changes={len(changed)}")


if __name__ == "__main__":
    main()
