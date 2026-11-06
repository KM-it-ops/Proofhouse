"""A provider entry can carry extra request fields (also_send), such as switching a model's thinking off."""
from __future__ import annotations

import json

import pytest

from proofhouse import cli, live, providers


class Seen:
    def __init__(self) -> None:
        self.bodies: list[dict[str, object]] = []

    def __call__(self, request: live.Request) -> live.Response:
        self.bodies.append(json.loads(request.body_bytes))
        return live.Response(200, {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]})


def test_also_send_rides_along_with_every_request() -> None:
    assert cli.main(["providers", "add", "ollama", "--base-url", "http://localhost:11434/v1",
                     "--also-send", "reasoning_effort=none", "--also-send", 'options={"num_ctx": 8192}']) == 0
    seen = Seen()
    result = live.run_prompt("ollama", "qwen3.5:4b", prompt="hi", max_output_tokens=64, transport=seen)
    assert result.status == "success", result.message
    assert seen.bodies[0]["reasoning_effort"] == "none"
    assert seen.bodies[0]["options"] == {"num_ctx": 8192}
    assert seen.bodies[0]["max_tokens"] == 64 and seen.bodies[0]["model"] == "qwen3.5:4b"


def test_without_also_send_nothing_extra_is_sent() -> None:
    seen = Seen()
    live.run_prompt("ollama", "llama3.2", prompt="hi", transport=seen)
    assert set(seen.bodies[0]) == {"model", "messages", "max_tokens"}


@pytest.mark.parametrize("field", sorted(providers.RESERVED_FIELDS))
def test_also_send_cannot_set_what_proofhouse_sets_or_what_changes_the_cost(field: str) -> None:
    with pytest.raises(providers.ProviderError, match=field):
        providers.parse_provider({"id": "x", "base_url": "https://api.example.com/v1", "also_send": {field: 2}}, "yours")


@pytest.mark.parametrize("bad", [[], "reasoning_effort=none", {"": 1}])
def test_also_send_must_be_an_object_of_named_fields(bad: object) -> None:
    with pytest.raises(providers.ProviderError, match="also_send"):
        providers.parse_provider({"id": "x", "base_url": "https://api.example.com/v1", "also_send": bad}, "yours")


def test_a_bad_also_send_flag_is_refused_and_nothing_is_saved() -> None:
    assert cli.main(["providers", "add", "myhost", "--base-url", "https://api.example.com/v1", "--also-send", "nofield"]) != 0
    assert providers.load_user()["providers"] == []


def test_a_paid_provider_never_gets_also_send_fields_past_the_spend_gate() -> None:
    assert cli.main(["providers", "add", "myhost", "--base-url", "https://api.example.com/v1", "--key-env", "MYHOST_KEY",
                     "--also-send", "service_tier=priority"]) == 0
    assert cli.main(["providers", "price", "myhost", "m1", "--input", "1", "--output", "2"]) == 0
    seen = Seen()
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("MYHOST_KEY", "k")
        result = live.run_prompt("myhost", "m1", prompt="hi", max_cost_usd="1", transport=seen)
    assert result.status == "refused" and result.code == "PHC-COST-0003" and "service_tier" in (result.message or "")
    assert seen.bodies == []


def test_on_this_machine_only_the_entrys_own_value_gets_through() -> None:
    from proofhouse import spend

    assert cli.main(["providers", "add", "ollama", "--base-url", "http://localhost:11434/v1", "--also-send", "reasoning_effort=none"]) == 0
    body = {"model": "m", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 8, "reasoning_effort": "high"}
    gated = spend.send_within_ceiling(body, provider="ollama", model="m", max_output_tokens=8,
                                      ceiling_usd=live.LOCAL_DEFAULT_LIMIT_USD, send=lambda _: None)
    assert gated.admission.decision != "admitted" and "reasoning_effort" in (gated.admission.message or "")
