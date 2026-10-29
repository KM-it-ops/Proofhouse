"""Faults a full live run exposed: a wrapped media-service file, uninstall's flag name, a silent render."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from proofhouse import cli, media

SERVICE = {"id": "my-gpu", "kinds": ["image"], "base_url": "http://localhost:7860", "key_env": None, "auth": "none",
           "unit": "image", "submit": {"path": "/generate", "body": {"prompt": "{prompt}"}}, "result": {"asset": ["image"]}}


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "home"
    folder.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: folder))
    monkeypatch.setenv("PROOFHOUSE_HOME", str(folder))
    return folder


def test_media_add_takes_the_wrapped_file_media_list_prints(home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    wrapped = {"schema": media.MEDIA_SCHEMA, "providers": [SERVICE, {**SERVICE, "id": "other-gpu"}]}
    (tmp_path / "w.json").write_text(json.dumps(wrapped), encoding="utf-8")
    assert cli.main(["media", "add", "--from", str(tmp_path / "w.json")]) == 0
    saved = json.loads(media.user_path().read_text(encoding="utf-8"))
    assert [entry["id"] for entry in saved["providers"]] == ["my-gpu", "other-gpu"]
    assert "my-gpu" in capsys.readouterr().out


def test_media_add_says_what_is_wrong_with_a_file_that_is_not_a_service(home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "x.json").write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    assert cli.main(["media", "add", "--from", str(tmp_path / "x.json")]) == 2
    err = capsys.readouterr().err
    assert "None" not in err and "id" in err


def test_uninstall_accepts_into_like_install_does(home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rule = tmp_path / "keep.md"
    rule.write_text("# Keep it short\n\nAnswer in one line.\n", encoding="utf-8")
    project = tmp_path / "proj"
    project.mkdir()
    assert cli.main(["install", "rule", str(rule), "--into", "claude", "--project", str(project)]) == 0
    capsys.readouterr()
    assert cli.main(["uninstall", "rule", "keep", "--into", "claude", "--project", str(project)]) == 0
    assert "removed rule keep" in capsys.readouterr().out


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="needs ffmpeg")
def test_render_video_says_where_the_files_went(home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = tmp_path / "video"
    folder.mkdir()
    picture = folder / "card.png"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=320x180", "-frames:v", "1", str(picture)], check=True)
    (folder / "script.json").write_text(json.dumps({"title": "t", "shots": [{"seconds": 1, "visual": "card", "caption": "Hi", "file": "card.png"}]}), encoding="utf-8")
    assert cli.main(["render", "video", str(folder), "--formats", "16x9", "--size-scale", "0.25"]) == 0
    out = capsys.readouterr().out
    assert "video-16x9.mp4" in out and "checks passed" in out
