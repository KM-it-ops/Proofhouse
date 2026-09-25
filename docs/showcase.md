# Proofhouse Showcase — the 5-minute no-key demo

Prompt systems that behave like maintained infrastructure: deterministic, inspectable, regression-tested. This page is a script you can run verbatim. Every command is offline; no provider is called; nothing here is a benchmark.

## Before you start

```powershell
$env:PYTHONUTF8='1'
uv sync --extra test
```

Presenting from a checkout that is already synced? Add `--no-sync` after `uv run` to skip the lock check.

## 0:00–0:30 — Frame it

"Proofhouse turns structured prompt requirements into deterministic, inspectable artifacts, and ships an offline eval harness. Two CLIs, one package, version 0.3.0. This demo makes no provider or benchmark claim."

## 0:30–1:00 — Prove the environment

```powershell
uv run proofhouse-compiler doctor
```

```text
doctor: success
```

Say: "Doctor asserts the certified path is offline. It does not probe the network — that is a design statement, not a measurement."

## 1:00–1:30 — Show the two products

```powershell
uv run proofhouse-compiler --help
uv run proofhouse --help
```

First is the compiler (`validate inspect compile adapters doctor closed-loop …`). Second is the eval harness (`validate report loadouts compile-loadout generate`). Say: "Same package, two console scripts. `proofhouse` never means the compiler."

## 1:30–3:15 — Run the real offline loop

```powershell
uv run proofhouse-compiler closed-loop tests/compiler/fixtures/closed_loop_requirements_minimal.json --repair-budget 1
```

```text
closed-loop: PASS
  requirements: ['REQ-EVAL-001']
  failed_attempts: 0
```

Then the evidence:

```powershell
uv run proofhouse-compiler closed-loop tests/compiler/fixtures/closed_loop_requirements_minimal.json --repair-budget 1 --json
```

Point at, in order: `"status":"PASS"`, `"adapter":{"id":"fake","version":"0.1.0"}`, `"network_allowed":false`, `"network_used":false`, `"repair_budget":1`, `"requirement_ids":["REQ-EVAL-001"]`, `"ir_sha256"`, `"baseline_digest"`. Say: "Requirements in, IR, fake-adapter compile, deterministic evaluation, one repair attempt allowed and none needed, evidence with digests. Real run, no network."

## 3:15–4:00 — Validate and compile a static IR

```powershell
uv run proofhouse-compiler validate examples/ir_minimal.json
uv run proofhouse-compiler compile examples/ir_minimal.json --adapter fake --adapter-version 0.1.0 --output build/demo
```

```text
validate: success
compile: success
  artifact: compiled_prompt -> <your checkout>/build/demo/compiled_prompt
```

Say: "One artifact, written to disk, path shown." Open `examples/ir_minimal.json` if asked what an IR looks like (60 lines: project, objective, requirements, behavior, evaluation, provenance). Do not open `compile --json` output on a projector — it carries a base64 artifact.

## 4:00–4:30 — Independent eval-harness operation

```powershell
uv run proofhouse validate --dataset evals/datasets/prompt_audit_cases.jsonl
uv run proofhouse report --dataset evals/datasets/prompt_audit_cases.jsonl --out evals/reports/prompt_audit_report.md
```

```text
Dataset validation passed: evals/datasets/prompt_audit_cases.jsonl
Report written: evals/reports/prompt_audit_report.md
```

## 4:30–5:00 — The conversational surface

Skill install (once, then a new Agent chat):

```powershell
uv run proofhouse-compiler install-skill
uv run proofhouse-compiler models show "Sonnet 5"
```

Say: "The skill installs from the package and verifies its own name. `models show` tells you the profile's source, review date and evidence label before you trust it; today every shipped profile says unverified, because none cites sources yet."

In the new chat: "Proofhouse: write a prompt for Sonnet 5 that summarises a security advisory." Show the one batched clarification form → compile → offer self-heal. If the skill is not installed on the presenting machine, open `skills/proofhouse/SKILL.md` and walk the Clarify → Compile → Self-heal flow and its honesty gates instead.

## Do not demo

Experimental hosted/MissionRig commands (`PROOFHOUSE_EXPERIMENTAL=1`), `execute-openai`, `apps/proofhouse.jsx` as a product, any API key.

## Example outcomes (conversational skill)

| You bring | Proofhouse returns |
|---|---|
| Rough Custom GPT instructions | Modular system prompt, missing-context policy, safety boundaries |
| Coding-agent workflow prompt | Tool permission map, stop conditions, verification loop, audit criteria |
| Prompt rewrite request | Rewritten prompt + rationale + regression checks |
| Eval design request | JSONL cases, 1–5 rubric criteria, report skeleton |

## Why cyber×AI teams care

- Explicit missing-context labels (`UNKNOWN`, `NOT SPECIFIED`, `NOT FOUND IN PROVIDED MATERIAL`) instead of invented facts
- Agentic permission maps and stop conditions before tools run
- Offline compiler and eval harness — inspectable, repeatable, no API keys
- Defensive default for security, automation, scraping, credentials, and sensitive data

## Public posture

- No secrets or provider credentials in the repo; `SECURITY.md` documents the stance.
- Runtime deps: `jsonschema>=4.18`, `rfc8785==0.1.4`. Extras: `test` (pytest), `live` (httpx, for the opt-in, not-certified `execute-openai`).
- Requirements compiler maturity `PARTIAL`. Certified path offline. No benchmark claims.

## Links

- [README](../README.md) · [Quickstart](quickstart.md) · [Custom GPT setup](custom-gpt-setup.md)
- Portfolio: [km-it-ops.github.io](https://km-it-ops.github.io/)
