from __future__ import annotations

from promptrig.compiler.ir import find_duplicate_semantic_owners, iter_schema_errors, parse_ir

from .fixtures.ir_fixtures import (
    ir_with_duplicate_requirement_ids,
    ir_with_repair_limit_above_two,
    ir_with_unknown_field,
    ir_with_wrong_spec_version,
    minimal_valid_ir,
)


def test_minimal_valid_ir_has_no_schema_errors(ir_schema_path):
    errors = iter_schema_errors(minimal_valid_ir(), ir_schema_path)
    assert errors == []


def test_unknown_field_rejected(ir_schema_path):
    errors = iter_schema_errors(ir_with_unknown_field(), ir_schema_path)
    assert len(errors) >= 1


def test_repair_limit_above_two_rejected(ir_schema_path):
    errors = iter_schema_errors(ir_with_repair_limit_above_two(), ir_schema_path)
    assert any("/evaluation/repair_limit" in e.json_pointer for e in errors)


def test_wrong_spec_version_is_schema_invalid(ir_schema_path):
    # The schema itself pins spec_version to a const; this is exercised
    # separately from find_duplicate_semantic_owners via the validation pass.
    errors = iter_schema_errors(ir_with_wrong_spec_version(), ir_schema_path)
    assert any(e.json_pointer == "/spec_version" for e in errors)


def test_duplicate_requirement_ids_detected():
    duplicates = find_duplicate_semantic_owners(ir_with_duplicate_requirement_ids())
    assert duplicates == [("/requirements/1/id", "REQ-001")]


def test_no_duplicates_in_minimal_ir():
    assert find_duplicate_semantic_owners(minimal_valid_ir()) == []


def test_parse_ir_computes_canonical_digest():
    import json

    raw = json.dumps(minimal_valid_ir()).encode("utf-8")
    parsed = parse_ir(raw, source_document="test.json")
    assert len(parsed.canonical_sha256) == 64
    assert parsed.document["spec_version"] == "0.1.0"


def test_parse_ir_digest_independent_of_key_order():
    import json

    doc = minimal_valid_ir()
    reordered = dict(reversed(list(doc.items())))
    raw_a = json.dumps(doc).encode("utf-8")
    raw_b = json.dumps(reordered).encode("utf-8")
    assert parse_ir(raw_a).canonical_sha256 == parse_ir(raw_b).canonical_sha256


def test_parse_ir_rejects_duplicate_keys():
    from promptrig.compiler.ir import IRParseError

    import pytest

    with pytest.raises(IRParseError):
        parse_ir('{"spec_version": "0.1.0", "spec_version": "0.1.0"}')
