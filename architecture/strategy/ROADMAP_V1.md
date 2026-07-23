# PromptRig Roadmap V1

**Status:** `OWNER_RATIFIED` through DR-007-01 through DR-007-09 in PR #12; authoritative upon merge into `feature/promptrig-framework`.
**Authority upon merge:** This file supersedes earlier sequencing statements, but not accepted contracts, ADRs, OARs, or historical evidence. Ratification authorizes no phase entry, mission execution, or implementation; every phase and MISSION-008 through MISSION-011 require separate exact-baseline authorization.

## Roadmap objective

Complete the canonical product loop in dependency order while preserving the certified Compiler Core v0.1 foundation:

```text
User intent
→ Requirements compiler
→ PromptRig IR
→ Capability resolution
→ Provider lowering
→ Evaluation
→ Bounded repair
→ Artifacts and evidence
```

A phase number expresses dependency order, not a calendar promise. Owner approval of this roadmap does not automatically approve entry into later phases.

## Phase 1 — Strategic Reconciliation and Roadmap Lock

**Goal:** Establish one repository-native account of product identity, current maturity, deferred work, dependency order, and owner authority.

**Entry criteria**

- MISSION-006 is merged at the required baseline.
- Compiler Core freeze tag and historical review evidence remain intact.
- Finalized vision input and current repository evidence are available.

**Normative deliverables**

- product vision and system ownership boundary;
- capability maturity map;
- this roadmap;
- deferred/rejected-work registry;
- requirement-to-roadmap traceability;
- next-mission sequence and owner decision request.

**Implementation deliverables:** None. This phase is governance and documentation only.

**Validation gates**

- every strategic law maps to a phase and verification method;
- every capability is evidenced, scheduled, deferred, or rejected;
- stale and contradictory sources are classified without historical rewrite;
- documentation-only diff, local links/anchors, full tests, dataset validation, TypeScript drift, historical integrity, frozen-tag verification, and seven-job CI pass.

**Owner decisions:** Accept the reconciled vision, adopt this roadmap, approve the MISSION-008–011 sequence, and retain all listed deferrals.

**Prohibited shortcuts:** No implementation, contract mutation, roadmap ratification by implication, MISSION-008 work, merge, auto-merge, or tag movement.

**Exit criteria:** Independent architectural review has no blocker and the owner explicitly ratifies the strategy package. Until then, Phase 1 remains proposed.

**Downstream dependencies:** Every later phase depends on this exit.

## Phase 2 — Requirements Compiler and PRS Contract

**Goal:** Define a deterministic, evidence-bearing boundary from user intent to valid PromptRig IR, and decide whether PRS is the first source language.

**Entry criteria**

- Phase 1 is owner-ratified.
- MISSION-008 is separately authorized from the approved baseline.
- Representative Simple Mode, Developer Mode, API, and file-based authoring cases are assembled as evidence.

**Normative deliverables**

- requirements model with stable identities, priority, provenance, assumptions, ambiguity, conflicts, and open questions;
- intent-input and requirements-output contracts;
- deterministic versus model-assisted stage boundary;
- source-location, diagnostic, and evidence model;
- exact IR-generation success, partial, refusal, and failure semantics;
- PRS decision: contract candidate, deferred source language, or rejected approach;
- security/privacy and approval requirement representation constraints;
- requirement-to-IR and requirement-to-test traceability contract.

**Implementation deliverables:** Contract fixtures, schema prototypes, and validators only if MISSION-008 explicitly authorizes them; no production requirements compiler.

**Validation gates**

- positive, negative, boundary, adversarial, ambiguity, conflict, provenance, and determinism fixtures;
- semantically vacuous but schema-valid cases fail;
- every emitted IR field traces to accepted requirements or declared defaults;
- unknown or unsupported meaning becomes an immutable diagnostic;
- no source-language convenience changes frozen IR v0.1.

