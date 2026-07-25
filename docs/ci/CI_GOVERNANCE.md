# PromptRig CI Governance

## Purpose

PromptRig uses three validation tiers so routine work receives fast, relevant feedback while the complete cross-platform matrix remains a deliberate final gate.

## Tier 1 — CI Fast

`CI Fast / scoped` runs on pull requests targeting `feature/promptrig-framework` and on pushes to `main`.

The job classifies the changed paths and selects the least expensive valid check set:

- `docs`: whitespace integrity and changed-Markdown local-link validation;
- `requirements`: CI helper tests, requirements-contract tests, and TypeScript drift when schemas changed;
- `compiler`: CI helper tests, Compiler Core tests, and installed CLI smoke checks;
- `broad`: complete pytest plus relevant drift and smoke checks.

Superseded runs are cancelled per pull request or ref.

## Tier 2 — CI Final Gate

The full matrix is not an ordinary commit check. It runs only when:

- a pull request targeting `feature/promptrig-framework` carries the `ci:final-gate` label; or
- an authorized operator dispatches the workflow with both a ref and its expected exact SHA.

The gate verifies the checked-out SHA before running:

- Ubuntu, Windows, and macOS;
- Python 3.11 and 3.12;
- complete pytest;
- all four legacy datasets;
- installed and module Compiler Core smoke checks;
- TypeScript regeneration drift.

If the pull-request head changes while `ci:final-gate` remains present, the final gate reruns for the new head and any prior exact-head review becomes stale.

## Tier 3 — CI Post-Merge Smoke

A push to `feature/promptrig-framework` runs one Ubuntu/Python 3.11 verification job. It checks package installation, Compiler Core health, frozen-contract drift, and the requirements contract validator.

The post-merge job does not repeat the complete matrix already proven against the merged exact head.

## Merge evidence contract

Before merge, the mission record must identify:

1. exact pull-request head;
2. successful `CI Fast / scoped` result;
3. successful `CI Final Gate` result for the same exact head;
4. independent review target and verdict;
5. unresolved review-thread count;
6. explicit owner merge authorization.

A changed head invalidates exact-head CI Final and independent-review evidence.

## Quota handling

Hosted-run quota exhaustion is recorded honestly. It does not authorize dummy commits, repeated retries, weaker checks, fabricated evidence, or bypassing an explicit final gate.

## Branch-protection recommendation

Require the stable `CI Fast / scoped` check on pull requests to `feature/promptrig-framework`. Treat the exact-head CI Final result as governed merge evidence unless repository settings can require it without leaving unlabeled pull requests permanently pending.

## Non-claims

This workflow design does not authorize automatic merge, reduce the final cross-platform matrix, purchase additional Actions usage, add self-hosted runners, or begin MISSION-009.
