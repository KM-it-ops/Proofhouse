# PromptRig Product Requirements Document

**Version:** 0.2.0

## Problem
Most people can describe what they want AI to accomplish but cannot translate that goal into a reliable prompt, agent, tool workflow, schema, retrieval design, evaluation suite, and provider-specific implementation.

Existing prompt-management and observability tools generally assume technical knowledge and begin after a prompt or application already exists.

## Solution
PromptRig accepts ordinary language, reconstructs requirements, selects an appropriate compilation level, produces a provider-neutral IR, compiles it for one or more AI providers, evaluates the result, performs bounded repair, and exports a complete implementation package.

## Primary User Stories

- As a nontechnical user, I can describe an outcome and receive a tested AI assistant without learning prompt engineering.
- As a developer, I can inspect and edit the IR, schemas, prompts, tools, and tests.
- As a consultant, I can create reusable client packages and export documentation.
- As a team, I can compare versions and understand why one compilation performed better.
- As a researcher, I can reproduce provider comparisons from frozen specifications and test sets.

## MVP Functional Requirements

### Project creation
- Create, name, save, duplicate, archive, and export projects.
- Store project intent, assumptions, compilation history, and evaluation results.

### Intake
- Accept free-form plain-language objectives.
- Ask only blocking or materially consequential questions.
- Permit user-selected provider and mode, but support automatic recommendations.

### Requirements compiler
- Reconstruct objective, users, inputs, outputs, constraints, risks, knowledge, tools, autonomy, and success criteria.
- Produce valid PromptRig IR.

### Compilation
- Select Prompt, Prompt System, Agent Blueprint, or Application Specification.
- Compile through provider adapters.
- Generate system instructions, user templates, schemas, tool manifests, evaluation cases, deployment notes, and implementation steps as required.

### Evaluation
- Validate schemas and required artifacts.
- Execute normal, edge, missing-data, adversarial, and formatting tests.
- Compare against a baseline where applicable.
- Perform no more than the configured repair limit.
- Report pass, fail, regression, confidence, cost, latency, and unresolved defects.

### Interfaces
- Simple Mode for nontechnical users.
- Developer Mode for raw configuration and artifacts.
- Mode switching must not fork the project state.

### Export
- Export Markdown package.
- Export JSON package.
- Export machine-readable manifest.
- Include version, provider, model, adapter, test, and timestamp metadata.

### Authentication and storage
- Secure authentication.
- Tenant-separated projects.
- User-controlled deletion and export.
- Secure provider credential handling.

## Nonfunctional Requirements

- Accessible, responsive interface
- Clear errors and recovery paths
- No critical secrets in logs
- Deterministic schema validation
- Bounded retries and repair loops
- Traceable provider calls
- Reproducible benchmark mode
- Modular provider adapters
- Automated test coverage
- Clean local setup for open-source use

## MVP Success Metrics

- At least 80% of nontechnical alpha users complete a first project without coaching.
- At least 70% correctly understand the final recommendation and next step.
- Generated artifacts pass at least 95% of deterministic contract tests.
- Evaluation loops terminate within configured limits in 100% of tested cases.
- Provider adapters pass shared conformance tests.
- No critical authorization or tenant-isolation defect remains at alpha release.

## Out of Scope
See PROMPTRIG_MASTER_SCOPE.md.
