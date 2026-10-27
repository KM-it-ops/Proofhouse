"""Train models on your data: fine-tuning services or your own machine, within one spending limit.

A training service is data, not code. An online service is three request
templates: upload the data file, start the job, read its status. A service on
your own machine is a command template (for example LoRA with MLX). Shipped
services are in ``data/training_services.json``; add any other in
``PROOFHOUSE_HOME/training_services.json`` with no code change.

Starting a paid job goes through the spend gate (``spend.send_training_within_ceiling``).
The gate builds the job request from the template, bounds the tokens it can bill
(every byte of the data, times the epochs written into the request), prices that
per million training tokens from the price you declared, and refuses before
anything is uploaded or started if it is over your limit. Uploading the data file
is a plain file upload that starts nothing; reading the job's status costs nothing.
"""

from __future__ import annotations

import csv
import json
import math
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from . import __version__, providers, spend

TRAIN_SCHEMA = "proofhouse.training-services/v1"
SHIPPED_PATH = Path(__file__).resolve().parent / "data" / "training_services.json"
ROLES = ("system", "user", "assistant")
MIN_EXAMPLES = 10
_REDACTED = "[REDACTED]"


class TrainError(ValueError):
    """The training service, data or request is unusable; nothing was sent."""


@dataclass(frozen=True, slots=True)
class TrainService:
    id: str
    name: str
    base_url: str | None
    key_env: str | None
    auth: str
    provider: str | None
    upload: dict[str, Any] | None
    create: dict[str, Any] | None
    status: dict[str, Any] | None
    command: tuple[str, ...] | None
    use_hint: str
    origin: str

    @property
    def local(self) -> bool:
        if self.command is not None:
            return True
        # A learned online service is never local, so it cannot skip the spending limit.
        if self.origin == "add-on learned":
            return False
        return (urlparse(self.base_url or "").hostname or "").lower() in providers.LOCAL_HOSTS


@dataclass(frozen=True, slots=True)
class TrainRequest:
    url: str
    headers: dict[str, str]
    body_bytes: bytes


@dataclass(frozen=True, slots=True)
class TrainResponse:
    status_code: int
    payload: dict[str, Any] | None = None
    location: str | None = None


@dataclass
class TrainResult:
    status: str  # "success", "started", "refused" or "error"
    code: str | None
    message: str | None
    service: str
    model: str
    job_id: str | None = None
    trained_model: str | None = None
    folder: str | None = None
    admission: dict[str, Any] = field(default_factory=dict)
    use: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dict(vars(self))


# --- services as data ---------------------------------------------------------------------------


def _parse(raw: object, origin: str) -> TrainService:
    if not isinstance(raw, dict):
        raise TrainError("a training service must be an object")
    sid = raw.get("id")
    if not isinstance(sid, str) or not providers._ID.fullmatch(sid):
        raise TrainError(f"training service id {sid!r} must be lowercase letters, digits, '.', '_' or '-'")
    hint = str(raw.get("use_hint") or "")
    key_env = raw.get("key_env")
    if key_env is not None and (not isinstance(key_env, str) or not providers._ENV.fullmatch(key_env)):
        raise TrainError(f"{sid}: key_env must be an environment variable name")
    command = raw.get("command")
    if command is not None:
        if not isinstance(command, list) or not command or not all(isinstance(c, str) and c for c in command):
            raise TrainError(f"{sid}: command must be a list of words")
        return TrainService(sid, str(raw.get("name", sid)), None, key_env, "none", None, None, None, None, tuple(command), hint, origin)
    upload, create, status = raw.get("upload"), raw.get("create"), raw.get("status")
    if not isinstance(upload, dict) or not isinstance(upload.get("path"), str) or not isinstance(upload.get("id"), str):
        raise TrainError(f"{sid}: upload needs a path and the id field of the answer")
    if not isinstance(create, dict) or not isinstance(create.get("path"), str) or not isinstance(create.get("body"), dict):
        raise TrainError(f"{sid}: create needs a path and a body")
    if '"{epochs}"' not in json.dumps(create["body"]):
        raise TrainError(f"{sid}: the create body must set the epochs with \"{{epochs}}\", so the cost has a limit")
    if not isinstance(status, dict) or not {"path", "field", "done"} <= set(status):
        raise TrainError(f"{sid}: status needs path, field and done")
    auth = raw.get("auth", "bearer")
    if auth not in ("bearer", "none") and not (isinstance(auth, str) and auth.startswith("header:") and len(auth) > 7):
        raise TrainError(f"{sid}: auth must be bearer, none or header:<Name>")
    try:
        base = providers.check_base_url(raw.get("base_url"))
    except providers.ProviderError as exc:
        raise TrainError(f"{sid}: {exc}") from None
    provider = raw.get("provider")
    return TrainService(sid, str(raw.get("name", sid)), base, key_env, auth, provider if isinstance(provider, str) else None,
                        upload, create, status, None, hint, origin)


