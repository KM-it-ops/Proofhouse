# Headless Core Certification Package v0.1 (MISSION-011)

**Status:** Certification evidence for headless core promotion under campaign pre-authorization.  
**Freeze:** MISSION-008 contract `0.1.0-draft`, MISSION-009 contract `0.1.0-draft`, MISSION-010 prototype `mission-010-closed-loop-v0.1` at merge of PR #17.

## Approved authoring profiles (implemented headlessly)

| Profile | Status |
|---|---|
| `structured_minimal_v0` | Implemented in `closed_loop.requirements_to_ir` |
| `structured_developer_v0` | Implemented (developer-mode envelope → same IR mapping with mandatory tool/stop constraints) |

## Explicitly not first semantic path

Plain-language / model-assisted Simple Mode is **not** implemented as the semantic requirements compiler. See [PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md](PLAIN_LANGUAGE_COMPILATION_SCHEDULE.md).

## Certification checklist

- Requirement→IR→fake-adapter→eval→repair traces with failed attempts retained
- Repair budgets 0/1/2 terminate correctly
- No-network / no-credential defaults
- Library/CLI parity for `closed-loop`
- Packaging: editable install + CLI entry smoke
- Adversarial/security review recorded in SDD ledger

## Non-claims

Live providers, hosted UI, benchmarks/marketing claims, MissionRig, IR v0.2 remain unauthorized.
