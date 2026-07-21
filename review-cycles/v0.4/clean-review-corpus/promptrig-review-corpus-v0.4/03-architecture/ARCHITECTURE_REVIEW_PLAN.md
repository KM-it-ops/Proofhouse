# Architecture Review Plan

## Review objective

Find contradictions, unjustified complexity, missing controls, brittle abstractions, benchmark bias, security gaps, and product assumptions before production implementation.

## Review rounds

### Round 1 — Independent critique

Each reviewer receives the same canonical corpus and one specialist assignment. Reviewers may not see one another's findings.

### Round 2 — Cross-examination

A separate synthesizer groups duplicate findings, identifies disagreements, requests evidence, and challenges weak recommendations.

### Round 3 — Resolution

Every material finding receives one disposition: accept, accept with modification, defer with owner/date, reject with rationale, or superseded.

### Round 4 — Architecture freeze

The board validates that blocking findings are resolved, ADRs are accepted, schemas are coherent, benchmark rules are executable, and remaining risks are explicitly owned.

## Severity

- **Critical:** unsafe or invalidates the product/benchmark; blocks implementation.
- **High:** likely major rework, security failure, or misleading result; blocks freeze unless formally waived.
- **Medium:** meaningful weakness with bounded workaround.
- **Low:** polish, maintainability, or future enhancement.

## Required reviewer output

Every finding must include ID, severity, affected documents, evidence, failure scenario, recommendation, validation method, and confidence. Vague opinions are rejected.
