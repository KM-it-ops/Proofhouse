from escape import escape_html
from inline import render_inline


def split_blocks(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        return []
    blocks: list[str] = []
    lines = text.split("\n")
    i = 0
    n = len(lines)
    while i < n:
        while i < n and lines[i].strip() == "":
            i += 1
        if i >= n:
            break
        if lines[i].startswith("```"):
            chunk = [lines[i]]
            i += 1
            while i < n and not lines[i].startswith("```"):
                chunk.append(lines[i])
                i += 1
            if i < n:
                chunk.append(lines[i])
                i += 1
            blocks.append("\n".join(chunk))
            continue
        chunk = [lines[i]]
        i += 1
        while i < n and lines[i].strip() != "":
            if lines[i].startswith("```"):
                break
            chunk.append(lines[i])
            i += 1
        blocks.append("\n".join(chunk))
    return blocks


def _heading(block: str) -> str | None:
    if not block.startswith("#"):
        return None
    level = 0
    while level < len(block) and block[level] == "#":
        level += 1
    if level > 6 or level >= len(block) or block[level] != " ":
        return None
    inner = render_inline(block[level + 1 :])
    return f"<h{level}>{inner}</h{level}>"


def _unordered_list(block: str) -> str | None:
    lines = block.split("\n")
    if not lines or lines[0][:1] not in "-*+":
        return None
    items: list[str] = []
    for line in lines:
        if len(line) < 2 or line[1] != " " or line[0] not in "-*+":
            return None
        items.append(f"<li>{render_inline(line[2:])}</li>")
    return "<ul>" + "".join(items) + "</ul>"


def _ordered_list(block: str) -> str | None:
    lines = block.split("\n")
    if not lines:
        return None
    items: list[str] = []
    expect = 1
    for line in lines:
        dot = line.find(". ")
        if dot == -1:
            return None
        num_part = line[:dot]
        if not num_part.isdigit() or int(num_part) != expect:
            return None
        items.append(f"<li>{render_inline(line[dot + 2 :])}</li>")
        expect += 1
    return "<ol>" + "".join(items) + "</ol>"


def _fenced_code(block: str) -> str | None:
    if not block.startswith("```"):
        return None
    first_newline = block.find("\n")
    if first_newline == -1:
        lang = block[3:].strip()
        body = ""
    else:
        lang = block[3:first_newline].strip()
        rest = block[first_newline + 1 :]
        if rest.endswith("```"):
            body = rest[:-3]
            if body.endswith("\n"):
                body = body[:-1]
        else:
            body = rest
    escaped = escape_html(body)
    if lang:
        return f'<pre><code class="language-{escape_html(lang)}">{escaped}</code></pre>'
    return f"<pre><code>{escaped}</code></pre>"


def _blockquote(block: str) -> str | None:
    lines = block.split("\n")
    if not lines or not lines[0].startswith("> "):
        return None
    parts: list[str] = []
    for line in lines:
        if not line.startswith("> "):
            return None
        parts.append(line[2:])
    text = " ".join(parts)
    return f"<blockquote><p>{render_inline(text)}</p></blockquote>"


def _paragraph(block: str) -> str:
    lines = block.split("\n")
    text = " ".join(lines)
    return f"<p>{render_inline(text)}</p>"


def render_block(block: str) -> str:
    if block in ("---", "***"):
        return "<hr>"
    heading = _heading(block)
    if heading is not None:
        return heading
    ul = _unordered_list(block)
    if ul is not None:
        return ul
    ol = _ordered_list(block)
    if ol is not None:
        return ol
    fence = _fenced_code(block)
    if fence is not None:
        return fence
    quote = _blockquote(block)
    if quote is not None:
        return quote
    return _paragraph(block)
