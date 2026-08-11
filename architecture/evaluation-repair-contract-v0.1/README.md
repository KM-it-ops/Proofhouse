# Evaluation and Bounded Repair Contract v0.1

**Status:** `PROPOSED` — executable contract evidence for MISSION-009. Not production-certified. Does not authorize a production evaluator/repair engine, live providers, benchmarks, UI, or MISSION-010/011 without separate launch.

**Exact baseline:** `main` at `d0bca1c9ebbf6ab4dfbfbab75ec27456c4f263cf`.

## Purpose

Define deterministic-first evaluation, baseline/candidate comparison, bounded repair (budgets 0–2), regression, and evidence semantics that close the compiler loop while preserving MISSION-008 requirement identities.

## Authority (non-negotiable)

1. Deterministic validators, schema validators, and security policy checks are authoritative for schema, security, and executable correctness.
2. Model judges are advisory only and must set `authoritative_for_executable=false`.
3. Failed attempts and regressions are retained evidence; discarding them is a contract violation (`EVR-EVD-0001`).
4. Termination must not depend on model self-report (`EVR-TRM-0001`).
5. Scoring must not hide evaluator errors (`EVR-SCR-0001`).
6. Repair must not weaken accepted objectives or security constraints (`EVR-SEC-0001`).
7. Default evaluation is no-network (`network_allowed=false`, `network_used=false`).

## Package index

| Path | Role |
|---|---|
| EVALUATION_REPAIR_SPEC.md | Normative terms and statuses |
| AUTHORITY_AND_PRECEDENCE.md | Evaluator authority order |
| BASELINE_AND_CANDIDATE.md | Baseline/candidate identity rules |
| REPAIR_BUDGETS_AND_MUTATIONS.md | Budgets 0/1/2 and stop states |
| EVIDENCE_MODEL.md | Evidence and REQ-* linkage |
| DIAGNOSTICS.md | EVR-* namespace |
| TRACEABILITY.md | Trace rules |
| SECURITY_CONSTRAINTS.md | Immutable security/objectives |
| DECISION_LOG.md | Proposed decisions |
| OPEN_QUESTIONS.md | Open questions |
| OWNER_DECISION_REQUEST.md | Owner choices |
| schemas/ | Draft 2020-12 schemas |
| fixtures/ | Semantic oracle + schema instances |
| validate_contract.py | Test-only validator |
| evidence/ | Validation evidence output |

## Out of scope

Production evaluator/repair engines, live provider judges as required infrastructure, unbounded repair, benchmarks, UI, hosted jobs, IR v0.2, frozen Compiler Core diagnostic registry edits.
