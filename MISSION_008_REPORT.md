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

Schema/version checks, identities, references, authority backing, approval resolution, default authorization, mechanical conflicts, security and privacy classification by canonical `type`, mapping completeness, terminal-status precedence, and fail-closed policy enforcement are deterministic authority, and each is now executed by the validator rather than asserted. A future model may propose records only; proposals preserve provenance, remain unaccepted, cannot self-approve or invent authority, and must pass deterministic validation. MISSION-008 makes no model call and defines no production prompt.

**Correction (this round).** Before this corrective round the validator did **not** actually enforce several of the properties this report previously claimed for it: an accepted requirement could carry `model_suggested` authority, an approval reference was treated as authorization without being resolved, a consequential default could self-certify through a boolean, security handling keyed on an ID prefix rather than `type`, and `SUCCESS`/`PARTIAL` could be reached with an accepted required requirement that had no emitting mapping. Those claims were stronger than the evidence supported. They are now backed by executed checks and adversarial regression tests; diagnostic ordering beyond code sorting remains `manual_review` rather than an executed guarantee.

## Requirement-to-IR traceability

Every requirement has a direct, deterministic-derivation, authorized-default, unresolved, prohibited, or no-IR-representation outcome. Successful mappings use exact RFC 6901 pointers into frozen IR v0.1. Every emitted leaf must reverse-map to accepted meaning, an authorized visible default, or a permitted deterministic derivation. Missing representation preserves the requirement, emits `RQC-IRG-0001`, blocks required meaning, and creates a Phase 5 input.

## IR v0.1 gap register

- `IRG-008-001`: opaque provider continuation state has no provider-neutral v0.1 representation.
- `IRG-008-002`: per-request reasoning configuration has no accepted v0.1 field.

Both remain blocked evidence for separately authorized Roadmap Phase 5 planning. Neither selects an IR shape, accepts ADR-007, changes v0.1, or bypasses the MISSION-011 production-certification dependency.

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
| 4 | How is accepted meaning distinguished from model suggestion? | Separate acceptance state and authority basis. `model_suggested` is structurally forbidden on accepted meaning, a model proposal can never be `accepted`, and meaning a proposal originated cannot be relabelled `directly_stated`. Enforcement does not depend on any self-reported adversarial flag. |
| 5 | How are requirement identities stabilized? | Version-scoped stable IDs with uniqueness enforcement, immutable evidence links, and no silent ID reuse for different meaning. |
| 6 | How are source locations preserved? | Stable source IDs with URI, RFC 6901 JSON Pointer, optional line/column, lifecycle, and content digest when bytes exist. |
| 7 | How are ambiguity and conflicts represented? | Explicit questions, assumptions, conflicts, disputed/unresolved acceptance state, affected requirement/source IDs, and stable diagnostics. |
| 8 | Which defaults require approval? | Every consequential default, resolved to an active, evidenced, scope-covering approval record under an explicit accepted approval policy; a boolean never authorizes. All defaults must also be visible, scoped, attributable, and non-conflicting. |
| 9 | What causes SUCCESS? | Every accepted requirement carries a permitted authority basis backed by resolved evidence, and every accepted requirement has a valid emitting mapping, with no blocking diagnostic. An accepted requirement without an emitting mapping is `BLOCKED`, never `SUCCESS`. |
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

