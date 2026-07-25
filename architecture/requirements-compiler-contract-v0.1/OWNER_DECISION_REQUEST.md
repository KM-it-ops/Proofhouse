# MISSION-008 Owner Decision Request

**Status:** **RESOLVED — all ten decisions approved.** The Project Owner approved `RCD-008-001` through
`RCD-008-010` individually on 2026-07-25 at head `ce4a3ac05bca4bab5b2574555ba69560ef733680`. The binding
record is [OAR-002](../OWNER_ACCEPTANCE_RECORDS/OAR-002.md); statuses are `Accepted` in
[DECISION_LOG.md](DECISION_LOG.md).

`RCD-008-009` was approved as `DEFERRED` — the deferral itself is the accepted outcome, so ADR-001 is
unchanged and PRS is not accepted contract syntax.

Ratification accepts the contract direction only. Every non-authorization below still stands, and merge,
release, capability promotion, and MISSION-009 onward remain separate explicit gates. `OQ-008-001` through
`OQ-008-010` remain open.

The recommendations below are retained as the record of what was requested and on what basis.

**Requested response format:** approve, reject, or modify each `RCD-008-*` decision separately.

## RCD-008-001 — Requirements and evidence model

**Recommendation:** Approve the source-language-neutral requirements document and evidence bundle as the canonical authoring-to-IR boundary.

**Alternatives:** Make raw authoring input canonical; make IR the first semantic record; require a different evidence envelope.

**Consequences:** Approval stabilizes identity, source, authority, acceptance, mapping, and validation evidence. Rejection leaves MISSION-009/010 without a trustworthy intent boundary.

**Expensive/irreversible aspects:** Accepted identity and evidence fields will become compatibility obligations for future consumers.

**Non-authorization:** No production compiler, parser, API, CLI, UI, model, or later mission is authorized.

## RCD-008-002 — Authority order

**Recommendation:** Approve the precedence in `AUTHORITY_AND_DEFAULTS.md`, with lower-ranked claims unable to weaken higher-ranked authority.

**Alternatives:** User always wins; accepted contract always wins; configurable precedence without a fixed floor.

**Consequences:** Approval makes owner/user conflicts and provider limitations visible rather than silently resolved.

**Expensive/irreversible aspects:** Precedence changes after adoption can reinterpret stored requirements and evidence.

**Non-authorization:** Approval does not resolve any specific future owner/user conflict or create runtime permissions.

## RCD-008-003 — Defaults

**Recommendation:** Approve visible, scoped, attributable, non-conflicting defaults; require explicit approval for consequential defaults.

**Alternatives:** Ban defaults; allow hidden implementation defaults; require approval for every default.

**Consequences:** Approval preserves usability without allowing invisible security, privacy, cost, retention, or destructive behavior.

**Expensive/irreversible aspects:** Default authority becomes part of replay and compatibility evidence.

**Non-authorization:** Approval does not approve any actual consequential default.

## RCD-008-004 — Deterministic/model-assisted boundary

**Recommendation:** Approve deterministic validation as authoritative for structural and contract validity; semantic acceptance additionally requires a permitted authority basis and attributable source evidence. Model output remains proposal-only until separately accepted through an attributable decision record.

**Alternatives:** Accept model output directly; prohibit model proposals entirely; allow model-selected authority.

**Consequences:** Approval permits future assistance without allowing nondeterministic output to self-ratify meaning.

**Expensive/irreversible aspects:** Model provenance and acceptance evidence become durable contract obligations.

**Non-authorization:** No model selection, prompt, call, integration, or production plain-language compiler is authorized.

## RCD-008-005 — Compile statuses

**Recommendation:** Approve `SUCCESS`, `PARTIAL`, `BLOCKED`, `REFUSED`, and `INVALID_OUTPUT` with RC-060 through RC-064 semantics.

**Alternatives:** Collapse non-success states; remove `PARTIAL`; use diagnostics without terminal status.

**Consequences:** Approval gives consumers stable distinctions between incomplete input, prohibited work, and invalid producer output.

**Expensive/irreversible aspects:** Status meanings become API and evidence compatibility commitments.

**Non-authorization:** Status approval does not implement compilation or authorize best-effort bypass.

## RCD-008-006 — Diagnostic namespace

**Recommendation:** Approve a separate versioned `RQC-*` namespace governed by `DIAGNOSTICS.md`.

**Alternatives:** Extend the frozen Compiler Core registry; use free-text errors; defer all requirements diagnostics.

**Consequences:** Approval avoids changing the frozen registry and makes requirements failures machine-stable.

**Expensive/irreversible aspects:** Published codes cannot be reused for new meaning.

**Non-authorization:** Proposed codes are not added to or accepted by the frozen registry and do not authorize production emission.

## RCD-008-007 — Security, privacy, and approvals

**Recommendation:** Approve first-class representation and fail-closed handling for missing consequential evidence, authority, and approvals.

**Alternatives:** Treat them as annotations; defer enforcement; rely on model judgment.

**Consequences:** Approval prevents authoring surfaces, models, providers, and implementations from weakening controlling policy.

**Expensive/irreversible aspects:** Approval and refusal evidence must remain replayable and auditable.

**Non-authorization:** No credential handling, live access, destructive operation, data processing, or runtime approval is authorized.

## RCD-008-008 — Requirement-to-IR traceability

**Recommendation:** Approve exact JSON Pointer mappings or explicit unresolved/prohibited/gap outcomes, with reverse traceability for every emitted IR leaf.

**Alternatives:** Document-level mappings; best-effort lowering; allow unmapped derived fields.

**Consequences:** Approval prevents silent disappearance and makes IR gaps honest.

**Expensive/irreversible aspects:** Mapping identities and pointers become evidence compatibility surfaces.

**Non-authorization:** Approval does not change or lower into frozen IR v0.1 and does not accept an IR v0.2 shape.

## RCD-008-009 — PRS disposition

**Recommendation:** Approve `DEFERRED`.

**Alternatives:** `CONTRACT_CANDIDATE`; `REJECTED`.

**Consequences:** Deferral preserves PRS as a candidate while preventing a one-example syntax proposal from owning semantics.

**Expensive/irreversible aspects:** A premature grammar freeze would create long-lived parser and source compatibility obligations; deferral does not.

**Non-authorization:** No PRS grammar, parser, formatter, language server, implementation, or ADR-001 status change is authorized.

## RCD-008-010 — IR v0.1 gaps

**Recommendation:** Carry IRG-008-001 and IRG-008-002 into separately authorized Phase 5 planning as blocked requirements evidence.

**Alternatives:** Reject the requirements; force them into existing fields; authorize a separate future change proposal.

**Consequences:** Approval preserves valid needs without corrupting frozen IR semantics.

**Expensive/irreversible aspects:** Any later IR change requires a versioned compatibility and migration decision; this proposal chooses no shape.

**Non-authorization:** Phase 5, IR v0.2, ADR-007 acceptance, MISSION-009 through MISSION-011, and downstream runtime reliance remain separately unauthorized.

## Collective effect and retained gates

All ten recommendations were approved, ratifying the contract direction only. The package still requires
separately authorized implementation and certification missions. Ratification does **not**:

- self-certify or promote the Requirements compiler capability;
- begin MISSION-009, MISSION-010, or MISSION-011;
- authorize production compilation, evaluation, repair, model calls, live execution, benchmarks, UI, hosted infrastructure, providers, credentials, or permissions;
- change PromptRig IR v0.1, the frozen diagnostic registry, generated contracts, frozen contracts, historical evidence, CI, packages, or tags;
- merge this PR or enable auto-merge.
