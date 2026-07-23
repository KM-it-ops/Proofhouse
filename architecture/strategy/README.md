# PromptRig Strategy Package

**Package status:** Proposed by MISSION-007. Independent architectural review returned a narrow correction requiring mandatory headless-core hardening and certification; the corrected roadmap and mission sequence are not authoritative until final independent review and explicit owner approval.

## Package index

| Document | Role | Authority before owner approval | Authority after owner approval |
|---|---|---|---|
| [Product Vision](PROMPTRIG_PRODUCT_VISION.md) | Concise product identity, canonical pipeline, system/product boundaries, and doctrines | Proposed normative reconciliation constrained by the MISSION-007 authorization | Normative strategy |
| [Capability Maturity Map](CAPABILITY_MATURITY_MAP.md) | Evidence-bound statement of what is certified, implemented, partial, proposed, deferred, or absent | Descriptive baseline | Descriptive baseline; future changes require evidence |
| [Roadmap V1](ROADMAP_V1.md) | Dependency order, phase gates, critical path, and safe parallel work | Proposed | Normative sequencing; phase entry still needs separate authorization |
| [Deferred and Rejected Work](DEFERRED_AND_REJECTED_WORK.md) | Deferrals, rejected shortcuts, obsolete assumptions, debt classes, and promotion triggers | Proposed governance | Normative sequencing guardrail |
| [Requirement-to-Roadmap Traceability](REQUIREMENT_TO_ROADMAP_TRACEABILITY.md) | Strategic-law and product-requirement mapping to evidence, phases, tests, and owner decisions | Proposed mixed normative/descriptive record | Normative traceability contract plus descriptive status |
| [Mission Sequence V1](MISSION_SEQUENCE_V1.md) | Recommended MISSION-008–011 purpose, scope, tests, stop conditions, and merge gates | Proposed | Normative sequence only; each mission needs separate launch authority |
| [Roadmap Decision Request](ROADMAP_DECISION_REQUEST.md) | Exact owner choices, recommendations, alternatives, and consequences | Pending decision package | Historical decision evidence after an owner record is added |

## Authority order

When sources disagree, use this order:

1. explicit owner acceptance records and accepted current ADRs;
2. frozen versioned contracts within their declared scope;
3. an owner-ratified version of this strategy package;
4. current implementation, tests, CI, package metadata, and merged PR outcomes as evidence of actual behavior, not authority to change architecture;
5. mission reports as point-in-time evidence;
6. deferred proposals;
7. preserved historical review material.

A lower-ranked source cannot silently amend a higher-ranked source. Current code that contradicts an accepted contract is a defect, not a new decision.

## Source authority register

The classifications below satisfy the MISSION-007 reconciliation requirement. `CURRENT_AND_AUTHORITATIVE` is always limited to the source's declared scope.

