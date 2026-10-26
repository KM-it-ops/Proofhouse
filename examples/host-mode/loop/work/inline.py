from escape import escape_html


def render_inline(text: str) -> str:
    return _render(text, 0, len(text))


def _render(text: str, start: int, end: int) -> str:
    out: list[str] = []
    i = start
    while i < end:
        ch = text[i]
        if ch == "\\" and i + 1 < end:
            out.append(escape_html(text[i + 1]))
            i += 2
            continue
        if ch == "`":
            close = text.find("`", i + 1, end)
            if close == -1:
                out.append(escape_html(text[i:end]))
                break
            inner = text[i + 1 : close]
            out.append(f"<code>{escape_html(inner)}</code>")
            i = close + 1
            continue
        if ch == "[":
            link_end = _match_link(text, i, end)
            if link_end is not None:
                inner_html, next_i = link_end
                out.append(inner_html)
                i = next_i
                continue
        if text.startswith("**", i, end):
            close = text.find("**", i + 2, end)
            if close == -1:
                out.append(escape_html(text[i:end]))
                break
            inner = _render(text, i + 2, close)
            out.append(f"<strong>{inner}</strong>")
            i = close + 2
            continue
        if ch == "*":
            close = _find_em_close(text, i + 1, end)
            if close == -1:
                out.append(escape_html(ch))
                i += 1
                continue
            inner = _render(text, i + 1, close)
            out.append(f"<em>{inner}</em>")
            i = close + 1
            continue
        out.append(escape_html(ch))
        i += 1
    return "".join(out)


def _find_em_close(text: str, start: int, end: int) -> int:
    i = start
    while i < end:
        if text[i] == "\\" and i + 1 < end:
            i += 2
            continue
        if text[i] == "*":
            if text.startswith("**", i, end):
                return -1
            return i
        i += 1
    return -1


def _match_link(text: str, start: int, end: int) -> tuple[str, int] | None:
    bracket = start
    depth = 0
    i = start + 1
    label_end = -1
    while i < end:
        if text[i] == "\\" and i + 1 < end:
            i += 2
            continue
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            if depth == 0:
                label_end = i
                break
            depth -= 1
        i += 1
    if label_end == -1 or label_end + 1 >= end or text[label_end + 1] != "(":
        return None
    paren_start = label_end + 2
    depth = 1
    i = paren_start
    while i < end and depth:
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                url = text[paren_start:i]
                if url.lower().startswith("javascript:"):
                    return None
                label = _render(text, bracket + 1, label_end)
                href_attr = (
                    url.replace("&", "&amp;")
                    .replace('"', "&quot;")
                    .replace("<", "&lt;")
                )
                return (f'<a href="{href_attr}">{label}</a>', i + 1)
        i += 1
    return None
