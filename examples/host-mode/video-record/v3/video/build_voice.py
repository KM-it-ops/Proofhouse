"""Build voice.wav for the film: each line is spoken by the local Kokoro model and placed at its shot's start.

Run: uv run --no-sync --with kokoro-onnx --with soundfile python build_voice.py <folder with kokoro-v1.0.onnx and voices-v1.0.bin>
Kokoro is Apache-2.0 and runs on the CPU; nothing is sent anywhere.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

HERE = Path(__file__).resolve().parent
MODELS = Path(sys.argv[1])
VOICE = "af_heart"
SPEED = 0.95
RATE = 24000

# (start second, spoken text). Starts follow the shot lengths in script.json: 0, 5, 8, 13, 18, 23, 27.
LINES = [
    (0.4, "The tide doesn't wait. And out here, there's no signal."),
    (5.2, "Meet Tidewatch."),
    (8.2, "Tide tables in your pocket. No signal required."),
    (13.1, "It works fully offline, with two years of tide data built in."),
    (18.2, "Just four ninety-nine. One time."),
    (23.2, "No accounts to make. No ads to skip."),
    (27.2, "Tidewatch. Know the water."),
]
TOTAL = 30.0


def main() -> None:
    kokoro = Kokoro(str(MODELS / "kokoro-v1.0.onnx"), str(MODELS / "voices-v1.0.bin"))
    track = np.zeros(int(TOTAL * RATE), dtype=np.float32)
    for start, text in LINES:
        samples, rate = kokoro.create(text, voice=VOICE, speed=SPEED, lang="en-us")
        assert rate == RATE, rate
        begin = int(start * RATE)
        end = begin + len(samples)
        print(f"{start:5.2f}s -> {end / RATE:5.2f}s  {text}")
        track[begin:end] += samples[: len(track) - begin]
    peak = float(np.max(np.abs(track)))
    if peak > 0.95:
        track *= 0.95 / peak
    sf.write(str(HERE / "voice.wav"), track, RATE)


if __name__ == "__main__":
    main()
