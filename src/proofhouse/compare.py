"""The same job on many models at once: outputs side by side with cost and time, and (optionally) a judge's scores.

The spending limit covers everything, including the judge. Calls run at the
same time, so each gets an equal share of the limit; no share can borrow from
another, and the total can never pass the limit.
"""

from __future__ import annotations

import hashlib
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

from . import __version__
from .make import _slug

MAX_TARGETS = 24
MAX_FILE_BYTES = 1_000_000

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
    provider: str = ""
    model: str = ""
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
    file_name: str | None = None
    sha256: str | None = None
    bytes: int | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class Comparison:
    folder: Path
    entries: list[Entry] = field(default_factory=list)
    best: str | None = None
    judge: dict[str, Any] | None = None
    files_judge: str | None = None
    spent_usd: Decimal = Decimal(0)
    mode: str = "models"


def parse_target(text: str) -> tuple[str, str]:
    provider, sep, model = text.partition(":")
    if not sep or not provider.strip() or not model.strip():
        raise CompareError(f"{text!r} must be provider:model, for example groq:llama-3.3-70b-versatile")
    return provider.strip(), model.strip()


def parse_label_value(text: str, *, what: str) -> tuple[str, str]:
    if "=" not in text:
        raise CompareError(f"{what} must be LABEL=value, for example cursor:composer-2.5=output.md")
    label, _, rest = text.partition("=")
    label, value = label.strip(), rest.strip()
    if not label:
        raise CompareError(f"{what} must be LABEL=value, for example cursor:composer-2.5=output.md")
    if not value:
        raise CompareError(f"{what} must be LABEL=value, for example cursor:composer-2.5=output.md")
    return label, value


def parse_score_value(text: str) -> tuple[str, int]:
    label, raw = parse_label_value(text, what="--score")
    try:
        number = float(raw)
    except ValueError:
        raise CompareError(f"score for {label!r} must be 0–10") from None
    if number != int(number) or not 0 <= number <= 10:
        raise CompareError(f"score for {label!r} must be 0–10")
    return label, int(number)


def _read_entry_file(path: Path) -> tuple[bytes, str]:
    if path.is_symlink():
        raise CompareError(f"symbolic link not allowed: {path}")
    if not path.is_file():
        raise CompareError(f"file not found: {path}")
    data = path.read_bytes()
    if not data:
        raise CompareError(f"file is empty: {path}")
    if len(data) > MAX_FILE_BYTES:
        raise CompareError(f"file is over 1 MB: {path}")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise CompareError(f"file is not UTF-8: {path}") from None
    return data, text


def _output_name(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-") or "output"


def _best_from_scores(entries: list[Entry]) -> str | None:
    scored = [(e.label, e.score) for e in entries if e.score is not None]
    if len(scored) < 2:
        return None
    top = max(score for _, score in scored)
    winners = [label for label, score in scored if score == top]
    return winners[0] if len(winners) == 1 else None


def compare_from_files(
    job: str,
    entries: list[tuple[str, Path]],
    *,
    scores: dict[str, int] | None = None,
    notes: dict[str, str] | None = None,
    files_judge: str | None = None,
    out_dir: Path | None = None,
) -> Comparison:
    if not job.strip():
        raise CompareError("give the job to run")
    if len(entries) < 2:
        raise CompareError("name at least two outputs with --entry LABEL=path")
    if len(entries) > MAX_TARGETS:
        raise CompareError(f"name at most {MAX_TARGETS} outputs with --entry LABEL=path")
    labels = [label for label, _ in entries]
    if len(set(labels)) != len(labels):
        raise CompareError("duplicate label in --entry")
    scores = scores or {}
    notes = notes or {}
    unknown = (set(scores) | set(notes)) - set(labels)
    if unknown:
        raise CompareError(f"unknown label {sorted(unknown)[0]!r}; use --entry for every label you score or note")
    if files_judge:
        from .host import agent_base

        if any(agent_base(files_judge) == agent_base(label) for label in labels):
            raise CompareError("judge must differ from every entry label")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    folder = (out_dir or Path.cwd() / f"compare-{_slug(job)}-{stamp}").resolve()
    folder.mkdir(parents=True, exist_ok=False)

    built: list[Entry] = []
    for label, path in entries:
        data, text = _read_entry_file(path.absolute())  # resolve() would follow a link past the check
        entry = Entry(
            label=label,
            status="success",
            output=text,
            file_name=f"{_output_name(label)}.md",
            sha256=hashlib.sha256(data).hexdigest(),
            bytes=len(data),
            score=scores.get(label),
            note=notes.get(label),
            why=notes.get(label) or "",
        )
        built.append(entry)
    result = Comparison(folder, built, mode="files", files_judge=files_judge)
    result.best = _best_from_scores(built)
    _write_files(folder, job, result)
    return result


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
    transport: Any | None = None,
    workers: int = 8,
) -> Comparison:
    from . import live, providers

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


