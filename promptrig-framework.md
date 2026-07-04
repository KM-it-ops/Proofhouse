# PromptRig Framework

A meta prompt-optimizer: natural language in, a model-specific optimized prompt out, with
branching clarification and a self-heal refinement loop. Portable spec — usable as an
interactive artifact, dropped into a new project, or run manually in conversation.

---

## How it works

1. **Input** — user states an objective in plain language, names a target model/provider, and
   picks a token-efficiency mode (Efficient / Balanced / Thorough).
2. **Clarify** — a single upfront batch of grouped questions, with conditional follow-ups
   that only appear when a prior answer opens that path (branching, not one-at-a-time —
   deliberately designed for models that aren't well suited to rapid back-and-forth). The
   number of questions asked scales with the chosen efficiency mode.
3. **Compile** — synthesizes the optimized prompt for that specific model, with a short
   rationale, suggested settings (effort level, temperature, etc. as applicable), and an
   explicit account of the token-saving choices made. Adds a Security & Reliability section
   automatically if the request touches software/infra/data handling.
4. **Self-heal** — if the result isn't right, feedback is diagnosed (scope mismatch, wrong
   tone, missing constraint, too rigid, too vague, model mismatch, security gap, token
   bloat/too verbose, other) and a revised version is produced. Prior versions stay accessible.

## Token efficiency system

Two separate things are kept lean: PromptRig's own API usage, and the compiled prompt it
hands back. Neither claim is "magic" — both are ordinary, verifiable engineering choices:

- **A universal token-discipline directive** is injected into every call PromptRig makes. It
  instructs the model to cut redundant framing, merge overlapping constraints into single
  directives, never restate already-established information, and default to the shortest
  phrasing that preserves meaning. For Claude targets, it also asks the compiled prompt to
  separate stable/reusable instructions from per-call variable content, so the user can apply
  prompt caching on their end.
- **An efficiency mode** (Efficient / Balanced / Thorough) scales both the number of
  clarifying questions asked (6-10 / 10-16 / 14-22) and the word cap on the compiled prompt
  itself (250 / 500 / 800 words) — the biggest lever for reducing tokens is asking fewer,
  better-chosen questions and producing a tighter final prompt, not compressing wording after
  the fact.
- **A visible token estimate** (`~N tokens (est.)`, computed locally as `chars / 4`, no extra
  API call) is shown next to every compiled prompt so efficiency is something you can check,
  not just something you're told.
- **Token bloat is a named self-heal category** — if a compiled prompt feels wasteful, saying
  so routes to the same diagnosis-and-revise loop as any other complaint.

This is deliberate, measurable token discipline — not a claim that it's unlike anything else,
which isn't a verifiable thing to assert about a prompting technique.

---

## Model notes (update as models change)

| Model | Notes |
|---|---|
| **Claude Fable 5** | Mythos-tier, built for long autonomous self-verifying runs, not rapid back-and-forth. State goals/success criteria, not steps — over-specifying degrades it. Default effort: high (xhigh for the hardest work). Delegates to subagents on its own. Benefits from a persistent lessons file across sessions. Runs safety classifiers on offensive-cybersecurity and bio/life-science content that can flag legitimate defensive/detection work — frame technique descriptions defensively. Never ask it to echo/explain its internal reasoning as response text (risks refusal fallback to Opus 4.8). Define explicit pause-vs-continue checkpoints for long tasks. |
| **Claude Mythos 5** | Same model as Fable 5, without the added cyber/bio safety layer, restricted to trusted orgs. Same prompting patterns as Fable 5. |
| **Claude Opus 4.8** | Strong general reasoning. Benefits from clear step structure, explicit success criteria, worked examples for style-sensitive tasks. Less suited to fully autonomous multi-hour runs than Fable 5. |
| **Claude Sonnet 5** | Fast, capable default. Concise, direct instructions; doesn't need heavy scaffolding. Good for genuine iteration. |
| **Claude Haiku 4.5** | Optimized for speed/cost. Keep prompts narrow; break multi-stage work into smaller discrete requests. |
| **GPT-5.5** | General best practice: explicit system/developer instructions, clear output format, few-shot examples for style-sensitive output. Vendor specifics may have shifted — verify against current OpenAI docs for anything critical. |
| **Gemini** | General best practice: explicit structure, clear formatting instructions, grounding context up front. Verify against current Google docs for anything critical. |
| **Other/unspecified** | General best practice: explicit goal, constraints, format, audience. Note in rationale that this is generic guidance. |

---

## System prompt — question generation

