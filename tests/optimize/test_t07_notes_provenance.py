"""T07 (review F05): model-note provenance labels and mandatory-gate precedence.

On 78e512c a local text file of explicitly invented notes was labeled
``source=researched`` with today's ``verified_at`` and no sources; the shipped
registry dates 17 entries with zero sources; and one profile told the
compiler to strip verification instructions without protecting user-required
gates.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from proofhouse.optimize.case import notes_from_file
from proofhouse.optimize.model_notes import (
    SOURCE_USER_SUPPLIED,
    VERIFICATION_REVIEWED,
    VERIFICATION_SOURCED,
    VERIFICATION_UNVERIFIED,
    list_builtin,
    remember,
    resolve_model_notes,
)
from proofhouse.optimize.packets import compile_packet, packet_markdown, revise_packet
from proofhouse.optimize.registry import REGISTRY_PATH

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))


def test_probe_notes_file_is_user_supplied_and_unverified(tmp_path: Path) -> None:
    notes = tmp_path / "notes.txt"
    notes.write_text("This is invented and has not been researched.", encoding="utf-8")
    resolved = notes_from_file("Zeta 9", notes)
    assert resolved.source == SOURCE_USER_SUPPLIED
    assert resolved.verification == VERIFICATION_UNVERIFIED
    assert resolved.verified_at is None
    assert resolved.sources == ()


def test_packet_header_labels_user_supplied_notes_as_unverified(tmp_path: Path) -> None:
    notes = tmp_path / "notes.txt"
    notes.write_text("Invented.", encoding="utf-8")
    resolved = notes_from_file("Zeta 9", notes)
    packet = compile_packet("Objective", resolved, "balanced", False, [("q", "a")])
    header = packet_markdown("compile", resolved, packet, "next").splitlines()[2]
    assert "source=user_supplied" in header
    assert "evidence=unverified" in header
    assert "researched" not in header


def test_unsourced_builtin_entries_are_not_labeled_verified() -> None:
    for resolved in list_builtin():
        if not resolved.sources:
            assert resolved.verification == VERIFICATION_UNVERIFIED, resolved.canonical_id
        else:
            assert resolved.verification in {VERIFICATION_SOURCED, VERIFICATION_REVIEWED}


def test_remember_with_sources_is_sourced_without_is_unverified() -> None:
    remember("Zeta 9", "Notes with a citation.", sources=["https://example.invalid/doc"], verified_at="2026-09-10")
    assert resolve_model_notes("Zeta 9").verification == VERIFICATION_SOURCED
    remember("Zeta 9", "Notes without a citation.", sources=[], verified_at="2026-09-10")
    assert resolve_model_notes("Zeta 9").verification == VERIFICATION_UNVERIFIED


def test_researcher_output_without_sources_is_unverified() -> None:
    resolved = resolve_model_notes("Zeta 10", researcher=lambda name: ("Generated paragraph.", []))
    assert resolved.verification == VERIFICATION_UNVERIFIED


def test_registry_has_explicit_evidence_policy() -> None:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    assert "evidencePolicy" in data
    assert "unverified" in data["evidencePolicy"].lower()


_STRIP_VERIFY = re.compile(r"\b(strip|remove|drop|omit)\b[^.]*\b(verif\w*|self-check\w*|test\w*|QA)\b", re.IGNORECASE)
_KEEP_GATES = re.compile(r"\bkeep\b[^.]*\b(user-required|required|mandatory)\b", re.IGNORECASE)


def test_no_model_note_removes_verification_without_protecting_required_gates() -> None:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    offenders = [
        model["id"]
        for model in data["models"]
        if _STRIP_VERIFY.search(model["notes"]) and not _KEEP_GATES.search(model["notes"])
    ]
    assert offenders == []


@pytest.mark.parametrize("builder", ["compile", "revise"])
def test_compile_system_prompt_states_mandatory_gate_precedence(builder: str) -> None:
    resolved = resolve_model_notes("Claude Opus 5")
    if builder == "compile":
        packet = compile_packet("Objective", resolved, "efficient", False, [("q", "a")])
    else:
        packet = revise_packet("Objective", resolved, "efficient", False, "prev", "feedback")
    assert "never remove" in packet.system.lower()
    assert "mandatory" in packet.system.lower()


def test_all_framework_copies_carry_the_precedence_rule() -> None:
    copies = [
        REPO / "proofhouse-framework.json",
        REPO / "skills" / "proofhouse" / "references" / "proofhouse-framework.json",
        REPO / "src" / "proofhouse" / "optimize" / "data" / "proofhouse-framework.json",
    ]
    rules = {json.loads(p.read_text(encoding="utf-8"))["policyPrecedence"] for p in copies}
    assert len(rules) == 1
