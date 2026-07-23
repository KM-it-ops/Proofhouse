# Roadmap Decision Request

**Status:** Pending independent architectural review and explicit owner decision.
**Decision package:** MISSION-007 strategy documents at baseline `b3b6f6cd46300e846e38f6601acb6a9d0b68cafb` plus this mission's documentation-only commits.

## Decision standard

Approval adopts governance and dependency order. It does not merge this PR, authorize MISSION-008 implementation, approve later phase entry, change frozen contracts, accept ADR-007, select a hosted platform, or authorize live execution.

## Requested decisions

### DR-007-01 — Accept the reconciled product vision

**Recommended answer:** Accept [PROMPTRIG_PRODUCT_VISION.md](PROMPTRIG_PRODUCT_VISION.md). PromptRig is a provider-neutral AI systems compiler whose durable center is PromptRig IR and whose complete loop runs from user intent through evaluation, bounded repair, artifacts, and evidence.

**Alternative:** Retain the current fragmented source set without one repository-native statement.

**Consequence of alternative:** Future missions must reconstruct authority from stale README text, historical v0.4 plans, freeze records, reports, and code; local optimization and contradictory claims remain likely.

### DR-007-02 — Adopt Roadmap V1 as authoritative sequencing

**Recommended answer:** Adopt [ROADMAP_V1.md](ROADMAP_V1.md), including its phase entry/exit gates, critical path, safe parallel work, and deferrals.

**Alternative:** Treat the roadmap as advisory or resume provider/runtime/UI work opportunistically.

**Consequence of alternative:** The middle of the pipeline will continue to deepen while the requirements and evaluation/repair stages remain absent; platform decisions may precede semantic stability.

### DR-007-03 — Approve the MISSION-008 through MISSION-010 sequence

**Recommended answer:** Approve the sequence in [MISSION_SEQUENCE_V1.md](MISSION_SEQUENCE_V1.md): requirements/evidence contract, evaluation/bounded-repair contract, then fake-adapter headless closed-loop prototype.

**Alternative:** Combine contracts and implementation into one mission or reorder the sequence.

**Consequence of alternative:** Ambiguous semantics become implementation defaults, evaluation identities cannot trace to accepted requirements, and closed-loop code becomes expensive to unwind.

### DR-007-04 — Retain PromptRig IR as the product center

**Recommended answer:** Confirm that source languages, providers, UI, API, storage, execution, MissionRig, and Workspace integrations remain replaceable boundaries around versioned IR.

**Alternative:** Let PRS, a provider payload, a hosted project model, or UI state become co-equal semantic truth.

**Consequence of alternative:** Portability, headless parity, migration, and semantic-retention guarantees become structurally unreliable.

### DR-007-05 — Prohibit new provider adapters until the closed loop exists

**Recommended answer:** Approve DFR-001. No fifth adapter before Roadmap Phase 4 exits and new provider evidence materially informs canonical design.

**Alternative:** Add Mistral or another adapter next.

**Consequence of alternative:** More offline lowering coverage is gained, but the product still cannot compile intent, evaluate behavior, or repair bounded failures.

### DR-007-06 — Keep live execution and hosted-product work deferred

**Recommended answer:** Defer live calls, credentials, persistence, tenancy, FastAPI, Next.js, billing, and broad UI until their roadmap entry gates.

**Alternative:** Start a thin hosted or live integration before the headless loop.

**Consequence of alternative:** Security, state, retry, cost, tenancy, and UI decisions may become accidental semantic owners and create rework.

### DR-007-07 — Keep ADR-007 Proposed pending an executable evidence threshold

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

**Recommended answer:** No IR v0.2 production schema or code until Phase 5 produces a SPEC, ADR decisions, semantic delta, compatibility/migration plan, fixtures, generated-contract impact, independent review, and owner ratification.

**Alternative:** Add fields incrementally when adapters or product work encounter gaps.

**Consequence of alternative:** Provider-shaped accretion can turn IR into an unstable union of APIs and break v0.1 compatibility.

## Decision matrix

| Decision | Recommended owner response | Expensive or irreversible aspect |
|---|---|---|
| DR-007-01 | Accept | Reversing product identity later would invalidate contracts, positioning, and downstream systems |
| DR-007-02 | Adopt | Phase order shapes investment, but roadmap versions remain changeable through governance |
| DR-007-03 | Approve sequence | Combining/reordering later would invalidate traceability and contract assumptions |
| DR-007-04 | Confirm | Moving the semantic center later would create a large migration and portability break |
| DR-007-05 | Approve prohibition | Low irreversibility; adapter work is delayed, not discarded |
| DR-007-06 | Approve deferral | Low irreversibility; premature platform/credential commitments are the expensive alternative |
| DR-007-07 | Keep Proposed | Accepting a state model too early creates security and migration cost |
| DR-007-08 | Require contract first | IR public-version mistakes are expensive to migrate and support |

## What remains deferred after approval

Approval still does not authorize:

- MISSION-008 execution without a separate exact-baseline launch;
- any production requirements compiler, PRS parser, evaluator, or repair engine;
- IR v0.2 schema or implementation;
- runtime/session state or ADR-007 acceptance;
- fifth provider adapter;
- live calls, credentials, network permissions, provider execution, or hosted jobs;
- FastAPI, Next.js, persistence, Supabase or another platform, tenancy, billing, or managed credits;
- benchmark runner, comparative claims, or publication;
- MissionRig or AI Engineering Workspace integration;
- merge, auto-merge, tag movement, or release.

## Requested response form

The owner should explicitly record accept, reject, or revise for DR-007-01 through DR-007-08. Silence, PR review activity, CI success, or merge preparation does not constitute acceptance.
