"""The video production line end to end: script, shots, voice-over, music, edit, captions, three renders, checks."""
from __future__ import annotations

import base64
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from proofhouse import cli, live, media, studio

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="FFmpeg not installed")

SCRIPT = {
    "title": "Proofhouse launch",
    "voiceover": "Say what you want. Pick any model. Proofhouse makes it.",
    "shots": [
        {"seconds": 2, "visual": "a glowing workshop at night", "caption": "Say what you want"},
        {"seconds": 2, "visual": "hands on a keyboard, neon light", "caption": "Pick any model"},
        {"seconds": 2, "visual": "a finished product on a desk", "caption": "Proofhouse makes it"},
    ],
    "music": "upbeat electronic, 120 bpm",
}


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


@pytest.fixture
def services(tmp_path: Path) -> dict[str, bytes]:
    _ffmpeg("-f", "lavfi", "-i", "color=c=0x2255aa:s=320x180", "-frames:v", "1", str(tmp_path / "frame.png"))
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=5", str(tmp_path / "voice.wav"))
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=220:duration=3", str(tmp_path / "bed.wav"))
    templates = [
        {"id": "local-images", "kinds": ["image"], "base_url": "http://localhost:7860", "auth": "none", "unit": "image",
         "submit": {"path": "/img", "body": {"prompt": "{prompt}"}}, "result": {"asset": ["image"], "ext": "png"}},
        {"id": "local-voice", "kinds": ["speech"], "base_url": "http://localhost:7861", "auth": "none", "unit": "1k_chars",
         "submit": {"path": "/tts", "body": {"text": "{prompt}"}}, "result": {"binary": True, "ext": "wav"}},
    ]
    (tmp_path / "t.json").write_text(json.dumps(templates), encoding="utf-8")
    assert cli.main(["media", "add", "--from", str(tmp_path / "t.json")]) == 0
    return {"png": (tmp_path / "frame.png").read_bytes(), "wav": (tmp_path / "voice.wav").read_bytes(), "bed": tmp_path / "bed.wav"}


def _script_writer(request: live.Request) -> live.Response:
    return live.Response(200, {"choices": [{"message": {"content": "Here you go:\n" + json.dumps(SCRIPT)}}],
                               "usage": {"prompt_tokens": 300, "completion_tokens": 200}})


def _media(assets: dict[str, bytes]):
    def post(request: media.MediaRequest) -> media.MediaResponse:
        if request.url.endswith("/img"):
            return media.MediaResponse(200, {"image": base64.b64encode(assets["png"]).decode()})
        return media.MediaResponse(200, None, assets["wav"])
    return post


@needs_ffmpeg
def test_a_brief_becomes_three_finished_renders_with_voice_music_and_captions(tmp_path: Path, services) -> None:
    made = studio.produce(
        "a 6-second hype video for Proofhouse", provider_id="ollama", model="llama3",
        visual_provider="local-images", visual_model="sdxl", voice_provider="local-voice", voice_model="tts",
        music_file=services["bed"], seconds=6, out_dir=tmp_path / "video", size_scale=0.1,
        text_transport=_script_writer, media_transport=_media(services),
    )
    assert made.stopped == "finished", made.stopped
    assert set(made.renders) == {"16x9", "9x16", "1x1"}
    failed = [c for c in made.checks if not c["ok"]]
    assert failed == [], failed
    sizes = {name: studio.probe(Path(path)) for name, path in made.renders.items()}
    assert (sizes["16x9"]["width"], sizes["16x9"]["height"]) == (192, 108)
    assert (sizes["9x16"]["width"], sizes["9x16"]["height"]) == (108, 192)
    assert all(abs(s["seconds"] - 6) <= 1 and s["audio"] for s in sizes.values())
    srt = (tmp_path / "video" / "captions.srt").read_text(encoding="utf-8")
    assert "00:00:02,000 --> 00:00:04,000\nPick any model" in srt
    record = json.loads((tmp_path / "video" / "studio.json").read_text(encoding="utf-8"))
    assert record["title"] == "Proofhouse launch" and len(record["shots"]) == 3 and record["ffmpeg"]
    assert sorted(p.name for p in (tmp_path / "video" / "shots").iterdir()) == ["shot-01.png", "shot-02.png", "shot-03.png"]


@needs_ffmpeg
def test_a_relative_output_folder_works(tmp_path: Path, services, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    made = studio.produce("x", provider_id="ollama", model="m", visual_provider="local-images", visual_model="m",
                          seconds=6, formats=("1x1",), out_dir=Path("relative-out"), size_scale=0.1,
                          text_transport=_script_writer, media_transport=_media(services))
    assert made.stopped == "finished" and Path(made.renders["1x1"]).is_file()


@needs_ffmpeg
def test_one_spending_limit_covers_the_whole_video(tmp_path: Path, services, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAL_KEY", "k")
    assert cli.main(["media", "price", "fal", "*", "--usd", "0.40"]) == 0
    calls: list[str] = []

    def paid(request: media.MediaRequest) -> media.MediaResponse:
        calls.append(request.url)
        return media.MediaResponse(200, {"request_id": "1", "status_url": "https://queue.fal.run/s", "response_url": "https://queue.fal.run/r"})

    made = studio.produce(
        "x", provider_id="ollama", model="llama3", visual_provider="fal", visual_model="fal-ai/model",
        seconds=6, out_dir=tmp_path / "v", max_cost_usd="1.00", size_scale=0.1,
        text_transport=_script_writer, media_transport=paid,
        media_get=lambda url, headers: media.MediaResponse(200, {"status": "FAILED"}),
    )
    assert made.renders == {} and len(calls) <= 2  # at most 2 x $0.40 fit under $1.00; the job failures stop it
    assert "fal" in made.stopped or "spending limit" in made.stopped


def test_a_paid_video_needs_one_limit_and_ffmpeg_formats_are_checked(tmp_path: Path) -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg not installed")
    with pytest.raises(studio.StudioError):
        studio.produce("x", provider_id="openai", model="m", visual_provider="fal", visual_model="m", out_dir=tmp_path / "a")
    with pytest.raises(studio.StudioError):
        studio.produce("x", provider_id="ollama", model="m", visual_provider="fal", visual_model="m", formats=("4x3",),
                       max_cost_usd="1", out_dir=tmp_path / "b")


def test_the_plan_is_stretched_to_the_asked_length_and_captions_are_timed() -> None:
    title, voiceover, music, shots = studio.plan_from({"shots": [{"seconds": 2, "visual": "a", "caption": "one"},
                                                                {"seconds": 2, "visual": "b", "caption": "two"}]}, 20)
    assert sum(s.seconds for s in shots) == 20
    assert studio.srt(shots).startswith("1\n00:00:00,000 --> 00:00:10,000\none\n")
    with pytest.raises(studio.StudioError):
        studio.plan_from({"shots": []}, 10)
