"""Turn a title into a URL slug."""

import re
import unicodedata


def slugify(title: str, max_length: int = 80) -> str:
    if not title:
        return ""

    nfkd = unicodedata.normalize("NFKD", title)
    text = "".join(c for c in nfkd if not unicodedata.combining(c)).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")

    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    if truncated.endswith("-"):
        return truncated.rstrip("-")
    last_dash = truncated.rfind("-")
    if last_dash > 0:
        return truncated[:last_dash]
    return truncated
