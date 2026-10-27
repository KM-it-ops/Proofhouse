"""Failing tests for review-daf3221. Copy into the repo as tests/test_review_daf3221.py, then run:
uv run --extra test pytest tests/test_review_daf3221.py -q
"""

from __future__ import annotations

from pathlib import Path

from scripts.stage3_hard_cases import _scrub

BS = chr(92)


# daf3221-F1: the profile scrubber stops at a space and only knows "Users"/"home" in that exact case.
def test_f1_scrub_removes_a_profile_name_that_has_a_space(tmp_path: Path) -> None:
    text = f'File "C:{BS}Users{BS}Jane Smith{BS}AppData{BS}x.py", line 1'
    assert "Smith" not in _scrub(text, tmp_path)


def test_f1_scrub_removes_a_lower_case_windows_profile_path(tmp_path: Path) -> None:
    text = f"c:{BS}users{BS}someone{BS}AppData{BS}x.py"
    assert "someone" not in _scrub(text, tmp_path)
