#!/usr/bin/env python3
"""Plain fallback frames for the recorded README run.

The README clip is the hype cut in videos/readme-hype (Remotion motion,
Hyperframes timeline). This script writes a separate plain pair so it does
not replace that cut. No model is called.

    uv run --with pillow python scripts/render_readme_demo.py
"""

from __future__ import annotations

import json
import math
import struct
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_MP4 = ROOT / "docs" / "assets" / "proofhouse-demo-plain.mp4"
OUT_JPG = ROOT / "docs" / "assets" / "proofhouse-demo-plain.jpg"
FONTS = Path(r"C:\Windows\Fonts")

W, H = 1920, 1080
FPS = 30
DURATION = 36.0
FRAMES = int(DURATION * FPS)

BG = (7, 14, 12)
CREAM = (244, 241, 234)
TEAL = (46, 230, 199)
RED = (255, 92, 108)
GOLD = (214, 177, 90)
MUTED = (158, 172, 166)
DIM = (96, 112, 106)
CARD = (14, 26, 24)
LINE = (42, 64, 58)


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def ease(value: float) -> float:
    value = clamp(value)
    return 1 - (1 - value) ** 3


def span(t: float, start: float, end: float) -> float:
    if end <= start:
        return 1.0 if t >= start else 0.0
    return ease((t - start) / (end - start))


def fade(t: float, start: float, end: float, edge: float = 0.28) -> float:
    if t < start or t >= end:
        return 0.0
    if t < start + edge:
        return ease((t - start) / edge)
    if t > end - edge:
        return ease((end - t) / edge)
    return 1.0


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


UI_B = font("segoeuib.ttf", 78)
UI_H = font("segoeuib.ttf", 54)
UI_M = font("segoeuib.ttf", 34)
UI = font("segoeui.ttf", 32)
UI_P = font("segoeui.ttf", 28)
UI_S = font("segoeui.ttf", 24)
UI_XS = font("segoeui.ttf", 20)
MONO = font("CascadiaMono.ttf", 30)
MONO_S = font("CascadiaMono.ttf", 26)
MONO_XS = font("CascadiaMono.ttf", 22)


def new_layer() -> Image.Image:
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def blit(base: Image.Image, layer: Image.Image, alpha: float) -> None:
    if alpha <= 0:
        return
    if alpha < 0.999:
        faded = layer.copy()
        bands = list(faded.split())
        bands[3] = bands[3].point(lambda px, amount=alpha: int(px * amount))
        faded = Image.merge("RGBA", bands)
        base.alpha_composite(faded)
    else:
        base.alpha_composite(layer)


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], content: str, face: ImageFont.FreeTypeFont, fill: tuple[int, int, int]) -> None:
    draw.text(xy, content, font=face, fill=fill + (255,))


def text_size(content: str, face: ImageFont.FreeTypeFont) -> tuple[int, int]:
    box = face.getbbox(content)
    return box[2] - box[0], box[3] - box[1]


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill: tuple[int, int, int], outline: tuple[int, int, int] | None = None) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill + (255,), outline=(outline + (255,)) if outline else None, width=2)


def center_text(draw: ImageDraw.ImageDraw, y: int, content: str, face: ImageFont.FreeTypeFont, fill: tuple[int, int, int]) -> None:
    width, _ = text_size(content, face)
    text(draw, ((W - width) // 2, y), content, face, fill)


DEMO = ROOT / "examples" / "readme-demo"
RAW_REQUEST = (DEMO / "objective.txt").read_text(encoding="utf-8").strip()
COMPILED_PROMPT = (DEMO / "prompt.txt").read_text(encoding="utf-8").strip()
ANSWERS = json.loads((DEMO / "answers.json").read_text(encoding="utf-8"))


def wrap_words(content: str, face: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in content.split(" "):
        trial = word if not current else f"{current} {word}"
        if text_size(trial, face)[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def block(label: str, body: str, face: ImageFont.FreeTypeFont) -> Image.Image:
    layer = new_layer()
    draw = ImageDraw.Draw(layer)
    text(draw, (140, 72), label, UI_XS, GOLD)
    y = 128
    leading = face.size + 10
    for para in body.splitlines():
        if not para.strip():
            y += leading // 2
            continue
        for line in wrap_words(para, face, 1640):
            text(draw, (140, y), line, face, CREAM)
            y += leading
    return layer


def answers_block() -> Image.Image:
    layer = new_layer()
    draw = ImageDraw.Draw(layer)
    text(draw, (140, 72), "CLARIFYING ANSWERS", UI_XS, GOLD)
    y = 128
    for question, answer in ANSWERS.items():
        for line in wrap_words(question, UI_S, 1600):
            text(draw, (140, y), line, UI_S, MUTED)
            y += 32
        for line in wrap_words(answer, UI, 1600):
            text(draw, (140, y), line, UI, CREAM)
            y += 42
        y += 16
    return layer


def render_frame(t: float) -> Image.Image:
    """Three artifacts from the run: objective, answers, compiled prompt."""
    base = Image.new("RGBA", (W, H), BG + (255,))
    if t < 8.4:
        blit(base, block("RAW REQUEST", RAW_REQUEST, UI_B), 1 - span(t, 7.6, 8.4))
    if 7.6 <= t < 20.4:
        blit(base, answers_block(), span(t, 7.6, 8.4) * (1 - span(t, 19.6, 20.4)))
    if t >= 19.6:
        blit(base, block("COMPILED PROMPT", COMPILED_PROMPT, UI_P), span(t, 19.6, 20.4))
    return base


def tone(t: float, freq: float, amp: float, attack: float, release: float) -> float:
    if t < 0 or t > attack + release:
        return 0.0
    if t < attack:
        env = t / attack
    else:
        env = 1 - (t - attack) / release
    return amp * env * math.sin(2 * math.pi * freq * t)


def write_audio(path: Path) -> None:
    rate = 48000
    count = int(rate * DURATION)
    hits = (
        (1.5, 220, 0.05, 0.01, 0.25),
        (6.4, 98, 0.16, 0.01, 0.28),
        (9.2, 262, 0.07, 0.01, 0.3),
        (15.5, 330, 0.08, 0.02, 0.4),
        (19.6, 392, 0.06, 0.02, 0.45),
    )
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        frames = bytearray()
        for index in range(count):
            t = index / rate
            sample = 0.035 * math.sin(2 * math.pi * 55 * t) + 0.015 * math.sin(2 * math.pi * 82.5 * t)
            for start, freq, amp, attack, release in hits:
                sample += tone(t - start, freq, amp, attack, release)
            sample = max(-1.0, min(1.0, sample))
            frames += struct.pack("<h", int(sample * 28000))
        handle.writeframes(frames)


def main() -> None:
    wav = OUT_MP4.with_suffix(".wav")
    write_audio(wav)
    poster_index = round(28.0 * FPS)
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{W}x{H}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-i",
        str(wav),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "20",
        "-preset",
        "medium",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
        "-shortest",
        str(OUT_MP4),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert process.stdin is not None
    for index in range(FRAMES):
        t = index / FPS
        frame = render_frame(t).convert("RGB")
        if index == poster_index:
            frame.save(OUT_JPG, quality=90)
        process.stdin.write(frame.tobytes())
    process.stdin.close()
    code = process.wait()
    wav.unlink(missing_ok=True)
    if code != 0:
        raise SystemExit(code)
    print(f"wrote {OUT_MP4}")
    print(f"wrote {OUT_JPG}")


if __name__ == "__main__":
    main()
