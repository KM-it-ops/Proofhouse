"""C1: a compiled artifact runs on any provider, never dropping a mandatory requirement.

Until this slice only ``execute_openai`` ran compiled artifacts, and only to
api.openai.com. ``execute_on_provider`` takes any provider Proofhouse knows
(shipped, add-on or yours), sends through the spend gate, and either puts every
mandatory requirement into the request body or stops before sending and names
the requirement it could not carry.

A requirement is "carried" when the OpenAI-style chat body has a field for it
(the openai request builder's supported capabilities) and the provider's entry
does not list it under ``ignores`` -- capabilities its address is documented to
accept and drop. Anthropic's OpenAI-compatible address ignores
``response_format`` and the ``strict`` flag on tools
(https://platform.claude.com/docs/en/api/openai-sdk), so structured output and
strict function calling are refused there rather than sent and lost.

Fake transport only: no network, no real keys.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from proofhouse import providers, spend
from proofhouse.compiler.execution import EXE_CRED_0001, LiveRunRequest, execute_on_provider

from .fixtures.ir_fixtures import (
    ir_with_capabilities,
    ir_with_openai_structured_output,
    ir_with_openai_tool,
    minimal_valid_ir,
)

EXE_CAP_0001 = "EXE-CAP-0001"
EXE_PROV_0001 = "EXE-PROV-0001"
MODEL = "synthetic-model"
STRUCTURED_JSON = "output.structured_json@1"
FUNCTION_CALLING = "tools.function_calling@1"
NEVER_CARRIED = (
    "reasoning.effort_control@1",
    "reasoning.extended_thinking@1",
    "reasoning.thinking_level@1",
    "tools.server_executed@1",
    "media.video_generation@1",
)
GATEWAY = {
    "id": "my-gateway",
    "name": "My gateway",
    "base_url": "https://gateway.example.test/v1",
    "shape": "openai-compatible",
    "key_env": "MY_GATEWAY_KEY",
}


def _shipped() -> list[providers.Provider]:
    return sorted(providers.all_providers().values(), key=lambda p: p.id)


SHIPPED_IDS = [p.id for p in _shipped()]


def _secret_for(provider_id: str) -> str:
    return f"dummy-key-{provider_id}-not-a-secret"


@pytest.fixture(autouse=True)
def _keys_and_prices(monkeypatch: pytest.MonkeyPatch) -> spend.PriceTable:
    """Dummy keys in every provider's key variable, and a test price for every provider."""
    for provider in _shipped():
        if provider.key_env:
            monkeypatch.setenv(provider.key_env, _secret_for(provider.id))
    monkeypatch.setenv(GATEWAY["key_env"], _secret_for(GATEWAY["id"]))
    table = spend.PriceTable(
        version="2026-10-17.1",
        entries=tuple(
            spend.PriceEntry(
                provider=provider_id,
                model=MODEL,
                input_usd_per_million_tokens=Decimal("0.01"),
                output_usd_per_million_tokens=Decimal("0.01"),
                applies_up_to_input_tokens=None,
                service_tier="default",
                source_url="https://example.com/test-prices",
                read_on="2026-10-17",
            )
            for provider_id in [*SHIPPED_IDS, GATEWAY["id"]]
        ),
    )
    monkeypatch.setattr(spend, "load_price_table", lambda: table)
    return table


@pytest.fixture()
def events(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, Any]]:
    """One ordered log: the gate being asked, the gate admitting the bytes, the transport sending them."""
    log: list[tuple[str, Any]] = []
    real = spend.send_within_ceiling

    def gate(body: Any, **kwargs: Any) -> Any:
        log.append(("gate", {"provider": kwargs["provider"], "model": kwargs["model"]}))
        inner = kwargs["send"]

        def admitted(raw: bytes) -> Any:
            log.append(("admitted", raw))
            return inner(raw)

        return real(body, **{**kwargs, "send": admitted})

    monkeypatch.setattr(spend, "send_within_ceiling", gate)
    return log


class RecordingTransport:
    def __init__(self, log: list[tuple[str, Any]]) -> None:
        self.log = log
        self.calls: list[Any] = []

    def send(self, prepared: Any) -> Any:
        self.calls.append(prepared)
        self.log.append(("send", prepared))
        return type("Resp", (), {"status_code": 200, "payload": {"choices": []}})()


