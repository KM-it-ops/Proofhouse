from __future__ import annotations

from promptrig.compiler.adapters.openai_schema_subset import check_strict_subset


def test_compliant_object_schema_has_no_violations():
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }
    assert check_strict_subset(schema) == ()


def test_missing_additional_properties_false_is_a_violation():
    schema = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
    violations = check_strict_subset(schema)
    assert any("additionalProperties" in v.reason for v in violations)


def test_property_missing_from_required_is_a_violation():
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"name": {"type": "string"}, "nickname": {"type": "string"}},
        "required": ["name"],
    }
    violations = check_strict_subset(schema)
    assert any("nickname" in v.reason for v in violations)


def test_nullable_type_union_is_supported_for_optional_fields():
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"nickname": {"type": ["string", "null"]}},
        "required": ["nickname"],
    }
    assert check_strict_subset(schema) == ()


def test_unsupported_type_is_flagged():
    schema = {"type": "object", "additionalProperties": False, "properties": {}, "required": []}
    schema["properties"]["thing"] = {"type": "unsupported_custom_type"}
    schema["required"] = ["thing"]
    violations = check_strict_subset(schema)
    assert any("unsupported type" in v.reason for v in violations)


def test_nested_object_violations_are_reported_with_json_pointer():
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["inner"],
        "properties": {
            "inner": {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
                # missing additionalProperties: false
            }
        },
    }
    violations = check_strict_subset(schema)
    assert any(v.json_pointer == "/properties/inner" and "additionalProperties" in v.reason for v in violations)


def test_array_without_items_is_a_violation():
    schema = {"type": "array"}
    violations = check_strict_subset(schema)
    assert any("items" in v.reason for v in violations)


def test_array_of_objects_recurses_into_items():
    schema = {
        "type": "array",
        "items": {"type": "object", "properties": {"x": {"type": "string"}}, "required": []},
    }
    violations = check_strict_subset(schema)
    assert any(v.json_pointer == "/items" for v in violations)


def test_base_pointer_is_respected():
    schema = {"type": "object", "properties": {}, "required": []}
    violations = check_strict_subset(schema, base_pointer="/tools/0/input_schema")
    assert violations[0].json_pointer == "/tools/0/input_schema"
