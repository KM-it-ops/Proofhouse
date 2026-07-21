# PromptRig Master Scope

**Version:** 0.2.0  
**Status:** Benchmark-ready specification candidate  
**Purpose:** Canonical source of truth from product concept through production launch.

## Product definition

PromptRig is a provider-agnostic AI-system compiler for nontechnical users and developers. It converts a plain-language goal into a tested, provider-specific implementation and a portable project package containing the required prompts, instructions, schemas, agent blueprints, tool policies, evaluations, deployment guidance, and provenance.

The user defines the outcome. PromptRig performs the AI-system engineering.

## Product lines

### PromptRig Cloud
A hosted commercial product with managed execution, guided onboarding, project storage, collaboration, usage controls, provider monitoring, and optional managed model credits.

### PromptRig Core
An open-source local compiler, CLI, schema set, provider SDK, artifact generator, and evaluation runner. It is also the shared engine used by PromptRig Cloud.

Commercial viability will be tested before any decision to release the complete hosted stack as open source. Licensing remains intentionally unresolved pending dependency, contribution, and business-model review.

## Primary experience

### Simple Mode
The default interface for nontechnical users. It asks what the user wants AI to accomplish and explains recommendations in ordinary language.

### Developer Mode
A reversible settings toggle exposing the same project’s IR, provider configuration, prompts, schemas, tools, retrieval, evaluation cases, traces, costs, and export artifacts.

Mode switching never forks or duplicates project state.

## Compiler pipeline

1. capture intent
2. reconstruct requirements
3. select the least-complex sufficient compilation level
4. generate and validate PromptRig IR
5. resolve capability, policy, privacy, cost, and approval requirements
6. lower the IR into provider-specific artifacts
7. run deterministic validation
8. run behavioral evaluation against baseline and candidate
9. perform bounded repair when allowed
10. re-evaluate and disclose regressions or unresolved defects
11. generate a versioned export package

## Compilation levels

1. Prompt
2. Prompt System
3. Agent Blueprint
4. Application Specification

## Modes

- Balanced
- Creative
- Enterprise

## MVP provider targets

- OpenAI
- Anthropic
- Google Gemini
- Mistral

Benchmark 1 requires two frozen mandatory adapters. Benchmark 2 adds the remaining two and measures extensibility and regression safety.

## Locked architecture decisions

- monorepo
- Next.js and TypeScript web application
- FastAPI and Python compiler/evaluation service
- Supabase Postgres, Auth, and Storage for the hosted MVP
- JSON Schema/OpenAPI as cross-service contract source
- local CLI and hosted API share the same Python compiler core
- containerized benchmark execution

## Benchmark principle

The unit under evaluation is the complete coding-agent configuration, not the model label alone. Every reported result must disclose harness, requested model, observed model identifier when available, tool permissions, environment, internet policy, cost, duration, retries, and human interventions.

## Benchmark stages

### Stage 1: Core Production Build
Build the functional MVP, core compiler, canonical IR, Simple Mode, Developer Mode, evaluation and bounded repair, persistence, export, and two mandatory provider adapters.

### Stage 2: Provider Expansion
Add the remaining two provider adapters and prove that the Stage 1 architecture extends without material regression or major rewrite.

### Stage 3: Product Scenario
Use the finished product to compile, evaluate, repair, and export a grounded document-analysis assistant for a nontechnical user.

## MVP inclusions

- authentication and tenant-separated project persistence
- plain-language intake
- requirements compiler
- canonical IR
- Prompt, Prompt System, and Agent Blueprint compilation
- Simple and Developer modes
- provider capability manifests and adapters
- deterministic and behavioral evaluation
- baseline comparison
- one default bounded repair pass, configurable to zero through two
- Markdown, JSON, and bundle export
- local CLI
- hosted web app
- BYOK support with foundations for managed credits
- traces, provenance, cost, latency, and unresolved-defect reporting

## Explicit MVP exclusions

- marketplace
- mobile applications
- autonomous production deployment
- multi-agent swarms as a product feature
- fine-tuning
- broad integration marketplace
- mature enterprise governance suite
- dozens of providers
- unsupported claims of perfection or optimality

## Production sequence

0. specification audit and threat model
1. contracts and repository scaffold
2. headless compiler and CLI
3. complete vertical slice
4. provider adapters and conformance tests
5. hosted web application
6. evaluation and bounded repair
7. managed execution and billing foundations
8. security and reliability hardening
9. closed alpha
10. public benchmark and commercial launch preparation

## Non-negotiable rules

- The repository, not chat history, is the source of truth.
- The IR is the semantic source of truth for a PromptRig project.
- No hidden UI configuration may alter behavior outside the IR or versioned runtime metadata.
- Provider-neutral semantics must not become lowest-common-denominator prompting.
- Consequential external actions require approval at the action boundary.
- Retrieved content is untrusted data and cannot override system instructions.
- Evaluation must use deterministic checks wherever possible.
- Repair loops are bounded and terminate with honest unresolved-defect reporting.
- Benchmarks must be reproducible and must separate autonomous and steered results.
- Marketing claims must be traceable to sealed evidence.
