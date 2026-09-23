# Proofhouse

[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-v1.3-7c3aed)](proofhouse-framework.json)
[![PromptOps](https://img.shields.io/badge/promptops-clarify%20%E2%86%92%20compile%20%E2%86%92%20heal-0f766e)](#why-proofhouse-exists)
[![License](https://img.shields.io/badge/license-MIT-111827)](LICENSE)

**Turn a rough objective into a prompt built for a specific model, then check that it actually works.**

I built Proofhouse because I kept rewriting the same prompt for different models and never had a good answer for which version was better. It takes a plain-language objective, asks its clarifying questions in one batch instead of a drip, compiles a prompt tuned for the model you named, and evaluates the result against cases you control. When the output misses, it diagnoses why (scope, tone, bloat, wrong model assumptions) and revises without throwing away the history.

Version 0.3.0 ships two command-line tools in one Python package: `proofhouse-compiler`, an offline compiler, and `proofhouse`, an eval harness. The certified path runs entirely on your machine with no API key. There is a Cursor skill if you want the conversational flow. This is a local tool, not a hosted service, and I make no benchmark claims for it.

Portfolio: [km-it-ops.github.io](https://km-it-ops.github.io/) · Skill: `skills/proofhouse/` · Showcase: [docs/showcase.md](docs/showcase.md)

---

## Why Proofhouse exists

Most prompts fail quietly. The model assumptions are wrong, context is missing, there is no stop condition, and nobody wrote a regression test. Proofhouse treats a prompt the way you would treat any other piece of infrastructure: specify it, compile it, test it, repair it.

| Stage | What happens |
|---|---|
| **Clarify** | One upfront batch of branching questions, not a back-and-forth |
| **Compile** | A model-specific prompt, settings, and a short note on why each token is there |
| **Evaluate** | JSONL cases, YAML rubrics, stdlib CLI validation |
| **Self-heal** | Diagnose scope, tone, bloat, or model mismatch and revise without losing history |

It was designed for coding agents, Custom GPTs, Cursor skills, and security-adjacent AI work, where inventing facts or skipping a safety boundary is not acceptable.

---

## Supported models (framework v1.3)

Built-in `modelNotes` cover prompting quirks, API ids, and cost and caching levers for each model:

<!-- supported-models:begin -->
| Tier | Models |
|---|---|
| **Anthropic** | Claude Fable 5.1 · Mythos 5.1 · Opus 5 · Sonnet 5 · Haiku 4.5 |
| **OpenAI** | GPT-5.6 Sol · Terra · Luna |
| **Google** | Gemini 3.8 Flash |
| **xAI** | Grok 4.6 |
| **Meta** | Muse Spark 1.3 |
| **Moonshot** | Kimi K3 |
| **Legacy** | GPT-5.5 · Gemini (generic) · Fable 5 · Mythos 5 · Opus 4.8 |
| **Other** | Skill and artifact: the host agent or the artifact web-researches the model and caches the paragraph. CLI (`proofhouse-compiler`): offline; `models remember` stores your own notes, otherwise the generic profile is used and labeled `fallback`. |

Profiles verified 2026-09-03; a profile older than 90 days is flagged stale. `proofhouse-compiler models list` shows per-model ids, aliases, and dates.

Full profiles: [`proofhouse-framework.json`](proofhouse-framework.json) · human-readable [`proofhouse-framework.md`](proofhouse-framework.md)
<!-- supported-models:end -->

---

## Surfaces (what runs where)

| Surface | Entry | Runs | Network | Model notes | Unknown model |
|---|---|---|---|---|---|
| Conversational skill | `proofhouse-compiler install-skill`, then "Proofhouse" in a new Cursor chat | host agent (Cursor) | host agent's tools | `references/proofhouse-framework.json` `modelNotes` + `modelRegistry` (`verifiedAt`) | host agent may web-research and reuse within the conversation |
| Interactive artifact | `apps/proofhouse.jsx` as a Claude artifact | Claude artifact runtime | calls `api.anthropic.com` | `MODEL_NOTES` in the JSX | web-researches, caches in artifact storage, labels `researched`/`cached`/`fallback` |
| Offline compiler | `proofhouse-compiler` | your machine | none on the certified path (`execute-openai` is opt-in) | `models list/show/remember/forget`, local cache under `~/.proofhouse` | **no research**: your notes via `models remember`, else generic `fallback` |
| Eval harness | `proofhouse` | your machine | none | n/a | n/a |

`proofhouse-compiler optimize` renders the framework's clarify / compile / self-heal prompts as packets you run in the host agent or model of your choice, records revisions, and checks them against criteria you declare. It does not call a model and it does not score quality.

---

## Three ways to use it

### 1. Conversational (default)

Install the Cursor skill with the console script (the bundle ships inside the package; `tests/test_skill_bundle.py` keeps it identical to `skills/proofhouse/`):

```powershell
uv run proofhouse-compiler install-skill        # -> ~/.cursor/skills/proofhouse, verifies name: proofhouse
```

Equivalent without the script: `python -m zipfile -e skills/proofhouse/proofhouse.skill ~/.cursor/skills`. Start a **new** Agent chat afterwards, say **Proofhouse**, and then:

1. State your objective and target model
2. Answer one batched clarification form
3. Paste the compiled prompt; say what's wrong to self-heal

### 2. Interactive artifact

Open [`apps/proofhouse.jsx`](apps/proofhouse.jsx), a React artifact with a model picker, efficiency modes, and a live compile loop. This artifact calls `https://api.anthropic.com/v1/messages` and is not offline.

### 3. Offline compiler (reproducible)

```bash
uv sync --extra test
uv run proofhouse-compiler doctor
uv run proofhouse-compiler closed-loop tests/compiler/fixtures/closed_loop_requirements_minimal.json --repair-budget 1
uv run proofhouse-compiler validate examples/ir_minimal.json
uv run proofhouse-compiler compile examples/ir_minimal.json --adapter fake --adapter-version 0.1.0 --output build/demo
```

Approved headless profiles: `structured_minimal_v0`, `structured_developer_v0`. The certified path is **offline** (fake adapter, no network). `proofhouse-compiler execute-openai` is a fail-closed, **opt-in** live OpenAI path and is **not** certified. No benchmark claims.

---

## 30-second start

Two console scripts ship in one package: `proofhouse-compiler` (offline compiler) and `proofhouse` (offline eval harness).

| Command | Surface | Subcommands |
|---|---|---|
| `proofhouse-compiler` | Compiler: requirements → IR → adapter artifact → evidence; plus offline optimize packets, model-notes cache, skill installer | `doctor` `validate` `inspect` `compile` `closed-loop` `adapters` `optimize` `models` `install-skill` |
| `proofhouse` | Eval harness: JSONL datasets, rubrics, report skeletons | `validate` `report` `loadouts` `compile-loadout` `generate` |

Clean clone with [uv](https://docs.astral.sh/uv/). Tested on Windows; the same commands work in bash without the `$env:` line.

```powershell
git clone https://github.com/KM-it-ops/Proofhouse.git
cd Proofhouse
$env:PYTHONUTF8='1'                                     # Windows: reliable console output
uv sync --extra test                                    # package + pytest into .venv
uv run proofhouse-compiler doctor                       # doctor: success
uv run proofhouse-compiler closed-loop tests/compiler/fixtures/closed_loop_requirements_minimal.json --repair-budget 1
                                                        # closed-loop: PASS
uv run proofhouse validate --dataset evals/datasets/prompt_audit_cases.jsonl
                                                        # Dataset validation passed: ...
uv run pytest -q                                        # all passed, 1 deselected (live tests are opt-in)
```

pip alternative (same result, your own venv):

```bash
python -m pip install -e ".[test]"
python -m pytest -q
```

Everything above is offline: fake adapter, no network, no API key. Nothing here is a benchmark.

---

## What you get

| Capability | Outcome |
|---|---|
| Meta-optimizer | Clarify → compile → self-heal with model-specific behavior |
| Token discipline | Efficient / Balanced / Thorough presets; cache-aware prompt structure |
| Loop engineering | Trigger, body, exit, escalation, compounding memory for recurring agents |
| Prompt architecture | Core prompt, modes, modules, project context templates |
| Audits | Missing-context labels, safety boundaries, rewrite notes |
| Agentic design | Permission maps, tool boundaries, verification loops, stop conditions |
| Evals | JSONL datasets, YAML rubrics, schema checks, report skeletons |
| Skill pack | Cursor skill + portable `proofhouse-framework.*` |

---

## Repository map

```text
proofhouse-framework.*   Portable meta-optimizer spec (v1.3 model profiles)
skills/proofhouse/       Cursor skill bundle + artifact JSX
apps/proofhouse.jsx      Interactive compile UI
prompts/                Core, modes, modules, Custom GPT pack
evals/                  JSONL datasets, YAML rubrics
examples/               Static demo inputs (examples/ir_minimal.json) and a prompt-audit request
src/proofhouse/          Stdlib eval harness + headless compiler + optimize (registry, packets, cases, cache)
tests/fixtures/         Contract schemas and validation fixtures
```

---

## Design rules

- Stay lightweight by default. Tighten only for safety, agentic execution, or missing context.
- Never invent repository or project facts.
- Use exact missing-context labels: `UNKNOWN`, `NOT SPECIFIED`, `NOT FOUND IN PROVIDED MATERIAL`.
- Keep cybersecurity and sensitive-data work defensive, authorized, and privacy-preserving.
- No private chain-of-thought dumps. Concise rationales only.

---

## Where things stand

Proofhouse is two products in one repo, at different levels of maturity.

The **PromptOps skill and framework (v1.3)** is the conversational meta-optimizer with current frontier model profiles. It is the surface most people want, and it is the most mature part of the project.

The **headless compiler** under `src/proofhouse/compiler/` is a contract-first offline pipeline, and its requirements-compiler maturity is still `PARTIAL`. What is certified is the offline path: fake adapter, no network. `proofhouse-compiler execute-openai` is a fail-closed, opt-in live OpenAI path and is **not** certified. The `hosted-*` and `missionrig-*` modules are experimental library slices, not a hosted UI (DFR-006/008). `apps/proofhouse.jsx` calls the Anthropic Messages API when run as a Claude artifact and is not the certified path either. None of this comes with benchmark claims.

Internal mission reports and review corpora are not published in this repository.

---

## Start here

- [Showcase](docs/showcase.md): pitch, demo flow, outcomes
- [Quickstart](docs/quickstart.md)
- [Custom GPT setup](docs/custom-gpt-setup.md)
- [Security policy](SECURITY.md)

---

<sub>Custom GPT surface: <strong>PromptOps Architect powered by Proofhouse</strong> · MIT License</sub>
