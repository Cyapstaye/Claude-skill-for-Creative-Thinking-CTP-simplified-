---
name: ctp-hw-v3
description: "Structured creative protocol for dense, non-obvious creative outputs. Use when the user wants something that is not a summary or best-practices answer — mentions CTP, 'creative protocol', 'avoid the obvious answer', 'multi-profile ideation', or asks for a reframing the default would not reach. Do not trigger for summarisation, factual retrieval, code generation, direct topic explanation, or short Q&A."
---

# ctp-hw-v3

Read this file in full. Then proceed to pre-flight. **Re-read this file every time stderr emits `PHASE_BOUNDARY=1`** — the rules below must remain in attention across phase boundaries.

Do not read any other file in this skill directory unless a script's stdout tells you to. Do not list directories. Do not infer protocol shape from filenames.

## Pre-flight

1. The user's input is a creative brief, reframe request, or open-ended query. If clearly ambiguous on purpose / audience / constraint / scope, read `mechs/l2x7m4.md` and follow it (one `AskUserQuestion`, four canonical axes). Otherwise skip clarify.
2. Run the bootstrap:
   ```
   python3 $SKILL_ROOT/scripts/b39kf2.py "<the user's query verbatim>"
       [--mode Exploratory|Applied|Combinatorial]
       [--clarify-answer "<label>"]
       [--workspace-dir <abs_path>]
   ```
3. To resume an in-progress run from a prior session: `python3 $SKILL_ROOT/scripts/b39kf2.py --resume`. The bootstrap reads the workspace's hidden tooling root, finds the most recent in-progress run, and re-emits its dispatch directive.

## The contract

Every dispatch script (bootstrap, validator, firewall when needed, decode at terminal) returns:

- **stdout, line 1:** a path relative to `$SKILL_ROOT` — the next file you read. Or the literal string `TERMINAL`, meaning the run is complete.
- **stderr:** `KEY=value` metadata. Standard keys: `RUN_DIR`, `CYCLE`, `NEXT_PROFILE`, `PROFILE_CONFIG_PATH`, `OUTPUT_PATH`, `OUTPUT_SCHEMA`, `NEXT_SCRIPT`, `PHASE_BOUNDARY`, `TODO_ADD`, `RETRY=1`, `RETRY_REASON`, `ERROR_CLASS`, `CYCLE_START`.

## The rigid loop

After bootstrap, repeat:

1. If stderr has `PHASE_BOUNDARY=1`, **re-read this SKILL.md** to refresh discipline. If `PHASE_BOUNDARY` is not set, skip the re-read.
2. If stderr has `TODO_ADD=<label>`, add a TodoList entry with that opaque label and mark it `in_progress`. If stderr has `TODO_COMPLETE=<label>`, mark that entry `completed`.
3. Read stdout line 1.
4. If line 1 == `TERMINAL`: run the decode script at stderr's `NEXT_SCRIPT` with `--run-dir <RUN_DIR>`. It writes the final deliverables to the workspace root and prints their paths on stderr. Surface those paths to the user. The run is complete.
5. Otherwise read the file at `$SKILL_ROOT/<line_1>`. Follow its instructions exactly. The instructions tell you what state files to read (using paths from stderr), what cognitive operation to perform (referring to a mech file in `mechs/`), and what state file to write (at `OUTPUT_PATH`, validating against `OUTPUT_SCHEMA`).
6. After writing, run the validator: `python3 <NEXT_SCRIPT> --run-dir <RUN_DIR> --last-output <OUTPUT_PATH>`.
7. Parse the validator's stderr:
   - `RETRY=1`: re-execute step 5 (re-read the same phase file and produce a corrected output). The validator tracks the retry counter; after the budget exhausts, it routes to recovery.
   - `ERROR_CLASS=<class>`: stdout points to a recovery file. Read it and follow its instructions (typically: halt and surface to user).
   - Otherwise: go to step 1.

## Forbidden

- Reading any file not named on the most recent stdout line 1, except: re-reading SKILL.md when `PHASE_BOUNDARY=1`.
- Inferring future steps. Do not "prepare" for likely next phases.
- Pattern-matching on filenames to guess content.
- Running scripts not named on stderr's `NEXT_SCRIPT`.
- Writing to the workspace root before `TERMINAL`. The decode script writes the deliverables; you do not.
- Editing this SKILL.md, dispatcher scripts, schemas, or any state file the dispatcher wrote.
- Listing directories.
- Asking the user clarifying questions outside of pre-flight clarify.
- Pre-allocating TodoList entries. Add only when stderr emits `TODO_ADD`.

If you find yourself about to do any of these, halt and surface to the user.
