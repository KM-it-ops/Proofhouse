# Architecture

```text
Cursor skill / proofhouse-compiler CLI / (future) interface
                     |
          Python library services (src/proofhouse)
                     |
   Accepted constraints + immutable prompt revisions      optimize/case.py, optimize/workflow.py
                     |
     Compile IR (offline) / import output / opt-in execute    compiler/, optimize/workflow.py, compiler/execution.py
                     |
       Recorded runs and imported observations            runs/*.json, product-eval datasets
                     |
   Checks + requirement coverage + comparison             optimize/checks.py, compiler/eval_*.py
                     |
       Evidence report + export/import + revision         optimize/workflow.py, compiler/evidence.py
```

## Records, and what binds them

A case is a directory you own. Every record that later evidence depends on carries a sha256 of the exact content it describes, and loading re-checks it.

| Record | File | Bound by | Verified on load |
|---|---|---|---|
| Case | `case.json` | revision and run digests, constraint ledger | schema id |
| Clarification snapshot | `case.json.clarification` | sha256 of the answers file used at compile | - |
| Constraint | `case.json.constraints[]` | id, version, state, history, linked criteria | - |
| Revision N | `revisions/vN.json` (exclusive create) | `sha256` of the prompt, repeated in `case.json` | both digests |
| Run (recorded output) | `runs/R<k>.json` (exclusive create) | `output_sha256`, `revision_sha256`, `input_sha256` | output digest and case summary |
| Verdict | `checks/verdicts.json` | `revision_sha256`, `criterion_sha256`, and for outputs `run_id` + `output_sha256` | stale if any differ |
| Check run | `checks/runs/<run_id>.json` (exclusive create) + `checks/vN.json` (latest view) | revision and criteria digests | - |
| Export | zip + `manifest.json` | sha256 of every file | every digest, entry paths, completeness |

`case.json` and the latest views are written atomically (temp file + `os.replace`). Revisions, runs and check runs are never overwritten.

**Trust boundary.** These digests detect drift, accidental edits and incomplete copies. A person who controls the whole directory can rewrite a record and its digests together; hashes do not make a local workspace tamper-proof, and Proofhouse does not claim they do. Signed exports are a possible later feature if a real verification need appears.

## What a PASS means

`optimize check` reports one of `PASS`, `FAIL`, `UNJUDGED` (manual, no bound verdict) or `NOT_EVALUATED` (output check, no recorded output) per criterion. A revision is `PASS` only when every criterion passes **and** every accepted constraint is satisfied by the criteria linked to it ([decision 0002](decisions/0002-what-pass-means.md)). Each result is labeled with its evidence class:

| Class | Source | Measures |
|---|---|---|
| prompt-text check | the revision's prompt | what the prompt says, not what a model does |
| recorded-output check | outputs you imported with `optimize output add` | those outputs only |
| human judgement | `optimize verdict`, bound to the digests it judged | your judgement |

The closed-loop compiler path adds its own evidence classes (`structural_compile_check`, `imported_observation_check`) and a `not_measured` list; a structural PASS never claims semantic quality.

## Compiler path and live execution

`closed-loop` maps structured requirements to IR, compiles with the offline fake adapter, runs the deterministic oracle and, optionally, product evaluation over imported observations. Evidence records each stage separately with its own evaluator identity, the repair budget, attempts and terminal reason ([decision 0003](decisions/0003-imported-observations-and-repair.md)).

`execute-openai` is the only live path. It is opt-in and needs a model, credential and ceilings at call time. The system message is rendered from `compiler/runtime_context.py`, which gives every IR field an explicit disposition (rendered, enforced by a request parameter, enforced by the compiler, metadata only, or unsupported). An unsupported mandatory field (required knowledge without content, persistent memory) refuses before any request is sent. The cost ceiling is recorded as a declared budget; it is **not** enforced before sending, because no pricing data is shipped.

## Model notes

Profiles come from `src/proofhouse/optimize/data/model_registry.json` and are copied to every surface by `scripts/generate_model_surfaces.py`. Each resolved profile carries `source` (builtin, cached, researched, user_supplied, fallback) and `verification` (unverified, sourced, reviewed). A review date is not verification ([decision 0004](decisions/0004-model-note-provenance.md)).
