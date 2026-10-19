"""Keep the list of models and workspaces current as new ones are released: ``proofhouse models update``.

Two ways in, both data:

- **Each provider's own model list.** For every provider whose key is set, or that runs on this
  machine, one free ``GET {base_url}/models`` with that provider's key and no other, sent only to
  that provider's own host and never redirected. Every model id it names that Proofhouse has not
  seen before is recorded with the day it was first seen. An add-on provider that names another
  provider's key on a different host is not sent it unless you name that add-on with ``--provider``.
- **Official release notes.** ``data/release_sources.json`` lists the official pages where makers
  announce new models and workspaces (add or replace any in ``PROOFHOUSE_HOME/release_sources.json``).
  With a model set up, Proofhouse reads each page and has that model pick out what was released.
  Each read is one call through the spend gate, inside one spending limit for the whole update.
  A new model gets researched notes (``proofhouse models show <name>``) that cite the page they came
  from; a new workspace is recorded with what the page says about it. A page is read only when it ends on
  https at its own site. Notes picked out of a page are not put into prompts until you review them.

What it found is kept in ``PROOFHOUSE_HOME/catalog/catalog.json`` and shown by ``proofhouse models list``,
which also says when the last update ran. Nothing a page or a model says changes a provider, a key or
where Proofhouse writes files.
"""

from __future__ import annotations

import html
import json
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from . import providers
from .optimize import model_notes
from .optimize.registry import find_model, load_registry, normalize_model_name

CATALOG_SCHEMA = "proofhouse.catalog/v1"
SOURCES_SCHEMA = "proofhouse.release-sources/v1"
SOURCES_PATH = Path(__file__).resolve().parent / "data" / "release_sources.json"
# The update is due again after this many days; ``proofhouse models list`` says so.
DUE_AFTER_DAYS = 7
PAGE_CHARS = 60000
MAX_BYTES = 5_000_000  # the most of any one answer that is read
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_SOURCE_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
_MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}")

# ``get(url, headers, follow_redirects) -> (status, final_url, text)``; swapped in tests.
Get = Callable[[str, dict[str, str], bool], tuple[int, str, str]]

_READ = (
    "You read one official page where a company announces AI models and tools. List every AI model and every AI "
    "workspace (an app, editor, terminal tool, agent or cloud teammate that people work in with AI) that the page "
    "says was released, launched, or made available. Use only what the page says; leave a field empty when the page "
    "does not say it. Reply with JSON only: "
    '{"models": [{"id": "<the exact model id used in API calls, if the page gives one>", "name": "<the model\'s '
    'name>", "maker": "<company>", "released": "<YYYY-MM-DD or empty>", "summary": "<what it is for, its context '
    'size, output limit and prices exactly as the page gives them>"}], '
    '"workspaces": [{"name": "<the workspace\'s name>", "maker": "<company>", "released": "<YYYY-MM-DD or empty>", '
    '"summary": "<what it is and what it connects to, as the page says>", "settings": "<where the page says it keeps '
    'agents, rules or MCP servers, or empty>"}]}\n\n'
    "Page address: {url}\n\nPAGE TEXT:\n{text}"
)


class CatalogError(ValueError):
    """The update cannot start; nothing was sent and nothing was written."""


@dataclass(frozen=True, slots=True)
class Source:
    id: str
    name: str
    url: str
    covers: tuple[str, ...]
    checked_at: str | None  # when this address was last confirmed by hand; None means "to check"

    @property
    def host(self) -> str:
        return (urlparse(self.url).hostname or "").lower()


@dataclass
class UpdateResult:
    checked_at: str
    new_models: list[dict[str, Any]] = field(default_factory=list)
    new_workspaces: list[dict[str, Any]] = field(default_factory=list)
    listed: dict[str, str] = field(default_factory=dict)  # provider id -> "N models" or why it could not be listed
    read: dict[str, str] = field(default_factory=dict)  # source id -> "N found" or why it could not be read
    spent_usd: Decimal = Decimal(0)
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "checked_at": self.checked_at,
            "new_models": self.new_models,
            "new_workspaces": self.new_workspaces,
            "listed": self.listed,
            "read": self.read,
            "spent_usd_estimated": format(self.spent_usd, "f"),
            "note": self.note,
            "catalog": str(catalog_path()),
        }


