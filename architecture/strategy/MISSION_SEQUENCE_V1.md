# Mission Sequence V1

**Status:** Proposed. These mission definitions authorize no work until the strategy package receives independent architectural review, explicit owner approval, and a separate mission launch from an exact verified baseline.

## Sequence law

MISSION-008, MISSION-009, and MISSION-010 are dependency-ordered. Contracts precede production implementation. No mission may silently change frozen Compiler Core v0.1, start live execution, add a provider, add a hosted surface, or merge without independent review and owner approval.

## MISSION-008 — Requirements Compiler Contract and Evidence Model

**Mission purpose:** Define the authoritative, testable boundary from user intent and structured authoring inputs to requirements evidence and valid PromptRig IR.

**Strict scope**

- requirements identities, priority, provenance, assumptions, ambiguity, conflicts, open questions, defaults, and owner/user decisions;
- deterministic versus model-assisted stage boundaries;
- source locations and immutable diagnostics;
- requirement-to-IR and requirement-to-test/evidence traceability;
- exact success, partial, blocked, refused, and invalid-output semantics;
- decision on whether PRS proceeds as a contract candidate, remains deferred, or is rejected;
- executable fixtures and validators for the contract package only.

**Non-scope**

- production requirements compiler or model integration;
- PRS parser implementation unless a later implementation mission is authorized;
- evaluation, repair, live provider calls, runtime state, UI, FastAPI, persistence, tenancy, benchmarks, MissionRig, or IR v0.2 code;
- changes to frozen IR v0.1.

**Required contract-first work**

1. Write the requirements/evidence SPEC before any schema prototype.
2. Define semantic invariants and authority/default rules.
3. Map every proposed field to representative authoring evidence.
4. Define diagnostics and source mappings.
5. Create adversarial valid-looking fixtures before accepting syntax.
6. Record IR gaps as Phase 5 inputs rather than altering v0.1.

**Expected tests**

- normal, missing-context, ambiguity, conflict, contradictory priority, duplicate identity, unsupported requirement, refusal, and adversarial injection cases;
- deterministic repeat and ordering cases;
- semantically empty but schema-valid rejection;
- source-location and diagnostic stability;
- requirement-to-IR leaf completeness;
- unknown-field and version mismatch;
- no-network and no-credential enforcement.

**Stop conditions**

- requirements cannot be represented without changing frozen IR;
- PRS syntax is being selected for convenience without representative cases;
- model-assisted output has no deterministic validation boundary;
- a default would silently change user meaning;
- security/privacy or approval requirements lack an honest fail-closed representation;
- source evidence or traceability cannot be preserved.

**Merge gate:** Independent architecture review confirms executable semantics and no frozen-contract mutation; the owner explicitly accepts the requirements/evidence contract and PRS disposition. CI and syntax validation alone are insufficient.

**Dependency on prior missions:** Requires owner-ratified MISSION-007 strategy. Produces normative inputs for MISSION-009 and MISSION-010.

## MISSION-009 — Evaluation and Bounded Repair Contract

**Mission purpose:** Define the deterministic-first evaluation, baseline comparison, bounded repair, regression, and evidence semantics required to close the compiler loop.

**Strict scope**

- evaluator taxonomy, authority order, identities, versions, inputs, outputs, confidence, cost, latency, and provenance;
- baseline/candidate comparison, score scales, aggregation, thresholds, errors, and unavailable-evaluator behavior;
- repair budgets of 0–2, attempt/time/cost limits, allowed mutations, provenance, regression prevention, and stop states;
- unresolved-defect and failed-attempt evidence;
- fake-adapter contract fixtures and validators only.

**Non-scope**

- production evaluator or repair engine;
- live provider/model judges as required infrastructure;
- unbounded repair, benchmark runner, UI, hosted jobs, billing, persistence, runtime state, or IR v0.2 implementation;
- modification of accepted objectives or safety policy to improve a score.

**Required contract-first work**

1. Define deterministic validators and their precedence.
2. Define baseline and candidate identity.
3. Specify judge isolation and failure semantics.
4. Specify repair authority and immutable fields.
5. Define evidence envelopes and traceability to MISSION-008 requirement identities.
6. Prove termination and regression rules in fixtures.

