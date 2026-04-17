# stage — STABILIZE

You have just finished the prior stage. This is the final operational stage. Either it emits the output or it seeds one recursion.

---

## Load prior state

Read `${CTP_RUN_DIR}/state_3.json`. Copy to `state_live.json`.

---

## Goal of this stage

Select **one** candidate. Score it rigorously with deterministic scripts. Compress it to a five-line `stable_core`. Then either emit or seed one recursion.

Read the mechanism file this stage uses:

- `mechs/mech_evaluation.md` — used by operations 3, 4, 5, 7, 9.

---

## Mode weights (active mode only)

Read `${CTP_RUN_DIR}/mode_weights.json`. The file was written by `scripts/start.py` at run initialisation and contains exactly one mode's row — the active one. Fields you will use below:

- `guilford_weights` — five-dimension weights for the composite score.
- `target_originality` — the originality threshold this stage compares against.
- `viability_floor` — the minimum viability score the selected candidate must clear.
- `prefer` — the selector keyword passed to `scripts/pareto.py`.
- `max_recursion_depth` — the ceiling for recursion used in op 9.

Do not attempt to reason about other modes; the file names only the active one.

---

## The 10 operations

### 1. Short-list.
Take the Pareto frontier from `candidate_structures` plus the top 2 non-frontier entries. Scoring pool is 3–7 candidates.

### 2. Semantic-density pre-check (hard floor).
For each candidate, write its three-line blend to a temp file and run:

```
python3 scripts/semantic_density.py "<one-line concatenation of the three lines>"
```

Parse the `score=` value. If `score == 0.0`, set `composite_score = 0` and remove from the pool. If the pool empties, return to stage REFACTOR: "All candidates failed the semantic-density floor."

### 3. Guilford five-dimension scoring.
Follow `mechs/mech_evaluation.md §Guilford`.
- **originality**: `python3 scripts/originality.py "<Proposition>" --domain <home_domain>` → parse `score=`.
- **flexibility**: count distinct domain clusters referenced. Floor **0.2** at 1 domain (not 0.0), 0.5 at 2, 0.75 at 3, 1.0 at 4+ (G3 fix).
- **elaboration**: `filled_slots / total_slots` from the blend's generic + emergent slots.
- **fluency**: `1 − mean_similarity(this, pool)`.
- **semantic_density**: as computed in op 2.

Compute `composite_score` with the active mode's weights.

### 4. Practical-viability check.
Follow `mechs/mech_evaluation.md §Viability`. Use `mode_weights.viability_floor` as the threshold. Apply the viability policy documented for the active mode in the mechanism file — do not inspect other modes' policies.

### 5. Novelty-utility Pareto selection.
For each candidate write:
- `utility` = `0.5 × elaboration + 0.5 × semantic_density`.
- `novelty` = `originality × flexibility`.

Write the list as JSON to `${CTP_RUN_DIR}/pareto_in.json`, then run:

```
python3 scripts/pareto.py "${CTP_RUN_DIR}/pareto_in.json" --mode <mode>
```

The first line is the selected candidate ID; subsequent lines are the other frontier points. Record `on_pareto_frontier` per candidate from the output.

### 6. Safe-choice check.
If the selected candidate is the most elaborated of the pool but not among the top 2 by originality, flag `convergence_bias_warning = true`. Compare explicitly against the second-ranked. State in one line why the safe-choice was preferred; if you cannot, re-select.

### 7. Compose the stable_core.
Five lines, exactly:

```
Proposition: <one sentence — the creative output as a claim>
Mechanism:   <one sentence — the structural logic that makes it work>
Novelty:     <one clause — the specific constraint inversion or cross-domain transfer that produced it>
Constraint:  <one clause — name the hard constraint it respects, by its `name` field>
Seed:        <one clause — the unresolved tension still generative; must name at least one constraint from `constraint_lattice` by name>
```

Save to `${CTP_RUN_DIR}/stable_core.txt` and run:

```
python3 scripts/compress_check.py --kind stable_core "${CTP_RUN_DIR}/stable_core.txt"
```

If it fails, rewrite the failing line and re-run.

