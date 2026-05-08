#!/usr/bin/env python3
"""
ctp-hw-v2 firewall — deterministic Python step.

Aggregates per-archetype state_1_group_*.json into state_1_internal.json
(with shard_groups + selection_trace), then applies whitelist strip to
produce state_1_crossed.json. The schema for state_1_crossed forbids
any field not on the whitelist via additionalProperties:false.

Invoked by the validator after the grouping phase completes for all archetypes.

Usage:
    python3 <skill>/scripts/<firewall>.py --run-dir <abs_path>
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _dispatch as d


def parse_cli():
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", required=True)
    return p.parse_args()


def main():
    args = parse_cli()
    run_dir_path = Path(args.run_dir).resolve()
    state = d.load_state_0(run_dir_path)
    cycle = state.get("cycle_depth", 0)
    session_id = state["session_id"]

    # 1. Aggregate per-archetype groupings
    group_files = []
    for archetype in d.ARCHETYPE_ORDER:
        gf = run_dir_path / f"state_1_group_c{cycle}_{archetype}.json"
        if gf.exists():
            group_files.append((archetype, json.loads(gf.read_text())))

    if len(group_files) < 1:
        print("FATAL: no state_1_group files to aggregate", file=sys.stderr)
        sys.exit(3)

    # Stub aggregation: take all shard_groups across archetypes, append archetype tag
    # to each group_id to keep them distinguishable. A more sophisticated firewall
    # would synthesize a richer selection_trace.
    aggregated_groups = []
    considered = []
    for archetype, payload in group_files:
        considered.append(archetype)
        for group in payload.get("shard_groups", []):
            aggregated_groups.append({
                "group_id": f"{archetype}:{group['group_id']}",
                "shards": group["shards"],
            })

    # Cap group count to schema max
    aggregated_groups = aggregated_groups[:6]

    state_1_internal = {
        "schema_version": "1",
        "session_id": session_id,
        "cycle": cycle,
        "shard_groups": aggregated_groups,
        "selection_trace": {
            "considered_archetypes": considered,
            "rationale": (
                "Aggregated shard_groups from each archetype's grouping output. "
                "All groups preserved up to schema cap; archetype identity prefixed "
                "to group_id for traceability. Selection of crossing subset deferred "
                "to whitelist strip."
            ),
        },
    }

    # Validate state_1_internal against schema
    ok, err = d.validate_against_schema(state_1_internal, "schema:state_1_internal")
    if not ok:
        print(f"FATAL: state_1_internal failed schema: {err}", file=sys.stderr)
        sys.exit(3)

    internal_path = run_dir_path / f"state_1_internal_c{cycle}.json"
    internal_path.write_text(json.dumps(state_1_internal, indent=2))

    # 2. Whitelist strip: produce state_1_crossed
    state_1_crossed = {
        "schema_version": "1",
        "session_id": session_id,
        "cycle": cycle,
        "shard_groups": aggregated_groups,
    }

    ok, err = d.validate_against_schema(state_1_crossed, "schema:state_1_crossed")
    if not ok:
        print(f"FATAL: state_1_crossed failed schema: {err}", file=sys.stderr)
        sys.exit(3)

    crossed_path = run_dir_path / f"state_1_crossed_c{cycle}.json"
    crossed_path.write_text(json.dumps(state_1_crossed, indent=2))

    # 3. Write firewall audit record
    audit_dir = run_dir_path / "_audit"
    audit_dir.mkdir(exist_ok=True)
    audit_path = audit_dir / f"firewall_strip_c{cycle}.json"
    audit_path.write_text(json.dumps({
        "session_id": session_id,
        "cycle": cycle,
        "internal_fields_present": sorted(state_1_internal.keys()),
        "crossed_fields_present": sorted(state_1_crossed.keys()),
        "stripped_fields": sorted(set(state_1_internal.keys()) - set(state_1_crossed.keys())),
    }, indent=2))

    print(f"OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
