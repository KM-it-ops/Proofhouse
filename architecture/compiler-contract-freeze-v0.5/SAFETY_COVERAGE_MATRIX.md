# Safety coverage matrix — MISSION-006

| Policy surface | Enforced behavior | Result when unresolved | Evidence |
|---|---|---|---|
| Side-effecting tool with `approval: never` | rejected | `PRG-SAFETY-0001` | existing safety tests |
| `autonomy.approval_policy: read_only` with side-effecting tool | rejected | `PRG-SAFETY-0001` | recovery safety test |
| `autonomy.max_tool_calls` | retained as provenance; no live execution exists in v0.1 | no execution is permitted | offline boundary tests |
| Tool approval / declared capability consistency | tool section and `tools.function_calling@1` must agree | `PRG-VALIDATION-0002` | recovery capability test |
| Security rules | frozen IR supplies free text, not machine-readable policy semantics | populated section fails closed with `PRG-SAFETY-0001` | recovery semantic test |
| Privacy rules / sensitive-data policy | frozen IR supplies free text, not machine-readable policy semantics | populated section fails closed with `PRG-SAFETY-0001` | recovery semantic test |

This matrix deliberately does not interpret policy prose. Doing so would invent a policy language absent from the frozen schema. MISSION-006 therefore rejects policy-bearing compilation rather than representing it as safe or deployable.
