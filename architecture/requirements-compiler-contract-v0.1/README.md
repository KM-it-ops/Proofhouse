# Requirements Compiler Contract and Evidence Model v0.1

**Status:** `RATIFIED DIRECTION` — `RCD-008-001` through `RCD-008-010` were approved by explicit owner decision on 2026-07-25, recorded in [OAR-002](../OWNER_ACCEPTANCE_RECORDS/OAR-002.md). This package is executable contract evidence; ratification accepts the **contract direction** only. It is **not** production-certified, not capability promotion, and not implementation authority, and it does not authorize merge, release, or tags. PRS remains `DEFERRED` and ADR-001 is unchanged. `OQ-008-001` through `OQ-008-009` remain open; `OQ-008-010` remains resolved as structured-only canonical assumption and question records.

**Exact baseline:** `feature/promptrig-framework` at `b12b8262449d1a04cb3802f17f5f44f9a84de5d4`.

## Purpose

This package defines a source-language-neutral, deterministic validation boundary between authoring input and evidence-bearing requirements that can be mapped honestly to frozen PromptRig IR v0.1. It specifies meaning, authority, defaults, evidence, diagnostics, statuses, and traceability without compiling ordinary language or changing IR.

The package is executable through draft JSON Schemas, evidence-first fixtures, a test-only semantic validator, and deterministic validation evidence. Green validation proves internal consistency of this proposal only.

## Scope

In scope:

- ordinary-language, Developer Mode-style, API, and file authoring envelopes;
- stable requirements and source evidence;
- authority, defaults, approvals, ambiguity, conflict, refusal, and blocked meaning;
- separate proposed Requirements Compiler diagnostics;
- requirement-to-IR and requirement-to-test evidence;
- proposed PRS disposition and owner decisions.

Out of scope:

- a production requirements compiler or natural-language interpreter;
- a model call, prompt-only compiler, or production PRS parser;
- evaluation, repair, runtime state, provider execution, UI, hosted infrastructure, benchmarks, or downstream products;
- changes to frozen PromptRig IR v0.1 or its frozen diagnostic registry;
- MISSION-009, MISSION-010, or MISSION-011 work.

## Package index

| File or directory | Role |
|---|---|
| [REQUIREMENTS_COMPILER_SPEC.md](REQUIREMENTS_COMPILER_SPEC.md) | Normative terms, lifecycle, statuses, transitions, determinism, and fail-closed rules |
| [AUTHORITY_AND_DEFAULTS.md](AUTHORITY_AND_DEFAULTS.md) | Authority precedence, override rules, defaults, and approvals |
| [REQUIREMENTS_EVIDENCE_MODEL.md](REQUIREMENTS_EVIDENCE_MODEL.md) | Required evidence records and acceptance distinctions |
| [SECURITY_PRIVACY_APPROVALS.md](SECURITY_PRIVACY_APPROVALS.md) | Security, privacy, permission, refusal, and human approval rules |
| [DIAGNOSTICS.md](DIAGNOSTICS.md) | Proposed `RQC-*` diagnostic namespace |
| [TRACEABILITY.md](TRACEABILITY.md) | Input-to-evidence-to-requirement-to-IR/gap/test chain |
| [PRS_DISPOSITION.md](PRS_DISPOSITION.md) | Evidence-based PRS disposition recommendation |
| [DECISION_LOG.md](DECISION_LOG.md) | MISSION-008 decisions — all ten `Accepted` per OAR-002 |
| [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) | Unresolved semantics and evidence thresholds |
| [OWNER_DECISION_REQUEST.md](OWNER_DECISION_REQUEST.md) | Exact owner choices and non-authorizations |
| `schemas/` | Eight Draft 2020-12 proposed schemas |
| `fixtures/cases.json` | 41 semantic-oracle cases. A **test-only semantic projection, not canonical requirements documents** |
| `fixtures/schema_instances.json` | 35 schema-conformance instances proving exact acceptance and rejection reasons |
| `fixtures/linked_artifact_sets.json` | 28 complete, cross-referenced artifact sets proving closure **and** semantic validity |
| `fixtures/ir_pointer_cases.json` | 11 frozen-IR pointer-validity cases |
| `evidence/` | Deterministic inventories, mappings, hashes, results, gaps, clause dispositions, and PRS matrix |
| `validate_contract.py` | Test-only package validator; not product runtime |

## Three independent validation layers

Deterministic validation reports three layers separately, each with its own counts. No layer's result is evidence for another:

1. **Schema-instance** (35) — individual records accepted, or rejected at the exact intended keyword and location.
2. **Semantic-oracle** (41) — terminal status and diagnostics for structured candidates. These cases are a compact test-only projection, **not** canonical requirements documents.
3. **Linked-artifact** (28) — complete schema-valid artifact sets whose references resolve, whose evidence bundle closes over every canonical record, and whose declared terminal status, reason codes, and diagnostics must reconcile **exactly** with the shared rule engine.

Layers 2 and 3 are evaluated by **one shared contract-rule engine** over a normalized rule context, reached through two adapters (compact fixture, canonical artifacts). There is no second rule implementation.

Canonical evaluation reads no authoring prose: `context_from_artifacts` consumes only canonical records plus `intent_input.contract_version`, so the terminal status of a canonical attempt is a function of its record set alone and a verifier holding only the records can recompute it. Owner/user authority conflict is therefore derived from structured conflict evidence — an unresolved `conflicts` record whose `authority_ranks` span `owner` and `user` — and never from how a caller formatted an input label. The compact corpus retains one `owner:`/`user:` prefix shorthand, confined to `context_from_fixture` and documented there as a noncanonical test projection; it cannot affect canonical validity.

A fourth corpus of 11 IR-pointer cases checks frozen-IR pointer classification against frozen IR v0.1 (`spec_version` `0.1.0`). Green validation proves internal consistency of this proposal only.

## Authority order

The controlling order is:

1. explicit owner decisions within their declared scope;
2. explicit user decisions that do not conflict with owner policy or accepted contracts;
3. accepted versioned contracts;
4. attributable source evidence;
5. explicitly authorized authoring-mode defaults;
6. deterministic derivations allowed by contract;
7. model-assisted suggestions;
8. provider constraints;
9. implementation convenience.

Lower sources never silently override higher sources. Conflict with a higher source is visible evidence and usually `BLOCKED` or `REFUSED`.

## Authoring surfaces

Simple Mode, Developer Mode, APIs, and files are replaceable producers of the same intent-input and evidence contracts. No surface owns canonical meaning. A future PRS language, if retained, must produce the same records with equal source-location and authority fidelity.

## Relationship to PromptRig IR

PromptRig IR remains the durable semantic center after accepted requirements. This package:

- maps accepted meaning to exact IR v0.1 JSON Pointers;
- preserves every unmappable requirement through a stable diagnostic and IR-gap record;
- prohibits unmapped IR leaves and silent requirement loss;
- does not edit or extend IR v0.1.

## Non-authorization

This package authorizes no production compiler, parser, model integration, IR lowering implementation, CLI/API feature, evaluation, repair, live execution, UI, hosted service, benchmark, release, tag, or later mission. Owner approval of this proposal would ratify contract direction only; implementation still requires separately authorized MISSION-010 and production certification requires MISSION-011.
