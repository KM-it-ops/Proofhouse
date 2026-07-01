from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_LOADOUTS_PATH = Path("loadouts") / "legendary_loadouts.json"


@dataclass(frozen=True)
class PromptLoadout:
    id: str
    name: str
    role: str
    tagline: str
    rank: str
    target_surfaces: list[str]
    primary: str
    mode: str
    modules: list[str]
    eval_packs: list[str]
    rubrics: list[str]
    full_blitz: list[str]
    exports: list[str]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PromptLoadout":
        return cls(
            id=_required_str(value, "id"),
            name=_required_str(value, "name"),
            role=_required_str(value, "role"),
            tagline=_required_str(value, "tagline"),
            rank=_required_str(value, "rank"),
            target_surfaces=_required_str_list(value, "target_surfaces"),
            primary=_required_str(value, "primary"),
            mode=_required_str(value, "mode"),
            modules=_required_str_list(value, "modules"),
            eval_packs=_required_str_list(value, "eval_packs"),
            rubrics=_required_str_list(value, "rubrics"),
            full_blitz=_required_str_list(value, "full_blitz"),
            exports=_required_str_list(value, "exports"),
        )


def load_legendary_loadouts(path: str | Path = DEFAULT_LOADOUTS_PATH) -> list[PromptLoadout]:
    data_path = Path(path)
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("loadout manifest must contain a list")
    return [PromptLoadout.from_dict(item) for item in raw]


def find_loadout(loadout_id: str, path: str | Path = DEFAULT_LOADOUTS_PATH) -> PromptLoadout:
    for loadout in load_legendary_loadouts(path):
        if loadout.id == loadout_id:
            return loadout
    raise ValueError(f"Unknown loadout id: {loadout_id}")


def compile_loadout(loadout_id: str, repo_root: str | Path = ".", path: str | Path = DEFAULT_LOADOUTS_PATH) -> str:
    root = Path(repo_root)
    loadout = find_loadout(loadout_id, root / path if not Path(path).is_absolute() else path)
    sections = [
        "# PromptRig Loadout",
        "",
        f"Name: {loadout.name}",
        f"Role: {loadout.role}",
        f"Rank: {loadout.rank}",
        f"Target Surfaces: {', '.join(loadout.target_surfaces)}",
        "",
        "## Full Blitz Sequence",
        "",
        *[f"{index}. {step}" for index, step in enumerate(loadout.full_blitz, start=1)],
        "",
        "## Exports",
        "",
        *[f"- {export}" for export in loadout.exports],
        "",
    ]

    prompt_paths = [loadout.primary, loadout.mode, *loadout.modules]
    for prompt_path in prompt_paths:
        source = root / prompt_path
        sections.extend(
            [
                f"## Source: {prompt_path}",
                "",
                source.read_text(encoding="utf-8").strip(),
                "",
            ]
        )
    return "\n".join(sections).rstrip() + "\n"


def _required_str(value: dict[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"loadout field {key} must be a non-empty string")
    return item


def _required_str_list(value: dict[str, Any], key: str) -> list[str]:
    item = value.get(key)
    if not isinstance(item, list) or not item:
        raise ValueError(f"loadout field {key} must be a non-empty list")
    if not all(isinstance(entry, str) and entry.strip() for entry in item):
        raise ValueError(f"loadout field {key} must contain only non-empty strings")
    return item
