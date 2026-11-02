"""Before make writes a prompt, skill, agent, rule or any other text kind, it interviews you.

1. Which AI tool or model is it for? Known tools come from the host list (``hosts.json``), known models
   from the model registry. Anything else is researched by your model and learned, never refused.
2. Questions: the framework's clarify step (``packets.clarify_packet``), told how that tool or model
   wants the thing written.
3. Say-back: the model says in plain words what it understood, and you confirm or correct it.

The answers become the brief that make writes, judges and revises against. Answers come from the
terminal, or from a file (``--answers``) for scripts and host agents. With neither, the interview
pauses: it leaves the questions in the make folder, and the same command with ``--answers`` goes on.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

from . import hosts, learn, learn_catalog
from .optimize import packets
from .optimize.model_notes import FALLBACK_ID, ResolvedNotes, prompt_notes, proofhouse_home, resolve_model_notes
from .optimize.registry import find_model, load_registry

SCHEMA = "proofhouse.make-interview/v1"
MAX_QUESTIONS = 30
INTERVIEW_FILES = ("questions.md", "understood.md")  # what the owner reads; never the made thing itself
MAX_FIXES = 3
NOT_ANSWERED = "(not answered)"
TYPES = ("single_select", "multi_select", "text")
_GUIDE_LIMIT = 4000
_ACCEPT = ("", "y", "yes", "ok", "okay", "right", "correct")

# One call: ``ask(role, prompt, input_text=None)``, through make's spend gate.
Ask = Callable[..., "str | None"]

_WHAT_IS = (
    'Someone wants a {kind} made for "{entered}". Is that an AI tool or app people work in (such as a coding tool, '
    "a chat app or an agent), or an AI model that is called directly? Reply with JSON only: "
    '{{"sort": "tool" or "model", "id": "<short lowercase-hyphenated name>", "name": "<its proper name>"}}'
)
_GUIDE_RESEARCH = (
    "Proofhouse is about to write a {kind} for {name} ({sort}). From {name}'s own documentation as you know it, say how "
    "{name} wants a {kind} written so it works at its best: the file or form it takes, required fields or frontmatter, "
    "where it goes, what the body should hold, length limits, and what to avoid. If {name} has no such thing as a {kind}, "
    "say what the closest thing is and how to write that. Reply with JSON only: "
    '{{"name": "<proper name>", "guide": "<the guidance, under 250 words>", "sources": ["https://..."]}}'
)
_KIND_NOTE = (
    "\n\nHere the thing being made is a {kind} for {name}, not only a prompt: ask what you need to write an excellent "
    "{kind} for {name}, in the form {name} wants."
)
_SAY_BACK = (
    "You are about to write a {kind} for {name}. Before writing anything, say back in plain everyday words what you "
    "understood, so the owner can correct it. Use short bullet points under these headings: What it is; Who or what "
    "uses it; What it must do; What it must not do; The form {name} needs; What I am assuming. Under 150 words. No "
    "jargon: if a technical term is needed, put it in brackets after the plain words. Output only the bullet points."
    "\n\n{brief}"
)


class InterviewError(Exception):
    """The interview cannot go on (no tool or model named, a bad answers file)."""


class Paused(Exception):
    """The interview needs answers it does not have yet; the questions are in the make folder."""

    def __init__(self, stage: str) -> None:
        super().__init__(stage)
        self.stage = stage


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    type: str
    options: tuple[str, ...] = ()
    depends_on: tuple[str, tuple[str, ...]] | None = None
    group: str = ""

    def to_dict(self) -> dict[str, Any]:
        depends = {"questionId": self.depends_on[0], "values": list(self.depends_on[1])} if self.depends_on else None
        return {"id": self.id, "text": self.text, "type": self.type, "options": list(self.options),
                "dependsOn": depends, "group": self.group}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Question:
        depends = data.get("dependsOn")
        return cls(data["id"], data["text"], data["type"], tuple(data.get("options") or ()),
                   (depends["questionId"], tuple(depends["values"])) if depends else None, data.get("group", ""))


_FALLBACK = (
    Question("goal", "What should it achieve, in a sentence or two?", "text", group="Scope & Goal"),
    Question("users", "Who or what will use it?", "text", group="Scope & Goal"),
    Question("must", "What must it always do?", "text", group="Constraints & Format"),
    Question("must_not", "What must it never do?", "text", group="Constraints & Format"),
    Question("done", "How will you know it worked?", "text", group="Constraints & Format"),
)


@dataclass(frozen=True)
class ToolTarget:
    """The AI tool or model the result is made for, and how it wants the thing written."""

    entered: str
    id: str
    name: str
    sort: str  # "tool" (people work in it) or "model" (called directly)
    guide: str
    guide_source: str
    learned_by: str | None = None  # set when a model researched the guide and nobody has reviewed it

    def to_dict(self) -> dict[str, Any]:
        return dict(vars(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolTarget:
        return cls(**{key: data.get(key) for key in ("entered", "id", "name", "sort", "guide", "guide_source", "learned_by")})


@dataclass
class Interview:
    request: str
    kind: str
    target: ToolTarget | None = None
    questions: list[Question] = field(default_factory=list)
    questions_from: str = "model"
    entries: list[tuple[str, str]] = field(default_factory=list)
    answered: bool = False
    understood: str | None = None
    corrections: list[str] = field(default_factory=list)
    confirmed: bool = False

    def brief(self) -> str:
        """What make writes, judges and revises against: the request plus everything the interview found."""
        parts = [f"REQUEST:\n{self.request}"]
        if self.target is not None:
            sort = "an AI tool people work in" if self.target.sort == "tool" else "an AI model called directly"
            parts.append(f"MADE FOR: {self.target.name} ({sort})")
        if self.entries:
            parts.append("WHAT THE OWNER TOLD US:\n" + packets.format_answered_entries(self.entries))
        if self.confirmed and self.understood:
            parts.append(f"UNDERSTANDING THE OWNER CONFIRMED:\n{self.understood}")
        if self.corrections:
            parts.append("CORRECTIONS FROM THE OWNER (these win over everything above):\n"
                         + "\n".join(f"- {c}" for c in self.corrections))
        if self.target is not None and self.target.guide:
            parts.append(f"HOW {self.target.name.upper()} WANTS A {self.kind.upper()} WRITTEN "
                         f"(from {self.target.guide_source}):\n{self.target.guide}")
        return "\n\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA, "request": self.request, "kind": self.kind,
            "target": self.target.to_dict() if self.target else None,
            "questions": [q.to_dict() for q in self.questions], "questions_from": self.questions_from,
            "entries": [list(e) for e in self.entries], "answered": self.answered, "understood": self.understood,
            "corrections": list(self.corrections), "confirmed": self.confirmed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Interview:
        if data.get("schema") != SCHEMA:
            raise InterviewError("interview.json is not a Proofhouse make interview")
        return cls(
            data["request"], data["kind"], ToolTarget.from_dict(data["target"]) if data.get("target") else None,
            [Question.from_dict(q) for q in data.get("questions") or []], data.get("questions_from", "model"),
            [(str(a), str(b)) for a, b in data.get("entries") or []], bool(data.get("answered")),
            data.get("understood"), list(data.get("corrections") or []), bool(data.get("confirmed")),
        )


class Interviewer(Protocol):
    def target(self) -> str | None: ...
    def answers(self, questions: list[Question]) -> dict[str, str] | None: ...
    def confirm(self, understood: str, corrections: list[str]) -> bool | str | None: ...


# --- questions ---------------------------------------------------------------------------------------

def _json_value(text: str | None) -> Any:
    body = text or ""
    for start in sorted(i for i in (body.find("["), body.find("{")) if i >= 0):
        try:
            return json.JSONDecoder().raw_decode(body[start:])[0]
        except ValueError:
            continue
    return None


def _clean_id(raw: str, n: int) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", raw.lower()).strip("_")[:40] or f"q{n}"


def parse_questions(text: str | None) -> list[Question]:
    """The framework's question batch, read leniently: fences, prose, a flat list or one group are all fine."""
    data = _json_value(text)
    if isinstance(data, dict):
        data = data.get("groups") or data.get("questions") or ([data] if isinstance(data.get("questions"), list) else None)
    if not isinstance(data, list):
        raise ValueError("the reply holds no question list")
    flat: list[tuple[str, dict[str, Any]]] = []
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("questions"), list):
            flat += [(str(item.get("group") or ""), q) for q in item["questions"] if isinstance(q, dict)]
        elif isinstance(item, dict):
            flat.append(("", item))
    found: list[Question] = []
    ids: dict[str, str] = {}  # the model's id -> ours
    for group, q in flat:
        text_ = str(q.get("text") or q.get("question") or "").strip()
        if not text_ or len(found) >= MAX_QUESTIONS:
            continue
        raw = str(q.get("id") or text_)
        qid = base = _clean_id(raw, len(found) + 1)
        n = 2
        while qid in ids.values():
            qid, n = f"{base}_{n}", n + 1
        ids.setdefault(raw, qid)
        kind = q.get("type") if q.get("type") in TYPES else "text"
        options = tuple(str(o).strip() for o in q.get("options") or [] if str(o).strip()) \
            if isinstance(q.get("options"), list) and kind != "text" else ()
        if not options:
            kind = "text"
        depends = q.get("dependsOn")
        parent, values = None, ()
        if isinstance(depends, dict):
            parent = depends.get("questionId")
            values = tuple(str(v) for v in depends.get("values") or [] if str(v).strip()) \
                if isinstance(depends.get("values"), list) else ()
        elif isinstance(depends, str):
            parent = depends
        found.append(Question(qid, text_, kind, options,
                              (ids[parent], values) if isinstance(parent, str) and parent in ids else None, group))
    if not found:
        raise ValueError("the reply holds no questions")
    return found


