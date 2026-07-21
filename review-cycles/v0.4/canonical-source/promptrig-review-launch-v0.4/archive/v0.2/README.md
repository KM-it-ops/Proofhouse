# PromptRig Foundation Pack v0.2

**Status:** Benchmark-ready specification candidate  
**Canonical date:** 2026-07-19  
**Purpose:** Provide one auditable source of truth for independent end-to-end builds of PromptRig by multiple coding-agent configurations.

## What changed since v0.1

This release adds the contracts and controls needed to begin implementation without relying on chat history:

- complete acceptance criteria and definition of done
- threat model and trust boundaries
- Simple Mode and Developer Mode UX specification
- API, database, job, trace, evaluation, artifact, and benchmark schemas
- frozen benchmark environment and execution protocol
- autonomous versus steered run policy
- submission manifest and evidence requirements
- hidden-test interface contract
- provider-documentation source manifest
- starter monorepo specification
- universal coding-agent master build prompt
- decision log, risk register, and change-control policy

## Source of truth order

1. `PROMPTRIG_MASTER_SCOPE.md`
2. `PRD.md`
3. `ACCEPTANCE_CRITERIA.md`
4. normative JSON Schemas in `schemas/`
5. `ARCHITECTURE.md`, `SECURITY_THREAT_MODEL.md`, and `UX_SPEC.md`
6. benchmark documents in `benchmark/`
7. implementation guidance and examples

When documents conflict, the earlier item in this list wins. A conflict must be recorded in `DECISION_LOG.md`; coding agents may not silently choose an interpretation.

## Intended benchmark tracks

- OpenAI Codex + GPT-5.6 Sol
- Claude Code + Claude Fable 5
- Kimi Code + Kimi K3

The benchmark evaluates the complete agent configuration: harness, model, tools, permissions, instructions, environment, routing, cost, interventions, and resulting software.

## Start here

1. Read `PROMPTRIG_MASTER_SCOPE.md`.
2. Read `benchmark/MASTER_BUILD_PROMPT.md`.
3. Validate the environment against `benchmark/ENVIRONMENT.md`.
4. Create a clean competitor branch and isolated database.
5. Execute the milestones in order.
6. Seal the submission using `schemas/SUBMISSION_MANIFEST.schema.json`.
