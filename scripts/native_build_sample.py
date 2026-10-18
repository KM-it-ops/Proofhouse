"""Build a fixed, committed app through the shipped platform build check."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from proofhouse import app_platforms


SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "native_build"


def prepare(folder: Path, platform_id: str) -> None:
    if platform_id == "pwa":
        shutil.copytree(SAMPLE / "pwa", folder)
        return
    source = "desktop" if platform_id in {"windows", "macos", "linux"} else platform_id
    shutil.copytree(SAMPLE / source, folder)
    web = folder / "www"
    shutil.copytree(SAMPLE / "web", web)


def main(argv: list[str] | None = None) -> int:
    shipped = {entry["id"]: entry for entry in app_platforms._read(app_platforms.SHIPPED)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=sorted(shipped))
    args = parser.parse_args(argv)
    entry = shipped[args.platform]
    with tempfile.TemporaryDirectory(prefix="proofhouse-native-sample-") as root:
        folder = Path(root) / "native-sample"
        prepare(folder, args.platform)
        static = app_platforms.static_checks(folder, entry)
        result = app_platforms.build_check(folder, entry, allow_commands=True, name="native-sample")
        print(json.dumps({"platform": args.platform, "static": static, "build": result}, indent=2))
        return 0 if all(check["ok"] is True for check in static) and result["ok"] is not False \
            and (result["ok"] is True or args.platform == "pwa") else 1


if __name__ == "__main__":
    raise SystemExit(main())
