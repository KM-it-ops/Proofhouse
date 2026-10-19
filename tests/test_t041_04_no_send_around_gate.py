"""T-041-04: no path can send around the spend gate. Fails the build when broken.

(a) Only a fixed list of modules may import anything that can reach the
    network, start another program, or load a module by a computed name.
(b) In the one module that can send, every call that can send sits inside the
    one send step, and that step is referenced exactly once: handed to
    ``spend.send_within_ceiling``.
(b2) Anywhere in the package, the raw sender (``_httpx_send``) is referenced
    only inside that file, and a ``send`` attribute is touched (called, stored
    or looked up with ``getattr``) only inside the one send step.
(c) No part has the runner role. Registering the first runner must change this
    test, which shows up in review.
(d) Behaviour: with the shipped price table, nothing is sent, whatever the
    model; a surprise inside the gate sends nothing; the gate calls ``send`` at
    most once, only after admitting, with exactly the bytes it counted.
"""
from __future__ import annotations

import ast
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from proofhouse import parts, spend
from proofhouse.compiler.execution import LiveOpenAIRequest, execute_openai

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "proofhouse"
EXECUTION = SRC / "compiler" / "execution.py"
# Every module that can send, with its raw sender. Each hands its one send step (``_dispatch``) to the gate.
SENDERS = {"compiler/execution.py": "_httpx_send", "live.py": "_httpx_post", "media.py": "_httpx_post", "train.py": "_httpx_post"}
# Plain reads (job status, finished files) that send no body and cost nothing; they may never post.
READERS = {"media.py": "_httpx_get", "train.py": "_httpx_get"}
# A data-file upload: a multipart post of a file (files=, never a JSON or raw body) that starts nothing and is not billed.
UPLOADERS = {"train.py": "_httpx_upload"}

NETWORK = {
    "httpx", "requests", "urllib3", "aiohttp", "websockets", "socket", "ssl", "asyncio",
    "http", "urllib.request", "ftplib", "smtplib", "poplib", "imaplib", "telnetlib",
    "xmlrpc", "socketserver", "webbrowser",
}
PROCESS_OR_FOREIGN = {"subprocess", "multiprocessing", "ctypes", "os.system"}

# The whole list. Adding a module here is a deliberate change that shows up in review.
ALLOWED = {
    ("compiler/execution.py", "httpx"),  # execute-openai; sends only through the spend gate
    ("live.py", "httpx"),  # any provider, any model; sends only through the spend gate
    ("catalog.py", "httpx"),  # free model lists and official release pages; the paid reading goes through live.run_prompt and the spend gate
    ("media.py", "httpx"),
    ("train.py", "httpx"),  # training jobs; the one paid request goes only through the spend gate
    ("train.py", "subprocess"),  # trains on this machine with your own command (for example MLX LoRA)  # any media service; the one paid request goes only through the spend gate
    ("optimize/reference_workflow.py", "subprocess"),  # runs the proofhouse CLI itself, offline
    ("studio.py", "subprocess"),  # runs ffmpeg and ffprobe on local files; no network
    ("sitecheck.py", "subprocess"),
    ("make_checks.py", "subprocess"),  # starts a made MCP server or hook locally: no shell, a reduced environment, a timeout
    ("deploy.py", "subprocess"),  # runs the hosting service's own tool (netlify, vercel, wrangler, surge) when you deploy
    ("loop.py", "subprocess"),  # runs your check and watch commands, and the agent's only with --allow-commands  # opens a generated site from disk in a local headless browser
    ("optimize/cli.py", "ctypes"),  # console handling on Windows
    ("make_checks.py", "ctypes"),  # a Windows job object so a made MCP server or hook cannot outlive its check
    ("parts.py", "import_module"),
    ("addons.py", "entry_points"),  # loads add-on packages you installed (group proofhouse.addons); their code runs as you  # loads registered parts by the module names in its own table
}


def _risky(name: str) -> str | None:
    if name == "urllib":  # a bare ``import urllib`` reaches ``urllib.request``
        return "urllib.request"
    for candidate in sorted(NETWORK | PROCESS_OR_FOREIGN, key=len, reverse=True):
        if name == candidate or name.startswith(candidate + "."):
            return candidate
    return None


def _found() -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for path in sorted(SRC.rglob("*.py")):
        where = path.relative_to(SRC).as_posix()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module, *(f"{node.module}.{alias.name}" for alias in node.names)]
            elif isinstance(node, ast.Call):
                func = node.func
                callee = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
                if callee == "entry_points":
                    found.add((where, "entry_points"))
                if callee in {"import_module", "__import__"}:
                    literal = node.args[0] if node.args and isinstance(node.args[0], ast.Constant) else None
                    hit = _risky(literal.value) if literal is not None and isinstance(literal.value, str) else None
                    found.add((where, hit or "import_module"))
                if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "os" and func.attr in {"system", "popen"} | {f"exec{s}" for s in ("l", "le", "lp", "lpe", "v", "ve", "vp", "vpe")} | {"spawnl", "spawnv", "startfile"}:
                    found.add((where, "os.system"))
            for name in names:
                hit = _risky(name)
                if hit:
                    found.add((where, hit))
    return found


