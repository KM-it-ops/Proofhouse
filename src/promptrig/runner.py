from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import validate_case, ValidationIssue


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rows.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
    return rows


def validate_dataset(path: str | Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                case = json.loads(stripped)
            except json.JSONDecodeError as exc:
                issues.append(ValidationIssue(line_number, f"Invalid JSON: {exc}"))
                continue
            issues.extend(validate_case(case, line_number))
    return issues


def build_markdown_report(dataset_path: str | Path) -> str:
    cases = load_jsonl(dataset_path)
    lines = [
        "# PromptRig Eval Report",
        "",
        f"Dataset: `{dataset_path}`",
        f"Cases: {len(cases)}",
        "",
        "| ID | Type | Expected Behavior | Pass Criteria |",
        "|---|---|---|---|",
    ]
    for case in cases:
        lines.append(
            "| {id} | {type} | {expected} | {pass_criteria} |".format(
                id=str(case.get("id", "UNKNOWN")).replace("|", "\\|"),
                type=str(case.get("type", "UNKNOWN")).replace("|", "\\|"),
                expected=str(case.get("expected_behavior", "UNKNOWN")).replace("|", "\\|"),
                pass_criteria=str(case.get("pass_criteria", "UNKNOWN")).replace("|", "\\|"),
            )
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("This report is a skeleton. Add model outputs and rubric scores after running prompt trials.")
    return "\n".join(lines) + "\n"
