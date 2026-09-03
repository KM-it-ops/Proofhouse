# PromptRig

[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-v1.3-7c3aed)](promptrig-framework.json)
[![PromptOps](https://img.shields.io/badge/promptops-clarify%20%E2%86%92%20compile%20%E2%86%92%20heal-0f766e)](#the-flow)
[![License](https://img.shields.io/badge/license-MIT-111827)](LICENSE)

**Turn a rough objective into a model-specific prompt that actually works — then prove it.**

PromptRig is a PromptOps framework for builders who care about *which* model runs the job, not just *what* you asked. Natural language in → batched clarification → optimized prompt out → self-heal when it misses. Built-in profiles for **September 2026 frontier models**, token discipline, loop engineering for recurring agents, and an offline eval harness — no API keys required for the certified headless path.

Portfolio: [km-it-ops.github.io](https://km-it-ops.github.io/) · Skill: `skills/promptrig/` · Showcase: [docs/showcase.md](docs/showcase.md)

---

## Why PromptRig exists

Generic prompts fail quietly: wrong model assumptions, missing context, no stop conditions, no regression tests. PromptRig treats prompts like production infrastructure:

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

Full profiles: [`promptrig-framework.json`](promptrig-framework.json) · human-readable [`promptrig-framework.md`](promptrig-framework.md)

---

## Three ways to use it

### 1. Conversational (default)

Install the Cursor skill from `skills/promptrig/` or invoke **PromptRig** in chat:

1. State your objective and target model
2. Answer one batched clarification form
3. Paste the compiled prompt; say what's wrong to self-heal

### 2. Interactive artifact

Open [`apps/promptrig.jsx`](apps/promptrig.jsx) — a React artifact with model picker, efficiency modes, and live compile loop.

### 3. Offline compiler (reproducible)

```bash
python -m pip install -e .
python -m pytest
promptrig-compiler doctor
promptrig-compiler closed-loop path/to/requirements.json --repair-budget 1 --json
```

Approved headless profiles: `structured_minimal_v0`, `structured_developer_v0`. Certified path is **offline** — no live providers, no benchmark claims. See [MISSION_011_REPORT.md](MISSION_011_REPORT.md).

---

## 30-second start

```bash
python -m pip install -e .
python -m pytest
python -m promptrig.cli validate --dataset evals/datasets/prompt_audit_cases.jsonl
python -m promptrig.cli report --dataset evals/datasets/prompt_audit_cases.jsonl --out evals/reports/prompt_audit_report.md
```

Windows:

```powershell
py -3.14 -m pip install -e .
py -3.14 -m pytest
```

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
| Skill pack | Cursor skill + portable `promptrig-framework.*` |

---

## Repository map

```text
promptrig-framework.*   Portable meta-optimizer spec (v1.3 model profiles)
skills/promptrig/       Cursor skill bundle + artifact JSX
apps/promptrig.jsx      Interactive compile UI
prompts/                Core, modes, modules, Custom GPT pack
evals/                  JSONL datasets, YAML rubrics
src/promptrig/          Stdlib eval harness + headless compiler
architecture/           Contract-first compiler missions (honesty-gated)
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

PromptRig ships two products in one repo:

1. **PromptOps skill + framework (v1.3)** — conversational meta-optimizer with current frontier model profiles. This is the user-facing surface most people want today.
2. **Headless compiler campaign** — contract-first offline pipeline (MISSION-008 through MISSION-036). Requirements compiler maturity remains `PARTIAL`. No live providers, no hosted UI, no benchmark claims without explicit certification.

Mission reports and acceptance records live under `architecture/` and `MISSION_*_REPORT.md`. Read those before claiming anything beyond the certified offline path.

---

## Start here

- [Showcase](docs/showcase.md) — pitch, demo flow, outcomes
- [Quickstart](docs/quickstart.md)
- [Custom GPT setup](docs/custom-gpt-setup.md)
- [Security policy](SECURITY.md)
- [Architecture governance](architecture/README.md)

---

<sub>Custom GPT surface: <strong>PromptOps Architect powered by PromptRig</strong> · MIT License</sub>
