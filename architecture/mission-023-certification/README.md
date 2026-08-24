# MISSION-023 Plain-Language IR Mapping (numbered + constraints)

**Status:** OAR-017 Accepted 2026-08-24.
**Baseline:** Campaign COMPILER remaining work after MISSION-022.
**Scope:** Map constrained `plain_language_v0` prose — Goal, numbered requirements, and optional constraint lines — to existing v0.1 IR pointers via `direct` outcome and `target_pointer` fields.

This is Campaign COMPILER plain-language mapping. Not a full production compiler.

## What this mission certifies (narrow)

- **Profile:** `plain_language_v0` only; offline certified path (`network_allowed=false`, no credentials, no live providers).
- **Goal line:** maps `direct` to `/objective/goal`.
- **Numbered requirement lines:** map `direct` to `/requirements/{n}/statement` for each numbered item.
- **Constraint lines:** map `direct` to `/behavior/constraints/{n}` for each constraint item.
- **Compile outcome:** a valid constrained write-up (Goal + numbered list + optional constraints) compiles **SUCCESS** — not invented IR shapes and not `RQC-BLK-0001` for this hole.
- **Explicit non-mappings:** does not mint mappings for optional `Project:` lines or for closed-loop default instructions.
- **Locked OQs (remain not built):** OQ-008-004 (no identity merge / no alias-group object), OQ-008-007 (PRS language DEFERRED), OQ-008-008 (no continuation IR field), OQ-008-009 (no reasoning IR field).

## Non-claims

- Not full MISSION-008 production compiler.
- Requirements compiler maturity remains **PARTIAL** per `CAPABILITY_MATURITY_MAP.md`.
- Not full Roadmap **Phase 4B** exit (no rubric/dataset evaluation engine).
- Not **M3** / **Simple Mode** UI.
- **Not a live** provider path; no credentials; `network_allowed` remains false on the certified path.
- **Not freeform** NLP; not live model-assisted suggestion; no PRS language/grammar unlock.
- No IR v0.2 fields. No Phase 6–9 product surfaces.
- OAR-014, OAR-015, and OAR-016 remain **Accepted** historical snapshots (including their prior “blocked” wording for earlier campaign scope). OAR-017 Accepted 2026-08-24.
