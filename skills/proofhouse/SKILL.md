---
name: proofhouse
description: Meta prompt-optimizer that turns a natural-language objective into a fully optimized, model-specific prompt through branching upfront clarification and a self-heal refinement loop. Use this whenever the user wants help crafting, refining, or optimizing a prompt for a specific AI model or provider (Claude Fable 5.1, Mythos 5.1, Opus 5, Sonnet 5, Haiku 4.5, GPT-5.6 Sol/Terra/Luna, Gemini 3.8 Flash, Grok 4.6, Muse Spark 1.3, Kimi K3, or any other model/tool) -- especially when they say "Proofhouse," "optimize this prompt," "write a prompt for [model]," ask for clarifying questions before drafting a prompt, care about token efficiency or prompt caching, are building a recurring/looping/autonomous task and need it engineered as a loop, want an unfamiliar model's prompting quirks researched, or want a "self-heal" pass on a prompt that isn't working right. Trigger even if they don't use the word "prompt" explicitly -- "help me get better output from Opus 5 for X" or "this isn't working with GPT" both qualify.
---

# Proofhouse

A meta prompt-optimizer, not a single prompt template. Given a raw objective and a target
model, it runs a fixed four-stage flow and hands back a ready-to-paste, model-specific
prompt. Full spec, system-prompt text, and JSON schemas live in
`references/proofhouse-framework.md` (human-readable) and
`references/proofhouse-framework.json` (machine-readable) -- read whichever is more useful
for the task at hand. An interactive version that runs the whole flow live (calling the
Claude API from inside a Claude artifact) is bundled at `assets/proofhouse.jsx` -- offer to
drop that in as an artifact when the user wants the point-and-click version rather than a
conversational walkthrough.

## The flow

1. **Input** — get the raw objective, the target model/provider, a token-efficiency
   preference (Efficient / Balanced / Thorough), and whether this is a one-shot task or a
   recurring/loop task.
2. **Clarify** — ask ONE upfront batch of grouped questions (not one-at-a-time -- see
   "Why batched, not iterative" below). Include conditional follow-ups that only apply given
   a particular answer (branching / domino-effect questions). Question count and depth scale
   with the efficiency preference: ~6-10 for Efficient, ~10-16 for Balanced, ~14-22 for
   Thorough.
3. **Compile** — synthesize the optimized prompt, a short rationale, suggested settings
   (effort level, temperature, etc.), and a one-line account of concrete token-saving choices
   made. Add a Security & Reliability section only if the task touches software/infra/data
   handling. Add a labeled Loop Structure section if this is a recurring task (see below).
4. **Self-heal** — if the user says it's not right, diagnose the complaint (scope mismatch,
   wrong tone, missing constraint, too rigid, too vague, model mismatch, security gap, token
   bloat/too verbose, other) and produce a revised version. Keep prior versions referenceable.
   Treat the user's clarification answers as accepted constraints: carry every one into every
   revision, and if new feedback conflicts with one, keep it and name the conflict instead of
   silently dropping it. Never remove a required test, acceptance check or approval gate for
   brevity, whatever a model note says.
5. **Evidence (optional)** — when the user wants proof rather than a draft, offer the offline
   CLI: `proofhouse-compiler optimize` records revisions and the outputs they produced, keeps
   the answers as constraints, checks both, and reports what passed and what was not measured
   (see `docs/reference-workflow.md` in the repository).

Run this conversationally when there's no artifact in play: ask the clarifying batch as a
single message (numbered, grouped), collect the answers in one reply, then compile. One
clarifying batch per compile -- don't drip-feed follow-up questions. Don't schedule Proofhouse
runs, run them in the background, or set them to repeat unless the user asks.

## Why batched, not iterative

Some targets (long-horizon/autonomous models especially) are expensive or clumsy to go
back-and-forth with. Front-load every question you'll plausibly need in one pass, including
questions that only matter *if* an earlier answer goes a certain way -- present those as
"if you chose X, also: ..." rather than waiting to discover you need them.

## Model notes

