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

Everything lands in one folder: every version, every test output, every score,
and every call's tokens and estimated cost (``record.json``), plus the best
version (``final.md``, or the skill folder). The judge is a model, so its score
is advice, not proof.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from . import live, providers

KINDS = ("prompt", "skill")
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
    "Also missing: {missing}\nOutput only the improved {kind}, nothing else.\n\nREQUEST:\n{request}\n\nCURRENT {upper}:\n{current}"
)


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


class _Budget:
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
) -> MakeResult:
    if kind not in KINDS:
        raise MakeError(f"kind must be one of {', '.join(KINDS)}")
    if not request.strip():
        raise MakeError("say what you want made")
    if type(rounds) is not int or not 1 <= rounds <= 20:
        raise MakeError("rounds must be 1 to 20")
    profile = providers.find(provider_id)
    if profile is None:
        raise MakeError(f"no provider named {provider_id!r}; see `proofhouse providers list`")
    if max_cost_usd is None and not profile.local:
        raise MakeError("name a spending limit for the whole make (--max-cost-usd)")
    try:
        budget = _Budget(max_cost_usd, profile.local)
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
        current = _strip_fences(call("write", _WRITE[kind], request) or "")
        if kind == "prompt" and test_input is None:
            test_input = _strip_fences(call("test input", _TEST_INPUT.format(prompt=current)) or "")
        for version in range(1, rounds + 1):
            if not current:
                raise _Stop("the model returned nothing to work with")
            output = None
            if kind == "prompt":
                output = call("try", current, test_input or "")
                subject = f"PROMPT:\n{current}\n\nTEST INPUT:\n{test_input}\n\nOUTPUT IT PRODUCED:\n{output}"
            else:
                subject = f"SKILL.md:\n{current}"
            score, missing, fix = _judgement(call("judge", _JUDGE.format(request=request, subject=subject)))
            result.rounds.append(Round(version, current, output, score, missing, fix))
            (folder / f"v{version}.md").write_text(current + "\n", encoding="utf-8")
            if score is not None and score >= target:
                result.stopped = f"reached score {score} (target {target})"
                break
            if version == rounds:
                break
            current = _strip_fences(call("revise", _REVISE.format(
                kind=kind, upper=kind.upper(), fix=fix or "make it fully meet the request",
                missing="; ".join(missing) or "nothing listed", request=request, current=current,
            )) or "")
    except _Stop as stop:
        result.stopped = str(stop)

    scored = [r for r in result.rounds if r.score is not None]
    best = max(scored, key=lambda r: (r.score, r.version)) if scored else (result.rounds[-1] if result.rounds else None)
    if best is not None:
        result.best_version, result.best_score = best.version, best.score
        _deliver(folder, kind, best.text)
    result.spent_usd = budget.spent
    _write_record(folder, request, profile.id, model, max_cost_usd, result)
    return result


class _Stop(Exception):
    pass


def _deliver(folder: Path, kind: str, text: str) -> None:
    if kind == "prompt":
        (folder / "final.md").write_text(text + "\n", encoding="utf-8")
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


def _write_record(folder: Path, request: str, provider_id: str, model: str, limit: str | None, result: MakeResult) -> None:
    record = {
        "schema": "proofhouse.make/v1",
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
    (folder / "record.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
