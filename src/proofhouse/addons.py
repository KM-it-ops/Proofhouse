"""Add-ons: other people's providers, media services, training services, tools and make kinds, with no change to Proofhouse.

Two ways in:
- a pack: a folder holding ``addon.json``, installed with ``proofhouse addons install <folder>``
  (copied to ``PROOFHOUSE_HOME/addons/<name>/``). Data only; nothing runs.
- a Python package you installed that declares an entry point in the group ``proofhouse.addons``.
  The entry point is a function that returns the same contents as ``addon.json``. It is code you
  chose to install, and it runs with your permissions when Proofhouse reads its add-ons.

Contents: ``providers``, ``media_providers``, ``training_services``, ``hosts``, ``deploy_targets`` (each
entry in the same shape as the matching file in ``PROOFHOUSE_HOME``) and ``make_kinds`` (a new ``make --kind``: a writer
prompt and a label for the judge). Order: shipped, then add-ons, then yours. Every request an add-on
adds still goes through the spend gate. A broken add-on is skipped and reported, never fatal.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any

from . import providers

ADDON_SCHEMA = "proofhouse.addon/v1"
ENTRY_POINT_GROUP = "proofhouse.addons"
SECTIONS = ("providers", "media_providers", "training_services", "hosts", "deploy_targets", "make_kinds")
_KIND = re.compile(r"[a-z][a-z0-9-]{1,39}")
_RESERVED_KINDS = {"prompt", "skill", "agent", "site", "app", "copy", "video", "launch"}


class AddonError(ValueError):
    """The add-on cannot be used as given."""


@dataclass
class Addon:
    name: str
    version: str
    description: str
    origin: str  # "pack" or "package"
    contents: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def counts(self) -> dict[str, int]:
        return {section: len(self.contents.get(section, [])) for section in SECTIONS if self.contents.get(section)}


def _check(raw: Any, where: str, origin: str) -> Addon:
    if not isinstance(raw, dict):
        raise AddonError(f"{where}: an add-on must be a JSON object")
    if raw.get("schema", ADDON_SCHEMA) != ADDON_SCHEMA:
        raise AddonError(f"{where}: schema must be {ADDON_SCHEMA}")
    name = raw.get("name")
    if not isinstance(name, str) or not providers._ID.fullmatch(name):
        raise AddonError(f"{where}: name must be lowercase letters, digits, '.', '_' or '-'")
    unknown = set(raw) - {"schema", "name", "version", "description", *SECTIONS}
    if unknown:
        raise AddonError(f"{where}: unknown keys {', '.join(sorted(unknown))}")
    contents: dict[str, list[dict[str, Any]]] = {}
    for section in SECTIONS:
        entries = raw.get(section, [])
        if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
            raise AddonError(f"{where}: {section} must be a list of objects")
        contents[section] = entries
    for kind in contents["make_kinds"]:
        if not isinstance(kind.get("kind"), str) or not _KIND.fullmatch(kind["kind"]) or kind["kind"] in _RESERVED_KINDS:
            raise AddonError(f"{where}: a make kind needs a new name of lowercase words joined by hyphens")
        if not isinstance(kind.get("write"), str) or len(kind["write"].strip()) < 20:
            raise AddonError(f"{where}: make kind {kind['kind']} needs a writer prompt (write)")
    return Addon(name, str(raw.get("version") or ""), str(raw.get("description") or ""), origin, contents)


def packs_dir() -> Path:
    return providers.proofhouse_home() / "addons"


def _packs() -> tuple[list[Addon], list[str]]:
    found, problems = [], []
    folder = packs_dir()
    for path in sorted(folder.glob("*/addon.json")) if folder.is_dir() else []:
        try:
            found.append(_check(json.loads(path.read_text(encoding="utf-8")), str(path), "pack"))
        except (OSError, ValueError) as exc:
            problems.append(f"{path.parent.name}: {exc}")
    return found, problems


def _packages() -> tuple[list[Addon], list[str]]:
    found, problems = [], []
    for point in sorted(entry_points(group=ENTRY_POINT_GROUP), key=lambda p: p.name):
        try:
            found.append(_check(point.load()(), f"package add-on {point.name}", "package"))
        except Exception as exc:  # noqa: BLE001 -- someone else's code; a broken add-on is skipped and reported
            problems.append(f"{point.name}: {type(exc).__name__}: {exc}"[:300])
    return found, problems


def all_addons() -> tuple[list[Addon], list[str]]:
    """Every add-on that loads, and a line for each one that does not."""
    packs, broken = _packs()
    packages, broken_packages = _packages()
    names: set[str] = set()
    kept = []
    for addon in packs + packages:
        if addon.name in names:
            broken.append(f"{addon.name}: two add-ons have this name; the second is skipped")
            continue
        names.add(addon.name)
        kept.append(addon)
    return kept, broken + broken_packages


def contributions(section: str) -> list[tuple[str, dict[str, Any]]]:
    """Entries every working add-on adds to one section, with the add-on's name."""
    return [(addon.name, entry) for addon in all_addons()[0] for entry in addon.contents.get(section, [])]


def make_kinds() -> dict[str, dict[str, Any]]:
    return {entry["kind"]: {**entry, "addon": name} for name, entry in contributions("make_kinds")}


def install(source: Path) -> Addon:
    """Check a pack (a folder with addon.json, or the JSON file itself) and copy it into PROOFHOUSE_HOME/addons/<name>/."""
    path = source / "addon.json" if source.is_dir() else source
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AddonError(f"{path} is unreadable: {type(exc).__name__}") from None
    addon = _check(raw, str(path), "pack")
    _check_entries(addon)
    target = packs_dir() / addon.name
    new_folder = not target.exists()
    try:
        providers.write_atomic(target / "addon.json", json.dumps(raw, indent=2) + "\n")
    except OSError:
        if new_folder:
            shutil.rmtree(target, ignore_errors=True)
        raise
    return addon


def _check_entries(addon: Addon) -> None:
    """Parse every entry with the parser its section uses, so a bad pack is refused before it is installed."""
    from . import deploy, hosts, media, train

    try:
        for entry in addon.contents["providers"]:
            providers.parse_provider(entry, f"add-on {addon.name}")
        for entry in addon.contents["media_providers"]:
            media._parse(entry, f"add-on {addon.name}")
        for entry in addon.contents["training_services"]:
            train._parse(entry, f"add-on {addon.name}")
        if addon.contents["hosts"]:
            hosts._check_hosts(addon.contents["hosts"], f"add-on {addon.name}")
        for entry in addon.contents["deploy_targets"]:
            deploy._check(entry, f"add-on {addon.name}")
    except (providers.ProviderError, media.MediaError, train.TrainError, hosts.HostError, deploy.DeployError) as exc:
        raise AddonError(f"{addon.name}: {exc}") from None


def remove(name: str) -> Path:
    target = packs_dir() / name
    if not providers._ID.fullmatch(name) or not (target / "addon.json").is_file():
        raise AddonError(f"no installed pack named {name!r}; see `proofhouse addons list`")
    shutil.rmtree(target)
    return target
