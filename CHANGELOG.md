# Changelog

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