def applies(question: Question, answers: dict[str, str]) -> bool:
    """A follow-up question is asked only when its parent's answer is one that triggers it."""
    if question.depends_on is None:
        return True
    parent, values = question.depends_on
    given = answers.get(parent, "")
    if not given or given == NOT_ANSWERED:
        return False
    chosen = {part.strip().lower() for part in given.split(",")}
    return not values or any(value.strip().lower() in chosen for value in values)


# --- the tool or model it is for ---------------------------------------------------------------------

def _key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _known_host(key: str) -> tuple[str, str, dict[str, Any]] | None:
    for host_id, host in hosts.all_hosts().items():
        names = [host_id, str(host.get("name") or "")] + [str(a) for a in host.get("aliases") or [] if isinstance(a, str)]
        if key in {_key(n) for n in names if n}:
            return host_id, str(host.get("name") or host_id), host
    for host_id, (_folder, label, _hint) in learn_catalog.skill_hosts().items():
        if key in (_key(host_id), _key(label)):
            return host_id, label, learn_catalog.active_skill_host(host_id) or {}
    return None


def _host_target(entered: str, host_id: str, name: str, host: dict[str, Any], kind: str) -> ToolTarget | None:
    guides = host.get("guides") if isinstance(host.get("guides"), dict) else {}
    guide = guides.get(kind)
    if not isinstance(guide, str) or not guide.strip():
        return None
    sources = host.get("guide_sources") or host.get("sources") or []
    learned = learn_catalog.is_learned(host)
    source = ", ".join(s for s in sources if isinstance(s, str)) or "the host list"
    return ToolTarget(entered, host_id, name, "tool", guide.strip()[:_GUIDE_LIMIT],
                      source + (" (named by the model, not checked)" if learned else ""),
                      str(host.get("learned_by") or "a model") if learned else None)


