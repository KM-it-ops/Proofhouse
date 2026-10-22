"""Generate images, video, speech and music with any service, known or unknown.

A media service is data, not code: a request template (where to send it, what
to send, with ``{prompt}``, ``{model}`` and other placeholders), how to wait for
a slow job, and where the finished file is in the answer. Shipped services are
in ``data/media_providers.json``; anyone can add one in
``PROOFHOUSE_HOME/media_providers.json`` with no code change.

Every paid request goes through the spend gate (``spend.send_media_within_ceiling``),
which builds the request itself from the template and the parameters, works out
the most it could cost from the price per unit (per image, per second of video,
per 1,000 characters of speech, or per request), and refuses before sending if
that is over your limit or there is no price. A service on this machine costs
nothing. One paid request per call; waiting for the result and downloading it
are plain reads that cost nothing.
"""

from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from . import providers, spend

MEDIA_SCHEMA = "proofhouse.media-providers/v1"
SHIPPED_PATH = Path(__file__).resolve().parent / "data" / "media_providers.json"
KINDS = ("image", "video", "speech", "music")
UNITS = ("request", "image", "second", "1k_chars")
DEFAULTS = {"size": "1024x1024", "voice": "alloy", "seconds": 5}
_REDACTED = "[REDACTED]"


class MediaError(ValueError):
    """The media service or request is unusable; nothing was sent."""


@dataclass(frozen=True, slots=True)
class MediaProvider:
    id: str
    name: str
    kinds: tuple[str, ...]
    base_url: str
    key_env: str | None
    auth: str
    unit: str
    submit: dict[str, Any]
    poll: dict[str, Any] | None
    result: dict[str, Any]
    origin: str

    @property
    def local(self) -> bool:
        return (urlparse(self.base_url).hostname or "").lower() in providers.LOCAL_HOSTS


@dataclass(frozen=True, slots=True)
class MediaRequest:
    url: str
    headers: dict[str, str]
    body: dict[str, Any]
    body_bytes: bytes


@dataclass(frozen=True, slots=True)
class MediaResponse:
    status_code: int
    payload: dict[str, Any] | None = None
    content: bytes | None = None


Transport = Callable[[str, str, dict[str, str], bytes | None], MediaResponse]


@dataclass
class MediaResult:
    status: str  # "success", "refused" or "error"
    code: str | None
    message: str | None
    provider: str
    model: str
    kind: str
    path: str | None = None
    admission: dict[str, Any] = field(default_factory=dict)
    cost: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return dict(vars(self))


def _parse(raw: object, origin: str) -> MediaProvider:
    if not isinstance(raw, dict):
        raise MediaError("a media service must be an object")
    pid = raw.get("id")
    if not isinstance(pid, str) or not providers._ID.fullmatch(pid):
        raise MediaError(f"media service id {pid!r} must be lowercase letters, digits, '.', '_' or '-'")
    kinds = tuple(raw.get("kinds") or ())
    if not kinds or any(k not in KINDS for k in kinds):
        raise MediaError(f"{pid}: kinds must be some of {', '.join(KINDS)}")
    unit = raw.get("unit", "request")
    if unit not in UNITS:
        raise MediaError(f"{pid}: unit must be one of {', '.join(UNITS)}")
    auth = raw.get("auth", "bearer")
    if auth not in ("bearer", "key", "none") and not (isinstance(auth, str) and auth.startswith("header:") and len(auth) > 7):
        raise MediaError(f"{pid}: auth must be bearer, key, none or header:<Name>")
    submit, result = raw.get("submit"), raw.get("result")
    if not isinstance(submit, dict) or not isinstance(submit.get("path"), str) or not isinstance(submit.get("body"), dict):
        raise MediaError(f"{pid}: submit needs a path and a body")
    if not isinstance(result, dict) or not (result.get("binary") or result.get("asset")):
        raise MediaError(f"{pid}: result needs asset paths or binary: true")
    poll = raw.get("poll")
    if poll is not None and (not isinstance(poll, dict) or not {"url", "status", "done"} <= set(poll)):
        raise MediaError(f"{pid}: poll needs url, status and done")
    key_env = raw.get("key_env")
    if key_env is not None and (not isinstance(key_env, str) or not providers._ENV.fullmatch(key_env)):
        raise MediaError(f"{pid}: key_env must be an environment variable name")
    try:
        base = providers.check_base_url(raw.get("base_url"))
    except providers.ProviderError as exc:
        raise MediaError(f"{pid}: {exc}") from None
    return MediaProvider(pid, str(raw.get("name", pid)), kinds, base, key_env, auth, unit, submit, poll, result, origin)


