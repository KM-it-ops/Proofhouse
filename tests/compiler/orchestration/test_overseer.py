"""Overseer dispatches to the same route implementation (T-P4-03)."""

from __future__ import annotations

import json

from proofhouse.compiler import cli_compiler
from proofhouse.compiler.orchestration.overseer import dispatch
from proofhouse.compiler.orchestration.route import RouteRequest, route

FIXTURES = (
    "build a marketing website",
    "nothing new is needed",
    "generate a product video",
)


def test_dispatch_matches_route_for_three_fixtures() -> None:
    for objective in FIXTURES:
        assert dispatch(objective).to_dict() == route(RouteRequest(objective, {})).to_dict()


def test_overseer_cli_matches_route_cli(capsys) -> None:
    for objective in FIXTURES:
        route_code = cli_compiler.main(["route", "--objective", objective, "--json"])
        route_payload = json.loads(capsys.readouterr().out)
        overseer_code = cli_compiler.main([objective, "--json"])
        overseer_payload = json.loads(capsys.readouterr().out)
        assert route_code == cli_compiler.EXIT_SUCCESS
        assert overseer_code == cli_compiler.EXIT_SUCCESS
        assert overseer_payload == route_payload


def test_both_console_scripts_reach_the_one_front_door() -> None:
    # MISSION-040 (OAR-033 option B): proofhouse is the front door; proofhouse-compiler is an alias of it.
    from pathlib import Path

    text = Path(__file__).resolve().parents[3].joinpath("pyproject.toml").read_text(encoding="utf-8")
    assert 'proofhouse = "proofhouse.cli:main"' in text
    assert 'proofhouse-compiler = "proofhouse.cli:main"' in text
