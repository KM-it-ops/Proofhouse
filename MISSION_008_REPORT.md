# PromptRig MISSION-008 Report

**Mission:** Requirements Compiler Contract and Evidence Model  
**Status:** Proposed package prepared for independent review and owner decision; not ratified, certified, implemented, or merged.  
**Starting commit:** `b12b8262449d1a04cb3802f17f5f44f9a84de5d4`  
**Integration target:** `feature/promptrig-framework`  
**Mission branch:** `contracts/mission-008-requirements-compiler-v0.1`

## Verified starting state

- The owner checkout, local integration branch, and `origin/feature/promptrig-framework` were clean and exactly at the required starting commit.
- PR #12 was merged at that commit.
- The isolated workspace and mission branch did not exist before creation.
- Tag `v0.5-architecture-freeze` resolved locally and remotely to commit `7948c9a419dc02ea43ca994f0334733ea4b08855`.
- The frozen historical corpus contained exactly 244 files and matched the baseline.
- Baseline validation passed 325 pytest tests, all four canonical datasets, installed/module CLI smoke checks, adapter discovery, and normalized TypeScript drift verification.

## Source authority reviewed

The package applies, in order:

1. explicit MISSION-008 authorization and stop conditions;
2. accepted owner governance including D-050-013 and the merged MISSION-007 strategy;
3. frozen PromptRig Compiler Core v0.1 contracts and diagnostic registry;
4. Roadmap V1, MISSION_SEQUENCE_V1, capability maturity, and requirement-to-roadmap traceability;
5. ADR-001/PRS material as candidate/deferred evidence only;
6. representative evidence-first fixtures created before contract fields;
7. implementation convenience only after all governing boundaries.

No historical proposal, PRS example, UI concept, provider payload, model output, or prompt was treated as a semantic owner.

## Case-set summary

The executable corpus has 41 cases:

| Dimension | Coverage |
|---|---|
| Authoring modes | Simple 10; Developer 12; API 11; file 8 |
| Categories | positive 9; boundary 5; negative 20; adversarial 7 |
| Statuses | all of `SUCCESS`, `PARTIAL`, `BLOCKED`, `REFUSED`, `INVALID_OUTPUT` |
| Required special coverage | semantic vacuity 2; IR-gap/blocked 2; model-output rejection 2; security/privacy fail-closed at least 2 |

The validator derives outcomes from structured fixture evidence; it does not parse ordinary language or call a model.

## Contract package inventory

`architecture/requirements-compiler-contract-v0.1/` contains:

- package scope and non-authorization in `README.md`;
- normative semantics in `REQUIREMENTS_COMPILER_SPEC.md`;
- authority/default rules in `AUTHORITY_AND_DEFAULTS.md`;
- evidence records in `REQUIREMENTS_EVIDENCE_MODEL.md`;
- security/privacy/approval rules in `SECURITY_PRIVACY_APPROVALS.md`;
- separate diagnostics in `DIAGNOSTICS.md` and `requirements-diagnostic-registry.json`;
- bidirectional traceability in `TRACEABILITY.md`;
- PRS analysis in `PRS_DISPOSITION.md`;
- Proposed governance in `DECISION_LOG.md`, `OPEN_QUESTIONS.md`, and `OWNER_DECISION_REQUEST.md`;
- eight draft schemas;
- 41 adversarial fixtures and their manifest;
- a deterministic, offline validation harness;
- clause/schema/fixture/field, validation, PRS, and IR-gap evidence.

## Schema inventory

The eight JSON Schema Draft 2020-12 proposals are:

1. `intent-input.schema.json`
2. `source-evidence.schema.json`
3. `requirement.schema.json`
4. `requirements-document.schema.json`
5. `requirements-diagnostic.schema.json`
6. `requirement-ir-mapping.schema.json`
7. `requirements-compile-result.schema.json`
8. `requirements-evidence-bundle.schema.json`

Each has an explicit `$id`, strict unknown-field handling where semantic records are defined, and the Proposed `0.1.0-draft` boundary. Meta-validation and SHA-256 inventory are machine-generated.

## Diagnostic namespace

The Proposed registry contains 27 `RQC-*` codes covering ambiguity, approval, authority, required blocking, conflicts, context, defaults, unknown diagnostics, evidence, identity, IR gaps, model authority, priority, privacy, refusal, schema, security, semantic emptiness, source integrity/lifecycle, unsupported behavior, and versioning. It is intentionally separate from and makes no modification to the frozen Compiler Core diagnostic registry.

