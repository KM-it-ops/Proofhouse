# PromptRig Showcase

Prompt systems that feel like maintained infrastructure — not sticky notes.

## Pitch

Most prompts fail quietly: they miss context, drift from the product, overfit to one model, or grow too long to maintain. PromptRig is a small operating system for prompts:

- Core identity and mission
- Modes for audit, rewriting, agentic workflows, and evaluation
- Reusable modules for repeated work
- Datasets and rubrics for regression testing
- A CLI that validates eval inputs **without** provider APIs

Built for builders who ship coding agents, Custom GPTs, and cyber×AI harnesses where inventing context is a defect.

## 60-second demo

1. Paste a rough product or agent prompt.
2. Run the Context Auditor — confirmed facts vs missing context.
3. Pick a mode: **Audit** · **Meta-Prompting** · **Agentic** · **Evaluator**.
4. Rewrite with safety and missing-context behavior preserved.
5. Add or update JSONL eval cases.
6. Run the CLI validator and generate a markdown report skeleton.

```bash
python -m pip install -e .
python -m promptrig.cli validate --dataset evals/datasets/prompt_audit_cases.jsonl
python -m promptrig.cli report --dataset evals/datasets/prompt_audit_cases.jsonl --out evals/reports/prompt_audit_report.md
```

## Example outcomes

| You bring | PromptRig returns |
|---|---|
| Rough Custom GPT instructions | Modular system prompt, missing-context policy, safety boundaries |
| Coding-agent workflow prompt | Tool permission map, stop conditions, verification loop, audit criteria |
| Prompt rewrite request | Rewritten prompt + rationale + regression checks |
| Eval design request | JSONL cases, 1–5 rubric criteria, report skeleton |

## Why cyber×AI teams care

- Explicit missing-context labels instead of hallucinated “facts”
- Agentic permission maps and stop conditions before tools run
- Offline eval harness — inspectable, repeatable, no API keys required
- Defensive default for security, automation, scraping, credentials, and sensitive data

## Public-ready posture

- No secrets or provider credentials in the repo
- Runtime deps: Python standard library only
- Defensive safety stance documented in `SECURITY.md`
- Source policy notes in `references/current_sources.md`
- Portable skill + framework spec in `skills/promptrig/` and `promptrig-framework.*`

## What’s next

- More real-world prompt packs
- Golden-output fixtures for common audits and rewrites
- Optional provider runners after the offline harness stays stable
- A small gallery of before/after prompt transformations

## Links

- [README](../README.md)
- [Quickstart](quickstart.md)
- [Custom GPT setup](custom-gpt-setup.md)
- Portfolio: [km-it-ops.github.io](https://km-it-ops.github.io/)
