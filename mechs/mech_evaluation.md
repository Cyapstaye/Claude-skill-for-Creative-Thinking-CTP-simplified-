# mech_evaluation.md

**Version: v3**

Reference material. Read only when a stage file instructs you to.

---

## §Guilford

Scoring a candidate on five dimensions, each in [0, 1]. v3 moves every computable dimension to a script.

1. **Originality.** `python3 scripts/originality.py "<Proposition>" --domain <home_domain>` — parses a reference corpus for the home domain and scores structural distance from the nearest corpus entry. No self-judgement.

2. **Flexibility.** Distinct conceptual clusters contributing to the blend. **v3 rescale (G3 fix):** 1 → 0.2, 2 → 0.5, 3 → 0.75, 4+ → 1.0. (v2 floored at 0.0, disproportionately penalizing single-domain candidates in Applied mode.)

3. **Elaboration.** `filled_slots / total_slots` across the shared generic's role slots plus any emergent slots from elaboration. Computed from the blend's own correspondence record.

4. **Fluency.** Distinctiveness of this candidate relative to the rest of the surviving pool. `1 − mean_similarity(this, pool)`. Similarity uses the same cosine-over-unigram-and-bigram metric that `originality.py` uses internally.

5. **Semantic density.** `python3 scripts/semantic_density.py "<three-line form>"` — parses for structural operators, divides by word count, normalises. Score = 0 → triggers the hard floor.

Composite: weight each score by the active mode's weights (from the stage file's mode-weights section) and sum. Only the active mode's row is used; do not consult the other modes' weights.

---

## §Viability

Practical-viability assessment.

```
{ "is_viable": true|false,
  "score": 0.0-1.0,
  "reasons_if_not": [...] }
```

Viability checks (any failure → `is_viable = false`):

- **Constraint satisfaction.** Re-verify every hard constraint.
- **Resource realism.** In **Applied** mode, the user must have supplied a concrete viability constraint at pre-flight (or in the input payload) — a named set of skills, tools, and time budget. If no constraint was supplied, viability is downgraded to a **flag** rather than a disqualifier (D4 fix). Exploratory and Combinatorial treat resource realism as informational.
- **Implementation risk.** Would executing this blend require violating something the input implicitly protects (legal, ethical, safety norm)?
- **Legibility.** Can the blend be communicated to the named audience without a primer?

Mode behaviour:

- **Exploratory:** non-viable flagged, stays in pool.
- **Applied (with viability constraint):** non-viable disqualified.
- **Applied (no viability constraint):** non-viable flagged only; selection may proceed.
- **Combinatorial:** non-viable flagged; if all viable candidates have low originality, allow the most promising non-viable to re-enter.

---

## §Pareto

Deferred to `scripts/pareto.py`.

Given a JSON list of `{id, utility, novelty}` records, the script computes the non-dominated frontier and prints, first, the ID chosen under the active mode's rule:

- Exploratory → max novelty on frontier.
- Applied → max `utility + novelty` on frontier.
- Combinatorial → max novelty among frontier points with `utility ≥ 0.5`; else max sum.

Stage 4 op 5 writes its candidates to `pareto_in.json` and reads the script's output. Do not compute the frontier in your head — the script is deterministic and always produces the same answer for the same inputs.

---

## §Recursion-decision

Compute:

```
gap      = target_originality[mode] - stable_core.originality_score
marginal = stable_core.originality_score - prior_cycle.stable_core.originality_score   (only if cycle_depth > 0)
seed_ok  = stable_core.seed names at least one constraint from constraint_lattice.{hard,soft,provisional}
```

Recurse if all of:

- `gap > 0`
- `cycle_depth < max_recursion_depth[mode]` — Exploratory 3, Combinatorial 2, Applied 1
- `seed_ok` is true
- (if `cycle_depth > 0`) `marginal > 0.02` AND `marginal > -0.05`

Force-emit flags:

- **Originality regression:** if `marginal < -0.05` → `run_stuck = true`, force emit with "the best cycle was N."
- **Stuck convergence:** if `marginal ≤ 0.02` for two consecutive cycles → force emit.
- **Budget exceeded:** if `operation_log.length > 150` → `budget_exceeded = true`, force emit.

Per-cycle state files (`state_0_c0.json`, `state_0_c1.json`, ...) and a `cycle_history` list (appended never overwritten) make every cycle independently inspectable (C1 fix). `start.py` is responsible for writing each cycle's `state_0_c<N>.json`; it never touches the cycle-0 file.

---

## §Audit

For each scored candidate, log:

```json
{
  "candidate_id": "...",
  "guilford":    { "originality": 0.x, "flexibility": 0.x, "elaboration": 0.x, "fluency": 0.x, "semantic_density": 0.x, "composite": 0.x },
  "viability":   { "is_viable": true|false, "score": 0.x, "reasons_if_not": [...] },
  "on_pareto_frontier": true|false,
  "selected":    true|false,
  "selection_notes": "<one line; if selected != max-composite, say why>"
}
```

The audit is *why* the selection was made. If the selected candidate is not the max-composite, the notes line must say why in one sentence.