**Expected tests**

- deterministic validator pass/fail/error and precedence;
- baseline absent/mismatched/stale cases;
- score aggregation boundaries and evaluator failures;
- model-judge disagreement without executable-authority override;
- repair limits 0, 1, and 2;
- timeout, cost exhaustion, repeated failure, regression, and unresolved-defect output;
- objective/safety immutability and complete failed-attempt provenance;
- repeated-run determinism and no-network default.

**Stop conditions**

- a model judge is made authoritative for schema, security, or executable correctness;
- failed attempts or regressions would be discarded;
- termination depends on model self-report;
- scoring can hide evaluator errors;
- repair authority can weaken accepted meaning;
- required requirement/evidence identities from MISSION-008 are unavailable.

**Merge gate:** Independent review and explicit owner approval of evaluator authority, score/baseline semantics, repair budgets, mutation boundary, and evidence model. All adversarial fixtures must have expected outcomes.

**Dependency on prior missions:** Requires accepted MISSION-008 requirements/evidence contract. Produces normative inputs for MISSION-010.

## MISSION-010 — Headless Closed-Loop Prototype with Fake Adapter

**Mission purpose:** Implement the smallest offline end-to-end proof that accepted structured requirements can produce IR, fake-adapter artifacts, evaluation evidence, bounded repair, and final artifacts through one library/CLI boundary.

**Strict scope**

- one minimal accepted structured-requirements profile;
- deterministic requirements-to-IR compilation for that profile;
- existing certified validation, capability resolution, fake lowering, artifacts, diagnostics, and provenance;
- deterministic evaluation and bounded repair exactly as contracted by MISSION-009;
- stable library and `promptrig-compiler` CLI envelopes;
- complete end-to-end evidence bundle and behavior-level tests.

**Non-scope**

- OpenAI, Anthropic, or Gemini execution;
- credentials, network, runtime/session state, provider-hosted tools, FastAPI, Next.js, persistence, tenancy, billing, benchmark implementation, MissionRig, Workspace integration, or broad product UX;
- IR v0.2 implementation or fifth adapter;
- production hardening beyond the explicitly approved prototype.

**Required contract-first work**

- freeze the exact MISSION-008 and MISSION-009 contract revisions used;
- define orchestration and result-envelope changes before code;
- define test fixtures and expected evidence bundle before implementation;
- identify any v0.1 IR limitation as a stop condition or Phase 5 input.

**Expected tests**

- failing end-to-end tests before implementation;
- successful no-repair and one-repair cases;
- repair limits 0/1/2 and terminal unresolved failure;
- semantic mutation changes artifact/evaluation evidence or fails explicitly;
- requirement-to-IR-to-capability-to-artifact-to-evaluation-to-repair trace completeness;
- invalid requirements, invalid IR, capability gap, evaluator error, repair regression, and sink failure;
- no-network/no-credential enforcement;
- repeated determinism, library/CLI deep parity, package build, clean install, and cross-platform CI.

**Stop conditions**

- implementation requires changing a frozen contract without a separate owner-ratified change;
- a provider-specific field is proposed for canonical semantics;
- fake-adapter evidence cannot represent the contracted evaluation/repair loop;
- traceability loses any accepted requirement or IR semantic leaf;
- scope expands into live execution, hosted product, benchmark, or MissionRig;
- independent review exposes a semantic defect that green CI does not cover.

**Merge gate:** Full behavior and packaging evidence, independent architectural review with no blocker, explicit owner approval, and all required CI jobs green on the final head. No automatic merge.

**Dependency on prior missions:** Requires accepted MISSION-008 and MISSION-009 contract packages. Its evidence is the entry basis for Roadmap Phase 5.

## Cross-mission repository rules

Each mission must start from the exact owner-authorized integration commit in a new isolated worktree, name its working branch and PR target, preserve the frozen tag and historical review corpus, add failing tests before behavioral fixes, record requirement-to-test/evidence mappings, verify CI triggers, and stop on unknown work or contract ambiguity. Merge, tag, credential, live-network, visibility, and release actions remain separately approval-gated.
