# ADR-006 — Reasoning/thinking configuration surface missing from PromptRig IR v0.1

**Status:** Accepted — the architectural gap is confirmed by three independent findings (MISSION-003, MISSION-004, MISSION-005); no specific schema-change shape is authorized by this acceptance, only the existence and reality of the gap.
**Date:** 2026-07-22
**Raised by:** Architect review, following independent findings in MISSION-003 and MISSION-004.

## Context

`PROMPTRIG_IR_V0_1.schema.json` has no field through which a caller can specify a per-request reasoning or thinking configuration (for example, a reasoning-effort level, a thinking-token budget, or any other provider-facing control over extended/adaptive reasoning behavior).

This gap was found independently, by two different adapters, working from two different providers' documentation, in two separate missions:

- **MISSION-003 (OpenAI adapter):** the capability manifest correctly reports `reasoning.effort_control@1` as `conditional`, but no artifact field can reflect a reasoning-effort setting, because the frozen IR has no field to source one from.
- **MISSION-004 (Anthropic adapter):** the capability manifest reports `reasoning.extended_thinking@1` with detailed, well-corroborated limits (`budget_tokens_minimum`, signature/preservation requirements, incompatibilities), but `budget_tokens` is always `null` in the lowered artifact for the same reason — the frozen IR has no field to source a concrete value from.

Both adapters modeled their respective provider's reasoning/thinking behavior faithfully and explicitly (never silently dropping or flattening the missing state — both surface it honestly as an unfillable field rather than fabricating a value). The gap is not an adapter defect in either case. It is a property of the frozen IR itself.

Per Architect Mode's evidence-over-preference law, two independent, unrelated confirmations of the same missing surface is treated here as sufficient evidence to formally record the finding, rather than waiting for a third (Gemini) occurrence to accumulate before acknowledging a pattern that already exists.

## Decision (proposed, not yet accepted)

Record this as a candidate architectural gap in PromptRig IR requiring a future versioned schema change. No action against the frozen `PROMPTRIG_IR_V0_1.schema.json` is authorized by this ADR. This document exists to:

1. Make the cross-provider nature of the finding visible and traceable, rather than letting it sit as two disconnected technical-debt bullet points in separate mission reports.
2. Provide a home for the eventual decision, whenever the owner and architect choose to act on it — likely as part of a future IR minor/major version (e.g. `0.2.0` or later), scoped by its own SPEC and ADR at that time.
3. Explicitly avoid scope creep: this ADR does not itself define the shape of the future field, does not authorize any implementation work, and does not block MISSION-005 or any other in-flight adapter mission.

## Candidate shape (non-binding, for future discussion only)

Not decided here. Options that a future SPEC might consider, listed only to make the design space visible, not to preselect one:

- A generic, provider-agnostic `reasoning` block in IR (e.g. an `effort` enum plus an optional `budget_tokens`-style numeric field), left optional and capability-resolved the same way `tools` and other optional IR sections are today.
- Per-adapter passthrough configuration, explicitly scoped and versioned, if a fully generic cross-provider shape proves too lossy.
- Deferring entirely until a fourth or fifth adapter's requirements clarify whether a shared shape is even achievable, versus provider-specific extension points.

Any of these requires its own SPEC, an accepted ADR revision superseding this one, and explicit owner ratification before implementation — this document is not that decision.

## Consequences of staying in Proposed status

- MISSION-003 and MISSION-004's adapters remain correct and complete as shipped: they report `conditional`/appropriate capability status and leave the artifact field genuinely empty rather than guessing, which is the right behavior given the current IR.
- Future adapters (Gemini, and beyond) should continue to surface the same gap explicitly if they hit it, rather than working around it locally — that keeps the evidence trail intact for whenever this ADR is revisited and either accepted (triggering a real schema-change SPEC) or explicitly rejected/deferred further by the owner.
- This ADR should be referenced from any future adapter mission's Technical Debt section that encounters the same gap, rather than each mission re-describing it as if newly discovered.

## Evidence

- `MISSION_002...MISSION_004` — `PROMPTRIG_IR_V0_1.schema.json` (`architecture/compiler-contract-freeze-v0.5/`), confirmed frozen, no reasoning/thinking field present.
- MISSION-003 Technical Debt: `reasoning.effort_control@1` capability-mismatch gap.
- MISSION-004 Technical Debt: `reasoning.extended_thinking@1` `budget_tokens` always-null finding, and the report's own MISSION-005 recommendation language proposing escalation "if Gemini hits the same gap."
