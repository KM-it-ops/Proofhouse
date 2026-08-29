"""MISSION-032 fail-closed live OpenAI execution (default suite, no real HTTP)."""

from __future__ import annotations

import json
import socket
from typing import Any

import pytest

from promptrig.compiler import api
from promptrig.compiler.cli_compiler import build_parser, main as compiler_main
from promptrig.compiler.closed_loop import ClosedLoopOptions, run_closed_loop
from promptrig.compiler.execution import LiveOpenAIRequest, execute_openai

from .fixtures.ir_fixtures import ir_with_openai_structured_output, minimal_valid_ir

SECRET = "sk-test-secret-do-not-leak-MISSION032"
CALLER_MODEL = "caller-supplied-unratified-model"


class RecordingTransport:
    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self.calls: list[Any] = []
        self.payload = payload or {
            "id": "chatcmpl-test-double",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
        }

    def send(self, prepared: Any) -> Any:
        self.calls.append(prepared)
        return type("Resp", (), {"status_code": 200, "payload": self.payload})()


@pytest.fixture()
def forbid_network(monkeypatch: pytest.MonkeyPatch):
    def _blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access attempted during an offline or fail-closed path")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    yield


def _raw() -> bytes:
    return json.dumps(ir_with_openai_structured_output(compliant=True)).encode("utf-8")


def _blob(value: object) -> str:
    return json.dumps(value, default=str)


def test_ae4_no_credentials_fail_closed(forbid_network: None) -> None:
    result = execute_openai(
        _raw(),
        LiveOpenAIRequest(
            opt_in=True,
            model=CALLER_MODEL,
            max_output_tokens=16,
            max_cost_usd="0.01",
            transport=RecordingTransport(),
        ),
    )
    assert result.status == "error"
    assert "EXE-CRED-0001" in result.diagnostics
    assert SECRET not in _blob(result.to_dict())


def test_missing_model_fail_closed(forbid_network: None) -> None:
    result = execute_openai(
        _raw(),
        LiveOpenAIRequest(
            opt_in=True,
            credential_value=SECRET,
            max_output_tokens=16,
            max_cost_usd="0.01",
            transport=RecordingTransport(),
        ),
    )
    assert result.status == "error"
    assert "EXE-MODEL-0001" in result.diagnostics
    assert SECRET not in _blob(result.to_dict())


def test_missing_ceilings_fail_closed(forbid_network: None) -> None:
    result = execute_openai(
        _raw(),
        LiveOpenAIRequest(
            opt_in=True,
            model=CALLER_MODEL,
            credential_value=SECRET,
            transport=RecordingTransport(),
        ),
    )
    assert result.status == "error"
    assert "EXE-CEIL-0001" in result.diagnostics
    assert SECRET not in _blob(result.to_dict())


def test_execute_without_opt_in_opens_no_sockets(forbid_network: None) -> None:
    result = execute_openai(
        _raw(),
        LiveOpenAIRequest(
            model=CALLER_MODEL,
            credential_value=SECRET,
            max_output_tokens=16,
            max_cost_usd="0.01",
            transport=RecordingTransport(),
        ),
    )
    assert result.status == "error"
    assert "EXE-OPT-0001" in result.diagnostics
    assert SECRET not in _blob(result.to_dict())


def test_execute_without_creds_opens_no_sockets(forbid_network: None) -> None:
    result = execute_openai(
        _raw(),
        LiveOpenAIRequest(
            opt_in=True,
            model=CALLER_MODEL,
            max_output_tokens=16,
            max_cost_usd="0.01",
        ),
    )
    assert result.status == "error"
    assert "EXE-CRED-0001" in result.diagnostics


def test_closed_loop_network_allowed_still_evr_net_0001() -> None:
    result = run_closed_loop(minimal_valid_ir(), ClosedLoopOptions(network_allowed=True))
    assert result.status == "BLOCKED"
    assert "EVR-NET-0001" in result.diagnostics


def test_compile_openai_adapter_still_offline(forbid_network: None) -> None:
    env = api.compile(_raw(), adapter_id="openai", adapter_version="0.1.0")
    assert env.status == "success"
    assert env.command == "compile"


def test_happy_path_opt_in_test_double_audit_and_stable_compile(forbid_network: None) -> None:
    transport = RecordingTransport()
    before = api.compile(_raw(), adapter_id="openai", adapter_version="0.1.0")
    assert before.status == "success"
    digest_before = before.data["artifacts"][0]["sha256"]

    result = execute_openai(
        _raw(),
        LiveOpenAIRequest(
            opt_in=True,
            model=CALLER_MODEL,
            credential_value=SECRET,
            max_output_tokens=32,
            max_cost_usd="0.02",
            transport=transport,
        ),
    )
    assert result.status == "success"
    assert result.audit_event is not None
    assert result.audit_event.get("event") == "live_openai_execute"
    assert result.envelope.get("single_request") is True
    assert "continuation" not in result.envelope
    assert len(transport.calls) == 1
    assert SECRET not in _blob(result.to_dict())
    assert SECRET not in _blob(result.audit_event)
    assert SECRET not in _blob(result.envelope)
    assert SECRET not in _blob(result.diagnostics)

    after = api.compile(_raw(), adapter_id="openai", adapter_version="0.1.0")
    assert after.status == "success"
    assert after.data["artifacts"][0]["sha256"] == digest_before
    assert after.data["artifacts"] == before.data["artifacts"]


