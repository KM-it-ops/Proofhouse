from __future__ import annotations

import json
import socket

import pytest

from promptrig.compiler import api

from .fixtures.ir_fixtures import ir_with_openai_structured_output, minimal_valid_ir


def _raw() -> bytes:
    return json.dumps(minimal_valid_ir()).encode("utf-8")


@pytest.fixture()
def forbid_network(monkeypatch):
    def _blocked(*args, **kwargs):
        raise AssertionError("network access attempted during an offline compiler operation")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    yield


def test_validate_makes_no_network_access(forbid_network):
    env = api.validate(_raw())
    assert env.status == "success"


def test_inspect_makes_no_network_access(forbid_network):
    env = api.inspect(_raw())
    assert env.status == "success"


def test_compile_with_fake_adapter_makes_no_network_access(forbid_network):
    env = api.compile(_raw(), adapter_id="fake")
    assert env.status == "success"


def test_compile_with_openai_adapter_makes_no_network_access(forbid_network):
    env = api.compile(
        json.dumps(ir_with_openai_structured_output(compliant=True)).encode("utf-8"), adapter_id="openai"
    )
    assert env.status == "success"


def test_list_adapters_makes_no_network_access(forbid_network):
    env = api.list_adapters()
    assert env.status == "success"


def test_doctor_makes_no_network_access(forbid_network):
    env = api.doctor()
    assert env.status == "success"


def _strip_volatile(data: dict) -> dict:
    data = json.loads(json.dumps(data))
    for entry in data.get("pass_trace", []):
        entry.pop("duration_seconds", None)
    return data


def test_compile_is_byte_deterministic_across_many_runs():
    raw = _raw()
    results = [api.compile(raw, adapter_id="fake") for _ in range(5)]
    normalized = [_strip_volatile(r.data) for r in results]
    assert all(n == normalized[0] for n in normalized)
    digests = {r.data["artifacts"][0]["sha256"] for r in results}
    assert len(digests) == 1


def test_validate_is_deterministic_across_many_runs():
    raw = _raw()
    results = [_strip_volatile(api.validate(raw).data) for _ in range(5)]
    assert all(r == results[0] for r in results)


def test_offline_option_is_always_true_by_default():
    from promptrig.compiler.contracts import CompileOptions

    assert CompileOptions().offline is True
