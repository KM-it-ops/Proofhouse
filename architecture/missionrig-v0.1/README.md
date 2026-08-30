# MissionRig v0.1 (one profile)

**Profile:** `structured_minimal_v0`
**Schema version:** `0.1.0-draft`
**Owner:** PromptRig remains semantic owner. MissionRig generates missions. Workspace consumes them read-only.

## Mission object

| Field | Rule |
|---|---|
| `status` | `READY` only when compiler evidence is PASS/SUCCESS and no unresolved defect; otherwise `PARTIAL` |
| `compiler_status` | Copied; never upgraded |
| `stop_conditions` | From intake `stop_conditions` or `objective.failure_conditions` |
| `requirement_ids` | Copied from evidence |
| `ir_sha256` | Copied; not recomputed into a new IR |

Write-back into IR is rejected. See `promptrig.compiler.missionrig`.