def _run(provider_id: str, ir: dict, log: list[tuple[str, Any]], **overrides: Any):
    transport = RecordingTransport(log)
    fields: dict[str, Any] = {
        "opt_in": True,
        "provider": provider_id,
        "model": MODEL,
        "max_output_tokens": 16,
        "max_cost_usd": "1",
        "transport": transport,
    }
    fields.update(overrides)
    return execute_on_provider(json.dumps(ir), LiveRunRequest(**fields)), transport


def _sentinel_ir() -> dict:
    ir = minimal_valid_ir()
    ir["requirements"][0]["statement"] = "REQUIREMENT_SENTINEL_X41 never omit this mandatory instruction"
    ir["requirements"][0]["acceptance"] = ["ACCEPTANCE_SENTINEL_X44"]
    ir["behavior"]["uncertainty_policy"] = "UNCERTAINTY_SENTINEL_X42"
    ir["behavior"]["evidence_policy"] = "EVIDENCE_SENTINEL_X43"
    ir["objective"]["success_criteria"] = ["SUCCESS_SENTINEL_X45"]
    ir["objective"]["failure_conditions"] = ["FAILURE_SENTINEL_X46"]
    ir["behavior"]["instructions"] = ["INSTRUCTION_SENTINEL_X47"]
    ir["behavior"]["constraints"] = ["CONSTRAINT_SENTINEL_X48"]
    return ir


SENTINELS = (
    "REQUIREMENT_SENTINEL_X41",
    "ACCEPTANCE_SENTINEL_X44",
    "UNCERTAINTY_SENTINEL_X42",
    "EVIDENCE_SENTINEL_X43",
    "SUCCESS_SENTINEL_X45",
    "FAILURE_SENTINEL_X46",
    "INSTRUCTION_SENTINEL_X47",
    "CONSTRAINT_SENTINEL_X48",
    "REQ-001",
    "MANDATORY",
)


def _system_text(prepared: Any) -> str:
    return "\n".join(m["content"] for m in prepared.body["messages"] if m["role"] in {"system", "developer"})


def _assert_sent_through_gate(provider_id: str, log: list[tuple[str, Any]], transport: RecordingTransport) -> Any:
    assert [kind for kind, _ in log] == ["gate", "admitted", "send"], log
    assert log[0][1] == {"provider": provider_id, "model": MODEL}
    assert len(transport.calls) == 1
    prepared = transport.calls[0]
    assert prepared.body_bytes == log[1][1], "the transport must send exactly the bytes the gate counted"
    return prepared


def _assert_named_refusal(result: Any, transport: RecordingTransport, log: list, *capabilities: str) -> None:
    assert result.status == "error", result.to_dict()
    assert EXE_CAP_0001 in result.diagnostics
    assert sorted(result.envelope["refused_requirements"]) == sorted(capabilities)
    assert log == [], "a refused requirement must stop the run before the spend gate and the send"
    assert transport.calls == []


# --- every shipped provider: mandatory requirements reach the body ---


@pytest.mark.parametrize("provider_id", SHIPPED_IDS)
def test_mandatory_requirements_reach_every_provider_body(provider_id: str, events: list) -> None:
    profile = providers.find(provider_id)
    assert profile is not None
    result, transport = _run(provider_id, _sentinel_ir(), events)
    assert result.status == "success", result.to_dict()
    prepared = _assert_sent_through_gate(provider_id, events, transport)

    assert prepared.url == profile.chat_url
    assert prepared.body["model"] == MODEL
    cap_field, other = (
        ("max_completion_tokens", "max_tokens") if profile.shape == "openai" else ("max_tokens", "max_completion_tokens")
    )
    assert prepared.body[cap_field] == 16
    assert other not in prepared.body
    system = _system_text(prepared)
    for sentinel in SENTINELS:
        assert sentinel in system, (provider_id, sentinel)


@pytest.mark.parametrize("provider_id", SHIPPED_IDS)
def test_key_comes_from_the_provider_entry_and_never_reaches_the_result(provider_id: str, events: list) -> None:
    profile = providers.find(provider_id)
    assert profile is not None
    result, transport = _run(provider_id, _sentinel_ir(), events)
    assert result.status == "success", result.to_dict()
    headers = transport.calls[0].headers
    if profile.key_env:
        assert headers["Authorization"] == f"Bearer {_secret_for(provider_id)}"
    else:
        assert "Authorization" not in headers, "a provider with no key variable gets no Authorization header"
    rendered = json.dumps(result.to_dict(), default=str)
    assert _secret_for(provider_id) not in rendered


