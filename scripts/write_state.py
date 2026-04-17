#!/usr/bin/env python3
"""write_state.py — E1. Canonical state file writer.

Usage:
    python3 scripts/write_state.py --stage N --state-file <path>

Reads a raw JSON object from stdin, normalises it (sorted keys, 2-space
indent, trailing newline), and writes atomically to the target path.
Removes per-run serialisation drift between Claude invocations.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, required=True)
    parser.add_argument("--state-file", required=True)
    args = parser.parse_args()

    try:
        obj = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(f"stdin is not valid JSON: {e}", file=sys.stderr)
        return 2
    # Minimal shape stamping — the validator enforces the rest.
    obj.setdefault("schema_version", 1)
    if args.stage >= 1 and "phase_completed" not in obj:
        obj["phase_completed"] = {1: "INIT", 2: "DRIFT", 3: "REFACTOR", 4: "STABILIZE"}[args.stage]

    p = Path(args.state_file)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, p)
    print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
