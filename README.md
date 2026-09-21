# Proofhouse

[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-v1.3-7c3aed)](proofhouse-framework.json)
[![PromptOps](https://img.shields.io/badge/promptops-clarify%20%E2%86%92%20compile%20%E2%86%92%20heal-0f766e)](#why-proofhouse-exists)
[![License](https://img.shields.io/badge/license-MIT-111827)](LICENSE)

**A local workspace for revising prompts with evidence you can trace: every PASS names the exact prompt, outputs, checks and judgements it came from.**

I built Proofhouse because I kept rewriting the same prompt for different models and never had a good answer for which version was better, or whether a revision had quietly dropped a requirement. You give it an objective and a target model; it asks its clarifying questions in one batch and turns your answers into constraints that every later revision must keep. You record each prompt revision and the outputs a model actually produced, declare the checks that matter, and Proofhouse tells you which revision passes, which constraint lacks evidence, and what changed between revisions.

Version 0.3.0 ships two command-line tools in one Python package: `proofhouse-compiler`, an offline compiler, and `proofhouse`, an eval harness. It runs on your machine with no API key: you run the generated packets in the agent or model you already use and paste the results back. It is a local tool, not a hosted service, and I make no benchmark or quality claims for it.

**Try it:** `uv sync --extra test` then `uv run python scripts/reference_workflow.py` runs the [reference workflow](docs/reference-workflow.md): a security-advisory summary whose first revision invents an exploitation claim and fails, and whose second revision passes without losing a constraint.

Portfolio: [km-it-ops.github.io](https://km-it-ops.github.io/) · Skill: `skills/proofhouse/` · Showcase: [docs/showcase.md](docs/showcase.md)

## What a PASS proves, and what it does not

| A PASS from `optimize check` means | It does not mean |
|---|---|
| Every check you declared passed on this exact revision (and, for output checks, on the outputs you recorded) | That the prompt is good in general, or better than one you did not test |
| Every accepted constraint is linked to a check that passed | That a model will reproduce the recorded outputs |
| Each human verdict applies to the exact text and check definition you judged | That model notes are correct: shipped profiles cite no sources yet and are labeled `unverified` |
| Nothing was edited after it was recorded (digests are re-checked) | That the files are tamper-proof against someone who controls your machine |

The `closed-loop` compiler command reports a structural check (the prompt compiles offline and passes security gates); its evidence lists what it did not measure. Details: [docs/architecture.md](docs/architecture.md), [decision 0002](docs/decisions/0002-what-pass-means.md).

## Maturity at a glance

| Surface | Status | Network |
|---|---|---|
| `proofhouse-compiler optimize` case workflow (constraints, revisions, outputs, checks, compare, report, export/import) | supported | none |
| `models`, `install-skill`, `validate` / `compile` / `closed-loop` | supported | none |
| Cursor skill | supported entry point | host agent's tools |
| `execute-openai` | experimental, opt-in | yes, only when opted in; budget recorded, not enforced |
| `evaluate-product`, requirements-contract commands, `route` / `assay` / `proof` | experimental | none |
| `apps/proofhouse.jsx` artifact | experimental | calls `api.anthropic.com` |
| `apps/dashboard/`, `hosted-*` slices | prototypes | none |

Full map with versions and diagnostic codes: [docs/surfaces.md](docs/surfaces.md).

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

Profiles last reviewed 2026-09-03; a profile older than 90 days is flagged stale. None of the 18 profiles cites sources yet, so every profile is labeled unverified. They are prompting guidance, not vendor specifications. `proofhouse-compiler models list` shows per-model ids, aliases, and dates.

Full profiles: [`proofhouse-framework.json`](proofhouse-framework.json) · human-readable [`proofhouse-framework.md`](proofhouse-framework.md)
<!-- supported-models:end -->

---

## Surfaces (what runs where)

| Surface | Entry | Runs | Network | Model notes | Unknown model |
|---|---|---|---|---|---|
| Conversational skill | `proofhouse-compiler install-skill`, then "Proofhouse" in a new Cursor chat | host agent (Cursor) | host agent's tools | `references/proofhouse-framework.json` `modelNotes` + `modelRegistry` (`verifiedAt`) | host agent may web-research and reuse within the conversation |
| Interactive artifact | `apps/proofhouse.jsx` as a Claude artifact | Claude artifact runtime | calls `api.anthropic.com` | `MODEL_NOTES` in the JSX | web-researches, caches in artifact storage, labels `researched`/`cached`/`fallback` |
| Offline compiler | `proofhouse-compiler` | your machine | none (`execute-openai` is opt-in) | `models list/show/remember/forget`, local cache under `~/.proofhouse` | **no research**: your notes via `models remember`, else generic `fallback` |
| Eval harness | `proofhouse` | your machine | none | n/a | n/a |

`proofhouse-compiler optimize` renders the framework's clarify / compile / self-heal prompts as packets you run in the host agent or model of your choice, keeps your answers as constraints, records revisions and the outputs you paste back, and checks them against criteria you declare. It does not call a model and it does not rate quality.

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

Approved headless profiles: `structured_minimal_v0`, `structured_developer_v0`. The tested path is **offline** (fake adapter, no network) and its PASS is structural. `proofhouse-compiler execute-openai` is a fail-closed, **opt-in** live OpenAI path: every mandatory requirement is rendered into the request or it refuses before sending, and its cost ceiling is recorded, not enforced. It is experimental. No benchmark claims.

---

## Install and verify

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
uv run python scripts/reference_workflow.py --quiet     # reference workflow: OK
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
examples/               Demo inputs (ir_minimal.json, prompt-audit request) and reference-advisory/ for the reference workflow
scripts/                Generators (model surfaces, skill bundle, contracts) and reference_workflow.py
src/proofhouse/          Stdlib eval harness + headless compiler + optimize (cases, constraints, runs, checks, export)
docs/                   Scope, architecture, surfaces, evidence format, decisions, assurance statements
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

The **headless compiler** under `src/proofhouse/compiler/` is a contract-first offline pipeline, and its requirements-compiler maturity is still `PARTIAL`. The tested path is offline: fake adapter, no network. `proofhouse-compiler execute-openai` is a fail-closed, opt-in live OpenAI path and is experimental. The `hosted-*` and `missionrig-*` modules are experimental library slices, not a hosted service, and their tenant label is not isolation. `apps/proofhouse.jsx` calls the Anthropic Messages API when run as a Claude artifact and is experimental. None of this comes with benchmark claims.

Internal mission reports and review corpora are not published in this repository; public decisions are summarized in [docs/decisions/](docs/decisions/), and each assurance statement in [docs/assurance/](docs/assurance/) lists the exact revision, commands, results and exclusions.

---

## Start here

- [Reference workflow](docs/reference-workflow.md): one failed check to a verified fix, offline
- [Product scope](docs/product-scope.md) · [Architecture](docs/architecture.md) · [Surfaces and contracts](docs/surfaces.md) · [Evidence format](docs/evidence-format.md)
- [Decision records](docs/decisions/) · [Assurance statements](docs/assurance/) · [Troubleshooting](docs/troubleshooting.md)
- [Showcase](docs/showcase.md): pitch, demo flow, outcomes
- [Quickstart](docs/quickstart.md)
- [Custom GPT setup](docs/custom-gpt-setup.md)
- [Security policy](SECURITY.md)

---

<sub>Custom GPT surface: <strong>PromptOps Architect powered by Proofhouse</strong> · MIT License</sub>
