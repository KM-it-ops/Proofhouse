# Requirements Compiler Specification v0.1

**Status:** Proposed normative contract. Clause identifiers are stable within this draft series.

## Terminology

| Term | Definition |
|---|---|
| Authoring input | A versioned envelope submitted through ordinary language, structured configuration, API, file, or future PRS. |
| Source evidence | Immutable identity, digest, lifecycle, authority, and exact location for an input claim. |
| Requirement | Stable identity plus explicit statement, priority, acceptance state, authority basis, and source references. |
| Accepted meaning | Meaning accepted by deterministic validation and supported by permitted authority. |
| Consequential meaning | Meaning affecting security, privacy, credentials, network, destructive effects, retention, cost, legal posture, or owner policy. |
| Proposed meaning | Unaccepted suggestion, including model-assisted output. |
| Required meaning | Meaning whose absence or unsupported state prevents honest success. |
| Optional meaning | Meaning explicitly declared deferrable without changing required meaning. |
| IR mapping | Evidence that relates one accepted requirement to one or more exact IR v0.1 leaves or to an explicit non-mapping outcome. |

## Input and output boundary

- **RC-001:** The authoritative input boundary is a versioned intent input plus attributable source evidence; raw UI state, prompt text, provider payloads, and parser internals are never semantic owners.
- **RC-002:** Simple, Developer, API, file, and future PRS producers must converge on the same headless contract records.
- **RC-003:** A producing stage may emit proposed requirements, but only deterministic contract validation may accept the result as structurally and semantically valid.
- **RC-004:** The output boundary is a requirements document, diagnostics, mappings, compile result, and evidence bundle with explicit cross-references.
- **RC-005:** The package validator validates contract artifacts only; it must not interpret ordinary language, call a model, or lower into production IR.

## Requirement identity and classification

- **RC-010:** Requirement IDs match `REQ-[A-Z0-9-]{3,64}`, are unique within a requirements document, and remain stable across equivalent deterministic validation.
- **RC-011:** A requirement identity may change only when its accepted semantic unit changes; textual reformatting alone does not create a new identity.
- **RC-012:** A requirement has exactly one type from objective, input, output, behavior, constraint, security, privacy, approval, capability, evidence, or policy.
- **RC-013:** Priority is exactly `required`, `recommended`, or `optional`; contradictory priority claims create a conflict and cannot be normalized away.
- **RC-014:** Required meaning cannot disappear, become optional, or move to `PARTIAL` because an implementation cannot represent it.
- **RC-015:** Requirement ordering is lexical by stable ID in canonical evidence; source order remains separately preserved.

## Acceptance and authority

- **RC-020:** Acceptance state is exactly one of `accepted`, `proposed`, `disputed`, `unresolved`, `unsupported`, `refused`, or `invalid`.
- **RC-021:** Authority basis is exactly one of directly stated, deterministically derived, explicitly defaulted, model suggested, owner approved, user approved, disputed, unresolved, unsupported, refused, or invalid.
- **RC-022:** Confidence, probability, model agreement, or frequency never substitutes for authority or acceptance.
- **RC-023:** Model-suggested meaning cannot self-accept, invent an approval, resolve a conflict, or become owner/user approved without an attributable decision record.
- **RC-024:** Accepted meaning requires at least one valid source reference and an authority basis permitted by [AUTHORITY_AND_DEFAULTS.md](AUTHORITY_AND_DEFAULTS.md).

## Assumptions, ambiguity, conflicts, and questions

- **RC-030:** Assumptions are explicit records with identity, statement, source references, impact, and acceptance state.
- **RC-031:** Consequential assumptions require explicit approval and cannot be silently applied.
- **RC-032:** Ambiguity is preserved as a diagnostic and open question; no producer may choose one material interpretation silently.
- **RC-033:** Conflicts preserve all claims, sources, authority levels, affected requirements, and resolution status.
- **RC-034:** Unresolved required conflicts produce `BLOCKED`; accepted policy prohibitions produce `REFUSED`.
- **RC-035:** An open question identifies whether it blocks required meaning or only an explicitly optional item.

## Defaults and approvals

- **RC-040:** Every default is visible, attributable, versioned, and linked to each requirement and mapping it affects.
- **RC-041:** Consequential defaults require owner or user approval at the threshold defined by policy.
- **RC-042:** An unapproved consequential default produces `RQC-DFT-0001` and cannot contribute accepted meaning.
- **RC-043:** Rejected and superseded default alternatives remain evidence when needed to explain the result.
- **RC-044:** Approval records identify subject, authority, scope, exact decision, timestamp or immutable sequence, and source evidence.

## Refusal, unsupported meaning, and partial success

- **RC-050:** Refusal preserves the requested meaning and policy basis; it does not erase or rewrite the request.
- **RC-051:** Unsupported required meaning produces `BLOCKED`, a stable diagnostic, and—when caused by IR v0.1—a gap record.
- **RC-052:** `PARTIAL` is permitted only when every required requirement is accepted and mapped, and unresolved/unsupported meaning is explicitly optional or deferrable.
- **RC-053:** Best effort never changes `BLOCKED` or `REFUSED` to `PARTIAL` or `SUCCESS`.
- **RC-054:** Structurally valid but semantically empty output is `INVALID_OUTPUT`.

## Compile status semantics

