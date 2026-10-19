"""Fail-closed opt-in live OpenAI execution (MISSION-032).

Adapters remain offline lowerers. This module is the only live path and is
not a flag on closed_loop.py. Default compile/validate/closed-loop stay
offline. Live is DEFERRED-to-opt-in, not CERTIFIED.

Q1 is gpt-5.6-luna (OAR-032). Model id, token/cost ceilings, and credential
material are still required at call time (function args and/or env var name);
Q1 is not a request default. The credential store is caller-supplied env var
name / value at invoke time, not a vault product.

Continuation is evidence-only and omitted for this campaign's single-request
live path. IR v0.1 is not extended.

Nothing is sent except through the spend gate (``proofhouse.spend``): the one
send step below is handed to ``send_within_ceiling``, which works out the worst
case from the exact bytes and refuses, sending nothing, when that is over
``max_cost_usd``, when the model has no price, or when no worst case can be made.
"""

from __future__ import annotations

import base64
import json
import math
import os
import uuid
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol
from urllib.parse import urlparse

from .. import providers, spend
from . import api
from .adapters.openai import FUNCTION_CALLING_CAPABILITY, STRUCTURED_JSON_CAPABILITY, SUPPORTED_CAPABILITIES
from .ir import IRParseError, parse_ir
from .runtime_context import render_runtime_context

CONTRACT_VERSION = "0.1.0-live-openai-opt-in"
DEFAULT_TARGET_URL = "https://api.openai.com/v1/chat/completions"
# The chat-body field that carries each capability the request builder supports.
_CAPABILITY_FIELDS = {STRUCTURED_JSON_CAPABILITY: "response_format", FUNCTION_CALLING_CAPABILITY: "tools"}
# OAR-032 Q1. Not a LiveOpenAIRequest default; --model is still required.
Q1_MODEL_ID = "gpt-5.6-luna"
ALLOWED_OPENAI_HOSTS = frozenset({"api.openai.com"})
ALLOWED_OPENAI_PATH_PREFIX = "/v1/"

EXE_OPT_0001 = "EXE-OPT-0001"
EXE_CRED_0001 = "EXE-CRED-0001"
EXE_MODEL_0001 = "EXE-MODEL-0001"
EXE_CEIL_0001 = "EXE-CEIL-0001"
EXE_DEP_0001 = "EXE-DEP-0001"
EXE_EGRESS_0001 = "EXE-EGRESS-0001"
EXE_COMPILE_0001 = "EXE-COMPILE-0001"
EXE_HTTP_0001 = "EXE-HTTP-0001"
# A mandatory IR field cannot be honored by this single-request path.
EXE_SEM_0001 = "EXE-SEM-0001"
EXE_CAP_0001 = "EXE-CAP-0001"
EXE_PROV_0001 = "EXE-PROV-0001"

_REDACTED = "[REDACTED]"


@dataclass(frozen=True, slots=True)
class PreparedLiveRequest:
    url: str
    method: str
    headers: dict[str, str]
    body: dict[str, Any]
    idempotency_key: str
    # The exact bytes the spend gate counted; the only bytes that are sent.
    body_bytes: bytes


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
    are not read from a vault. Pass them here. Q1 is gpt-5.6-luna (OAR-032);
    this struct still has no default model.
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
class LiveRunRequest:
    opt_in: bool = False
    provider: str | None = None
    model: str | None = None
    credential_env_name: str | None = None
    credential_value: str | None = None
    max_output_tokens: int | None = None
    max_cost_usd: str | None = None
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


@dataclass(frozen=True, slots=True)
class _SendFailed:
    """The send step raised; nothing usable came back. Normalized so no secret leaks."""

    envelope: dict[str, Any]


def _error(code: str, envelope: dict[str, Any] | None = None) -> ExecutionResult:
    return ExecutionResult(
        status="error",
        diagnostics=(code,),
        envelope=_redact_tree(
            envelope or {"single_request": True, "q1_unpicked": False, "q1_model": Q1_MODEL_ID}
        ),
    )


def _secrets_from(request: LiveOpenAIRequest | LiveRunRequest, resolved: str | None) -> tuple[str, ...]:
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


