"""Pictures, music and a voice that cost nothing ship in the media list, so a film is never blank or silent for want
of a key."""
from __future__ import annotations

import json
import os
import sys
import wave
from array import array
from pathlib import Path

import pytest

from proofhouse import cli, local_images, local_music, local_voice, media


def _read(path: Path) -> tuple[int, int, float, array]:
    with wave.open(str(path), "rb") as w:
        rate, channels, frames = w.getframerate(), w.getnchannels(), w.getnframes()
        samples = array("h", w.readframes(frames))
    return rate, channels, frames / rate, samples


def test_the_running_python_starts_a_program_line(tmp_path: Path) -> None:
    script = tmp_path / "make.py"
    script.write_text("import sys\nopen(sys.argv[1], 'w').write(sys.executable)\n", encoding="utf-8")
    (tmp_path / "t.json").write_text(json.dumps({"id": "py-maker", "kinds": ["image"],
                                                 "run": {"command": ["@python", str(script), "{out}"], "ext": "txt"}}),
                                     encoding="utf-8")
    assert cli.main(["media", "add", "--from", str(tmp_path / "t.json")]) == 0
    done = media.generate("image", "py-maker", "local", prompt="a fox", out=tmp_path / "fox")
    assert done.status == "success", done.message
    assert Path(Path(done.path).read_text()).resolve() == Path(sys.executable).resolve()


def test_local_music_and_voice_ship_as_free_entries_in_the_media_list() -> None:
    music, voice = media.find("local-music"), media.find("local-voice")
    assert music is not None and voice is not None
    assert music.kinds == ("music",) and voice.kinds == ("speech",)
    assert music.local and voice.local and music.origin == voice.origin == "shipped"
    assert music.run["command"][0] == voice.run["command"][0] == "@python"


def test_the_music_bed_is_as_long_as_asked_in_stereo_and_never_silent(tmp_path: Path) -> None:
    done = media.generate("music", "local-music", "local", prompt="warm, hopeful, gentle piano and soft drums",
                          out=tmp_path / "bed", params={"seconds": 12})
    assert done.status == "success", done.message
    assert done.admission["worst_case_usd"] == "0"
    rate, channels, seconds, samples = _read(Path(done.path))
    assert channels == 2 and rate >= 32000 and 12 <= seconds < 12.5
    loud = max(abs(s) for s in samples)
    assert 8000 < loud < 32767  # clearly audible, never clipped
    # the sound keeps going: no second of the bed is silent
    second = rate * channels
    for start in range(0, len(samples) - second, second):
        assert max(abs(s) for s in samples[start:start + second]) > 1000


def test_the_mood_words_set_the_tempo_key_and_drums() -> None:
    calm = local_music.arrangement("calm ambient pads, slow and reflective")
    hype = local_music.arrangement("energetic hype, driving drums, fast and bold")
    dark = local_music.arrangement("dark tense cinematic")
    assert calm["bpm"] < 95 < hype["bpm"]
    assert not calm["drums"] and hype["drums"]
    assert dark["mode"] == "minor" and local_music.arrangement("bright happy pop")["mode"] == "major"
    assert local_music.arrangement("calm ambient pads") == local_music.arrangement("calm ambient pads")  # same words, same piece


