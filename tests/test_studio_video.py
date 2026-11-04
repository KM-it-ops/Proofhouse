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
def test_a_storyboard_layer_the_engine_cannot_draw_is_refused_before_any_picture_is_made(tmp_path: Path, services) -> None:
    bad = {**BEATS, "beats": [{**BEATS["beats"][0], "layers": [{"kind": "hologram", "at": 0}]}]}
    calls: list[str] = []

    def post(request: media.MediaRequest) -> media.MediaResponse:
        calls.append(request.url)
        return _media(services)(request)

    made = studio.produce("x", provider_id="ollama", model="llama3", visual_provider="local-images", visual_model="sdxl",
                          voice_provider="local-voice", voice_model="tts", seconds=6, formats=("1x1",),
                          out_dir=tmp_path / "v", size_scale=0.1, media_transport=post,
                          text_transport=lambda r: live.Response(200, {"choices": [{"message": {"content": json.dumps(bad)}}],
                                                                        "usage": {"prompt_tokens": 1, "completion_tokens": 1}}))
    assert made.stopped.startswith("beat 1:") and calls == [], made.stopped


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