**Continuation-specific fix (round 1).** The authority-vocabulary defect (schema missing `user_decision`, three normative docs and one fixture using stale `owner_approved`/`user_approved`) is corrected. `validate_contract.py` is extended with a resolver-aware schema-instance validator (`referencing.Registry` keyed by each schema's `$id`) that independently reports two corpora rather than one: the original 41 semantic-oracle fixtures, and a new schema-instance corpus covering all eight schemas.

**Independent-review corrective work (round 2).** An independent review of the first draft PR returned eight numbered blockers; all eight are addressed in this package as new corrective commits on top of the original five plus the round-1 fix, without amending, squashing, rebasing, resetting, or force-pushing any published commit:

1. **Canonical requirement vocabulary.** `REQUIREMENTS_COMPILER_SPEC.md` RC-012/RC-013 and `requirement.schema.json` now agree exactly: the requirement-type set is grounded in contract evidence (`runtime` is backed by `REQ-RUNTIME-001`/`IRG-008-001`; `capability`/`policy` have zero backing anywhere in the package and are excluded from both prose and schema); priority stays `required`/`optional` (`recommended` is not introduced, since it has no terminal-status behavior, mapping rule, fixture, or owner-review consequence defined); the requirement-ID pattern is bounded to `^REQ-[A-Z0-9-]{3,64}$` everywhere it appears (`requirement.schema.json`, `requirement-ir-mapping.schema.json`, `requirements-diagnostic.schema.json`, `requirements-evidence-bundle.schema.json`). A new `find_vocabulary_drift` validator check and dedicated pytest tests (including one that injects a deliberately broken enum to prove the check is not vacuous) cover this.
2. **IR-pointer validity.** The `file-source-location-stability` fixture's mapping target was replaced with a real frozen-IR v0.1 leaf (`/objective/goal`/`/requirements/0/statement` pattern); `/project/objective` is no longer used as a positive example anywhere. `validate_contract.py` gained `build_ir_pointer_index`/`classify_ir_pointer`, which walks the frozen IR schema and classifies every candidate `target_pointer` as `valid`, `invalid_pointer_syntax`, `subtree_shortcut`, or `not_a_permitted_leaf`; `_derive_outcome` now rejects any emitting mapping (`direct`/`deterministic_derivation`/`authorized_default`) whose `target_pointer` does not classify as `valid`. A new 11-case fixture corpus (`fixtures/ir_pointer_cases.json`, 6 positive/5 negative) and dedicated pytest tests cover both the classifier directly and a synthetic semantic case proving the invalid-pointer rejection fires with the correct diagnostic (`RQC-EVD-0001`).
3. **Evidence-model schema strictness.** `requirements-evidence-bundle.schema.json` now requires explicit reference arrays for every EM-020 record class (`derivation_refs`, `model_proposal_refs`, `assumption_refs`, `conflict_refs`, `question_refs`, `approval_refs`, `default_refs`, `test_mapping_refs`, `diagnostic_refs`, `gap_refs`) plus `frozen_ir_version` (exact frozen-IR target version) and an optional `compile_result_ref` (terminal-status evidence). `requirements-document.schema.json` replaces unrestricted object placeholders with strict inline `$defs` (`additionalProperties: false`, required fields, ID patterns) for `assumption`, `question`, `conflict`, `default`, `approval`, `model_proposal`, `derivation`, and `test_mapping`; the `assumption`/`question` `$defs` use `oneOf[string, strict object]` to preserve the 41 preserved semantic-oracle fixtures' existing bare-string shorthand without leaving the schema unrestricted (disclosed as `OQ-008-010`). 14 new schema-instance fixture pairs (7 positive/7 negative) cover these new nested records.
4. **Traceability repair.** `evidence/requirement-field-justifications.json` was corrected against the package's actual clause text (14 misattributed citations fixed, 28 newly-required fields given verified citations across two passes). New validator checks — `find_unknown_clause_references` (rejects any cited clause ID not actually defined in the package's `.md` files) and `find_uncovered_required_fields` (rejects any schema-required field lacking a justification entry) — plus dedicated pytest tests (including an injected-defect test proving both checks actually detect drift) close the gap between claimed and real traceability.
5. **Governance wording.** `DECISION_LOG.md` RCD-008-004 and RCD-008-010, and the matching line in this report and in `evidence/unresolved-ir-gaps.json`, now read "separately authorized Roadmap Phase 5 planning" (not "unauthorized"). RCD-008-004 explicitly states deterministic validation establishes structural/contract validity while semantic acceptance additionally requires permitted authority and attributable evidence, and that model-assisted output remains proposal-only until separately accepted.
6. **Exact frozen-byte integrity.** The frozen-hash test no longer normalizes CRLF/LF on a working-tree read; it now shells out to `git show HEAD:<path>` (via `subprocess.run`, not shell interpolation) and hashes the exact returned git-blob bytes, with an explicit `pytest.fail` path if the blob cannot be retrieved. This detects any committed byte change, including a line-ending-only change, and cannot be fooled by a local `core.autocrlf` checkout setting.
7. **PR metadata** and **CI verification** are addressed after this corrective push — see "Final-head CI and PR state" below.

