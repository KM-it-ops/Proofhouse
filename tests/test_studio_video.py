"""The video production line end to end: script, shots, voice-over, music, edit, captions, three renders, checks."""
from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import proofhouse
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
    assert record["proofhouse_version"] == proofhouse.__version__
    assert sorted(p.name for p in (tmp_path / "video" / "shots").iterdir()) == ["shot-01.png", "shot-02.png", "shot-03.png"]


@needs_ffmpeg
def test_a_voice_longer_than_the_film_is_reported_not_silently_cut(tmp_path: Path, services) -> None:
    for name in ("long", "fits", "silent"):
        (tmp_path / name).mkdir()
    shots =[studio.Shot(2, "a", "one", str(tmp_path / "frame.png")), studio.Shot(2, "b", "two", str(tmp_path / "frame.png"))]
    made = studio.assemble(tmp_path / "long", shots, visual_kind="image", formats=("1x1",), size_scale=0.1,
                           voice_file=str(tmp_path / "voice.wav"))  # the voice is 5 s, the film 4 s
    check = next(c for c in made.checks if c["check"] == "voice fits the film")
    assert check["ok"] is False
    assert "5.0s of voice" in check["detail"] and "4s film" in check["detail"] and "last 1.0s" in check["detail"]
    fits = studio.assemble(tmp_path / "fits", shots + [studio.Shot(2, "c", "three", str(tmp_path / "frame.png"))],
                           visual_kind="image", formats=("1x1",), size_scale=0.1, voice_file=str(tmp_path / "voice.wav"))
    assert next(c for c in fits.checks if c["check"] == "voice fits the film")["ok"] is True
    silent = studio.assemble(tmp_path / "silent", shots, visual_kind="image", formats=("1x1",), size_scale=0.1)
    assert not [c for c in silent.checks if c["check"] == "voice fits the film"]


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


def test_caption_size_follows_the_short_side_of_each_format_on_the_288_line_grid() -> None:
    assert studio.caption_style(studio.FORMATS["16x9"]) == "Fontsize=20.2,Outline=1.7,Shadow=1,MarginV=40"
    assert studio.caption_style(studio.FORMATS["1x1"]) == "Fontsize=20.2,Outline=1.7,Shadow=1,MarginV=40"
    # tall frame: same short side, but the 288-line grid is stretched over 1920 lines, so the text is smaller on the grid
    assert studio.caption_style(studio.FORMATS["9x16"]) == "Fontsize=11.3,Outline=1.5,Shadow=1,MarginV=40"


def test_caption_size_depends_on_the_frame_and_the_outline_never_goes_below_its_floor() -> None:
    def fields(size: tuple[int, int]) -> dict[str, str]:
        return dict(part.split("=") for part in studio.caption_style(size).split(","))

    tall, wide, small = fields((1080, 1920)), fields((1920, 1080)), fields((192, 108))
    assert float(tall["Fontsize"]) < float(wide["Fontsize"])
    assert small["Fontsize"] == wide["Fontsize"]  # a scaled render keeps the same text size on the grid
    assert float(tall["Outline"]) == 1.5


def test_the_final_render_command_uses_the_caption_style_of_its_own_frame() -> None:
    wide = studio.final_command(Path("j.mp4"), None, None, 6, True, Path("o.mp4"), (1920, 1080))
    tall = studio.final_command(Path("j.mp4"), None, None, 6, True, Path("o.mp4"), (1080, 1920))
    default = studio.final_command(Path("j.mp4"), None, None, 6, True, Path("o.mp4"))
    assert f"force_style='{studio.caption_style((1920, 1080))}'" in wide[wide.index("-filter_complex") + 1]
    assert f"force_style='{studio.caption_style((1080, 1920))}'" in tall[tall.index("-filter_complex") + 1]
    assert default == wide
    assert "-filter_complex" not in studio.final_command(Path("j.mp4"), None, None, 6, False, Path("o.mp4"))


def test_the_plan_is_stretched_to_the_asked_length_and_captions_are_timed() -> None:
    title, voiceover, music, shots = studio.plan_from({"shots": [{"seconds": 2, "visual": "a", "caption": "one"},
                                                                {"seconds": 2, "visual": "b", "caption": "two"}]}, 20)
    assert sum(s.seconds for s in shots) == 20
    assert studio.srt(shots).startswith("1\n00:00:00,000 --> 00:00:10,000\none\n")
    with pytest.raises(studio.StudioError):
        studio.plan_from({"shots": []}, 10)


def _colour_at(path: Path, seconds: float) -> tuple[int, int, int]:
    run = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(seconds), "-i", str(path), "-frames:v", "1",
                          "-vf", "scale=1:1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    return run.stdout[0], run.stdout[1], run.stdout[2]