**Owner decisions:** Accept the requirements/evidence boundary; decide PRS status and source-language scope; decide which unresolved semantics become Phase 5 IR inputs.

**Prohibited shortcuts:** No parser-first grammar freeze, hidden defaults, prompt-only “compiler,” model-output trust without deterministic validation, or IR v0.2 implementation.

**Exit criteria:** A reviewed, owner-ratified contract package is executable through fixtures and unambiguously defines the later implementation mission.

**Downstream dependencies:** Phases 3, 4, and 4B consume the requirement/evidence identity model; Phase 8 consumes only a headless requirements boundary already hardened under Phase 4B.

## Phase 3 — Evaluation and Bounded Repair Contract

**Goal:** Define how artifacts and behavior are evaluated, compared, repaired within budget, regression-checked, and reported.

**Entry criteria**

- Phase 2 requirements/evidence identities are accepted.
- MISSION-009 is separately authorized.
- Fake-adapter artifact fixtures and representative evaluation cases exist.

**Normative deliverables**

- evaluator types and deterministic-first authority order;
- evaluator identity/version, rubric/dataset version, input/output, cost, latency, confidence, and provenance contracts;
- baseline/candidate comparison and score scale/aggregation rules;
- threshold, error, unavailable-evaluator, and partial-result semantics;
- repair budgets fixed to 0–2 for v0.1, with attempt/time/cost/regression limits;
- repair plan, mutation authority, provenance, stop conditions, unresolved-defect report, and regression-prevention contracts;
- explicit separation of candidate generation, judging, and human review contexts.

**Implementation deliverables:** Contract fixtures and deterministic evaluator prototypes only if separately authorized; no production closed loop.

**Validation gates**

- deterministic validators outrank model judges for schema, security, and executable correctness;
- failed repairs preserve evidence and cannot weaken objectives or safety constraints;
- identical inputs/configuration produce identical deterministic results;
- score aggregation cannot turn evaluator errors into passes;
- repair terminates at the declared budget and reports unresolved failures.

**Owner decisions:** Ratify evaluator authority, score/baseline semantics, repair budgets, and permissible repair mutation surface.

**Prohibited shortcuts:** No unbounded self-improvement, score-only success, silent baseline replacement, judge-as-sole-authority, or discarded failed-attempt evidence.

**Exit criteria:** Independent review and owner approval establish an executable evaluation/repair contract sufficient for a fake-adapter prototype.

**Downstream dependencies:** Phase 4 prototypes this contract; Phase 4B productionizes it; Phases 7 and 8 depend on the certified evidence model rather than the prototype alone.

## Phase 4 — Headless Closed-Loop Prototype

**Goal:** Prove one end-to-end, offline, deterministic loop from structured requirements through IR, fake lowering, evaluation, bounded repair, and evidence output.

**Entry criteria**

- Phases 2 and 3 contracts are accepted.
- MISSION-010 is authorized with exact fixtures and failure expectations.
- Certified Compiler Core v0.1 remains unchanged unless a separately approved compatibility decision permits extension.

**Normative deliverables**

- closed-loop orchestration contract and stable library/CLI result envelopes;
- end-to-end provenance and semantic-disposition requirements;
- explicit offline/no-network and deterministic execution profile.

**Implementation deliverables**

- minimal requirements-to-IR implementation for the accepted structured profile;
- deterministic evaluators and bounded repair using the fake adapter only;
- artifact/evidence bundle and library/CLI parity;
- adversarial and metamorphic end-to-end tests.

**Validation gates**

- failing tests precede behavior changes;
- zero network and zero credentials are enforced;
- repair limit 0, 1, and 2 paths terminate correctly;
- semantic mutations alter evidence/artifacts or fail explicitly;
- requirements, IR leaves, capability decisions, artifacts, evaluation results, repair attempts, and diagnostics form a complete trace;
- full regression, packaging, installed CLI, cross-platform CI, and independent architecture review pass.

