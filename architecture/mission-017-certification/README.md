# MISSION-008 File/API Envelope Producers (MISSION-017)

**Status:** OAR-011 Ready for owner acceptance. OAR-010 remains Accepted. OAR-009 remains Ready (not Accepted).
**Baseline:** local `main` @ `62a7e1b`.
**Scope:** `produce_requirements` turns file/api envelopes into canonical MISSION-008 artifact mappings. `compile_requirements` remains the sole rule engine via `compile_requirements_input`. Existing M0/M1/M2 closed-loop profiles unchanged.

This is Campaign COMPILER remaining 008 producers. Historical ambition-gap P2 "MISSION-017 platform SPECs" is not this mission.

## What this mission certifies (narrow)

- File and api authoring envelopes (structured claims/sources, not prose) assemble canonical records.
- Public `produce_requirements` / `compile_requirements_input`; CLI `compile-requirements` dispatches on payload shape.
- Compact `cases.json` remains test-only. This is not an authoring-prose interpreter.

## Non-claims

- Not full MISSION-008 production compiler (no freeform NLP; no Simple/Developer/PRS producers).
- Not full Roadmap Phase 4B exit (no rubric/dataset evaluation engine).
- Not M3 / Simple Mode UI.
- Not a live provider path; no credentials; network_allowed remains false on the certified path.
- Not freeform NLP; not live model-assisted suggestion.
- OQ-008-001 through OQ-008-009 remain open; this mission does not invent owner answers.
- Requirements compiler maturity remains PARTIAL.
- Ambition-gap C4 (IR v0.2 planning) is not this mission.
- OAR-011 Ready, not Accepted. OAR-009 remains Ready (not Accepted).
- An envelope with no explicit mappings cannot reach SUCCESS: synthesized mappings are unresolved and non-emitting.
