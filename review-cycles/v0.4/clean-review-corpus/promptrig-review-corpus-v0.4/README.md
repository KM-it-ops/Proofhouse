# PromptRig Design Review & Research Edition v0.3

This repository is the living source of truth for PromptRig. It supersedes the snapshot-only workflow used in Foundation Packs v0.1 and v0.2 while preserving those packs under `archive/`.

## Purpose of this release

v0.3 prepares PromptRig for an architecture freeze before production code is generated. It adds research controls, architecture decision records, design-review protocols, reviewer-specific critique prompts, resolution tracking, and implementation-entry gates.

## Release status

**Design-review ready; not implementation-authorized.**

Production coding begins only after the Architecture Review Board records all blocking findings, approves the architecture-freeze checklist, and creates the executable starter repository.

## Source-of-truth precedence

1. `00-governance/PROJECT_CHARTER.md`
2. `01-vision/PROMPTRIG_MASTER_SCOPE.md`
3. accepted ADRs in `03-architecture/adrs/`
4. accepted RFCs in `03-architecture/rfcs/`
5. `04-specification/`
6. `05-benchmark/`
7. research and implementation guidance
8. archived packs and conversation history

When sources conflict, stop, record the conflict, and resolve it through an ADR or change request. Never silently choose the convenient interpretation.

## Next release

After review and freeze: **PromptRig v0.4 — Executable Benchmark Starter Repository**.


## v0.4 review execution

Start with `09-review-execution/EXECUTION_RUNBOOK.md`. This release does not authorize production implementation.
