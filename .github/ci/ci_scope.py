#!/usr/bin/env python3
"""Classify a PromptRig change into the least expensive valid CI scope."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


DOC_SUFFIXES = {".md", ".txt", ".rst"}


def changed_files(base: str, head: str) -> list[str]:
    output = subprocess.check_output(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        text=True,
    )
    return [line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def classify(paths: list[str]) -> dict[str, object]:
    docs_only = bool(paths) and all(
        Path(path).suffix.lower() in DOC_SUFFIXES
        or path.startswith("docs/")
        or path.startswith("review-cycles/")
        for path in paths
    )

    requirements = any(
        path.startswith("architecture/requirements-compiler-contract-v0.1/")
        or path.startswith("tests/requirements/")
        for path in paths
    )
    compiler = any(
        path.startswith("src/promptrig/compiler/")
        or path.startswith("tests/compiler/")
        or path == "pyproject.toml"
        for path in paths
    )
    typescript = any(
        path.startswith("architecture/typescript/")
        or path.endswith(".schema.json")
        or path == "scripts/generate_typescript_contracts.py"
        for path in paths
    )

    if docs_only:
        scope = "docs"
    elif requirements and not compiler:
        scope = "requirements"
    elif compiler and not requirements:
        scope = "compiler"
    else:
        scope = "broad"

    return {
        "scope": scope,
        "typescript_drift": typescript,
        "changed_files": paths,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--github-output")
    args = parser.parse_args()

    result = classify(changed_files(args.base, args.head))
    print(json.dumps(result, indent=2))
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as handle:
            handle.write(f"scope={result['scope']}\n")
            handle.write(f"typescript_drift={str(result['typescript_drift']).lower()}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