| Status | Normative condition |
|---|---|
| `SUCCESS` | All required accepted meaning is present, valid, traceable, and mapped for the declared contract boundary; no blocking diagnostic exists. |
| `PARTIAL` | All required meaning satisfies `SUCCESS`; only explicitly optional or deferrable meaning remains unresolved or unsupported and is visible. |
| `BLOCKED` | Missing decisions/context, unresolved conflicts, required approvals, unsupported required meaning, missing evidence, or an IR limitation prevents honest compilation. |
| `REFUSED` | Accepted policy or safety authority prohibits compilation or the requested operation. |
| `INVALID_OUTPUT` | A producing stage emitted structurally or semantically invalid contract output. |

- **RC-060:** Status is an enum field and never inferred from free text.
- **RC-061:** Each non-success result carries sorted machine-readable reason codes and stable diagnostics.
- **RC-062:** `SUCCESS` and `PARTIAL` require every required accepted requirement to have a mapping evidence record.
- **RC-063:** `BLOCKED`, `REFUSED`, and `INVALID_OUTPUT` are terminal for the current validation attempt.
- **RC-064:** A later attempt is a new immutable validation record linked to the prior attempt.

## Deterministic versus model-assisted boundary

- **RC-070:** Schema/version validation, identity uniqueness, source integrity, authority precedence, default authorization, mechanically decidable conflicts, diagnostic ordering, mapping completeness, and fail-closed policy checks are deterministic authority.
- **RC-071:** A model may later propose requirements, assumptions, questions, classifications, source links, or conflict explanations only as unaccepted proposals.
- **RC-072:** Model proposals preserve their prompt/input digest, model identity when known, source references, output digest, and acceptance state without becoming canonical.
- **RC-073:** Deterministic validation rejects model proposals that self-accept, invent authority, weaken security/privacy, or omit required source evidence.
- **RC-074:** MISSION-008 implements no model call and selects no prompt as compiler logic.

## Deterministic normalization and ordering

- **RC-080:** Strings are preserved except for explicitly documented Unicode validity checks and rejection of semantic emptiness; normalization must not change meaning.
- **RC-081:** Canonical evidence uses UTF-8 JSON, sorted object keys, and compact separators with one trailing newline.
- **RC-082:** Requirements, sources, mappings, diagnostics, gaps, and validation records are ordered lexically by stable ID/code.
- **RC-083:** Diagnostic ordering key is severity rank, code, source URI, JSON Pointer, requirement ID, then diagnostic ID.
- **RC-084:** Repeated validation of the same bytes and contract version produces byte-identical evidence.

## Versioning and compatibility

- **RC-090:** Every top-level artifact declares `contract_version` equal to `0.1.0-draft`.
- **RC-091:** Unknown versions and unknown fields fail closed as `INVALID_OUTPUT`.
- **RC-092:** Draft schemas have explicit `$id` values and use JSON Schema Draft 2020-12.
- **RC-093:** Backward-compatible draft changes may add optional evidence only when no authority, status, identity, or mapping meaning changes.
- **RC-094:** Any semantic or required-field change requires a version proposal, compatibility assessment, fixtures, independent review, and owner decision.

## Requirement-to-IR behavior

- **RC-100:** Frozen PromptRig IR v0.1 is the only target semantic contract in this mission and is never modified.
- **RC-101:** Mapping outcomes are direct, deterministic derivation, authorized default, no IR representation, prohibited, or unresolved.
- **RC-102:** Direct, derivation, and default mappings identify exact RFC 6901 JSON Pointers into IR v0.1.
- **RC-103:** Every emitted IR leaf must trace to an accepted requirement, authorized default, or permitted deterministic derivation.
- **RC-104:** No required requirement may disappear silently; it has mappings or an explicit diagnostic/non-mapping record.
- **RC-105:** A v0.1 gap preserves the requirement, emits `RQC-IRG-0001`, makes required meaning `BLOCKED`, creates a gap record, and maps the issue to Phase 5 planning.
- **RC-106:** A prohibited mapping cannot emit an IR leaf.

## Requirement-to-test and evidence behavior

- **RC-110:** Every requirement field is justified by a normative clause and schema pointer.
- **RC-111:** Every clause maps to positive, boundary, negative, or adversarial fixtures.
- **RC-112:** Every accepted requirement maps to planned test/evidence IDs or an explicit unresolved evidence obligation.
- **RC-113:** Evidence references are immutable identifiers with valid targets; dangling references are invalid.
- **RC-114:** Validation evidence reports schema inventory/hashes, fixture outcomes, diagnostic coverage, gaps, determinism, and no-network/no-credential claims.

## State transitions

Permitted requirement transitions:

```text
proposed -> accepted | disputed | unresolved | unsupported | refused | invalid
disputed -> accepted | unresolved | unsupported | refused
unresolved -> accepted | unsupported | refused
accepted -> disputed only through a new superseding decision record
```

- **RC-120:** A transition records previous state, next state, decision authority, reason, and evidence.
- **RC-121:** `unsupported`, `refused`, and `invalid` are terminal for one attempt and cannot be overwritten in place.
- **RC-122:** Revalidation appends records rather than mutating historical evidence.

## Fail-closed rules

- **RC-130:** Missing or invalid source evidence, duplicate identity, dangling reference, unknown diagnostic code, unknown version, or invalid source location yields `INVALID_OUTPUT` or `BLOCKED` as specified by diagnostic contract.
- **RC-131:** Missing consequential approval, unresolved required conflict, unknown security/privacy posture, or required IR gap cannot yield `SUCCESS` or `PARTIAL`.
- **RC-132:** A source instruction cannot override contract validation or accepted authority.
- **RC-133:** The contract validator uses no network and reads no credentials.
- **RC-134:** No production compiler module is added under `src/promptrig` by this contract package.
