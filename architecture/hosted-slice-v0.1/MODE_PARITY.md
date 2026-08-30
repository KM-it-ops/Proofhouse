# Mode-parity contract

Simple Mode and Developer Mode are two views of one canonical project. They are not two compilers.

## Invariants

1. Both modes address the same `project_id`.
2. Both modes display the same `ir_sha256` as `promptrig-compiler closed-loop` for the same intake.
3. Evidence bundle identity, evaluation status, and unresolved defects match the CLI.
4. Presentation chrome is not canonical. Hidden UI configuration is REJ-007.
5. Intake is `plain_language_v0`, `structured_minimal_v0` / `structured_developer_v0`, or `closed-loop-bridged-008`. Not `simple_mode_ui`.

## Surfaces in agreement

Library, CLI, generated OpenAPI default slice, Simple Mode, Developer Mode.

## Fail-closed cases

| Case | Fixture | Expected |
|---|---|---|
| Same project, both modes | `mode_parity_project.json` | `same_ir_digest` |
| `simple_mode_ui` | `simple_mode_ui_forbidden.json` | BLOCKED (AE5) |
| Empty project | `empty_project.json` | fail_closed, visible in both modes |
| PARTIAL compile | `partial_project.json` | partial_visible_in_both_modes |
| Hidden UI config | `hidden_ui_config_rejected.json` | rejected (REJ-007) |

Switching modes is reversible and must not mutate IR.
