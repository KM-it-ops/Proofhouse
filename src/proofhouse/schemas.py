from __future__ import annotations

from dataclasses import dataclass
from typing import Any

REQUIRED_CASE_FIELDS = {
    "id",
    "type",
    "input",
    "expected_behavior",
    "failure_signals",
    "pass_criteria",
}

VALID_CASE_TYPES = {
    "normal",
    "edge",
    "missing_context",
    "adversarial",
    "regression",
}


@dataclass(frozen=True)
class ValidationIssue:
    line: int
    message: str


def validate_case(case: dict[str, Any], line: int) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    missing = sorted(REQUIRED_CASE_FIELDS - set(case))
    if missing:
        issues.append(ValidationIssue(line, f"Missing fields: {', '.join(missing)}"))

    case_type = case.get("type")
    if case_type is not None and case_type not in VALID_CASE_TYPES:
        issues.append(ValidationIssue(line, f"Invalid type: {case_type}"))

    failure_signals = case.get("failure_signals")
    if failure_signals is not None and not isinstance(failure_signals, list):
        issues.append(ValidationIssue(line, "failure_signals must be a list"))

    for key in ["id", "input", "expected_behavior", "pass_criteria"]:
        value = case.get(key)
        if value is not None and not isinstance(value, str):
            issues.append(ValidationIssue(line, f"{key} must be a string"))
        if isinstance(value, str) and not value.strip():
            issues.append(ValidationIssue(line, f"{key} must not be empty"))

    return issues
