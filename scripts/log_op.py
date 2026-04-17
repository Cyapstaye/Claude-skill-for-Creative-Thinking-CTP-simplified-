#!/usr/bin/env python3
"""log_op.py — E3. Incrementally append operation records to state_live.json.

Usage:
    python3 scripts/log_op.py --state-file <path> --op <name> --notes "<<=12 words>"

Replaces the pattern of Claude holding operation_log in its head until
end-of-phase. Each op is recorded atomically the moment it completes.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--op", required=True)
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    p = Path(args.state_file)
    if not p.exists():
        print(f"state file not found: {p}", file=sys.stderr)
        return 2
    state = json.loads(p.read_text())
    log = state.setdefault("operation_log", [])
    log.append(
        {
            "op": args.op,
            "notes": args.notes[:120],
            "timestamp": dt.datetime.utcnow().isoformat() + "Z",
            "index": len(log),
        }
    )
    # Atomic write.
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    os.replace(tmp, p)
    print(f"op_logged={args.op} total_ops={len(log)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
