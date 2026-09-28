"""README "How it works" is executable: every ``pc ...`` line runs, with the exit code its comment states.

Same rules as tests/test_reference_workflow_doc.py: the inputs are the files in
examples/reference-advisory/, and the answers are put in advisory-case/answers.json
after ``optimize new`` (the README says to save them).
"""
from __future__ import annotations

import re
import shlex
import shutil
from pathlib import Path

from proofhouse.compiler import cli_compiler

REPO = Path(__file__).resolve().parents[1]
README = REPO / "README.md"
EXAMPLE = REPO / "examples" / "reference-advisory"
EXIT_COMMENT = re.compile(r"#\s*exit\s+(\d+)")


def _commands() -> list[tuple[list[str], int]]:
    text = README.read_text(encoding="utf-8")
    section = text.split("\n## How it works", 1)[1].split("\n## ", 1)[0]
    commands = []
    for block in re.findall(r"```bash\n(.*?)```", section, flags=re.DOTALL):
        for line in block.splitlines():
            line = line.strip()
            if not line.startswith("pc "):
                continue
            match = EXIT_COMMENT.search(line)
            commands.append((shlex.split(line.split(" #", 1)[0])[1:], int(match.group(1)) if match else 0))
    return commands


def test_readme_how_it_works_runs_as_written(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    for item in EXAMPLE.iterdir():
        shutil.copy(item, tmp_path / item.name)
    monkeypatch.chdir(tmp_path)
    commands = _commands()
    assert commands, "no pc commands found under ## How it works"
    for argv, expected in commands:
        code = cli_compiler.main(argv)
        captured = capsys.readouterr()
        assert code == expected, (argv, captured.out, captured.err)
        if argv[:2] == ["optimize", "new"]:
            shutil.copy(tmp_path / "answers.json", tmp_path / "advisory-case" / "answers.json")