def _load(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as exc:
        raise TrainError(f"{path} is unreadable: {type(exc).__name__}") from None
    if not isinstance(data, dict) or data.get("schema") != TRAIN_SCHEMA or not isinstance(data.get("services"), list):
        raise TrainError(f"{path} must be a {TRAIN_SCHEMA} file with a services list")
    return data["services"]


def user_path() -> Path:
    return providers.proofhouse_home() / "training_services.json"


def all_services() -> dict[str, TrainService]:
    """Shipped services, then yours, then other add-on packs. A learned service is used only when the id is still free."""
    from . import learn_catalog

    shipped = {s.id: s for s in (_parse(raw, "shipped") for raw in _load(SHIPPED_PATH))}
    user = {s.id: s for s in (_parse(raw, "yours") for raw in _load(user_path()))}
    found = dict(shipped)
    found.update(user)
    others, learned = learn_catalog.split_contributions("training_services")
    for name, raw in others:
        try:
            added = _parse(raw, f"add-on {name}")
        except TrainError:
            continue  # checked when the pack was installed; a package add-on's bad entry is skipped
        found[added.id] = added
    for name, raw in learned:
        if raw.get("id") in found:
            continue
        try:
            added = _parse(raw, f"add-on {name}")
        except TrainError:
            continue
        found[added.id] = added
    return found


def find(service_id: str) -> TrainService | None:
    return all_services().get(service_id)


# --- data ---------------------------------------------------------------------------------------


def _example(raw: Any, system: str | None) -> dict[str, Any]:
    if isinstance(raw, dict) and isinstance(raw.get("messages"), list):
        messages = raw["messages"]
    elif isinstance(raw, dict):
        given = next((raw[k] for k in ("input", "prompt", "question") if isinstance(raw.get(k), str)), None)
        wanted = next((raw[k] for k in ("output", "completion", "response", "answer") if isinstance(raw.get(k), str)), None)
        if given is None or wanted is None:
            raise TrainError("each example needs messages, or an input and an output")
        messages = [{"role": "user", "content": given}, {"role": "assistant", "content": wanted}]
    else:
        raise TrainError("each example must be a JSON object")
    if system and not (messages and isinstance(messages[0], dict) and messages[0].get("role") == "system"):
        messages = [{"role": "system", "content": system}, *messages]
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in ROLES or not isinstance(message.get("content"), str) \
                or not message["content"].strip():
            raise TrainError("every message needs a role (system, user or assistant) and some content")
    if not messages or messages[-1]["role"] != "assistant" or not any(m["role"] == "user" for m in messages):
        raise TrainError("each example needs a user message and must end with the assistant's answer")
    return {"messages": [{"role": m["role"], "content": m["content"]} for m in messages]}


def read_examples(source: Path, system: str | None = None) -> list[dict[str, Any]]:
    rows: list[Any]
    if source.suffix.lower() == ".csv":
        with source.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    else:
        rows = []
        for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    raise TrainError(f"{source.name} line {number} is not JSON") from None
    examples, seen = [], set()
    for number, row in enumerate(rows, start=1):
        try:
            example = _example(row, system)
        except TrainError as exc:
            raise TrainError(f"{source.name} example {number}: {exc}") from None
        key = json.dumps(example, sort_keys=True)
        if key not in seen:
            seen.add(key)
            examples.append(example)
    if not examples:
        raise TrainError(f"{source.name} has no examples")
    return examples


def build_dataset(source: Path, out_dir: Path, *, system: str | None = None, valid_share: float = 0.1) -> dict[str, Any]:
    """Clean examples into train.jsonl and valid.jsonl (every n-th example held out), with a summary in data.json."""
    if not 0 <= valid_share < 0.5:
        raise TrainError("--valid-share must be from 0 to 0.5")
    examples = read_examples(source, system)
    every = round(1 / valid_share) if valid_share else 0
    held = [e for i, e in enumerate(examples) if every and len(examples) >= 2 * every and i % every == every - 1]
    kept = [e for e in examples if not any(e is h for h in held)]
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, chosen in (("train.jsonl", kept), ("valid.jsonl", held)):
        (out_dir / name).write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in chosen), encoding="utf-8")
    summary = {"source": str(source), "examples": len(examples), "train": len(kept), "valid": len(held),
               "train_bytes": (out_dir / "train.jsonl").stat().st_size, "system_message": bool(system),
               "warnings": [f"only {len(examples)} examples; most services need at least {MIN_EXAMPLES}"]
               if len(examples) < MIN_EXAMPLES else []}
    (out_dir / "data.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def _data_files(data: Path) -> tuple[Path, Path | None]:
    if data.is_dir():
        train_file, valid_file = data / "train.jsonl", data / "valid.jsonl"
        if not train_file.is_file():
            raise TrainError(f"{data} has no train.jsonl; make one with `proofhouse train data`")
        return train_file, valid_file if valid_file.is_file() and valid_file.stat().st_size else None
    if not data.is_file():
        raise TrainError(f"{data} does not exist")
    return data, None


# --- the one paid request (built by the spend gate) ---------------------------------------------


def _fill(value: Any, params: dict[str, Any]) -> Any:
    """Fill placeholders; a value that is only a placeholder keeps its type, and is dropped when it has no value."""
    if isinstance(value, str):
        if value.startswith("{") and value.endswith("}") and value.count("{") == 1:
            return params.get(value[1:-1])
        for key, val in params.items():
            if val is not None:
                value = value.replace("{" + key + "}", str(val))
        return value
    if isinstance(value, dict):
        filled = {k: _fill(v, params) for k, v in value.items()}
        return {k: v for k, v in filled.items() if v is not None}
    if isinstance(value, list):
        return [v for v in (_fill(v, params) for v in value) if v is not None]
    return value


def build_job_request(profile: TrainService, model: str, params: dict[str, Any]) -> tuple[str, dict[str, Any], int, int]:
    """The job's URL and body, its epochs, and the bytes of data it trains on. Same inputs, same answer, every time."""
    epochs = params.get("epochs")
    if type(epochs) is not int or not 1 <= epochs <= 50:
        raise TrainError("epochs must be a whole number from 1 to 50")
    files = params.get("data_files")
    if not isinstance(files, list) or not files:
        raise TrainError("no data files")
    data_bytes = sum(Path(f).stat().st_size for f in files)
    if profile.create is None or profile.base_url is None:
        raise TrainError(f"{profile.id} runs on this machine and has no job request")
    values = {k: v for k, v in params.items() if k != "data_files"} | {"model": model}
    filled = _fill(profile.create["path"], {k: v for k, v in values.items() if isinstance(v, str)})
    if not isinstance(filled, str):
        raise TrainError(f"{profile.id}: the request address leaves the service's host")
    url = profile.base_url.rstrip("/") + filled
    if profile.origin == "add-on learned":
        from .learn_catalog import service_path_ok

        if not service_path_ok(profile.base_url, filled):
            raise TrainError(f"{profile.id}: the request address leaves the service's host")
    elif (urlparse(url).hostname or "").lower() != (urlparse(profile.base_url).hostname or "").lower():
        raise TrainError(f"{profile.id}: the request address leaves the service's host")
    body = _fill(profile.create["body"], values)
    if epochs not in _numbers(body):
        raise TrainError(f"{profile.id}: the job request does not carry the epochs")
    return url, body, epochs, data_bytes


def _numbers(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return [n for v in value.values() for n in _numbers(v)]
    if isinstance(value, list):
        return [n for v in value for n in _numbers(v)]
    return [value] if type(value) is int else []


# --- the network ----------------------------------------------------------------------------------


def _headers(profile: TrainService, secret: str | None, json_body: bool = True) -> dict[str, str]:
    headers = {"Content-Type": "application/json"} if json_body else {}
    if secret and profile.auth == "bearer":
        headers["Authorization"] = f"Bearer {secret}"
    elif secret and profile.auth.startswith("header:"):
        headers[profile.auth[len("header:"):]] = secret
    return headers


def _httpx_post(request: TrainRequest) -> TrainResponse:
    try:
        import httpx
    except ImportError:
        raise ModuleNotFoundError("httpx") from None
    with httpx.Client(timeout=120.0, follow_redirects=False) as client:
        return _as_response(client.post(request.url, headers=request.headers, content=request.body_bytes))


def _httpx_upload(url: str, headers: dict[str, str], fields: dict[str, str], file_field: str, file_name: str,
                  content: bytes) -> TrainResponse:
    """A file upload: it stores your data file with the service and starts nothing."""
    try:
        import httpx
    except ImportError:
        raise ModuleNotFoundError("httpx") from None
    with httpx.Client(timeout=600.0, follow_redirects=False) as client:
        reply = client.post(url, headers=headers, data=fields, files={file_field: (file_name, content, "application/jsonl")})
        return _as_response(reply)


def _httpx_get(url: str, headers: dict[str, str]) -> TrainResponse:
    """A plain read of the job's status. It sends no body and costs nothing."""
    try:
        import httpx
    except ImportError:
        raise ModuleNotFoundError("httpx") from None
    with httpx.Client(timeout=60.0, follow_redirects=False) as client:
        return _as_response(client.get(url, headers=headers))


def _as_response(reply: Any) -> TrainResponse:
    headers = getattr(reply, "headers", {}) or {}
    location = headers.get("location") or headers.get("Location")
    if not isinstance(location, str) or not 300 <= reply.status_code < 400:
        location = None
    try:
        payload = None if location else reply.json()
    except ValueError:
        payload = None
    return TrainResponse(reply.status_code, payload if isinstance(payload, dict) else None, location if isinstance(location, str) else None)


def _dig(data: Any, path: str) -> Any:
    for part in path.split("."):
        if isinstance(data, dict) and part in data:
            data = data[part]
        else:
            return None
    return data


def _scrub(text: str, secret: str | None) -> str:
    return text.replace(secret, _REDACTED) if secret else text


Upload = Callable[[str, dict[str, str], dict[str, str], str, str, bytes], TrainResponse]
Read = Callable[[str, dict[str, str]], TrainResponse]


def start(
    service_id: str,
    model: str,
    data: Path,
    *,
    epochs: int = 3,
    suffix: str | None = None,
    max_cost_usd: str | None = None,
    wait: bool = True,
    out_dir: Path | None = None,
    transport: Callable[[TrainRequest], TrainResponse] | None = None,
    upload: Upload | None = None,
    get: Read | None = None,
    poll_every: float = 30.0,
    poll_limit_seconds: float = 6 * 3600.0,
    allow_commands: bool = False,
    research: Any = None,
    ask: Any = None,
) -> TrainResult:
    from . import learn, learn_catalog

    model = (model or "").strip()
    profile = find(service_id)
    if profile is None:
        if ask is None and research is None:
            return TrainResult("refused", "PHC-RUN-0001", f"PHC-RUN-0001: no training service named {service_id!r}; see `proofhouse train services`",
                               service_id, model)
        try:
            if ask is not None:
                learn_catalog.ensure_train(service_id, None, ask)
            else:
                learn_catalog.ensure_train(service_id, research)
        except learn.LearnError as exc:
            return TrainResult("refused", "PHC-RUN-0001", f"PHC-RUN-0001: {exc}", service_id, model)
        profile = find(service_id)
    if profile is None:
        return TrainResult("refused", "PHC-RUN-0001", f"PHC-RUN-0001: could not learn training service {service_id!r}", service_id, model)
    pending = learn_catalog.unapproved("training_services", service_id, profile)
    if pending:
        return TrainResult(
            "refused",
            "PHC-RUN-0001",
            learn_catalog.refusal_message(pending, thing=f"Training service {service_id}",
                                          command=f"{learn_catalog.APPROVE_CMD} {service_id}"),
            service_id,
            model,
        )
    if profile.command is not None and learn_catalog.is_learned(profile) and not allow_commands:
        from . import make_checks
        return TrainResult("refused", "PHC-RUN-0002", f"PHC-RUN-0002: {make_checks.NOT_ALLOWED}", service_id, model)
    if not model:
        return TrainResult("refused", "PHC-RUN-0002", "PHC-RUN-0002: name the base model to train", profile.id, model)
    if type(epochs) is not int or not 1 <= epochs <= 50:  # before the cost is worked out: a negative count would price as free
        return TrainResult("refused", "PHC-RUN-0002", "PHC-RUN-0002: epochs must be a whole number from 1 to 50; nothing was uploaded", profile.id, model)
    try:
        train_file, valid_file = _data_files(data)
        examples = read_examples(train_file)
    except (TrainError, OSError) as exc:
        return TrainResult("refused", "PHC-RUN-0002", f"PHC-RUN-0002: {exc}", profile.id, model)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    folder = (out_dir or Path.cwd() / f"train-{profile.id}-{stamp}").resolve()
    folder.mkdir(parents=True, exist_ok=True)
    if profile.command is not None:
        result = _run_local(profile, model, train_file, valid_file, len(examples), epochs, suffix, folder)
    else:
        result = _run_service(profile, model, train_file, valid_file, epochs, suffix, max_cost_usd, wait, folder,
                              transport, upload or _httpx_upload, get or _httpx_get, poll_every, poll_limit_seconds)
    result.folder = str(folder)
    (folder / "train.json").write_text(json.dumps({**result.to_dict(), "proofhouse_version": __version__}, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return result


def _run_service(profile: TrainService, model: str, train_file: Path, valid_file: Path | None, epochs: int, suffix: str | None,
                 max_cost_usd: str | None, wait: bool, folder: Path, transport: Any, upload: Upload, read: Read,
                 poll_every: float, poll_limit: float) -> TrainResult:
    base = {"service": profile.id, "model": model}
    secret = os.environ.get(profile.key_env) if profile.key_env else None
    if profile.key_env and not secret and not profile.local:
        return TrainResult("refused", "PHC-RUN-0003", f"PHC-RUN-0003: set {profile.key_env} to your {profile.name} key", **base)
    if max_cost_usd is None:
        if not profile.local:
            return TrainResult("refused", "PHC-RUN-0002", "PHC-RUN-0002: name a spending limit for a paid service (--max-cost-usd)", **base)
        max_cost_usd = "0.000000000001"
    data_files = [str(train_file)] + ([str(valid_file)] if valid_file else [])
    try:  # refuse before uploading anything when the job could never be admitted
        per_million = spend._training_price(profile, model)
    except spend.SpendRefused as refusal:
        return TrainResult("refused", refusal.code, f"{refusal.code}: {refusal.detail}; nothing was uploaded", **base)
    if per_million is None:
        return TrainResult("refused", "PHC-COST-0002", f"PHC-COST-0002: no training price for {model!r} on {profile.id}; declare one "
                           "with `proofhouse train price`; nothing was uploaded", **base)
    worst = sum(Path(f).stat().st_size for f in data_files) * epochs * per_million[0] / 1_000_000
    try:
        over = worst > spend._ceiling(max_cost_usd)
    except spend.SpendRefused as refusal:
        return TrainResult("refused", refusal.code, f"{refusal.code}: {refusal.detail}", **base)
    if over:
        return TrainResult("refused", "PHC-COST-0001", f"PHC-COST-0001: worst case ${worst} is over the ceiling ${max_cost_usd}; "
                           "nothing was uploaded", **base)

    ids: dict[str, str] = {}
    for label, path in (("file_id", train_file), ("valid_file_id", valid_file)):
        if path is None:
            continue
        upload_spec = profile.upload or {}
        fields = {k: _fill(v, {"file_name": path.name}) for k, v in (upload_spec.get("fields") or {}).items()}
        try:
            upload_path = upload_spec["path"]
            if profile.origin == "add-on learned":
                from .learn_catalog import service_path_ok

                if not isinstance(upload_path, str) or not service_path_ok(profile.base_url or "", upload_path):
                    raise TrainError(f"{profile.id}: the request address leaves the service's host")
            answer = upload(profile.base_url.rstrip("/") + upload_path, _headers(profile, secret, json_body=False),
                            fields, str(upload_spec.get("file_field", "file")), path.name, path.read_bytes())
        except Exception as exc:  # noqa: BLE001 -- the live boundary must not leak the key
            return TrainResult("error", "PHC-RUN-0005", f"PHC-RUN-0005: the data upload failed ({type(exc).__name__}); no job was started", **base)
        file_id = _dig(answer.payload or {}, upload_spec["id"])
        if answer.location or not 200 <= answer.status_code < 300 or not isinstance(file_id, str):
            where = f"; redirected to {answer.location}; nothing was sent there" if answer.location else ""
            return TrainResult("error", "PHC-RUN-0006", _scrub(f"PHC-RUN-0006: {profile.name} did not accept the data file "
                               f"(HTTP {answer.status_code}){where}; no job was started", secret), **base)
        ids[label] = file_id

    headers = _headers(profile, secret)

    def _dispatch(url: str, body_bytes: bytes) -> Any:
        # The only paid send. It runs only when the spend gate calls it, with the job request the gate built and priced.
        request = TrainRequest(url, headers, body_bytes)
        try:
            return transport(request) if transport is not None else _httpx_post(request)
        except ModuleNotFoundError:
            return "httpx is not installed (pip install 'proofhouse[live]')"
        except Exception as exc:  # noqa: BLE001 -- the live boundary must not leak the key
            return type(exc).__name__

    params = {**ids, "epochs": epochs, "suffix": suffix, "data_files": data_files}
    gated = spend.send_training_within_ceiling(profile, model, params, ceiling_usd=max_cost_usd, send=_dispatch)
    admission = gated.admission.to_dict()
    if gated.admission.decision != "admitted":
        return TrainResult("refused", gated.admission.code, gated.admission.message, **base, admission=admission)
    response = gated.response
    if not isinstance(response, TrainResponse):
        return TrainResult("error", "PHC-RUN-0005", f"PHC-RUN-0005: the job request could not be sent ({response})", **base, admission=admission)
    job_id = _dig(response.payload or {}, str((profile.create or {}).get("id", "id")))
    if response.location or not 200 <= response.status_code < 300 or not isinstance(job_id, str):
        reason = _dig(response.payload or {}, "error.message")
        where = f"; redirected to {response.location}; nothing was sent there" if response.location else ""
        message = f"PHC-RUN-0006: {profile.name} answered HTTP {response.status_code}" + (f": {reason}" if isinstance(reason, str) else "") + where
        return TrainResult("error", "PHC-RUN-0006", _scrub(message, secret), **base, admission=admission)
    result = TrainResult("started", None, None, **base, job_id=job_id, admission=admission)
    if wait:
        _wait(profile, result, headers, read, poll_every, poll_limit, secret)
    return result


def _status_url(profile: TrainService, job_id: str) -> str:
    path = _fill((profile.status or {})["path"], {"job_id": job_id})
    if profile.origin == "add-on learned":
        from .learn_catalog import service_path_ok

        if not isinstance(path, str) or not service_path_ok(profile.base_url or "", path):
            raise TrainError(f"{profile.id}: the request address leaves the service's host")
    return (profile.base_url or "").rstrip("/") + path


def _apply_status(profile: TrainService, result: TrainResult, answer: TrainResponse) -> str | None:
    spec = profile.status or {}
    state = _dig(answer.payload or {}, spec["field"])
    if state in spec["done"]:
        trained = _dig(answer.payload or {}, str(spec.get("model", "")))
        result.status, result.trained_model = "success", trained if isinstance(trained, str) else None
        if result.trained_model:
            result.use = f"proofhouse run --provider {profile.provider or profile.id} --model {result.trained_model} --prompt \"...\""
    elif state in spec.get("failed", []):
        result.status, result.code, result.message = "error", "PHC-RUN-0006", f"PHC-RUN-0006: {profile.name} reports the job {state}"
    return state if isinstance(state, str) else None


def _wait(profile: TrainService, result: TrainResult, headers: dict[str, str], read: Read, every: float, limit: float,
          secret: str | None) -> None:
    waited = 0.0
    while result.status == "started":
        try:
            answer = read(_status_url(profile, result.job_id or ""), headers)
            if answer.location or 300 <= answer.status_code < 400:
                result.status, result.code = "error", "PHC-RUN-0006"
                result.message = _scrub(f"PHC-RUN-0006: {profile.name} redirected to {answer.location or 'another address'}; nothing was sent there", secret)
                return
            _apply_status(profile, result, answer)
        except Exception as exc:  # noqa: BLE001 -- a failed read is reported; the job keeps running at the service
            result.message = _scrub(f"could not read the job status ({type(exc).__name__}); check later with `proofhouse train status`", secret)
            return
        if result.status != "started":
            return
        if waited >= limit:
            result.message = f"still running after {int(limit)} seconds; check later with `proofhouse train status`"
            return
        time.sleep(every)
        waited += every


def status(service_id: str, job_id: str, *, get: Read | None = None) -> TrainResult:
    from . import learn_catalog

    profile = find(service_id)
    if profile is None or profile.command is not None:
        return TrainResult("refused", "PHC-RUN-0001", f"PHC-RUN-0001: no online training service named {service_id!r}", service_id, "")
    pending = learn_catalog.unapproved("training_services", service_id, profile)
    if pending:
        return TrainResult("refused", "PHC-RUN-0001", learn_catalog.refusal_message(
            pending, thing=f"Training service {service_id}", command=f"{learn_catalog.APPROVE_CMD} {service_id}"), service_id, "")
    secret = os.environ.get(profile.key_env) if profile.key_env else None
    result = TrainResult("started", None, None, profile.id, "", job_id=job_id)
    try:
        answer = (get or _httpx_get)(_status_url(profile, job_id), _headers(profile, secret))
        if answer.location or 300 <= answer.status_code < 400:
            return TrainResult("error", "PHC-RUN-0006", _scrub(
                f"PHC-RUN-0006: {profile.name} redirected to {answer.location or 'another address'}; nothing was sent there", secret),
                profile.id, "", job_id=job_id)
        state = _apply_status(profile, result, answer)
    except Exception as exc:  # noqa: BLE001 -- the live boundary must not leak the key
        return TrainResult("error", "PHC-RUN-0005", f"PHC-RUN-0005: could not read the job status ({type(exc).__name__})", profile.id, "", job_id=job_id)
    if result.status == "started":
        result.message = f"{profile.name} reports the job {state or 'in an unknown state'}"
    return result


# --- your own machine ---------------------------------------------------------------------------


def _run_local(profile: TrainService, model: str, train_file: Path, valid_file: Path | None, examples: int, epochs: int,
               suffix: str | None, folder: Path) -> TrainResult:
    base = {"service": profile.id, "model": model}
    data_dir = folder / "data"
    data_dir.mkdir(exist_ok=True)
    shutil.copyfile(train_file, data_dir / "train.jsonl")
    (data_dir / "valid.jsonl").write_bytes(valid_file.read_bytes() if valid_file else train_file.read_bytes())
    out = folder / "adapter"
    values = {"model": model, "data_dir": str(data_dir), "train": str(data_dir / "train.jsonl"), "valid": str(data_dir / "valid.jsonl"),
              "epochs": str(epochs), "iters": str(max(1, epochs * math.ceil(examples / 4))), "out": str(out), "suffix": suffix or "proofhouse"}
    command = [str(_fill(word, values)) for word in profile.command or ()]
    if shutil.which(command[0]) is None and not Path(command[0]).is_file():
        return TrainResult("refused", "PHC-RUN-0002", f"PHC-RUN-0002: {command[0]} is not installed on this machine", **base)
    from . import learn_catalog

    env = learn_catalog.command_env(folder, profile.key_env) if learn_catalog.is_learned(profile) else None
    with (folder / "train.log").open("w", encoding="utf-8") as log:
        run = subprocess.run(command, cwd=folder, stdout=log, stderr=subprocess.STDOUT, check=False, env=env)
    result = TrainResult("success" if run.returncode == 0 else "error", None if run.returncode == 0 else "PHC-RUN-0006",
                         None if run.returncode == 0 else f"PHC-RUN-0006: the training command exited {run.returncode}; see train.log",
                         **base, trained_model=str(out) if run.returncode == 0 else None,
                         admission={"price": {"source": spend.SOURCE_LOCAL}, "command": command})
    if run.returncode == 0 and profile.use_hint:
        text = str(_fill(profile.use_hint, values))
        if learn_catalog.is_learned(profile):
            saved = learn_catalog.learned_raw("training_services", profile.id)
            text = learn_catalog.suggested(text, saved.get("learned_by") if saved else None)
        result.use = text
    return result
