"""Builds the Tidewatch demo assets with free local tools only: Pillow pictures, numpy music,
and the Windows speech lines from make_voice.ps1.
Run: uv run --no-sync --with pillow --with numpy python build_assets.py"""

from __future__ import annotations

import json
import math
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
W, H = 1280, 720
FONTS = Path("C:/Windows/Fonts")
NAVY, TEAL, INK = (8, 38, 71), (30, 140, 160), (20, 40, 60)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def gradient(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    ys = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(top) * (1 - ys) + np.array(bottom) * ys) * np.ones((H, W, 3))
    return Image.fromarray(arr.astype("uint8"), "RGB")


def waves(img: Image.Image, base: float, amp: float, color: tuple[int, int, int], alpha: int, phase: float, freq: float = 1.6) -> None:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pts = [
        (x, base + amp * math.sin(x / W * math.tau * freq + phase) + amp * 0.4 * math.sin(x / W * math.tau * freq * 2.3 + phase * 1.7))
        for x in range(0, W + 8, 8)
    ]
    d.polygon(pts + [(W, H), (0, H)], fill=color + (alpha,))
    img.paste(layer, (0, 0), layer)


def center(d: ImageDraw.ImageDraw, text: str, y: int, f: ImageFont.FreeTypeFont, fill: tuple[int, ...]) -> None:
    w = d.textlength(text, font=f)
    d.text(((W - w) / 2, y), text, font=f, fill=fill)


def glow_text(img: Image.Image, text: str, y: int, f: ImageFont.FreeTypeFont, fill: tuple[int, int, int]) -> None:
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    center(ImageDraw.Draw(glow), text, y, f, TEAL)
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    img.paste(Image.blend(img, Image.composite(glow, img, glow.convert("L")), 0.6))
    center(ImageDraw.Draw(img), text, y, f, fill)


def stars(img: Image.Image, seed: int) -> None:
    rng = np.random.default_rng(seed)
    d = ImageDraw.Draw(img)
    for _ in range(70):
        x, y, r = int(rng.integers(0, W)), int(rng.integers(0, 330)), int(rng.integers(1, 3))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(200, 225, 235))


def title_card(path: str, big: str, small: str) -> None:
    img = gradient((6, 28, 58), (14, 70, 100))
    stars(img, 3)
    waves(img, 470, 22, (20, 100, 130), 150, 0.4)
    waves(img, 540, 26, (14, 78, 112), 190, 2.1)
    waves(img, 610, 30, (8, 52, 88), 230, 4.0)
    glow_text(img, big, 190, font("seguisb.ttf", 150), (255, 255, 255))
    center(ImageDraw.Draw(img), small, 385, font("segoeuil.ttf", 38), (190, 225, 232))
    img.save(HERE / path)


def tide_curve(path: str) -> None:
    img = gradient((228, 245, 247), (150, 205, 215))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((250, 30, 1030, 525), 36, fill=(255, 255, 255), outline=(60, 120, 140), width=4)
    d.text((300, 54), "Harbor Point", font=font("seguisb.ttf", 40), fill=INK)
    d.text((300, 106), "Sat 25  -  next high 6:42 PM", font=font("segoeui.ttf", 28), fill=(70, 110, 125))
    pts = [(300 + i * 4, 360 - 110 * math.sin(i / 180 * math.tau + 0.6)) for i in range(0, 181)]
    d.polygon(pts + [(1020, 460), (300, 460)], fill=(190, 228, 236))
    d.line(pts, fill=TEAL, width=7, joint="curve")
    now = pts[78]
    d.line((now[0], now[1] + 18, now[0], 460), fill=NAVY, width=3)
    d.ellipse((now[0] - 16, now[1] - 16, now[0] + 16, now[1] + 16), fill=(255, 255, 255), outline=NAVY, width=6)
    for x, lab in ((300, "6 AM"), (660, "12 PM"), (1020, "6 PM")):
        d.text((x - 30, 470), lab, font=font("segoeui.ttf", 22), fill=(70, 110, 125))
    img.save(HERE / path)


