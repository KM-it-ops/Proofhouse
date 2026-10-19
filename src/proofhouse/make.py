"""The make engine: say what you want, pick any model, get it made, tested and improved.

``make`` writes version 1 with your model, tries it, has a judge score it
against what you asked for, and revises until the score reaches your target,
the rounds run out, or the next call would cross your spending limit. Every
call goes through ``live.run_prompt`` and so through the spend gate. The limit
covers the whole command: each call may spend only what is left.

Kinds:
- ``prompt``: a prompt. Each round runs it on a test input (yours, or one the
  model writes) and the judge scores the output.
- ``skill``: an agent skill (a folder with ``SKILL.md``). The judge scores the
  skill text against your request, and the result is checked so that
  ``proofhouse install-skill --bundle <folder>`` accepts it.
- any other name: a kind an add-on brings, or one Proofhouse has not met yet.
  A new kind is researched by your model first and saved as a learned kind
  (``learn.py``), then made like the others; it is never refused for being new.

Everything lands in one folder: every version, every test output, every score,
and every call's tokens and estimated cost (``record.json``), plus the best
version (``final.md``, or the skill folder). The judge is a model, so its score
is advice, not proof.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from . import __version__, app_platforms, live, make_checks, providers, sitecheck

KINDS = ("prompt", "skill", "agent", "site", "app", "copy", "rule", "mcp", "hook")
DEFAULT_ROUNDS = 3
DEFAULT_TARGET = 9

_WRITE = {
    "prompt": (
        "You write excellent prompts for AI models. Write the complete prompt that best achieves the request below. "
        "Be specific about the task, the audience, the output format and the quality bar. "
        "Output only the prompt text, nothing before or after it."
    ),
    "skill": (
        "You write agent skills (a SKILL.md file for Claude Code, Cursor and similar agents). Write the complete SKILL.md "
        "that best achieves the request below. It must start with YAML frontmatter between '---' lines holding exactly "
        "'name: <lowercase-hyphenated-name>' and 'description: <one line saying when to use it>', then clear instructions. "
        "Output only the file content."
    ),
    "site": (
        "You build excellent websites. Build the complete static website (HTML, CSS and JavaScript, no build step, "
        "no external dependencies) that best achieves the request below: responsive, accessible, fast, with real copy. "
        'Reply with JSON only: {"files": {"index.html": "...", "styles.css": "...", "script.js": "..."}} '
        "(more pages are fine; every file the pages link to must be included)."
    ),
    "app": (
        "Build a complete working shared web app for the request. Write responsive accessible HTML, CSS and JavaScript "
        "with real functionality and no outside runtime dependency. The app will be wrapped for the chosen platforms. "
        'Reply with JSON only: {"files": {"index.html": "...", "styles.css": "...", "script.js": "..."}}.'
    ),
    "copy": (
        "You write launch and announcement copy that people actually read: headline, short body, a clear call to action, "
        "and ready-to-post versions for the channels the request names (for example a post, an email, a store listing). "
        "Write the complete copy that best achieves the request below. Plain, specific, no filler. Output only the copy."
    ),
    "agent": (
        "You write subagents for Claude Code (a Markdown file). Write the complete file that best achieves the request "
        "below. It must start with YAML frontmatter between '---' lines holding 'name: <lowercase-hyphenated-name>' and "
        "'description: <one line saying when to use it>', then the agent's instructions. Output only the file content."
    ),
    "rule": (
        "Write a standing Markdown instruction for an AI coding tool that fulfills the request. No frontmatter is needed. "
        'Reply with JSON only: {"name": "lowercase-hyphenated-name", "content": "complete Markdown rule"}.'
    ),
    "mcp": (
        "Build a working MCP server using JSON-RPC 2.0 over stdio. It must answer initialize and tools/list with at least one "
        'tool with a name and inputSchema. Reply with JSON only: {"name": "lowercase-hyphenated-name", '
        '"command": "python", "args": ["server.py"], "files": {"server.py": "complete source"}}. '
        "The command and args must start the server from its file folder. Any language is allowed."
    ),
    "hook": (
        "Build a Claude Code command hook. It receives event JSON on stdin and exits 0 to allow or 2 to block. "
        'Reply with JSON only: {"event": "PreToolUse", "matcher": "optional pattern", "command": "python hook.py", '
        '"files": {"hook.py": "complete source"}, "sample_event": {"hook_event_name": "PreToolUse"}}. '
        "Use a documented Claude Code event name; the command must work from the file folder."
    ),
}
_TEST_INPUT = (
    "Write one realistic input that the prompt below will receive in real use. Output only that input.\n\nPROMPT:\n{prompt}"
)
_JUDGE = (
    "You judge AI work strictly against what was asked. Reply with JSON only: "
    '{{"score": <0-10>, "missing": ["..."], "fix": "<the single most important change>"}}.\n\n'
    "REQUEST:\n{request}\n\n{subject}"
)
_REVISE = (
    "Improve the {kind} below so it fully achieves the request. Fix this first: {fix}\n"
    "Also missing: {missing}\nOutput only the improved {kind}, nothing else.{form}\n\nREQUEST:\n{request}\n\nCURRENT {upper}:\n{current}"
)
_SUBJECT = {"skill": "SKILL.md", "agent": "SUBAGENT FILE", "copy": "COPY"}
_SITE_FORM = ' Reply with the complete site again as JSON only: {"files": {"index.html": "...", ...}}.'
_JSON_FORM = {
    "rule": ' Reply with the complete rule again as JSON only: {"name": "...", "content": "..."}.',
    "mcp": ' Reply with the complete server again as JSON only: {"name": "...", "command": "...", "args": [...], "files": {...}}.',
    "hook": ' Reply with the complete hook again as JSON only: {"event": "...", "matcher": "...", "command": "...", "files": {...}, "sample_event": {...}}.',
}


class MakeError(Exception):
    """make cannot start (bad provider, kind, limit or input)."""


@dataclass
class Call:
    role: str
    status: str
    code: str | None
    tokens_in: Any
    tokens_out: Any
    usd: Any


@dataclass
class Round:
    version: int
    text: str
    test_output: str | None
    score: int | None
    missing: list[str]
    fix: str


@dataclass
class MakeResult:
    folder: Path
    kind: str
    stopped: str
    best_version: int | None
    best_score: int | None
    spent_usd: Decimal
    rounds: list[Round] = field(default_factory=list)
    calls: list[Call] = field(default_factory=list)
    # The kind's entry when this make researched and learned it (learn.py); ``None`` otherwise.
    learned: dict[str, Any] | None = None


def _slug(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())[:6]
    return "-".join(words) or "made"


def _strip_fences(text: str) -> str:
    match = re.fullmatch(r"\s*```[a-zA-Z0-9_-]*\n(.*?)\n```\s*", text, flags=re.S)
    return (match.group(1) if match else text).strip()


def _judgement(text: str | None) -> tuple[int | None, list[str], str]:
    if not text:
        return None, [], ""
    match = re.search(r"\{.*\}", text, flags=re.S)
    try:
        data = json.loads(match.group(0)) if match else {}
    except ValueError:
        data = {}
    score = data.get("score")
    score = int(score) if isinstance(score, (int, float)) and not isinstance(score, bool) and 0 <= score <= 10 else None
    missing = [str(m) for m in data.get("missing", []) if isinstance(m, (str, int, float))][:10]
    fix = str(data.get("fix", "")).strip()
    return score, missing, fix


class Budget:
    """One spending limit for the whole command; each call may use only what is left."""

    def __init__(self, limit: str | None, local: bool) -> None:
        self.unlimited_local = limit is None and local
        self.left = Decimal(limit) if limit is not None else Decimal(0)
        self.spent = Decimal(0)

    def for_next_call(self) -> str | None:
        if self.unlimited_local:
            return None
        return format(self.left, "f") if self.left > 0 else "0"

    def charge(self, result: live.RunResult) -> None:
        if result.status == "refused":  # nothing was sent, nothing was spent
            return
        figure = (result.cost or {}).get("usd")
        worst = result.admission.get("worst_case_usd")
        for value in (figure, worst):
            try:
                amount = Decimal(str(value))
            except (InvalidOperation, ValueError):
                continue
            if amount.is_finite() and amount >= 0:
                self.spent += amount
                self.left -= amount
                return


def make(
    request: str,
    *,
    provider_id: str,
    model: str,
    kind: str = "prompt",
    max_cost_usd: str | None = None,
    rounds: int = DEFAULT_ROUNDS,
    target: int = DEFAULT_TARGET,
    test_input: str | None = None,
    out_dir: Path | None = None,
    max_output_tokens: int = 2048,
    transport: live.Transport | None = None,
    allow_commands: bool = False,
    platforms: list[str] | None = None,
) -> MakeResult:
    from . import addons, learn

    extra = {} if kind in KINDS else addons.make_kinds()
    if kind not in KINDS and kind not in extra:
        named = learn.kind_name(kind)
        if named is None:
            raise MakeError("a kind is a name such as press-kit: letters, digits and hyphens, 2 to 40 characters")
        kind = named
    if kind in learn.OWN_ENGINE:
        raise MakeError(f"{kind} has its own engine: run `proofhouse make --kind {kind}`")
    # A kind nobody has taught Proofhouse yet is researched by your model first, then made (learn.py).
    learning = kind not in KINDS and kind not in extra
    if not request.strip():
        raise MakeError("say what you want made")
    if type(rounds) is not int or not 1 <= rounds <= 20:
        raise MakeError("rounds must be 1 to 20")
    try:
        catalog = app_platforms.all_platforms() if kind == "app" else {}
    except ValueError as exc:
        raise MakeError(str(exc)) from exc
    chosen = list(dict.fromkeys(platforms if platforms is not None else catalog))
    if kind == "app":
        unknown = [platform for platform in chosen if platform not in catalog]
        if unknown:
            raise MakeError(f"unknown platform: {', '.join(unknown)}; known: {', '.join(sorted(catalog))}")
        if not chosen:
            raise MakeError("choose at least one platform")
    profile = providers.find(provider_id)
    if profile is None:
        raise MakeError(f"no provider named {provider_id!r}; see `proofhouse providers list`")
    if max_cost_usd is None and not profile.local:
        raise MakeError("name a spending limit for the whole make (--max-cost-usd)")
    try:
        budget = Budget(max_cost_usd, profile.local)
    except InvalidOperation:
        raise MakeError("--max-cost-usd must be a decimal such as 0.50") from None

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    folder = out_dir or Path.cwd() / f"make-{_slug(request)}-{stamp}"
    folder.mkdir(parents=True, exist_ok=False)
    result = MakeResult(folder, kind, "rounds used up", None, None, Decimal(0))

    def call(role: str, prompt: str, input_text: str | None = None) -> str | None:
        limit = budget.for_next_call()
        if limit == "0":
            raise _Stop("spending limit reached")
        reply = live.run_prompt(
            profile.id, model, prompt=prompt, input_text=input_text,
            max_output_tokens=max_output_tokens, max_cost_usd=limit, transport=transport,
        )
        cost = reply.cost or {}
        result.calls.append(Call(role, reply.status, reply.code, cost.get("tokens_in"), cost.get("tokens_out"), cost.get("usd")))
        budget.charge(reply)
        if reply.code == "PHC-COST-0001":
            raise _Stop("spending limit reached")
        if reply.status != "success":
            raise _Stop(f"{reply.message}")
        return reply.output_text

    current: str | None = None
    try:
        if learning:
            try:
                result.learned = learn.learn(kind, lambda prompt: call("research", prompt), learned_by=f"{profile.id}/{model}")
            except learn.LearnError as exc:
                raise _Stop(f"could not learn what a {kind} is: {exc}") from None
            extra = {**extra, kind: {**result.learned, "addon": learn.LEARNED_PACK}}
        writer = _WRITE[kind] if kind in _WRITE else extra[kind]["write"]
        label = _SUBJECT.get(kind) or str(extra.get(kind, {}).get("subject") or kind.upper())
        current = _strip_fences(call("write", writer, request) or "")
        if kind == "prompt" and test_input is None:
            test_input = _strip_fences(call("test input", _TEST_INPUT.format(prompt=current)) or "")
        for version in range(1, rounds + 1):
            if not current:
                raise _Stop("the model returned nothing to work with")
            output = None
            if kind == "prompt":
                output = call("try", current, test_input or "")
                subject = f"PROMPT:\n{current}\n\nTEST INPUT:\n{test_input}\n\nOUTPUT IT PRODUCED:\n{output}"
            elif kind == "app":
                output, subject = _try_app(current, request, folder / f"v{version}", chosen, catalog,
                                           allow_commands, call)
            elif kind == "site":
                output, subject = _try_site(current, folder / f"v{version}")
            elif kind in ("rule", "mcp", "hook"):
                output, subject = _try_new_kind(kind, current, request, folder / f"v{version}", allow_commands)
            else:
                subject = f"{label}:\n{current}"
            score, missing, fix = _judgement(call("judge", _JUDGE.format(request=request, subject=subject)))
            result.rounds.append(Round(version, current, output, score, missing, fix))
            if kind not in ("site", "app", "rule", "mcp", "hook"):
                (folder / f"v{version}.md").write_text(current + "\n", encoding="utf-8")
            if score is not None and score >= target:
                result.stopped = f"reached score {score} (target {target})"
                break
            if version == rounds:
                break
            current = _strip_fences(call("revise", _REVISE.format(
                kind=kind, upper=kind.upper(), fix=fix or "make it fully meet the request",
                form=_SITE_FORM if kind in ("site", "app") else _JSON_FORM.get(kind, ""),
                missing="; ".join(missing) or "nothing listed", request=request, current=current,
            ) + (f"\nCHECK FAILURES FROM THIS ROUND:\n{subject}" if kind == "app" else "")) or "")
    except _Stop as stop:
        result.stopped = str(stop)

    scored = [r for r in result.rounds if r.score is not None]
    best = max(scored, key=lambda r: (r.score, r.version)) if scored else (result.rounds[-1] if result.rounds else None)
    if best is not None:
        result.best_version, result.best_score = best.version, best.score
        if kind == "app":
            _deliver_app(folder, best.version, chosen, catalog)
        elif kind == "site":
            source = folder / f"v{best.version}" / "site"
            if source.is_dir():
                shutil.copytree(source, folder / "site")
        elif kind in ("rule", "mcp", "hook"):
            _deliver_new_kind(folder, kind, best.text, request, best.version)
        else:
            _deliver(folder, "copy" if kind in extra else kind, best.text)
    result.spent_usd = budget.spent
    _write_record(folder, request, profile.id, model, max_cost_usd, result, extra.get(kind))
    return result


class _Stop(Exception):
    pass


def _site_files(text: str) -> dict[str, str]:
    match = re.search(r"\{.*\}", text, flags=re.S)
    try:
        data = json.loads(match.group(0)) if match else None
    except ValueError:
        data = None
    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, dict) or not all(isinstance(v, str) for v in files.values()):
        raise sitecheck.SiteError("the model did not return the site as JSON files")
    return files


def _try_site(text: str, version_dir: Path) -> tuple[str, str]:
    """Write this version of the site, check it like a visitor, and describe both for the judge."""
    try:
        names = sitecheck.write_site(_site_files(text), version_dir / "site")
        checks = sitecheck.check_site(version_dir / "site", version_dir / "screenshots")
    except sitecheck.SiteError as exc:
        names, checks = [], [{"check": "site written", "ok": False, "detail": str(exc)}]
    (version_dir).mkdir(parents=True, exist_ok=True)
    (version_dir / "checks.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    failed = [c for c in checks if c["ok"] is False]
    summary = "\n".join(f"- {'PASS' if c['ok'] else ('NOT MEASURED' if c['ok'] is None else 'FAIL')}: {c['check']} {c['detail']}".rstrip()
                        for c in checks)
    index = ""
    if (version_dir / "site" / "index.html").is_file():
        index = (version_dir / "site" / "index.html").read_text(encoding="utf-8")[:8000]
    subject = f"FILES: {', '.join(names) or 'none'}\n\nindex.html:\n{index}\n\nCHECKS RUN ON THE SITE:\n{summary}"
    return f"{len(checks) - len(failed)} of {len(checks)} checks passed", subject


def _try_app(
    text: str, request: str, version_dir: Path, chosen: list[str], catalog: dict[str, dict[str, Any]],
    allow_commands: bool, call: Callable[[str, str, str | None], str | None],
) -> tuple[str, str]:
    _, site_subject = _try_site(text, version_dir)
    checks: list[dict[str, Any]] = json.loads((version_dir / "checks.json").read_text(encoding="utf-8"))
    try:
        shared_files = _site_files(text)
    except sitecheck.SiteError:
        shared_files = {}
    subjects = ["SHARED WEB APP:\n" + site_subject]
    written: dict[str, list[str]] = {}
    responses: dict[str, str] = {}
    # Each platform's next round sees what it wrote last round and which of its checks failed.
    previous = version_dir.parent / f"v{int(version_dir.name[1:]) - 1}"
    try:
        last_checks: list[dict[str, Any]] = json.loads((previous / "checks.json").read_text(encoding="utf-8"))
        last_responses: dict[str, str] = json.loads((previous / "responses.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        last_checks, last_responses = [], {}
    for platform_id in chosen:
        entry = catalog[platform_id]
        web = app_platforms.web_dir(entry)
        place = f"`{web}/`" if web else "the root of your platform folder"
        failed = [f"- {c['check']}: {c['detail']}" for c in last_checks
                  if c.get("ok") is False and str(c.get("check", "")).startswith(platform_id + " ")]
        last_round = (f"\nYOUR FILES LAST ROUND:\n{last_responses.get(platform_id, '')}\n"
                      "CHECKS THAT FAILED LAST ROUND (fix these):\n" + ("\n".join(failed) or "- none")) \
            if platform_id in last_responses else ""
        prompt = (
            f"Build the {entry['name']} platform shell for this working app. Shell: {entry['shell']}. "
            f"Instructions: {entry['write']} Reply with JSON only as {{\"files\": {{...}}}}. "
            f"The shared web files below are copied into {place}; include changed web files (under that path) when needed. "
            f"Required files and JSON checks: {json.dumps(entry['checks'])}.\n"
            f"OWNER REQUEST:\n{request}\nSHARED WEB FILES:\n{json.dumps(shared_files)}{last_round}"
        )
        response = _strip_fences(call(f"write {platform_id}", prompt) or "")
        responses[platform_id] = response[:12000]
        destination = version_dir / platform_id
        try:
            additions = _site_files(response)
            output_name = entry["build"]["output"]
            if "{mainBinaryName}" in output_name or "{productName}" in output_name:
                try:
                    config = json.loads(additions["src-tauri/tauri.conf.json"])
                    for field in ("mainBinaryName", "productName"):
                        if isinstance(config.get(field), str):
                            output_name = output_name.replace("{" + field + "}", config[field])
                except (KeyError, ValueError, TypeError, AttributeError):
                    pass  # Static and build checks report malformed or missing config.
            output = PurePosixPath(output_name.lower()).parts
            # Otherwise a model file could stand in for build output that the build never made.
            if output and any(PurePosixPath(name.lower()).parts[:len(output)] == output for name in additions):
                raise ValueError(f"the model may not write files under the build output {entry['build']['output']}")
            shared_here = {(f"{web}/{name}" if web else name): text for name, text in shared_files.items()}
            app_platforms.check_packages({**shared_here, **additions})
            app_platforms.check_platform({**shared_here, **additions}, entry)
            names = make_checks.write_files({**shared_here, **additions}, destination)
            written[platform_id] = names
            platform_checks = app_platforms.static_checks(destination, entry)
            if entry["checks"].get("site"):
                platform_checks.extend(sitecheck.check_site(destination / web, version_dir / f"screenshots-{platform_id}"))
            platform_checks.append(app_platforms.build_check(destination, entry, allow_commands, _slug(request)))
        except (sitecheck.SiteError, ValueError, OSError) as exc:
            names = []
            platform_checks = [{"check": f"{platform_id} written", "ok": False, "detail": str(exc)}]
        checks.extend(platform_checks)
        subjects.append(f"{entry['name']} FILES: {', '.join(names) or 'none'}\nMODEL FILES:\n{response[:12000]}")
    version_dir.mkdir(parents=True, exist_ok=True)
    (version_dir / "checks.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    (version_dir / "written.json").write_text(json.dumps(written, indent=2) + "\n", encoding="utf-8")
    (version_dir / "responses.json").write_text(json.dumps(responses, indent=2) + "\n", encoding="utf-8")
    summary = "\n".join(f"- {'PASS' if c['ok'] is True else 'FAIL' if c['ok'] is False else 'NOT BUILT'}: "
                        f"{c['check']} {c['detail']}" for c in checks)
    passed = sum(c["ok"] is True for c in checks)
    return f"{passed} of {len(checks)} checks passed", "\n\n".join(subjects) + "\n\nCHECKS:\n" + summary


def _deliver_app(folder: Path, version: int, chosen: list[str], catalog: dict[str, dict[str, Any]]) -> None:
    source = folder / f"v{version}"
    if (source / "site").is_dir():
        shutil.copytree(source / "site", folder / "site")
    checks: list[dict[str, Any]] = json.loads((source / "checks.json").read_text(encoding="utf-8"))
    written: dict[str, list[str]] = json.loads((source / "written.json").read_text(encoding="utf-8"))
    lines = ["# App", "", "Shared web app: `site/index.html` (serve over HTTPS or localhost).", ""]
    for platform_id in chosen:
        entry = catalog[platform_id]
        # Only the source files go out; installed packages and build output stay in the version folder.
        # Build steps ran model code in that folder, so each name and file is checked again: no links, nothing outside.
        base = (source / platform_id).resolve()
        for name in written.get(platform_id, []):
            path = source / platform_id / str(name)
            if not make_checks.safe_name(name) or path.is_symlink() or not path.is_file() \
                    or not path.resolve().is_relative_to(base):
                continue
            target = folder / platform_id / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / platform_id / name, target)
        build = entry["build"]
        steps = [[word.replace("{folder}", ".").replace("{name}", folder.name) for word in step]
                 for step in [*build.get("before", []), build["command"]] if step]
        result = next((c for c in checks if c["check"] == f"{platform_id} build"), None)
        status = result["detail"] if result else "not built"
        built = bool(result and result["ok"] is True and build["output"])
        web = app_platforms.web_dir(entry)
        lines.extend([f"## {entry['name']} ({platform_id})", "", f"Shell: {entry['shell']}",
                      f"Files: `{platform_id}/`", f"Build status: {status}"])
        if built:
            lines.append(f"Built output: `v{version}/{platform_id}/{build['output']}`")
        elif build["output"]:
            lines.append(f"Expected output after building: `{platform_id}/{build['output']}`")
        lines.append(f"Install: {build['install']}")
        if build.get("to_check"):
            lines.append(f"To check: {build['to_check']}")
        lines.extend(["Build by hand: `" + ("cd " + platform_id + " && " + " && ".join(" ".join(step) for step in steps) if steps else
                                          "serve " + (f"{platform_id}/{web}" if web else platform_id)
                                          + " over HTTPS or localhost and install from the browser") + "`", ""])
    (folder / "README.md").write_text("\n".join(lines), encoding="utf-8")


def _try_new_kind(kind: str, text: str, request: str, version_dir: Path, allow_commands: bool) -> tuple[str, str]:
    version_dir.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    try:
        if kind == "rule":
            name, checks = make_checks.rule(text, request, version_dir)
            names = [f"{name}.md"]
        else:
            data = make_checks.parse_json(text)
            names = make_checks.write_files(data.get("files"), version_dir / kind)
            checks = make_checks.mcp(data, version_dir / kind, allow_commands) if kind == "mcp" \
                else make_checks.hook(data, version_dir / kind, allow_commands)
            (version_dir / "manifest.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except (ValueError, OSError) as exc:
        checks = [{"check": f"{kind} written", "ok": False, "detail": str(exc)}]
    (version_dir / "checks.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    summary = "\n".join(f"- {'PASS' if c['ok'] else ('NOT CHECKED' if c['ok'] is None else 'FAIL')}: "
                        f"{c['check']} {c['detail']}" for c in checks)
    subject = f"{kind.upper()} SPECIFICATION:\n{text[:12000]}\n\nFILES: {', '.join(names) or 'none'}\n\nCHECKS:\n{summary}"
    passed = sum(c["ok"] is True for c in checks)
    return f"{passed} of {len(checks)} checks passed", subject


def _deliver_new_kind(folder: Path, kind: str, text: str, request: str, version: int) -> None:
    source = folder / f"v{version}"
    if kind == "rule":
        for path in source.glob("*.md"):
            shutil.copy2(path, folder / path.name)
        return
    if not (source / kind).is_dir():
        return
    data = make_checks.parse_json(text)
    make_checks.write_files(data.get("files"), folder / kind)
    if kind == "mcp":
        from .hosts import check_name
        try:
            name = check_name(data["name"])
        except (KeyError, ValueError):
            name = _slug(request)
        command, args = data.get("command"), data.get("args")
        if not isinstance(command, str) or not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            return
        line = make_checks.install_line(name, command, args, folder / kind)
        if line is not None:
            (folder / "INSTALL-MCP.txt").write_text(line + "\n", encoding="utf-8")
    else:
        event, command, matcher = data.get("event"), data.get("command"), data.get("matcher")
        if not isinstance(event, str) or not isinstance(command, str):
            return
        snippet = make_checks.settings_snippet(event, matcher if isinstance(matcher, str) else None, command, folder / kind)
        if snippet is not None:
            (folder / "settings-snippet.json").write_text(json.dumps(snippet, indent=2) + "\n", encoding="utf-8")


def _deliver(folder: Path, kind: str, text: str) -> None:
    if kind in ("prompt", "copy"):
        (folder / "final.md").write_text(text + "\n", encoding="utf-8")
        return
    if kind == "agent":
        from .hosts import HostError, check_name
        from .hosts_cli import _frontmatter_value

        try:
            name = check_name(_frontmatter_value(text + "\n", "name") or "")
            if not _frontmatter_value(text + "\n", "description"):
                raise HostError("no description")
        except HostError as exc:
            (folder / "final-agent.md").write_text(text + "\n", encoding="utf-8")
            (folder / "AGENT-NOT-INSTALLABLE.txt").write_text(f"{exc}\n", encoding="utf-8")
            return
        (folder / f"{name}.md").write_text(text + "\n", encoding="utf-8")
        return
    from .optimize.install_skill import check_frontmatter

    try:
        name = check_frontmatter(text)
    except Exception as exc:  # noqa: BLE001 -- the model's skill text failed the installer's own check
        (folder / "final-SKILL.md").write_text(text + "\n", encoding="utf-8")
        (folder / "SKILL-NOT-INSTALLABLE.txt").write_text(f"{exc}\n", encoding="utf-8")
        return
    skill = folder / name
    skill.mkdir(exist_ok=True)
    (skill / "SKILL.md").write_text(text + "\n", encoding="utf-8")


def _write_record(
    folder: Path, request: str, provider_id: str, model: str, limit: str | None, result: MakeResult,
    kind_entry: dict[str, Any] | None = None,
) -> None:
    record = {
        "schema": "proofhouse.make/v1",
        "proofhouse_version": __version__,
        "request": request,
        "kind": result.kind,
        "provider": provider_id,
        "model": model,
        "spending_limit_usd": limit,
        "spent_usd_estimated": format(result.spent_usd, "f"),
        "stopped": result.stopped,
        "best_version": result.best_version,
        "best_score": result.best_score,
        "judge_note": "scores come from a model acting as judge; they are advice, not proof",
        "rounds": [vars(r) for r in result.rounds],
        "calls": [vars(c) for c in result.calls],
    }
    if kind_entry is not None:  # an add-on or learned kind: say where its writer instructions came from
        record["kind_from"] = {key: kind_entry[key] for key in (
            "addon", "what_it_is", "sources", "sources_note", "learned_by", "learned_at") if key in kind_entry}
        record["kind_from"]["learned_this_run"] = result.learned is not None
    (folder / "record.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
