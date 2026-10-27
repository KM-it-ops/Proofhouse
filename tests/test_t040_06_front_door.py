"""T-040-06: the front door (SPEC §2.1), the architecture test, and the done check's end-to-end flow.

Architecture test (design §2.4), failing the build when broken:
(a) there is one command tree; (b) every command path is in one explicit map,
as a spine command or a registered part id; (c) the package declares exactly
two console scripts, both pointing at the same ``main``.

The end-to-end flow (SPEC §5 bullet 1) runs one prompt case and one skill case
through identical commands, with the network blocked and no API key set: it
must work with no AI driver at all.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest

from proofhouse import cli, parts
from proofhouse.command_map import COMMAND_MAP, PART, SPINE
from proofhouse.compiler import cli_compiler

ROOT = Path(__file__).resolve().parents[1]
API_KEY_VARS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "XAI_API_KEY")


@pytest.fixture(autouse=True)
def _sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "user-home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "ph"))
    monkeypatch.delenv("PROOFHOUSE_EXPERIMENTAL", raising=False)


def front(argv: list[str], capsys, prog: str = "proofhouse") -> tuple[int, str, str]:
    code = cli.main(argv, prog=prog)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def command_paths(parser: argparse.ArgumentParser, prefix: tuple[str, ...] = ()) -> set[str]:
    paths: set[str] = set()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, sub in action.choices.items():
                below = command_paths(sub, (*prefix, name))
                paths |= below or {" ".join((*prefix, name))}
    return paths


# --- the architecture test ----------------------------------------------------------------


def test_a_there_is_one_command_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    for gate in ("", "1"):
        monkeypatch.setenv("PROOFHOUSE_EXPERIMENTAL", gate)
        assert command_paths(cli.build_parser()) == command_paths(cli_compiler.build_parser())
    source = (ROOT / "src" / "proofhouse" / "cli.py").read_text(encoding="utf-8")
    assert "ArgumentParser(" not in source  # the front door builds no tree of its own


def test_b_every_command_path_is_mapped_to_the_spine_or_a_registered_part(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_EXPERIMENTAL", "1")  # the gated commands are in the map too
    paths = command_paths(cli_compiler.build_parser())
    assert sorted(paths - set(COMMAND_MAP)) == [], "commands missing from proofhouse.command_map"
    assert sorted(set(COMMAND_MAP) - paths) == [], "command_map lists commands that do not exist"
    registered = set(parts.part_ids())
    for path, (role, part_id, reason) in COMMAND_MAP.items():
        assert role in (SPINE, PART), path
        assert reason and "\n" not in reason, path
        if role == PART:
            assert part_id in registered, f"{path} names unregistered part {part_id!r}"
        else:
            assert part_id == "", path


def test_c_exactly_two_console_scripts_both_pointing_at_the_same_main() -> None:
    scripts = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
    assert set(scripts) == {"proofhouse", "proofhouse-compiler"}
    assert len(set(scripts.values())) == 1
    module, func = next(iter(scripts.values())).split(":")
    assert (module, func) == ("proofhouse.cli", "main")
    entry_points = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "proofhouse.parts" not in entry_points.split("[project.scripts]", 1)[1].split("[tool", 1)[0]


def test_no_plug_in_discovery_entry_point_group() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "entry-points" not in text and "entry_points" not in text


# --- the front door -------------------------------------------------------------------------


def test_proofhouse_compiler_prints_one_notice_on_stderr_and_behaves_the_same(capsys) -> None:
    code_a, out_a, err_a = front(["parts", "--json"], capsys, prog="proofhouse")
    code_b, out_b, err_b = front(["parts", "--json"], capsys, prog="/usr/local/bin/proofhouse-compiler")
    assert code_a == code_b == 0
    assert out_a == out_b  # stdout, and so --json, is untouched
    assert err_a == ""
    assert err_b == cli.COMPILER_NOTICE + "\n"
    for prog in ("proofhouse-compiler.exe", r"C:\tools\Scripts\proofhouse-compiler.exe", "proofhouse-compiler-script.py"):
        assert front(["parts"], capsys, prog=prog)[2] == cli.COMPILER_NOTICE + "\n"


def test_optimize_alias_prints_its_notice_and_matches_case(tmp_path: Path, capsys) -> None:
    case = tmp_path / "c"
    assert front(["case", "new", "--case", str(case), "--objective", "a b", "--model", "Zeta 9"], capsys)[0] == 0
    code_a, out_a, err_a = front(["case", "status", "--case", str(case)], capsys)
    code_b, out_b, err_b = front(["optimize", "status", "--case", str(case)], capsys)
    assert code_a == code_b == 0
    assert out_a == out_b
    assert err_a == ""
    assert err_b.splitlines() == [
        (
            "notice: 'proofhouse optimize' is now 'proofhouse case' (same subcommands and flags); "
            "the optimize alias will be removed after 0.5"
        )
    ]


def test_case_carries_every_optimize_subcommand() -> None:
    paths = command_paths(cli_compiler.build_parser())
    case = {p.removeprefix("case ") for p in paths if p.startswith("case ")}
    optimize = {p.removeprefix("optimize ") for p in paths if p.startswith("optimize ")}
    assert case == optimize
    for name in ("new", "compile", "record", "revise", "status", "criteria add", "verdict", "check",
                 "constraints add", "output add", "compare", "report", "export", "import"):
        assert name in case


@pytest.mark.parametrize(
    ("argv", "new_form"),
    [
        (["validate", "--dataset", "x.jsonl"], "proofhouse eval validate --dataset"),
        (["validate", "--dataset=x.jsonl"], "proofhouse eval validate --dataset"),
        (["report", "--dataset", "x", "--out", "y"], "proofhouse eval report"),
        (["loadouts"], "proofhouse eval loadouts"),
        (["compile-loadout", "--id", "x"], "proofhouse eval compile-loadout"),
        (["generate", "--project-name", "x"], "proofhouse eval generate"),
    ],
)
def test_each_old_harness_form_fails_with_one_line_naming_the_new_form(argv: list[str], new_form: str, capsys) -> None:
    code, out, err = front(argv, capsys)
    assert code != 0 and code == cli_compiler.EXIT_USAGE_ERROR
    assert out == ""
    assert len(err.splitlines()) == 1
    assert new_form in err


def test_validate_without_dataset_is_still_ir_validation(capsys) -> None:
    code, _out, err = front(["validate", str(ROOT / "examples" / "ir_minimal.json")], capsys)
    assert code == 0, err


def test_eval_harness_runs_under_eval(capsys) -> None:
    code, out, _err = front(["eval", "validate", "--dataset", str(ROOT / "evals/datasets/prompt_audit_cases.jsonl")], capsys)
    assert code == 0 and out.startswith("Dataset validation passed")
    assert front(["eval", "loadouts"], capsys)[0] == 0


def test_scan_and_parts_stay_top_level(tmp_path: Path, capsys) -> None:
    (tmp_path / "proj").mkdir()
    assert front(["scan", str(tmp_path / "proj"), "--json"], capsys)[0] == 0
    code, out, _ = front(["parts"], capsys)
    assert code == 0 and "skill-checker" in out


def test_adapters_keeps_its_request_builder_output(capsys) -> None:
    code, out, _ = front(["adapters", "--json"], capsys)
    assert code == 0
    assert "text-checker" not in out and "install-skill" not in out


def test_overseer_trigger_still_reaches_route(capsys) -> None:
    code, out, _ = front(["write one prompt for a product description", "--json"], capsys)
    assert code == 0
    assert "class" in json.loads(out) or "artifact_class" in json.loads(out)


def test_case_new_kind_flag(tmp_path: Path, capsys) -> None:
    for flag, kind in (([], "prompt.text@1"), (["--kind", "prompt"], "prompt.text@1"), (["--kind", "skill"], "agent.skill@1")):
        case = tmp_path / f"c-{len(flag)}-{kind}"
        code, _out, err = front(["case", "new", "--case", str(case), "--objective", "x y", "--model", "Zeta 9", *flag], capsys)
        assert code == 0, err
        assert json.loads((case / "case.json").read_text(encoding="utf-8"))["kind"] == kind
    code, _out, err = front(["case", "new", "--case", str(tmp_path / "bad"), "--objective", "x", "--model", "Z", "--kind", "image"], capsys)
    assert code == 2 and not (tmp_path / "bad").exists()


def test_python_dash_m_front_door(tmp_path: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PROOFHOUSE_HOME": str(tmp_path / "ph")}
    done = subprocess.run(
        [sys.executable, "-m", "proofhouse.cli", "parts", "--json"], capture_output=True, text=True, env=env, timeout=60, check=False
    )
    assert done.returncode == 0, done.stderr
    assert done.stderr == ""
    assert json.loads(done.stdout)["contract_version"] == parts.PART_CONTRACT_VERSION


# --- the done check: objective -> version -> run -> checks -> compare -> export -> import -> re-check --


@pytest.fixture()
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    def _blocked(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    for name in API_KEY_VARS:
        monkeypatch.delenv(name, raising=False)


def write(path: Path, text: str) -> str:
    path.write_text(text, encoding="utf-8")
    return str(path)


def make_version(tmp_path: Path, kind: str, n: int) -> list[str]:
    if kind == "prompt":
        text = "Summarise the advisory for SOC analysts." + (" Write UNKNOWN for anything it does not state." if n == 2 else "")
        return ["--prompt-file", write(tmp_path / f"prompt-v{n}.txt", text)]
    folder = tmp_path / f"skill-v{n}"
    (folder / "scripts").mkdir(parents=True)
    (folder / "SKILL.md").write_text(
        f"---\nname: advisory-summary\ndescription: Summarise advisories, version {n}.\n---\n\n# Use\n", encoding="utf-8"
    )
    (folder / "scripts" / "check.py").write_bytes(b"print('ok')\r\n")
    return ["--skill-folder", str(folder)]


def verify_bundle(bundle: Path) -> None:
    with zipfile.ZipFile(bundle) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        listed = {entry["path"]: entry["sha256"] for entry in manifest["files"]}
        assert set(archive.namelist()) - {"manifest.json"} == set(listed)
        for name, digest in listed.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest


@pytest.mark.parametrize("kind", ["prompt", "skill"])
def test_end_to_end_with_no_ai_driver_and_identical_commands(kind: str, tmp_path: Path, offline, capsys) -> None:
    case = tmp_path / f"{kind}-case"
    steps: list[tuple[list[str], int]] = [
        (["case", "new", "--case", str(case), "--kind", kind, "--model", "Zeta 9",
          "--objective", "Summarise a security advisory for SOC analysts without guessing"], 0),
        (["case", "record", "--case", str(case), *make_version(tmp_path, kind, 1)], 0),
        (["case", "output", "add", "--case", str(case), "--revision", "1", "--input-id", "adv-1", "--model", "host model",
          "--source", "pasted", "--output-file", write(tmp_path / "out-1.txt", "Severity high. Exploited in the wild.")], 0),
        (["case", "criteria", "add", "--case", str(case), "--id", "UNK", "--target", "output", "--must-contain", "UNKNOWN"], 0),
        (["case", "criteria", "add", "--case", str(case), "--id", "OWN",
          *(["--must-contain", "SOC analysts"] if kind == "prompt" else ["--skill-check", "install-roundtrip"])], 0),
        (["case", "check", "--case", str(case)], 3),
        (["case", "record", "--case", str(case), *make_version(tmp_path, kind, 2)], 0),
        (["case", "output", "add", "--case", str(case), "--revision", "2", "--input-id", "adv-1", "--model", "host model",
          "--source", "pasted", "--output-file", write(tmp_path / "out-2.txt", "Severity high. Exploitation: UNKNOWN.")], 0),
        (["case", "check", "--case", str(case), "--all"], 3),  # v1 still fails; v2 passes
        (["case", "check", "--case", str(case)], 0),
        (["case", "compare", "--case", str(case), "--from", "1", "--to", "2"], 0),
        (["case", "report", "--case", str(case), "--out", str(tmp_path / "report.md")], 0),
        (["case", "export", "--case", str(case), "--out", str(tmp_path / "bundle.zip")], 0),
        (["case", "import", "--bundle", str(tmp_path / "bundle.zip"), "--case", str(tmp_path / "imported")], 0),
        (["case", "check", "--case", str(tmp_path / "imported")], 0),
    ]
    for argv, expected in steps:
        code, out, err = front(argv, capsys)
        assert code == expected, (argv, out, err)
        assert "notice:" not in err
    verify_bundle(tmp_path / "bundle.zip")
    data = json.loads((tmp_path / "imported" / "case.json").read_text(encoding="utf-8"))
    assert data["kind"] == ("prompt.text@1" if kind == "prompt" else "agent.skill@1")
    assert [run["cost"]["usd"] for run in data["runs"]] == ["unknown", "unknown"]
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "## Cost" in report
    if kind == "skill":
        names = zipfile.ZipFile(tmp_path / "bundle.zip").namelist()
        assert "revisions/v2-files/SKILL.md" in names and "revisions/v2-files/scripts/check.py" in names
        assert "No independent pass ran on this skill" in report


def test_review_f4_command_map_names_test_files_that_exist() -> None:
    import re

    from proofhouse import command_map

    named = re.findall(r"tests/[\w/]+\.py", command_map.__doc__ or "")
    assert named, "the map's docstring should name the architecture test"
    assert [name for name in named if not (ROOT / name).is_file()] == []


def test_version_and_help_name_the_front_door(capsys: pytest.CaptureFixture[str]) -> None:
    from proofhouse import __version__
    from proofhouse.cli import main as front_door

    assert front_door(["--version"], prog="proofhouse") == 0
    assert capsys.readouterr().out.strip() == f"proofhouse {__version__}"

    assert front_door(["--help"], prog="proofhouse") == 0
    usage = capsys.readouterr().out
    assert usage.startswith("usage: proofhouse ")
    assert "proofhouse-compiler" not in usage and "Compiler Core" not in usage
