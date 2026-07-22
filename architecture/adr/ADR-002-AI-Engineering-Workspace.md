# ADR-002 — AI Engineering Workspace

**Status:** Accepted / Deferred  
**Date:** 2026-07-21

## Decision

Use `C:\\AI\\skills\\architect-mode` as the canonical reusable Architect Mode location and keep a versioned snapshot in PromptRig. A broader AI Engineering Workspace product is deferred until a stable compiler milestone.

## Consequences

Canonical methodology updates occur in the reusable workspace first; repository snapshots identify their version and do not overwrite user-created workspace files blindly.
