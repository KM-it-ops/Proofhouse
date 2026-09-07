"""The committed skill bundle must match its source directory.

`skills/proofhouse/proofhouse.skill` is a zip of `skills/proofhouse/`, committed
as an artifact. It was hand-packed once and then drifted unnoticed for two
months, shipping framework v1.2 against a v1.3 source. These tests are the gate
that makes that impossible to repeat: the bundle is now built by
`scripts/build_skill_bundle.py`, and a stale bundle fails here.
"""

from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE = REPO_ROOT / "skills" / "proofhouse" / "proofhouse.skill"


def _load_builder():
    path = REPO_ROOT / "scripts" / "build_skill_bundle.py"
    spec = importlib.util.spec_from_file_location("build_skill_bundle", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_skill_bundle"] = module
    spec.loader.exec_module(module)
    return module


def test_committed_bundle_matches_source_directory() -> None:
    """Every source file is present in the bundle with identical content."""
    builder = _load_builder()
    expected = {
        builder.entry_name(p): builder.entry_bytes(p) for p in builder.source_files()
    }
    assert expected, "no source files found for the skill bundle"

    with zipfile.ZipFile(BUNDLE) as archive:
        actual = {name: archive.read(name) for name in archive.namelist()}

    assert set(actual) == set(expected), (
        "bundle entries do not match the source directory; "
        "run scripts/build_skill_bundle.py"
    )
    for name, content in expected.items():
        assert actual[name] == content, (
            f"{name} in the bundle differs from its source; "
            "run scripts/build_skill_bundle.py"
        )


def test_committed_bundle_matches_regenerated_output(tmp_path: Path) -> None:
    """Rebuilding produces the committed bytes exactly.

    The build fixes timestamps, attributes and entry order, and normalises text
    to LF, so this holds regardless of which platform packed the bundle.
    """
    builder = _load_builder()
    rebuilt = builder.build(tmp_path / "rebuilt.skill")
    assert rebuilt.read_bytes() == BUNDLE.read_bytes(), (
        "committed bundle differs from a fresh build; "
        "run scripts/build_skill_bundle.py and commit the result"
    )


def test_bundle_carries_the_current_framework_version() -> None:
    """The exact drift that went unnoticed: bundle version vs source version."""
    source = (
        REPO_ROOT / "skills" / "proofhouse" / "references" / "proofhouse-framework.json"
    ).read_text(encoding="utf-8")
    with zipfile.ZipFile(BUNDLE) as archive:
        bundled = archive.read(
            "proofhouse/references/proofhouse-framework.json"
        ).decode("utf-8")

    import json

    assert json.loads(bundled)["version"] == json.loads(source)["version"]
