# PromptRig Acceptance Criteria

**Version:** 0.2.0

## Release classifications

### Benchmark-complete
A submission satisfies all benchmark hard gates and provides a sealed evidence package. It is not automatically production-ready.

### Alpha-ready
A benchmark-complete implementation also passes security, tenancy, recovery, accessibility, and observed-user testing thresholds.

### Production-ready
An alpha-ready implementation additionally completes operational readiness, privacy/legal review, monitoring, incident response, billing controls, backup restoration, and a documented launch approval.

## Hard gates for Benchmark 1

1. Clean checkout builds without manual source edits.
2. Documented one-command local startup succeeds.
3. Database migrations succeed from an empty database.
4. Unit, integration, contract, and end-to-end suites pass.
5. Type checking and linting pass.
6. PromptRig IR validates against the canonical schema.
7. Two mandatory provider adapters pass shared conformance tests.
8. Simple Mode creates, compiles, evaluates, and exports a project.
9. Developer Mode exposes and safely edits the same project IR.
10. Static validation catches malformed IR, schemas, adapters, and artifact manifests.
11. Behavioral evaluation records baseline and candidate results.
12. Repair terminates within configured limits and preserves prior versions.
13. Exported bundle validates and includes provenance.
14. Authentication and project-level authorization are enforced.
15. Cross-tenant access tests fail closed.
16. Provider credentials are encrypted or stored in the designated secret system and never returned to clients.
17. No committed secrets or critical known vulnerabilities remain.
18. The submission manifest, SBOM, test report, and trace summary are complete.

## Required Simple Mode flow

A new nontechnical user can:

1. create an account
2. create a project
3. describe an AI goal in ordinary language
4. review a plain-language interpretation and consequential assumptions
5. select or accept a recommended provider/mode
6. compile the project
7. understand whether tests passed and what remains uncertain
8. try a sample interaction
9. download the project package

No developer terminology is required to finish this flow.

## Required Developer Mode capabilities

- inspect/edit canonical IR with validation
- inspect generated provider artifacts
- inspect capability resolution and fallbacks
- inspect evaluation cases and results
- inspect traces, model identifiers, cost, and latency
- configure zero to two repair passes
- download machine-readable artifacts
- restore a prior version

## Evaluation acceptance

- 100% termination under configured limits
- 100% deterministic schema-test completion
- at least 95% pass rate on normative contract tests
- no candidate may be declared improved unless it exceeds or equals the baseline on hard gates and meets the configured weighted threshold
- regressions are visible and preserved in the result
- evaluator failures are distinguished from candidate failures

## UX acceptance

- keyboard-operable primary flows
- accessible names and focus states
- responsive layout at supported breakpoints
- clear loading, empty, success, partial-success, and failure states
- destructive operations require confirmation
- Simple Mode avoids unexplained technical jargon

## Security acceptance

- tenant isolation enforced server-side
- authorization tested on every project resource class
- prompt-injection tests cover uploaded and retrieved content
- outbound tool actions default deny unless declared
- audit records for credential changes and consequential actions
- rate limits and bounded retries
- secure headers and dependency scanning

## Evidence requirements

Every acceptance claim must point to one of:

- automated test output
- build artifact
- trace record
- screenshot/video identified by hash
- human-review record
- explicit waiver approved in the decision log
