---
name: promptrig
description: Meta prompt-optimizer that turns a natural-language objective into a fully optimized, model-specific prompt through branching upfront clarification and a self-heal refinement loop. Use this whenever the user wants help crafting, refining, or optimizing a prompt for a specific AI model or provider (Claude Fable 5, Claude Mythos 5, Opus 4.8, Sonnet 5, Haiku 4.5, GPT, Gemini, or any other model/tool) -- especially when they say "PromptRig," "optimize this prompt," "write a prompt for [model]," ask for clarifying questions before drafting a prompt, care about token efficiency or prompt caching, are building a recurring/looping/autonomous task and need it engineered as a loop, want an unfamiliar model's prompting quirks researched, or want a "self-heal" pass on a prompt that isn't working right. Trigger even if they don't use the word "prompt" explicitly -- "help me get better output from Fable 5 for X" or "this isn't working with GPT" both qualify.
---

# PromptRig

A meta prompt-optimizer, not a single prompt template. Given a raw objective and a target
model, it runs a fixed four-stage flow and hands back a ready-to-paste, model-specific
prompt. Full spec, system-prompt text, and JSON schemas live in
`references/promptrig-framework.md` (human-readable) and
`references/promptrig-framework.json` (machine-readable) -- read whichever is more useful
for the task at hand. An interactive version that runs the whole flow live (calling the
Claude API from inside a Claude artifact) is bundled at `assets/promptrig.jsx` -- offer to
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

Run this conversationally when there's no artifact in play: ask the clarifying batch as a
single message (numbered, grouped), collect the answers in one reply, then compile.

## Why batched, not iterative

Some targets (long-horizon/autonomous models especially) are expensive or clumsy to go
back-and-forth with. Front-load every question you'll plausibly need in one pass, including
questions that only matter *if* an earlier answer goes a certain way -- present those as
"if you chose X, also: ..." rather than waiting to discover you need them.

## Model notes

Built-in profiles for Claude Fable 5, Claude Mythos 5, Opus 4.8, Sonnet 5, Haiku 4.5, GPT,
and Gemini are in `references/promptrig-framework.json` under `modelNotes`. For anything
else the user names:

1. Check whether you (or a prior PromptRig run) already have notes on it in this
   conversation's memory or an artifact's persistent storage.
2. If not, research it -- web search for the model's actual prompting behavior, context
   window, and known quirks -- before compiling the prompt. Don't guess.
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

Full directive text is in `references/promptrig-framework.json` under `loopEngineering`.

## Security & Reliability

If the objective involves building software, handling sensitive data, or touching
production systems, add a short section to the compiled prompt covering the relevant
constraints. Omit entirely when not applicable -- don't pad prompts with boilerplate
security language for tasks that don't need it.
