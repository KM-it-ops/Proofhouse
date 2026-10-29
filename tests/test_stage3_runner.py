"""Fast Stage 3 case-list checks; these never execute a hard case."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from scripts.stage3_hard_cases import (CASES, Case, Expected, _captured, _environment, _exit_code, _safety,
                                       parser_commands)


def test_two_cases_for_every_real_top_level_subcommand() -> None:
    counts = Counter(case.command for case in CASES)
    commands = parser_commands()
    assert len(commands) == 40
    assert set(counts) == commands
    assert all(counts[command] >= 2 for command in commands)


def test_case_ids_are_unique() -> None:
    ids = [case.id for case in CASES]
    assert len(ids) == len(set(ids))


def test_every_case_has_written_expectations() -> None:
    for case in CASES:
        assert case.argv and case.argv[0] == case.command, case.id
        assert case.hard and case.hard.endswith("."), case.id
        assert case.expected.exits, case.id
        assert case.expected.must or case.expected.exists or case.expected.absent, case.id
        assert "Traceback" in case.expected.must_not, case.id


def _case(*argv: str, command: str = "check") -> Case:
    return Case(id="x-1", command=command, hard="A hard case.", argv=(command, *argv), fixtures=(),
                expected=Expected(exits=(0,), must=("ok",)))


BACKSLASH = chr(92)


@pytest.mark.parametrize("value", ["--out=C:" + BACKSLASH + "outside", "--case=/outside", "--in=.." + BACKSLASH + "up", "--out=a/../../up"])
def test_safety_refuses_an_option_value_that_leaves_the_case_folder(value: str) -> None:
    with pytest.raises(ValueError):
        _safety(_case(value))


def test_safety_accepts_an_ordinary_option_value() -> None:
    _safety(_case("--out=results", "--score=7"))


def test_environment_drops_connection_strings_and_personal_access_tokens(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DATABASE_URL", "POSTGRES_URL", "CONNECTION_STRING", "GH_PAT", "REDIS_URL", "AWS_SESSION", "SENTRY_DSN"):
        monkeypatch.setenv(name, "fake-test-value")
    env = _environment(tmp_path)
    leaked = [name for name in env if env[name] == "fake-test-value"]
    assert leaked == []


def test_a_timed_out_case_has_its_local_paths_scrubbed(tmp_path: Path) -> None:
    raw = f"workspace {tmp_path} and {tmp_path.as_posix()}".encode()
    text = _captured(raw, tmp_path)
    assert str(tmp_path) not in text and tmp_path.as_posix() not in text
    assert "<case>" in text


def test_the_runner_fails_when_any_case_broke() -> None:
    held = {"verdict": "held", "unable": False}
    broke = {"verdict": "broke", "unable": False}
    assert _exit_code([held, held], under_two=[]) == 0
    assert _exit_code([held, broke], under_two=[]) == 1
    assert _exit_code([held, {"verdict": "held", "unable": True}], under_two=[]) == 1
    assert _exit_code([held], under_two=["make"]) == 1
