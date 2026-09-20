# Proofhouse Quickstart

Two offline surfaces, one package (`proofhouse` 0.2.1):

- `proofhouse-compiler` — the compiler. Requirements → IR → fake-adapter artifact → evaluation/repair evidence.
- `proofhouse` — the eval harness. JSONL dataset validation, rubric checks, markdown report skeletons.

No API key is used on any path in this document. The certified path is offline by construction (fake adapter, `network_allowed=false`). `doctor` asserts this; it does not probe the network.

## Install

With uv (recommended, tested on Windows):

```powershell
$env:PYTHONUTF8='1'          # Windows only; bash users skip this
uv sync --extra test
```

With pip in your own virtual environment:

```bash
python -m pip install -e ".[test]"
```

`test` installs pytest only. Runtime dependencies stay `jsonschema>=4.18` and `rfc8785==0.1.4`; optional extra `live` installs `httpx>=0.27` for the opt-in, not-certified `execute-openai` path. Do not add further runtime deps without an OAR.

Prefix commands with `uv run` (uv) or run them inside your activated venv (pip). Examples below use `uv run`.

## Compiler

```powershell
uv run proofhouse-compiler doctor
```

```text
doctor: success
```

Exit 0. `--json` shows the four checks: `python_version`, `diagnostic_registry`, `ir_schema`, `offline_mode_assertion`.

Closed loop on the tracked requirements fixture — requirements → IR → fake adapter → evaluate → repair (budget 1) → evidence:

```powershell
uv run proofhouse-compiler closed-loop tests/compiler/fixtures/closed_loop_requirements_minimal.json --repair-budget 1
```

```text
closed-loop: PASS
  requirements: ['REQ-EVAL-001']
  failed_attempts: 0
```

Add `--json` for the full evidence envelope (`status`, `evidence_bundle.network_allowed: false`, `network_used: false`, `adapter.id: fake`, `ir_sha256`, `baseline_digest`).

Validate and compile a static IR file:

```powershell
uv run proofhouse-compiler validate examples/ir_minimal.json
uv run proofhouse-compiler compile examples/ir_minimal.json --adapter fake --adapter-version 0.1.0 --output build/demo
```

```text
validate: success
compile: success
  artifact: compiled_prompt -> <your checkout>/build/demo/compiled_prompt
```

The artifact line prints the absolute path. `build/` is git-ignored. `--json` on `compile` returns the machine envelope (includes a base64 artifact; use it for automation, not for reading).

## Eval harness

```powershell
uv run proofhouse validate --dataset evals/datasets/prompt_audit_cases.jsonl
uv run proofhouse validate --dataset evals/datasets/meta_prompting_cases.jsonl
uv run proofhouse validate --dataset evals/datasets/agentic_mode_cases.jsonl
uv run proofhouse validate --dataset evals/datasets/adversarial_cases.jsonl
```

```text
Dataset validation passed: evals/datasets/prompt_audit_cases.jsonl
```

Every JSONL case must include:

```json
{
  "id": "string",
  "type": "normal | edge | missing_context | adversarial | regression",
  "input": "string",
  "expected_behavior": "string",
  "failure_signals": ["string"],
  "pass_criteria": "string"
}
```

Report skeleton:

```powershell
uv run proofhouse report --dataset evals/datasets/prompt_audit_cases.jsonl --out evals/reports/prompt_audit_report.md
```

```text
Report written: evals/reports/prompt_audit_report.md
```

Reports are generated artifacts and are git-ignored except `evals/reports/.gitkeep`.

## Tests

```powershell
uv run pytest -q
```

All tests pass with `1 deselected`: the `live` marker is excluded by default (`addopts = "-m \"not live\""`).

## Boundaries

- `proofhouse-compiler --help` also lists advanced commands (`compile-requirements`, `evaluate-product`, `closed-loop-bridged-008`, `route`, `assay`, `proof`, `execute-openai`). They run, but only the commands in this document are the presented path. `execute-openai` is fail-closed opt-in live OpenAI and is **not** certified.
- Requirements compiler maturity is `PARTIAL`. No benchmark, quality, latency, or cost claim is made.
- Hosted/MissionRig commands are hidden behind `PROOFHOUSE_EXPERIMENTAL=1` and are experimental library slices, not a product. Do not set that variable for a demo.
- `apps/proofhouse.jsx` calls the Anthropic Messages API when run as a Claude artifact and is not the offline path.

## Prompt library

- `prompts/core/proofhouse_core.md` — universal behavior.
- `prompts/custom_gpt/promptops_architect_custom_gpt.md` — Custom GPT instructions.
- `prompts/modes/*.md` — task-specific operating modes.
- `prompts/modules/*.md` — reusable audit, rewrite, safety, eval, and changelog components.
