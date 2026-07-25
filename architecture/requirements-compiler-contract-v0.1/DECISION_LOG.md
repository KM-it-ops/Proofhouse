# MISSION-008 Decision Log

**Status:** Accepted. All ten decisions were ratified by explicit owner decision on 2026-07-25 at head
`ce4a3ac05bca4bab5b2574555ba69560ef733680`, recorded in [OAR-002](../OWNER_ACCEPTANCE_RECORDS/OAR-002.md).

Ratification accepts the **contract direction** only. It is not certification, not capability promotion,
and not implementation authority, and it does not authorize merge, release, or tags.

These records are separate from the frozen D-050 decision log and must not be appended to it.

| ID | Decision | Status | Evidence |
|---|---|---|---|
| RCD-008-001 | Adopt the source-language-neutral requirements document and evidence bundle as the canonical boundary between authoring input and frozen PromptRig IR v0.1. | Accepted | `REQUIREMENTS_COMPILER_SPEC.md`; `REQUIREMENTS_EVIDENCE_MODEL.md` |
| RCD-008-002 | Adopt the authority order owner decision → user decision → accepted contract → source evidence → authorized default → deterministic derivation → model proposal → provider constraint → implementation convenience. | Accepted | `AUTHORITY_AND_DEFAULTS.md` |
| RCD-008-003 | Permit defaults only when visible, scoped, non-conflicting, attributable, and approved when consequential. | Accepted | `AUTHORITY_AND_DEFAULTS.md`; `SECURITY_PRIVACY_APPROVALS.md` |
| RCD-008-004 | Deterministic validation establishes structural and contract validity; semantic acceptance additionally requires a permitted authority basis and attributable source evidence. Model-assisted output remains proposal-only until separately accepted through an attributable decision record; no model call is part of MISSION-008. | Accepted | RC-070 through RC-074; model adversarial fixtures |
| RCD-008-005 | Adopt `SUCCESS`, `PARTIAL`, `BLOCKED`, `REFUSED`, and `INVALID_OUTPUT` as distinct terminal statuses for a validation attempt. | Accepted | RC-060 through RC-064; 41-case fixture set |
| RCD-008-006 | Adopt the separate, versioned `RQC-*` Requirements Compiler diagnostic namespace without modifying the frozen Compiler Core registry. | Accepted | `DIAGNOSTICS.md`; `requirements-diagnostic-registry.json` |
| RCD-008-007 | Represent security, privacy, and approvals as first-class requirements and require consequential uncertainty or missing authority to fail closed. | Accepted | `SECURITY_PRIVACY_APPROVALS.md`; adversarial fixtures |
| RCD-008-008 | Require every requirement to map to exact frozen IR v0.1 pointers or an explicit unresolved/prohibited/gap outcome, and every emitted IR leaf to trace to accepted meaning, authorized default, or permitted deterministic derivation. | Accepted | `TRACEABILITY.md`; mapping schema; evidence maps |
| RCD-008-009 | Recommend PRS disposition `DEFERRED` pending representative syntax, source-map, grammar, complexity, and value evidence; do not change ADR-001. | Accepted | `PRS_DISPOSITION.md`; `evidence/prs-evaluation-matrix.json` |
| RCD-008-010 | Carry IRG-008-001 and IRG-008-002 into separately authorized Roadmap Phase 5 planning without changing frozen IR v0.1. | Accepted | `evidence/unresolved-ir-gaps.json` |

## Decision effect

Owner approval ratified the requirements contract direction only. It does **not** implement a requirements
compiler, authorize a PRS parser or grammar, accept an IR v0.2 shape, start MISSION-009 through
MISSION-011, or authorize model calls, evaluation, repair, live execution, benchmark work, UI, hosted
infrastructure, merge, release, or tags. Merge, release, capability promotion, and later missions remain
separate explicit gates.

`RCD-008-009` is recorded as `Accepted` in the sense that its **content** — the `DEFERRED` PRS disposition —
is the accepted outcome. PRS is therefore deferred, not adopted: ADR-001 is unchanged, PRS is not accepted
contract syntax, and no grammar, parser, formatter, or language server is authorized.

## Open items not resolved by ratification

`OQ-008-001` through `OQ-008-009` remain open. `OQ-008-010` remains **resolved** as structured-only
canonical assumption and question records; ratification neither changes nor reopens that resolution.
`OQ-008-003` (approval-authority thresholds) is the
operationally significant one: required authority continues to resolve from an accepted approval-threshold
policy, and undeterminable authority remains `BLOCKED` rather than assumed. Semantic equivalence between a
preserved source fragment and a requirement statement remains a manual review obligation; deterministic
validation proves provenance, never equivalence.
