# MISSION-008 Open Questions

**Status:** Owner-resolved 2026-08-22. `OQ-008-001` through `OQ-008-010` are decided below. Resolutions settle owner policy only. They authorize no production implementation, no engine change, no `RCD-008-*` rewrite, and no append to the frozen D-050 decision log. Fail-closed producer/engine behavior remains until a separately authorized campaign implements a named resolution.

| ID | Question | Alternatives | Consequence | Evidence required | Decision timing | Downstream impact |
|---|---|---|---|---|---|---|
| OQ-008-001 | **RESOLVED — require when bytes exist.** Should all source-backed requirements require a content digest, or only sources with stable bytes? | Require for all; require when bytes exist (**chosen**); allow optional | Universal digests may invent identity for ephemeral input; optional digests weaken reproducibility | API/interactive source lifecycle examples and replay requirements | Resolved | MISSION-010/011 evidence envelopes |
| OQ-008-002 | **RESOLVED — PARTIAL with evidence.** Should optional unresolved meaning produce `PARTIAL` when it has no representable IR target? | `PARTIAL` with evidence (**chosen**); `BLOCKED`; omit it | Determines whether honest partial compilation can preserve optional gaps | More mixed required/optional adversarial cases | Resolved | Status parity and consumer behavior |
| OQ-008-003 | **RESOLVED — policy-defined authority.** Which consequential categories always require owner-level rather than user-level approval? | Fixed owner-only list; policy-defined authority (**chosen**); all consequential owner-only | Over-broad gates harm usability; under-broad gates weaken governance | Phase 6 permission model and security review | Resolved as policy; live/production still Phase 6 | MISSION-011 certification and Phase 6 |
| OQ-008-004 | **RESOLVED — deterministic alias group.** How should semantically equivalent requirements from distinct sources be coalesced? | Preserve separately; deterministic alias group (**chosen**; later study for implementation); merge identity | Merging can erase provenance; preserving duplicates may complicate evaluation | Multi-source equivalence and conflict fixtures | Resolved as policy; implementation later | Evaluation and repair identity |
| OQ-008-005 | **RESOLVED — strict exact version.** What compatibility policy governs a future accepted 0.1 contract? | Strict exact version (**chosen**); negotiated minor compatibility; migration adapters | Controls installed consumers and evidence replay | Consumer matrix and migration fixtures | Resolved | MISSION-010/011 packaging |
| OQ-008-006 | **RESOLVED — yes when explicitly non-semantic.** Should advisory diagnostics ever coexist with `SUCCESS`? | Yes when explicitly non-semantic (**chosen**); only with `PARTIAL`; never | Affects status predictability and consumer UX | Advisory-only fixture suite and owner policy | Resolved | Library/CLI parity |
| OQ-008-007 | **RESOLVED — deferred.** Is PRS worth retaining after comparative authoring evidence? | Contract candidate; deferred (**chosen**); rejected | Premature promotion freezes syntax; rejection may discard ergonomic value | Full 41-case PRS rendering, grammar/source-map conformance, comparison with JSON/API/file | Resolved | Future authoring surface only |
| OQ-008-008 | **RESOLVED — defer.** What provider-neutral shape, if any, should represent opaque continuation state? | New IR field; artifact/evidence only; prohibit canonical storage; defer (**chosen**) | A premature shape may encode one provider and create security/retention debt | ADR-007 threshold, cross-provider use cases, replay/retention threat model | Resolved as deferral; Phase 5 still required for any shape | IR v0.2 and runtime state |
| OQ-008-009 | **RESOLVED — remain unsupported.** Should per-request reasoning controls enter canonical IR? | Provider-neutral bounded field; capability request; remain unsupported (**chosen**) | Provider vocabulary may leak into durable semantics | Cross-provider semantic cases and compatibility analysis | Resolved for IR v0.1; Phase 5 still required for any field | IR v0.2 and provider lowering |
| OQ-008-010 | **RESOLVED — structured-only.** Should `requirements-document.schema.json`'s `assumption`/`open_question` entries require the full structured record in every case, or continue to permit a bare non-empty string as informal shorthand? | Require structured records only (**chosen**); permit `oneOf[string, structured record]`; permit string-only | Resolved by explicit owner decision. Canonical assumption and question records now carry stable identity and normative evidence, so `assumption_refs`/`question_refs` close over every canonical record | Owner decision recorded below; schema, fixtures, and evidence updated accordingly | Resolved | Evidence-bundle closure over assumptions and questions is now well defined |

