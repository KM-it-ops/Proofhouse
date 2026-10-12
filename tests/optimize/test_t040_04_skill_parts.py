"""T-040-04 (SECURITY-RELEVANT): skill checker, generalised installer and uninstall (SPEC §2.5).

Also the conformance suite of the ``skill-checker`` and ``install-skill`` parts.

Every test points the host skills folder, ``Path.home()`` and
``PROOFHOUSE_HOME`` at temporary folders; nothing here can reach a real home
folder or a real host. Refusals that only zip input can express on Windows
(a name ending in a dot or space, a reserved device name, a backslash) are
tested through zip input on every OS, and through folder input where the OS
lets the test create such a file.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import stat
import sys
import zipfile
from pathlib import Path

import pytest

from proofhouse import parts
from proofhouse.compiler import cli_compiler
from proofhouse.optimize import case as case_mod
from proofhouse.optimize import install_skill
from proofhouse.optimize.case_codes import CodedCaseError
from proofhouse.optimize.install_skill import InstallSkillError, install, uninstall
from proofhouse.optimize.kinds import (
    AGENT_SKILL,
    MAX_ENTRIES,
    MAX_UNCOMPRESSED_BYTES,
    check_path,
)
from proofhouse.optimize.model_notes import resolve_model_notes
from proofhouse.optimize.registry import PACKAGE_BUNDLE_PATH

SKILL = {
    "SKILL.md": b"---\nname: demo-skill\ndescription: A demo skill.\n---\n\n# Demo\n",
    "scripts/run.py": b"print('hi')\r\n",
    "notes/a b.txt": b"\x00\xffnot text\n",
}
RESERVED = ["con", "prn", "aux", "nul", "com1", "com9", "lpt1", "lpt9", "CON", "Nul", "com0", "lpt0", "CONIN$", "clock$"]
NOT_PORTABLE = [
    *RESERVED, *(f"{name}.txt" for name in RESERVED[:4]), "conout$.txt", "a.", "b ", "c. ", "d .", "q?", "s*", "l<", "p|",
]
BAD_NAMES = [
    "Demo", "demo_skill", "demo.skill", "demo skill", "-demo", "", "a" * 65, "c:", "../demo", "demo/x", "demo\\x",
    "con", "nul", "aux", "prn", "com1", "lpt9", "demo.",
]
# A typed name keeps its trailing space; in frontmatter YAML drops it, so it is only a typed-name case.
BAD_TYPED_NAMES = [*BAD_NAMES, "demo ", " demo"]
links_supported = pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
posix_only = pytest.mark.skipif(sys.platform == "win32", reason="Windows cannot create this file name")


@pytest.fixture(autouse=True)
def _sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "user-home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "ph"))


@pytest.fixture()
def host(tmp_path: Path) -> Path:
    return tmp_path / "host" / "skills"


def skill_folder(root: Path, files: dict[str, bytes] = SKILL) -> Path:
    for rel, blob in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
    return root


def zip_bundle(path: Path, entries: dict[str, bytes], links: dict[str, str] | None = None) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, blob in entries.items():
            archive.writestr(name, blob)
        for name, target in (links or {}).items():
            info = zipfile.ZipInfo(name)
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, target)
    return path


def skill_zip(path: Path, top: str = "demo-skill", extra: dict[str, bytes] | None = None) -> Path:
    entries = {f"{top}/{rel}": blob for rel, blob in SKILL.items()}
    entries.update(extra or {})
    return zip_bundle(path, entries)


def link_folder(link: Path, target: Path) -> Path:
    """A folder link any user can make: a directory junction on Windows, a symlink elsewhere."""
    if sys.platform == "win32":
        import subprocess

        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)
    else:
        os.symlink(target, link, target_is_directory=True)
    return link


def snapshot(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def state(root: Path) -> str:
    return install_skill.folder_state_digest(root)


def run(argv: list[str], capsys) -> tuple[int, str, str]:
    code = cli_compiler.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# --- names, from frontmatter -----------------------------------------------------------------


@pytest.mark.parametrize("name", BAD_NAMES)
def test_bad_skill_name_in_frontmatter_is_refused(tmp_path: Path, host: Path, name: str) -> None:
    src = skill_folder(tmp_path / "src", {**SKILL, "SKILL.md": f"---\nname: {name}\ndescription: x\n---\n".encode()})
    with pytest.raises(InstallSkillError) as info:
        install(host, src)
    assert info.value.exit_code == 7
    assert not host.exists()


@pytest.mark.parametrize("name", BAD_TYPED_NAMES)
def test_bad_skill_name_is_refused_by_uninstall(host: Path, name: str) -> None:
    with pytest.raises(InstallSkillError) as info:
        uninstall(name, host)
    assert info.value.exit_code == 2


@pytest.mark.parametrize("name", ["a", "demo-skill", "0", "a" * 64, "x-1-y"])
def test_good_skill_names_are_accepted(name: str) -> None:
    assert install_skill.skill_name_problem(name) is None


def test_name_comes_from_frontmatter_not_the_folder(tmp_path: Path, host: Path) -> None:
    src = skill_folder(tmp_path / "Some Folder.v2")
    result = install(host, src)
    assert result.name == "demo-skill"
    assert result.dest == (host / "demo-skill").resolve()
    assert snapshot(result.dest) == SKILL


def test_zip_folder_name_must_match_frontmatter_name(tmp_path: Path, host: Path) -> None:
    bundle = skill_zip(tmp_path / "b.zip", top="other-name")
    with pytest.raises(InstallSkillError, match="lacks the line 'name: other-name'") as info:
        install(host, bundle)
    assert info.value.exit_code == 7
    assert not host.exists()


@pytest.mark.parametrize(
    "skill_md",
    [
        "---\nname: demo-skill\n---\n",
        "---\nname: demo-skill\ndescription:\n---\n",
        "---\nname: demo-skill\ndescription: \"\"\n---\n",
        "---\nname: demo-skill\ndescription: >\n---\n",
        "---\nname: demo-skill\nname: demo-skill\ndescription: x\n---\n",
        "---\nname: demo-skill\ndescription: x\n",
        "name: demo-skill\ndescription: x\n",
        "---\n  name: demo-skill\ndescription: x\n---\n",
    ],
)
def test_frontmatter_needs_one_name_and_a_description(tmp_path: Path, host: Path, skill_md: str) -> None:
    src = skill_folder(tmp_path / "src", {**SKILL, "SKILL.md": skill_md.encode()})
    with pytest.raises(InstallSkillError, match="failed verification"):
        install(host, src)
    assert not host.exists()


def test_block_scalar_description_is_accepted(tmp_path: Path, host: Path) -> None:
    md = b"---\nname: demo-skill\ndescription: >\n  Folded text\n  over two lines.\n---\nbody\n"
    src = skill_folder(tmp_path / "src", {**SKILL, "SKILL.md": md})
    assert install(host, src).name == "demo-skill"


# --- entries: traversal, links, portability, limits ------------------------------------------


@pytest.mark.parametrize(
    "evil",
    [
        "../evil", "demo-skill/../evil", "demo-skill/sub/../../evil", "/demo-skill/abs", "demo-skill//x",
        "demo-skill/./x", "demo-skill\\..\\evil", "demo-skill/C:/x", "demo-skill/c:x", "other/SKILL.md",
    ],
)
def test_zip_path_traversal_is_refused_before_anything_is_written(tmp_path: Path, host: Path, evil: str) -> None:
    bundle = skill_zip(tmp_path / "b.zip", extra={evil: b"x"})
    with pytest.raises(InstallSkillError, match="bundle unreadable") as info:
        install(host, bundle)
    assert info.value.exit_code == 7
    assert not host.exists()
    assert not (tmp_path / "evil").exists()


@pytest.mark.parametrize("segment", NOT_PORTABLE)
def test_zip_entries_not_portable_to_every_os_are_refused_on_every_os(tmp_path: Path, host: Path, segment: str) -> None:
    bundle = skill_zip(tmp_path / "b.zip", extra={f"demo-skill/notes/{segment}": b"x"})
    with pytest.raises(InstallSkillError, match="PHC-SKILL-0009") as info:
        install(host, bundle)
    assert info.value.exit_code == 7
    assert not host.exists()


@pytest.mark.parametrize("segment", NOT_PORTABLE)
def test_check_path_refuses_names_not_portable_to_every_os(segment: str) -> None:
    for path in (segment, f"dir/{segment}", f"{segment}/SKILL.md"):
        with pytest.raises(CodedCaseError) as info:
            check_path(path)
        assert info.value.code == "PHC-SKILL-0009"


@pytest.mark.parametrize("ok", ["console.txt", "con-fig", "nul1", "com10", "lpt", "a.b.c", "auxiliary", ".hidden", "x y"])
def test_check_path_accepts_names_that_only_resemble_reserved_ones(ok: str) -> None:
    check_path(ok)


@posix_only
@pytest.mark.parametrize("segment", ["CON", "aux.txt", "nul", "com1", "CONIN$", "a.", "b ", "q?", "back\\slash", "co:lon"])
def test_folder_entries_not_portable_are_refused(tmp_path: Path, host: Path, segment: str) -> None:
    src = skill_folder(tmp_path / "src", {**SKILL, f"notes/{segment}": b"x"})
    with pytest.raises(InstallSkillError, match="skill folder refused") as info:
        install(host, src)
    assert info.value.exit_code == 7
    assert not host.exists()


def test_zip_link_entry_is_refused(tmp_path: Path, host: Path) -> None:
    bundle = zip_bundle(
        tmp_path / "b.zip",
        {f"demo-skill/{rel}": blob for rel, blob in SKILL.items()},
        links={"demo-skill/escape": "../../../../etc/passwd"},
    )
    with pytest.raises(InstallSkillError, match="link entry"):
        install(host, bundle)
    assert not host.exists()


@links_supported
def test_folder_with_a_file_link_is_refused(tmp_path: Path, host: Path) -> None:
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    src = skill_folder(tmp_path / "src")
    os.symlink(outside, src / "notes" / "leak.txt")
    with pytest.raises(InstallSkillError, match="PHC-SKILL-0003"):
        install(host, src)
    assert not host.exists()


@links_supported
def test_folder_with_a_folder_link_is_refused(tmp_path: Path, host: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "x.txt").write_text("x", encoding="utf-8")
    src = skill_folder(tmp_path / "src")
    os.symlink(outside, src / "linked", target_is_directory=True)
    with pytest.raises(InstallSkillError, match="PHC-SKILL-0003"):
        install(host, src)
    assert not host.exists()


def test_skill_folder_that_is_itself_a_link_is_refused(tmp_path: Path, host: Path) -> None:
    real = skill_folder(tmp_path / "real")
    link = link_folder(tmp_path / "link", real)
    with pytest.raises(InstallSkillError, match="PHC-SKILL-0003"):
        install(host, link)
    assert not host.exists()


def test_a_file_replaced_while_the_folder_is_read_is_refused(tmp_path: Path, host: Path, monkeypatch) -> None:
    src = skill_folder(tmp_path / "src")
    victim = src / "scripts" / "run.py"
    real_open = os.open

    def replace_then_open(path, flags, *args, **kwargs):
        if Path(path) == victim:  # checked by lstat already; now something else takes its place
            spare = victim.with_name("spare.tmp")
            spare.write_bytes(b"swapped in after the check\n")
            os.replace(spare, victim)
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", replace_then_open)
    with pytest.raises(InstallSkillError, match="PHC-SKILL-0003"):
        install(host, src)
    assert not host.exists()


@pytest.mark.skipif(sys.platform != "win32", reason="directory junctions exist only on Windows")
def test_folder_with_a_junction_is_refused(tmp_path: Path, host: Path) -> None:
    import subprocess

    outside = tmp_path / "outside"
    outside.mkdir()
    src = skill_folder(tmp_path / "src")
    subprocess.run(["cmd", "/c", "mklink", "/J", str(src / "junction"), str(outside)], check=True, capture_output=True)
    with pytest.raises(InstallSkillError, match="PHC-SKILL-0003"):
        install(host, src)
    assert not host.exists()


def test_zip_with_too_many_entries_is_refused(tmp_path: Path, host: Path) -> None:
    extra = {f"demo-skill/many/f{i}.txt": b"x" for i in range(MAX_ENTRIES)}
    with pytest.raises(InstallSkillError, match=f"more than {MAX_ENTRIES} entries"):
        install(host, skill_zip(tmp_path / "b.zip", extra=extra))
    assert not host.exists()


def test_folder_with_too_many_entries_is_refused(tmp_path: Path, host: Path) -> None:
    src = skill_folder(tmp_path / "src", {**SKILL, **{f"many/f{i}.txt": b"x" for i in range(MAX_ENTRIES)}})
    with pytest.raises(InstallSkillError, match="PHC-SKILL-0005"):
        install(host, src)
    assert not host.exists()


def test_oversize_zip_is_refused(tmp_path: Path, host: Path) -> None:
    big = {"demo-skill/big.bin": b"\0" * (MAX_UNCOMPRESSED_BYTES + 1)}
    with pytest.raises(InstallSkillError, match="too large"):
        install(host, skill_zip(tmp_path / "b.zip", extra=big))
    assert not host.exists()


def test_oversize_folder_is_refused(tmp_path: Path, host: Path) -> None:
    src = skill_folder(tmp_path / "src", {**SKILL, "big.bin": b"\0" * (MAX_UNCOMPRESSED_BYTES + 1)})
    with pytest.raises(InstallSkillError, match="PHC-SKILL-0004"):
        install(host, src)
    assert not host.exists()


def test_zip_entries_that_collide_on_a_case_insensitive_disk_are_refused(tmp_path: Path, host: Path) -> None:
    with pytest.raises(InstallSkillError, match="PHC-SKILL-0006"):
        install(host, skill_zip(tmp_path / "b.zip", extra={"demo-skill/Notes/x.txt": b"x"}))
    assert not host.exists()


# --- install: zip or folder, staging, rollback ------------------------------------------------


def test_folder_and_zip_of_the_same_skill_install_the_same_bytes(tmp_path: Path) -> None:
    a = install(tmp_path / "a", skill_folder(tmp_path / "src"))
    b = install(tmp_path / "b", skill_zip(tmp_path / "b.zip"))
    assert snapshot(a.dest) == snapshot(b.dest) == SKILL
    assert a.digest == b.digest == install_skill.installed_digest(a.dest)
    assert a.files == b.files == tuple(sorted(f"demo-skill/{rel}" for rel in SKILL))


def test_default_install_is_the_0_4_1_install(tmp_path: Path, host: Path) -> None:
    result = install(host)
    with zipfile.ZipFile(PACKAGE_BUNDLE_PATH) as archive:
        expected = {
            info.filename[len("proofhouse/"):]: archive.read(info)
            for info in archive.infolist()
            if not info.filename.endswith("/")
        }
    assert result.dest == (host / "proofhouse").resolve()
    assert snapshot(result.dest) == expected
    assert sorted(p.name for p in host.iterdir()) == ["proofhouse"]  # no record or backup beside it
    assert result.backup is None and result.leftover is None


def test_rollback_after_a_failed_swap_restores_the_previous_install(tmp_path: Path, host: Path, monkeypatch) -> None:
    old = skill_folder(host / "demo-skill", {**SKILL, "SKILL.md": b"---\nname: demo-skill\ndescription: old\n---\n"})
    (old / "mine.txt").write_text("user file", encoding="utf-8")
    before = snapshot(host)
    real = install_skill._move
    calls = {"n": 0}

    def flaky(src: Path, dst: Path) -> None:
        calls["n"] += 1
        if calls["n"] == 2:  # live -> aside works; staged -> live fails
            raise PermissionError("simulated lock")
        real(src, dst)

    monkeypatch.setattr(install_skill, "_move", flaky)
    with pytest.raises(InstallSkillError, match="previous installation restored"):
        install(host, skill_folder(tmp_path / "src"), force=True)
    assert snapshot(host) == before
    assert sorted(p.name for p in host.iterdir()) == ["demo-skill"]
    # The failed install left no record behind, so uninstall cannot claim the old folder.
    with pytest.raises(InstallSkillError, match="no record"):
        uninstall("demo-skill", host)


def test_forced_install_refuses_a_skill_folder_holding_a_link(tmp_path: Path, host: Path) -> None:
    outside = skill_folder(tmp_path / "outside", {"secret.txt": b"secret", "deep/x.txt": b"x"})
    skill_folder(host / "demo-skill", {"SKILL.md": b"---\nname: demo-skill\ndescription: mine\n---\n"})
    link_folder(host / "demo-skill" / "linked", outside)
    before = state(host)
    with pytest.raises(InstallSkillError, match="link") as info:
        install(host, skill_folder(tmp_path / "src"), force=True)
    assert info.value.exit_code == 2
    assert state(host) == before
    assert snapshot(outside) == {"secret.txt": b"secret", "deep/x.txt": b"x"}
    assert not (tmp_path / "ph" / install_skill.BACKUP_DIR).exists()  # nothing was copied out of the link
    assert not (tmp_path / "ph" / install_skill.INSTALLS_DIR).exists()


def test_forced_install_refuses_a_skill_folder_that_is_a_link(tmp_path: Path, host: Path) -> None:
    target = skill_folder(tmp_path / "elsewhere")
    host.mkdir(parents=True)
    link_folder(host / "demo-skill", target)
    with pytest.raises(InstallSkillError, match="link") as info:
        install(host, skill_folder(tmp_path / "src", {**SKILL, "v2.txt": b"v2"}), force=True)
    assert info.value.exit_code == 2
    assert install_skill._is_link(host / "demo-skill")  # still the link, not a copy of its target
    assert snapshot(target) == SKILL
    assert not (tmp_path / "ph" / install_skill.BACKUP_DIR).exists()


def test_zip_install_writes_the_bytes_it_checked_even_if_the_zip_changes(tmp_path: Path, host: Path, monkeypatch) -> None:
    bundle = skill_zip(tmp_path / "b.zip")
    real_read = install_skill.read_skill

    def read_then_swap(source, dest_dir=None):
        skill = real_read(source, dest_dir)
        bundle.unlink()  # after the check, the zip on disk becomes something else
        skill_zip(bundle, extra={"demo-skill/unchecked.txt": b"never validated"})
        return skill

    monkeypatch.setattr(install_skill, "read_skill", read_then_swap)
    result = install(host, bundle)
    assert snapshot(result.dest) == SKILL


def test_forced_install_refuses_a_backup_that_does_not_match_the_folder(tmp_path: Path, host: Path, monkeypatch) -> None:
    skill_folder(host / "demo-skill", {"SKILL.md": b"---\nname: demo-skill\ndescription: mine\n---\n"})
    before = snapshot(host)
    real_copytree = shutil.copytree

    def copy_then_change(src, dst, *args, **kwargs):
        real_copytree(src, dst, *args, **kwargs)
        (Path(dst) / "late.txt").write_text("written while the backup was taken", encoding="utf-8")

    monkeypatch.setattr(shutil, "copytree", copy_then_change)
    with pytest.raises(InstallSkillError, match="changed while it was being backed up") as info:
        install(host, skill_folder(tmp_path / "src"), force=True)
    assert info.value.exit_code == 7
    assert snapshot(host) == before
    assert sorted(p.name for p in host.iterdir()) == ["demo-skill"]
    with pytest.raises(InstallSkillError, match="no record"):
        uninstall("demo-skill", host)


def test_install_never_writes_outside_the_skill_folder_and_home(tmp_path: Path, host: Path) -> None:
    install(host, skill_folder(tmp_path / "src"))
    assert sorted(p.name for p in host.iterdir()) == ["demo-skill"]
    assert not any((tmp_path / "user-home").iterdir())  # Path.home() untouched
    records = list((tmp_path / "ph" / install_skill.INSTALLS_DIR).iterdir())
    assert len(records) == 1


# --- uninstall ------------------------------------------------------------------------------


def test_uninstall_of_a_fresh_install_removes_it_and_leaves_the_folder_as_before(tmp_path: Path, host: Path) -> None:
    other = skill_folder(host / "other", {"SKILL.md": b"---\nname: other\ndescription: o\n---\n"})
    before = state(host)
    install(host, skill_folder(tmp_path / "src"))
    result = uninstall("demo-skill", host)
    assert result.restored is None and not result.forced and result.safety_backup is None
    assert state(host) == before
    assert snapshot(other) == {"SKILL.md": b"---\nname: other\ndescription: o\n---\n"}
    with pytest.raises(InstallSkillError, match="no record"):
        uninstall("demo-skill", host)


def test_uninstall_restores_the_backup_the_install_replaced(tmp_path: Path, host: Path) -> None:
    prior = {"SKILL.md": b"---\nname: demo-skill\ndescription: user's own\n---\n", "mine.txt": b"keep me"}
    skill_folder(host / "demo-skill", prior)
    before = state(host)
    result = install(host, skill_folder(tmp_path / "src"), force=True)
    assert result.backup is not None
    restored = uninstall("demo-skill", host)
    assert restored.restored == result.backup
    assert snapshot(host / "demo-skill") == prior
    assert state(host) == before


def test_uninstall_walks_back_through_each_install(tmp_path: Path, host: Path) -> None:
    prior = {"SKILL.md": b"---\nname: demo-skill\ndescription: prior\n---\n"}
    v2 = {**SKILL, "extra.txt": b"v2"}
    skill_folder(host / "demo-skill", prior)
    install(host, skill_folder(tmp_path / "v1"), force=True)
    install(host, skill_folder(tmp_path / "v2", v2), force=True)
    uninstall("demo-skill", host)
    assert snapshot(host / "demo-skill") == SKILL
    uninstall("demo-skill", host)
    assert snapshot(host / "demo-skill") == prior
    with pytest.raises(InstallSkillError, match="no record"):
        uninstall("demo-skill", host)


def test_reinstalling_the_same_skill_changes_nothing(tmp_path: Path, host: Path) -> None:
    src = skill_folder(tmp_path / "src")
    install(host, src)
    after_first = state(host)
    record = install_skill._record_path((host / "demo-skill").resolve(), None)
    history = json.loads(record.read_text(encoding="utf-8"))["history"]
    install(host, src, force=True)
    assert state(host) == after_first
    assert json.loads(record.read_text(encoding="utf-8"))["history"] == history
    uninstall("demo-skill", host)
    assert not (host / "demo-skill").exists()


def test_uninstall_refuses_a_folder_it_did_not_install(host: Path) -> None:
    skill_folder(host / "demo-skill")
    before = snapshot(host)
    with pytest.raises(InstallSkillError, match="no record") as info:
        uninstall("demo-skill", host, force=True)
    assert info.value.exit_code == 2
    assert snapshot(host) == before


def test_uninstall_refuses_a_changed_folder_unless_forced_then_backs_it_up(tmp_path: Path, host: Path) -> None:
    install(host, skill_folder(tmp_path / "src"))
    (host / "demo-skill" / "notes" / "edited.txt").write_text("my edit", encoding="utf-8")
    changed = snapshot(host / "demo-skill")
    with pytest.raises(InstallSkillError, match="no longer matches") as info:
        uninstall("demo-skill", host)
    assert info.value.exit_code == 2
    assert snapshot(host / "demo-skill") == changed

    result = uninstall("demo-skill", host, force=True)
    assert result.forced
    assert result.safety_backup is not None
    assert snapshot(result.safety_backup) == changed
    assert (tmp_path / "ph") in result.safety_backup.parents
    assert not (host / "demo-skill").exists()


def test_uninstall_removes_a_link_never_what_it_points_at(tmp_path: Path, host: Path) -> None:
    install(host, skill_folder(tmp_path / "src"))
    target = skill_folder(tmp_path / "elsewhere")
    shutil.rmtree(host / "demo-skill")
    link_folder(host / "demo-skill", target)
    with pytest.raises(InstallSkillError, match="no longer matches"):
        uninstall("demo-skill", host)
    result = uninstall("demo-skill", host, force=True)
    assert not os.path.lexists(host / "demo-skill")
    assert snapshot(target) == SKILL  # what the link pointed at is untouched
    assert result.safety_backup is not None
    note = result.safety_backup.parent / "demo-skill.link.txt"
    assert str(target) in note.read_text(encoding="utf-8")


def test_uninstall_touches_nothing_outside_the_skill_folder(tmp_path: Path, host: Path) -> None:
    skill_folder(host / "other", {"SKILL.md": b"---\nname: other\ndescription: o\n---\n", "o.txt": b"o"})
    (host / "loose.txt").write_text("loose", encoding="utf-8")
    install(host, skill_folder(tmp_path / "src"))
    before_other = snapshot(host / "other")
    uninstall("demo-skill", host)
    assert snapshot(host / "other") == before_other
    assert (host / "loose.txt").read_text(encoding="utf-8") == "loose"
    assert sorted(p.name for p in host.iterdir()) == ["loose.txt", "other"]


def test_uninstall_refuses_a_record_whose_backup_points_outside_the_backup_area(tmp_path: Path, host: Path) -> None:
    skill_folder(host / "demo-skill", {"SKILL.md": b"---\nname: demo-skill\ndescription: p\n---\n"})
    install(host, skill_folder(tmp_path / "src"), force=True)
    record = install_skill._record_path((host / "demo-skill").resolve(), None)
    data = json.loads(record.read_text(encoding="utf-8"))
    evil = skill_folder(tmp_path / "evil" / "demo-skill", {"SKILL.md": b"evil"})
    data["history"][-1]["backup"] = str(evil)
    record.write_text(json.dumps(data), encoding="utf-8")
    before = snapshot(host)
    with pytest.raises(InstallSkillError, match="outside"):
        uninstall("demo-skill", host)
    assert snapshot(host) == before


def test_uninstall_refuses_a_record_whose_backup_is_reached_through_a_link(tmp_path: Path, host: Path) -> None:
    skill_folder(host / "demo-skill", {"SKILL.md": b"---\nname: demo-skill\ndescription: p\n---\n"})
    install(host, skill_folder(tmp_path / "src"), force=True)
    record = install_skill._record_path((host / "demo-skill").resolve(), None)
    data = json.loads(record.read_text(encoding="utf-8"))
    evil = skill_folder(tmp_path / "evil" / "demo-skill", {"SKILL.md": b"evil"})
    stamp = link_folder(tmp_path / "ph" / install_skill.BACKUP_DIR / "20990101T000000000000Z", evil.parent)
    data["history"][-1]["backup"] = str(stamp / "demo-skill")
    record.write_text(json.dumps(data), encoding="utf-8")
    before = snapshot(host)
    with pytest.raises(InstallSkillError, match="outside"):
        uninstall("demo-skill", host)
    assert snapshot(host) == before


def test_uninstall_refuses_a_backup_that_changed_since_the_install(tmp_path: Path, host: Path) -> None:
    skill_folder(host / "demo-skill", {"SKILL.md": b"---\nname: demo-skill\ndescription: p\n---\n"})
    result = install(host, skill_folder(tmp_path / "src"), force=True)
    (result.backup / "SKILL.md").write_bytes(b"---\nname: demo-skill\ndescription: edited later\n---\n")
    record = install_skill._record_path(result.dest, None)
    recorded = record.read_text(encoding="utf-8")
    before = snapshot(host)
    with pytest.raises(InstallSkillError, match="no longer matches what the install replaced") as info:
        uninstall("demo-skill", host)
    assert info.value.exit_code == 7
    assert snapshot(host) == before
    assert sorted(p.name for p in host.iterdir()) == ["demo-skill"]  # no half-made restore left beside it
    assert record.read_text(encoding="utf-8") == recorded


def test_uninstall_refuses_a_backup_holding_a_link_without_copying_it(tmp_path: Path, host: Path, monkeypatch) -> None:
    skill_folder(host / "demo-skill", {"SKILL.md": b"---\nname: demo-skill\ndescription: p\n---\n"})
    result = install(host, skill_folder(tmp_path / "src"), force=True)
    outside = skill_folder(tmp_path / "outside", {"secret.txt": b"secret"})
    link_folder(result.backup / "linked", outside)
    before = snapshot(host)
    copied: list[Path] = []
    real_copytree = shutil.copytree

    def watch(src, dst, *args, **kwargs):
        copied.append(Path(src))
        return real_copytree(src, dst, *args, **kwargs)

    monkeypatch.setattr(shutil, "copytree", watch)
    with pytest.raises(InstallSkillError, match="no longer matches what the install replaced"):
        uninstall("demo-skill", host)
    assert copied == []
    assert snapshot(host) == before
    assert snapshot(outside) == {"secret.txt": b"secret"}


def test_uninstall_that_cannot_update_its_record_removes_nothing(tmp_path: Path, host: Path, monkeypatch) -> None:
    install(host, skill_folder(tmp_path / "src"))
    record = install_skill._record_path((host / "demo-skill").resolve(), None)
    recorded = record.read_text(encoding="utf-8")
    before = snapshot(host)

    def read_only(*_args, **_kwargs):
        raise PermissionError("simulated read-only PROOFHOUSE_HOME")

    monkeypatch.setattr(install_skill, "_write_record", read_only)
    with pytest.raises(InstallSkillError, match="nothing was removed") as info:
        uninstall("demo-skill", host)
    assert info.value.exit_code == 7
    assert snapshot(host) == before
    assert sorted(p.name for p in host.iterdir()) == ["demo-skill"]
    assert record.read_text(encoding="utf-8") == recorded


def test_uninstall_whose_restore_fails_keeps_its_record(tmp_path: Path, host: Path, monkeypatch) -> None:
    skill_folder(host / "demo-skill", {"SKILL.md": b"---\nname: demo-skill\ndescription: p\n---\n"})
    install(host, skill_folder(tmp_path / "src"), force=True)
    record = install_skill._record_path((host / "demo-skill").resolve(), None)
    recorded = record.read_text(encoding="utf-8")
    before = snapshot(host)
    real = install_skill._move
    calls = {"n": 0}

    def flaky(src: Path, dst: Path) -> None:
        calls["n"] += 1
        if calls["n"] == 2:  # installed -> aside works; backup -> live fails
            raise PermissionError("simulated lock")
        real(src, dst)

    monkeypatch.setattr(install_skill, "_move", flaky)
    with pytest.raises(InstallSkillError, match="nothing was removed"):
        uninstall("demo-skill", host)
    assert snapshot(host) == before
    assert sorted(p.name for p in host.iterdir()) == ["demo-skill"]
    assert record.read_text(encoding="utf-8") == recorded


def test_uninstall_of_a_missing_folder_is_refused(tmp_path: Path, host: Path) -> None:
    install(host, skill_folder(tmp_path / "src"))
    shutil.rmtree(host / "demo-skill")
    with pytest.raises(InstallSkillError, match="does not exist"):
        uninstall("demo-skill", host)


def test_uninstall_needs_a_host_or_a_folder() -> None:
    with pytest.raises(InstallSkillError, match="nothing was removed") as info:
        uninstall("demo-skill")
    assert info.value.exit_code == 2


# --- the commands ---------------------------------------------------------------------------


def test_install_and_uninstall_commands_round_trip(tmp_path: Path, host: Path, capsys) -> None:
    src = skill_folder(tmp_path / "src")
    code, out, err = run(["install-skill", "--dest", str(host), "--bundle", str(src)], capsys)
    assert code == 0, err
    assert out.splitlines()[:2] == [
        f"install-skill: installed 3 files -> {(host / 'demo-skill').resolve()}",
        "  verified: name: demo-skill",
    ]
    assert "use the demo-skill skill" in out
    code, out, err = run(["uninstall-skill", "demo-skill", "--dest", str(host), "--json"], capsys)
    assert code == 0, err
    data = json.loads(out)["data"]
    assert data["name"] == "demo-skill" and data["forced"] is False and data["restored"] is None
    assert not (host / "demo-skill").exists()


def test_uninstall_command_restores_what_the_default_install_replaced(capsys) -> None:
    claude = Path.home() / ".claude" / "skills"
    mine = {"SKILL.md": b"---\nname: proofhouse\ndescription: my own edited copy\n---\n", "notes.txt": b"mine"}
    skill_folder(claude / "proofhouse", mine)
    code, _out, err = run(["install-skill", "--host", "claude", "--force"], capsys)
    assert code == 0, err
    assert snapshot(claude / "proofhouse") != mine
    code, out, err = run(["uninstall-skill", "proofhouse", "--host", "claude"], capsys)
    assert code == 0, err
    assert out.startswith("uninstall-skill: removed ")
    assert "restored the installation it had replaced" in out
    assert snapshot(claude / "proofhouse") == mine


def test_uninstall_command_refusals_exit_2(tmp_path: Path, host: Path, capsys) -> None:
    code, out, err = run(["uninstall-skill", "demo-skill", "--dest", str(host)], capsys)
    assert code == 2 and out == "" and "no record" in err
    code, out, err = run(["uninstall-skill", "CON", "--dest", str(host)], capsys)
    assert code == 2 and "must match" in err


def test_uninstall_help_is_ascii(capsys) -> None:
    code, out, err = run(["uninstall-skill", "--help"], capsys)
    assert code == 0
    (out + err).encode("ascii")


# --- the skill checker ----------------------------------------------------------------------


def evidence(result) -> dict[str, str]:
    return {row["check"]: row["result"] for row in result.evidence}


def test_skill_checker_round_trip_passes_on_a_good_skill(tmp_path: Path) -> None:
    src = skill_folder(tmp_path / "src")
    part = parts.get_part(parts.SKILL_CHECKER_ID)
    result = parts.perform(part, {"kind": AGENT_SKILL, "folder": src})
    assert evidence(result) == dict.fromkeys(parts.SKILL_CHECK_STEPS, "PASS")
    assert "behaviour in hosts not tested" in result.not_measured
    assert all(row["evidence_class"] == "structural_check" for row in result.evidence)
    assert snapshot(src) == SKILL  # the checked folder is read, never written


def test_skill_checker_passes_a_skill_named_like_its_placeholder(tmp_path: Path) -> None:
    md = b"---\nname: other-skill\ndescription: Shares a name with the checker's unrelated skill.\n---\n"
    src = skill_folder(tmp_path / "src", {**SKILL, "SKILL.md": md})
    result = parts.perform(parts.get_part(parts.SKILL_CHECKER_ID), {"kind": AGENT_SKILL, "folder": src})
    assert evidence(result) == dict.fromkeys(parts.SKILL_CHECK_STEPS, "PASS")


def test_skill_checker_passes_a_skill_near_the_entry_limit(tmp_path: Path) -> None:
    files = {**SKILL, **{f"many/f{i}.txt": b"x" for i in range(MAX_ENTRIES - 10)}}
    result = parts.perform(parts.get_part(parts.SKILL_CHECKER_ID), {"kind": AGENT_SKILL, "folder": skill_folder(tmp_path / "s", files)})
    assert set(evidence(result).values()) == {"PASS"}


def test_skill_checker_never_touches_the_real_home(tmp_path: Path) -> None:
    parts.perform(parts.get_part(parts.SKILL_CHECKER_ID), {"kind": AGENT_SKILL, "folder": skill_folder(tmp_path / "s")})
    assert not any((tmp_path / "user-home").iterdir())
    assert not (tmp_path / "ph").exists()


def test_skill_checker_stops_at_bad_frontmatter(tmp_path: Path) -> None:
    src = skill_folder(tmp_path / "src", {**SKILL, "SKILL.md": b"---\nname: Bad Name\ndescription: x\n---\n"})
    result = parts.perform(parts.get_part(parts.SKILL_CHECKER_ID), {"kind": AGENT_SKILL, "folder": src})
    assert evidence(result) == {
        "frontmatter": "FAIL", "write": "NOT_EVALUATED", "read_back": "NOT_EVALUATED",
        "reinstall_no_change": "NOT_EVALUATED", "uninstall_restores": "NOT_EVALUATED",
    }


def test_skill_checker_fails_a_folder_that_drifted_from_its_version_digest(tmp_path: Path) -> None:
    src = skill_folder(tmp_path / "src")
    result = parts.perform(
        parts.get_part(parts.SKILL_CHECKER_ID), {"kind": AGENT_SKILL, "folder": src, "digest": "0" * 64}
    )
    assert evidence(result)["frontmatter"] == "FAIL"


def test_skill_checker_fails_when_uninstall_does_not_restore(tmp_path: Path, monkeypatch) -> None:
    real = install_skill.uninstall

    def sloppy(name, dest=None, **kwargs):
        result = real(name, dest, **kwargs)
        (Path(dest) / "stray.txt").write_text("left behind", encoding="utf-8")
        return result

    monkeypatch.setattr(install_skill, "uninstall", sloppy)
    result = parts.perform(parts.get_part(parts.SKILL_CHECKER_ID), {"kind": AGENT_SKILL, "folder": skill_folder(tmp_path / "s")})
    assert evidence(result)["uninstall_restores"] == "FAIL"


@pytest.mark.parametrize(
    "request_body",
    [{"kind": "prompt.text@1", "folder": "x"}, {"kind": AGENT_SKILL}],
)
def test_skill_checker_refuses_without_running(request_body: dict) -> None:
    part = parts.get_part(parts.SKILL_CHECKER_ID)
    assert part.check(request_body).answer == parts.UNSUPPORTED
    with pytest.raises(parts.PartRefusedError):
        parts.perform(part, request_body)


def test_skill_checker_descriptor() -> None:
    d = parts.get_part(parts.SKILL_CHECKER_ID).describe()
    parts.validate_descriptor(d)
    assert d.role == parts.ROLE_CHECKER
    assert d.kinds_in == (AGENT_SKILL,) and d.kinds_out == ()
    assert d.status == parts.IMPLEMENTED_NOT_CERTIFIED
    assert d.reproducibility == parts.DETERMINISTIC and d.network == parts.NETWORK_NONE
    assert "behaviour in hosts not tested" in d.not_measured


# --- the host writer part --------------------------------------------------------------------


def test_host_writer_installs_a_folder_and_uninstalls_it(tmp_path: Path, host: Path) -> None:
    part = parts.get_part(parts.HOST_WRITER_ID)
    src = skill_folder(tmp_path / "src")
    result = parts.perform(part, {"kind": AGENT_SKILL, "dest": host, "bundle": src})
    assert result.artifacts[0].digest == install_skill.installed_digest(host / "demo-skill")
    gone = parts.perform(part, {"kind": AGENT_SKILL, "dest": host, "action": "uninstall", "name": "demo-skill"})
    assert gone.evidence[0]["action"] == "uninstall"
    assert not (host / "demo-skill").exists()


@pytest.mark.parametrize(
    "request_body",
    [
        {"kind": AGENT_SKILL, "dest": "x", "action": "delete"},
        {"kind": AGENT_SKILL, "dest": "x", "action": "uninstall"},
    ],
)
def test_host_writer_refuses_unknown_actions_and_unnamed_uninstall(request_body: dict, tmp_path: Path) -> None:
    part = parts.get_part(parts.HOST_WRITER_ID)
    with pytest.raises(parts.PartRefusedError):
        parts.perform(part, request_body)


def test_host_writer_descriptor_names_both_actions() -> None:
    d = parts.get_part(parts.HOST_WRITER_ID).describe()
    parts.validate_descriptor(d)
    assert d.capability_manifest["actions"] == ["install", "uninstall"]
    assert sorted(d.capability_manifest["hosts"]) == ["claude", "cursor"]  # no new host


# --- a skill case: the checker is judged by the case pass rule --------------------------------


@pytest.fixture()
def skill_case(tmp_path: Path) -> Path:
    case = tmp_path / "skill-case"
    case_mod.new_case(
        case, objective="Review a demo skill", resolved=resolve_model_notes("Zeta 9"),
        preset_key="balanced", loop=False, kind=AGENT_SKILL,
    )
    case_mod.record_skill_revision(case, skill_folder(tmp_path / "v1"))
    return case


def test_skill_case_checks_pass_through_the_skill_checker(skill_case: Path, tmp_path: Path, capsys) -> None:
    code, out, err = run(["case", "criteria", "add", "--case", str(skill_case), "--skill-check", "install-roundtrip"], capsys)
    assert code == 0, err
    code, out, err = run(["case", "check", "--case", str(skill_case), "--json"], capsys)
    assert code == 0, out + err
    report = json.loads(out)["data"]["revisions"][0]
    row = report["results"][0]
    assert row["result"] == "PASS" and row["part"] == "skill-checker"
    assert [item["check"] for item in row["evidence"]] == list(parts.SKILL_CHECK_STEPS)
    assert "behaviour in hosts not tested" in row["not_measured"]

    # A broken second version fails the same criterion, and compare shows it.
    case_mod.record_skill_revision(
        skill_case, skill_folder(tmp_path / "v2", {**SKILL, "SKILL.md": b"---\nname: demo-skill\n---\n"})
    )
    code, out, err = run(["case", "compare", "--case", str(skill_case), "--from", "1", "--to", "2"], capsys)
    assert code == 3, out + err
    assert "regression" in out

    report_path = tmp_path / "report.md"
    code, out, err = run(["case", "report", "--case", str(skill_case), "--revision", "1", "--out", str(report_path)], capsys)
    assert code == 0, err
    text = report_path.read_text(encoding="utf-8")
    assert "skill check (temporary host folder)" in text
    assert "Behaviour in hosts was not" in text
    assert "No independent pass ran on this skill" in text


def test_skill_check_on_a_prompt_version_or_an_output_target_is_refused(tmp_path: Path, skill_case: Path, capsys) -> None:
    code, _out, err = run(
        ["case", "criteria", "add", "--case", str(skill_case), "--skill-check", "install-roundtrip", "--target", "output"],
        capsys,
    )
    assert code == 2 and "no --target" in err
    code, _out, err = run(["case", "criteria", "add", "--case", str(skill_case), "--skill-check", "anything"], capsys)
    assert code == 2 and "install-roundtrip" in err

    prompt_case = tmp_path / "prompt-case"
    case_mod.new_case(prompt_case, objective="x", resolved=resolve_model_notes("Zeta 9"), preset_key="balanced", loop=False)
    case_mod.record_revision(prompt_case, "a prompt")
    assert run(["case", "criteria", "add", "--case", str(prompt_case), "--skill-check", "install-roundtrip"], capsys)[0] == 0
    code, _out, err = run(["case", "check", "--case", str(prompt_case)], capsys)
    assert code == 2 and "is a skill check" in err


def test_skill_check_on_a_version_whose_files_drifted_is_refused(skill_case: Path, capsys) -> None:
    run(["case", "criteria", "add", "--case", str(skill_case), "--skill-check", "install-roundtrip"], capsys)
    files = skill_case / case_mod.skill_files_relpath(1)
    (files / "SKILL.md").write_bytes(SKILL["SKILL.md"] + b"edited\n")
    code, _out, err = run(["case", "check", "--case", str(skill_case)], capsys)
    assert code == 2 and "v1" in err


def test_a_checked_skill_case_still_exports_and_imports(skill_case: Path, tmp_path: Path, capsys) -> None:
    from proofhouse.optimize import workflow

    run(["case", "criteria", "add", "--case", str(skill_case), "--skill-check", "install-roundtrip"], capsys)
    assert run(["case", "check", "--case", str(skill_case)], capsys)[0] == 0
    workflow.export_case(skill_case, tmp_path / "b.zip")
    workflow.import_case(tmp_path / "b.zip", tmp_path / "imported")
    code, out, err = run(["case", "check", "--case", str(tmp_path / "imported")], capsys)
    assert code == 0, out + err


def test_sha_helper_matches_hashlib() -> None:  # keeps the helpers above honest about bytes
    assert hashlib.sha256(SKILL["SKILL.md"]).hexdigest() == hashlib.sha256(io.BytesIO(SKILL["SKILL.md"]).read()).hexdigest()


def test_review_f3_skill_case_report_prints_the_part_and_its_status_apart_from_the_case_result(
    skill_case: Path, tmp_path: Path, capsys
) -> None:
    code, _out, err = run(["case", "criteria", "add", "--case", str(skill_case), "--skill-check", "install-roundtrip"], capsys)
    assert code == 0, err
    report_path = tmp_path / "report.md"
    code, _out, err = run(["case", "report", "--case", str(skill_case), "--revision", "1", "--out", str(report_path)], capsys)
    assert code == 0, err
    text = report_path.read_text(encoding="utf-8")
    assert "Overall: **PASS**" in text  # the case result
    status = parts.get_part(parts.SKILL_CHECKER_ID).describe().status
    assert parts.SKILL_CHECKER_ID in text  # the part that produced the evidence
    assert status in text  # and its own status, printed apart from the case PASS


def test_review_g2_skill_check_criterion_fails_when_any_step_fails(skill_case: Path, monkeypatch, capsys) -> None:
    real = install_skill.uninstall

    def sloppy(name, dest=None, **kwargs):
        result = real(name, dest, **kwargs)
        (Path(dest) / "stray.txt").write_text("left behind", encoding="utf-8")
        return result

    monkeypatch.setattr(install_skill, "uninstall", sloppy)
    code, _out, err = run(["case", "criteria", "add", "--case", str(skill_case), "--skill-check", "install-roundtrip"], capsys)
    assert code == 0, err
    _code, out, err = run(["case", "check", "--case", str(skill_case), "--json"], capsys)
    row = json.loads(out)["data"]["revisions"][0]["results"][0]
    steps = {item["check"]: item["result"] for item in row["evidence"]}
    assert steps["uninstall_restores"] == "FAIL" and "PASS" in steps.values()  # some steps pass, one fails
    assert row["result"] == "FAIL"


def test_skill_case_report_names_what_the_skill_checker_did_not_measure(skill_case: Path, tmp_path: Path, capsys) -> None:
    code, _out, err = run(["case", "criteria", "add", "--case", str(skill_case), "--skill-check", "install-roundtrip"], capsys)
    assert code == 0, err
    report_path = tmp_path / "report.md"
    code, _out, err = run(["case", "report", "--case", str(skill_case), "--revision", "1", "--out", str(report_path)], capsys)
    assert code == 0, err
    lines = report_path.read_text(encoding="utf-8").splitlines()
    part_lines = [line for line in lines if f"`{parts.SKILL_CHECKER_ID}`" in line]
    assert len(part_lines) == 1 and "Overall" not in part_lines[0]
    assert all(item in part_lines[0] for item in parts.SKILL_CHECKER_NOT_MEASURED)


# --- installer re-check of 550a367 -------------------------------------------------------------

THEIRS = {"SKILL.md": b"---\nname: demo-skill\ndescription: theirs\n---\n"}


def backups(tmp_path: Path) -> list[Path]:
    root = tmp_path / "ph" / install_skill.BACKUP_DIR
    return sorted(root.rglob("*")) if root.exists() else []


def records(tmp_path: Path) -> list[Path]:
    root = tmp_path / "ph" / install_skill.INSTALLS_DIR
    return sorted(root.glob("*.json")) if root.exists() else []


@pytest.mark.parametrize("target", ["outside", "own folder"])
def test_forced_uninstall_refuses_a_skill_folder_holding_a_link_and_copies_nothing(
    tmp_path: Path, host: Path, target: str
) -> None:
    install(host, skill_folder(tmp_path / "src"))
    outside = skill_folder(tmp_path / "outside", {"secret.txt": b"secret", "deep/x.txt": b"x"})
    link_folder(host / "demo-skill" / "node_modules", outside if target == "outside" else host / "demo-skill")
    record = install_skill._record_path((host / "demo-skill").resolve(), None)
    recorded = record.read_text(encoding="utf-8")
    host_before, home_before = state(host), state(tmp_path / "ph")
    with pytest.raises(InstallSkillError, match="link or junction") as info:
        uninstall("demo-skill", host, force=True)
    assert info.value.exit_code == 2
    assert state(host) == host_before
    assert state(tmp_path / "ph") == home_before  # nothing copied out of the link; nothing new at all
    assert record.read_text(encoding="utf-8") == recorded
    assert snapshot(outside) == {"secret.txt": b"secret", "deep/x.txt": b"x"}


@pytest.mark.parametrize(
    ("plant_after", "force"), [("_stage", False), ("_write_record", False), ("_write_record", True)]
)
def test_install_refuses_a_skill_folder_that_appears_while_it_installs(
    tmp_path: Path, host: Path, monkeypatch, plant_after: str, force: bool
) -> None:
    real = getattr(install_skill, plant_after)

    def then_plant(*args, **kwargs):
        result = real(*args, **kwargs)
        if not (host / "demo-skill").exists():
            skill_folder(host / "demo-skill", THEIRS)
        return result

    monkeypatch.setattr(install_skill, plant_after, then_plant)
    with pytest.raises(InstallSkillError, match="appeared") as info:
        install(host, skill_folder(tmp_path / "src"), force=force)
    assert info.value.exit_code == 2
    assert snapshot(host / "demo-skill") == THEIRS
    assert sorted(p.name for p in host.iterdir()) == ["demo-skill"]
    assert backups(tmp_path) == []
    assert records(tmp_path) == []


@pytest.mark.parametrize("where", ["inside", "itself"])
def test_forced_install_refuses_a_link_that_appears_while_it_installs(
    tmp_path: Path, host: Path, monkeypatch, where: str
) -> None:
    skill_folder(host / "demo-skill", THEIRS)
    outside = skill_folder(tmp_path / "outside", {"secret.txt": b"secret"})
    real = install_skill._stage

    def stage_then_link(*args, **kwargs):
        real(*args, **kwargs)
        if where == "inside":
            link_folder(host / "demo-skill" / "linked", outside)
        else:
            os.rename(host / "demo-skill", tmp_path / "moved")
            link_folder(host / "demo-skill", outside)

    monkeypatch.setattr(install_skill, "_stage", stage_then_link)
    with pytest.raises(InstallSkillError, match="link or junction") as info:
        install(host, skill_folder(tmp_path / "src"), force=True)
    assert info.value.exit_code == 2
    linked = host / "demo-skill" / "linked" if where == "inside" else host / "demo-skill"
    assert install_skill._is_link(linked)
    assert sorted(p.name for p in host.iterdir()) == ["demo-skill"]
    assert snapshot(outside) == {"secret.txt": b"secret"}
    assert backups(tmp_path) == []
    assert records(tmp_path) == []


@links_supported
def test_forced_install_refuses_a_backup_that_holds_a_link(tmp_path: Path, host: Path, monkeypatch) -> None:
    skill_folder(host / "demo-skill", THEIRS)
    outside = skill_folder(tmp_path / "outside", {"secret.txt": b"secret"})
    real_copytree = shutil.copytree

    def link_then_copy(src, dst, *args, **kwargs):
        if Path(src).name == "demo-skill" and not os.path.lexists(Path(src) / "linked"):
            os.symlink(outside, Path(src) / "linked", target_is_directory=True)  # copied as a link, not followed
        return real_copytree(src, dst, *args, **kwargs)

    monkeypatch.setattr(shutil, "copytree", link_then_copy)
    with pytest.raises(InstallSkillError, match="link or junction") as info:
        install(host, skill_folder(tmp_path / "src"), force=True)
    assert info.value.exit_code == 2
    assert (host / "demo-skill" / "SKILL.md").read_bytes() == THEIRS["SKILL.md"]
    assert sorted(p.name for p in host.iterdir()) == ["demo-skill"]
    assert backups(tmp_path) == []
    assert records(tmp_path) == []


def test_a_backup_that_fails_midway_leaves_nothing_under_proofhouse_home(tmp_path: Path, host: Path, monkeypatch) -> None:
    skill_folder(host / "demo-skill", {**THEIRS, "big/a.txt": b"a"})
    before = snapshot(host)
    real_copytree = shutil.copytree

    def copy_then_fail(src, dst, *args, **kwargs):
        real_copytree(src, dst, *args, **kwargs)
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(shutil, "copytree", copy_then_fail)
    with pytest.raises(InstallSkillError, match="cannot back up") as info:
        install(host, skill_folder(tmp_path / "src"), force=True)
    assert info.value.exit_code == 7
    assert snapshot(host) == before
    assert backups(tmp_path) == []
    assert records(tmp_path) == []


@pytest.mark.parametrize("failure", ["copy fails", "copy differs"])
def test_a_backup_that_cannot_be_removed_is_named_in_the_error(
    tmp_path: Path, host: Path, monkeypatch, failure: str
) -> None:
    skill_folder(host / "demo-skill", THEIRS)
    real_copytree = shutil.copytree

    def copy_then(src, dst, *args, **kwargs):
        real_copytree(src, dst, *args, **kwargs)
        if failure == "copy fails":
            raise OSError(28, "No space left on device")
        (Path(dst) / "late.txt").write_text("written while the backup was taken", encoding="utf-8")

    monkeypatch.setattr(shutil, "copytree", copy_then)
    monkeypatch.setattr(install_skill, "_discard", lambda path: False)
    with pytest.raises(InstallSkillError) as info:
        install(host, skill_folder(tmp_path / "src"), force=True)
    left = sorted((tmp_path / "ph" / install_skill.BACKUP_DIR).glob("*/demo-skill"))
    assert len(left) == 1
    assert f"left at {left[0]}" in str(info.value)


def test_a_forced_uninstall_whose_safety_copy_fails_leaves_nothing_under_proofhouse_home(
    tmp_path: Path, host: Path, monkeypatch
) -> None:
    install(host, skill_folder(tmp_path / "src"))
    (host / "demo-skill" / "notes" / "edited.txt").write_text("my edit", encoding="utf-8")
    record = install_skill._record_path((host / "demo-skill").resolve(), None)
    recorded = record.read_text(encoding="utf-8")
    before = snapshot(host)
    real_copytree = shutil.copytree

    def copy_then_fail(src, dst, *args, **kwargs):
        real_copytree(src, dst, *args, **kwargs)
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(shutil, "copytree", copy_then_fail)
    with pytest.raises(InstallSkillError, match="nothing was removed") as info:
        uninstall("demo-skill", host, force=True)
    assert info.value.exit_code == 7
    assert snapshot(host) == before
    assert record.read_text(encoding="utf-8") == recorded
    uninstalled = tmp_path / "ph" / install_skill.UNINSTALLED_DIR
    assert not uninstalled.exists() or list(uninstalled.rglob("*")) == []


@pytest.mark.parametrize("action", ["install", "uninstall"])
def test_a_rollback_that_cannot_put_the_record_back_says_so(
    tmp_path: Path, host: Path, monkeypatch, action: str
) -> None:
    if action == "install":
        skill_folder(host / "demo-skill", THEIRS)
    else:
        install(host, skill_folder(tmp_path / "src"))
    record = install_skill._record_path((host / "demo-skill").resolve(), None)
    before = snapshot(host)

    def locked(src: Path, dst: Path) -> None:
        if record.is_file():
            record.unlink()
        record.mkdir(parents=True, exist_ok=True)  # the record path can no longer be written or removed
        raise PermissionError("simulated lock")

    monkeypatch.setattr(install_skill, "_move", locked)
    with pytest.raises(InstallSkillError, match="record not restored") as info:
        if action == "install":
            install(host, skill_folder(tmp_path / "src"), force=True)
        else:
            uninstall("demo-skill", host)
    assert info.value.exit_code == 7
    assert str(record) in str(info.value)
    assert snapshot(host) == before


@links_supported
def test_forced_uninstall_refuses_a_safety_copy_that_differs_from_the_folder(tmp_path: Path, host: Path, monkeypatch) -> None:
    install(host, skill_folder(tmp_path / "src"))
    (host / "demo-skill" / "notes" / "edited.txt").write_text("my edit", encoding="utf-8")
    outside = skill_folder(tmp_path / "outside", {"secret.txt": b"secret"})
    record = install_skill._record_path((host / "demo-skill").resolve(), None)
    recorded = record.read_text(encoding="utf-8")
    real_copytree = shutil.copytree

    def link_then_copy(src, dst, *args, **kwargs):
        if Path(src).name == "demo-skill" and not os.path.lexists(Path(src) / "linked"):
            os.symlink(outside, Path(src) / "linked", target_is_directory=True)  # after the link check
        return real_copytree(src, dst, *args, **kwargs)

    monkeypatch.setattr(shutil, "copytree", link_then_copy)
    with pytest.raises(InstallSkillError, match="changed while it was being backed up; nothing was removed") as info:
        uninstall("demo-skill", host, force=True)
    assert info.value.exit_code == 7
    assert (host / "demo-skill" / "notes" / "edited.txt").read_text(encoding="utf-8") == "my edit"
    assert record.read_text(encoding="utf-8") == recorded
    uninstalled = tmp_path / "ph" / install_skill.UNINSTALLED_DIR
    assert not uninstalled.exists() or list(uninstalled.rglob("*")) == []
