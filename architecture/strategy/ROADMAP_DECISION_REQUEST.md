# Roadmap Decision Record

**Status:** `DECIDED`. After final independent architectural review, the owner explicitly approved DR-007-01 through DR-007-09 exactly as recommended in PR #12. The strategy package becomes authoritative upon merge into `feature/promptrig-framework`; no phase, mission, or implementation is authorized by this decision.
**Decision package:** MISSION-007 strategy documents at baseline `b3b6f6cd46300e846e38f6601acb6a9d0b68cafb` plus this mission's documentation-only commits.

## Decision standard

The recorded approval adopts governance and dependency order upon merge. It does not merge this PR, authorize execution of MISSION-008 through MISSION-011, approve later phase entry, change frozen contracts, accept ADR-007, select a hosted platform, or authorize live execution.

## Decisions recorded

### DR-007-01 — Accept the reconciled product vision

**Decision:** Approved exactly as recommended.

**Recommended answer:** Accept [PROMPTRIG_PRODUCT_VISION.md](PROMPTRIG_PRODUCT_VISION.md). PromptRig is a provider-neutral AI systems compiler whose durable center is PromptRig IR and whose complete loop runs from user intent through evaluation, bounded repair, artifacts, and evidence.

**Alternative:** Retain the current fragmented source set without one repository-native statement.

**Consequence of alternative:** Future missions must reconstruct authority from stale README text, historical v0.4 plans, freeze records, reports, and code; local optimization and contradictory claims remain likely.

### DR-007-02 — Adopt Roadmap V1 as authoritative sequencing

**Decision:** Approved exactly as recommended.

**Recommended answer:** Adopt [ROADMAP_V1.md](ROADMAP_V1.md), including its phase entry/exit gates, critical path, safe parallel work, and deferrals.

**Alternative:** Treat the roadmap as advisory or resume provider/runtime/UI work opportunistically.

**Consequence of alternative:** The middle of the pipeline will continue to deepen while the requirements and evaluation/repair stages remain absent; platform decisions may precede semantic stability.

### DR-007-03 — Approve the MISSION-008 through MISSION-011 sequence

**Decision:** Approved exactly as recommended.

**Recommended answer:** Approve the sequence in [MISSION_SEQUENCE_V1.md](MISSION_SEQUENCE_V1.md): requirements/evidence contract, evaluation/bounded-repair contract, fake-adapter headless closed-loop prototype, then mandatory headless-core hardening and certification.

**Alternative:** Combine contracts and implementation into one mission or reorder the sequence.

**Consequence of alternative:** Ambiguous semantics become implementation defaults, evaluation identities cannot trace to accepted requirements, or prototype-grade requirements/evaluation/repair become accidental production infrastructure that is expensive to unwind.

### DR-007-04 — Retain PromptRig IR as the product center

**Decision:** Approved exactly as recommended.

**Recommended answer:** Confirm that source languages, providers, UI, API, storage, execution, MissionRig, and Workspace integrations remain replaceable boundaries around versioned IR.

**Alternative:** Let PRS, a provider payload, a hosted project model, or UI state become co-equal semantic truth.

**Consequence of alternative:** Portability, headless parity, migration, and semantic-retention guarantees become structurally unreliable.

### DR-007-05 — Prohibit new provider adapters until the headless core is certified

**Decision:** Approved exactly as recommended.

**Recommended answer:** Approve DFR-001. No fifth adapter before mandatory Roadmap Phase 4B certifies the headless core and new provider evidence materially informs canonical design.

**Alternative:** Add Mistral or another adapter next.

**Consequence of alternative:** More offline lowering coverage is gained, but the product still cannot compile intent, evaluate behavior, or repair bounded failures.

### DR-007-06 — Keep live execution and hosted-product work deferred

**Decision:** Approved exactly as recommended.

**Recommended answer:** Defer live calls, credentials, benchmark construction or claims, persistence, tenancy, FastAPI, Next.js, billing, and broad UI until Phase 4B headless-core certification and their later roadmap entry gates.

**Alternative:** Start a thin hosted or live integration before the headless loop.

**Consequence of alternative:** Security, state, retry, cost, tenancy, and UI decisions may become accidental semantic owners and create rework.

### DR-007-07 — Keep ADR-007 Proposed pending an executable evidence threshold

**Decision:** Approved exactly as recommended; ADR-007 remains Proposed.

**Recommended answer:** Do not accept or reject the IR gap shape yet. Keep ADR-007 Proposed until all threshold items exist:

