"""Agents that run on their own: watch, act, check, repeat, inside one spending limit.

Each round, the model sees the goal, the folder it works in, what happened in the
last rounds, and (when you gave them) the output of your watch command and your
check command. It answers with actions: read a file, write a file, or run a
command (only with ``allow_commands``). Proofhouse carries them out in the folder
and records the round.

The loop stops when your check command passes, when the agent says it is done
(and the check, if any, passes), when the rounds or the time run out, when the
next call would cross the spending limit, or when you press Ctrl-C. With a watch
command and ``every``, a round whose watch output did not change sends nothing
and costs nothing.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable

from . import __version__, live, media, providers
from .make import Budget, _slug

MAX_ACTIONS = 10
MAX_READ = 20_000
MAX_OUTPUT = 4_000
HISTORY = 6

_AGENT = """You are an agent working on your own toward a goal, in a folder on the user's machine.
Each round you get the goal, the files in the folder, what happened in recent rounds, and any
watch or check output. Answer with ONE JSON object and nothing else:

{"thinking": "one or two sentences", "actions": [ ... ], "done": false, "summary": "what you did this round"}

Actions (at most 10 per round, carried out in order):
  {"read": "<a file name from the list, such as notes.txt>"}
  {"write": "<the file name to create or replace>", "text": "the whole new file content"}
  {"run": "a shell command, run in the folder"}%s

Set "done": true only when the goal is fully met. Paths must stay inside the folder.

