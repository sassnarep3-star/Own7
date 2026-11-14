#!/usr/bin/env python3
"""Write-or-verify helper for the skill-separation desk (session cfdd5580).

`--check` re-derives every artifact in memory and fails if a committed file is missing or
stale, so CI can prove the published tables really come from the saved evidence.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

CHECK = False


def set_check(value: bool) -> None:
    global CHECK
    CHECK = bool(value)


def emit(path: Path, text: str) -> None:
    if CHECK:
        if not path.exists():
            raise SystemExit(f"--check: missing committed artifact {path}")
        with path.open("r", encoding="utf-8", newline="") as fh:
            current = fh.read()
        if current != text:
            first = next((i for i, (a, b) in enumerate(zip(current, text)) if a != b),
                         min(len(current), len(text)))
            raise SystemExit(
                f"--check: {path} is stale (first difference at character {first}); "
                f"rerun the script without --check")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def emit_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise SystemExit(f"refusing to write an empty table: {path}")
    # Union of keys in first-seen order, so a row that does not need a column (for example the
    # break-even case, which has no edge to detect) leaves it blank instead of crashing the build.
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    emit(path, buf.getvalue())


def emit_json(path: Path, payload) -> None:
    emit(path, json.dumps(payload, indent=2) + "\n")


def parse_args(description: str):
    import argparse
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--check", action="store_true",
                        help="verify the committed artifacts are current instead of writing them")
    args = parser.parse_args()
    set_check(args.check)
    return args
