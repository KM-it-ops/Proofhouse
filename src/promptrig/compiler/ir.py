"""Strict PromptRig IR v0.1 parsing and schema loading.

Parsing (structural JSON correctness under the canonical-JSON profile) is
kept separate from schema validation, which is a pass-protocol concern
(see passes/validation.py). This module owns only: turning raw bytes/text
into a parsed+digested document, and running that document against the
frozen `PROMPTRIG_IR_V0_1.schema.json`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .canonical import CanonicalizationError, canonical_sha256, parse_strict_json
from .paths import join_json_pointer


class IRParseError(ValueError):
    """Raised when raw input is not valid strict canonical JSON."""


@dataclass(frozen=True, slots=True)
class SchemaError:
    message: str
    json_pointer: str


@dataclass(frozen=True, slots=True)
class ParsedIR:
    document: dict
    canonical_sha256: str
    source_document: str


@lru_cache(maxsize=None)
def _validator(schema_path: str) -> Draft202012Validator:
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def parse_ir(raw: bytes | str, *, source_document: str = "<input>") -> ParsedIR:
    """Parse and canonically digest raw IR input.

    Raises IRParseError for structural failures (invalid JSON, duplicate
    keys, invalid Unicode) -- these precede schema validation entirely.
    """
    try:
        document = parse_strict_json(raw)
    except CanonicalizationError as exc:
        raise IRParseError(str(exc)) from exc
    if not isinstance(document, dict):
        raise IRParseError("IR document must be a JSON object")
    digest = canonical_sha256(document)
    return ParsedIR(document=document, canonical_sha256=digest, source_document=source_document)


def iter_schema_errors(document: dict, schema_path: Path) -> list[SchemaError]:
    validator = _validator(str(schema_path))
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    result: list[SchemaError] = []
    for e in errors:
        parts = [str(p) for p in e.path]
        pointer = ""
        for part in parts:
            pointer = join_json_pointer(pointer, part)
        result.append(SchemaError(message=e.message, json_pointer=pointer))
    return result


def find_duplicate_semantic_owners(document: dict) -> list[tuple[str, str]]:
    """Returns (json_pointer, id) pairs for ids duplicated within a single
    IR array section (requirements, tools, workflow.steps). Each such array
    is a distinct semantic-owner namespace under the frozen schema."""
    duplicates: list[tuple[str, str]] = []
    duplicates.extend(_find_duplicate_ids(document.get("requirements"), "/requirements"))
    duplicates.extend(_find_duplicate_ids(document.get("tools"), "/tools"))
    workflow = document.get("workflow")
    if isinstance(workflow, dict):
        duplicates.extend(_find_duplicate_ids(workflow.get("steps"), "/workflow/steps"))
    return duplicates


def _find_duplicate_ids(items: Any, base_pointer: str) -> list[tuple[str, str]]:
    duplicates: list[tuple[str, str]] = []
    if not isinstance(items, list):
        return duplicates
    seen: dict[str, int] = {}
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str):
            continue
        if item_id in seen:
            duplicates.append((f"{base_pointer}/{idx}/id", item_id))
        else:
            seen[item_id] = idx
    return duplicates
