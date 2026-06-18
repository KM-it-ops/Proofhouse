# PromptRig

[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab)](https://www.python.org/)
[![Runtime deps](https://img.shields.io/badge/runtime%20deps-stdlib%20only-2f855a)](#quick-start)
[![PromptOps](https://img.shields.io/badge/promptops-modular%20%7C%20testable%20%7C%20safe-6b46c1)](#what-promptrig-does)
[![License](https://img.shields.io/badge/license-MIT-111827)](LICENSE)

PromptRig is a lightweight prompt-operations framework for designing, auditing, rewriting, testing, and maintaining prompt systems across chatbots, coding agents, local LLMs, API agents, and autonomous workflows.

Its Custom GPT interface is **PromptOps Architect powered by PromptRig**.

PromptRig treats prompts like production infrastructure: modular, versioned, testable, grounded, safe, and reusable.

## What PromptRig Does

| Capability | What you get |
|---|---|
| Prompt architecture | Core prompt, mode prompts, reusable modules, and project context templates. |
| Prompt audits | Missing-context checks, safety boundaries, rewrite recommendations, and changelog notes. |
| Agentic mode design | Permission maps, tool boundaries, verification loops, and stop conditions. |
| Prompt evals | JSONL datasets, YAML rubrics, schema validation, scoring helpers, and report skeletons. |
| Custom GPT packaging | A ready instruction set for **PromptOps Architect powered by PromptRig**. |
| Codex adoption | A source-controlled local skill in `skills/promptrig/` for fresh Codex sessions. |

## Quick Start

```bash
python -m pip install -e .
python -m pytest
python -m promptrig.cli validate --dataset evals/datasets/prompt_audit_cases.jsonl
python -m promptrig.cli report --dataset evals/datasets/prompt_audit_cases.jsonl --out evals/reports/prompt_audit_report.md
```

On Windows, if `python` points at a managed environment without `pip`, use the launcher form:

```powershell
py -3.14 -m pip install -e .
py -3.14 -m pytest
```

## Repository Map

```text
prompts/
  custom_gpt/       PromptOps Architect Custom GPT instructions
  core/             Universal PromptRig prompt, safety, reference, and context policies
  modes/            Default, Audit, Meta-Prompting, Agentic, and Evaluator modes
  modules/          Reusable audit, rewrite, safety, eval, and changelog modules
evals/
  datasets/         JSONL prompt evaluation cases
  rubrics/          Human-readable YAML rubrics
  reports/          Generated reports, ignored except .gitkeep
src/promptrig/      Standard-library eval harness and CLI
tests/              Pytest coverage for schemas, scoring, and bundled datasets
docs/               GitHub-facing quickstart, showcase, and Custom GPT setup
skills/promptrig/   Source copy of the local Codex skill
references/         Current and legacy source policy notes
```

## CLI

Validate a dataset:

```bash
python -m promptrig.cli validate --dataset evals/datasets/prompt_audit_cases.jsonl
```

Generate a markdown report skeleton:

```bash
python -m promptrig.cli report --dataset evals/datasets/prompt_audit_cases.jsonl --out evals/reports/prompt_audit_report.md
```

## Design Rules

- Stay lightweight by default.
- Become stricter only when safety, agentic execution, repo work, evals, or missing context require it.
- Do not invent repository facts or project context.
- Use exact missing-context labels: `UNKNOWN`, `NOT SPECIFIED`, and `NOT FOUND IN PROVIDED MATERIAL`.
- Keep cybersecurity, automation, scraping, credentials, exploit research, malware analysis, and sensitive-data workflows defensive, authorized, educational, privacy-preserving, and compliance-oriented.
- Do not expose private chain-of-thought; use concise reasoning summaries and audit rationales.

## Start Here

- [Quickstart](docs/quickstart.md)
- [Showcase](docs/showcase.md)
- [Custom GPT setup](docs/custom-gpt-setup.md)
- [Prompt audit example](examples/prompt-audit-request.md)
- [Security policy](SECURITY.md)

## Status

PromptRig is intentionally small right now: no provider adapters, no API keys, no account-specific configuration, and no network dependency in the eval harness. The next useful layer is richer eval fixtures and real-world prompt system examples.
