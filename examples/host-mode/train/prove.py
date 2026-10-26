"""Prepare fine-tuning data with `proofhouse train data`, check it, and show that nothing is trained or paid for.

Run from the repository root:  uv run --no-sync python examples/host-mode/train/prove.py

The network and program launching are switched off, and no key is set, so even `train start` could not spend anything.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = "examples/host-mode/train"
home = tempfile.mkdtemp(prefix="proofhouse-train-")
os.environ["PROOFHOUSE_HOME"] = home
for name in [n for n in os.environ if n.endswith(("_API_KEY", "_TOKEN"))]:
    del os.environ[name]
os.chdir(ROOT)


def forbidden(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("tried to use the network or start a program")


socket.socket.connect = forbidden  # type: ignore[method-assign]
socket.socket.connect_ex = forbidden  # type: ignore[method-assign]
socket.getaddrinfo = forbidden  # type: ignore[assignment]
subprocess.Popen = forbidden  # type: ignore[misc,assignment]
subprocess.run = forbidden  # type: ignore[assignment]

from proofhouse import cli  # noqa: E402

failures: list[str] = []


def shown(text: str) -> str:
    for form, label in ((home, "<home>"), (str(ROOT), "<repo>")):
        text = text.replace(form, label).replace(form.replace("\\", "\\\\"), label)
    return text


def run(*args: str) -> tuple[int, str]:
    print(f"\n$ proofhouse {shown(' '.join(args))}")
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(args))
    text = shown((out.getvalue() + err.getvalue()).rstrip())
    print(text + f"\n[exit {code}]")
    return code, text


def expect(ok: bool, what: str) -> None:
    print(f"  {'PASS' if ok else 'FAIL'}: {what}")
    if not ok:
        failures.append(what)


def lines(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


system = Path(f"{HERE}/system-prompt.md").read_text(encoding="utf-8").strip()
out = Path(f"{HERE}/data")
shutil.rmtree(out, ignore_errors=True)
print("network, program launching and all *_API_KEY / *_TOKEN variables are switched off for this whole run")
print(f"input: {HERE}/tickets.jsonl has {len(Path(f'{HERE}/tickets.jsonl').read_text(encoding='utf-8').splitlines())} lines (20 invented tickets plus 1 deliberate duplicate)")

print("\n== PREPARE THE DATA ==")
code, _ = run("train", "data", f"{HERE}/tickets.jsonl", "--out", f"{HERE}/data", "--system", system)
expect(code == 0, "train data exits 0")
train_rows, valid_rows = lines(out / "train.jsonl"), lines(out / "valid.jsonl")
summary = json.loads((out / "data.json").read_text(encoding="utf-8"))
print("\ndata.json:", json.dumps({k: v for k, v in summary.items()}))
print("\nfirst line of train.jsonl:\n" + json.dumps(train_rows[0], indent=2))

print("\n== CHECKS ON THE OUTPUT (done here, independently of Proofhouse) ==")
categories, priorities = {"billing", "account", "bug", "feature-request"}, {"high", "medium", "low"}
expect(summary["examples"] == 20, "the duplicate line was dropped: 21 lines in, 20 examples")
expect((len(train_rows), len(valid_rows)) == (18, 2), "18 to train on and 2 held out to check")
every = train_rows + valid_rows
expect(all([m["role"] for m in row["messages"]] == ["system", "user", "assistant"] for row in every), "every example is system, user, assistant in that order")
expect(all(row["messages"][0]["content"] == system for row in every), "the system message is the same in every example")
labels = [str(row["messages"][2]["content"]).split(" | ") for row in every]
expect(all(len(p) == 2 and p[0] in categories and p[1] in priorities for p in labels), "every answer is '<category> | <priority>' from the allowed lists")
expect({json.dumps(r) for r in train_rows}.isdisjoint({json.dumps(r) for r in valid_rows}), "no example is both trained on and held out")
expect(set(c for c, _ in labels) == categories, "all four categories appear")

print("\n== BAD DATA IS REFUSED ==")
bad = Path(home) / "bad.jsonl"
bad.write_text('{"input": "My invoice is wrong"}\n', encoding="utf-8")
code, text = run("train", "data", str(bad), "--out", str(Path(home) / "bad-out"))
expect(code != 0 and "needs messages, or an input and an output" in text and not (Path(home) / "bad-out").exists(), "a ticket with no answer stops the run and writes nothing")
small = Path(home) / "small.jsonl"
small.write_text("".join(json.dumps({"input": f"ticket {i}", "output": "bug | low"}) + "\n" for i in range(4)), encoding="utf-8")
code, text = run("train", "data", str(small), "--out", str(Path(home) / "small-out"))
expect("only 4 examples" in text, "too few examples gives a warning")

print("\n== NO MODEL IS TRAINED OR PAID FOR ==")
os.chdir(home)  # train start leaves a record folder in the current folder, so run it in the throwaway one
code, text = run("train", "start", "--service", "openai", "--model", "gpt-4.1-mini", "--data", str(ROOT / HERE / "data"))
expect(code != 0 and "OPENAI_API_KEY" in text, "train start without an OPENAI_API_KEY is refused")
record = next(Path(home).glob("train-openai-*/train.json"))
refusal = json.loads(record.read_text(encoding="utf-8"))
print("refusal record:", json.dumps({k: refusal[k] for k in ("status", "job_id", "trained_model", "message")}))
expect(refusal["status"] == "refused" and refusal["job_id"] is None and refusal["trained_model"] is None, "the record says refused: no job, no trained model")
os.chdir(ROOT)
print("data prepared is plain files in", f"{HERE}/data:", sorted(p.name for p in out.iterdir()))

shutil.rmtree(home, ignore_errors=True)
print("\nRESULT:", "FAILED: " + "; ".join(failures) if failures else "all checks passed")
raise SystemExit(1 if failures else 0)
