# PromptRig Build-Off Rules

## Unit under test

The complete coding-agent configuration: harness, model, instructions, tools, permissions, runtime, routing behavior, and produced software.

## Competitor obligations

- begin from the frozen starter commit
- obey normative scope and acceptance criteria
- never inspect hidden tests or competitor branches
- maintain a decision and evidence log
- run required validation commands
- produce the sealed submission manifest
- disclose incomplete work honestly

## Autonomous run

No human guidance after launch except documented infrastructure recovery that does not change application code or product decisions.

## Steered run

Human clarification or redirection is permitted and logged verbatim with timestamp and effect. Steered scores are reported separately.

## Prohibited benchmark conduct

- changing scoring after seeing submissions
- giving one competitor additional product information
- manual patches attributed to the agent
- hidden model substitution without disclosure
- cherry-picking one run while concealing failures
- exposing hidden tests to public branches before sealing

## Completion

A run ends when the agent declares completion, reaches the frozen budget, becomes irrecoverably blocked, or violates benchmark isolation. Partial submissions are still evaluated and reported.
