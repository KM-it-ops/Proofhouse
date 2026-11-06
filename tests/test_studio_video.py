"""The video production line end to end: script, shots, voice-over, music, edit, captions, three renders, checks."""
from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import sys
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
    _ffmpeg("-f", "lavfi", "-i", "testsrc2=s=320x180", "-frames:v", "1", str(tmp_path / "frame.png"))  # a picture with detail, as a real shot has
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
def test_a_voice_longer_than_the_film_lengthens_the_shots_instead_of_being_cut(tmp_path: Path, services) -> None:
    for name in ("long", "fits", "silent"):
        (tmp_path / name).mkdir()
    shots = [studio.Shot(2, "a", "one two three four", str(tmp_path / "frame.png")),
             studio.Shot(2, "b", "five", str(tmp_path / "frame.png"))]
    made = studio.assemble(tmp_path / "long", shots, visual_kind="image", formats=("1x1",), size_scale=0.1,
                           voice_file=str(tmp_path / "voice.wav"))  # the voice is 5 s, the film 4 s
    check = next(c for c in made.checks if c["check"] == "voice fits the film")
    assert check["ok"] is True
    assert "5.0s of voice" in check["detail"] and "lengthened from 4s to 6s" in check["detail"]
    assert [s.seconds for s in shots] == [4, 2]  # the extra time goes where the words are densest
    assert studio.probe(Path(made.renders["1x1"]))["seconds"] == pytest.approx(6, abs=0.3)
    assert "00:00:04,000 --> 00:00:06,000\nfive" in (tmp_path / "long" / "captions.srt").read_text(encoding="utf-8")
    shots = [studio.Shot(2, "a", "one", str(tmp_path / "frame.png")), studio.Shot(2, "b", "two", str(tmp_path / "frame.png"))]
    fits = studio.assemble(tmp_path / "fits", shots + [studio.Shot(2, "c", "three", str(tmp_path / "frame.png"))],
                           visual_kind="image", formats=("1x1",), size_scale=0.1, voice_file=str(tmp_path / "voice.wav"))
    assert next(c for c in fits.checks if c["check"] == "voice fits the film")["ok"] is True
    silent = studio.assemble(tmp_path / "silent", shots, visual_kind="image", formats=("1x1",), size_scale=0.1)
    assert not [c for c in silent.checks if c["check"] == "voice fits the film"]


@needs_ffmpeg
def test_a_render_that_fails_its_checks_is_set_aside_not_left_looking_finished(tmp_path: Path, services,
                                                                                monkeypatch: pytest.MonkeyPatch) -> None:
    real = studio._render_checks

    def broken(name, *args, **kwargs):  # noqa: ANN001, ANN202
        checks = real(name, *args, **kwargs)
        return [dict(c, ok=False) if name == "1x1" and c["check"] == "length" else c for c in checks]

    monkeypatch.setattr(studio, "_render_checks", broken)
    (tmp_path / "out").mkdir()
    shots = [studio.Shot(2, "a", "one", str(tmp_path / "frame.png"))]
    made = studio.assemble(tmp_path / "out", shots, visual_kind="image", formats=("1x1", "16x9"), size_scale=0.1)
    assert Path(made.renders["1x1"]).name == "video-1x1.failed.mp4" and Path(made.renders["1x1"]).is_file()
    assert not (tmp_path / "out" / "video-1x1.mp4").exists()
    assert Path(made.renders["16x9"]).name == "video-16x9.mp4"  # its checks passed


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


@needs_ffmpeg
def test_a_zero_limit_runs_free_calls_and_the_spend_gate_refuses_the_paid_one(tmp_path: Path, services,
                                                                          monkeypatch: pytest.MonkeyPatch) -> None:
    assert studio._Budget("0").next_limit() == "0"  # nothing left still asks the gate; it does not stop first
    monkeypatch.setenv("FAL_KEY", "k")
    assert cli.main(["media", "price", "fal", "*", "--usd", "0.40"]) == 0
    calls: list[str] = []

    def paid(request: media.MediaRequest) -> media.MediaResponse:
        calls.append(request.url)
        return media.MediaResponse(200, {})

    made = studio.produce(
        "x", provider_id="ollama", model="llama3", visual_provider="fal", visual_model="fal-ai/model",
        seconds=6, out_dir=tmp_path / "v", max_cost_usd="0", size_scale=0.1,
        text_transport=_script_writer, media_transport=paid, media_get=lambda url, headers: media.MediaResponse(200, {}),
    )
    assert calls == [] and made.renders == {} and made.stopped == "spending limit reached"
    assert made.calls[0]["role"] == "script" and made.calls[0]["status"] == "success"  # the free script was written

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
    # red and blue clips with a darker square swinging across them: two still pictures would be a slideshow
    for name, back, square in (("red", "0xcc2222", "0x881111"), ("blue", "0x2222cc", "0x111188")):
        _ffmpeg("-filter_complex", f"color=c={back}:s=320x180:r=25:d=3[b];color=c={square}:s=48x48:r=25:d=3[s];"
                f"[b][s]overlay=x='136+90*sin(t*5)':y=66", "-t", "3", "-pix_fmt", "yuv420p", str(tmp_path / f"{name}.mp4"))
    shots = [studio.Shot(2, "a", "one", str(tmp_path / "red.mp4")), studio.Shot(2, "b", "two", str(tmp_path / "blue.mp4"))]
    (tmp_path / "out").mkdir()
    made = studio.assemble(tmp_path / "out", shots, visual_kind="video", formats=("1x1",), size_scale=0.1)
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
    _ffmpeg("-f", "lavfi", "-i", "testsrc2=s=320x180", "-frames:v", "1", str(tmp_path / "frame.png"))
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


def _textured(path: Path) -> None:
    _ffmpeg("-f", "lavfi", "-i", "testsrc2=s=320x180", "-frames:v", "1", str(path))


def test_a_captured_still_gets_a_different_camera_move_on_each_neighbouring_shot() -> None:
    moves = {" ".join(studio.shot_command(Path("c.png"), "still", 6, (1920, 1080), Path("o.mp4"), variant=v)) for v in range(4)}
    assert len(moves) == 4 and all("zoompan" in m and "overlay" in m for m in moves)


def test_a_generated_image_keeps_moving_for_the_whole_shot() -> None:
    cmd = " ".join(studio.shot_command(Path("g.png"), "image", 9, (1920, 1080), Path("o.mp4")))
    assert "on/269" in cmd and "min(zoom+" not in cmd  # the old push-in was capped after five seconds and then froze


