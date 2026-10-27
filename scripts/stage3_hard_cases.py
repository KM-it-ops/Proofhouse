"""Stage 3 offline, isolated hard cases for every Proofhouse front-door command.

Expectations below were written from the command help and implementation before
running the cases. A surprising result is reported as broke, not normalized.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "docs" / "stage3"
TIMEOUT = 120
SENSITIVE = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "CREDENTIAL", "AUTH", "SESSION", "CONNECTION", "DSN", "COOKIE")
SENSITIVE_SUFFIXES = ("_URL", "_URI", "_PAT", "_PWD")


@dataclass(frozen=True)
class Fixture:
    path: str
    kind: str
    content: str = ""


@dataclass(frozen=True)
class Expected:
    exits: tuple[int, ...]
    must: tuple[str, ...] = ()
    must_not: tuple[str, ...] = ("Traceback", "internal error")
    exists: tuple[str, ...] = ()
    absent: tuple[str, ...] = ()
    home_clean: bool = False


@dataclass(frozen=True)
class Case:
    id: str
    command: str
    hard: str
    argv: tuple[str, ...]
    fixtures: tuple[Fixture, ...]
    expected: Expected
    env: tuple[tuple[str, str], ...] = ()


CASES: list[Case] = []


def add(command: str, number: int, hard: str, argv: list[str], *,
        fixtures: tuple[Fixture, ...] = (), exits: tuple[int, ...] = (2,),
        must: tuple[str, ...] = (), must_not: tuple[str, ...] = (),
        exists: tuple[str, ...] = (), absent: tuple[str, ...] = (),
        env: tuple[tuple[str, str], ...] = (), home_clean: bool = False) -> None:
    CASES.append(Case(f"{command}-{number}", command, hard, tuple(argv), fixtures,
                      Expected(exits, must, ("Traceback", "internal error", *must_not), exists, absent, home_clean), env))


FAKE_OPENAI = (("OPENAI_API_KEY", "fake-test-value"),)
FAKE_REPLICATE = (("REPLICATE_API_TOKEN", "fake-test-value"),)


def file(path: str, content: str) -> Fixture:
    return Fixture(path, "text", content)


def folder(path: str) -> Fixture:
    return Fixture(path, "dir")


def binary(path: str) -> Fixture:
    return Fixture(path, "binary")


def huge(path: str) -> Fixture:
    return Fixture(path, "huge")


# Compiler: strict input size, encoding, JSON, capability, and option boundaries.
add("validate", 1, "An IR file has a .json name but contains binary bytes.", ["validate", "odd name ☃.json"], fixtures=(binary("odd name ☃.json"),), exits=(3,), must=("validate: error",))
add("validate", 2, "A sparse IR file is one byte past the documented 8 MiB limit.", ["validate", "huge.json"], fixtures=(huge("huge.json"),), must=("EVR-RES-0001",))
add("inspect", 1, "An input path names a directory instead of an IR file.", ["inspect", "looks.json"], fixtures=(folder("looks.json"),), exits=(2,), must=("error",))
add("inspect", 2, "A JSON file repeats a key, which must not be silently accepted.", ["inspect", "repeat.json"], fixtures=(file("repeat.json", '{"a":1,"a":2}'),), exits=(3,), must=("inspect: error",))
add("compile", 1, "A binary input must fail before creating the requested output folder.", ["compile", "binary.json", "--adapter-version", "0.1", "--output", "built"], fixtures=(binary("binary.json"),), exits=(3,), must=("compile: error",), absent=("built",))
add("compile", 2, "An unsupported adapter and an existing output folder cannot produce an artifact (adapter failure is documented as exit 6).", ["compile", "empty.json", "--adapter", "not-real", "--adapter-version", "999", "--output", "built"], fixtures=(file("empty.json", "{}"), folder("built")), exits=(6,), must=("compile: error",), absent=("built/artifact.json",))
add("adapters", 1, "Repeated JSON switches should still return one parseable registry result.", ["adapters", "--json", "--json"], exits=(0,), must=('"command": "adapters"',))
add("adapters", 2, "A plausible but unsupported adapter filter must be rejected.", ["adapters", "--adapter", "fake"], must=("unrecognized arguments",))
add("doctor", 1, "Doctor runs with every credential-like variable stripped.", ["doctor", "--json"], exits=(0, 7), must=('"command": "doctor"',))
add("doctor", 2, "A repeated output switch must not turn a health result into a traceback.", ["doctor", "--json", "--json"], exits=(0, 7), must=('"command": "doctor"',))
add("closed-loop", 1, "A negative repair budget is outside the advertised 0 to 2 range.", ["closed-loop", "requirements.json", "--repair-budget", "-1"], fixtures=(file("requirements.json", "{}"),), must=("invalid choice",))
add("closed-loop", 2, "A product dataset without its rubric must be refused before reading input.", ["closed-loop", "missing.json", "--product-eval-dataset", "data.jsonl"], must=("requires both",))
add("compile-requirements", 1, "A JSON envelope with duplicate keys must be rejected.", ["compile-requirements", "duplicate.json"], fixtures=(file("duplicate.json", '{"kind":"file","kind":"api"}'),), must=("invalid JSON",))
add("compile-requirements", 2, "A binary file using a .json extension must be rejected cleanly.", ["compile-requirements", "binary.json"], fixtures=(binary("binary.json"),), must=("invalid JSON",))
add("evaluate-product", 1, "The dataset path is a folder while the rubric is a real file.", ["evaluate-product", "--dataset", "data.jsonl", "--rubric", "rubric.json", "--candidate-digest", "sha256:abc"], fixtures=(folder("data.jsonl"), file("rubric.json", "{}")), must=("dataset not found",))
add("evaluate-product", 2, "The rubric path is a folder while the dataset is a real file.", ["evaluate-product", "--dataset", "data.jsonl", "--rubric", "rubric.json", "--candidate-digest", "sha256:abc"], fixtures=(file("data.jsonl", ""), folder("rubric.json")), must=("rubric not found",))
add("closed-loop-bridged-008", 1, "A repeated JSON key must fail before bridging requirements.", ["closed-loop-bridged-008", "double.json"], fixtures=(file("double.json", '{"status":"SUCCESS","status":"PARTIAL"}'),), must=("invalid JSON",))
add("closed-loop-bridged-008", 2, "An enormous repair budget must fail argument parsing.", ["closed-loop-bridged-008", "missing.json", "--repair-budget", "999999999"], must=("invalid choice",))
add("route", 1, "Routing constraints contain a JSON array where an object is required.", ["route", "--objective", "Make a site", "--constraints", "[]"], must=("constraints must be a JSON object",))
add("route", 2, "Routing constraints contain truncated JSON.", ["route", "--objective", "Make a site", "--constraints", '{"kind":'], must=("constraints must be a JSON object",))
add("assay", 1, "Claims are stored as a JSON object instead of the required array.", ["assay", "--claims", "claims.json"], fixtures=(file("claims.json", "{}"),), exits=(2,), must=("error",), must_not=("PASS",))
add("assay", 2, "A .json claims file contains binary bytes.", ["assay", "--claims", "claims.json", "--rotten-fields"], fixtures=(binary("claims.json"),), exits=(2,), must=("error",), must_not=("PASS",))
add("proof", 1, "Empty artifact and spec must never be described as reviewed.", ["proof", "--artifact", "", "--spec", ""], exits=(3,), must=("UNJUDGED",), must_not=("SHIP",))
add("proof", 2, "Unicode claims and a contradictory spec must remain unjudged without a review pass.", ["proof", "--artifact", "π = 4", "--spec", "π = 3.14", "--json"], exits=(3,), must=("UNJUDGED",), must_not=('"SHIP"',))
add("execute-openai", 1, "Live execution receives an IR file but no explicit opt-in; the documented refusal is EXE-OPT-0001 with exit 7.", ["execute-openai", "ir.json", "--model", "unknown", "--credential-env", "FAKE_KEY", "--max-output-tokens", "1", "--max-cost-usd", "0", "--json"], fixtures=(file("ir.json", "{}"),), exits=(7,), must=("EXE-OPT-0001",))
add("execute-openai", 2, "A provider and target URL conflict must fail before any network access.", ["execute-openai", "missing.json", "--provider", "openai", "--target-url", "https://example.invalid"], must=("cannot be used with",))

# Offline case workflow and locally scoped installation.
add("case", 1, "A new case collides with an existing folder holding another user's file.", ["case", "new", "--case", "case dir", "--objective", "Write a prompt", "--model", "unknown"], fixtures=(folder("case dir"), file("case dir/keep.txt", "keep")), must=("error",), exists=("case dir/keep.txt",), absent=("case dir/case.json",))
add("case", 2, "An objective file path names a folder.", ["case", "new", "--case", "new-case", "--objective-file", "goal.txt", "--model", "unknown"], fixtures=(folder("goal.txt"),), must=("file not found",), absent=("new-case",))
add("optimize", 1, "The deprecated alias must still reject a case folder that already exists.", ["optimize", "new", "--case", "old", "--objective", "Make a skill", "--model", "unknown"], fixtures=(folder("old"),), must=("error",), exists=("old",), absent=("old/case.json",))
add("optimize", 2, "The alias status command sees a half-written case folder.", ["optimize", "status", "--case", "half"], fixtures=(folder("half"), file("half/case.json", "{")), must=("error",))
add("demo", 1, "The offline demo gets a workspace path that is a file.", ["demo", "--workspace", "workspace"], fixtures=(file("workspace", "already here"),), exits=(2,), must=("error",), exists=("workspace",))
add("demo", 2, "The offline demo gets an already populated workspace and must preserve its file.", ["demo", "--workspace", "workspace", "--quiet"], fixtures=(folder("workspace"), file("workspace/keep.txt", "keep")), exits=(0, 1, 2), exists=("workspace/keep.txt",))
add("models", 1, "A model name with Unicode has no local notes and cannot trigger research.", ["models", "show", "unknown-☃"], exits=(0,), must=("unknown-",), home_clean=True)
add("models", 2, "Forgetting a never-cached model must not create a notes file.", ["models", "forget", "never-cached-☃"], exits=(2,), must=("nothing cached",), home_clean=True)
add("install-skill", 1, "A bundle path names a plain text file rather than a skill archive (environment failure, exit 7).", ["install-skill", "--dest", "skills", "--bundle", "fake.skill", "--json"], fixtures=(file("fake.skill", "not a zip"),), exits=(7,), must=("error",), absent=("skills/proofhouse",))
add("install-skill", 2, "A bundle folder has no SKILL.md and must leave the destination empty.", ["install-skill", "--dest", "skills", "--bundle", "bundle", "--json"], fixtures=(folder("bundle"), file("bundle/readme.md", "not a skill")), exits=(7,), must=("error",), absent=("skills/proofhouse",))
add("uninstall-skill", 1, "A named skill was never installed in the isolated destination.", ["uninstall-skill", "proofhouse", "--dest", "skills", "--json"], exits=(2,), must=("error",), absent=("skills/proofhouse",))
add("uninstall-skill", 2, "An untracked skill folder must not be removed without a matching install record.", ["uninstall-skill", "proofhouse", "--dest", "skills", "--json"], fixtures=(folder("skills/proofhouse"), file("skills/proofhouse/keep.txt", "keep")), exits=(2,), must=("error",), exists=("skills/proofhouse/keep.txt",))

# Host-built artifacts, bounded model calls, and local registries.
add("check", 1, "A rule path is a directory instead of a rules file.", ["check", "rule", "rules.md"], fixtures=(folder("rules.md"),), exits=(1, 2), must=("error",))
add("check", 2, "A skill folder is half written and lacks SKILL.md, so it is not a skill (usage error, exit 2).", ["check", "skill", "skill dir"], fixtures=(folder("skill dir"), file("skill dir/readme.txt", "partial")), exits=(2,), must=("skill dir",))
add("record", 1, "A score below zero must be rejected before recording anything.", ["record", "rule", "rule.md", "--out", "record", "--request", "Make a rule", "--agent", "cursor", "--score", "-1"], fixtures=(file("rule.md", "Be clear."),), absent=("record",))
add("record", 2, "The same agent cannot also be its independent judge.", ["record", "rule", "rule.md", "--out", "record", "--request", "Make a rule", "--agent", "Cursor", "--judge", "cursor", "--judge-score", "8"], fixtures=(file("rule.md", "Be clear."),), must=("different agent",), absent=("record",))
add("render", 1, "An empty format list must fail before FFmpeg sees a folder.", ["render", "video", "film", "--formats", ",, "], fixtures=(folder("film"),), must=("name at least one format",))
add("render", 2, "A movie folder is actually a file.", ["render", "video", "film", "--formats", "16x9"], fixtures=(file("film", "not a film"),), exits=(1, 2), must=("error",))
add("make", 1, "A paid maker request has no spending ceiling or credential.", ["make", "Build a prompt", "--kind", "prompt", "--provider", "openai", "--model", "unknown", "--out", "made"], exits=(2, 7), must=("limit",), absent=("made/result.txt",))
add("make", 2, "A video request has no visual service or model.", ["make", "Make a short film", "--kind", "video", "--provider", "openai", "--model", "unknown", "--out", "made"], must=("video needs",), absent=("made",))
add("providers", 1, "An invalid negative cloud price must not alter the provider registry.", ["providers", "price", "openai", "unknown", "--input", "-1", "--output", "1"], must=("plain decimal",), home_clean=True)
add("providers", 2, "Removing a shipped provider must leave the local registry untouched.", ["providers", "remove", "openai"], must=("not in your providers file",), home_clean=True)
add("run", 1, "A paid run with a (fake) key and prompt text lacks the required spending ceiling.", ["run", "--provider", "openai", "--model", "unknown", "--prompt", "Hello"], exits=(7,), must=("PHC-RUN-0002", "spending limit"), env=FAKE_OPENAI)
add("run", 2, "A prompt file is actually a directory.", ["run", "--provider", "openai", "--model", "unknown", "--prompt-file", "prompt.txt"], fixtures=(folder("prompt.txt"),), must=("cannot read a file",))
add("loop", 1, "A negative duration is not a valid length of time.", ["loop", "Write a file", "--provider", "openai", "--model", "unknown", "--for", "-1", "--in", ".", "--out", "loop"], must=("not a length of time",), absent=("loop",))
add("loop", 2, "A watch loop without an interval must refuse to start.", ["loop", "Watch files", "--provider", "openai", "--model", "unknown", "--watch", "echo changed", "--in", ".", "--out", "loop"], must=("--every",), absent=("loop/rounds.jsonl",))
add("referee", 1, "Starting a check without opt-in must not run a shell command.", ["referee", "start", "Check output", "--check", "echo HELLO", "--folder", ".", "--out", "rounds"], must=("--allow-commands",), absent=("rounds/rounds.jsonl",))
add("referee", 2, "A record folder is only half written before status reads it.", ["referee", "status", "rounds"], fixtures=(folder("rounds"), file("rounds/loop.json", "{")), must=("loop.json", "not readable JSON"))
add("compare", 1, "Saved-output mode receives a directory instead of an output file.", ["compare", "A job", "--entry", "one=output.txt", "--entry", "two=other.txt", "--out", "comparison"], fixtures=(folder("output.txt"), file("other.txt", "answer")), must=("file not found",), absent=("comparison/side-by-side.html",))
add("compare", 2, "Saved outputs and live model selections conflict and must never call a model.", ["compare", "A job", "--entry", "one=output.txt", "--on", "openai:unknown", "--out", "comparison"], fixtures=(file("output.txt", "answer"),), must=("mutually exclusive",), absent=("comparison",))
add("train", 1, "An empty training file cannot be divided into training and validation data.", ["train", "data", "empty.jsonl", "--out", "training"], fixtures=(file("empty.jsonl", ""),), must=("error",), absent=("training/train.jsonl",))
add("train", 2, "Training start has a negative epoch count, which used to price as free and upload first.", ["train", "start", "--service", "openai", "--model", "unknown", "--data", "data", "--epochs", "-2", "--out", "training"], fixtures=(file("data/train.jsonl", "{}"),), exits=(7,), must=("PHC-RUN-0002", "epochs must be a whole number", "nothing was uploaded"), env=FAKE_OPENAI)
add("addons", 1, "An add-on folder lacks the required addon.json manifest.", ["addons", "install", "pack"], fixtures=(folder("pack"),), must=("error",))
add("addons", 2, "Removing a pack that was never installed must leave other state alone.", ["addons", "remove", "never-installed"], must=("error",))
add("deploy", 1, "A deployment dry run receives a path that is a file.", ["deploy", "site", "--to", "netlify", "--dry-run"], fixtures=(file("site", "not a folder"),), must=("error",))
add("deploy", 2, "A populated site can produce a dry-run command without deploying it.", ["deploy", "site with spaces", "--to", "netlify", "--dry-run", "--json"], fixtures=(folder("site with spaces"), file("site with spaces/index.html", "<h1>Hi</h1>")), exits=(0,), must=("dry run",), exists=("site with spaces/index.html",))
add("hosts", 1, "The host registry should remain readable without any account credentials.", ["hosts", "list", "--json"], exits=(0,), must=('"hosts"',))
add("hosts", 2, "A repeated JSON flag should still return one host registry.", ["hosts", "list", "--json", "--json"], exits=(0,), must=('"hosts"',))
add("install", 1, "An agent file lacks required frontmatter and must not be installed into the project.", ["install", "agent", "agent.md", "--into", "cursor", "--project", "project"], fixtures=(file("agent.md", "plain text"), folder("project")), must=("frontmatter",), absent=("project/.cursor/agents/agent.md",))
add("install", 2, "An MCP server has no command and cannot be installed into the project.", ["install", "mcp", "test-server", "--into", "cursor", "--project", "project"], fixtures=(folder("project"),), must=("needs --command",), absent=("project/.cursor/mcp.json",))
add("uninstall", 1, "A project install was never recorded and must not remove anything.", ["uninstall", "agent", "missing", "--from", "cursor", "--project", "project"], fixtures=(folder("project"),), must=("error",))
add("uninstall", 2, "An existing hand-written rule must survive an uninstall without a record.", ["uninstall", "rule", "handmade", "--from", "cursor", "--project", "project"], fixtures=(folder("project"), file("project/.cursor/rules/handmade.mdc", "Keep me.")), must=("error",), exists=("project/.cursor/rules/handmade.mdc",))
add("generate", 1, "A paid image request with a (fake) key has no spending ceiling.", ["generate", "image", "--provider", "openai-images", "--model", "unknown", "--prompt", "A moon", "--out", "moon.png"], exits=(7,), must=("PHC-RUN-0002", "spending limit"), absent=("moon.png",), env=FAKE_OPENAI)
add("generate", 2, "A negative video length must be rejected before any paid request is priced or sent.", ["generate", "video", "--provider", "replicate", "--model", "unknown", "--prompt", "A moon", "--seconds", "-3", "--out", "clip.mp4"], exits=(2,), must=("--seconds",), absent=("clip.mp4",), env=FAKE_REPLICATE)
add("media", 1, "A negative declared unit price must not be saved.", ["media", "price", "openai-images", "unknown", "--usd", "-1"], must=("plain decimal",), home_clean=True)
add("media", 2, "A media service template is actually a binary file.", ["media", "add", "--from", "media.json"], fixtures=(binary("media.json"),), must=("error",), home_clean=True)
add("eval", 1, "A JSONL dataset contains a broken line after a valid-looking extension.", ["eval", "validate", "--dataset", "data with spaces.jsonl"], fixtures=(file("data with spaces.jsonl", "{broken\n"),), exits=(1,), must=("validation failed",))
add("eval", 2, "A loadout id does not exist and must not create output.", ["eval", "compile-loadout", "--id", "never-existed", "--out", "loadout.md"], exits=(2, 8), must=("error",), absent=("loadout.md",))
add("scan", 1, "The scan target is a file instead of a project folder.", ["scan", "project.txt"], fixtures=(file("project.txt", "a file"),), must=("scan:",))
add("scan", 2, "A directory with a Unicode name and binary file must still scan safely.", ["scan", "project ☃", "--json"], fixtures=(folder("project ☃"), binary("project ☃/data.bin")), exits=(0,), must=('"',))
add("parts", 1, "The part registry must serialize in an isolated home with no keys.", ["parts", "--json"], exits=(0,), must=('"parts"',))
add("parts", 2, "An unsupported filter must fail rather than print an incomplete part list.", ["parts", "--kind", "video"], must=("unrecognized arguments",))


def parser_commands() -> set[str]:
    """Read the real parser, so coverage grows when the product does."""
    from proofhouse.cli import build_parser

    parser = build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    raise RuntimeError("Proofhouse parser has no subcommands")


def _inside(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError(f"unsafe case path: {relative!r}")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"case path escapes temporary folder: {relative!r}")
    return resolved


def _fixture(root: Path, item: Fixture) -> None:
    target = _inside(root, item.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if item.kind == "dir":
        target.mkdir(parents=True, exist_ok=True)
    elif item.kind == "text":
        target.write_text(item.content, encoding="utf-8", newline="\n")
    elif item.kind == "binary":
        target.write_bytes(b"\x00\xff\x80\x00")
    elif item.kind == "huge":
        with target.open("wb") as handle:
            handle.truncate(8 * 1024 * 1024 + 1)
    else:
        raise ValueError(f"unknown fixture kind: {item.kind}")


def _environment(root: Path, extra: tuple[tuple[str, str], ...] = ()) -> dict[str, str]:
    env = {name: value for name, value in os.environ.items()
           if not any(mark in name.upper() for mark in SENSITIVE)
           and not name.upper().endswith(SENSITIVE_SUFFIXES)}
    env.pop("VIRTUAL_ENV", None)
    env.pop("UV_PROJECT_ENVIRONMENT", None)
    for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "XDG_CONFIG_HOME",
                 "XDG_DATA_HOME", "PROOFHOUSE_HOME", "TMP", "TEMP", "TMPDIR", "UV_CACHE_DIR"):
        target = root / ("home" if name in ("HOME", "USERPROFILE") else name.lower())
        target.mkdir(parents=True, exist_ok=True)
        env[name] = str(target)
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env[name] = "http://127.0.0.1:9"
    env["NO_PROXY"] = ""
    env["no_proxy"] = ""
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["UV_NO_PROGRESS"] = "1"
    env.update(dict(extra))  # fake values only; the dead proxy above means nothing can be sent
    return env


def _safety(case: Case) -> None:
    if not case.argv or case.argv[0] != case.command:
        raise ValueError("case command and argv disagree")
    if any(Path(part).is_absolute() or part[0] in ("/", chr(92)) or ".." in Path(part).parts
           for value in case.argv for part in (value, value.partition("=")[2]) if part):
        raise ValueError("case argv contains an absolute or parent path")
    if "--allow-commands" in case.argv or "--opt-in" in case.argv:
        raise ValueError("case enables command execution or live model execution")
    if case.command == "deploy" and "--dry-run" not in case.argv:
        raise ValueError("deploy case is not a dry run")
    if case.command == "models" and "update" in case.argv:
        raise ValueError("models update uses the network")
    if case.command in {"make", "run", "loop", "generate", "train"} and "--max-cost-usd" in case.argv:
        raise ValueError("paid case sets a spending ceiling")
    if case.command in {"install", "uninstall"} and "--project" not in case.argv:
        raise ValueError("host install case has no isolated project")
    if case.command in {"install-skill", "uninstall-skill"} and "--dest" not in case.argv:
        raise ValueError("skill install case has no isolated destination")


def _scrub(text: str, root: Path) -> str:
    """Keep local paths out of the committed report: the case folder, the repo and the user's profile."""
    for base, label in ((root, "<case>"), (ROOT, "<repo>")):
        for form in (str(base), base.as_posix(), str(base).replace("\\", "\\\\")):
            text = text.replace(form, label)
    return re.sub(r"[A-Za-z]:[\/]+Users[\/]+[^\/\s\"']+", "<user>", text)


