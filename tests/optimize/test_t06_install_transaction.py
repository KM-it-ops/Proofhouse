"""T06 (review F08): a failed forced install leaves the previous installation unchanged.

On 78e512c ``install --force`` deleted the existing skill, extracted, then
checked frontmatter; a verification failure removed the new directory and
the user's previous installation (including local modifications) was gone.
Backups live under ``PROOFHOUSE_HOME``, never beside the skill, so the host
never loads a second copy.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from proofhouse.optimize import install_skill
from proofhouse.optimize.install_skill import InstallSkillError, install

GOOD_MD = "---\nname: proofhouse\ndescription: test\n---\n\n# new body\n"


def _bundle(path: Path, entries: dict[str, str | bytes]) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return path


@pytest.fixture()
def existing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    dest = tmp_path / "skills"
    old = dest / "proofhouse"
    old.mkdir(parents=True)
    (old / "SKILL.md").write_text("---\nname: proofhouse\n---\nold\n", encoding="utf-8")
    (old / "custom.txt").write_text("user modification", encoding="utf-8")
    return dest


def _snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _assert_unchanged(dest: Path, before: dict[str, bytes]) -> None:
    assert _snapshot(dest) == before
    leftovers = [p.name for p in dest.iterdir() if p.name != "proofhouse"]
    assert leftovers == [], leftovers


def test_probe_invalid_frontmatter_force_install_preserves_previous(existing: Path, tmp_path: Path) -> None:
    before = _snapshot(existing)
    bundle = _bundle(tmp_path / "invalid.skill", {"proofhouse/SKILL.md": "invalid frontmatter"})
    with pytest.raises(InstallSkillError):
        install(existing, bundle, force=True)
    _assert_unchanged(existing, before)


def test_extraction_failure_preserves_previous(existing: Path, tmp_path: Path, monkeypatch) -> None:
    before = _snapshot(existing)
    bundle = _bundle(tmp_path / "ok.skill", {"proofhouse/SKILL.md": GOOD_MD, "proofhouse/a.txt": "a"})

    def explode(self, *args, **kwargs):
        raise OSError("simulated interruption during extraction")

    monkeypatch.setattr(zipfile.ZipFile, "extractall", explode)
    monkeypatch.setattr(zipfile.ZipFile, "extract", explode)
    with pytest.raises(InstallSkillError):
        install(existing, bundle, force=True)
    _assert_unchanged(existing, before)


def test_swap_failure_rolls_back(existing: Path, tmp_path: Path, monkeypatch) -> None:
    before = _snapshot(existing)
    bundle = _bundle(tmp_path / "ok.skill", {"proofhouse/SKILL.md": GOOD_MD})
    real_replace = install_skill._move
    calls = {"n": 0}

    def flaky(src: Path, dst: Path) -> None:
        calls["n"] += 1
        if calls["n"] == 2:  # first move = old -> backup succeeds; second = staged -> live fails
            raise PermissionError("simulated lock on destination")
        real_replace(src, dst)

    monkeypatch.setattr(install_skill, "_move", flaky)
    with pytest.raises(InstallSkillError, match="restored"):
        install(existing, bundle, force=True)
    _assert_unchanged(existing, before)


def test_successful_force_install_keeps_a_rollback_backup_outside_skills_dir(existing: Path, tmp_path: Path) -> None:
    bundle = _bundle(tmp_path / "ok.skill", {"proofhouse/SKILL.md": GOOD_MD})
    result = install(existing, bundle, force=True)
    assert (existing / "proofhouse" / "SKILL.md").read_text(encoding="utf-8") == GOOD_MD
    assert not (existing / "proofhouse" / "custom.txt").exists()
    assert result.backup is not None
    assert (result.backup / "custom.txt").read_text(encoding="utf-8") == "user modification"
    assert existing not in result.backup.parents
    assert (tmp_path / "home") in result.backup.parents
    assert [p.name for p in existing.iterdir()] == ["proofhouse"]


def test_fresh_install_has_no_backup(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    result = install(tmp_path / "skills", _bundle(tmp_path / "ok.skill", {"proofhouse/SKILL.md": GOOD_MD}))
    assert result.backup is None


@pytest.mark.parametrize(
    "name",
    [
        "proofhouse/..\\evil.txt",
        "proofhouse\\..\\evil.txt",
        "proofhouse/C:/evil.txt",
        "proofhouse//abs.txt",
        "proofhouse/sub/../../evil.txt",
        "/proofhouse/abs.txt",
    ],
)
def test_windows_and_absolute_path_variants_are_refused(existing: Path, tmp_path: Path, name: str) -> None:
    before = _snapshot(existing)
    bundle = _bundle(tmp_path / "bad.skill", {"proofhouse/SKILL.md": GOOD_MD, name: "x"})
    with pytest.raises(InstallSkillError):
        install(existing, bundle, force=True)
    _assert_unchanged(existing, before)


def test_oversized_bundle_is_refused_before_touching_anything(existing: Path, tmp_path: Path) -> None:
    before = _snapshot(existing)
    big = b"\0" * (install_skill.MAX_UNCOMPRESSED_BYTES + 1)
    bundle = _bundle(tmp_path / "big.skill", {"proofhouse/SKILL.md": GOOD_MD, "proofhouse/big.bin": big})
    with pytest.raises(InstallSkillError, match="too large"):
        install(existing, bundle, force=True)
    _assert_unchanged(existing, before)
