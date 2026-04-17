# stage — DRIFT

You have just finished the prior stage. The ten operations in this stage grow the candidate pool under the constraint lattice; the validator at the end selects the next stage.

---

## Load prior state

Read `${CTP_RUN_DIR}/state_1.json`. Copy it to `state_live.json`. You will mutate `state_live.json` throughout this stage and rename it to `state_2.json` at the end.

The validator enforces that `phase_completed == "INIT"` and every prior invariant. If the load fails, return to caller.

---

## Goal of this stage

Produce **breadth**. Generate a field of structurally distinct candidates under deliberately relaxed constraints, so that the next stage has a genuine selection to work against. Flatness (many similar candidates) is failure. Depth (few polished candidates) is also failure.

You want a fluency index **≥ `max(10, 20 - 5 × cycle_depth)`** across at least 2 domain clusters. (Cycle 0: 20. Cycle 1: 15. Cycle 2+: 10.) Read `cycle_depth` from `state_live.json`.

Every candidate must be expressed as a compressed structural proposition in this exact form:

```
[structural element A] × [structural element B] → [consequence or tension]
```

One line per candidate. No paragraphs. No qualifiers. Each side of `×` and `→` must contain **at least 2 tokens**. The validator enforces this as a regex; candidates that fail it will be rejected.

Read the mechanism files this stage uses:

- `mechs/mech_associative.md` — used by operations 1, 2, 5, 6.
- `mechs/mech_constraint.md` — used by operations 3 and 4.
- `mechs/distance_table.md` — used by operation 6.

---

## The 10 operations

Log each operation with `scripts/log_op.py` as in the prior stage.

### 1. Remote associate sampling.
Sample from the tails of the flat associative field — nodes with the most distant pairwise feature overlap relative to the input payload. Pick 5–7 such nodes. Generate a candidate proposition per node. If your first candidates feel obvious, you are sampling the centre — re-sample.

### 2. Conceptual-distance filter.
Reject any candidate that is too close to the input's dominant framings (from `state_1.suppression_log`). Distance heuristic: does the candidate use *different structural elements* than the input's default, or merely different surface words? Different words with identical structure = reject.

### 3. Incremental soft-constraint relaxation.
Walk the soft constraints in ascending `relax_rank`. For each, produce 1–2 candidates that violate that constraint only. Log `relaxed_constraint` on each candidate. Follow `mechs/mech_constraint.md §Relaxation`.

### 4. Provisional-constraint inversion.
For each invertible provisional constraint, generate a candidate that assumes the opposite. The inversion must be **structural**, not lexical. Follow `mechs/mech_constraint.md §Inversion`.

### 5. Cross-domain transfer.
Using `state_1.projected`, extract a template from the analogue domain. Re-apply the template to the home domain with exactly one substitution. Follow `mechs/mech_associative.md §Template-extraction`.

### 6. Analogical candidates from a second distant domain.
Choose a **second** analogue domain (different from `state_1.projected.analogue_domain`) at distance ≥ 2 per `mechs/distance_table.md`. Generate 3–5 candidates. Purpose: lift `flexibility_index` to ≥ 2.

### 7. Accumulate failure residue.
Record every tried combination that failed (incoherent, violates a hard constraint, collapses to trivial rewording) as:

```
{ "proposition": "[A] × [B] — failed at [specific conflict]", "source": "failure_residue" }
```

Do not discard failures. They are consumed by the next stage.

### 8. Combinatorial pairing for tension.
Pair candidates that are **structurally incompatible** (share an abstract relation, commit to opposite resolutions). Log pairs with `tension_score` in [0, 1]; keep pairs with score ≥ 0.5.

### 9. Running metrics.
Compute `fluency_index = count(candidates)` and `flexibility_index = count(distinct domain clusters)`. If `flexibility_index < 2` after op 6, cross-domain transfer has failed. Re-run op 6 with a **more distant** domain. Do not compensate with in-domain candidates.

### 10. Finalise and validate.
Merge `entropy_field` into `state_live.json` with fields:
`candidates`, `tension_pairs`, `failure_residue`, `fluency_index`, `flexibility_index`.

Then run:

```
cp "${CTP_RUN_DIR}/state_live.json" "${CTP_RUN_DIR}/state_2.json"
python3 scripts/validate.py 2 "${CTP_RUN_DIR}/state_2.json"
```

The validator checks (a) schema including the strict `[A] × [B] → [C]` regex per candidate, (b) cycle-adjusted fluency floor, (c) flexibility ≥ 2, (d) failure_residue ≥ 3, (e) op-log timestamps and total count.

**Read-and-execute whatever filename the validator printed on stdout.**