def offline(path: str) -> None:
    img = gradient((238, 226, 196), (214, 190, 150))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((700, 20, 960, 540), 40, fill=INK)
    d.rounded_rectangle((714, 54, 946, 506), 22, fill=(236, 247, 249))
    for i, hgt in enumerate((18, 34, 50, 66)):
        x = 760 + i * 30
        d.rectangle((x, 160 - hgt, x + 18, 160), fill=(150, 160, 165))
    d.line((740, 90, 920, 185), fill=(200, 50, 40), width=12)
    d.text((740, 230), "Harbor Point", font=font("seguisb.ttf", 28), fill=INK)
    d.text((740, 275), "High 6:42 PM", font=font("segoeui.ttf", 26), fill=(70, 110, 125))
    d.text((740, 315), "Low 12:31 AM", font=font("segoeui.ttf", 26), fill=(70, 110, 125))
    d.rounded_rectangle((736, 375, 924, 427), 26, fill=TEAL)
    d.text((772, 384), "OFFLINE", font=font("seguisb.ttf", 30), fill=(255, 255, 255))
    d.text((110, 180), "No signal.", font=font("seguisb.ttf", 76), fill=INK)
    d.text((110, 280), "No problem.", font=font("segoeuil.ttf", 76), fill=(90, 70, 40))
    img.save(HERE / path)


def price(path: str) -> None:
    img = gradient((10, 56, 92), (24, 110, 138))
    waves(img, 560, 20, (30, 130, 155), 110, 1.0)
    waves(img, 620, 24, (10, 70, 100), 200, 3.0)
    d = ImageDraw.Draw(img)
    cx, cy, r = W // 2, 290, 210
    d.ellipse((cx - r - 12, cy - r - 12, cx + r + 12, cy + r + 12), fill=(255, 255, 255))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(236, 247, 249))
    d.ellipse((cx - r + 14, cy - r + 14, cx + r - 14, cy + r - 14), outline=TEAL, width=5)
    f = font("seguisb.ttf", 150)
    d.text((cx - d.textlength("$4.99", font=f) / 2, cy - 130), "$4.99", font=f, fill=NAVY)
    f2 = font("seguisb.ttf", 40)
    d.text((cx - d.textlength("ONE TIME", font=f2) / 2, cy + 50), "ONE TIME", font=f2, fill=TEAL)
    f3 = font("segoeuil.ttf", 32)
    d.text((cx - d.textlength("yours to keep", font=f3) / 2, cy + 110), "yours to keep", font=f3, fill=(70, 110, 125))
    img.save(HERE / path)


def checklist(path: str, items: list[str], head: str) -> None:
    img = gradient((236, 246, 247), (200, 226, 232))
    d = ImageDraw.Draw(img)
    d.text((140, 40), head, font=font("seguisb.ttf", 54), fill=INK)
    y = 140
    for label in items:
        d.rounded_rectangle((140, y, 1140, y + 110), 28, fill=(255, 255, 255), outline=(150, 190, 200), width=3)
        d.ellipse((176, y + 17, 252, y + 93), fill=(214, 70, 60))
        d.line((196, y + 37, 232, y + 73), fill=(255, 255, 255), width=9)
        d.line((232, y + 37, 196, y + 73), fill=(255, 255, 255), width=9)
        d.text((290, y + 24), label, font=font("segoeui.ttf", 50), fill=INK)
        y += 135
    img.save(HERE / path)


def end_card(path: str) -> None:
    img = gradient((4, 22, 46), (12, 62, 92))
    stars(img, 9)
    waves(img, 520, 18, (24, 112, 138), 140, 0.9)
    waves(img, 590, 24, (10, 60, 94), 220, 2.6)
    glow_text(img, "Tidewatch", 170, font("seguisb.ttf", 130), (255, 255, 255))
    center(ImageDraw.Draw(img), "$4.99  -  offline  -  no accounts  -  no ads", 330, font("segoeui.ttf", 30), (140, 190, 205))
    img.save(HERE / path)


