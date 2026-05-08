# Phase instruction file

Phase boundary. Re-read SKILL.md if `PHASE_BOUNDARY=1` was emitted on stderr this turn.

## Your inputs (from stderr)

- `RUN_DIR`, `NEXT_PROFILE`, `PROFILE_CONFIG_PATH`, `OUTPUT_PATH`, `OUTPUT_SCHEMA`, `CYCLE`, `NEXT_SCRIPT`.

## Procedure

1. Read `<RUN_DIR>/state_1_run_c<CYCLE>_<NEXT_PROFILE>.json` — the shard pool your archetype produced in the prior phase. (You will not find shards from other archetypes; they are not yours to group.)
2. Read `PROFILE_CONFIG_PATH`. The same archetype priming applies here as in the prior phase. Hold the operative mode.
3. Read the mechanism file at `mechs/y3j7m4.md` — the recognition/grouping contract. Each archetype's mode of recognition is distinct; the mech describes them.
4. Group your shards into 3–6 cohesive clusters. Each `group_id` is a short label (3–60 chars) naming the *pattern* the shards share, in your archetype's voice.
5. Write the JSON file at `OUTPUT_PATH`. Schema at `OUTPUT_SCHEMA`. Required: `schema_version`, `session_id`, `archetype`, `cycle`, `shard_groups` (array of `{group_id, shards[]}`).
6. Run the validator: `python3 <NEXT_SCRIPT> --run-dir <RUN_DIR> --last-output <OUTPUT_PATH>`.

## Constraints

- 3–6 groups. 4–8 shards per group.
- Drop shards that do not fit any group your archetype recognizes. (Better than forcing them.)
- Stay inside the operative mode. Do not narrate the grouping process.
- No reading outside the listed inputs.
