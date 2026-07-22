"""Reproducible TypeScript generation with a CI drift check: regenerating
from the vendored schemas must byte-for-byte match the committed output
under architecture/typescript/. If this test fails, run
`python scripts/generate_typescript_contracts.py` and commit the diff."""
from __future__ import annotations

from promptrig.compiler import paths
from promptrig.compiler.codegen.typescript import generate_all


def test_generation_is_deterministic():
    a = generate_all(ir_schema_path=paths.IR_SCHEMA_PATH, diagnostic_schema_path=paths.DIAGNOSTIC_CONTRACT_SCHEMA_PATH)
    b = generate_all(ir_schema_path=paths.IR_SCHEMA_PATH, diagnostic_schema_path=paths.DIAGNOSTIC_CONTRACT_SCHEMA_PATH)
    assert a == b


def test_committed_typescript_matches_regenerated_output(repo_root):
    generated = generate_all(
        ir_schema_path=paths.IR_SCHEMA_PATH, diagnostic_schema_path=paths.DIAGNOSTIC_CONTRACT_SCHEMA_PATH
    )
    ts_dir = repo_root / "architecture" / "typescript"
    for filename, source in generated.items():
        committed = (ts_dir / filename).read_text(encoding="utf-8")
        assert committed == source, (
            f"{filename} is out of date; run scripts/generate_typescript_contracts.py and commit the diff"
        )


def test_generated_ir_type_has_required_and_optional_fields():
    generated = generate_all(
        ir_schema_path=paths.IR_SCHEMA_PATH, diagnostic_schema_path=paths.DIAGNOSTIC_CONTRACT_SCHEMA_PATH
    )
    ir_ts = generated["promptrig_ir.ts"]
    assert "export interface PromptRigIR {" in ir_ts
    assert "spec_version: \"0.1.0\";" in ir_ts
    assert "workflow?: PromptRigIRWorkflow;" in ir_ts  # optional (not in required[])


def test_generated_diagnostic_type_matches_contract_shape():
    generated = generate_all(
        ir_schema_path=paths.IR_SCHEMA_PATH, diagnostic_schema_path=paths.DIAGNOSTIC_CONTRACT_SCHEMA_PATH
    )
    diag_ts = generated["diagnostic.ts"]
    assert "export interface Diagnostic {" in diag_ts
    assert "fingerprint: string;" in diag_ts
    assert "hint?: string;" in diag_ts
