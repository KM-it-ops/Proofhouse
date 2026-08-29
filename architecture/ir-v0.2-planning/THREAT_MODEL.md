# Threat model — opaque provider-returned continuation state

**Status:** Planning. No production storage of continuation blobs in IR v0.1.
**Scope:** Provider-returned opaque state (thought signatures, thinking-block signatures, encrypted reasoning items) if it is ever retained.

## Assets

- Canonical IR v0.1 (single-request; must not absorb vendor blobs).
- Evidence bundles and execution artifacts (the recommended U6 home if anything is retained).
- Credentials and live request payloads (U6, not this mission).
- User/project content that a provider may embed inside an opaque blob.

## Trust boundaries

- Provider → caller: blob is attacker-influenced relative to PromptRig (the provider, a MITM, or a previous-turn attacker may have shaped it).
- Caller → later request: echo-unmodified requirements create an integrity obligation, not a license to treat the blob as trusted input.
- Evidence store → later readers: retention and redaction rules apply even when the bytes are opaque.

## Threats

| ID | Threat | Why it matters | Control (planning) |
|---|---|---|---|
| TM-CONT-001 | Secret-in-blob | Encrypted or signed reasoning may still be sensitive or replayable | Do not put blobs in IR. If evidence-only, classify retention, redact logs, never commit fixtures with live blobs |
| TM-CONT-002 | Replay / confused deputy | Echoing a blob on the wrong session, tenant, or request continues someone else's turn | Bind any stored blob to request/session identity; fail closed on mismatch |
| TM-CONT-003 | Integrity bypass | Mutating a signature-required blob breaks provider checks or enables injection | Store verbatim; do not parse, rewrite, or interpret vendor structure |
| TM-CONT-004 | Canonicalization of a vendor key | A Gemini/Anthropic/OpenAI field name in IR freezes one API into PromptRig semantics | Invalid without a provider-neutral owner (see `OPTIONS.json`) |
| TM-CONT-005 | Silent downgrade | Stripping continuation so a v0.1 reader "succeeds" hides missing state | Fail closed on unknown version / downgrade |
| TM-CONT-006 | Cross-tenant leakage | Evidence or logs leak another user's continuation | Same tenancy/deletion rules as other evidence; U8 still owns hosted tenancy |
| TM-CONT-007 | Prompt injection via opaque echo | Treating the blob as model-visible text rather than provider-only state | Keep it out of IR `behavior.instructions`; evidence-only and provider-echo only |
| TM-CONT-008 | Live path contamination | Default compile grows an HTTP client or credential | U6 is opt-in and separate. This package implements no live HTTP |

## Recommended U6 posture

Evidence-only continuation: if U6 must round-trip a provider blob for a later owner-authorized turn, record it in the execution artifact/evidence, not in IR. Single-request live in this campaign can omit the blob entirely.

## Non-claims

This is not a live implementation, not a credential design, and not CERTIFIED IR v0.2. Skip-cert law is not a substitute for this threat model when Q4 later authorizes storage.
