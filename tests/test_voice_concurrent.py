"""Speaking a film's lines can overlap when the voice runs on this machine; the result must be the same as one at a time."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from proofhouse import storyboard
from proofhouse.storyboard import StoryboardError


def _beats(tmp_path: Path, lines: int) -> list[storyboard.Beat]:
    rows = [{"say": f"Line number {i} of the film.", "base": {"kind": "living"}} for i in range(lines)]
    return storyboard.parse(rows, tmp_path)


def test_lines_are_spoken_at_the_same_time_and_land_on_the_right_beat(tmp_path: Path) -> None:
    beats = _beats(tmp_path, 6)
    live, peak, lock = 0, 0, threading.Lock()

    def speak(text: str, name: str) -> Path:
        nonlocal live, peak
        with lock:
            live += 1
            peak = max(peak, live)
        time.sleep(0.15)
        with lock:
            live -= 1
        out = tmp_path / f"{name}.wav"
        out.write_text(text, encoding="utf-8")
        return out

    storyboard.voice(beats, speak, lambda path: 1.0 + len(path.read_text(encoding="utf-8")) / 100, workers=4)
    assert peak > 1
    for beat in beats:
        for phrase in beat.phrases:
            assert phrase.file is not None and phrase.file.read_text(encoding="utf-8") == phrase.text
            assert phrase.seconds > 1.0


def test_one_worker_keeps_the_old_order_and_never_overlaps(tmp_path: Path) -> None:
    beats = _beats(tmp_path, 4)
    order: list[str] = []

    def speak(text: str, name: str) -> Path:
        order.append(name)
        out = tmp_path / f"{name}.wav"
        out.write_bytes(b"x")
        return out

    storyboard.voice(beats, speak, lambda path: 1.0)
    assert order == sorted(order) and len(order) == 4


def test_a_line_that_fails_stops_the_film_with_its_own_error(tmp_path: Path) -> None:
    beats = _beats(tmp_path, 5)

    def speak(text: str, name: str) -> Path:
        if name.startswith("beat03"):
            raise StoryboardError("the voice broke on beat 3")
        out = tmp_path / f"{name}.wav"
        out.write_bytes(b"x")
        return out

    with pytest.raises(StoryboardError, match="beat 3"):
        storyboard.voice(beats, speak, lambda path: 1.0, workers=3)


def test_a_silent_file_is_still_caught_after_concurrent_speaking(tmp_path: Path) -> None:
    beats = _beats(tmp_path, 3)

    def speak(text: str, name: str) -> Path:
        out = tmp_path / f"{name}.wav"
        out.write_bytes(b"x")
        return out

    with pytest.raises(StoryboardError, match="no sound"):
        storyboard.voice(beats, speak, lambda path: 0.0, workers=3)