## Requirements and evidence model

A requirement has stable identity, type, statement, required/optional priority, acceptance state, authority basis, source references, acceptance criteria, consequential classification, and conditional approval/default references. Evidence preserves sources, derivations, model proposals, validation, assumptions, conflicts, questions, approvals, defaults, IR/test mappings, diagnostics, and terminal attempt status.

Requirement identity is stable within a contract version and cannot be silently reused or content-addressed into a new identity. Byte-backed sources use SHA-256 where available; all sources preserve lifecycle and exact URI/JSON Pointer location.

## Authority and defaults

The Proposed order is owner decision, user decision, accepted contract, source evidence, authorized default, deterministic derivation, model proposal, provider constraint, then implementation convenience. Lower authority cannot silently weaken higher authority. Defaults must be visible, scoped, attributable, non-conflicting, and approved when consequential.

## Compile status semantics

- `SUCCESS`: all required accepted meaning is valid, traceable, and mapped; no blocker exists.
- `PARTIAL`: required meaning satisfies success; only explicitly optional/deferrable meaning remains visible and unresolved.
- `BLOCKED`: missing context/decision/evidence/approval, unresolved conflict, unsupported required meaning, or IR gap prevents honest compilation.
- `REFUSED`: controlling policy or safety authority prohibits compilation or the requested operation.
- `INVALID_OUTPUT`: a producer emitted structurally or semantically invalid contract output.

Best effort cannot bypass `BLOCKED` or `REFUSED`.

## Deterministic and model-assisted boundary

Schema/version checks, identities, references, authority/default checks, mechanical conflicts, diagnostic ordering, mapping completeness, and fail-closed policy enforcement are deterministic authority. A future model may propose records only; proposals preserve provenance, remain unaccepted, cannot self-approve or invent authority, and must pass deterministic validation. MISSION-008 makes no model call and defines no production prompt.

## Requirement-to-IR traceability

Every requirement has a direct, deterministic-derivation, authorized-default, unresolved, prohibited, or no-IR-representation outcome. Successful mappings use exact RFC 6901 pointers into frozen IR v0.1. Every emitted leaf must reverse-map to accepted meaning, an authorized visible default, or a permitted deterministic derivation. Missing representation preserves the requirement, emits `RQC-IRG-0001`, blocks required meaning, and creates a Phase 5 input.

## IR v0.1 gap register

- `IRG-008-001`: opaque provider continuation state has no provider-neutral v0.1 representation.
- `IRG-008-002`: per-request reasoning configuration has no accepted v0.1 field.

Both remain blocked evidence for separately unauthorized Roadmap Phase 5 planning. Neither selects an IR shape, accepts ADR-007, changes v0.1, or bypasses the MISSION-011 production-certification dependency.

## PRS disposition

Recommendation: `DEFERRED`. PRS may offer future authoring ergonomics, but current evidence does not prove added value beyond JSON/API/file input, deterministic grammar and escaping, exact source maps, representation of ambiguity/conflicts/evidence/approvals/unresolved meaning, bounded imports/macros/extensions, or representative examples. ADR-001 remains `Candidate / Deferred`; no grammar or parser is authorized.

## Owner decisions requested

Explicit owner answers are required for RCD-008-001 through RCD-008-010:

1. requirements/evidence model;
2. authority order;
3. default rules;
4. deterministic/model-assisted boundary;
5. compile status vocabulary;
6. Requirements Compiler diagnostic namespace;
7. security/privacy/approval representation;
8. requirement-to-IR mapping rules;
9. PRS `DEFERRED` recommendation;
10. IRG-008-001 and IRG-008-002 as Phase 5 inputs.

All remain Proposed pending independent review and explicit owner approval.

## Required manual review answers

