"""Static proof: nothing under src/proofhouse/optimize/ imports a network module."""

from __future__ import annotations

import ast
from pathlib import Path

import proofhouse.optimize

PACKAGE_DIR = Path(proofhouse.optimize.__file__).resolve().parent
FORBIDDEN = frozenset({"socket", "urllib", "http", "httpx", "requests", "ssl", "asyncio"})


def _top_level(module_name: str | None) -> str:
    return (module_name or "").split(".")[0]


def test_optimize_package_imports_no_network_modules() -> None:
    sources = sorted(PACKAGE_DIR.rglob("*.py"))
    assert sources, PACKAGE_DIR
    offenders: list[str] = []
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [_top_level(alias.name) for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [_top_level(node.module)] if node.level == 0 else []
            else:
                continue
            for name in names:
                if name in FORBIDDEN:
                    offenders.append(f"{path.relative_to(PACKAGE_DIR)}:{node.lineno} imports {name}")
    assert offenders == []
