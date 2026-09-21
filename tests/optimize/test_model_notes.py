"""Local model-notes cache: builtin / cached / researched / fallback provenance, offline."""

from __future__ import annotations

import json
import socket
from datetime import date
from pathlib import Path

import pytest

from proofhouse.optimize import model_notes, registry
from proofhouse.optimize.model_notes import (
    CACHE_SCHEMA,
    ResolvedNotes,
    cache_dir,
    forget,
    list_builtin,
    list_cached,
    proofhouse_home,
    remember,
    resolve_model_notes,
)
from proofhouse.optimize.registry import find_model, load_registry

OTHER_NOTES = (
    "No verified vendor-specific behavior available. General best practice: "
    "explicit goal, constraints, format, audience. Note in rationale that this "
    "is generic guidance."
)


@pytest.fixture()
def forbid_network(monkeypatch):
    def _blocked(*args, **kwargs):
        raise AssertionError("network access attempted during an offline compiler operation")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    yield


@pytest.fixture()
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, forbid_network) -> Path:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path))
    return tmp_path


def _cache_files(home: Path) -> list[Path]:
    directory = home / "model-notes"
    return sorted(directory.glob("*.json")) if directory.is_dir() else []


def test_proofhouse_home_honours_env_and_defaults_to_dot_proofhouse(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert proofhouse_home() == home
    assert cache_dir() == home / "model-notes"
    monkeypatch.delenv("PROOFHOUSE_HOME")
    assert proofhouse_home() == Path.home() / ".proofhouse"


def test_builtin_resolve_keeps_entered_name(home: Path) -> None:
    resolved = resolve_model_notes("  Claude Opus 5 ")
    assert isinstance(resolved, ResolvedNotes)
    assert resolved.entered_name == "  Claude Opus 5 "
    assert resolved.canonical_id == "claude-opus-5"
    assert resolved.display_name == "Claude Opus 5"
    assert resolved.provider == "Anthropic"
    assert resolved.tier == "current"
    assert resolved.source == "builtin"
    assert resolved.verified_at == "2026-09-03"
    assert resolved.stale_after_days == 90
    assert resolved.sources == ()
    assert resolved.provenance is None
    assert resolved.notes == find_model("claude-opus-5").notes
    assert _cache_files(home) == []


def test_alias_resolves_to_canonical_builtin(home: Path) -> None:
    resolved = resolve_model_notes("opus 5")
    assert resolved.canonical_id == "claude-opus-5"
    assert resolved.entered_name == "opus 5"
    assert resolved.source == "builtin"
    via_prefix = resolve_model_notes("anthropic/claude-opus-5")
    assert via_prefix.canonical_id == "claude-opus-5"


def test_unknown_without_researcher_is_fallback_and_writes_nothing(home: Path) -> None:
    resolved = resolve_model_notes("Zeta 9")
    assert resolved.source == "fallback"
    assert resolved.entered_name == "Zeta 9"
    assert resolved.canonical_id == "zeta-9"
    assert resolved.display_name == "Zeta 9"
    assert resolved.provider is None
    assert resolved.tier == "generic"
    assert resolved.verified_at is None
    assert resolved.stale is False
    assert resolved.age_days is None
    assert resolved.notes == OTHER_NOTES
    assert _cache_files(home) == []


def test_unknown_with_fake_researcher_is_researched_then_cached(home: Path) -> None:
    calls: list[str] = []

    def fake_researcher(name: str) -> tuple[str, list[str]]:
        calls.append(name)
        return ("Zeta 9 likes terse system prompts.", ["https://example.invalid/zeta"])

    first = resolve_model_notes("Zeta 9", researcher=fake_researcher)
    assert first.source == "researched"
    assert first.canonical_id == "zeta-9"
    assert first.notes == "Zeta 9 likes terse system prompts."
    assert first.sources == ("https://example.invalid/zeta",)
    assert first.verified_at == registry.today().isoformat()
    assert calls == ["Zeta 9"]

    files = _cache_files(home)
    assert [p.name for p in files] == ["zeta-9.json"]
    entry = json.loads(files[0].read_text(encoding="utf-8"))
    assert entry["schema"] == CACHE_SCHEMA == "proofhouse.model-notes/v0"
    assert entry["sources"] == ["https://example.invalid/zeta"]
    assert entry["entered_name"] == "Zeta 9"
    assert entry["canonical_id"] == "zeta-9"
    assert entry["source"] == "researched"

    second = resolve_model_notes("zeta 9", researcher=fake_researcher)
    assert second.source == "cached"
    assert second.entered_name == "zeta 9"
    assert second.notes == first.notes
    assert calls == ["Zeta 9"]


def test_remember_newer_than_builtin_wins_as_cached(home: Path) -> None:
    path = remember("opus 5", "My own Opus 5 notes.", sources=["https://example.invalid/opus"], verified_at="2026-09-10")
    assert path == home / "model-notes" / "claude-opus-5.json"
    resolved = resolve_model_notes("Claude Opus 5")
    assert resolved.source == "cached"
    assert resolved.canonical_id == "claude-opus-5"
    assert resolved.display_name == "Claude Opus 5"
    assert resolved.provider == "Anthropic"
    assert resolved.verified_at == "2026-09-10"
    assert resolved.sources == ("https://example.invalid/opus",)
    assert resolved.notes == "My own Opus 5 notes."


def test_remember_older_than_builtin_loses_to_builtin(home: Path) -> None:
    remember("Claude Opus 5", "Ancient notes.", sources=[], verified_at="2026-01-01")
    resolved = resolve_model_notes("opus 5")
    assert resolved.source == "builtin"
    assert resolved.verified_at == "2026-09-03"
    assert resolved.notes == find_model("claude-opus-5").notes
    # ties go to the cache
    remember("Claude Opus 5", "Same-day notes.", sources=[], verified_at="2026-09-03")
    tied = resolve_model_notes("opus 5")
    assert tied.source == "cached"
    assert tied.notes == "Same-day notes."


def test_remember_defaults_verified_at_to_today_and_overwrites(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(registry, "today", lambda: date(2026, 9, 21))
    remember("Zeta 9", "v1", sources=[], provenance="notes file zeta.md")
    remember("Zeta 9", "v2", sources=["https://example.invalid/2"])
    entry = json.loads((home / "model-notes" / "zeta-9.json").read_text(encoding="utf-8"))
    assert entry["verified_at"] == "2026-09-21"
    assert entry["notes"] == "v2"
    assert entry["provenance"] is None
    assert len(_cache_files(home)) == 1
    with pytest.raises(ValueError):
        remember("Zeta 9", "bad", sources=[], verified_at="not-a-date")


def test_forget_returns_true_then_false(home: Path) -> None:
    remember("Zeta 9", "notes", sources=[])
    assert forget("zeta 9") is True
    assert _cache_files(home) == []
    assert forget("Zeta 9") is False
    assert forget("Claude Opus 5") is False


def test_stale_is_computed_from_injected_today(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(registry, "today", lambda: date(2027, 1, 1))
    resolved = resolve_model_notes("Claude Opus 5")
    assert resolved.stale is True
    assert resolved.age_days is not None and resolved.age_days >= 90
    assert resolved.age_days == (date(2027, 1, 1) - date(2026, 9, 3)).days
    fresh = resolve_model_notes("Other")
    assert fresh.stale is False and fresh.age_days is None


def test_list_builtin_and_list_cached(home: Path) -> None:
    builtin = list_builtin()
    reg = load_registry()
    assert len(builtin) == 18
    assert [r.canonical_id for r in builtin] == [m.id for m in reg.models]
    assert {r.source for r in builtin} == {"builtin"}
    assert list_cached() == ()
    remember("Zeta 9", "z", sources=[])
    remember("Alpha 1", "a", sources=[])
    cached = list_cached()
    assert [r.canonical_id for r in cached] == ["alpha-1", "zeta-9"]
    assert cached[1].entered_name == "Zeta 9"
    assert {r.source for r in cached} == {"cached"}
    assert cached[0].tier == "cached" and cached[0].provider is None


def test_empty_name_after_normalisation_is_rejected(home: Path) -> None:
    with pytest.raises(ValueError):
        resolve_model_notes("!!!")
    with pytest.raises(ValueError):
        remember("   ", "x", sources=[])
    assert _cache_files(home) == []


def test_to_dict_exposes_every_field_with_json_types(home: Path) -> None:
    data = resolve_model_notes("Kimi").to_dict()
    assert set(data) == {
        "entered_name",
        "canonical_id",
        "display_name",
        "provider",
        "tier",
        "source",
        "verification",
        "verified_at",
        "stale",
        "age_days",
        "stale_after_days",
        "sources",
        "provenance",
        "notes",
    }
    assert data["sources"] == []
    assert data["canonical_id"] == "kimi-k3"
    json.dumps(data)
    assert model_notes.CACHE_SCHEMA == CACHE_SCHEMA
