"""T-041-03: execute-openai sends only through the spend gate.

The gate works out the worst case from the exact bytes that will be sent and
refuses, sending nothing, when that is over the ceiling (PHC-COST-0001), when
the model has no price (PHC-COST-0002), or when no worst case can be made
(PHC-COST-0003). Every earlier check still runs first. No environment variable
changes the outcome.
"""
from __future__ import annotations

import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from proofhouse import spend
from proofhouse.compiler import execution
from proofhouse.compiler.cli_compiler import main as compiler_main
from proofhouse.compiler.execution import LiveOpenAIRequest, execute_openai

from .fixtures.ir_fixtures import minimal_valid_ir


class RecordingTransport:
    def __init__(self) -> None:
        self.calls: list[Any] = []

    def send(self, prepared: Any) -> Any:
        self.calls.append(prepared)
        return type("Resp", (), {"status_code": 200, "payload": {}})()


def _price(model: str, input_price: str, output_price: str) -> spend.PriceEntry:
    return spend.PriceEntry(
        provider="openai",
        model=model,
        input_usd_per_million_tokens=Decimal(input_price),
        output_usd_per_million_tokens=Decimal(output_price),
        applies_up_to_input_tokens=None,
        service_tier="default",
        source_url="https://example.com/pricing",
        read_on="2026-10-12",
    )


@pytest.fixture
def prices(monkeypatch: pytest.MonkeyPatch):
    """Replace the shipped table for one test; records how often the gate read it."""
    reads: list[int] = []

    def install(*entries: spend.PriceEntry) -> list[int]:
        table = spend.PriceTable(version="2026-10-12.9", entries=tuple(entries))

        def load() -> spend.PriceTable:
            reads.append(1)
            return table

        monkeypatch.setattr(spend, "load_price_table", load)
        return reads

    return install


def _run(**overrides):
    transport = overrides.pop("transport", None) or RecordingTransport()
    base = dict(
        opt_in=True,
        model="model-a",
        credential_value="dummy-not-a-secret",
        max_output_tokens=64,
        max_cost_usd="1",
        transport=transport,
    )
    base.update(overrides)
    return execute_openai(json.dumps(minimal_valid_ir()), LiveOpenAIRequest(**base)), transport


def _gate(result) -> dict:
    return result.envelope["admission"]["cost_ceiling"]


def test_a_worst_case_over_the_ceiling_is_refused_and_nothing_is_sent(prices) -> None:
    prices(_price("model-a", "1000", "1000"))
    result, transport = _run(max_cost_usd="0.01")
    assert transport.calls == []
    assert result.status == "error"
    assert result.diagnostics == ("PHC-COST-0001",)
    gate = _gate(result)
    assert gate["decision"] == "refused"
    assert gate["code"] == "PHC-COST-0001"
    assert Decimal(gate["worst_case_usd"]) > Decimal(gate["ceiling_usd"]) == Decimal("0.01")
    assert gate["message"] == (
        f"PHC-COST-0001: worst case ${gate['worst_case_usd']} is over the ceiling $0.01 for 'model-a' "
        "(prices 2026-10-12.9, read 2026-10-12); nothing was sent"
    )
    assert gate["enforcement"] == spend.ENFORCEMENT == "refused_pre_send_when_worst_case_over_ceiling"
    assert gate["counting_rule"] == spend.COUNTING_RULE


def test_a_model_with_no_price_is_refused_with_the_shipped_table() -> None:
    for model in ("gpt-5.6-luna", "model-a"):
        result, transport = _run(model=model)
        assert transport.calls == []
        assert result.diagnostics == ("PHC-COST-0002",)
        assert _gate(result)["message"] == (
            f"PHC-COST-0002: no price for {model!r} in price table {spend.load_price_table().version}; nothing was sent"
        )


def test_a_broken_table_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    broken = tmp_path / "price_table.json"
    broken.write_text('{"schema": "proofhouse.price_table/v1"}', encoding="utf-8")
    monkeypatch.setattr(spend, "PRICE_TABLE_PATH", broken)
    result, transport = _run()
    assert transport.calls == []
    assert result.diagnostics == ("PHC-COST-0003",)
    assert _gate(result)["message"].startswith("PHC-COST-0003: no worst-case cost could be made (price table ")
    assert _gate(result)["message"].endswith("); nothing was sent")


def test_an_input_bound_above_the_priced_range_is_refused(prices) -> None:
    entry = _price("model-a", "1", "1")
    prices(spend.PriceEntry(**{**{f: getattr(entry, f) for f in entry.__slots__}, "applies_up_to_input_tokens": 1100}))
    result, transport = _run()
    assert transport.calls == []
    assert result.diagnostics == ("PHC-COST-0003",)
    assert "above the 1100 input tokens its price applies to" in _gate(result)["message"]


def test_a_worst_case_equal_to_the_ceiling_is_sent_and_one_below_is_not(prices) -> None:
    prices(_price("model-a", "3", "15"))
    probe, _ = _run(max_cost_usd="1000")
    worst = Decimal(_gate(probe)["worst_case_usd"])
    at, sent = _run(max_cost_usd=str(worst))
    assert _gate(at)["decision"] == "admitted" and len(sent.calls) == 1
    below, unsent = _run(max_cost_usd=str(worst - Decimal("0.000000000001")))
    assert below.diagnostics == ("PHC-COST-0001",) and unsent.calls == []


