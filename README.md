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

**MISSION-013 M1 constrained prose intake certified (OAR-007 Accepted 2026-08-14)** (`plain_language_v0` grammar → `structured_minimal_v0` → closed loop) — see `MISSION_013_REPORT.md` and `architecture/mission-013-certification/`.

**MISSION-014 M2 fake suggester sidecar certified (OAR-008 Accepted 2026-08-14)** — opt-in offline `fake-suggester-v0` proposals as sidecar evidence only (`enable_model_suggestions`; default off); see `MISSION_014_REPORT.md` and `architecture/mission-014-certification/`.

**MISSION-015 Phase 4B residual evidence complete (OAR-009 Accepted 2026-08-22)** — PEP 517 clean-install, installed-package consumer matrix, and operational resource ceilings for the offline fake closed loop; see `MISSION_015_REPORT.md` and `architecture/mission-015-certification/`. Requirements compiler maturity remains `PARTIAL` (not CERTIFIED). Still no full Roadmap Phase 4B exit, no live model assistance, no freeform NLP, no Simple Mode UI (M3), no live providers, no benchmark claims.

**MISSION-016 shared MISSION-008 contract-rule engine certified (OAR-010 Accepted 2026-08-21)** — `compile_requirements` / `promptrig-compiler compile-requirements` evaluate canonical artifact sets only; see `MISSION_016_REPORT.md` and `architecture/mission-016-certification/`. OAR-009 Accepted 2026-08-22. Requirements compiler maturity remains `PARTIAL` (not CERTIFIED). Not a full MISSION-008 production compiler (canonical records only; OQ-008-001 through OQ-008-009 owner-resolved in OPEN_QUESTIONS.md, policy only). This engine does not unblock M3. Still no full Roadmap Phase 4B exit, no freeform NLP, no Simple Mode UI (M3), no live providers.

**MISSION-017 file/api envelope producers (OAR-011 Accepted 2026-08-22)** — `produce_requirements` / `compile_requirements_input` assemble canonical MISSION-008 artifact mappings from file/api envelopes; `promptrig-compiler compile-requirements` dispatches envelope vs canonical payload; see `MISSION_017_REPORT.md` and `architecture/mission-017-certification/`. OAR-009 Accepted 2026-08-22. OAR-010 remains Accepted. Requirements compiler maturity remains `PARTIAL` (not CERTIFIED). Not a full MISSION-008 production compiler (no simple/developer/prs/authoring-prose producers until a later campaign; OQ-008-001 through OQ-008-009 owner-resolved in OPEN_QUESTIONS.md, policy only). This mission does not unblock M3. Still no full Roadmap Phase 4B exit, no freeform NLP, no Simple Mode UI (M3), no live providers.

**MISSION-018 simple/developer envelope producers (OAR-012 Accepted 2026-08-22)** — `produce_requirements` / `compile_requirements_input` assemble canonical MISSION-008 artifact mappings from simple (`ordinary_language`) and developer (`developer_config`) envelopes alongside file/api; `promptrig-compiler compile-requirements` help names file/api/simple/developer envelopes; see `MISSION_018_REPORT.md` and `architecture/mission-018-certification/`. OAR-009 Accepted 2026-08-22. OAR-010 and OAR-011 remain Accepted. Requirements compiler maturity remains `PARTIAL` (not CERTIFIED). Not a full MISSION-008 production compiler (no prs/authoring-prose producers; OQ-008-001 through OQ-008-009 owner-resolved in OPEN_QUESTIONS.md, policy only). This mission does not unblock M3. Still no full Roadmap Phase 4B exit, no freeform NLP, no Simple Mode UI (M3), no live providers.

**MISSION-019 prs envelope producers (OAR-013 Accepted 2026-08-22)** — `produce_requirements` / `compile_requirements_input` assemble canonical MISSION-008 artifact mappings from structured `authoring_mode=prs` envelopes alongside file/api/simple/developer; `promptrig-compiler compile-requirements` help names file/api/simple/developer/prs envelopes; see `MISSION_019_REPORT.md` and `architecture/mission-019-certification/`. OAR-009 Accepted 2026-08-22. OAR-010, OAR-011, and OAR-012 remain Accepted. Requirements compiler maturity remains `PARTIAL` (not CERTIFIED). PRS **language** (grammar, parser) remains DEFERRED per `PRS_DISPOSITION.md` — this mission implements only the structured envelope producer. Not a full MISSION-008 production compiler (no authoring-prose producers; OQ-008-001 through OQ-008-009 owner-resolved in `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md`, policy only — engine still fail-closed until a new campaign implements them). This mission does not unblock M3. Still no full Roadmap Phase 4B exit, no freeform NLP, no Simple Mode UI (M3), no live providers.

