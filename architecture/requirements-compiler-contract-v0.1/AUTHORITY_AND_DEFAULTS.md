# Authority and Defaults

**Status:** Proposed MISSION-008 contract. Stable clauses use the `AD-*` namespace.

## Precedence

| Rank | Authority source | Permitted role |
|---:|---|---|
| 1 | Owner decision | Governs its declared architecture, safety, release, or scope boundary |
| 2 | User decision | Governs requested product meaning within owner policy and accepted contracts |
| 3 | Accepted contract | Defines versioned invariants and valid behavior |
| 4 | Source evidence | Supports claims; does not outrank explicit governing decisions |
| 5 | Authorized authoring default | Supplies visible non-conflicting meaning within declared scope |
| 6 | Deterministic derivation | Derives only contract-permitted consequences |
| 7 | Model-assisted suggestion | Proposes unaccepted meaning |
| 8 | Provider constraint | Constrains deployability; does not own canonical meaning |
| 9 | Implementation convenience | Has no semantic authority |

- **AD-001:** Lower-ranked input cannot silently override, erase, reinterpret, or weaken higher-ranked authority.
- **AD-002:** Equal-rank disagreement is an explicit conflict unless a recorded tie-break rule applies.
- **AD-003:** Owner/user conflicts remain visible; owner policy controls execution while the user claim remains preserved as disputed evidence.
- **AD-004:** Accepted contracts control artifact validity; owner approval is required to revise their semantic boundary.
- **AD-005:** Provider constraints may cause blocked/unsupported evidence but never mutate a canonical requirement.

## Override behavior

- **AD-010:** An override identifies the superseded record, new authority, scope, reason, and evidence.
- **AD-011:** Overrides are append-only evidence; rejected and superseded alternatives remain addressable.
- **AD-012:** A user may override a prior user choice when owner policy and accepted contracts permit it.
- **AD-013:** A model, provider, parser, UI, or implementation cannot issue an override.
- **AD-014:** Unknown or ambiguous override scope is `BLOCKED`.

## Defaults

- **AD-020:** A default record has stable ID, statement, authority reference, scope, affected requirement IDs, consequential flag, approval state, and source references.
- **AD-021:** Defaults are never applied invisibly.
- **AD-022:** Consequential defaults include security, privacy, credential, network, destructive action, retention, cost, legal, publication, and external-side-effect choices.
- **AD-023:** Consequential defaults require explicit owner approval when policy/architecture is affected and explicit user approval when user intent or side effects are affected.
- **AD-024:** Non-consequential defaults may be authorized by an accepted contract only within exact declared scope.
- **AD-025:** An unapproved or convenience-sourced default is prohibited and emits `RQC-DFT-0001`.
- **AD-026:** A default cannot convert missing required meaning into apparent acceptance.
- **AD-027:** Default application is traceable to each IR leaf it influences.

## Deterministic derivation

- **AD-030:** A derivation is permitted only by a stable contract clause and identifies inputs, rule ID, outputs, and validation evidence.
- **AD-031:** Derivation cannot introduce a new objective, permission, provider preference, security posture, or consequential choice.
- **AD-032:** “No network” may deterministically imply an offline constraint; it may not imply retention, provider, or approval policy.
- **AD-033:** When more than one valid derivation exists and the choice is material, the result is ambiguous and requires a decision.

## Model-assisted suggestions

- **AD-040:** Model output has proposal authority only.
- **AD-041:** Model output cannot mark itself accepted, user approved, or owner approved.
- **AD-042:** Model output cannot approve defaults or resolve authority conflicts.
- **AD-043:** Suggested source links must be validated against preserved source evidence.
- **AD-044:** Suggested security/privacy weakening is rejected and fails closed.

## Approval thresholds

| Decision | Minimum approval |
|---|---|
| Architecture/contract semantic change | Owner |
| Security/privacy policy or prohibited-operation exception | Owner and affected user where applicable |
| Credential/network/destructive side effect | Explicit governing policy plus affected user approval |
| Consequential default | Owner or user according to governing scope; never model/provider/parser |
| Non-consequential presentation default | Accepted contract or explicit user choice |

- **AD-050:** Approval records are exact-scope; silence and UI state are not approval.
- **AD-051:** Approval expiration, revocation, or supersedence is preserved as evidence.
- **AD-052:** Missing approval for required consequential meaning makes the result `BLOCKED`; policy prohibition makes it `REFUSED`.
