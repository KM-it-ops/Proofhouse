# Proofhouse

[![CI](https://github.com/KM-it-ops/Proofhouse/actions/workflows/ci.yml/badge.svg)](https://github.com/KM-it-ops/Proofhouse/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-111827)](https://github.com/KM-it-ops/Proofhouse/blob/main/LICENSE)

**You say what you want. You pick any model, from any provider. Proofhouse makes it, runs it, improves it, and keeps every version.**

A prompt, a skill, a website, an app, a video, or a whole launch. Proofhouse writes it with the model you name, tries it for real, has a judge score it, revises it, and keeps each version with what it cost. A model on your machine costs nothing. A paid model needs a spending limit.

It is a local command-line tool, not a hosted service. The `proofhouse` command is the one front door.

**Host mode (no API key):** use `proofhouse check`, `proofhouse record` and `proofhouse render video` when your existing AI app writes and judges; see [docs/usage.md](docs/usage.md#host-mode-no-api-key).

## Try it in two minutes

```bash
uv tool install proofhouse
proofhouse demo
```

`proofhouse demo` runs a full example offline. It needs no key and calls no model. With pip: `python -m pip install proofhouse`. On Windows, set `$env:PYTHONUTF8='1'` first for reliable console output.

## What it makes

| You want | Command |
|---|---|
| A prompt, skill, agent or announcement copy | `proofhouse make "a prompt that answers refund emails warmly" --provider ollama --model llama3` |
| A rule, MCP server (a tool an AI app can call) or hook (a small program a coding tool runs on events) | `proofhouse make "..." --kind mcp` |
| A website | `proofhouse make "a landing page for my bakery" --kind site` |
| An app for the web, Windows, macOS, Linux, iOS or Android | `proofhouse make "..." --kind app --platform pwa --platform android` |
| Images, voice, music | `proofhouse generate image --provider openai-images --model gpt-image-1 --prompt "a red fox"` |
| A finished video with voice, music and captions | `proofhouse make "a 30-second hype video for my app" --kind video` |
| A whole launch: site, video, copy and more from one goal | `proofhouse make "launch my app" --kind launch` |
| An agent that keeps working on its own, within limits | `proofhouse loop "make the tests pass" --check "pytest -q" --allow-commands` |
| A fine-tuned model | `proofhouse train start --service openai --model <base-model> --data my-data` |

Not sure which kind fits? `proofhouse "<what you want>"` picks one. A kind Proofhouse has never made is researched by your chosen model and learned as an add-on, never refused for being new.

Run any prompt on any provider, or the same job on many models at once with a score, a cost and a side-by-side page:

```bash
proofhouse run --provider mistral --model mistral-large --prompt "Say hi" --max-cost-usd 0.05
proofhouse compare "Summarise this contract in five bullet points." --input-file contract.txt   --on anthropic:<model> --on openai:<model> --on ollama:llama3 --judge anthropic:<model>
```

Put the result where you work. Agents, rules and MCP servers install into Claude Code, Cursor and Codex, and sites deploy to Netlify, Vercel, Cloudflare or Surge:

```bash
proofhouse install agent make-*/review-bot.md --into claude
proofhouse deploy make-landing-page-* --to netlify --dry-run
```

Every command, flag and option is in the [usage guide](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/usage.md).

## How it behaves

- **Any provider, any model.** OpenAI, Anthropic, Google, Mistral, Groq, Together, Fireworks, OpenRouter, DeepSeek, xAI, models on your own machine (Ollama, LM Studio, vLLM, llama.cpp), or anything else you add with one command. Providers are data, not code.
- **A spending limit on every paid call.** A call is refused before it is sent if its worst-case estimate is over your `--max-cost-usd`, or if the model has no price. Dollar figures are estimates, not your bill.
- **Your keys stay in your environment.** Proofhouse reads them from there when a call is made.
- **Every version is kept** with its test output, score and cost, in one folder. Judge scores are a model's advice, not proof.
- **Commands run only when you allow them.** Made MCP servers, hooks and app builds run model-written code with your rights, so they run only with `--allow-commands`. That flag is an opt-in, not isolation.
- **No benchmark claims.** Model notes are prompting guidance; any profile that cites no source is labeled unverified.
- **An optional evidence trail.** `proofhouse case` records constraints, outputs and checks so a PASS names exactly what it came from. It does not call a model and does not rate quality. See [the evidence trail](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/evidence-trail.md).

---

## Supported models (framework v1.3)

Built-in `modelNotes` cover prompting quirks, API ids, and cost and caching levers for each model:

<!-- supported-models:begin -->
| Tier | Models |
|---|---|
| **Anthropic** | Claude Fable 5.1 · Opus 5.5 · Sonnet 5.5 · Haiku 5.5 · Mythos 5.1 |
| **OpenAI** | GPT-6 Astra · GPT-6.1 Sol · GPT-6 Sol · GPT-6 Luna |
| **Google** | Gemini 4 Argon · Gemini 3.8 Flash |
| **xAI** | Grok 4.7 |
| **Meta** | Muse Spark 1.3 |
| **Moonshot** | Kimi K3 |
| **Legacy** | Opus 5 · Sonnet 5 · Haiku 4.5 · GPT-5.6 Sol · Terra · Luna · GPT-5.5 · Grok 4.6 · Gemini (generic) · Fable 5 · Mythos 5 · Opus 4.8 |
| **Other** | Skill and artifact: the host agent or the artifact web-researches the model and caches the paragraph. CLI (`proofhouse`): offline; `models remember` stores your own notes, otherwise the generic profile is used and labeled `fallback`. |

Profiles last reviewed 2026-10-18; a profile older than 90 days is flagged stale. 10 of 27 profiles cite sources; the rest are labeled unverified. They are prompting guidance, not vendor specifications. `proofhouse models list` shows per-model ids, aliases, and dates.

Full profiles: [`proofhouse-framework.json`](proofhouse-framework.json) · human-readable [`proofhouse-framework.md`](proofhouse-framework.md)
<!-- supported-models:end -->

---

## Learn more

- [Usage guide](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/usage.md): every way to make, run and deliver
- [Evidence trail](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/evidence-trail.md) · [Reference workflow](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/reference-workflow.md) · [Providers](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/providers.md)
- [Product scope](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/product-scope.md) · [Architecture](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/architecture.md) · [Surfaces and contracts](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/surfaces.md)
- [Development and checks](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/development.md) · [Contributing](https://github.com/KM-it-ops/Proofhouse/blob/main/CONTRIBUTING.md) · [Changelog](https://github.com/KM-it-ops/Proofhouse/blob/main/CHANGELOG.md) · [Security policy](https://github.com/KM-it-ops/Proofhouse/blob/main/SECURITY.md)
- [Releases](https://github.com/KM-it-ops/Proofhouse/releases): what changed in each version and how it was checked

<sub>MIT License</sub>
