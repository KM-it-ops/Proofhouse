"""Fail-closed opt-in live OpenAI execution (MISSION-032).

Adapters remain offline lowerers. This module is the only live path and is
not a flag on closed_loop.py. Default compile/validate/closed-loop stay
offline. Live is DEFERRED-to-opt-in, not CERTIFIED.

Q1 remains an owner gate before real-network tests: model id, token/cost
ceilings, and credential material are required at call time (function args
and/or env var name). There is no ratified first live model. The credential
store is caller-supplied env var name / value at invoke time, not a vault
product.

Continuation is evidence-only and omitted for this campaign's single-request
live path. IR v0.1 is not extended.
"""

from __future__ import annotations

import base64
import json
import os
import uuid
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol
from urllib.parse import urlparse

from . import api

CONTRACT_VERSION = "0.1.0-live-openai-opt-in"
DEFAULT_TARGET_URL = "https://api.openai.com/v1/chat/completions"
ALLOWED_OPENAI_HOSTS = frozenset({"api.openai.com"})
ALLOWED_OPENAI_PATH_PREFIX = "/v1/"

EXE_OPT_0001 = "EXE-OPT-0001"
EXE_CRED_0001 = "EXE-CRED-0001"
EXE_MODEL_0001 = "EXE-MODEL-0001"
EXE_CEIL_0001 = "EXE-CEIL-0001"
EXE_DEP_0001 = "EXE-DEP-0001"
EXE_EGRESS_0001 = "EXE-EGRESS-0001"
EXE_COMPILE_0001 = "EXE-COMPILE-0001"

_REDACTED = "[REDACTED]"


@dataclass(frozen=True, slots=True)
class PreparedLiveRequest:
    url: str
    method: str
    headers: dict[str, str]
    body: dict[str, Any]
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class LiveTransportResponse:
    status_code: int
    payload: dict[str, Any]


class LiveTransport(Protocol):
    def send(self, prepared: PreparedLiveRequest) -> Any:
        """Send one live request. Must not be retried by the caller on success."""


@dataclass(frozen=True, slots=True)
class LiveOpenAIRequest:
    """Call-time live request. Missing model, ceilings, or credentials fail closed.

    Model, token/cost ceilings, and credential material have no defaults and
    are not read from a vault. Pass them here. Q1 is unpicked: this struct is
    not a ratified production model or credential-store decision.
    """

    opt_in: bool = False
    model: str | None = None
    credential_env_name: str | None = None
    credential_value: str | None = None
    max_output_tokens: int | None = None
    max_cost_usd: str | None = None
    target_url: str | None = None
    transport: LiveTransport | None = None
    idempotency_key: str | None = None
    cancelled: bool = False


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    status: str
    diagnostics: tuple[str, ...]
    envelope: dict[str, Any] = field(default_factory=dict)
    audit_event: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "command": "execute-openai",
            "status": self.status,
            "diagnostics": list(self.diagnostics),
            "envelope": self.envelope,
        }
        if self.audit_event is not None:
            payload["audit_event"] = self.audit_event
        return payload


def _error(code: str, envelope: dict[str, Any] | None = None) -> ExecutionResult:
    return ExecutionResult(
        status="error",
        diagnostics=(code,),
        envelope=_redact_tree(envelope or {"single_request": True, "q1_unpicked": True}),
    )


def _secrets_from(request: LiveOpenAIRequest, resolved: str | None) -> tuple[str, ...]:
    secrets = []
    if request.credential_value:
        secrets.append(request.credential_value)
    if resolved:
        secrets.append(resolved)
    return tuple(s for s in secrets if s)


def _redact_tree(value: Any, secrets: tuple[str, ...] = ()) -> Any:
    if isinstance(value, str):
        out = value
        for secret in secrets:
            if secret:
                out = out.replace(secret, _REDACTED)
        lowered = out.lower()
        if lowered.startswith("bearer ") or "api-key" in lowered:
            return _REDACTED
        return out
    if isinstance(value, dict):
        redacted = {}
        for key, nested in value.items():
            key_l = str(key).lower()
            if key_l in {"authorization", "api_key", "credential", "credential_value", "secret"}:
                redacted[key] = _REDACTED
            else:
                redacted[key] = _redact_tree(nested, secrets)
        return redacted
    if isinstance(value, list):
        return [_redact_tree(item, secrets) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_tree(item, secrets) for item in value)
    return value


def _resolve_credential(request: LiveOpenAIRequest) -> str | None:
    if request.credential_env_name:
        value = os.environ.get(request.credential_env_name, "")
        if value:
            return value
        return None
    if request.credential_value:
        return request.credential_value
    return None


def _ceilings_ok(request: LiveOpenAIRequest) -> bool:
    if request.max_output_tokens is None or int(request.max_output_tokens) <= 0:
        return False
    if request.max_cost_usd is None or not str(request.max_cost_usd).strip():
        return False
    try:
        amount = Decimal(str(request.max_cost_usd))
    except (InvalidOperation, ValueError):
        return False
    return amount > 0


def _allowlisted_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    if parsed.username or parsed.password:
        return False
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_OPENAI_HOSTS:
        return False
    if parsed.port not in (None, 443):
        return False
    path = parsed.path or ""
    if not path.startswith(ALLOWED_OPENAI_PATH_PREFIX):
        return False
    if parsed.query or parsed.fragment:
        return False
    return True


