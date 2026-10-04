"""`proofhouse-compiler install-skill` through cli_compiler.main(); never touches the real ~/.cursor."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from proofhouse.compiler import cli_compiler
from proofhouse.optimize import install_skill
from proofhouse.optimize.registry import PACKAGE_BUNDLE_PATH

EXPECTED_FILES = [
    "proofhouse/INSTALL.md",
    "proofhouse/SKILL.md",
    "proofhouse/assets/proofhouse.jsx",
    "proofhouse/references/proofhouse-framework.json",
    "proofhouse/references/proofhouse-framework.md",
    "proofhouse/scripts/scan_project.py",
]


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Forced replacements write a rollback backup under PROOFHOUSE_HOME (T06).
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))


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


def test_default_dest_needs_an_agent_and_bundle_is_package_data() -> None:
    assert install_skill.default_dest("cursor") == Path.home() / ".cursor" / "skills"
    with pytest.raises(TypeError):
        install_skill.default_dest()  # type: ignore[call-arg]
    assert install_skill.DEFAULT_BUNDLE == PACKAGE_BUNDLE_PATH
    assert PACKAGE_BUNDLE_PATH.is_file()
    assert "install-skill" in cli_compiler.COMPILER_COMMANDS


def test_claude_host_default_dest_is_claude_skills() -> None:
    assert install_skill.default_dest("claude") == Path.home() / ".claude" / "skills"


def test_host_claude_installs_to_home_claude_skills_and_says_claude_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    code, out, err = _run(["install-skill", "--host", "claude"], capsys)
    assert code == 0 and err == ""
    skill_dir = tmp_path / ".claude" / "skills" / "proofhouse"
    assert out.splitlines() == [
        f"install-skill: installed 6 files -> {skill_dir.resolve()}",
        "  verified: name: proofhouse",
        '  next: start a new Claude Code session and say "Proofhouse"',
    ]
    installed = sorted(str(p.relative_to(skill_dir.parent)).replace("\\", "/") for p in skill_dir.rglob("*") if p.is_file())
    assert installed == EXPECTED_FILES
    assert not (tmp_path / ".cursor").exists()


def test_unknown_host_is_a_usage_error(tmp_path: Path, capsys) -> None:
    code, out, err = _run(["install-skill", "--host", "vscode", "--dest", str(tmp_path / "skills")], capsys)
    assert code == 2 and out == ""
    assert "invalid choice" in err
    assert not (tmp_path / "skills").exists()


def test_fresh_install_extracts_six_files_and_verifies_name(tmp_path: Path, capsys) -> None:
    dest = tmp_path / "skills"
    code, out, err = _run(["install-skill", "--dest", str(dest)], capsys)
    assert code == 0 and err == ""
    skill_dir = dest / "proofhouse"
    assert out.splitlines() == [
        f"install-skill: installed 6 files -> {skill_dir.resolve()}",
        "  verified: name: proofhouse",
        '  next: start a new chat or session in your agent and say "Proofhouse"',
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
    assert out.splitlines()[0] == f"install-skill: installed 6 files -> {skill_dir.resolve()}"
    assert (skill_dir / "SKILL.md").read_text(encoding="utf-8").splitlines()[1] == "name: proofhouse"
    assert not (skill_dir / "stray.txt").exists()


def test_bundle_with_wrong_name_fails_verification_exit_7_and_is_removed(tmp_path: Path, capsys) -> None:
    bundle = _make_bundle(tmp_path / "bad.skill", {"proofhouse/SKILL.md": _skill_md("nope")})
    dest = tmp_path / "skills"
    code, out, err = _run(["install-skill", "--dest", str(dest), "--bundle", str(bundle)], capsys)
    assert code == 7 and out == ""
    assert err.startswith("error: installed skill failed verification: ")
    assert "name: proofhouse" in err
    # T06: verification happens in staging, so nothing reaches the destination.
    assert f"nothing was installed at {(dest / 'proofhouse').resolve()}" in err
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
    assert set(data) == {"host", "agent", "dest", "files", "verified", "bundle", "backup"}
    assert data["agent"] is None
    assert data["backup"] is None
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
    for flag in ("--host", "--dest", "--bundle", "--force", "--json"):
        assert flag in out


def test_cli_warns_when_the_replaced_copy_could_not_be_removed(tmp_path: Path, monkeypatch, capsys) -> None:
    from proofhouse.compiler import cli_compiler
    from proofhouse.optimize import install_skill

    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    dest = tmp_path / "skills"
    assert cli_compiler.main(["install-skill", "--dest", str(dest)]) == 0
    monkeypatch.setattr(install_skill, "_discard", lambda path: False)
    capsys.readouterr()
    assert cli_compiler.main(["install-skill", "--dest", str(dest), "--force"]) == 0
    err = capsys.readouterr().err
    assert err.startswith("warning: could not remove the replaced copy at ")
    assert "delete it so the host does not load two copies" in err


def test_no_host_flag_never_creates_an_unused_agent_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "ph"))
    monkeypatch.setattr("sys.stdin", open(__import__("os").devnull))  # non-interactive
    (tmp_path / ".claude").mkdir()  # the user runs Claude Code only
    cli_compiler.main(["install-skill"])
    capsys.readouterr()
    assert not (tmp_path / ".cursor").exists()


def test_install_api_without_host_or_dest_refuses_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Replaces review-4a1217c-F2's Cursor-default test: Boss ruled (2026-10-04) that the
    # library never assumes an agent either.
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "ph"))
    with pytest.raises(install_skill.InstallSkillError) as excinfo:
        install_skill.install()
    assert excinfo.value.exit_code == 2
    assert "--host" in str(excinfo.value) and "--dest" in str(excinfo.value)
    assert list(tmp_path.iterdir()) == []


def test_no_host_flag_installs_for_the_only_agent_folder_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    (tmp_path / ".claude").mkdir()
    code, out, err = _run(["install-skill"], capsys)
    assert code == 0 and err == ""
    assert (tmp_path / ".claude" / "skills" / "proofhouse" / "SKILL.md").is_file()
    assert "a new Claude Code session" in out


@pytest.mark.parametrize("present", [[], [".claude", ".cursor"]])
def test_no_host_flag_with_no_or_several_agent_folders_exits_2_and_lists_choices(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, present: list[str]
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    for name in present:
        (tmp_path / name).mkdir()
    code, out, err = _run(["install-skill"], capsys)
    assert code == 2 and out == ""
    assert "--host {claude,cursor}" in err
    assert not (tmp_path / ".claude" / "skills").exists() and not (tmp_path / ".cursor" / "skills").exists()


def test_dest_without_host_installs_there_and_names_no_agent(tmp_path: Path, capsys) -> None:
    code, out, _ = _run(["install-skill", "--dest", str(tmp_path / "skills"), "--json"], capsys)
    assert code == 0
    assert json.loads(out)["data"]["host"] is None


def test_install_api_unknown_host_is_a_usage_error() -> None:
    with pytest.raises(install_skill.InstallSkillError) as excinfo:
        install_skill.install(host="codex")
    assert excinfo.value.exit_code == 2


class _Terminal(io.StringIO):
    """Typed answers on a stdin that reports itself as an interactive terminal."""

    def isatty(self) -> bool:
        return True


def _interactive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, typed: str, folders: list[str]) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr("sys.stdin", _Terminal(typed))
    for name in folders:
        (tmp_path / name).mkdir()


def test_terminal_without_host_lists_every_agent_and_a_new_one_then_installs_the_pick(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    _interactive(monkeypatch, tmp_path, "1\n", [".claude", ".cursor"])
    code, out, err = _run(["install-skill"], capsys)
    assert code == 0, err
    assert "Which agent should Proofhouse be installed for?" in err
    assert "1) Claude Code" in err and "2) Cursor" in err
    assert "3) Another agent" in err
    assert err.count("(found)") == 2
    assert (tmp_path / ".claude" / "skills" / "proofhouse" / "SKILL.md").is_file()
    assert not (tmp_path / ".cursor" / "skills").exists()
    assert "a new Claude Code session" in out


def test_terminal_asks_even_when_only_one_agent_folder_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    _interactive(monkeypatch, tmp_path, "2\n", [".claude"])
    code, out, err = _run(["install-skill"], capsys)
    assert code == 0, err
    assert "Which agent" in err and err.count("(found)") == 1
    assert (tmp_path / ".cursor" / "skills" / "proofhouse" / "SKILL.md").is_file()
    assert not (tmp_path / ".claude" / "skills").exists()


def test_terminal_new_agent_takes_a_name_and_skills_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    folder = tmp_path / "ws" / "skills"
    _interactive(monkeypatch, tmp_path, f"3\nWindsurf\n{folder}\n", [])
    code, out, err = _run(["install-skill", "--json"], capsys)
    assert code == 0, err
    data = json.loads(out)["data"]
    assert data["host"] is None and data["agent"] == "Windsurf"
    assert data["dest"] == str((folder / "proofhouse").resolve())
    assert (folder / "proofhouse" / "SKILL.md").is_file()


def test_terminal_new_agent_next_step_names_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    _interactive(monkeypatch, tmp_path, f"3\nWindsurf\n{tmp_path / 'ws'}\n", [])
    code, out, err = _run(["install-skill"], capsys)
    assert code == 0, err
    assert out.splitlines()[-1] == '  next: start a new chat or session in Windsurf and say "Proofhouse"'


@pytest.mark.parametrize("typed", ["", "9\n0\nx\n", "3\nWindsurf\n\n"])
def test_terminal_without_a_valid_answer_exits_2_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, typed: str
) -> None:
    _interactive(monkeypatch, tmp_path, typed, [".claude"])
    code, out, err = _run(["install-skill"], capsys)
    assert code == 2 and out == ""
    assert "--host" in err
    assert not (tmp_path / ".claude" / "skills").exists() and not (tmp_path / ".cursor").exists()


def test_terminal_with_host_flag_asks_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    _interactive(monkeypatch, tmp_path, "", [])
    code, _, err = _run(["install-skill", "--host", "claude"], capsys)
    assert code == 0 and err == ""
    assert (tmp_path / ".claude" / "skills" / "proofhouse" / "SKILL.md").is_file()


def test_null_device_stdin_is_not_a_terminal_and_installs_for_the_only_agent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    # On Windows the null device reports isatty() == True; a program or agent passing it
    # must get detection, not a question nobody can answer.
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    null = open(__import__("os").devnull)
    monkeypatch.setattr("sys.stdin", null)
    (tmp_path / ".claude").mkdir()
    try:
        code, out, err = _run(["install-skill"], capsys)
    finally:
        null.close()
    assert code == 0, err
    assert "Which agent" not in err
    assert (tmp_path / ".claude" / "skills" / "proofhouse" / "SKILL.md").is_file()


def test_terminal_answer_that_looks_like_a_digit_but_is_not_one_is_refused_not_a_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    _interactive(monkeypatch, tmp_path, "²\n", [".claude"])  # superscript two
    code, out, err = _run(["install-skill"], capsys)
    assert code == 2 and out == ""
    assert not (tmp_path / ".claude" / "skills").exists()


def test_terminal_with_dest_asks_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    _interactive(monkeypatch, tmp_path, "", [".claude"])
    code, out, err = _run(["install-skill", "--dest", str(tmp_path / "skills")], capsys)
    assert code == 0, err
    assert "Which agent" not in err
    assert (tmp_path / "skills" / "proofhouse" / "SKILL.md").is_file()


def test_json_host_reports_the_detected_agent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "ph"))
    (tmp_path / ".claude").mkdir()
    code, out, _ = _run(["install-skill", "--json"], capsys)
    assert code == 0
    assert json.loads(out)["data"]["host"] == "claude"


def test_a_plain_file_named_like_an_agent_folder_is_not_an_agent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "ph"))
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".cursor").write_text("not a folder")
    code, out, err = _run(["install-skill"], capsys)
    assert code == 0, err
    assert (tmp_path / ".claude" / "skills" / "proofhouse" / "SKILL.md").is_file()


def test_terminal_new_agent_folder_typed_with_a_tilde_lands_under_the_home_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    elsewhere = tmp_path / "cwd"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    _interactive(monkeypatch, tmp_path, "3\nWindsurf\n~/ws/skills\n", [])
    code, out, err = _run(["install-skill"], capsys)
    assert code == 0, err
    assert (tmp_path / "ws" / "skills" / "proofhouse" / "SKILL.md").is_file()
    assert not (elsewhere / "~").exists()


def test_host_cursor_next_step_names_a_cursor_agent_chat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    code, out, err = _run(["install-skill", "--host", "cursor"], capsys)
    assert code == 0, err
    assert out.splitlines()[-1] == '  next: start a new Cursor Agent chat and say "Proofhouse"'


def test_terminal_answer_that_is_a_huge_number_is_refused_not_a_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    _interactive(monkeypatch, tmp_path, "9" * 5000 + "\n", [".claude"])
    code, out, err = _run(["install-skill"], capsys)
    assert code == 2 and out == ""
    assert not (tmp_path / ".claude" / "skills").exists()


def test_terminal_menu_marks_found_only_on_the_line_of_an_agent_folder_that_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    _interactive(monkeypatch, tmp_path, "", [".claude"])
    (tmp_path / ".cursor").write_text("not a folder")
    _, _, err = _run(["install-skill"], capsys)
    lines = err.splitlines()
    claude_line = next(line for line in lines if "1) Claude Code" in line)
    cursor_line = next(line for line in lines if "2) Cursor" in line)
    assert claude_line.endswith("(found)")
    assert "(found)" not in cursor_line


@pytest.mark.parametrize(
    ("present", "reason"),
    [([], "found no agent folder"), ([".claude", ".cursor"], "found more than one agent folder")],
)
def test_no_host_flag_refusal_says_whether_none_or_several_agent_folders_were_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, present: list[str], reason: str
) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    for name in present:
        (tmp_path / name).mkdir()
    code, _, err = _run(["install-skill"], capsys)
    assert code == 2
    assert reason in err