## Resolved questions

**OQ-008-001 — content digest when stable bytes exist.**

- **Resolution:** require a content digest when the source has stable bytes; do not invent identity for ephemeral input that has no bytes.
- **Authority:** explicit owner decision 2026-08-22. It is **not** appended to the frozen D-050 decision log and does not rewrite `RCD-008-*`.
- **Effect:** file and other byte-stable sources must carry a digest. API/interactive sources without bytes are not required to mint one.
- **Non-authorization:** no producer/engine change is authorized. Current fail-closed file-fragment-without-digest behavior remains until a separately authorized campaign implements this policy.

**OQ-008-002 — optional unresolved meaning is PARTIAL with evidence.**

- **Resolution:** optional unresolved meaning with no representable IR target produces `PARTIAL` with evidence, not `BLOCKED`, and is not omitted.
- **Authority:** explicit owner decision 2026-08-22. It is **not** appended to the frozen D-050 decision log.
- **Effect:** honest partial compilation may preserve optional gaps as evidence-bearing `PARTIAL`.
- **Non-authorization:** no status-table or engine change is authorized by this record. Required unresolved meaning remains fail-closed under existing rules.

**OQ-008-003 — policy-defined consequential authority.**

- **Resolution:** which consequential categories require owner-level rather than user-level approval is defined by accepted policy, not a frozen owner-only list and not “all consequential owner-only.”
- **Authority:** explicit owner decision 2026-08-22. It is **not** appended to the frozen D-050 decision log.
- **Effect:** undeterminable authority remains `BLOCKED` rather than assumed. A live/production permission model still requires Phase 6 evidence and a separate campaign.
- **Non-authorization:** no Phase 6 implementation, runtime permissions, or credential handling is authorized.

**OQ-008-004 — deterministic alias group (implementation later).**

- **Resolution:** semantically equivalent requirements from distinct sources form a deterministic alias group. Identities are not merged.
- **Authority:** explicit owner decision 2026-08-22. It is **not** appended to the frozen D-050 decision log.
- **Effect:** provenance of each source is preserved; aliasing is the coalescing rule for a later implementation study with multi-source fixtures.
- **Non-authorization:** the engine must not merge identities now. Until a later campaign, records remain separately preserved.

**OQ-008-005 — strict exact version for accepted 0.1.**

- **Resolution:** a future accepted 0.1 requirements contract is governed by strict exact version match. Unknown or other versions are unsupported (`RQC-VER-0001`).
- **Authority:** explicit owner decision 2026-08-22. It is **not** appended to the frozen D-050 decision log.
- **Effect:** negotiated minor compatibility and migration adapters remain the 1.x / packaging story (`COMPATIBILITY_PROMISE.md`: unknown major rejected; minor extensions need declared behavior; IR migration opt-in with provenance, never silent compile-time upgrade). They are not the 0.1 acceptance policy.
- **Non-authorization:** this does not drop `-draft`, accept a production 0.1 contract, or implement range matching.

**OQ-008-006 — advisory diagnostics with SUCCESS only when non-semantic.**

- **Resolution:** advisory diagnostics may coexist with `SUCCESS` only when they are explicitly non-semantic.
- **Authority:** explicit owner decision 2026-08-22. It is **not** appended to the frozen D-050 decision log.
- **Effect:** semantic diagnostics still prevent `SUCCESS`. Advisory-only, non-semantic diagnostics do not.
- **Non-authorization:** no diagnostic-class or CLI/library change is authorized until a campaign adds the advisory-only fixture suite.

