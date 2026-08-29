# MISSION-032 credential redaction rules

These rules apply to `execute_openai`, CLI `execute-openai`, result envelopes, audit events, diagnostics, fixtures, and IR.

## Never persist or emit

- Credential **values** (API keys, bearer tokens, env var contents).
- `Authorization` header values.
- Fields named `api_key`, `credential`, `credential_value`, `secret`.

## Allowed to emit

- Credential **env var name** supplied by the caller (not the value).
- Caller-supplied **model id** (Q1 unpicked; the id is not a secret).
- Host name `api.openai.com`, allowlisted URL, token/cost ceilings as declared.
- Idempotency key, compile artifact digest, IR digest.

## Placement bans

| Surface | Secret values |
|---|---|
| IR v0.1 | Forbidden. Do not add credential or continuation fields. |
| Frozen compile fixtures / goldens | Forbidden. |
| Result envelope / audit event | Forbidden. Replace with `[REDACTED]` if a value is seen. |
| Diagnostics / CLI text | Forbidden. |
| Logs | Do not log headers or credential values. |

## Credential store (Q1 unpicked)

Caller-supplied env var name and/or value at invoke time. Not a vault product. Empty env var is missing credentials (`EXE-CRED-0001`). CLI accepts `--credential-env` only (no `--credential-value`) to avoid argv leakage.
