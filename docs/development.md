# Development

Checks, layout and design rules for people working on Proofhouse. Contribution rules are in [CONTRIBUTING.md](../CONTRIBUTING.md).

## Install and verify

One Python package, version 0.10.3, ships one command, `proofhouse`. Every interface reaches the same command tree (`proofhouse-compiler` still works as an alias and prints a one-line notice on stderr; `proofhouse optimize` likewise forwards to `proofhouse case`):

| Command group | What it is | Commands |
|---|---|---|
| Cases | The prompt or skill workspace above (`case new --kind prompt` or `--kind skill`), the skill installer, the model-notes cache, the packaged reference demo, and the part registry | `case` `install-skill` `uninstall-skill` `models` `demo` `parts` `scan` |
| Compiler | Offline compiler: requirements → IR → request builder artifact → evidence | `doctor` `validate` `inspect` `compile` `closed-loop` `adapters` |
| Eval harness | JSONL datasets, YAML rubrics, report skeletons | `eval validate` `eval report` `eval loadouts` `eval compile-loadout` `eval generate` |

Supported: the `case` workflow, `models`, `install-skill`, `demo`, and `validate` / `compile` / `closed-loop`. The experimental commands are listed under [Experimental and prototype parts](#experimental-and-prototype-parts).

```bash
uv sync --extra test                                    # package + pytest into .venv
uv run proofhouse doctor                                # doctor: success
uv run proofhouse closed-loop tests/compiler/fixtures/closed_loop_requirements_minimal.json --repair-budget 1
                                                        # closed-loop: PASS (structural)
uv run proofhouse eval validate --dataset evals/datasets/prompt_audit_cases.jsonl
                                                        # Dataset validation passed: ...
uv run pytest -q                                        # all passed, 1 deselected (live tests are opt-in)
uv run proofhouse demo --quiet                          # reference workflow: OK
uv run python scripts/reference_workflow.py --quiet     # same run via the script wrapper
```

CI runs the test suite on Linux, macOS and Windows with Python 3.11 to 3.14, runs the reference workflow against the built wheel, and runs `proofhouse demo` from that wheel outside the checkout. Everything above is offline: no network, no API key. Nothing here is a benchmark.

The compiler's `closed-loop` PASS is structural: the prompt compiles offline with the fake adapter and passes security gates, and its evidence lists what it did not measure. Its approved headless profiles are `structured_minimal_v0` and `structured_developer_v0`.

The skill bundle shipped inside the package is kept identical to `skills/proofhouse/` by `tests/test_skill_bundle.py`.

## Experimental and prototype parts

These ship in the repository but are not the supported path. Treat them as previews.

| Part | Status | Network |
|---|---|---|
| `proofhouse execute-openai`: a fail-closed live OpenAI call that refuses to send unless every mandatory requirement is in the request, and refuses before sending when the worst-case estimate of its cost is over your ceiling or the model has no price. It runs on any provider with `--provider ID`, always through the spend gate, and refuses a model that has no price (shipped or declared by you). Its dollar figures are estimates, not your bill | experimental, opt-in | yes, only when opted in |
| `evaluate-product`, the requirements-contract commands, `route` / `assay` / `proof` | experimental | none |
| [`apps/proofhouse.jsx`](../apps/proofhouse.jsx): a Claude artifact with a model picker, efficiency modes and a live compile loop; for an unknown model it web-researches, caches the result in artifact storage and labels it `researched` / `cached` / `fallback` | experimental | calls `api.anthropic.com` |
| The `hosted-*` and `missionrig-*` modules: experimental library slices, not a hosted service (their tenant label is not isolation) | experimental | none |
| `apps/dashboard/` | prototype | none |

The headless requirements compiler's maturity is still `PARTIAL`. Full map with versions and diagnostic codes: [docs/surfaces.md](surfaces.md).

## Design rules

- Stay lightweight by default. Tighten only for safety, agentic execution, or missing context.
- Never invent repository or project facts.
- Use exact missing-context labels: `UNKNOWN`, `NOT SPECIFIED`, `NOT FOUND IN PROVIDED MATERIAL`.
- Keep cybersecurity and sensitive-data work defensive, authorized, and privacy-preserving.
- No private chain-of-thought dumps. Concise rationales only.

It was designed for coding agents, Custom GPTs, Cursor skills, and security-adjacent AI work, where inventing facts or skipping a safety boundary is not acceptable.

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

Internal mission reports and review corpora are not published in this repository. Public decisions are summarized in [docs/decisions/](decisions/), and each assurance statement in [docs/assurance/](assurance/) lists the exact revision, commands, results and exclusions.