def test_titles_are_timed_to_their_shots_and_slide_in_and_out() -> None:
    shots = [studio.Shot(4, "a", "Any model", "a.png"), studio.Shot(5, "b", "", "b.png"), studio.Shot(6, "c", "Every version kept", "c.png")]
    ass = studio.title_track(shots, (1920, 1080), 0.5)
    assert "PlayResX: 1920" in ass and "PlayResY: 1080" in ass
    lines = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
    assert len(lines) == 2 and "Any model" in lines[0] and "Every version kept" in lines[1]  # a shot with no words gets no title
    assert "\\move(" in lines[0] and "\\fad(" in lines[0]
    assert lines[0].split(",")[1] == "0:00:00.60" and lines[0].split(",")[2] == "0:00:03.50"
    assert lines[1].split(",")[1] == "0:00:09.60" and lines[1].split(",")[2] == "0:00:14.50"  # in after the dissolve, out before the next


def test_titles_cannot_break_the_subtitle_file() -> None:
    ass = studio.title_track([studio.Shot(5, "a", "{\\an9}One, two\nthree", "a.png")], (1920, 1080), 0.5)
    text = next(line for line in ass.splitlines() if line.startswith("Dialogue:"))
    assert "{\\an9}" not in text and "\n" not in text.split(",", 9)[-1] and "One, two" in text


def test_the_final_command_burns_the_titles_only_when_asked() -> None:
    on = studio.final_command(Path("j.mp4"), None, None, 6, False, Path("o.mp4"), titles=True)
    assert "subtitles=titles.ass" in " ".join(on)
    assert "titles.ass" not in " ".join(studio.final_command(Path("j.mp4"), None, None, 6, False, Path("o.mp4")))


@needs_ffmpeg
def test_a_film_of_captures_keeps_moving_and_carries_its_titles(tmp_path: Path) -> None:
    _textured(tmp_path / "card.png")
    shots = [studio.Shot(6, "a", "First words", str(tmp_path / "card.png"), source="capture"),
             studio.Shot(6, "b", "Second words", str(tmp_path / "card.png"), source="capture")]
    (tmp_path / "out").mkdir()
    made = studio.assemble(tmp_path / "out", shots, visual_kind="mixed", formats=("16x9",), size_scale=0.2, captions=False)
    assert made.stopped == "finished", made.stopped
    moving = next(c for c in made.checks if c["check"] == "picture keeps moving")
    assert moving["ok"] is True, moving
    assert "First words" in (tmp_path / "out" / "titles.ass").read_text(encoding="utf-8")
    assert all(c["ok"] for c in made.checks), made.checks
    assert max((d for _, d in studio.frozen_stretches(Path(made.renders["16x9"]))), default=0.0) < studio.MAX_HOLD


@needs_ffmpeg
def test_titles_are_off_when_captions_are_burned_in_and_can_be_turned_off(tmp_path: Path) -> None:
    _textured(tmp_path / "card.png")
    shots = [studio.Shot(4, "a", "Words", str(tmp_path / "card.png"), source="capture")]
    for name, extra in (("captioned", {}), ("plain", {"captions": False, "titles": False})):
        (tmp_path / name).mkdir()
        studio.assemble(tmp_path / name, shots, visual_kind="mixed", formats=("1x1",), size_scale=0.1, **extra)
        assert not (tmp_path / name / "titles.ass").exists(), name


@needs_ffmpeg
def test_a_film_whose_picture_freezes_for_seconds_fails_its_check(tmp_path: Path) -> None:
    _ffmpeg("-f", "lavfi", "-i", "color=c=0x2255aa:s=320x180:d=6:r=30", "-pix_fmt", "yuv420p", str(tmp_path / "still.mp4"))
    (tmp_path / "out").mkdir()
    made = studio.assemble(tmp_path / "out", [studio.Shot(6, "a", "", str(tmp_path / "still.mp4"))], visual_kind="video",
                           formats=("1x1",), size_scale=0.1)
    check = next(c for c in made.checks if c["check"] == "picture keeps moving")
    assert check["ok"] is False and "holds still" in check["detail"], check


# ---------------------------------------------------------------- storyboard films written by the model

BEATS = {
    "title": "Proofhouse launch", "music": "upbeat electronic, 120 bpm",
    "beats": [
        {"say": "Say what you want.", "base": {"prompt": "a glowing workshop at night"},
         "layers": [{"kind": "title", "text": "Say what you want", "at": "phrase 1"}], "energy": "mid"},
        {"say": "Pick any model.", "base": {"prompt": "hands on a keyboard, neon light"},
         "layers": [{"kind": "chips", "items": ["any", "model"], "at": "start"}]},
        {"say": "Proofhouse makes it.", "base": {"prompt": "a finished product on a desk"},
         "layers": [{"kind": "lower_third", "title": "Proofhouse", "at": 0.3}]},
    ],
}


def _beats_writer(request: live.Request) -> live.Response:
    return live.Response(200, {"choices": [{"message": {"content": json.dumps(BEATS)}}],
                               "usage": {"prompt_tokens": 300, "completion_tokens": 200}})


@needs_ffmpeg
def test_a_storyboard_from_the_model_is_voiced_phrase_by_phrase_and_rendered(tmp_path: Path, services) -> None:
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=1.2", str(tmp_path / "phrase.wav"))
    assets = {**services, "wav": (tmp_path / "phrase.wav").read_bytes()}
    made = studio.produce(
        "a hype video for Proofhouse", provider_id="ollama", model="llama3",
        visual_provider="local-images", visual_model="sdxl", voice_provider="local-voice", voice_model="tts",
        music_file=services["bed"], seconds=6, formats=("16x9", "9x16"), out_dir=tmp_path / "video", size_scale=0.1,
        text_transport=_beats_writer, media_transport=_media(assets),
    )
    assert made.stopped == "finished", made.stopped
    assert set(made.renders) == {"16x9", "9x16"}
    failed = [c for c in made.checks if not c["ok"]]
    assert failed == [], failed
    assert {"real footage share", "captions match the script", "voice fits the film"} <= {c["check"] for c in made.checks}
    fits = next(c for c in made.checks if c["check"] == "voice fits the film")
    assert "the last word ends at" in fits["detail"]
    folder = tmp_path / "video"
    assert sorted(p.name for p in (folder / "shots").iterdir()) == ["beat-01.png", "beat-02.png", "beat-03.png"]
    assert sorted(p.name for p in (folder / "voice").iterdir()) == ["beat01-01.wav", "beat02-01.wav", "beat03-01.wav"]
    record = json.loads((folder / "studio.json").read_text(encoding="utf-8"))
    assert [b["beat"] for b in record["beats"]] == [1, 2, 3]
    assert record["beats"][1]["phrases"][0] == {"text": "Pick any model.", "start": pytest.approx(record["beats"][1]["phrases"][0]["start"]),
                                                "seconds": pytest.approx(1.2, abs=0.05), "file": "voice/beat02-01.wav"}
    starts = [b["start"] for b in record["beats"]]
    assert starts == sorted(starts) and starts[0] == 0
    script = json.loads((folder / "script.json").read_text(encoding="utf-8"))  # a re-render needs no voice service
    assert all("say" not in row for row in script["beats"])
    assert script["beats"][0]["phrases"] == [{"text": "Say what you want.", "file": "voice/beat01-01.wav"}]
    assert script["beats"][0]["base"] == {"kind": "image", "file": "shots/beat-01.png"}
    assert "Pick any model." in (folder / "captions.srt").read_text(encoding="utf-8")


