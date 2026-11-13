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
import re
import shutil
import subprocess
import sys
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
PYTHON = "@python"  # a program line may start the Python that runs Proofhouse, wherever it lives
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
    run: dict[str, Any] | None = None  # a program on this machine instead of a web address

    @property
    def local(self) -> bool:
        # A learned service is never treated as local, even at a loopback address: it always needs a spending limit.
        if self.origin == "add-on learned":
            return False
        if self.run is not None:
            return True
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
    location: str | None = None


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


_PROGRAM_ORIGINS = ("shipped", "yours")
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _parse_run(pid: str, run: object, origin: str) -> dict[str, Any]:
    """A program on this machine: a command list (never one shell string), what goes on stdin, where the file comes out."""
    if origin not in _PROGRAM_ORIGINS:
        raise MediaError(f"{pid}: only the shipped table and your own media_providers.json may run a program on this machine")
    if not isinstance(run, dict):
        raise MediaError(f"{pid}: run must be an object with a command list")
    command = run.get("command")
    if not isinstance(command, list) or not command or any(not isinstance(a, str) or not a for a in command):
        raise MediaError(f"{pid}: run.command must be a list of words, never one shell string")
    if "{" in command[0]:
        raise MediaError(f"{pid}: the program to run is never filled in from a placeholder")
    stdin = run.get("stdin")
    if stdin is not None and not isinstance(stdin, str):
        raise MediaError(f"{pid}: run.stdin must be text")
    output = run.get("output", "file")
    if output not in ("file", "stdout"):
        raise MediaError(f"{pid}: run.output must be file or stdout")
    ext = run.get("ext")
    if not isinstance(ext, str) or not re.fullmatch(r"[a-z0-9]{1,8}", ext):
        raise MediaError(f"{pid}: run.ext must name the file type it makes, such as wav or png")
    timeout = run.get("timeout", 900)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 1 <= timeout <= 86400:
        raise MediaError(f"{pid}: run.timeout must be between 1 and 86400 seconds")
    if output == "file" and not any("{out}" in a for a in command[1:]):
        raise MediaError(f"{pid}: run.command must say where the file goes ({{out}}), or set output to stdout")
    return {"command": list(command), "stdin": stdin, "output": output, "ext": ext, "timeout": timeout}


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
    key_env = raw.get("key_env")
    if key_env is not None and (not isinstance(key_env, str) or not providers._ENV.fullmatch(key_env)):
        raise MediaError(f"{pid}: key_env must be an environment variable name")
    if "run" in raw:
        run = _parse_run(pid, raw["run"], origin)
        return MediaProvider(pid, str(raw.get("name", pid)), kinds, "", key_env, "none", unit, {}, None,
                             {"ext": run["ext"]}, origin, run)
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
    try:
        base = providers.check_base_url(raw.get("base_url"))
    except providers.ProviderError as exc:
        raise MediaError(f"{pid}: {exc}") from None
    if origin in ("learned", "add-on learned") and result.get("ext") is not None:
        from .learn_catalog import media_ext_problem

        problem = media_ext_problem(result.get("ext"))
        if problem:
            raise MediaError(f"{pid}: {problem}")
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
    """Shipped services, then yours, then other add-on packs. A learned service is used only when the id is still free."""
    from . import learn_catalog

    shipped = {p.id: p for p in (_parse(raw, "shipped") for raw in _load(SHIPPED_PATH))}
    user = {p.id: p for p in (_parse(raw, "yours") for raw in _load(user_path()))}
    found = dict(shipped)
    found.update(user)
    others, learned = learn_catalog.split_contributions("media_providers")
    for name, raw in others:
        try:
            added = _parse(raw, f"add-on {name}")
        except MediaError:
            continue  # checked when the pack was installed; a package add-on's bad entry is skipped
        found[added.id] = added
    for name, raw in learned:
        if raw.get("id") in found:
            continue
        try:
            added = _parse(raw, f"add-on {name}")
        except MediaError:
            continue
        found[added.id] = added
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
    if profile.run is not None:
        text = {k: str(v) for k, v in values.items()}

        def fill(arg: str) -> str:  # one pass, so words in the prompt are never read as placeholders
            return _PLACEHOLDER.sub(lambda m: text.get(m.group(1), m.group(0)), arg)

        def word(arg: str) -> str:
            filled = fill(arg)
            if filled.startswith("-") and not arg.startswith("-"):  # a value, not the line, made it a switch
                raise MediaError(f"{profile.id}: a value starting with '-' would be read as an option by the "
                                 "program; send free text on stdin")
            return filled

        command = profile.run["command"]
        stdin = profile.run["stdin"]
        url = "program:" + profile.id
        body: Any = {"command": [command[0], *(word(a) for a in command[1:])],
                     "stdin": None if stdin is None else fill(stdin)}
    else:
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


