# MISSION-032 live OpenAI threat model

Scope: opt-in `execute_openai` / `promptrig-compiler execute-openai` only. Default compile, validate, inspect, doctor, adapters, and `closed-loop` remain offline.

## Assets

- Caller-supplied credential value or env var contents at invoke time.
- Lowered OpenAI request payload (already produced offline by the openai adapter).
- Execution result envelope, audit event, CLI stdout/stderr, diagnostics.
- IR v0.1 documents and compile artifacts (must stay uncontaminated).

## Trust boundary

Execution is a **new module**, not a flag on `closed_loop.py`. Adapters do not grow HTTP clients. Opt-in is explicit (`opt_in=True` / `--opt-in`). Missing opt-in, model, ceilings, or credentials fail-closed without sockets.

## Egress allowlist

Live HTTP may target only:

| Host | Scheme | Path prefix | Port |
|---|---|---|---|
| `api.openai.com` | `https` | `/v1/` | 443 or omitted |

Default URL: `https://api.openai.com/v1/chat/completions`. Any other host, scheme, userinfo, query, fragment, or path fail-closes `EXE-EGRESS-0001`. No proxy-to-arbitrary-URL.

## Threats and controls

| ID | Threat | Control |
|---|---|---|
| TM-LIVE-001 | Offline compile grows a network client | Separate module; openai `lower()` unchanged; `forbid_network` tests on compile/validate |
| TM-LIVE-002 | closed-loop used as live switch | `network_allowed` still `EVR-NET-0001`; no live flags on `closed-loop` |
| TM-LIVE-003 | Missing credentials still send | AE4: `EXE-CRED-0001` before send |
| TM-LIVE-004 | Hardcoded production model | Q1 unpicked; model required at call time; no default model id |
| TM-LIVE-005 | Secret leakage in IR/envelope/logs | Redaction rules; credentials never stored in IR or fixtures |
| TM-LIVE-006 | Retry duplicates a billed call | Single send; idempotency key; no retry on success |
| TM-LIVE-007 | Cancel drops evidence | Cancel-before-send returns `cancelled` with evidence, no send |
| TM-LIVE-008 | Optional HTTP extra pulled into default install | `[project.optional-dependencies] live = ["httpx"]`; `EXE-DEP-0001` if missing |
| TM-LIVE-009 | Real-network tests in ordinary CI | pytest marker `live` plus `addopts = -m "not live"` |
| TM-LIVE-010 | Continuation contaminates IR v0.1 | Single-request; no continuation field; evidence-only |

## Q1 owner gate

Model choice, numeric ceiling policy, and credential-store product are **unpicked**. This mission requires those values at invoke time so the code cannot invent them. Do not run real-network tests until the owner picks Q1.
