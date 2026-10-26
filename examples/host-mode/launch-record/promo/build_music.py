"""Build music.wav for the promo: a 24 second warm pad with a soft pulse and bell notes, made with numpy only.

Run: uv run --no-sync --with numpy python build_music.py
Chords change every 6 seconds (Am9, Fmaj7, C, G); the last 4 seconds lift. No samples, no paid music.
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RATE = 44100
TOTAL = 24.0
N = int(TOTAL * RATE)
T = np.arange(N) / RATE

CHORDS = [  # note numbers (MIDI) per 6 second block
    [45, 57, 60, 64, 67],  # Am9 without the 9 on top, low root
    [41, 57, 60, 64, 65],  # Fmaj7
    [48, 55, 60, 64, 67],  # C
    [43, 55, 59, 62, 67],  # G
]
HZ = lambda m: 440.0 * 2 ** ((m - 69) / 12)


def pad() -> np.ndarray:
    out = np.zeros(N)
    for block, notes in enumerate(CHORDS):
        t0, t1 = block * 6.0, block * 6.0 + 6.0
        env = np.clip((T - (t0 - 1.5)) / 2.5, 0, 1) * np.clip(((t1 + 1.5) - T) / 2.5, 0, 1)
        env = env**1.5
        for note in notes:
            f = HZ(note)
            for detune, gain in ((-0.0035, 0.5), (0.0, 1.0), (0.0035, 0.5)):
                phase = 2 * np.pi * f * (1 + detune) * T
                tone = np.sin(phase) + 0.35 * np.sin(2 * phase) + 0.12 * np.sin(3 * phase)
                out += env * gain * tone * (0.9 if note < 50 else 0.55)
    swell = 0.8 + 0.2 * np.sin(2 * np.pi * T / 12.0)
    return out * swell


def pulse() -> np.ndarray:
    out = np.zeros(N)
    for beat in np.arange(0.0, TOTAL, 1.0):
        i = int(beat * RATE)
        m = min(int(0.35 * RATE), N - i)
        local = np.arange(m) / RATE
        thump = np.sin(2 * np.pi * (52 + 40 * np.exp(-local * 18)) * local) * np.exp(-local * 9)
        out[i : i + m] += thump * (0.55 if beat % 2 == 0 else 0.35)
    return out


def bells() -> np.ndarray:
    out = np.zeros(N)
    scale = [76, 79, 83, 81, 79, 76, 74, 79]
    for k, beat in enumerate(np.arange(1.5, TOTAL - 1.0, 2.0)):
        i = int(beat * RATE)
        m = min(int(2.4 * RATE), N - i)
        local = np.arange(m) / RATE
        f = HZ(scale[k % len(scale)])
        tone = np.sin(2 * np.pi * f * local) + 0.3 * np.sin(2 * np.pi * 2.76 * f * local) * np.exp(-local * 6)
        out[i : i + m] += tone * np.exp(-local * 2.2) * 0.35
    return out


def main() -> None:
    mix = 0.30 * pad() + 0.16 * pulse() + 0.10 * bells()
    lift = 1.0 + 0.55 * np.clip((T - 19.5) / 1.5, 0, 1) * np.clip((TOTAL - T) / 1.5, 0, 1)
    mix *= lift
    fade = np.clip(T / 1.2, 0, 1) * np.clip((TOTAL - T) / 2.0, 0, 1)
    mix *= fade
    left = mix + 0.08 * np.roll(mix, int(0.011 * RATE))
    right = mix + 0.08 * np.roll(mix, int(0.017 * RATE))
    stereo = np.stack([left, right], axis=1)
    stereo *= 0.8 / np.max(np.abs(stereo))
    pcm = (stereo * 32767).astype("<i2")
    with wave.open(str(HERE / "music.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    print(f"wrote music.wav, {TOTAL:.0f}s")


if __name__ == "__main__":
    main()
