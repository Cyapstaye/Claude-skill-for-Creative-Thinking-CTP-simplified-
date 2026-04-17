#!/usr/bin/env python3
"""start.py — initialise a CTP-40 run and emit the first stage token.

Usage:
    python3 scripts/start.py [--input "<payload>"] [--mode Exploratory|Applied|Combinatorial]

Called by SKILL.md pre-flight. Creates a per-run working directory and a
state_0.json with the verbatim input and run metadata. Prints the first
stage filename on stdout. The calling model then reads that file.

Environment:
    CTP_RUN_DIR   — root of run working directories (default: $CWD/.ctp40_run)
    CTP_INPUT     — verbatim input payload; overrides --input
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import sys
from pathlib import Path


FIRST_STAGE = "phase_7a3c9.md"

# Mode-weight table is held in one place (this script) so no stage file has to
# enumerate sibling modes. At init we write only the active row to
# mode_weights.json; the stabilize stage reads the file without ever seeing the
# other two modes' target thresholds.
_MODE_WEIGHTS = {
    "Exploratory": {
        "target_originality": 0.75,
        "viability_floor": 0.30,
        "prefer": "max_novelty",
        "max_recursion_depth": 3,
        "guilford_weights": {
            "originality": 0.30, "flexibility": 0.20,
            "elaboration": 0.15, "fluency": 0.10, "semantic_density": 0.25,
        },
    },
    "Applied": {
        "target_originality": 0.50,
        "viability_floor": 0.70,
        "prefer": "max_sum",
        "max_recursion_depth": 1,
        "guilford_weights": {
            "originality": 0.15, "flexibility": 0.15,
            "elaboration": 0.25, "fluency": 0.10, "semantic_density": 0.35,
        },
    },
    "Combinatorial": {
        "target_originality": 0.60,
        "viability_floor": 0.50,
        "prefer": "max_novelty_with_viability",
        "max_recursion_depth": 2,
        "guilford_weights": {
            "originality": 0.25, "flexibility": 0.25,
            "elaboration": 0.15, "fluency": 0.10, "semantic_density": 0.25,
        },
    },
}


def _slug_from(s: str, n: int = 3) -> str:
    """Kebab-case slug of up to n words from the first 40 chars."""
    head = re.sub(r"[^a-z0-9\s]+", " ", s.lower())[:60].strip()
    words = [w for w in head.split() if len(w) > 2][:n]
    if not words:
        words = ["run"]
    return "-".join(words)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=os.environ.get("CTP_INPUT", ""))
    parser.add_argument("--mode", default="Exploratory", choices=["Exploratory", "Applied", "Combinatorial"])
    parser.add_argument("--cycle-depth", type=int, default=0)
    args = parser.parse_args()

    if not args.input.strip():
        print("start.py: no input provided. Pass --input or set CTP_INPUT.", file=sys.stderr)
        return 2

    run_root = Path(os.environ.get("CTP_RUN_DIR", Path.cwd() / ".ctp40_run"))
    run_id = f"{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{secrets.token_hex(3)}"
    run_dir = run_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # For recursion: we never overwrite state_0; we write state_0_c<N>.
    cycle = args.cycle_depth
    state_0_name = "state_0.json" if cycle == 0 else f"state_0_c{cycle}.json"

    state_0 = {
        "schema_version": 1,
        "input_payload": args.input,
        "mode": args.mode,
        "payload_slug": _slug_from(args.input),
        "cycle_depth": cycle,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "started_at": dt.datetime.utcnow().isoformat() + "Z",
        "operation_log": [],
    }

    (run_dir / state_0_name).write_text(json.dumps(state_0, indent=2, sort_keys=True))

    # Write ONLY the active mode's weights. Stage 4 reads this file and never
    # sees a table of alternative modes — that way no stage file leaks the
    # existence of the other two modes.
    active_mode = dict(_MODE_WEIGHTS[args.mode])
    active_mode["mode"] = args.mode
    (run_dir / "mode_weights.json").write_text(json.dumps(active_mode, indent=2, sort_keys=True))

    # Expose CTP_RUN_DIR for downstream scripts via a .env-ish sidecar.
    (run_dir / "env").write_text(f"CTP_RUN_DIR={run_dir}\n")

    # Emit the first stage token on stdout. This is the only place the first
    # stage's filename is written down in the skill.
    print(FIRST_STAGE)
    print(f"RUN_DIR={run_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
