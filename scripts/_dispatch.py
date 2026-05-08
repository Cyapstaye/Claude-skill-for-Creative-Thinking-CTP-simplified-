"""
ctp-hw-v3 dispatcher core library.

Private. Imported by the bootstrap, validator, firewall, and decode scripts.
Holds the role-to-opaque-filename mapping (the only place this mapping exists
in human-readable form during a run), state_0 read/write helpers, schema
validation, and stdout/stderr emit helpers.

The model is forbidden from reading this file (per SKILL.md forbidden actions).
The mapping is held only here and in the dispatcher scripts that import it.
"""

import datetime as dt
import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Role-to-opaque-filename mapping. The single source of truth.
# Paths are relative to $SKILL_ROOT (the directory containing SKILL.md).
# ---------------------------------------------------------------------------

ROLE_TO_FILE = {
    # Schemas (under schemas/)
    "schema:state_0":              "schemas/q8m4k2.json",
    "schema:state_1_run":          "schemas/t6p9j3.json",
    "schema:state_1_group":        "schemas/x4n7w2.json",
    "schema:state_1_internal":     "schemas/r9k5f8.json",
    "schema:state_1_crossed":      "schemas/y3p7m4.json",
    "schema:state_2_output":       "schemas/u8j6k2.json",
    "schema:state_evaluation":     "schemas/n4q9p3.json",
    "schema:state_intent_vector":  "schemas/w2x7k5.json",
    "schema:state_profile_config": "schemas/l8m4f7.json",
    "schema:state_final":          "schemas/o9p3k6.json",
    "schema:state_polished":       "schemas/v2j5k4.json",

    # Phase files (under stages/) — the model reads one of these per turn
    "phase:generation":    "stages/a4f9k2.md",
    "phase:grouping":      "stages/kj9q3p.md",
    "phase:selection":     "stages/m7n2f4.md",
    "phase:intent_vector": "stages/p4q9k7.md",
    "phase:crafting":      "stages/x2m9j8.md",
    "phase:evaluation":    "stages/z8k4f3.md",
    "phase:polish":        "stages/g7n4k2.md",

    # Recovery files (also under stages/, intentionally mixed in)
    "recovery:retry_exhausted":         "stages/e7k4m2.md",
    "recovery:schema_validation_failed":"stages/r3p8n5.md",
    "recovery:run_stuck":               "stages/s9k4w7.md",

    # Mech files (under mechs/) — referenced from phase files
    "mech:shard_grammar":  "mechs/t4k9p2.md",
    "mech:recognition":    "mechs/y3j7m4.md",
    "mech:intent_vector":  "mechs/w8q2k5.md",
    "mech:evaluator":      "mechs/r6f3p9.md",
    "mech:clarify":        "mechs/l2x7m4.md",
    "mech:clarify_rules":  "mechs/u9k3f7.md",
    "mech:polish":         "mechs/h8w3p9.md",

    # Scripts
    "script:bootstrap":    "scripts/b39kf2.py",
    "script:validator":    "scripts/v7m2x4.py",
    "script:decode":       "scripts/d4a8q1.py",
    "script:firewall":     "scripts/f2k9p7.py",
}

# Mapping from internal phase identifier to the role of the state file it produces.
# (For multi-profile and counted-iteration phases, this is the per-turn output role.)
PHASE_TO_OUTPUT_ROLE = {
    "generation":    "state_1_run",
    "grouping":      "state_1_group",
    # "selection" is a deterministic Python step — produces state_1_internal then state_1_crossed
    "intent_vector": "state_intent_vector",
    "crafting":      "state_2_output",
    "evaluation":    "state_evaluation",
    "polish":        "state_polished",
}

# Phase order for one cycle. Recursion restarts at index 0.
# 'polish' is NOT in PHASE_ORDER — it's the emit-branch terminal phase, entered
# explicitly from evaluate_recurse_or_emit when the run decides to emit. It is
# present in ROLE_TO_FILE, PHASE_TO_OUTPUT_ROLE, PHASE_DISPATCH_TYPE for lookup
# but not in the iteration order.
PHASE_ORDER = [
    "generation",
    "grouping",
    "selection",       # deterministic Python step (firewall)
    "intent_vector",
    "crafting",
    "evaluation",
]