def _load(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as exc:
        raise MediaError(f"{path} is unreadable: {type(exc).__name__}") from None
    if not isinstance(data, dict) or data.get("schema") != MEDIA_SCHEMA or not isinstance(data.get("providers"), list):
        raise MediaError(f"{path} must be a {MEDIA_SCHEMA} file with a providers list")
    return data["providers"]


def user_path() -> Path:
    return providers.proofhouse_home() / "media_providers.json"


def all_media_providers() -> dict[str, MediaProvider]:
    from . import addons, learn_catalog

    shipped = {p.id: p for p in (_parse(raw, "shipped") for raw in _load(SHIPPED_PATH))}
    user = {p.id: p for p in (_parse(raw, "yours") for raw in _load(user_path()))}
    merged = learn_catalog.merge_learned(
        {pid: {"id": pid} for pid in shipped},
        "media_providers",
        user={pid: {"id": pid} for pid in user},
    )
    found = dict(shipped)
    for name, raw in addons.contributions("media_providers"):
        if name == learn_catalog.LEARNED_PACK:
            if raw.get("id") in merged and raw.get("id") not in shipped and raw.get("id") not in user:
                try:
                    found[_parse(raw, f"add-on {name}").id] = _parse(raw, f"add-on {name}")
                except MediaError:
                    continue
            continue
        try:
            added = _parse(raw, f"add-on {name}")
        except MediaError:
            continue  # checked when the pack was installed; a package add-on's bad entry is skipped
        found[added.id] = added
    found.update(user)
    return found


def find(provider_id: str) -> MediaProvider | None:
    return all_media_providers().get(provider_id)


# --- building the one paid request (called by the spend gate) -----------------------------------


def _fill(value: Any, params: dict[str, Any]) -> Any:
    if isinstance(value, str):
        whole = value[1:-1] if value.startswith("{") and value.endswith("}") and value.count("{") == 1 else None
        if whole is not None and whole in params:
            return params[whole]  # keeps numbers numbers
        for key, val in params.items():
            value = value.replace("{" + key + "}", str(val))
        return value
    if isinstance(value, dict):
        return {k: _fill(v, params) for k, v in value.items()}
    if isinstance(value, list):
        return [_fill(v, params) for v in value]
    return value


def build_request(profile: MediaProvider, model: str, params: dict[str, Any]) -> tuple[str, dict[str, Any], Decimal]:
    """The URL, the body and how many price units this request is. Same parameters, same units, every time."""
    values = {**DEFAULTS, **params, "model": model}
    url = profile.base_url.rstrip("/") + _fill(profile.submit["path"], {k: str(v) for k, v in values.items()})
    if (urlparse(url).hostname or "").lower() != (urlparse(profile.base_url).hostname or "").lower():
        raise MediaError(f"{profile.id}: the request address leaves the service's host")
    body = _fill(profile.submit["body"], values)
    if profile.unit == "image":
        units = Decimal(int(values.get("n", 1)))
    elif profile.unit == "second":
        units = Decimal(str(values["seconds"]))
    elif profile.unit == "1k_chars":
        units = Decimal(-(-len(str(values.get("prompt", ""))) // 1000))
    else:
        units = Decimal(1)
    if not units.is_finite() or units <= 0:
        raise MediaError("the request size must be above zero")
    return url, body, units


# --- reading answers ----------------------------------------------------------------------------


def _dig(data: Any, path: str) -> Any:
    for part in path.split("."):
        if isinstance(data, list) and part.isdigit() and int(part) < len(data):
            data = data[int(part)]
        elif isinstance(data, dict) and part in data:
            data = data[part]
        else:
            return None
    return data


def _headers(profile: MediaProvider, secret: str | None) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if secret:
        if profile.auth == "bearer":
            headers["Authorization"] = f"Bearer {secret}"
        elif profile.auth == "key":
            headers["Authorization"] = f"Key {secret}"
        elif profile.auth.startswith("header:"):
            headers[profile.auth[len("header:"):]] = secret
    return headers


def _httpx_post(request: MediaRequest) -> MediaResponse:
    try:
        import httpx
    except ImportError:
        raise ModuleNotFoundError("httpx") from None
    with httpx.Client(timeout=600.0, follow_redirects=True) as client:
        reply = client.post(request.url, headers=request.headers, content=request.body_bytes)
        return _as_response(reply)


def _httpx_get(url: str, headers: dict[str, str]) -> MediaResponse:
    """A plain read (job status, finished file). It sends no body and costs nothing."""
    try:
        import httpx
    except ImportError:
        raise ModuleNotFoundError("httpx") from None
    with httpx.Client(timeout=600.0, follow_redirects=True) as client:
        return _as_response(client.get(url, headers=headers))


def _as_response(reply: Any) -> MediaResponse:
    kind = reply.headers.get("content-type", "")
    if "json" in kind:
        try:
            return MediaResponse(reply.status_code, reply.json())
        except ValueError:
            pass
    return MediaResponse(reply.status_code, None, reply.content)


def _refused(code: str, detail: str, provider: str, model: str, kind: str) -> MediaResult:
    return MediaResult("refused", code, f"{code}: {detail}", provider, model, kind)


def generate(
    kind: str,
    provider_id: str,
    model: str,
    *,
    prompt: str,
    out: Path,
    params: dict[str, Any] | None = None,
    max_cost_usd: str | None = None,
    transport: Callable[[MediaRequest], MediaResponse] | None = None,
    get: Callable[[str, dict[str, str]], MediaResponse] | None = None,
    poll_every: float = 2.0,
    poll_limit_seconds: float = 900.0,
    research: Any = None,
    ask: Any = None,
) -> MediaResult:
    """Make one image, video clip, voice track or music track and save it at ``out`` (extension added if missing)."""
    from . import learn, learn_catalog

    model = (model or "").strip()
    try:
        profile = find(provider_id)
    except MediaError as exc:
        return _refused("PHC-RUN-0001", str(exc), provider_id, model, kind)
    if profile is None:
        if ask is None and research is None:
            return _refused("PHC-RUN-0001", f"no media service named {provider_id!r}; see `proofhouse media list`", provider_id, model, kind)
        try:
            if ask is not None:
                learn_catalog.ensure_media(provider_id, None, ask)
            else:
                learn_catalog.ensure_media(provider_id, research)
        except learn.LearnError as exc:
            return _refused("PHC-RUN-0001", str(exc), provider_id, model, kind)
        try:
            profile = find(provider_id)
        except MediaError as exc:
            return _refused("PHC-RUN-0001", str(exc), provider_id, model, kind)
    if profile is None:
        return _refused("PHC-RUN-0001", f"could not learn media service {provider_id!r}", provider_id, model, kind)
    learned = learn_catalog.learned_raw("media_providers", provider_id)
    if learned and learn_catalog.needs_approval(learned):
        return _refused(
            "PHC-RUN-0001",
            learn_catalog.refusal_message(learned, thing=f"Media service {provider_id}",
                                          command=f"{learn_catalog.APPROVE_CMD} {provider_id}"),
            provider_id,
            model,
            kind,
        )
    if kind not in profile.kinds:
        return _refused("PHC-RUN-0002", f"{profile.name} does not make {kind} (it makes {', '.join(profile.kinds)})", profile.id, model, kind)
    if not model or not prompt.strip():
        return _refused("PHC-RUN-0002", "name the model and say what to make", profile.id, model, kind)
    secret = os.environ.get(profile.key_env) if profile.key_env else None
    if profile.key_env and not secret and not profile.local:
        return _refused("PHC-RUN-0003", f"set {profile.key_env} to your {profile.name} key", profile.id, model, kind)
    if max_cost_usd is None:
        if not profile.local:
            return _refused("PHC-RUN-0002", "name a spending limit for a paid service (--max-cost-usd)", profile.id, model, kind)
        max_cost_usd = "0.000000000001"
    headers = _headers(profile, secret)
    read = get or _httpx_get

    def _dispatch(url: str, body_bytes: bytes) -> Any:
        # The only paid send. It runs only when the spend gate calls it, with the request the gate built and counted.
        request = MediaRequest(url, headers, {}, body_bytes)
        try:
            return transport(request) if transport is not None else _httpx_post(request)
        except ModuleNotFoundError:
            return "httpx is not installed (pip install 'proofhouse[live]')"
        except Exception as exc:  # noqa: BLE001 -- the live boundary must not leak the key
            return type(exc).__name__

    gated = spend.send_media_within_ceiling(
        profile, model, {**(params or {}), "prompt": prompt}, ceiling_usd=max_cost_usd, send=_dispatch
    )
    admission = gated.admission.to_dict()
    base = dict(provider=profile.id, model=model, kind=kind, admission=admission)
    if gated.admission.decision != "admitted":
        return MediaResult("refused", gated.admission.code, gated.admission.message, **base)
    cost = {"usd": admission.get("worst_case_usd"), "basis": "estimated", "unit": profile.unit, "wall_seconds": None}
    response = gated.response
    if not isinstance(response, MediaResponse):
        return MediaResult("error", "PHC-RUN-0005", f"PHC-RUN-0005: the request could not be sent ({response}); nothing more was tried", **base, cost=cost)
    if not 200 <= response.status_code < 300:
        reason = _dig(response.payload or {}, "error.message") or _dig(response.payload or {}, "detail")
        message = f"PHC-RUN-0006: {profile.name} answered HTTP {response.status_code}" + (f": {reason}" if isinstance(reason, str) else "")
        return MediaResult("error", "PHC-RUN-0006", _scrub(message, secret), **base, cost=cost)
    try:
        data = _wait_and_fetch(profile, response, headers, read, poll_every, poll_limit_seconds)
    except MediaError as exc:
        return MediaResult("error", "PHC-RUN-0006", _scrub(f"PHC-RUN-0006: {exc}", secret), **base, cost=cost)
    ext = profile.result.get("ext") or _guess_ext(data, kind)
    target = out if out.suffix else out.with_suffix("." + ext)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return MediaResult("success", None, None, **base, path=str(target), cost=cost)


def _scrub(text: str, secret: str | None) -> str:
    return text.replace(secret, _REDACTED) if secret else text


def _wait_and_fetch(profile: MediaProvider, response: MediaResponse, headers: dict[str, str], read: Callable[..., MediaResponse],
                    every: float, limit: float) -> bytes:
    if profile.result.get("binary"):
        if response.content is None:
            raise MediaError(f"{profile.name} answered with JSON where a file was expected")
        return response.content
    payload = response.payload or {}
    if profile.poll:
        status_url = _dig(payload, profile.poll["url"])
        if not isinstance(status_url, str) or not status_url.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            raise MediaError(f"{profile.name} gave no address to check the job")
        waited = 0.0
        while True:
            state = read(status_url, headers)
            current = state.payload or {}
            status = _dig(current, profile.poll["status"])
            if status in profile.poll["done"]:
                payload = current
                break
            if status in profile.poll.get("failed", []):
                raise MediaError(f"{profile.name} reports the job {status}")
            if waited >= limit:
                raise MediaError(f"{profile.name} did not finish within {int(limit)} seconds")
            time.sleep(every)
            waited += every
        if profile.poll.get("result_url"):
            result_url = _dig(payload, profile.poll["result_url"]) or _dig(response.payload or {}, profile.poll["result_url"])
            if not isinstance(result_url, str):
                raise MediaError(f"{profile.name} gave no address for the result")
            payload = read(result_url, headers).payload or {}
    for path in profile.result.get("asset", []):
        found = _dig(payload, path)
        if isinstance(found, str) and found:
            if found.startswith(("https://", "http://")):
                fetched = read(found, {})
                if fetched.content is None:
                    raise MediaError(f"{profile.name}'s file address returned no file")
                return fetched.content
            try:
                return base64.b64decode(found, validate=True)
            except ValueError:
                continue
    raise MediaError(f"{profile.name}'s answer held no file at {', '.join(profile.result.get('asset', []))}")


def _guess_ext(data: bytes, kind: str) -> str:
    signatures = {b"\x89PNG": "png", b"\xff\xd8": "jpg", b"GIF8": "gif", b"ID3": "mp3", b"RIFF": "wav", b"OggS": "ogg"}
    for head, ext in signatures.items():
        if data.startswith(head):
            return ext
    if data[4:8] == b"ftyp":
        return "mp4"
    return {"image": "png", "video": "mp4", "speech": "mp3", "music": "mp3"}[kind]
