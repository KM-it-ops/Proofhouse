"""One-off stdlib PNG title cards for the Tidewatch demo video (no third-party deps)."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

# Minimal 5x7 bitmap font (rows as bit strings, 1 = ink)
_GLYPHS: dict[str, list[str]] = {
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    "!": ["00100", "00100", "00100", "00100", "00000", "00100", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "00100", "00100"],
    ",": ["00000", "00000", "00000", "00000", "00100", "00100", "01000"],
    "$": ["00100", "01110", "10100", "01110", "00101", "01110", "00100"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
    "3": ["01110", "10001", "00001", "00110", "00001", "10001", "01110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    "a": ["00000", "00000", "01110", "00001", "01111", "10001", "01111"],
    "b": ["10000", "10000", "10110", "11001", "10001", "10001", "11110"],
    "c": ["00000", "00000", "01110", "10001", "10000", "10001", "01110"],
    "d": ["00001", "00001", "01101", "10011", "10001", "10001", "01111"],
    "e": ["00000", "00000", "01110", "10001", "11110", "10000", "01110"],
    "f": ["00110", "01001", "01000", "11100", "01000", "01000", "01000"],
    "g": ["00000", "00000", "01111", "10001", "01111", "00001", "01110"],
    "h": ["10000", "10000", "10110", "11001", "10001", "10001", "10001"],
    "i": ["00100", "00000", "01100", "00100", "00100", "00100", "01110"],
    "k": ["10000", "10000", "10101", "11010", "11100", "10100", "10010"],
    "l": ["01100", "00100", "00100", "00100", "00100", "00100", "01110"],
    "m": ["00000", "00000", "11010", "10101", "10101", "10001", "10001"],
    "n": ["00000", "00000", "10110", "11001", "10001", "10001", "10001"],
    "o": ["00000", "00000", "01110", "10001", "10001", "10001", "01110"],
    "p": ["00000", "00000", "11110", "10001", "11110", "10000", "10000"],
    "q": ["00000", "00000", "01101", "10011", "01111", "00001", "00011"],
    "r": ["00000", "00000", "10110", "11001", "10000", "10000", "10000"],
    "s": ["00000", "00000", "01111", "10000", "01110", "00001", "11110"],
    "t": ["01000", "01000", "11110", "01000", "01000", "01001", "00110"],
    "u": ["00000", "00000", "10001", "10001", "10001", "10011", "01101"],
    "v": ["00000", "00000", "10001", "10001", "10001", "01010", "00100"],
    "w": ["00000", "00000", "10001", "10001", "10101", "10101", "01010"],
    "x": ["00000", "00000", "10001", "01010", "00100", "01010", "10001"],
    "y": ["00000", "00000", "10001", "10001", "01111", "00001", "01110"],
    "z": ["00000", "00000", "11111", "00010", "00100", "01000", "11111"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "/": ["00001", "00010", "00100", "01000", "10000", "00000", "00000"],
}


def _wrap(text: str, max_chars: int = 42) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if len(trial) <= max_chars:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _draw_text(
    pixels: bytearray,
    width: int,
    height: int,
    lines: list[str],
    scale: int,
    color: tuple[int, int, int],
    y_start: int,
) -> None:
    line_height = 7 * scale + scale * 2
    for line_index, line in enumerate(lines):
        text_width = sum(6 * scale for _ in line)
        x = max(0, (width - text_width) // 2)
        y = y_start + line_index * line_height
        for ch in line:
            glyph = _GLYPHS.get(ch, _GLYPHS.get(ch.lower(), _GLYPHS[" "]))
            for row_index, row in enumerate(glyph):
                for col_index, bit in enumerate(row):
                    if bit != "1":
                        continue
                    for dy in range(scale):
                        for dx in range(scale):
                            px = x + col_index * scale + dx
                            py = y + row_index * scale + dy
                            if 0 <= px < width and 0 <= py < height:
                                offset = (py * width + px) * 3
                                pixels[offset : offset + 3] = bytes(color)
            x += 6 * scale


def _fill_gradient(
    pixels: bytearray,
    width: int,
    height: int,
    top: tuple[int, int, int],
    bottom: tuple[int, int, int],
) -> None:
    for y in range(height):
        t = y / max(height - 1, 1)
        color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        row = y * width * 3
        for x in range(width):
            offset = row + x * 3
            pixels[offset : offset + 3] = bytes(color)


def _write_png(path: Path, width: int, height: int, rgb_rows: bytes) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + rgb_rows[y * width * 3 : (y + 1) * width * 3] for y in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def render_card(path: Path, bg_top: tuple[int, int, int], bg_bottom: tuple[int, int, int], caption: str, scale: int = 4) -> None:
    width, height = 960, 540
    pixels = bytearray(width * height * 3)
    _fill_gradient(pixels, width, height, bg_top, bg_bottom)
    lines = _wrap(caption, max_chars=36 if len(caption) > 28 else 22)
    block_height = len(lines) * (7 * scale + scale * 2)
    y_start = (height - block_height) // 2
    _draw_text(pixels, width, height, lines, scale, (245, 248, 250), y_start)
    _write_png(path, width, height, bytes(pixels))


def main() -> None:
    folder = Path(__file__).resolve().parent
    cards = [
        ("shot-01.png", (15, 36, 51), (26, 77, 109), "Tidewatch", 6),
        ("shot-02.png", (232, 244, 248), (26, 77, 109), "Tide tables in your pocket, no signal required.", 3),
        ("shot-03.png", (246, 240, 230), (26, 77, 109), "Works fully offline with bundled tide data for two years", 3),
        ("shot-04.png", (26, 77, 109), (15, 36, 51), "$4.99 one-time purchase", 4),
        ("shot-05.png", (232, 244, 248), (196, 92, 62), "No accounts and no ads", 4),
    ]
    for name, top, bottom, caption, scale in cards:
        target = folder / name
        render_card(target, top, bottom, caption, scale)
        size = target.stat().st_size
        if size > 200_000:
            raise SystemExit(f"{name} is {size} bytes (max 200 KB)")


if __name__ == "__main__":
    main()
