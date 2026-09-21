"""Offline packets rendered from the package framework templates (clarify / compile / revise)."""

from __future__ import annotations

import json
import math
import re

import pytest

from proofhouse.optimize import packets
from proofhouse.optimize.model_notes import resolve_model_notes
from proofhouse.optimize.registry import PACKAGE_FRAMEWORK_PATH

PLACEHOLDER = re.compile(r"\{\{[^}]*\}\}")
OBJECTIVE = "Summarise a security advisory for a SOC audience"


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path))


@pytest.fixture()
def framework() -> dict:
    return json.loads(PACKAGE_FRAMEWORK_PATH.read_text(encoding="utf-8"))


def test_render_fills_every_placeholder_and_rejects_unknown() -> None:
    assert packets.render("a {{x}} b {{preset.label}}", {"x": "1", "preset.label": "Balanced"}) == "a 1 b Balanced"
    with pytest.raises(ValueError, match="unfilled placeholder"):
        packets.render("{{resolvedModel}} and {{nope}}", {"resolvedModel": "X"})


def test_clarify_compile_revise_fill_every_placeholder(framework: dict) -> None:
    resolved = resolve_model_notes("Sonnet 5")
    clarify = packets.clarify_packet(OBJECTIVE, resolved, "balanced", False)
    compile_ = packets.compile_packet(OBJECTIVE, resolved, "efficient", False, [("audience", "SOC analysts")])
    revise = packets.revise_packet(OBJECTIVE, resolved, "thorough", False, "Previous prompt text here.", "too long")
    for packet in (clarify, compile_, revise):
        assert not PLACEHOLDER.search(packet.system), packet.system
        assert not PLACEHOLDER.search(packet.user), packet.user
        assert "Target model: Claude Sonnet 5" in packet.system
        assert resolved.notes in packet.system
        assert framework["tokenDiscipline"]["universalDirective"] in packet.system
        assert OBJECTIVE in packet.user
    assert "Balanced (standard coverage)" in clarify.system
    assert "10-16 total questions" in clarify.system
    assert "under 250 words" in compile_.system
    assert "- audience: SOC analysts" in compile_.user
    assert "Previous prompt text here." in revise.user
    assert f"~{math.ceil(len('Previous prompt text here.') / 4)} tokens" in revise.user
    assert 'User feedback on that version: "too long"' in revise.user


def test_loop_flag_injects_loop_directive_only_when_set(framework: dict) -> None:
    resolved = resolve_model_notes("Sonnet 5")
    loop_directive = framework["loopEngineering"]["directive"]
    on = packets.clarify_packet(OBJECTIVE, resolved, "balanced", True)
    off = packets.clarify_packet(OBJECTIVE, resolved, "balanced", False)
    assert loop_directive in on.system
    assert "Loop & Recurrence" in on.system
    assert loop_directive not in off.system
    assert "Loop & Recurrence" not in off.system
    compiled_on = packets.compile_packet(OBJECTIVE, resolved, "balanced", True, [("q", "a")])
    compiled_off = packets.compile_packet(OBJECTIVE, resolved, "balanced", False, [("q", "a")])
    assert loop_directive in compiled_on.system
    assert loop_directive not in compiled_off.system


def test_fallback_model_uses_entered_name_and_generic_notes() -> None:
    resolved = resolve_model_notes("Zeta 9")
    packet = packets.clarify_packet(OBJECTIVE, resolved, "balanced", False)
    assert "Target model: Zeta 9" in packet.system
    assert "No verified vendor-specific behavior available." in packet.system


def test_packet_markdown_layout_is_fixed() -> None:
    resolved = resolve_model_notes("Sonnet 5")
    packet = packets.clarify_packet(OBJECTIVE, resolved, "balanced", False)
    text = packets.packet_markdown("clarify", resolved, packet, "next: do the thing")
    lines = text.splitlines()
    assert lines[0] == "# Proofhouse packet: clarify"
    assert lines[1] == ""
    assert lines[2] == (
        "Target model: Claude Sonnet 5 (claude-sonnet-5) -- source=builtin, verified_at=2026-09-03, stale=no"
    )
    assert lines[3] == ""
    assert lines[4] == "## System prompt"
    assert lines[5] == "```text"
    close_system = lines.index("```", 6)
    assert lines[close_system + 1] == "## User message"
    assert lines[close_system + 2] == "```text"
    close_user = lines.index("```", close_system + 3)
    assert lines[close_user + 1] == "## Next"
    assert lines[close_user + 2] == "next: do the thing"
    assert len(lines) == close_user + 3
    assert text.endswith("\n")
    for forbidden in ("api.anthropic", "openai.com", "api_key", "Anthropic"):
        assert forbidden not in text


def test_unknown_preset_raises() -> None:
    resolved = resolve_model_notes("Sonnet 5")
    with pytest.raises(ValueError, match="unknown preset"):
        packets.clarify_packet(OBJECTIVE, resolved, "turbo", False)
