"""A music bed made from scratch on this machine: chords, bass, a plucked line and drums, picked from the mood words.

It needs nothing but Python, costs nothing and never calls out. The shipped ``local-music`` entry in the media list runs
it (``python -m proofhouse.local_music --seconds 30 --out bed.wav`` with the brief on stdin), so a film always has
music even with no music service. A paid service makes richer music; this is the floor, not the ceiling.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import random
import re
import sys
import wave
from array import array
from pathlib import Path
from typing import Any

RATE = 32000  # the film's mix resamples to 48 kHz; a bed needs no more detail than this
MAX_SECONDS = 1200

_CALM = {"calm", "ambient", "slow", "soft", "gentle", "reflective", "quiet", "peaceful", "dreamy", "warm", "relaxed",
         "meditative", "lofi", "lo-fi", "sad", "tender", "minimal", "chill"}
_FAST = {"energetic", "hype", "fast", "driving", "bold", "exciting", "punchy", "upbeat", "intense", "epic", "action",
         "powerful", "dance", "edm", "rock", "pumping", "triumphant"}
_MINOR = {"dark", "sad", "tense", "serious", "moody", "cinematic", "mysterious", "suspense", "suspenseful", "melancholy",
          "melancholic", "ominous", "dramatic", "minor", "noir"}
_NO_DRUMS = {"ambient", "no drums", "drone", "pads", "meditative", "solo piano", "piano only"}
_ROOTS = (45, 48, 50, 53, 55)  # A2, C3, D3, F3, G3 as MIDI notes
_MAJOR_STEPS = (0, 2, 4, 5, 7, 9, 11)
_MINOR_STEPS = (0, 2, 3, 5, 7, 8, 10)
_PROGRESSIONS = {"major": ((0, 4, 5, 3), (0, 5, 3, 4), (0, 3, 4, 4)), "minor": ((0, 5, 2, 6), (0, 3, 5, 4), (0, 6, 5, 6))}


def _words(brief: str) -> set[str]:
    text = brief.lower()
    found = set(re.findall(r"[a-z][a-z-]*", text))
    found.update(phrase for phrase in _NO_DRUMS if " " in phrase and phrase in text)
    return found


def arrangement(brief: str) -> dict[str, Any]:
    """What the bed will be: the same words always make the same piece."""
    words = _words(brief)
    seed = int.from_bytes(hashlib.sha256(brief.strip().lower().encode("utf-8")).digest()[:8], "big")
    rng = random.Random(seed)
    calm, fast = len(words & _CALM), len(words & _FAST)
    if fast > calm:
        bpm = rng.choice((118, 120, 124, 128))
    elif calm > fast:
        bpm = rng.choice((72, 76, 80, 84))
    else:
        bpm = rng.choice((96, 100, 104))
    mode = "minor" if words & _MINOR else "major"
    drums = not (words & _NO_DRUMS) and not (calm > fast and calm >= 2)
    return {"bpm": bpm, "mode": mode, "root": rng.choice(_ROOTS), "progression": list(rng.choice(_PROGRESSIONS[mode])),
            "drums": drums, "arp": fast >= calm, "seed": seed}


def _freq(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _chord(plan: dict[str, Any], degree: int) -> list[int]:
    steps = _MINOR_STEPS if plan["mode"] == "minor" else _MAJOR_STEPS
    return [plan["root"] + 12 * ((degree + i) // 7) + steps[(degree + i) % 7] for i in (0, 2, 4)]


def _add(track: array, start: int, notes: list[float]) -> None:
    end = min(len(track), start + len(notes))
    for i in range(start, end):
        track[i] += notes[i - start]


def _pad(freq: float, length: int, gain: float) -> list[float]:
    attack, release = int(RATE * 0.4), int(RATE * 0.6)
    w = [2 * math.pi * freq * k / RATE for k in (1.0, 1.004, 0.996)]
    out = []
    for i in range(length):
        env = min(1.0, i / attack, (length - i) / release)
        s = math.sin(w[0] * i) + 0.5 * math.sin(w[1] * i) + 0.5 * math.sin(w[2] * i) + 0.18 * math.sin(2 * w[0] * i)
        out.append(gain * env * s)
    return out


def _pluck(freq: float, length: int, gain: float) -> list[float]:
    w = 2 * math.pi * freq / RATE
    decay = 6.0 / RATE
    return [gain * math.exp(-decay * i * 2.2) * (math.sin(w * i) + 0.3 * math.sin(2 * w * i)) * min(1.0, i / 40) for i in range(length)]


def _bass(freq: float, length: int, gain: float) -> list[float]:
    w = 2 * math.pi * freq / RATE
    tail = int(RATE * 0.03)
    return [gain * min(1.0, i / 60, (length - i) / tail) * (math.sin(w * i) + 0.25 * math.sin(2 * w * i)) for i in range(length)]


def _kick(gain: float) -> list[float]:
    n, phase, out = int(RATE * 0.35), 0.0, []
    for i in range(n):
        t = i / RATE
        phase += 2 * math.pi * (45 + 110 * math.exp(-t * 30)) / RATE
        out.append(gain * math.exp(-t * 9) * math.sin(phase))
    return out


def _noise_hit(rng: random.Random, seconds: float, decay: float, gain: float, bright: bool) -> list[float]:
    n, last, out = int(RATE * seconds), 0.0, []
    for i in range(n):
        v = rng.uniform(-1, 1)
        hp = v - last if bright else v  # a one-step difference keeps only the hiss
        last = v
        out.append(gain * math.exp(-decay * i / RATE) * hp)
    return out


def _loop(plan: dict[str, Any], *, drums: bool, arp: bool) -> tuple[array, array]:
    beat = round(RATE * 60 / plan["bpm"])
    bar = beat * 4
    left, right = array("f", bytes(4 * bar * 4)), array("f", bytes(4 * bar * 4))
    rng = random.Random(plan["seed"])
    for b, degree in enumerate(plan["progression"]):
        chord = _chord(plan, degree)
        start = b * bar
        for k, note in enumerate(chord):
            tone = _pad(_freq(note + 12), bar + beat // 2, 0.10)
            _add(left if k != 2 else right, start, tone)
            _add(right if k != 0 else left, start, [v * 0.7 for v in tone])
        bass = _freq(chord[0] - 12)
        for e in range(8):
            if e % 2 == 0 or plan["bpm"] >= 110:
                tone = _bass(bass * (2 if e == 7 and plan["bpm"] >= 110 else 1), beat // 2 - 20, 0.22)
                _add(left, start + e * beat // 2, tone)
                _add(right, start + e * beat // 2, tone)
        if arp:
            pattern = [chord[0], chord[1], chord[2], chord[1] + 12 if rng.random() < 0.5 else chord[2] + 12]
            for e in range(8):
                note = pattern[e % 4] + 12
                tone = _pluck(_freq(note), beat, 0.09)
                _add(left if e % 2 == 0 else right, start + e * beat // 2, tone)
                _add(right if e % 2 == 0 else left, start + e * beat // 2, [v * 0.5 for v in tone])
    if drums:
        kick, snare = _kick(0.55), _noise_hit(rng, 0.18, 22, 0.22, False)
        for b in range(4):
            for q in range(4):
                at = b * bar + q * beat
                if q in (0, 2) or (plan["bpm"] >= 110 and q == 3 and b % 2):
                    _add(left, at, kick)
                    _add(right, at, kick)
                if q in (1, 3):
                    _add(left, at, snare)
                    _add(right, at, snare)
                for h in (0, 1):
                    hat = _noise_hit(rng, 0.05, 70, 0.07 if h else 0.1, True)
                    _add(left if h else right, at + h * beat // 2, hat)
    return left, right


def make(brief: str, seconds: float, out: Path) -> Path:
    """Write a stereo WAV bed of ``seconds`` at ``out``: an opening without drums, then the full loop, then a fade."""
    if not 1 <= seconds <= MAX_SECONDS:
        raise ValueError(f"the bed must be 1 to {MAX_SECONDS} seconds")
    plan = arrangement(brief)
    total = int(RATE * seconds)
    intro = _loop(plan, drums=False, arp=False)
    full = _loop(plan, drums=plan["drums"], arp=plan["arp"])
    left, right = array("f"), array("f")
    first = True
    while len(left) < total:
        part = intro if first and seconds >= 16 else full
        left.extend(part[0])
        right.extend(part[1])
        first = False
    del left[total:], right[total:]
    peak = max(max(map(abs, left)), max(map(abs, right))) or 1.0
    scale = 0.7 / peak
    fade_in, fade_out = int(RATE * 0.5), int(RATE * min(2.0, seconds / 4))
    pcm = array("h", bytes(4 * total))
    for i in range(total):
        env = min(1.0, (i + 1) / fade_in, (total - i) / fade_out) * scale
        pcm[2 * i] = int(32767 * max(-1.0, min(1.0, math.tanh(left[i] * env * 1.1))))
        pcm[2 * i + 1] = int(32767 * max(-1.0, min(1.0, math.tanh(right[i] * env * 1.1))))
    if sys.byteorder == "big":
        pcm.byteswap()
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m proofhouse.local_music", description="Make a music bed from the brief on stdin.")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--seconds", required=True, type=float)
    args = parser.parse_args(argv)
    if not 1 <= args.seconds <= MAX_SECONDS:
        parser.error(f"--seconds must be 1 to {MAX_SECONDS}")
    brief = sys.stdin.read() if not sys.stdin.isatty() else ""
    make(brief, args.seconds, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
