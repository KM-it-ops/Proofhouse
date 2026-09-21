"""`proofhouse-compiler install-skill` through cli_compiler.main(); never touches the real ~/.cursor."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from proofhouse.compiler import cli_compiler
from proofhouse.optimize import install_skill
from proofhouse.optimize.registry import PACKAGE_BUNDLE_PATH

EXPECTED_FILES = [
    "proofhouse/SKILL.md",
    "proofhouse/assets/proofhouse.jsx",
    "proofhouse/references/proofhouse-framework.json",
    "proofhouse/references/proofhouse-framework.md",
]


def _run(argv: list[str], capsys) -> tuple[int, str, str]:
    code = cli_compiler.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _make_bundle(path: Path, entries: dict[str, str]) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, text in entries.items():
            archive.writestr(name, text)
    return path


def _skill_md(name: str) -> str:
    return f"---\nname: {name}\ndescription: test skill\n---\n\n# body\n"


def test_default_dest_is_cursor_skills_and_bundle_is_package_data() -> None:
    assert install_skill.default_dest() == Path.home() / ".cursor" / "skills"
    assert install_skill.DEFAULT_BUNDLE == PACKAGE_BUNDLE_PATH
    assert PACKAGE_BUNDLE_PATH.is_file()
    assert "install-skill" in cli_compiler.COMPILER_COMMANDS


def test_fresh_install_extracts_four_files_and_verifies_name(tmp_path: Path, capsys) -> None:
    dest = tmp_path / "skills"
    code, out, err = _run(["install-skill", "--dest", str(dest)], capsys)
    assert code == 0 and err == ""
    skill_dir = dest / "proofhouse"
    assert out.splitlines() == [
        f"install-skill: installed 4 files -> {skill_dir.resolve()}",
        "  verified: name: proofhouse",
        '  next: start a new Cursor Agent chat and say "Proofhouse"',
    ]
    installed = sorted(str(p.relative_to(dest)).replace("\\", "/") for p in skill_dir.rglob("*") if p.is_file())
    assert installed == EXPECTED_FILES
    lines = (skill_dir / "SKILL.md").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "---"
    assert lines[1] == "name: proofhouse"


def test_second_run_without_force_exits_2_and_leaves_files_untouched(tmp_path: Path, capsys) -> None:
    dest = tmp_path / "skills"
    assert _run(["install-skill", "--dest", str(dest)], capsys)[0] == 0
    skill_md = dest / "proofhouse" / "SKILL.md"
    skill_md.write_text("sentinel\n", encoding="utf-8")
    before = {p: p.stat().st_mtime_ns for p in (dest / "proofhouse").rglob("*") if p.is_file()}

    code, out, err = _run(["install-skill", "--dest", str(dest)], capsys)
    assert code == 2 and out == ""
    assert err == f"error: {(dest / 'proofhouse').resolve()} already exists; re-run with --force to replace it\n"
    assert skill_md.read_text(encoding="utf-8") == "sentinel\n"
    after = {p: p.stat().st_mtime_ns for p in (dest / "proofhouse").rglob("*") if p.is_file()}
    assert after == before


def test_force_replaces_existing_install(tmp_path: Path, capsys) -> None:
    dest = tmp_path / "skills"
    assert _run(["install-skill", "--dest", str(dest)], capsys)[0] == 0
    skill_dir = dest / "proofhouse"
    (skill_dir / "SKILL.md").write_text("sentinel\n", encoding="utf-8")
    (skill_dir / "stray.txt").write_text("leftover\n", encoding="utf-8")

    code, out, err = _run(["install-skill", "--dest", str(dest), "--force"], capsys)
    assert code == 0 and err == ""
    assert out.splitlines()[0] == f"install-skill: installed 4 files -> {skill_dir.resolve()}"
    assert (skill_dir / "SKILL.md").read_text(encoding="utf-8").splitlines()[1] == "name: proofhouse"
    assert not (skill_dir / "stray.txt").exists()


def test_bundle_with_wrong_name_fails_verification_exit_7_and_is_removed(tmp_path: Path, capsys) -> None:
    bundle = _make_bundle(tmp_path / "bad.skill", {"proofhouse/SKILL.md": _skill_md("nope")})
    dest = tmp_path / "skills"
    code, out, err = _run(["install-skill", "--dest", str(dest), "--bundle", str(bundle)], capsys)
    assert code == 7 and out == ""
    assert err.startswith("error: installed skill failed verification: ")
    assert "name: proofhouse" in err
    assert f"removed {(dest / 'proofhouse').resolve()}" in err
    assert not (dest / "proofhouse").exists()


def test_bundle_missing_skill_md_fails_verification_exit_7(tmp_path: Path, capsys) -> None:
    bundle = _make_bundle(tmp_path / "noskill.skill", {"proofhouse/README.md": "# nothing\n"})
    dest = tmp_path / "skills"
    code, out, err = _run(["install-skill", "--dest", str(dest), "--bundle", str(bundle)], capsys)
    assert code == 7 and out == ""
    assert err.startswith("error: installed skill failed verification: ")
    assert "SKILL.md" in err
    assert not (dest / "proofhouse").exists()


def test_bundle_not_a_zip_exit_7(tmp_path: Path, capsys) -> None:
    bogus = tmp_path / "bogus.skill"
    bogus.write_text("not a zip\n", encoding="utf-8")
    dest = tmp_path / "skills"
    code, out, err = _run(["install-skill", "--dest", str(dest), "--bundle", str(bogus)], capsys)
    assert code == 7 and out == ""
    assert err.startswith("error: bundle unreadable: ")
    assert not dest.exists()

    code, out, err = _run(["install-skill", "--dest", str(dest), "--bundle", str(tmp_path / "absent.skill")], capsys)
    assert code == 7 and out == ""
    assert err.startswith("error: bundle unreadable: ")


@pytest.mark.parametrize("evil", ["../evil", "proofhouse/../evil", "other/SKILL.md", "/proofhouse/SKILL.md"])
def test_unsafe_zip_entry_exits_7_before_extraction(tmp_path: Path, capsys, evil: str) -> None:
    bundle = _make_bundle(tmp_path / "evil.skill", {"proofhouse/SKILL.md": _skill_md("proofhouse"), evil: "x\n"})
    dest = tmp_path / "skills"
    code, out, err = _run(["install-skill", "--dest", str(dest), "--bundle", str(bundle)], capsys)
    assert code == 7 and out == ""
    assert err.startswith("error: bundle unreadable: ")
    assert evil in err
    assert not dest.exists()
    assert not (tmp_path / "evil").exists()


def test_json_output_lists_files_and_bundle(tmp_path: Path, capsys) -> None:
    dest = tmp_path / "skills"
    code, out, err = _run(["install-skill", "--dest", str(dest), "--json"], capsys)
    assert code == 0 and err == ""
    assert out.endswith("\n")
    payload = json.loads(out)
    assert json.dumps(payload, sort_keys=True) + "\n" == out
    assert payload["command"] == "install-skill"
    assert payload["status"] == "success"
    data = payload["data"]
    assert set(data) == {"dest", "files", "verified", "bundle"}
    assert data["dest"] == str((dest / "proofhouse").resolve())
    assert data["files"] == EXPECTED_FILES
    assert data["verified"] is True
    assert data["bundle"] == str(PACKAGE_BUNDLE_PATH)

    code, out, err = _run(["install-skill", "--dest", str(dest), "--json"], capsys)
    assert code == 2 and out == ""
    assert err.startswith("error: ")


def test_frontmatter_check_requires_exact_line_inside_first_two_dashes(tmp_path: Path) -> None:
    good = tmp_path / "good.md"
    good.write_text("---\r\nname: proofhouse\r\ndescription: x\r\n---\r\nbody\r\n", encoding="utf-8")
    install_skill.verify_skill_md(good)

    for text in (
        "---\nname:proofhouse\n---\n",
        "---\nname: proofhouse-x\n---\n",
        "name: proofhouse\n---\n---\n",
        "---\ndescription: x\n---\nname: proofhouse\n",
        "---\nname: proofhouse\n",
    ):
        bad = tmp_path / "bad.md"
        bad.write_text(text, encoding="utf-8")
        with pytest.raises(install_skill.InstallSkillError) as excinfo:
            install_skill.verify_skill_md(bad)
        assert excinfo.value.exit_code == 7


def test_help_is_ascii(capsys) -> None:
    code, out, err = _run(["install-skill", "--help"], capsys)
    assert code == 0
    (out + err).encode("ascii")
    for flag in ("--dest", "--bundle", "--force", "--json"):
        assert flag in out