def test_a_only_the_listed_modules_can_reach_the_network_or_start_programs() -> None:
    found = _found()
    assert sorted(found - ALLOWED) == [], "a new module can reach the network or start a program"
    assert sorted(ALLOWED - found) == [], "the allowlist names something that no longer exists"


def _enclosing_functions(tree: ast.AST) -> dict[ast.AST, tuple[str, ...]]:
    scope: dict[ast.AST, tuple[str, ...]] = {}

    def visit(node: ast.AST, names: tuple[str, ...]) -> None:
        for child in ast.iter_child_nodes(node):
            inner = (*names, child.name) if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else names
            scope[child] = inner
            visit(child, inner)

    visit(tree, ())
    return scope


@pytest.mark.parametrize("module", sorted(SENDERS))
def test_b_every_send_sits_in_the_one_step_and_that_step_goes_only_to_the_gate(module: str) -> None:
    raw = SENDERS[module]
    tree = ast.parse((SRC / module).read_text(encoding="utf-8"))
    scope = _enclosing_functions(tree)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]

    def callee(call: ast.Call) -> str:
        func = call.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            owner = func.value.id if isinstance(func.value, ast.Name) else "?"
            return f"{owner}.{func.attr}"
        return "?"

    sends = [c for c in calls if callee(c) in {raw, "transport"} or callee(c).endswith(".send")]
    assert sends, "the send step has no send in it"
    for call in sends:
        assert scope[call][-1:] == ("_dispatch",), f"{callee(call)} at line {call.lineno} is outside the send step"
    wire = [c for c in calls if callee(c).startswith("httpx.") or callee(c).endswith((".post", ".request", ".stream"))]
    reader = READERS.get(module)
    uploader = UPLOADERS.get(module)
    for call in wire:
        where = scope[call][-1:]
        words = {k.arg for k in call.keywords}
        posts = callee(call).endswith((".post", ".request", ".stream"))
        is_upload = uploader is not None and where == (uploader,) and (
            not posts or (callee(call).endswith(".post") and "files" in words and not words & {"json", "content"})
        )
        assert where == (raw,) or is_upload or (reader is not None and where == (reader,) and not posts), (
            f"{callee(call)} at line {call.lineno} is outside {raw}"
        )

    loads = {
        name: [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Load)]
        for name in ("_dispatch", raw)
    }
    assert len(loads[raw]) == 1 and scope[loads[raw][0]][-1:] == ("_dispatch",)
    (dispatch,) = loads["_dispatch"]  # referenced exactly once ...
    (gate,) = [c for c in calls if callee(c) in {"spend.send_within_ceiling", "spend.send_media_within_ceiling",
                                                 "spend.send_training_within_ceiling"}]
    assert [k.value for k in gate.keywords if k.arg == "send"] == [dispatch]  # ... as the gate's send=


SEND_NAMES = {"send", *SENDERS.values()}


