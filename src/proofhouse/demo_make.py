"""`proofhouse demo make`: the real make path, replayed.

The questions, the say-back, the writing, the judging and the revision all run through the same code a real make
uses. Two things are recorded: the model's replies and the lines a person would type. So it needs no key and no
model, sends nothing anywhere and spends nothing. It says so on screen: a replay must never pass for a live run.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from . import live, make
from . import make_interview as mi

DATA_PATH = Path(__file__).resolve().parent / "data" / "demo_make.json"
MODEL = "recorded-demo"
_PROVIDER = "ollama"  # a provider on this machine: no key and a price of $0; the recorded replies answer for it


def recording() -> dict[str, Any]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


class Recorded:
    """Stands in for the model: answers each call from the recording, by what the call asks for."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.said_back = self.written = self.judged = 0
        self.calls: list[str] = []

    def _next(self, key: str, count: int) -> Any:
        items = self.data[key]
        return items[min(count, len(items) - 1)]

    def __call__(self, request: live.Request) -> live.Response:
        text = " ".join(str(m.get("content", "")) for m in json.loads(request.body_bytes)["messages"])
        if text.startswith("You are an expert prompt engineer. You generate"):
            role, content = "questions", json.dumps(self.data["questions"])
        elif text.startswith("You are about to write a"):
            role, content = "say back", self._next("say_back", self.said_back)
            self.said_back += 1
        elif text.startswith("You judge AI work"):
            role, content = "judge", json.dumps(self._next("judge", self.judged))
            self.judged += 1
        elif text.startswith("Improve the"):
            self.written = max(self.written, 1)
            role, content = "revise", self._next("versions", self.written)
            self.written += 1
        elif text.startswith("You write agent skills"):
            role, content = "write", self._next("versions", self.written)
            self.written += 1
        else:  # nothing else is part of this recording; an empty reply is handled like any model's
            role, content = "other", ""
        self.calls.append(role)
        return live.Response(200, {"choices": [{"message": {"content": content}}],
                                   "usage": {"prompt_tokens": 0, "completion_tokens": 0}})


def run(workspace: str | None = None, write: Callable[[str], None] | None = None) -> int:
    say = write or (lambda text: print(text, end="", flush=True))
    data = recording()
    typed = list(data["typed"])

    def read() -> str:
        line = typed.pop(0) if typed else ""
        say((line or "(Enter)") + "\n")
        return line

    # make wants a folder that does not exist yet, so the made thing goes one level down
    folder = (Path(workspace).resolve() if workspace else Path(tempfile.mkdtemp(prefix="proofhouse-demo-"))) / "make"
    say("This is a replay. Recorded replies stand in for the model and recorded lines stand in for you, so it needs\n"
        "no key and no model, sends nothing anywhere and costs nothing. Everything else is the real make.\n\n"
        f"You ask for: {data['request']}\nFor: {data['for']}\n")
    model = Recorded(data)
    try:
        made = make.make(data["request"], provider_id=_PROVIDER, model=MODEL, kind=data["kind"], out_dir=folder,
                         transport=model, interviewer=mi.TerminalInterviewer(read, say, data["for"], data["kind"]))
    except (make.MakeError, mi.InterviewError, OSError) as exc:
        say(f"\nerror: {exc}\n")
        return 2
    say("\n")
    for done in made.rounds:
        met = sum(1 for a in done.asked if a["met"])
        say(f"version {done.version}: judge score {done.score}/10, {met} of {len(done.asked)} asked-for items met\n")
        for a in done.asked:
            if not a["met"]:
                say(f"  not met: {a['item']} ({a['why']}), so it is revised\n")
    say(f"made: version {made.best_version} (judge score {made.best_score}/10); stopped: {made.stopped}\n")
    for line in make.closing(made)["lines"]:
        if "--judge" not in line:  # in a replay one recording wrote and judged; that advice is for a real make
            say(line + "\n")
    say(f"everything is in {made.folder}\n\n"
        "Now make your own. With a model on this machine (free):\n"
        '  proofhouse make "what you want" --kind skill --provider ollama --model <a model you have pulled>\n'
        "Or let the AI app you already use do it, with no terminal:\n"
        "  proofhouse connect\n"
        "Check what this machine has: proofhouse setup\n")
    return 0 if made.best_version else 1