def _ceilings_ok(request: LiveOpenAIRequest | LiveRunRequest) -> bool:
    """Positive integer token ceiling and a positive, finite decimal cost ceiling.

    ``bool`` is rejected even though it is an ``int`` subclass; ``NaN``,
    ``Infinity`` and exponent overflow are rejected rather than raised.
    """
    tokens = request.max_output_tokens
    if type(tokens) is not int or tokens <= 0:
        return False
    if not isinstance(request.max_cost_usd, str) or not request.max_cost_usd.strip():
        return False
    try:
        amount = Decimal(request.max_cost_usd.strip())
    except (InvalidOperation, ValueError):
        return False
    if not amount.is_finite():
        return False
    try:
        return amount > 0 and math.isfinite(float(amount))
    except (InvalidOperation, OverflowError, ValueError):
        return False


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


def _provider_body(
    model: str, lowered: dict[str, Any], system_text: str, max_output_tokens: int, shape: str = "openai"
) -> dict[str, Any]:
    messages = [{"role": "system", "content": system_text}]
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_completion_tokens" if shape == "openai" else "max_tokens": max_output_tokens,
    }
    tools = lowered.get("tools") or []
    if tools:
        body["tools"] = tools
    response_format = lowered.get("response_format")
    if response_format:
        body["response_format"] = response_format
    return body


def _admission(
    request: LiveOpenAIRequest | LiveRunRequest, admission: spend.Admission, shape: str = "openai"
) -> dict[str, Any]:
    """What the spend gate decided before sending, and how the output-token ceiling was applied."""
    return {
        "cost_ceiling": {"declared_usd": request.max_cost_usd, **admission.to_dict()},
        "output_token_ceiling": {
            "value": request.max_output_tokens,
            "enforcement": "sent_as_max_completion_tokens" if shape == "openai" else "sent_as_max_tokens",
        },
    }


def _httpx_send(prepared: PreparedLiveRequest) -> LiveTransportResponse:
    # Optional extra: default install must not import httpx at module load.
    try:
        import httpx
    except ImportError:
        raise ModuleNotFoundError("httpx") from None
    with httpx.Client(timeout=30.0) as client:
        response = client.post(prepared.url, headers=prepared.headers, content=prepared.body_bytes)
        try:
            payload = response.json()
        except ValueError:
            payload = {"text": response.text}
        if not isinstance(payload, dict):
            payload = {"value": payload}
        return LiveTransportResponse(status_code=response.status_code, payload=payload)


