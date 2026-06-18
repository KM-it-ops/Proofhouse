# Custom GPT Setup

Use this to create **PromptOps Architect powered by PromptRig**.

## Instructions

Paste the contents of:

```text
prompts/custom_gpt/promptops_architect_custom_gpt.md
```

into the Custom GPT instruction field.

## Knowledge Files

Recommended uploads:

- `prompts/core/promptrig_core.md`
- `prompts/core/project_context_template.md`
- `prompts/core/safety_policy.md`
- `prompts/core/reference_policy.md`
- `prompts/modes/default_mode.md`
- `prompts/modes/audit_mode.md`
- `prompts/modes/meta_prompting_mode.md`
- `prompts/modes/agentic_mode.md`
- `prompts/modes/evaluator_mode.md`
- `prompts/modules/context_auditor.md`
- `prompts/modules/missing_context_register.md`
- `prompts/modules/rewrite_engine.md`
- `prompts/modules/safety_boundary_checker.md`
- `prompts/modules/evaluation_builder.md`
- `prompts/modules/changelog_builder.md`

Keep eval datasets and source code in the repository unless the GPT needs to discuss them directly.

## Conversation Starters

- Audit this prompt system and identify missing context.
- Rewrite this agent prompt with tool boundaries and verification steps.
- Build eval cases for this Custom GPT instruction set.
- Convert these rough notes into modular PromptRig prompts.

## Safety Defaults

Use the exact missing-context labels:

- `UNKNOWN`
- `NOT SPECIFIED`
- `NOT FOUND IN PROVIDED MATERIAL`

For cybersecurity, automation, scraping, credentials, exploit research, malware analysis, and sensitive-data workflows, keep outputs defensive, authorized, educational, privacy-preserving, and compliance-oriented.
