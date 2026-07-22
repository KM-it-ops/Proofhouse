"""Anthropic's documented strict JSON Schema subset, shared by JSON Outputs
(`output_config.format`) and strict tool use (`strict: true` tool definitions).

Deliberately narrow, following the same discipline as
`openai_schema_subset.py`: this module encodes only the constraints
confirmed with confidence against current Anthropic documentation as of
this mission (2026-07-22), via web search cross-checked across multiple
independent sources (direct fetches of `platform.claude.com` guide pages
were not reliably retrievable as body text through the available tools,
the same limitation MISSION-003 hit for `platform.openai.com`). It is not
a general JSON Schema subset checker.

Confirmed hard constraints (enforced as violations by this module --
sourced from Anthropic's Structured Outputs and Strict Tool Use guides,
cross-checked against independent secondary summaries of the same guides):
  - Every object-typed schema node MUST set additionalProperties: false.
  - Every property declared in an object's `properties` MUST also appear
    in that object's `required` array.
  - Supported base types: string, number, integer, boolean, array, object,
    null (standalone or in a type-union list).

Confirmed but NOT enforced by this checker (informational only -- see
ANTHROPIC_CAPABILITY note below and MISSION_004_REPORT.md Technical Debt):
  - Anthropic's strict subset additionally documents support for `enum`,
    `const`, `anyOf`/`allOf`, and `$ref`/`$defs`, which OpenAI's confirmed
    subset (per MISSION-003) did not assert either way. This module does
    not add checks for these keywords' presence/absence; it only flags the
    two hard constraints above.
  - Keywords such as `minLength`, `maxLength`, `pattern`, `minItems`,
    `maxItems`, `minimum`, `maximum`, and `multipleOf` are confirmed, across
    multiple independent sources, to be *accepted but silently unenforced*
    by Anthropic's constrained decoding under strict mode -- this is a
    materially different behavior than "rejected as a violation", so this
    checker deliberately does NOT flag their presence as a subset violation
    (doing so would misrepresent silently-ignored-but-permitted as
    disallowed). Recorded as a known, source-confirmed gap: no diagnostic
    currently warns a schema author that these keywords will be ignored.
  - Recursive schemas (`$ref` cycles) are documented as unsupported, but
    this walker -- like the OpenAI checker it parallels -- does not detect
    reference cycles; it assumes a tree-shaped schema.
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