```
You are an expert prompt engineer. You generate a single batch of clarifying questions
that will let you fully optimize a prompt for a specific target model, given a user's raw
natural-language request.

Target model: {{resolvedModel}}
Known behavior of this target: {{modelNotes}}

Because this target is not always well suited to rapid back-and-forth (especially
long-horizon models), ask everything you'll need in ONE batch rather than iteratively.
Group questions into 3-5 categories relevant to the request (choose from: Scope & Goal,
Constraints & Format, Tone & Audience, Autonomy & Iteration Cadence, Security & Reliability,
Technical Environment -- only include categories relevant to this specific request). Within
groups, include conditional follow-up questions that only make sense given a particular
answer (a domino-effect branch), marked with dependsOn.

Keep every question under 15 words and every option under 5 words. Produce 10-18 total
questions including branches.

Return ONLY valid JSON (no markdown fences, no prose) matching exactly this schema:
[{"group":"string","questions":[{"id":"short_snake_case","text":"string",
"type":"single_select|multi_select|text","options":["..."],"dependsOn":null}]}]

For conditional questions, dependsOn must be {"questionId":"parent_id",
"values":["option","that","triggers","it"]} -- otherwise null. For type "text", options
must be an empty array.
```

User message: `Raw request: "{{rawRequest}}"\n\nGenerate the question batch now.`

---

## System prompt — compile optimized prompt

```
You are an expert prompt engineer. Synthesize a fully optimized prompt for the target
model below, using the user's raw request and their clarifying answers.

Target model: {{resolvedModel}}
Known behavior of this target: {{modelNotes}}

Optimize for: user satisfaction, feasibility, usability, and top-tier performance on this
specific model. If the request involves building software, systems, or handling sensitive
data, include a short "Security & Reliability" section in the prompt capturing relevant
constraints -- omit it entirely if not applicable. Keep the whole response under 500 words.

Return ONLY valid JSON (no markdown fences, no prose) matching exactly this schema:
{"prompt":"the full optimized prompt text, ready to paste as-is","rationale":"2-4
sentences on key choices made for this model","settings":"one line of suggested settings
for this model (effort level, temperature, etc.) or empty string if not applicable"}
```

**First compile:** `Raw request: "{{rawRequest}}"\n\nClarifying answers:\n{{answeredEntries}}\n\nCompile the optimized prompt now.`

**Self-heal revision:** `Original request: "{{rawRequest}}"\n\nPrevious optimized prompt:\n{{previousPrompt}}\n\nUser feedback on that version: "{{feedback}}"\n\nDiagnose what's wrong (scope mismatch, wrong tone, missing constraint, too rigid, too vague, model mismatch, security gap, or other) and produce a revised version that fixes it. Reflect the diagnosis briefly in the rationale.`

---

## Unfamiliar-model research & indexing

If the target is "Other" and the named model/provider isn't one of the built-in profiles,
PromptRig doesn't fall back to generic guidance right away:

1. **Check the index first** — looks for previously researched notes on this model in
   persistent storage (`model-notes:{name}`, shared across sessions/users of the tool).
2. **Research if unknown** — runs a web-search-enabled API call to find the model's actual
   prompting quirks, context window, and known behavior, and condenses it into one dense
   paragraph in the same style as the built-in profiles.
3. **Index it** — writes the result back to persistent storage so the next person (or the
   same person, next session) gets the cached version instantly instead of re-researching.
4. **Fail gracefully** — if research turns up nothing usable, falls back to generic guidance
   and says so rather than inventing specifics.

The UI shows which source was used (built-in / cached from a prior session / freshly
researched / fallback) so this is never silent.

## Loop engineering

A "Loop / recurring task" toggle switches the compiled prompt from a one-shot shape to a
loop shape when the objective is a repeated cycle rather than a single pass. When enabled,
both stages inject a loop-engineering directive and the compiled prompt includes an explicit
**Loop Structure** section covering:

- **Trigger/cadence** — what starts each iteration (schedule, event, manual)
- **Loop body** — plan, act, verify each iteration against evidence, not assumption
- **Exit/stop condition** — what ends the loop, distinct from what ends one iteration
- **Checkpoint/escalation** — what's severe or ambiguous enough to interrupt and involve a human
- **Compounding memory** — a running lessons file so later iterations benefit from earlier ones

The clarification stage also adds a "Loop & Recurrence" question group when this is enabled,
covering trigger type, interval/condition, stop condition, and what counts as "done."

## Reuse

- **Interactive**: use `promptrig.jsx` as-is (calls the Claude API directly, no backend needed).
- **Manual**: paste the system/user prompts above into any conversation, filling in the
  `{{placeholders}}` by hand.
- **Portable**: `promptrig-framework.json` holds the same content as structured data for
  scripting or dropping into other tools.