### 8. Extract the recursion seed.
The `Seed` line is the recursion payload. Convert it to: "If re-entered, the next cycle's input is: `<Seed line, rephrased as an open problem statement>`." The validator enforces that the seed names at least one constraint (C4 fix).

### 9. Decide emit or recurse.
Follow `mechs/mech_evaluation.md §Recursion-decision`. Compute:

```
gap = target_originality - stable_core.originality_score
marginal = stable_core.originality_score - prior_cycle.stable_core.originality_score   (if cycle_depth > 0)
```

Set `action = "recurse"` only if:
- `gap > 0`, AND
- `cycle_depth < mode_weights.max_recursion_depth`, AND
- the seed names a constraint from the lattice, AND
- (if `cycle_depth > 0`) `marginal > 0.02` AND `marginal > -0.05` (originality floor, C2 fix). A negative marginal > 0.05 triggers **force emit** with a `run_stuck = true` flag.

Check budget: if `len(operation_log) > 150`, force emit with `budget_exceeded = true`.

Otherwise `action = "emit"`.

### 10. Execute the decision.

Merge `stable_core`, `action`, `composite_score`, `cycle_history` (append the current cycle's stable_core, never overwrite), and flags into `state_live.json`. Write `state_4.json` **first** (Bug-4 fix — the cycle record is canonical before any recursion state is touched):

```
cp "${CTP_RUN_DIR}/state_live.json" "${CTP_RUN_DIR}/state_4_c${cycle_depth}.json"
python3 scripts/validate.py 4 "${CTP_RUN_DIR}/state_4_c${cycle_depth}.json"
```

**Read-and-execute whatever filename the validator printed on stdout.**

If validator emits `phase_7a3c9.md` (recursion), the validator has already confirmed the action is `recurse`. Re-invoke:

```
CTP_INPUT="<seed-rephrased-as-open-problem>" python3 scripts/start.py --mode <mode> --cycle-depth $((cycle_depth + 1))
```

This writes `state_0_c<N+1>.json` in the same `run_dir` (start.py never overwrites state_0 — C1 fix). Then re-enter stage INIT.

If validator emits `END`, proceed to the **Emit** section below.

---

## Emit (run only if validator emitted `END`)

Produce the two user-facing files in the user's workspace folder (use `$WORKSPACE_DIR` if set, else fall back to `$(pwd)`; H3 fix):

### File 1 — `CTP_brief_<payload_slug>.md`

```markdown
# CTP-40 Brief — <payload_slug>

**Mode:** <mode>
**Cycle count:** <cycle_depth + 1>
**Date:** <YYYY-MM-DD>

## stable_core

Proposition: ...
Mechanism:   ...
Novelty:     ...
Constraint:  ...
Seed:        ...
```

The brief contains the stable_core and nothing else. No commentary.

### File 2 — `CTP_full_<payload_slug>.md`

Full reasoning topology. Sections in this order:

```markdown
# CTP-40 Full — <payload_slug>

**Mode:** <mode>
**Cycles run:** <N>
**Date:** <YYYY-MM-DD>

## stable_core
Proposition: ...
Mechanism:   ...
Novelty:     ...
Constraint:  ...
Seed:        ...

## I. Constraint lattice
- Hard: <compressed labels>
- Soft (in relaxation order): <labels with relax_rank>
- Provisional (inversions available): <assumption → ¬assumption>
- Suppressed dominant framings: <1-2 compressed propositions>

## II. Entropy field
Group by source. Each candidate one line.
Fluency: <int> | Flexibility: <int domains>

## III. Blend paths
For each blend (selected + discarded):
  Proposition / Mechanism / Emergence / Inputs / Integrity / Originality / on_frontier / Status.

## IV. Selection tree
Table of candidates with Guilford dimensions and composite.

## V. Recursion seed
- Unresolved tension: <one clause>
- Recommended next mode (if re-entered): <mode>
- If re-entered, input_payload becomes: "<seed restated as an open problem>"

## VI. Cycle history (only if cycles > 1)
For each cycle: stable_core proposition + Δ from previous.
```

Every entry is a compressed proposition. No prose. Every word carries a reasoning step.

Present both files with `computer://` links. End of protocol.