@needs_ffmpeg
def test_a_storyboard_with_words_but_no_voice_service_stops_before_spending(tmp_path: Path, services) -> None:
    calls: list[str] = []

    def post(request: media.MediaRequest) -> media.MediaResponse:
        calls.append(request.url)
        return _media(services)(request)

    made = studio.produce("x", provider_id="ollama", model="llama3", visual_provider="local-images", visual_model="sdxl",
                          seconds=6, formats=("1x1",), out_dir=tmp_path / "v", size_scale=0.1,
                          text_transport=_beats_writer, media_transport=post)
    assert "voice service" in made.stopped and calls == [] and made.renders == {}


@needs_ffmpeg
def test_a_storyboard_layer_the_engine_cannot_draw_is_sent_back_before_any_picture_is_made(tmp_path: Path, services) -> None:
    bad = {**BEATS, "beats": [{**BEATS["beats"][0], "layers": [{"kind": "hologram", "at": 0}]}]}
    asked: list[str] = []
    calls: list[int] = []  # how many times the writer had been asked when each picture or voice was made

    def post(request: media.MediaRequest) -> media.MediaResponse:
        calls.append(len(asked))
        return _media(services)(request)

    made = studio.produce("x", provider_id="ollama", model="llama3", visual_provider="local-images", visual_model="sdxl",
                          voice_provider="local-voice", voice_model="tts", seconds=6, formats=("1x1",),
                          out_dir=tmp_path / "v", size_scale=0.1, media_transport=post,
                          text_transport=_writer_of(bad, asked=asked))
    assert len(asked) == 1 + studio.SCRIPT_FIXES and all("hologram" in a for a in asked[1:])
    assert calls and min(calls) == len(asked)  # nothing was made until the writer had every chance to fix it
    assert made.stopped == "finished", made.stopped
    assert "hologram" not in (tmp_path / "v" / "script.json").read_text(encoding="utf-8")
    left = next(c for c in made.checks if c["check"] == "unreadable parts dropped")["detail"]
    assert "beat 1 layer 1 (hologram) left out" in left, left


def test_a_storyboard_may_only_show_footage_from_the_fact_sheet() -> None:
    facts = {"product": "Proofhouse", "commands": [{"id": "help", "argv": ["proofhouse", "--help"]}]}
    rows = studio.beats_from({"beats": [{"say": "Look.", "base": {"ref": "help"}}]}, facts)
    assert rows[0]["base"] == {"kind": "capture", "ref": "help"}
    with pytest.raises(studio.StudioError, match="not in the fact sheet"):
        studio.beats_from({"beats": [{"say": "Look.", "base": {"ref": "secret"}}]}, facts)
    with pytest.raises(studio.StudioError, match="no beats"):
        studio.beats_from({"beats": []}, None)


# ---------------------------------------------------------------- something happens on screen

DEMO = Path(__file__).resolve().parents[1] / "docs" / "assets" / "proofhouse-demo.mp4"


@needs_ffmpeg
def test_the_readme_hype_film_counts_as_something_happening_all_the_way_through() -> None:
    # measured: its longest pause is 1.3 s (from 33.7 s) and something happens in 98% of its seconds. A storyboard
    # cut from stills with a slow camera measured 7.2 s and 61%, and a still film read over a voice 20.1 s and 11%:
    # both rightly fail.
    activity = studio.picture_activity(DEMO)
    assert activity["longest_quiet"] == pytest.approx(1.3, abs=0.2) and activity["longest_quiet"] <= studio.MAX_QUIET
    assert activity["lively_share"] == pytest.approx(0.98, abs=0.02) and activity["lively_share"] >= studio.MIN_LIVELY


@needs_ffmpeg
def test_a_slow_camera_over_a_still_and_a_long_hold_after_motion_count_as_nothing_happening(tmp_path: Path) -> None:
    still = tmp_path / "still.png"
    _ffmpeg("-f", "lavfi", "-i", "testsrc2=s=640x360", "-frames:v", "1", str(still))
    _ffmpeg("-loop", "1", "-i", str(still), "-vf", "zoompan=z='1+0.0006*on':d=200:s=320x180:fps=25", "-t", "8",
            "-pix_fmt", "yuv420p", str(tmp_path / "push.mp4"))
    push = studio.picture_activity(tmp_path / "push.mp4")  # measured 5.9 s and 23%
    assert push["longest_quiet"] > studio.MAX_QUIET and push["lively_share"] < studio.MIN_LIVELY
    _ffmpeg("-f", "lavfi", "-t", "4", "-i", "testsrc2=s=640x360:r=25", "-loop", "1", "-t", "4", "-i", str(still),
            "-filter_complex", "[1:v]fps=25[hold];[0:v][hold]concat=n=2:v=1[v]", "-map", "[v]", "-pix_fmt", "yuv420p",
            str(tmp_path / "hold.mp4"))
    hold = studio.picture_activity(tmp_path / "hold.mp4")  # measured 3.9 s from 4.0 s, and 57%
    assert hold["longest_quiet"] == pytest.approx(3.9, abs=0.2) and hold["quiet_from"] == pytest.approx(4.0, abs=0.2)
    assert hold["lively_share"] < studio.MIN_LIVELY


@needs_ffmpeg
def test_a_film_that_cannot_be_read_never_counts_as_lively(tmp_path: Path) -> None:
    (tmp_path / "broken.mp4").write_bytes(b"not a film")
    activity = studio.picture_activity(tmp_path / "broken.mp4")
    assert activity["longest_quiet"] > studio.MAX_QUIET and activity["lively_share"] == 0.0


@needs_ffmpeg
def test_a_film_cut_from_stills_fails_the_something_happens_checks(tmp_path: Path) -> None:
    for name, colour in (("red", "0xcc2222"), ("blue", "0x2222cc")):
        _ffmpeg("-f", "lavfi", "-i", f"color=c={colour}:s=320x180", "-frames:v", "1", str(tmp_path / f"{name}.png"))
    shots = [studio.Shot(4, "a", "one", str(tmp_path / "red.png")), studio.Shot(4, "b", "two", str(tmp_path / "blue.png"))]
    (tmp_path / "out").mkdir()
    made = studio.assemble(tmp_path / "out", shots, visual_kind="image", formats=("1x1",), size_scale=0.1)
    failed = {c["check"]: c["detail"] for c in made.checks if not c["ok"]}
    assert "something happens" in failed and "picture changes every second" in failed, made.checks
    assert "nothing new on screen for" in failed["something happens"]


