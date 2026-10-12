"""T-041-02: the worst-case estimate.

Input tokens are bounded by the UTF-8 bytes of the request body exactly as sent
plus a fixed margin; output tokens by the output-token ceiling the call already
requires. Money is exact ``Decimal``: an amount that would need rounding is
refused (PHC-COST-0003), never rounded, and ``spend.py`` holds no float.
"""
from __future__ import annotations

import ast
import json
from decimal import Decimal
from pathlib import Path

import pytest

from proofhouse import spend

ROOT = Path(__file__).resolve().parents[1]


def _entry(input_price: str, output_price: str) -> spend.PriceEntry:
    return spend.PriceEntry(
        provider="openai",
        model="model-a",
        input_usd_per_million_tokens=Decimal(input_price),
        output_usd_per_million_tokens=Decimal(output_price),
        applies_up_to_input_tokens=None,
        service_tier="default",
        source_url="https://example.com/pricing",
        read_on="2026-10-12",
    )


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for k, v in value.items() for s in (*_strings(k), *_strings(v))]
    if isinstance(value, list):
        return [s for item in value for s in _strings(item)]
    return []


BODIES = [
    {"model": "m", "messages": [{"role": "system", "content": "plain ascii"}], "max_completion_tokens": 8},
    {"model": "m", "messages": [{"role": "system", "content": "é ü ß – € 中文 日本語 🙂🙂"}], "max_completion_tokens": 8},
    {"model": "m", "messages": [{"role": "system", "content": 'line\nbreak\ttab "quote" \\ back \u0001 ctl'}], "max_completion_tokens": 8},
    {
        "model": "m",
        "messages": [{"role": "system", "content": "x"}],
        "max_completion_tokens": 8,
        "tools": [{"type": "function", "function": {"name": "f", "description": "emoji 🧪 in a tool", "parameters": {"type": "object"}}}],
        "response_format": {"type": "json_schema", "json_schema": {"name": "out", "schema": {"type": "object", "description": "ünïcode"}}},
    },
]


@pytest.mark.parametrize("body", BODIES)
def test_the_input_bound_covers_every_byte_of_text_the_provider_reads(body: dict) -> None:
    sent = spend.request_body_bytes(body)
    assert json.loads(sent) == body  # the bytes are the body, unchanged
    text_bytes = sum(len(s.encode("utf-8")) for s in _strings(body))
    bound = spend.input_tokens_bound(sent)
    assert bound >= text_bytes + spend.INPUT_TOKEN_MARGIN
    assert bound == len(sent) + spend.INPUT_TOKEN_MARGIN == len(sent) + 1024


def test_the_counting_rule_is_stated_in_one_line_with_its_assumption() -> None:
    assert "\n" not in spend.COUNTING_RULE
    assert "UTF-8 bytes" in spend.COUNTING_RULE and "1024" in spend.COUNTING_RULE
    assert "one token per byte" in spend.COUNTING_RULE


@pytest.mark.parametrize(
    "body",
    [{"content": "lone \ud800 surrogate"}, {"n": float("nan")}, {"n": float("inf")}],
    ids=["lone-surrogate", "nan", "infinity"],
)
def test_a_body_that_cannot_be_sent_as_exact_bytes_is_refused(body: dict) -> None:
    with pytest.raises(spend.SpendRefused) as caught:
        spend.request_body_bytes(body)
    assert caught.value.code == "PHC-COST-0003"


@pytest.mark.parametrize(
    "prices,tokens_in,tokens_out,expected",
    [
        (("0.15", "0.6"), 1000, 500, "0.00045"),  # 0.00015 + 0.0003
        (("1.25", "10"), 2048, 4096, "0.04352"),  # 0.00256 + 0.04096
        (("3", "15"), 0, 1, "0.000015"),
        (("0.000001", "0.000001"), 1, 1, "2E-12"),
    ],
)
def test_the_worst_case_is_exact(prices: tuple[str, str], tokens_in: int, tokens_out: int, expected: str) -> None:
    amount = spend.worst_case_usd(_entry(*prices), tokens_in, tokens_out)
    assert type(amount) is Decimal
    assert amount == Decimal(expected)


@pytest.mark.parametrize(
    "prices,tokens_in,tokens_out",
    [
        (("0." + "1" * 70, "1"), 3, 1),  # more digits than the context holds: would round
        (("0.6", "0.6"), 1, 10**80),  # an absurd output ceiling
    ],
    ids=["too-many-digits", "absurd-output-ceiling"],
)
def test_an_amount_that_would_need_rounding_is_refused(prices: tuple[str, str], tokens_in: int, tokens_out: int) -> None:
    with pytest.raises(spend.SpendRefused) as caught:
        spend.worst_case_usd(_entry(*prices), tokens_in, tokens_out)
    assert caught.value.code == "PHC-COST-0003"


@pytest.mark.parametrize("tokens", [-1, True, 1.5, "8", None])
def test_token_counts_must_be_non_negative_integers(tokens) -> None:
    for args in ((tokens, 1), (1, tokens)):
        with pytest.raises(spend.SpendRefused) as caught:
            spend.worst_case_usd(_entry("1", "1"), *args)
        assert caught.value.code == "PHC-COST-0003"


def test_a_refusal_carries_a_registered_code_and_a_one_line_message() -> None:
    from proofhouse.optimize.case_codes import CODES

    refusal = spend.SpendRefused("PHC-COST-0003", "x")
    assert str(refusal) == "PHC-COST-0003: x"
    assert "PHC-COST-0003" in CODES
    with pytest.raises(ValueError):
        spend.SpendRefused("PHC-COST-9999", "unregistered")


def test_spend_holds_no_float() -> None:
    tree = ast.parse((ROOT / "src" / "proofhouse" / "spend.py").read_text(encoding="utf-8"))
    floats = [
        node.lineno
        for node in ast.walk(tree)
        if (isinstance(node, ast.Constant) and type(node.value) is float)
        or (isinstance(node, ast.Name) and node.id == "float")
    ]
    assert floats == [], f"float in spend.py at lines {floats}"
