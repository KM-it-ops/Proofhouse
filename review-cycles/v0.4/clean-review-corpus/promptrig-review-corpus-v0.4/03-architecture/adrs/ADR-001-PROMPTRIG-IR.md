# ADR-001-PROMPTRIG-IR — PromptRig IR as Canonical Semantic Layer

**Status:** Accepted

## Context

Portability, diffability, validation, migrations, and provider-specific lowering require a stable semantic layer.

## Decision

Use a versioned typed intermediate representation as the canonical semantic system description. Provider artifacts are generated from it rather than authored as independent sources of truth.

## Consequences

Schema evolution and semantic-versioning discipline become mandatory.

## Review trigger

Revisit when evidence materially changes the tradeoff, not merely because an implementer prefers another stack.
