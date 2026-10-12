"""make --kind site: a model writes a static site; it is checked like a visitor would and improved."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from proofhouse import live, make, sitecheck

GOOD = {
    "index.html": '<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width">'
                  '<title>Acme</title><link rel="stylesheet" href="styles.css"></head><body><h1>Acme</h1>'
                  '<img src="logo.svg" alt="Acme logo"><a href="about.html">About</a><script src="script.js"></script></body></html>',
    "about.html": '<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width"><title>About</title></head>'
                  '<body><a href="index.html">Home</a></body></html>',
    "styles.css": "body{font-family:sans-serif}",
    "script.js": "document.title = document.title;",
    "logo.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>',
}


class SiteModel:
    def __init__(self, versions: list[dict], scores: list[int]) -> None:
        self.versions, self.scores, self.judged = list(versions), list(scores), []

    def __call__(self, request: live.Request) -> live.Response:
        text = " ".join(m["content"] for m in json.loads(request.body_bytes)["messages"])
        if text.startswith("You judge AI work"):
            self.judged.append(text)
            content = json.dumps({"score": self.scores.pop(0), "missing": [], "fix": "fix the broken link"})
        else:
            content = json.dumps({"files": self.versions.pop(0)})
        return live.Response(200, {"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}})


def test_a_site_is_written_checked_judged_and_improved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(tmp_path / "no-browser"))
    broken = {k: v for k, v in GOOD.items() if k != "about.html"}
    model = SiteModel([broken, GOOD], [5, 9])
    made = make.make("a landing page for Acme", provider_id="ollama", model="m", kind="site", rounds=3,
                     out_dir=tmp_path / "s", transport=model)
    assert made.best_version == 2 and made.stopped.startswith("reached score 9")
    assert "FAIL: every internal link and file exists index.html -> about.html" in model.judged[0]
    assert "PASS: every internal link and file exists" in model.judged[1]
    assert sorted(p.name for p in (tmp_path / "s" / "site").iterdir()) == sorted(GOOD)
    assert json.loads((tmp_path / "s" / "v2" / "checks.json").read_text(encoding="utf-8"))


def test_the_checks_catch_what_a_visitor_would_notice(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_BROWSER", str(tmp_path / "no-browser"))
    sitecheck.write_site({"index.html": "<html><head></head><body><img src='x.png'><a href='/missing/'>x</a></body></html>"}, tmp_path / "w")
    checks = {c["check"]: c for c in sitecheck.check_site(tmp_path / "w")}
    for name in ("index.html has a title", "index.html declares its language", "index.html works on phones (viewport)",
                 "index.html images have alt text", "every internal link and file exists"):
        assert checks[name]["ok"] is False, name
    assert checks["opened in a browser"]["ok"] is None  # honest: not measured without a browser


@pytest.mark.parametrize("name", ["../escape.html", "/abs.html", ".hidden", "a b.html", "dir/../../x.html"])
def test_a_model_cannot_write_outside_the_site_folder(tmp_path: Path, name: str) -> None:
    with pytest.raises(sitecheck.SiteError):
        sitecheck.write_site({"index.html": "x", name: "y"}, tmp_path / "w")


@pytest.mark.skipif(sitecheck.find_browser() is None, reason="no Chrome or Chromium on this machine")
def test_with_a_browser_the_site_is_opened_and_screenshotted(tmp_path: Path) -> None:
    sitecheck.write_site(GOOD, tmp_path / "w")
    checks = {c["check"]: c for c in sitecheck.check_site(tmp_path / "w", tmp_path / "shots")}
    assert checks["screenshots at desktop and phone width"]["ok"] is True
    assert checks["no JavaScript errors in the browser"]["ok"] is True


def test_a_browser_that_hangs_is_reported_not_measured_never_a_crash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sitecheck.write_site(GOOD, tmp_path / "w")
    monkeypatch.setattr(sitecheck, "find_browser", lambda: "/fake/chrome")

    launches: list[list[str]] = []

    def hangs(command, **kwargs):
        launches.append(command)
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(sitecheck.subprocess, "run", hangs)
    checks = {c["check"]: c for c in sitecheck.check_site(tmp_path / "w", tmp_path / "shots", timeout=1)}
    assert checks["opened in a browser"]["ok"] is None
    assert "did not finish in 1 s, twice" in checks["opened in a browser"]["detail"]
    assert len(launches) == 4  # desktop and phone, each tried once more after hanging