def make_pictures() -> None:
    title_card("shot-01.png", "Tidewatch", "tide tables for people on the water")
    tide_curve("shot-02.png")
    offline("shot-03.png")
    price("shot-04.png")
    checklist("shot-05.png", ["No account to create", "No sign-in, ever", "No email asked for"], "No accounts")
    checklist("shot-06.png", ["No banner ads", "No video ads", "No tracking pop-ups"], "No ads")
    end_card("shot-07.png")


def tone(freq: float, n: int, sr: int, attack: float, release: float, harmonics: tuple[float, ...] = (1.0, 0.4, 0.15)) -> np.ndarray:
    t = np.arange(n) / sr
    sig = sum(a * np.sin(math.tau * freq * (k + 1) * t) for k, a in enumerate(harmonics))
    env = np.minimum(1, t / attack) * np.minimum(1, (n / sr - t) / release)
    return sig * env


def make_music(total: float, path: str) -> None:
    sr = 44100
    n = int(total * sr)
    out = np.zeros((n, 2))
    beat = 60 / 92
    bar = beat * 4
    chords = [(57, (60, 64, 67, 71)), (53, (57, 60, 64, 67)), (48, (55, 60, 64, 67)), (55, (59, 62, 66, 69))]

    def midi(m: int) -> float:
        return 440 * 2 ** ((m - 69) / 12)

    for b in range(int(total / bar) + 1):
        root, notes = chords[b % 4]
        start = int(b * bar * sr)
        length = min(int(bar * sr * 1.15), n - start)
        if length <= 0:
            break
        for m in notes:
            for detune, pan in ((0.997, 0.35), (1.003, 0.65)):
                s = tone(midi(m) * detune, length, sr, 0.8, 1.2, (1.0, 0.25)) * 0.05
                out[start:start + length, 0] += s * (1 - pan)
                out[start:start + length, 1] += s * pan
        for k in range(4):
            bs = start + int(k * beat * sr)
            bl = min(int(beat * 0.95 * sr), n - bs)
            if bl <= 0:
                continue
            note = root - 12 + (7 if k == 3 else 0)
            out[bs:bs + bl] += (tone(midi(note), bl, sr, 0.01, 0.35, (1.0, 0.5, 0.2)) * (0.22 if k == 0 else 0.14))[:, None]
        rng = np.random.default_rng(b)
        for k in range(8):
            ts = start + int(k * beat / 2 * sr)
            tl = min(int(0.07 * sr), n - ts)
            if tl <= 0:
                continue
            hit = rng.standard_normal(tl) * np.exp(-np.arange(tl) / (0.012 * sr)) * (0.05 if k % 2 == 0 else 0.03)
            out[ts:ts + tl] += hit[:, None]
    idx = np.arange(n)
    out *= (np.minimum(1, idx / (sr * 1.5)) * np.minimum(1, (n - idx) / (sr * 2.5)))[:, None]
    out *= 0.85 / max(1e-9, np.abs(out).max())
    with wave.open(str(HERE / path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((out * 32767).astype("<i2").tobytes())


def make_voice_track(durations: list[int], path: str) -> None:
    lines = sorted(HERE.glob("line-*.wav"))
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for f in lines:
        cmd += ["-i", str(f)]
    parts, start = [], 0
    for i, secs in enumerate(durations):
        parts.append(f"[{i}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={int((start + 0.2) * 1000)}:all=1[a{i}]")
        start += secs
    mix = "".join(f"[a{i}]" for i in range(len(lines)))
    parts.append(f"{mix}amix=inputs={len(lines)}:normalize=0,volume=1.25[out]")
    cmd += ["-filter_complex", ";".join(parts), "-map", "[out]", "-t", str(sum(durations)), str(HERE / path)]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    script = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
    secs = [s["seconds"] for s in script["shots"]]
    make_pictures()
    make_music(sum(secs), "music.wav")
    make_voice_track(secs, "voice.wav")
    print("assets built,", sum(secs), "seconds")
