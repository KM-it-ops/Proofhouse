# MISSION-030 008 SUCCESS→IR Bridge

**Status:** OAR-023 Ready (not Accepted).
**Baseline:** Campaign remaining-product U4 on MISSION-027/029 (`eb58a13` product-eval CLI parity on top of 027). Skip-cert law is OAR-022 Ready (not undone).
**Scope:** Explicit library/CLI bridge from canonical 008 SUCCESS (and honest PARTIAL with representable IR) into `structured_minimal_v0`, then existing fake closed-loop. Does not re-implement 027/029 engines. Does not teach `closed-loop` / `closed_loop_from_json` to parse 008 envelopes.

This mission does not promote the requirements compiler.

## What this mission records (narrow)

- **OAR-023 Ready (not Accepted).** This record is Ready until Boss Accepts. Do not treat it as Accepted.
- Requirements compiler stays **PARTIAL**. **Not CERTIFIED**. Not full MISSION-008. Not full Roadmap **Phase 4B** exit. Not M3.
- Fake-adapter eval/repair oracle stays **CERTIFIED**. CERTIFIED never expands scope.
- Constructor: `compile_requirements` on the 008 artifact set; project accepted mappings + `requirements_document` into `structured_minimal_v0` (`objective.goal` from `/objective/goal`, `requirements` every REQ-* id+statement, `network_allowed` false); then existing `requirements_to_ir` and fake closed-loop. RFC 6901 pointers are not applied onto IR v0.1.
- Unbridged 008 JSON on `closed-loop` stays **BLOCKED** `EVR-RQC-0001`.
- BLOCKED / REFUSED / INVALID_OUTPUT 008 outputs do not lower. PARTIAL without representable goal/requirements fails closed (`EVR-BRG-0001`); meaning is not invented.
- **OQ-008-004** / **OQ-008-007** / **OQ-008-008** / **OQ-008-009** remain locked-not-built.
- `EVR-SEC-0001` and `network_allowed=false` unchanged. Repair budgets `{0,1,2}`.
- `simple_mode_ui` / `simple_ui_only` stay forbidden on closed-loop.
- OAR-022 skip-cert stays Ready (sibling record, not rewritten). Peer review is **not a gate**. Independent 4B-exit certification is not a Phase 5–9 entry gate.
- OAR-021 remains MISSION-027. OAR-022 remains MISSION-028. This mission does not Accept either.

## Non-claims

- Not CERTIFIED requirements compiler. Not full MISSION-008. Not full Phase 4B exit.
- Not **M3** / **Simple Mode** UI.
- **Not a live** provider path. **Not freeform** NLP. No IR v0.2.
- Skip-cert law (OAR-022) is not undone.