**Owner decisions:** Accept the prototype only as bounded proof, authorize mandatory MISSION-011 hardening, and separately decide whether Phase 5 planning may begin from prototype evidence.

**Prohibited shortcuts:** No live adapters, credentials, hosted API, database, UI, benchmark claims, or silent contract amendments.

**Exit criteria:** The fake-adapter closed loop is reproducible and behaviorally proven within its declared prototype profile, with no unresolved correctness blocker. Exit does not certify the loop for production consumers.

**Downstream dependencies:** Supplies evidence to Phase 4B and may inform separately authorized Phase 5 planning. Live execution, benchmark construction or claims, and product APIs cannot enter from Phase 4 evidence alone.

## Phase 4B — Headless Core Hardening and Certification

**Goal:** Convert the MISSION-010 fake-adapter prototype and the MISSION-008/009 contract packages into stable, production-grade headless requirements, evaluation, bounded-repair, and evidence boundaries before downstream runtime or product investment.

**Entry criteria**

- Phases 2 and 3 contracts are accepted and the exact approved authoring profiles are identified.
- Phase 4 has produced independently reviewed prototype evidence without changing frozen Compiler Core v0.1.
- MISSION-011 is separately authorized from an exact verified baseline with explicit certification fixtures, platforms, performance/resource measures, and failure expectations.

**Normative deliverables**

- production requirements/evidence, evaluation, repair, orchestration, provenance, unresolved-defect, and result-envelope contracts;
- a stable library API and `promptrig-compiler` CLI contract with deep parity and versioned evidence bundles;
- deterministic validation around every model-assisted requirements stage, with no model output accepted directly as canonical meaning;
- a ratified headless implementation schedule for plain-language/model-assisted intent compilation so Simple Mode cannot become its first or only semantic implementation;
- operational, resource, security, packaging, compatibility, and consumer-support boundaries where meaningful;
- capability-promotion criteria tied to behavior-level certification rather than prototype completion or test counts.

**Implementation deliverables**

- production-grade requirements compiler behavior for every authoring profile approved for implementation by MISSION-008;
- production deterministic-first evaluation and bounded-repair engines implementing the MISSION-009 authority, budget, baseline, regression, failed-attempt, unresolved-defect, and provenance contracts;
- hardened offline orchestration, stable evidence bundles, and library/CLI surfaces suitable for external consumers;
- package build and clean-install proof, external-consumer smoke fixtures, cross-platform behavior, security/adversarial coverage, and bounded performance/resource evidence.

**Validation gates**

- requirement-to-IR-to-capability-to-artifact-to-evaluation-to-repair trace completeness, including terminal unresolved failures and every failed attempt;
- positive, negative, adversarial, metamorphic, ambiguity, injection, regression, and failure-path tests;
- model-assisted and plain-language outputs cannot bypass deterministic semantic validation or immutable diagnostics;
- repair budgets 0, 1, and 2 terminate correctly and cannot weaken accepted objectives, security constraints, or meaning;
- baseline identity, regression protection, failed-attempt evidence, unresolved-defect evidence, and provenance remain stable and reproducible;
- zero network and zero credentials remain the default and are enforced across library, CLI, package, and external-consumer paths;
- deterministic repeatability and stable library/CLI deep parity pass;
- package build, clean install, installed CLI, external-consumer smoke tests, and supported cross-platform CI pass;
- explicit performance/resource ceilings or measured bounds exist where meaningful;
- independent architecture and security review certify the boundary, and the owner explicitly approves promotion.

**Owner decisions:** Approve the production authoring profiles, plain-language/model-assisted headless schedule, stable API/CLI and evidence contracts, operational/resource limits, supported platforms, certification evidence, and promotion of the headless core for downstream reliance.

