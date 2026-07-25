#!/usr/bin/env python3
"""Validate local links in changed Markdown files."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def changed_markdown(base: str, head: str) -> list[Path]:
    output = subprocess.check_output(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        text=True,
    )
    return [
        Path(path)
        for path in output.splitlines()
        if path.lower().endswith(".md") and Path(path).exists()
    ]


def validate(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for raw in LINK.findall(text):
            target = raw.strip().split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:", "tel:", "#")):
                continue
            target = unquote(target).strip("<>")
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"{path}: broken local link -> {raw}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()

    errors = validate(changed_markdown(args.base, args.head))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Markdown local links: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
