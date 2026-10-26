"""Build voice.wav for the promo: each line is spoken by the local Kokoro model and placed at its shot's start.

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

# (start second, spoken text). Starts follow the shot lengths in script.json: 0, 4, 7, 12, 16, 20.
LINES = [
    (0.3, "Low tide. A sandbar. No signal."),
    (4.2, "Meet Tidewatch."),
    (7.2, "Tide tables in your pocket, no signal required."),
    (12.15, "Works fully offline with bundled tide data for two years."),
    (16.2, "A four ninety-nine one-time purchase."),
    (20.2, "No accounts and no ads."),
]
TOTAL = 24.0


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