@needs_ffmpeg
def test_a_script_reply_that_cannot_be_read_is_kept_beside_the_record(tmp_path: Path, services) -> None:
    def rambler(request: live.Request) -> live.Response:
        return live.Response(200, {"choices": [{"message": {"content": "Sure! {title: 'no quotes', beats: [,]}"}}],
                                   "usage": {"prompt_tokens": 30, "completion_tokens": 20}})

    made = studio.produce("x", provider_id="ollama", model="m", visual_provider="local-images", visual_model="m",
                          seconds=6, out_dir=tmp_path / "v", size_scale=0.1, text_transport=rambler,
                          media_transport=_media(services))
    assert made.renders == {} and "script-reply.txt" in made.stopped
    assert (tmp_path / "v" / "script-reply.txt").read_text(encoding="utf-8").startswith("Sure! {title")


@needs_ffmpeg
def test_a_script_cut_off_by_a_small_window_says_so_and_how_to_give_it_room(tmp_path: Path, services) -> None:
    asked: list[str] = []

    def cut_short(request: live.Request) -> live.Response:
        asked.append(request.body["messages"][-1]["content"])
        return live.Response(200, {"choices": [{"message": {"content": '{"title": "T", "beats": [{"say": "It makes'},
                                                "finish_reason": "length"}]})

    made = studio.produce("x", provider_id="ollama", model="m", visual_provider="local-images", visual_model="m",
                          seconds=6, out_dir=tmp_path / "v", size_scale=0.1, text_transport=cut_short,
                          media_transport=_media(services))
    assert made.renders == {} and "cut off" in made.stopped and "OLLAMA_CONTEXT_LENGTH" in made.stopped, made.stopped
    assert len(asked) == 1 + studio.SCRIPT_FIXES and all("cut off before it ended" in a for a in asked[1:])


@needs_ffmpeg
def test_a_fix_sends_the_writers_reply_back_without_its_indents(tmp_path: Path, services) -> None:
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=1.0", str(tmp_path / "phrase.wav"))
    rambling = {**BEATS, "beats": [{**row, "say": "Say what you want, in as many words as you like, and then some more. " * 3}
                                   for row in BEATS["beats"]]}
    asked: list[str] = []
    studio.produce("a hype video", provider_id="ollama", model="llama3", visual_provider="local-images",
                   visual_model="sdxl", voice_provider="local-voice", voice_model="tts", music_file=services["bed"],
                   seconds=6, formats=("1x1",), out_dir=tmp_path / "v", size_scale=0.1,
                   text_transport=_writer_of(json.dumps(rambling, indent=2), BEATS, asked=asked),
                   media_transport=_media({**services, "wav": (tmp_path / "phrase.wav").read_bytes()}))
    said = asked[1].split("YOUR REPLY WAS:\n", 1)[1]
    assert said == json.dumps(rambling, ensure_ascii=False, separators=(",", ":"))[:6000]


# ---------------------------------------------------------------- the film fits the asked length

def test_the_script_asks_for_beats_and_words_that_fit_the_asked_length() -> None:
    short, long = studio.script_budget(10), studio.script_budget(60)
    assert short["most"] <= 4 and short["words"] <= 18
    assert long["fewest"] > short["most"] and long["words"] > 4 * short["words"]
    assert studio.script_budget(10, rate=1.5)["words"] < short["words"]
    prompt = studio.script_prompt("a hype film", 10)
    assert f"{short['words']} words in all at most" in prompt and f"{short['fewest']} to {short['most']} beats" in prompt
    assert "5 to 10 beats" not in prompt


def _writer_of(*replies: dict | str, asked: list[str]):  # noqa: ANN202
    def write(request: live.Request) -> live.Response:
        asked.append(request.body["messages"][-1]["content"])
        reply = replies[min(len(asked), len(replies)) - 1]
        text = reply if isinstance(reply, str) else json.dumps(reply)
        return live.Response(200, {"choices": [{"message": {"content": text}}],
                                   "usage": {"prompt_tokens": 30, "completion_tokens": 20}})
    return write


@needs_ffmpeg
def test_a_script_too_long_for_the_film_is_sent_back_before_anything_is_spoken(tmp_path: Path, services) -> None:
    rambling = {**BEATS, "beats": [{**row, "say": "Say what you want, in as many words as you like, and then some more. " * 3}
                                   for row in BEATS["beats"]]}
    asked: list[str] = []
    spoken: list[str] = []

    def post(request: media.MediaRequest) -> media.MediaResponse:
        spoken.append(request.url)
        return _media({**services, "wav": (tmp_path / "phrase.wav").read_bytes()})(request)

    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=1.2", str(tmp_path / "phrase.wav"))
    made = studio.produce("a hype video", provider_id="ollama", model="llama3", visual_provider="local-images",
                          visual_model="sdxl", voice_provider="local-voice", voice_model="tts", music_file=services["bed"],
                          seconds=6, formats=("1x1",), out_dir=tmp_path / "v", size_scale=0.1,
                          text_transport=_writer_of(rambling, BEATS, asked=asked), media_transport=post)
    assert made.stopped == "finished", made.stopped
    assert [c["role"] for c in made.calls][:2] == ["script", "script fix"]
    assert len(asked) == 2 and "too long" in asked[1] and "Say what you want, in as many words" in asked[1]
    assert f"{studio.script_budget(6)['words']} words" in asked[1]
    assert len([u for u in spoken if u.endswith("/tts")]) == 3  # only the fixed script was spoken
    script = json.loads((tmp_path / "v" / "script.json").read_text(encoding="utf-8"))
    assert all("as many words" not in p["text"] for row in script["beats"] for p in row["phrases"])


