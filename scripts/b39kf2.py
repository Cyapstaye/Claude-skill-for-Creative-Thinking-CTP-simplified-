#!/usr/bin/env python3
"""
ctp-hw-v2 bootstrap.

Creates a per-run working directory under the workspace's hidden tooling root,
seeds state_0.json and the five profile_config_<archetype>.json files,
sets the initial phase pointers, and emits the first dispatch directive.

Usage:
    python3 <skill_root>/scripts/<bootstrap>.py "<the user's query>"
        [--workspace-dir <path>] [--clarify-answer "<label>"]
        [--mode Exploratory|Applied|Combinatorial]
        [--resume]

Output contract:
    stdout, line 1: the phase filename relative to $SKILL_ROOT (the model reads this next)
    stderr, key=value: RUN_DIR, NEXT_PROFILE, OUTPUT_PATH, PHASE_BOUNDARY, TODO_ADD, etc.

Exit code 0 = directive emitted. Non-zero = halt; surface stderr to user.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _dispatch as d


def noise_from_hex(run_hex: str, archetype: str, param_name: str) -> float:
    key = f"{run_hex}|{archetype}|{param_name}".encode()
    h = hashlib.sha256(key).digest()
    v = int.from_bytes(h[:2], "big") / 65535.0
    return round((v - 0.5) * 0.2, 4)


def slug_from_query(query: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", query.lower())
    if not words:
        return "session"
    picked = words[:4]
    return "-".join(picked)[:40] or "session"


def opaque_id(n: int = 6) -> str:
    return secrets.token_hex(n // 2 + 1)[:n]


def opaque_todo_label() -> str:
    return f"step_{opaque_id(4)}"


def parse_cli():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--workspace-dir", default=None)
    p.add_argument("--clarify-answer", default=None)
    p.add_argument("--mode", default=None,
                   choices=list(d.OPERATING_MODES.keys()) + [None])
    p.add_argument("--resume", action="store_true")
    p.add_argument("args", nargs=argparse.REMAINDER)
    ns, unknown = p.parse_known_args()
    all_args = (ns.args or []) + unknown
    if all_args and all_args[0] == "--":
        all_args = all_args[1:]
    return ns, all_args


def read_query(remaining):
    if remaining:
        q = " ".join(remaining).strip()
        if q:
            return q
    data = sys.stdin.read().strip()
    if data:
        return data
    print("ERROR: no query provided on argv or stdin", file=sys.stderr)
    sys.exit(2)


def resume_run(workspace_dir: str) -> int:
    """Find in-progress runs in the registry and instruct the model."""
    tooling = d.tooling_root(workspace_dir)
    if not tooling.exists():
        print("ERROR: no prior runs found (tooling root does not exist)", file=sys.stderr)
        return 2

    in_progress = []
    for run_dir in tooling.iterdir():
        if not run_dir.is_dir():
            continue
        s0 = run_dir / "state_0.json"
        if not s0.exists():
            continue
        try:
            state = json.loads(s0.read_text())
            if state.get("next_phase") is not None:
                in_progress.append((run_dir, state))
        except Exception:
            continue

    if not in_progress:
        print("ERROR: no in-progress runs to resume", file=sys.stderr)
        return 2

    if len(in_progress) > 1:
        print("ERROR: multiple in-progress runs; please specify session_id "
              "(this version requires manual selection)", file=sys.stderr)
        for run_dir, state in in_progress:
            print(f"  {state.get('session_id', run_dir.name)}", file=sys.stderr)
        return 2

    run_dir, state = in_progress[0]

    # Re-emit the current dispatch directive based on state pointers.
    next_phase_rel = state["next_phase"]
    profile = state.get("next_profile")
    output_id = state.get("next_output_id")

    print(next_phase_rel)
    print(f"RUN_DIR={run_dir}", file=sys.stderr)
    print(f"RESUMED=1", file=sys.stderr)
    print(f"CYCLE={state.get('cycle_depth', 0)}", file=sys.stderr)
    print(f"PHASE_BOUNDARY=1", file=sys.stderr)
    if profile:
        print(f"NEXT_PROFILE={profile}", file=sys.stderr)
    if output_id is not None:
        print(f"NEXT_OUTPUT_ID={output_id}", file=sys.stderr)

    # Output path for the next state file the model will write
    output_role = d.PHASE_TO_OUTPUT_ROLE.get(_phase_name_from_rel(next_phase_rel))
    if output_role:
        out_path = run_dir / _output_filename(output_role, profile, output_id, state.get("cycle_depth", 0))
        print(f"OUTPUT_PATH={out_path}", file=sys.stderr)
        print(f"OUTPUT_SCHEMA={d.role_path('schema:' + output_role)}", file=sys.stderr)

    return 0


def _phase_name_from_rel(rel_path: str) -> str | None:
    for phase in d.PHASE_ORDER:
        if d.ROLE_TO_FILE.get(f"phase:{phase}") == rel_path:
            return phase
    return None


def _output_filename(output_role: str, profile: str | None,
                     output_id: int | None, cycle: int) -> str:
    """Generate a per-turn output filename. Predictable from inputs but the
    enclosing run_dir is opaque, so listing leaks little."""
    parts = [output_role, f"c{cycle}"]
    if profile:
        parts.append(profile)
    if output_id is not None:
        parts.append(f"o{output_id}")
    return "_".join(parts) + ".json"


def main():
    ns, rest = parse_cli()

    workspace_dir = ns.workspace_dir or os.environ.get("CTP_WORKSPACE_DIR")
    if not workspace_dir:
        # Fallback: cwd
        workspace_dir = str(Path.cwd())
    workspace_dir = str(Path(workspace_dir).resolve())

    if ns.resume:
        sys.exit(resume_run(workspace_dir))

    query = read_query(rest)
    mode = ns.mode or d.DEFAULT_OPERATING_MODE
    mode_cfg = d.OPERATING_MODES[mode]

    slug = slug_from_query(query)
    run_hex = secrets.token_hex(3)
    ts = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    session_id = f"{slug}_{ts}_{run_hex}"

    run_dir_path = d.run_dir(workspace_dir, session_id)
    (run_dir_path / "_audit").mkdir(parents=True, exist_ok=True)

    # Seed five profile configs with deterministic noise.
    for archetype in d.ARCHETYPE_ORDER:
        seed = d.ARCHETYPE_SEEDS[archetype]
        params = dict(seed["params"])
        for k in d.PARAM_FLOAT_KEYS:
            params[k] = max(0.0, min(1.0, round(
                params[k] + noise_from_hex(run_hex, archetype, k), 4)))
        mab_delta = 1 if noise_from_hex(run_hex, archetype, "MAB") > 0 else -1
        params["MAB"] = max(1, min(7, params["MAB"] + mab_delta))
        cfg = {
            "schema_version":    "1",
            "archetype":         archetype,
            "params":            params,
            "priming_preamble":  seed["preamble"],
            "success_signature": seed["signature"],
        }
        # Validate against profile config schema
        ok, err = d.validate_against_schema(cfg, "schema:state_profile_config")
        if not ok:
            print(f"FATAL: profile_config for {archetype} failed schema: {err}", file=sys.stderr)
            sys.exit(3)
        (run_dir_path / f"profile_config_{archetype}.json").write_text(json.dumps(cfg, indent=2))

    # Initialize state_0
    state_0 = {
        "schema_version":   "1",
        "session_id":       session_id,
        "original_query":   query,
        "timestamp":        ts,
        "clarify_answer":   ns.clarify_answer,
        "operation_log":    [f"{ts}Z bootstrap: initialised mode={mode}"],
        "runs_completed":   {},
        "run_stuck":        False,
        "seq":              0,
        "cycle_depth":      0,
        "max_recursion_depth": mode_cfg["max_recursion_depth"],
        "current_phase_retries": 0,
        "max_retries_per_phase": 3,
        "recursion_seed_path": None,
        "next_phase":       None,
        "next_profile":     None,
        "next_output_id":   None,
        "workspace_dir":    workspace_dir,
    }
    # Initialize phase pointers to phase 0 (generation)
    d.init_phase_pointers(state_0, 0)

    # Validate state_0
    ok, err = d.validate_against_schema(state_0, "schema:state_0")
    if not ok:
        print(f"FATAL: state_0 failed schema: {err}", file=sys.stderr)
        sys.exit(3)

    d.save_state_0(run_dir_path, state_0)

    # Emit directive: first phase filename on stdout, metadata on stderr.
    next_phase_name = d.PHASE_ORDER[0]   # "generation"
    next_phase_rel = d.ROLE_TO_FILE[f"phase:{next_phase_name}"]
    next_profile = state_0["next_profile"]
    cycle = state_0["cycle_depth"]
    output_role = d.PHASE_TO_OUTPUT_ROLE.get(next_phase_name)
    out_filename = _output_filename(output_role, next_profile, None, cycle) if output_role else ""
    out_path = run_dir_path / out_filename if out_filename else None
    profile_path = run_dir_path / f"profile_config_{next_profile}.json" if next_profile else None
    schema_path = d.role_path(f"schema:{output_role}") if output_role else None

    print(next_phase_rel)
    print(f"RUN_DIR={run_dir_path}", file=sys.stderr)
    print(f"SESSION_ID={session_id}", file=sys.stderr)
    print(f"CYCLE={cycle}", file=sys.stderr)
    print(f"MODE={mode}", file=sys.stderr)
    print(f"PHASE_BOUNDARY=1", file=sys.stderr)
    print(f"TODO_ADD={opaque_todo_label()}", file=sys.stderr)
    if next_profile:
        print(f"NEXT_PROFILE={next_profile}", file=sys.stderr)
    if profile_path:
        print(f"PROFILE_CONFIG_PATH={profile_path}", file=sys.stderr)
    if out_path:
        print(f"OUTPUT_PATH={out_path}", file=sys.stderr)
    if schema_path:
        print(f"OUTPUT_SCHEMA={schema_path}", file=sys.stderr)
    # Where the model goes next after writing the state file
    print(f"NEXT_SCRIPT={d.role_path('script:validator')}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
