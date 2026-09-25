# Evidence format

## Optimize case directory

```text
advisory-case/
  case.json               proofhouse.optimize.case/v0: objective, model profile, stage,
                          revisions[] (n, sha256, parent, feedback_on_previous),
                          criteria[] (id, kind, value, note, target?), constraints[],
                          clarification {answers, answers_sha256}, runs[] (summaries)
  answers.json            your answers to the clarify packet
  01-clarify.md           packets you run elsewhere (contain local paths; not exported)
  02-compile.md
  03-revise-vN.md
  revisions/vN.json       immutable; prompt + sha256 + rationale/settings/efficiency
  runs/R<k>.json          immutable; proofhouse.optimize.run/v1
  checks/verdicts.json    human verdicts, each bound to digests
  checks/vN.json          latest check view for revision N
  checks/runs/<id>.json   immutable check runs
```

### Constraint (`case.json.constraints[]`)

| Field | Meaning |
|---|---|
| `id` | `K1`, `K2`, ... |
| `text` | the requirement, in the user's words |
| `origin` | `clarification` (seeded from answers at compile) or `user` |
| `state` | `accepted`, `proposed`, `rejected`, `superseded` |
| `version`, `replaces` | a proposal carries the next version and the id it would replace |
| `criteria` | criterion ids whose results evidence it |
| `source_ref` | `answers.json#<question>` or `cli` |
| `history` | `{event, at, detail}` entries: accepted, proposed, linked, superseded, rejected |

### Run (`runs/R<k>.json`)

`run_id`, `revision`, `revision_sha256`, `input_id`, `input_sha256` (if an input file was given), `output_text`, `output_sha256`, `model`, `settings`, `method` (`imported`), `evidence_class` (`imported_output`), `source`, `recorded_at`.

### Verdict (`checks/verdicts.json`)

`revision`, `criterion`, `result` (`pass`/`fail`), `note`, `recorded_at`, `revision_sha256`, `criterion_sha256`, `checks_version`, and for output criteria `run_id` + `output_sha256`. A verdict whose digests do not match the current material is stale and counts as `UNJUDGED`.

### Check run (`checks/runs/<run_id>.json`)

`revision`, `revision_sha256`, `criteria_sha256` (per criterion), `checks_version`, `checked_at`, `target`, `results[]` (`id`, `kind`, `value`, `result`, and for output criteria `target: output` + `runs[]` with `run_id`, `input_id`, `output_sha256`, `result`; manual prompt criteria carry `stale_verdict`), `constraints[]` (`id`, `text`, `origin`, `criteria`, `status`), `overall`.

### Export bundle

A zip with `manifest.json` (`proofhouse.optimize.export/v1`: `files[]` with `path`, `bytes`, `sha256`; `package_version`; `excluded`; `notice`) and every file it lists. Import requires safe relative paths, a manifest that lists exactly the files present, and matching digests; it writes to a staging directory, re-verifies revisions and runs, then renames into place.

## Closed-loop evidence bundle

`evidence_schema: eeb-headless-v0.1` keys are unchanged. Added:

| Key | Meaning |
|---|---|
| `stage_schema` | `proofhouse.closed-loop.stages/v1` |
| `stages.compile` | `status`, `adapter` |
| `stages.deterministic_evaluation` | `status`, `diagnostic_codes`, `scores`, `evaluator`, `attempt_index` |
| `stages.product_evaluation` | `null`, or `status`, `evaluator`, `observation_source`, `candidate_digest`, `candidate_binding`, `dataset_sha256`, `rubric_sha256`, `rubric`, `aggregation`, `case_results[]`, `requirement_coverage` |
| `stages.repair` | `budget`, `attempted`, `terminal_reason` (`not_needed`, `passed_after_repair`, `repair_budget_exhausted`, `repair_budget_zero`, `refused_immutable`, `repair_unsupported_imported_observations`, `blocked_before_repair`) |
| `candidate_digest` | the candidate the final evaluation was about |
| `requirement_coverage` | `required`, `covered`, `missing`, `not_declared` |
| `evidence_classes` | e.g. `structural_compile_check`, `imported_observation_check` |
| `not_measured` | e.g. `live_model_output`, `semantic_quality` |
| `evaluator` | the evaluator that produced the final result (product evaluator when it ran) |

## Live execution envelope

`execute-openai` success envelopes add `runtime_context` (`version`, `fields[]` with `source_path`/`disposition`/`detail`, `unsupported[]`, `system_message_sha256`) and `admission` (`cost_ceiling` with `declared_usd`, `enforcement: declared_only_not_enforced_pre_send`, `pricing_source: null`, `input_token_estimate: null`; `output_token_ceiling`). A refused request (`EXE-SEM-0001`) lists `unsupported_semantics`.

Diagnostic codes are listed in [surfaces.md](surfaces.md#diagnostic-codes-added-by-the-evidence-integrity-work).
