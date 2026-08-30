# Forbidden surfaces

These trees and profiles are **not this slice** and must not be extended or treated as Simple Mode or Developer Mode.

| Surface | Rule |
|---|---|
| `apps/dashboard` | Vite/React prototype. Must not become the product UI. |
| `apps/promptrig.jsx` | Conversational JSX. Must not gain compile/eval/repair semantics. |
| `profile=simple_mode_ui` | Forbidden on closed-loop (AE5). |
| `authoring_mode=simple_ui_only` | Forbidden on closed-loop. |
| Legacy `promptrig` PromptOps CLI | Not Compiler Core; not the hosted transport. |

Allowed intake once a UI exists: `plain_language_v0`, structured profiles, or `closed-loop-bridged-008`.

KTD8: Phase 8 is a new UI after Q2. Do not extend the Vite dashboard.
