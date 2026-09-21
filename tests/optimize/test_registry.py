"""The reviewed model registry: fixed order, unique keys, normalisation, staleness."""

from __future__ import annotations

import re
from datetime import date

import pytest

from proofhouse.optimize import registry
from proofhouse.optimize.registry import (
    PACKAGE_BUNDLE_PATH,
    PACKAGE_FRAMEWORK_PATH,
    REGISTRY_PATH,
    ModelEntry,
    age_days,
    find_model,
    is_stale,
    load_registry,
    lookup_keys,
    normalize_model_name,
)

EXPECTED_IDS = (
    "claude-fable-5-1",
    "claude-mythos-5-1",
    "claude-opus-5",
    "claude-sonnet-5",
    "claude-haiku-4-5",
    "gpt-5-6-sol",
    "gpt-5-6-terra",
    "gpt-5-6-luna",
    "gpt-5-5",
    "gemini-3-8-flash",
    "grok-4-6",
    "muse-spark-1-3",
    "kimi-k3",
    "gemini",
    "claude-fable-5",
    "claude-mythos-5",
    "claude-opus-4-8",
    "other",
)

EXPECTED_DISPLAY_NAMES = (
    "Claude Fable 5.1",
    "Claude Mythos 5.1",
    "Claude Opus 5",
    "Claude Sonnet 5",
    "Claude Haiku 4.5",
    "GPT-5.6 Sol",
    "GPT-5.6 Terra",
    "GPT-5.6 Luna",
    "GPT-5.5",
    "Gemini 3.8 Flash",
    "Grok 4.6",
    "Muse Spark 1.3",
    "Kimi K3",
    "Gemini",
    "Claude Fable 5",
    "Claude Mythos 5",
    "Claude Opus 4.8",
    "Other",
)


def test_data_paths_live_under_package_data() -> None:
    assert REGISTRY_PATH.is_file()
    assert REGISTRY_PATH.parent.name == "data"
    assert PACKAGE_FRAMEWORK_PATH.parent == REGISTRY_PATH.parent
    assert PACKAGE_BUNDLE_PATH.parent == REGISTRY_PATH.parent


def test_registry_metadata() -> None:
    reg = load_registry()
    assert reg.schema == "proofhouse.model-registry/v0"
    assert reg.framework_version == "1.3"
    assert reg.stale_after_days == 90


def test_registry_has_eighteen_models_in_fixed_order() -> None:
    reg = load_registry()
    assert len(reg.models) == 18
    assert tuple(m.id for m in reg.models) == EXPECTED_IDS
    assert tuple(m.display_name for m in reg.models) == EXPECTED_DISPLAY_NAMES
    assert all(isinstance(m, ModelEntry) for m in reg.models)


def test_ids_and_display_names_unique() -> None:
    reg = load_registry()
    ids = [m.id for m in reg.models]
    names = [m.display_name for m in reg.models]
    assert len(set(ids)) == len(ids)
    assert len(set(names)) == len(names)


def test_lookup_keys_unique_across_models() -> None:
    reg = load_registry()
    seen: dict[str, str] = {}
    for entry in reg.models:
        for key in lookup_keys(entry):
            assert key not in seen, f"{key!r} claimed by {seen[key]} and {entry.id}"
            seen[key] = entry.id


def test_every_entry_resolves_to_itself() -> None:
    reg = load_registry()
    for entry in reg.models:
        assert normalize_model_name(entry.id) == entry.id
        hit = find_model(entry.display_name, reg)
        assert hit is not None and hit.id == entry.id
        for alias in entry.aliases:
            alias_hit = find_model(alias, reg)
            assert alias_hit is not None and alias_hit.id == entry.id, alias


@pytest.mark.parametrize(
    ("entered", "expected"),
    [
        ("GPT-5.6 Sol", "gpt-5-6-sol"),
        ("anthropic/claude-opus-5", "claude-opus-5"),
        ("Opus 5", "opus-5"),
        ("  Kimi  ", "kimi"),
        ("Zeta 9", "zeta-9"),
        ("openai: gpt-5.6", "gpt-5-6"),
        ("x-ai/Grok__4.6", "grok-4-6"),
        ("--Weird!!Name--", "weirdname"),
    ],
)
def test_normalize_model_name_examples(entered: str, expected: str) -> None:
    assert normalize_model_name(entered) == expected


def test_find_model_via_alias_and_provider_prefix() -> None:
    assert find_model("anthropic/claude-opus-5").id == "claude-opus-5"
    assert find_model("Opus 5").id == "claude-opus-5"
    assert find_model("  Kimi  ").id == "kimi-k3"
    assert find_model("gpt-5.6").id == "gpt-5-6-sol"
    assert find_model("gpt-5.6-terra").id == "gpt-5-6-terra"
    assert find_model("other/unspecified").id == "other"


def test_find_model_unknown_is_none() -> None:
    assert find_model("Zeta 9") is None
    assert find_model("") is None


def test_is_stale_boundary_with_injected_today() -> None:
    verified = "2026-09-03"
    day_89 = date(2026, 12, 1)
    day_90 = date(2026, 12, 2)
    assert age_days(verified, today=day_89) == 89
    assert age_days(verified, today=day_90) == 90
    assert is_stale(verified, today=day_89, stale_after_days=90) is False
    assert is_stale(verified, today=day_90, stale_after_days=90) is True


def test_none_verified_at_is_never_stale() -> None:
    assert age_days(None, today=date(2030, 1, 1)) is None
    assert is_stale(None, today=date(2030, 1, 1), stale_after_days=90) is False


def test_today_is_a_module_function_returning_a_date(monkeypatch: pytest.MonkeyPatch) -> None:
    assert isinstance(registry.today(), date)
    monkeypatch.setattr(registry, "today", lambda: date(2027, 1, 1))
    assert registry.today() == date(2027, 1, 1)


def test_other_entry_is_generic_and_unverified() -> None:
    other = find_model("other")
    assert other is not None
    assert other.tier == "generic"
    assert other.verified_at is None
    assert other.provider is None
    assert other.api_id is None
    assert other.aliases == ("unspecified", "other/unspecified")
    assert other.notes == (
        "No verified vendor-specific behavior available. General best practice: "
        "explicit goal, constraints, format, audience. Note in rationale that this "
        "is generic guidance."
    )


def test_notes_and_verified_at_are_well_formed() -> None:
    reg = load_registry()
    for entry in reg.models:
        assert "|" not in entry.notes, entry.id
        assert entry.notes.strip() == entry.notes and entry.notes
        assert entry.sources == ()
        if entry.id == "other":
            continue
        assert entry.verified_at is not None
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry.verified_at), entry.id
        assert entry.verified_at == "2026-09-03"
        assert entry.tier in {"current", "legacy"}
