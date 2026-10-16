"""The same job on many models at once: outputs side by side with cost and time, and (optionally) a judge's scores.

The spending limit covers everything, including the judge. Calls run at the
same time, so each gets an equal share of the limit; no share can borrow from
another, and the total can never pass the limit.
"""

from __future__ import annotations

import html
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import ROUND_DOWN, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from . import __version__, live, providers
from .make import _slug

MAX_TARGETS = 24

_JUDGE = """You judge AI outputs. Several models were given the same job. Score each output from 0 to 10
for how well it does what was asked: correctness first, then completeness, then clarity. Be strict and fair;
the outputs are anonymous. Answer with ONE JSON object and nothing else:
{"scores": {"A": {"score": 7, "why": "one sentence"}, "B": {...}}, "best": "A"}

THE JOB:
%s
%s
THE OUTPUTS:
%s"""


class CompareError(ValueError):
    """The comparison cannot start as asked."""


@dataclass
class Entry:
    label: str
    provider: str
    model: str
    status: str = "not run"
    code: str | None = None
    message: str | None = None
    output: str | None = None
    tokens_in: Any = None
    tokens_out: Any = None
    usd: Any = None
    seconds: float | None = None
    score: int | None = None
    why: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class Comparison:
    folder: Path
    entries: list[Entry] = field(default_factory=list)
    best: str | None = None
    judge: dict[str, Any] | None = None
    spent_usd: Decimal = Decimal(0)


def parse_target(text: str) -> tuple[str, str]:
    provider, sep, model = text.partition(":")
    if not sep or not provider.strip() or not model.strip():
        raise CompareError(f"{text!r} must be provider:model, for example groq:llama-3.3-70b-versatile")
    return provider.strip(), model.strip()


def _figure(value: Any) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal(0)
    return amount if amount.is_finite() and amount >= 0 else Decimal(0)


def _spent(reply: live.RunResult) -> Decimal:
    if reply.status == "refused":
        return Decimal(0)
    cost = (reply.cost or {}).get("usd")
    return _figure(cost if cost is not None else reply.admission.get("worst_case_usd"))


def compare(
    prompt: str,
    targets: list[str],
    *,
    input_text: str | None = None,
    judge: str | None = None,
    max_cost_usd: str | None = None,
    max_output_tokens: int = 2048,
    out_dir: Path | None = None,
    transport: live.Transport | None = None,
    workers: int = 8,
) -> Comparison:
    if not prompt.strip():
        raise CompareError("give the job to run")
    pairs = [parse_target(t) for t in targets]
    if not 1 <= len(pairs) <= MAX_TARGETS:
        raise CompareError(f"name 1 to {MAX_TARGETS} models with --on provider:model")
    judge_pair = parse_target(judge) if judge else None
    profiles = {}
    for provider_id, _ in pairs + ([judge_pair] if judge_pair else []):
        profile = providers.find(provider_id)
        if profile is None:
            raise CompareError(f"no provider named {provider_id!r}; see `proofhouse providers list`")
        profiles[provider_id] = profile
    paid = any(not p.local for p in profiles.values())
    if paid and max_cost_usd is None:
        raise CompareError("name one spending limit for the whole comparison (--max-cost-usd)")
    share: str | None = None
    if max_cost_usd is not None:
        try:
            limit = Decimal(max_cost_usd)
        except InvalidOperation:
            raise CompareError("--max-cost-usd must be a decimal such as 1.00") from None
        if not limit.is_finite() or limit <= 0:
            raise CompareError("--max-cost-usd must be above zero")
        calls = len(pairs) + (1 if judge_pair else 0)
        share = format((limit / calls).quantize(Decimal("0.000001"), rounding=ROUND_DOWN), "f")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    folder = (out_dir or Path.cwd() / f"compare-{_slug(prompt)}-{stamp}").resolve()
    folder.mkdir(parents=True, exist_ok=False)
    labels = [chr(ord("A") + i) if i < 26 else f"M{i}" for i in range(len(pairs))]
    result = Comparison(folder, [Entry(label, p, m) for label, (p, m) in zip(labels, pairs)])

    def run(entry: Entry) -> Decimal:
        started = time.monotonic()
        reply = live.run_prompt(entry.provider, entry.model, prompt=prompt, input_text=input_text,
                                max_output_tokens=max_output_tokens, max_cost_usd=share, transport=transport)
        entry.seconds = round(time.monotonic() - started, 2)
        cost = reply.cost or {}
        entry.status, entry.code, entry.message, entry.output = reply.status, reply.code, reply.message, reply.output_text
        entry.tokens_in, entry.tokens_out, entry.usd = cost.get("tokens_in"), cost.get("tokens_out"), cost.get("usd")
        return _spent(reply)

    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(result.entries)))) as pool:
        result.spent_usd = sum(pool.map(run, result.entries), Decimal(0))

    answered = [e for e in result.entries if e.status == "success" and e.output]
    if judge_pair and answered:
        given = f"\nTHE INPUT IT WAS GIVEN:\n{input_text}\n" if input_text else ""
        shown = "\n\n".join(f"--- OUTPUT {e.label} ---\n{e.output}" for e in answered)
        reply = live.run_prompt(judge_pair[0], judge_pair[1], prompt=_JUDGE % (prompt, given, shown),
                                max_output_tokens=1024, max_cost_usd=share, transport=transport)
        result.spent_usd += _spent(reply)
        result.judge = {"provider": judge_pair[0], "model": judge_pair[1], "status": reply.status, "code": reply.code,
                        "note": "Scores are a model's advice, not proof."}
        _apply_scores(result, reply.output_text if reply.status == "success" else None)

    _write(folder, prompt, input_text, max_cost_usd, result)
    return result


