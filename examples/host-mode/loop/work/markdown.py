from blocks import render_block, split_blocks


def convert(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        return ""
    blocks = split_blocks(text)
    return "\n".join(render_block(b) for b in blocks)