1. at least two executable cross-turn use cases, including one closed-loop evaluation/repair or tool-continuation case, demonstrate that opaque provider-returned state must survive across requests;
2. evidence spans at least two provider mechanisms or one provider plus a provider-neutral compiler use case;
3. a provider-neutral semantic boundary distinguishes canonical session/turn meaning from opaque provider continuation data;
4. replay, confidentiality, integrity, storage, retention/deletion, cancellation, and idempotency threats are specified;
5. v0.1 compatibility, migration, downgrade/failure behavior, fixtures, and generated-contract impact are defined;
6. independent architectural/security review finds the evidence sufficient for an owner decision.

**Alternative A:** Accept now that the gap exists, without choosing a shape.

**Consequence:** This acknowledges multi-provider documentation evidence sooner but may create pressure to design state before executable closed-loop needs are known.

**Alternative B:** Reject the gap.

**Consequence:** Current provider continuation evidence must remain adapter-only and any future multi-turn mission would likely stop immediately.

### DR-007-08 — Require contract-first IR v0.2 work

**Decision:** Approved exactly as recommended.

**Recommended answer:** Phase 5 planning may use MISSION-010 prototype evidence only when separately authorized. No IR v0.2 production schema, code, or downstream runtime reliance may proceed until Phase 5 produces a SPEC, ADR decisions, semantic delta, compatibility/migration plan, fixtures, generated-contract impact, independent review, and owner ratification, and the relevant dependency also respects Phase 4B certification.

**Alternative:** Add fields incrementally when adapters or product work encounter gaps.

**Consequence of alternative:** Provider-shaped accretion can turn IR into an unstable union of APIs and break v0.1 compatibility.

### DR-007-09 — Require headless-core hardening and certification before downstream reliance

**Decision:** Approved exactly as recommended.

**Recommended answer:** Approve Roadmap Phase 4B and MISSION-011 as a mandatory gate. Productionize and certify the approved requirements compiler profiles, deterministic-first evaluation, bounded repair, evidence envelopes, library/CLI parity, packaging, installed-consumer behavior, cross-platform behavior, security/adversarial resistance, and meaningful performance/resource limits before live execution, benchmark construction or claims, or Product Vertical Slice entry. Require an explicit headless implementation schedule for plain-language/model-assisted intent compilation so UI is never its first or only semantic implementation.

**Alternative:** Allow MISSION-010 prototype evidence to satisfy downstream entry or let the Product Vertical Slice productionize missing headless semantics.

**Consequence of alternative:** Live, benchmark, and hosted-product investments would depend on a fake-adapter prototype that explicitly excludes production hardening; Simple Mode could become the accidental semantic owner of requirements compilation.

## Decision matrix

| Decision | Recorded owner decision | Expensive or irreversible aspect |
|---|---|---|
| DR-007-01 | Approved: Accept | Reversing product identity later would invalidate contracts, positioning, and downstream systems |
| DR-007-02 | Approved: Adopt | Phase order shapes investment, but roadmap versions remain changeable through governance |
| DR-007-03 | Approved: Approve sequence | Combining/reordering later would invalidate traceability and contract assumptions |
| DR-007-04 | Approved: Confirm | Moving the semantic center later would create a large migration and portability break |
| DR-007-05 | Approved: Approve prohibition | Low irreversibility; adapter work is delayed, not discarded |
| DR-007-06 | Approved: Approve deferral | Low irreversibility; premature platform/credential commitments are the expensive alternative |
| DR-007-07 | Approved: Keep Proposed | Accepting a state model too early creates security and migration cost |
| DR-007-08 | Approved: Require contract first | IR public-version mistakes are expensive to migrate and support |
| DR-007-09 | Approved: Require Phase 4B/MISSION-011 | Skipping certification lets prototype boundaries harden accidentally inside runtime, benchmark, or UI work |

## What remains deferred after approval

Approval still does not authorize:

- MISSION-008 execution without a separate exact-baseline launch;
- MISSION-009, MISSION-010, or MISSION-011 execution without its own separate exact-baseline launch and accepted dependencies;
- any production requirements compiler, PRS parser, evaluator, or repair engine;
- IR v0.2 schema or implementation;
- runtime/session state or ADR-007 acceptance;
- fifth provider adapter;
- live calls, credentials, network permissions, provider execution, or hosted jobs;
- FastAPI, Next.js, persistence, Supabase or another platform, tenancy, billing, or managed credits;
- benchmark runner, comparative claims, or publication;
- MissionRig or AI Engineering Workspace integration;
- merge, auto-merge, tag movement, or release.

## Decision record

The owner explicitly approved DR-007-01 through DR-007-09 exactly as recommended in PR #12 and authorized the PR to proceed to merge review. The approval is limited to strategy and sequencing governance. It does not authorize MISSION-008 through MISSION-011, phase entry, implementation, merge automation, release, or tag movement.
