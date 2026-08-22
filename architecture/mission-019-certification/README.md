# MISSION-008 PRS Envelope Producers (MISSION-019)

**Status:** OAR-013 Ready (not Accepted). OAR-012 Accepted 2026-08-22. OAR-011 and OAR-010 remain Accepted. OAR-009 remains Ready (not Accepted).
**Baseline:** local `main` @ `e64655e` (MISSION-019 worktree start).
**Scope:** Extend `produce_requirements` so structured `authoring_mode=prs` envelopes assemble canonical MISSION-008 artifact mappings and evaluate via the existing `compile_requirements` engine. File, api, simple, and developer envelope producers from MISSION-017/018 remain unchanged.

This is Campaign COMPILER remaining 008 producers. Historical ambition-gap P2 "MISSION-017 platform SPECs" is not this mission.

## What this mission certifies (narrow)

- PRS (`authoring_mode=prs`, structured `prs` sources) envelopes assemble canonical records.
- Public `produce_requirements` / `compile_requirements_input`; CLI `compile-requirements` dispatches on payload shape.
- File, api, simple, and developer envelope producers from MISSION-017/018 remain in scope and unchanged.
- Compact `cases.json` remains test-only. This is not an authoring-prose interpreter.

## Non-claims

- Not full MISSION-008 production compiler (no freeform NLP; authoring-prose remains unauthorized).
- Not full Roadmap Phase 4B exit (no rubric/dataset evaluation engine).
- Not M3 / Simple Mode UI (`authoring_mode=prs` here is the 008 envelope mode, not M3 UI semantics).
- Not a live provider path; no credentials; network_allowed remains false on the certified path.
- Not freeform NLP; not live model-assisted suggestion.
- OQ-008-001 through OQ-008-009 remain open; this mission does not invent owner answers.
- PRS **language** (grammar, parser, CONTRACT_CANDIDATE) remains DEFERRED per `PRS_DISPOSITION.md`; this mission implements only the structured envelope producer, not a PRS language implementation.
- Requirements compiler maturity remains PARTIAL.
- Ambition-gap C4 (IR v0.2 planning) is not this mission.
- OAR-013 Ready (not Accepted). OAR-012 Accepted. OAR-011 and OAR-010 Accepted. OAR-009 remains Ready (not Accepted).
- An envelope with no explicit mappings cannot reach SUCCESS: synthesized mappings are unresolved and non-emitting.
