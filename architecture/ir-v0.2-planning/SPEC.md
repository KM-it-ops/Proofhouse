# PromptRig IR v0.2 SPEC (planning draft)

**Status:** Planning package only. **Not a production schema.** Not CERTIFIED IR v0.2. No frozen v0.1 edit.
**Mission:** MISSION-031 / campaign U5.
**Owner gate:** **Q4** — continuation and reasoning shapes. The owner decides later; this SPEC lists options, owners, and the invalid-field rule.
**Live in this campaign:** **single-request.** Multi-turn live cannot work under frozen IR v0.1.

This document is not an implementation authorization. Production schema/code requires a later mission after Q4 plus a separately accepted ADR revision.

## Semantic delta

Continuation and reasoning are distinct gaps. Resolving one does not resolve the other.

| Axis | Continuation (ADR-007, still Proposed) | Reasoning (ADR-006, Accepted as a gap only) |
|---|---|---|
| What it is | Provider-returned opaque state that must be echoed on a later turn | Caller-chosen per-request configuration (effort, thinking budget) |
| When it appears | Across requests (session/turn). IR v0.1 is a single compiled request | Inside one request |
| Neutral owner if canonicalized | Session/turn continuation blob + provenance + retention class — never a vendor key | Caller-chosen reasoning configuration — never a vendor vocabulary enum copied into IR |
| v0.1 today | No session/turn concept; nowhere to put the blob | No field; adapters report conditional/unsupported; do not invent a value |
| OQ lock | OQ-008-008 deferred for v0.1 | OQ-008-009 remain unsupported in v0.1 |

Provider API shapes (Gemini thought signatures, Anthropic thinking-block signatures, OpenAI encrypted reasoning items) are evidence that a problem exists. They are not candidate IR field names.

## Q4 options (see `OPTIONS.json`)

Every candidate option must have a **provider-neutral owner** or be **explicitly rejected**. A proposed field without a provider-neutral owner is **invalid**.

### Continuation

1. **Evidence-only (recommended for U6).** Owner: execution artifact / evidence bundle, not IR. Live stays single-request; any opaque echo lives beside the request, not inside `PROMPTRIG_IR_V0_1`.
2. **Provider-neutral IR field (Q4 option).** Owner: opaque continuation state attached to a future conversation/session concept, with provenance, integrity, and retention. Requires a later production schema mission after owner pick. Not authorized here.
3. **Prohibit canonical storage (Q4 option, explicit reject of durable storage).** Owner: none in PromptRig canonical surfaces; callers hold state out-of-band. Explicitly rejected as an IR or evidence field.

### Reasoning

1. **Remain unsupported in v0.1 (current).** Explicitly rejected for frozen v0.1. ADR-006 records the gap; no schema shape is authorized.
2. **Provider-neutral reasoning block (Q4 option).** Owner: caller-chosen reasoning configuration (`effort` enum + optional numeric budget), capability-resolved like other optional IR sections. Requires later SPEC/ADR/owner ratification. Not authorized here.
3. **Per-adapter passthrough (explicitly rejected as canonical IR).** Owner would be a vendor surface. Rejected: no provider-neutral owner, so it is not a valid IR field.

## Invalid-field rule

A proposed field without a provider-neutral owner is invalid. Example: `gemini_thought_signature` on the IR object. Documented in `OPTIONS.json` (`INV-PROVIDER-SHAPED-THOUGHT-SIGNATURE`).

## U6 recommendation

Recommend **evidence-only continuation** for the U6 live path (artifact/evidence, not an IR field). Do not implement live HTTP in this mission. Reasoning stays unsupported in v0.1.

## Compatibility (summary)

v0.1 inputs retain defined behavior. Unknown `spec_version` and downgrade of a declared later document fail closed. See `COMPATIBILITY_MIGRATION.md` and `fixtures/`.

## Non-claims

- Not a production schema. Frozen `PROMPTRIG_IR_V0_1.schema.json` bytes stay identical.
- Not CERTIFIED IR v0.2. Not M3. Not a live implementation.
- Does not Accept ADR-007. Does not change ADR-006 status.
- Does not start U6.
