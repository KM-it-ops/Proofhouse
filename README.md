# PromptRig

PromptRig is a professional prompt-operations framework for designing, auditing, refining, testing, and maintaining prompt systems across chatbots, coding agents, local LLMs, API agents, and autonomous workflows.

Its Custom GPT interface is **PromptOps Architect powered by PromptRig**.

PromptRig treats prompts as production infrastructure: modular, versioned, testable, grounded, safe, and reusable.

## What PromptRig Includes

- A lightweight but disciplined core prompt
- Modular operating modes
- Reusable prompt modules
- Prompt audit and rewrite templates
- Safety and missing-context rules
- Prompt evaluation rubrics
- JSONL test cases
- A small offline Python eval harness

## Target Runtimes

PromptRig is intended for:

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

PromptRig does not assume any tool exists. Agentic workflows must detect available capabilities before using them.

## Repository Layout

```text
prompts/
  custom_gpt/
  core/
  modes/
  modules/
evals/
  datasets/
  rubrics/
  reports/
src/promptrig/
tests/
references/
```

## Quick Start

Install the package in editable mode:

```bash
python -m pip install -e .
```

Validate the included prompt eval datasets:

```bash
python -m promptrig.cli validate --dataset evals/datasets/prompt_audit_cases.jsonl
```

Create a markdown report skeleton:

```bash
python -m promptrig.cli report --dataset evals/datasets/prompt_audit_cases.jsonl --out evals/reports/prompt_audit_report.md
```

Run tests:

```bash
python -m pytest
```

## Design Principle

PromptRig stays lightweight by default and becomes stricter only when the task requires stricter controls: safety, agentic execution, repo work, evals, missing context, or sensitive domains.
