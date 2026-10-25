"""Host-mode writing and site readability checks (no network, no models)."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

_MIN_WORDS = {"copy": 25, "prompt": 40, "skill": 60}

_FILLER_PHRASES = (
    "game-changing",
    "cutting-edge",
    "state-of-the-art",
    "world-class",
    "revolutionary",
    "seamless",
    "seamlessly",
    "unlock the power",
    "take it to the next level",
    "best-in-class",
    "in today's fast-paced world",
    "leverage",
    "synergy",
    "robust solution",
    "innovative solution",
    "next-generation",
    "empower",
    "elevate your",
    "streamline your",
    "all-in-one solution",
    "effortless",
    "unparalleled",
    "delve",
    "tapestry",
    "it is important to note",
)

_FILLER_PATTERNS = tuple(
    (phrase, re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.IGNORECASE))
    for phrase in _FILLER_PHRASES
)

_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_CURRENCY_RE = re.compile(r"[$€£]\s*\d+|\d+\.\d{2}\b")
_CAPITAL_NAME = re.compile(r"^[A-Z][a-z]{2,}$")
_HEX_COLOR = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
_STYLE_BLOCK = re.compile(r"<style[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_STRIP_TAGS = re.compile(r"<[^>]+>")


def word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def body_after_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4 :].lstrip("\n")
    return text


def _find_filler_phrases(text: str) -> list[str]:
    found: list[str] = []
    for phrase, pattern in _FILLER_PATTERNS:
        if pattern.search(text):
            found.append(phrase)
    return found


def _has_specifics(text: str) -> bool:
    if re.search(r"\d", text):
        return True
    if _CURRENCY_RE.search(text):
        return True
    for chunk in re.split(r"(?<=[.!?])\s+|\n+", text):
        words = _WORD_RE.findall(chunk)
        for index, word in enumerate(words):
            if index and _CAPITAL_NAME.match(word):
                return True
    return False


def text_quality_rows(text: str, role: str) -> list[dict[str, Any]]:
    minimum = _MIN_WORDS.get(role, _MIN_WORDS["copy"])
    count = word_count(text)
    rows: list[dict[str, Any]] = [
        {
            "check": "length",
            "ok": count >= minimum,
            "detail": f"{count} words (need {minimum})" if count < minimum else f"{count} words",
        },
    ]
    phrases = _find_filler_phrases(text)
    if len(phrases) >= 2:
        rows.append({"check": "filler", "ok": False, "detail": ", ".join(phrases)})
    elif len(phrases) == 1:
        rows.append({"check": "filler", "ok": True, "detail": phrases[0]})
    else:
        rows.append({"check": "filler", "ok": True, "detail": ""})
    if role == "copy":
        ok = _has_specifics(text)
        rows.append({
            "check": "specifics",
            "ok": ok,
            "detail": "" if ok else "no digit, amount or proper name found",
        })
    return rows


def _shingles(text: str) -> set[tuple[str, ...]]:
    words = [w.casefold() for w in _WORD_RE.findall(text)]
    if len(words) < 3:
        return set()
    return {tuple(words[index : index + 3]) for index in range(len(words) - 2)}


def jaccard_shingle_overlap(left: str, right: str) -> float:
    a, b = _shingles(left), _shingles(right)
    if not a or not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def parts_differ_rows(part_texts: dict[str, str]) -> list[dict[str, Any]]:
    eligible = {part_id: text for part_id, text in part_texts.items() if word_count(text) >= 15}
    ids = sorted(eligible)
    for left_id in ids:
        for right_id in ids:
            if left_id >= right_id:
                continue
            overlap = jaccard_shingle_overlap(eligible[left_id], eligible[right_id])
            if overlap >= 0.5:
                percent = int(round(overlap * 100))
                return [{
                    "check": "parts differ",
                    "ok": False,
                    "detail": f"{left_id}/{right_id}: {percent}%",
                }]
    return [{"check": "parts differ", "ok": True, "detail": ""}]


def html_to_text(source: str) -> str:
    stripped = _TAG_RE.sub(" ", source)
    stripped = _STRIP_TAGS.sub(" ", stripped)
    return html.unescape(re.sub(r"\s+", " ", stripped)).strip()


def site_text_from_folder(folder: Path) -> str:
    chunks: list[str] = []
    for file in sorted(folder.rglob("*.html")):
        try:
            chunks.append(html_to_text(file.read_text(encoding="utf-8")))
        except OSError:
            continue
    return "\n".join(chunks)


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    raw = hex_color.lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    r = int(raw[0:2], 16) / 255
    g = int(raw[2:4], 16) / 255
    b = int(raw[4:6], 16) / 255
    return r, g, b


def _relative_luminance(rgb: tuple[float, float, float]) -> float:
    def channel(value: float) -> float:
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(foreground: str, background: str) -> float:
    l1 = _relative_luminance(_hex_to_rgb(foreground))
    l2 = _relative_luminance(_hex_to_rgb(background))
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _collect_css(folder: Path) -> str:
    chunks: list[str] = []
    style_css = folder / "style.css"
    if style_css.is_file():
        try:
            chunks.append(style_css.read_text(encoding="utf-8"))
        except OSError:
            pass
    index = folder / "index.html"
    if index.is_file():
        try:
            source = index.read_text(encoding="utf-8")
        except OSError:
            source = ""
        chunks.extend(match.group(1) for match in _STYLE_BLOCK.finditer(source))
    return "\n".join(chunks)


def _rule_blocks(css: str, selector: str) -> list[str]:
    pattern = re.compile(rf"{selector}\s*\{{([^}}]*)\}}", re.IGNORECASE)
    return [match.group(1) for match in pattern.finditer(css)]


def _property_hex(block: str, names: tuple[str, ...]) -> str | None:
    for name in names:
        match = re.search(rf"{name}\s*:\s*(#[0-9a-fA-F]{{3,6}})", block, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _plain_color_pair(css: str) -> tuple[str, str] | None:
    for block in _rule_blocks(css, r":root") + _rule_blocks(css, r"html"):
        text = _property_hex(block, ("--text", "color"))
        background = _property_hex(block, ("--bg", "background-color", "background"))
        if text and background:
            return text, background
    for block in _rule_blocks(css, r"body"):
        text = _property_hex(block, ("color",))
        background = _property_hex(block, ("background-color", "background"))
        if text and background:
            return text, background
    return None


def _body_font_size_px(css: str) -> float | None:
    for block in _rule_blocks(css, r"body"):
        match = re.search(r"font-size\s*:\s*([\d.]+)\s*(px|rem)\b", block, re.IGNORECASE)
        if not match:
            continue
        value = float(match.group(1))
        unit = match.group(2).lower()
        return value if unit == "px" else value * 16
    return None


class _IndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.h1_count = 0
        self.images_without_alt = 0
        self._in_title = False
        self._title_done = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "title" and not self._title_done:
            self._in_title = True
        if tag == "h1":
            self.h1_count += 1
        if tag == "img" and not values.get("alt", "").strip():
            self.images_without_alt += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._in_title:
            self._in_title = False
            self._title_done = True

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def site_readability_rows(folder: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    css = _collect_css(folder)
    pair = _plain_color_pair(css)
    if pair is None:
        rows.append({"check": "contrast", "ok": True, "detail": "no plain colour pair found"})
    else:
        ratio = contrast_ratio(pair[0], pair[1])
        rows.append({
            "check": "contrast",
            "ok": ratio >= 4.5,
            "detail": f"ratio {ratio:.2f}",
        })
    size_px = _body_font_size_px(css)
    if size_px is None:
        rows.append({"check": "text size", "ok": True, "detail": ""})
    else:
        rows.append({
            "check": "text size",
            "ok": size_px >= 16,
            "detail": f"{size_px:g}px",
        })
    index = folder / "index.html"
    parser = _IndexParser()
    if index.is_file():
        try:
            parser.feed(index.read_text(encoding="utf-8"))
        except OSError:
            pass
    rows.append({
        "check": "headings",
        "ok": parser.h1_count == 1,
        "detail": f"{parser.h1_count} h1",
    })
    missing = 0
    for page in sorted(folder.rglob("*.html")):
        page_parser = _IndexParser()
        try:
            page_parser.feed(page.read_text(encoding="utf-8"))
        except OSError:
            continue
        missing += page_parser.images_without_alt
    rows.append({
        "check": "image alt",
        "ok": missing == 0,
        "detail": f"{missing} without alt" if missing else "",
    })
    title = parser.title.strip()
    title_ok = 10 <= len(title) <= 70
    rows.append({
        "check": "title",
        "ok": title_ok,
        "detail": title[:70] if title else "missing",
    })
    return rows