def test_the_bytes_sent_are_the_bytes_counted(prices) -> None:
    prices(_price("model-a", "1", "1"))
    result, transport = _run()
    assert result.status == "success"
    (prepared,) = transport.calls
    gate = _gate(result)
    assert gate["decision"] == "admitted" and gate["code"] is None and gate["message"] is None
    assert gate["input_tokens_bound"] == len(prepared.body_bytes) + spend.INPUT_TOKEN_MARGIN
    assert gate["output_tokens_bound"] == 64
    assert gate["body_sha256"] == hashlib.sha256(prepared.body_bytes).hexdigest()
    assert json.loads(prepared.body_bytes) == prepared.body
    assert gate["price"]["model"] == "model-a" and gate["price_table_version"] == "2026-10-12.9"


def test_httpx_posts_the_counted_bytes_not_its_own_serialisation(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    class Client:
        def __init__(self, **_: Any) -> None: ...
        def __enter__(self): return self
        def __exit__(self, *_: Any) -> None: ...

        def post(self, url: str, **kwargs: Any):
            seen.update(kwargs, url=url)
            return type("R", (), {"status_code": 200, "json": lambda self: {}, "text": ""})()

    monkeypatch.setitem(sys.modules, "httpx", type(sys)("httpx"))
    sys.modules["httpx"].Client = Client
    prepared = execution.PreparedLiveRequest(
        url="https://api.openai.com/v1/chat/completions", method="POST", headers={"H": "v"},
        body={"a": "é"}, idempotency_key="k", body_bytes=b'{"a":"\xc3\xa9"}',
    )
    execution._httpx_send(prepared)
    assert seen["content"] == prepared.body_bytes
    assert "json" not in seen


EARLIER = [
    ({"opt_in": False}, "EXE-OPT-0001"),
    ({"credential_value": None}, "EXE-CRED-0001"),
    ({"model": "  "}, "EXE-MODEL-0001"),
    ({"max_cost_usd": "NaN"}, "EXE-CEIL-0001"),
    ({"max_output_tokens": 0}, "EXE-CEIL-0001"),
    ({"target_url": "https://evil.example/v1/chat/completions"}, "EXE-EGRESS-0001"),
]


@pytest.mark.parametrize("overrides,code", EARLIER, ids=[code for _, code in EARLIER])
def test_every_earlier_check_still_runs_first(prices, overrides: dict, code: str) -> None:
    reads = prices(_price("model-a", "1000", "1000"))
    result, transport = _run(max_cost_usd="0.01", **overrides) if "max_cost_usd" not in overrides else _run(**overrides)
    assert result.diagnostics == (code,)
    assert transport.calls == [] and reads == []


def test_a_cancelled_request_never_reaches_the_gate(prices) -> None:
    reads = prices(_price("model-a", "1", "1"))
    result, transport = _run(cancelled=True)
    assert result.status == "cancelled" and transport.calls == [] and reads == []


def test_no_environment_variable_switches_the_gate_off(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in {
        "PROOFHOUSE_EXPERIMENTAL": "1",
        "PROOFHOUSE_LIVE": "1",
        "PROOFHOUSE_SKIP_COST_CHECK": "1",
        "PROOFHOUSE_PRICE_TABLE": "/nonexistent/prices.json",
        "PROOFHOUSE_HOME": "/tmp/elsewhere",
    }.items():
        monkeypatch.setenv(name, value)
    result, transport = _run(model="gpt-5.6-luna")
    assert result.diagnostics == ("PHC-COST-0002",)
    assert transport.calls == []


def test_a_refusal_leaks_no_secret(prices) -> None:
    prices(_price("model-a", "1000", "1000"))
    result, transport = _run(max_cost_usd="0.01", credential_value="sk-leak-check-XYZ")
    assert transport.calls == []
    assert "sk-leak-check-XYZ" not in json.dumps(result.to_dict())


def _cli(tmp_path: Path, capsys, *extra: str) -> tuple[int, str, str]:
    ir = tmp_path / "ir.json"
    ir.write_text(json.dumps(minimal_valid_ir()), encoding="utf-8")
    code = compiler_main(
        ["execute-openai", str(ir), "--opt-in", "--model", "gpt-5.6-luna", "--credential-env", "T041_DUMMY_CRED",
         "--max-output-tokens", "8", "--max-cost-usd", "0.5", *extra]
    )
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_cli_refusal_is_one_line_and_exits_7(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("T041_DUMMY_CRED", "dummy")
    code, out, err = _cli(tmp_path, capsys)
    assert code == 7
    version = spend.load_price_table().version
    assert out == f"PHC-COST-0002: no price for 'gpt-5.6-luna' in price table {version}; nothing was sent\n"
    assert "internal error" not in err
    code, out, _ = _cli(tmp_path, capsys, "--json")
    assert code == 7
    payload = json.loads(out)
    assert payload["diagnostics"] == ["PHC-COST-0002"]
    assert payload["envelope"]["admission"]["cost_ceiling"]["decision"] == "refused"
