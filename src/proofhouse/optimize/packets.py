"""Render the framework's clarify / compile / self-heal prompts as offline packets.

A packet is a system prompt plus a user message, filled from the package copy
of ``proofhouse-framework.json``. You run it in the host agent or model of your
choice; nothing here calls a model, and the rendered text carries no provider
name, API key field, or endpoint.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

from .model_notes import SOURCE_FALLBACK, ResolvedNotes
from .registry import PACKAGE_FRAMEWORK_PATH

PRESET_KEYS = ("efficient", "balanced", "thorough")
_PLACEHOLDER = re.compile(r"\{\{([^{}]*)\}\}")
_FRAMEWORK: dict | None = None


@dataclass(frozen=True)
class Packet:
    kind: str
    system: str
    user: str


def framework() -> dict:
    """The package framework copy, read once."""
    global _FRAMEWORK
    if _FRAMEWORK is None:
        _FRAMEWORK = json.loads(PACKAGE_FRAMEWORK_PATH.read_text(encoding="utf-8"))
    return _FRAMEWORK


def presets() -> dict:
    return framework()["tokenDiscipline"]["efficiencyPresets"]


def preset(preset_key: str) -> dict:
    try:
        return presets()[preset_key]
    except KeyError:
        raise ValueError(f"unknown preset {preset_key!r}; choose one of {', '.join(PRESET_KEYS)}") from None


def token_estimate(text: str) -> int:
    """The framework's local estimate: ceil(len(text) / 4)."""
    return math.ceil(len(text) / 4)


def render(template: str, mapping: dict[str, str]) -> str:
    """Substitute the template's own ``{{key}}`` placeholders from ``mapping`` in one pass.

    Only placeholders present in ``template`` are inspected, so ``{{...}}`` inside
    the substituted values (user objective, answers, recorded prompt, feedback)
    is copied verbatim. A template placeholder missing from ``mapping`` is an error.
    """

    def repl(match: re.Match) -> str:
        key = match.group(1)
        if key not in mapping:
            raise ValueError(f"unfilled placeholder {{{{{key}}}}} in template")
        return mapping[key]

    return _PLACEHOLDER.sub(repl, template)


def _token_discipline(loop: bool) -> str:
    fw = framework()
    text = fw["tokenDiscipline"]["universalDirective"]
    if loop:
        text += "\n\n" + fw["loopEngineering"]["directive"] + "\n" + fw["loopEngineering"]["effectOnClarify"]
    return text


def _resolved_model(resolved: ResolvedNotes) -> str:
    return resolved.display_name if resolved.source != SOURCE_FALLBACK else resolved.entered_name


def _system_mapping(resolved: ResolvedNotes, preset_key: str, loop: bool) -> dict[str, str]:
    chosen = preset(preset_key)
    return {
        "resolvedModel": _resolved_model(resolved),
        "modelNotes": resolved.notes,
        "TOKEN_DISCIPLINE": _token_discipline(loop),
        "preset.label": str(chosen["label"]),
        "preset.note": str(chosen["note"]),
        "preset.questionCount": str(chosen["questionCount"]),
        "preset.promptWordCap": str(chosen["promptWordCap"]),
    }


def clarify_packet(objective: str, resolved: ResolvedNotes, preset_key: str, loop: bool) -> Packet:
    prompts = framework()["systemPrompts"]["generateQuestions"]
    system = render(prompts["template"], _system_mapping(resolved, preset_key, loop))
    user = render(prompts["userTemplate"], {"rawRequest": objective})
    return Packet(kind="clarify", system=system, user=user)


def format_answered_entries(answered_entries: list[tuple[str, str]]) -> str:
    return "\n".join(f"- {label}: {answer}" for label, answer in answered_entries)


def compile_packet(
    objective: str,
    resolved: ResolvedNotes,
    preset_key: str,
    loop: bool,
    answered_entries: list[tuple[str, str]],
) -> Packet:
    prompts = framework()["systemPrompts"]["compilePrompt"]
    system = render(prompts["template"], _system_mapping(resolved, preset_key, loop))
    user = render(
        prompts["userTemplateFirstPass"],
        {"rawRequest": objective, "answeredEntries": format_answered_entries(answered_entries)},
    )
    return Packet(kind="compile", system=system, user=user)


def revise_packet(
    objective: str,
    resolved: ResolvedNotes,
    preset_key: str,
    loop: bool,
    previous_prompt: str,
    feedback: str,
    *,
    answered_entries: list[tuple[str, str]] | None = None,
    accepted_constraints: list[tuple[str, str]] | None = None,
) -> Packet:
    """Self-heal packet. The clarification answers and accepted constraints ride along (review F11)."""
    prompts = framework()["systemPrompts"]["compilePrompt"]
    system = render(prompts["template"], _system_mapping(resolved, preset_key, loop))
    constraints_text = "\n".join(f"- [{kid}] {text}" for kid, text in (accepted_constraints or [])) or "(none recorded)"
    user = render(
        prompts["userTemplateSelfHeal"],
        {
            "rawRequest": objective,
            "answeredEntries": format_answered_entries(answered_entries or []) or "(none recorded)",
            "acceptedConstraints": constraints_text,
            "tokenEstimate": str(token_estimate(previous_prompt)),
            "previousPrompt": previous_prompt,
            "feedback": feedback,
        },
    )
    return Packet(kind="revise", system=system, user=user)


def _fence(*blocks: str) -> str:
    fence = "```"
    while any(fence in block for block in blocks):
        fence += "`"
    return fence


def packet_markdown(title: str, resolved: ResolvedNotes, packet: Packet, next_line: str) -> str:
    """Fixed packet layout: heading, target line, system + user fenced blocks, next step."""
    fence = _fence(packet.system, packet.user)
    stale = "yes" if resolved.stale else "no"
    lines = [
        f"# Proofhouse packet: {title}",
        "",
        f"Target model: {_resolved_model(resolved)} ({resolved.canonical_id}) -- "
        f"source={resolved.source}, verified_at={resolved.verified_at or '-'}, stale={stale}, "
        f"evidence={resolved.verification}",
        "",
        "## System prompt",
        f"{fence}text",
        packet.system,
        fence,
        "## User message",
        f"{fence}text",
        packet.user,
        fence,
        "## Next",
        next_line,
    ]
    return "\n".join(lines) + "\n"
