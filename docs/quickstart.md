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

## Optimize packets (offline, no provider call)

`optimize` turns an objective + target model into the framework's own clarify → compile → self-heal prompts, written to a case directory. You run each packet in the host agent or model you choose and record the result; Proofhouse never calls a model here.

```powershell
uv run proofhouse-compiler optimize new --case build/case-demo --objective "Summarise a security advisory for a SOC audience" --model "Sonnet 5"
# answer build/case-demo/01-clarify.md in your host agent; put answers in build/case-demo/answers.json
uv run proofhouse-compiler optimize compile --case build/case-demo
# run 02-compile.md; save the compiled prompt to a file
uv run proofhouse-compiler optimize record --case build/case-demo --prompt-file <file>
uv run proofhouse-compiler optimize criteria add --case build/case-demo --must-contain "SOC"
uv run proofhouse-compiler optimize criteria add --case build/case-demo --max-words 200
uv run proofhouse-compiler optimize check --case build/case-demo --all
uv run proofhouse-compiler optimize revise --case build/case-demo --feedback "too long"
```

```text
optimize: new case C:\AI\projects\PromptRig\.worktrees\T-S\build\case-demo
  model: Claude Sonnet 5 (claude-sonnet-5) source=builtin verified_at=2026-09-03 stale=no
  preset: balanced  loop: no
  wrote: case.json, 01-clarify.md, answers.json
  next: run 01-clarify.md in your host agent, put answers in answers.json, then: proofhouse-compiler optimize compile --case C:\AI\projects\PromptRig\.worktrees\T-S\build\case-demo
check: C:\AI\projects\PromptRig\.worktrees\T-S\build\case-demo
  v1: PASS  C1=PASS C2=PASS
```

Criteria are yours: substring, word cap, regex, or a manual verdict (`optimize verdict`). `check` prints PASS/FAIL/UNJUDGED per criterion per revision and exits 3 on any FAIL. There is no score and no comparison across models.

## Model notes: where a profile comes from and how old it is

```powershell
uv run proofhouse-compiler models list
uv run proofhouse-compiler models show "opus 5"
uv run proofhouse-compiler models show "Zeta 9"
```

```text
models: 18 builtin, 0 cached (registry v1.3, stale after 90 days)
model: Claude Opus 5
  entered: opus 5
  canonical_id: claude-opus-5
  provider: Anthropic  tier: current
  source: builtin  verified_at: 2026-09-03  stale: no
  sources: none recorded
  notes: Anthropic's default for complex agentic coding. 1M context, 128k output (`claude-opus-5`), thinking on by default (disable only at effort high or below), default effort high, $5/$25. Give the full task spec and let it run -- it finishes rather than stubbing. Strip verify/self-check/subagent-QA instructions (they cause over-verification). Cap subagent spawns; it delegates eagerly. Ask for concise progress explicitly; default replies run long. Constrain scope on large jobs or it will expand them. Step up to Fable 5.1 only when Opus 5 at higher effort still fails evals.
warning: no notes for "Zeta 9"; using the generic profile (source=fallback)
model: Zeta 9
  entered: Zeta 9
  canonical_id: zeta-9
  provider: -  tier: generic
  source: fallback  verified_at: -  stale: no
  sources: none recorded
  notes: No verified vendor-specific behavior available. General best practice: explicit goal, constraints, format, audience. Note in rationale that this is generic guidance.
```

`source` is `builtin` (shipped registry), `cached` (your `models remember`), `researched` (notes file passed to `optimize new --notes-file`), or `fallback` (generic profile; the CLI does not research unknown models). Profiles older than 90 days print a stale warning. Aliases such as `opus 5` or `anthropic/claude-opus-5` resolve to the canonical id while your entered name is kept. Cache lives under `~/.proofhouse/model-notes/` (override with `PROOFHOUSE_HOME`); `models remember NAME --notes-file F [--source-url U]` stores or refreshes an entry, `models forget NAME` removes it.

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

- `proofhouse-compiler --help` also lists advanced commands (`compile-requirements`, `evaluate-product`, `closed-loop-bridged-008`, `route`, `assay`, `proof`, `optimize`, `models`, `install-skill`, `execute-openai`). They run, but only the commands in this document are the presented path. `execute-openai` is fail-closed opt-in live OpenAI and is **not** certified. `optimize` renders packets and never calls a model; `models` never researches online.
- Requirements compiler maturity is `PARTIAL`. No benchmark, quality, latency, or cost claim is made.
- Hosted/MissionRig commands are hidden behind `PROOFHOUSE_EXPERIMENTAL=1` and are experimental library slices, not a product. Do not set that variable for a demo.
- `apps/proofhouse.jsx` calls the Anthropic Messages API when run as a Claude artifact and is not the offline path.

## Prompt library

- `prompts/core/proofhouse_core.md` — universal behavior.
- `prompts/custom_gpt/promptops_architect_custom_gpt.md` — Custom GPT instructions.
- `prompts/modes/*.md` — task-specific operating modes.
- `prompts/modules/*.md` — reusable audit, rewrite, safety, eval, and changelog components.
