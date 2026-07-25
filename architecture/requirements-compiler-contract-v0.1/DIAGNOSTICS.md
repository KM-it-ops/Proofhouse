# Requirements Compiler Diagnostics

**Status:** Proposed separate namespace. These codes do not modify or reuse the frozen Compiler Core diagnostic registry.

## Contract

- **DG-001:** Code format is `RQC-[A-Z]{3}-[0-9]{4}`.
- **DG-002:** Each code has stable severity, immutable/advisory classification, message key, parameters, and compatibility meaning.
- **DG-003:** A diagnostic identifies source location and related source/requirement IDs when available.
- **DG-004:** Messages are parameterized presentation; code and parameters carry machine meaning.
- **DG-005:** Unknown emitted codes cause `RQC-DIA-0001` and `INVALID_OUTPUT`.
- **DG-006:** Codes are never reused for different meaning; retirement preserves the record.
- **DG-007:** Ordering is severity rank (`error`, `warning`, `info`), code, URI, JSON Pointer, requirement ID, diagnostic ID.
- **DG-008:** Immutable diagnostics cannot be suppressed to change status; advisory diagnostics may be displayed without changing status.

## Proposed registry

| Code | Severity | Class | Meaning |
|---|---|---|---|
| `RQC-CTX-0001` | error | immutable | Required context is missing |
| `RQC-AMB-0001` | warning/error by requiredness | immutable | Meaning is ambiguous |
| `RQC-CFL-0001` | error | immutable | Source statements conflict |
| `RQC-CFL-0002` | error | immutable | Owner/user decisions conflict |
| `RQC-IDN-0001` | error | immutable | Duplicate requirement identity |
| `RQC-PRI-0001` | error | immutable | Priority claims contradict |
| `RQC-UNS-0001` | error | immutable | Required meaning/capability unsupported |
| `RQC-UNS-0002` | error | immutable | Import/reference behavior unsupported |
| `RQC-DFT-0001` | error | immutable | Hidden or unapproved consequential default |
| `RQC-APR-0001` | error | immutable | Required approval missing |
| `RQC-SRC-0001` | error | immutable | Duplicate source identity |
| `RQC-SRC-0002` | error | immutable | Source missing |
| `RQC-SRC-0003` | error | immutable | Source location invalid |
| `RQC-SRC-0004` | error | immutable | Source claims conflict |
| `RQC-SRC-0005` | warning | advisory | Stale/replaced source preserved |
| `RQC-EVD-0001` | error | immutable | Evidence or reference is incomplete/dangling |
| `RQC-MDL-0001` | error | immutable | Model output crossed the proposal boundary |
| `RQC-SEM-0001` | error | immutable | Output is semantically empty |
| `RQC-SCH-0001` | error | immutable | Schema/unknown-field violation |
| `RQC-VER-0001` | error | immutable | Contract version unsupported |
| `RQC-IRG-0001` | error | immutable | Required meaning has no IR v0.1 representation |
| `RQC-SEC-0001` | error | immutable | Security requirement failed closed |
| `RQC-PRV-0001` | error | immutable | Privacy/data-handling posture unknown or violated |
| `RQC-REF-0001` | error | immutable | Accepted policy refuses compilation |
| `RQC-BLK-0001` | error | immutable | Required meaning is blocked |
| `RQC-AUT-0001` | error | immutable | Authority precedence violation |
| `RQC-DIA-0001` | error | immutable | Unknown Requirements Compiler diagnostic emitted |

The machine-readable proposed registry is `requirements-diagnostic-registry.json`. It is package-local draft evidence and is not installed with PromptRig.

## Compatibility

- **DG-020:** Adding a code requires a proposed decision, normative clause, fixture, validator behavior, and owner review.
- **DG-021:** Changing severity or immutable/advisory class is a semantic breaking change.
- **DG-022:** Presentation text may change compatibly only when code meaning and parameters do not.
- **DG-023:** The registry version is independent from frozen `PRG-*` Compiler Core diagnostics.
