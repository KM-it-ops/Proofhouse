"""Compiler input size bound and cost-ceiling honesty (T-P1-03)."""

from __future__ import annotations

import io
import sys

from proofhouse.compiler import cli_compiler
from proofhouse.compiler.cli_compiler import _read_input
from proofhouse.compiler.closed_loop import closed_loop_from_json

EIGHT_MIB = 8 * 1024 * 1024


def test_read_input_rejects_file_over_eight_mib(tmp_path) -> None:
    path = tmp_path / "oversize.bin"
    path.write_bytes(b"x" * (EIGHT_MIB + 1))
    try:
        _read_input(str(path))
    except ValueError as exc:
        assert str(exc) == "EVR-RES-0001: input exceeds MAX_INPUT_BYTES"
    else:
        raise AssertionError("expected ValueError for oversize input")


def test_read_input_accepts_sixteen_byte_file(tmp_path) -> None:
    path = tmp_path / "small.bin"
    path.write_bytes(b"abcdefghijklmnop")
    assert _read_input(str(path)) == b"abcdefghijklmnop"


def test_read_input_rejects_oversize_stdin(monkeypatch) -> None:
    stdin = type("Stdin", (), {"buffer": io.BytesIO(b"x" * (EIGHT_MIB + 1))})()
    monkeypatch.setattr(sys, "stdin", stdin)
    try:
        _read_input("-")
    except ValueError as exc:
        assert str(exc).startswith("EVR-RES-0001")
    else:
        raise AssertionError("expected ValueError for oversize stdin")


def test_cli_oversize_input_is_usage_error(tmp_path, capsys) -> None:
    path = tmp_path / "oversize.bin"
    path.write_bytes(b"x" * (EIGHT_MIB + 1))
    exit_code = cli_compiler.main(["validate", str(path), "--json"])
    err = capsys.readouterr().err
    assert exit_code == cli_compiler.EXIT_USAGE_ERROR
    assert "EVR-RES-0001: input exceeds MAX_INPUT_BYTES" in err


def test_closed_loop_from_json_blocks_oversize_bytes() -> None:
    result = closed_loop_from_json(b"x" * (EIGHT_MIB + 1))
    assert result.status == "BLOCKED"
    assert result.diagnostics == ["EVR-RES-0001"]
    assert result.evidence_bundle == {}


def test_max_cost_usd_help_says_not_enforced(capsys) -> None:
    exit_code = cli_compiler.main(["execute-openai", "--help"])
    help_text = " ".join("".join(capsys.readouterr()).split())
    assert exit_code == 0
    assert "Declared cost ceiling recorded in evidence; not enforced pre-send." in help_text
    assert "Q1 unpicked" not in help_text