**Prohibited shortcuts:** No live provider execution, credentials, hosted API or UI, persistence, tenancy, fifth adapter, benchmark runner or public claim, MissionRig, Workspace integration, unauthorized IR v0.2 change, model-output trust, UI-owned requirements semantics, or promotion from green CI alone.

**Exit criteria:** Independent architectural and security certification plus explicit owner approval establish production-grade headless requirements, evaluation, repair, evidence, library, CLI, packaging, installed-consumer, and cross-platform boundaries with no unresolved correctness or security blocker.

**Downstream dependencies:** Phase 6 live execution, Phase 7 benchmark construction or claims, and Phase 8 product entry all require this exit. Phase 5 planning may begin earlier from Phase 4 evidence only when separately authorized, but IR implementation or downstream runtime reliance cannot bypass Phase 4B and separately ratified compatibility decisions.

## Phase 5 — IR v0.2 Planning and Migration Design

**Goal:** Use requirements and closed-loop evidence to plan, but not prematurely code, the next IR version.

**Entry criteria**

- Phase 4 evidence exists.
- Phase 5 planning may proceed before Phase 4B exits only under separate authorization; production IR implementation and downstream runtime reliance remain blocked by Phase 4B and ratified compatibility decisions.
- ADR-006 inputs and ADR-007 evidence are current.
- Requirements, evaluation, repair, server-tool, output-cardinality, and runtime-state needs are traceable to executable cases.

**Normative deliverables**

- IR v0.2 SPEC and semantic delta;
- ADR decisions for reasoning configuration, runtime/continuation state, provider-hosted tools, output cardinality, and evaluation/repair representation;
- compatibility promise, version negotiation, migration rules, downgrade/failure behavior, and deprecation policy;
- schema fixtures, generated-contract impact, library/CLI compatibility matrix, and phased rollout plan;
- threat model for opaque provider-returned state and replay.

**Implementation deliverables:** Migration prototypes and fixtures only when explicitly authorized; production schema/code changes occur in a later implementation mission after ratification.

**Validation gates**

- every new field has a provider-neutral semantic owner and at least one executable use case;
- no provider API shape becomes canonical by convenience;
- v0.1 inputs retain defined behavior;
- upgrade/downgrade, round-trip, invalid migration, and unknown-version cases pass;
- generated TypeScript and Python boundaries remain single-source.

**Owner decisions:** Accept, defer, or reject each IR change; decide ADR-007 status only after its evidence threshold; approve the migration and compatibility policy.

**Prohibited shortcuts:** No direct edits to frozen v0.1 contracts, no schema-first implementation without semantics, and no bundling unrelated debt cleanup.

**Exit criteria:** A ratified, independently reviewed IR evolution package exists with an authorized implementation sequence.

**Downstream dependencies:** Phase 6 uses the accepted runtime/configuration boundary; Phase 8 consumes the stable versioned contract.

## Phase 6 — Live Execution Permission Boundary

**Goal:** Define and prove a separate, auditable boundary that may execute provider requests without contaminating offline lowering or canonical semantics.

**Entry criteria**

- Phase 4B headless-core hardening and certification has exited with explicit owner approval; prototype evidence alone is insufficient.
- Relevant Phase 5 IR/runtime decisions are ratified.
- Current provider documentation and security assumptions are refreshed.

**Normative deliverables**

- execution request/result, provider-returned state, retry, timeout, cancellation, idempotency, partial-result, and audit-event contracts;
- network allowlist and egress policy;
- credential/BYOK lifecycle, vault, rotation, scoping, redaction, and incident rules;
- action-boundary permissions and human approval protocol;
- cost/token budgets and provider provenance requirements.

**Implementation deliverables**

- one minimal execution adapter behind explicit opt-in and test doubles;
- credential-free default profile;
- audit trail and cancellation/idempotency proof;
- no-network tests for all offline paths.

**Validation gates**

- threat model and secret scan;
- denied/unavailable/expired credentials fail closed;
- retries do not duplicate consequential actions;
- cancellation and partial results preserve evidence;
- offline compile behavior is byte-stable and remains the default;
- live tests are isolated, opt-in, budgeted, and never required for ordinary CI.

