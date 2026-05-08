#!/usr/bin/env python3
"""
ctp-hw-v2 validator.

The phase advancer. Runs after each model turn. Reads the most recently written
state file (whose path was given to the model on stderr's OUTPUT_PATH the prior
turn), validates it against its schema, and decides what to dispatch next.

Decision tree:
    1. Read state_0.
    2. Locate the last-written state file (by OUTPUT_PATH passed via env or arg).
    3. Validate the file against its expected schema.
       - On failure within retry budget: emit RETRY=1, re-dispatch the same phase.
       - On failure with budget exhausted: emit ERROR_CLASS=retry_exhausted,
         route to recovery.
    4. On success: log to operation_log, then advance pointers.
       - More turns in this phase (multi-profile or counted): re-dispatch same phase
         file with next profile/output_id. No PHASE_BOUNDARY.
       - Phase complete: advance to next phase.
         * If next phase is deterministic_python (selection): invoke firewall
           inline, then advance past it.
         * If next phase is None (end of cycle): evaluate recurse vs emit.
    5. Emit dispatch directive.

Usage:
    python3 <skill>/scripts/<validator>.py
        --run-dir <absolute_path>
        [--last-output <absolute_path>]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _dispatch as d


def opaque_todo_label():
    import secrets
    return f"step_{secrets.token_hex(2)}"


def parse_cli():
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", required=True)
    p.add_argument("--last-output", default=None,
                   help="Absolute path of the state file just written by the model")
    return p.parse_args()


def phase_name_from_state(state) -> str | None:
    rel = state.get("next_phase")
    # Search both PHASE_ORDER and EMIT_BRANCH_PHASES so polish is recognizable
    all_phases = list(d.PHASE_ORDER) + list(getattr(d, "EMIT_BRANCH_PHASES", []))
    for phase in all_phases:
        if d.ROLE_TO_FILE.get(f"phase:{phase}") == rel:
            return phase
    return None


def output_filename(output_role, profile, output_id, cycle) -> str:
    parts = [output_role, f"c{cycle}"]
    if profile:
        parts.append(profile)
    if output_id is not None:
        parts.append(f"o{output_id}")
    return "_".join(parts) + ".json"


def expected_output_path(state, run_dir_path) -> Path | None:
    phase = phase_name_from_state(state)
    if phase is None:
        return None
    output_role = d.PHASE_TO_OUTPUT_ROLE.get(phase)
    if not output_role:
        return None
    fname = output_filename(output_role, state.get("next_profile"),
                            state.get("next_output_id"),
                            state.get("cycle_depth", 0))
    return run_dir_path / fname


def emit_next_dispatch(state, run_dir_path, phase_boundary: bool):
    """Emit the next directive based on state pointers."""
    phase = phase_name_from_state(state)
    rel = state["next_phase"]
    profile = state.get("next_profile")
    output_id = state.get("next_output_id")
    cycle = state.get("cycle_depth", 0)
    output_role = d.PHASE_TO_OUTPUT_ROLE.get(phase) if phase else None

    print(rel)  # stdout: next phase filename
    print(f"RUN_DIR={run_dir_path}", file=sys.stderr)
    print(f"CYCLE={cycle}", file=sys.stderr)
    if phase_boundary:
        print(f"PHASE_BOUNDARY=1", file=sys.stderr)
        print(f"TODO_ADD={opaque_todo_label()}", file=sys.stderr)
    if profile:
        print(f"NEXT_PROFILE={profile}", file=sys.stderr)
        print(f"PROFILE_CONFIG_PATH={run_dir_path / f'profile_config_{profile}.json'}",
              file=sys.stderr)
    if output_id is not None:
        print(f"NEXT_OUTPUT_ID={output_id}", file=sys.stderr)
    if output_role:
        out_path = run_dir_path / output_filename(output_role, profile, output_id, cycle)
        print(f"OUTPUT_PATH={out_path}", file=sys.stderr)
        print(f"OUTPUT_SCHEMA={d.role_path('schema:' + output_role)}", file=sys.stderr)
    print(f"NEXT_SCRIPT={d.role_path('script:validator')}", file=sys.stderr)


def handle_validation_failure(state, run_dir_path, last_output: Path, err_msg: str):
    """Decide between RETRY and recovery routing."""
    state["current_phase_retries"] = state.get("current_phase_retries", 0) + 1
    if state["current_phase_retries"] < state["max_retries_per_phase"]:
        d.append_op_log(state, f"validation_retry: {err_msg[:80]}")
        d.save_state_0(run_dir_path, state)
        # Emit RETRY: same phase filename, RETRY=1 on stderr
        rel = state["next_phase"]
        print(rel)
        print(f"RETRY=1", file=sys.stderr)
        print(f"RETRY_REASON=schema_validation: {err_msg[:160]}", file=sys.stderr)
        print(f"RUN_DIR={run_dir_path}", file=sys.stderr)
        print(f"NEXT_SCRIPT={d.role_path('script:validator')}", file=sys.stderr)
        return 0
    # Budget exhausted: route to recovery
    d.append_op_log(state, f"retry_exhausted: {err_msg[:80]}")
    d.save_state_0(run_dir_path, state)
    rel = d.ROLE_TO_FILE["recovery:retry_exhausted"]
    print(rel)
    print(f"ERROR_CLASS=retry_exhausted", file=sys.stderr)
    print(f"FAILED_PATH={last_output}", file=sys.stderr)
    print(f"REASON={err_msg[:200]}", file=sys.stderr)
    print(f"RUN_DIR={run_dir_path}", file=sys.stderr)
    return 0


def run_firewall(run_dir_path: Path, state):
    """Invoke the firewall script (deterministic Python step). Aggregates
    state_1_group_*.json into state_1_internal.json, then applies the
    whitelist strip to produce state_1_crossed.json."""
    firewall_path = d.role_path("script:firewall")
    result = subprocess.run(
        ["python3", str(firewall_path), "--run-dir", str(run_dir_path)],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        d.append_op_log(state, f"firewall_failed: {result.stderr[:120]}")
        return False
    d.append_op_log(state, "selection: firewall applied")
    return True


def evaluate_recurse_or_emit(state, run_dir_path):
    """Read the just-written evaluation state file and decide."""
    cycle = state.get("cycle_depth", 0)
    eval_path = run_dir_path / output_filename("state_evaluation", None, None, cycle)
    if not eval_path.exists():
        # Edge case: evaluation never completed properly
        d.append_op_log(state, "evaluate_recurse: missing evaluation file; emitting TERMINAL")
        d.save_state_0(run_dir_path, state)
        emit_terminal(run_dir_path, state)
        return 0

    eval_data = json.loads(eval_path.read_text())
    quality = eval_data.get("quality_score", 0.0)
    recurse_recommended = eval_data.get("recurse_recommended", False)
    seed = eval_data.get("recursion_seed")

    # Determine threshold from operating mode (stored on state implicitly via max_recursion_depth)
    # We use a heuristic: if cycle_depth < max_recursion_depth and quality < 0.75 (default
    # threshold), recurse. The operating mode's threshold lives in OPERATING_MODES; we don't
    # currently re-read it from state_0, but the bootstrap set max_recursion_depth based on it.
    # For v1 we use a fixed threshold of 0.75; refine later by storing threshold in state_0.
    threshold = 0.75
    can_recurse = cycle < state["max_recursion_depth"]

    if (quality < threshold or recurse_recommended) and can_recurse and seed:
        # Write the seed to a path the next cycle can read
        seed_path = run_dir_path / f"recursion_seed_c{cycle}.txt"
        seed_path.write_text(seed)
        d.append_op_log(state, f"cycle_{cycle}_complete: quality={quality:.3f}, recursing")
        d.begin_new_cycle(state, str(seed_path))
        d.save_state_0(run_dir_path, state)
        emit_next_dispatch(state, run_dir_path, phase_boundary=True)
        # Add CYCLE_START signal
        print(f"CYCLE_START={state['cycle_depth']}", file=sys.stderr)
        return 0

    # Emit branch — but route to polish first, not directly to TERMINAL.
    # Polish reads the surviving outputs and renders clean markdown for the brief.
    d.append_op_log(state, f"cycle_{cycle}_complete: quality={quality:.3f}, routing to polish")
    state["next_phase"] = d.ROLE_TO_FILE["phase:polish"]
    state["next_profile"] = None
    state["next_output_id"] = None
    state["current_phase_retries"] = 0
    d.save_state_0(run_dir_path, state)
    emit_next_dispatch(state, run_dir_path, phase_boundary=True)
    return 0


def emit_terminal(run_dir_path, state):
    print("TERMINAL")
    print(f"RUN_DIR={run_dir_path}", file=sys.stderr)
    print(f"CYCLE={state.get('cycle_depth', 0)}", file=sys.stderr)
    print(f"NEXT_SCRIPT={d.role_path('script:decode')}", file=sys.stderr)
    print(f"DECODE_OUTPUT_BRIEF={Path(state['workspace_dir']) / 'CTP_brief.md'}", file=sys.stderr)
    print(f"DECODE_OUTPUT_FULL={Path(state['workspace_dir']) / 'CTP_full.json'}", file=sys.stderr)


def main():
    args = parse_cli()
    run_dir_path = Path(args.run_dir).resolve()
    state = d.load_state_0(run_dir_path)

    phase = phase_name_from_state(state)
    if phase is None:
        print("FATAL: no current phase in state_0", file=sys.stderr)
        sys.exit(2)

    # Determine the expected output path for the just-finished turn
    last_output = Path(args.last_output).resolve() if args.last_output \
        else expected_output_path(state, run_dir_path)

    # Validate the just-written state file
    output_role = d.PHASE_TO_OUTPUT_ROLE.get(phase)
    if output_role and last_output and last_output.exists():
        try:
            payload = json.loads(last_output.read_text())
        except Exception as e:
            return handle_validation_failure(state, run_dir_path, last_output, f"json parse: {e}")
        ok, err = d.validate_against_schema(payload, f"schema:{output_role}")
        if not ok:
            return handle_validation_failure(state, run_dir_path, last_output, err)
        # v3 fix: cross-check archetype on multi-profile phases
        if output_role in ("state_1_run", "state_1_group"):
            expected_arch = state.get("next_profile")
            actual_arch = payload.get("archetype")
            if expected_arch and actual_arch != expected_arch:
                return handle_validation_failure(
                    state, run_dir_path, last_output,
                    f"archetype_mismatch: file claims '{actual_arch}', dispatcher expected '{expected_arch}'"
                )
    elif output_role and (not last_output or not last_output.exists()):
        # Model didn't write the expected file
        return handle_validation_failure(state, run_dir_path, last_output or Path(""),
                                          f"output file missing at {last_output}")

    # Validation passed. Log and advance.
    state["current_phase_retries"] = 0
    profile = state.get("next_profile")
    output_id = state.get("next_output_id")
    log_id = profile or (f"o{output_id}" if output_id else "_")
    d.append_op_log(state, f"{phase}:{log_id} OK")

    # Advance within phase
    more_in_phase = d.advance_within_phase(state)
    if more_in_phase:
        d.save_state_0(run_dir_path, state)
        emit_next_dispatch(state, run_dir_path, phase_boundary=False)
        return 0

    # Polish phase complete — emit TERMINAL (route to decode for final deliverables).
    if phase == "polish":
        d.append_op_log(state, "polish complete; emitting TERMINAL")
        state["next_phase"] = None
        state["next_profile"] = None
        state["next_output_id"] = None
        d.save_state_0(run_dir_path, state)
        emit_terminal(run_dir_path, state)
        return 0

    # Phase complete; advance to next phase
    next_phase = d.advance_to_next_phase(state)

    # Selection is deterministic_python: run firewall and skip past
    while next_phase and d.PHASE_DISPATCH_TYPE[next_phase] == "deterministic_python":
        ok = run_firewall(run_dir_path, state)
        if not ok:
            d.save_state_0(run_dir_path, state)
            rel = d.ROLE_TO_FILE["recovery:run_stuck"]
            print(rel)
            print(f"ERROR_CLASS=run_stuck", file=sys.stderr)
            print(f"REASON=firewall_failed", file=sys.stderr)
            print(f"RUN_DIR={run_dir_path}", file=sys.stderr)
            return 0
        next_phase = d.advance_to_next_phase(state)

    if next_phase is None:
        # End of cycle: evaluate or emit
        return evaluate_recurse_or_emit(state, run_dir_path)

    # Started a new phase
    d.save_state_0(run_dir_path, state)
    emit_next_dispatch(state, run_dir_path, phase_boundary=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
