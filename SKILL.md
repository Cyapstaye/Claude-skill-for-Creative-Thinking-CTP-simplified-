---
name: divergent-ideation
description: "Structured divergent-ideation protocol that produces a single compressed, load-bearing creative proposition from an input problem or brief. Use whenever the user wants genuinely novel ideas, wants to reframe a problem from first principles, asks for something surprising or non-obvious, runs an ideation or brainstorming pass, synthesises across unrelated domains, or mentions 'CTP', 'CTP-40', 'creative protocol', 'divergent thinking', 'conceptual blending', or 'constraint relaxation'. Trigger only when the request implies generating something new that is valued for novelty; do not trigger when the request is answerable by retrieval, summarisation, factual lookup, or direct explanation. A full run can consume ~10-20k tokens of context; a minimal run is cheaper. Also registered under the alias ctp-40."
---

# divergent-ideation (alias: ctp-40)

A structured creativity protocol. This file is the entry point only. It does not contain the protocol.

---

## Pre-flight

**Step 1 — Confirm the input.**
The user must have given you a problem, brief, concept, or question to develop. If the input is ambiguous on its purpose, its audience, or the constraints the user wants respected, follow the canonical single-question clarification procedure in `mechs/mech_clarify.md` — read that file and use exactly one AskUserQuestion call with at most four options. Do not invent details the user did not provide.

**Step 2 — Initialise the run.**
Run:

```
python3 scripts/start.py
```

from this skill's directory. The script will:

- create a per-run working directory at `${CTP_RUN_DIR:-$(pwd)/.ctp40_run}/<run_id>/`
- write the initial state file `state_0.json` containing the user input and a generated `payload_slug`
- print the first-stage filename on stdout and `RUN_DIR=<absolute_path>` on stderr

**Step 3 — Capture the concrete run directory.**
Parse the `RUN_DIR=<path>` line from `start.py`'s stderr. Substitute that absolute path for every occurrence of `${CTP_RUN_DIR}` you encounter in stage files — stage files show the placeholder, but the Read tool needs a concrete path. The run directory persists for the entire run (including recursion cycles); do not create a new one per stage.

Then read the file whose name was printed to stdout, and execute it. Do nothing else first.

---

## Begin

Read the file emitted by `scripts/start.py` and execute it.
