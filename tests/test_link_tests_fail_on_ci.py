"""A link test that cannot make its link skips on a locked-down machine and fails on CI."""
from __future__ import annotations

import pytest

pytest_plugins = ["pytester"]

_TEST = '''
import pytest

def test_link():
    pytest.skip("directory junctions not permitted in this environment: denied")

def test_other():
    pytest.skip("no browser here")
'''


@pytest.mark.parametrize("ci, expected", [("", {"skipped": 2}), ("true", {"failed": 1, "skipped": 1})])
def test_a_refused_link_skips_off_ci_and_fails_on_ci(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch, ci: str, expected: dict) -> None:
    import pathlib

    pytester.makeconftest(pathlib.Path(__file__).with_name("conftest.py").read_text(encoding="utf-8"))
    pytester.makepyfile(_TEST)
    monkeypatch.setenv("CI", ci)
    pytester.runpytest_inprocess("-p", "no:cacheprovider").assert_outcomes(**expected)
