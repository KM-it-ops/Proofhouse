# Requirements Evidence Model

**Status:** Proposed MISSION-008 contract. Stable clauses use `EM-*`.

## Core records

| Record | Required evidence |
|---|---|
| Requirement | Stable ID, type, statement, priority, acceptance state, authority basis, source refs, acceptance criteria, consequential flag, approvals/default |
| Source | Stable ID, kind, SHA-256 digest when bytes exist, lifecycle, authority claim, URI, JSON Pointer, optional line/column |
| Derivation | Stable ID, rule/clause, input refs, output refs, deterministic validation ref |
| Model proposal | Stable ID, source refs, producer identity/version when known, input/output digest, proposed records, acceptance state |
| Validation | Stable ID, validator/contract version, schema hashes, artifact hashes, deterministic result, diagnostics |
| Assumption | Stable ID, statement, impact, source refs, acceptance state, consequential flag, approval refs when consequential |
| Conflict | Stable ID, claims, sources, authority ranks, affected requirements, resolution state |
| Question | Stable ID, text, affected requirements, required/optional impact, resolution state, resolution evidence when resolved |
| Approval | Stable ID, subject refs, authority, decision, machine-readable scope, non-empty evidence, immutable sequence/timestamp |
| Default | Stable ID, statement, authority, scope, consequential flag, approval state, affected refs, source refs, approval refs when consequential |
| IR mapping | Stable ID, requirement, outcome, exact target pointer or non-mapping reason, authority, validation, diagnostic/gap |
| Test mapping | Stable ID, requirement/clause, planned test/evidence ID, status |
| Diagnostic ref | Stable diagnostic ID/code and affected source/requirement refs |
| Terminal status | Compile status, sorted reason codes, attempt identity, prior-attempt ref, evidence bundle ref |

## Acceptance distinctions

- **EM-001:** `directly_stated` preserves exact attributable source meaning.
- **EM-002:** `deterministically_derived` identifies the contract rule and all input/output refs.
- **EM-003:** `explicitly_defaulted` identifies a visible authorized default record.
- **EM-004:** `model_suggested` is unaccepted regardless of confidence.
- **EM-005:** `owner_decision` and `user_decision` are authority-basis values identifying who decided, not approval evidence; when the underlying decision is consequential, the record must additionally carry an immutable approval record via `approval_refs` (`APR-*`). Approval is never expressed as an authority-basis value.
- **EM-006:** `disputed`, `unresolved`, `unsupported`, `refused`, and `invalid` remain visible and cannot be collapsed into accepted.
- **EM-007:** Confidence may be recorded as descriptive proposal metadata but never changes authority, acceptance, status, or priority.

## Identity and immutability

- **EM-010:** Stable IDs are unique per record namespace and case-sensitive.
- **EM-011:** Source location is preserved byte-for-byte in evidence and never rewritten to a parser convenience path.
- **EM-012:** Source replacement links old and new source IDs; old evidence is not deleted.
- **EM-013:** Every validation attempt is immutable and content-addressable by canonical JSON SHA-256.
- **EM-014:** Evidence references are closed over the bundle or explicitly external with URI and digest; dangling refs are invalid.

## Evidence bundle

- **EM-020:** The evidence bundle closes over sources, derivations, proposals, validations, assumptions, conflicts, questions, approvals, defaults, mappings, tests, diagnostics, status evidence, and gaps.
- **EM-021:** Lists use deterministic ID ordering and preserve source order separately when semantically relevant.
- **EM-022:** The bundle distinguishes generated evidence from accepted source evidence.
- **EM-023:** The bundle includes contract version and exact frozen IR target version. The exact value is `0.1.0`, equal to frozen PromptRig IR v0.1's `spec_version` constant; deterministic validation reads that constant and compares it against the bundle rather than trusting the declared string.
- **EM-025:** The bundle names the compile-result attempt it supports (`compile_result_ref`), and that result names the bundle (`evidence_bundle_ref`). Same-attempt membership is proved by this explicit reference chain, never by records merely appearing together. Attempt-bound artifacts are the intent input, requirements document, mappings, diagnostics, and compile result. Sources, policies, approvals, and external evidence are **reusable authority evidence**: they need not be produced by the citing attempt, but must be immutable, content-addressed, and referenced exactly.
- **EM-026:** Accepted-contract authority requires the exact contract identity, version, and content digest carried on a current source of kind `contract`. Source kind alone never establishes accepted-contract authority.
- **EM-027:** The canonical hashing domain is exact: UTF-8 encoding; JSON object keys sorted lexicographically; array order preserved as semantic order; compact separators; exactly one trailing newline; SHA-256 over those bytes. `artifact_hashes` keys are limited to the attempt-bound artifacts, and the bundle never contains a hash of itself, so the digest domain is acyclic. A reusable record's `content_digest` is taken over the record with its own `content_digest` removed.
- **EM-024:** The bundle never claims production compiler certification.

## Requirement and IR completeness

- **EM-030:** Every requirement appears in mapping evidence with at least one mapping or explicit non-mapping outcome.
- **EM-031:** Every direct/derived/default mapping names a valid accepted requirement and exact IR pointer.
- **EM-032:** Every `no_ir_representation` mapping carries a stable diagnostic and gap record.
- **EM-033:** Every prohibited mapping carries the controlling policy evidence.
- **EM-034:** Every unresolved mapping identifies the question/conflict/approval that blocks it.
- **EM-035:** Every emitted IR leaf is covered by accepted meaning; subtree shortcuts are prohibited unless every leaf is enumerated or a justified closed schema boundary is referenced.

## Test and validation evidence

- **EM-040:** Clause-to-schema, clause-to-fixture, and field-justification mappings are machine-readable.
- **EM-041:** Validation result includes every schema hash and fixture outcome.
- **EM-042:** Repeated validation evidence is byte-identical.
- **EM-043:** Validation records explicitly state no network and no credential access.
- **EM-044:** Frozen IR and frozen diagnostic registry hashes are recorded and checked without editing those files.
