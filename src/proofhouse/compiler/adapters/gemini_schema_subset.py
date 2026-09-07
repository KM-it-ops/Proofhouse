"""Gemini's documented OpenAPI-3.0-subset schema shape, shared by
structured output (`responseSchema`) and function calling
(`functionDeclarations[].parameters`).

Deliberately narrow, following the same discipline as
`openai_schema_subset.py` and `anthropic_schema_subset.py`: this module
encodes only the constraints confirmed with confidence against current
Gemini documentation as of this mission (2026-07-22), via web search
cross-checked across multiple independent sources (official
`ai.google.dev` guide pages, Google's own developer blog announcements,
and independent third-party technical write-ups and SDK issue trackers
describing the same documented behavior). Direct fetches of `ai.google.dev`
guide pages were redirected by the environment's context-mode hook before
reaching page content, the same limitation MISSION-003 and MISSION-004 hit
with `platform.openai.com`/`platform.claude.com` -- WebSearch cross-checking
was used instead, never a single-source claim.

Confirmed hard constraint (enforced as a violation by this module):
  - Supported base types: string, number, integer, boolean, array, object,
    null (standalone or in a type-union list) -- the same base type set
    OpenAI and Anthropic's checkers enforce, and consistent with Gemini's
    `responseSchema` being documented as a subset of the OpenAPI 3.0 Schema
    Object (which itself restricts `type` to this set plus `null` via a
    type array, matching modern JSON Schema conventions Gemini's docs
    explicitly reference).
  - Array schemas must declare `items` -- carried forward from the OpenAPI
    3.0 Schema Object shape `responseSchema` is documented to be a subset
    of; not independently confirmed by a Gemini-specific source stating
    "items is mandatory," so treated the same cautious way as the
    OpenAI/Anthropic checkers' shared, not-fully-source-specific baseline
    assumptions.

Confirmed but deliberately NOT enforced as a violation (this is the
genuine, source-confirmed divergence from OpenAI's and Anthropic's strict
subsets -- see MISSION_005_REPORT.md's capability manifest section):
  - Gemini does NOT require `additionalProperties: false` on object
    schemas, and does NOT require every declared property to appear in
    `required`. Multiple independent sources (the official Structured
    Outputs guide's own worked example, Firebase AI Logic's structured
    output guide, and independent technical write-ups) confirm fields are
    optional by default -- only entries actually listed in `required` are
    mandatory in the model's output. This is the opposite convention from
    OpenAI/Anthropic's all-properties-required strict mode, and is why
    this checker never flags a missing `required` entry or an omitted/true
    `additionalProperties` as a violation the way the OpenAI/Anthropic
    checkers do.
  - As of a November 2025 Gemini API structured-outputs update (Google's
    own developer blog announcement, cross-checked against an independent
    SDK issue tracker (`googleapis/python-genai#1815`) and independent
    technical blogs describing the same change), `additionalProperties`,
    `anyOf`, and `$ref`/`$defs` (including recursive schemas) became
    supported keywords, not merely unenforced-but-present ones. This
    checker does not add explicit validation for these newly-supported
    keywords (their presence is never treated as a violation, matching
    their now-confirmed support), consistent with the OpenAI/Anthropic
    checkers' precedent of not adding checks beyond confirmed hard
    constraints.
  - Unrecognized/unsupported schema keywords are documented (independent
    third-party source, not officially confirmed to checker-verification
    confidence) to be silently ignored by the API rather than rejected --
    a materially different failure mode than OpenAI/Anthropic's outright
    validation error. This checker does not attempt to enumerate an
    ignored-keyword list or flag unknown-keyword presence, to avoid
    misrepresenting "silently ignored" as "rejected" (the same discipline
    MISSION-004 applied to Anthropic's documented-but-unenforced keywords).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..paths import join_json_pointer

_SUPPORTED_TYPES = frozenset({"string", "number", "integer", "boolean", "array", "object", "null"})


@dataclass(frozen=True, slots=True)
class SubsetViolation:
    json_pointer: str
    reason: str


def check_supported_subset(schema: dict, *, base_pointer: str = "") -> tuple[SubsetViolation, ...]:
    """Returns every violation of Gemini's documented `responseSchema`/
    function-parameter OpenAPI-3.0-subset shape found in `schema`, walked
    recursively through object properties and array items. An empty tuple
    means the schema is expressible in the supported subset. Unlike
    `openai_schema_subset.check_strict_subset` and
    `anthropic_schema_subset.check_strict_subset`, this deliberately does
    NOT require `additionalProperties: false` or all-properties-required --
    see the module docstring for why that is a confirmed divergence, not
    an oversight."""
    violations: list[SubsetViolation] = []
    _walk(schema, base_pointer, violations)
    return tuple(violations)


def _walk(schema: dict, pointer: str, violations: list[SubsetViolation]) -> None:
    if not isinstance(schema, dict):
        violations.append(SubsetViolation(pointer, "schema node must be a JSON object"))
        return

    schema_type = schema.get("type")
    # A node using anyOf/oneOf (confirmed supported since the November 2025
    # update -- see module docstring) legitimately has no "type" key at all;
    # the frozen IR's json_schema $def only requires "$schema"/"type" at the
    # document root, not on every nested node, so this is not a violation.
    if schema_type is None and ("anyOf" in schema or "oneOf" in schema):
        return
    type_names = schema_type if isinstance(schema_type, list) else [schema_type]
    unsupported = [t for t in type_names if t not in _SUPPORTED_TYPES]
    if unsupported:
        violations.append(
            SubsetViolation(pointer, f"unsupported type(s) {unsupported} outside {sorted(_SUPPORTED_TYPES)}")
        )

    if "object" in type_names:
        properties: dict = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            _walk(prop_schema, join_json_pointer(join_json_pointer(pointer, "properties"), prop_name), violations)

    if "array" in type_names:
        items = schema.get("items")
        if items is None:
            violations.append(SubsetViolation(pointer, "array schemas must declare items"))
        else:
            _walk(items, join_json_pointer(pointer, "items"), violations)


def property_ordering(schema: dict) -> list[str] | None:
    """Derives Gemini's `propertyOrdering` extension field deterministically
    from an object schema's `properties` key order (Python dict/JSON
    parsing preserves source insertion order). Returns None for non-object
    schemas or schemas with no declared properties -- `propertyOrdering` is
    only meaningful for object-typed schemas, per the documented purpose of
    forcing consistent generation order for a schema's own properties."""
    schema_type = schema.get("type")
    type_names = schema_type if isinstance(schema_type, list) else [schema_type]
    if "object" not in type_names:
        return None
    properties = schema.get("properties")
    if not properties:
        return None
    return list(properties.keys())
