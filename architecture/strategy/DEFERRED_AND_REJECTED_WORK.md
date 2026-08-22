# Deferred and Rejected Work

**Status:** Owner-ratified through DR-007-01 through DR-007-09 in PR #12; authoritative as a sequencing guardrail upon merge into `feature/promptrig-framework`. Ratification activates no deferred work and authorizes no implementation.

## Registry rules

`DEFERRED` means strategically valid but blocked by explicit dependencies. `REJECTED` means the described interpretation or shortcut must not be pursued; it does not permanently ban a technology reconsidered under a new evidence-backed decision. `OBSOLETE` means a statement remains preserved as history but cannot direct current work.

## Deferred work registry

| ID | Work | Disposition | Why it is not active | Promotion trigger | Earliest roadmap phase |
|---|---|---|---|---|---|
| DFR-001 | Fifth provider adapter | `DEFERRED` | Adapter breadth would optimize the already-strong middle of the pipeline while intent, evaluation, and repair remain missing | Phase 4B certifies the headless core; a provider adds distinct evidence that affects canonical design; owner authorizes scope | Phase 5 or later, after Phase 4B |
| DFR-002 | Broad UI work | `DEFERRED` | A UI before stable headless behavior risks hidden semantics and duplicated state | Phase 4B certifies headless requirements/evaluation/repair and Phases 5–7 provide any additional required APIs/evidence; one shared project model and accessibility gates are ratified | Phase 8 |
| DFR-003 | Live provider calls | `DEFERRED` | Lowering is certified offline; execution introduces network, cost, provider-returned state, partial failure, and side effects | Phase 4B certifies the production headless loop and Phase 6 permission/execution contract is accepted | Phase 6 |
| DFR-004 | Credential integration and BYOK | `DEFERRED` | No secret lifecycle, scope, redaction, audit, or incident contract exists | Accepted threat model, vault/rotation contract, action-boundary approvals, and live-execution design | Phase 6 |
| DFR-005 | Billing and managed credits | `DEFERRED` | Commercial accounting cannot precede stable execution, identity, budgets, and tenancy | Hosted vertical slice proves metering and owner approves commercial boundary | After Phase 8 |
| DFR-006 | Hosted multi-tenancy | `DEFERRED` | Tenant authorization, isolation, retention, deletion, and incident semantics are unresolved | Phase 8 SPEC, threat model, migration plan, adversarial isolation tests, and owner platform decision | Phase 8 |
| DFR-007 | Persistence and background jobs | `DEFERRED` | Current sinks are local outputs, not durable product state; no job/idempotency contract exists | Phase 4B-certified headless core plus project, job, cancellation, retention, and recovery contracts | Phase 8 |
| DFR-008 | MissionRig implementation | `DEFERRED` | Mission generation is downstream of reliable canonical compilation and evidence | PromptRig completes Phases 2–8 and MissionRig receives a separate ratified SPEC | Phase 9 |
| DFR-009 | AI Engineering Workspace integration | `DEFERRED` | Workspace orchestration must consume, not shape, compiler semantics | Stable compiler/product APIs and a versioned consumer-boundary contract | Phase 9 |
| DFR-010 | Marketplace, mobile, enterprise control plane, arbitrary plugins | `DEFERRED` | These are expansion surfaces without critical-path value | Product vertical slice, security posture, demand evidence, and separate owner scope | After Phase 9 |

## Rejected shortcuts and interpretations

| ID | Rejected item | Reason | Reconsideration condition |
|---|---|---|---|
| REJ-001 | Inherited Supabase commitment | The v0.4 Supabase ADR was provisional and the current freeze explicitly excludes hosted-platform architecture | Supabase may compete with portable Postgres-first alternatives in a Phase 8 platform/security ADR |
| REJ-002 | Cosmetic repository redesign as roadmap work | Renaming, reorganizing, or restyling does not complete the canonical pipeline and risks historical damage | Only bounded changes required by an approved deliverable, migration, accessibility, or maintainability gate |
| REJ-003 | Unbounded technical-debt cleanup | It obscures authorization and can silently rewrite accepted behavior | Each item must be tied to a phase gate, correctness defect, measurable maintenance risk, or accepted ADR |
| REJ-004 | Premature IR v0.2 coding | Reasoning, server-tool, multi-turn, output-cardinality, evaluation, and repair needs lack one ratified migration design | Phase 5 SPEC, ADRs, compatibility/migration plan, fixtures, generated-contract impact, and owner approval |
| REJ-005 | Benchmark claims without executable evidence | Historical benchmark prose, test counts, or green CI do not establish fair, repeatable comparative results | Phase 7 sealed runner, manifests, repeated autonomous runs, independent verification, and claims review |
| REJ-006 | Adapter count as product progress | A fifth lowerer would deepen local optimization while the beginning and end of the compiler loop remain absent | Same promotion trigger as DFR-001 |
| REJ-007 | UI-owned canonical configuration | Hidden UI state violates IR ownership and breaks headless parity | No reconsideration; UI state may only be presentation state or versioned runtime metadata outside canonical semantics |
| REJ-008 | Provider-native payload as complete semantic artifact | MISSION-006 proved provider payloads alone cannot retain all canonical meaning | No reconsideration without a versioned contract that still preserves or rejects every semantic leaf |
| REJ-009 | PRS examples as an executable grammar | Current PRS files are explicitly non-binding and omit core language rules | A ratified PRS grammar, parser contract, source mapping, diagnostics, fixtures, and compatibility policy |

## Obsolete or superseded assumptions

These sources remain preserved. The classification changes their authority, not their bytes.

