# stage — INIT

You are now executing the first stage of this protocol. Complete the ten operations below in order; the validator at the end will print the filename of the next stage on its stdout.

---

## Load prior state

Read `${CTP_RUN_DIR}/state_0.json` (the path `scripts/start.py` created). Verify the keys `input_payload`, `mode`, `payload_slug`, `cycle_depth`, `run_dir`, and `run_id` are present. If any are missing, stop — pre-flight was skipped. Return to caller.

Copy `state_0.json` to `state_live.json` in the same directory. You will write incremental updates to `state_live.json` throughout this stage using `scripts/log_op.py`, and at the end the validator will atomically rename it to `state_1.json`.

---

## Goal of this stage

Dissolve the dominant framing of the input. Surface what is usually taken for granted. Produce a structured substrate — a **constraint lattice** plus a **flattened associative field** — that later work can pull from.

Everything produced in this stage must be compressed. Not terse for terseness's sake — **minimum length to carry a reasoning step**. If a proposition can be shortened without losing a reasoning step, shorten it.

Read only the two mechanism files this stage uses:

- `mechs/mech_constraint.md` — used by operations 4, 5, and 10.
- `mechs/mech_associative.md` — used by operations 8 and 9.

---

## The 10 operations

Execute in order. After each operation, run:

```
python3 scripts/log_op.py --state-file "${CTP_RUN_DIR}/state_live.json" --op "<op_name>" --notes "<≤12 words>"
```

The script timestamps and indexes the entry. Also write the operation's output fields back into `state_live.json` (merge, do not overwrite).

### 1. Parse the input to structural primitives.
Extract the atomic entities, the binary relations between them, and the functional roles each plays. Strip rhetoric. Output: `primitives = [ {entity, role, relates_to?} … ]`. Target 5–30 primitives. Fewer than 5 → input is too sparse; ask the user for more. Over 50 → you are over-tokenising; merge.

### 2. Identify dominant response paths.
Name the first-order framings an average responder would default to. Rank them by how immediately they surface. Output: `dominant_paths = [ "<compressed framing> (activation: 0.x)" … ]`. Expect 2–5.

### 3. Suppress the dominant response paths.
For each path in step 2, write a one-line inhibition note: `"<framing> → suppressed because <reason>"`. You are not erasing them; you are declaring them off-limits as defaults so remote candidates get oxygen.

### 4. Extract implicit assumptions.
Surface assumptions the input *takes for granted* — omitted roles, unstated causal directionality, assumed temporal ordering, assumed scope, assumed audience. Follow `mechs/mech_constraint.md §Extraction`.

Output: `implicit = [ {kind, content, confidence} … ]`. Minimum 3. Under 3 → re-run.

### 5. Build the constraint lattice.
Classify every constraint (explicit + implicit) using `mechs/mech_constraint.md §Classification`. Tiers: **hard** (cost = ∞), **soft** (`relax_cost`, `relax_rank`), **provisional** (`invertible: true`, `inversion: "a → ¬a"`).

**Count rule:** the `hard` bucket must contain **exactly 1 or 2** entries. The `soft + provisional` union must contain **≥ 2**. The validator enforces both bounds.

### 6. Flatten the semantic hierarchy.
Convert hierarchical category labels in your primitives into flat feature lists. Exception: if a category is protected by a hard constraint, keep it.

### 7. Remove temporal anchoring.
Where primitives carry sequence, generate concurrent/simultaneous variants. Output: `concurrent_variants`.

### 8. Identify one analogical domain and map the primitives onto it.
Follow `mechs/mech_associative.md §Cross-domain`. Pick one domain at **distance ≥ 2** from the input's home domain, as defined in `mechs/distance_table.md`. Project the primitives onto this domain's native entities and relations. Output: `projected = { home_domain, analogue_domain, distance, mapping }`.

### 9. Initialise the flat associative field.
Follow `mechs/mech_associative.md §Field-init`. Output: `field = { nodes, edges }`. Target 8+ nodes, no orphans.

### 10. Finalise and validate.
Write `${CTP_RUN_DIR}/state_live.json` into its final shape (all fields from ops 1–9, plus the metadata inherited from state_0). Then run:

```
cp "${CTP_RUN_DIR}/state_live.json" "${CTP_RUN_DIR}/state_1.json"
python3 scripts/validate.py 1 "${CTP_RUN_DIR}/state_1.json"
```

The validator enforces the schema (including the hard-constraint range [1, 2], op timestamps, and op-budget ceiling) and on success prints the next stage's filename on stdout. On failure it prints `phase_recovery.md` on stdout and the specific failure + op-to-rerun on stderr.

**Read-and-execute whatever filename the validator printed on stdout.** Do not hunt for a next step inside this file.