def _httpx_post(request: MediaRequest, *, follow_redirects: bool = False) -> MediaResponse:
    try:
        import httpx
    except ImportError:
        raise ModuleNotFoundError("httpx") from None
    with httpx.Client(timeout=600.0, follow_redirects=follow_redirects) as client:
        reply = client.post(request.url, headers=request.headers, content=request.body_bytes)
        return _as_response(reply)


def _httpx_get(url: str, headers: dict[str, str], *, follow_redirects: bool = False) -> MediaResponse:
    """A plain read (job status, finished file). It sends no body and costs nothing."""
    try:
        import httpx
    except ImportError:
        raise ModuleNotFoundError("httpx") from None
    with httpx.Client(timeout=600.0, follow_redirects=follow_redirects) as client:
        return _as_response(client.get(url, headers=headers))


def _as_response(reply: Any) -> MediaResponse:
    headers = getattr(reply, "headers", {}) or {}
    location = headers.get("location") or headers.get("Location")
    if isinstance(location, str) and 300 <= reply.status_code < 400:
        return MediaResponse(reply.status_code, None, None, location)
    kind = headers.get("content-type", "")
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
    pending = learn_catalog.unapproved("media_providers", provider_id, profile)
    if pending:
        return _refused(
            "PHC-RUN-0001",
            learn_catalog.refusal_message(pending, thing=f"Media service {provider_id}",
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
        return _refused("PHC-RUN-0003", providers.missing_key(profile.key_env, profile.name), profile.id, model, kind)
    if max_cost_usd is None:
        if not profile.local:
            return _refused("PHC-RUN-0002", "name a spending limit for a paid service (--max-cost-usd)", profile.id, model, kind)
        max_cost_usd = "0.000000000001"
    headers = _headers(profile, secret)
    # One admission authorizes one destination. Redirects can replay a paid POST
    # or forward a custom credential header to a different service.
    follow = False
    read = get or (lambda url, hdrs: _httpx_get(url, hdrs, follow_redirects=follow))
    asked = {**(params or {}), "prompt": prompt}
    target = None
    if profile.run is not None:
        target = (out if out.suffix else out.with_suffix("." + profile.run["ext"])).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.unlink(missing_ok=True)  # an old file must never pass for a new one
        asked["out"] = str(target)

    def _dispatch(url: str, body_bytes: bytes) -> Any:
        # The only paid send. It runs only when the spend gate calls it, with the request the gate built and counted.
        if profile.run is not None:
            return _run_program(profile, body_bytes)
        request = MediaRequest(url, headers, {}, body_bytes)
        try:
            return transport(request) if transport is not None else _httpx_post(request, follow_redirects=follow)
        except ModuleNotFoundError:
            return "httpx is not installed (pip install 'proofhouse[live]')"
        except Exception as exc:  # noqa: BLE001 -- the live boundary must not leak the key
            return type(exc).__name__

    gated = spend.send_media_within_ceiling(profile, model, asked, ceiling_usd=max_cost_usd, send=_dispatch)
    admission = gated.admission.to_dict()
    base = dict(provider=profile.id, model=model, kind=kind, admission=admission)
    if gated.admission.decision != "admitted":
        return MediaResult("refused", gated.admission.code, gated.admission.message, **base)
    cost = {"usd": admission.get("worst_case_usd"), "basis": "estimated", "unit": profile.unit, "wall_seconds": None}
    response = gated.response
    if target is not None:
        if not isinstance(response, MediaResponse):
            return MediaResult("error", "PHC-RUN-0005", f"PHC-RUN-0005: {profile.name} did not finish: {response}", **base, cost=cost)
        if response.content is not None:
            target.write_bytes(response.content)
        if not target.is_file() or target.stat().st_size == 0:
            return MediaResult("error", "PHC-RUN-0006", f"PHC-RUN-0006: {profile.name} finished but wrote nothing at {target}",
                               **base, cost=cost)
        return MediaResult("success", None, None, **base, path=str(target), cost=cost)
    if not isinstance(response, MediaResponse):
        return MediaResult("error", "PHC-RUN-0005", f"PHC-RUN-0005: the request could not be sent ({response}); nothing more was tried", **base, cost=cost)
    if response.location or 300 <= response.status_code < 400:
        where = response.location or "another address"
        return MediaResult("error", "PHC-RUN-0006", _scrub(
            f"PHC-RUN-0006: {profile.name} redirected to {where}; nothing was sent there", secret), **base, cost=cost)
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


def _run_program(profile: MediaProvider, body_bytes: bytes) -> MediaResponse | str:
    """Run the exact command the gate counted. No shell: every word reaches the program as plain text."""
    assert profile.run is not None
    body = json.loads(body_bytes)
    first, *rest = body["command"]
    program = sys.executable if first == PYTHON else _find_program(first)
    if program is None:
        return f"{first} is not installed or not on PATH (or give its full path)"
    if Path(program).suffix.lower() in (".bat", ".cmd"):
        return f"{program} is a batch file, which would read the words as commands; point the line at the program itself"
    timeout = profile.run["timeout"]
    stdin = body["stdin"]
    try:
        done = subprocess.run([program, *rest], input=None if stdin is None else stdin.encode("utf-8"),
                              stdin=subprocess.DEVNULL if stdin is None else None, capture_output=True,
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return f"it ran past its {timeout:g} s limit and was stopped"
    except OSError as exc:
        return f"{first} could not start ({type(exc).__name__})"
    if done.returncode != 0:
        lines = done.stderr.decode("utf-8", "replace").strip().splitlines()
        return f"it stopped with exit code {done.returncode}" + (f": {lines[-1][:300]}" if lines else "")
    return MediaResponse(200, None, done.stdout if profile.run["output"] == "stdout" else None)


def _find_program(first: str) -> str | None:
    """A bare name from PATH's full folders only, never the current folder (which Windows searches first, and where
    a downloaded film folder could plant one); anything else must be a full path."""
    if Path(first).is_absolute():
        try:
            return first if Path(first).is_file() else None
        except OSError:
            return None
    if Path(first).name != first:
        return None  # a relative path would depend on where the command was run
    exts = [""]
    if os.name == "nt":
        pathext = [e for e in os.environ.get("PATHEXT", ".COM;.EXE").split(os.pathsep) if e]
        if Path(first).suffix.upper() not in (e.upper() for e in pathext):
            exts = pathext
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        if not folder or not Path(folder).is_absolute():
            continue
        for ext in exts:
            hit = Path(folder) / (first + ext)
            try:
                if hit.is_file() and os.access(hit, os.X_OK):
                    return str(hit)
            except OSError:
                continue
    return None


def _scrub(text: str, secret: str | None) -> str:
    return text.replace(secret, _REDACTED) if secret else text


def _same_service_url(profile: MediaProvider, url: Any) -> bool:
    """A status or result address: https (or local http for a built-in) and the service's own host."""
    if not isinstance(url, str) or not url:
        return False
    if profile.origin == "add-on learned":
        from .learn_catalog import public_https

        if not public_https(url):
            return False
    elif not url.startswith(("https://", "http://localhost", "http://127.0.0.1")):
        return False
    return (urlparse(url).hostname or "").lower() == (urlparse(profile.base_url).hostname or "").lower()


def _wait_and_fetch(profile: MediaProvider, response: MediaResponse, headers: dict[str, str], read: Callable[..., MediaResponse],
                    every: float, limit: float) -> bytes:
    def checked_read(url: str, request_headers: dict[str, str]) -> MediaResponse:
        if profile.origin == "add-on learned" and not _same_service_url(profile, url):
            raise MediaError(f"{profile.name} gave an address that is not https on its own host: {url}")
        answer = read(url, request_headers)
        if answer.location or 300 <= answer.status_code < 400:
            raise MediaError(f"{profile.name} redirected to {answer.location or 'another address'}; nothing was sent there")
        return answer

    if profile.result.get("binary"):
        if response.content is None:
            raise MediaError(f"{profile.name} answered with JSON where a file was expected")
        return response.content
    payload = response.payload or {}
    if profile.poll:
        status_url = _dig(payload, profile.poll["url"])
        if not _same_service_url(profile, status_url):
            raise MediaError(f"{profile.name} gave no address on its own host to check the job: {status_url}")
        waited = 0.0
        while True:
            state = checked_read(status_url, headers)
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
            if not _same_service_url(profile, result_url):
                raise MediaError(f"{profile.name} gave an address that is not https on its own host: {result_url}")
            payload = checked_read(result_url, headers).payload or {}
    for path in profile.result.get("asset", []):
        found = _dig(payload, path)
        if isinstance(found, str) and found:
            if found.startswith(("https://", "http://")):
                fetched = checked_read(found, {})
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
