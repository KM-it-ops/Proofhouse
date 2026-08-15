# Installed-package consumer matrix (MISSION-015)

Consumers import **only** `promptrig.compiler.api`. They run from an isolated venv install (no `PYTHONPATH=src`).

| Case | Input | Expect |
|---|---|---|
| Structured closed-loop | `closed_loop_requirements_minimal.json` | PASS, IR digest present, no proposal |
| `plain_language_v0` | grammar text envelope | PASS, `intake_profile=plain_language_v0` |
| Opt-in `fake-suggester-v0` | structured + `--enable-model-suggestions` | PASS, proposal `acceptance_state=proposed`, `authority_basis=model_suggested`, `proposed_records=["REQ-MS-001"]`, IR digest equals suggestion-off |
| Simple Mode | `authoring_mode=simple_ui_only` | BLOCKED, Simple Mode diagnostic |
| `network_allowed` true | structured doc with `network_allowed: true` | BLOCKED, `EVR-NET-0001` |
| No credentials | credential env keys stripped | same PASS as structured (no key required) |

Existing PYTHONPATH smokes in MISSION-012/013/014 are not replaced.