def _provider_body(model: str, lowered: dict[str, Any], max_output_tokens: int) -> dict[str, Any]:
    messages = [{"role": "system", "content": lowered.get("instructions") or ""}]
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_output_tokens,
    }
    tools = lowered.get("tools") or []
    if tools:
        body["tools"] = tools
    response_format = lowered.get("response_format")
    if response_format:
        body["response_format"] = response_format
    return body


def _httpx_send(prepared: PreparedLiveRequest) -> LiveTransportResponse:
    # Optional extra: default install must not import httpx at module load.
    try:
        import httpx
    except ImportError:
        raise ModuleNotFoundError("httpx") from None
    with httpx.Client(timeout=30.0) as client:
        response = client.post(prepared.url, headers=prepared.headers, json=prepared.body)
        try:
            payload = response.json()
        except ValueError:
            payload = {"text": response.text}
        if not isinstance(payload, dict):
            payload = {"value": payload}
        return LiveTransportResponse(status_code=response.status_code, payload=payload)


def execute_openai(
    ir_raw: bytes | str,
    request: LiveOpenAIRequest | None = None,
) -> ExecutionResult:
    """Opt-in single-request live OpenAI execution. Fail closed when gates fail."""
    request = request or LiveOpenAIRequest()
    resolved = _resolve_credential(request)
    secrets = _secrets_from(request, resolved)

    def finish(result: ExecutionResult) -> ExecutionResult:
        envelope = _redact_tree(result.envelope, secrets)
        audit = _redact_tree(result.audit_event, secrets) if result.audit_event is not None else None
        return ExecutionResult(
            status=result.status,
            diagnostics=result.diagnostics,
            envelope=envelope,
            audit_event=audit,
        )

    if not request.opt_in:
        return finish(_error(EXE_OPT_0001))
    if not resolved:
        return finish(_error(EXE_CRED_0001))
    model = (request.model or "").strip()
    if not model:
        return finish(_error(EXE_MODEL_0001))
    if not _ceilings_ok(request):
        return finish(_error(EXE_CEIL_0001))

    target_url = request.target_url or DEFAULT_TARGET_URL
    if not _allowlisted_url(target_url):
        return finish(_error(EXE_EGRESS_0001, {"target_url_rejected": True, "single_request": True}))

    compile_env = api.compile(ir_raw, adapter_id="openai", adapter_version="0.1.0")
    if compile_env.status == "error":
        return finish(_error(EXE_COMPILE_0001, {"compile_status": compile_env.status}))

    artifact = compile_env.data["artifacts"][0]
    if artifact.get("data_base64"):
        lowered = json.loads(base64.b64decode(artifact["data_base64"]))
    else:
        lowered = json.loads(artifact.get("data") or "{}")

    idempotency_key = request.idempotency_key or str(uuid.uuid4())
    host = urlparse(target_url).hostname or ""
    evidence = {
        "single_request": True,
        "q1_unpicked": True,
        "host": host,
        "idempotency_key": idempotency_key,
        "ir_sha256": compile_env.data.get("ir_sha256"),
        "compile_artifact_sha256": artifact.get("sha256"),
        "credential_env_name": request.credential_env_name,
        "max_output_tokens": request.max_output_tokens,
        "max_cost_usd": request.max_cost_usd,
    }

    if request.cancelled:
        return finish(
            ExecutionResult(
                status="cancelled",
                diagnostics=(),
                envelope={"single_request": True, "evidence": {**evidence, "cancelled_before_send": True}},
            )
        )

    prepared = PreparedLiveRequest(
        url=target_url,
        method="POST",
        headers={
            "Authorization": f"Bearer {resolved}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        },
        body=_provider_body(model, lowered, int(request.max_output_tokens or 0)),
        idempotency_key=idempotency_key,
    )

    if request.transport is None:
        try:
            response = _httpx_send(prepared)
        except ModuleNotFoundError:
            return finish(_error(EXE_DEP_0001, {"missing_optional_dependency": "httpx"}))
        except Exception as exc:  # noqa: BLE001 -- live boundary must not leak secrets
            return finish(
                _error(
                    EXE_DEP_0001,
                    {"transport_error": type(exc).__name__, "single_request": True},
                )
            )
    else:
        response = request.transport.send(prepared)

    status_code = getattr(response, "status_code", None)
    payload = getattr(response, "payload", None)
    if payload is None and isinstance(response, dict):
        payload = response
        status_code = response.get("status_code", 200)
    if not isinstance(payload, dict):
        payload = {"value": payload}

    envelope = {
        "contract_version": CONTRACT_VERSION,
        "command": "execute-openai",
        "single_request": True,
        "q1_unpicked": True,
        "model": model,
        "host": host,
        "target_url": target_url,
        "max_output_tokens": request.max_output_tokens,
        "max_cost_usd": request.max_cost_usd,
        "credential_env_name": request.credential_env_name,
        "idempotency_key": idempotency_key,
        "http_status": status_code,
        "provider_response": payload,
        "ir_sha256": compile_env.data.get("ir_sha256"),
        "compile_artifact_sha256": artifact.get("sha256"),
    }
    audit = {
        "event": "live_openai_execute",
        "opt_in": True,
        "single_request": True,
        "host": host,
        "model_supplied": True,
        "credential_env_name": request.credential_env_name,
        "idempotency_key": idempotency_key,
        "status": "success",
        "http_status": status_code,
    }
    return finish(
        ExecutionResult(
            status="success",
            diagnostics=(),
            envelope=envelope,
            audit_event=audit,
        )
    )
