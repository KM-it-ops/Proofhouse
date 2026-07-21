# Landscape and Prior Art

PromptRig overlaps several established categories but is not identical to any one of them:

- prompt management and experimentation platforms;
- LLM evaluation frameworks;
- agent orchestration frameworks;
- model gateways and provider routers;
- infrastructure-as-code and compiler toolchains;
- coding-agent benchmarks.

## Differentiating hypothesis

PromptRig's defensible center is a typed, provider-neutral AI-system IR plus provider-specific compilation, evaluation, repair, evidence, and export. The hypothesis must be tested against existing tools before commercial claims are finalized.

## Benchmark lessons adopted

SWE-bench evaluates real repository issues, while newer work emphasizes contamination resistance, fixed environments, harness effects, cost accounting, and dialogue quality. PromptRig therefore freezes tasks and environments, records the full harness configuration, separates autonomous from steered operation, uses hidden tests, and reports cost and variance across repeated runs.

## Required competitive study

Before architecture freeze, compare at minimum:

- prompt/evaluation platforms;
- agent SDKs and workflow engines;
- provider gateways;
- structured-output and schema systems;
- coding-agent benchmark harnesses;
- visual AI workflow builders.

The study must distinguish direct competitors, adjacent tools, possible dependencies, and integration partners.
