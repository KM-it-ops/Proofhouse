"""Deterministic plain_language_v0 constrained prose parser (MISSION-013 M1)."""
from __future__ import annotations

import re
from typing import Any

_NUMBERED_REQ = re.compile(r"^(\d+)\.\s*(.+)$")
_CONSTRAINT = re.compile(r"^- (.+)$")

_DEFAULT_PROJECT_NAME = "plain-language-m1"
_DEFAULT_INSTRUCTIONS = ["Follow requirements exactly."]


class PlainLanguageParseError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def parse_plain_language_v0(text: str, *, project_name: str | None = None) -> dict[str, Any]:
    """Parse constrained prose into a structured_minimal_v0 requirements document."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    parsed_project: str | None = None
    goal: str | None = None
    requirements: list[dict[str, str]] = []
    constraints: list[str] = []

    state = "start"
    expected_req_num = 1
    saw_requirements_header = False
    saw_constraints_header = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            raise PlainLanguageParseError("PL-PARSE-0001", f"forbidden comment line: {line!r}")

        if state == "start":
            if line.startswith("Project:"):
                parsed_project = line[len("Project:") :].strip()
                if not parsed_project:
                    raise PlainLanguageParseError("PL-PARSE-0002", "Project: requires a non-empty name")
                state = "after_project"
                continue
            if line.startswith("Goal:"):
                goal = line[len("Goal:") :].strip()
                if not goal:
                    raise PlainLanguageParseError("PL-PARSE-0002", "Goal: requires a non-empty goal")
                state = "after_goal"
                continue
            raise PlainLanguageParseError("PL-PARSE-0001", f"unexpected line: {line!r}")

        if state == "after_project":
            if line.startswith("Goal:"):
                goal = line[len("Goal:") :].strip()
                if not goal:
                    raise PlainLanguageParseError("PL-PARSE-0002", "Goal: requires a non-empty goal")
                state = "after_goal"
                continue
            raise PlainLanguageParseError("PL-PARSE-0001", f"expected Goal: after Project:, got: {line!r}")

        if state == "after_goal":
            if line == "Requirements:":
                saw_requirements_header = True
                state = "requirements"
                continue
            raise PlainLanguageParseError("PL-PARSE-0001", f"expected Requirements: header, got: {line!r}")

        if state == "requirements":
            if line == "Constraints:":
                if not requirements:
                    raise PlainLanguageParseError("PL-PARSE-0002", "Requirements: must list at least one item")
                saw_constraints_header = True
                state = "constraints"
                continue
            match = _NUMBERED_REQ.match(line)
            if match is None:
                raise PlainLanguageParseError("PL-PARSE-0001", f"expected numbered requirement, got: {line!r}")
            req_num = int(match.group(1))
            statement = match.group(2).strip()
            if not statement:
                raise PlainLanguageParseError("PL-PARSE-0002", f"requirement {req_num} missing statement")
            if req_num != expected_req_num:
                raise PlainLanguageParseError(
                    "PL-PARSE-0003",
                    f"requirement numbering gap: expected {expected_req_num}, got {req_num}",
                )
            requirements.append(
                {
                    "id": f"REQ-PL-{req_num:03d}",
                    "statement": statement,
                }
            )
            expected_req_num += 1
            continue

        if state == "constraints":
            match = _CONSTRAINT.match(line)
            if match is None:
                raise PlainLanguageParseError("PL-PARSE-0001", f"expected constraint line, got: {line!r}")
            constraint = match.group(1).strip()
            if not constraint:
                raise PlainLanguageParseError("PL-PARSE-0002", "constraint line requires non-empty text")
            constraints.append(constraint)
            continue

        raise PlainLanguageParseError("PL-PARSE-0001", f"unexpected line: {line!r}")

    if goal is None:
        raise PlainLanguageParseError("PL-PARSE-0002", "missing required Goal: line")
    if not saw_requirements_header or not requirements:
        raise PlainLanguageParseError("PL-PARSE-0002", "missing Requirements: header or empty requirements list")
    if saw_constraints_header and state == "constraints" and not constraints:
        pass

    resolved_project = parsed_project or project_name or _DEFAULT_PROJECT_NAME

    return {
        "profile": "structured_minimal_v0",
        "intake_profile": "plain_language_v0",
        "contract_version": "0.1.0",
        "project_name": resolved_project,
        "network_allowed": False,
        "objective": {"goal": goal},
        "requirements": requirements,
        "behavior": {
            "instructions": list(_DEFAULT_INSTRUCTIONS),
            "constraints": constraints,
        },
    }
