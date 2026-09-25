# 0003: Imported observations are bound, covered, and never repaired against

Accepted 2026-09-21.

## Decision

Product evaluation (closed-loop `--product-eval-*`, `evaluate-product`) scores observations the caller supplies; Proofhouse did not generate them. Therefore:

- Results record the dataset and rubric sha256, rubric id/version, a per-case result table, and `observation_source: imported`.
- Duplicate `case_id` or `criterion_id` values are rejected; scores use structured `(case_id, criterion_id)` keys, and aggregation does not depend on case order.
- Every mandatory requirement must appear in some case's `req_ids`, or the result is `BLOCKED` (`EVR-COV-0001`).
- A row may declare `candidate_digest`; a mismatch with the candidate under evaluation is `BLOCKED` (`EVR-BND-0001`). Rows without one are reported as `unbound`.
- When product evaluation fails, the closed loop does not attempt repair — rewording the prompt cannot change static observations — and says so: `EVR-REP-0005`, `terminal_reason: repair_unsupported_imported_observations`, with the true evaluator identity and the failing cases kept.

## Why

The review showed a passing duplicate row erasing a failing one, a dataset about an unrelated requirement producing a PASS that claimed the declared requirement, and a product failure reported with the wrong evaluator and no repair explanation.

## Consequences

Datasets that relied on duplicate ids or on covering only some mandatory requirements now fail loudly. Meaningful automated repair needs regenerated outputs, which is the `optimize` workflow's revise → record → output path.
