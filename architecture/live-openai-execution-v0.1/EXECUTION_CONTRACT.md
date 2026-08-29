# Live OpenAI execution request/result contract (opt-in v0.1)

**Status:** Draft for MISSION-032. Not a freeze schema. Do not edit `architecture/compiler-contract-freeze-v0.5/`.
**Contract version:** `0.1.0-live-openai-opt-in`
**Live posture:** DEFERRED-to-opt-in, not CERTIFIED. Single-request. Q1 unpicked.

This file is the execution request/result contract. Compiler Core IR, diagnostic registry, and adapter lowering contracts stay frozen.

## Q1 owner gate (required)

The owner has **not** picked Q1. This contract therefore:

- Does **not** name a ratified first live model.
- Requires **model**, **token ceiling**, **cost ceiling**, and **credential material** at call time.
- Treats the credential store as **caller-supplied env var name / value at invoke time**, not a vault product.

Do not run real-network tests until Q1 is picked.

## Request (library)

`execute_openai(ir_raw, LiveOpenAIRequest(...))`

| Field | Required | Notes |
|---|---|---|
| `opt_in` | yes (must be true) | Else `EXE-OPT-0001`, no sockets |
| `model` | yes | Caller-supplied; no default |
| `credential_env_name` and/or `credential_value` | yes | Env name preferred when set; empty env is AE4 |
| `max_output_tokens` | yes | Positive int |
| `max_cost_usd` | yes | Positive decimal string; declared ceiling, not a price table |
| `target_url` | no | Default `https://api.openai.com/v1/chat/completions`; must be allowlisted |
| `transport` | no | Test double; default suite must use this, not HTTP |
| `idempotency_key` | no | Generated if omitted; one send; no retry on success |
| `cancelled` | no | If true after gates pass, return `cancelled` with evidence, no send |

CLI: `promptrig-compiler execute-openai INPUT --opt-in --model MODEL --credential-env NAME --max-output-tokens N --max-cost-usd X [--target-url URL] [--json]`

CLI never accepts a credential value flag.

## Egress allowlist

Only `https://api.openai.com` host, path prefix `/v1/`, port 443 or omitted. Deny everything else (`EXE-EGRESS-0001`).

## Result envelope

```json
{
  "command": "execute-openai",
  "status": "success | error | cancelled",
  "diagnostics": ["EXE-…"],
  "envelope": {
    "contract_version": "0.1.0-live-openai-opt-in",
    "single_request": true,
    "q1_unpicked": true,
    "model": "<caller-supplied>",
    "host": "api.openai.com",
    "provider_response": {},
    "idempotency_key": "<key>"
  },
  "audit_event": {
    "event": "live_openai_execute",
    "opt_in": true,
    "single_request": true
  }
}
```

No `continuation` field. Evidence-only continuation is omitted for this single-request campaign path.

## Diagnostics (execution contract, not frozen PRG registry)

| Code | When |
|---|---|
| `EXE-OPT-0001` | Opt-in not granted |
| `EXE-CRED-0001` | AE4: no credentials |
| `EXE-MODEL-0001` | Missing model |
| `EXE-CEIL-0001` | Missing or invalid token/cost ceilings |
| `EXE-EGRESS-0001` | Host/URL not allowlisted |
| `EXE-DEP-0001` | Optional `httpx` extra missing when a real send is requested |
| `EXE-COMPILE-0001` | Offline openai compile of the IR failed |

## Offline isolation

- `compile --adapter openai` lowers only.
- `closed-loop` remains fake-only; `network_allowed` → `EVR-NET-0001`.
- Default extra-less install does not require `httpx`.
- Ordinary pytest: `-m "not live"`.
