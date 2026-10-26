"""Build music.wav for the film: a 30 second 92 BPM pad with a plucked bass, a brushed shaker and bell notes, numpy only.

Run: uv run --no-sync --with numpy python build_music.py
Chords change every two bars (Am, F, C, G, Am, F); the last 4 seconds lift. No samples, no paid music.
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RATE = 44100
TOTAL = 30.0
N = int(TOTAL * RATE)
T = np.arange(N) / RATE
BEAT = 60.0 / 92.0
BLOCK = 8 * BEAT  # two bars of four beats

CHORDS = [  # MIDI notes: bass root, then the pad voicing
    (45, [57, 60, 64, 67]),  # Am7
    (41, [57, 60, 64, 65]),  # Fmaj7
    (48, [55, 60, 64, 67]),  # C
    (43, [55, 59, 62, 67]),  # G
    (45, [57, 60, 64, 67]),  # Am7
    (41, [57, 60, 64, 65]),  # Fmaj7
]
HZ = lambda m: 440.0 * 2 ** ((m - 69) / 12)
RNG = np.random.default_rng(7)


def pad() -> np.ndarray:
    out = np.zeros(N)
    for block, (_, notes) in enumerate(CHORDS):
        t0, t1 = block * BLOCK, block * BLOCK + BLOCK
        env = np.clip((T - (t0 - 1.5)) / 2.5, 0, 1) * np.clip(((t1 + 1.5) - T) / 2.5, 0, 1)
        env = env**1.5
        for note in notes:
            f = HZ(note)
            for detune, gain in ((-0.0035, 0.5), (0.0, 1.0), (0.0035, 0.5)):
                phase = 2 * np.pi * f * (1 + detune) * T
                out += env * gain * (np.sin(phase) + 0.3 * np.sin(2 * phase) + 0.1 * np.sin(3 * phase)) * 0.55
    return out * (0.8 + 0.2 * np.sin(2 * np.pi * T / 13.0))


def bass() -> np.ndarray:
    out = np.zeros(N)
    for block, (root, _) in enumerate(CHORDS):
        for beat in (0, 2, 4, 5.5, 6):  # a gentle walking pattern inside each two-bar block
            start = block * BLOCK + beat * BEAT
            i = int(start * RATE)
            if i >= N:
                continue
            m = min(int(0.7 * RATE), N - i)
            local = np.arange(m) / RATE
            note = root if beat != 5.5 else root + 7
            f = HZ(note)
            tone = np.sin(2 * np.pi * f * local) + 0.25 * np.sin(4 * np.pi * f * local)
            out[i : i + m] += tone * np.exp(-local * 5.5) * (0.9 if beat in (0, 4) else 0.6)
    return out


def shaker() -> np.ndarray:
    out = np.zeros(N)
    for k in range(int(TOTAL / (BEAT / 2))):
        start = k * BEAT / 2
        i = int(start * RATE)
        m = min(int(0.09 * RATE), N - i)
        if m <= 0:
            continue
        local = np.arange(m) / RATE
        noise = RNG.standard_normal(m)
        noise = noise - np.convolve(noise, np.ones(8) / 8, mode="same")  # keep only the bright part
        out[i : i + m] += noise * np.exp(-local * 55) * (0.5 if k % 2 == 0 else 0.3)
    return out


def bells() -> np.ndarray:
    out = np.zeros(N)
    scale = [76, 79, 83, 81, 79, 76, 74, 79]
    for k, beat in enumerate(np.arange(3.0, TOTAL / BEAT - 4, 6.0)):
        i = int(beat * BEAT * RATE)
        m = min(int(2.4 * RATE), N - i)
        local = np.arange(m) / RATE
        f = HZ(scale[k % len(scale)])
        tone = np.sin(2 * np.pi * f * local) + 0.3 * np.sin(2 * np.pi * 2.76 * f * local) * np.exp(-local * 6)
        out[i : i + m] += tone * np.exp(-local * 2.2) * 0.35
    return out


def main() -> None:
    mix = 0.30 * pad() + 0.22 * bass() + 0.05 * shaker() + 0.10 * bells()
    mix *= 1.0 + 0.5 * np.clip((T - 26.0) / 1.5, 0, 1) * np.clip((TOTAL - T) / 1.5, 0, 1)
    mix *= np.clip(T / 1.2, 0, 1) * np.clip((TOTAL - T) / 2.0, 0, 1)
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
