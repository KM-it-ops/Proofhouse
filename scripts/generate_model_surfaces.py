#!/usr/bin/env python3
"""Generate every human-facing model list from the reviewed registry.

Source: src/proofhouse/optimize/data/model_registry.json. Targets:

  1. proofhouse-framework.json   modelNotes + modelRegistry
  2. proofhouse-framework.md     table between <!-- model-notes:begin/end -->
  3. apps/proofhouse.jsx         MODEL_NOTES between // model-notes:begin/end
  4. README.md                   table between <!-- supported-models:begin/end -->
  5. skills/proofhouse/SKILL.md  paragraph between <!-- model-list:begin/end -->
  6. copies: skills/proofhouse/references/*.{json,md}, skills/proofhouse/assets/*.jsx,
     src/proofhouse/optimize/data/proofhouse-framework.json

Run with:  python scripts/generate_model_surfaces.py [--check]

--check renders everything in memory and compares LF-normalised bytes with the
files on disk; it never writes. All writes are UTF-8 with LF line endings.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from proofhouse.optimize.registry import ModelEntry, Registry, load_registry

REPO_ROOT = Path(__file__).resolve().parent.parent
ROOT_JSON = REPO_ROOT / "proofhouse-framework.json"
ROOT_MD = REPO_ROOT / "proofhouse-framework.md"
ROOT_JSX = REPO_ROOT / "apps" / "proofhouse.jsx"
README = REPO_ROOT / "README.md"
SKILL_MD = REPO_ROOT / "skills" / "proofhouse" / "SKILL.md"
SKILL_JSON = REPO_ROOT / "skills" / "proofhouse" / "references" / "proofhouse-framework.json"
SKILL_MD_REF = REPO_ROOT / "skills" / "proofhouse" / "references" / "proofhouse-framework.md"
SKILL_JSX = REPO_ROOT / "skills" / "proofhouse" / "assets" / "proofhouse.jsx"
PACKAGE_JSON = REPO_ROOT / "src" / "proofhouse" / "optimize" / "data" / "proofhouse-framework.json"

REGISTRY_SOURCE = "src/proofhouse/optimize/data/model_registry.json"

MD_BEGIN, MD_END = "<!-- model-notes:begin -->", "<!-- model-notes:end -->"
JSX_BEGIN, JSX_END = "// model-notes:begin", "// model-notes:end"
README_BEGIN, README_END = "<!-- supported-models:begin -->", "<!-- supported-models:end -->"
SKILL_BEGIN, SKILL_END = "<!-- model-list:begin -->", "<!-- model-list:end -->"

README_OTHER_ROW = (
    "| **Other** | Skill and artifact: the host agent or the artifact web-researches the model "
    "and caches the paragraph. CLI (`proofhouse-compiler`): offline; `models remember` stores "
    "your own notes, otherwise the generic profile is used and labeled `fallback`. |"
)
README_FULL_PROFILES = (
    "Full profiles: [`proofhouse-framework.json`](proofhouse-framework.json) · "
    "human-readable [`proofhouse-framework.md`](proofhouse-framework.md)"
)


class SurfaceError(Exception):
    """A target file lacks the structure the generator expects."""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def _join_and(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _max_verified_at(registry: Registry) -> str:
    dates = [m.verified_at for m in registry.models if m.verified_at]
    return max(dates)


def _lines(text: str) -> list[str]:
    return text.split("\n")


def replace_region(
    text: str,
    begin: str,
    end: str,
    body: str,
    *,
    first_line: str,
    last_line: str,
    after_heading: str | None = None,
) -> str:
    """Replace the lines between the markers with ``body``.

    When the markers are absent, the block from the first line for which
    ``first_line(line)`` holds (searching after ``after_heading`` when given) to the
    first following line for which ``last_line(line)`` holds is wrapped in the
    markers and replaced.
    """
    lines = _lines(text)
    if begin in lines and end in lines:
        start = lines.index(begin)
        stop = lines.index(end)
        if stop < start:
            raise SurfaceError(f"end marker {end!r} precedes begin marker")
        return "\n".join(lines[: start + 1] + _lines(body) + lines[stop:])
    if begin in lines or end in lines:
        raise SurfaceError(f"only one of {begin!r} / {end!r} present")

    search_from = 0
    if after_heading is not None:
        try:
            search_from = lines.index(after_heading) + 1
        except ValueError as exc:
            raise SurfaceError(f"heading {after_heading!r} not found") from exc
    start = next(
        (i for i in range(search_from, len(lines)) if first_line(lines[i])),
        None,
    )
    if start is None:
        raise SurfaceError("could not locate the block to wrap in markers")
    stop = next((i for i in range(start, len(lines)) if last_line(lines[i])), None)
    if stop is None:
        raise SurfaceError("could not locate the end of the block to wrap in markers")
    return "\n".join(lines[:start] + [begin] + _lines(body) + [end] + lines[stop + 1 :])


# --- 1. framework JSON -------------------------------------------------------


def _registry_row(entry: ModelEntry) -> dict:
    return {
        "id": entry.id,
        "displayName": entry.display_name,
        "triggerLabel": entry.trigger_label,
        "provider": entry.provider,
        "tier": entry.tier,
        "apiId": entry.api_id,
        "aliases": list(entry.aliases),
        "verifiedAt": entry.verified_at,
    }


def render_framework_json(current: str, registry: Registry) -> str:
    data = json.loads(current)
    if "modelNotes" not in data:
        raise SurfaceError("framework JSON has no modelNotes key")
    out: dict = {}
    for key, value in data.items():
        if key == "modelRegistry":
            continue
        if key == "modelNotes":
            out["modelNotes"] = {m.display_name: m.notes for m in registry.models}
            out["modelRegistry"] = {
                "source": REGISTRY_SOURCE,
                "staleAfterDays": registry.stale_after_days,
                "models": [_registry_row(m) for m in registry.models],
            }
            continue
        out[key] = value
    return json.dumps(out, indent=2, ensure_ascii=False) + "\n"


# --- 2. framework Markdown ---------------------------------------------------


def render_framework_md(current: str, registry: Registry) -> str:
    rows = ["| Model | Verified | Notes |", "|---|---|---|"]
    rows.extend(
        f"| **{m.display_name}** | {m.verified_at or '-'} | {m.notes} |" for m in registry.models
    )
    return replace_region(
        current,
        MD_BEGIN,
        MD_END,
        "\n".join(rows),
        first_line=lambda line: line.startswith("|"),
        last_line=lambda line: line.startswith("| **Other"),
        after_heading="## Model notes (update as models change)",
    )


# --- 3. JSX ------------------------------------------------------------------


def render_jsx(current: str, registry: Registry) -> str:
    lines = ["const MODEL_NOTES = {"]
    for m in registry.models:
        lines.append(f"  {json.dumps(m.display_name)}:")
        lines.append(f"    {json.dumps(m.notes, ensure_ascii=False)},")
    lines.append("};")
    return replace_region(
        current,
        JSX_BEGIN,
        JSX_END,
        "\n".join(lines),
        first_line=lambda line: line.startswith("const MODEL_NOTES = {"),
        last_line=lambda line: line == "};",
    )


# --- 4. README ---------------------------------------------------------------


def render_readme(current: str, registry: Registry) -> str:
    by_provider: dict[str, list[str]] = {}
    for m in registry.models:
        if m.tier == "current" and m.provider:
            by_provider.setdefault(m.provider, []).append(m.trigger_label)
    legacy = [m.trigger_label for m in registry.models if m.tier == "legacy"]
    rows = ["| Tier | Models |", "|---|---|"]
    rows.extend(f"| **{provider}** | {' · '.join(labels)} |" for provider, labels in by_provider.items())
    rows.append(f"| **Legacy** | {' · '.join(legacy)} |")
    rows.append(README_OTHER_ROW)
    rows.append("")
    rows.append(
        f"Profiles verified {_max_verified_at(registry)}; a profile older than "
        f"{registry.stale_after_days} days is flagged stale. `proofhouse-compiler models list` "
        "shows per-model ids, aliases, and dates."
    )
    rows.append("")
    rows.append(README_FULL_PROFILES)
    return replace_region(
        current,
        README_BEGIN,
        README_END,
        "\n".join(rows),
        first_line=lambda line: line.startswith("|"),
        last_line=lambda line: line.startswith("Full profiles:"),
        after_heading="## Supported models (framework v1.3)",
    )


# --- 5. SKILL.md -------------------------------------------------------------


def render_skill_md(current: str, registry: Registry) -> str:
    current_names = [m.display_name for m in registry.models if m.tier == "current"]
    legacy_names = [m.display_name for m in registry.models if m.tier == "legacy"]
    paragraph = (
        f"Built-in profiles for {_join_and(current_names)} (plus legacy {_join_and(legacy_names)}) "
        "are in `references/proofhouse-framework.json` under `modelNotes`; canonical ids, aliases, "
        f"and `verifiedAt` dates (profiles verified {_max_verified_at(registry)}) are under "
        "`modelRegistry`. Say which profile you used and its verified date; if it is older than "
        f"{registry.stale_after_days} days, tell the user to re-check pricing, context, and settings "
        "against vendor docs. For anything else the user names:"
    )
    return replace_region(
        current,
        SKILL_BEGIN,
        SKILL_END,
        paragraph,
        first_line=lambda line: line.startswith("Built-in profiles for"),
        last_line=lambda line: line.endswith("else the user names:"),
    )


def missing_trigger_labels(skill_text: str, registry: Registry) -> list[str]:
    description = next(
        (line for line in _lines(skill_text) if line.startswith("description:")), ""
    )
    return [
        m.trigger_label
        for m in registry.models
        if m.tier == "current" and m.trigger_label not in description
    ]


# --- render / check / write --------------------------------------------------


def render_all(registry: Registry | None = None) -> dict[Path, str]:
    registry = registry or load_registry()
    framework_json = render_framework_json(_read(ROOT_JSON), registry)
    framework_md = render_framework_md(_read(ROOT_MD), registry)
    jsx = render_jsx(_read(ROOT_JSX), registry)
    readme = render_readme(_read(README), registry)
    skill_md = render_skill_md(_read(SKILL_MD), registry)
    missing = missing_trigger_labels(skill_md, registry)
    if missing:
        raise SurfaceError(
            "SKILL.md description: line is missing current-tier trigger labels: "
            + ", ".join(missing)
        )
    return {
        ROOT_JSON: framework_json,
        ROOT_MD: framework_md,
        ROOT_JSX: jsx,
        README: readme,
        SKILL_MD: skill_md,
        SKILL_JSON: framework_json,
        SKILL_MD_REF: framework_md,
        SKILL_JSX: jsx,
        PACKAGE_JSON: framework_json,
    }


def check(registry: Registry | None = None) -> list[Path]:
    """Paths whose LF-normalised on-disk bytes differ from the rendered output."""
    drift: list[Path] = []
    for path, text in render_all(registry).items():
        on_disk = _lf(path.read_bytes()) if path.is_file() else None
        if on_disk != text.encode("utf-8"):
            drift.append(path)
    return drift


def write(registry: Registry | None = None) -> list[Path]:
    rendered = render_all(registry)
    for path, text in rendered.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        _write(path, text)
    return list(rendered)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate model lists from the reviewed registry.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare rendered output with the files on disk; never write",
    )
    args = parser.parse_args(argv)
    registry = load_registry()
    try:
        if args.check:
            drift = check(registry)
            for path in drift:
                print(f"drift: {path.relative_to(REPO_ROOT).as_posix()}")
            if drift:
                return 1
            print(f"model surfaces: in sync ({len(registry.models)} models)")
            return 0
        for path in write(registry):
            print(f"wrote {path.relative_to(REPO_ROOT).as_posix()}")
        return 0
    except SurfaceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