GOAL:
%s"""

_PLACEHOLDER_PATHS = {"relative/path", "path", "path/to/file", "filename", "file name", "file_name", "your/path"}

_NO_COMMANDS ="\n(Running commands is switched off for this agent: use read and write only.)"


class LoopError(ValueError):
    """The loop cannot start as asked."""


@dataclass
class Step:
    round: int
    when: str
    sent: bool
    thinking: str = ""
    summary: str = ""
    actions: list[dict[str, Any]] = field(default_factory=list)
    check: dict[str, Any] | None = None
    watch_changed: bool | None = None
    call: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"round": self.round, "when": self.when, "sent": self.sent, "thinking": self.thinking, "summary": self.summary,
                "actions": self.actions, "check": self.check, "watch_changed": self.watch_changed, "call": self.call}


@dataclass
class LoopResult:
    folder: Path
    workdir: Path
    stopped: str = "rounds used up"
    done: bool = False
    steps: list[Step] = field(default_factory=list)
    spent_usd: Decimal = Decimal(0)

    @property
    def calls(self) -> int:
        return sum(1 for s in self.steps if s.sent)


class _Stop(Exception):
    pass


def _secrets() -> list[str]:
    """Key values for every known provider and media service, so command output never carries them anywhere."""
    names: set[str] = set()
    try:
        names |= {p.key_env for p in providers.all_providers().values() if p.key_env}
        names |= {p.key_env for p in media.all_media_providers().values() if p.key_env}
    except (providers.ProviderError, media.MediaError):
        pass
    return [value for name in names if len(value := os.environ.get(name, "")) >= 6]


def _clean(text: str, secrets: list[str], limit: int = MAX_OUTPUT) -> str:
    for value in secrets:
        text = text.replace(value, "[redacted]")
    return text if len(text) <= limit else "…" + text[-limit:]


def _shell(command: str, cwd: Path, timeout: int, secrets: list[str]) -> dict[str, Any]:
    # No bytecode caches: an edit of the same size in the same second would otherwise run the old Python file.
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        run = subprocess.run(command, shell=True, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"exit": None, "output": f"stopped after {timeout} seconds"}
    except OSError as exc:
        return {"exit": None, "output": f"could not start: {exc}"}
    return {"exit": run.returncode, "output": _clean((run.stdout or "") + (run.stderr or ""), secrets)}


def _inside(workdir: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise LoopError("a path is missing")
    if relative.strip().strip("\"'<>").lower() in _PLACEHOLDER_PATHS:
        raise LoopError(f"{relative!r} is a placeholder, not a real file name; use a real name")
    target = (workdir / relative).resolve()
    if not target.is_relative_to(workdir):
        raise LoopError(f"{relative!r} is outside the folder")
    return target


def _listing(workdir: Path, limit: int = 200) -> str:
    names = []
    for path in sorted(workdir.rglob("*")):
        parts = path.relative_to(workdir).parts
        if any(part.startswith(".") or part in {"node_modules", "__pycache__", "venv"} for part in parts):
            continue
        names.append(path.relative_to(workdir).as_posix() + ("/" if path.is_dir() else ""))
        if len(names) >= limit:
            names.append("… (more not shown)")
            break
    return "\n".join(names) or "(empty)"


def _plan(text: str | None) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text or "", flags=re.S)
    try:
        data = json.loads(match.group(0)) if match else None
    except ValueError:
        data = None
    if not isinstance(data, dict):
        return {"thinking": "", "actions": [], "done": False, "summary": "the model did not answer with the JSON asked for"}
    actions = data.get("actions") if isinstance(data.get("actions"), list) else []
    return {"thinking": str(data.get("thinking") or ""), "actions": actions[:MAX_ACTIONS],
            "done": data.get("done") is True, "summary": str(data.get("summary") or "")}


def _act(action: Any, workdir: Path, allow_commands: bool, timeout: int, secrets: list[str]) -> dict[str, Any]:
    if not isinstance(action, dict):
        return {"action": "unknown", "ok": False, "result": "an action must be a JSON object"}
    try:
        if "read" in action:
            target = _inside(workdir, action["read"])
            if not target.is_file():
                return {"action": f"read {action['read']}", "ok": False, "result": "no such file"}
            text = target.read_text(encoding="utf-8", errors="replace")
            return {"action": f"read {action['read']}", "ok": True, "result": _clean(text, secrets, MAX_READ)}
        if "write" in action:
            target = _inside(workdir, action["write"])
            text = action.get("text")
            if not isinstance(text, str):
                return {"action": f"write {action['write']}", "ok": False, "result": "write needs text"}
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            return {"action": f"write {action['write']}", "ok": True, "result": f"{len(text.encode('utf-8'))} bytes written"}
        if "run" in action:
            command = str(action["run"])
            if not allow_commands:
                return {"action": f"run {command}", "ok": False, "result": "running commands is switched off for this agent"}
            outcome = _shell(command, workdir, timeout, secrets)
            return {"action": f"run {command}", "ok": outcome["exit"] == 0, "result": f"exit {outcome['exit']}\n{outcome['output']}"}
    except (LoopError, OSError) as exc:
        return {"action": json.dumps(action)[:120], "ok": False, "result": str(exc)}
    return {"action": json.dumps(action)[:120], "ok": False, "result": "unknown action; use read, write or run"}


def _state(workdir: Path, steps: list[Step], watch: str | None, check: dict[str, Any] | None) -> str:
    lines = [f"FILES IN THE FOLDER:\n{_listing(workdir)}"]
    recent = [s for s in steps if s.sent][-HISTORY:]
    if recent:
        lines.append("RECENT ROUNDS:")
        for step in recent:
            lines.append(f"round {step.round}: {step.summary}")
            for done in step.actions:
                lines.append(f"  {'ok' if done['ok'] else 'FAILED'} {done['action']}\n    {done['result'][:1500]}")
            if step.check is not None:
                lines.append(f"  check: exit {step.check['exit']}")
    if watch is not None:
        lines.append(f"WATCH OUTPUT NOW:\n{watch}")
    if check is not None:
        lines.append(f"CHECK COMMAND RIGHT NOW: exit {check['exit']}\n{check['output']}")
    return "\n\n".join(lines)


def run_loop(
    goal: str,
    *,
    provider_id: str,
    model: str,
    workdir: Path,
    check: str | None = None,
    watch: str | None = None,
    every: float | None = None,
    max_rounds: int = 20,
    max_seconds: float | None = None,
    max_cost_usd: str | None = None,
    allow_commands: bool = False,
    command_timeout: int = 300,
    out_dir: Path | None = None,
    max_output_tokens: int = 4096,
    transport: live.Transport | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> LoopResult:
    if not goal.strip():
        raise LoopError("say what the agent should get done")
    if type(max_rounds) is not int or not 1 <= max_rounds <= 1000:
        raise LoopError("rounds must be 1 to 1000")
    if every is not None and every < 0:
        raise LoopError("--every must be zero or more seconds")
    if watch is not None and not every:
        raise LoopError("a watch needs --every (seconds between looks)")
    workdir = workdir.resolve()
    if not workdir.is_dir():
        raise LoopError(f"{workdir} is not a folder")
    profile = providers.find(provider_id)
    if profile is None:
        raise LoopError(f"no provider named {provider_id!r}; see `proofhouse providers list`")
    if max_cost_usd is None and not profile.local:
        raise LoopError("name a spending limit for the whole loop (--max-cost-usd)")
    try:
        budget = Budget(max_cost_usd, profile.local)
    except InvalidOperation:
        raise LoopError("--max-cost-usd must be a decimal such as 2.00") from None

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    folder = (out_dir or Path.cwd() / f"loop-{_slug(goal)}-{stamp}").resolve()
    if folder.exists():
        raise LoopError(f"{folder} already exists; pick a new folder with --out, or remove it first")
    folder.mkdir(parents=True, exist_ok=False)
    result = LoopResult(folder, workdir)
    secrets = _secrets()
    system = _AGENT % ("" if allow_commands else _NO_COMMANDS, goal)
    started = clock()
    last_watch: str | None = None
    last_check: dict[str, Any] | None = None  # the check run right after the last round, still failing
    sent_rounds = 0
    number = 0

    def record(step: Step) -> None:
        result.steps.append(step)
        with (folder / "rounds.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(step.to_dict(), sort_keys=True) + "\n")
        _write_record(folder, goal, profile.id, model, max_cost_usd, check, watch, every, allow_commands, result, budget)

    try:
        while True:
            if max_seconds is not None and clock() - started >= max_seconds:
                raise _Stop("time limit reached")
            number += 1
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            watch_output = None
            if watch is not None:
                outcome = _shell(watch, workdir, command_timeout, secrets)
                watch_output = f"exit {outcome['exit']}\n{outcome['output']}"
                if last_watch is not None and watch_output == last_watch:
                    record(Step(number, now, sent=False, summary="nothing changed; nothing sent", watch_changed=False))
                    sleep(every or 0)
                    continue
                last_watch = watch_output
            if sent_rounds >= max_rounds:
                raise _Stop("rounds used up")
            check_now = None
            if check:
                check_now = last_check if last_check is not None and watch is None else _shell(check, workdir, command_timeout, secrets)
            if check_now is not None and check_now["exit"] == 0 and watch is None:
                result.done = True
                raise _Stop("check passed")
            limit = budget.for_next_call()
            if limit == "0":
                raise _Stop("spending limit reached")
            reply = live.run_prompt(profile.id, model, prompt=system, input_text=_state(workdir, result.steps, watch_output, check_now),
                                    max_output_tokens=max_output_tokens, max_cost_usd=limit, transport=transport)
            budget.charge(reply)
            cost = reply.cost or {}
            call = {"status": reply.status, "code": reply.code, "tokens_in": cost.get("tokens_in"),
                    "tokens_out": cost.get("tokens_out"), "usd": cost.get("usd")}
            if reply.code == "PHC-COST-0001":
                raise _Stop("spending limit reached")
            if reply.status != "success":
                raise _Stop(reply.message or "the model call failed")
            sent_rounds += 1
            plan = _plan(reply.output_text)
            step = Step(number, now, sent=True, thinking=plan["thinking"], summary=plan["summary"], call=call,
                        watch_changed=True if watch is not None else None)
            step.actions = [_act(action, workdir, allow_commands, command_timeout, secrets) for action in plan["actions"]]
            if check:
                step.check = last_check = _shell(check, workdir, command_timeout, secrets)
            record(step)
            if step.check is not None and step.check["exit"] == 0 and watch is None:
                result.done = True
                raise _Stop("check passed")
            if plan["done"] and check is None and watch is None:
                result.done = True
                raise _Stop(f"the agent says it is done: {plan['summary']}".rstrip(": "))
            if every:
                sleep(every)
    except _Stop as stop:
        result.stopped = str(stop)
    except KeyboardInterrupt:
        result.stopped = "stopped by you"
    result.spent_usd = budget.spent
    _write_record(folder, goal, profile.id, model, max_cost_usd, check, watch, every, allow_commands, result, budget)
    return result


def _write_record(folder: Path, goal: str, provider: str, model: str, limit: str | None, check: str | None, watch: str | None,
                  every: float | None, allow_commands: bool, result: LoopResult, budget: Budget) -> None:
    record = {
        "proofhouse_version": __version__, "goal": goal, "provider": provider, "model": model, "workdir": str(result.workdir),
        "max_cost_usd": limit, "check": check, "watch": watch, "every_seconds": every, "commands_allowed": allow_commands,
        "stopped": result.stopped, "done": result.done, "rounds": len(result.steps), "calls": result.calls,
        "spent_usd_estimated": format(budget.spent, "f"),
        "note": "Dollar figures are estimates from token counts and prices, not your bill.",
    }
    (folder / "loop.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