**MISSION-020 authoring-prose producers (OAR-014 Accepted 2026-08-22)** — constrained `plain_language_v0` text envelopes (`{profile, text}`) parse via existing `parse_plain_language_v0` and lower through `produce_plain_language_requirements` into canonical MISSION-008 artifact mappings; `compile_requirements_input` / `promptrig-compiler compile-requirements` dispatch canonical vs prose vs file/api/simple/developer/prs envelope; CLI help names `plain_language_v0`; see `MISSION_020_REPORT.md` and `architecture/mission-020-certification/`. OAR-009 Accepted 2026-08-22. OAR-010, OAR-011, OAR-012, and OAR-013 remain Accepted. Requirements compiler maturity remains `PARTIAL` (not CERTIFIED). Valid constrained prose yields `BLOCKED` / `RQC-BLK-0001` (goal maps direct; numbered/constraint mappings unresolved). Not a full MISSION-008 production compiler (OQ-008-001 through OQ-008-010 owner-resolved in `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md`, policy only — engine still fail-closed until a new campaign implements them). PRS **language** remains DEFERRED. This mission does not unblock M3. Still no full Roadmap Phase 4B exit, no freeform NLP, no Simple Mode UI (M3), no live providers.

**MISSION-021 OQ-008-001/002/006 implementation (OAR-015 Accepted 2026-08-23)** — OQ-008-001 file-digest fail-closed named policy; OQ-008-002 optional unresolved / optional `no_ir_representation` meaning compiles PARTIAL with evidence; OQ-008-006 SUCCESS may carry advisory non-semantic `RQC-ADV-0001`; `evaluate_contract_rules` remains sole RC-065 implementation; see `MISSION_021_REPORT.md` and `architecture/mission-021-certification/`. OAR-009 through OAR-014 remain Accepted. Requirements compiler maturity remains `PARTIAL` (not CERTIFIED). Valid constrained `plain_language_v0` grammar remains BLOCKED (`RQC-BLK-0001`). Remaining executable OQs 003/005/010 are MISSION-022. Not a full MISSION-008 production compiler. PRS **language** remains DEFERRED. This mission does not unblock M3. Still no full Roadmap Phase 4B exit, no freeform NLP, no Simple Mode UI (M3), no live providers.

**MISSION-022 remaining OQ-008-003/005/010 implementation (OAR-016 Accepted 2026-08-24)** — OQ-008-003 undeterminable required authority → BLOCKED; OQ-008-005 exact `0.1.0-draft`; OQ-008-010 structured-only assumption/open-question records; OQ-008-004/007/008/009 locked-not-built; `evaluate_contract_rules` remains sole RC-065 implementation; see `MISSION_022_REPORT.md` and `architecture/mission-022-certification/`. OAR-009 through OAR-015 remain Accepted. Requirements compiler maturity remains `PARTIAL` (not CERTIFIED). Valid constrained `plain_language_v0` grammar remains BLOCKED (`RQC-BLK-0001`). Not a full MISSION-008 production compiler. PRS **language** remains DEFERRED. This mission does not unblock M3. Still no full Roadmap Phase 4B exit, no freeform NLP, no Simple Mode UI (M3), no live providers.

**MISSION-023 constrained prose numbered/constraint IR mapping (OAR-017 Accepted 2026-08-24)** — numbered requirement lines map `direct` to `/requirements/{n}/statement` and constraint lines map `direct` to `/behavior/constraints/{n}`; Goal remains `direct` to `/objective/goal`; a valid Goal + numbered list + optional constraints write-up compiles SUCCESS rather than `RQC-BLK-0001` for this hole; see `MISSION_023_REPORT.md` and `architecture/mission-023-certification/`. OAR-009 through OAR-016 remain Accepted. Requirements compiler maturity remains `PARTIAL` (not CERTIFIED). OQ-008-004/007/008/009 remain locked-not-built. Not a full MISSION-008 production compiler. PRS **language** remains DEFERRED. This mission does not unblock M3. Still no full Roadmap Phase 4B exit, no freeform NLP, no Simple Mode UI (M3), no live providers.