@needs_ffmpeg
def test_a_script_too_long_once_spoken_is_sent_back_with_the_voice_s_own_pace(tmp_path: Path, services) -> None:
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=3", str(tmp_path / "slow.wav"))
    one = {**BEATS, "beats": BEATS["beats"][:1]}
    asked: list[str] = []
    made = studio.produce("a hype video", provider_id="ollama", model="llama3", visual_provider="local-images",
                          visual_model="sdxl", voice_provider="local-voice", voice_model="tts", music_file=services["bed"],
                          seconds=6, formats=("1x1",), out_dir=tmp_path / "v", size_scale=0.1,
                          text_transport=_writer_of(BEATS, one, asked=asked),
                          media_transport=_media({**services, "wav": (tmp_path / "slow.wav").read_bytes()}))
    assert made.stopped == "finished", made.stopped
    assert [c["role"] for c in made.calls if c["role"].startswith("script")] == ["script", "script fix"]
    assert "spoken by the chosen voice" in asked[1] and "1.1 words a second" in asked[1]
    folder = tmp_path / "v"
    assert sorted(p.name for p in (folder / "voice-too-long-1").iterdir()) == ["beat01-01.wav", "beat02-01.wav", "beat03-01.wav"]
    assert sorted(p.name for p in (folder / "voice").iterdir()) == ["beat01-01.wav"]
    fits = next(c for c in made.checks if c["check"] == "length matches the brief")
    assert fits["ok"] and "of the 6s asked" in fits["detail"], fits
    assert next(c for c in made.checks if c["check"] == "length")["ok"]


@needs_ffmpeg
def test_a_script_that_stays_too_long_keeps_its_opening_and_close_and_cuts_middle_beats_to_fit(
        tmp_path: Path, services) -> None:
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=1.5", str(tmp_path / "phrase.wav"))
    long = json.loads(json.dumps(BEATS))
    long["beats"].insert(2, {"say": "Watch it get better.", "base": {"prompt": "a chart climbing"}})
    long["beats"].insert(1, {"say": "Every version is kept.", "base": {"prompt": "a shelf of folders"}})
    asked: list[str] = []
    made = studio.produce("a hype video", provider_id="ollama", model="llama3", visual_provider="local-images",
                          visual_model="sdxl", voice_provider="local-voice", voice_model="tts", music_file=services["bed"],
                          seconds=6, formats=("1x1",), out_dir=tmp_path / "v", size_scale=0.1,
                          text_transport=_writer_of(long, asked=asked),
                          media_transport=_media({**services, "wav": (tmp_path / "phrase.wav").read_bytes()}))
    assert len(asked) == 1 + studio.SCRIPT_FIXES and all("too long" in a for a in asked[1:])  # every chance first
    assert made.stopped == "finished" and "1x1" in made.renders, made.stopped
    script = json.loads((tmp_path / "v" / "script.json").read_text(encoding="utf-8"))
    said = [row["phrases"][0]["text"] for row in script["beats"]]
    assert said[0] == long["beats"][0]["say"] and said[-1] == long["beats"][-1]["say"]  # the opening and the close
    assert 2 <= len(said) < len(long["beats"])
    assert next(c for c in made.checks if c["check"] == "length matches the brief")["ok"]
    cut = next(c for c in made.checks if c["check"] == "middle beats cut to fit")
    assert all(f"'{s}'" in cut["detail"] for row in long["beats"] if (s := row["say"]) not in said), cut
    shots = sorted(p.name for p in (tmp_path / "v" / "shots").iterdir())
    assert len([s for s in shots if s.endswith(".png")]) == len(said)  # no picture is made for a cut beat


@needs_ffmpeg
def test_a_script_that_stays_too_long_stops_before_any_picture_is_made(tmp_path: Path, services) -> None:
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=3", str(tmp_path / "slow.wav"))
    asked: list[str] = []
    pictures: list[str] = []

    def post(request: media.MediaRequest) -> media.MediaResponse:
        if request.url.endswith("/img"):
            pictures.append(request.url)
        return _media({**services, "wav": (tmp_path / "slow.wav").read_bytes()})(request)

    made = studio.produce("a hype video", provider_id="ollama", model="llama3", visual_provider="local-images",
                          visual_model="sdxl", voice_provider="local-voice", voice_model="tts", music_file=services["bed"],
                          seconds=6, formats=("1x1",), out_dir=tmp_path / "v", size_scale=0.1,
                          text_transport=_writer_of(BEATS, asked=asked), media_transport=post)
    assert len(asked) == 1 + studio.SCRIPT_FIXES and pictures == [] and made.renders == {}
    assert "too long" in made.stopped and "script-reply.txt" in made.stopped, made.stopped


@needs_ffmpeg
def test_a_timing_that_stays_unreadable_falls_back_to_the_default_instead_of_losing_the_film(tmp_path: Path, services) -> None:
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=1.0", str(tmp_path / "phrase.wav"))
    garbled = json.loads(json.dumps(BEATS))
    garbled["beats"][0]["layers"].append({"kind": "chips", "items": ["fast"], "at": "3:+"})
    garbled["beats"][1]["sounds"] = [{"kind": "whoosh", "at": "+/- 0.5 seconds of end::"}, {"kind": "hit", "at": "start"}]
    asked: list[str] = []
    made = studio.produce("a hype video", provider_id="ollama", model="llama3", visual_provider="local-images",
                          visual_model="sdxl", voice_provider="local-voice", voice_model="tts", music_file=services["bed"],
                          seconds=6, formats=("1x1",), out_dir=tmp_path / "v", size_scale=0.1,
                          text_transport=_writer_of(garbled, asked=asked),
                          media_transport=_media({**services, "wav": (tmp_path / "phrase.wav").read_bytes()}))
    assert len(asked) == 1 + studio.SCRIPT_FIXES  # the writer had every chance to fix them first
    assert made.stopped == "finished" and "1x1" in made.renders, made.stopped
    script = json.loads((tmp_path / "v" / "script.json").read_text(encoding="utf-8"))
    # the overlay and the sound stay; only their unreadable times are gone, so they play at the default moment
    assert script["beats"][0]["layers"] == [*BEATS["beats"][0]["layers"], {"kind": "chips", "items": ["fast"]}]
    assert script["beats"][1]["sounds"] == [{"kind": "whoosh"}, {"kind": "hit", "at": "start"}]
    untimed = next(c for c in made.checks if c["check"] == "unreadable parts dropped")
    assert "beat 1 layer 2" in untimed["detail"] and "beat 2 sound 1" in untimed["detail"], untimed


