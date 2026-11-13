"""`proofhouse mcp`: Proofhouse as tools an AI app can call, so nobody has to open a terminal.

The app (Claude Code, Cursor, Codex, or any app that speaks the Model Context Protocol) starts this itself and
talks to it over stdin and stdout. The tools drive the same make the command line runs, through the places where
the interview already pauses: which tool it is for, the questions, the say-back. Nothing here can skip them. The
answers step never confirms, and the confirm step refuses until a say-back exists.

A make takes longer than an app waits for one tool call, so each step runs in the background. A call waits a
short while and otherwise answers "still working"; `make_status` picks it up.

The writing can be done by the app's own logged-in model at $0: a call to an agent bridge address
(`agent-<name>`, see agent_server.py) is answered by running that agent here, so no bridge has to be started.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TextIO
from urllib.parse import urlsplit

from . import __version__, agent_server, live, make, providers
from . import make_interview as mi

PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
SESSION_FILE = "chat-session.json"
WAIT_SECONDS = 40.0
MAKES_DIR_ENV = "PROOFHOUSE_MAKES_DIR"

_ASK_FIRST = ("Ask the person; never answer for them. ")
_SHOW = "Show the person this say-back word for word, then call make_confirm with what they said."


class ToolError(Exception):
    """Something the caller can put right; said back in plain words, never a stack trace."""


def _agent_at(url: str) -> tuple[str, dict[str, Any]] | None:
    """The agent whose bridge address this is, when the address is on this machine."""
    parts = urlsplit(url)
    if parts.hostname not in ("127.0.0.1", "localhost", "::1"):
        return None
    for name, entry in agent_server.load_agents().items():
        if entry.get("port") == parts.port:
            return name, entry
    return None


def agent_transport(runner: agent_server.Runner = agent_server.run_agent,
                    timeout: float = agent_server.DEFAULT_TIMEOUT_SECONDS,
                    otherwise: live.Transport | None = None) -> live.Transport:
    """A sender that answers agent bridge addresses by running the agent here; everything else goes out as usual."""

    def send(request: live.Request) -> Any:
        found = _agent_at(request.url)
        if found is None:
            return otherwise(request) if otherwise is not None else live.PASS_ON  # the send step sends it
        name, entry = found
        try:
            return live.Response(200, agent_server.complete(name, entry, json.loads(request.body_bytes), runner, timeout))
        except agent_server.AgentError as exc:
            return live.Response(502, {"error": {"message": str(exc)}})

    return send


def agents_here(which: Callable[[str], str | None] = shutil.which) -> list[str]:
    """Agents that are installed and that `proofhouse connect` has declared as a provider."""
    found = []
    for name, entry in agent_server.load_agents().items():
        argv = entry.get("argv") or [""]
        profile = providers.find(f"agent-{name}")
        if which(str(argv[0])) and profile is not None and profile.local:
            found.append(name)
    return found


@dataclass
class Job:
    folder: Path
    settings: dict[str, Any]
    thread: threading.Thread | None = None
    made: Any = None
    error: str | None = None
    shown: str | None = None  # the say-back last handed to the app; only that one can be confirmed
    lock: threading.Lock = field(default_factory=threading.Lock)


class Tools:
    """The tools themselves, apart from the protocol, so they can be driven directly."""

    def __init__(self, agent: str | None = None, base: Path | None = None, transport: live.Transport | None = None,
                 wait: float = WAIT_SECONDS, which: Callable[[str], str | None] = shutil.which) -> None:
        self.agent, self.wait, self.which = agent, wait, which
        self.base = base or Path(os.environ.get(MAKES_DIR_ENV) or Path.cwd())
        self.transport = transport or agent_transport()
        self.jobs: dict[str, Job] = {}

    # -- which model writes, and which judges ----------------------------------------------------------------
    def _writer(self, provider: str | None, model: str | None) -> tuple[str, str]:
        if provider:
            if not model and not provider.startswith("agent-"):
                raise ToolError(f"name a model for {provider} (see `proofhouse providers list`)")
            return provider, model or "default"
        here = agents_here(self.which)
        chosen = self.agent if self.agent in here else (here[0] if here else None)
        if chosen is None:
            raise ToolError(
                "No model is set up for chat makes yet. Either run `proofhouse connect` once (it lets the AI app "
                "you are logged in to do the writing at no extra cost), or pass provider and model, for example "
                "provider \"ollama\" with a model you have pulled.")
        return f"agent-{chosen}", model or "default"

    def _judge(self, writer: str, judge: str | None) -> str | None:
        if judge or not writer.startswith("agent-"):
            return judge
        other = next((name for name in agents_here(self.which) if f"agent-{name}" != writer), None)
        return f"agent-{other}/default" if other else None

    # -- finding a make --------------------------------------------------------------------------------------
    def _job(self, args: dict[str, Any]) -> Job:
        named = args.get("make")
        if not isinstance(named, str) or not named.strip():
            raise ToolError("say which make: pass `make`, the folder make_start gave you")
        folder = Path(named)
        try:  # only a folder make_start made here: a folder planted elsewhere could carry its own settings
            ours = folder.resolve().parent == self.base.resolve()
        except OSError:
            ours = False
        if not ours:
            raise ToolError(f"{folder} is not a make started from chat here (those are kept in {self.base}); "
                            "start one with make_start")
        job = self.jobs.get(str(folder))
        if job is not None:
            return job
        try:
            settings = json.loads((folder / SESSION_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise ToolError(f"{folder} is not a make started from chat; start one with make_start") from None
        if not isinstance(settings, dict) or not isinstance(settings.get("request"), str):
            raise ToolError(f"{folder / SESSION_FILE} is damaged; start a new make with make_start")
        job = self.jobs[str(folder)] = Job(folder, settings)
        return job

    def _busy(self, job: Job) -> bool:
        return job.thread is not None and job.thread.is_alive()

    # -- one step of the make --------------------------------------------------------------------------------
    def _step(self, job: Job) -> dict[str, Any]:
        settings = job.settings

        def work() -> None:
            try:
                answers = job.folder / "answers.json"
                interviewer = mi.FileInterviewer(answers if answers.is_file() else None, settings.get("for"), "for")
                job.made = make.make(
                    settings["request"], provider_id=settings["provider"], model=settings["model"],
                    kind=settings["kind"], max_cost_usd=settings.get("max_cost_usd"), out_dir=job.folder,
                    judge=settings.get("judge"), interviewer=interviewer, transport=self.transport)
            except (make.MakeError, mi.InterviewError, providers.ProviderError, OSError) as exc:
                job.error = str(exc)
            except Exception as exc:  # noqa: BLE001 -- a step that dies silently would read as "still working" forever
                job.error = f"{type(exc).__name__}: {exc}"
            if job.folder.is_dir():
                try:
                    providers.write_atomic(job.folder / SESSION_FILE, json.dumps(settings, indent=2, sort_keys=True))
                except OSError:
                    pass

        job.made, job.error = None, None
        job.thread = threading.Thread(target=work, daemon=True, name="proofhouse-make")
        job.thread.start()
        return self._report(job)

    def _report(self, job: Job) -> dict[str, Any]:
        base: dict[str, Any] = {"make": str(job.folder)}
        if job.thread is not None:
            job.thread.join(self.wait)
        if self._busy(job):
            return {**base, "stage": "working",
                    "next": "Still working. Tell the person it is under way, then call make_status with this make."}
        if job.error is not None:
            return {**base, "stage": "error", "error": job.error}
        if (job.folder / "record.json").is_file():
            return {**base, **self._done(job)}
        try:
            saved = mi.load(job.folder)
        except mi.InterviewError as exc:
            return {**base, "stage": "error", "error": str(exc)}
        if saved is None:
            return {**base, "stage": "error", "error": "nothing was made and nothing is waiting; start again with make_start"}
        iv = saved[0]
        note = getattr(job.made, "waiting_note", "") if job.made is not None else ""
        notes = [*iv.notes, *([note] if note else [])]
        if iv.target is None:
            return {**base, "stage": "which_tool", "question": mi.target_question(iv.kind), "notes": notes,
                    "next": _ASK_FIRST + "Then call make_answer with `for` set to their answer."}
        if not iv.answered:
            return {**base, "stage": "questions", "made_for": iv.target.name, "notes": notes,
                    "questions": [_question(q) for q in iv.questions],
                    "next": _ASK_FIRST + "Ask every question, the must-know ones first. If they leave one open, leave "
                            "it out: Proofhouse decides it and says what it chose. If they want Proofhouse to decide "
                            "all of them, pass decide_for_me true. Then call make_answer with `answers` (question id "
                            "to their words)."}
        job.shown = iv.understood
        return {**base, "stage": "say_back", "made_for": iv.target.name, "say_back": iv.understood,
                "corrections_so_far": list(iv.corrections), "notes": notes,
                "next": _SHOW + " Nothing is made until they say it is right. If they change anything, pass it as "
                        "`correction` and show the new say-back."}

    def _done(self, job: Job) -> dict[str, Any]:
        made = job.made
        if made is None or made.waiting is not None:  # finished before this server started: read what it left
            try:
                record = json.loads((job.folder / "record.json").read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                return {"stage": "error", "error": f"cannot read the record: {exc}"}
            return {"stage": "done" if record.get("best_version") else "failed", **{key: record.get(key) for key in (
                "kind", "stopped", "best_version", "best_score", "spent_usd_estimated", "asked_for", "notes")},
                "judge_note": record.get("judge_note"), "files": str(job.folder)}
        closing = make.closing(made)
        out: dict[str, Any] = {
            "stage": "done", "kind": made.kind, "stopped": made.stopped, "best_version": made.best_version,
            "best_score": made.best_score, "rounds": len(made.rounds), "calls": len(made.calls),
            "spent_usd_estimated": format(made.spent_usd, "f"), "asked_for": closing["asked_for"],
            "summary": closing["lines"], "notes": closing["notes"], "files": str(made.folder),
        }
        if made.interview is not None and made.interview.target is not None:
            out["made_for"] = made.interview.target.name
        if made.judged_by:
            out["judged_by"] = made.judged_by
        out["next"] = ("Tell the person what was made, which asked-for items were met and which were not, every "
                       "note, and where the files are. The judge score is advice, not proof. " + _install_hint(made))
        if not made.best_version:
            out["stage"] = "failed"
            out["next"] = "Nothing usable came out. Tell the person why (see stopped and notes) and offer to try again."
        return out

    # -- the tools -------------------------------------------------------------------------------------------
    def make_start(self, args: dict[str, Any]) -> dict[str, Any]:
        request = args.get("request")
        if not isinstance(request, str) or not request.strip():
            raise ToolError("say what you want made: pass `request` in the person's own words")
        kind = str(args.get("kind") or "prompt")
        from . import make_media

        if kind in make_media.media_kinds():
            raise ToolError(f"{kind} is made on the command line for now: proofhouse make \"...\" --kind {kind}. "
                            "Chat makes cover text, code, sites and apps.")
        provider, model = self._writer(_text(args.get("provider")), _text(args.get("model")))
        settings: dict[str, Any] = {"request": request, "kind": kind, "provider": provider, "model": model}
        judge = self._judge(provider, _text(args.get("judge")))
        if judge:
            settings["judge"] = judge
        for key in ("for", "max_cost_usd"):
            value = _text(args.get(key))
            if value:
                settings[key] = value
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        folder = self.base / f"make-{make._slug(request)}-{stamp}"
        count = 1
        while folder.exists() or str(folder) in self.jobs:
            count += 1
            folder = self.base / f"make-{make._slug(request)}-{stamp}-{count}"
        job = self.jobs[str(folder)] = Job(folder, settings)
        out = self._step(job)
        out["written_by"] = f"{provider}/{model}"
        out["judged_by"] = judge or f"{provider}/{model} (the same model that writes; a second one judges better)"
        return out

    def make_answer(self, args: dict[str, Any]) -> dict[str, Any]:
        job = self._job(args)
        with job.lock:
            self._idle(job)
            stage = self._report(job).get("stage")
            if stage == "say_back":
                raise ToolError("the answers are in. Show the say-back and use make_confirm; to change an answer, "
                                "pass it there as `correction`")
            if stage not in ("which_tool", "questions"):
                raise ToolError(f"this make is not waiting for answers (it is at: {stage})")
            data = _answers_file(job.folder)
            made_for, answers = _text(args.get("for")), args.get("answers")
            if made_for:
                job.settings["for"] = data["for"] = made_for
            if answers is not None:
                if not isinstance(answers, dict):
                    raise ToolError("`answers` is an object: question id to the person's answer")
                kept = data.get("answers") if isinstance(data.get("answers"), dict) else {}
                data["answers"] = {**kept, **{str(k): v for k, v in answers.items()}}
            if args.get("decide_for_me") is True:
                data["decide_for_me"] = True
            if stage == "which_tool" and not job.settings.get("for"):
                raise ToolError("pass `for`: " + mi.target_question(job.settings["kind"]))
            data["confirmed"] = False  # answering never confirms; the say-back is always shown first
            _save_answers(job.folder, data)
            return self._step(job)

    def make_confirm(self, args: dict[str, Any]) -> dict[str, Any]:
        job = self._job(args)
        with job.lock:
            self._idle(job)
            seen = job.shown
            report = self._report(job)
            stage = report.get("stage")
            if stage != "say_back":
                raise ToolError(f"there is no say-back to confirm yet (this make is at: {stage})")
            data = _answers_file(job.folder)
            correction = _text(args.get("correction"))
            if not correction and args.get("confirmed") is True and seen != report["say_back"]:
                # it finished while the app was told "working", or the app was restarted: nobody has read this one
                return {**report, "next": "This say-back has not been shown to the person yet, so it is not confirmed. "
                                          + _SHOW}
            if correction:
                data["correction"], data["confirmed"] = correction, False
            elif args.get("confirmed") is True:
                data["confirmed"] = True
            else:
                raise ToolError("pass confirmed true when the person says the say-back is right, or `correction` "
                                "with what they want changed")
            _save_answers(job.folder, data)
            return self._step(job)

    def make_status(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._report(self._job(args))

    def make_list(self, args: dict[str, Any]) -> dict[str, Any]:
        found = []
        for folder in sorted(self.base.glob("make-*"), reverse=True):
            if (folder / "record.json").is_file():
                state = "done"
            elif (folder / "interview.json").is_file():
                state = "waiting for answers"
            else:
                continue
            found.append({"make": str(folder), "state": state, "from_chat": (folder / SESSION_FILE).is_file()})
        return {"folder": str(self.base), "makes": found[:50]}

    def _idle(self, job: Job) -> None:
        if self._busy(job):
            raise ToolError("this make is still working on the last step; call make_status first")


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _question(q: mi.Question) -> dict[str, Any]:
    out: dict[str, Any] = {"id": q.id, "question": q.text, "must_know": q.must}
    if q.group:
        out["about"] = q.group
    if q.options:
        out["options"] = list(q.options)
        out["pick"] = "any of these, or their own words" if q.type == "multi_select" else "one of these, or their own words"
    if q.depends_on:
        out["ask_only_if"] = {"question": q.depends_on[0], "answered": list(q.depends_on[1])}
    return out


def _answers_file(folder: Path) -> dict[str, Any]:
    try:
        data = json.loads((folder / "answers.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_answers(folder: Path, data: dict[str, Any]) -> None:
    providers.write_atomic(folder / "answers.json", json.dumps(data, indent=2, ensure_ascii=False))


def _install_hint(made: Any) -> str:
    folder = made.folder
    target = made.interview.target if made.interview is not None else None
    host = target.id if target is not None and target.sort == "tool" else "claude"
    hints = {
        "skill": f"To install the skill, run: proofhouse install-skill --bundle {folder}/<skill-name> --host {host}",
        "agent": f"To install the agent, run: proofhouse install agent {folder}/<agent-name>.md --into {host}",
        "rule": f"The rule file is in {folder}; install it with: proofhouse install rule <file> --into {host}",
        "site": f"Open {folder}/site/index.html to see the site.",
        "app": f"The app and how to build it: {folder}/README.md",
        "mcp": f"The server is in {folder}/mcp; the install line is in {folder}/INSTALL-MCP.txt",
        "hook": f"The hook is in {folder}/hook; the settings to add are in {folder}/settings-snippet.json",
    }
    hint = hints.get(made.kind, f"The best version is in {folder}.")
    return hint + " Ask before installing anything."


_MAKE = {"type": "string", "description": "The make folder that make_start returned."}
TOOLS: list[dict[str, Any]] = [
    {"name": "make_start",
     "description": "Start making something with Proofhouse: a prompt, skill, agent, rule, MCP server, hook, site, app, "
                    "or a kind it has to research first. It does not make anything yet. It comes back with questions "
                    "for the person. Ask them those questions in chat; never answer for them and never skip them.",
     "inputSchema": {"type": "object", "required": ["request"], "properties": {
         "request": {"type": "string", "description": "What the person wants, in their own words."},
         "kind": {"type": "string", "description": "prompt (default), skill, agent, rule, mcp, hook, site, app, copy, or another kind."},
         "for": {"type": "string", "description": "The AI tool it is for (for example Claude Code, Cursor, Codex), "
                                                   "where a site is published, or the platforms of an app. Leave out to be asked."},
         "provider": {"type": "string", "description": "Which provider writes it. Leave out to use the AI app the person is logged in to."},
         "model": {"type": "string", "description": "Which model writes it. Needed with a provider that is not an agent."},
         "judge": {"type": "string", "description": "provider/model that judges each version. Leave out to use a second installed AI app when there is one."},
         "max_cost_usd": {"type": "string", "description": "Spending limit for the whole make, such as 0.50. Needed for any paid provider."}}}},
    {"name": "make_answer",
     "description": "Give Proofhouse the person's answers to its questions (or which tool it is for). Comes back with a "
                    "say-back: what Proofhouse understood. This never starts the making.",
     "inputSchema": {"type": "object", "required": ["make"], "properties": {
         "make": _MAKE,
         "for": {"type": "string", "description": "The answer to the 'which tool / where / which platforms' question."},
         "answers": {"type": "object", "description": "Question id to the person's answer, in their words. Leave out any they left open.",
                     "additionalProperties": True},
         "decide_for_me": {"type": "boolean", "description": "True only when the person said Proofhouse should decide every open question."}}}},
    {"name": "make_confirm",
     "description": "After the person has read the say-back: confirm it (the making starts) or pass their correction "
                    "(a new say-back comes back). Only confirm when the person has seen the say-back and said it is right.",
     "inputSchema": {"type": "object", "required": ["make"], "properties": {
         "make": _MAKE,
         "confirmed": {"type": "boolean", "description": "True when the person says the say-back is right."},
         "correction": {"type": "string", "description": "What the person wants changed, in their words."}}}},
    {"name": "make_status",
     "description": "Where a make stands: still working, waiting on a question or the say-back, or done with the "
                    "result, what was asked for and met, and where the files are.",
     "inputSchema": {"type": "object", "required": ["make"], "properties": {"make": _MAKE}}},
    {"name": "make_list",
     "description": "The makes in the current folder, newest first.",
     "inputSchema": {"type": "object", "properties": {}}},
]

INSTRUCTIONS = ("Proofhouse makes prompts, skills, agents, rules, MCP servers, hooks, sites and apps for any AI tool. "
                "Flow: make_start, ask the person its questions, make_answer, show the say-back, make_confirm, then "
                "make_status until done. The questions and the say-back belong to the person: never answer or confirm for them.")


def handle(tools: Tools, message: Any) -> dict[str, Any] | None:
    """One protocol message in, the reply out (``None`` for a notification)."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "not a JSON-RPC 2.0 request"}}
    if "id" not in message:
        return None
    ident, method = message["id"], message["method"]
    params = message.get("params") if isinstance(message.get("params"), dict) else {}

    def reply(result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": ident, "result": result}

    def refuse(code: int, text: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": ident, "error": {"code": code, "message": text}}

    if method == "initialize":
        asked = params.get("protocolVersion")
        return reply({"protocolVersion": asked if asked in PROTOCOLS else PROTOCOLS[0],
                      "capabilities": {"tools": {}}, "instructions": INSTRUCTIONS,
                      "serverInfo": {"name": "proofhouse", "version": __version__}})
    if method == "ping":
        return reply({})
    if method == "tools/list":
        return reply({"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name")
        if name not in {tool["name"] for tool in TOOLS}:
            return refuse(-32602, f"no tool named {name!r}")
        args = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        try:
            result, failed = getattr(tools, name)(args), False
        except ToolError as exc:
            result, failed = {"error": str(exc)}, True
        failed = failed or result.get("stage") in ("error", "failed")
        return reply({"content": [{"type": "text", "text": json.dumps(result, indent=2, ensure_ascii=False)}],
                      "isError": failed})
    return refuse(-32601, f"method {method!r} is not supported")


def serve(tools: Tools, stdin: TextIO, stdout: TextIO) -> int:
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            answer: dict[str, Any] | None = {"jsonrpc": "2.0", "id": None,
                                             "error": {"code": -32700, "message": "not JSON"}}
        else:
            answer = handle(tools, message)
        if answer is not None:
            stdout.write(json.dumps(answer, ensure_ascii=False) + "\n")
            stdout.flush()
    return 0


def _cmd_mcp(args: argparse.Namespace) -> int:
    # The protocol owns stdout: anything else printed there would break the app's connection, so it goes to stderr.
    stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", newline="\n")
    stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")
    sys.stdout = sys.stderr
    return serve(Tools(agent=args.agent), stdin, stdout)


def add_mcp_command(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "mcp", help="Proofhouse as tools for an AI app (Claude Code, Cursor, Codex). The app starts this itself; "
                    "`proofhouse connect` sets it up.")
    p.add_argument("--agent", default=None,
                   help="The logged-in agent that writes when a make names no provider (claude, codex, grok, or your own).")
    p.set_defaults(func=_cmd_mcp)
