"""Stage 3 hard cases that broke: each one is pinned here so the break cannot come back."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofhouse.compiler import cli_compiler


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PROOFHOUSE_HOME", str(tmp_path / "home"))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _run(argv: list[str], capsys) -> tuple[int, str, str]:
    code = cli_compiler.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_inspect_of_a_folder_is_a_clean_usage_error(home: Path, capsys) -> None:
    (home / "looks.json").mkdir()
    code, out, err = _run(["inspect", "looks.json"], capsys)
    assert code == 2
    assert "error" in err
    assert "internal error" not in err + out


def test_demo_into_a_workspace_that_is_a_file_is_a_clean_usage_error(home: Path, capsys) -> None:
    (home / "workspace").write_text("already here", encoding="utf-8")
    code, out, err = _run(["demo", "--workspace", "workspace"], capsys)
    assert code == 2
    assert "error" in err
    assert "internal error" not in err + out
    assert (home / "workspace").read_text(encoding="utf-8") == "already here"


def test_failed_compile_leaves_no_output_folder(home: Path, capsys) -> None:
    (home / "binary.json").write_bytes(b"\xff\xfe\x00")
    code, _, _ = _run(["compile", "binary.json", "--adapter-version", "0.1", "--output", "built"], capsys)
    assert code == 3
    assert not (home / "built").exists()


def test_assay_claims_object_instead_of_array_is_refused(home: Path, capsys) -> None:
    (home / "claims.json").write_text("{}", encoding="utf-8")
    code, out, err = _run(["assay", "--claims", "claims.json"], capsys)
    assert code == 2
    assert "array" in err + out
    assert "PASS" not in out


def test_assay_claims_with_a_non_object_row_is_refused(home: Path, capsys) -> None:
    (home / "claims.json").write_text(json.dumps([1]), encoding="utf-8")
    code, out, err = _run(["assay", "--claims", "claims.json"], capsys)
    assert code == 2
    assert "PASS" not in out


def test_assay_binary_claims_file_is_a_clean_error(home: Path, capsys) -> None:
    (home / "claims.json").write_bytes(b"\xff\xfe\x00\x01")
    code, out, err = _run(["assay", "--claims", "claims.json", "--rotten-fields"], capsys)
    assert code == 2
    assert "error" in err + out


def test_assay_claims_with_missing_fields_is_a_clean_error(home: Path, capsys) -> None:
    (home / "claims.json").write_text(json.dumps([{"id": "c1"}]), encoding="utf-8")
    code, out, err = _run(["assay", "--claims", "claims.json"], capsys)
    assert code == 2
    assert "error" in err + out


def test_case_status_on_a_half_written_case_file_is_a_clean_error(home: Path, capsys) -> None:
    (home / "half").mkdir()
    (home / "half" / "case.json").write_text("{", encoding="utf-8")
    code, out, err = _run(["optimize", "status", "--case", "half"], capsys)
    assert code == 2
    assert "error" in err
    assert "Traceback" not in err


def test_models_show_prints_a_name_the_console_cannot_encode(home: Path, monkeypatch, capfdbinary) -> None:
    import io
    import sys

    narrow = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdout", narrow)
    code = cli_compiler.main(["models", "show", "unknown-☃"])
    narrow.flush()
    assert code in (0, 2)