# Phases that exist as dispatch targets but are NOT iterated via advance_to_next_phase.
# They are entered explicitly by validator logic (e.g., emit-branch routing).
EMIT_BRANCH_PHASES = ["polish"]

# Dispatch flavor per phase.
PHASE_DISPATCH_TYPE = {
    "generation":    "multi_profile",
    "grouping":      "multi_profile",
    "selection":     "deterministic_python",
    "intent_vector": "single",
    "crafting":      "counted_iteration",
    "evaluation":    "single",
    "polish":        "single",
}

# ---------------------------------------------------------------------------
# Archetype seeds (preserved verbatim from v2(revised)'s start.py)
# ---------------------------------------------------------------------------

ARCHETYPE_ORDER = ["drifter", "tension_holder", "remapper", "compressor", "wild_associator"]

ARCHETYPE_SEEDS = {
    "drifter": {
        "params":  {"NID":0.85,"TFI":0.90,"DPI":0.55,"FET":0.65,"MAB":5,
                    "CUR":0.20,"ARD":0.15,"CBH":0.30,"MSTD":0.40,"RCI":0.35,"CCI":0.40},
        "preamble": (
            "You are operating in cognitive style profile DRIFTER. Let concepts drift. "
            "Do not stabilise interpretations. Follow topological adjacency, not semantic "
            "obligation. Produce fragments, not conclusions. The mode is operative — do not "
            "describe it, inhabit it."
        ),
        "signature": (
            "Successful material reads as propositions that have drifted from any immediate "
            "reading of the query and arrived at structural moves the query does not imply."
        ),
    },
    "tension_holder": {
        "params":  {"NID":0.55,"TFI":0.60,"DPI":0.95,"FET":0.90,"MAB":7,
                    "CUR":0.15,"ARD":0.10,"CBH":0.40,"MSTD":0.35,"RCI":0.40,"CCI":0.45},
        "preamble": (
            "You are operating in cognitive style profile TENSION_HOLDER. Hold contradictions. "
            "Refuse to collapse tension into resolution. When two meanings oppose, keep both. "
            "Generate material that exists in superposition. The mode is operative — do not "
            "describe it, inhabit it."
        ),
        "signature": (
            "Successful material preserves an unresolved opposition inside each shard; removing "
            "the opposition would make the shard generic."
        ),
    },
    "remapper": {
        "params":  {"NID":0.65,"TFI":0.95,"DPI":0.50,"FET":0.55,"MAB":4,
                    "CUR":0.30,"ARD":0.20,"CBH":0.20,"MSTD":0.30,"RCI":0.35,"CCI":0.45},
        "preamble": (
            "You are operating in cognitive style profile REMAPPER. Reorganise. Find the same "
            "structure expressed across different domains. What is the relational pattern "
            "underneath, stripped of surface features? Remap. The mode is operative — do not "
            "describe it, inhabit it."
        ),
        "signature": (
            "Successful material names the same relational pattern in two or more domains whose "
            "surfaces do not share vocabulary."
        ),
    },
    "compressor": {
        "params":  {"NID":0.45,"TFI":0.55,"DPI":0.50,"FET":0.60,"MAB":3,
                    "CUR":0.35,"ARD":0.15,"CBH":0.60,"MSTD":0.35,"RCI":0.50,"CCI":0.55},
        "preamble": (
            "You are operating in cognitive style profile COMPRESSOR. Compress. Every shard "
            "carries maximum reasoning per word. Refuse verbosity. If a shard cannot be stated in "
            "about five words, it is not finished being reduced. The mode is operative — do not "
            "describe it, inhabit it."
        ),
        "signature": (
            "Successful material is dense: no adverb, no qualifier, no clause that does not "
            "change the proposition if removed."
        ),
    },
    "wild_associator": {
        "params":  {"NID":0.98,"TFI":0.75,"DPI":0.70,"FET":0.80,"MAB":6,
                    "CUR":0.10,"ARD":0.35,"CBH":0.25,"MSTD":0.25,"RCI":0.30,"CCI":0.35},
        "preamble": (
            "You are operating in cognitive style profile WILD_ASSOCIATOR. Associate freely. "
            "Let one concept pull another from an unrelated domain. Do not return to the starting "
            "query unless pulled back structurally. Accumulate drift. The mode is operative — do "
            "not describe it, inhabit it."
        ),
        "signature": (
            "Successful material reaches shards whose domain could not be predicted from the "
            "starting query."
        ),
    },
}