def _send_references(path: Path, where: str) -> list[str]:
    """Every reference to the raw sender or to a ``send`` attribute outside the one send step."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    scope = _enclosing_functions(tree)
    in_live_path = where in SENDERS
    found: list[str] = []
    for node in ast.walk(tree):
        inside_step = in_live_path and scope.get(node, ())[-1:] == ("_dispatch",)
        # ``.send`` and ``_httpx_send`` in any form; a plain local name ``send`` (the gate's own parameter) is fine.
        raw_names = set(SENDERS.values())
        name = node.attr if isinstance(node, ast.Attribute) else node.id if isinstance(node, ast.Name) and node.id in raw_names else None
        if name in SEND_NAMES and not inside_step:
            found.append(f"{where}:{node.lineno} {name}")
        if isinstance(node, ast.ImportFrom) and any(alias.name in raw_names for alias in node.names):
            found.append(f"{where}:{node.lineno} import of a raw sender")
        if in_live_path and isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "transport" and not inside_step:
            found.append(f"{where}:{node.lineno} transport called outside the send step")
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"getattr", "setattr"}
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value in SEND_NAMES
        ):
            found.append(f"{where}:{node.lineno} getattr {node.args[1].value!r}")
    return found


def test_b2_nothing_else_in_the_package_reaches_the_sender() -> None:
    found = [ref for path in sorted(SRC.rglob("*.py")) for ref in _send_references(path, path.relative_to(SRC).as_posix())]
    assert found == []


SNEAKY = {
    "other module imports the sender": ("sneaky.py", "from .compiler.execution import _httpx_send\ndef resend(p):\n    return _httpx_send(p)\n"),
    "other module reaches it by attribute": ("sneaky.py", "from .compiler import execution\ndef resend(p):\n    return execution._httpx_send(p)\n"),
    "other module calls a transport": ("sneaky.py", "def resend(request, p):\n    return request.transport.send(p)\n"),
    "send stored then called": ("compiler/execution.py", "def execute_openai(request, p):\n    s = request.transport.send\n    return s(p)\n"),
    "send looked up by name": ("compiler/execution.py", "def execute_openai(t, p):\n    return getattr(t, 'send')(p)\n"),
    "any-provider sender imported": ("sneaky.py", "from .live import _httpx_post\ndef resend(r):\n    return _httpx_post(r)\n"),
    "transport called outside the step": ("live.py", "def run_prompt(transport, r):\n    return transport(r)\n"),
}


@pytest.mark.parametrize("label", sorted(SNEAKY))
def test_b2_catches_the_ways_round_it(tmp_path: Path, label: str) -> None:
    where, source = SNEAKY[label]
    path = tmp_path / "module.py"
    path.write_text(source, encoding="utf-8")
    assert _send_references(path, where), label


@pytest.mark.parametrize("module", sorted(SENDERS))
def test_b3_the_send_step_and_the_sender_cannot_repeat_a_send(module: str) -> None:
    # One admitted worst case pays for one request: no loop, comprehension or recursion around a send.
    raw = SENDERS[module]
    tree = ast.parse((SRC / module).read_text(encoding="utf-8"))
    loops = (ast.For, ast.AsyncFor, ast.While, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
    steps = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in {"_dispatch", raw}]
    assert sorted(n.name for n in steps) == sorted(["_dispatch", raw])
    for step in steps:
        found = [type(n).__name__ for n in ast.walk(step) if isinstance(n, loops)]
        assert found == [], f"{step.name} has {found}"
        recursive = [n for n in ast.walk(step) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == step.name]
        assert recursive == [], step.name


def test_c_no_part_has_the_runner_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOFHOUSE_EXPERIMENTAL", "1")
    assert parts.part_ids(parts.ROLE_RUNNER) == ()


class RecordingTransport:
    def __init__(self) -> None:
        self.calls: list[Any] = []

    def send(self, prepared: Any) -> Any:
        self.calls.append(prepared)
        return type("Resp", (), {"status_code": 200, "payload": {}})()


def _ir() -> dict:
    import importlib.util

    spec = importlib.util.spec_from_file_location("_ir_fixtures", ROOT / "tests" / "compiler" / "fixtures" / "ir_fixtures.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.minimal_valid_ir()


def _live(model: str, transport: RecordingTransport, ceiling: str = "1000000") -> Any:
    request = LiveOpenAIRequest(
        opt_in=True, model=model, credential_value="dummy", max_output_tokens=8, max_cost_usd=ceiling, transport=transport
    )
    return execute_openai(json.dumps(_ir()), request)


@pytest.mark.parametrize("model", ["gpt-5.6-luna", "gpt-4o", "o3", "model-a", "openai/gpt-5.6-luna"])
def test_d_the_shipped_table_lets_nothing_through(model: str) -> None:
    transport = RecordingTransport()
    result = _live(model, transport)
    assert result.diagnostics == ("PHC-COST-0002",)
    assert transport.calls == []


def test_d_a_surprise_inside_the_gate_sends_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode() -> spend.PriceTable:
        raise RuntimeError("surprise")

    monkeypatch.setattr(spend, "load_price_table", explode)
    transport = RecordingTransport()
    with pytest.raises(RuntimeError):
        _live("model-a", transport)
    assert transport.calls == []


def test_d_the_gate_calls_send_once_only_after_admitting_with_the_counted_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = spend.PriceEntry("openai", "model-a", Decimal("1"), Decimal("1"), None, "default", "https://example.com/p", "2026-10-12")
    monkeypatch.setattr(spend, "load_price_table", lambda: spend.PriceTable("2026-10-12.9", (entry,)))
    body = {"model": "model-a", "messages": [{"role": "system", "content": "hello"}], "max_completion_tokens": 8}
    seen: list[bytes] = []
    refused = spend.send_within_ceiling(body, provider="openai", model="model-a", max_output_tokens=8, ceiling_usd="0.000001", send=seen.append)
    assert refused.admission.decision == "refused" and seen == [] and refused.response is None
    admitted = spend.send_within_ceiling(body, provider="openai", model="model-a", max_output_tokens=8, ceiling_usd="1", send=seen.append)
    assert admitted.admission.decision == "admitted"
    assert seen == [spend.request_body_bytes(body)]
