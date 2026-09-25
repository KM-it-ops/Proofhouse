# Changelog

## Unreleased

### Removed

- Removed the deprecated pre-Proofhouse console-script aliases and live-test
  environment fallback at the documented 0.3.0 boundary.

### Changed

- Completed the Proofhouse identity migration across active wire media types,
  semantic-context keys, benchmark and diagnostic identifiers, generated
  TypeScript names, schema filenames, dashboard metadata, CI, docs, and tests.
- Bumped the package to 0.3.0. Frozen v0.5 contract fixtures, requirements
  contract evidence, the original dashboard backup, and changelog history keep
  their historical names intentionally.

### Evidence integrity (adversarial review of 78e512c, findings F01-F12)

Behavior changes a user will notice are marked **(breaking)**. See
[docs/decisions/](docs/decisions/) for the reasoning and
[docs/assurance/](docs/assurance/) for what was verified.

#### Fixed

- **Live requests keep every mandatory field (F01).** `execute-openai` renders
  requirements (id, mandatory flag, acceptance), success/failure criteria,
  uncertainty and evidence policies, workflow, autonomy and assumptions into
  the system message from an explicit per-field map; fields a single request
  cannot honor refuse with `EXE-SEM-0001` before sending. The envelope records
  the mapping and the system-message digest.
- **(breaking)** **Duplicate evaluation ids are rejected (F02).** `case_id` and
  `criterion_id` duplicates, duplicate JSON keys inside a dataset row or rubric,
  malformed rows and non-finite values raise with the line number; scores use
  structured keys; aggregation is order-independent. A rubric must name
  `rubric_id` and `version` as non-empty strings.
- **(breaking)** **Coverage and binding (F03).** A mandatory requirement with no
  product-eval case is `BLOCKED` (`EVR-COV-0001`); rows declaring another
  candidate digest are `BLOCKED` (`EVR-BND-0001`). Results carry dataset/rubric
  digests and per-case results. `closed-loop` withholds a candidate PASS unless
  every row declares the candidate's `candidate_digest`: unbound or partially
  bound rows give `BLOCKED` (`EVR-BND-0002`, exit 5), which includes every
  dataset written before this change. Standalone `evaluate-product` still
  PASSes them; a declared digest is caller-supplied, not authenticated.
- **(breaking)** **Edited revisions and stale verdicts (F04).** Revisions are
  digest-checked on load; verdicts bind to revision and criterion digests and
  go stale when either changes; check runs are immutable files; `case.json`
  writes are atomic; revision files are never overwritten. Verdicts recorded
  before this change carry no digests and now show as stale (`UNJUDGED`);
  record them again with `optimize verdict`.
- **(breaking)** **Model-note provenance (F05).** Notes files are
  `user_supplied`, undated and unverified (they were `researched`, verified
  today). Every profile carries an `evidence` label; unsourced profiles say
  `unverified`; `models list` says "reviewed", not "verified". The Opus 5
  note no longer advises stripping verification, and every compile prompt says
  efficiency advice never removes a required gate.
- **Stage identity and repair (F06).** Closed-loop evidence reports compile,
  deterministic evaluation, product evaluation and repair as separate stages
  with true evaluator identities; a failing product evaluation stops with
  `EVR-REP-0005` and a terminal reason instead of a silent zero-attempt FAIL.
- **Malformed input (F07).** Closed-loop intake rejects non-object roots,
  wrong nested types, non-boolean `network_allowed`, non-finite numbers,
  duplicate keys/ids and excessive nesting with `EVR-INP-*`/`EVR-DUP-0001`
  instead of raising or passing.
- **Transactional skill install (F08).** A failed forced install leaves the
  previous skill unchanged; replacements keep a backup under
  `PROOFHOUSE_HOME/skill-backups/`; unsafe archive paths and oversized
  bundles are refused.
- **Budget inputs (F09).** `NaN`/`Infinity`/non-positive ceilings are rejected
  without raising; the envelope states the cost ceiling is declared only.
  Library callers must pass `max_cost_usd` as a decimal string (as the CLI
  does) and `max_output_tokens` as a positive `int` (not `bool`).
- **Artifact responses (F10).** The JSX artifact schema-validates every model
  response, excludes answers to hidden questions, and adds timeout/cancel,
  including for the unfamiliar-model research call (a cancel stops the run
  rather than falling back to generic notes).
- **Revision context (F11).** Revise packets (CLI and artifact) carry the
  clarification answers and accepted constraints. The artifact describes the
  answers as still in force unless the new feedback changes one, not as
  overriding it.
- **Public trust docs (F12).** SECURITY.md names a private reporting route;
  CONTRIBUTING installs the test extra and documents a public decision
  process; CLI help no longer cites unpublished internal ids.
- `proofhouse.__version__` reads the installed version (it said 0.1.1).

#### Added

- `optimize constraints add|list|propose|accept|reject|link`: a constraint
  ledger outside the prompt, seeded from clarification answers.
- `optimize output add|list`: record imported outputs bound to a revision.
- `criteria add --target output`, `verdict --run`: checks on recorded outputs.
- **(breaking)** `optimize check` passes only when every accepted constraint
  is satisfied by linked criteria ([decision 0002](docs/decisions/0002-what-pass-means.md)).
- `optimize compare`, `optimize report`, `optimize export|import`.
- `examples/reference-advisory/` and `scripts/reference_workflow.py`, run by
  the test suite and by the wheel-install CI job.
- Docs: product scope, architecture, surfaces and contracts, evidence format,
  reference workflow, troubleshooting, decision records, assurance statement.

### Added

- `[test]` extra declaring pytest, locked in `uv.lock`, so `uv sync --extra test`
  and `pip install -e ".[test]"` establish the test prerequisite on a clean clone.
