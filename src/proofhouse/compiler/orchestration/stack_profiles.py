"""Stack profiles. Fail closed when registries are missing. Do not invent sources."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

ProfileId = Literal[
    "SP-static",
    "SP-react-motion",
    "SP-react-3d",
    "SP-react-data",
    "SP-next-app",
]


class RegistryMissingError(FileNotFoundError):
    """Ship-walk registries are required; missing files fail closed."""


@dataclass(frozen=True)
class MigrationDelta:
    source_id: str
    extra_deps: list[str]
    extra_build_steps: int
    adaptation_required: bool


@dataclass(frozen=True)
class Registries:
    profiles: dict[str, dict[str, Any]]
    sources: dict[str, dict[str, Any]]


def load_registries(profiles_path: Path, sources_path: Path) -> Registries:
    if not profiles_path.is_file() or not sources_path.is_file():
        raise RegistryMissingError("stack-profiles.json and component-registry.json are required")
    profiles_raw = json.loads(profiles_path.read_text(encoding="utf-8"))
    sources_raw = json.loads(sources_path.read_text(encoding="utf-8"))
    profiles = {item["id"]: item for item in profiles_raw.get("profiles", [])}
    sources = {item["id"]: item for item in sources_raw.get("sources", [])}
    return Registries(profiles=profiles, sources=sources)


def bind_profile(concept: str) -> ProfileId:
    text = concept.lower()
    if any(token in text for token in ("auth", "database", "next app", "saas product")):
        return "SP-next-app"
    if any(token in text for token in ("dashboard", "charts", "soc")):
        return "SP-react-data"
    if any(token in text for token in ("immersive", "hero-led", "hero led", "3d", "portfolio")):
        return "SP-react-3d"
    if any(token in text for token in ("motion", "marketing")):
        return "SP-react-motion"
    return "SP-static"


def source_delta(regs: Registries, *, profile_id: str, source_id: str) -> MigrationDelta:
    profile = regs.profiles.get(profile_id, {})
    permitted = set(profile.get("permitted_sources") or [])
    source = regs.sources.get(source_id)
    if source is not None and source_id in permitted and profile_id in set(source.get("stack_profiles") or []):
        return MigrationDelta(source_id, [], 0, False)
    if source is None:
        return MigrationDelta(source_id, [source_id], 1, True)
    deps = [str(item) for item in (source.get("dependencies") or [])]
    extra_steps = 0 if profile_id == "SP-static" and not deps else 1
    if extra_steps == 0:
        extra_steps = 1
    return MigrationDelta(
        source_id,
        deps,
        extra_steps,
        bool(source.get("adaptation_required", True)),
    )