| # | Question | Answer |
|---:|---|---|
| 1 | What is the canonical requirements boundary? | A versioned requirements document, diagnostics, IR mappings, compile result, and evidence bundle between attributable intent input and frozen IR v0.1. |
| 2 | What is authoritative input? | Explicit owner/user decisions and accepted contracts under the documented precedence, supported by attributable source evidence. |
| 3 | What is merely proposed input? | Model suggestions, PRS/source-language drafts, unresolved defaults, provider constraints, and any unaccepted producer output. |
| 4 | How is accepted meaning distinguished from model suggestion? | Separate acceptance state and authority basis; model proposals cannot self-accept and require deterministic validation plus permitted authority. |
| 5 | How are requirement identities stabilized? | Version-scoped stable IDs with uniqueness enforcement, immutable evidence links, and no silent ID reuse for different meaning. |
| 6 | How are source locations preserved? | Stable source IDs with URI, RFC 6901 JSON Pointer, optional line/column, lifecycle, and content digest when bytes exist. |
| 7 | How are ambiguity and conflicts represented? | Explicit questions, assumptions, conflicts, disputed/unresolved acceptance state, affected requirement/source IDs, and stable diagnostics. |
| 8 | Which defaults require approval? | Every consequential default; all defaults must also be visible, scoped, attributable, and non-conflicting. |
| 9 | What causes SUCCESS? | Every required accepted requirement is valid, evidenced, and mapped, with no blocking diagnostic. |
| 10 | What causes PARTIAL? | All required meaning meets SUCCESS while only explicitly optional/deferrable meaning remains visible and unresolved. |
| 11 | What causes BLOCKED? | Missing decisions/context/evidence/approvals, unresolved conflicts, unsupported required meaning, or v0.1 mapping gaps. |
| 12 | What causes REFUSED? | Accepted policy or safety authority prohibits compilation or the requested operation. |
| 13 | What causes INVALID_OUTPUT? | Unknown schema/version/diagnostic, duplicate identity, invalid references/locations, semantic emptiness, or model self-acceptance. |
| 14 | How does every requirement map to IR or an explicit gap? | A mapping record names a permitted outcome, exact target pointer where applicable, authority/validation evidence, or stable gap/diagnostic. |
| 15 | How does every emitted IR leaf map back to accepted meaning? | Reverse traceability admits only accepted requirements, authorized defaults, or permitted deterministic derivations. |
| 16 | How are security/privacy/approval requirements prevented from weakening? | They are first-class required meaning; lower authority, models, providers, and implementations cannot weaken them, and missing evidence fails closed. |
| 17 | What is the PRS disposition recommendation and why? | `DEFERRED`, because source-neutral semantics now exist but grammar, source maps, complexity limits, representative coverage, and comparative value remain unproven. |
| 18 | Which PRS elements remain unproven? | Grammar, escaping, version negotiation, deterministic parsing, source maps, error behavior, imports, macros, extensions, adversarial semantics, and added value. |
| 19 | Which requirements expose IR v0.1 gaps? | Opaque continuation state (`REQ-RUNTIME-001`) and per-request reasoning configuration (`REQ-REASONING-001`). |
| 20 | Which exact owner decisions are still required? | RCD-008-001 through RCD-008-010, listed above and detailed in `OWNER_DECISION_REQUEST.md`. |
| 21 | What remains non-authorized after approval? | Production compilation/parser/model work; MISSION-009–011; IR v0.2/ADR-007 acceptance; evaluation/repair; providers/live/credentials/benchmarks/UI/hosting; merge/release/tags. |
| 22 | Why is this not a production requirements compiler? | It validates structured contract fixtures and schemas only; it does not parse ordinary language/PRS, generate requirements, lower into IR, call a model, expose a product API/CLI, or carry production certification. |

## Deviations and unresolved issues

- No scope deviation required production code, frozen-contract, diagnostic-registry, adapter, CI, package, generated-contract, or tag changes.
- PRS remains deferred rather than promoted.
- The two IR gaps remain explicit; no stop condition was hidden or solved by widening scope.
- Open semantic questions are recorded in `OPEN_QUESTIONS.md`.

## Local validation