def _guide_file(key: str, kind: str) -> Path:
    return proofhouse_home() / "guides" / f"{key}.{kind}.json"


def _cached(entered: str, key: str, kind: str) -> ToolTarget | None:
    path = _guide_file(key, kind)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return ToolTarget(entered, data["id"], data["name"], data["sort"], data["guide"], data["guide_source"],
                          data.get("learned_by"))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _research_guide(entered: str, key: str, name: str, sort: str, kind: str, ask: Ask, learned_by: str) -> ToolTarget | None:
    reply = ask("research", _GUIDE_RESEARCH.format(kind=kind, name=name, sort="a tool" if sort == "tool" else "a model"))
    try:
        data = learn.extract_answer(reply, thing=f"how {name} wants a {kind}")
    except learn.LearnError:
        return None
    guide = data.get("guide") if isinstance(data, dict) else None
    if not isinstance(guide, str) or not guide.strip():
        return None
    meta = learn.provenance(data, learned_by=learned_by)
    sources = ", ".join(meta["sources"]) or "no sources named"
    found = ToolTarget(entered, key, str(data.get("name") or name).strip()[:100] or name, sort,
                       guide.strip()[:_GUIDE_LIMIT], f"{sources} (named by the model, not checked)", learned_by)
    path = _guide_file(key, kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": "proofhouse.guide/v1", "kind": kind, "learned_at": meta["learned_at"],
                                **found.to_dict()}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return found


