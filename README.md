# PromptRig

[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab)](https://www.python.org/)
[![Runtime deps](https://img.shields.io/badge/runtime%20deps-stdlib%20only-2f855a)](#30-second-start)
[![PromptOps](https://img.shields.io/badge/promptops-modular%20%7C%20testable%20%7C%20safe-0f766e)](#what-you-get)
[![License](https://img.shields.io/badge/license-MIT-111827)](LICENSE)

**Prompt operations for agentic and security-minded builders.**

PromptRig turns sticky-note prompts into inspectable infrastructure: modular architecture, missing-context audits, agent permission maps, offline evals, and a self-heal compile loop — without API keys or provider lock-in.

Custom GPT surface: **PromptOps Architect powered by PromptRig**.

Portfolio: [km-it-ops.github.io](https://km-it-ops.github.io/) · Showcase: [docs/showcase.md](docs/showcase.md)

## Why it exists

Most prompts fail quietly — missing context, model overfitting, no regression tests, no stop conditions. PromptRig gives prompt systems the same discipline you’d expect from production code:

1. **Clarify** — batched, branching questions before you write
2. **Compile** — model-specific prompt + settings + token rationale
3. **Evaluate** — JSONL cases, YAML rubrics, stdlib CLI validation
4. **Self-heal** — diagnose failures and revise without losing prior versions

Built for coding agents, Custom GPTs, local LLMs, and cyber×AI workflows where inventing facts or skipping safety boundaries is unacceptable.

## What you get

| Capability | Outcome |
|---|---|
| Prompt architecture | Core prompt, modes, reusable modules, project context templates |
| Audits | Missing-context labels, safety boundaries, rewrite notes, changelogs |
| Agentic design | Permission maps, tool boundaries, verification loops, stop conditions |
| Evals | JSONL datasets, YAML rubrics, schema checks, report skeletons |
| Skill pack | Cursor / Codex / Claude skill in `skills/promptrig/` + portable `promptrig-framework.*` |
| Custom GPT pack | Ready instruction set for PromptOps Architect |

## 30-second start

```bash
python -m pip install -e .
python -m pytest
python -m promptrig.cli validate --dataset evals/datasets/prompt_audit_cases.jsonl
python -m promptrig.cli report --dataset evals/datasets/prompt_audit_cases.jsonl --out evals/reports/prompt_audit_report.md
```

Windows launcher form if needed:

```powershell
py -3.14 -m pip install -e .
py -3.14 -m pytest
```

## Demo path

1. Drop a rough agent or product prompt into PromptRig (skill, Custom GPT, or modules).
2. Run Context Auditor — separate confirmed facts from `UNKNOWN` / `NOT SPECIFIED` / `NOT FOUND IN PROVIDED MATERIAL`.
3. Choose mode: Audit · Meta-Prompting · Agentic · Evaluator.
4. Rewrite with safety and missing-context behavior preserved.
5. Add JSONL eval cases; validate with the CLI; generate a report skeleton.

## Repository map

```text
prompts/            Core, modes, modules, templates, Custom GPT pack
evals/              JSONL datasets, YAML rubrics, report output
src/promptrig/      Stdlib eval harness + CLI
tests/              Pytest for schemas, scoring, bundled datasets
docs/               Quickstart, showcase, Custom GPT setup
skills/promptrig/   v1.2 skill bundle (.skill, framework refs, artifact JSX)
apps/               Interactive PromptRig artifact (promptrig.jsx)
promptrig-framework.*  Portable human/JSON meta-optimizer spec
```

## CLI highlights

```bash
# Validate eval dataset
python -m promptrig.cli validate --dataset evals/datasets/prompt_audit_cases.jsonl

# Report skeleton
python -m promptrig.cli report --dataset evals/datasets/prompt_audit_cases.jsonl --out evals/reports/prompt_audit_report.md

# Render versioned prompt-architect templates
python -m promptrig.cli generate --template prompt-architect \
  --project-name "Incident Desk" \
  --project-description "Build an internal incident review assistant." \
  --platform web --stack "Next.js, Supabase" --scale M \
  --out-dir exports/incident-desk
```

## Design rules

- Stay lightweight by default; tighten only for safety, agentic execution, repo work, evals, or missing context.
- Never invent repository or project facts.
- Use exact missing-context labels: `UNKNOWN`, `NOT SPECIFIED`, `NOT FOUND IN PROVIDED MATERIAL`.
- Keep cybersecurity, automation, scraping, credentials, exploit research, malware analysis, and sensitive-data work defensive, authorized, educational, and privacy-preserving.
- No private chain-of-thought dumps — concise rationales only.

## Engineering methodology

[Architect Mode v1.2.0](docs/methodology/architect-mode/README.md) is the architecture-first, contract-first methodology snapshot retained in-repo for reviewability. Compiler Core work stays gated by the [v0.5 contract-freeze candidate](architecture/compiler-contract-freeze-v0.5/README.md).

## Start here

- [Showcase](docs/showcase.md) — pitch, demo flow, outcomes
- [Quickstart](docs/quickstart.md)
- [Custom GPT setup](docs/custom-gpt-setup.md)
- [Prompt audit example](examples/prompt-audit-request.md)
- [Security policy](SECURITY.md)
- [Architecture governance](architecture/README.md)

## Status

**MISSION-012 offline eval/repair/evidence certified (OAR-006 Accepted 2026-08-12)** on the fake-adapter headless closed loop (`promptrig-compiler closed-loop`): deterministic evaluator, bounded repair (budgets `{0,1,2}`), versioned evidence (`eeb-headless-v0.1`). Builds on OAR-005 (MISSION-011) and MISSION-008/009 contracts — see `MISSION_012_REPORT.md` and `architecture/mission-012-certification/`.

**MISSION-013 M1 constrained prose intake certified (OAR-007 Accepted 2026-08-14)** (`plain_language_v0` grammar → `structured_minimal_v0` → closed loop) — see `MISSION_013_REPORT.md` and `architecture/mission-013-certification/`. Requirements compiler maturity remains `PARTIAL` (not CERTIFIED). Still no freeform NLP, no model calls (M2), no Simple Mode UI (M3), no live providers, no benchmark claims.
