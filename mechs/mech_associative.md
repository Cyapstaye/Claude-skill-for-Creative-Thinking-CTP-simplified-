# mech_associative.md

**Version: v3**

Reference material. Read only when a stage file instructs you to.

---

## §Field-init

How to build the flat associative field.

A node is a single feature from your primitives or from an analogue-domain projection. Every node gets `baseline_activation = 1.0` — the field is deliberately flat so remote samples are not dominated by the input's high-probability centre.

An edge is drawn between two nodes when:

- They co-occur in the same primitive (an entity and its role).
- They are aligned in the `projected` mapping (a home element and its analogue).
- They share a functional role across primitives.

Edge weight in [0, 1] from `weight = co_occurrences / max_co_occurrences_in_field`. Weights steer sampling later; they do not change baseline activation.

Output:

```json
{
  "nodes": [ {"id": "...", "name": "...", "domain": "...", "baseline_activation": 1.0} ],
  "edges": [ {"source": "...", "target": "...", "weight": 0.x, "kind": "co_occurrence | projection | role"} ]
}
```

Target 8+ nodes and at least one edge per node (no orphans).

---

## §Cross-domain

Choosing an analogue domain.

An analogue is valid when its conceptual distance from the home domain is **≥ 2**. Distance is defined in `mechs/distance_table.md` — consult it, do not rely on intuition.

Quick reference (full table in `distance_table.md`):

- **Distance 1** — same parent domain or sibling sub-domain. Invalid. Example: k-12 vs higher-ed; language learning vs skill acquisition.
- **Distance 2** — different parent domain but shares an abstract relation (both involve agents, both involve flows, both involve thresholds). Valid and usually most productive. Example: education ↔ supply chains (both move resources through stages); education ↔ immune systems (both involve acquisition + memory).
- **Distance 3+** — requires an analogy to bridge. Valid but riskier (more failure residue).

Generate 2 candidate analogue domains from the table, pick the more distant of the two that still has a viable structural mapping. Do not pick the first analogue that comes to mind — the first is almost always distance 1.

Output:

```json
{
  "home_domain":     "...",
  "analogue_domain": "...",
  "distance":        2,
  "mapping":         [ {"home": "...", "analogue": "...", "shared_role": "..."} ]
}
```

---

## §Template-extraction

How to extract a reusable template from the analogue domain.

Find a characteristic relation or behaviour in the analogue domain that the home domain does not natively express. The template is the *pattern*, not the words:

```
[low-activation population] × [re-exposure trigger] → [fast re-activation of prior response]
```

Re-apply the template to the home domain, substituting **exactly one** element. Straight re-application produces a metaphor, not a blend — the substitution is where novelty comes from.

```
[low-activation student pool] × [re-exposure trigger] → [fast re-activation of prior skill]
       ↑ substituted back into home               ↑ kept from analogue
```

Generate 3–5 template transfers. Log each with `"source": "cross_domain"`, the template, and the substitution point.

---

## §Sampling-from-tails

When drawing remote associates, sample nodes in the lowest-weight tail of the edge distribution — nodes whose connections to the input's primitives are weak. Distance-2+ candidates live there.

Sampling the centre → obvious candidates. Sampling the tail → unusual ones, some of which will be incoherent (log to failure_residue, do not discard) and some surprising and usable.

Heuristic: for every usable remote-associate you produce, you should also have produced 1–2 failed ones. A 100% success rate at remote sampling means you are not sampling remotely enough.
