# distance_table.md

**Version: v3**

Reference material. Read only when a stage file instructs you to.

Formal definition of conceptual distance between two domains. Used by `mech_associative.md §Cross-domain` and stage-file op 8.

---

## Definition

Conceptual distance between domains A and B is the smallest integer d such that there exists a chain A = D_0, D_1, ..., D_d = B where each adjacent pair (D_i, D_{i+1}) shares a classifier at a higher level.

The classifier hierarchy used for this skill:

- **Level 0:** specific sub-domain (e.g. "k-12 pedagogy", "digital immunology", "municipal water supply").
- **Level 1:** parent domain (e.g. "education", "biology", "infrastructure").
- **Level 2:** meta-domain (e.g. "human systems", "natural systems", "engineered systems").
- **Level 3:** abstract-relation class (e.g. "agent-producing-X", "flow-through-stages", "threshold-triggered-event", "memory-with-decay").

---

## Distances

- **Distance 0** — same sub-domain. Never valid for cross-domain transfer. Example: k-12 pedagogy vs k-12 pedagogy.
- **Distance 1** — same parent, different sub-domain. Invalid for CTP cross-domain. Example: k-12 vs higher-ed (both under education). Example: language learning vs skill acquisition (both under education).
- **Distance 2** — different parent, same meta-domain OR shares an abstract relation. **Valid, usually most productive.** Examples:
  - education ↔ supply chains (both "flow through stages")
  - education ↔ immune systems (both "memory with decay + reactivation")
  - urban planning ↔ traffic simulation (both "congestion under load")
  - branding ↔ ecology (both "niche competition")
- **Distance 3** — shares only an abstract-relation class; the domains otherwise have nothing in common. Valid but riskier — more failure residue expected. Examples:
  - branding ↔ thermodynamics (both "gradients drive change")
  - education ↔ materials science (both "phase transitions under accumulated stress")
- **Distance 4+** — no shared classifier below the most abstract. Not recommended — the analogy will likely not sustain a template. Example: branding ↔ quantum mechanics.

---

## How to compute distance

1. Identify the home domain's sub-domain, parent, meta-domain, and the abstract relation its primitives most naturally instantiate.
2. For the candidate analogue, identify the same four levels.
3. The distance is the lowest level at which the two domains share a classifier. (Share at level 0 = distance 0. Share first at level 3 = distance 3.)
4. If you cannot identify a shared classifier at any level, the distance is undefined — pick a different analogue.

---

## Usage

- Stage INIT op 8: pick one analogue at distance **≥ 2**. Record `distance` in the output schema.
- Stage DRIFT op 6: pick a second analogue, different from the first, also at distance **≥ 2**. Prefer a different abstract-relation class than the first chose.
- Mech_associative §Cross-domain: "generate 2 candidate domains, pick the more distant" — the distance here is the computed integer, not intuition.

Record the distance integer in `state_1.projected.distance` and in each cross-domain candidate's metadata. Downstream phases can audit whether the distance constraint was actually met.
