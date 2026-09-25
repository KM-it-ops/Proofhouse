"""Local model-notes cache and provenance resolution.

Answers "where did this profile come from, how old is it, what is its
canonical id" for ``builtin``, ``cached``, ``researched``, ``user_supplied``
and ``fallback`` notes.

``verification`` is separate from ``source`` (T07, review F05): notes with
no sources are ``unverified`` whatever their origin, and a date alone
(``verified_at``) records when someone last looked at them, not that anyone
checked them against vendor documentation. Notes supplied from a local file
are ``user_supplied`` and never dated. The cache lives under ``PROOFHOUSE_HOME`` (default ``~/.proofhouse``)
as ``model-notes/<normalized-key>.json``.

Stdlib only; nothing here opens a network connection. ``resolve_model_notes``
accepts an injectable ``researcher`` callable; this package never constructs
one and the CLI never passes one.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from . import registry
from .registry import ModelEntry, Registry, age_days, find_model, is_stale, load_registry, normalize_model_name

CACHE_SCHEMA = "proofhouse.model-notes/v0"
SOURCE_BUILTIN = "builtin"
SOURCE_CACHED = "cached"
SOURCE_RESEARCHED = "researched"
SOURCE_FALLBACK = "fallback"
SOURCE_USER_SUPPLIED = "user_supplied"
FALLBACK_ID = "other"

VERIFICATION_UNVERIFIED = "unverified"
VERIFICATION_SOURCED = "sourced"
VERIFICATION_REVIEWED = "reviewed"

Researcher = Callable[[str], tuple[str, list[str]]]


@dataclass(frozen=True)
class ResolvedNotes:
    entered_name: str
    canonical_id: str
    display_name: str
    provider: str | None
    tier: str
    source: str
    verified_at: str | None
    stale: bool
    age_days: int | None
    stale_after_days: int
    sources: tuple[str, ...]
    provenance: str | None
    notes: str
    verification: str = VERIFICATION_UNVERIFIED

    def to_dict(self) -> dict:
        return {
            "entered_name": self.entered_name,
            "canonical_id": self.canonical_id,
            "display_name": self.display_name,
            "provider": self.provider,
            "tier": self.tier,
            "source": self.source,
            "verified_at": self.verified_at,
            "stale": self.stale,
            "age_days": self.age_days,
            "stale_after_days": self.stale_after_days,
            "sources": list(self.sources),
            "provenance": self.provenance,
            "notes": self.notes,
            "verification": self.verification,
        }


def verification_for(sources: tuple[str, ...] | list[str], reviewed_by: str | None = None) -> str:
    """``reviewed`` needs sources and a named reviewer; ``sourced`` needs sources; else ``unverified``."""
    if not sources:
        return VERIFICATION_UNVERIFIED
    return VERIFICATION_REVIEWED if reviewed_by else VERIFICATION_SOURCED


def proofhouse_home() -> Path:
    override = os.environ.get("PROOFHOUSE_HOME")
    if override:
        return Path(override)
    return Path.home() / ".proofhouse"


def cache_dir() -> Path:
    return proofhouse_home() / "model-notes"


def cache_key(name: str, reg: Registry | None = None) -> str:
    """Cache key: the builtin id when the name resolves to one, else the normalised name."""
    normalized = normalize_model_name(name)
    if not normalized:
        raise ValueError(f"model name {name!r} is empty after normalisation")
    builtin = find_model(name, reg or load_registry())
    return builtin.id if builtin else normalized


def _cache_file(key: str) -> Path:
    return cache_dir() / f"{key}.json"


def _read_cache(key: str) -> dict | None:
    path = _cache_file(key)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_cache(key: str, entry: dict) -> Path:
    directory = cache_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = _cache_file(key)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, indent=2, sort_keys=True, ensure_ascii=False))
        handle.write("\n")
    return path


def _freshness(verified_at: str | None, reg: Registry) -> tuple[bool, int | None]:
    now = registry.today()
    stale = is_stale(verified_at, today=now, stale_after_days=reg.stale_after_days)
    return stale, age_days(verified_at, today=now)


def _from_builtin(entered_name: str, entry: ModelEntry, reg: Registry) -> ResolvedNotes:
    stale, age = _freshness(entry.verified_at, reg)
    return ResolvedNotes(
        entered_name=entered_name,
        canonical_id=entry.id,
        display_name=entry.display_name,
        provider=entry.provider,
        tier=entry.tier,
        source=SOURCE_BUILTIN,
        verified_at=entry.verified_at,
        stale=stale,
        age_days=age,
        stale_after_days=reg.stale_after_days,
        sources=entry.sources,
        provenance=None,
        notes=entry.notes,
        verification=verification_for(entry.sources),
    )


def _from_cache(
    entered_name: str,
    cached: dict,
    builtin: ModelEntry | None,
    reg: Registry,
    *,
    source: str,
) -> ResolvedNotes:
    verified_at = cached.get("verified_at")
    stale, age = _freshness(verified_at, reg)
    return ResolvedNotes(
        entered_name=entered_name,
        canonical_id=builtin.id if builtin else cached["canonical_id"],
        display_name=builtin.display_name if builtin else cached["entered_name"],
        provider=builtin.provider if builtin else None,
        tier=builtin.tier if builtin else SOURCE_CACHED,
        source=source,
        verified_at=verified_at,
        stale=stale,
        age_days=age,
        stale_after_days=reg.stale_after_days,
        sources=tuple(cached.get("sources") or ()),
        provenance=cached.get("provenance"),
        notes=cached["notes"],
        verification=verification_for(tuple(cached.get("sources") or ()), cached.get("reviewed_by")),
    )


def _fallback(entered_name: str, reg: Registry) -> ResolvedNotes:
    other = find_model(FALLBACK_ID, reg)
    if other is None:
        raise RuntimeError("registry has no 'other' entry")
    return ResolvedNotes(
        entered_name=entered_name,
        canonical_id=normalize_model_name(entered_name),
        display_name=entered_name,
        provider=None,
        tier=other.tier,
        source=SOURCE_FALLBACK,
        verified_at=None,
        stale=False,
        age_days=None,
        stale_after_days=reg.stale_after_days,
        sources=(),
        provenance=None,
        notes=other.notes,
    )


def _cache_is_newer_or_tied(cached: dict, builtin: ModelEntry) -> bool:
    cached_at = cached.get("verified_at")
    if cached_at is None:
        return builtin.verified_at is None
    if builtin.verified_at is None:
        return True
    return date.fromisoformat(cached_at) >= date.fromisoformat(builtin.verified_at)


def resolve_model_notes(name: str, *, researcher: Researcher | None = None) -> ResolvedNotes:
    """Resolve notes for ``name``: cache/builtin by freshness, else researcher, else fallback."""
    reg = load_registry()
    key = cache_key(name, reg)
    builtin = find_model(name, reg)
    cached = _read_cache(key)
    if cached is not None and builtin is not None:
        if _cache_is_newer_or_tied(cached, builtin):
            return _from_cache(name, cached, builtin, reg, source=SOURCE_CACHED)
        return _from_builtin(name, builtin, reg)
    if cached is not None:
        return _from_cache(name, cached, None, reg, source=SOURCE_CACHED)
    if builtin is not None:
        return _from_builtin(name, builtin, reg)
    if researcher is not None:
        notes, sources = researcher(name)
        entry = _entry(name, key, notes, sources, registry.today().isoformat(), SOURCE_RESEARCHED, "researcher")
        _write_cache(key, entry)
        return _from_cache(name, entry, None, reg, source=SOURCE_RESEARCHED)
    return _fallback(name, reg)


def _entry(
    entered_name: str,
    key: str,
    notes: str,
    sources: list[str],
    verified_at: str,
    source: str,
    provenance: str | None,
) -> dict:
    return {
        "schema": CACHE_SCHEMA,
        "entered_name": entered_name,
        "canonical_id": key,
        "notes": notes,
        "source": source,
        "verified_at": verified_at,
        "sources": list(sources),
        "provenance": provenance,
    }


def remember(
    name: str,
    notes: str,
    *,
    sources: list[str],
    verified_at: str | None = None,
    provenance: str | None = None,
) -> Path:
    """Store (or overwrite, which is how a refresh works) the user's own notes for ``name``."""
    reg = load_registry()
    key = cache_key(name, reg)
    stamped = verified_at or registry.today().isoformat()
    date.fromisoformat(stamped)
    return _write_cache(key, _entry(name, key, notes, sources, stamped, SOURCE_CACHED, provenance))


def forget(name: str) -> bool:
    path = _cache_file(cache_key(name))
    if not path.is_file():
        return False
    path.unlink()
    return True


def list_builtin() -> tuple[ResolvedNotes, ...]:
    reg = load_registry()
    return tuple(_from_builtin(entry.display_name, entry, reg) for entry in reg.models)


def list_cached() -> tuple[ResolvedNotes, ...]:
    directory = cache_dir()
    if not directory.is_dir():
        return ()
    reg = load_registry()
    resolved: list[ResolvedNotes] = []
    for path in sorted(directory.glob("*.json")):
        cached = json.loads(path.read_text(encoding="utf-8"))
        builtin = find_model(cached["canonical_id"], reg)
        resolved.append(_from_cache(cached["entered_name"], cached, builtin, reg, source=SOURCE_CACHED))
    return tuple(resolved)
