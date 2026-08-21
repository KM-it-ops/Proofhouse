"""Resolves the frozen contract files the compiler ships with.

These are vendored, byte-identical copies of the frozen sources under
`architecture/` (see test_contract_schema_drift.py, which fails the build
if a vendored copy ever diverges from its frozen source). Vendoring makes
the installed package self-contained: an installed wheel does not depend
on the surrounding Git repository being present.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

_SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"

IR_SCHEMA_PATH = _SCHEMAS_DIR / "promptrig_ir_v0_1.schema.json"
DIAGNOSTIC_CONTRACT_SCHEMA_PATH = _SCHEMAS_DIR / "diagnostic_contract.schema.json"
DIAGNOSTIC_REGISTRY_PATH = _SCHEMAS_DIR / "diagnostic_code_registry.json"
REQUIREMENTS_DIAGNOSTIC_REGISTRY_PATH = _SCHEMAS_DIR / "requirements_diagnostic_registry.json"


def escape_json_pointer_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def join_json_pointer(base: str, token: str | int) -> str:
    return f"{base}/{escape_json_pointer_token(str(token))}"


def all_json_pointers(value: Any, base: str = "") -> tuple[str, ...]:
    pointers = [base]
    if isinstance(value, dict):
        for key, nested in value.items():
            pointers.extend(all_json_pointers(nested, join_json_pointer(base, key)))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            pointers.extend(all_json_pointers(nested, join_json_pointer(base, index)))
    return tuple(pointers)


def semantic_leaf_pointers(value: Any, base: str = "") -> tuple[str, ...]:
    """Return paths whose exact JSON values are semantic units.

    Scalar values are leaves. Empty arrays and objects are also units because
    their explicit presence differs semantically from an absent optional
    section. This is intentionally separate from ``all_json_pointers``: a
    source-identity pointer inventory must never be presented as coverage.
    """
    if isinstance(value, dict):
        if not value:
            return (base,)
        return tuple(path for key, nested in value.items() for path in semantic_leaf_pointers(nested, join_json_pointer(base, key)))
    if isinstance(value, list):
        if not value:
            return (base,)
        return tuple(path for index, nested in enumerate(value) for path in semantic_leaf_pointers(nested, join_json_pointer(base, index)))
    return (base,)
