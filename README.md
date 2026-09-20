# Proofhouse

[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-v1.3-7c3aed)](proofhouse-framework.json)
[![PromptOps](https://img.shields.io/badge/promptops-clarify%20%E2%86%92%20compile%20%E2%86%92%20heal-0f766e)](#the-flow)
[![License](https://img.shields.io/badge/license-MIT-111827)](LICENSE)

**Turn a rough objective into a model-specific prompt that actually works — then prove it.**

Proofhouse is a PromptOps framework for builders who care about *which* model runs the job, not just *what* you asked. Natural language in → batched clarification → optimized prompt out → self-heal when it misses. Built-in profiles for **September 2026 frontier models**, token discipline, loop engineering for recurring agents, and an offline eval harness — no API keys required for the certified headless path.

Portfolio: [km-it-ops.github.io](https://km-it-ops.github.io/) · Skill: `skills/proofhouse/` · Showcase: [docs/showcase.md](docs/showcase.md)

---

## Why Proofhouse exists

Generic prompts fail quietly: wrong model assumptions, missing context, no stop conditions, no regression tests. Proofhouse treats prompts like production infrastructure:

| Stage | What happens |
|---|---|
| **Clarify** | One upfront batch of branching questions — not drip-feed back-and-forth |
| **Compile** | Model-specific prompt + settings + token-saving rationale |
| **Evaluate** | JSONL cases, YAML rubrics, stdlib CLI validation |
| **Self-heal** | Diagnose scope/tone/bloat/model-mismatch and revise without losing history |

Designed for coding agents, Custom GPTs, Cursor skills, and cyber×AI workflows where inventing facts or skipping safety boundaries is unacceptable.

---

## Supported models (framework v1.3)

Built-in `modelNotes` — prompting quirks, API ids, cost/caching levers:

| Tier | Models |
|---|---|
| **Anthropic** | Claude Fable 5.1 · Mythos 5.1 · Opus 5 · Sonnet 5 · Haiku 4.5 |
| **OpenAI** | GPT-5.6 Sol · Terra · Luna |
| **Google** | Gemini 3.8 Flash |
| **xAI** | Grok 4.6 |
| **Meta** | Muse Spark 1.3 |
| **Moonshot** | Kimi K3 |
| **Legacy** | Fable 5 · Mythos 5 · Opus 4.8 · GPT-5.5 · Gemini (generic) |
| **Other** | Auto-research via web search, cached for reuse |

Full profiles: [`proofhouse-framework.json`](proofhouse-framework.json) · human-readable [`proofhouse-framework.md`](proofhouse-framework.md)

---

## Three ways to use it

### 1. Conversational (default)

Install the Cursor skill (the bundle is the zipped `skills/proofhouse/` directory; `tests/test_skill_bundle.py` keeps them identical):

```powershell
# Windows PowerShell, from the repository root
uv run python -m zipfile -e skills/proofhouse/proofhouse.skill "$env:USERPROFILE\.cursor\skills"
```

```bash
# macOS / Linux
python -m zipfile -e skills/proofhouse/proofhouse.skill ~/.cursor/skills
```

This lands `~/.cursor/skills/proofhouse/SKILL.md`, the user-level location Cursor scans for skills. Start a **new** Agent chat afterwards; then say **Proofhouse** and:

1. State your objective and target model
2. Answer one batched clarification form
3. Paste the compiled prompt; say what's wrong to self-heal

### 2. Interactive artifact

Open [`apps/proofhouse.jsx`](apps/proofhouse.jsx) — a React artifact with model picker, efficiency modes, and live compile loop. This artifact calls `https://api.anthropic.com/v1/messages` and is not offline.

### 3. Offline compiler (reproducible)

```bash
uv sync --extra test
uv run proofhouse-compiler doctor
uv run proofhouse-compiler closed-loop tests/compiler/fixtures/closed_loop_requirements_minimal.json --repair-budget 1
uv run proofhouse-compiler validate examples/ir_minimal.json
uv run proofhouse-compiler compile examples/ir_minimal.json --adapter fake --adapter-version 0.1.0 --output build/demo
```

Approved headless profiles: `structured_minimal_v0`, `structured_developer_v0`. Certified path is **offline** (fake adapter, no network). `proofhouse-compiler execute-openai` is fail-closed **opt-in** live OpenAI and is **not** certified. No benchmark claims.

---

## 30-second start

Two console scripts ship in one package: `proofhouse-compiler` (offline compiler) and `proofhouse` (offline eval harness).

| Command | Surface | Subcommands |
|---|---|---|
| `proofhouse-compiler` | Compiler: requirements → IR → adapter artifact → evaluation/repair evidence | `doctor` `validate` `inspect` `compile` `closed-loop` `adapters` |
| `proofhouse` | Eval harness: JSONL datasets, rubrics, report skeletons | `validate` `report` `loadouts` `compile-loadout` `generate` |

Clean clone with [uv](https://docs.astral.sh/uv/) (tested on Windows; the same commands work in bash without the `$env:` line):

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
src/proofhouse/          Stdlib eval harness + headless compiler
tests/fixtures/         Contract schemas and validation fixtures
```

---

## Design rules

- Stay lightweight by default; tighten only for safety, agentic execution, or missing context.
- Never invent repository or project facts.
- Use exact missing-context labels: `UNKNOWN`, `NOT SPECIFIED`, `NOT FOUND IN PROVIDED MATERIAL`.
- Keep cybersecurity and sensitive-data work defensive, authorized, and privacy-preserving.
- No private chain-of-thought dumps — concise rationales only.

---

## Engineering status

Proofhouse ships two products in one repo:

1. **PromptOps skill + framework (v1.3)** — conversational meta-optimizer with current frontier model profiles. This is the user-facing surface most people want today.
2. **Headless compiler** — contract-first offline pipeline under `src/proofhouse/compiler/`. Requirements compiler maturity remains `PARTIAL`. Certified path is **offline** (fake adapter, no network). `proofhouse-compiler execute-openai` is fail-closed **opt-in** live OpenAI and is **not** certified. `hosted-*` / `missionrig-*` are experimental library slices, not a hosted UI (DFR-006/008). `apps/proofhouse.jsx` calls the Anthropic Messages API when run as a Claude artifact and is **not** the certified path. No benchmark claims.

Internal mission reports and review corpora are not published in this repository.

---

## Start here

- [Showcase](docs/showcase.md) — pitch, demo flow, outcomes
- [Quickstart](docs/quickstart.md)
- [Custom GPT setup](docs/custom-gpt-setup.md)
- [Security policy](SECURITY.md)

---

<sub>Custom GPT surface: <strong>PromptOps Architect powered by Proofhouse</strong> · MIT License</sub>
