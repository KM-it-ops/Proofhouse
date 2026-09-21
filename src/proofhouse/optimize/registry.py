"""Reviewed model registry: load, normalise names, look up entries, judge staleness.

Pure functions. The only I/O is reading ``data/model_registry.json``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
REGISTRY_PATH = DATA_DIR / "model_registry.json"
PACKAGE_FRAMEWORK_PATH = DATA_DIR / "proofhouse-framework.json"
PACKAGE_BUNDLE_PATH = DATA_DIR / "proofhouse.skill"

_PROVIDER_PREFIX = re.compile(r"^(anthropic|openai|google|xai|x-ai|meta|moonshot|moonshotai)[/:]\s*")
_SEPARATORS = re.compile(r"[\s_.]+")
_NOT_ALLOWED = re.compile(r"[^a-z0-9-]")
_DASHES = re.compile(r"-+")


@dataclass(frozen=True)
class ModelEntry:
    id: str
    display_name: str
    trigger_label: str
    provider: str | None
    tier: str
    api_id: str | None
    aliases: tuple[str, ...]
    verified_at: str | None
    sources: tuple[str, ...]
    notes: str


@dataclass(frozen=True)
class Registry:
    schema: str
    framework_version: str
    stale_after_days: int
    models: tuple[ModelEntry, ...]


def _entry_from_json(raw: dict) -> ModelEntry:
    return ModelEntry(
        id=raw["id"],
        display_name=raw["display_name"],
        trigger_label=raw["trigger_label"],
        provider=raw["provider"],
        tier=raw["tier"],
        api_id=raw["api_id"],
        aliases=tuple(raw["aliases"]),
        verified_at=raw["verified_at"],
        sources=tuple(raw["sources"]),
        notes=raw["notes"],
    )


def load_registry(path: Path = REGISTRY_PATH) -> Registry:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Registry(
        schema=data["schema"],
        framework_version=data["frameworkVersion"],
        stale_after_days=int(data["staleAfterDays"]),
        models=tuple(_entry_from_json(raw) for raw in data["models"]),
    )


def normalize_model_name(name: str) -> str:
    text = name.lower().strip()
    text = _PROVIDER_PREFIX.sub("", text, count=1)
    text = _SEPARATORS.sub("-", text)
    text = _NOT_ALLOWED.sub("", text)
    text = _DASHES.sub("-", text)
    return text.strip("-")


def lookup_keys(entry: ModelEntry) -> frozenset[str]:
    keys = {normalize_model_name(entry.id), normalize_model_name(entry.display_name)}
    if entry.api_id:
        keys.add(normalize_model_name(entry.api_id))
    keys.update(normalize_model_name(alias) for alias in entry.aliases)
    return frozenset(keys)


def find_model(name: str, registry: Registry | None = None) -> ModelEntry | None:
    key = normalize_model_name(name)
    if not key:
        return None
    registry = registry or load_registry()
    for entry in registry.models:
        if key in lookup_keys(entry):
            return entry
    return None


def today() -> date:
    return date.today()


def age_days(verified_at: str | None, *, today: date) -> int | None:
    if verified_at is None:
        return None
    return (today - date.fromisoformat(verified_at)).days


def is_stale(verified_at: str | None, *, today: date, stale_after_days: int) -> bool:
    age = age_days(verified_at, today=today)
    if age is None:
        return False
    return age >= stale_after_days
