# phase_recovery.md

You are reading this file because `scripts/validate.py` exited with code 1.
The validator has printed the specific failure on stderr, including the
operation number to re-run. Do not continue to a new stage.

---

## Recovery procedure

1. **Read the validator's stderr output.** It contains two lines:

   ```
   FAIL: <human-readable description of which check failed>
   RERUN_OP: <integer>
   ```

   (`RERUN_OP` may be absent for whole-schema failures; those require re-running
   the entire stage.)

2. **Locate the failing operation.** Operations are numbered 1–10 within each
   stage file. The op numbers are stable across stages. Re-open the stage
   file you were executing and go to the operation with the matching number.

3. **Re-run that operation.** Then, re-run every operation *after* it in the
   same stage (because later ops may depend on the output of the failed one).

4. **Re-write the state artifact.** Copy `state_live.json` over the failed
   `state_N.json` and re-invoke `python3 scripts/validate.py N state_N.json`.

5. **If the validator fails twice on the same RERUN_OP,** the failure is
   likely structural (input is too thin, constraints are under-specified, or
   the home domain has too few candidate analogues). Return to the caller
   with a short report naming the operation and the specific invariant it
   failed to produce. Do not loop indefinitely.

---

## Common recoveries by failure message

| Validator message                                              | Likely cause                                                 | Recovery                                                                       |
| -------------------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| `constraint_lattice.hard must be [1, 2] items`                 | Over- or under-classified hard constraints.                  | Re-run op 5: apply the coverage check from `mechs/mech_constraint.md §Classification`. |
| `fluency_index <N> below cycle-adjusted threshold <M>`         | DRIFT did not produce enough distinct candidates.            | Re-run ops 1, 5, 6 with more tail-sampling. Do not generate duplicates.         |
| `candidates[i].proposition fails [A] × [B] → [C] shape`        | One or more candidates are not in compressed structural form. | Re-run op 2 (distance filter) on offending candidates; compress until they match the regex. |
| `candidate_structures[i].<field> must be one line`             | Blend has multi-line fields.                                 | Re-run op 5 (emergence → compression).                                          |
| `recovery_attempts <N> > cap 3`                                | Failure-residue recovery looped.                             | Set `failure_residue_recovery_attempted: true` with a reason; proceed.          |
| `stable_core.seed must name at least one constraint`           | Seed is a rewording, not a tension.                          | Re-run op 8; name at least one constraint_lattice entry by `name`.              |
| `originality regressed by more than 0.05`                      | Cycle N is worse than cycle N-1.                             | Force emit with `run_stuck: true`; best cycle is N-1.                           |
| `operation_log exceeded MAX_OPS_PER_RUN`                       | Run is over budget.                                          | Force emit with `budget_exceeded: true`.                                        |

---

## After recovery

Re-run `scripts/validate.py <stage> <state_N.json>`. The validator will
either print the next-stage filename on stdout (continue) or `phase_recovery.md`
again (new failure — follow the same procedure).

Do not navigate between stages except through the validator.
