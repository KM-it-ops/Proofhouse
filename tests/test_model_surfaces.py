"""Five human-facing model lists derive from one registry; drift is a failure."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from proofhouse.optimize.registry import load_registry

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_generator():
    path = REPO_ROOT / "scripts" / "generate_model_surfaces.py"
    spec = importlib.util.spec_from_file_location("generate_model_surfaces", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["generate_model_surfaces"] = module
    spec.loader.exec_module(module)
    return module


def _root_framework() -> dict:
    return json.loads((REPO_ROOT / "proofhouse-framework.json").read_text(encoding="utf-8"))


def test_check_reports_no_drift() -> None:
    generator = _load_generator()
    assert generator.check() == [], "run scripts/generate_model_surfaces.py"


def test_root_json_model_notes_keys_match_registry_order() -> None:
    reg = load_registry()
    notes = _root_framework()["modelNotes"]
    assert list(notes) == [m.display_name for m in reg.models]
    for entry in reg.models:
        assert notes[entry.display_name] == entry.notes


def test_root_json_model_registry_mirrors_registry() -> None:
    reg = load_registry()
    data = _root_framework()
    keys = list(data)
    assert keys.index("modelRegistry") == keys.index("modelNotes") + 1
    block = data["modelRegistry"]
    assert block["source"] == "src/proofhouse/optimize/data/model_registry.json"
    assert block["staleAfterDays"] == reg.stale_after_days
    assert len(block["models"]) == len(reg.models)
    for i, entry in enumerate(reg.models):
        row = block["models"][i]
        assert row["id"] == entry.id
        assert row["displayName"] == entry.display_name
        assert row["triggerLabel"] == entry.trigger_label
        assert row["provider"] == entry.provider
        assert row["tier"] == entry.tier
        assert row["apiId"] == entry.api_id
        assert row["aliases"] == list(entry.aliases)
        assert row["verifiedAt"] == entry.verified_at
    assert data["version"] == "1.3"


def test_jsx_model_notes_carry_registry_notes() -> None:
    reg = load_registry()
    opus = next(m for m in reg.models if m.id == "claude-opus-5")
    jsx = (REPO_ROOT / "apps" / "proofhouse.jsx").read_text(encoding="utf-8")
    expected = '  "Claude Opus 5":\n    ' + json.dumps(opus.notes, ensure_ascii=False) + ","
    assert expected in jsx.replace("\r\n", "\n")
    assert "// model-notes:begin" in jsx and "// model-notes:end" in jsx


def test_readme_supported_models_table_is_generated() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "| **Anthropic** | Claude Fable 5.1 · Mythos 5.1 · Opus 5 · Sonnet 5 · Haiku 4.5 |" in readme
    assert "| **Legacy** | GPT-5.5 · Gemini (generic) · Fable 5 · Mythos 5 · Opus 4.8 |" in readme
    assert "labeled `fallback`" in readme
    assert "<!-- supported-models:begin -->" in readme and "<!-- supported-models:end -->" in readme


def test_framework_markdown_table_has_verified_column() -> None:
    md = (REPO_ROOT / "proofhouse-framework.md").read_text(encoding="utf-8")
    assert "<!-- model-notes:begin -->\n| Model | Verified | Notes |\n|---|---|---|\n" in md
    assert "| **Other** | - | No verified vendor-specific behavior available." in md


def test_skill_md_paragraph_and_description_cover_current_models() -> None:
    reg = load_registry()
    skill = (REPO_ROOT / "skills" / "proofhouse" / "SKILL.md").read_text(encoding="utf-8")
    begin = skill.index("<!-- model-list:begin -->")
    end = skill.index("<!-- model-list:end -->")
    paragraph = skill[begin:end]
    assert paragraph.rstrip().endswith("For anything else the user names:")
    for entry in reg.models:
        if entry.tier in {"current", "legacy"}:
            assert entry.display_name in paragraph, entry.display_name
    description = next(line for line in skill.splitlines() if line.startswith("description:"))
    for entry in reg.models:
        if entry.tier == "current":
            assert entry.trigger_label in description, entry.trigger_label
