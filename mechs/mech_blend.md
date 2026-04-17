# mech_blend.md

**Version: v3**

Reference material. Read only when a stage file instructs you to.

---

## §Pairing

Two candidates are a **good** blend pair when they:

- Share an **abstract relational structure** (same generic pattern, e.g. "an agent produces X given Y").
- Differ in **surface content** (entities and domains are not the same).
- Have at least one **structural conflict** (resolve the abstract pattern in opposite or incommensurable ways).

**Bad** blend pairs: surface-similar (produces juxtaposition), share no abstract relation (produces collage), resolve their shared pattern identically (no tension).

Metric: `complementarity = generic_strength × surface_distance`. Keep pairs with complementarity ≥ 0.5. Reject `generic_strength < 0.6` (nothing to blend) and `surface_distance < 0.5` (will juxtapose).

---

## §Correspondence

For each pair produce:

- `shared_generic` — one-sentence abstract pattern both inputs instantiate.
- `aligned_roles` — `[{abstract_role, from_a, from_b}]`.
- `conflicts` — `[{a_element, b_element, type}]` with type in `{value, direction, scope}`.
- `unmapped_a` / `unmapped_b` — elements with no counterpart.

Unmapped elements are not waste — they are candidates for **emergent projection**. An element with no counterpart, projected into the blend, often produces the emergent property you are looking for.

---

## §Selective-projection

Project an element if it is **either**:

- Compatible with the `shared_generic` AND produces tension with a projected element from the other side.
- Novel relative to the other space (an unmapped element whose presence changes what the blend can do).

Do **not** project:

- Redundant elements (both spaces carry the same thing).
- Ornamental elements (vivid but structurally inert).
- Elements that would force the blend to violate a hard constraint.

Selective projection is the antidote to shallow blends.

---

## §Emergence

Three sub-operations. Skipping any one produces a flat output.

1. **Composition.** Resolve the `conflicts` from correspondence. Each conflict has multiple possible resolutions; the blend must pick one; the pick itself is informative. Log: `[{conflict, resolution, why_this_one}]`.
2. **Completion.** Invoke background knowledge to fill gaps the projected set creates. Log: `[{schema_invoked, triggered_by, implied_features}]`. If nothing is triggered, projection was too sparse — go back.
3. **Elaboration.** Run the blend forward as a scenario. "Given this blend, what happens next? Then?" 2–3 causal steps. Collect `new_inferences`.

### Structural definition of "new" (v3 — G1 fix)

An inference is **new** iff **all** of the following are true:

1. It references at least one `feature` or `relation` that appears in *neither* `origin_pair.a` nor `origin_pair.b`'s primitives / aligned-role set.
2. It is not a strict re-statement of either input's claim with substituted words.
3. It makes a prediction or commitment whose truth value depends on the blend holding (i.e. if you unblend, the inference no longer follows).

Record each inference with:

```
{ "inference": "...",
  "novel_features": ["<feature not in a or b>", ...],
  "derivable_only_from_blend": true|false }
```

A blend is "genuine" when `new_inferences` contains **at least 2 entries each satisfying criteria 1–3**. A blend with 0–1 new inferences has not emerged — it has composed. Composition without elaboration is structurally equivalent to juxtaposition.

---

## §Integrity

Deterministic formula (scored in-stage, verified by schema):

```
blend_integrity =
    0.4 × (aligned_roles.length / max(1, generic_role_slots)) +
    0.3 × (completion_schemas_non_empty ? 1 : 0) +
    0.3 × (new_inferences.length ≥ 2 ? 1 : 0)
```

Three checks — each ≥ 0.5 required for admissibility:

- At least half the generic's role slots filled via aligned roles.
- At least one background schema invoked in completion.
- At least two new inferences produced by elaboration (per the definition above).

A blend below 0.5 on any one check goes back to pair selection, not scoring.

---

## §Compression rules for the three-line form

```
Proposition: <one sentence, declarative, no hedges>
Mechanism:   <one sentence, names HOW, not WHAT>
Emergence:   <one clause, names a property present in the blend but in NEITHER input>
```

Rules:

- **Proposition** is a claim, not a description. "It brings people together" is description; "learning compounds when each session leaves an observable residue the learner can revisit" is a claim.
- **Mechanism** names *how*, not *what*. Structural operation, not experience.
- **Emergence** must name a property that is *new* — not in either input's feature set. If it is in an input, it is a carry-over, not emergence.

Reduction test: for each word, does it carry a reasoning step? If not, remove it.

`scripts/compress_check.py --kind blend <file>` enforces the three-line structure and per-line word bounds deterministically.