All commands were run from the isolated MISSION-008 worktree in an isolated `.venv` (Python 3.11.15, matching the CI matrix's minimum), built via `python -m pip install -e .` exactly as CI does. Command authority is the current repository: `.github/workflows/ci.yml`, `validate_contract.py`, `tests/requirements/test_requirements_contract.py`, and `pyproject.toml`.

**Continuation-specific fix.** The authority-vocabulary defect (schema missing `user_decision`, three normative docs and one fixture using stale `owner_approved`/`user_approved`) is corrected. `validate_contract.py` is extended with a resolver-aware schema-instance validator (`referencing.Registry` keyed by each schema's `$id`) that independently reports two corpora rather than one:

- the original 41 semantic-oracle fixtures (`fixture_count`/`fixture_pass_count`), unchanged in shape;
- a new 19-instance schema-instance corpus (`schema_instance_count`/`schema_instance_pass_count`) covering all eight schemas, added because the validator previously only meta-validated the schema documents themselves and never validated any instance against them.

Every negative schema instance carries `expected_rejection` metadata (`keyword`, `instance_path`, optional `schema_path`) and only "passes" when the validator's actual error matches that exact expectation — proving the intended defect is the specific reason for rejection, not merely that some error occurred. The two `requirement.schema.json` instances using stale `owner_approved`/`user_approved` both fail specifically at `/authority_basis` under the `enum` keyword, as required. Validation-error records are normalized (`instance_path`, `keyword`, `schema_path`, `message`) and deterministically sorted before being written to evidence.

**Targeted MISSION-008 validation** — `python -m pytest tests/requirements/`: **13/13 passed** (10 original + 3 new: authority-basis vocabulary/prose parity, schema-instance corpus correctness, schema-instance byte-determinism).

**Contract validator** — `python architecture/requirements-compiler-contract-v0.1/validate_contract.py --write-evidence`: `"status": "PASS"`, `"errors": []`.
- Semantic fixtures: 41/41 passed, 8 schemas meta-validated.
- Schema-instance corpus: 19/19 passed (10 positive, 9 negative), covering all eight schemas; the `requirement.schema.json` corpus specifically proves `owner_decision`, `user_decision`, and `accepted_contract` are accepted and `owner_approved`/`user_approved` are rejected at `/authority_basis`.
- Repeated-run byte-identity confirmed directly (two consecutive `validate_package()` calls produced identical canonical JSON).
- Frozen IR and diagnostic-registry hashes unchanged (`test_frozen_ir_and_diagnostic_registry_hashes_are_unchanged` passed).

**Full repository validation** — `python -m pytest`: **338/338 passed** (325 baseline + 13 in `tests/requirements/`).
- Four dataset validations (`prompt_audit_cases.jsonl`, `meta_prompting_cases.jsonl`, `agentic_mode_cases.jsonl`, `adversarial_cases.jsonl`): all passed.
- Compiler Core smoke tests, installed script and `python -m` invocation, `doctor` and `adapters`: all returned `"status": "success"`.
- TypeScript regeneration (`scripts/generate_typescript_contracts.py`): zero drift (`git diff --exit-code -- architecture/typescript` exited 0; the working tree shows only a line-ending normalization artifact from local `core.autocrlf`, with no content difference, and this repository's generated TypeScript files were not part of this continuation's intended change set).
- `git diff --check`: no whitespace errors.
- Frozen tag `v0.5-architecture-freeze` resolves to `7948c9a419dc02ea43ca994f0334733ea4b08855` locally, matching the required commit.
- Changed-file scope review (`git diff --name-only b12b8262449d1a04cb3802f17f5f44f9a84de5d4`): every changed or new file is within `architecture/requirements-compiler-contract-v0.1/`, `architecture/README.md`, `architecture/strategy/CAPABILITY_MATURITY_MAP.md`, `architecture/strategy/REQUIREMENT_TO_ROADMAP_TRACEABILITY.md`, or `tests/requirements/`; no frozen path (`architecture/compiler-contract-freeze-v0.5/`, `architecture/diagnostics/DIAGNOSTIC_CODE_REGISTRY.json`) or `src/promptrig` production code changed.

**Explicitly not run — no current executable definition found.** This repository has no standing script for a Markdown link/anchor check, a duplicate-heading check, or a historical-corpus count/aggregate-SHA check (searched `scripts/` and the repository; none exists). Per this continuation's command-authority rule, current CI/scripts/package configuration governs over historical mission reports, so these checks are reported as not currently defined rather than invented or borrowed wholesale from a prior mission's ad hoc numbers.

## Final-head CI and PR state

This report cannot embed the final-head CI run or PR state as a claim inside itself: doing so would require a commit that changes HEAD, which would invalidate the very claim that the recorded run tested the final head. Final-head CI results and current PR state are therefore authoritative only through GitHub PR metadata (the draft PR's checks and a PR comment recording the exact run), not through any commit to this file.

## Explicit non-claims

- The contract package remains Proposed and is not self-ratified or certified.
- No production requirements compiler, ordinary-language compiler, or PRS parser exists.
- No model was integrated or called.
- No evaluation, repair, live execution, provider, credential, permission, benchmark, UI, hosted infrastructure, or MISSION-009–011 work began.
- Frozen PromptRig IR v0.1, the frozen diagnostic registry, frozen contracts, existing code/tests/schemas/adapters/CI/packages/generated contracts/historical evidence/tags were not changed.
- The draft PR is not permission to merge, mark ready, or enable auto-merge.