**Targeted MISSION-008 validation** — `python -m pytest tests/requirements/`: **21/21 passed** (13 from round 1 + 8 new: vocabulary-drift absence, bounded requirement-ID pattern, unknown-clause-reference absence, required-field-coverage completeness, an injected-defect proof that the drift/coverage checks are not vacuous, the 11-case IR-pointer corpus, `validate_package`'s aggregate reporting of all three new checks, and a synthetic semantic case proving an impossible IR pointer yields `INVALID_OUTPUT`/`RQC-EVD-0001`).

**Contract validator** — `python architecture/requirements-compiler-contract-v0.1/validate_contract.py --write-evidence`: `"status": "PASS"`, `"errors": []`.
- Semantic fixtures: 41/41 passed, 8 schemas meta-validated.
- Schema-instance corpus: 33/33 passed, covering all eight schemas including the new nested evidence-model records; the `requirement.schema.json` corpus specifically proves `owner_decision`, `user_decision`, and `accepted_contract` are accepted and `owner_approved`/`user_approved` are rejected at `/authority_basis`.
- IR-pointer case corpus: 11/11 passed (6 positive, 5 negative), including the `/project/objective` → `not_a_permitted_leaf` and `/requirements/0` → `subtree_shortcut` negative cases.
- Zero unknown clause references, zero uncovered required fields, zero vocabulary drift.
- Repeated-run byte-identity confirmed directly (two consecutive `validate_package()` calls produced identical canonical JSON).
- Frozen IR and diagnostic-registry hashes unchanged, verified via exact git-blob subprocess hashing (`test_frozen_ir_and_diagnostic_registry_hashes_are_unchanged` passed).

**Full repository validation** — `python -m pytest`: **346/346 passed** (338 from round 1 + 8 new in `tests/requirements/`).

**Final corrective round — how this round was validated.** The round-2 numbers above describe head `e04086be` and are retained as the record of that round. In the final corrective round the local environment had no installable `pytest` (a locked system interpreter refused both a normal and a `--user` install), so this report does **not** assert a local pytest count for it. Instead the round was validated by (a) executing `validate_contract.py` directly, which reports all four corpora and the traceability checks, (b) executing each new test assertion as a standalone script against the real validator, and (c) the GitHub Actions CI matrix, which installs pytest and runs the full suite on every pushed head. The authoritative pass/fail signal for this round is the final-head CI run recorded in the PR, not a locally claimed number.
- Four dataset validations (`prompt_audit_cases.jsonl`, `meta_prompting_cases.jsonl`, `agentic_mode_cases.jsonl`, `adversarial_cases.jsonl`): all passed.
- Compiler Core smoke tests, installed script and `python -m` invocation, `doctor` and `adapters`: all returned `"status": "success"`.
- TypeScript regeneration (`scripts/generate_typescript_contracts.py`): zero drift (`git diff --exit-code -- architecture/typescript` exited 0; a byte-level `cmp` against the committed blob confirmed the regenerated files are identical to HEAD, with git status flagging them only due to a stat-level line-ending artifact under local `core.autocrlf`, not a content change).
- `git diff --check`: no whitespace errors.
- Frozen tag `v0.5-architecture-freeze` resolves to `7948c9a419dc02ea43ca994f0334733ea4b08855` locally, matching the required commit; confirmed unchanged before and after this round's corrective work.
- Changed-file scope review: every changed or new file for this round is within `architecture/requirements-compiler-contract-v0.1/` or `tests/requirements/test_requirements_contract.py`; no frozen path (`architecture/compiler-contract-freeze-v0.5/`, `architecture/diagnostics/DIAGNOSTIC_CODE_REGISTRY.json`) or `src/promptrig` production code changed.

**Explicitly not run — no current executable definition found.** This repository has no standing script for a Markdown link/anchor check, a duplicate-heading check, or a historical-corpus count/aggregate-SHA check (searched `scripts/` and the repository; none exists). Per this continuation's command-authority rule, current CI/scripts/package configuration governs over historical mission reports, so these checks are reported as not currently defined rather than invented or borrowed wholesale from a prior mission's ad hoc numbers.

## Final corrective round — blocker corrections and three-layer evidence

Two independent reviews returned `REQUEST CHANGES` against head `e04086be`. All four confirmed blockers are corrected in this round; the ten published commits are preserved and only new commits were created.

| Blocker | Correction |
|---|---|
| B1 — model-suggested meaning could self-accept | `requirement.schema.json` conditionally restricts an accepted requirement to the six accepted-permitted authority bases; `model_proposal.acceptance_state` can no longer be `accepted`; the validator independently rejects impermissible accepted authority and refuses to let model-originated meaning be relabelled `directly_stated`. Optional `self_accepted`/`weakens_security` markers now gate nothing (RC-025, RC-026). |
| B2 — approval references were never resolved | Approvals are loaded and resolved: the record must exist, be an active `approved` decision, cover the subject, and carry non-empty evidence. Rejected, revoked, expired, superseded, and dangling references all fail closed. A default's `approved` boolean no longer authorizes anything. Required authority follows an explicit accepted approval-policy reference; while OQ-008-003 is open, undeterminable authority is `BLOCKED` rather than assumed (SP-020, SP-025). |
| B3 — security keyed on ID prefixes | Security and privacy handling keys on canonical `type`. Identifiers are identity only (SP-001). |
| B4 — mapping completeness unenforced | Terminal status is derived by an explicit precedence matrix rather than a first-match chain. An accepted requirement without an emitting mapping is `BLOCKED`; optional ambiguity can no longer mask a security refusal, missing approval, or unmapped required meaning (RC-065, RC-066). |

**Three independent validation layers**, each reported with its own counts; no layer's result is evidence for another:

| Layer | Corpus | Result |
|---|---|---|
| Schema-instance | `fixtures/schema_instances.json` | 33/33 |
| Semantic-oracle | `fixtures/cases.json` | 41/41 |
| Linked-artifact closure | `fixtures/linked_artifact_sets.json` | 11/11 (4 positive covering SUCCESS/PARTIAL/BLOCKED/REFUSED, 7 negative each proving its specific rejection reason) |
| IR-pointer classification | `fixtures/ir_pointer_cases.json` | 11/11 |

The 41 semantic-oracle cases are a **test-only semantic projection, not canonical requirements documents**, and were deliberately not rewritten into schema documents.

**Linked-artifact closure.** Each set validates every artifact against its own schema, then proves that references resolve, that the bundle closes over every canonical document record class, and that result and bundle references are mutually consistent. Same-attempt membership is proved by an explicit reference chain — `compile_result.attempt_id` ↔ `evidence_bundle.compile_result_ref`, and `compile_result.requirements_document_ref` → `requirements_document.document_id` — never by records appearing together in one fixture (EM-025).

**Frozen IR version.** `frozen_ir_version` is the exact `0.1.0`, equal to frozen IR v0.1's `spec_version` constant, which the validator reads and compares. `compile_result_ref` is now required (EM-023).

**Traceability.** Required-field coverage now spans all eight schemas including nested `$defs` and conditionally required fields: **125 fields**, against the 53 the previous five-schema top-level-only check inspected. All 183 normative clauses carry exactly one explicit disposition in `evidence/clause-dispositions.json`. `manual_review` is retained as a first-class disposition with a required rationale (34 clauses): deterministic validation proves identifier existence, disposition completeness, and field coverage, and **does not** claim to prove that a natural-language clause citation is semantically apt (TR-014, TR-015).

**OQ-008-010 resolved — structured-only canonical records**, by explicit owner decision recorded in the MISSION-008 instruction context and **not** appended to the frozen D-050 log. Canonical assumptions and questions now require stable identity and normative evidence, so `assumption_refs`/`question_refs` close over every canonical record. All `RCD-008-*` decisions remain **Proposed**; this round approves none of them, and the PRS disposition remains `DEFERRED`.

## Corrective round 3 — canonical composition and complete reference resolution

A further independent review of head `05ca2e2` returned `REQUEST CHANGES`. It accepted the B1–B4
corrections *within the semantic-oracle layer* and identified that the canonical path never ran
those rules, plus several incomplete resolutions. All seven blockers are corrected.

| Blocker | Correction |
|---|---|
| 1 — closure was not validity | One shared contract-rule engine (`evaluate_contract_rules`) now evaluates a normalized `ContractRuleContext` reached through two adapters: `context_from_fixture` (compact) and `context_from_artifacts` (canonical). Every linked set derives its terminal status and diagnostics from its canonical artifacts and must match `compile_result.status`, `reason_codes`, `diagnostic_refs`, and mapping evidence exactly; a canonical `SUCCESS`/`PARTIAL` that fails semantic validation is rejected. There is exactly one rule implementation. ~~Canonical evaluation inspects **no** authoring prose.~~ **This last sentence was false at this round's head**: `owner_user_conflict` was still derived from `authoritative_inputs` string prefixes. See "Round 4 — canonical conflict made structural" below, which corrects it. |
| 2 — approval resolution incomplete | Authorization now requires the full chain: subject → `approval_ref` → approval → `policy_ref` → accepted policy → authoritative source with exact identity, version, and digest. Unique ID, active `approved`, exact subject coverage, `scope.kind`+`scope.value` coverage, authority satisfying the policy, and evidence resolving through `evidence_refs` (preserved source or governed external URI+SHA-256) are all checked. `required_authority` is `owner`/`user`/`owner_or_user`/`owner_and_user` — the ambiguous `any` is gone. Requirements, assumptions, and defaults share one resolution path, and `default.approved` must agree exactly with the resolved state. A truthy string never satisfies the gate. |
| 3 — duplicate identities hidden | `find_duplicate_identities` counts over **lists** across all 16 canonical namespaces; `_unique` fails closed on zero *or* more than one match, so authorization cannot depend on which duplicate appears last. Order-reversal fixtures prove it. |
| 4 — security status semantics | An accepted security/privacy requirement missing evidence or mapping is now `BLOCKED` (`RQC-BLK-0001` + `RQC-SEC-0001`/`RQC-PRV-0001`). `REFUSED` requires an accepted `prohibition` policy that resolves and whose scope applies (SP-011/SP-024). The regression tests that expected unconditional `REFUSED` were corrected. |
| 5 — authority-basis matrix incomplete | Each basis now resolves fully, and withdrawn/replaced/missing evidence never supports acceptance. `accepted_contract` requires exact identity, version, and digest — not merely source kind. Per RC-027, a byte-backed `directly_stated` source additionally requires the statement digest to equal the preserved fragment digest; semantic *equivalence* remains manual review and is never claimed as automated proof. |
| 6 — closure incomplete | Mapping `authority_ref` (type-specific) and `validation_ref`, diagnostics, gaps, derivations, and validation records all resolve; result mappings and diagnostics equal the attempt's exactly; reason codes reconcile with diagnostics; and declared hashes are recomputed from actual canonical bytes. No syntactically valid dangling reference survives. |
| 7 — pointer parity | `source-evidence.schema.json` accepts complete multi-segment RFC 6901 pointers, matching the semantic validator exactly, with new nested-pointer positive and malformed-escape negative fixtures. |

**Attempt-bound versus reusable evidence (EM-025).** Intent input, requirements document, mappings,
diagnostics, and compile result are attempt-bound and hash-verified. Sources, policies, approvals,
and external evidence are reusable authority evidence: not produced by the citing attempt, but
immutable, content-addressed, and referenced exactly. The report no longer claims every record
belongs to the same attempt.

**Canonical hashing (EM-027).** UTF-8; object keys sorted; array order preserved as semantic order;
compact separators; one trailing newline; SHA-256 over those bytes. `artifact_hashes` keys are
restricted to the attempt-bound artifacts and the bundle never hashes itself, so the digest domain
is acyclic. A reusable record's `content_digest` is taken over the record with that field removed.

**Layer results (four independent corpora):** schema-instance **35/35**, semantic-oracle **41/41**,
linked-artifact **26/26** (5 positive covering SUCCESS/PARTIAL/BLOCKED/REFUSED plus a fully resolved
approval chain; 21 negative each proving its specific rejection reason), IR-pointer **11/11**.
Deterministic evidence is byte-identical across repeated runs.

**Traceability after this round.** The new canonical records enlarge the required-field surface:
**159 enumerated required fields** across all eight schemas including nested `$defs` and
conditionally required fields, all covered, carried by 160 justification entries (155 for required
fields plus 5 documenting conditionally-optional fields). Normative clauses rise to **186**, each
with exactly one explicit disposition, of which **35** remain `manual_review` with a recorded
rationale. The counts stated in the previous round's section above (125 fields, 183 clauses, 34
`manual_review`) describe that round and are retained as its record, not as current totals.

