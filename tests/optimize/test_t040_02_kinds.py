"""T-040-02: the kind registry (SPEC §2.3).

Fixtures are written as bytes into temporary folders, so no digest here
depends on how the checkout converted line endings. The pinned manifest
digest is the cross-OS proof: CI runs this file on Linux, macOS and Windows
and every one must produce the same hex.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pytest

from proofhouse.compiler.canonical import canonical_sha256
from proofhouse.optimize import install_skill, kinds
from proofhouse.optimize.case import CaseError, prompt_sha256
from proofhouse.optimize.case_codes import CODES, RETIRED_CODES, CodedCaseError

SKILL_FIXTURE: dict[str, bytes] = {
    "SKILL.md": b"---\nname: demo-skill\ndescription: A demo skill.\n---\n\n# Demo\r\n",
    "scripts/run.py": b"print('hi')\r\n",
    "notes/a b.txt": b"\x00\xffnot text\n",
    "notes/nested/deep.md": "café 日本\n".encode("utf-8"),
}
# Fingerprint of SKILL_FIXTURE's manifest. Same value on every operating system.
SKILL_FIXTURE_DIGEST = "6a4434139734ef79b4fff99f921cb1b442d50b7da00472ed684fdb5eda002bbb"


def _write_folder(root: Path, files: dict[str, bytes]) -> Path:
    for rel, blob in files.items():
        target = root / Path(*rel.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
    return root


def _code(excinfo: pytest.ExceptionInfo[BaseException]) -> str:
    return excinfo.value.code  # type: ignore[attr-defined]


# --- the registry ---------------------------------------------------------------------------


def test_registry_holds_exactly_two_kinds() -> None:
    assert kinds.KIND_IDS == ("prompt.text@1", "agent.skill@1")
    assert kinds.get_kind("prompt.text@1").payload == kinds.PAYLOAD_TEXT
    assert kinds.get_kind("agent.skill@1").payload == kinds.PAYLOAD_FILES


@pytest.mark.parametrize("kind_id", ["prompt.text@2", "agent.skill", "image.png@1", "", "PROMPT.TEXT@1", None, 1])
def test_unknown_kind_is_refused_with_a_code(kind_id: object) -> None:
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.get_kind(kind_id)
    assert _code(excinfo) == "PHC-KIND-0001"
    assert str(excinfo.value).startswith("PHC-KIND-0001: ")
    assert "prompt.text@1, agent.skill@1" in str(excinfo.value)
    assert isinstance(excinfo.value, CaseError)  # the CLI's usage-error path catches it


def test_artifact_digest_refuses_unknown_kind() -> None:
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.artifact_digest("prompt.text@9", "hello")
    assert _code(excinfo) == "PHC-KIND-0001"


# --- prompt.text@1 --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    ["", "hello", "line one\r\nline two\n", "naïve — 日本語 \U0001f680", "  trailing  \n\n"],
)
def test_prompt_digest_equals_prompt_sha256(text: str) -> None:
    assert kinds.text_digest(text) == prompt_sha256(text)
    assert kinds.artifact_digest(kinds.PROMPT_TEXT, text) == prompt_sha256(text)
    assert kinds.text_digest(text) == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_prompt_payload_must_be_text() -> None:
    with pytest.raises(CaseError):
        kinds.artifact_digest(kinds.PROMPT_TEXT, [{"path": "SKILL.md", "sha256": "0" * 64}])


# --- agent.skill@1 manifest and digest --------------------------------------------------------


def test_folder_manifest_is_sorted_forward_slash_paths_with_sha256(tmp_path: Path) -> None:
    root = _write_folder(tmp_path / "skill", SKILL_FIXTURE)
    manifest = kinds.folder_manifest(root)
    assert [entry["path"] for entry in manifest] == sorted(SKILL_FIXTURE)
    for entry in manifest:
        assert set(entry) == {"path", "sha256"}
        assert entry["sha256"] == hashlib.sha256(SKILL_FIXTURE[entry["path"]]).hexdigest()


def test_manifest_digest_uses_the_canonical_helper(tmp_path: Path) -> None:
    manifest = kinds.folder_manifest(_write_folder(tmp_path / "skill", SKILL_FIXTURE))
    assert kinds.manifest_digest(manifest) == canonical_sha256(manifest)
    assert kinds.artifact_digest(kinds.AGENT_SKILL, manifest) == canonical_sha256(manifest)


def test_skill_digest_is_pinned_across_operating_systems(tmp_path: Path) -> None:
    manifest = kinds.folder_manifest(_write_folder(tmp_path / "skill", SKILL_FIXTURE))
    assert kinds.manifest_digest(manifest) == SKILL_FIXTURE_DIGEST


def test_folder_and_in_memory_files_give_the_same_digest(tmp_path: Path) -> None:
    from_folder = kinds.folder_manifest(_write_folder(tmp_path / "skill", SKILL_FIXTURE))
    from_memory = kinds.files_manifest(reversed(list(SKILL_FIXTURE.items())))
    assert from_folder == from_memory


def test_digest_changes_with_content_or_name(tmp_path: Path) -> None:
    base = kinds.manifest_digest(kinds.files_manifest(SKILL_FIXTURE.items()))
    edited = dict(SKILL_FIXTURE, **{"scripts/run.py": b"print('hi')\n"})
    renamed = {("scripts/go.py" if k == "scripts/run.py" else k): v for k, v in SKILL_FIXTURE.items()}
    assert kinds.manifest_digest(kinds.files_manifest(edited.items())) != base
    assert kinds.manifest_digest(kinds.files_manifest(renamed.items())) != base


def test_empty_folders_do_not_change_the_digest(tmp_path: Path) -> None:
    root = _write_folder(tmp_path / "skill", SKILL_FIXTURE)
    before = kinds.manifest_digest(kinds.folder_manifest(root))
    (root / "empty" / "deeper").mkdir(parents=True)
    assert kinds.manifest_digest(kinds.folder_manifest(root)) == before


def test_skill_md_must_be_at_the_root(tmp_path: Path) -> None:
    nested = {"inner/SKILL.md": b"x", "README.md": b"y"}
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.folder_manifest(_write_folder(tmp_path / "nested", nested))
    assert _code(excinfo) == "PHC-SKILL-0001"
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.files_manifest([("skill.md", b"x")])
    assert _code(excinfo) == "PHC-SKILL-0001"


def test_missing_or_non_folder_root_is_refused(tmp_path: Path) -> None:
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.folder_manifest(tmp_path / "absent")
    assert _code(excinfo) == "PHC-SKILL-0007"
    plain = tmp_path / "file.txt"
    plain.write_bytes(b"x")
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.folder_manifest(plain)
    assert _code(excinfo) == "PHC-SKILL-0007"


@pytest.mark.parametrize(
    "path",
    ["/SKILL.md", "a//b.md", "./a.md", "a/./b.md", "a/../b.md", "..", "a\\b.md", "c:x.md", "a/b:c.md", "dir/", "", "a\0b"],
)
def test_unsafe_paths_are_refused(path: str) -> None:
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.files_manifest([("SKILL.md", b"x"), (path, b"y")])
    assert _code(excinfo) == "PHC-SKILL-0002"


@pytest.mark.skipif(sys.platform == "win32", reason="Windows cannot name a file with a backslash or colon")
@pytest.mark.parametrize("name", ["a\\b.md", "c:x.md"])
def test_unsafe_names_on_disk_are_refused(tmp_path: Path, name: str) -> None:
    root = _write_folder(tmp_path / "skill", {"SKILL.md": b"x"})
    (root / name).write_bytes(b"y")
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.folder_manifest(root)
    assert _code(excinfo) == "PHC-SKILL-0002"


@pytest.mark.parametrize("pair", [("a.md", "a.md"), ("Notes.md", "notes.md")])
def test_duplicate_paths_are_refused(pair: tuple[str, str]) -> None:
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.files_manifest([("SKILL.md", b"x"), (pair[0], b"1"), (pair[1], b"2")])
    assert _code(excinfo) == "PHC-SKILL-0006"


def _symlink_or_skip(target: Path, link: Path, *, directory: bool) -> None:
    try:
        os.symlink(target, link, target_is_directory=directory)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"cannot create a symlink here: {exc}")


def test_file_symlink_is_refused(tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"secret")
    root = _write_folder(tmp_path / "skill", {"SKILL.md": b"x"})
    _symlink_or_skip(outside, root / "link.txt", directory=False)
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.folder_manifest(root)
    assert _code(excinfo) == "PHC-SKILL-0003"


def test_directory_symlink_is_refused(tmp_path: Path) -> None:
    outside = _write_folder(tmp_path / "outside", {"secret.txt": b"secret"})
    root = _write_folder(tmp_path / "skill", {"SKILL.md": b"x"})
    _symlink_or_skip(outside, root / "linked", directory=True)
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.folder_manifest(root)
    assert _code(excinfo) == "PHC-SKILL-0003"


def test_root_that_is_a_link_is_refused(tmp_path: Path) -> None:
    real = _write_folder(tmp_path / "real", {"SKILL.md": b"x"})
    _symlink_or_skip(real, tmp_path / "alias", directory=True)
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.folder_manifest(tmp_path / "alias")
    assert _code(excinfo) == "PHC-SKILL-0003"


@pytest.mark.skipif(sys.platform != "win32", reason="directory junctions exist only on Windows")
def test_directory_junction_is_refused(tmp_path: Path) -> None:
    import _winapi  # type: ignore[import-not-found]

    outside = _write_folder(tmp_path / "outside", {"secret.txt": b"secret"})
    root = _write_folder(tmp_path / "skill", {"SKILL.md": b"x"})
    _winapi.CreateJunction(str(outside), str(root / "junction"))
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.folder_manifest(root)
    assert _code(excinfo) == "PHC-SKILL-0003"


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="named pipes need os.mkfifo")
def test_special_file_is_refused(tmp_path: Path) -> None:
    root = _write_folder(tmp_path / "skill", {"SKILL.md": b"x"})
    os.mkfifo(root / "pipe")
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.folder_manifest(root)
    assert _code(excinfo) == "PHC-SKILL-0003"


def test_limits_are_todays_installer_limits() -> None:
    assert kinds.MAX_UNCOMPRESSED_BYTES == 16 * 1024 * 1024
    assert kinds.MAX_ENTRIES == 256
    assert install_skill.MAX_UNCOMPRESSED_BYTES == kinds.MAX_UNCOMPRESSED_BYTES
    assert install_skill.MAX_ENTRIES == kinds.MAX_ENTRIES


def test_over_size_folder_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(kinds, "MAX_UNCOMPRESSED_BYTES", 10)
    root = _write_folder(tmp_path / "skill", {"SKILL.md": b"12345", "b.txt": b"678901"})
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.folder_manifest(root)
    assert _code(excinfo) == "PHC-SKILL-0004"
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.files_manifest([("SKILL.md", b"12345"), ("b.txt", b"678901")])
    assert _code(excinfo) == "PHC-SKILL-0004"


def test_real_size_limit_is_enforced_in_memory() -> None:
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.files_manifest([("SKILL.md", b"x"), ("big.bin", b"\0" * kinds.MAX_UNCOMPRESSED_BYTES)])
    assert _code(excinfo) == "PHC-SKILL-0004"


def test_over_entry_folder_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(kinds, "MAX_ENTRIES", 3)
    files = {"SKILL.md": b"x", "a.txt": b"a", "b.txt": b"b", "c.txt": b"c"}
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.folder_manifest(_write_folder(tmp_path / "skill", files))
    assert _code(excinfo) == "PHC-SKILL-0005"
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.files_manifest(files.items())
    assert _code(excinfo) == "PHC-SKILL-0005"


def test_folders_count_toward_the_entry_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(kinds, "MAX_ENTRIES", 3)
    root = _write_folder(tmp_path / "skill", {"SKILL.md": b"x"})
    for name in ("d1", "d2", "d3"):
        (root / name).mkdir()
    with pytest.raises(CodedCaseError) as excinfo:
        kinds.folder_manifest(root)
    assert _code(excinfo) == "PHC-SKILL-0005"


# --- stored manifests -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "manifest",
    [
        "not a list",
        [],
        [{"path": "SKILL.md"}],
        [{"path": "SKILL.md", "sha256": "0" * 64, "extra": 1}],
        [{"path": "SKILL.md", "sha256": "ABC"}],
        [{"path": "b.md", "sha256": "0" * 64}, {"path": "SKILL.md", "sha256": "0" * 64}],
        [{"path": "SKILL.md", "sha256": "0" * 64}, {"path": "SKILL.md", "sha256": "1" * 64}],
        [{"path": "SKILL.md", "sha256": "0" * 64}, {"path": "../x", "sha256": "1" * 64}],
    ],
)
def test_malformed_stored_manifest_is_refused(manifest: object) -> None:
    with pytest.raises(CodedCaseError):
        kinds.manifest_digest(manifest)  # type: ignore[arg-type]


# --- the code table ---------------------------------------------------------------------------

# Append-only: a code's meaning never changes and a code is never reused.
PINNED_CODES = {
    "PHC-KIND-0001": "unknown artifact kind",
    "PHC-SKILL-0001": "skill files have no SKILL.md at their root",
    "PHC-SKILL-0002": "unsafe path in skill files",
    "PHC-SKILL-0003": "link, junction or special file in a skill folder",
    "PHC-SKILL-0004": "skill files exceed the size limit",
    "PHC-SKILL-0005": "skill files exceed the entry limit",
    "PHC-SKILL-0006": "duplicate path in skill files",
    "PHC-SKILL-0007": "skill folder missing or unreadable",
    "PHC-SKILL-0008": "malformed skill file manifest",
}


def test_codes_are_append_only() -> None:
    assert {code: CODES[code] for code in PINNED_CODES} == PINNED_CODES
    assert not set(RETIRED_CODES) & set(CODES)


def test_unregistered_code_cannot_be_raised() -> None:
    with pytest.raises(ValueError):
        CodedCaseError("PHC-NOT-REAL-9999", "nope")
