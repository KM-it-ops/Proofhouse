"""Use a coding agent you are already logged in to (Claude Code, Codex, Grok) as a model provider.

``proofhouse agent-server codex`` starts a small server on this machine only (127.0.0.1) and asks every
request for a private bearer token (``PROOFHOUSE_AGENT_TOKEN``, or one it makes and saves to a file only you
can read; the token itself is never printed), so another local process cannot trigger agent runs. It speaks the OpenAI chat shape, so any Proofhouse command
that takes a provider can point at it. Each request is one headless call to the agent's own command line,
billed to that agent's plan, not metered per call. Agents are data in ``data/agent_commands.json``; add your
own in ``PROOFHOUSE_HOME/agent_commands.json`` with no code change.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from . import providers

SHIPPED_PATH = Path(__file__).resolve().parent / "data" / "agent_commands.json"
HOST = "127.0.0.1"
DEFAULT_TIMEOUT_SECONDS = 600.0
TOKEN_ENV = "PROOFHOUSE_AGENT_TOKEN"
TOKEN_FILE = "agent-bridge-token"
MAX_REQUEST_BYTES = 1_000_000

Runner = Callable[[list[str], str, float], str]


class AgentError(Exception):
    pass


def _read(path: Path) -> dict[str, dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    agents = data.get("agents") if isinstance(data, dict) else None
    return {k: v for k, v in agents.items() if isinstance(v, dict) and v.get("argv")} if isinstance(agents, dict) else {}


def load_agents() -> dict[str, dict]:
    known = _read(SHIPPED_PATH)
    known.update(_read(providers.proofhouse_home() / "agent_commands.json"))
    return known


def bridge_notes(name: str) -> tuple[str, str] | None:
    """For ``agent-<agent>`` (the provider id ``agent-server`` tells you to add), the agent and a plain-words note."""
    agent = name.strip().lower().removeprefix("agent-")
    entry = load_agents().get(agent) if name.strip().lower().startswith("agent-") else None
    if entry is None:
        return None
    return agent, (
        f"Your own logged-in {agent} coding agent, answering through `proofhouse agent-server {agent}` on this machine "
        f"only ({HOST}, port {entry.get('port', 'of your choice')}). The server asks each request for a private bearer "
        f"token, so add the provider with `--key-env {TOKEN_ENV}` and set {TOKEN_ENV} in both shells (when it is not "
        "set, the server saves one to a file and tells you how to load it). "
        "Which model answers is whatever the agent itself "
        "uses: Proofhouse asks for 'default' unless you name one. Each call runs the agent's own command line and is "
        "billed to that agent's plan, not metered per call, so there is no provider API key or table price. "
        "Answers come back with token counts of 0. There are no vendor-checked prompting notes for the model behind it: "
        "write the prompt for that model."
    )


def build_prompt(messages: list[dict]) -> str:
    parts = []
    for message in messages:
        content = message.get("content", "")
        if isinstance(content, list):
            content = "\n".join(str(p.get("text", "")) for p in content if isinstance(p, dict))
        role = str(message.get("role", "user"))
        parts.append(str(content) if role == "user" and len(messages) == 1 else f"[{role}]\n{content}")
    return "\n\n".join(parts)


def build_argv(entry: dict, model: str, agent: str) -> list[str]:
    argv = list(entry["argv"])
    if model and model not in ("default", agent) and entry.get("model_flag"):
        flag = [part.replace("{model}", model) for part in entry["model_flag"]]
        # keep a trailing "-" (read the question from stdin) last
        at = len(argv) - 1 if argv and argv[-1] == "-" else len(argv)
        argv[at:at] = flag
    return argv


def run_agent(argv: list[str], prompt: str, timeout: float) -> str:
    """Run the agent once and return its plain-text answer."""
    found = shutil.which(argv[0])
    if not found:
        raise AgentError(f"{argv[0]} is not installed or not on PATH")
    argv = [found, *argv[1:]]
    temp: str | None = None
    stdin: str | None = prompt
    if any("{prompt_file}" in part for part in argv):
        handle, temp = tempfile.mkstemp(suffix=".txt", prefix="proofhouse-agent-")
        with os.fdopen(handle, "w", encoding="utf-8") as fh:
            fh.write(prompt)
        argv = [part.replace("{prompt_file}", temp) for part in argv]
        stdin = None
    try:
        # With no prompt to pipe in, give the agent an empty input: it must never read this process's own
        # (under `proofhouse mcp` that is the app's protocol stream).
        feed: dict = {"input": stdin} if stdin is not None else {"stdin": subprocess.DEVNULL}
        done = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, check=False, **feed)
    except subprocess.TimeoutExpired as exc:
        raise AgentError(f"{argv[0]} did not answer within {int(timeout)} s") from exc
    except OSError as exc:
        raise AgentError(f"could not start {argv[0]}: {exc}") from exc
    finally:
        if temp:
            Path(temp).unlink(missing_ok=True)
    answer = done.stdout.strip()
    if done.returncode != 0 or not answer:
        detail = (done.stderr or done.stdout).strip().splitlines()
        raise AgentError(f"{Path(argv[0]).stem} failed (exit {done.returncode}): {detail[-1] if detail else 'no output'}")
    return answer


def complete(agent: str, entry: dict, body: dict, runner: Runner, timeout: float) -> dict:
    model = str(body.get("model") or "default")
    answer = runner(build_argv(entry, model, agent), build_prompt(list(body.get("messages") or [])), timeout)
    return {
        "id": f"agent-{int(time.time() * 1000)}", "object": "chat.completion", "created": int(time.time()), "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def bridge_token() -> tuple[str, Path | None]:
    """The token every request must carry, and the file it was saved to when the environment did not name one.

    A token in the environment wins. Otherwise one is made once and kept in a file only the owner can read, so it
    never appears on screen, in shell history or in a process list.
    """
    named = os.environ.get(TOKEN_ENV, "").strip()
    if named:
        return named, None
    path = providers.proofhouse_home() / TOKEN_FILE
    try:
        saved = path.read_text(encoding="utf-8").strip()
    except OSError:
        saved = ""
    if not saved:
        saved = secrets.token_urlsafe(32)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(handle, "w", encoding="utf-8") as fh:
                fh.write(saved)
        except OSError as exc:
            raise AgentError(f"could not save a bridge token to {path}: {exc}. Set {TOKEN_ENV} yourself and start again.") from exc
    return saved, path


def make_server(agent: str, port: int | None = None, runner: Runner = run_agent,
                timeout: float = DEFAULT_TIMEOUT_SECONDS) -> ThreadingHTTPServer:
    known = load_agents()
    if agent not in known:
        raise AgentError(f"unknown agent '{agent}'. Known: {', '.join(sorted(known)) or 'none'}")
    entry = known[agent]
    # Every caller must present this token: loopback is reachable by every local process and user, and each
    # accepted request runs the agent's own command line on the owner's plan.
    token, token_file = bridge_token()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, payload: dict) -> None:
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            if self.path.rstrip("/").endswith("/models"):
                self._send(200, {"object": "list", "data": [{"id": "default", "object": "model", "owned_by": agent}]})
            else:
                self._send(404, {"error": {"message": "not found"}})

        def do_POST(self) -> None:  # noqa: N802
            if not self.path.rstrip("/").endswith("/chat/completions"):
                self._send(404, {"error": {"message": "not found"}})
                return
            if not secrets.compare_digest(self.headers.get("Authorization", "").encode("utf-8"),
                                          f"Bearer {token}".encode("utf-8")):
                self._send(401, {"error": {"message": "a valid bridge bearer token is required"}})
                return
            if self.headers.get("Origin") or self.headers.get_content_type() != "application/json":
                self._send(403, {"error": {"message": "browser-origin requests are not allowed; send application/json"}})
                return
            try:
                size = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                self._send(400, {"error": {"message": "bad request: Content-Length is not a number"}})
                return
            if size > MAX_REQUEST_BYTES:
                self._send(413, {"error": {"message": f"body over {MAX_REQUEST_BYTES} bytes is refused"}})
                return
            try:
                if size <= 0:
                    raise ValueError("body must not be empty")
                body = json.loads(self.rfile.read(size) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError("body must be a JSON object")
                messages = body.get("messages")
                if not isinstance(messages, list) or not messages or not all(isinstance(m, dict) for m in messages):
                    raise ValueError("messages must be a nonempty list of message objects")
            except ValueError as exc:
                self._send(400, {"error": {"message": f"bad request: {exc}"}})
                return
            try:
                self._send(200, complete(agent, entry, body, runner, timeout))
            except AgentError as exc:
                self._send(502, {"error": {"message": str(exc)}})

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

    server = ThreadingHTTPServer((HOST, entry["port"] if port is None else port), Handler)
    server.daemon_threads = True
    server.token = token  # type: ignore[attr-defined]
    server.token_file = token_file  # type: ignore[attr-defined]
    return server


def _cmd_agent_server(args: argparse.Namespace) -> int:
    try:
        server = make_server(args.agent, port=args.port, timeout=args.timeout)
    except AgentError as exc:
        print(f"error: {exc}")
        return 2
    except OSError as exc:
        print(f"error: could not listen on {HOST}:{args.port}: {exc}")
        return 2
    base = f"http://{HOST}:{server.server_address[1]}/v1"
    print(f"{args.agent} is answering at {base} (this machine only, token required). Stop with Ctrl+C.")
    if server.token_file is not None:  # type: ignore[attr-defined]
        path = server.token_file  # type: ignore[attr-defined]
        print(f"{TOKEN_ENV} was not set, so a private token was saved to {path}")
        print("Load it in the shell that will call the bridge, once:")
        print(f"  PowerShell:  $env:{TOKEN_ENV} = Get-Content '{path}'")
        print(f"  bash:        export {TOKEN_ENV}=\"$(cat '{path}')\"")
    print(f"Add it once:  proofhouse providers add agent-{args.agent} --base-url {base} --key-env {TOKEN_ENV}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def add_agent_server_command(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("agent-server", help="Serve a logged-in coding agent (claude, codex, grok) as a model provider on this machine.")
    p.add_argument("agent", help="Agent name from data/agent_commands.json (claude, codex, grok, or your own).")
    p.add_argument("--port", type=int, default=None, help="Port to listen on (default: the agent's own port).")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS, help="Seconds to wait for one answer.")
    p.set_defaults(func=_cmd_agent_server)