- `examples/ir_minimal.json` — static, human-readable copy of the canonical
  minimal IR (`tests/compiler/test_examples_ir_minimal.py` pins it to the
  fixture factory) for `validate` / `compile` demos without a Python pipeline.
- README and `docs/quickstart.md` now separate the two console scripts
  (`proofhouse-compiler`, `proofhouse`), lead with tested uv commands, and give
  the Cursor skill install command (`python -m zipfile -e … ~/.cursor/skills`).
  `docs/showcase.md` is an executable 5-minute offline script.
- `proofhouse-compiler optimize new|compile|record|revise|status|criteria|verdict|check`:
  offline case workflow that renders the framework's clarify / compile / self-heal
  prompts as packets for the user's own host agent, records revisions, and checks
  them against user-declared criteria. No provider call, no scoring.
- `proofhouse-compiler models list|show|remember|forget`: model-note provenance
  (`builtin|cached|researched|fallback`), canonical ids, aliases, `verified_at`,
  stale warnings, and a local cache under `~/.proofhouse/` (`PROOFHOUSE_HOME`).
  The CLI never researches online.
- `proofhouse-compiler install-skill`: extracts the bundled `proofhouse.skill` into
  `~/.cursor/skills` and verifies `name: proofhouse`. The bundle, the framework
  JSON, and the model registry ship as package data.
- One reviewed registry (`src/proofhouse/optimize/data/model_registry.json`) now
  generates the framework `modelNotes` + `modelRegistry`, the framework Markdown
  table, the JSX `MODEL_NOTES`, the skill model paragraph, and the README
  supported-models table (`scripts/generate_model_surfaces.py --check` is a test).
- README "Surfaces" matrix scopes auto-research to the skill and artifact.

### Changed

- CI test matrix now includes Python 3.13 and 3.14 on Ubuntu, Windows, and
  macOS (Fable D6). Typescript-drift and wheel-install stay on 3.11.
- Q1 live model is `gpt-5.6-luna` (OAR-032). `execute-openai` still requires
  `--model` at call time; envelopes record `q1_unpicked: false`. Cost ceilings
  remain recorded, not enforced. Live stays opt-in and not CERTIFIED.
- Live OpenAI payload uses `max_completion_tokens` (Q1 `gpt-5.6-luna` rejects
  `max_tokens`).
- `execute-openai` reports `error` / `EXE-HTTP-0001` when the provider HTTP
  status is not 2xx (a completed send is not a successful completion).

## 0.2.1 - Skill Bundle Rebuild

### Fixed

- `skills/proofhouse/proofhouse.skill` was a hand-packed artifact last built
  2026-07-04. It shipped framework **v1.2** while the repository was on v1.3, so
  its model tables still listed superseded entries. Rebuilt from the source
  directory; the bundle now carries v1.3 and its entries are named `proofhouse/`.

### Added

- `scripts/build_skill_bundle.py` builds the bundle reproducibly — fixed
  timestamps and attributes, entry order sorted by name, text normalised to LF,
  and stored uncompressed, so the output does not depend on the platform or the
  Python version that packed it.
- `tests/test_skill_bundle.py` fails if the committed bundle and its source
  directory disagree, which is what went unnoticed for two months.


## 0.2.0 - Proofhouse Rename

### Changed

- Renamed the project from PromptRig to Proofhouse across the package, console
  scripts, schema `$id` namespaces, environment variables, generated TypeScript,
  brand-named files, and documentation.
- Python package `promptrig` is now `proofhouse` (`src/proofhouse/`).
- Schema `$id` namespaces moved to `proofhouse.dev` and `proofhouse.local`.
  `proofhouse.local` remains a deliberately non-resolving namespace.

### Added

- Console scripts `proofhouse` and `proofhouse-compiler`.
- Test-only environment names `PROOFHOUSE_LIVE*` (legacy fallback
  `PROMPTRIG_LIVE*`) are read by
  `tests/compiler/live/test_live_openai_q1_gate.py` under pytest marker `live`
  (deselected by default). `execution.py` does not read them. Removable at
  0.3.0 with the aliases.

### Deprecated

- Console scripts `promptrig` and `promptrig-compiler` remain as aliases for one
  minor version and are removable at 0.3.0.

### Unchanged

- The frozen contract schema `PROMPTRIG_IR_V0_1.schema.json` keeps its filename
  and its `$id`; it is a historical artifact and its identity is part of the record.
- Wire identifiers, media types, and canonical digest inputs are untouched. The
  three pinned `ir_sha256` digests are byte-identical across the rename.
- Maturity is unchanged: the requirements compiler remains `PARTIAL`.


## 0.1.1 - Showcase and Local Skill Adoption

### Added

- Public-facing README with quickstart, feature map, and repo navigation.
- Quickstart, showcase, Custom GPT setup, security, and contribution docs.
- Prompt audit example for before/after positioning.
- GitHub Actions CI workflow for tests and dataset validation.
- Source-controlled Codex skill package under `skills/promptrig/`.

### Changed

- Rubric scoring now accepts only integer values from 1 to 5.

## 0.1.0 - Initial PromptRig Scaffold

### Added

- PromptRig project identity
- Custom GPT identity: PromptOps Architect powered by PromptRig
- Core prompt
- Mode prompts for Default, Audit, Meta-Prompting, Agentic, and Evaluator modes
- Modular prompt components
- Reference policy
- Prompt quality rubrics
- JSONL test datasets
- Offline Python eval harness
- Basic tests

### Notes

This scaffold is intentionally lightweight. Provider-specific adapters can be added later after the core prompt architecture and eval datasets stabilize.
