"""Checks for the committed, model-free native build fixture."""

from __future__ import annotations

import json
from pathlib import Path

from proofhouse import app_platforms
from scripts import native_build_sample


def test_sample_satisfies_each_platform_static_checks(tmp_path: Path) -> None:
    for entry in app_platforms._read(app_platforms.SHIPPED):
        folder = tmp_path / entry["id"]
        native_build_sample.prepare(folder, entry["id"])
        assert all(check["ok"] is True for check in app_platforms.static_checks(folder, entry)), entry["id"]


def test_mobile_builds_copy_web_assets_and_use_native_debug_tools() -> None:
    shipped = {entry["id"]: entry for entry in app_platforms._read(app_platforms.SHIPPED)}
    ios = shipped["ios"]["build"]
    android = shipped["android"]["build"]
    for platform_id, build in (("ios", ios), ("android", android)):
        assert ["npx", "--no-install", "cap", "copy", platform_id] in build["before"]
    assert ios["command"][0] == "xcodebuild" and "CODE_SIGNING_ALLOWED=NO" in ios["command"]
    assert "-derivedDataPath" in ios["command"] and ios["output"].endswith("App.app")
    assert android["command"][0] == "{gradlew}" and "assembleDebug" in android["command"]
    assert android["output"].endswith("app-debug.apk")
    assert app_platforms._fill(android["command"], Path("app"), "app")[0].endswith(
        "gradlew.bat" if app_platforms.os.name == "nt" else "gradlew")


def test_sample_runner_reports_build_failure(monkeypatch, capsys) -> None:
    monkeypatch.setattr(app_platforms, "build_check", lambda *args, **kwargs: {
        "check": "android build", "ok": False, "detail": "build failed"})
    assert native_build_sample.main(["android"]) == 1
    assert json.loads(capsys.readouterr().out)["build"]["detail"] == "build failed"


def test_output_through_a_directory_link_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "app.bin").write_text("keep", encoding="utf-8")
    folder = tmp_path / "app"
    folder.mkdir()
    (folder / "noop.py").write_text("pass\n", encoding="utf-8")
    try:
        (folder / "dist").symlink_to(outside, target_is_directory=True)
    except OSError:
        return
    entry = {"id": "custom", "host_os": [app_platforms.host_os()], "build": {
        "tool": "python", "install": "python", "command": ["python", "noop.py"],
        "output": "dist/app.bin", "timeout": 10}}
    found = app_platforms.build_check(folder, entry, True, "app")
    assert found["ok"] is False and "outside" in found["detail"]
    assert (outside / "app.bin").read_text(encoding="utf-8") == "keep"
