# MISSION-008 OQ-008-001/002/006 Implementation (MISSION-021)

**Status:** OAR-015 Accepted 2026-08-23. OAR-014 through OAR-009 remain Accepted.
**Baseline:** local `main` @ `ca888a8`.
**Scope:** Implement owner-resolved OQ-008-001 (file digest when stable bytes exist), OQ-008-002 (optional unresolved meaning → PARTIAL with evidence), and OQ-008-006 (SUCCESS may carry advisory non-semantic diagnostics) in the existing `evaluate_contract_rules` engine and file-envelope producer.

This is Campaign COMPILER remaining 008 policy implementation. Not a full production compiler.

## What this mission certifies (narrow)

- OQ-008-001: file sources without `sha256` and without `fragment_digest` remain fail-closed; the OQN text names the implemented policy (not "unanswered").
- OQ-008-002: optional accepted unmapped meaning and optional `no_ir_representation` become PARTIAL with evidence; required gaps stay BLOCKED (`RQC-BLK-0001`).
- OQ-008-006: SUCCESS may include emitted advisory codes with registry `semantic: false` (`RQC-ADV-0001`). `RQC-SRC-0005` remains PARTIAL.
- Valid constrained `plain_language_v0` grammar remains BLOCKED (`RQC-BLK-0001`); numbered/constraint mappings stay unresolved.

## Non-claims

- Not full MISSION-008 production compiler. Remaining executable OQs after 001/002/006 are MISSION-022 (003/005/010 implemented there; 004/007/008/009 locked-not-built).
- Not full Roadmap Phase 4B exit (no rubric/dataset evaluation engine).
- Not M3 / Simple Mode UI.
- Not a live provider path; no credentials; network_allowed remains false on the certified path.
- Not freeform NLP; not live model-assisted suggestion.
- PRS **language** (grammar, parser, CONTRACT_CANDIDATE) remains DEFERRED per `PRS_DISPOSITION.md`.
- Requirements compiler maturity remains PARTIAL.
- OAR-015 Accepted 2026-08-23. OAR-014 through OAR-009 Accepted.