**OQ-008-007 — PRS remains deferred.**

- **Resolution:** deferred. Aligns with accepted `RCD-008-009`. Not `CONTRACT_CANDIDATE`. Not `REJECTED`.
- **Authority:** explicit owner decision 2026-08-22. It is **not** appended to the frozen D-050 decision log.
- **Effect:** `PRS_DISPOSITION.md` and ADR-001 remain unchanged. Structured `authoring_mode=prs` envelopes (MISSION-019 / OAR-013) are not a PRS language.
- **Non-authorization:** no grammar, parser, formatter, language server, or CONTRACT_CANDIDATE promotion is authorized.

**OQ-008-008 — defer opaque continuation-state shape.**

- **Resolution:** defer. No provider-neutral IR field is chosen. Opaque provider continuation blobs are not stored in canonical IR v0.1.
- **Authority:** explicit owner decision 2026-08-22. It is **not** appended to the frozen D-050 decision log. ADR-007 remains Proposed.
- **Effect:** adapters may continue describing the *requirement* in lowering artifacts. Compact fixtures that mark continuation as `unsupported` remain valid. Any session/turn model remains Phase 5.
- **Non-authorization:** no IR v0.2 field, canonical storage of thought signatures / encrypted reasoning, or ADR-007 acceptance is authorized.

**OQ-008-009 — reasoning controls remain unsupported in canonical IR v0.1.**

- **Resolution:** remain unsupported in canonical IR v0.1. No provider-neutral bounded field and no IR-level capability-request value.
- **Authority:** explicit owner decision 2026-08-22. It is **not** appended to the frozen D-050 decision log. ADR-006 remains accepted as a *gap* only (no schema shape).
- **Effect:** adapter capability manifests may continue to report reasoning capabilities as conditional/unsupported without sourcing a value from IR. Compact fixtures that mark `REQ-REASONING-001` unsupported remain valid.
- **Non-authorization:** no IR `reasoning` block, no vendor vocabulary in durable IR, and no IR v0.2 implementation is authorized.

**OQ-008-010 — canonical assumption and question record structure.**

- **Resolution:** structured-only canonical records.
- **Authority:** explicit owner decision recorded in the MISSION-008 instruction context. It is **not** appended to the frozen D-050 decision log.
- **Effect:** `requirements-document.schema.json` no longer accepts bare strings for `assumptions` or `open_questions`. A canonical assumption requires `id`, `statement`, `impact`, `source_refs`, `acceptance_state`, and `consequential`, plus `approval_refs` when consequential. A canonical question requires `id`, `text`, `affected_requirement_refs`, `impact`, and `resolution_state`, plus `resolution_evidence` when resolved.
- **Fixture corpus:** the preserved 41-case semantic-oracle corpus is a **test-only semantic projection, not a canonical requirements document**. It was deliberately not rewritten into schema documents; its compact shorthand carries no canonical status and is not evidence of canonical record shape.
- **Non-authorization:** this resolution settles record structure only. It authorizes no production implementation and approves no `RCD-008-*` decision.

MISSION-021 implements OQ-008-001, OQ-008-002, and OQ-008-006 in the production engine/producer. MISSION-022 implements OQ-008-003, OQ-008-005, and OQ-008-010 in the production engine (OAR-016 Accepted 2026-08-24). MISSION-023 maps numbered/constraint `plain_language_v0` records to IR (OAR-017 Accepted 2026-08-24). MISSION-024 remaining-Phase-4B inventory (OAR-018 Ready, not Accepted). OQ-008-004, OQ-008-007, OQ-008-008, and OQ-008-009 remain locked-not-built. M3 / Simple Mode UI, live providers, full MISSION-008 production compiler, CERTIFIED maturity, and full Phase 4B exit remain unauthorized.