def _general(entered: str, key: str, name: str, sort: str) -> ToolTarget:
    other = find_model(FALLBACK_ID, load_registry())
    return ToolTarget(entered, key, name, sort, other.notes if other else "",
                      "Proofhouse's general notes (nothing specific was found)", None)


def find_target(entered: str, kind: str, ask: Ask, *, learned_by: str) -> ToolTarget:
    """Known tools first, then known models, then what was learned before; anything else is researched now."""
    entered = entered.strip()
    key = _key(entered)
    if not key:
        raise InterviewError("say which AI tool or model this is for")
    host = _known_host(key)
    if host is not None:
        found = _host_target(entered, *host, kind)
        if found is not None:
            return found
        return _cached(entered, host[0], kind) or _research_guide(entered, host[0], host[1], "tool", kind, ask, learned_by) \
            or _general(entered, host[0], host[1], "tool")
    entry = find_model(entered, load_registry())
    if entry is not None and entry.id != FALLBACK_ID:
        notes = resolve_model_notes(entered)
        return ToolTarget(entered, entry.id, notes.display_name, "model", prompt_notes(notes),
                          ", ".join(notes.sources) or "Proofhouse's model notes", None)
    cached = _cached(entered, key, kind)
    if cached is not None:
        return cached
    try:
        what = learn.extract_answer(ask("research", _WHAT_IS.format(kind=kind, entered=entered)), thing=entered) or {}
    except learn.LearnError:
        what = {}
    sort = what.get("sort") if what.get("sort") in ("tool", "model") else ("tool" if kind in ("skill", "agent", "rule") else "model")
    name = str(what.get("name") or entered).strip()[:100] or entered
    if sort == "tool":
        plain = learn_catalog.plain_host_id(str(what.get("id") or "")) or learn_catalog.plain_host_id(key)
        if plain is not None:
            try:
                learn_catalog.ensure_host(plain, None, ask=lambda prompt: ask("research", prompt), learned_by=learned_by)
            except learn.LearnError:
                pass
            learned = hosts.all_hosts().get(plain)
            if learned is not None:
                found = _host_target(entered, plain, str(learned.get("name") or name), learned, kind)
                if found is not None:
                    return found
    return _research_guide(entered, key, name, sort, kind, ask, learned_by) or _general(entered, key, name, sort)


def _notes_for(target: ToolTarget) -> ResolvedNotes:
    return ResolvedNotes(
        entered_name=target.entered, canonical_id=target.id, display_name=target.name, provider=None, tier="target",
        source="target", verified_at=None, stale=False, age_days=None, stale_after_days=0, sources=(),
        provenance=target.guide_source, notes=target.guide,
    )


# --- the interview -----------------------------------------------------------------------------------

def _questions(iv: Interview, ask: Ask, preset: str) -> tuple[list[Question], str]:
    assert iv.target is not None
    packet = packets.clarify_packet(f"Make a {iv.kind} for {iv.target.name}. {iv.request}", _notes_for(iv.target), preset, False)
    system = packet.system + _KIND_NOTE.format(kind=iv.kind, name=iv.target.name)
    for user in (packet.user, packet.user + "\n\nReply with the JSON array only, nothing else."):
        try:
            return parse_questions(ask("questions", system, user)), "model"
        except ValueError:
            continue
    return list(_FALLBACK), "fallback"


def _say_back(iv: Interview, ask: Ask) -> str:
    assert iv.target is not None
    reply = (ask("say back", _SAY_BACK.format(kind=iv.kind, name=iv.target.name, brief=iv.brief())) or "").strip()
    return reply or "\n".join(f"- {q}: {a}" for q, a in iv.entries) or f"- {iv.request}"


