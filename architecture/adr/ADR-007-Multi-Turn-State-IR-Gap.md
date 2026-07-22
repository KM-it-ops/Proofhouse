# ADR-007 — Multi-turn/conversation-state surface missing from PromptRig IR v0.1

**Status:** Proposed / Candidate — not yet accepted, no schema change authorized by this document.
**Date:** 2026-07-22
**Raised by:** Architect review, following a finding in MISSION-005 (Gemini adapter).

## Context

`PROMPTRIG_IR_V0_1.schema.json` compiles a single request. It has no concept of a conversation, session, or turn sequence, and therefore no field capable of carrying state returned by a provider on one turn forward into a subsequent compiled request.

MISSION-005 (Gemini adapter) surfaced this while investigating Gemini's mandatory thought-signature continuation-token requirement: Gemini returns an opaque signature that the caller must echo back on a later turn to preserve reasoning continuity when using function calling. The IR cannot represent this — not because a specific field is missing, but because the IR has no concept of "a later turn" at all.

This is related to, but explicitly distinct from, the gap recorded in ADR-006. ADR-006 concerns a missing field for a *caller-chosen configuration value* (a reasoning-effort level or thinking-token budget) within a single request. This gap concerns *provider-returned opaque state* that must be carried across multiple requests — a session/turn-state modeling question, not a configuration-field question. Resolving ADR-006 (e.g. adding a `reasoning` block to a single compiled request) would not resolve this gap; they require different, independently-scoped IR extensions.

This is currently a single, first-occurrence finding (Gemini only). Unlike ADR-006, this has not yet been independently confirmed by a second unrelated provider or adapter, though OpenAI's and Anthropic's adapters did not surface an equivalent finding in their own missions — it is plausible this is a Gemini-specific requirement (its thought-signature model) rather than a universal one, or it may simply not have been triggered by the fixture/IR shapes exercised so far. This ADR is Proposed accordingly, at a lower confidence tier than ADR-006's now-Accepted status.

## Decision (proposed, not yet accepted)

Record this as a candidate architectural gap in PromptRig IR requiring a future versioned schema change, separate from ADR-006. No action against the frozen `PROMPTRIG_IR_V0_1.schema.json` is authorized by this ADR. This document exists to:

1. Make this a distinctly tracked finding rather than folding it into ADR-006, where its different nature (opaque returned state vs. caller-chosen configuration) would be lost.
2. Provide a home for a future decision, likely as part of IR `0.2.0` or later, its own SPEC, and explicit owner ratification.
3. Avoid scope creep: this ADR does not define the shape of any future session/turn-state model, does not authorize implementation work, and does not block any in-flight or future adapter mission.

## Candidate shape (non-binding, for future discussion only)

Not decided here. Listed only to make the design space visible:

- A generic, provider-agnostic opaque "continuation state" field attached to a conversation/session-level IR concept (which does not currently exist and would itself be a larger addition than a single field).
- A narrower carve-out scoped specifically to reasoning/thinking continuity, separate from a full multi-turn IR model, if a full session concept proves too large a change for near-term needs.
- Deferring entirely until a broader multi-turn use case (not just reasoning-signature echoing) makes the need for session/turn modeling unambiguous.

Any of these requires its own SPEC, an accepted ADR, and explicit owner ratification before implementation.

## Consequences of staying in Proposed status

- The Gemini adapter remains correct and complete as shipped: it explicitly represents the shape of the continuation requirement in its artifact (mandatory when function calling, opaque, must be echoed back) without fabricating or omitting the signature value, given the current IR has nowhere to source one from.
- Future adapter or evaluation/repair missions that involve multi-turn interaction should reference this ADR explicitly if they hit the same gap, rather than re-describing it as newly discovered — this keeps the evidence trail intact for whenever this ADR is revisited.
- If a second, independent provider or use case confirms the same gap, this ADR should be revisited for possible escalation, the same way ADR-006 was.

## Evidence

- `PROMPTRIG_IR_V0_1.schema.json` (`architecture/compiler-contract-freeze-v0.5/`), confirmed frozen, no session/turn/conversation-state concept present anywhere in the schema.
- MISSION-005 Technical Debt: "Thought-signature/multi-turn continuation state cannot be represented in IR v0.1 at all," and the dedicated "ADR-006 third-confirmation check" report subsection explicitly distinguishing this finding from the ADR-006 gap.
- `PROVIDER_SELECTION_MATRIX.md`: Gemini's documented "thinking levels/signatures with model-specific continuation rules."