def _apply_scores(result: Comparison, text: str | None) -> None:
    match = re.search(r"\{.*\}", text or "", flags=re.S)
    try:
        data = json.loads(match.group(0)) if match else {}
    except ValueError:
        data = {}
    scores = data.get("scores") if isinstance(data, dict) else None
    if not isinstance(scores, dict):
        return
    for entry in result.entries:
        given = scores.get(entry.label)
        if isinstance(given, dict) and type(given.get("score")) is int and 0 <= given["score"] <= 10:
            entry.score, entry.why = given["score"], str(given.get("why") or "")
    scored = [e for e in result.entries if e.score is not None]
    if scored:
        top = max(scored, key=lambda e: (e.score, -_figure(e.usd), -(e.seconds or 0)))
        result.best = f"{top.provider}:{top.model}"


def _write(folder: Path, prompt: str, input_text: str | None, limit: str | None, result: Comparison) -> None:
    outputs = folder / "outputs"
    outputs.mkdir(exist_ok=True)
    for entry in result.entries:
        name = re.sub(r"[^A-Za-z0-9._-]+", "-", f"{entry.label}-{entry.provider}-{entry.model}")
        (outputs / f"{name}.md").write_text((entry.output or f"({entry.status}: {entry.message})") + "\n", encoding="utf-8")
    record = {"proofhouse_version": __version__, "prompt": prompt, "input": input_text, "max_cost_usd": limit, "best": result.best, "judge": result.judge,
              "spent_usd_estimated": format(result.spent_usd, "f"), "entries": [e.to_dict() for e in result.entries],
              "note": "Dollar figures are estimates from token counts and prices, not your bill."}
    (folder / "compare.json").write_text(json.dumps(record, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (folder / "side-by-side.html").write_text(_page(prompt, result), encoding="utf-8")


def _page(prompt: str, result: Comparison) -> str:
    cards = []
    for e in result.entries:
        best = " best" if result.best == f"{e.provider}:{e.model}" else ""
        facts = [f"{e.status}", f"${e.usd}" if e.usd is not None else "cost unknown",
                 f"{e.seconds}s" if e.seconds is not None else "", f"{e.tokens_out} tokens out" if e.tokens_out is not None else ""]
        score = f"<p class=score>{e.score}/10 — {html.escape(e.why)}</p>" if e.score is not None else ""
        body = html.escape(e.output or e.message or "")
        cards.append(f"<section class='card{best}'><h2>{html.escape(e.provider)} · {html.escape(e.model)}</h2>"
                     f"<p class=facts>{html.escape(' · '.join(f for f in facts if f))}</p>{score}<pre>{body}</pre></section>")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Side by side</title>
<style>
:root {{ --bg:#fff; --fg:#1b1b1f; --muted:#5d5d66; --line:#d9d9e0; --best:#1a7f37; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#141417; --fg:#ececf1; --muted:#a0a0ab; --line:#33333b; --best:#3fb950; }} }}
body {{ margin:0; padding:16px; background:var(--bg); color:var(--fg); font:15px/1.5 system-ui, sans-serif; }}
.job {{ color:var(--muted); white-space:pre-wrap; margin-bottom:16px; }}
.grid {{ display:grid; gap:12px; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); }}
.card {{ border:1px solid var(--line); border-radius:8px; padding:12px; min-width:0; }}
.card.best {{ border:2px solid var(--best); }}
h2 {{ font-size:15px; margin:0 0 4px; overflow-wrap:anywhere; }}
.facts, .score {{ color:var(--muted); margin:0 0 8px; font-size:13px; }}
pre {{ white-space:pre-wrap; overflow-wrap:anywhere; margin:0; font:13px/1.45 ui-monospace, monospace; }}
</style></head><body>
<h1>Side by side</h1><p class=job>{html.escape(prompt)}</p>
<div class=grid>{''.join(cards)}</div>
</body></html>
"""
