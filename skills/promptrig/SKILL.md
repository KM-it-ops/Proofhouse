---
name: promptrig
description: Prompt architecture, prompt audits, prompt rewrites, agentic mode design, missing-context analysis, safety boundary checks, and offline prompt evaluation using the PromptRig framework. Use when the user asks to improve, audit, modularize, test, package, or operationalize prompts for ChatGPT, Custom GPTs, Claude, Gemini, Codex, Cursor, Claude Code, Manus, Hermes, Lovable, local LLMs, API agents, browser/terminal agents, or multi-agent workflows.
---

# PromptRig

PromptRig treats prompts as production infrastructure: modular, versioned, testable, grounded, safe, and reusable.

## Workflow

1. Identify the target surface: chatbot, Custom GPT, coding agent, API agent, browser/terminal agent, local LLM, or multi-agent workflow.
2. Extract confirmed facts from the user's material. Do not invent project facts.
3. Label missing context with exactly `UNKNOWN`, `NOT SPECIFIED`, or `NOT FOUND IN PROVIDED MATERIAL`.
4. Choose the lightest useful mode: Default, Audit, Meta-Prompting, Agentic, or Evaluator.
5. Produce a prompt, audit, rewrite, module set, eval cases, or rubric that is repo-ready.
6. Add verification: checklist, JSONL eval case, rubric criteria, or CLI command when the prompt will be reused.

## Mode Selection

- Use Audit Mode for existing prompt/system review.
- Use Meta-Prompting Mode for prompt generation, rewrite, comparison, or optimization.
- Use Agentic Mode for tools, permissions, stop conditions, autonomous workflows, and repo work.
- Use Evaluator Mode for rubric design, JSONL cases, scoring, and regression checks.
- Use Default Mode for ordinary prompt architecture help.

## Safety

For cybersecurity, automation, scraping, credentials, account access, exploit research, malware analysis, sensitive data, legal, medical, or financial workflows, keep the output defensive, authorized, educational, privacy-preserving, and compliance-oriented.

Do not expose private chain-of-thought. Provide concise reasoning summaries, audit rationales, decision tables, and final recommendations.

## Local Project

When working in the local PromptRig repository, start at:

```text
C:\Users\alkur\Projects\PromptRig
```

Useful files:

- `prompts/core/promptrig_core.md`
- `prompts/custom_gpt/promptops_architect_custom_gpt.md`
- `prompts/modes/*.md`
- `prompts/modules/*.md`
- `evals/datasets/*.jsonl`
- `evals/rubrics/*.yaml`
- `src/promptrig/cli.py`

Run local verification with:

```powershell
py -3.14 -m pytest
py -3.14 -m promptrig.cli validate --dataset evals/datasets/prompt_audit_cases.jsonl
```

## References

Read `references/promptops-workflow.md` when you need a compact checklist for audits, rewrites, agentic workflows, or eval case construction.
