from __future__ import annotations

import json

import pytest

from promptrig.compiler import cli_compiler

from .fixtures.ir_fixtures import (
    ir_with_anthropic_structured_output,
    ir_with_capabilities,
    ir_with_gemini_structured_output,
    ir_with_openai_structured_output,
    ir_with_unknown_field,
    minimal_valid_ir,
)


def _write_ir(tmp_path, doc: dict, name: str = "ir.json") -> str:
    path = tmp_path / name
    path.write_text(json.dumps(doc), encoding="utf-8")
    return str(path)


def test_validate_success_exit_zero(tmp_path, capsys):
    input_path = _write_ir(tmp_path, minimal_valid_ir())
    exit_code = cli_compiler.main(["validate", input_path, "--json"])
    assert exit_code == cli_compiler.EXIT_SUCCESS
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "success"


def test_validate_invalid_exit_three(tmp_path, capsys):
    input_path = _write_ir(tmp_path, ir_with_unknown_field())
    exit_code = cli_compiler.main(["validate", input_path, "--json"])
    assert exit_code == cli_compiler.EXIT_VALIDATION_FAILURE
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"


def test_compile_success_exit_zero(tmp_path, capsys):
    input_path = _write_ir(tmp_path, minimal_valid_ir())
    exit_code = cli_compiler.main(["compile", input_path, "--json"])
    assert exit_code == cli_compiler.EXIT_SUCCESS
    out = json.loads(capsys.readouterr().out)
    assert out["data"]["adapter_id"] == "fake"


def test_compile_missing_required_capability_exit_four(tmp_path, capsys):
    ir = ir_with_capabilities(required=["nonexistent.capability@1"])
    input_path = _write_ir(tmp_path, ir)
    exit_code = cli_compiler.main(["compile", input_path, "--json"])
    assert exit_code == cli_compiler.EXIT_CAPABILITY_UNSUPPORTED


def test_compile_writes_artifacts_to_output_dir(tmp_path, capsys):
    input_path = _write_ir(tmp_path, minimal_valid_ir())
    out_dir = tmp_path / "out"
    exit_code = cli_compiler.main(["compile", input_path, "--output", str(out_dir), "--json"])
    assert exit_code == cli_compiler.EXIT_SUCCESS
    assert (out_dir / "compiled_prompt").exists()


def test_adapters_exit_zero(capsys):
    exit_code = cli_compiler.main(["adapters", "--json"])
    assert exit_code == cli_compiler.EXIT_SUCCESS
    out = json.loads(capsys.readouterr().out)
    ids = [a["adapter_id"] for a in out["data"]["adapters"]]
    assert ids == ["fake", "openai", "anthropic", "gemini"]


def test_compile_with_openai_adapter_exit_zero(tmp_path, capsys):
    input_path = _write_ir(tmp_path, ir_with_openai_structured_output(compliant=True))
    exit_code = cli_compiler.main(["compile", input_path, "--adapter", "openai", "--json"])
    assert exit_code == cli_compiler.EXIT_SUCCESS
    out = json.loads(capsys.readouterr().out)
    assert out["data"]["adapter_id"] == "openai"


def test_compile_with_anthropic_adapter_exit_zero(tmp_path, capsys):
    input_path = _write_ir(tmp_path, ir_with_anthropic_structured_output(compliant=True))
    exit_code = cli_compiler.main(["compile", input_path, "--adapter", "anthropic", "--json"])
    assert exit_code == cli_compiler.EXIT_SUCCESS
    out = json.loads(capsys.readouterr().out)
    assert out["data"]["adapter_id"] == "anthropic"


def test_compile_with_gemini_adapter_exit_zero(tmp_path, capsys):
    input_path = _write_ir(tmp_path, ir_with_gemini_structured_output(compliant=True))
    exit_code = cli_compiler.main(["compile", input_path, "--adapter", "gemini", "--json"])
    assert exit_code == cli_compiler.EXIT_SUCCESS
    out = json.loads(capsys.readouterr().out)
    assert out["data"]["adapter_id"] == "gemini"


def test_doctor_exit_zero(capsys):
    exit_code = cli_compiler.main(["doctor", "--json"])
    assert exit_code == cli_compiler.EXIT_SUCCESS


def test_usage_error_exit_two(capsys):
    exit_code = cli_compiler.main(["not-a-real-command"])
    assert exit_code == cli_compiler.EXIT_USAGE_ERROR


def test_missing_input_file_exit_two(capsys):
    exit_code = cli_compiler.main(["validate", "/no/such/file.json"])
    assert exit_code == cli_compiler.EXIT_USAGE_ERROR


def test_stdin_input_supported(tmp_path, monkeypatch, capsys):
    import io

    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(json.dumps(minimal_valid_ir()).encode())))
    exit_code = cli_compiler.main(["validate", "-", "--json"])
    assert exit_code == cli_compiler.EXIT_SUCCESS


def test_human_readable_output_not_json(tmp_path, capsys):
    input_path = _write_ir(tmp_path, minimal_valid_ir())
    exit_code = cli_compiler.main(["validate", input_path])
    assert exit_code == cli_compiler.EXIT_SUCCESS
    out = capsys.readouterr().out
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)
    assert "validate: success" in out


def test_json_stdout_is_exactly_one_json_object(tmp_path, capsys):
    input_path = _write_ir(tmp_path, minimal_valid_ir())
    cli_compiler.main(["compile", input_path, "--json"])
    out = capsys.readouterr().out
    assert out.count("\n") == 1
    json.loads(out)  # must not raise