| Source or assumption | Classification | Current treatment |
|---|---|---|
| Root `README.md` statements that PromptRig has no provider adapters, is Python 3.10+, and should next add richer eval fixtures | `CONTRADICTORY` | Superseded for strategic status by this package and actual package/code evidence; README correction is a separate future documentation task |
| `architecture/README.md` and freeze-package README calling v0.5 a candidate with implementation unauthorized | `CURRENT_BUT_INCOMPLETE` | OAR-001, merged PR #2, and the immutable tag establish the accepted v0.1 freeze; contract contents remain authoritative |
| v0.4 `PROMPTRIG_MASTER_SCOPE.md` claim that version 0.2.0 is canonical and benchmark-ready | `SUPERSEDED` | OAR-001 makes IR 0.1.0 the first frozen public contract; benchmark readiness requires Phase 7 evidence |
| v0.4 roadmap Phase A “Complete” and immediate executable benchmark/build-off sequence | `SUPERSEDED` | Replaced by dependency-ordered `ROADMAP_V1.md` after approval |
| v0.4 Mistral MVP adapter and “full provider catalog beyond first four” language | `HISTORICAL_EVIDENCE_ONLY` | Current ratified initial set is fake, OpenAI, Anthropic, Gemini; any fifth provider is DFR-001 |
| v0.4 Next.js/FastAPI acceptance | `CURRENT_BUT_INCOMPLETE` | Retained as proposed target direction, not a frozen or implemented hosted architecture; re-ratify in Phase 8 |
| v0.4 Supabase MVP decision | `SUPERSEDED` | Automatic inheritance is REJ-001; platform selection is reopened |
| MISSION-002 through MISSION-006 reports saying their PR is open or draft | `HISTORICAL_EVIDENCE_ONLY` | Accurate at report time; GitHub PR metadata and merge commits are current authority |
| Current Vite dashboard and legacy interactive artifact as Simple/Developer modes | `REJECTED_INTERPRETATION` | They are prototypes/legacy surfaces and do not operate on the canonical shared project/IR |

## Technical-debt classification

### Correctness-critical

No known unresolved correctness-critical defect is accepted at the MISSION-007 baseline. Any future failure in RFC 8785 canonicalization, immutable diagnostics, input non-mutation, semantic retention/rejection, provenance, deployability agreement, or required-capability fail-closed behavior immediately blocks the affected phase and must use a recovery mission.

### Blocking

- MISSION-017 added file/api envelope producers for canonical assembly (`produce_requirements`, `compile_requirements_input`); MISSION-018 added simple/developer envelope producers; remaining unauthorized: prs/prose producers; OQs open; no full 008 compiler; no M3.
- OAR-006 certified the narrow offline deterministic compile/security evaluator and bounded instruction-append repair (budgets `{0,1,2}`, `EVR-SEC-0001`). Still unauthorized: full rubric/dataset engine, baseline comparison product, scoring aggregation, and production regression gate.
- OAR-006 accepted a narrow offline structured+fake headless boundary (fake adapter only, no network). OAR-007 Accepted 2026-08-14 certifies MISSION-013 M1 constrained prose intake (`plain_language_v0`). OAR-008 Accepted 2026-08-14 certifies MISSION-014 offline fake `fake-suggester-v0` M2 sidecar; proposals are sidecar evidence only and are not mapped to IR. MISSION-015 residual evidence (OAR-009 Ready for owner acceptance) adds PEP 517 clean-install, installed-package consumer matrix, and operational resource ceilings for the fake path — not a benchmark. MISSION-016 (OAR-010 Accepted 2026-08-21) lifted the 008 rule engine into production for canonical records only. Still unauthorized: live model-assisted suggestion, freeform NLP, live M2, M3 / Simple Mode UI, no full 008 authoring-envelope production compiler; OQs open; full Roadmap Phase 4B exit; do not claim production-hardened full Phase 4B engines.
- ADR-007 remains Proposed; runtime state, replay, security, retention, and migration semantics are unresolved.
- Provider schema-subset checkers are intentionally bounded and cannot support live-execution claims without refreshed authoritative provider evidence and failure semantics.
- IR v0.1 has no machine-readable security/privacy policy grammar and fails closed on populated free-text policy blocks.
- Hosted jobs, identity, tenancy, secrets, storage, retention, deletion, and incident behavior lack contracts.

### Bounded cleanup

- Compiler CLI diagnostic-to-exit-code mapping is manually maintained.
- IR validation reports the first schema error rather than a complete set.
- `doctor()` checks only a narrow environment subset.
- The TypeScript generator supports only current schema constructs.
- Provider schema checkers do not fully classify supported, rejected, or silently unenforced keywords.
- Root and architecture index wording is stale; this strategy package supersedes status claims without rewriting those historical/current documents in MISSION-007.

These items may be scheduled only when a named phase touches the boundary or when a regression proves them blocking.

### Cosmetic

- dashboard restyling;
- repository-wide renaming or reorganization;
- historical duplicate cleanup;
- changing the unusual integration-branch name;
- documentation polish that does not resolve authority, traceability, safety, or correctness.

Cosmetic work is not on the critical path.

### Accepted limitations

- Compiler Core v0.1 uses a separate `promptrig-compiler` entry point.
- Optimization is a traced no-op in v0.1.
- One output contract per request is enforced in v0.1; composite output lowering requires later design.
- Semantic context is a PromptRig sidecar and does not claim every provider natively executes every IR field.
- OpenAI, Anthropic, and Gemini adapters are deterministic offline lowerers only.
- Generated TypeScript contracts are consumer boundaries, not duplicated semantics.

## Promotion controls

Deferred work becomes active only when its trigger is recorded in an accepted mission or ADR, dependencies are evidenced rather than asserted, the maturity map and traceability file are updated in the same change, and the owner authorizes the scope. A user request, prototype, provider announcement, or passing test count alone does not promote work.
