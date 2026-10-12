"""T08 (review F09): live admission rejects invalid ceilings and states how the ceiling is enforced.

On 78e512c ``Infinity`` was accepted as a cost ceiling and ``NaN`` raised
``decimal.InvalidOperation`` out of ``execute_openai``. Since MISSION-041 the
ceiling is enforced before sending by the spend gate; the envelope states the
gate's decision and the worst case it was based on.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from proofhouse.compiler.cli_compiler import main as compiler_main
from proofhouse.compiler.execution import EXE_CEIL_0001, LiveOpenAIRequest, execute_openai

from .fixtures.ir_fixtures import minimal_valid_ir

# The spend gate refuses a model with no price; these tests exercise what happens after it admits.
pytestmark = pytest.mark.usefixtures("priced")


class RecordingTransport:
    def __init__(self) -> None:
        self.calls: list[Any] = []

    def send(self, prepared: Any) -> Any:
        self.calls.append(prepared)
        return type("Resp", (), {"status_code": 200, "payload": {}})()


def _run(**overrides):
    transport = RecordingTransport()
    base = dict(
        opt_in=True,
        model="synthetic-model",
        credential_value="dummy-not-a-secret",
        max_output_tokens=16,
        max_cost_usd="1",
        transport=transport,
    )
    base.update(overrides)
    return execute_openai(json.dumps(minimal_valid_ir()), LiveOpenAIRequest(**base)), transport


@pytest.mark.parametrize(
    "budget",
    ["NaN", "nan", "sNaN", "Infinity", "-Infinity", "inf", "1e999999", "-1", "0", "", "  ", "abc", "1,00"],
)
def test_invalid_cost_ceilings_fail_closed_without_raising(budget: str) -> None:
    result, transport = _run(max_cost_usd=budget)
    assert result.status == "error"
    assert result.diagnostics == (EXE_CEIL_0001,)
    assert transport.calls == []


@pytest.mark.parametrize("tokens", [0, -5, True, "16", 1.5, None])
def test_invalid_output_token_ceilings_fail_closed(tokens) -> None:
    result, transport = _run(max_output_tokens=tokens)
    assert result.status == "error"
    assert result.diagnostics == (EXE_CEIL_0001,)
    assert transport.calls == []


def test_success_envelope_discloses_the_gate_decision(priced) -> None:
    result, transport = _run()
    assert result.status == "success"
    admission = result.envelope["admission"]
    gate = admission["cost_ceiling"]
    assert gate["declared_usd"] == "1"
    assert gate["enforcement"] == "refused_pre_send_when_worst_case_over_ceiling"
    assert gate["decision"] == "admitted"
    assert gate["ceiling_usd"] == "1"
    assert gate["price"]["source_url"] == "https://example.com/test-prices"
    assert gate["price_table_version"] == priced.version
    assert gate["input_tokens_bound"] > 0 and gate["output_tokens_bound"] == 16
    assert "pricing_source" not in gate and "input_token_estimate" not in gate
    assert admission["output_token_ceiling"]["enforcement"] == "sent_as_max_completion_tokens"
    assert len(transport.calls) == 1


def test_transport_exception_is_normalized_without_secret_leak() -> None:
    class Exploding:
        def send(self, prepared: Any) -> Any:
            raise RuntimeError(f"boom {prepared.headers['Authorization']}")

    result, _ = _run(transport=Exploding(), credential_value="sk-leak-check-XYZ")
    assert result.status == "error"
    assert "sk-leak-check-XYZ" not in json.dumps(result.to_dict())


def test_cli_nan_budget_is_a_clean_rejection(tmp_path, capsys, monkeypatch) -> None:
    ir = tmp_path / "ir.json"
    ir.write_text(json.dumps(minimal_valid_ir()), encoding="utf-8")
    monkeypatch.setenv("T08_DUMMY_CRED", "dummy")
    code = compiler_main(
        [
            "execute-openai",
            str(ir),
            "--opt-in",
            "--model",
            "synthetic",
            "--credential-env",
            "T08_DUMMY_CRED",
            "--max-output-tokens",
            "8",
            "--max-cost-usd",
            "NaN",
            "--json",
        ]
    )
    captured = capsys.readouterr()
    assert code != 0
    assert "internal error" not in captured.err
    payload = json.loads(captured.out)
    assert EXE_CEIL_0001 in json.dumps(payload)