# --- sources and the catalog file --------------------------------------------------------------


def _parse_sources(data: Any, where: str) -> list[Source]:
    if not isinstance(data, dict) or data.get("schema") != SOURCES_SCHEMA or not isinstance(data.get("sources"), list):
        raise CatalogError(f"{where} must be a {SOURCES_SCHEMA} file with a sources list")
    found: list[Source] = []
    for raw in data["sources"]:
        if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or not _SOURCE_ID.fullmatch(raw["id"]):
            raise CatalogError(f"{where}: every source needs an id of lowercase words joined by hyphens")
        url = raw.get("url")
        parsed = urlparse(url) if isinstance(url, str) else None
        if parsed is None or parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise CatalogError(f"{where}: source {raw['id']} needs an https address")
        covers = raw.get("covers", ["models"])
        if not isinstance(covers, list) or not covers or any(c not in ("models", "workspaces") for c in covers):
            raise CatalogError(f"{where}: source {raw['id']} covers models, workspaces or both")
        checked = raw.get("checked_at")
        found.append(Source(raw["id"], str(raw.get("name", raw["id"])), url, tuple(covers),
                            checked if isinstance(checked, str) else None))
    return found


def sources() -> list[Source]:
    """The shipped release-note pages, then yours (``PROOFHOUSE_HOME/release_sources.json``); yours replace by id."""
    found = {s.id: s for s in _parse_sources(json.loads(SOURCES_PATH.read_text(encoding="utf-8")), str(SOURCES_PATH))}
    mine = providers.proofhouse_home() / "release_sources.json"
    if mine.is_file():
        try:
            data = json.loads(mine.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CatalogError(f"{mine} is unreadable: {type(exc).__name__}") from None
        found.update({s.id: s for s in _parse_sources(data, str(mine))})
    return list(found.values())


def catalog_path() -> Path:
    return providers.proofhouse_home() / "catalog" / "catalog.json"


def load() -> dict[str, Any]:
    """What earlier updates found. A file that cannot be read is kept aside and the catalog starts again."""
    path = catalog_path()
    empty: dict[str, Any] = {"schema": CATALOG_SCHEMA, "checked_at": None, "models": {}, "workspaces": {}}
    if not path.is_file():
        return empty
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != CATALOG_SCHEMA or not isinstance(data.get("models"), dict) \
                or not isinstance(data.get("workspaces"), dict):
            raise ValueError("not a catalog")
        return data
    except (OSError, ValueError, AttributeError):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path.replace(path.with_name(f"catalog.json.unreadable-{stamp}"))
        return empty


def due(data: dict[str, Any] | None = None, *, today: date | None = None) -> str | None:
    """A plain reminder when the update has never run or is older than ``DUE_AFTER_DAYS``; else ``None``."""
    checked = (data if data is not None else load()).get("checked_at")
    if not isinstance(checked, str):
        return "the model list has never been updated here; run `proofhouse models update`"
    age = ((today or date.today()) - date.fromisoformat(checked[:10])).days
    if age >= DUE_AFTER_DAYS:
        return f"the model list was last updated {age} days ago; run `proofhouse models update`"
    return None


# --- the network ---------------------------------------------------------------------------------


def _httpx_get(url: str, headers: dict[str, str], follow_redirects: bool) -> tuple[int, str, str]:
    """One GET; the body is read only up to ``MAX_BYTES``, so a huge page cannot fill memory."""
    try:
        import httpx
    except ImportError:
        raise ModuleNotFoundError("httpx") from None
    with httpx.Client(timeout=60.0, follow_redirects=follow_redirects) as client:
        with client.stream("GET", url, headers=headers) as reply:
            body = bytearray()
            for chunk in reply.iter_bytes():
                body.extend(chunk[: MAX_BYTES - len(body)])
                if len(body) >= MAX_BYTES:
                    break
            return reply.status_code, str(reply.url), body.decode(reply.encoding or "utf-8", errors="replace")


def _same_site(final_url: str, expected: str) -> bool:
    """The page ended on https at the source's own host, a host under it, or the one it sits under.

    docs.x.ai may end on x.ai or www.docs.x.ai, never on another-site.github.io next to it.
    """
    parsed = urlparse(final_url)
    host, expected = (parsed.hostname or "").lower(), expected.lower()
    if parsed.scheme != "https" or not host:
        return False
    return host == expected or host.endswith("." + expected) or ("." in host and expected.endswith("." + host))


def page_text(raw: str) -> str:
    """The readable text of an HTML page (scripts, styles and tags removed), cut to ``PAGE_CHARS``."""
    text = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()[:PAGE_CHARS]


def list_provider(profile: providers.Provider, get: Get) -> list[str]:
    """Model ids the provider's own ``/models`` list names. Raises ``CatalogError`` with the reason it could not."""
    url = profile.base_url.rstrip("/") + "/models"
    if (urlparse(url).hostname or "").lower() != profile.host:
        raise CatalogError(f"the address {url!r} does not match provider {profile.id}")
    headers = {"Accept": "application/json"}
    secret = os.environ.get(profile.key_env) if profile.key_env else None
    if profile.key_env and not secret and not profile.local:
        raise CatalogError(f"{profile.key_env} is not set")
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
    try:
        status, _final, body = get(url, headers, False)  # never redirected: the key goes to this host only
    except ModuleNotFoundError:
        raise CatalogError("httpx is not installed (pip install 'proofhouse[live]')") from None
    except Exception as exc:  # noqa: BLE001 -- the key must not show in any message
        raise CatalogError(f"could not reach it ({type(exc).__name__})") from None
    if not 200 <= status < 300:
        raise CatalogError(f"it answered HTTP {status}")
    try:
        data = json.loads(body)
    except ValueError:
        raise CatalogError("its answer was not JSON") from None
    rows = data.get("data") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise CatalogError("its answer had no list of models")
    ids = [row.get("id") if isinstance(row, dict) else row for row in rows]
    return sorted({i for i in ids if isinstance(i, str) and _MODEL_ID.fullmatch(i)})


# --- what is already known -----------------------------------------------------------------------


def _known(name: str, data: dict[str, Any], reg: Any) -> bool:
    key = normalize_model_name(name)
    return not key or key in data["models"] or find_model(name, reg) is not None \
        or (model_notes.cache_dir() / f"{key}.json").is_file()


def _workspace_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:64]


