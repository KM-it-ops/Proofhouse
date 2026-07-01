from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


TEMPLATE_ID = "prompt-architect"
TEMPLATE_MANIFEST = Path("prompts") / "templates" / "prompt_architect" / "manifest.json"
COMPACT_PROJECT_PLACEHOLDER = (
    r"\[PROJECT DESCRIPTION — describe what you're building, which platforms, your preferred "
    r"or existing stack, and whether this is a quick utility, a feature, a full app, or a "
    r"shippable product\]"
)


@dataclass(frozen=True)
class PromptArchitectInputs:
    project_name: str
    project_description: str
    platforms: list[str] = field(default_factory=list)
    stack: str = ""
    scale: str = ""
    open_decisions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RenderedPromptArchitect:
    system: str
    compact: str
    version: str


@dataclass(frozen=True)
class ExportedPromptArchitect:
    system_path: Path
    compact_path: Path
    version: str


def render_prompt_architect(
    inputs: PromptArchitectInputs,
    *,
    version: str | None = None,
    repo_root: str | Path | None = None,
) -> RenderedPromptArchitect:
    root = _resolve_repo_root(repo_root)
    manifest = _load_manifest(root)
    resolved_version = version or _required_str(manifest, "default_version")
    version_info = _version_info(manifest, resolved_version)

    system_template = _read_template(root, version_info, "system")
    compact_template = _read_template(root, version_info, "compact")
    project_brief = render_project_brief(inputs)

    if COMPACT_PROJECT_PLACEHOLDER not in compact_template:
        raise ValueError("compact prompt template is missing the project description placeholder")

    compact = compact_template.replace(COMPACT_PROJECT_PLACEHOLDER, project_brief)
    system = "\n\n".join(
        [
            system_template.rstrip(),
            "## PROJECT INPUT PACKET",
            "Use this project input when generating the stack audit and meta prompt.",
            "",
            project_brief,
        ]
    ).rstrip() + "\n"

    return RenderedPromptArchitect(system=system, compact=compact, version=resolved_version)


def export_prompt_architect(
    inputs: PromptArchitectInputs,
    out_dir: str | Path,
    *,
    version: str | None = None,
    repo_root: str | Path | None = None,
) -> ExportedPromptArchitect:
    rendered = render_prompt_architect(inputs, version=version, repo_root=repo_root)
    destination = Path(out_dir)
    destination.mkdir(parents=True, exist_ok=True)

    system_path = destination / "prompt-architect-system.md"
    compact_path = destination / "prompt-architect-compact.md"
    system_path.write_text(rendered.system, encoding="utf-8")
    compact_path.write_text(rendered.compact, encoding="utf-8")

    return ExportedPromptArchitect(
        system_path=system_path,
        compact_path=compact_path,
        version=rendered.version,
    )


def render_project_brief(inputs: PromptArchitectInputs) -> str:
    _require_non_empty(inputs.project_name, "project_name")
    _require_non_empty(inputs.project_description, "project_description")

    lines = [
        f"Project Name: {inputs.project_name.strip()}",
        "",
        "Project Description:",
        inputs.project_description.strip(),
        "",
        f"Platforms: {_format_list(inputs.platforms)}",
        f"Preferred or Existing Stack: {inputs.stack.strip() or 'NOT SPECIFIED'}",
        f"Project Scale: {inputs.scale.strip() or 'NOT SPECIFIED'}",
        f"Open Decisions: {_format_list(inputs.open_decisions)}",
    ]
    return "\n".join(lines)


def _resolve_repo_root(repo_root: str | Path | None) -> Path:
    candidates = []
    if repo_root is not None:
        candidates.append(Path(repo_root))
    candidates.append(Path.cwd())
    candidates.append(Path(__file__).resolve().parents[2])

    for candidate in candidates:
        if (candidate / TEMPLATE_MANIFEST).exists():
            return candidate
    raise FileNotFoundError(f"Could not find {TEMPLATE_MANIFEST}")


def _load_manifest(root: Path) -> dict[str, Any]:
    raw = json.loads((root / TEMPLATE_MANIFEST).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("template manifest must contain an object")
    if raw.get("id") != TEMPLATE_ID:
        raise ValueError(f"template manifest id must be {TEMPLATE_ID}")
    return raw


def _version_info(manifest: dict[str, Any], version: str) -> dict[str, Any]:
    versions = manifest.get("versions")
    if not isinstance(versions, dict):
        raise ValueError("template manifest must contain versions")
    value = versions.get(version)
    if not isinstance(value, dict):
        raise ValueError(f"Unknown prompt architect template version: {version}")
    return value


def _read_template(root: Path, version_info: dict[str, Any], key: str) -> str:
    template_path = version_info.get(key)
    if not isinstance(template_path, str) or not template_path.strip():
        raise ValueError(f"template version is missing {key}")
    return (root / TEMPLATE_MANIFEST.parent / template_path).read_text(encoding="utf-8")


def _required_str(value: dict[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"template manifest field {key} must be a non-empty string")
    return item


def _format_list(values: list[str]) -> str:
    cleaned = [value.strip() for value in values if value.strip()]
    return ", ".join(cleaned) if cleaned else "NOT SPECIFIED"


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
