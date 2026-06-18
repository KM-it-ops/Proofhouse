# Changelog

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
