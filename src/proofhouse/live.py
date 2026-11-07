"""Run a prompt on any provider and any model.

``run_prompt`` looks the provider up (shipped or yours), builds one chat request,
and hands its one send step to the spend gate, which works out the worst case
and refuses before sending if it is over your limit or has no price. A provider
on this machine costs nothing. The key is read from the provider's environment
variable at call time, never stored, and never shown in any result.

Every provider here speaks the OpenAI chat format (``/chat/completions``), which
covers nearly every service and local server. One request is sent per call;
nothing is retried.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from typing import Any, Callable
from urllib.parse import urlparse

from . import providers, spend

# A call that names no limit for a provider on this machine gets this one: the smallest the gate takes.
LOCAL_DEFAULT_LIMIT_USD = "0.000000000001"
_REDACTED = "[REDACTED]"


@dataclass(frozen=True, slots=True)
class Request:
    url: str
    headers: dict[str, str]
    body: dict[str, Any]
    body_bytes: bytes


@dataclass(frozen=True, slots=True)
class Response:
    status_code: int
    payload: dict[str, Any]


Transport = Callable[[Request], Any]


@dataclass(frozen=True, slots=True)
class RunResult:
    status: str  # "success", "refused" or "error"
    code: str | None
    message: str | None
    provider: str
    model: str
    output_text: str | None = None
    http_status: int | None = None
    admission: dict[str, Any] = field(default_factory=dict)
    cost: dict[str, Any] | None = None
    cost_warning: str | None = None
    cut_off: bool = False  # the reply stopped at the output cap or the model's window, so it may be unfinished

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "code": self.code,
            "message": self.message,
            "provider": self.provider,
            "model": self.model,
            "output_text": self.output_text,
            "http_status": self.http_status,
            "admission": self.admission,
            "cost": self.cost,
            "cost_warning": self.cost_warning,
            "cut_off": self.cut_off,
        }


@dataclass(frozen=True, slots=True)
class _SendFailed:
    reason: str
    timed_out: bool = False


def _refused(code: str, detail: str, provider: str, model: str) -> RunResult:
    from .optimize.case_codes import CODES

    if code not in CODES:
        raise ValueError(f"unregistered diagnostic code: {code}")
    return RunResult("refused", code, f"{code}: {detail}", provider, model)


def _scrub(value: Any, secret: str | None) -> Any:
    if not secret:
        return value
    if isinstance(value, str):
        return value.replace(secret, _REDACTED)
    if isinstance(value, dict):
        return {k: _scrub(v, secret) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v, secret) for v in value]
    return value


DEFAULT_TIMEOUT_SECONDS = 120.0
LOCAL_TIMEOUT_SECONDS = 600.0  # a model on this machine is slow on a CPU, and waiting for it costs nothing


def _timeout_seconds(url: str = "") -> float:
    """How long to wait for a model: PROOFHOUSE_TIMEOUT_SECONDS if it is a positive number, else 600 for a model on
    this machine and 120 for one elsewhere."""
    here = (urlparse(url).hostname or "").lower() in providers.LOCAL_HOSTS
    fallback = LOCAL_TIMEOUT_SECONDS if here else DEFAULT_TIMEOUT_SECONDS
    try:
        seconds = float(os.environ.get("PROOFHOUSE_TIMEOUT_SECONDS", ""))
    except ValueError:
        return fallback
    return seconds if 0 < seconds < float("inf") else fallback


def _client_headers(headers: dict[str, str]) -> dict[str, str]:
    """The request's headers, naming Proofhouse as the client unless the provider set its own name: some providers'
    front doors (Groq's Cloudflare, error 1010) refuse Python's default client name with a 403."""
    if any(name.lower() == "user-agent" for name in headers):
        return headers
    from . import __version__

    return {**headers, "User-Agent": f"proofhouse/{__version__}"}


def _httpx_post(request: Request) -> Response:
    timeout = _timeout_seconds(request.url)
    headers = _client_headers(request.headers)
    # Optional extra: a default install must not import httpx at module load. Without it, the standard library sends.
    try:
        import httpx
    except ImportError:
        import json
        import urllib.error
        import urllib.request

        sent = urllib.request.Request(request.url, data=request.body_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(sent, timeout=timeout) as answer:
                status, raw = answer.status, answer.read()
        except urllib.error.HTTPError as exc:  # a 4xx or 5xx is still an answer to read
            status, raw = exc.code, exc.read()
        try:
            decoded = json.loads(raw)
        except ValueError:
            decoded = {"text": raw.decode("utf-8", "replace")}
        return Response(status, decoded if isinstance(decoded, dict) else {"value": decoded})
    with httpx.Client(timeout=timeout) as client:
        reply = client.post(request.url, headers=headers, content=request.body_bytes)
        try:
            payload = reply.json()
        except ValueError:
            payload = {"text": reply.text}
        return Response(reply.status_code, payload if isinstance(payload, dict) else {"value": payload})


def _output_text(payload: dict[str, Any]) -> str | None:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"]
    return None


LOCAL_THINKING_ROOM = 16384  # the cap for the one retry when a model on this machine thought through its whole cap


def _cut_off(payload: dict[str, Any]) -> bool:
    """True when the reply stopped because it reached the output cap."""
    choices = payload.get("choices")
    return isinstance(choices, list) and bool(choices) and isinstance(choices[0], dict) and \
        choices[0].get("finish_reason") == "length"


STRUCTURED_JSON = "output.structured_json@1"  # the capability a provider entry lists under ignores to opt out


def run_prompt(
    provider_id: str,
    model: str,
    *,
    prompt: str,
    input_text: str | None = None,
    images: list[str] | None = None,
    max_output_tokens: int = 1024,
    max_cost_usd: str | None = None,
    transport: Transport | None = None,
    json_reply: bool = False,
) -> RunResult:
    """Send one prompt (and optional input) to any provider through the spend gate.

    ``json_reply`` asks for JSON mode, so the reply comes back as one whole JSON object, unless the provider's entry
    says it ignores structured JSON (then nothing extra is sent and the prompt's own words must do it).

    ``images`` are inline pictures (``data:image/png;base64,...`` or JPEG) sent beside the owner's words; the spend
    gate refuses any it cannot count."""
    model = (model or "").strip()
    # One read of the providers files for the whole run; the spend gate prices this same entry.
    try:
        known = providers.snapshot()
    except providers.ProviderError as exc:
        return _refused("PHC-RUN-0001", f"providers file: {exc}", provider_id, model)
    profile = known.find(provider_id)
    if profile is None:
        return _refused(
            "PHC-RUN-0001", f"no provider named {provider_id!r}; see `proofhouse providers list` or add one", provider_id, model
        )
    if not model:
        return _refused("PHC-RUN-0002", "name the model to run (--model)", profile.id, model)
    if not isinstance(prompt, str) or not prompt.strip():
        return _refused("PHC-RUN-0002", "the prompt is empty", profile.id, model)
    secret = None
    if profile.key_env:
        secret = os.environ.get(profile.key_env) or None
        if secret is None and not profile.local:
            return _refused("PHC-RUN-0003", f"set {profile.key_env} to your {profile.name} key", profile.id, model)
    if max_cost_usd is None:
        if not profile.local:
            return _refused("PHC-RUN-0002", "name a spending limit for a paid provider (--max-cost-usd)", profile.id, model)
        max_cost_usd = LOCAL_DEFAULT_LIMIT_USD
    url = profile.chat_url
    if (urlparse(url).hostname or "").lower() != profile.host:
        return _refused("PHC-RUN-0004", f"the address {url!r} does not match provider {profile.id}", profile.id, model)

    words = prompt if input_text is None else input_text
    user: Any = words
    if images:
        user = [{"type": "text", "text": words}] + [{"type": "image_url", "image_url": {"url": url}} for url in images]
    if input_text is None:
        messages = [{"role": "user", "content": user}]
    else:
        messages = [{"role": "system", "content": prompt}, {"role": "user", "content": user}]
    cap_field = "max_completion_tokens" if profile.shape == "openai" else "max_tokens"
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
    body: dict[str, Any] = {**profile.also_send, "model": model, "messages": messages, cap_field: max_output_tokens}
    if json_reply and STRUCTURED_JSON not in profile.ignores:
        body["response_format"] = {"type": "json_object"}
    unsent = Request(url, headers, body, b"")

    def _dispatch(body_bytes: bytes) -> Any:
        # The only send step. It runs only when the spend gate calls it, with the bytes the gate counted.
        request = replace(unsent, body_bytes=body_bytes)
        try:
            return transport(request) if transport is not None else _httpx_post(request)
        except ModuleNotFoundError:
            return _SendFailed("httpx is not installed (pip install 'proofhouse[live]')")
        except Exception as exc:  # noqa: BLE001 -- the live boundary must not leak the key
            slow = isinstance(exc, TimeoutError) or "Timeout" in type(exc).__name__
            return _SendFailed(type(exc).__name__, timed_out=slow)

    gated = spend.send_within_ceiling(
        unsent.body,
        provider=profile.id,
        model=model,
        max_output_tokens=max_output_tokens,
        ceiling_usd=max_cost_usd,
        send=_dispatch,
        snapshot=known,
    )
    admission = gated.admission.to_dict()
    if gated.admission.decision != "admitted":
        return RunResult("refused", gated.admission.code, gated.admission.message, profile.id, model, admission=admission)
    response = gated.response
    if isinstance(response, _SendFailed):
        if response.timed_out:
            waited = _timeout_seconds(url)
            detail = (
                f"{profile.name} did not answer within {waited:g} seconds; nothing more was tried. A slow or large "
                f"model needs longer: set PROOFHOUSE_TIMEOUT_SECONDS (for example {max(600.0, 2 * waited):g}), "
                "or use a faster model"
            )
        elif profile.local:
            detail = (
                f"nothing answered at {urlparse(url).netloc}; {profile.name} is probably not running. "
                "Start it, then try again (`proofhouse setup` shows how); nothing more was tried"
            )
        else:
            detail = f"the request could not be sent ({response.reason}); nothing more was tried"
        result = RunResult("error", "PHC-RUN-0005", f"PHC-RUN-0005: {detail}", profile.id, model, admission=admission)
        return RunResult(**_scrub(result.to_dict(), secret))
    status_code = getattr(response, "status_code", None)
    payload = getattr(response, "payload", None)
    if not isinstance(payload, dict):
        payload = {"value": payload}
    cost, warning = spend.cost_after(gated, payload)
    ok = isinstance(status_code, int) and 200 <= status_code < 300
    text = _output_text(payload) if ok else None
    code = None if ok else "PHC-RUN-0006"
    message = None
    if not ok:
        error = payload.get("error")
        reason = error.get("message") if isinstance(error, dict) else None
        message = f"PHC-RUN-0006: {profile.name} answered HTTP {status_code}" + (f": {reason}" if isinstance(reason, str) else "")
    if ok and profile.local and not (text or "").strip() and _cut_off(payload) and max_output_tokens < LOCAL_THINKING_ROOM:
        # A model that thinks before it answers can spend the whole cap thinking and say nothing. On this machine the
        # call is free, so ask once more with room to finish rather than hand back an empty reply.
        return run_prompt(provider_id, model, prompt=prompt, input_text=input_text, images=images,
                          max_output_tokens=LOCAL_THINKING_ROOM, max_cost_usd=max_cost_usd, transport=transport,
                          json_reply=json_reply)
    result = RunResult(
        "success" if ok else "error", code, message, profile.id, model, text, status_code, admission, cost, warning,
        ok and _cut_off(payload),
    )
    return RunResult(**_scrub(result.to_dict(), secret))
