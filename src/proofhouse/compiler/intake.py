"""Strict JSON intake and structured-profile shape validation (T01, review F07).

Every rejection is a string prefixed with a stable code so callers can route
on the code and show the message:

- ``EVR-INP-0001`` input is not a single JSON object (bad UTF-8, bad JSON,
  duplicate keys, non-object root)
- ``EVR-INP-0002`` a field has the wrong type or value
- ``EVR-INP-0003`` a non-finite number literal (``NaN``, ``Infinity``)
- ``EVR-INP-0004`` nesting or array size exceeds the intake bounds
- ``EVR-DUP-0001`` a duplicate identifier

Validation runs before any field access or mutation; nothing here raises on
user input.
"""
from __future__ import annotations

import json
import math
from typing import Any

INP_NOT_OBJECT = "EVR-INP-0001"
INP_TYPE = "EVR-INP-0002"
INP_NONFINITE = "EVR-INP-0003"
INP_BOUNDS = "EVR-INP-0004"
DUP_ID = "EVR-DUP-0001"

MAX_DEPTH = 32
MAX_ARRAY_ITEMS = 1000

_PRIORITIES = ("required", "optional")


class IntakeError(ValueError):
    """Carries one coded diagnostic string."""

    def __init__(self, diagnostic: str) -> None:
        super().__init__(diagnostic)
        self.diagnostic = diagnostic


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise IntakeError(f"{INP_NOT_OBJECT}: duplicate JSON key {key!r}")
        out[key] = value
    return out


def _reject_constant(name: str) -> Any:
    raise IntakeError(f"{INP_NONFINITE}: non-finite number literal {name} is not allowed")


def _check_bounds(value: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise IntakeError(f"{INP_BOUNDS}: nesting deeper than {MAX_DEPTH} levels")
    if isinstance(value, dict):
        for nested in value.values():
            _check_bounds(nested, depth + 1)
    elif isinstance(value, list):
        if len(value) > MAX_ARRAY_ITEMS:
            raise IntakeError(f"{INP_BOUNDS}: array longer than {MAX_ARRAY_ITEMS} items")
        for nested in value:
            _check_bounds(nested, depth + 1)
    elif isinstance(value, float) and not math.isfinite(value):
        raise IntakeError(f"{INP_NONFINITE}: non-finite number is not allowed")


def parse_json_object(raw: bytes | str) -> dict[str, Any]:
    """Parse one bounded JSON object; raise ``IntakeError`` otherwise."""
    if isinstance(raw, (bytes, bytearray)):
        try:
            text = bytes(raw).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise IntakeError(f"{INP_NOT_OBJECT}: input is not valid UTF-8 ({exc.reason})") from None
    else:
        text = raw
    try:
        doc = json.loads(text, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_constant)
    except IntakeError:
        raise
    except RecursionError:
        raise IntakeError(f"{INP_BOUNDS}: nesting deeper than {MAX_DEPTH} levels") from None
    except json.JSONDecodeError as exc:
        raise IntakeError(f"{INP_NOT_OBJECT}: invalid JSON at line {exc.lineno} column {exc.colno}: {exc.msg}") from None
    except ValueError as exc:  # e.g. an integer longer than Python's int-conversion limit
        raise IntakeError(f"{INP_NOT_OBJECT}: invalid JSON: {str(exc)[:160]}") from None
    if not isinstance(doc, dict):
        raise IntakeError(f"{INP_NOT_OBJECT}: document root must be a JSON object, got {_type_name(doc)}")
    _check_bounds(doc)
    return doc


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def _string_list(value: Any, path: str, *, required: bool) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, list) or not value:
        return f"{INP_TYPE}: {path} must be a non-empty array of strings, got {_type_name(value)}"
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            return f"{INP_TYPE}: {path}[{index}] must be a non-empty string, got {_type_name(item)}"
    return None