@pytest.mark.parametrize("provider_id", SHIPPED_IDS)
@pytest.mark.parametrize(
    ("capability", "ir_builder", "field"),
    [
        (STRUCTURED_JSON, lambda: ir_with_openai_structured_output(compliant=True), "response_format"),
        (FUNCTION_CALLING, lambda: ir_with_openai_tool(compliant=True), "tools"),
    ],
)
def test_required_capability_is_carried_or_refused_by_name(
    provider_id: str, capability: str, ir_builder: Any, field: str, events: list
) -> None:
    result, transport = _run(provider_id, ir_builder(), events)
    if result.status == "success":
        prepared = _assert_sent_through_gate(provider_id, events, transport)
        assert prepared.body.get(field), f"{provider_id} admitted {capability} but the body has no {field}"
    else:
        _assert_named_refusal(result, transport, events, capability)


def test_structured_output_body_carries_the_exact_contract(events: list) -> None:
    ir = ir_with_openai_structured_output(compliant=True)
    result, transport = _run("mistral", ir, events)
    assert result.status == "success", result.to_dict()
    response_format = transport.calls[0].body["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["schema"] == ir["output_contracts"][0]["schema"]
    assert response_format["json_schema"]["strict"] is True


@pytest.mark.parametrize("capability", [STRUCTURED_JSON, FUNCTION_CALLING])
def test_anthropic_compatible_address_refuses_what_it_is_documented_to_ignore(capability: str, events: list) -> None:
    ir = ir_with_openai_structured_output() if capability == STRUCTURED_JSON else ir_with_openai_tool()
    result, transport = _run("anthropic", ir, events)
    _assert_named_refusal(result, transport, events, capability)


@pytest.mark.parametrize(("capability", "field"), [(STRUCTURED_JSON, "response_format"), (FUNCTION_CALLING, "tools")])
def test_optional_capability_the_address_ignores_is_rendered_not_sent(capability: str, field: str, events: list) -> None:
    ir = ir_with_openai_structured_output() if capability == STRUCTURED_JSON else ir_with_openai_tool()
    ir["provider_requirements"] = {"required_capabilities": [], "optional_capabilities": [capability]}
    result, transport = _run("anthropic", ir, events)
    assert result.status == "success", result.to_dict()
    prepared = _assert_sent_through_gate("anthropic", events, transport)
    assert field not in prepared.body, f"anthropic drops {field}, so sending it would lose it silently"
    system = _system_text(prepared)
    if capability == STRUCTURED_JSON:
        assert ir["output_contracts"][0]["id"] in system, "the output contract must reach the prompt instead"
    else:
        assert ir["tools"][0]["id"] in system, "the tool definitions must reach the prompt instead"
    fields = {row["source_path"]: row for row in result.envelope["runtime_context"]["fields"]}
    rendered_path = "/output_contracts" if capability == STRUCTURED_JSON else "/tools"
    assert fields[rendered_path]["disposition"] != "enforced_by_request_parameter"


@pytest.mark.parametrize("provider_id", SHIPPED_IDS)
@pytest.mark.parametrize("capability", NEVER_CARRIED)
def test_required_capability_the_chat_body_cannot_hold_is_refused_by_name(
    provider_id: str, capability: str, events: list
) -> None:
    result, transport = _run(provider_id, ir_with_capabilities(required=[capability]), events)
    _assert_named_refusal(result, transport, events, capability)


def test_refusal_names_only_what_cannot_be_carried(events: list) -> None:
    ir = ir_with_openai_structured_output()
    ir["provider_requirements"]["required_capabilities"].append("reasoning.effort_control@1")
    result, transport = _run("openai", ir, events)
    _assert_named_refusal(result, transport, events, "reasoning.effort_control@1")


def test_optional_capability_that_cannot_be_carried_does_not_block(events: list) -> None:
    result, transport = _run("openai", ir_with_capabilities(optional=["reasoning.effort_control@1"]), events)
    assert result.status == "success", result.to_dict()
    _assert_sent_through_gate("openai", events, transport)


# --- your own providers file ---


def _write_user_providers(entry: dict) -> None:
    home = Path(providers.proofhouse_home())
    home.mkdir(parents=True, exist_ok=True)
    (home / "providers.json").write_text(
        json.dumps({"schema": "proofhouse.providers/v1", "providers": [entry]}), encoding="utf-8"
    )


def test_a_provider_from_your_own_file_runs(events: list) -> None:
    _write_user_providers(GATEWAY)
    result, transport = _run(GATEWAY["id"], _sentinel_ir(), events)
    assert result.status == "success", result.to_dict()
    prepared = _assert_sent_through_gate(GATEWAY["id"], events, transport)
    assert prepared.url == "https://gateway.example.test/v1/chat/completions"
    assert prepared.body["max_tokens"] == 16
    assert "REQUIREMENT_SENTINEL_X41" in _system_text(prepared)


def test_your_provider_can_say_what_its_address_ignores(events: list) -> None:
    _write_user_providers({**GATEWAY, "ignores": [STRUCTURED_JSON]})
    result, transport = _run(GATEWAY["id"], ir_with_openai_structured_output(), events)
    _assert_named_refusal(result, transport, events, STRUCTURED_JSON)


# --- fail closed before any send ---


def test_unknown_provider_is_refused_by_name(events: list) -> None:
    result, transport = _run("no-such-provider", _sentinel_ir(), events)
    assert result.status == "error"
    assert EXE_PROV_0001 in result.diagnostics
    assert "no-such-provider" in json.dumps(result.to_dict())
    assert events == [] and transport.calls == []


def test_missing_key_for_a_cloud_provider_stops_before_the_gate(monkeypatch: pytest.MonkeyPatch, events: list) -> None:
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    result, transport = _run("mistral", _sentinel_ir(), events)
    assert result.status == "error"
    assert EXE_CRED_0001 in result.diagnostics
    assert events == [] and transport.calls == []


@pytest.mark.parametrize(("provider_id", "other_env"), [("groq", "OPENAI_API_KEY"), ("ollama", "SOME_SERVER_SECRET")])
def test_another_variable_key_never_goes_to_this_provider(
    monkeypatch: pytest.MonkeyPatch, events: list, provider_id: str, other_env: str
) -> None:
    secret = "other-service-secret-not-for-this-provider"
    monkeypatch.setenv(other_env, secret)
    result, transport = _run(provider_id, _sentinel_ir(), events, credential_env_name=other_env)
    assert result.status == "error"
    assert EXE_CRED_0001 in result.diagnostics
    assert events == [] and transport.calls == []
    assert secret not in json.dumps(result.to_dict())


def test_a_key_passed_in_is_not_recorded_as_coming_from_a_variable(events: list) -> None:
    result, transport = _run("groq", _sentinel_ir(), events, credential_value="passed-in-key-not-a-secret")
    assert result.status == "success", result.to_dict()
    assert transport.calls[0].headers["Authorization"] == "Bearer passed-in-key-not-a-secret"
    assert result.envelope["credential_env_name"] is None
    assert result.audit_event is not None and result.audit_event["credential_env_name"] is None
    assert "passed-in-key-not-a-secret" not in json.dumps(result.to_dict(), default=str)


def test_a_key_given_as_the_provider_id_is_never_echoed(events: list) -> None:
    secret = "sk-live-looks-like-a-key"
    result, transport = _run(secret, _sentinel_ir(), events, credential_value=secret)
    assert EXE_PROV_0001 in result.diagnostics
    assert events == [] and transport.calls == []
    assert secret not in json.dumps(result.to_dict())


def test_without_opt_in_nothing_is_sent(events: list) -> None:
    result, transport = _run("groq", _sentinel_ir(), events, opt_in=False)
    assert result.status == "error"
    assert events == [] and transport.calls == []


def test_spend_gate_refusal_means_no_send(
    monkeypatch: pytest.MonkeyPatch, events: list, _keys_and_prices: spend.PriceTable
) -> None:
    unpriced = spend.PriceTable(
        version=_keys_and_prices.version,
        entries=tuple(e for e in _keys_and_prices.entries if e.provider != "deepseek"),
    )
    monkeypatch.setattr(spend, "load_price_table", lambda: unpriced)
    result, transport = _run("deepseek", _sentinel_ir(), events)
    assert result.status == "error"
    assert [kind for kind, _ in events] == ["gate"], "the gate was asked and refused; nothing was sent"
    assert transport.calls == []
    assert result.envelope["admission"]["cost_ceiling"]["decision"] == "refused"
