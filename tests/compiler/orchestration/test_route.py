"""ADR-008 route classifier (T-P4-01)."""

from __future__ import annotations

import json

from proofhouse.compiler.orchestration.route import RouteDecision, RouteRequest, route


def test_nothing_new_is_first_class() -> None:
    decision = route(RouteRequest("nothing new is needed for this", {}))
    assert decision.artifact_class == "nothing_new"
    assert decision.ship_walk is False


def test_one_prompt_is_first_class() -> None:
    decision = route(RouteRequest("one prompt is enough", {}))
    assert decision.artifact_class == "one_prompt"
    assert decision.ship_walk is False


def test_site_sets_ship_walk_and_does_not_inline_html() -> None:
    decision = route(RouteRequest("build a marketing website for the foundry", {}))
    assert decision.artifact_class == "site"
    assert decision.ship_walk is True
    blob = json.dumps(decision.to_dict())
    assert "<" not in blob
    assert "html" not in blob.lower()


def test_media_must_not_say_certified() -> None:
    decision = route(RouteRequest("generate a product video and thumbnail image", {}))
    assert decision.artifact_class == "media"
    assert decision.ship_walk is False
    assert "certified" not in decision.rationale.lower()
    assert "CERTIFIED" not in json.dumps(decision.to_dict())


def test_away_signal_routes_hook_or_loop() -> None:
    decision = route(RouteRequest("run this check while Boss is away", {}))
    assert decision.artifact_class in {"hook", "loop"}


def test_route_does_not_mutate_or_require_ir() -> None:
    ir = {"spec_version": "0.1.0", "ir_sha256": "deadbeef"}
    decision = route(RouteRequest("write one prompt for the fake adapter", {"ir": ir}))
    dumped = json.dumps(decision.to_dict())
    assert "deadbeef" not in dumped
    assert decision.artifact_class in {
        "prompt",
        "one_prompt",
        "nothing_new",
        "plain_code",
    }
    assert ir["ir_sha256"] == "deadbeef"


def test_cli_route_json_matches_library(capsys) -> None:
    from proofhouse.compiler import cli_compiler

    expected = route(RouteRequest("build a marketing website", {})).to_dict()
    code = cli_compiler.main(
        ["route", "--objective", "build a marketing website", "--json"]
    )
    assert code == cli_compiler.EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    assert payload == expected
