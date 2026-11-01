"""The sound kit, the track it lays down, and which moments of a scene get a sound."""

from __future__ import annotations

import wave
from array import array
from pathlib import Path

import pytest

from proofhouse import motion, sound


def test_every_sound_in_the_kit_is_its_length_and_full_scale() -> None:
    for kind in sound.KINDS:
        samples = sound.sound(kind)
        assert len(samples) == round(sound.SECONDS[kind] * sound.RATE)
        assert max(abs(v) for v in samples) == pytest.approx(1.0)


def test_variants_differ_so_repeats_do_not_drone() -> None:
    assert list(sound.sound("pop", 0)) != list(sound.sound("pop", 1))
    assert list(sound.sound("pop", 3)) == list(sound.sound("pop", 3))


def test_an_unknown_sound_is_refused_plainly() -> None:
    with pytest.raises(sound.SoundError, match="the kit makes"):
        sound.sound("explosion")


def _read(path: Path) -> array:
    with wave.open(str(path), "rb") as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, sound.RATE)
        return array("h", w.readframes(w.getnframes()))


def test_mix_lays_sounds_on_one_track_and_a_riser_ends_on_its_moment(tmp_path: Path) -> None:
    track = _read(sound.mix([(1.0, "riser"), (1.5, "hit")], 3.0, tmp_path / "fx.wav"))
    assert len(track) == 3 * sound.RATE

    def loud(a: float, b: float) -> int:
        return max(abs(v) for v in track[round(a * sound.RATE):round(b * sound.RATE)])

    assert loud(0.5, 0.99) > 1000  # the riser builds before 1 s
    assert loud(1.01, 1.49) == 0  # and stops on it
    assert loud(1.5, 1.7) > 1000  # the hit lands at 1.5 s
    assert max(abs(v) for v in track) <= round(0.9 * 32767) + 1


def test_mix_of_nothing_is_silence(tmp_path: Path) -> None:
    assert set(_read(sound.mix([], 0.5, tmp_path / "quiet.wav"))) == {0}


def test_scene_events_follow_what_moves_and_skip_quiet_layers() -> None:
    pytest.importorskip("PIL")
    scene = {"size": [640, 360], "fps": 30, "seconds": 4.0, "layers": [
        {"kind": "title", "text": "Hello", "at": 0.5},
        {"kind": "wipe", "at": 2.0},
        {"kind": "wipe", "at": 3.0, "quiet": True},
        {"kind": "chips", "items": ["a", "b"], "at": 1.0},
    ]}
    got = motion.events(scene)
    assert (0.5, "hit") in got
    assert (2.0, "whoosh") in got
    assert not [e for e in got if e[0] == 3.0]
    assert [k for t, k in got if 1.0 <= t < 1.5] == ["pop", "pop"]
    assert got == sorted(got)
