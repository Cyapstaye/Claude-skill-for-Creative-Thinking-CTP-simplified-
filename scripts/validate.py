#!/usr/bin/env python3
"""validate.py — schema + structural validator for CTP-40 stage artifacts.

Usage:
    python3 scripts/validate.py <stage_number> <state_file> [--run-dir <dir>]

Exit codes:
    0 — validation passed; stdout prints the next-stage file token.
    1 — validation failed; stderr prints the first failing check and the
        op number to re-run, and stdout prints the recovery file token.

This script is the mechanical gate between stages. Stage files do NOT name
their successor. The validator does. That enforces the 'position in file
= position in execution' rule: Claude cannot discover the next stage's
identity except by passing this script.
"""
from __future__ import annotations
import json
import os
import re
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SCHEMA_DIR = SKILL_DIR / "schemas"

# Stage chain, keyed by the stage just completed. Opaque tokens.
NEXT_TOKEN = {
    1: "phase_b21f4.md",
    2: "phase_d41e2.md",
    3: "phase_e55aa.md",
    4: None,  # stage 4 ends or loops via start.py
}

# Per-run op budgets. C3 from For_v3.
MAX_OPS_PER_RUN = 150


def _die(msg: str, op_to_rerun: int | None = None) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    if op_to_rerun is not None:
        print(f"RERUN_OP: {op_to_rerun}", file=sys.stderr)
    # Recovery pointer goes to stdout so the phase file can read it.
    print("phase_recovery.md")
    sys.exit(1)