def _files_compare_note(result: Comparison) -> str:
    if result.files_judge:
        return f"Scores by {result.files_judge}. Proofhouse did not call any model for this comparison."
    if any(entry.score is not None for entry in result.entries):
        return "Scores are the writers' own advice. Proofhouse did not call any model for this comparison."
    return "Proofhouse did not call any model for this comparison."


def _write_files(folder: Path, job: str, result: Comparison) -> None:
    outputs = folder / "outputs"
    outputs.mkdir(exist_ok=True)
    json_entries: list[dict[str, Any]] = []
    taken: set[str] = set()
    for entry in result.entries:
        name = entry.file_name or f"{_output_name(entry.label)}.md"
        # Labels such as "a:b" and "a/b" clean to one name, and Windows ignores case; never overwrite.
        stem, n = name[: -len(".md")] if name.endswith(".md") else name, 2
        while name.lower() in taken:
            name, n = f"{stem}-{n}.md", n + 1
        taken.add(name.lower())
        entry.file_name = name
        (outputs / name).write_text((entry.output or "") + "\n", encoding="utf-8")
        json_entries.append(
            {
                "label": entry.label,
                "file": name,
                "sha256": entry.sha256,
                "bytes": entry.bytes,
                "score": entry.score,
                "note": entry.note,
            }
        )
    record: dict[str, Any] = {
        "proofhouse_version": __version__,
        "mode": "files",
        "job": job,
        "best": result.best,
        "entries": json_entries,
        "note": _files_compare_note(result),
    }
    if result.files_judge:
        record["judge"] = result.files_judge
    (folder / "compare.json").write_text(json.dumps(record, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (folder / "side-by-side.html").write_text(_page(job, result), encoding="utf-8")


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
    files_mode = result.mode == "files"
    if files_mode:
        note = _files_compare_note(result)
        banner = f"<p class=banner>{html.escape(note)}</p>"
    else:
        banner = ""
    cards = []
    for e in result.entries:
        if files_mode:
            best = " best" if result.best == e.label else ""
            facts = [f"{e.bytes} bytes"] if e.bytes is not None else []
            title = html.escape(e.label)
            why = e.note or e.why
        else:
            best = " best" if result.best == f"{e.provider}:{e.model}" else ""
            facts = [f"{e.status}", f"${e.usd}" if e.usd is not None else "cost unknown",
                     f"{e.seconds}s" if e.seconds is not None else "", f"{e.tokens_out} tokens out" if e.tokens_out is not None else ""]
            title = f"{html.escape(e.provider)} · {html.escape(e.model)}"
            why = e.why
        score = f"<p class=score>{e.score}/10 — {html.escape(why)}</p>" if e.score is not None else ""
        body = html.escape(e.output or e.message or "")
        cards.append(f"<section class='card{best}'><h2>{title}</h2>"
                     f"<p class=facts>{html.escape(' · '.join(f for f in facts if f))}</p>{score}<pre>{body}</pre></section>")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Side by side</title>
<style>
:root {{ --bg:#fff; --fg:#1b1b1f; --muted:#5d5d66; --line:#d9d9e0; --best:#1a7f37; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#141417; --fg:#ececf1; --muted:#a0a0ab; --line:#33333b; --best:#3fb950; }} }}
body {{ margin:0; padding:16px; background:var(--bg); color:var(--fg); font:15px/1.5 system-ui, sans-serif; }}
.job {{ color:var(--muted); white-space:pre-wrap; margin-bottom:16px; }}
.banner {{ color:var(--muted); margin:0 0 16px; font-size:14px; }}
.grid {{ display:grid; gap:12px; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); }}
.card {{ border:1px solid var(--line); border-radius:8px; padding:12px; min-width:0; }}
.card.best {{ border:2px solid var(--best); }}
h2 {{ font-size:15px; margin:0 0 4px; overflow-wrap:anywhere; }}
.facts, .score {{ color:var(--muted); margin:0 0 8px; font-size:13px; }}
pre {{ white-space:pre-wrap; overflow-wrap:anywhere; margin:0; font:13px/1.45 ui-monospace, monospace; }}
</style></head><body>
<h1>Side by side</h1>{banner}<p class=job>{html.escape(prompt)}</p>
<div class=grid>{''.join(cards)}</div>
</body></html>
"""
