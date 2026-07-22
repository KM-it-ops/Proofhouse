"""OpenAI's documented "strict" JSON Schema subset for Structured Outputs
and strict function/tool calling.

Deliberately narrow: this module encodes only the constraints confirmed
against current OpenAI documentation as of this mission (2026-07-22) via
public API docs and OpenAI's own developer-community guidance, not every
undocumented quirk. It is not a general JSON Schema subset checker.

Confirmed constraints (structured outputs and strict:true function tools
share the same rules):
  - Every object-typed schema node MUST set additionalProperties: false.
  - Every property declared in an object's `properties` MUST also appear
    in that object's `required` array -- "optional" fields are expressed
    as a nullable type union (e.g. `"type": ["string", "null"]`), not by
    omission from `required`.
  - Supported primitive/composite types: string, number, integer,
    boolean, array, object, null (used standalone or in a nullable
    type-union list).

Anything outside this -- schema keywords not explicitly confirmed here
(minLength, pattern, format, numeric bounds, etc.) -- is deliberately NOT
asserted as supported or unsupported by this module; see
MISSION_003_REPORT.md Technical Debt for the scope boundary and sourcing.
"""
from __future__ import annotations

from dataclasses import dataclass

_SUPPORTED_TYPES = frozenset({"string", "number", "integer", "boolean", "array", "object", "null"})


@dataclass(frozen=True, slots=True)
class SubsetViolation:
    json_pointer: str
    reason: str


def check_strict_subset(schema: dict, *, base_pointer: str = "") -> tuple[SubsetViolation, ...]:
    """Returns every violation of the documented strict-mode subset found in
    `schema`, walked recursively through object properties and array items.
    An empty tuple means the schema is expressible in the strict subset."""
    violations: list[SubsetViolation] = []
    _walk(schema, base_pointer, violations)
    return tuple(violations)


def _walk(schema: dict, pointer: str, violations: list[SubsetViolation]) -> None:
    if not isinstance(schema, dict):
        violations.append(SubsetViolation(pointer, "schema node must be a JSON object"))
        return

    schema_type = schema.get("type")
    type_names = schema_type if isinstance(schema_type, list) else [schema_type]
    unsupported = [t for t in type_names if t not in _SUPPORTED_TYPES]
    if unsupported:
        violations.append(
            SubsetViolation(pointer, f"unsupported type(s) {unsupported} outside {sorted(_SUPPORTED_TYPES)}")
        )

    if "object" in type_names:
        if schema.get("additionalProperties") is not False:
            violations.append(SubsetViolation(pointer, "object schemas must set additionalProperties: false"))

        properties: dict = schema.get("properties", {})
        required = set(schema.get("required", []))
        missing_required = sorted(set(properties) - required)
        if missing_required:
            violations.append(
                SubsetViolation(
                    pointer,
                    f"all properties must be listed in required (missing: {missing_required}); "
                    f"express optional fields as a nullable type union instead",
                )
            )
        for prop_name, prop_schema in properties.items():
            _walk(prop_schema, f"{pointer}/properties/{prop_name}", violations)

    if "array" in type_names:
        items = schema.get("items")
        if items is None:
            violations.append(SubsetViolation(pointer, "array schemas must declare items"))
        else:
            _walk(items, f"{pointer}/items", violations)
