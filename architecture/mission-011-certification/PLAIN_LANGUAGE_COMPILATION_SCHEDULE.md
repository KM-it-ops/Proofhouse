# Plain-Language / Model-Assisted Compilation Schedule

**Decision (MISSION-011):** Plain-language and model-assisted requirements compilation MUST NOT be the first or only semantic implementation of requirements compilation.

## Ratified milestone order

1. **M0 (done):** Structured profiles (`structured_minimal_v0`, `structured_developer_v0`) compile headlessly with deterministic validation.
2. **M1 (future, separate authorization):** Headless plain-language intake that emits structured requirements records subject to MISSION-008 deterministic validation before IR.
3. **M2 (future, after M1):** Optional model-assisted suggestion stage that cannot bypass deterministic validation, authority/defaults, or evidence rules.
4. **M3 (future, after M1+M2 certified):** Product UI may expose Simple Mode only as a client of the already-certified headless path.

## Hard rule

Any attempt to introduce Simple Mode semantics only in UI code, or to treat model output as canonical requirements without deterministic validation, is a certification failure.
