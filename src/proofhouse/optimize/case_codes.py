"""Coded refusals for case and artifact-kind records (MISSION-040 SPEC §2.3).

A separate, append-only table from the compiler's ``PRG-*`` registry, which
is frozen with its own contract. A code's meaning never changes and a code is
never reused; a code that stops being used moves to ``RETIRED_CODES``.
"""

from __future__ import annotations

from .case import CaseError

CODES: dict[str, str] = {
    "PHC-KIND-0001": "unknown artifact kind",
    "PHC-SKILL-0001": "skill files have no SKILL.md at their root",
    "PHC-SKILL-0002": "unsafe path in skill files",
    "PHC-SKILL-0003": "link, junction or special file in a skill folder",
    "PHC-SKILL-0004": "skill files exceed the size limit",
    "PHC-SKILL-0005": "skill files exceed the entry limit",
    "PHC-SKILL-0006": "duplicate path in skill files",
    "PHC-SKILL-0007": "skill folder missing or unreadable",
    "PHC-SKILL-0008": "malformed skill file manifest",
}
RETIRED_CODES: tuple[str, ...] = ()


class CodedCaseError(CaseError):
    """A case refusal that carries a registered code; the message starts with the code."""

    def __init__(self, code: str, detail: str) -> None:
        if code not in CODES:
            raise ValueError(f"unregistered case diagnostic code: {code}")
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")
