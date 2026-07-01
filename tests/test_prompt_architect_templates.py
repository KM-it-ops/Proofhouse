import shutil
from pathlib import Path

from promptrig.templates import (
    COMPACT_PROJECT_PLACEHOLDER,
    PromptArchitectInputs,
    export_prompt_architect,
    render_project_brief,
    render_prompt_architect,
)


def test_project_brief_uses_not_specified_for_missing_optional_inputs():
    brief = render_project_brief(
        PromptArchitectInputs(
            project_name="Incident Desk",
            project_description="Build an internal incident review assistant.",
        )
    )

    assert "Project Name: Incident Desk" in brief
    assert "Platforms: NOT SPECIFIED" in brief
    assert "Preferred or Existing Stack: NOT SPECIFIED" in brief
    assert "Open Decisions: NOT SPECIFIED" in brief


def test_render_prompt_architect_injects_project_inputs():
    rendered = render_prompt_architect(
        PromptArchitectInputs(
            project_name="Incident Desk",
            project_description="Build an internal incident review assistant.",
            platforms=["web", "desktop"],
            stack="Next.js, Tauri, Supabase",
            scale="L",
            open_decisions=["Choose deployment target"],
        )
    )

    assert rendered.version == "1.0"
    assert "Agentic Prompt Architect — System Prompt v1.0" in rendered.system
    assert "Agentic Prompt Architect — Compact User Prompt v1.0" in rendered.compact
    assert "## PROJECT INPUT PACKET" in rendered.system
    assert "Project Name: Incident Desk" in rendered.system
    assert "Build an internal incident review assistant." in rendered.compact
    assert "Platforms: web, desktop" in rendered.compact
    assert COMPACT_PROJECT_PLACEHOLDER not in rendered.compact


def test_export_prompt_architect_writes_both_variants():
    out_dir = Path(".test-output") / "prompt-architect-template-export"
    if out_dir.exists():
        shutil.rmtree(out_dir)

    exported = export_prompt_architect(
        PromptArchitectInputs(
            project_name="OSINT Console",
            project_description="Generate a locked spec for an OSINT triage dashboard.",
            platforms=["web"],
            stack="FastAPI, React",
            scale="M",
        ),
        out_dir,
    )

    assert exported.system_path == out_dir / "prompt-architect-system.md"
    assert exported.compact_path == out_dir / "prompt-architect-compact.md"
    assert exported.system_path.exists()
    assert exported.compact_path.exists()
    assert "OSINT Console" in exported.system_path.read_text(encoding="utf-8")
    assert "OSINT Console" in exported.compact_path.read_text(encoding="utf-8")

    shutil.rmtree(out_dir)
