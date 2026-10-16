"""Providers: any model service Proofhouse can send a request to, known or unknown.

A provider is data, not code: an id, a name, the base address of its chat API,
the request shape it speaks, and the name of the environment variable that
holds its key (none for a server on this machine). The common services ship in
``data/providers.json``. Anyone can add a provider, override a shipped one, or
declare what a model costs in ``PROOFHOUSE_HOME/providers.json``, with no code
change (``proofhouse providers add`` / ``price``).

Most services speak the OpenAI chat format, so one request shape covers nearly
all of them: ``openai-compatible``, whose output cap is ``max_tokens``. OpenAI
itself uses ``max_completion_tokens`` (shape ``openai``).

A provider on this machine (``localhost``, ``127.0.0.1``, ``::1``) may use plain
http and needs no key. Anything else must use https. A broken providers file is
refused as a whole (fail closed), never half-read.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _read_umask() -> int:
    """The process umask, read once (os.umask can only be read by setting it, so it is put straight back)."""
    mask = os.umask(0)
    os.umask(mask)
    return mask


_UMASK = _read_umask()

PROVIDERS_SCHEMA = "proofhouse.providers/v1"
SHIPPED_PATH = Path(__file__).resolve().parent / "data" / "providers.json"
USER_FILE = "providers.json"
SHAPES = ("openai", "openai-compatible")
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
_ENV = re.compile(r"[A-Z_][A-Z0-9_]{0,127}")
_PROVIDER_KEYS = frozenset({"id", "name", "base_url", "shape", "key_env"})


class ProviderError(ValueError):
    """A provider entry or providers file is broken; nothing in it is used."""


@dataclass(frozen=True, slots=True)
class Provider:
    id: str
    name: str
    base_url: str
    shape: str
    key_env: str | None
    origin: str  # "shipped" or "yours"

    @property
    def host(self) -> str:
        return (urlparse(self.base_url).hostname or "").lower()

    @property
    def local(self) -> bool:
        return self.host in LOCAL_HOSTS

    @property
    def chat_url(self) -> str:
        return self.base_url.rstrip("/") + "/chat/completions"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "base_url": self.base_url,
            "shape": self.shape,
            "key_env": self.key_env,
            "local": self.local,
            "origin": self.origin,
        }


def check_base_url(url: object) -> str:
    """https anywhere; plain http only on this machine; no user, password, query or fragment."""
    if not isinstance(url, str) or not url or any(c.isspace() for c in url):
        raise ProviderError("base_url must be an address such as https://api.example.com/v1")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host:
        raise ProviderError(f"base_url {url!r} has no host")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and host in LOCAL_HOSTS):
        raise ProviderError(f"base_url {url!r} must use https (plain http only for localhost)")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ProviderError(f"base_url {url!r} must not carry a user, password, query or fragment")
    return url


def parse_provider(raw: object, origin: str) -> Provider:
    if not isinstance(raw, dict) or set(raw) - _PROVIDER_KEYS or not {"id", "base_url"} <= set(raw):
        raise ProviderError(f"a provider must have id and base_url, and only {', '.join(sorted(_PROVIDER_KEYS))}")
    provider_id = raw["id"]
    if not isinstance(provider_id, str) or not _ID.fullmatch(provider_id):
        raise ProviderError(f"provider id {provider_id!r} must be lowercase letters, digits, '.', '_' or '-'")
    shape = raw.get("shape", "openai-compatible")
    if shape not in SHAPES:
        raise ProviderError(f"provider {provider_id}: shape must be one of {', '.join(SHAPES)}")
    key_env = raw.get("key_env")
    if key_env is not None and (not isinstance(key_env, str) or not _ENV.fullmatch(key_env)):
        raise ProviderError(f"provider {provider_id}: key_env must be an environment variable name such as MY_API_KEY")
    name = raw.get("name", provider_id)
    if not isinstance(name, str) or not name.strip():
        raise ProviderError(f"provider {provider_id}: name must be text")
    return Provider(provider_id, name, check_base_url(raw["base_url"]), shape, key_env, origin)


def proofhouse_home() -> Path:
    override = os.environ.get("PROOFHOUSE_HOME")
    return Path(override) if override else Path.home() / ".proofhouse"


def user_path() -> Path:
    return proofhouse_home() / USER_FILE


def _read(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (OSError, ValueError) as exc:
        raise ProviderError(f"{path} is unreadable: {type(exc).__name__}") from None
    if not isinstance(data, dict) or data.get("schema") != PROVIDERS_SCHEMA:
        raise ProviderError(f"{path} must be a {PROVIDERS_SCHEMA} file")
    return data


def load_user() -> dict[str, Any]:
    """Your providers file as data ({"providers": [...], "prices": [...]}); empty when there is none."""
    try:
        data = _read(user_path())
    except FileNotFoundError:
        return {"schema": PROVIDERS_SCHEMA, "providers": [], "prices": [], "media_prices": [], "training_prices": []}
    for key in ("providers", "prices", "media_prices", "training_prices"):
        if not isinstance(data.setdefault(key, []), list):
            raise ProviderError(f"{user_path()}: {key} must be a list")
    unknown = set(data) - {"schema", "providers", "prices", "media_prices", "training_prices", "note"}
    if unknown:
        raise ProviderError(f"{user_path()}: unknown keys {', '.join(sorted(unknown))}")
    return data


def write_atomic(path: Path, content: str | bytes) -> None:
    """Write ``path`` in one step: a temporary file, then replace. A failed write leaves the old file and no leftover.

    Every writer gets its own temporary file, so two saves of the same file never share one.
    The new file keeps the old one's permission bits, so a settings file you locked down stays locked down;
    a brand-new file gets the normal create bits (0o666 minus your umask), as if it had been opened directly.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".proofhouse-tmp")
    temporary = Path(name)
    try:
        # Closed first: Windows cannot replace a file that is still open.
        os.close(handle)
        # POSIX: set the permission bits before any content goes in, so it is never briefly readable by others.
        # Windows has only a read-only flag, which would block writing and cleaning up the temporary file.
        if os.name != "nt":
            if path.exists():
                shutil.copymode(path, temporary)
            else:
                temporary.chmod(0o666 & ~_UMASK)
        if isinstance(content, bytes):
            temporary.write_bytes(content)
        else:
            temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def save_user(data: dict[str, Any]) -> Path:
    """Write your providers file in one step. A failed save leaves it unchanged and raises ProviderError."""
    path = user_path()
    try:
        write_atomic(path, json.dumps(data, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        raise ProviderError(f"could not save {path}: {exc}; it is unchanged") from None
    return path


def all_providers() -> dict[str, Provider]:
    """Shipped providers, then add-ons, then yours; a later one with the same id replaces an earlier one."""
    from . import addons

    shipped = _read(SHIPPED_PATH)
    found: dict[str, Provider] = {}
    for raw in shipped["providers"]:
        provider = parse_provider(raw, "shipped")
        found[provider.id] = provider
    for name, raw in addons.contributions("providers"):
        try:
            provider = parse_provider(raw, f"add-on {name}")
        except ProviderError:
            continue  # checked when the pack was installed; a package add-on's bad entry is skipped
        found[provider.id] = provider
    seen: set[str] = set()
    for raw in load_user()["providers"]:
        provider = parse_provider(raw, "yours")
        if provider.id in seen:
            raise ProviderError(f"{user_path()} lists provider {provider.id} twice")
        seen.add(provider.id)
        found[provider.id] = provider
    return found


def find(provider_id: str) -> Provider | None:
    return all_providers().get(provider_id)
