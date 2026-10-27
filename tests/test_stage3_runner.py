"""Fast Stage 3 case-list checks; these never execute a hard case."""

from __future__ import annotations

from collections import Counter

from scripts.stage3_hard_cases import CASES, parser_commands


def test_two_cases_for_every_real_top_level_subcommand() -> None:
    counts = Counter(case.command for case in CASES)
    commands = parser_commands()
    assert len(commands) == 39
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
