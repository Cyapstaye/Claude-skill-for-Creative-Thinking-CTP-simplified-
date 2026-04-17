#!/usr/bin/env python3
"""compress_check.py — F6. Verify a three-line blend or a stable_core for
compression rules.

Usage:
    python3 scripts/compress_check.py --kind blend <file>
    python3 scripts/compress_check.py --kind stable_core <file>

Exit code 0 on pass, 1 on fail.
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path


BLEND_KEYS = ("Proposition", "Mechanism", "Emergence")
CORE_KEYS = ("Proposition", "Mechanism", "Novelty", "Constraint", "Seed")


def _lines_by_key(text: str, keys: tuple[str, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        for k in keys:
            m = re.match(rf"^\s*{k}\s*:\s*(.+?)\s*$", line)
            if m:
                out[k] = m.group(1)
    return out


def _word_count(s: str) -> int:
    return len([w for w in re.split(r"\s+", s) if w])


def check(kind: str, text: str) -> tuple[bool, list[str]]:
    keys = BLEND_KEYS if kind == "blend" else CORE_KEYS
    max_words_per_line = 25 if kind == "blend" else 22
    found = _lines_by_key(text, keys)
    errs = []
    for k in keys:
        if k not in found:
            errs.append(f"missing line: {k}")
            continue
        n = _word_count(found[k])
        if n > max_words_per_line:
            errs.append(f"{k} line too long: {n} words > {max_words_per_line}")
        if n < 3:
            errs.append(f"{k} line too short: {n} words")
    return (not errs), errs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True, choices=["blend", "stable_core"])
    parser.add_argument("path")
    args = parser.parse_args()
    text = Path(args.path).read_text()
    ok, errs = check(args.kind, text)
    if ok:
        print("compress_check=pass")
        return 0
    for e in errs:
        print(f"FAIL: {e}", file=sys.stderr)
    print("compress_check=fail")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
