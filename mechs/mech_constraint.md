# mech_constraint.md

**Version: v3** (update this line when the math changes).

Reference material. Read only when a stage file instructs you to.

---

## §Extraction

How to surface implicit assumptions that did not appear in the input verbatim.

Scan for five kinds of latent assumption:

1. **Role absence.** The input uses a verb or relation but omits a typical role. "Make it faster" — speaker? consumer? measured where? Each omitted role is an implicit constraint that some default answer is expected.
2. **Direction.** Causal or dependency arrows the input leaves unstated. "Onboarding should feel effortless" assumes effort flows toward the user; flipping that is often the most generative inversion.
3. **Temporal ordering.** Sequences assumed by the noun phrases. "Discovery → consideration → purchase" — the order is not written in the input but is assumed by the nouns.
4. **Scope.** Boundaries the input does not name but requires. "A newsletter for engineers" assumes medium (email), cadence (regular), tone (professional).
5. **Audience.** Who the output is for. Inputs almost never name the audience exhaustively.

Record:

```
{ "kind": "role_absence | direction | temporal | scope | audience",
  "content": "<declarative statement>",
  "confidence": 0.0-1.0 }
```

Low confidence is fine — it flags the assumption as a strong candidate for provisional classification.

---

## §Classification

Every constraint becomes exactly one of three tiers.

- **Hard.** Violating it makes the output *a different thing*. Cost = ∞. Typical: format (must be a name / slogan / fit in a headline), register (SFW), correctness (factually true), audience accessibility.
- **Soft.** Relaxable at a cost. Has `relax_cost` in [0, 1] and `relax_rank` (integer, lower = relaxed earlier).
- **Provisional.** Assumption you suspect is wrong or at least invertible. Has `invertible: true` and `inversion: "<a → ¬a>"`.

**Count rule (v3 — replaces the v2 'demote if > 2' heuristic).**

The hard bucket must contain **1–2 entries** (validator enforces).

After classification, perform a **coverage check** (G2 fix):

> Estimate, by inspection of the entropy field you are about to generate, what fraction of candidates the hard bucket would admit. If that fraction is below 0.5 (i.e. hard constraints would reject more than half of an unconstrained field), and you have 2 hard constraints, **demote the weakest to soft**. If you have only 1 hard constraint, keep it and proceed.

This replaces the blanket "more than 2 hard → demote" rule. Some problems have genuinely multiple hard constraints (format + safety, for instance); the coverage check lets the math decide.

Output schema:

```json
{
  "hard":         [ {"name": "...", "content": "...", "cost_of_violation": "infinity"} ],
  "soft":         [ {"name": "...", "content": "...", "relax_cost": 0.x, "relax_rank": 1} ],
  "provisional":  [ {"name": "...", "content": "...", "invertible": true, "inversion": "... → ..."} ]
}
```

Every entry must have a stable `name` field. The stable_core's `Seed` line will reference constraint names by value; missing names break the C4 validator check.

---

## §Relaxation

How to relax a soft constraint during divergent candidate generation.

- Walk constraints in ascending `relax_rank`. Lower rank first.
- Generate 1–2 candidates per constraint that violate *only* that constraint.
- Log `"relaxed_constraint": "<name>"`.
- Do not relax hard constraints. If a candidate would require it, discard to failure_residue.
- One relaxation per candidate.

---

## §Inversion

How to invert a provisional constraint.

- **Structural, not lexical.** "Sequential" inverts to "concurrent" / "simultaneous" / "interleaved" — not "non-sequential" (a mere negation of a word).
- Record `"inverted_constraint": "<name>"` and `"inversion_applied": "<a → ¬a>"` on the candidate.
- Signal of good inversion: different structural *operators*, not different adjectives.
