"""Shipped Tauri build checks follow the names in each generated project."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofhouse import app_platforms, make_checks


@pytest.mark.parametrize("platform_id,relative_output", [
    ("windows", "src-tauri/target/release/weather-station.exe"),
    ("linux", "src-tauri/target/release/weather-station"),
    ("macos", "src-tauri/target/release/bundle/macos/Weather Station.app"),
])
@pytest.mark.parametrize("make_output", [True, False])
def test_shipped_tauri_build_checks_project_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform_id: str,
    relative_output: str, make_output: bool,
) -> None:
    entry = {item["id"]: item for item in app_platforms._read(app_platforms.SHIPPED)}[platform_id]
    folder = tmp_path / "weather-station"
    config = folder / "src-tauri" / "tauri.conf.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"mainBinaryName": "weather-station", "productName": "Weather Station"}), encoding="utf-8")
    expected = folder / relative_output

    monkeypatch.setattr(app_platforms, "host_os", lambda: platform_id)
    monkeypatch.setattr(app_platforms, "_tool_problem", lambda *args: None)
    monkeypatch.setattr(make_checks, "_command", lambda *args: ["fake-tool"])
    calls = 0

    def fake_build(*args: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == len(entry["build"]["before"]) + 1 and make_output:
            if platform_id == "macos":
                expected.mkdir(parents=True)
                (expected / "Contents").mkdir()
                (expected / "Contents" / "Info.plist").write_text("app", encoding="utf-8")
            else:
                expected.parent.mkdir(parents=True)
                expected.write_text("binary", encoding="utf-8")
        return {"ok": True, "detail": "built"}

    monkeypatch.setattr(make_checks, "build", fake_build)
    found = app_platforms.build_check(folder, entry, True, "weather-station")
    assert calls == len(entry["build"]["before"]) + 1
    if make_output:
        assert found["ok"] is True, found
    else:
        assert found["ok"] is False and "missing" in found["detail"], found