**Owner decisions:** Select first live provider, credential model, network policy, budgets, and approval boundary.

**Prohibited shortcuts:** No credentials in prompts, artifacts, fixtures, logs, or repository; no implicit live call; no retry without idempotency semantics.

**Exit criteria:** Independent security and architecture review plus owner approval confirm one bounded live path without weakening offline guarantees.

**Downstream dependencies:** Phase 7 may benchmark live configurations; Phase 8 may offer managed execution.

## Phase 7 — Reproducible Whole-Configuration Benchmark

**Goal:** Build and validate a sealed benchmark that measures complete agent configurations under comparable conditions.

**Entry criteria**

- Phase 4B has certified the production evaluation, bounded-repair, evidence, library/CLI, packaging, and consumer boundaries; the Phase 4 prototype alone is insufficient.
- Any live track uses the accepted Phase 6 boundary.
- Source snapshots, resource budgets, network modes, repetition policy, and scoring are frozen before competitors run.

**Normative deliverables**

- benchmark/version manifest, starter commit, environment/container digest, source snapshot hashes, secrets policy, permissions, budgets, run count, intervention policy, and contamination controls;
- scoring rubric with hard gates and evaluator authority;
- autonomous versus steered reporting contract;
- evidence and submission manifests with checksum/output/timestamp validation;
- marketing-claims policy.

**Implementation deliverables**

- executable runner, sealed environment, public tests, hidden-test interface, evidence sealer, and report generator;
- repeated-run automation and infrastructure-failure classification.

**Validation gates**

- at least three autonomous attempts unless a ratified budget says otherwise;
- equivalent starting state and isolation for every configuration;
- hidden tests remain inaccessible;
- manifests validate content, hashes, timestamps, environment, and outputs, not only JSON syntax;
- an independent dry run reproduces scores and evidence.

**Owner decisions:** Freeze competitors/configurations, resource budgets, network tracks, public claims, release timing, and cost ceiling.

**Prohibited shortcuts:** No model-only labels, incomparable runs, cherry-picked success, post-hoc scoring changes, undisclosed interventions, or claims from non-executable plans.

**Exit criteria:** Independent benchmark review finds no fairness/reproducibility blocker and the owner authorizes any publication.

**Downstream dependencies:** Phase 8 uses validated evidence surfaces; Phase 9 may use benchmark operations.

## Phase 8 — Product Vertical Slice

**Goal:** Deliver one narrow hosted/user-facing slice in which Simple Mode and Developer Mode operate on the same canonical project and headless compiler.

**Entry criteria**

- Phase 4B has certified the headless requirements, evaluation, bounded-repair, evidence, library, and CLI boundaries; Simple Mode and Developer Mode consume those boundaries and cannot become their first production implementation.
- Platform, persistence, identity, tenancy, storage, retention, deletion, and secrets decisions are ratified.
- FastAPI, Next.js, and Supabase/alternatives are reevaluated with current evidence.

**Normative deliverables**

- one canonical project model and mode-parity contract;
- transport/OpenAPI and generated-contract boundary;
- authentication/authorization, tenancy, persistence, retention/deletion, audit, and incident contracts;
- accessibility, consent, uncertainty, cost, latency, provenance, and unresolved-defect presentation requirements.

**Implementation deliverables**

- minimal FastAPI or owner-selected transport;
- minimal Next.js or owner-selected UI;
- one Simple Mode intent-to-evidence workflow;
- reversible Developer Mode view of the same project;
- export and deletion paths;
- production-like threat, accessibility, and recovery tests.

**Validation gates**

- no hidden UI semantics;
- library, CLI, API, Simple Mode, and Developer Mode agree on canonical behavior;
- cross-tenant and authorization adversarial tests pass;
- secrets never enter canonical artifacts;
- accessibility and nontechnical usability evidence exists;
- backup/recovery, retention, deletion, and export behavior is proven.

