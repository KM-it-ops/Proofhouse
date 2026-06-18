# PromptRig Showcase

PromptRig is for teams and solo builders who want prompt systems to feel less like sticky notes and more like maintained infrastructure.

## The Pitch

Most prompts fail quietly: they miss context, drift from the product, overfit to a single model, or become too long to maintain. PromptRig gives prompts a small operating system:

- a core identity and mission,
- modes for audit, rewriting, agentic workflows, and evaluation,
- reusable modules for repeated work,
- datasets and rubrics for regression testing,
- a CLI that validates eval inputs without provider APIs.

## Demo Flow

1. Paste a rough product or agent prompt into PromptRig.
2. Run the Context Auditor module to separate confirmed facts from missing context.
3. Pick the right mode: Audit, Meta-Prompting, Agentic, or Evaluator.
4. Rewrite the prompt with safety and missing-context behavior preserved.
5. Add or update JSONL eval cases.
6. Run the CLI validator and generate a markdown report skeleton.

## Example Outcomes

| Input | PromptRig output |
|---|---|
| Rough Custom GPT instructions | Modular system prompt, missing-context policy, and safety boundaries. |
| Coding-agent workflow prompt | Tool permission map, stop conditions, verification loop, and audit criteria. |
| Prompt rewrite request | Rewritten prompt plus rationale and regression checks. |
| Eval design request | JSONL cases, 1-5 rubric criteria, and report skeleton. |

## What Makes It Public-Ready

- No secrets or provider credentials.
- No runtime dependencies beyond Python standard library.
- Defensive safety stance for security, automation, scraping, credentials, and sensitive-data work.
- Clear source references in `references/current_sources.md`.
- Local Codex skill source in `skills/promptrig/`.

## What Comes Next

- More real-world prompt packs.
- Golden-output fixtures for common audits and rewrites.
- Optional provider-specific runners after the offline harness stabilizes.
- A small gallery of before/after prompt transformations.