@needs_ffmpeg
def test_an_overlay_the_engine_cannot_draw_is_left_out_instead_of_losing_the_film(tmp_path: Path, services) -> None:
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=1.0", str(tmp_path / "phrase.wav"))
    slipped = json.loads(json.dumps(BEATS))
    slipped["beats"][0]["layers"].append({"kind": "card", "items": ["x"]})  # a kind the engine does not have
    slipped["beats"][1]["layers"].append({"text": "no kind"})
    slipped["beats"][2]["sounds"] = [{"kind": "boom"}, {"kind": "hit", "at": "start"}]
    asked: list[str] = []
    made = studio.produce("a hype video", provider_id="ollama", model="llama3", visual_provider="local-images",
                          visual_model="sdxl", voice_provider="local-voice", voice_model="tts", music_file=services["bed"],
                          seconds=6, formats=("1x1",), out_dir=tmp_path / "v", size_scale=0.1,
                          text_transport=_writer_of(slipped, asked=asked),
                          media_transport=_media({**services, "wav": (tmp_path / "phrase.wav").read_bytes()}))
    assert len(asked) == 1 + studio.SCRIPT_FIXES  # the writer had every chance to fix them first
    assert made.stopped == "finished" and "1x1" in made.renders, made.stopped
    script = json.loads((tmp_path / "v" / "script.json").read_text(encoding="utf-8"))
    assert script["beats"][0]["layers"] == BEATS["beats"][0]["layers"]  # everything that could be drawn stays
    assert script["beats"][1]["layers"] == BEATS["beats"][1]["layers"]
    assert script["beats"][2]["sounds"] == [{"kind": "hit", "at": "start"}]
    left = next(c for c in made.checks if c["check"] == "unreadable parts dropped")["detail"]
    assert "beat 1 layer" in left and "(card) left out" in left and "(no kind) left out" in left
    assert "beat 3 sound 1 (boom) left out" in left, left


@needs_ffmpeg
def test_a_pace_that_stays_unreadable_falls_back_to_the_default_instead_of_losing_the_film(tmp_path: Path, services) -> None:
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=1.0", str(tmp_path / "phrase.wav"))
    garbled = json.loads(json.dumps(BEATS))
    garbled["beats"][1]["energy"] = "low+"  # a small model's near miss, written again after every fix
    garbled["beats"][2]["cut"] = "zoomy"
    asked: list[str] = []
    made = studio.produce("a hype video", provider_id="ollama", model="llama3", visual_provider="local-images",
                          visual_model="sdxl", voice_provider="local-voice", voice_model="tts", music_file=services["bed"],
                          seconds=6, formats=("1x1",), out_dir=tmp_path / "v", size_scale=0.1,
                          text_transport=_writer_of(garbled, asked=asked),
                          media_transport=_media({**services, "wav": (tmp_path / "phrase.wav").read_bytes()}))
    assert len(asked) == 1 + studio.SCRIPT_FIXES  # the writer had every chance to fix them first
    assert made.stopped == "finished" and "1x1" in made.renders, made.stopped
    script = json.loads((tmp_path / "v" / "script.json").read_text(encoding="utf-8"))
    assert "energy" not in script["beats"][1] and "cut" not in script["beats"][2]  # the default pace plays instead
    assert script["beats"][1]["phrases"][0]["text"] == BEATS["beats"][1]["say"]  # and the beat itself is kept whole
    untimed = next(c for c in made.checks if c["check"] == "unreadable parts dropped")
    assert "beat 2 energy 'low+'" in untimed["detail"] and "beat 3 cut 'zoomy'" in untimed["detail"], untimed


@needs_ffmpeg
def test_stray_text_in_the_beats_is_named_to_the_writer_and_left_out_when_it_stays(tmp_path: Path, services) -> None:
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=1.0", str(tmp_path / "phrase.wav"))
    garbled = json.loads(json.dumps(BEATS))
    garbled["beats"] += ["layers': [{", "kind, "]  # what a small model's broken reply leaves after the last beat
    asked: list[str] = []
    made = studio.produce("a hype video", provider_id="ollama", model="llama3", visual_provider="local-images",
                          visual_model="sdxl", voice_provider="local-voice", voice_model="tts", music_file=services["bed"],
                          seconds=6, formats=("1x1",), out_dir=tmp_path / "v", size_scale=0.1,
                          text_transport=_writer_of(garbled, asked=asked),
                          media_transport=_media({**services, "wav": (tmp_path / "phrase.wav").read_bytes()}))
    fix = asked[1]
    n = len(BEATS["beats"])
    assert "no beats" not in fix and f"beat {n + 1}: " in fix and f"beat {n + 2}: " in fix and "not a beat" in fix
    assert len(asked) == 1 + studio.SCRIPT_FIXES and made.stopped == "finished", made.stopped
    script = json.loads((tmp_path / "v" / "script.json").read_text(encoding="utf-8"))
    assert len(script["beats"]) == n  # every real beat is kept; only the stray text is gone
    untimed = next(c for c in made.checks if c["check"] == "unreadable parts dropped")
    assert f"beat {n + 1} stray text" in untimed["detail"], untimed


@needs_ffmpeg
def test_the_script_writer_is_told_every_problem_at_once_so_one_fix_can_mend_them_all(tmp_path: Path, services) -> None:
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=1.0", str(tmp_path / "phrase.wav"))
    broken = json.loads(json.dumps(BEATS))
    broken["beats"][0]["layers"].append({"kind": "counter", "text": "1"})  # a counter with nothing to count to
    broken["beats"][1]["layers"][0]["at"] = "phrase 2"  # the beat has one phrase
    broken["beats"][2]["layers"].append({"kind": "card", "items": ["x"]})  # a kind the engine does not have
    asked: list[str] = []
    made = studio.produce("a hype video", provider_id="ollama", model="llama3", visual_provider="local-images",
                          visual_model="sdxl", voice_provider="local-voice", voice_model="tts", music_file=services["bed"],
                          seconds=6, formats=("1x1",), out_dir=tmp_path / "v", size_scale=0.1,
                          text_transport=_writer_of(broken, BEATS, asked=asked),
                          media_transport=_media({**services, "wav": (tmp_path / "phrase.wav").read_bytes()}))
    assert len(asked) == 2 and made.stopped == "finished", made.stopped  # one fix was enough
    fix = asked[1]
    assert "beat 1: layer 2 (counter)" in fix and "needs 'to'" in fix
    assert "beat 2: layer 1 at:" in fix and "no phrase 2" in fix
    assert "beat 3: layer 2 has" in fix and "unknown kind 'card'" in fix


@needs_ffmpeg
def test_a_short_film_is_held_out_to_the_asked_length(tmp_path: Path, services) -> None:
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=1.0", str(tmp_path / "phrase.wav"))
    made = studio.produce("a hype video", provider_id="ollama", model="llama3", visual_provider="local-images",
                          visual_model="sdxl", voice_provider="local-voice", voice_model="tts", music_file=services["bed"],
                          seconds=12, formats=("1x1",), out_dir=tmp_path / "v", size_scale=0.1,
                          text_transport=_beats_writer,
                          media_transport=_media({**services, "wav": (tmp_path / "phrase.wav").read_bytes()}))
    assert made.stopped == "finished", made.stopped
    assert studio.probe(Path(made.renders["1x1"]))["seconds"] == pytest.approx(12, abs=0.15)
    assert next(c for c in made.checks if c["check"] == "length matches the brief")["ok"]


# --- every second is lively ------------------------------------------------------------------------------

