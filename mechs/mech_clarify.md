# mech_clarify.md

**Version: v3**

Reference material for pre-flight clarification. Read only when SKILL.md judges the input ambiguous.

---

## When to clarify

Ask *one* clarifying question only when at least one of the following is missing from the user's input:

- **Purpose.** Is the user trying to generate a name, a concept, a positioning, a mechanism, a product direction, a reframing? Different purposes lead to different modes.
- **Audience.** Who is the output for? The audience determines the legibility constraint in the viability check.
- **Respected constraints.** What must the output not violate? (Format, register, safety, budget, timeline.)

If the input already contains all three — or if the user explicitly says "just go," or provides a dense brief — skip clarification.

---

## The canonical single-question form

Use `AskUserQuestion`. The question header:

> "Before I run the protocol, one clarification — choose the option closest to your intent."

Multi-choice body (adjust the option labels to the input, but keep the structure):

- **Option A — Sharp, specific output.** "I want one high-confidence creative answer I can act on." (→ Applied mode.)
- **Option B — Exploration of the space.** "I want the most non-obvious framing available, even if less actionable." (→ Exploratory mode.)
- **Option C — Multi-domain synthesis.** "I want something that draws on multiple domains and holds them together." (→ Combinatorial mode.)
- **Option D — Other.** (Free-text — user describes in 1 sentence.)

For Option A, also prompt for **audience** and **one hard constraint** (format, medium, register, or budget). These become entries in `state_0.audience_spec` and the constraint lattice at INIT op 5.

---

## What not to ask

- Do **not** ask what mode to run. The mode is a consequence of the user's choice above, not a user-facing concept.
- Do **not** ask how long the output should be. Length is an output of the compression rules, not a user choice.
- Do **not** ask about methodology (phases, blending, etc.). Protocol internals are never user-facing.
- Do **not** ask more than one question before starting. The clarification is a single `AskUserQuestion` invocation. Further ambiguity surfaces inside the protocol and is handled by specific operations.

---

## Fallback

If `AskUserQuestion` is unavailable in the environment, write a single one-paragraph request in the response and stop; the protocol does not start until the user has answered. Resumption writes state_0 with the confirmed fields.
