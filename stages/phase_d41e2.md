# stage — REFACTOR

You have just finished the prior stage. The ten operations in this stage reshape each candidate into an evaluable blend structure; the validator at the end selects the next stage.

---

## Load prior state

Read `${CTP_RUN_DIR}/state_2.json`. Copy to `state_live.json`. You will mutate `state_live.json` and rename to `state_3.json` at the end.

---

## Goal of this stage

Narrow the wide field to **≥ 5 ranked blends with genuine emergent structure**. A blend is not a juxtaposition ("X and Y, side by side"). A blend produces a property that was in neither input. If you cannot state that property, you do not have a blend — you have a collage.

Every completed blend must be recorded in this exact three-line form:

```
Proposition: <what the blend claims or does — one sentence, no qualifiers>
Mechanism:   <how the blended structures interact — one sentence>
Emergence:   <property present in the blend but not in either input — one clause>
```

Four lines = over-elaborated. Two lines = emergence missing. Three lines, dense, load-bearing.

Read the mechanism file this stage uses:

- `mechs/mech_blend.md` — used by operations 2, 3, 4, 5.

---

## The 10 operations

Log each via `scripts/log_op.py`.

### 1. Filter for self-consistency.
Drop candidates that internally contradict themselves. Score remaining `self_consistency` in [0, 1]. Keep those ≥ 0.7.

### 2. Construct input-space pairs.
Follow `mechs/mech_blend.md §Pairing`. Pair candidates that share an abstract relational skeleton but differ in surface content. Target 5–8 pairs. Pull 1–2 from `entropy_field.tension_pairs` (pre-flagged for incompatibility).

### 3. Map cross-space correspondences.
Follow `mechs/mech_blend.md §Correspondence`. Produce `shared_generic`, `aligned_roles`, `conflicts`, `unmapped_a`, `unmapped_b` per pair.

### 4. Project selectively into the blend space.
Follow `mechs/mech_blend.md §Selective-projection`. Project only elements that are (compatible with the generic) AND (produce tension OR are genuinely novel).

### 5. Cultivate emergent structure.
Three sub-operations in order (composition → completion → elaboration). The **Elaboration** step must produce `new_inferences` with `new_inferences.length ≥ 2`. An inference is **new** iff it references at least one feature or relation that appears in neither input's mapping — see `mechs/mech_blend.md §Emergence` for the structural definition. If fewer than 2 new inferences, the blend has not emerged; re-run elaboration or re-select the pair.

### 6. Hard-constraint filter.
For each elaborated blend, check every entry in `constraint_lattice.hard`. Violations → discard and log to `discarded_blends`. Soft violations → keep and flag.

### 7. Compress clusters.
Cluster blends with intra-cluster similarity ≥ 0.85. Keep the most novel representative; subsume the rest.

### 8. Mutate the top candidates.
Take the top 3–5. Apply **one** of: feature substitution, relational inversion, role reassignment. Validate mutations against the hard-constraint filter.

### 9. Recover from failure residue.
Attempt to recover **at least one** entry from `entropy_field.failure_residue` by mutating one element and re-blending. **Cap recovery attempts at 3** (bug-3 fix). Track `failure_residue_recovery_attempts` in state. If all 3 attempts fail, set `failure_residue_recovery_attempted: true` with a reason and stop; do not loop.

### 10. Rank and finalise.
Score each surviving blend:

- `blend_integrity` — computed per `mechs/mech_blend.md §Integrity` (deterministic formula, three checks ≥ 0.5).
- `originality` — run `python3 scripts/originality.py "<Proposition>" --domain <home_domain>`. Parse the `score=` value.

Rank by `blend_integrity × originality`. Then compute the Pareto frontier over (`blend_integrity`, `originality`). Keep frontier + top 2 non-frontier for diversity.

Merge into `state_live.json` with fields `candidate_structures`, `discarded_blends`, `failure_residue_recovery_attempts`. Then:

```
cp "${CTP_RUN_DIR}/state_live.json" "${CTP_RUN_DIR}/state_3.json"
python3 scripts/validate.py 3 "${CTP_RUN_DIR}/state_3.json"
```

**Read-and-execute whatever filename the validator printed on stdout.**
