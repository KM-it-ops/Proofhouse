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
| Case | `proofhouse.optimize.case/v1` with a `kind` (`prompt.text@1` or `agent.skill@1`); revisions are `proofhouse.optimize.revision/v1` artifact references. A `case/v0` case (0.4.1) still opens and is upgraded one way on its first write, with `case.v0-backup.json` kept | `optimize/case.py`, `optimize/kinds.py` |
| Check semantics | `proofhouse.optimize.checks/v1` | `optimize/checks.py` |
| Run record / export | `proofhouse.optimize.run/v2` (adds `part` and `cost`; `run/v1` still reads), `proofhouse.optimize.export/v1` | `optimize/workflow.py` |
| Part contract | `proofhouse.part/v1`, descriptor v1 (no `cost_model`) | `parts.py` |
| Price table | `proofhouse.price_table/v1`, `price_table_version` `YYYY-MM-DD.N` pinned to its content | `data/price_table.json`, `spend.py` |
| Install record | `proofhouse.skill-install/v1` under `PROOFHOUSE_HOME/skill-installs/` | `optimize/install_skill.py` |

A package release can change any of these; the changelog says which.

## Surface map

| Surface | Status | Network | What it promises |
|---|---|---|---|
| `proofhouse case ...` (new, compile, record, revise, status, criteria, verdict, check, constraints, output, compare, report, export, import); `new --kind prompt` or `--kind skill` | **supported** | none | The local evidence workflow in [product-scope.md](product-scope.md), for a prompt or a skill. Digests verified on load; PASS as defined in [decision 0002](decisions/0002-what-pass-means.md). `proofhouse optimize ...` is a deprecated alias for 0.5 and prints a notice. |
| `proofhouse models ...` | **supported** | none | Profile source, evidence label, review date, staleness. Notes are guidance, not specifications. |
| `proofhouse install-skill` | **supported** | none | Installs Proofhouse's own skill (default) or any skill given as a zip or a folder; name from validated `SKILL.md` frontmatter. Transactional: a failed install leaves the previous one unchanged; replaced copies kept under `PROOFHOUSE_HOME/skill-backups/`. `--force` refuses a skill folder that is or holds a link or junction. |
| `proofhouse uninstall-skill NAME` | **supported** | none | Removes only a skill `install-skill` recorded installing, and restores what that install replaced if its backup is unchanged. Refuses a changed folder unless `--force` (then backs it up first, and refuses a folder that holds a link or junction); removes a link, never what it points at. |
| `proofhouse parts` (`--json`) | **supported** | none | Lists every registered part (request builders, text checker, skill checker, host writer) with role, kinds, status and conformance suite version. A case PASS never promotes a part. |
| `proofhouse demo` | **supported** | none | The reference advisory workflow, from files shipped in the package. Recorded outputs only; no model call and no checkout. |
| Cursor or Claude Code skill (`skills/proofhouse/`; `install-skill --host claude` for Claude Code) | **supported** entry point | host agent's tools | The conversational way into the same workflow. Host behavior is outside this repo's tests. |
| `proofhouse validate / inspect / compile / adapters / doctor` | **supported** | none | Deterministic IR validation and offline lowering. `adapters` lists the request builders only (its output is unchanged); `parts` lists every part. |
| `proofhouse closed-loop` | **supported** (structural) | none | Offline fake-adapter loop; strict intake validation; stage-separated evidence. A PASS is a structural check, not a quality measurement. |
| `proofhouse evaluate-product` | experimental | none | Imported observations vs a rubric; duplicate ids rejected; coverage and candidate binding reported. |
| `proofhouse compile-requirements`, `closed-loop-bridged-008` | experimental | none | Requirements-contract evaluation (maturity `PARTIAL`). |
| `proofhouse "<objective>"` (overseer) | experimental | none | Prints the `route` decision. A routed prompt or skill opens a case (as `case new` would) that records the route; any other class opens nothing and is appended as "no part yet" to `PROOFHOUSE_HOME/demand/no-part-yet.jsonl`; `nothing_new` / `one_prompt` do neither. |
| `proofhouse route / assay / proof` | experimental, not gated | none | Orchestration-layer prototypes; registered without `PROOFHOUSE_EXPERIMENTAL`. No review pass is wired to `proof`, so it reports `UNJUDGED` (exit 3), never `SHIP`. |
| `proofhouse make` | new | **yes**, one call per step, within one spending limit | Writes, tries, judges and improves a prompt or skill with any provider; keeps every version, score and cost in one folder. Judge scores are a model's advice. |
| `proofhouse run`, `proofhouse providers` | new | **yes**, `run` only, one request per call | Any provider that speaks the OpenAI chat format, shipped or added by you ([providers](providers.md)). Every run goes through the spend gate; a model on your own machine costs nothing. |
| `proofhouse execute-openai` | experimental, opt-in | **yes**, only with `--opt-in` and a credential | Every mandatory IR field is rendered into the request or execution refuses (`EXE-SEM-0001`). Before sending, the worst-case cost is worked out from the exact request bytes and the shipped price table; the call is refused (`PHC-COST-0001` to `0003`, exit 7) when that is over `--max-cost-usd`, when the model has no price, or when no worst case can be made. The table ships with no entries, so every model is refused until a cited price is added ([decision 0006](decisions/0006-refuse-before-sending-over-the-ceiling.md)). |
| `hosted-*`, `missionrig-generate`, `workspace-consume` | experimental, hidden unless `PROOFHOUSE_EXPERIMENTAL=1` | none | Library slices only. The tenant label is not isolation. Do not expose over HTTP. |
| `proofhouse eval ...` (validate --dataset, report, loadouts, compile-loadout, generate) | supported (legacy) | none | Dataset validation and report skeletons. The old top-level forms (`proofhouse validate --dataset`, `proofhouse report`, ...) fail with a one-line pointer to the new form. |
| `proofhouse scan` | supported | none | Read-only scan of a project folder. |
| `proofhouse-compiler ...` | deprecated alias | as the command | Same commands as `proofhouse`; prints a one-line notice on stderr, so `--json` output on stdout stays clean. |
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
