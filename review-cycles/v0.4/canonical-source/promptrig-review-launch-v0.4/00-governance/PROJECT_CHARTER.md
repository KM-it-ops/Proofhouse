# Project Charter

## Mission

PromptRig compiles plain-language intent into portable, testable, provider-aware AI systems. It generates prompts, schemas, tools, agent workflows, evaluations, deployment artifacts, and evidence—not merely polished text prompts.

## Product tracks

- **PromptRig Cloud:** commercial SaaS for nontechnical users and teams.
- **PromptRig Core:** developer-facing compiler, CLI, schemas, provider contracts, and local evaluation tooling.
- **PromptRig Benchmark:** reproducible coding-agent build-off and product-conformance suite.

## Governing principles

1. The repository is the source of truth.
2. Claims require evidence and provenance.
3. Provider-neutral semantics must not collapse into lowest-common-denominator behavior.
4. Generated systems must expose assumptions, uncertainty, costs, and unresolved failures.
5. Evaluation is a product capability, not a launch-day add-on.
6. Security, tenant isolation, and secret handling are release gates.
7. Benchmark outcomes evaluate complete agent configurations, including model, harness, tools, environment, routing, and intervention policy.
8. Nontechnical usability is the default; technical depth remains available through Developer Mode.

## Authority model

The project owner approves scope, branding, commercial boundaries, and final release. The Architecture Review Board may recommend or block implementation based on unresolved critical findings. Coding agents may propose changes but cannot silently redefine requirements.
