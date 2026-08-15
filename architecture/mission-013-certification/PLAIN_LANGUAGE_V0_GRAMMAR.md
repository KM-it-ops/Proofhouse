# plain_language_v0 Constrained Prose Grammar

**Profile:** `plain_language_v0` (intake only)  
**Mission:** MISSION-013 M1  
**Output:** `structured_minimal_v0` records for existing MISSION-008 validation and MISSION-012 closed loop

## Scope and non-claims

- This is **constrained prose**, not freeform NLP. Lines outside the grammar fail closed with a `PL-PARSE-*` diagnostic; the parser never guesses requirements.
- **No model calls.** Parsing is deterministic and offline (`network_allowed=false` on emitted records).
- This grammar is **not** the MISSION-008 full requirements compiler and **not** M2 model-assisted suggestion (MISSION-014, future).
- Canonical evaluation still does not interpret ordinary language (RC-005). The parser is a producer; structured validation remains the semantic owner.

## Document format

UTF-8 text. Line endings: `\n` or `\r\n`. Blank lines are ignored. **`#` comments are forbidden** (a line starting with `#` is a parse error).

Labels are **case-sensitive**.

```
Project: <name>          # optional, at most one line
Goal: <nonempty goal>    # required, exactly one
Requirements:            # required header
1. <statement>           # required, consecutive integers starting at 1
2. <statement>
Constraints:             # optional header
- <constraint>           # zero or more; only if Constraints: present
```

### Field rules

| Label | Cardinality | Notes |
|---|---|---|
| `Project:` | 0–1 | If omitted, default project name is assigned at parse time (`plain-language-m1`). |
| `Goal:` | exactly 1 | Non-empty goal text after the label. |
| `Requirements:` | exactly 1 header | Must be followed by at least one numbered requirement. |
| Numbered items | ≥1 | IDs `1.`, `2.`, … consecutive with no gaps. |
| `Constraints:` | 0–1 header | If present, followed by zero or more `- <constraint>` lines. |

Any other non-blank line → **parse error** (`PL-PARSE-0001`).

Missing `Goal:` or empty requirements list → `PL-PARSE-0002`.  
Numbering gaps (e.g. `1.` then `3.`) → `PL-PARSE-0003`.

## Requirement ID assignment

Requirements receive stable IDs in listed order:

- First item → `REQ-PL-001`
- Second → `REQ-PL-002`
- …

Identical source text yields identical IDs (deterministic).

## Mapping to structured_minimal_v0

The parser emits a `structured_minimal_v0` document with:

- `intake_profile`: `plain_language_v0`
- `profile`: `structured_minimal_v0`
- `contract_version`: `0.1.0`
- `network_allowed`: `false`
- `objective.goal` from `Goal:`
- `requirements[].id` / `requirements[].statement` from numbered lines
- `behavior.constraints` from `-` lines under `Constraints:` (if any)
- Default `behavior.instructions`: `["Follow requirements exactly."]`

Downstream: `validate_structured_requirements` → `requirements_to_ir` → `run_closed_loop` (unchanged from MISSION-012).

## Diagnostic prefix

All parse failures use diagnostic prefix **`PL-PARSE-`**.