**Local verification for this round.** Unlike the previous round, a working interpreter was
available, so the full suite ran locally: `python -m pytest` **366 passed**; four dataset
validations passed; Compiler Core CLI `doctor` and `adapters` returned success; TypeScript
regeneration produced no drift; `git diff --check` clean; frozen IR and frozen diagnostic-registry
blobs byte-identical to baseline with tag `v0.5-architecture-freeze` still at
`7948c9a419dc02ea43ca994f0334733ea4b08855`.

All `RCD-008-*` decisions remain **Proposed**; this round approves none. PRS remains `DEFERRED`.

## Round 4 — canonical conflict made structural (independent-audit correction)

An independent read-only audit of head `c2fd4ad6b72929ec009fef1e0417045c1875f7d4`, reconciled and
confirmed, found one blocker that this round corrects. It is recorded here in full because the
previous round's claim about it was false.

**The defect.** `context_from_artifacts` derived the status-bearing `owner_user_conflict` signal from
`owner:` / `user:` string prefixes in `intent_input.authoritative_inputs`, a field the schema
constrains only to a nonempty string (no pattern, no enum). The audit produced two canonical artifact
sets **identical in every record** — same requirements, sources, approvals, policies, mappings, and
diagnostics — that both validated as `valid` while declaring different terminal statuses (`SUCCESS`
versus `BLOCKED` with `RQC-AUT-0001` and `RQC-CFL-0002`), because only the free-text labels differed.
Canonical terminal status was therefore **not** a function of the canonical record set, and a verifier
holding only the records could not recompute it. The rule was also exercised by **0 of 26** linked
artifact sets, so no canonical fixture could have caught it.

