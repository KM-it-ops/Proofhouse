"""T-041-05: what a sent call cost, and whether the worst-case bound held.

Token counts the provider reports are measured. The dollar figure worked out
from them at table prices is estimated, never measured: the table can be stale
and Proofhouse never sees the bill. A figure nobody knows is ``unknown``, never
``0``. If the provider reports more tokens than the bound the gate used, the
result says so (PHC-COST-0004) and still returns the output.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from proofhouse import spend
from proofhouse.compiler import execution
from proofhouse.compiler.cli_compiler import main as compiler_main
from proofhouse.compiler.execution import LiveOpenAIRequest, execute_openai

from .fixtures.ir_fixtures import minimal_valid_ir

FIELDS = ("tokens_in", "tokens_out", "usd", "wall_seconds", "compute_seconds")


class Transport:
    def __init__(self, status: int, payload: dict) -> None:
        self.status, self.payload, self.calls = status, payload, []

    def send(self, prepared: Any) -> Any:
        self.calls.append(prepared)
        return type("Resp", (), {"status_code": self.status, "payload": self.payload})()


@pytest.fixture(autouse=True)
def _prices(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = spend.PriceEntry(
        "openai", "model-a", Decimal("1.25"), Decimal("10"), None, "default", "https://example.com/p", "2026-10-12"
    )
    monkeypatch.setattr(spend, "load_price_table", lambda: spend.PriceTable("2026-10-12.9", (entry,)))


def _run(payload: dict, status: int = 200, max_output_tokens: int = 300):
    transport = Transport(status, payload)
    request = LiveOpenAIRequest(
        opt_in=True, model="model-a", credential_value="dummy", max_output_tokens=max_output_tokens,
        max_cost_usd="1", transport=transport,
    )
    result = execute_openai(json.dumps(minimal_valid_ir()), request)
    assert len(transport.calls) == 1
    return result


def test_reported_tokens_are_measured_and_dollars_are_estimated_exactly() -> None:
    result = _run({"usage": {"prompt_tokens": 812, "completion_tokens": 240, "total_tokens": 1052}})
    assert result.status == "success" and result.diagnostics == ()
    cost = result.envelope["cost"]
    assert set(cost) == {*FIELDS, "basis", "price_table_version"}
    assert cost["tokens_in"] == 812 and cost["tokens_out"] == 240
    assert cost["usd"] == "0.003415"  # (812 x 1.25 + 240 x 10) / 1,000,000
    assert Decimal(cost["wall_seconds"]) >= 0
    assert cost["compute_seconds"] == "unknown"
    assert cost["basis"] == {
        "tokens_in": "measured", "tokens_out": "measured", "usd": "estimated",
        "wall_seconds": "measured", "compute_seconds": "unknown",
    }
    assert cost["price_table_version"] == "2026-10-12.9"


@pytest.mark.parametrize(
    "payload,status",
    [
        ({}, 200),
        ({"usage": None}, 200),
        ({"usage": "812"}, 200),
        ({"usage": {"prompt_tokens": -1, "completion_tokens": 5}}, 200),
        ({"usage": {"prompt_tokens": True, "completion_tokens": 5}}, 200),
        ({"usage": {"prompt_tokens": 5.0, "completion_tokens": 5}}, 200),
        ({"usage": {"prompt_tokens": "5", "completion_tokens": 5}}, 200),
        ({"error": {"message": "server error"}}, 500),
    ],
    ids=["no-usage", "null", "string", "negative", "bool", "float", "numeric-string", "http-error"],
)
def test_unusable_usage_leaves_figures_unknown_never_zero(payload: dict, status: int) -> None:
    cost = _run(payload, status).envelope["cost"]
    assert cost["tokens_in"] == "unknown" and cost["basis"]["tokens_in"] == "unknown"
    assert cost["usd"] == "unknown" and cost["basis"]["usd"] == "unknown"
    assert cost["price_table_version"] == ""
    assert 0 not in [cost[field] for field in FIELDS]


def test_one_good_count_is_kept_but_dollars_need_both() -> None:
    cost = _run({"usage": {"prompt_tokens": 100, "completion_tokens": None}}).envelope["cost"]
    assert cost["tokens_in"] == 100 and cost["basis"]["tokens_in"] == "measured"
    assert cost["tokens_out"] == "unknown" and cost["usd"] == "unknown"


def test_dollars_are_never_labelled_measured() -> None:
    for payload in ({"usage": {"prompt_tokens": 1, "completion_tokens": 1}}, {}):
        assert _run(payload).envelope["cost"]["basis"]["usd"] != "measured"


def test_output_over_the_bound_is_reported_and_the_output_still_returned() -> None:
    result = _run({"usage": {"prompt_tokens": 10, "completion_tokens": 301}, "choices": [{"message": {"content": "hi"}}]})
    assert result.status == "success"
    assert result.diagnostics == ("PHC-COST-0004",)
    assert result.envelope["cost_warning"] == (
        "PHC-COST-0004: 'model-a' used 301 output tokens, over the bound of 300; "
        "the price check did not hold for this call"
    )
    assert result.envelope["provider_response"]["choices"][0]["message"]["content"] == "hi"


def test_input_over_the_bound_is_reported() -> None:
    probe = _run({})
    bound = probe.envelope["admission"]["cost_ceiling"]["input_tokens_bound"]
    result = _run({"usage": {"prompt_tokens": bound + 1, "completion_tokens": 1}})
    assert result.diagnostics == ("PHC-COST-0004",)
    assert f"used {bound + 1} input tokens, over the bound of {bound}" in result.envelope["cost_warning"]


def test_within_the_bound_there_is_no_warning() -> None:
    result = _run({"usage": {"prompt_tokens": 10, "completion_tokens": 300}})
    assert result.diagnostics == () and "cost_warning" not in result.envelope


def test_cli_prints_the_warning_on_stderr_and_exits_0(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("T041_DUMMY_CRED", "dummy")
    monkeypatch.setattr(
        execution, "_httpx_send",
        lambda prepared: execution.LiveTransportResponse(200, {"usage": {"prompt_tokens": 1, "completion_tokens": 9}}),
    )
    ir = tmp_path / "ir.json"
    ir.write_text(json.dumps(minimal_valid_ir()), encoding="utf-8")
    argv = ["execute-openai", str(ir), "--opt-in", "--model", "model-a", "--credential-env", "T041_DUMMY_CRED",
            "--max-output-tokens", "8", "--max-cost-usd", "1"]
    for extra in ([], ["--json"]):
        code = compiler_main([*argv, *extra])
        captured = capsys.readouterr()
        assert code == 0
        assert captured.err == (
            "PHC-COST-0004: 'model-a' used 9 output tokens, over the bound of 8; the price check did not hold for this call\n"
        )
