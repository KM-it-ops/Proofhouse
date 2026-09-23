# Surfaces and contracts

Which promises belong to which surface. "Supported" means covered by the default test suite and documented here; "experimental" means it works but may change or be removed without a deprecation period.

## Versions are separate

| Thing | Current | Where it lives |
|---|---|---|
| Python package | see `pyproject.toml` (`proofhouse.__version__` reads the installed value) | `pyproject.toml` |
| Framework (prompts, presets, model notes layout) | 1.3 | `proofhouse-framework.json` `version` |
| Model profiles | last reviewed date per entry; evidence label per entry | `src/proofhouse/optimize/data/model_registry.json` |
| IR contract | `spec_version` 0.1.0 | `src/proofhouse/compiler/schemas/` |
| Closed-loop evidence bundle | `eeb-headless-v0.1` + `stage_schema` `proofhouse.closed-loop.stages/v1` | `compiler/evidence.py` |
| Optimize case | `proofhouse.optimize.case/v0` (+ optional `constraints`, `clarification`, `runs`) | `optimize/case.py` |
| Check semantics | `proofhouse.optimize.checks/v1` | `optimize/checks.py` |
| Run record / export | `proofhouse.optimize.run/v1`, `proofhouse.optimize.export/v1` | `optimize/workflow.py` |

A package release can change any of these; the changelog says which.

## Surface map

| Surface | Status | Network | What it promises |
|---|---|---|---|
| `proofhouse-compiler optimize ...` (new, compile, record, revise, status, criteria, verdict, check, constraints, output, compare, report, export, import) | **supported** | none | The local evidence workflow in [product-scope.md](product-scope.md). Digests verified on load; PASS as defined in [decision 0002](decisions/0002-what-pass-means.md). |
| `proofhouse-compiler models ...` | **supported** | none | Profile source, evidence label, review date, staleness. Notes are guidance, not specifications. |
| `proofhouse-compiler install-skill` | **supported** | none | Transactional install; a failed install leaves the previous one unchanged; replaced copies kept under `PROOFHOUSE_HOME/skill-backups/`. |
| Cursor skill (`skills/proofhouse/`) | **supported** entry point | host agent's tools | The conversational way into the same workflow. Host behavior is outside this repo's tests. |
| `proofhouse-compiler validate / inspect / compile / adapters / doctor` | **supported** | none | Deterministic IR validation and offline lowering. |
| `proofhouse-compiler closed-loop` | **supported** (structural) | none | Offline fake-adapter loop; strict intake validation; stage-separated evidence. A PASS is a structural check, not a quality measurement. |
| `proofhouse-compiler evaluate-product` | experimental | none | Imported observations vs a rubric; duplicate ids rejected; coverage and candidate binding reported. |
| `proofhouse-compiler compile-requirements`, `closed-loop-bridged-008` | experimental | none | Requirements-contract evaluation (maturity `PARTIAL`). |
| `proofhouse-compiler route / assay / proof` | experimental | none | Orchestration-layer prototypes. |
| `proofhouse-compiler execute-openai` | experimental, opt-in | **yes**, only with `--opt-in` and a credential | Every mandatory IR field is rendered into the request or execution refuses (`EXE-SEM-0001`). The cost ceiling is recorded, not enforced before sending. |
| `hosted-*`, `missionrig-generate`, `workspace-consume` | experimental, hidden unless `PROOFHOUSE_EXPERIMENTAL=1` | none | Library slices only. The tenant label is not isolation. Do not expose over HTTP. |
| `proofhouse` (eval harness: validate, report, loadouts, generate) | supported (legacy) | none | Dataset validation and report skeletons. |
| `apps/proofhouse.jsx` artifact | experimental | calls `api.anthropic.com` | Responses schema-validated; hidden answers excluded; timeout and cancel. Hosting and authentication behavior are the artifact runtime's, not verified here. |
| `apps/dashboard/` | prototype | none | Design exploration with simulated telemetry. Not the product; do not demo it as one. |

## Diagnostic codes added by the evidence-integrity work

| Code | Meaning |
|---|---|
| `EVR-INP-0001` | Input is not one JSON object (bad UTF-8, bad JSON, duplicate keys, wrong root) |
| `EVR-INP-0002` | A field has the wrong type or value |
| `EVR-INP-0003` | Non-finite number (`NaN`, `Infinity`) |
| `EVR-INP-0004` | Nesting deeper than 32 or an array longer than 1000 |
| `EVR-DUP-0001` | Duplicate identifier (requirement, case, criterion) |
| `EVR-COV-0001` | A mandatory requirement has no evaluation case |
| `EVR-BND-0001` | Observations declare a different candidate digest |
| `EVR-REP-0005` | Repair not attempted: imported observations cannot change with the prompt |
| `EXE-SEM-0001` | A mandatory IR field cannot be honored by the live path; nothing was sent |

The full record layout is in [evidence-format.md](evidence-format.md).
