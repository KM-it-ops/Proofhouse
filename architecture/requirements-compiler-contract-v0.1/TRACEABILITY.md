# Requirements Compiler Traceability

**Status:** Proposed MISSION-008 normative traceability contract.

## Canonical chain

```text
authoring input
-> source evidence
-> requirement identity
-> authority/default decision
-> diagnostic or acceptance
-> IR field/leaf or explicit gap
-> planned test/evidence
```

- **TR-001:** Every chain node has a stable identity and every edge is machine-readable.
- **TR-002:** Every accepted requirement references valid source evidence.
- **TR-003:** Every authority/default decision identifies its controlling clause and evidence.
- **TR-004:** Every requirement has at least one mapping or explicit non-mapping outcome.
- **TR-005:** Every emitted IR leaf maps to accepted meaning, a visible authorized default, or a permitted deterministic derivation.
- **TR-006:** No source-language field may create an untraceable IR subtree.
- **TR-007:** No requirement may disappear silently.
- **TR-008:** Every unsupported required mapping has diagnostic `RQC-IRG-0001`, a gap record, and Phase 5 planning evidence.
- **TR-009:** Every requirement and normative clause maps to planned tests/evidence.

## Mapping classes

| Mapping class | Required evidence | IR emission |
|---|---|---|
| `direct` | Accepted requirement, source refs, exact target JSON Pointer, validation refs | Permitted |
| `deterministic_derivation` | Accepted input requirements, clause/rule ID, derivation record, exact target pointer | Permitted |
| `authorized_default` | Accepted default record and approval/contract authority, exact target pointer | Permitted |
| `no_ir_representation` | Preserved requirement, `RQC-IRG-0001`, stable gap record, Phase 5 link | Prohibited |
| `prohibited` | Preserved requirement, policy/authority evidence, refusal/security diagnostic | Prohibited |
| `unresolved` | Preserved requirement and blocking question/conflict/approval evidence | Prohibited |

## IR pointer rules

- **TR-010:** Target pointers use RFC 6901 and identify exact leaves in frozen IR v0.1.
- **TR-011:** Array mappings identify stable semantic items and their canonical pointer for the validated artifact.
- **TR-012:** A pointer is invalid if the target leaf is not permitted by the frozen IR schema.
- **TR-013:** Mapping validation does not produce IR; it validates evidence supplied by a future producing stage.

## Completeness algorithm

For one validation attempt:

1. collect unique requirement IDs;
2. collect unique mapping IDs and requirement references;
3. reject dangling requirement, source, diagnostic, approval, default, validation, or gap references;
4. require each required accepted requirement to have one or more emitting mappings;
5. require each unsupported/prohibited/unresolved requirement to have an explicit non-emitting mapping;
6. require each emitting mapping to have source and authority evidence;
7. sort mappings by ID and produce deterministic completeness evidence.

## Evidence-first fixture traceability

| Authoring mode | Required fixture themes |
|---|---|
| Simple | clear, missing, contradictory, approval, security/privacy, IR gap, hostile, semantic emptiness |
| Developer | explicit config, duplicate ID, priority conflict, assumptions/questions, unsupported capability, fail closed, defaults, IR gap |
| API | version, unknown field/version, invalid location, authority conflict, broken evidence, ordering, refusal, model rejection |
| File | multi-source, duplicate/missing/stale/conflicting sources, stable locations, unsupported imports, adversarial content |

The machine-readable clause-to-fixture and clause-to-schema matrices under `evidence/` are authoritative evidence for this proposed package. They do not certify a production compiler.

## Three independent validation layers

Deterministic validation reports three separate layers with their own counts and results. No layer's result is evidence for another:

| Layer | Corpus | What it proves |
|---|---|---|
| Schema-instance | `fixtures/schema_instances.json` | Individual records are accepted, or rejected by the exact schema keyword and location intended |
| Semantic-oracle | `fixtures/cases.json` | Terminal status and diagnostics for structured candidates. These 41 cases are a **test-only semantic projection, not canonical requirements documents** |
| Linked-artifact | `fixtures/linked_artifact_sets.json` | Complete, schema-valid, cross-referenced artifact sets close over themselves with unambiguous document/result/bundle linkage |

- **TR-014:** Every normative clause carries exactly one explicit disposition in `evidence/clause-dispositions.json`: `schema_enforced`, `semantic_fixture_enforced`, `linked_artifact_enforced`, `manual_review`, `governance_only`, `future_deferred`, or `non_executable_definition`.
- **TR-015:** Deterministic validation proves clause-identifier existence, disposition completeness and uniqueness, and required-field coverage across all eight schemas including nested `$defs` and conditionally required fields. It does **not** prove that a natural-language clause citation is semantically apt. Clauses whose satisfaction is a human judgement carry `manual_review` with a recorded rationale, and that judgement is never reported as automated proof.
