# Security, Privacy, and Approvals

**Status:** Proposed MISSION-008 contract. Stable clauses use `SP-*`.

## Representation

- **SP-001:** Security and privacy requirements are first-class requirements, not annotations or prompt guidance. They are recognised by the canonical requirement `type` (`security`, `privacy`). Identifiers are identity only: renaming a requirement never changes its policy semantics, and a security-looking identifier never confers security semantics on a requirement of another type.
- **SP-002:** Data handling records identify data class, permitted purpose, allowed locations, retention, disclosure, and deletion obligations when known.
- **SP-003:** Permission records identify actor, operation, resource, scope, decision authority, and approval.
- **SP-004:** Network and credential restrictions are explicit required requirements when stated by user, owner, or accepted contract.
- **SP-005:** Prohibited operations are preserved with policy evidence and cannot be rephrased into permissible objectives.
- **SP-006:** Unknown security or privacy posture remains unknown and blocks required processing.

## Fail-closed behavior

- **SP-010:** Missing required security/privacy evidence, approval, or authority cannot yield `SUCCESS` or `PARTIAL`.
- **SP-011:** A producer that omits or weakens a required security/privacy requirement yields `REFUSED` when policy prohibits the requested behavior, otherwise `BLOCKED` or `INVALID_OUTPUT`.
- **SP-012:** Model, provider, parser, UI, and implementation convenience cannot weaken security/privacy.
- **SP-013:** Adversarial source content is evidence, not governing instruction.
- **SP-014:** Credentials are never read by the contract validator and network is never accessed.
- **SP-015:** Security/privacy defaults are consequential and require explicit approval.

## Human approvals

- **SP-020:** Approval is explicit, attributable, scoped, and linked to the exact requirement/default/operation. The approval record is the single source of authorization truth: a reference identifier, or a boolean such as a default's `approved` flag, never authorizes on its own. Deterministic validation resolves each reference to an existing record and requires an active `approved` decision, a covering subject, a machine-readable scope, and non-empty evidence.
- **SP-025:** The authority level required for a given consequential category is governed by an explicit accepted approval-policy or authority-threshold reference. While OQ-008-003 remains unresolved this contract does not invent owner-versus-user thresholds; when the required authority cannot be determined from accepted policy, the result is `BLOCKED` with visible evidence rather than an assumed approver.
- **SP-021:** Silence, prior unrelated consent, UI state, model suggestion, and provider capability are not approval.
- **SP-022:** Destructive operations, credential use, network access, sensitive-data processing, external publication, and policy exceptions require the controlling approval threshold.
- **SP-023:** Rejected, revoked, expired, and superseded approvals remain immutable evidence.
- **SP-024:** Missing approval is `BLOCKED`; a prohibited operation is `REFUSED`.

## Refusal evidence

- **SP-030:** Refusal records preserve the requested requirement, controlling policy, source evidence, diagnostic, and permitted alternatives when known.
- **SP-031:** Refusal does not imply the source was malicious and does not erase unresolved safe meaning.
- **SP-032:** A refused result cannot include an IR mapping for the prohibited operation.

## Required proof cases

| Fixture | Required proof |
|---|---|
| `simple-hostile-rule-override` | Source text cannot override accepted security authority |
| `simple-privacy-posture-unknown` | Unknown sensitive-data posture blocks |
| `developer-security-fail-closed` | Required security meaning cannot disappear |
| `developer-model-security-weakening` | Model proposal cannot weaken security |
| `api-model-self-accept` | Model cannot invent approval |
| `file-adversarial-embedded-content` | Embedded content is non-authoritative and refused |