@needs_ffmpeg
def test_bare_still_beats_with_long_lines_still_have_something_happening_every_second(tmp_path: Path) -> None:
    out = tmp_path / "film"
    (out / "shots").mkdir(parents=True)
    (out / "voice").mkdir()
    for n in (1, 2, 3, 4):
        _ffmpeg("-f", "lavfi", "-i", f"testsrc2=s=640x360:d={n}", "-frames:v", "1", str(out / "shots" / f"beat-0{n}.png"))
    for n, length in ((1, 3.6), (2, 4.2), (3, 2.0)):
        _ffmpeg("-f", "lavfi", "-i", f"sine=frequency=440:duration={length}", str(out / "voice" / f"beat0{n}-01.wav"))
    lines = ["Imagine one tool that makes everything you ask for",
             "Prompts, pictures, films, sites and loops from any model you pick",
             "Try Proofhouse today"]
    board = {"beats": [{"base": {"kind": "image", "file": f"shots/beat-0{n}.png"},
                        "phrases": [{"text": line, "file": f"voice/beat0{n}-01.wav"}] if line else []}
                       for n, line in zip((1, 2, 3, 4), [*lines, None])]}
    made = studio.assemble_beats(out, board, formats=("16x9", "9x16"), size_scale=0.25, seconds=16)
    assert made.stopped == "finished", made.stopped
    failed = {(c["render"], c["check"]): c["detail"] for c in made.checks if not c["ok"]}
    assert failed == {}, failed
    for path in made.renders.values():
        activity = studio.picture_activity(Path(path))
        assert activity["longest_quiet"] <= 1.0 and activity["lively_share"] >= 0.95, (path, activity)


# ---------------------------------------------------------------- the writer's full toolkit, and real footage

def test_the_writer_is_offered_every_layer_kind_sound_and_cut_the_engine_draws() -> None:
    from proofhouse import sound, storyboard
    prompt = studio.script_prompt("a hype film", 30)
    for kind in ("title", "label", "chips", "cards", "panel", "counter", "lower_third"):
        assert re.search(rf"\b{kind}\b", prompt), kind
    for kind in sound.KINDS:
        assert kind in prompt, kind
    for cut in storyboard.CUTS:
        assert cut in prompt, cut
    assert "two or three layers" in prompt


def test_a_fact_sheet_page_may_say_how_it_is_used_how_big_it_is_and_what_frame_it_plays_in(tmp_path: Path) -> None:
    page = {"id": "app", "url": "http://localhost:3000", "steps": [{"do": "wait", "seconds": 1}], "size": [390, 844],
            "frame": "phone"}
    sheet = tmp_path / "facts.json"

    def load(**change: object) -> dict:
        sheet.write_text(json.dumps({"product": "P", "summary": "S", "pages": [{**page, **change}]}), encoding="utf-8")
        return studio.load_facts(sheet)

    assert load()["pages"][0] == page
    with pytest.raises(studio.StudioError, match="steps"):
        load(steps=[{"do": "dance"}])
    with pytest.raises(studio.StudioError, match="size"):
        load(size=[10, 844])
    with pytest.raises(studio.StudioError, match="size"):
        load(size=[390, True])
    with pytest.raises(studio.StudioError, match="frame"):
        load(frame="tv")


TERMINAL_FACTS = {"product": "Proofhouse", "summary": "a test",
                  "commands": [{"id": "hi", "argv": [sys.executable, "-c", "print('hi there')"], "display": "proofhouse hi"}]}


def _with_refs(*refs: str | None) -> dict:
    return {**BEATS, "beats": [{**row, "base": {"ref": ref}} if ref else row for row, ref in zip(BEATS["beats"], refs)]}


def _footage_film(tmp_path: Path, services, *replies: dict, asked: list[str], seconds: int = 12):  # noqa: ANN202
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=1.2", str(tmp_path / "phrase.wav"))
    return studio.produce("a hype video", provider_id="ollama", model="llama3", visual_provider="local-images",
                          visual_model="sdxl", voice_provider="local-voice", voice_model="tts",
                          music_file=services["bed"], seconds=seconds, formats=("1x1",), out_dir=tmp_path / "v",
                          size_scale=0.1, facts=TERMINAL_FACTS, allow_commands=True,
                          text_transport=_writer_of(*replies, asked=asked),
                          media_transport=_media({**services, "wav": (tmp_path / "phrase.wav").read_bytes()}))


@needs_ffmpeg
def test_a_command_in_the_fact_sheet_is_typed_in_a_terminal_with_its_real_output(tmp_path: Path, services) -> None:
    made = _footage_film(tmp_path, services, _with_refs(None, "hi", None), asked=[])
    assert made.stopped == "finished", made.stopped
    folder = tmp_path / "v"
    timeline = json.loads((folder / "footage" / "hi" / "terminal.json").read_text(encoding="utf-8"))
    assert timeline["command"] == "proofhouse hi" and "hi there" in json.dumps(timeline["output"])
    row = json.loads((folder / "script.json").read_text(encoding="utf-8"))["beats"][1]
    assert row["base"] == {"kind": "living"} and row["real"] is True and row["hold"] >= timeline["seconds"]
    assert row["layers"][0]["kind"] == "terminal" and row["layers"][0]["timeline"] == timeline
    assert row["layers"][1]["kind"] == "chips" and row["layers"][1]["y"] == studio.TERMINAL_SLOTS[0]  # words clear of it
    assert sorted(p.name for p in (folder / "shots").iterdir()) == ["beat-01.png", "beat-03.png"]  # nothing generated for it
    share = next(c for c in made.checks if c["check"] == "real footage share")
    assert share["ok"], share


@needs_ffmpeg
def test_command_footage_without_permission_stops_before_anything_is_spoken_or_made(tmp_path: Path, services) -> None:
    calls: list[str] = []

    def post(request: media.MediaRequest) -> media.MediaResponse:
        calls.append(request.url)
        return _media(services)(request)

    made = studio.produce("x", provider_id="ollama", model="llama3", visual_provider="local-images", visual_model="sdxl",
                          voice_provider="local-voice", voice_model="tts", seconds=12, formats=("1x1",),
                          out_dir=tmp_path / "v", size_scale=0.1, facts=TERMINAL_FACTS,
                          text_transport=_writer_of(_with_refs(None, "hi", None), asked=[]), media_transport=post)
    assert "--allow-commands" in made.stopped and calls == [] and made.renders == {}, made.stopped


@needs_ffmpeg
def test_too_much_real_footage_is_sent_back_to_the_writer_before_any_picture_is_made(tmp_path: Path, services) -> None:
    asked: list[str] = []
    made = _footage_film(tmp_path, services, _with_refs("hi", "hi", "hi"), _with_refs(None, "hi", None), asked=asked)
    assert made.stopped == "finished", made.stopped
    assert len(asked) == 2 and "real product footage fills" in asked[1] and "fewer footage refs" in asked[1]
    assert sorted(p.name for p in (tmp_path / "v" / "shots").iterdir()) == ["beat-01.png", "beat-03.png"]
    assert "real footage cut to a third" not in {c["check"] for c in made.checks}


