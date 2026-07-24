# MISSION-008 Proposed Decision Log

**Status:** Proposed. None of these decisions is accepted, ratified, certified, or implementation authority.

These records are separate from the frozen D-050 decision log.

| ID | Proposed decision | Status | Evidence |
|---|---|---|---|
| RCD-008-001 | Adopt the source-language-neutral requirements document and evidence bundle as the canonical boundary between authoring input and frozen PromptRig IR v0.1. | Proposed | `REQUIREMENTS_COMPILER_SPEC.md`; `REQUIREMENTS_EVIDENCE_MODEL.md` |
| RCD-008-002 | Adopt the authority order owner decision → user decision → accepted contract → source evidence → authorized default → deterministic derivation → model proposal → provider constraint → implementation convenience. | Proposed | `AUTHORITY_AND_DEFAULTS.md` |
| RCD-008-003 | Permit defaults only when visible, scoped, non-conflicting, attributable, and approved when consequential. | Proposed | `AUTHORITY_AND_DEFAULTS.md`; `SECURITY_PRIVACY_APPROVALS.md` |
| RCD-008-004 | Deterministic validation establishes structural and contract validity; semantic acceptance additionally requires a permitted authority basis and attributable source evidence. Model-assisted output remains proposal-only until separately accepted through an attributable decision record; no model call is part of MISSION-008. | Proposed | RC-070 through RC-074; model adversarial fixtures |
| RCD-008-005 | Adopt `SUCCESS`, `PARTIAL`, `BLOCKED`, `REFUSED`, and `INVALID_OUTPUT` as distinct terminal statuses for a validation attempt. | Proposed | RC-060 through RC-064; 41-case fixture set |
| RCD-008-006 | Adopt the separate, versioned `RQC-*` Requirements Compiler diagnostic namespace without modifying the frozen Compiler Core registry. | Proposed | `DIAGNOSTICS.md`; `requirements-diagnostic-registry.json` |
| RCD-008-007 | Represent security, privacy, and approvals as first-class requirements and require consequential uncertainty or missing authority to fail closed. | Proposed | `SECURITY_PRIVACY_APPROVALS.md`; adversarial fixtures |
| RCD-008-008 | Require every requirement to map to exact frozen IR v0.1 pointers or an explicit unresolved/prohibited/gap outcome, and every emitted IR leaf to trace to accepted meaning, authorized default, or permitted deterministic derivation. | Proposed | `TRACEABILITY.md`; mapping schema; evidence maps |
| RCD-008-009 | Recommend PRS disposition `DEFERRED` pending representative syntax, source-map, grammar, complexity, and value evidence; do not change ADR-001. | Proposed | `PRS_DISPOSITION.md`; `evidence/prs-evaluation-matrix.json` |
| RCD-008-010 | Carry IRG-008-001 and IRG-008-002 into separately authorized Roadmap Phase 5 planning without changing frozen IR v0.1. | Proposed | `evidence/unresolved-ir-gaps.json` |

## Decision effect

Owner approval would ratify the proposed requirements contract direction only. It would not implement a requirements compiler, authorize a PRS parser or grammar, accept an IR v0.2 shape, start MISSION-009 through MISSION-011, or authorize model calls, evaluation, repair, live execution, benchmark work, UI, hosted infrastructure, merge, release, or tags.