**Correction of a false prior claim.** Earlier sections of this report, and the previous version of
the package README and of `context_from_artifacts`' own docstring, asserted that canonical evaluation
inspects **no** authoring prose. That assertion was **incorrect** for `authoritative_inputs` at heads
up to and including `c2fd4ad`. It is now true and enforced by test.

**What changed.** A new `structured_owner_user_conflict()` derives the signal from records only: an
unresolved `conflicts` record whose required `authority_ranks` span `owner` and `user`. The canonical
adapter uses that and nothing else, and now reads no field of `intent_input` other than
`contract_version`. No new free-text convention, prefix grammar, or parser was introduced. The
owner/user check moved **ahead** of the generic conflict codes in the precedence matrix, because a
canonical conflict record always carries `source_ids` (required, `minItems` 1), so `RQC-SRC-0004`
would otherwise shadow the specific authority diagnostic on every canonical set. `AD-003` now states
the structural basis normatively. The compact corpus keeps its `owner:`/`user:` shorthand, confined to
`context_from_fixture` and documented there as a noncanonical test projection that cannot reach
canonical validity.

**Canonical coverage added.** Two linked artifact sets close the corpus gap, taking the layer to
**28**: `LAS-POS-OWNER-USER-CONFLICT-001` (a real structured conflict, `BLOCKED` with
`RQC-AUT-0001`/`RQC-CFL-0002`) and `LAS-NEG-PROSE-ONLY-CONFLICT-001` (the former exploit — prose
prefixes present, no conflict record, declared `BLOCKED`, rejected as `semantic_status_mismatch`).

