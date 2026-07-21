# Architecture Freeze Checklist

Implementation is authorized only when all required items are checked and signed in the decision log.

## Scope and value

- [ ] Core user problem and target personas are explicit.
- [ ] MVP exclusions are explicit.
- [ ] Every P0 requirement maps to architecture and acceptance tests.

## Architecture

- [ ] IR ownership, versioning, and migration rules are accepted.
- [ ] Compiler stage boundaries and deterministic/model-assisted behavior are defined.
- [ ] Provider adapter contract is accepted.
- [ ] Data, job, authentication, storage, and secret boundaries are accepted.
- [ ] Failure recovery and observability are designed.

## Security and privacy

- [ ] Threat model covers prompt injection, tool abuse, secret leakage, cross-tenant access, malicious uploads, supply chain, and evaluator manipulation.
- [ ] Critical and high findings are resolved or formally waived with owner and expiry.
- [ ] Data retention and deletion behavior are testable.

## Benchmark

- [ ] Task, environment, budgets, intervention policy, hidden-test contract, sealing, and scoring are executable.
- [ ] Model/harness identity and routing evidence are captured.
- [ ] Repeated-run and variance policy is fixed.
- [ ] Marketing-claims policy is accepted.

## Product and operations

- [ ] Simple Mode has an end-to-end usability test.
- [ ] Developer Mode exposes traceable technical artifacts.
- [ ] Cost ceilings and bounded repair are defined.
- [ ] Backup, restore, migration, and incident paths are designed.

## Review

- [ ] Independent reviews completed.
- [ ] Findings synthesized and dispositions recorded.
- [ ] ADRs and RFCs updated.
- [ ] No unresolved critical finding remains.
- [ ] Architecture freeze version and commit are tagged.
