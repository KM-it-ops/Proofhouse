# Requirements Compiler Contract and Evidence Model v0.1

**Status:** `PROPOSED` by MISSION-008. This package is executable contract evidence under draft review. It is not owner-ratified, production-certified, or implementation authority.

**Exact baseline:** `feature/promptrig-framework` at `b12b8262449d1a04cb3802f17f5f44f9a84de5d4`.

## Purpose

This package defines a source-language-neutral, deterministic validation boundary between authoring input and evidence-bearing requirements that can be mapped honestly to frozen PromptRig IR v0.1. It specifies meaning, authority, defaults, evidence, diagnostics, statuses, and traceability without compiling ordinary language or changing IR.

The package is executable through draft JSON Schemas, evidence-first fixtures, a test-only semantic validator, and deterministic validation evidence. Green validation proves internal consistency of this proposal only.

## Scope

In scope:

- ordinary-language, Developer Mode-style, API, and file authoring envelopes;
- stable requirements and source evidence;
- authority, defaults, approvals, ambiguity, conflict, refusal, and blocked meaning;
- separate proposed Requirements Compiler diagnostics;
- requirement-to-IR and requirement-to-test evidence;
- proposed PRS disposition and owner decisions.

Out of scope:

- a production requirements compiler or natural-language interpreter;
- a model call, prompt-only compiler, or production PRS parser;
- evaluation, repair, runtime state, provider execution, UI, hosted infrastructure, benchmarks, or downstream products;
- changes to frozen PromptRig IR v0.1 or its frozen diagnostic registry;
- MISSION-009, MISSION-010, or MISSION-011 work.

## Package index

| File or directory | Role |
|---|---|
| [REQUIREMENTS_COMPILER_SPEC.md](REQUIREMENTS_COMPILER_SPEC.md) | Normative terms, lifecycle, statuses, transitions, determinism, and fail-closed rules |
| [AUTHORITY_AND_DEFAULTS.md](AUTHORITY_AND_DEFAULTS.md) | Authority precedence, override rules, defaults, and approvals |
| [REQUIREMENTS_EVIDENCE_MODEL.md](REQUIREMENTS_EVIDENCE_MODEL.md) | Required evidence records and acceptance distinctions |
| [SECURITY_PRIVACY_APPROVALS.md](SECURITY_PRIVACY_APPROVALS.md) | Security, privacy, permission, refusal, and human approval rules |
| [DIAGNOSTICS.md](DIAGNOSTICS.md) | Proposed `RQC-*` diagnostic namespace |
| [TRACEABILITY.md](TRACEABILITY.md) | Input-to-evidence-to-requirement-to-IR/gap/test chain |
| [PRS_DISPOSITION.md](PRS_DISPOSITION.md) | Evidence-based PRS disposition recommendation |
| [DECISION_LOG.md](DECISION_LOG.md) | Proposed MISSION-008 decisions only |
| [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) | Unresolved semantics and evidence thresholds |
| [OWNER_DECISION_REQUEST.md](OWNER_DECISION_REQUEST.md) | Exact owner choices and non-authorizations |
| `schemas/` | Eight Draft 2020-12 proposed schemas |
| `fixtures/` | Evidence-first positive, boundary, negative, and adversarial cases |
| `evidence/` | Deterministic inventories, mappings, hashes, results, gaps, and PRS matrix |
| `validate_contract.py` | Test-only package validator; not product runtime |

## Authority order

The controlling order is:

1. explicit owner decisions within their declared scope;
2. explicit user decisions that do not conflict with owner policy or accepted contracts;
3. accepted versioned contracts;
4. attributable source evidence;
5. explicitly authorized authoring-mode defaults;
6. deterministic derivations allowed by contract;
7. model-assisted suggestions;
8. provider constraints;
9. implementation convenience.

Lower sources never silently override higher sources. Conflict with a higher source is visible evidence and usually `BLOCKED` or `REFUSED`.

## Authoring surfaces

Simple Mode, Developer Mode, APIs, and files are replaceable producers of the same intent-input and evidence contracts. No surface owns canonical meaning. A future PRS language, if retained, must produce the same records with equal source-location and authority fidelity.

## Relationship to PromptRig IR

PromptRig IR remains the durable semantic center after accepted requirements. This package:

- maps accepted meaning to exact IR v0.1 JSON Pointers;
- preserves every unmappable requirement through a stable diagnostic and IR-gap record;
- prohibits unmapped IR leaves and silent requirement loss;
- does not edit or extend IR v0.1.

## Non-authorization

This package authorizes no production compiler, parser, model integration, IR lowering implementation, CLI/API feature, evaluation, repair, live execution, UI, hosted service, benchmark, release, tag, or later mission. Owner approval of this proposal would ratify contract direction only; implementation still requires separately authorized MISSION-010 and production certification requires MISSION-011.