def test_credential_redaction_in_envelope_and_diagnostics(forbid_network: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROMPTRIG_TEST_OPENAI_KEY", SECRET)
    result = execute_openai(
        _raw(),
        LiveOpenAIRequest(
            opt_in=True,
            model=CALLER_MODEL,
            credential_env_name="PROMPTRIG_TEST_OPENAI_KEY",
            max_output_tokens=8,
            max_cost_usd="0.01",
            transport=RecordingTransport(),
        ),
    )
    dumped = _blob(result.to_dict())
    assert SECRET not in dumped
    assert "sk-test-secret" not in dumped
    assert result.status == "success"


def test_empty_credential_env_fail_closed(forbid_network: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROMPTRIG_TEST_OPENAI_KEY", "")
    result = execute_openai(
        _raw(),
        LiveOpenAIRequest(
            opt_in=True,
            model=CALLER_MODEL,
            credential_env_name="PROMPTRIG_TEST_OPENAI_KEY",
            max_output_tokens=8,
            max_cost_usd="0.01",
            transport=RecordingTransport(),
        ),
    )
    assert result.status == "error"
    assert "EXE-CRED-0001" in result.diagnostics


def test_egress_non_openai_host_fail_closed(forbid_network: None) -> None:
    result = execute_openai(
        _raw(),
        LiveOpenAIRequest(
            opt_in=True,
            model=CALLER_MODEL,
            credential_value=SECRET,
            max_output_tokens=8,
            max_cost_usd="0.01",
            target_url="https://evil.example/v1/chat/completions",
            transport=RecordingTransport(),
        ),
    )
    assert result.status == "error"
    assert "EXE-EGRESS-0001" in result.diagnostics
    assert SECRET not in _blob(result.to_dict())


def test_missing_httpx_extra_fail_closed_without_transport(forbid_network: None) -> None:
    result = execute_openai(
        _raw(),
        LiveOpenAIRequest(
            opt_in=True,
            model=CALLER_MODEL,
            credential_value=SECRET,
            max_output_tokens=8,
            max_cost_usd="0.01",
        ),
    )
    assert result.status == "error"
    assert "EXE-DEP-0001" in result.diagnostics
    assert SECRET not in _blob(result.to_dict())


def test_cancellation_preserves_evidence_without_call(forbid_network: None) -> None:
    transport = RecordingTransport()
    result = execute_openai(
        _raw(),
        LiveOpenAIRequest(
            opt_in=True,
            model=CALLER_MODEL,
            credential_value=SECRET,
            max_output_tokens=8,
            max_cost_usd="0.01",
            transport=transport,
            cancelled=True,
        ),
    )
    assert result.status == "cancelled"
    assert result.envelope.get("evidence")
    assert transport.calls == []
    assert SECRET not in _blob(result.to_dict())


def test_success_does_not_retry(forbid_network: None) -> None:
    transport = RecordingTransport()
    result = execute_openai(
        _raw(),
        LiveOpenAIRequest(
            opt_in=True,
            model=CALLER_MODEL,
            credential_value=SECRET,
            max_output_tokens=8,
            max_cost_usd="0.01",
            transport=transport,
        ),
    )
    assert result.status == "success"
    assert len(transport.calls) == 1
    prepared = transport.calls[0]
    key = getattr(prepared, "idempotency_key", None) or prepared.get("idempotency_key")
    assert key


def test_lazy_api_export_matches_module() -> None:
    assert callable(api.execute_openai)
    assert api.execute_openai is execute_openai


def test_cli_execute_openai_without_opt_in_fail_closed(tmp_path: Any, capsys: pytest.CaptureFixture[str], forbid_network: None) -> None:
    path = tmp_path / "ir.json"
    path.write_bytes(_raw())
    code = compiler_main(
        [
            "execute-openai",
            str(path),
            "--model",
            CALLER_MODEL,
            "--credential-env",
            "PROMPTRIG_TEST_OPENAI_KEY",
            "--max-output-tokens",
            "8",
            "--max-cost-usd",
            "0.01",
            "--json",
        ]
    )
    assert code != 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
    assert "EXE-OPT-0001" in out["diagnostics"]
    assert SECRET not in json.dumps(out)


def test_closed_loop_cli_has_no_live_execute_flags() -> None:
    parser = build_parser()
    import argparse

    subparsers = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    assert "execute-openai" in subparsers.choices
    loop_parser = subparsers.choices["closed-loop"]
    dests = {a.dest for a in loop_parser._actions}
    assert "opt_in" not in dests
    assert "credential_env" not in dests
    assert "model" not in dests


def test_no_ratified_production_model_id_in_execution_module() -> None:
    from pathlib import Path

    source = Path("src/promptrig/compiler/execution.py").read_text(encoding="utf-8").lower()
    for banned in ("gpt-4o", "gpt-4.1", "gpt-5", "o1-preview", "o3-mini"):
        assert banned not in source
    assert "q1" in source
    assert "caller-supplied" in source or "call time" in source or "invoke time" in source