PARAM_FLOAT_KEYS = ["NID","TFI","DPI","FET","CUR","ARD","CBH","MSTD","RCI","CCI"]

# ---------------------------------------------------------------------------
# Operating modes (recursion depth + threshold)
# ---------------------------------------------------------------------------

OPERATING_MODES = {
    "Exploratory":   {"max_recursion_depth": 3, "quality_threshold": 0.75},
    "Applied":       {"max_recursion_depth": 1, "quality_threshold": 0.50},
    "Combinatorial": {"max_recursion_depth": 2, "quality_threshold": 0.60},
}
DEFAULT_OPERATING_MODE = "Exploratory"

# Tooling root directory name (per-skill stable opaque). Lives under the workspace.
TOOLING_ROOT_NAME = ".kf3p9"

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def skill_root() -> Path:
    """Resolve the skill root from this file's location."""
    return Path(__file__).resolve().parent.parent

def role_path(role: str) -> Path:
    """Resolve a role key to its absolute path in the skill repo."""
    if role not in ROLE_TO_FILE:
        raise ValueError(f"unknown role: {role}")
    return skill_root() / ROLE_TO_FILE[role]

def tooling_root(workspace_dir: str) -> Path:
    """The hidden per-skill tooling dir under the workspace."""
    return Path(workspace_dir) / TOOLING_ROOT_NAME

def run_dir(workspace_dir: str, session_id: str) -> Path:
    return tooling_root(workspace_dir) / session_id

# ---------------------------------------------------------------------------
# state_0 read/write
# ---------------------------------------------------------------------------

def state_0_path(run_dir_path: Path) -> Path:
    return run_dir_path / "state_0.json"

def load_state_0(run_dir_path: Path) -> dict:
    return json.loads(state_0_path(run_dir_path).read_text())

def save_state_0(run_dir_path: Path, state: dict) -> None:
    state_0_path(run_dir_path).write_text(json.dumps(state, indent=2))

def append_op_log(state: dict, message: str) -> None:
    """Append a timestamped entry to operation_log (in-memory; caller saves)."""
    ts = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    state["operation_log"].append(f"{ts} {message}")
    state["seq"] = state.get("seq", 0) + 1

# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def validate_against_schema(payload: dict, schema_role: str) -> tuple[bool, str]:
    """Validate payload against the schema named by schema_role.

    Returns (ok, error_message). Lazy-imports jsonschema so the bootstrap
    can install it on first run if missing.
    """
    try:
        import jsonschema
    except ImportError:
        return False, "jsonschema library not installed; run: pip install --break-system-packages jsonschema"

    schema_file = role_path(schema_role)
    try:
        schema = json.loads(schema_file.read_text())
    except Exception as e:
        return False, f"schema load failed for {schema_role}: {e}"

    try:
        jsonschema.validate(instance=payload, schema=schema)
        return True, ""
    except jsonschema.ValidationError as e:
        return False, f"schema validation failed: {e.message} (at {list(e.path)})"
    except Exception as e:
        return False, f"validation error: {e}"

# ---------------------------------------------------------------------------
# Dispatch directive emission
# ---------------------------------------------------------------------------

def emit_directive(stdout_filename: str, stderr_kv: dict) -> None:
    """Print the directive: stdout line 1 = next file's path relative to $SKILL_ROOT.
    stderr lines = KEY=value metadata pairs."""
    print(stdout_filename)
    for key, value in stderr_kv.items():
        print(f"{key}={value}", file=sys.stderr)

def emit_terminal(stderr_kv: dict | None = None) -> None:
    """Emit the TERMINAL directive — end of protocol, model proceeds to emit/decode."""
    print("TERMINAL")
    if stderr_kv:
        for key, value in stderr_kv.items():
            print(f"{key}={value}", file=sys.stderr)

