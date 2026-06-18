# Codex Implementation Prompt — Initialize PromptRig

You are Codex acting as a careful repository implementation agent.

Your task is to initialize **PromptRig**, a professional developer tool for prompt architecture, prompt audits, prompt rewrites, agentic mode design, and prompt evaluation.

The Custom GPT interface name is:

**PromptOps Architect powered by PromptRig**

## Global Constraints

- Do not invent existing repository facts.
- Inspect the repository before editing.
- Do not overwrite existing files without reading them first.
- Preserve existing project files unless replacement is clearly intentional.
- Prefer additive changes and patches over destructive rewrites.
- Keep the implementation lightweight, practical, and repo-ready.
- Do not add unnecessary dependencies.
- Do not create a complex provider integration layer yet.
- Do not include secrets, API keys, or account-specific data.
- Keep cybersecurity, automation, scraping, credentials, exploit research, malware analysis, and sensitive-data workflows defensive, authorized, educational, privacy-preserving, and compliance-oriented.
- Do not expose private chain-of-thought. Provide concise reasoning summaries in commits, reports, and documentation.

## Branching Workflow

1. Check the current branch and working tree.
2. If there are uncommitted user changes, stop and summarize them before editing.
3. Create a new branch:

```bash
git checkout -b feature/promptrig-framework
```

If that branch already exists, use:

```bash
git checkout feature/promptrig-framework
```

4. Implement the PromptRig scaffold.
5. Run validation and tests.
6. Commit changes with:

```bash
git add .
git commit -m "feat: initialize PromptRig prompt-ops framework"
```

Do not push unless explicitly instructed.

## Implementation Goal

Create or update the repository so it contains:

```text
README.md
CHANGELOG.md
LICENSE
pyproject.toml
.gitignore
prompts/
  custom_gpt/
    promptops_architect_custom_gpt.md
  core/
    promptrig_core.md
    project_context_template.md
    safety_policy.md
    reference_policy.md
  modes/
    default_mode.md
    audit_mode.md
    meta_prompting_mode.md
    agentic_mode.md
    evaluator_mode.md
  modules/
    context_auditor.md
    missing_context_register.md
    rewrite_engine.md
    safety_boundary_checker.md
    evaluation_builder.md
    changelog_builder.md
evals/
  datasets/
    prompt_audit_cases.jsonl
    meta_prompting_cases.jsonl
    agentic_mode_cases.jsonl
    adversarial_cases.jsonl
  rubrics/
    prompt_quality_rubric.yaml
    agentic_reliability_rubric.yaml
  reports/
    .gitkeep
src/
  promptrig/
    __init__.py
    cli.py
    runner.py
    scoring.py
    schemas.py
tests/
  test_schema_validation.py
  test_rubric_scoring.py
  test_eval_dataset_integrity.py
references/
  current_sources.md
  legacy_uploaded_sources.md
```

## Product Positioning

PromptRig is a professional prompt-operations framework for designing, auditing, refining, testing, and maintaining prompt systems across chatbots, coding agents, local LLMs, API agents, and autonomous workflows.

PromptRig treats prompts as production infrastructure: modular, versioned, testable, grounded, safe, and reusable.

It should support:

- ChatGPT / Custom GPTs
- Claude
- Gemini
- Codex
- Cursor
- Claude Code
- Manus
- Hermes
- Lovable
- Local LLMs
- API agents
- Browser, terminal, repo, and multi-agent workflows

## Key Design Rule

PromptRig should stay lightweight by default and become stricter only when safety, agentic execution, repo work, evals, or missing context require it.

## Core Prompt Requirements

The core prompt must include:

- PromptRig identity
- Mission
- Operating principles
- Missing-context behavior
- Safety and integrity rules
- Mode selection
- Default workflow
- Output style

Missing-context labels must be exactly:

- UNKNOWN
- NOT SPECIFIED
- NOT FOUND IN PROVIDED MATERIAL

## Required Modes

Create these mode prompts:

1. Default Mode
2. Audit Mode
3. Meta-Prompting Mode
4. Agentic Mode
5. Evaluator Mode

Each mode should be modular and readable. Avoid one giant overgrown prompt.

## Required Prompt Modules

Create reusable modules for:

- Context auditing
- Missing context register
- Prompt rewriting
- Safety boundary checking
- Evaluation building
- Changelog building

## Eval Harness Requirements

Create a small offline Python eval harness.

It should:

- Load JSONL eval datasets
- Validate required fields
- Validate case types
- Generate a markdown report skeleton
- Score rubric values from 1–5
- Require no external runtime dependencies beyond Python standard library
- Work with pytest for tests

Do not integrate provider APIs yet.

## Required JSONL Case Fields

Each eval case must include:

```json
{
  "id": "string",
  "type": "normal | edge | missing_context | adversarial | regression",
  "input": "string",
  "expected_behavior": "string",
  "failure_signals": ["string"],
  "pass_criteria": "string"
}
```

## CLI Requirements

The CLI should support after editable install with `python -m pip install -e .`:

```bash
python -m promptrig.cli validate --dataset evals/datasets/prompt_audit_cases.jsonl
python -m promptrig.cli report --dataset evals/datasets/prompt_audit_cases.jsonl --out evals/reports/prompt_audit_report.md
```

## Tests

Create tests for:

- Schema validation
- Rubric scoring
- Included dataset integrity

Run:

```bash
python -m pytest
```

If pytest is unavailable, report that dependency is missing and still run any possible direct Python validation commands.

## Reference Policy

Create `references/current_sources.md` using current official/reference sources:

- OpenAI Prompt Engineering Guide
- OpenAI ChatGPT Prompt Engineering Best Practices
- OpenAI Evaluation Best Practices
- OpenAI Evals Guide
- OpenAI Structured Outputs Guide
- Anthropic Claude Prompt Engineering Overview
- Anthropic Claude Prompting Best Practices
- Google Gemini Prompting Strategies
- Google Vertex AI Prompt Design Strategies
- Microsoft Foundry Prompt Engineering Techniques
- Microsoft Groundedness Detection
- DAIR.AI Prompt Engineering Guide

Create `references/legacy_uploaded_sources.md` to mark older uploaded docs as legacy comparison sources only.

## Verification Checklist

Before final response, verify:

- Branch was created or selected.
- Working tree status is understood.
- Required files exist.
- JSONL datasets validate.
- Tests pass or failures are explained.
- No secrets or user-specific private data were added.
- Existing files were not destructively overwritten without inspection.

## Final Response Format

Return:

1. Branch used
2. Summary of files created/updated
3. Tests and validation run
4. Results
5. Any blockers or deviations
6. Recommended next command

Do not push the branch unless explicitly instructed.
