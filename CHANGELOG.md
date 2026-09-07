# Changelog

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
- Environment variables `PROOFHOUSE_LIVE*` for opt-in live runs.

### Deprecated

- Console scripts `promptrig` and `promptrig-compiler` remain as aliases for one
  minor version and are removable at 0.3.0.
- Environment variables `PROMPTRIG_LIVE*` remain as a fallback that warns once
  per process, also removable at 0.3.0.

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
