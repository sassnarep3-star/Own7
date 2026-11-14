#!/usr/bin/env python3
"""Write-or-verify helper for the market-origination desk (session arena/64198b4b-own7).

`--check` re-derives every artifact in memory and fails if a committed file is missing or stale,
so CI proves the published tables really come from the saved evidence rather than from a
hand-edited file. Identical contract to `nfl-skill-cfdd/emit.py`; deliberately duplicated so this
desk cannot silently drift when another desk changes its helper.
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
        current = path.read_text(encoding="utf-8")
        if current != text:
            first = next((i for i, (a, b) in enumerate(zip(current, text)) if a != b),
                         min(len(current), len(text)))
            raise SystemExit(
                f"--check: {path} is stale (first difference at character {first}); "
                f"rerun the script without --check")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def emit_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise SystemExit(f"refusing to write an empty table: {path}")
    fields: list[str] = []
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
