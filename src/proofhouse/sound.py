"""A small sound kit made from scratch: whooshes, ticks, clicks, pops, hits, risers and chimes.

No sample files and nothing to download: each sound is drawn from sine waves and filtered noise, so every film
gets sound design on any machine that has Python. ``mix`` lays the sounds of a film on one track.
"""
from __future__ import annotations

import math
import random
import wave
from array import array
from pathlib import Path

RATE = 48000
KINDS = ("whoosh", "tick", "click", "pop", "hit", "riser", "chime")
GAIN = {"whoosh": 0.5, "tick": 0.22, "click": 0.4, "pop": 0.35, "hit": 0.75, "riser": 0.4, "chime": 0.45}
SECONDS = {"whoosh": 0.55, "tick": 0.03, "click": 0.05, "pop": 0.14, "hit": 0.9, "riser": 1.2, "chime": 1.8}


class SoundError(ValueError):
    """A sound the kit does not make, or a track it cannot write."""


def _normal(samples: list[float]) -> array:
    peak = max((abs(v) for v in samples), default=0.0)
    return array("f", (v / peak for v in samples) if peak > 0 else samples)


def sound(kind: str, variant: int = 0) -> array:
    """One sound as samples from -1 to 1 at ``RATE``. Variants differ a little in pitch, so repeats do not drone."""
    if kind not in KINDS:
        raise SoundError(f"unknown sound {kind!r}; the kit makes: {', '.join(KINDS)}")
    rng = random.Random(f"{kind}-{variant}")
    pitch = 1 + 0.06 * ((variant % 5) - 2)
    n = round(SECONDS[kind] * RATE)
    out: list[float] = []
    if kind in ("whoosh", "riser"):
        low = high = 0.0
        for i in range(n):
            p = i / n
            if kind == "whoosh":
                env = math.sin(math.pi * min(1.0, p / 0.45) / 2) ** 2 if p < 0.45 else math.cos(math.pi * (p - 0.45) / 1.1) ** 2
                cut = 0.03 + 0.3 * math.sin(math.pi * p)
            else:  # rises to its moment, then stops short
                env = p ** 2 * (1.0 if p < 0.97 else (1 - p) / 0.03)
                cut = 0.02 + 0.25 * p
            x = rng.uniform(-1, 1)
            low += cut * (x - low)
            high += 0.01 * (low - high)
            tone = math.sin(2 * math.pi * pitch * (200 + 600 * p) * i / RATE) * 0.25 if kind == "riser" else 0.0
            out.append(env * ((low - high) + tone))
    elif kind in ("tick", "click"):
        f = (3200 if kind == "tick" else 1700) * pitch
        tau = 0.004 if kind == "tick" else 0.007
        for i in range(n):
            t = i / RATE
            out.append(math.exp(-t / tau) * (0.7 * math.sin(2 * math.pi * f * t) + 0.3 * rng.uniform(-1, 1)))
    elif kind == "pop":
        phase = 0.0
        for i in range(n):
            t = i / RATE
            phase += 2 * math.pi * pitch * (300 + 600 * math.exp(-t / 0.02)) / RATE
            out.append(math.exp(-t / 0.035) * math.sin(phase))
    elif kind == "hit":
        phase, low = 0.0, 0.0
        for i in range(n):
            t = i / RATE
            phase += 2 * math.pi * pitch * (45 + 30 * math.exp(-t / 0.05)) / RATE
            low += 0.08 * (rng.uniform(-1, 1) - low)
            out.append(math.tanh(1.6 * (math.exp(-t / 0.28) * math.sin(phase) + 0.6 * math.exp(-t / 0.04) * low)))
    else:  # chime: a bell, a fundamental and its inharmonic partials
        f0 = 1046.5 * pitch
        partials = ((1.0, 1.0, 0.9), (2.76, 0.45, 0.45), (5.4, 0.2, 0.22), (1.5, 0.5, 0.7))
        for i in range(n):
            t = i / RATE
            attack = min(1.0, t / 0.004)
            out.append(attack * sum(a * math.exp(-t / d) * math.sin(2 * math.pi * f0 * r * t) for r, a, d in partials))
    return _normal(out)


def mix(events: list[tuple[float, str]], seconds: float, out: Path) -> Path:
    """Lay every (time, kind) sound on one 16-bit mono track ``seconds`` long. A riser ends at its time; the rest start there."""
    n = max(1, round(seconds * RATE))
    track = array("f", bytes(4 * n))
    made: dict[tuple[str, int], array] = {}
    for count, (when, kind) in enumerate(sorted(events)):
        key = (kind, count % 5)
        samples = made.get(key)
        if samples is None:
            samples = made[key] = sound(kind, count % 5)
        start = round(when * RATE) - (len(samples) if kind == "riser" else 0)
        gain = GAIN[kind]
        for j in range(max(0, -start), min(len(samples), n - start)):
            track[start + j] += gain * samples[j]
    peak = max((abs(v) for v in track), default=0.0)
    scale = 0.9 / peak if peak > 0.9 else 1.0
    pcm = array("h", (round(32767 * max(-1.0, min(1.0, v * scale))) for v in track))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    return out