def _execute_live(
    ir_raw: bytes | str,
    request: LiveOpenAIRequest | LiveRunRequest,
    *,
    provider_id: str = "openai",
    target_url: str | None = None,
    resolved_credential: str | None = None,
    shape: str = "openai",
    credential_env_name: str | None = None,
    allow_keyless: bool = False,
    ignores: tuple[str, ...] = (),
    expected_host: str | None = None,
    snapshot: providers.Snapshot | None = None,
) -> ExecutionResult:
    """Shared single-request send path after provider-specific selection."""
    resolved = _resolve_credential(request) if isinstance(request, LiveOpenAIRequest) else resolved_credential
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
    if not resolved and not allow_keyless:
        return finish(_error(EXE_CRED_0001))
    model = (request.model or "").strip()
    if not model:
        return finish(_error(EXE_MODEL_0001))
    if not _ceilings_ok(request):
        return finish(_error(EXE_CEIL_0001))

    if target_url is None:
        target_url = (request.target_url or DEFAULT_TARGET_URL) if isinstance(request, LiveOpenAIRequest) else ""
    if isinstance(request, LiveOpenAIRequest) and not _allowlisted_url(target_url):
        return finish(_error(EXE_EGRESS_0001, {"target_url_rejected": True, "single_request": True}))
    # The last check before the key is attached: the address the request goes to is the provider's own host.
    final = urlparse(target_url)
    if expected_host is not None and ((final.hostname or "").lower() != expected_host or final.username or final.password):
        return finish(_error(EXE_EGRESS_0001, {"provider": provider_id, "target_url_rejected": True, "single_request": True}))

    compile_env = api.compile(ir_raw, adapter_id="openai", adapter_version="0.1.0")
    if compile_env.status == "error":
        return finish(_error(EXE_COMPILE_0001, {"compile_status": compile_env.status}))

    artifacts = list(compile_env.data.get("artifacts") or [])
    if not artifacts:
        return finish(_error(EXE_COMPILE_0001, {"compile_status": compile_env.status, "artifacts": 0}))
    artifact = artifacts[0]
    if artifact.get("data_base64"):
        lowered = json.loads(base64.b64decode(artifact["data_base64"]))
    else:
        lowered = json.loads(artifact.get("data") or "{}")
    # A field the provider's address drops is not sent; the runtime context renders it into the prompt instead.
    for capability in ignores:
        lowered.pop(_CAPABILITY_FIELDS.get(capability, ""), None)

    semantic = lowered.get("proofhouse_semantic_context")
    ir_document = semantic.get("ir") if isinstance(semantic, dict) else None
    if not isinstance(ir_document, dict):
        return finish(
            _error(
                EXE_SEM_0001,
                {"single_request": True, "unsupported_semantics": [{"source_path": "", "reason": "artifact has no semantic context"}]},
            )
        )
    runtime = render_runtime_context(
        ir_document,
        response_format_sent=bool(lowered.get("response_format")),
        tools_sent=bool(lowered.get("tools")),
    )
    if runtime.unsupported:
        return finish(
            _error(
                EXE_SEM_0001,
                {
                    "single_request": True,
                    "unsupported_semantics": [dict(row) for row in runtime.unsupported],
                    "runtime_context": runtime.evidence(),
                },
            )
        )

    idempotency_key = request.idempotency_key or str(uuid.uuid4())
    host = urlparse(target_url).hostname or ""
    evidence = {
        "single_request": True,
        "q1_unpicked": False,
        "q1_model": Q1_MODEL_ID,
        "host": host,
        "idempotency_key": idempotency_key,
        "ir_sha256": compile_env.data.get("ir_sha256"),
        "compile_artifact_sha256": artifact.get("sha256"),
        "credential_env_name": credential_env_name if isinstance(request, LiveRunRequest) else request.credential_env_name,
        "max_output_tokens": request.max_output_tokens,
        "max_cost_usd": request.max_cost_usd,
    }
    if isinstance(request, LiveRunRequest):
        evidence["provider"] = provider_id

    if request.cancelled:
        return finish(
            ExecutionResult(
                status="cancelled",
                diagnostics=(),
                envelope={"single_request": True, "evidence": {**evidence, "cancelled_before_send": True}},
            )
        )

    unsent = PreparedLiveRequest(
        url=target_url,
        method="POST",
        headers={
            **({"Authorization": f"Bearer {resolved}"} if resolved else {}),
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        },
        body=_provider_body(model, lowered, runtime.system_text, int(request.max_output_tokens or 0), shape),
        idempotency_key=idempotency_key,
        body_bytes=b"",
    )

    def _dispatch(body_bytes: bytes) -> Any:
        # The only send step. It runs only when the spend gate calls it, with the bytes the gate counted.
        prepared = replace(unsent, body_bytes=body_bytes)
        if request.transport is None:
            try:
                return _httpx_send(prepared)
            except ModuleNotFoundError:
                return _SendFailed({"missing_optional_dependency": "httpx"})
            except Exception as exc:  # noqa: BLE001 -- live boundary must not leak secrets
                return _SendFailed({"transport_error": type(exc).__name__, "single_request": True})
        try:
            return request.transport.send(prepared)
        except Exception as exc:  # noqa: BLE001 -- injected transports get the same normalized boundary
            return _SendFailed({"transport_error": type(exc).__name__, "single_request": True})

    gated = spend.send_within_ceiling(
        unsent.body,
        provider=provider_id,
        model=model,
        max_output_tokens=request.max_output_tokens,
        ceiling_usd=request.max_cost_usd,
        send=_dispatch,
        snapshot=snapshot,
    )
    if gated.admission.decision != "admitted":
        refusal = {
            "single_request": True,
            "q1_unpicked": False,
            "q1_model": Q1_MODEL_ID,
            "model": model,
            "admission": _admission(request, gated.admission, shape),
        }
        if isinstance(request, LiveRunRequest):
            refusal.update({"provider": provider_id, "host": host})
        return finish(
            _error(
                str(gated.admission.code),
                refusal,
            )
        )
    response = gated.response
    if isinstance(response, _SendFailed):
        return finish(_error(EXE_DEP_0001, response.envelope))

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
        "q1_unpicked": False,
        "q1_model": Q1_MODEL_ID,
        "model": model,
        "host": host,
        "target_url": target_url,
        "max_output_tokens": request.max_output_tokens,
        "max_cost_usd": request.max_cost_usd,
        "credential_env_name": credential_env_name if isinstance(request, LiveRunRequest) else request.credential_env_name,
        "idempotency_key": idempotency_key,
        "http_status": status_code,
        "provider_response": payload,
        "ir_sha256": compile_env.data.get("ir_sha256"),
        "compile_artifact_sha256": artifact.get("sha256"),
        "runtime_context": runtime.evidence(),
        "admission": _admission(request, gated.admission, shape),
    }
    if isinstance(request, LiveRunRequest):
        envelope["provider"] = provider_id
    cost, cost_warning = spend.cost_after(gated, payload)
    envelope["cost"] = cost
    if cost_warning is not None:
        envelope["cost_warning"] = cost_warning
    ok = isinstance(status_code, int) and 200 <= status_code < 300
    result_status = "success" if ok else "error"
    diagnostics = () if ok else (EXE_HTTP_0001,)
    if cost_warning is not None:
        diagnostics = (*diagnostics, "PHC-COST-0004")  # the money is spent; the output is still returned
    audit = {
        "event": "live_openai_execute",
        "opt_in": True,
        "single_request": True,
        "host": host,
        "model_supplied": True,
        "credential_env_name": credential_env_name if isinstance(request, LiveRunRequest) else request.credential_env_name,
        "idempotency_key": idempotency_key,
        "status": result_status,
        "http_status": status_code,
    }
    if isinstance(request, LiveRunRequest):
        audit["provider"] = provider_id
    return finish(
        ExecutionResult(
            status=result_status,
            diagnostics=diagnostics,
            envelope=envelope,
            audit_event=audit,
        )
    )