def _band_level(path: Path, start: float, length: float, hertz: int) -> float:
    run = subprocess.run(["ffmpeg", "-nostats", "-ss", str(start), "-t", str(length), "-i", str(path), "-af",
                          f"bandpass=f={hertz}:width_type=h:w=40,volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True, check=True)
    return float(re.search(r"mean_volume: (-?[\d.]+) dB", run.stderr).group(1))


def _loudness(path: Path) -> float:
    run = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True, check=True)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", run.stderr)[-1])


@needs_ffmpeg
def test_shots_dissolve_into_each_other_and_the_film_fades_in_and_out_of_black(tmp_path: Path) -> None:
    _ffmpeg("-f", "lavfi", "-i", "color=c=0xcc2222:s=320x180", "-frames:v", "1", str(tmp_path / "red.png"))
    _ffmpeg("-f", "lavfi", "-i", "color=c=0x2222cc:s=320x180", "-frames:v", "1", str(tmp_path / "blue.png"))
    shots = [studio.Shot(2, "a", "one", str(tmp_path / "red.png")), studio.Shot(2, "b", "two", str(tmp_path / "blue.png"))]
    (tmp_path / "out").mkdir()
    made = studio.assemble(tmp_path / "out", shots, visual_kind="image", formats=("1x1",), size_scale=0.1)
    assert made.stopped == "finished", made.stopped
    film = Path(made.renders["1x1"])
    assert studio.probe(film)["seconds"] == pytest.approx(4, abs=0.15)
    assert sum(_colour_at(film, 0.0)) < 120  # starts from black
    red, blue = _colour_at(film, 1.2), _colour_at(film, 2.8)
    assert red[0] > 150 and red[2] < 80 and blue[2] > 150 and blue[0] < 80
    mixed = _colour_at(film, 1.8)  # inside the dissolve that ends at the cut
    assert mixed[0] > 70 and mixed[2] > 70, mixed
    assert sum(_colour_at(film, 3.95)) < 150  # ends in black
    assert all(c["ok"] for c in made.checks), made.checks


@needs_ffmpeg
def test_one_shot_has_no_dissolve_and_very_short_shots_still_render_at_the_full_length(tmp_path: Path) -> None:
    _ffmpeg("-f", "lavfi", "-i", "color=c=0xcc2222:s=320x180", "-frames:v", "1", str(tmp_path / "red.png"))
    (tmp_path / "one").mkdir()
    (tmp_path / "four").mkdir()
    one = studio.assemble(tmp_path / "one", [studio.Shot(3, "a", "", str(tmp_path / "red.png"))], visual_kind="image",
                          formats=("1x1",), size_scale=0.1)
    assert one.stopped == "finished" and studio.probe(Path(one.renders["1x1"]))["seconds"] == pytest.approx(3, abs=0.15)
    quick = [studio.Shot(1, "a", "", str(tmp_path / "red.png")) for _ in range(4)]
    four = studio.assemble(tmp_path / "four", quick, visual_kind="image", formats=("1x1",), size_scale=0.1)
    assert four.stopped == "finished" and studio.probe(Path(four.renders["1x1"]))["seconds"] == pytest.approx(4, abs=0.15)


@needs_ffmpeg
def test_music_dips_under_the_voice_and_the_mix_is_brought_to_a_normal_listening_level(tmp_path: Path) -> None:
    _ffmpeg("-f", "lavfi", "-i", "color=c=0x2255aa:s=320x180", "-frames:v", "1", str(tmp_path / "frame.png"))
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-af", "adelay=3000|3000", str(tmp_path / "voice.wav"))
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=220:duration=8", str(tmp_path / "music.wav"))
    shots = [studio.Shot(2, "a", "", str(tmp_path / "frame.png")) for _ in range(3)]  # a 6 s film; the voice speaks in its second half
    (tmp_path / "out").mkdir()
    made = studio.assemble(tmp_path / "out", shots, visual_kind="image", formats=("1x1",), size_scale=0.1,
                           voice_file=str(tmp_path / "voice.wav"), music_file=str(tmp_path / "music.wav"))
    assert made.stopped == "finished" and all(c["ok"] for c in made.checks), made.checks
    film = Path(made.renders["1x1"])
    alone, under_voice = _band_level(film, 1.0, 1.8, 220), _band_level(film, 3.6, 1.5, 220)
    assert under_voice < alone - 3, (alone, under_voice)
    assert abs(_loudness(film) - -16) <= 3


def test_the_final_command_cleans_the_voice_ducks_the_music_and_fades_in_and_out() -> None:
    both = studio.final_command(Path("j.mp4"), Path("v.wav"), Path("m.wav"), 30, False, Path("o.mp4"))
    graph = both[both.index("-filter_complex") + 1]
    assert "highpass" in graph and "sidechaincompress" in graph and "loudnorm" in graph and "afade=t=out" in graph
    assert "fade=t=in" in graph and "fade=t=out" in graph
    music_only = studio.final_command(Path("j.mp4"), None, Path("m.wav"), 30, False, Path("o.mp4"))
    assert "sidechaincompress" not in music_only[music_only.index("-filter_complex") + 1]
    silent = studio.final_command(Path("j.mp4"), None, None, 30, False, Path("o.mp4"))
    assert "-filter_complex" not in silent and "fade=t=in" in silent[silent.index("-vf") + 1]
