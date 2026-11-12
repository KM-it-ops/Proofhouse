"""The shared secret-hygiene module: one pattern, one scrubber, one minimal environment for every surface."""
from __future__ import annotations

from proofhouse import scrub


def test_secret_values_covers_named_keys_and_secret_named_variables_longest_first(monkeypatch) -> None:
    monkeypatch.setenv("MY_API_KEY", "key-value-123456")
    monkeypatch.setenv("GH_TOKEN", "ghp-longer-secret-value")
    monkeypatch.setenv("PATH", "/usr/bin")  # not secret-named: never collected
    values = scrub.secret_values(["MY_API_KEY", "MISSING_NAME"])
    assert "key-value-123456" in values and "ghp-longer-secret-value" in values
    assert values == sorted(values, key=len, reverse=True)
    assert "/usr/bin" not in values


def test_secret_values_ignores_too_short_values(monkeypatch) -> None:
    monkeypatch.setenv("GH_TOKEN", "abc")
    assert "abc" not in scrub.secret_values(["GH_TOKEN"])


def test_clean_blanks_secrets_and_keeps_only_the_tail_when_long(monkeypatch) -> None:
    text = "token ghp-longer-secret-value here " + "x" * 100
    out = scrub.clean(text, ["ghp-longer-secret-value"], 50)
    assert "ghp-longer-secret-value" not in out
    assert out.startswith("…") and len(out) == 51
    assert scrub.clean("short ghp-longer-secret-value", ["ghp-longer-secret-value"], 50) == "short [redacted]"


def test_minimal_env_keeps_the_allowlist_and_drops_secret_named_variables(monkeypatch) -> None:
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("HOME", "/home/x")
    monkeypatch.setenv("GH_TOKEN", "ghp-xyz-123")
    monkeypatch.setenv("SOMETHING_ELSE", "plain-value")
    env = scrub.minimal_env()
    assert env["PATH"] == "/usr/bin" and env["HOME"] == "/home/x"
    assert "GH_TOKEN" not in env and "SOMETHING_ELSE" not in env
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
