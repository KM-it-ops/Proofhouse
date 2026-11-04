"""Music and a voice that cost nothing ship in the media list, so a film is never silent for want of a key."""
from __future__ import annotations

import json
import sys
import wave
from array import array
from pathlib import Path

import pytest

from proofhouse import cli, local_music, local_voice, media


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


@pytest.mark.skipif(not local_voice.available(), reason="no speech engine on this machine")
def test_the_local_voice_really_speaks(tmp_path: Path) -> None:
    done = media.generate("speech", "local-voice", "local", prompt="Proofhouse makes the film you asked for.",
                          out=tmp_path / "line")
    assert done.status == "success", done.message
    rate, channels, seconds, samples = _read(Path(done.path))
    assert 1.0 < seconds < 10 and max(abs(s) for s in samples) > 2000
