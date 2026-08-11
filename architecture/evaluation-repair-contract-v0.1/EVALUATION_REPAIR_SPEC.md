# Evaluation Repair Spec

## Statuses

`PASS`, `FAIL`, `ERROR`, `BLOCKED`, `UNAVAILABLE`, `REGRESSION`, `UNRESOLVED_DEFECT`.

## Determinism

Given identical request, evaluators, and fixtures, validation outcomes are byte-stable. No network. No wall-clock dependence in the oracle.

## Fail-closed

Unavailable evaluators, schema failures, authority violations, and evidence gaps produce `BLOCKED`/`ERROR`/`UNAVAILABLE` — never a silent PASS.
