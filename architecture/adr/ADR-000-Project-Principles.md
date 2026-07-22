# ADR-000 — Project Principles

**Status:** Accepted  
**Date:** 2026-07-21

## Decision

PromptRig adopts architecture-first, contract-first, evidence-driven development. Canonical IR preserves user intent; validation precedes provider lowering; diagnostics and historical evidence are immutable; unsupported semantics fail explicitly.

## Consequences

Implementation convenience cannot silently weaken accepted architecture. Contract changes require a versioned decision, compatibility assessment, tests, and traceability to source requirements.