**Regression tests.** Seven new tests prove: eleven prose variants (prefix, capitalization,
punctuation, empty-suffix, repeated, lookalike, embedded-in-sentence) change neither status nor
diagnostics and cannot even set the signal; a real structured conflict blocks with the specific
codes; removing or renaming prose cannot hide a structured conflict; the structured signal is exact
(resolved, single-rank, or mis-cased ranks do not set it); the canonical fixtures exercise both
directions; the fixture-only shorthand is confined to the fixture adapter. One test is an in-memory
**negative control** that monkeypatches the legacy prefix behaviour back in, asserts the
prose-invariance property then breaks (`SUCCESS` → `BLOCKED`), and restores the original — so the
regression suite is proven load-bearing rather than decorative. No validator file is modified by it.

**Layer results after this round:** schema-instance **35/35**, semantic-oracle **41/41**,
linked-artifact **28/28** (6 positive, 22 negative), IR-pointer **11/11**; `tests/requirements`
**48 passed**; full suite **366 passed**; deterministic evidence byte-identical across two
regenerations. Traceability counts are unchanged at 159 required fields, 160 justification entries,
186 clauses, and 35 `manual_review` dispositions: no schema field and no normative clause was added.

**Also corrected.** The frozen Compiler Core diagnostic registry is
`architecture/diagnostics/DIAGNOSTIC_CODE_REGISTRY.json`. Earlier handoff prose referred to a
nonexistent `architecture/compiler-contract-freeze-v0.5/compiler-diagnostic-registry.json`; any check
following that path would have verified nothing. The in-repo frozen-hash test already pinned the
correct path and is unchanged.

Round 4 changes no schema, adds no production code, touches no frozen path, and approves no decision.
All ten `RCD-008-*` decisions remain **Proposed**. PRS remains `DEFERRED`.

## Final-head CI and PR state

This report cannot embed the final-head CI run or PR state as a claim inside itself: doing so would require a commit that changes HEAD, which would invalidate the very claim that the recorded run tested the final head. Final-head CI results and current PR state are therefore authoritative only through GitHub PR metadata (the draft PR's checks and a PR comment recording the exact run), not through any commit to this file.

## Explicit non-claims

- The contract package remains Proposed and is not self-ratified or certified.
- No production requirements compiler, ordinary-language compiler, or PRS parser exists.
- No model was integrated or called.
- No evaluation, repair, live execution, provider, credential, permission, benchmark, UI, hosted infrastructure, or MISSION-009–011 work began.
- Frozen PromptRig IR v0.1, the frozen diagnostic registry, frozen contracts, existing code/tests/schemas/adapters/CI/packages/generated contracts/historical evidence/tags were not changed.
- The draft PR is not permission to merge, mark ready, or enable auto-merge.
