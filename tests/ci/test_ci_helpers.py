from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scope = load_module("ci_scope", ".github/ci/ci_scope.py")
markdown = load_module("validate_markdown", ".github/ci/validate_markdown.py")


def test_docs_only_scope():
    result = scope.classify(["docs/guide.md", "MISSION_REPORT.md"])
    assert result["scope"] == "docs"
    assert result["typescript_drift"] is False


def test_requirements_scope_and_schema_drift():
    result = scope.classify(
        [
            "architecture/requirements-compiler-contract-v0.1/schemas/requirement.schema.json",
            "tests/requirements/test_requirements_contract.py",
        ]
    )
    assert result["scope"] == "requirements"
    assert result["typescript_drift"] is True


def test_compiler_scope():
    result = scope.classify(["src/promptrig/compiler/api.py", "tests/compiler/test_api.py"])
    assert result["scope"] == "compiler"


def test_mixed_or_ci_change_is_broad():
    result = scope.classify(["src/promptrig/compiler/api.py", "tests/requirements/test_requirements_contract.py"])
    assert result["scope"] == "broad"
    assert scope.classify([".github/workflows/ci-fast.yml"])["scope"] == "broad"


def test_markdown_validator_accepts_existing_and_external_links(tmp_path: Path):
    target = tmp_path / "target.md"
    target.write_text("# Target\n", encoding="utf-8")
    source = tmp_path / "source.md"
    source.write_text("[local](target.md) [web](https://example.com)\n", encoding="utf-8")
    assert markdown.validate([source]) == []


def test_markdown_validator_rejects_missing_local_link(tmp_path: Path):
    source = tmp_path / "source.md"
    source.write_text("[missing](does-not-exist.md)\n", encoding="utf-8")
    errors = markdown.validate([source])
    assert len(errors) == 1
    assert "broken local link" in errors[0]