def execute_openai(
    ir_raw: bytes | str,
    request: LiveOpenAIRequest | None = None,
) -> ExecutionResult:
    """Opt-in single-request live OpenAI execution. Fail closed when gates fail."""
    return _execute_live(ir_raw, request or LiveOpenAIRequest())


def execute_on_provider(ir_raw: bytes | str, request: LiveRunRequest) -> ExecutionResult:
    """Run a compiled artifact through a configured provider and the spend gate."""
    if not request.opt_in:
        return _error(EXE_OPT_0001)
    provider_id = request.provider or ""
    # One read of the providers files for the whole run; the spend gate prices this same entry.
    try:
        known = providers.snapshot()
        profile = known.find(provider_id)
    except providers.ProviderError:
        known, profile = None, None
    if profile is None:
        return _error(
            EXE_PROV_0001, _redact_tree({"provider": provider_id, "single_request": True}, _secrets_from(request, None))
        )

    # The key comes from the provider entry's own variable, so another service's key never goes to this address.
    # To use a different variable, add or override the provider with that key_env.
    if request.credential_env_name and request.credential_env_name != profile.key_env:
        return _error(EXE_CRED_0001, {"provider": provider_id, "credential_env_mismatch": True, "single_request": True})
    if request.credential_value and not request.credential_env_name:
        credential_env_name, resolved = None, request.credential_value
    else:
        credential_env_name = profile.key_env
        resolved = os.environ.get(credential_env_name) if credential_env_name else None
    secrets = _secrets_from(request, resolved)

    def refuse(code: str, envelope: dict[str, Any] | None = None) -> ExecutionResult:
        result = _error(code, envelope)
        return replace(result, envelope=_redact_tree(result.envelope, secrets))

    # A server on this machine may run without its optional key, as `proofhouse run` allows.
    if not resolved and not profile.local:
        return refuse(EXE_CRED_0001)
    if not (request.model or "").strip():
        return refuse(EXE_MODEL_0001)
    if not _ceilings_ok(request):
        return refuse(EXE_CEIL_0001)

    try:
        document = parse_ir(ir_raw).document
    except IRParseError:
        document = {}
    requirements = document.get("provider_requirements") or {}
    required = requirements.get("required_capabilities", []) if isinstance(requirements, dict) else []
    refused = (
        sorted(
            {
                cap
                for cap in required
                if isinstance(cap, str) and (cap not in SUPPORTED_CAPABILITIES or cap in profile.ignores)
            }
        )
        if isinstance(required, list)
        else []
    )
    if refused:
        return refuse(
            EXE_CAP_0001,
            {"provider": provider_id, "refused_requirements": refused, "single_request": True},
        )

    return _execute_live(
        ir_raw,
        request,
        provider_id=profile.id,
        target_url=profile.chat_url,
        resolved_credential=resolved,
        shape=profile.shape,
        credential_env_name=credential_env_name,
        allow_keyless=profile.local,
        ignores=profile.ignores,
        expected_host=profile.host,
        snapshot=known,
    )
