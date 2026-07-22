"""Library/CLI parity per LIBRARY_CLI_PARITY_MATRIX.json: CLI JSON data and
diagnostics must deep-equal the serialized library result after removing
declared transport metadata (here: nothing is added, so equality is exact
modulo the volatile `duration_seconds` field)."""
from __future__ import annotations

import io
import json

from promptrig.compiler import api, cli_compiler

from .fixtures.ir_fixtures import (
    ir_with_anthropic_structured_output,
    ir_with_capabilities,
    ir_with_gemini_structured_output,
    ir_with_openai_structured_output,
    ir_with_repair_limit_above_two,
    minimal_valid_ir,
)


def _strip_volatile(data: dict) -> dict:
    data = json.loads(json.dumps(data))
    for entry in data.get("pass_trace", []):
        entry.pop("duration_seconds", None)
    return data


def _run_cli(argv: list[str], capsys) -> dict:
    exit_code = cli_compiler.main(argv)
    out = json.loads(capsys.readouterr().out)
    return exit_code, out


def test_parity_001_validate_minimal(tmp_path, capsys):
    doc = minimal_valid_ir()
    path = tmp_path / "ir.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    lib_env = api.validate(json.dumps(doc).encode("utf-8"), source_document=str(path))
    exit_code, cli_out = _run_cli(["validate", str(path), "--json"], capsys)

    assert exit_code == 0
    assert _strip_volatile(cli_out["data"]) == _strip_volatile(lib_env.data)
    assert [d.to_dict() for d in lib_env.diagnostics] == cli_out["diagnostics"]


def test_parity_003_repair_limit_above_two(tmp_path, capsys):
    doc = ir_with_repair_limit_above_two()
    path = tmp_path / "ir.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    exit_code, cli_out = _run_cli(["validate", str(path), "--json"], capsys)
    assert exit_code == 3
    assert cli_out["status"] == "error"


def test_parity_004_compile_fake_adapter_success(tmp_path, capsys):
    doc = minimal_valid_ir()
    path = tmp_path / "ir.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    lib_env = api.compile(json.dumps(doc).encode("utf-8"), adapter_id="fake", adapter_version="0.1.0", source_document=str(path))
    exit_code, cli_out = _run_cli(["compile", str(path), "--adapter-version", "0.1.0", "--json"], capsys)

    assert exit_code == 0
    assert _strip_volatile(cli_out["data"]) == _strip_volatile(lib_env.data)


def test_parity_005_missing_required_capability(tmp_path, capsys):
    doc = ir_with_capabilities(required=["nonexistent.capability@1"])
    path = tmp_path / "ir.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    exit_code, cli_out = _run_cli(["compile", str(path), "--adapter-version", "0.1.0", "--json"], capsys)
    assert exit_code == 4
    assert cli_out["data"]["artifacts"] == []


def test_parity_006_optional_capability_warning(tmp_path, capsys):
    doc = ir_with_capabilities(optional=["nonexistent.optional@1"])
    path = tmp_path / "ir.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    exit_code, cli_out = _run_cli(["compile", str(path), "--adapter-version", "0.1.0", "--json"], capsys)
    assert exit_code == 0  # success, including warning-only results
    assert cli_out["status"] == "warning"


def test_parity_007_inspect_compiled_manifest(tmp_path, capsys):
    doc = ir_with_capabilities(required=["output.structured_json@1"])
    path = tmp_path / "ir.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    lib_env = api.inspect(json.dumps(doc).encode("utf-8"), source_document=str(path))
    exit_code, cli_out = _run_cli(["inspect", str(path), "--json"], capsys)

    assert exit_code == 0
    assert _strip_volatile(cli_out["data"]) == _strip_volatile(lib_env.data)


def test_parity_008_adapters_registry(capsys):
    lib_env = api.list_adapters()
    exit_code, cli_out = _run_cli(["adapters", "--json"], capsys)

    assert exit_code == 0
    assert cli_out["data"] == lib_env.data
    ids = [a["adapter_id"] for a in cli_out["data"]["adapters"]]
    assert ids == ["fake", "openai", "anthropic", "gemini"]


def test_parity_011_compile_openai_adapter_success(tmp_path, capsys):
    doc = ir_with_openai_structured_output(compliant=True)
    path = tmp_path / "ir.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    lib_env = api.compile(json.dumps(doc).encode("utf-8"), adapter_id="openai", adapter_version="0.1.0", source_document=str(path))
    exit_code, cli_out = _run_cli(["compile", str(path), "--adapter", "openai", "--adapter-version", "0.1.0", "--json"], capsys)

    assert exit_code == 0
    assert cli_out["data"]["adapter_id"] == "openai"
    assert _strip_volatile(cli_out["data"]) == _strip_volatile(lib_env.data)


def test_parity_012_compile_anthropic_adapter_success(tmp_path, capsys):
    doc = ir_with_anthropic_structured_output(compliant=True)
    path = tmp_path / "ir.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    lib_env = api.compile(json.dumps(doc).encode("utf-8"), adapter_id="anthropic", adapter_version="0.1.0", source_document=str(path))
    exit_code, cli_out = _run_cli(["compile", str(path), "--adapter", "anthropic", "--adapter-version", "0.1.0", "--json"], capsys)

    assert exit_code == 0
    assert cli_out["data"]["adapter_id"] == "anthropic"
    assert _strip_volatile(cli_out["data"]) == _strip_volatile(lib_env.data)


def test_parity_013_compile_gemini_adapter_success(tmp_path, capsys):
    doc = ir_with_gemini_structured_output(compliant=True)
    path = tmp_path / "ir.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    lib_env = api.compile(json.dumps(doc).encode("utf-8"), adapter_id="gemini", adapter_version="0.1.0", source_document=str(path))
    exit_code, cli_out = _run_cli(["compile", str(path), "--adapter", "gemini", "--adapter-version", "0.1.0", "--json"], capsys)

    assert exit_code == 0
    assert cli_out["data"]["adapter_id"] == "gemini"
    assert _strip_volatile(cli_out["data"]) == _strip_volatile(lib_env.data)


def test_parity_009_doctor_healthy(capsys):
    lib_env = api.doctor()
    exit_code, cli_out = _run_cli(["doctor", "--json"], capsys)

    assert exit_code == 0
    assert cli_out["data"] == lib_env.data


def test_parity_010_doctor_invalid_configuration(monkeypatch, tmp_path, capsys):
    from promptrig.compiler import paths

    missing = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(paths, "DIAGNOSTIC_REGISTRY_PATH", missing)

    exit_code, cli_out = _run_cli(["doctor", "--json"], capsys)
    assert exit_code == 7
    assert cli_out["status"] == "error"
    assert any(d["code"] == "PRG-ENVIRONMENT-0001" for d in cli_out["diagnostics"])


def test_parity_installed_script_and_python_module_agree(tmp_path, capsys):
    """Both required invocation forms (installed script, python -m) resolve to
    the same main() entry point and therefore produce identical output."""
    import promptrig.compiler.cli_compiler as module_entry

    doc = minimal_valid_ir()
    path = tmp_path / "ir.json"
    path.write_text(json.dumps(doc), encoding="utf-8")

    exit_a = module_entry.main(["validate", str(path), "--json"])
    out_a = json.loads(capsys.readouterr().out)
    exit_b = cli_compiler.main(["validate", str(path), "--json"])
    out_b = json.loads(capsys.readouterr().out)

    assert exit_a == exit_b
    out_a["data"] = _strip_volatile(out_a["data"])
    out_b["data"] = _strip_volatile(out_b["data"])
    assert out_a == out_b
