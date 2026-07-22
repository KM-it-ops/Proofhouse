"""Resolves the frozen contract files the compiler ships with.

These are vendored, byte-identical copies of the frozen sources under
`architecture/` (see test_contract_schema_drift.py, which fails the build
if a vendored copy ever diverges from its frozen source). Vendoring makes
the installed package self-contained: an installed wheel does not depend
on the surrounding Git repository being present.
"""
from __future__ import annotations

from pathlib import Path

_SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"

IR_SCHEMA_PATH = _SCHEMAS_DIR / "promptrig_ir_v0_1.schema.json"
DIAGNOSTIC_CONTRACT_SCHEMA_PATH = _SCHEMAS_DIR / "diagnostic_contract.schema.json"
DIAGNOSTIC_REGISTRY_PATH = _SCHEMAS_DIR / "diagnostic_code_registry.json"