def run(iv: Interview, source: Interviewer, ask: Ask, *, preset: str, learned_by: str) -> Interview:
    """Ask which tool or model, ask the questions, say back what was understood until the owner confirms it.

    Saves nothing itself; raises ``Paused`` when ``source`` has no answer yet, with ``iv`` filled so far.
    """
    packets.preset(preset)  # an unknown preset is refused before any call
    if iv.target is None:
        entered = (source.target() or "").strip()
        if not entered:
            raise Paused("for")
        iv.target = find_target(entered, iv.kind, ask, learned_by=learned_by)
    if not iv.questions:
        iv.questions, iv.questions_from = _questions(iv, ask, preset)
    if not iv.answered:
        answers = source.answers(iv.questions)
        if answers is None:
            raise Paused("answers")
        iv.entries = [(q.text, answers[q.id]) for q in iv.questions
                      if applies(q, answers) and answers.get(q.id, "").strip() not in ("", NOT_ANSWERED)]
        iv.answered = True
    if iv.understood is None:
        iv.understood = _say_back(iv, ask)
    while not iv.confirmed:
        reply = source.confirm(iv.understood, iv.corrections)
        if reply is None:
            raise Paused("confirm")
        if reply is True:
            iv.confirmed = True
            break
        iv.corrections.append(str(reply).strip())
        iv.understood = _say_back(iv, ask)
        if len(iv.corrections) >= MAX_FIXES:  # the corrections themselves go into the brief and win
            iv.confirmed = True
    return iv


# --- where the answers come from ---------------------------------------------------------------------

def _answer_text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(v).strip() for v in value if str(v).strip())
    return str(value).strip() if value is not None else ""


class FileInterviewer:
    """Answers from a JSON file: {"for": "...", "answers": {"<id>": "..."}, "confirmed": true, "correction": "..."}."""

    def __init__(self, path: Path | None, for_target: str | None = None) -> None:
        self.data: dict[str, Any] = {}
        if path is not None:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise InterviewError(f"cannot read the answers file {path}: {exc}") from None
            if not isinstance(data, dict):
                raise InterviewError(f"{path} must hold one JSON object")
            self.data = data
        self.for_target = for_target

    def target(self) -> str | None:
        return self.for_target or (self.data["for"] if isinstance(self.data.get("for"), str) else None)

    def answers(self, questions: list[Question]) -> dict[str, str] | None:
        given = self.data.get("answers")
        if not isinstance(given, dict):
            return None
        by_key = {str(k).strip().lower(): _answer_text(v) for k, v in given.items()}
        found = {q.id: by_key.get(q.id.lower()) or by_key.get(q.text.strip().lower()) or "" for q in questions}
        return found if any(found.values()) else None

    def confirm(self, understood: str, corrections: list[str]) -> bool | str | None:
        correction = _answer_text(self.data.get("correction"))
        if correction and correction not in corrections:
            return correction
        return True if self.data.get("confirmed") is True else None


class TerminalInterviewer:
    """Asks in the terminal. Enter skips a question; at the say-back, Enter accepts and any other text corrects."""

    def __init__(self, read: Callable[[], str], write: Callable[[str], None], for_target: str | None = None) -> None:
        self.read, self.write, self.for_target = read, write, for_target

    def _line(self, prompt: str) -> str:
        self.write(prompt)
        try:
            return self.read().strip()
        except EOFError:
            return ""

    def target(self) -> str | None:
        if self.for_target:
            return self.for_target
        for _ in range(3):
            entered = self._line("Which AI tool or model is this for? (for example Claude Code, Cursor, Codex, "
                                 "or a model name): ")
            if entered:
                return entered
        raise InterviewError("say which AI tool or model this is for (--for)")

    def answers(self, questions: list[Question]) -> dict[str, str] | None:
        self.write("\nA few questions so it comes out right. Press Enter to skip one.\n")
        found: dict[str, str] = {}
        group = None
        for q in questions:
            if not applies(q, found):
                continue
            if q.group and q.group != group:
                group = q.group
                self.write(f"\n{group}\n")
            lines = [q.text] + [f"  {n}) {option}" for n, option in enumerate(q.options, 1)]
            hint = {"single_select": "number or your own words", "multi_select": "numbers with commas, or your own words"}
            raw = self._line("\n".join(lines) + (f"\n  ({hint[q.type]}) " if q.type in hint else "\n  ") + "> ")
            found[q.id] = _picked(raw, q) or NOT_ANSWERED
        return found

    def confirm(self, understood: str, corrections: list[str]) -> bool | str | None:
        reply = self._line(f"\nHere is what I understood:\n{understood}\n\n"
                           "Press Enter if that is right, or type what to change: ")
        return True if reply.lower() in _ACCEPT else reply