def structured_shape_errors(doc: Any) -> list[str]:
    """Type/shape errors for the structured closed-loop profiles, in document order.

    Only fields the closed loop reads are checked here; profile and contract
    semantics stay in ``validate_structured_requirements``.
    """
    if not isinstance(doc, dict):
        return [f"{INP_NOT_OBJECT}: document root must be a JSON object, got {_type_name(doc)}"]
    try:
        _check_bounds(doc)
    except IntakeError as exc:
        return [exc.diagnostic]
    errors: list[str] = []

    for key in ("network_allowed", "enable_model_suggestions"):
        if key in doc and not isinstance(doc[key], bool):
            errors.append(f"{INP_TYPE}: {key} must be true or false, got {_type_name(doc[key])}")

    if "repair_budget" in doc:
        budget = doc["repair_budget"]
        if isinstance(budget, bool) or not isinstance(budget, int) or budget not in (0, 1, 2):
            errors.append(f"{INP_TYPE}: repair_budget must be the integer 0, 1 or 2, got {budget!r}")

    for key in ("profile", "contract_version", "project_name", "authoring_mode"):
        if key in doc and not isinstance(doc[key], str):
            errors.append(f"{INP_TYPE}: {key} must be a string, got {_type_name(doc[key])}")

    objective = doc.get("objective")
    if not isinstance(objective, dict):
        errors.append(f"{INP_TYPE}: objective must be an object, got {_type_name(objective)}")
    else:
        goal = objective.get("goal")
        if not isinstance(goal, str) or not goal.strip():
            errors.append(f"{INP_TYPE}: objective.goal must be a non-empty string, got {_type_name(goal)}")
        for key in ("target_users", "success_criteria", "failure_conditions"):
            if key in objective:
                error = _string_list(objective[key], f"objective.{key}", required=True)
                if error:
                    errors.append(error)

    if "behavior" in doc:
        behavior = doc["behavior"]
        if not isinstance(behavior, dict):
            errors.append(f"{INP_TYPE}: behavior must be an object, got {_type_name(behavior)}")
        else:
            for key in ("instructions", "constraints"):
                if key in behavior:
                    error = _string_list(behavior[key], f"behavior.{key}", required=True)
                    if error:
                        errors.append(error)
            for key in ("uncertainty_policy", "evidence_policy"):
                if key in behavior and (not isinstance(behavior[key], str) or not behavior[key].strip()):
                    errors.append(f"{INP_TYPE}: behavior.{key} must be a non-empty string")

    requirements = doc.get("requirements")
    if not isinstance(requirements, list):
        errors.append(f"{INP_TYPE}: requirements must be an array, got {_type_name(requirements)}")
    else:
        seen: set[str] = set()
        for index, req in enumerate(requirements):
            where = f"requirements[{index}]"
            if not isinstance(req, dict):
                errors.append(f"{INP_TYPE}: {where} must be an object, got {_type_name(req)}")
                continue
            rid = req.get("id")
            if not isinstance(rid, str):
                errors.append(f"{INP_TYPE}: {where}.id must be a string, got {_type_name(rid)}")
            elif rid in seen:
                errors.append(f"{DUP_ID}: duplicate requirement id {rid}")
            else:
                seen.add(rid)
            statement = req.get("statement")
            if not isinstance(statement, str) or not statement.strip():
                errors.append(f"{INP_TYPE}: {where}.statement must be a non-empty string")
            if "priority" in req and req["priority"] not in _PRIORITIES:
                errors.append(f"{INP_TYPE}: {where}.priority must be one of {', '.join(_PRIORITIES)}")
            if "acceptance" in req:
                error = _string_list(req["acceptance"], f"{where}.acceptance", required=True)
                if error:
                    errors.append(error)

    if "tool_permissions" in doc:
        tools = doc["tool_permissions"]
        if not isinstance(tools, dict):
            errors.append(f"{INP_TYPE}: tool_permissions must be an object")
        elif "allowed_tools" in tools:
            error = _string_list(tools["allowed_tools"], "tool_permissions.allowed_tools", required=True)
            if error:
                errors.append(error)
    if "stop_conditions" in doc:
        error = _string_list(doc["stop_conditions"], "stop_conditions", required=True)
        if error:
            errors.append(error)
    return errors
