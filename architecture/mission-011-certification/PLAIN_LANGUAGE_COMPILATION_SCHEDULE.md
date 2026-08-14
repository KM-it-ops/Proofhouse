# Plain-Language / Model-Assisted Compilation Schedule

**Decision (MISSION-011):** Plain-language and model-assisted requirements compilation MUST NOT be the first or only semantic implementation of requirements compilation.

## Ratified milestone order

1. **M0 (done):** Structured profiles (`structured_minimal_v0`, `structured_developer_v0`) compile headlessly with deterministic validation.
2. **M1 (authorized, in progress — MISSION-013):** Headless `plain_language_v0` constrained prose intake (see `architecture/mission-013-certification/PLAIN_LANGUAGE_V0_GRAMMAR.md`); emits `structured_minimal_v0` records subject to MISSION-008 deterministic validation before IR. **Not done** until MISSION-013 Task 6 and OAR-007 owner acceptance. M2 and M3 remain future.
3. **M2 (future, after M1):** Optional model-assisted suggestion stage that cannot bypass deterministic validation, authority/defaults, or evidence rules.
4. **M3 (future, after M1+M2 certified):** Product UI may expose Simple Mode only as a client of the already-certified headless path. Simple Mode UI semantics remain forbidden until M3.

## Hard rule

Any attempt to introduce Simple Mode semantics only in UI code, or to treat model output as canonical requirements without deterministic validation, is a certification failure.
