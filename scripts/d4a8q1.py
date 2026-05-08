#!/usr/bin/env python3
"""
ctp-hw-v2 decode — emit-time deliverable renderer.

Reads completed run state and writes:
    <workspace>/CTP_brief_<slug>.md   — short, dense final output (markdown)
    <workspace>/CTP_full_<slug>.json  — complete reasoning topology (JSON)

Invoked at TERMINAL by the model. The model passes the run dir; decode reads
state_0, all per-cycle state files, and renders both deliverables.

Usage:
    python3 <skill>/scripts/<decode>.py --run-dir <abs_path>
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _dispatch as d


def parse_cli():
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", required=True)
    return p.parse_args()


def slug_from_query(query: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", query.lower())
    if not words:
        return "session"
    return "-".join(words[:4])[:40] or "session"


def collect_cycle_state(run_dir_path: Path, cycle: int) -> dict:
    """Read every state file in this cycle and return as a dict."""
    cycle_state = {"cycle": cycle, "files": {}}
    for f in run_dir_path.glob(f"state_*_c{cycle}*.json"):
        try:
            cycle_state["files"][f.name] = json.loads(f.read_text())
        except Exception:
            cycle_state["files"][f.name] = {"_decode_error": "json_parse_failed"}
    return cycle_state


def main():
    args = parse_cli()
    run_dir_path = Path(args.run_dir).resolve()
    state_0 = d.load_state_0(run_dir_path)

    workspace_dir = Path(state_0.get("workspace_dir") or run_dir_path.parent.parent)
    slug = slug_from_query(state_0["original_query"])

    cycles_completed = state_0.get("cycle_depth", 0) + 1
    all_cycles = [collect_cycle_state(run_dir_path, c) for c in range(cycles_completed)]

    # Find the final cycle's evaluation file for the brief
    final_cycle = cycles_completed - 1
    eval_file = run_dir_path / f"state_evaluation_c{final_cycle}.json"
    eval_data = json.loads(eval_file.read_text()) if eval_file.exists() else {}

    # Find final crafted outputs from the final cycle
    final_outputs = []
    for output_id in (1, 2, 3):
        of = run_dir_path / f"state_2_output_c{final_cycle}_o{output_id}.json"
        if of.exists():
            try:
                payload = json.loads(of.read_text())
                final_outputs.append({
                    "output_id": output_id,
                    "final_form": payload.get("final_form", ""),
                    "cycle_origin": final_cycle,
                })
            except Exception:
                pass

    # ---- Brief (markdown) ----
    # In v3, the brief comes from the polish phase's polished_markdown verbatim.
    # If the polish file is missing (e.g., cycle errored before polish), fall back
    # to constructing the brief from raw final_forms as v2 did.
    brief_path = workspace_dir / f"CTP_brief_{slug}.md"
    polish_path = run_dir_path / f"state_polished_c{final_cycle}.json"
    polished_markdown = None
    if polish_path.exists():
        try:
            polish_data = json.loads(polish_path.read_text())
            polished_markdown = polish_data.get("polished_markdown")
        except Exception:
            polished_markdown = None

    if polished_markdown:
        # Polish phase ran. Write its output verbatim. Add only a small metadata
        # header that doesn't intrude on the polished content.
        header = (
            f"<!-- ctp-hw-v3 | mode={_mode_from_state(state_0)} | "
            f"cycles={cycles_completed} | session={state_0['session_id']} -->\n\n"
        )
        brief_path.write_text(header + polished_markdown)
    else:
        # Fallback: build brief from raw outputs (v2 behaviour)
        brief_lines = [
            f"# CTP Run — {slug}",
            f"",
            f"**Mode:** {_mode_from_state(state_0)} | **Cycles:** {cycles_completed} | "
            f"**Session:** `{state_0['session_id']}`",
            "",
            "---",
            "",
            "_(polish phase output unavailable; rendering from raw final_forms)_",
            "",
        ]
        if eval_data.get("presentation_recommendation"):
            brief_lines.append(f"**Presentation:** {eval_data['presentation_recommendation']}")
            brief_lines.append("")
        if final_outputs:
            for out in final_outputs:
                brief_lines.append(f"## Output {out['output_id']}")
                brief_lines.append("")
                brief_lines.append(out["final_form"])
                brief_lines.append("")
        else:
            brief_lines.append("(no final outputs produced)")
        if eval_data.get("rationale"):
            brief_lines.append("---")
            brief_lines.append("")
            brief_lines.append(f"**Rationale:** {eval_data['rationale']}")
        brief_path.write_text("\n".join(brief_lines))

    # ---- Full (JSON) ----
    full_path = workspace_dir / f"CTP_full_{slug}.json"
    full = {
        "session_id": state_0["session_id"],
        "original_query": state_0["original_query"],
        "mode": _mode_from_state(state_0),
        "cycles_completed": cycles_completed,
        "operation_log": state_0.get("operation_log", []),
        "final_outputs": final_outputs,
        "final_evaluation": eval_data,
        "cycles": all_cycles,
    }
    full_path.write_text(json.dumps(full, indent=2))

    print(f"BRIEF={brief_path}", file=sys.stderr)
    print(f"FULL={full_path}", file=sys.stderr)
    print(f"EMIT_OK=1", file=sys.stderr)
    return 0


def _mode_from_state(state_0):
    """Infer operating mode from max_recursion_depth (which the bootstrap set
    based on mode). This is a back-derivation; future versions should store the
    mode name explicitly in state_0."""
    depth = state_0.get("max_recursion_depth", 3)
    for name, cfg in d.OPERATING_MODES.items():
        if cfg["max_recursion_depth"] == depth:
            return name
    return "Unknown"


if __name__ == "__main__":
    sys.exit(main())
