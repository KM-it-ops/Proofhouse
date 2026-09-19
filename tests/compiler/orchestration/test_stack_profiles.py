"""Stack profiles with stated migration deltas (T-P4-02)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofhouse.compiler.orchestration.stack_profiles import (
    MigrationDelta,
    RegistryMissingError,
    bind_profile,
    load_registries,
    source_delta,
)


def _write_regs(tmp_path: Path) -> tuple[Path, Path]:
    profiles = tmp_path / "stack-profiles.json"
    sources = tmp_path / "component-registry.json"
    profiles.write_text(
        json.dumps(
            {
                "profiles": [
                    {
                        "id": "SP-static",
                        "permitted_sources": ["animejs"],
                    },
                    {
                        "id": "SP-react-motion",
                        "permitted_sources": ["kokonut", "animejs"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    sources.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "id": "animejs",
                        "stack_profiles": ["SP-static", "SP-react-motion"],
                        "dependencies": ["animejs"],
                        "adaptation_required": False,
                    },
                    {
                        "id": "kokonut",
                        "stack_profiles": ["SP-react-motion"],
                        "dependencies": ["react", "tailwind", "motion"],
                        "adaptation_required": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    return profiles, sources


def test_missing_registries_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(RegistryMissingError):
        load_registries(tmp_path / "missing-profiles.json", tmp_path / "missing-sources.json")


def test_bind_profile_two_level_concept() -> None:
    assert bind_profile("editorial one-pager") == "SP-static"
    assert bind_profile("immersive hero-led portfolio") == "SP-react-3d"
    assert bind_profile("dashboard with charts") == "SP-react-data"
    assert bind_profile("product with auth and database") == "SP-next-app"
    assert bind_profile("marketing site with motion") == "SP-react-motion"


def test_source_in_profile_has_empty_delta(tmp_path: Path) -> None:
    regs = load_registries(*_write_regs(tmp_path))
    delta = source_delta(regs, profile_id="SP-static", source_id="animejs")
    assert delta == MigrationDelta("animejs", [], 0, False)


def test_source_not_in_profile_emits_delta_never_omitted(tmp_path: Path) -> None:
    regs = load_registries(*_write_regs(tmp_path))
    delta = source_delta(regs, profile_id="SP-static", source_id="kokonut")
    assert delta.source_id == "kokonut"
    assert delta.extra_deps == ["react", "tailwind", "motion"]
    assert delta.extra_build_steps >= 1
    assert delta.adaptation_required is True


def test_unknown_source_still_emits_delta(tmp_path: Path) -> None:
    regs = load_registries(*_write_regs(tmp_path))
    delta = source_delta(regs, profile_id="SP-static", source_id="no-such-source")
    assert delta.source_id == "no-such-source"
    assert delta.extra_deps != [] or delta.extra_build_steps >= 1 or delta.adaptation_required
