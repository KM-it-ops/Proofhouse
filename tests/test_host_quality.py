"""Host-mode quality checks: text, launch overlap, site readability."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofhouse import cli
from proofhouse.host import collect_checks
from proofhouse.host_quality import (
    jaccard_shingle_overlap,
    parts_differ_rows,
    site_readability_rows,
    text_quality_rows,
    word_count,
)
from proofhouse.host_launch import collect_launch_checks


def _copy_words(n: int) -> str:
    return " ".join(f"item{i}" for i in range(1, n + 1)) + " Price is $9.99."


def test_length_fails_below_threshold() -> None:
    short = " ".join(f"item{i}" for i in range(1, 11))
    row = next(r for r in text_quality_rows(short, "copy") if r["check"] == "length")
    assert row["ok"] is False
    assert "10 words" in row["detail"]


def test_length_passes_at_threshold() -> None:
    text = _copy_words(25)
    row = next(r for r in text_quality_rows(text, "copy") if r["check"] == "length")
    assert row["ok"] is True


def test_prompt_needs_forty_words() -> None:
    text = " ".join(f"w{i}" for i in range(39))
    row = next(r for r in text_quality_rows(text, "prompt") if r["check"] == "length")
    assert row["ok"] is False


def test_filler_one_phrase_warns() -> None:
    text = _copy_words(25) + " We offer seamless checkout."
    row = next(r for r in text_quality_rows(text, "copy") if r["check"] == "filler")
    assert row["ok"] is True
    assert "seamless" in row["detail"]


def test_filler_two_phrases_fail() -> None:
    text = _copy_words(25) + " A seamless, game-changing experience."
    row = next(r for r in text_quality_rows(text, "copy") if r["check"] == "filler")
    assert row["ok"] is False
    assert "seamless" in row["detail"] and "game-changing" in row["detail"]


def test_specifics_requires_concrete_detail() -> None:
    vague = " ".join(["lorem"] * 30)
    row = next(r for r in text_quality_rows(vague, "copy") if r["check"] == "specifics")
    assert row["ok"] is False
    concrete = vague + " Meet Alex at noon."
    row2 = next(r for r in text_quality_rows(concrete, "copy") if r["check"] == "specifics")
    assert row2["ok"] is True


def test_parts_differ_flags_high_overlap() -> None:
    left = " ".join(f"shared phrase chunk {i}" for i in range(20))
    right = left
    rows = parts_differ_rows({"a": left, "b": right})
    assert rows[0]["check"] == "parts differ"
    assert rows[0]["ok"] is False
    assert "a/b" in rows[0]["detail"]


def test_parts_differ_skips_short_parts() -> None:
    rows = parts_differ_rows({"a": "one two three four", "b": "one two three four five"})
    assert rows == [{"check": "parts differ", "ok": True, "detail": ""}]


def test_jaccard_overlap_on_shingles() -> None:
    a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"
    b = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda nu"
    assert jaccard_shingle_overlap(a, b) >= 0.5


def test_site_contrast_fails_low_ratio(tmp_path: Path) -> None:
    folder = tmp_path / "site"
    folder.mkdir()
    (folder / "style.css").write_text("body { color: #777777; background-color: #888888; }\n", encoding="utf-8")
    (folder / "index.html").write_text(
        '<!doctype html><html lang="en"><head><title>Readable Title Here</title></head>'
        "<body><h1>Only one</h1></body></html>",
        encoding="utf-8",
    )
    contrast = next(r for r in site_readability_rows(folder) if r["check"] == "contrast")
    assert contrast["ok"] is False


def test_site_text_size_and_title(tmp_path: Path) -> None:
    folder = tmp_path / "site"
    folder.mkdir()
    (folder / "style.css").write_text("body { font-size: 12px; }\n", encoding="utf-8")
    (folder / "index.html").write_text(
        '<!doctype html><html lang="en"><head><title>Hi</title></head>'
        '<body><h1>Title</h1><img src="x.png"></body></html>',
        encoding="utf-8",
    )
    rows = {r["check"]: r for r in site_readability_rows(folder)}
    assert rows["text size"]["ok"] is False
    assert rows["title"]["ok"] is False
    assert rows["image alt"]["ok"] is False
    assert rows["headings"]["ok"] is True


def test_collect_checks_copy_includes_quality(tmp_path: Path) -> None:
    path = tmp_path / "copy.md"
    path.write_text(_copy_words(25), encoding="utf-8")
    names = {r["check"] for r in collect_checks("copy", path, allow_commands=False)}
    assert {"length", "filler", "specifics"} <= names


def test_launch_parts_differ_row(tmp_path: Path) -> None:
    launch = tmp_path / "L"
    launch.mkdir()
    body = " ".join(f"Brew Brand coffee roast number {i} for commuters." for i in range(8))
    manifest = {
        "name": "Brew",
        "goal": "launch",
        "parts": [
            {"id": "a", "kind": "copy", "path": "a.md"},
            {"id": "b", "kind": "copy", "path": "b.md"},
        ],
    }
    (launch / "launch.json").write_text(json.dumps(manifest), encoding="utf-8")
    (launch / "a.md").write_text(body, encoding="utf-8")
    (launch / "b.md").write_text(body, encoding="utf-8")
    rows = collect_launch_checks(launch, allow_commands=False)
    differ = next(r for r in rows if r["check"] == "parts differ")
    assert differ["ok"] is False


@pytest.fixture(autouse=True)
def block_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(Path("no-such-browser")))
