"""Windows cp1252 --help and doctor honesty (T-P3-01)."""

from __future__ import annotations

from proofhouse.compiler import api, cli_compiler

CLOSED_LOOP_HELP = (
    "Headless closed-loop (OAR-006 certified slice): structured requirements or "
    "plain_language_v0 envelope -> IR -> fake adapter -> eval/repair -> evidence. "
    "Not a live provider. Not full MISSION-008."
)

DOCTOR_OFFLINE_DETAIL = (
    "certified path performs no network access; this is an assertion, not a probe"
)


def test_format_help_encodes_to_cp1252() -> None:
    help_text = cli_compiler.build_parser().format_help()
    help_text.encode("cp1252")
    assert "\u2192" not in help_text


def test_closed_loop_help_is_certified_slice() -> None:
    parser = cli_compiler.build_parser()
    action = parser._subparsers._group_actions[0]
    helps = {choice.dest: choice.help for choice in action._choices_actions}
    assert helps["closed-loop"] == CLOSED_LOOP_HELP


def test_doctor_offline_mode_is_an_assertion() -> None:
    env = api.doctor()
    checks = {c["name"]: c for c in env.data["checks"]}
    assert "offline_mode" not in checks
    check = checks["offline_mode_assertion"]
    assert check["ok"] is True
    assert check["detail"] == DOCTOR_OFFLINE_DETAIL
