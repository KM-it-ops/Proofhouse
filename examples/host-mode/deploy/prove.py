"""Show what `proofhouse deploy --dry-run` would do for the example site, with the network and process launching switched off.

Run from the repository root:  uv run --no-sync python examples/host-mode/deploy/prove.py

If the dry run tried to open a connection or start any program (the hosting tools), this script would stop with an error.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import socket
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SITE = ROOT / "examples" / "host-mode" / "site"
home = tempfile.mkdtemp(prefix="proofhouse-deploy-")
os.environ["PROOFHOUSE_HOME"] = home


def forbidden(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("the dry run tried to use the network or start a program")


socket.socket.connect = forbidden  # type: ignore[method-assign]
socket.socket.connect_ex = forbidden  # type: ignore[method-assign]
socket.getaddrinfo = forbidden  # type: ignore[assignment]
subprocess.Popen = forbidden  # type: ignore[misc,assignment]
subprocess.run = forbidden  # type: ignore[assignment]

from proofhouse import cli  # noqa: E402  (imported after the switches so nothing can slip past them)


def shown(text: str) -> str:
    for form, label in ((str(SITE), "<repo>/examples/host-mode/site"), (home, "<home>")):
        text = text.replace(form, label).replace(form.replace("\\", "\\\\"), label)
    return text


def run(*args: str) -> int:
    print(f"\n$ proofhouse {shown(' '.join(args))}")
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(args))
    print(shown((out.getvalue() + err.getvalue()).rstrip()) + f"\n[exit {code}]")
    return code


print("network and program launching are switched off for this whole run")
run("deploy", "--list")
for target in ("netlify", "vercel", "cloudflare", "surge"):
    run("deploy", str(SITE), "--to", target, "--dry-run", "--name", "tidewatch")
run("deploy", str(SITE), "--to", "netlify", "--dry-run", "--json")
run("deploy", str(SITE), "--to", "nowhere", "--dry-run")
empty = Path(home) / "not-a-site"
empty.mkdir()
run("deploy", str(empty), "--to", "netlify", "--dry-run")
left = sorted(p.name for p in Path(home).iterdir())
print(f"\nfiles the dry runs wrote into the Proofhouse home: {[n for n in left if n != 'not-a-site'] or 'none'}")
print("no deploy log was written:", not (Path(home) / "deploys.jsonl").exists())
