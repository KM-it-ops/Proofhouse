from __future__ import annotations

from promptrig.compiler.adapters.gemini_schema_subset import check_supported_subset, property_ordering


def test_compliant_object_schema_has_no_violations():
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }
    assert check_supported_subset(schema) == ()


def test_missing_additional_properties_false_is_not_a_violation():
    """Genuine, source-confirmed divergence from OpenAI/Anthropic: Gemini
    does not require additionalProperties: false on object schemas."""
    schema = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
    assert check_supported_subset(schema) == ()


def test_property_missing_from_required_is_not_a_violation():
    """Genuine, source-confirmed divergence from OpenAI/Anthropic: fields
    are optional by default for Gemini; only entries actually listed in
    `required` are mandatory."""
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "nickname": {"type": "string"}},
        "required": ["name"],
    }
    assert check_supported_subset(schema) == ()


def test_no_required_array_at_all_is_not_a_violation():
    schema = {"type": "object", "properties": {"name": {"type": "string"}}}
    assert check_supported_subset(schema) == ()


def test_nullable_type_union_is_supported_for_optional_fields():
    schema = {
        "type": "object",
        "properties": {"nickname": {"type": ["string", "null"]}},
        "required": ["nickname"],
    }
    assert check_supported_subset(schema) == ()


def test_unsupported_type_is_flagged():
    schema = {"type": "object", "properties": {}, "required": []}
    schema["properties"]["thing"] = {"type": "unsupported_custom_type"}
    schema["required"] = ["thing"]
    violations = check_supported_subset(schema)
    assert any("unsupported type" in v.reason for v in violations)


def test_nested_object_recurses_into_properties():
    schema = {
        "type": "object",
        "required": ["inner"],
        "properties": {
            "inner": {
                "type": "object",
                "properties": {"x": {"type": "unsupported_custom_type"}},
                "required": ["x"],
            }
        },
    }
    violations = check_supported_subset(schema)
    assert any(v.json_pointer == "/properties/inner/properties/x" for v in violations)


def test_array_without_items_is_a_violation():
    schema = {"type": "array"}
    violations = check_supported_subset(schema)
    assert any("items" in v.reason for v in violations)


def test_array_of_objects_recurses_into_items():
    schema = {
        "type": "array",
        "items": {"type": "object", "properties": {"x": {"type": "string"}}},
    }
    violations = check_supported_subset(schema)
    assert violations == ()


def test_base_pointer_is_respected():
    schema = {"type": "array"}
    violations = check_supported_subset(schema, base_pointer="/tools/0/input_schema")
    assert violations[0].json_pointer == "/tools/0/input_schema"


def test_additional_properties_true_and_anyof_ref_are_not_flagged():
    """Confirmed supported since the November 2025 structured-outputs
    update (see module docstring); this checker does not add validation
    for these newly-supported keywords, so their presence must never be
    treated as a violation."""
    schema = {
        "type": "object",
        "additionalProperties": True,
        "properties": {
            "value": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
        },
        "required": [],
    }
    assert check_supported_subset(schema) == ()


def test_property_ordering_derives_from_properties_key_order():
    schema = {
        "type": "object",
        "properties": {"z_field": {"type": "string"}, "a_field": {"type": "string"}},
        "required": [],
    }
    assert property_ordering(schema) == ["z_field", "a_field"]


def test_property_ordering_is_none_for_non_object_schema():
    assert property_ordering({"type": "array", "items": {"type": "string"}}) is None


def test_property_ordering_is_none_for_object_with_no_properties():
    assert property_ordering({"type": "object"}) is None
