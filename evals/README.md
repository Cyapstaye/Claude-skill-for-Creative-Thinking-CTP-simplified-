# evals/

Eval cases for the CTP-40 v3 skill. Two categories:

1. **Component evals** — `python3 scripts/run_eval.py` exercises the
   deterministic pieces (semantic density, Pareto, originality, candidate
   regex) against curated inputs. Must pass before any change ships.

2. **Case evals** — `case_*/` directories each contain an `input.json`
   (what to feed the skill) and an `expected.json` (structural invariants
   the final `state_4.json` + `CTP_brief` must satisfy). These are not
   executed by the harness today — they require a live model to run. Use
   them as the manual checklist for each run and as the regression baseline
   for future versions.

## Running

```
python3 scripts/run_eval.py                # all component evals
python3 scripts/run_eval.py --only pareto  # one
```

## Adding a new case

1. Create `evals/case_N_<slug>/` with `input.json` and `expected.json`.
2. `expected.json` records only structural invariants — never exact strings.
3. After running the skill against the input, validate the state_4 artifact
   manually against `expected.json`'s checklist. Log the run in `case_N_<slug>/history.md`.
