"""docs/reference-workflow.md is executable: every ``pc ...`` line runs, with the exit code its comment states.

This keeps the hand-run walkthrough honest in addition to scripts/reference_workflow.py.
"""
from __future__ import annotations

import re
import shlex
import shutil
from pathlib import Path

from proofhouse.compiler import cli_compiler

REPO = Path(__file__).resolve().parents[1]
DOC = REPO / "docs" / "reference-workflow.md"
EXAMPLE = REPO / "examples" / "reference-advisory"
EXIT_COMMENT = re.compile(r"#\s*exit\s+(\d+)")


def _commands() -> list[tuple[list[str], int]]:
    text = DOC.read_text(encoding="utf-8")
    blocks = re.findall(r"```bash\n(.*?)```", text, flags=re.DOTALL)
    joined: list[str] = []
    for block in blocks:
        buffer = ""
        for line in block.splitlines():
            buffer += line.rstrip("\\").rstrip() + " " if line.rstrip().endswith("\\") else line
            if not line.rstrip().endswith("\\"):
                joined.append(buffer.strip())
                buffer = ""
    commands = []
    for line in joined:
        if not line.startswith("pc "):
            continue
        expected = 0
        match = EXIT_COMMENT.search(line)
        if match:
            expected = int(match.group(1))
        code_part = line.split(" #", 1)[0]
        commands.append((shlex.split(code_part)[1:], expected))
    return commands


def test_doc_has_the_whole_journey() -> None:
    names = [" ".join(argv[:2]) for argv, _ in _commands()]
    for step in ("optimize new", "optimize compile", "optimize record", "optimize output", "optimize check",
                 "optimize revise", "optimize compare", "optimize report", "optimize export", "optimize import"):
        assert step in names, step


def test_every_documented_command_runs_as_documented(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    for item in EXAMPLE.iterdir():
        shutil.copy(item, tmp_path / item.name)
    monkeypatch.chdir(tmp_path)
    for argv, expected in _commands():
        code = cli_compiler.main(argv)
        captured = capsys.readouterr()
        assert code == expected, (argv, captured.out, captured.err)
        if argv[:2] == ["optimize", "new"]:
            # "Put the answers in advisory-case/answers.json (the example has them)".
            shutil.copy(tmp_path / "answers.json", tmp_path / "advisory-case" / "answers.json")
    assert (tmp_path / "report.md").is_file()
    assert (tmp_path / "elsewhere" / "advisory-case" / "case.json").is_file()