def test_the_music_maker_refuses_a_length_it_cannot_make(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        local_music.main(["--out", str(tmp_path / "x.wav"), "--seconds", "0"])
    with pytest.raises(SystemExit):
        local_music.main(["--out", str(tmp_path / "x.wav"), "--seconds", "100000"])


def test_the_local_voice_picks_the_first_speech_engine_this_machine_has(monkeypatch: pytest.MonkeyPatch) -> None:
    have = {"espeak-ng": "/usr/bin/espeak-ng", "espeak": "/usr/bin/espeak"}
    monkeypatch.delenv("PROOFHOUSE_VOICE_ENGINE", raising=False)
    monkeypatch.setattr(local_voice, "_program", lambda name: have.get(name))
    monkeypatch.setattr(local_voice, "_has_module", lambda name: False)
    assert local_voice.pick() == "espeak-ng"
    monkeypatch.setattr(local_voice, "_has_module", lambda name: name == "kokoro")
    assert local_voice.pick() == "kokoro"  # the better-sounding engine wins when both are here
    monkeypatch.setenv("PROOFHOUSE_VOICE_ENGINE", "espeak")
    assert local_voice.pick() == "espeak"  # unless one is named
    monkeypatch.delenv("PROOFHOUSE_VOICE_ENGINE")
    monkeypatch.setattr(local_voice, "_has_module", lambda name: False)
    monkeypatch.setattr(local_voice, "_program", lambda name: None)
    with pytest.raises(local_voice.VoiceError, match="no speech engine"):
        local_voice.pick()


def test_the_words_reach_the_engine_on_stdin_never_in_the_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_run(command: list[str], **kw: object) -> object:
        seen["command"], seen["input"] = command, kw.get("input")
        Path(seen.setdefault("out", str(tmp_path / "v.wav"))).write_bytes(b"RIFF....WAVE")

        class Done:
            returncode, stderr = 0, b""
        return Done()

    monkeypatch.setattr(local_voice, "_program", lambda name: "C:/x/" + name if name in ("powershell", "espeak-ng") else None)
    monkeypatch.setattr(local_voice, "_has_module", lambda name: False)
    monkeypatch.setattr(local_voice.subprocess, "run", fake_run)
    words = "Say $(rm -rf ~) & \"quoted\"; it's fine"
    for engine in ("windows", "espeak-ng"):
        local_voice.speak(words, tmp_path / "v.wav", voice="alloy", engine=engine)
        assert words not in " ".join(seen["command"])  # type: ignore[arg-type]
        assert seen["input"] == words.encode("utf-8")


def _hosted_macos_say() -> bool:
    # Hosted macOS runners have `say`, but there it renders an empty file (~5 ms of audio), so the
    # really-speaks smoke test cannot assert real speech on them.
    if sys.platform != "darwin" or os.environ.get("GITHUB_ACTIONS") != "true":
        return False
    try:
        return local_voice.pick() == "say"
    except local_voice.VoiceError:
        return False


@pytest.mark.skipif(not local_voice.available(), reason="no speech engine on this machine")
@pytest.mark.skipif(_hosted_macos_say(), reason="hosted macOS runners have `say` but it renders an empty audio file there")
def test_the_local_voice_really_speaks(tmp_path: Path) -> None:
    done = media.generate("speech", "local-voice", "local", prompt="Proofhouse makes the film you asked for.",
                          out=tmp_path / "line")
    assert done.status == "success", done.message
    rate, channels, seconds, samples = _read(Path(done.path))
    assert 1.0 < seconds < 10 and max(abs(s) for s in samples) > 2000


# ---- pictures ----

def _picture(path: Path):
    from PIL import Image

    with Image.open(path) as im:
        return im.convert("RGB").copy()


def _mean(image) -> tuple[float, float, float]:
    from PIL import ImageStat

    r, g, b = ImageStat.Stat(image).mean
    return r, g, b


def test_pictures_made_here_ship_as_a_free_entry_in_the_media_list() -> None:
    images = media.find("local-images")
    assert images is not None and images.kinds == ("image",) and images.local and images.origin == "shipped"
    assert images.run["command"][:3] == ["@python", "-m", "proofhouse.local_images"]
    assert "{size}" in images.run["command"] and "{model}" in images.run["command"]


def test_the_floor_makes_a_picture_of_the_asked_size_at_no_cost(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    done = media.generate("image", "local-images", "floor", prompt="a neon city at night, fast energy",
                          out=tmp_path / "shot", params={"size": "320x180"})
    assert done.status == "success", done.message
    assert done.admission["worst_case_usd"] == "0"
    picture = _picture(Path(done.path))
    assert picture.size == (320, 180)
    low, high = zip(*picture.getextrema())
    assert max(high) - min(low) > 60  # light and shade, not one flat colour


def test_the_prompts_colour_words_set_the_colours(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    red = _mean(_picture(local_images.paint("a red poster, bold", tmp_path / "r.png", size=(160, 90), engine="floor")))
    blue = _mean(_picture(local_images.paint("a blue poster, bold", tmp_path / "b.png", size=(160, 90), engine="floor")))
    assert red[0] > red[2] + 20 and blue[2] > blue[0] + 20
    dark = _mean(_picture(local_images.paint("dark night, noir", tmp_path / "d.png", size=(160, 90), engine="floor")))
    light = _mean(_picture(local_images.paint("bright airy morning", tmp_path / "l.png", size=(160, 90), engine="floor")))
    assert sum(light) > sum(dark) + 90


def test_the_same_prompt_makes_the_same_picture_and_another_prompt_another(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    for name, prompt in (("1", "a calm sea"), ("2", "a calm sea"), ("3", "a calm forest")):
        local_images.paint(prompt, tmp_path / f"{name}.png", size=(128, 72), engine="floor")
    one, two, other = (_picture(tmp_path / f"{n}.png").tobytes() for n in "123")
    assert one == two and one != other


def test_the_floor_never_writes_words_on_the_picture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("PIL")
    from PIL import ImageDraw

    def no_words(*args: object, **kwargs: object) -> None:
        raise AssertionError("the floor drew text")

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", no_words)
    monkeypatch.setattr(ImageDraw.ImageDraw, "multiline_text", no_words)
    local_images.paint("Launch day: SALE 50% OFF, stars and waves", tmp_path / "w.png", size=(200, 120), engine="floor")


def test_the_engine_is_the_model_when_installed_and_the_floor_otherwise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PROOFHOUSE_IMAGE_ENGINE", raising=False)
    installed = {"PIL"}
    monkeypatch.setattr(local_images, "_has_module", lambda name: name in installed)
    assert local_images.pick("local") == "floor" and local_images.available()
    with pytest.raises(local_images.ImageError, match="local-images"):
        local_images.pick("stabilityai/sdxl-turbo")
    installed |= {"diffusers", "torch", "transformers"}
    assert local_images.pick("local") == "diffusers"
    assert local_images.pick("floor") == "floor" and local_images.pick("stabilityai/sdxl-turbo") == "diffusers"
    monkeypatch.setenv("PROOFHOUSE_IMAGE_ENGINE", "floor")
    assert local_images.pick("local") == "floor"
    installed.clear()
    assert not local_images.available()


def test_the_model_runs_at_its_own_size_and_the_picture_comes_back_at_the_asked_one(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("PIL")
    import types

    from PIL import Image

    calls: list[dict] = []

    class Pipe:
        def to(self, device: str) -> "Pipe":
            calls.append({"device": device})
            return self

        def __call__(self, **kwargs: object) -> object:
            calls.append(kwargs)
            return types.SimpleNamespace(images=[Image.new("RGB", (kwargs["width"], kwargs["height"]), (200, 30, 30))])

    class Auto:
        @staticmethod
        def from_pretrained(name: str, torch_dtype: object) -> Pipe:
            calls.append({"name": name, "dtype": torch_dtype})
            return Pipe()

    backends = types.SimpleNamespace(mps=types.SimpleNamespace(is_available=lambda: False))
    torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False), backends=backends,
                                  float16="f16", float32="f32")
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "diffusers", types.SimpleNamespace(AutoPipelineForText2Image=Auto))
    out = local_images.paint("a red fox", tmp_path / "fox.png", size=(1792, 1024), model="local", engine="diffusers")
    assert calls[0] == {"name": local_images.DEFAULT_MODEL, "dtype": "f32"} and calls[1] == {"device": "cpu"}
    run = calls[2]
    assert run["prompt"] == "a red fox" and run["num_inference_steps"] == 1 and run["guidance_scale"] == 0.0
    assert max(run["width"], run["height"]) == 512 and run["width"] % 64 == run["height"] % 64 == 0
    assert _picture(out).size == (1792, 1024)


def test_a_bad_size_or_an_empty_prompt_fails_plainly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                      capsys: pytest.CaptureFixture[str]) -> None:
    import io
    import types

    with pytest.raises(local_images.ImageError, match="1792x1024"):
        local_images.parse_size("big")
    with pytest.raises(local_images.ImageError, match="64 to 8192"):
        local_images.parse_size("10x10")
    monkeypatch.setattr(sys, "stdin", types.SimpleNamespace(buffer=io.BytesIO(b"   ")))
    assert local_images.main(["--out", str(tmp_path / "x.png"), "--model", "floor"]) == 2
    assert "nothing to picture" in capsys.readouterr().err
