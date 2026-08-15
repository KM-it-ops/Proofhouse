# Plain-Language / Model-Assisted Compilation Schedule

**Decision (MISSION-011):** Plain-language and model-assisted requirements compilation MUST NOT be the first or only semantic implementation of requirements compilation.

## Ratified milestone order

1. **M0 (done):** Structured profiles (`structured_minimal_v0`, `structured_developer_v0`) compile headlessly with deterministic validation.
2. **M1 (implemented, OAR-007 Accepted 2026-08-14 — MISSION-013):** Headless `plain_language_v0` constrained prose intake (see `architecture/mission-013-certification/PLAIN_LANGUAGE_V0_GRAMMAR.md`); emits `structured_minimal_v0` records subject to MISSION-008 deterministic validation before IR. M3 remains future.
3. **M2 (implemented, OAR-008 Accepted 2026-08-14 — MISSION-014):** Optional headless `fake-suggester-v0` suggestion sidecar (see `architecture/mission-014-certification/FAKE_SUGGESTER.md`); proposals remain `acceptance_state=proposed` and are never mapped to IR; cannot bypass deterministic validation, authority/defaults, or evidence rules; not a live provider.
4. **M3 (future, after M1+M2 certified):** Product UI may expose Simple Mode only as a client of the already-certified headless path. Simple Mode UI semantics remain forbidden until M3.

## Hard rule

Any attempt to introduce Simple Mode semantics only in UI code, or to treat model output as canonical requirements without deterministic validation, is a certification failure.