| Source | Classification | Reconciliation treatment |
|---|---|---|
| Owner-supplied `PROMPTRIG_STRATEGIC_RECONCILIATION_AND_FORWARD_FOCUS_LOCK.md` | `CURRENT_AND_AUTHORITATIVE` mission input; incomplete as repository governance | Supplies the non-negotiable vision and critical-path direction; this package translates it into repository-native proposed governance |
| MISSION-007 execution prompt | `CURRENT_AND_AUTHORITATIVE` mission authorization | Controls scope, required deliverables, stop conditions, baseline, branch, validation, and no-merge boundary |
| PR #12 independent architectural review | `CURRENT_AND_AUTHORITATIVE` correction finding, not owner ratification | Found that MISSION-010 was a bounded prototype with no mandatory productionization dependency; blocks merge until Phase 4B/MISSION-011 and affected mappings are corrected |
| PR #12 headless-core gate correction prompt | `CURRENT_AND_AUTHORITATIVE` correction authorization | Limits the response to documentation/governance changes on the existing branch and PR; requires preservation of the original seven commits, final-head validation/CI, and no mission implementation |
| [OAR-001](../OWNER_ACCEPTANCE_RECORDS/OAR-001.md) | `CURRENT_AND_AUTHORITATIVE` | Binds Python 3.11+, adapter order, IR 0.1.0, canonical hashing, and diagnostic registry for Compiler Core v0.1 |
| [ADR-000](../adr/ADR-000-Project-Principles.md), [ADR-005](../adr/ADR-005-Compiler-Core-CLI-Entry-Point.md), [ADR-006](../adr/ADR-006-Reasoning-Configuration-IR-Gap.md) | `CURRENT_AND_AUTHORITATIVE` within stated scopes | Preserved; roadmap must comply |
| [ADR-001](../adr/ADR-001-PromptRig-Specification.md), [ADR-002](../adr/ADR-002-AI-Engineering-Workspace.md), [ADR-003](../adr/ADR-003-MissionRig.md), [ADR-004](../adr/ADR-004-Structured-Mission-Format.md) | `DEFERRED_PROPOSAL` or accepted direction with deferred implementation | Do not treat as executable product capability; mapped to Phases 2 and 9 |
| [ADR-007](../adr/ADR-007-Multi-Turn-State-IR-Gap.md) and its owner request | `UNRESOLVED_OWNER_DECISION` | Remains Proposed; no IR change; MISSION-007 recommends an explicit evidence threshold |
| Frozen contract files under `architecture/compiler-contract-freeze-v0.5/` | `CURRENT_AND_AUTHORITATIVE` for Compiler Core v0.1 | Contract contents remain binding; the directory README's candidate wording is stale metadata |
| Freeze-package README and [architecture index](../README.md) | `CURRENT_BUT_INCOMPLETE` | They predate ratification/implementation and do not report current maturity; this package supersedes their roadmap/status implications |
| Freeze [decision log](../compiler-contract-freeze-v0.5/DECISION_LOG.md) | `CURRENT_AND_AUTHORITATIVE` per-row status | Accepted rows bind their scope; Proposed rows remain non-binding |
| Freeze open questions | `CURRENT_BUT_INCOMPLETE` | Correctly defers product surfaces but predates MISSION-002–006 implementation and this dependency order |
| Language/platform and provider-selection decisions in the freeze package | `CURRENT_AND_AUTHORITATIVE` for v0.1 compiler and initial conformance targets | Preserve Python/TypeScript boundary and fake→OpenAI→Anthropic→Gemini set; they do not freeze hosted platform or a fifth adapter |
| PRS overview, syntax, examples, and roadmap | `DEFERRED_PROPOSAL` | Examples are non-binding; MISSION-008 must accept, defer, or reject the PRS direction |
| Root `README.md` | `CONTRADICTORY` for current status; otherwise current project documentation | Claims Python 3.10+, no adapters, and a next step inconsistent with package/code evidence; this package supersedes those strategic-status claims without editing the README |
| `pyproject.toml`, `src/promptrig/compiler/`, generated contracts, tests, and `.github/workflows/ci.yml` at the baseline | `CURRENT_AND_AUTHORITATIVE` evidence of implemented behavior | Used to assign maturity; code cannot ratify architecture by existence |
| Legacy `src/promptrig` eval/report tooling | `CURRENT_BUT_INCOMPLETE` | It is a legacy PromptOps dataset/rubric surface, not the canonical Compiler Core evaluation/repair stage |
| `apps/dashboard` Vite application and `apps/promptrig.jsx` | `CURRENT_BUT_INCOMPLETE` prototypes | Neither implements shared canonical Simple/Developer modes; no hosted-product maturity claim |
| `MISSION_REPORT.md` and `MISSION_002_REPORT.md` through `MISSION_006_REPORT.md` | `HISTORICAL_EVIDENCE_ONLY` for point-in-time mission state | Capability/test/debt evidence is useful; “PR open/draft” statements do not override later GitHub merges |
| GitHub PR #1 through #11 metadata and merge commits | `CURRENT_AND_AUTHORITATIVE` for PR outcome and merge state | All eleven are merged; PR #11 merge commit is the required baseline |
| `review-cycles/v0.4/` as a corpus | `HISTORICAL_EVIDENCE_ONLY` | Immutable evidence; no document in the corpus directly governs current work |
| v0.4 Project Charter and Product Constitution | `HISTORICAL_EVIDENCE_ONLY` with selected principles retained | Product thesis, provider neutrality, evidence, nontechnical UX, and whole-system benchmarking are carried forward only through this package |
| v0.4 Master Scope and Status/Decisions | `SUPERSEDED` where they claim IR 0.2.0, benchmark readiness, mandatory hosted stack, or current Supabase commitment | Current OAR, code, and strategy package take precedence |
| v0.4 Baseline Architecture and Next.js/FastAPI ADR | `HISTORICAL_EVIDENCE_ONLY` and current future-target input | Next.js/FastAPI remain proposed for Phase 8 and require renewed ratification |
| v0.4 Supabase ADR | `SUPERSEDED` as inherited commitment | Supabase is one future candidate, not the default |
| v0.4 compiler/provider/evaluation RFCs | `HISTORICAL_EVIDENCE_ONLY` or `DEFERRED_PROPOSAL` | Useful requirements are remapped; review-status RFCs are not current contracts |
| v0.4 benchmark rules, environment, rubric, manifest, and claims policy | `HISTORICAL_EVIDENCE_ONLY` and deferred design input | Whole-configuration doctrine is retained; no runner, sealed source, or result is claimed |
| v0.4 release roadmap | `SUPERSEDED` | Replaced by `ROADMAP_V1.md` after approval; Phase A “complete” and benchmark-first sequencing are not current |

## Supersedence boundary

After owner approval, this package supersedes older roadmap, phase-order, maturity, product-status, inherited-platform, and adapter-expansion statements. It does not edit or supersede:

- OAR-001 or accepted current ADRs;
- frozen Compiler Core v0.1 contracts;
- historical mission/review evidence;
- exact merged PR and tag history.

Conflicting historical statements remain available for audit and must be described as historical when cited.

## Future update contract

A mission that changes product identity, phase order, entry/exit criteria, capability status, a strategic-law mapping, or a deferred/rejected disposition must update all affected package documents and append a decision-log entry in the same PR. Evidence must name exact contracts, code, tests, artifacts, and CI results. New roadmap versions remain proposed until independent review and explicit owner acceptance.

No future mission may call a phase complete from test counts alone. The manual review must confirm current meaning, non-claims, deferred boundaries, and requirement-to-evidence coverage.

## Disagreement escalation

When code, documents, reviewers, or owner requests conflict:

1. stop the affected implementation;
2. record the exact conflicting sources and scope;
3. classify whether the issue is defect, drift, ambiguity, or proposed architecture change;
4. preserve historical evidence;
5. request an ADR/SPEC/OAR or owner decision at the correct authority level;
6. resume only from an explicitly accepted resolution.

Coding agents and reviewers may recommend; they may not silently ratify.