def _load_json(path: Path, label: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        _die(f"{label} file missing at {path}")
    except json.JSONDecodeError as e:
        _die(f"{label} is not valid JSON: {e}")


def _require(cond: bool, msg: str, op: int | None = None) -> None:
    if not cond:
        _die(msg, op)


def _is_triple_product(s: str) -> bool:
    """Match '[A] × [B] → [C]' with at least 2 non-trivial tokens per side."""
    # Permissive on brackets; strict on operators and token count.
    m = re.match(
        r"^\s*(.{3,}?)\s*×\s*(.{3,}?)\s*→\s*(.{3,}?)\s*$",
        s,
    )
    if not m:
        return False
    for part in m.groups():
        words = [w for w in re.split(r"\s+", part) if w]
        if len(words) < 2:
            return False
    return True


def _check_schema_minimal(state: dict, schema: dict, label: str) -> None:
    """Lightweight Draft-07 subset sufficient for this skill's needs.

    We intentionally avoid pulling in `jsonschema` to keep the validator
    a single zero-dep file. Full JSON Schema is overkill here.
    """
    required = schema.get("required", [])
    for k in required:
        _require(k in state, f"{label}: missing required key '{k}'")

    props = schema.get("properties", {})
    for k, rule in props.items():
        if k not in state:
            continue
        val = state[k]
        if "type" in rule:
            types = rule["type"] if isinstance(rule["type"], list) else [rule["type"]]
            py_types = {
                "string": str,
                "number": (int, float),
                "integer": int,
                "boolean": bool,
                "object": dict,
                "array": list,
                "null": type(None),
            }
            if not any(isinstance(val, py_types[t]) for t in types if t in py_types):
                _die(f"{label}: '{k}' has wrong type; expected {types}")
        if "const" in rule:
            _require(val == rule["const"], f"{label}: '{k}' must be {rule['const']!r}, got {val!r}")
        if "enum" in rule:
            _require(val in rule["enum"], f"{label}: '{k}' must be in {rule['enum']}, got {val!r}")
        if "pattern" in rule and isinstance(val, str):
            _require(
                re.search(rule["pattern"], val) is not None,
                f"{label}: '{k}' does not match pattern {rule['pattern']!r}",
            )
        if rule.get("type") == "array":
            if "minItems" in rule:
                _require(
                    isinstance(val, list) and len(val) >= rule["minItems"],
                    f"{label}: '{k}' must have >= {rule['minItems']} items, got {len(val) if isinstance(val, list) else 'n/a'}",
                )
            if "maxItems" in rule:
                _require(
                    isinstance(val, list) and len(val) <= rule["maxItems"],
                    f"{label}: '{k}' must have <= {rule['maxItems']} items, got {len(val) if isinstance(val, list) else 'n/a'}",
                )


def _check_stage_1(state: dict) -> None:
    # Bug-1: hard constraints ceiling enforced alongside schema minItems: 1.
    hard = state.get("constraint_lattice", {}).get("hard", [])
    _require(1 <= len(hard) <= 2, f"constraint_lattice.hard must be [1, 2] items; got {len(hard)}", op=5)

    # Operation-budget check, C3.
    _require(
        len(state.get("operation_log", [])) <= MAX_OPS_PER_RUN,
        f"operation_log exceeded MAX_OPS_PER_RUN ({MAX_OPS_PER_RUN})",
    )

    # Bug-5: timestamps required on each op.
    for i, op in enumerate(state.get("operation_log", [])):
        _require("timestamp" in op, f"operation_log[{i}] missing timestamp", op=10)


def _check_stage_2(state: dict) -> None:
    ef = state.get("entropy_field", {})
    candidates = ef.get("candidates", [])

    # B3: strict pattern on proposition, per candidate.
    for i, cand in enumerate(candidates):
        prop = cand.get("proposition", "")
        _require(_is_triple_product(prop), f"candidates[{i}].proposition fails [A] × [B] → [C] shape: {prop!r}", op=2)

    # Bug-2: fluency threshold depends on cycle_depth.
    cycle_depth = state.get("cycle_depth", 0)
    fluency_threshold = max(10, 20 - 5 * cycle_depth)
    fluency = ef.get("fluency_index", 0)
    _require(
        fluency >= fluency_threshold,
        f"fluency_index {fluency} below cycle-adjusted threshold {fluency_threshold}",
        op=9,
    )

    # Bug-5: timestamps on ops.
    for i, op in enumerate(state.get("operation_log", [])):
        _require("timestamp" in op, f"operation_log[{i}] missing timestamp", op=10)


def _check_stage_3(state: dict) -> None:
    cs = state.get("candidate_structures", [])
    for i, c in enumerate(cs):
        # Three-line form sanity: each of the three fields is non-empty
        # and is a single line (no newline inside).
        for k in ("proposition", "mechanism", "emergence"):
            _require(k in c and c[k].strip(), f"candidate_structures[{i}] missing {k}", op=5)
            _require("\n" not in c[k], f"candidate_structures[{i}].{k} must be one line", op=5)

    # Bug-3: recovery attempts capped.
    recovery_attempts = state.get("failure_residue_recovery_attempts", 0)
    _require(recovery_attempts <= 3, f"recovery_attempts {recovery_attempts} > cap 3", op=9)


def _check_stage_4(state: dict) -> None:
    sc = state.get("stable_core", {})
    for k in ("proposition", "mechanism", "novelty", "constraint", "seed"):
        _require(k in sc and sc[k].strip(), f"stable_core missing {k}")

    # C4: seed must reference a constraint by name from the lattice.
    lattice = state.get("constraint_lattice", {})
    constraint_names = set()
    for bucket in ("hard", "soft", "provisional"):
        for c in lattice.get(bucket, []):
            if isinstance(c, dict) and "name" in c:
                constraint_names.add(c["name"])
    seed = sc.get("seed", "")
    _require(
        any(name in seed for name in constraint_names),
        "stable_core.seed must name at least one constraint from constraint_lattice",
        op=8,
    )

    # Originality floor on recursion (C2): if prior cycle exists, compare.
    cycle_history = state.get("cycle_history", [])
    if len(cycle_history) >= 1 and state.get("action") == "recurse":
        prior = cycle_history[-1].get("stable_core", {}).get("originality_score", 0)
        curr = sc.get("originality_score", 0)
        _require(
            curr - prior > -0.05,
            f"originality regressed by more than 0.05 (prior={prior:.2f}, curr={curr:.2f}); force-emit rule triggered",
            op=9,
        )


def main() -> int:
    if len(sys.argv) < 3:
        _die("usage: validate.py <stage_number> <state_file> [--run-dir <dir>]")
    stage = int(sys.argv[1])
    state_path = Path(sys.argv[2])
    state = _load_json(state_path, f"state_{stage}")

    schema_path = SCHEMA_DIR / f"state_{stage}.schema.json"
    schema = _load_json(schema_path, f"state_{stage}.schema")

    _check_schema_minimal(state, schema, f"state_{stage}")

    checks = {1: _check_stage_1, 2: _check_stage_2, 3: _check_stage_3, 4: _check_stage_4}
    if stage in checks:
        checks[stage](state)

    # Success path: print the next-stage token. For stage 4, action decides.
    if stage == 4:
        if state.get("action") == "recurse":
            # Loop control is the responsibility of start.py on re-entry.
            print("phase_7a3c9.md")
        else:
            # Terminate silently; caller emits the user-facing files.
            print("END")
    else:
        nxt = NEXT_TOKEN[stage]
        if nxt is None:
            print("END")
        else:
            print(nxt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
