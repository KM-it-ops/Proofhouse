# Proofhouse

[![CI](https://github.com/KM-it-ops/Proofhouse/actions/workflows/ci.yml/badge.svg)](https://github.com/KM-it-ops/Proofhouse/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-v1.3-7c3aed)](proofhouse-framework.json)
[![PromptOps](https://img.shields.io/badge/promptops-clarify%20%E2%86%92%20compile%20%E2%86%92%20heal-0f766e)](#how-it-works)
[![License](https://img.shields.io/badge/license-MIT-111827)](LICENSE)

**A local workspace for revising prompts with evidence you can trace: every PASS names the exact prompt, outputs, checks and judgements it came from.**

I built Proofhouse because I kept rewriting the same prompt for different models and never had a good answer for which version was better, or whether a revision had quietly dropped a requirement. You give it an objective and a target model; it asks its clarifying questions in one batch and turns your answers into constraints that every later revision must keep. You record each prompt revision and the outputs a model actually produced, declare the checks that matter, and Proofhouse tells you which revision passes, which constraint lacks evidence, and what changed between revisions.

It runs on your machine with no API key. Proofhouse writes the prompts it needs as packets; you run them in the agent or model you already use and paste the results back. It is a local tool, not a hosted service, and I make no benchmark or quality claims for it.

[![Proofhouse in 23 seconds: a prompt revision that invents an exploitation claim fails its checks, and the next revision passes with every constraint kept](docs/assets/proofhouse-demo.jpg)](docs/assets/proofhouse-demo.mp4)

*23-second demo (click to play). The terminal lines are the real `optimize check` output from the reference workflow below (case path shortened).*

Portfolio: [km-it-ops.github.io](https://km-it-ops.github.io/)

---

## Try it in two minutes

```bash
git clone https://github.com/KM-it-ops/Proofhouse.git
cd Proofhouse
uv sync --extra test
uv run python scripts/reference_workflow.py
```

That runs the [reference workflow](docs/reference-workflow.md) end to end, offline: a security-advisory summary whose first revision invents an exploitation claim and fails its checks, and whose second revision passes without losing a constraint. On Windows, set `$env:PYTHONUTF8='1'` first for reliable console output.

Without [uv](https://docs.astral.sh/uv/): `python -m pip install -e ".[test]"`, then `python scripts/reference_workflow.py`.

---

## How it works

`proofhouse-compiler optimize` renders the framework's clarify / compile / self-heal prompts as packets you run in the agent or model of your choice, and checks what you paste back against the criteria you declare. It does not call a model and it does not rate quality.

These are the [reference workflow](docs/reference-workflow.md)'s steps, and they run as written. `pc` below is `proofhouse-compiler` (`uv run proofhouse-compiler` from a clone). Work in a scratch folder holding copies of the example inputs:

```bash
mkdir -p build/try && cp examples/reference-advisory/* build/try && cd build/try
```

**1. Start a case and answer one batch of questions.** Proofhouse writes a clarify packet, `advisory-case/01-clarify.md`. You run it in your own agent and save the answers as `advisory-case/answers.json` (for this example, copy `answers.json` there). Compile turns each answer into an accepted constraint (K1-K3) that every later revision receives.

```bash
pc optimize new --case advisory-case --objective-file objective.txt --model "Claude Sonnet 5" --preset efficient
pc optimize compile --case advisory-case
```

**2. Say how each constraint will be checked.** Checks can look at the prompt text or at what a model returned (`--target output`), and some can be a human judgement (`--manual`).

```bash
pc optimize constraints add --case advisory-case --text "Cite the advisory section for each claim"      # K4
pc optimize criteria add --case advisory-case --id AUD --must-contain "SOC analysts"
pc optimize criteria add --case advisory-case --id UNK --target output --must-contain UNKNOWN
pc optimize criteria add --case advisory-case --id NOGUESS --target output --must-not-contain "exploited in the wild"
pc optimize criteria add --case advisory-case --id LEN --target output --max-words 120
pc optimize criteria add --case advisory-case --id CITE --target output --regex "\(s\d\)"
pc optimize criteria add --case advisory-case --id ACC --target output --manual "Every claim matches the advisory"
pc optimize constraints link --case advisory-case --id K1 --criterion AUD
pc optimize constraints link --case advisory-case --id K2 --criterion UNK
pc optimize constraints link --case advisory-case --id K2 --criterion NOGUESS
pc optimize constraints link --case advisory-case --id K3 --criterion LEN
pc optimize constraints link --case advisory-case --id K4 --criterion CITE
pc optimize constraints link --case advisory-case --id K4 --criterion ACC
```

**3. Record a revision and what it produced, judge the manual check, then check it.**

```bash
pc optimize record --case advisory-case --prompt-file prompt-v1.txt
pc optimize output add --case advisory-case --revision 1 --output-file output-v1.txt --input-id EC-2026-017 --input-file advisory.txt --model "Claude Sonnet 5" --source "pasted from host agent"
pc optimize verdict --case advisory-case --revision 1 --criterion ACC --run R1 --result fail --note "claims active exploitation; the advisory does not say that"
pc optimize check --case advisory-case        # exit 3: v1 FAIL  UNK NOGUESS CITE ACC fail
```

**4. Revise without losing anything.** The revise packet carries your feedback, the original answers and every accepted constraint. Run it in your agent, save the new prompt, and record revision 2 the same way.

```bash
pc optimize revise --case advisory-case --feedback "It claimed active exploitation, which the advisory never states."
pc optimize record --case advisory-case --prompt-file prompt-v2.txt
pc optimize output add --case advisory-case --revision 2 --output-file output-v2.txt --input-id EC-2026-017 --input-file advisory.txt --model "Claude Sonnet 5" --source "pasted from host agent"
pc optimize verdict --case advisory-case --revision 2 --criterion ACC --run R2 --result pass
pc optimize check --case advisory-case        # exit 0: v2 PASS, K1-K4 satisfied
```

**5. Compare, report and hand it on.** `compare` shows what newly passes or regresses between revisions, `report` writes the evidence as Markdown, and `export` / `import` move a case to another workspace, refusing any file that does not match the bundle's manifest (the manifest is not signed).

### What a PASS proves, and what it does not

| A PASS from `optimize check` means | It does not mean |
|---|---|
| Every check you declared passed on this exact revision (and, for output checks, on the outputs you recorded) | That the prompt is good in general, or better than one you did not test |
| Every accepted constraint is linked to a check that passed | That a model will reproduce the recorded outputs |
| Each human verdict applies to the exact text and check definition you judged | That model notes are correct: shipped profiles cite no sources yet and are labeled `unverified` |
| Nothing was edited after it was recorded (digests are re-checked) | That the files are tamper-proof against someone who controls your machine |

Details: [docs/architecture.md](docs/architecture.md), [decision 0002](docs/decisions/0002-what-pass-means.md), [evidence format](docs/evidence-format.md).

---

## Two ways in

| Entry | Use it when | Status | Network |
|---|---|---|---|
| **Command line**: `proofhouse-compiler optimize` | You want the evidence trail above: constraints, recorded outputs, checks, compare, report | supported | none |
| **Cursor or Claude Code skill**: `proofhouse-compiler install-skill` (Cursor) or `install-skill --host claude` (Claude Code), then say "Proofhouse" in a new chat or session | You want the same clarify → compile → self-heal loop as a conversation | supported entry point | the host agent's tools |

Proofhouse is two products in one repo, at different levels of maturity. The **PromptOps skill and framework (v1.3)**, the conversational meta-optimizer with current frontier model profiles, is the most mature part of the project. The headless compiler's maturity is listed under [Experimental and prototype parts](#experimental-and-prototype-parts).

Both entries use the same framework ([`proofhouse-framework.json`](proofhouse-framework.json)) and the same model notes. The framework also covers Efficient / Balanced / Thorough token presets, loops for recurring agents (trigger, body, exit, escalation), prompt audits with missing-context labels, and agent design (permission maps, tool boundaries, stop conditions). The skill is installed to `~/.cursor/skills/proofhouse` (or `~/.claude/skills/proofhouse` with `--host claude`) and the installer checks it (the bundle ships inside the package; `tests/test_skill_bundle.py` keeps it identical to `skills/proofhouse/`); without the console script, `python -m zipfile -e skills/proofhouse/proofhouse.skill ~/.cursor/skills` (or `~/.claude/skills`) does the same. The skill can research an unfamiliar model with the host agent's tools; the command line never goes online, and uses your own notes (`models remember`) or a generic profile labeled `fallback`.

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

## Install and verify

One Python package, version 0.3.0, ships two console scripts:

| Command | What it is | Subcommands |
|---|---|---|
| `proofhouse-compiler` | The prompt workspace above, plus an offline compiler (requirements → IR → adapter artifact → evidence), the model-notes cache and the skill installer | `optimize` `models` `install-skill` `doctor` `validate` `inspect` `compile` `closed-loop` `adapters` |
| `proofhouse` | Eval harness: JSONL datasets, YAML rubrics, report skeletons | `validate` `report` `loadouts` `compile-loadout` `generate` |

Supported: the `optimize` case workflow, `models`, `install-skill`, and `validate` / `compile` / `closed-loop`. The experimental commands are listed under [Experimental and prototype parts](#experimental-and-prototype-parts).

```bash
uv sync --extra test                                    # package + pytest into .venv
uv run proofhouse-compiler doctor                       # doctor: success
uv run proofhouse-compiler closed-loop tests/compiler/fixtures/closed_loop_requirements_minimal.json --repair-budget 1
                                                        # closed-loop: PASS (structural)
uv run proofhouse validate --dataset evals/datasets/prompt_audit_cases.jsonl
                                                        # Dataset validation passed: ...
uv run pytest -q                                        # all passed, 1 deselected (live tests are opt-in)
uv run python scripts/reference_workflow.py --quiet     # reference workflow: OK
```

CI runs the test suite on Linux, macOS and Windows with Python 3.11 to 3.14, and runs the reference workflow against the built wheel. Everything above is offline: no network, no API key. Nothing here is a benchmark.

The compiler's `closed-loop` PASS is structural: the prompt compiles offline with the fake adapter and passes security gates, and its evidence lists what it did not measure. Its approved headless profiles are `structured_minimal_v0` and `structured_developer_v0`.

---

## Experimental and prototype parts

These ship in the repository but are not the supported path. Treat them as previews.

| Part | Status | Network |
|---|---|---|
| `proofhouse-compiler execute-openai`: a fail-closed live OpenAI call that refuses to send unless every mandatory requirement is in the request; its cost ceiling is recorded, not enforced | experimental, opt-in | yes, only when opted in |
| `evaluate-product`, the requirements-contract commands, `route` / `assay` / `proof` | experimental | none |
| [`apps/proofhouse.jsx`](apps/proofhouse.jsx): a Claude artifact with a model picker, efficiency modes and a live compile loop; for an unknown model it web-researches, caches the result in artifact storage and labels it `researched` / `cached` / `fallback` | experimental | calls `api.anthropic.com` |
| The `hosted-*` and `missionrig-*` modules: experimental library slices, not a hosted service (their tenant label is not isolation) | experimental | none |
| `apps/dashboard/` | prototype | none |

The headless requirements compiler's maturity is still `PARTIAL`. Full map with versions and diagnostic codes: [docs/surfaces.md](docs/surfaces.md).

---

## Design rules

- Stay lightweight by default. Tighten only for safety, agentic execution, or missing context.
- Never invent repository or project facts.
- Use exact missing-context labels: `UNKNOWN`, `NOT SPECIFIED`, `NOT FOUND IN PROVIDED MATERIAL`.
- Keep cybersecurity and sensitive-data work defensive, authorized, and privacy-preserving.
- No private chain-of-thought dumps. Concise rationales only.

It was designed for coding agents, Custom GPTs, Cursor skills, and security-adjacent AI work, where inventing facts or skipping a safety boundary is not acceptable.

---

## Repository map

```text
proofhouse-framework.*   Portable meta-optimizer spec (v1.3 model profiles)
skills/proofhouse/       Cursor / Claude Code skill bundle + artifact JSX
src/proofhouse/          Eval harness, headless compiler, optimize (cases, constraints, runs, checks, export)
examples/                Demo inputs, including reference-advisory/ for the reference workflow
scripts/                 Generators (model surfaces, skill bundle, contracts) and reference_workflow.py
docs/                    Scope, architecture, surfaces, evidence format, decisions, assurance statements
prompts/                 Core prompt, modes, modules, templates, Custom GPT pack
evals/                   JSONL datasets, YAML rubrics
apps/                    Experimental artifact and dashboard prototypes
tests/                   Test suite, contract schemas and fixtures
```

Internal mission reports and review corpora are not published in this repository. Public decisions are summarized in [docs/decisions/](docs/decisions/), and each assurance statement in [docs/assurance/](docs/assurance/) lists the exact revision, commands, results and exclusions.

---

## Start here

- [Reference workflow](docs/reference-workflow.md): one failed check to a verified fix, offline
- [Product scope](docs/product-scope.md) · [Architecture](docs/architecture.md) · [Surfaces and contracts](docs/surfaces.md) · [Evidence format](docs/evidence-format.md)
- [Decision records](docs/decisions/) · [Assurance statements](docs/assurance/) · [Troubleshooting](docs/troubleshooting.md)
- [Quickstart](docs/quickstart.md) · [Showcase](docs/showcase.md) · [Custom GPT setup](docs/custom-gpt-setup.md)
- [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security policy](SECURITY.md)

---

<sub>Custom GPT surface: <strong>PromptOps Architect powered by Proofhouse</strong> · MIT License</sub>
