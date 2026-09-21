#!/usr/bin/env python3
"""Run the documented reference workflow end to end and fail on any unexpected result.

The flagship case: summarise a synthetic security advisory for SOC analysts
while preserving uncertainty, evidence and format requirements. Revision 1
fails real checks against a recorded output; revision 2 fixes them; compare,
report, export and import close the loop. Offline: outputs are imported text
files from examples/reference-advisory/, no model is called.

    python scripts/reference_workflow.py                       # uses this interpreter's package
    python scripts/reference_workflow.py --cli proofhouse-compiler   # uses an installed console script

docs/reference-workflow.md shows the same commands. tests/optimize/test_reference_workflow.py
and the wheel-install CI job run this script, so the documentation cannot drift.
"""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "reference-advisory"


class Step(Exception):
    pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cli", default=None, help="Console script to run (default: this interpreter's module).")
    parser.add_argument("--workspace", default=None, help="Directory to work in (default: a new temp directory).")
    parser.add_argument("--quiet", action="store_true", help="Print only the summary.")
    args = parser.parse_args(argv)

    cli = shlex.split(args.cli) if args.cli else [sys.executable, "-m", "proofhouse.compiler.cli_compiler"]
    workspace = (Path(args.workspace) if args.workspace else Path(tempfile.mkdtemp(prefix="proofhouse-reference-"))).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    for name in ("objective.txt", "advisory.txt", "answers.json", "prompt-v1.txt", "prompt-v2.txt", "output-v1.txt", "output-v2.txt"):
        shutil.copy(EXAMPLE / name, workspace / name)
    case = workspace / "advisory-case"
    started = time.monotonic()

    def run(*parts: str, expect: int = 0, as_json: bool = False) -> dict | str:
        command = [*cli, *parts, *(["--json"] if as_json else [])]
        completed = subprocess.run(command, cwd=workspace, capture_output=True, text=True, encoding="utf-8", check=False)
        if not args.quiet:
            print("$ proofhouse-compiler " + " ".join(parts))
            shown = completed.stdout.strip()
            if shown and not as_json:
                print("  " + "\n  ".join(shown.splitlines()[:12]))
        if completed.returncode != expect:
            raise Step(f"{' '.join(parts)} exited {completed.returncode}, expected {expect}\n{completed.stdout}\n{completed.stderr}")
        return json.loads(completed.stdout) if as_json else completed.stdout

    c = str(case)
    run("optimize", "new", "--case", c, "--objective-file", "objective.txt", "--model", "Claude Sonnet 5", "--preset", "efficient")
    shutil.copy(workspace / "answers.json", case / "answers.json")
    run("optimize", "compile", "--case", c)
    ledger = run("optimize", "constraints", "list", "--case", c, as_json=True)["data"]["constraints"]
    by_text = {entry["text"]: entry["id"] for entry in ledger}
    audience = next(k for t, k in by_text.items() if t.startswith("Who reads"))
    missing = next(k for t, k in by_text.items() if t.startswith("What if"))
    fmt = next(k for t, k in by_text.items() if t.startswith("Format"))
    cite = run("optimize", "constraints", "add", "--case", c, "--text", "Cite the advisory section for each claim", as_json=True)["data"]["constraint"]["id"]

    run("optimize", "criteria", "add", "--case", c, "--id", "AUD", "--must-contain", "SOC analysts")
    run("optimize", "criteria", "add", "--case", c, "--id", "UNK", "--target", "output", "--must-contain", "UNKNOWN")
    run("optimize", "criteria", "add", "--case", c, "--id", "NOGUESS", "--target", "output", "--must-not-contain", "exploited in the wild")
    run("optimize", "criteria", "add", "--case", c, "--id", "LEN", "--target", "output", "--max-words", "120")
    run("optimize", "criteria", "add", "--case", c, "--id", "CITE", "--target", "output", "--regex", r"\(s\d\)")
    run("optimize", "criteria", "add", "--case", c, "--id", "ACC", "--target", "output", "--manual", "Every claim matches the advisory")
    for kid, cid in ((audience, "AUD"), (missing, "UNK"), (missing, "NOGUESS"), (fmt, "LEN"), (cite, "CITE"), (cite, "ACC")):
        run("optimize", "constraints", "link", "--case", c, "--id", kid, "--criterion", cid)

    run("optimize", "record", "--case", c, "--prompt-file", "prompt-v1.txt")
    r1 = run("optimize", "output", "add", "--case", c, "--revision", "1", "--output-file", "output-v1.txt",
             "--input-id", "EC-2026-017", "--input-file", "advisory.txt", "--model", "Claude Sonnet 5",
             "--source", "pasted from host agent", as_json=True)["data"]["run"]["run_id"]
    run("optimize", "verdict", "--case", c, "--revision", "1", "--criterion", "ACC", "--run", r1, "--result", "fail",
        "--note", "claims active exploitation; the advisory does not say that")
    v1 = run("optimize", "check", "--case", c, expect=3, as_json=True)["data"]["revisions"][0]
    failed_v1 = sorted(row["id"] for row in v1["results"] if row["result"] != "PASS")
    if failed_v1 != ["ACC", "CITE", "NOGUESS", "UNK"]:
        raise Step(f"revision 1 should fail ACC, CITE, NOGUESS, UNK; failed {failed_v1}")

    run("optimize", "revise", "--case", c, "--feedback", "It claimed active exploitation, which the advisory never states, and cited nothing.")
    packet = (case / "03-revise-v1.md").read_text(encoding="utf-8")
    for needle in ("never guess exploitation status", "Cite the advisory section for each claim", "Tier-1 SOC analysts"):
        if needle not in packet:
            raise Step(f"revise packet lost the constraint: {needle}")
    run("optimize", "record", "--case", c, "--prompt-file", "prompt-v2.txt")
    r2 = run("optimize", "output", "add", "--case", c, "--revision", "2", "--output-file", "output-v2.txt",
             "--input-id", "EC-2026-017", "--input-file", "advisory.txt", "--model", "Claude Sonnet 5",
             "--source", "pasted from host agent", as_json=True)["data"]["run"]["run_id"]
    run("optimize", "verdict", "--case", c, "--revision", "2", "--criterion", "ACC", "--run", r2, "--result", "pass")
    v2 = run("optimize", "check", "--case", c, as_json=True)["data"]["revisions"][0]
    if v2["overall"] != "PASS" or {row["status"] for row in v2["constraints"]} != {"satisfied"}:
        raise Step(f"revision 2 should pass with every constraint satisfied: {v2}")

    comparison = run("optimize", "compare", "--case", c, "--from", "1", "--to", "2", as_json=True)["data"]
    changes = {row["id"]: row["change"] for row in comparison["criteria"]}
    expected = {"AUD": "still_passing", "UNK": "newly_passing", "NOGUESS": "newly_passing", "LEN": "still_passing",
                "CITE": "newly_passing", "ACC": "newly_passing"}
    if changes != expected:
        raise Step(f"unexpected comparison {changes}")
    run("optimize", "compare", "--case", c, "--from", "2", "--to", "1", expect=3)  # a regression stops promotion

    run("optimize", "report", "--case", c, "--out", "report.md")
    run("optimize", "export", "--case", c, "--out", "advisory-case.zip")
    second = workspace / "second-workspace" / "advisory-case"
    run("optimize", "import", "--bundle", "advisory-case.zip", "--case", str(second))
    again = run("optimize", "check", "--case", str(second), as_json=True)["data"]["revisions"][0]
    strip = lambda rep: {k: v for k, v in rep.items() if k not in {"run_id", "checked_at"}}  # noqa: E731
    if strip(again) != strip(v2):
        raise Step("the imported case does not reproduce the same check result")

    elapsed = time.monotonic() - started
    print(
        f"reference workflow: OK in {elapsed:.1f}s -- v1 FAIL {failed_v1}, v2 PASS with "
        f"{len(v2['constraints'])} constraints satisfied; export/import reproduced; workspace {workspace}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Step as exc:
        print(f"reference workflow: FAILED -- {exc}", file=sys.stderr)
        raise SystemExit(1) from None
