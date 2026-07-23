# PromptRig Product Vision

**Status:** Owner-ratified through DR-007-01 through DR-007-09 in PR #12; authoritative upon merge into `feature/promptrig-framework`. Ratification governs strategy only and authorizes no phase, mission, or implementation.
**Baseline:** `feature/promptrig-framework` at `b3b6f6cd46300e846e38f6601acb6a9d0b68cafb`.

## Product identity

PromptRig is a provider-neutral AI systems compiler. It converts user intent into a versioned, validated, provider-aware system specification; lowers that specification without losing canonical meaning; evaluates the resulting behavior; applies bounded repair when authorized; and emits reproducible artifacts, diagnostics, provenance, and evidence.

PromptRig is not a prompt-template collection, a provider SDK wrapper, a hosted dashboard with hidden semantics, or a benchmark that ranks model labels in isolation.

## Canonical pipeline

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

Every stage must either preserve the accepted meaning or fail explicitly. Validation precedes lowering. Evaluation and repair are compiler stages, not optional presentation features.

## Durable semantic center

PromptRig IR is the durable product center and the canonical semantic contract. Source languages, provider APIs, user interfaces, transports, storage systems, and execution services are replaceable boundaries around it.

The following laws are normative:

1. Providers and adapters are replaceable.
2. Canonical semantics cannot depend on a single provider API shape.
3. Lowering cannot mutate or silently discard canonical meaning.
4. Diagnostics, provenance, evidence, and reproducibility are first-class outputs.
5. Architecture changes require versioning, compatibility analysis, evidence, independent review, and owner ratification.
6. Hosted infrastructure and user interfaces wrap the compiler and never become the semantic owner.

## System boundaries

### PromptRig owns

- plain-language and structured requirements compilation;
- PRS only if a future contract authorizes it as one source language;
- PromptRig IR, validation, deterministic passes, capability and policy resolution;
- provider lowering and provider capability evidence;
- evaluation, baseline comparison, bounded repair, and regression evidence;
- canonical diagnostics, provenance, artifacts, and export packages;
- a shared headless library and CLI used by every product surface.

### PromptRig does not own

- provider-hosted semantic truth or provider-specific state as the canonical model;
- architecture-governance authority;
- repository/project orchestration unrelated to compilation;
- implementation-mission generation;
- hidden UI-only configuration;
- unbounded autonomous execution or repair.

## Ownership boundaries

| System | Ownership | Boundary condition |
|---|---|---|
| PromptRig | Intent-to-artifact compile, evaluate, repair, and evidence loop | Owns canonical semantics and compiler behavior |
| Architect Mode | Governance method, ADRs, OARs, SPECs, RFCs, mission construction, review discipline | May govern PromptRig but does not implement or own compiler semantics |
| AI Engineering Workspace | Future project, repository, template, orchestration, documentation, and benchmark operations | Consumes PromptRig outputs; cannot redefine IR or compiler contracts |
| MissionRig | Future generation of versioned, agent-specific implementation missions from accepted specifications | Remains downstream of a functioning PromptRig closed loop |

## Product modes

Simple Mode and Developer Mode are two views of one canonical project, not separate products or duplicated state.

### Simple Mode

Simple Mode is the default future interface. It captures desired outcomes in ordinary language, exposes assumptions and consequential approvals, and explains recommendations without requiring compiler vocabulary.

### Developer Mode

Developer Mode is a reversible future view of the same project. It exposes requirements, PRS when authorized, IR, provider configuration, prompts, schemas, tools, traces, diagnostics, latency, cost, evaluation evidence, repair history, and exported artifacts.

Neither mode is implemented by the current experimental Vite dashboard or the legacy PromptOps artifact. A mode is complete only when it operates on the shared canonical project/IR and passes behavioral and accessibility gates.

## Headless-first doctrine

The authoritative compiler must be production-hardened, independently certified, and usable through the Python library and `promptrig-compiler` CLI before live execution, benchmarking, a hosted transport, or a user interface is allowed to rely on the capability. Plain-language/model-assisted requirements compilation must have a headless implementation path with deterministic validation; Simple Mode cannot become its first or only semantic implementation. FastAPI, Next.js, persistence, and tenancy are later wrappers. They may orchestrate the compiler but may not duplicate its semantics.