def _picked(raw: str, q: Question) -> str:
    """Option numbers become the options' words; anything else is the owner's own answer, kept as typed."""
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if q.options and parts and all(p.isdigit() and 1 <= int(p) <= len(q.options) for p in parts):
        return ", ".join(q.options[int(p) - 1] for p in (parts if q.type == "multi_select" else parts[:1]))
    return raw


# --- files in the make folder ------------------------------------------------------------------------

def save(folder: Path, iv: Interview, calls: list[dict[str, Any]], spent_usd: str) -> Path:
    path = folder / "interview.json"
    path.write_text(json.dumps({**iv.to_dict(), "calls": calls, "spent_usd_estimated": spent_usd,
                                "saved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
                               indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load(folder: Path) -> tuple[Interview, list[dict[str, Any]], str] | None:
    path = folder / "interview.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise InterviewError(f"{path} is not readable JSON: {exc}") from None
    return Interview.from_dict(data), list(data.get("calls") or []), str(data.get("spent_usd_estimated") or "0")


def questions_markdown(iv: Interview) -> str:
    lines = [f"# Questions before making: {iv.request}", ""]
    if iv.target is None:
        lines += ["Which AI tool or model is this for? Put it in answers.json as \"for\" (or pass --for).", ""]
        return "\n".join(lines)
    lines += [f"Made for: {iv.target.name}", ""]
    for n, q in enumerate(iv.questions, 1):
        lines.append(f"{n}. **{q.id}**: {q.text}")
        if q.options:
            lines.append(f"   options ({'pick any' if q.type == 'multi_select' else 'pick one'}, or your own words): "
                         + "; ".join(q.options))
        if q.depends_on:
            parent, values = q.depends_on
            lines.append(f"   only if {parent} is " + (" or ".join(values) if values else "answered"))
    lines += ["", "Answer in answers.json (\"answers\": question id to answer; leave one empty to skip it), "
              "then run the same command again with --answers pointing at that file."]
    return "\n".join(lines) + "\n"


def write_pause(folder: Path, iv: Interview, stage: str) -> list[Path]:
    """Leave what the owner needs to answer: the questions, an answers file to fill and, at the end, the say-back."""
    written = [folder / INTERVIEW_FILES[0]]
    written[0].write_text(questions_markdown(iv), encoding="utf-8")
    answers = folder / "answers.json"
    filled: dict[str, Any] = {}
    if answers.exists():  # keep what the owner wrote; add the questions asked since
        try:
            loaded = json.loads(answers.read_text(encoding="utf-8"))
            filled = loaded if isinstance(loaded, dict) else {}
        except ValueError:
            filled = {}
    given = filled.get("answers") if isinstance(filled.get("answers"), dict) else {}
    answers.write_text(json.dumps({
        "for": filled.get("for") or (iv.target.entered if iv.target else ""),
        "answers": {**{q.id: "" for q in iv.questions}, **given},
        "confirmed": filled.get("confirmed") is True,
        "correction": filled.get("correction") or "",
    }, indent=2) + "\n", encoding="utf-8")
    written.append(answers)
    if stage == "confirm" and iv.understood:
        understood = folder / INTERVIEW_FILES[1]
        understood.write_text(
            f"# What I understood\n\n{iv.understood}\n\nIf that is right, set \"confirmed\": true in answers.json. "
            "If not, write what to change in \"correction\". Then run the same command again.\n", encoding="utf-8")
        written.append(understood)
    return written
