# Decision log

| ID | Decision | Status | Evidence |
|---|---|---|---|
| D-050-001 | Freeze only the Compiler Core v0.1 boundary, not the hosted product or benchmark architecture. | Accepted | Review synthesis; unresolved benchmark and tenant findings; OAR-001 |
| D-050-002 | Use strict PromptRig IR v0.1 with no unknown fields and no duplicate semantic owners. | Accepted | Claude/Codex/Gemini IR findings; OAR-001 |
| D-050-003 | Set repair limit to 0–2 in IR; repair execution remains out of v0.1. | Accepted | Accepted v0.4 intent and cross-schema contradiction findings; OAR-001 |
| D-050-004 | Use Python 3.11+ for Compiler Core and CLI; generate TypeScript contracts for consumers. | Accepted | Existing package, platform matrix, cross-platform goals; OAR-001 |
| D-050-005 | Keep all v0.1 compiler passes deterministic and offline. | Accepted | Reproducibility and benchmark findings; OAR-001 |
| D-050-006 | Make OpenAI the first live adapter target, Anthropic the second conformance target, Gemini the third. | Accepted | Provider matrix and strategic validation breadth; OAR-001 |
| D-050-007 | CLI wraps the same public library and returns stable JSON envelopes and exit codes. | Accepted | Mission requirement; parity contract; OAR-001 |
| D-050-008 | Preserve historical review artifacts byte-for-byte. | Accepted | Architect Mode law and mission policy |
| D-050-009 | Ship Compiler Core v0.1 CLI as its own `promptrig-compiler` binary, not merged into the legacy `promptrig` binary, to resolve the `validate` command-name collision. | Accepted | ADR-005; MISSION_002_REPORT.md Deviations item 1; owner ratification during MISSION-002 review |
| D-050-010 | Record, as a candidate (not yet accepted) architectural gap, that PromptRig IR v0.1 has no field for a per-request reasoning/thinking configuration, per two independent adapter findings. No schema change is authorized by this entry. | Proposed | ADR-006; MISSION_002_REPORT.md; MISSION_003_REPORT.md; MISSION_004_REPORT.md |
| D-050-011 | Accept ADR-006: PromptRig IR v0.1's missing per-request reasoning/thinking configuration field is a confirmed architectural gap, per three independent adapter findings (OpenAI, Anthropic, Gemini). No specific schema-change shape is authorized by this acceptance, only the existence and reality of the gap. | Accepted | ADR-006; MISSION_003_REPORT.md; MISSION_004_REPORT.md; MISSION_005_REPORT.md |
| D-050-012 | Record, as a candidate (not yet accepted) architectural gap, that PromptRig IR v0.1 has no multi-turn/conversation-state concept, so it cannot carry provider-returned opaque continuation state (e.g. Gemini's thought-signature) across requests. No schema change is authorized by this entry. | Proposed | ADR-007; MISSION_005_REPORT.md |
| D-050-013 | Accept the corrected MISSION-007 strategy package, `ROADMAP_V1.md`, its ten-stage dependency order, the MISSION-008 through MISSION-011 sequence, mandatory Phase 4B/MISSION-011 headless-core hardening and certification, and all associated deferrals and non-claims. Acceptance governs strategy and sequence only: it does not authorize MISSION-008, MISSION-009, MISSION-010, or MISSION-011 execution; does not accept ADR-007; and does not authorize live execution, hosted-product work, benchmarks, IR v0.2 implementation, a fifth adapter, merge automation, or tag changes. | Accepted | `architecture/strategy/`; MISSION_007_REPORT.md; PR #12 independent architectural review; explicit owner approval of DR-007-01 through DR-007-09 recorded in PR #12 |

OAR-001 binds Compiler Core v0.1. Accepted rows bind their declared scope; D-050-013 governs strategy and sequence upon merge and authorizes no implementation. Deferred product-surface questions remain outside this freeze.