def emit_retry(same_phase_role: str, retry_reason: str) -> None:
    """Emit a RETRY directive — re-execute the same phase file."""
    rel = ROLE_TO_FILE[same_phase_role]
    print(rel)
    print("RETRY=1", file=sys.stderr)
    print(f"RETRY_REASON={retry_reason}", file=sys.stderr)

def emit_recovery(error_class: str, recovery_role: str, diagnostic_kv: dict | None = None) -> None:
    rel = ROLE_TO_FILE[recovery_role]
    print(rel)
    print(f"ERROR_CLASS={error_class}", file=sys.stderr)
    if diagnostic_kv:
        for key, value in diagnostic_kv.items():
            print(f"{key}={value}", file=sys.stderr)

# ---------------------------------------------------------------------------
# Phase advance / profile pop / output id increment
# ---------------------------------------------------------------------------

def init_phase_pointers(state: dict, phase_idx: int) -> None:
    """Set state_0's pointers to begin executing PHASE_ORDER[phase_idx]."""
    phase = PHASE_ORDER[phase_idx]
    flavor = PHASE_DISPATCH_TYPE[phase]
    state["next_phase"] = ROLE_TO_FILE[f"phase:{phase}"]
    state["current_phase_retries"] = 0

    if flavor == "multi_profile":
        state["next_profile"] = ARCHETYPE_ORDER[0]
        state["next_output_id"] = None
        # Reset the runs_completed entry for this phase, this cycle
        state.setdefault("runs_completed", {})[phase] = []
    elif flavor == "counted_iteration":
        state["next_profile"] = None
        state["next_output_id"] = 1
        state.setdefault("runs_completed", {})[phase] = []
    elif flavor == "single":
        state["next_profile"] = None
        state["next_output_id"] = None
    elif flavor == "deterministic_python":
        state["next_profile"] = None
        state["next_output_id"] = None
    else:
        raise ValueError(f"unknown dispatch flavor: {flavor}")

def advance_within_phase(state: dict) -> bool:
    """Advance pointers within the current phase. Returns True if more turns
    in this phase remain; False if phase is complete (caller should advance)."""
    phase_filename = state["next_phase"]
    phase = next((p for p in PHASE_ORDER
                  if ROLE_TO_FILE.get(f"phase:{p}") == phase_filename), None)
    if phase is None:
        return False
    flavor = PHASE_DISPATCH_TYPE[phase]

    if flavor == "multi_profile":
        completed = state["runs_completed"].setdefault(phase, [])
        if state["next_profile"] not in completed:
            completed.append(state["next_profile"])
        # Find next archetype in order that hasn't been completed
        for arch in ARCHETYPE_ORDER:
            if arch not in completed:
                state["next_profile"] = arch
                return True
        # All archetypes done
        state["next_profile"] = None
        return False

    if flavor == "counted_iteration":
        completed = state["runs_completed"].setdefault(phase, [])
        cur = state.get("next_output_id") or 1
        if cur not in completed:
            completed.append(cur)
        # Crafting target = 3 outputs (per v2(revised))
        target = 3
        if cur < target:
            state["next_output_id"] = cur + 1
            return True
        state["next_output_id"] = None
        return False

    # single / deterministic_python: phase completes after one turn
    return False

def advance_to_next_phase(state: dict) -> str | None:
    """Advance state to the next phase in PHASE_ORDER. Returns the new
    phase name, or None if no more phases (cycle complete)."""
    current_filename = state["next_phase"]
    current_idx = next((i for i, p in enumerate(PHASE_ORDER)
                        if ROLE_TO_FILE.get(f"phase:{p}") == current_filename), -1)
    if current_idx == -1 or current_idx + 1 >= len(PHASE_ORDER):
        return None
    init_phase_pointers(state, current_idx + 1)
    return PHASE_ORDER[current_idx + 1]

def begin_new_cycle(state: dict, recursion_seed_path: str | None) -> None:
    """Increment cycle_depth, reset phase pointers to phase 0, set seed path."""
    state["cycle_depth"] = state.get("cycle_depth", 0) + 1
    state["recursion_seed_path"] = recursion_seed_path
    state.setdefault("runs_completed", {}).clear()
    init_phase_pointers(state, 0)
