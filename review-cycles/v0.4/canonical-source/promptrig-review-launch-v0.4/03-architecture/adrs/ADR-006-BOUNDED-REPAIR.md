# ADR-006-BOUNDED-REPAIR — Bounded Evaluation and Repair

**Status:** Accepted

## Context

Unbounded autonomous refinement is costly, nonterminating, and difficult to audit.

## Decision

Repair loops must have explicit attempt, time, cost, and regression limits and must preserve evidence from unsuccessful attempts.

## Consequences

The system may stop with unresolved failures and must report them honestly.

## Review trigger

Revisit when evidence materially changes the tradeoff, not merely because an implementer prefers another stack.
