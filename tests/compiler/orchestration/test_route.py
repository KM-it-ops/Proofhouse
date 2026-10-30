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


def test_video_must_not_say_certified() -> None:
    decision = route(RouteRequest("generate a product video and thumbnail image", {}))
    assert decision.artifact_class == "video"
    assert decision.ship_walk is False
    assert "certified" not in decision.rationale.lower()
    assert "CERTIFIED" not in json.dumps(decision.to_dict())


def test_away_signal_routes_hook_or_loop() -> None:
    decision = route(RouteRequest("run this check while Boss is away", {}))
    assert decision.artifact_class in {"hook", "loop"}
    assert "without an operator" in decision.rationale


def test_going_away_routes_a_loop() -> None:
    assert route(RouteRequest("Run checks when I go away", {})).artifact_class == "loop"
    assert route(RouteRequest("send the report right away", {})).artifact_class != "loop"


def test_still_pictures_take_the_media_lane() -> None:
    assert route(RouteRequest("make an image", {})).artifact_class == "video"
    assert route(RouteRequest("make a thumbnail image", {})).artifact_class == "video"
    assert route(RouteRequest("build a docker image for the api", {})).artifact_class != "video"
    assert route(RouteRequest("build an image search tool", {})).artifact_class != "video"


def test_an_app_with_a_word_before_it_is_still_an_app() -> None:
    for goal in (
        "an installable app to track my water intake",
        "build a simple budgeting app for my family",
        "I need an offline-first habit tracking app",
        "a progressive web app for tracking workouts",
    ):
        assert route(RouteRequest(goal, {})).artifact_class == "app", goal
    # What the app only reads or is named in stays what it was.
    assert route(RouteRequest("a prompt that summarizes reviews for a recipe app", {})).artifact_class == "prompt"


def test_must_survive_routes_harness() -> None:
    assert route(RouteRequest("make a process that must survive failure", {})).artifact_class == "harness"
    assert route(RouteRequest("make an image that must survive resizing", {})).artifact_class != "harness"


def test_credentials_route_a_tool() -> None:
    assert route(RouteRequest("connect with credentials", {})).artifact_class == "tool"
    assert route(RouteRequest("connect to the vendor with a token", {})).artifact_class == "tool"
    assert route(RouteRequest("write a guide to using credentials", {})).artifact_class != "tool"


def test_long_goals_take_linear_time() -> None:
    import time

    def seconds(count: int) -> float:
        start = time.perf_counter()
        route(RouteRequest("make a video for the team " * count, {}))
        return time.perf_counter() - start

    seconds(200)
    small, large = seconds(1000), seconds(4000)
    # Four times the text, so about four times the time; a square law would be sixteen.
    assert large < small * 10 + 0.05


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
