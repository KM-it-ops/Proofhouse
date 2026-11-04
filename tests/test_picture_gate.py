"""The spend gate lets a judge see a picture: a small PNG or JPEG sent inline, counted at a fixed worst case."""
from __future__ import annotations

import base64
import json
import struct
import zlib
from decimal import Decimal

import pytest

from proofhouse import live, spend


def _png(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    rows = b"".join(b"\x00" + b"\x00" * (3 * width) for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def _jpeg(width: int, height: int) -> bytes:
    sof = b"\xff\xc0" + struct.pack(">HBHHB", 17, 8, height, width, 3) + b"\x01\x11\x00\x02\x11\x00\x03\x11\x00"
    return b"\xff\xd8" + b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + sof + b"\xff\xd9"


def _url(data: bytes, kind: str = "png") -> str:
    return f"data:image/{kind};base64," + base64.b64encode(data).decode("ascii")


def _picture(url: str) -> dict:
    return {"type": "image_url", "image_url": {"url": url}}


@pytest.fixture
def priced(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = spend.PriceEntry(provider="openai", model="model-a", input_usd_per_million_tokens=Decimal("1"),
                             output_usd_per_million_tokens=Decimal("1"), applies_up_to_input_tokens=None,
                             service_tier="default", source_url="https://example.com/pricing", read_on="2026-10-12")
    monkeypatch.setattr(spend, "load_price_table", lambda: spend.PriceTable(version="2026-10-12.9", entries=(entry,)))


def _gate(content: object) -> tuple[spend.Gated, list[bytes]]:
    body = {"model": "model-a", "max_completion_tokens": 8,
            "messages": [{"role": "system", "content": "judge"}, {"role": "user", "content": content}]}
    sent: list[bytes] = []
    return spend.send_within_ceiling(body, provider="openai", model="model-a", max_output_tokens=8, ceiling_usd="1000",
                                     send=sent.append), sent


def test_a_small_picture_with_words_is_sent_and_counted_at_the_fixed_worst_case(priced: None) -> None:
    url = _url(_png(64, 48))
    gated, sent = _gate([{"type": "text", "text": "the plan"}, _picture(url)])
    assert gated.admission.decision == "admitted" and len(sent) == 1
    # the picture's own bytes are not read as text: they are swapped for the fixed bound per picture
    assert gated.admission.input_tokens_bound == len(sent[0]) - len(url) + spend.INPUT_TOKEN_MARGIN + spend.PICTURE_TOKENS_BOUND
    assert "picture" in spend.COUNTING_RULE and str(spend.PICTURE_TOKENS_BOUND) in spend.COUNTING_RULE


def test_two_pictures_count_twice_and_jpeg_counts_like_png(priced: None) -> None:
    one, two = _url(_jpeg(1024, 576), "jpeg"), _url(_png(10, 10))
    gated, sent = _gate([{"type": "text", "text": "x"}, _picture(one), _picture(two)])
    assert gated.admission.decision == "admitted"
    assert gated.admission.input_tokens_bound == (len(sent[0]) - len(one) - len(two) + spend.INPUT_TOKEN_MARGIN
                                                  + 2 * spend.PICTURE_TOKENS_BOUND)


REFUSED = [
    ("a picture larger than 1024 on a side", lambda: [_picture(_url(_png(1025, 10)))]),
    ("a tall jpeg over the limit", lambda: [_picture(_url(_jpeg(500, 2000), "jpeg"))]),
    ("a picture fetched from the web", lambda: [_picture("https://example.com/a.png")]),
    ("a detail setting", lambda: [{"type": "image_url", "image_url": {"url": _url(_png(8, 8)), "detail": "high"}}]),
    ("a picture that is not a png or jpeg", lambda: [_picture("data:image/gif;base64,R0lGODlhAQABAAAAACw=")]),
    ("bytes that do not match the type", lambda: [_picture(_url(_png(8, 8), "jpeg"))]),
    ("broken base64", lambda: [_picture("data:image/png;base64,***")]),
    ("words only in parts", lambda: [{"type": "text", "text": "x"}]),
    ("an audio part", lambda: [_picture(_url(_png(8, 8))), {"type": "input_audio", "input_audio": {"data": "AA", "format": "wav"}}]),
    ("a text part with extra fields", lambda: [{"type": "text", "text": "x", "cache": 1}, _picture(_url(_png(8, 8)))]),
]


@pytest.mark.parametrize("label,content", REFUSED, ids=[label for label, _ in REFUSED])
def test_anything_the_fixed_bound_does_not_cover_is_refused(priced: None, label: str, content) -> None:
    gated, sent = _gate(content())
    assert gated.admission.code == "PHC-COST-0003", label
    assert sent == []


def test_only_the_owners_message_may_carry_a_picture(priced: None) -> None:
    body = {"model": "model-a", "max_completion_tokens": 8,
            "messages": [{"role": "system", "content": [_picture(_url(_png(8, 8)))]}]}
    sent: list[bytes] = []
    gated = spend.send_within_ceiling(body, provider="openai", model="model-a", max_output_tokens=8, ceiling_usd="1000",
                                      send=sent.append)
    assert gated.admission.code == "PHC-COST-0003" and sent == []


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[live.Request] = []

    def __call__(self, request: live.Request) -> live.Response:
        self.calls.append(request)
        return live.Response(200, {"choices": [{"message": {"role": "assistant", "content": "ok"}}],
                                   "usage": {"prompt_tokens": 9, "completion_tokens": 1}})


def test_a_run_can_carry_pictures_with_the_owners_words() -> None:
    url = _url(_png(32, 32))
    rec = _Recorder()
    result = live.run_prompt("ollama", "m", prompt="judge", input_text="the plan", images=[url], transport=rec)
    assert result.status == "success", result.message
    body = json.loads(rec.calls[0].body_bytes)
    assert body["messages"] == [{"role": "system", "content": "judge"},
                                {"role": "user", "content": [{"type": "text", "text": "the plan"}, _picture(url)]}]
    assert result.admission["input_tokens_bound"] >= spend.PICTURE_TOKENS_BOUND


def test_a_run_with_no_input_puts_the_prompt_beside_the_picture() -> None:
    url = _url(_png(8, 8))
    rec = _Recorder()
    assert live.run_prompt("ollama", "m", prompt="what is this", images=[url], transport=rec).status == "success"
    assert json.loads(rec.calls[0].body_bytes)["messages"] == [
        {"role": "user", "content": [{"type": "text", "text": "what is this"}, _picture(url)]}]


def test_a_picture_too_big_to_count_is_refused_before_sending() -> None:
    rec = _Recorder()
    result = live.run_prompt("ollama", "m", prompt="judge", input_text="x", images=[_url(_png(2000, 4))], transport=rec)
    assert result.status != "success" and result.code == "PHC-COST-0003" and not rec.calls