<!-- model-list:begin -->
Built-in profiles for Claude Fable 5.1, Claude Mythos 5.1, Claude Opus 5, Claude Sonnet 5, Claude Haiku 4.5, GPT-5.6 Sol, GPT-5.6 Terra, GPT-5.6 Luna, Gemini 3.8 Flash, Grok 4.6, Muse Spark 1.3, and Kimi K3 (plus legacy GPT-5.5, Gemini, Claude Fable 5, Claude Mythos 5, and Claude Opus 4.8) are in `references/proofhouse-framework.json` under `modelNotes`; canonical ids, aliases, and `verifiedAt` review dates (last reviewed 2026-09-03) are under `modelRegistry`. Say which profile you used, its review date, and its `evidence` label; an `unverified` profile has no cited sources. If it is older than 90 days, tell the user to re-check pricing, context, and settings against vendor docs. Never drop a user-required test, acceptance check, or approval gate because a model note suggests brevity. For anything else the user names:
<!-- model-list:end -->

1. Check whether you (or a prior Proofhouse run) already have notes on it in this
   conversation's memory, an artifact's persistent storage, or -- when a Proofhouse
   checkout is at hand -- the local cache (`proofhouse-compiler models show "<name>"`).
2. If not, research it -- web search for the model's actual prompting behavior, context
   window, and known quirks -- before compiling the prompt. Don't guess. Tell the user you
   are researching and why, since it costs time and tokens the built-in profiles don't.
3. Condense findings into one dense paragraph matching the style of the built-in profiles,
   and treat it as reusable knowledge for the rest of the conversation (or write it to
   storage if running inside the artifact).
4. If research turns up nothing solid, say so and fall back to general best practice rather
   than inventing vendor-specific claims.

## Token discipline

Every compiled prompt should itself be lean: no redundant framing, no restated context,
merged rather than enumerated constraints, and -- for Claude targets -- a note on separating
stable/reusable instructions from per-call variable content so the user can use prompt
caching. Efficiency preference controls how aggressively you trim (see word caps in the
reference file). State an honest, checkable account of what you trimmed -- not a vague claim
of being maximally efficient.

## Loop engineering

When the objective is recurring or autonomous rather than one-shot, structure the compiled
prompt with an explicit loop shape instead of (or alongside) linear instructions:

- **Trigger/cadence** -- what starts each iteration
- **Loop body** -- plan, act, verify each iteration against evidence
- **Exit/stop condition** -- distinct from what ends a single iteration
- **Checkpoint/escalation** -- what's severe or ambiguous enough to involve the human
- **Compounding memory** -- a running lessons file so later iterations build on earlier ones

Full directive text is in `references/proofhouse-framework.json` under `loopEngineering`.

## Security & Reliability

If the objective involves building software, handling sensitive data, or touching
production systems, add a short section to the compiled prompt covering the relevant
constraints. Omit entirely when not applicable -- don't pad prompts with boilerplate
security language for tasks that don't need it.

## Offline compiler

Reach for the CLI instead of compiling in chat when the user wants a reproducible,
inspectable compile result rather than a pasteable prompt. Check the environment with
`proofhouse-compiler doctor`. The closed-loop path takes structured requirements JSON (or
`-` for stdin) and runs requirements -> IR -> adapter compile -> eval/repair -> evidence:

```
proofhouse-compiler closed-loop <input.json> [--repair-budget {0,1,2}] [--json]
```

`structured_developer_v0` additionally requires `tool_permissions.allowed_tools` and
`stop_conditions`.

## Honesty gates

The tested path is offline. Package is `proofhouse` 0.3.0 (`src/proofhouse/`).
CLIs: `proofhouse` (eval harness) and `proofhouse-compiler` (compiler, including
`route` / `assay` / `proof`, and the offline optimize / models / install-skill
commands; optimize renders packets and never calls a model).
Approved profiles `structured_minimal_v0`, `structured_developer_v0`. Requirements
compiler maturity is `PARTIAL`. `route` / `assay` / `proof` and media are experimental.
`execute-openai` is fail-closed and opt-in: it sends every mandatory requirement or refuses,
and it is experimental. Hosted/MissionRig commands are experimental and hidden behind
`PROOFHOUSE_EXPERIMENTAL=1`; their tenant label is not isolation. Do not claim a hosted UI,
live-default providers, or output quality.

A PASS from `optimize check` means every declared check passed on that exact revision and its
recorded outputs, and every accepted constraint has a passing linked check. It does not mean
the prompt is good in general. Model profiles cite no sources yet and are labeled
`unverified`; say so when you rely on one. Public decisions are in `docs/decisions/`.

Fable parked remainder is CLOSED (2026-09-20): no IR v0.2, no 008 join, no
CERTIFIED promotion, no hosted/MissionRig product,
no `max_cost_usd` enforcement (recorded, not enforced). Do not describe any of
these as pending.