def _known_workspace(name: str, data: dict[str, Any]) -> bool:
    from . import hosts

    key = _workspace_key(name)
    if not key or key in data["workspaces"]:
        return True
    try:
        known = hosts.all_hosts()
    except hosts.HostError:
        known = {}
    return any(key in (h, _workspace_key(str(spec.get("name", h)))) for h, spec in known.items())


def _text(value: Any, limit: int) -> str:
    """One line of plain text: whitespace collapsed, control characters (terminal escapes) removed, cut."""
    if not isinstance(value, str):
        return ""
    return _CONTROL.sub("", re.sub(r"\s+", " ", value)).strip()[:limit]


def _borrowed_key(profile: providers.Provider, everyone: list[providers.Provider]) -> providers.Provider | None:
    """The shipped or user provider on another host whose key an add-on provider names, if any.

    The automatic sweep never sends that key to the add-on's host. Name the add-on with ``--provider``
    to use it on purpose.
    """
    if not profile.key_env or profile.origin in ("shipped", "yours"):
        return None
    return next((other for other in everyone if other.key_env == profile.key_env and other.host != profile.host
                 and other.origin in ("shipped", "yours")), None)


def _parse_reading(answer: str | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    match = re.search(r"\{.*\}", answer or "", flags=re.S)
    try:
        data = json.loads(match.group(0)) if match else None
    except ValueError:
        data = None
    if not isinstance(data, dict):
        raise CatalogError("the model's answer was not the JSON asked for")
    models = [m for m in data.get("models", []) if isinstance(m, dict)] if isinstance(data.get("models"), list) else []
    spaces = [w for w in data.get("workspaces", []) if isinstance(w, dict)] \
        if isinstance(data.get("workspaces"), list) else []
    return models, spaces


# --- the update ----------------------------------------------------------------------------------


def update(
    *,
    provider_id: str | None = None,
    model: str | None = None,
    max_cost_usd: str | None = None,
    only: list[str] | None = None,
    get: Get | None = None,
    transport: Any = None,
    max_output_tokens: int = 4096,
) -> UpdateResult:
    """List every reachable provider's models, then (with a model) read the release notes; record what is new."""
    from . import live, make

    get = get or _httpx_get
    reader = None
    if provider_id or model:
        if not (provider_id and model):
            raise CatalogError("name both --provider and --model to read release notes, or neither")
        reader = providers.find(provider_id)
        if reader is None:
            raise CatalogError(f"no provider named {provider_id!r}; see `proofhouse providers list`")
        if max_cost_usd is None and not reader.local:
            raise CatalogError("name a spending limit for the whole update (--max-cost-usd)")
        if max_cost_usd is not None:
            try:
                limit = Decimal(max_cost_usd)
            except (InvalidOperation, ValueError, TypeError):
                limit = Decimal("NaN")
            if not limit.is_finite() or limit < 0:
                raise CatalogError(f"--max-cost-usd must be a plain amount of dollars, 0 or more, not {max_cost_usd!r}")
    picked = sources()
    if only:
        unknown = sorted(set(only) - {s.id for s in picked})
        if unknown:
            raise CatalogError(f"no release source named {', '.join(unknown)}; known: {', '.join(s.id for s in picked)}")
        picked = [s for s in picked if s.id in only]

    data = load()
    reg = load_registry()
    now = datetime.now(timezone.utc)
    stamp, today = now.strftime("%Y-%m-%dT%H:%M:%SZ"), now.date().isoformat()
    result = UpdateResult(stamp)

    # 1. Each provider's own list: free, its own key only, its own host only.
    everyone = list(providers.all_providers().values())
    for profile in everyone:
        if profile.key_env and not os.environ.get(profile.key_env) and not profile.local:
            continue
        owner = _borrowed_key(profile, everyone) if profile.id != provider_id else None
        if owner is not None:
            result.listed[profile.id] = (f"not listed: it names {profile.key_env}, the key of {owner.id}, but runs on "
                                         f"{profile.host}; name it with --provider to use it on purpose")
            continue
        try:
            ids = list_provider(profile, get)
        except CatalogError as exc:
            result.listed[profile.id] = f"not listed: {exc}"
            continue
        result.listed[profile.id] = f"{len(ids)} models"
        for model_id in ids:
            key = normalize_model_name(model_id)
            if _known(model_id, data, reg):
                entry = data["models"].get(key)
                if entry is not None and profile.id not in entry["listed_by"]:
                    entry["listed_by"].append(profile.id)
                continue
            entry = {"id": model_id, "name": model_id, "maker": None, "first_seen": today, "listed_by": [profile.id],
                     "sources": [], "summary": None}
            data["models"][key] = entry
            result.new_models.append(entry)

    # 2. Official release notes, read by the model you picked, each call inside one limit.
    if reader is None:
        result.note = ("read the official release notes too by naming a model: "
                       "proofhouse models update --provider P --model M --max-cost-usd X")
    else:
        budget = make.Budget(max_cost_usd, reader.local)
        for source in picked:
            try:
                status, final, raw = get(source.url, {"Accept": "text/html"}, True)
            except ModuleNotFoundError:
                result.read[source.id] = "not read: httpx is not installed (pip install 'proofhouse[live]')"
                continue
            except Exception as exc:  # noqa: BLE001
                result.read[source.id] = f"not read: could not reach it ({type(exc).__name__})"
                continue
            if not 200 <= status < 300:
                result.read[source.id] = f"not read: it answered HTTP {status}"
                continue
            if not _same_site(final, source.host):
                result.read[source.id] = (f"not read: it moved to {urlparse(final).hostname}, outside {source.host}; "
                                          f"if the page really moved, give its new address in "
                                          f"{providers.proofhouse_home() / 'release_sources.json'}")
                continue
            text = page_text(raw)
            if len(text) < 200:
                result.read[source.id] = "not read: the page had no readable text"
                continue
            reply = live.run_prompt(
                reader.id, model, prompt=_READ.replace("{url}", source.url).replace("{text}", text),
                max_output_tokens=max_output_tokens, max_cost_usd=budget.for_next_call(), transport=transport,
            )
            budget.charge(reply)
            if reply.status != "success":
                result.read[source.id] = f"not read: {reply.message or reply.code}"
                continue
            try:
                models, spaces = _parse_reading(reply.output_text)
            except CatalogError as exc:
                result.read[source.id] = f"not read: {exc}"
                continue
            result.read[source.id] = f"{len(models)} models, {len(spaces)} workspaces on the page"
            read_by = f"{reader.id}/{model}"
            if "models" in source.covers:
                _add_models(models, source, read_by, today, data, reg, result)
            if "workspaces" in source.covers:
                _add_workspaces(spaces, source, read_by, today, data, result)
        result.spent_usd = budget.spent

    data["checked_at"] = stamp
    providers.write_atomic(catalog_path(), json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return result


def _add_models(found: list[dict[str, Any]], source: Source, read_by: str, today: str, data: dict[str, Any],
                reg: Any, result: UpdateResult) -> None:
    for raw in found:
        name = _text(raw.get("name"), 120)
        model_id = _text(raw.get("id"), 128)
        model_id = model_id if _MODEL_ID.fullmatch(model_id) else ""
        label = model_id or name
        key = normalize_model_name(label)
        summary = _text(raw.get("summary"), 1500)
        if not key:
            continue
        listed = data["models"].get(key)
        if listed is not None and not listed.get("summary") and summary:
            listed.update(name=name or listed["name"], maker=_text(raw.get("maker"), 80) or None, summary=summary,
                          sources=[source.url])  # a provider listed it before; the page now says what it is
            _write_notes(label, listed, source, read_by, raw)
            continue
        if _known(label, data, reg) or (name and _known(name, data, reg)):
            continue
        entry = {"id": model_id or None, "name": name or model_id, "maker": _text(raw.get("maker"), 80) or None,
                 "first_seen": today, "listed_by": [], "sources": [source.url], "summary": summary or None,
                 "released": _text(raw.get("released"), 10) or None}
        data["models"][key] = entry
        result.new_models.append(entry)
        if summary:
            _write_notes(label, entry, source, read_by, raw)


def _write_notes(label: str, entry: dict[str, Any], source: Source, read_by: str, raw: dict[str, Any]) -> None:
    released = _text(raw.get("released"), 10)
    notes = (f"{entry['summary']} (From {source.name}{', released ' + released if released else ''}; "
             f"picked out of the page by {read_by}; not reviewed.)")
    model_notes.resolve_model_notes(label, researcher=lambda _name: (notes, [source.url]), extracted_by=read_by)


def _add_workspaces(found: list[dict[str, Any]], source: Source, read_by: str, today: str, data: dict[str, Any],
                    result: UpdateResult) -> None:
    for raw in found:
        name = _text(raw.get("name"), 80)
        if not name or _known_workspace(name, data):
            continue
        entry = {"name": name, "maker": _text(raw.get("maker"), 80) or None, "first_seen": today,
                 "released": _text(raw.get("released"), 10) or None, "summary": _text(raw.get("summary"), 1500) or None,
                 "settings": _text(raw.get("settings"), 400) or None, "sources": [source.url], "read_by": read_by,
                 "next": (f"to install agents, rules or MCP servers into {name}, add where it keeps them to "
                          f"{providers.proofhouse_home() / 'hosts.json'} (`proofhouse hosts list` shows the shape)")}
        data["workspaces"][_workspace_key(name)] = entry
        result.new_workspaces.append(entry)