@needs_ffmpeg
def test_real_footage_that_stays_too_long_is_cut_to_a_third_and_noted(tmp_path: Path, services) -> None:
    asked: list[str] = []
    made = _footage_film(tmp_path, services, _with_refs("hi", "hi", "hi"), asked=asked)
    assert made.stopped == "finished", made.stopped
    assert len(asked) == 1 + studio.SCRIPT_FIXES
    cut = [c for c in made.checks if c["check"] == "real footage cut to a third"]
    assert cut and all("moving background" in c["detail"] for c in cut)
    rows = json.loads((tmp_path / "v" / "script.json").read_text(encoding="utf-8"))["beats"]
    assert 1 <= sum(1 for r in rows if r.get("real")) < 3
    assert all(r["layers"][0]["kind"] != "terminal" for r in rows if not r.get("real"))
    assert next(c for c in made.checks if c["check"] == "real footage share")["ok"]


@needs_ffmpeg
def test_with_no_picture_service_generated_beats_stand_on_a_moving_background_and_it_is_noted(
        tmp_path: Path, services) -> None:
    calls: list[str] = []

    def post(request: media.MediaRequest) -> media.MediaResponse:
        calls.append(request.url)
        return _media({**services, "wav": (tmp_path / "phrase.wav").read_bytes()})(request)

    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=1.2", str(tmp_path / "phrase.wav"))
    made = studio.produce("a hype video", provider_id="ollama", model="llama3", voice_provider="local-voice",
                          voice_model="tts", music_file=services["bed"], seconds=12, formats=("1x1",),
                          out_dir=tmp_path / "v", size_scale=0.1, text_transport=_writer_of(BEATS, asked=[]),
                          media_transport=post)
    assert made.stopped == "finished", made.stopped
    rows = json.loads((tmp_path / "v" / "script.json").read_text(encoding="utf-8"))["beats"]
    assert [r["base"] for r in rows] == [{"kind": "living"}] * 3
    assert not list((tmp_path / "v" / "shots").iterdir())  # no picture was asked for
    noted = [c for c in made.checks if c["check"] == "no picture service"]
    assert len(noted) == 1 and "1, 2, 3" in noted[0]["detail"]
    assert all("image" not in url for url in calls)


@needs_ffmpeg
def test_a_film_with_footage_on_hand_but_none_used_is_sent_back_then_given_the_terminal(tmp_path: Path, services) -> None:
    asked: list[str] = []
    made = _footage_film(tmp_path, services, BEATS, asked=asked)
    assert len(asked) == 1 + studio.SCRIPT_FIXES and all("no real product footage" in a and "hi" in a for a in asked[1:])
    assert made.stopped == "finished", made.stopped
    row = json.loads((tmp_path / "v" / "script.json").read_text(encoding="utf-8"))["beats"][1]
    assert row["real"] is True and row["layers"][0]["kind"] == "terminal", row
    assert (tmp_path / "v" / "footage" / "hi" / "terminal.json").is_file()
    settled = next(c for c in made.checks if c["check"] == "script settled")
    assert settled["ok"] and "beat 2 shows the real footage 'hi'" in settled["detail"], settled


@needs_ffmpeg
def test_a_writer_that_adds_the_footage_when_told_is_not_asked_again(tmp_path: Path, services) -> None:
    asked: list[str] = []
    made = _footage_film(tmp_path, services, BEATS, _with_refs(None, "hi", None), asked=asked)
    assert len(asked) == 2 and made.stopped == "finished", made.stopped
    assert not any(c["check"] == "script settled" for c in made.checks)


def _counted(to: object, say: str = "Proofhouse makes it.") -> dict:
    third = {**BEATS["beats"][2], "say": say,
             "layers": [*BEATS["beats"][2]["layers"], {"kind": "counter", "to": to, "label": "fixes found", "at": 0.5}]}
    return {**BEATS, "beats": [BEATS["beats"][0], {**BEATS["beats"][1], "base": {"ref": "hi"}}, third]}


def test_a_figure_the_facts_never_give_is_sent_back_and_left_out_at_the_last_chance() -> None:
    ask = {"brief": "a 12 second film", "seconds": 12, "facts": TERMINAL_FACTS, "footage": ["hi"], "voiced": True}
    board = studio.beats_from(_counted(42, "Done in 0.4s."), TERMINAL_FACTS)
    gaps = studio.script_gaps(board, **ask)
    assert any("beat 3 layer 2 states 42" in g for g in gaps), gaps
    assert any("beat 3's narration states 0.4" in g for g in gaps), gaps
    notes = studio.settle_gaps(board, **ask)
    assert [lay["kind"] for lay in board[2]["layers"]] == ["lower_third"]
    assert board[2]["say"] == "Done in 0.4s."  # the narration stays; only what is drawn is left out
    assert any("beat 3 layer 2 left out" in n for n in notes), notes


def test_figures_from_the_brief_or_facts_and_version_tags_are_not_invented() -> None:
    facts = {**TERMINAL_FACTS, "facts": ["It runs 1,200 checks."]}
    for figure in (12, 1200):
        board = studio.beats_from(_counted(figure, "Proofhouse v1.0 makes it."), facts)
        assert studio.script_gaps(board, brief="a 12 second film", seconds=12, facts=facts, footage=["hi"],
                                  voiced=True) == []
    assert studio.script_gaps(studio.beats_from(_counted(42), TERMINAL_FACTS), brief="x", seconds=12, facts=None,
                              footage=[], voiced=True) == []  # with no fact sheet there is nothing to hold it to


def test_narration_too_thin_for_the_film_is_sent_back_and_accepted_at_the_last_chance() -> None:
    board = studio.beats_from(BEATS)  # ten words
    fit = studio.script_budget(45)
    gaps = studio.script_gaps(board, brief="x", seconds=45, facts=None, footage=[], voiced=True)
    assert gaps == [f"the narration is too thin: 10 words over 45 seconds leaves long silences; use {fit['least']} to "
                    f"{fit['words']} words in full flowing sentences"]
    assert studio.script_gaps(board, brief="x", seconds=12, facts=None, footage=[], voiced=True) == []
    assert studio.script_gaps(board, brief="x", seconds=45, facts=None, footage=[], voiced=False) == []
    assert studio.settle_gaps(board, brief="x", seconds=45, facts=None, footage=[], voiced=True) == [
        "the narration stays thin: 10 words over 45 seconds"]
    assert fit["least"] < fit["words"] and f"{fit['least']} words at least" in studio.script_prompt("x", 45)