def _captured(raw: str | bytes | None, root: Path) -> str:
    """Output from a child, scrubbed the same way whether it finished, failed or timed out."""
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else (raw or "")
    return _scrub(text, root)


def _exit_code(results: list[dict], under_two: list[str]) -> int:
    """Non-zero when a case broke, could not run, or a command has fewer than two cases."""
    broke = any(result["verdict"] == "broke" for result in results)
    return 1 if under_two or broke or any(result["unable"] for result in results) else 0


def run_case(case: Case) -> dict:
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix=f"{case.id}-", dir=REPORT_DIR) as directory:
        root = Path(directory)
        try:
            _safety(case)
            for item in case.fixtures:
                _fixture(root, item)
            completed = subprocess.run(
                ["uv", "run", "--no-sync", "proofhouse", *case.argv],
                cwd=root, env=_environment(root, case.env), stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT,
                check=False,
            )
            output = _scrub(completed.stdout, root)
            code = completed.returncode
            hung = False
            unable = False
        except subprocess.TimeoutExpired as exc:
            output = _captured(exc.stdout, root)
            code = None
            hung = True
            unable = False
        except (OSError, ValueError) as exc:
            output = _scrub(f"could not run: {exc}", root)
            code = None
            hung = False
            unable = True
        failures = []
        expected = case.expected
        if hung:
            failures.append("hung past 120 seconds")
        elif unable:
            failures.append("case could not run at all")
        else:
            if code not in expected.exits:
                failures.append(f"exit {code}; expected {list(expected.exits)}")
            for text in expected.must:
                if text.casefold() not in output.casefold():
                    failures.append(f"missing text {text!r}")
            for text in expected.must_not:
                if text.casefold() in output.casefold():
                    failures.append(f"misleading or forbidden text {text!r}")
            for path in expected.exists:
                if not _inside(root, path).exists():
                    failures.append(f"missing file {path}")
            for path in expected.absent:
                if _inside(root, path).exists():
                    failures.append(f"unexpected file {path}")
            if expected.home_clean:
                written = sorted(p.relative_to(root).as_posix() for p in (root / "proofhouse_home").rglob("*") if p.is_file())
                if written:
                    failures.append(f"wrote into the Proofhouse home: {written}")
        seconds = round(time.perf_counter() - started, 3)
        first_line = re.sub(r"\s+", " ", output.strip().splitlines()[0] if output.strip() else "no output")[:160]
        happened = "; ".join(failures) if failures else f"Exit {code}; {first_line}"
        return {
            "id": case.id, "command": case.command, "hard": case.hard,
            "argv": list(case.argv), "fixtures": [asdict(item) for item in case.fixtures],
            "expected": asdict(expected), "verdict": "broke" if failures else "held",
            "exit_code": code, "output_first_400": output[:400], "wall_seconds": seconds,
            "happened": happened, "hung": hung, "unable": unable,
        }


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    counts = collections.Counter(case.command for case in CASES)
    uncovered = sorted(parser_commands() - set(counts))
    under_two = sorted(command for command in parser_commands() if counts[command] < 2)
    results = []
    for index, case in enumerate(CASES, 1):
        result = run_case(case)
        results.append(result)
        print(f"{index}/{len(CASES)} {case.id}: {result['verdict']}", flush=True)
    payload = {"timeout_seconds": TIMEOUT, "case_count": len(results),
               "uncovered_commands": uncovered, "commands_with_fewer_than_two_cases": under_two,
               "cases": results}
    (REPORT_DIR / "results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    lines = ["# Stage 3 hard cases", "", f"{len(results)} cases across {len(counts)} subcommands. What broke, what held and what it cost: [findings.md](findings.md).", "",
             "| Case | What makes it hard | Verdict | What happened | Seconds |",
             "| --- | --- | --- | --- | ---: |"]
    for result in results:
        cells = (result["id"], result["hard"], result["verdict"], result["happened"], str(result["wall_seconds"]))
        lines.append("| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", " ") for cell in cells) + " |")
    lines.extend(["", "## Broke cases", ""])
    broken = [result for result in results if result["verdict"] == "broke"]
    lines.extend(f"- **{result['id']}**: {result['happened']}" for result in broken)
    if not broken:
        lines.append("None.")
    (REPORT_DIR / "hard-cases.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {len(results)} verdicts: {len(broken)} broke; {len(under_two)} commands under two cases.")
    return _exit_code(results, under_two)


if __name__ == "__main__":
    raise SystemExit(main())