## Provider-neutrality doctrine

A provider adapter consumes validated IR plus a versioned capability manifest and produces provider-shaped artifacts, diagnostics, omissions, and provenance. Provider-native limits are explicit. Unsupported required meaning fails closed; optional omissions remain machine-readable and affect deployability as defined by contract. No adapter may introduce credentials, live calls, or provider-owned state into the offline lowering boundary.

A fifth provider adapter is prohibited until the headless compile/evaluate/repair loop is production-hardened and certified after the fake-adapter prototype. The current four conformance targets are fake, OpenAI, Anthropic, and Gemini.

## Benchmark doctrine

PromptRig benchmarks the complete agent configuration: model, harness, instructions, tools, permissions, environment, routing, network policy, budgets, retries, interventions, and outputs. Autonomous and steered runs remain separate. Public claims require sealed executable evidence, repeated runs, reproducible environments, disclosed limitations, and traceable scoring. A plan, schema, or green CI run alone is not benchmark evidence.

## Hosted-product doctrine

The hosted product is a later delivery surface around the headless compiler. FastAPI and Next.js remain proposed target technologies, subject to phase entry evidence and owner approval. Persistence, authentication, tenancy, secrets, storage, retention, deletion, background jobs, billing, and managed credits require explicit security and platform contracts before implementation.

Supabase is not an inherited commitment. It may be reconsidered alongside portable Postgres-first alternatives during the Product Vertical Slice phase; no platform is selected by MISSION-007.

## Commitment classes

### Current commitments

- provider-neutral PromptRig IR remains the semantic center;
- Python 3.11+ is authoritative for Compiler Core v0.1;
- validation precedes lowering;
- the fixed offline compiler pipeline and four-adapter conformance set remain the current v0.1 foundation;
- generated TypeScript contracts are boundary artifacts, not a second compiler;
- live execution is separate from lowering;
- architecture and contract changes remain owner-ratified and evidence-gated;
- historical evidence is preserved without silent rewrite.

### Future targets

- a deterministic requirements compiler from user intent into canonical IR;
- a contract-governed PRS source language if evidence supports it;
- evaluation, baseline comparison, and bounded repair;
- a headless closed loop proven first with the fake adapter;
- mandatory production hardening and certification of the headless requirements, evaluation, repair, evidence, library, CLI, packaging, and consumer boundaries;
- versioned IR evolution with migrations and compatibility evidence;
- a permissioned live-execution boundary;
- a reproducible whole-configuration benchmark;
- a shared Simple Mode and Developer Mode product vertical slice;
- MissionRig and AI Engineering Workspace integration after the closed loop is reliable.

### Deferred ideas

- fifth and later provider adapters;
- live provider calls, credentials, hosted jobs, billing, and multi-tenancy;
- broad UI implementation and product expansion;
- MissionRig implementation and AI Engineering Workspace orchestration;
- marketplace, mobile-native clients, enterprise control plane, and arbitrary executable plugins.

### Rejected interpretations

- PromptRig is primarily a prompt optimizer or provider request exporter;
- adapter count is a proxy for product completeness;
- provider-native payload fields are sufficient evidence of semantic preservation;
- a UI or hosted database may own configuration outside canonical IR and versioned runtime metadata;
- Supabase, Next.js, or FastAPI is already an irrevocable product commitment;
- green tests or CI alone certify semantic correctness or benchmark readiness;
- PRS examples constitute a frozen grammar;
- IR v0.2 may be coded before a ratified specification, migration design, fixtures, and compatibility plan;
- MissionRig should begin before PromptRig can compile, evaluate, repair, and produce evidence.

## Authority and change control

This document reconciles the mission-authorized vision with the repository at the baseline above. Independent architectural review passed and the owner ratified this repository-native statement through DR-007-01 through DR-007-09 in PR #12. It becomes authoritative upon merge into `feature/promptrig-framework`; ratification does not authorize entry into any phase or execution of MISSION-008 through MISSION-011. Future changes must update the strategy index, maturity map, roadmap traceability, decision record, and affected mission gates together.
