# PromptRig Quickstart

Use this when you want to verify the project locally or hand it to another agent.

## Install

```bash
python -m pip install -e .
```

If your default `python` is managed by another tool, use a specific launcher or interpreter:

```powershell
py -3.14 -m pip install -e .
```

## Validate Datasets

```bash
python -m promptrig.cli validate --dataset evals/datasets/prompt_audit_cases.jsonl
python -m promptrig.cli validate --dataset evals/datasets/meta_prompting_cases.jsonl
python -m promptrig.cli validate --dataset evals/datasets/agentic_mode_cases.jsonl
python -m promptrig.cli validate --dataset evals/datasets/adversarial_cases.jsonl
```

Every JSONL case must include:

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

## Generate A Report Skeleton

```bash
python -m promptrig.cli report --dataset evals/datasets/prompt_audit_cases.jsonl --out evals/reports/prompt_audit_report.md
```

Reports are generated artifacts and are ignored by default except for `evals/reports/.gitkeep`.

## Run Tests

```bash
python -m pytest
```

The package runtime uses only the Python standard library. Pytest is needed only for the test suite.

## Use PromptRig

Start with:

- `prompts/core/promptrig_core.md` for the universal behavior.
- `prompts/custom_gpt/promptops_architect_custom_gpt.md` for Custom GPT instructions.
- `prompts/modes/*.md` for task-specific operating modes.
- `prompts/modules/*.md` for reusable audit, rewrite, safety, eval, and changelog components.