**Owner decisions:** Ratify stack, platform, hosting, identity, tenancy, storage, and commercial boundary; approve closed-alpha scope.

**Prohibited shortcuts:** No broad feature catalog, billing-first design, platform lock-in without portability analysis, duplicated TypeScript compiler logic, or UI-only configuration.

**Exit criteria:** One complete vertical slice is independently reviewed, security-gated, usable, exportable, and owner-approved.

**Downstream dependencies:** Phase 9 builds on stable consumer and orchestration boundaries.

## Phase 9 — MissionRig and Workspace Expansion

**Goal:** Add downstream mission generation and engineering-workspace orchestration without transferring PromptRig semantic ownership.

**Entry criteria**

- PromptRig can compile, evaluate, repair, benchmark, and expose a stable product boundary.
- MissionRig and Workspace SPECs define ownership, versioning, portability, and failure isolation.

**Normative deliverables**

- canonical specification-to-mission contract;
- versioned mission schema, renderer, agent-profile boundary, and mission-report contract;
- workspace project/repository/template/orchestration consumer contract;
- compatibility and provenance rules back to PromptRig artifacts.

**Implementation deliverables**

- minimal MissionRig generator for one accepted specification profile;
- one Workspace integration that consumes versioned PromptRig outputs;
- conformance, portability, and failure-isolation tests.

**Validation gates**

- generated missions preserve objectives, inputs, permissions, stop conditions, acceptance gates, and evidence requirements;
- downstream systems cannot mutate canonical PromptRig semantics;
- agent-specific rendering is deterministic and traceable;
- failure in MissionRig/Workspace cannot corrupt PromptRig projects or evidence.

**Owner decisions:** Ratify product boundaries, release/commercial model, supported agents, and expansion sequence.

**Prohibited shortcuts:** No mission generation from unaccepted chat state, no hidden workspace authority, and no coupling canonical IR to one coding agent.

**Exit criteria:** Downstream products operate through versioned contracts and pass independent architecture/product review.

**Downstream dependencies:** Later roadmap versions may add integrations only through the same governance.

## Critical path

```text
Phase 1
→ Phase 2
→ Phase 3
→ Phase 4
→ Phase 4B
→ Phase 5
→ Phase 6
→ Phase 7
→ Phase 8
→ Phase 9
```

The dependency is semantic, not merely chronological. Requirements identity feeds evaluation evidence; both feed the prototype; Phase 4B converts the prototype into a certified production headless core; stable headless and IR/runtime boundaries precede live execution; certified executable behavior precedes benchmark construction or claims; hardened headless requirements/evaluation/repair precede product UI; and PromptRig product capability precedes MissionRig/Workspace expansion. Separately authorized Phase 5 planning may overlap Phase 4B using prototype evidence, but production IR implementation or downstream runtime reliance cannot bypass either Phase 4B or ratified compatibility decisions.

## Safe parallel work

The following may proceed in parallel after Phase 1 only when a mission explicitly authorizes it and no accepted contract is changed:

- representative requirements authoring cases and evaluation fixture collection;
- provider documentation refresh and capability-evidence capture;
- benchmark methodology research without runner implementation or public claims;
- product usability/accessibility research without broad UI coding;
- hosted platform/security option analysis without selecting or provisioning infrastructure;
- bounded technical-debt evidence collection without cleanup changes.

Contract decisions and production implementation remain dependency-ordered. Parallel research cannot silently become architecture.

## Roadmap drift control

Every future mission must identify its roadmap phase, entry criteria, exact authorization, prohibited shortcuts, requirement/test/evidence links, and owner gate. A mission that changes phase order, product laws, capability status, or a deferred/rejected disposition must update this roadmap, the maturity map, traceability file, strategy index, and decision log in one reviewable change.
