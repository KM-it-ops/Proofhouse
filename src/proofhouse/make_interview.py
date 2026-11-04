"""Before make writes a prompt, skill, agent, rule, site, app or any other kind, it interviews you.

1. Where is it for? For text kinds, an AI tool or model: known tools come from the host list (``hosts.json``),
   known models from the model registry. For a site, where it will be published (the deploy list); for an app,
   the platforms it runs on (the platform list). Anything else is researched by your model and learned, never
   refused.
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

from . import app_platforms, deploy, hosts, learn, learn_catalog, media
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
_SAY_BACK_PLACE = (
    "You are about to write a {kind}{where}. Before writing anything, say back in plain everyday words what you "
    "understood, so the owner can correct it. Use short bullet points under these headings: What it is; Who or what "
    "uses it; What it must do; What it must not do; Where it will live; What I am assuming. Under 150 words. No "
    "jargon: if a technical term is needed, put it in brackets after the plain words. Output only the bullet points."
    "\n\n{brief}"
)
_PLACE_NOTE = (
    "\n\nHere the thing being made is a {kind} {where}: ask what you need to make an excellent {kind} for that, "
    "using what is known about it below.\n\nWHAT IS KNOWN:\n{guide}"
)
_SAY_BACK_MEDIA = (
    "You are about to make a {kind} with {name}. {name} is only the tool that makes it: the {kind} is about what "
    "the request says, never about {name}, so leave {name} out of what you say back. Before making anything, say "
    "back in plain everyday words what you understood, so the owner can correct it. Use short bullet points under these headings: What it is; What it is "
    "for; Who will see or hear it; How long or how big; The look, voice or music; Where it will be shown; What I am "
    "assuming. Under 150 words. No jargon: if a technical term is needed, put it in brackets after the plain words. "
    "Output only the bullet points.\n\n{brief}"
)
_MEDIA_NOTE = (
    "\n\nHere the thing being made is a {kind} (a picture, a voice, music or a film, not text). {name} is only the "
    "tool that makes it: the {kind} is about what the request says, never about {name}, so ask nothing about {name} "
    "itself and never name it in a question. Ask "
    "what you need to make it well: what it is for, who will see or hear it, how long or how big it should be, the "
    "look it should have, the voice (who speaks, how it sounds), the music (mood, pace), and where it will be shown "
    "(so the right shapes are made, such as wide, tall or square). Ask nothing about writing code or text files."
)
_SHARED_NOTE = "\n\nThe owner already answered these for the whole launch. Do not ask them again:\n{shared}"
_GIVEN_NOTE = "\n\nThe owner already set these on the command. They are decided: do not ask about them:\n{given}"
_PLACE_SORTS = ("deploy", "platform", "launch")
_MEDIA_PREFIX = re.compile(r"(visuals|voice|music)\s*:\s*(.*)", flags=re.I | re.S)


class InterviewError(Exception):
    """The interview cannot go on (no tool or model named, a bad answers file)."""


class Refused(InterviewError):
    """The answer names something that must be approved first; nothing is asked or made until it is."""


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
    sort: str  # "tool" (people work in it), "model" (called directly), "deploy", "platform" or "launch"
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
    shared: str = ""  # what the owner told us for the whole launch this part belongs to
    given: str = ""  # what the owner already set on the command (a length, the shapes), so it is never asked

    def brief(self) -> str:
        """What make writes, judges and revises against: the request plus everything the interview found."""
        parts = [f"REQUEST:\n{self.request}"]
        if self.target is not None and self.target.sort == "media":  # what the tools make, never their names
            parts.append("MADE WITH: the tools the owner chose (only the tools that make it; the piece is not about "
                         "them, and never shows or names them)")
        elif self.target is not None:
            parts.append(f"MADE FOR: {_made_for(self.target)}")
        if self.shared:
            parts.append(f"WHAT THE OWNER TOLD US FOR THE WHOLE LAUNCH:\n{self.shared}")
        if self.given:
            parts.append(f"WHAT THE OWNER ALREADY SET:\n{self.given}")
        if self.entries:
            parts.append("WHAT THE OWNER TOLD US:\n" + packets.format_answered_entries(self.entries))
        if self.confirmed and self.understood:
            parts.append(f"UNDERSTANDING THE OWNER CONFIRMED:\n{self.understood}")
        if self.corrections:
            parts.append("CORRECTIONS FROM THE OWNER (these win over everything above):\n"
                         + "\n".join(f"- {c}" for c in self.corrections))
        if self.target is not None and self.target.guide:
            if self.target.sort in ("tool", "model"):
                heading = f"HOW {self.target.name.upper()} WANTS A {self.kind.upper()} WRITTEN"
            elif self.target.sort == "media":
                heading = "THE TOOLS THAT WILL MAKE IT (never the subject of the piece)"
            else:
                heading = f"WHAT IS KNOWN ABOUT {self.target.name.upper()}"
            guide = _nameless(self.target.guide) if self.target.sort == "media" else self.target.guide
            parts.append(f"{heading} (from {self.target.guide_source}):\n{guide}")
        return "\n\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA, "request": self.request, "kind": self.kind,
            "target": self.target.to_dict() if self.target else None,
            "questions": [q.to_dict() for q in self.questions], "questions_from": self.questions_from,
            "entries": [list(e) for e in self.entries], "answered": self.answered, "understood": self.understood,
            "corrections": list(self.corrections), "confirmed": self.confirmed, "shared": self.shared,
            "given": self.given,
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
            str(data.get("shared") or ""), str(data.get("given") or ""),
        )


def _nameless(guide: str) -> str:
    """A media guide ("visuals: Name (id/model) makes image") as just what each part makes ("visuals: makes image"),
    so a writer never draws a service because of its name."""
    lines = []
    for line in guide.splitlines():
        role, _, rest = line.partition(": ")
        _, found, makes = rest.rpartition(" makes ")
        if found:
            lines.append(f"{role}: makes {makes}")
    return "\n".join(lines)


def _made_for(target: ToolTarget) -> str:
    if target.sort == "deploy":
        return f"{target.name} (where the site will be published)"
    if target.sort == "platform":
        return f"{target.name} (the platforms the app runs on)"
    if target.sort == "launch":
        return target.name
    if target.sort == "media":
        return f"{target.name} (only the tools that make it; the piece is not about them)"
    return f"{target.name} ({'an AI tool people work in' if target.sort == 'tool' else 'an AI model called directly'})"


def _where(target: ToolTarget) -> str:
    """The target in a phrase that follows the kind: 'to be published on Netlify'."""
    if target.sort == "deploy":
        return f"to be published on {target.name}"
    if target.sort == "platform":
        return f"that runs on {target.name}"
    return ""


def target_question(kind: str) -> str:
    """The question that asks where the thing is for, with examples read from the lists, not written in code."""
    if kind == "site":
        return f"Where will the site be published? (for example: {', '.join(deploy.all_targets())})"
    if kind == "app":
        return f"Which platforms should the app run on? (for example: {', '.join(app_platforms.all_platforms())})"
    from . import make_media

    if kind in make_media.media_kinds():
        needs = make_media.service_kinds(kind)
        listed = [(pid, p) for pid, p in media.all_media_providers().items() if needs & set(p.kinds)]
        found = [pid for pid, p in sorted(listed, key=lambda e: e[1].origin == "shipped")]  # your own first
        return (f"Which service makes it? Name it as service or service/model, such as {', '.join(found[:8])}"
                + (" (for a video you can name several, such as 'visuals: a, voice: b, music: c')" if kind == "video" else ""))
    return "Which AI tool or model is this for? (for example Claude Code, Cursor, Codex, or a model name)"


def shared_text(iv: Interview) -> str:
    """What the owner told us, and the understanding they confirmed, to hand on to the parts of a launch."""
    parts = []
    if iv.entries:
        parts.append(packets.format_answered_entries(iv.entries))
    if iv.corrections:
        parts.append("Corrections (these win):\n" + "\n".join(f"- {c}" for c in iv.corrections))
    if iv.confirmed and iv.understood:
        parts.append(f"Understanding the owner confirmed:\n{iv.understood}")
    return "\n\n".join(parts)


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
    return re.sub(r"[^a-z0-9_]+", "_", raw.lower()).strip("_")[:40].strip("_") or f"q{n}"


_PLACEHOLDER_IDS = {"short_snake_case", "snake_case", "id", "question_id"}  # copied from the schema's example


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
    taken: set[str] = set()  # every id given out so far
    asked: dict[str, str] = {}  # a question's words, said plainly -> our id for it
    for group, q in flat:
        text_ = str(q.get("text") or q.get("question") or "").strip()
        if not text_ or len(found) >= MAX_QUESTIONS:
            continue
        raw = str(q.get("id") or text_)
        same = _plain_question(text_)
        if same in asked:  # the same question asked twice (a model often repeats one with a note after it)
            ids.setdefault(raw, asked[same])
            continue
        reused = raw in ids or _clean_id(raw, 0) in _PLACEHOLDER_IDS
        qid = base = _clean_id(text_ if reused else raw, len(found) + 1)  # a reused id: name it by its own words
        n = 2
        while qid in taken:
            qid, n = f"{base}_{n}", n + 1
        ids.setdefault(raw, qid)
        taken.add(qid)
        asked[same] = qid
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


_GIVEN_TOPICS = {  # a line of what the command set -> the words of a question that asks it again
    "- length:": re.compile(r"\b(length|duration|runtime)\b|\bhow long\b", re.I),
    "- shapes to deliver:": re.compile(
        r"\b(format|formats|aspect|orientation|ratio|vertical|horizontal|landscape|portrait|widescreen)\b"
        r"|\b\d+ ?[:x] ?\d+\b"  # 16:9, 9x16
        r"|\b(wide|tall|square)\b.*\b(wide|tall|square)\b", re.I),  # "wide, tall or square": two of them
}


def not_given(questions: list[Question], given: str) -> list[Question]:
    """The questions left once those about what the command already set are dropped, whatever the model asked.

    A follow-up of a dropped question is asked plainly, since its parent is decided."""
    topics = [words for line, words in _GIVEN_TOPICS.items() if line in given]
    dropped = {q.id for q in questions
               if any(words.search(f"{q.id.replace('_', ' ')} {q.text}") for words in topics)}
    return [Question(q.id, q.text, q.type, q.options, None, q.group)
            if q.depends_on and q.depends_on[0] in dropped else q
            for q in questions if q.id not in dropped]


def _plain_question(text: str) -> str:
    """A question's words without case, punctuation or a note in brackets at the end, to spot one asked twice."""
    text = re.sub(r"\s*\([^()]*\)\s*$", "", text.strip())
    return " ".join(re.sub(r"[^\w\s]", " ", text.lower()).split())


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


def _ask_for(kind: str) -> str:
    from . import make_media

    if kind in make_media.media_kinds():
        return "which service makes it"
    return {"site": "where the site will be published", "app": "which platforms the app should run on"}.get(
        kind, "which AI tool or model this is for")


def _by_key(entries: dict[str, dict[str, Any]], key: str) -> str | None:
    for entry_id, entry in entries.items():
        if key in (_key(entry_id), _key(str(entry.get("name") or ""))):
            return entry_id
    return None


def _deploy_target(entered: str, key: str, ask: Ask, learned_by: str) -> ToolTarget:
    """Where a site will be published: the deploy list first, then learned. Make never deploys, so it only shapes the guide."""
    found = _by_key(deploy.all_targets(), key)
    if found is None:
        plain = learn_catalog.plain_service_id(key)
        if plain is None:
            raise InterviewError(f"{entered!r} is not a plain name for a place to publish; try its short name")
        try:
            learn_catalog.ensure_deploy(plain, None, lambda prompt: ask("research", prompt))
        except learn.LearnError as exc:
            raise InterviewError(f"could not learn how to publish on {entered}: {exc}") from None
        found = _by_key(deploy.all_targets(), plain)
        if found is None:
            raise InterviewError(f"could not learn how to publish on {entered}")
    entry = deploy.all_targets()[found]
    learned = learn_catalog.is_learned(entry)
    guide = (f"{entry.get('name') or found} is published with the tool {entry.get('tool')}. "
             f"Install: {entry.get('install')}. Command: {' '.join(str(w) for w in entry.get('command') or [])}")
    return ToolTarget(entered, found, str(entry.get("name") or found), "deploy", guide[:_GUIDE_LIMIT],
                      "learned (named by a model, not checked)" if learned else "the deploy list",
                      learned_by if learned else None)


def _unknown_platform(piece: str) -> str:
    return f"unknown platform: {piece.strip()}; known: {', '.join(sorted(app_platforms.all_platforms()))}"


def _platform_target(entered: str, ask: Ask, learned_by: str) -> ToolTarget:
    """The platforms an app runs on: each from the platform list, or learned (make waits for approval before using it)."""
    ids: list[str] = []
    for piece in re.split(r",|\+|\s+and\s+", entered, flags=re.I):
        key = _key(piece)
        if not key:
            continue
        found = _by_key(app_platforms.all_platforms(), key)
        if found is None:
            plain = learn_catalog.plain_platform_id(key)
            if plain is None:
                raise InterviewError(f"{piece.strip()!r} is not a plain platform name")
            try:
                learn_catalog.ensure_platform(plain, None, lambda prompt: ask("research", prompt))
            except learn.LearnError:
                raise InterviewError(_unknown_platform(piece)) from None
            found = _by_key(app_platforms.all_platforms(), plain)
            if found is None:
                raise InterviewError(_unknown_platform(piece))
        if found not in ids:
            ids.append(found)
    if not ids:
        raise InterviewError(f"say {_ask_for('app')}")
    catalog = app_platforms.all_platforms()
    names, guides, learned = [], [], False
    for platform_id in ids:
        entry = catalog[platform_id]
        pending = learn_catalog.unapproved("app_platforms", platform_id, entry)
        if pending:  # stop before the questions: a learned platform carries build commands and waits for approval
            raise Refused(learn_catalog.refusal_message(
                pending, thing=f"Platform {platform_id}", command=f"{learn_catalog.APPROVE_CMD} {platform_id}"))
        names.append(str(entry.get("name") or platform_id))
        learned = learned or learn_catalog.is_learned(entry)
        guides.append(f"{names[-1]}: shell {entry.get('shell')}. {entry.get('write')}")
    return ToolTarget(entered, "+".join(ids), ", ".join(names), "platform", "\n".join(guides)[:_GUIDE_LIMIT],
                      "learned (named by a model, not checked)" if learned else "the platform list",
                      learned_by if learned else None)


def _media_target(entered: str, kind: str, ask: Ask, learned_by: str) -> ToolTarget:
    """The services that make a media piece: each from the media list (or your own program), or learned and held for approval."""
    from . import make_media

    made = make_media.media_kinds()[kind]["media"]
    roles = make_media.ROLES[made]
    filled: dict[str, tuple[str, str]] = {}
    for piece in re.split(r",|\+|\s+and\s+", entered, flags=re.I):
        text = piece.strip()
        prefix = _MEDIA_PREFIX.fullmatch(text)
        role = None
        if prefix:
            role, text = prefix.group(1).lower(), prefix.group(2).strip()
        if role is not None and role not in roles:
            continue
        service, _, model = text.partition("/")
        key = _key(service)
        if not key:
            continue
        found = next((p for pid, p in media.all_media_providers().items() if key in (_key(pid), _key(p.name))), None)
        if found is None:
            plain = learn_catalog.plain_service_id(key)
            if plain is None:
                raise InterviewError(f"{service.strip()!r} is not a plain name for a media service")
            try:
                learn_catalog.ensure_media(plain, None, ask=lambda prompt: ask("research", prompt))
            except learn.LearnError as exc:
                raise InterviewError(f"could not learn the media service {service.strip()}: {exc}") from None
            found = media.find(plain)
            if found is None:
                raise InterviewError(f"could not learn the media service {service.strip()}")
        pending = learn_catalog.unapproved("media_providers", found.id, found)
        if pending:  # stop before the questions: a learned service waits for approval
            raise Refused(learn_catalog.refusal_message(
                pending, thing=f"Media service {found.id}", command=f"{learn_catalog.APPROVE_CMD} {found.id}"))
        fits = [r for r, makes in roles.items() if makes & set(found.kinds) and (role is None or r == role)]
        if not fits:
            raise InterviewError(f"{found.id} makes {', '.join(found.kinds)}, not {made if role is None else role}")
        free = [r for r in fits if r not in filled]
        if not free:
            continue  # that part is already taken by the first service named for it
        model = model.strip() or ("local" if found.run is not None else "")
        if not model:
            raise InterviewError(f"{found.id} is a web service: name its model, such as {found.id}/<model>")
        filled[free[0]] = (found.id, model)
    if not filled:
        raise InterviewError(f"say {_ask_for(kind)}")
    catalog = media.all_media_providers()
    guides = [f"{r}: {catalog[pid].name} ({pid}/{model}) makes {', '.join(catalog[pid].kinds)}"
              for r, (pid, model) in filled.items()]
    learned = any(catalog[pid].origin == "add-on learned" for pid, _ in filled.values())
    return ToolTarget(entered, "+".join(f"{r}={pid}/{model}" for r, (pid, model) in filled.items()),
                      ", ".join(catalog[pid].name for pid, _ in filled.values()), "media",
                      "\n".join(guides)[:_GUIDE_LIMIT],
                      "learned (named by a model, not checked)" if learned else "the media list",
                      learned_by if learned else None)


def find_target(entered: str, kind: str, ask: Ask, *, learned_by: str) -> ToolTarget:
    """Known tools first, then known models, then what was learned before; anything else is researched now."""
    from . import make_media

    entered = entered.strip()
    key = _key(entered)
    if not key:
        raise InterviewError(f"say {_ask_for(kind)}")
    if kind in make_media.media_kinds():
        return _media_target(entered, kind, ask, learned_by)
    if kind == "site":
        return _deploy_target(entered, key, ask, learned_by)
    if kind == "app":
        return _platform_target(entered, ask, learned_by)
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
    target = iv.target
    where = _where(target)
    if where:
        objective = f"Make a {iv.kind} {where}. {iv.request}"
    elif target.sort == "media":
        objective = f"Make a {iv.kind}. {iv.request}"  # the services make it; they are not who it is for
    else:
        objective = f"Make a {iv.kind} for {target.name}. {iv.request}"
    packet = packets.clarify_packet(objective, _notes_for(target), preset, False)
    if target.sort == "media":
        system = packet.system + _MEDIA_NOTE.format(kind=iv.kind, name=target.name)
    elif target.sort in _PLACE_SORTS:
        system = packet.system + _PLACE_NOTE.format(kind=iv.kind, where=where or f"({target.name})", guide=target.guide)
    else:
        system = packet.system + _KIND_NOTE.format(kind=iv.kind, name=target.name)
    if iv.shared:
        system += _SHARED_NOTE.format(shared=iv.shared)
    if iv.given:
        system += _GIVEN_NOTE.format(given=iv.given)
    for user in (packet.user, packet.user + "\n\nReply with the JSON array only, nothing else."):
        try:
            kept = not_given(parse_questions(ask("questions", system, user)), iv.given)
            return (kept, "model") if kept else (list(_FALLBACK), "fallback")
        except ValueError:
            continue
    return list(_FALLBACK), "fallback"


def _say_back(iv: Interview, ask: Ask) -> str:
    assert iv.target is not None
    if iv.target.sort == "media":
        prompt = _SAY_BACK_MEDIA.format(kind=iv.kind, name=iv.target.name, brief=iv.brief())
    elif iv.target.sort in _PLACE_SORTS:
        prompt = _SAY_BACK_PLACE.format(kind=iv.kind, where=(" " + _where(iv.target)).rstrip(), brief=iv.brief())
    else:
        prompt = _SAY_BACK.format(kind=iv.kind, name=iv.target.name, brief=iv.brief())
    reply = (ask("say back", prompt) or "").strip()
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

def answered_by(interviewer: Any, *, shared: bool = False) -> str:
    """Where the interview was answered, as the record names it: the answers file, the terminal, a launch or the
    caller, and the flag that named the tool when a flag did (``--for``, ``--platform`` or the service flags)."""
    if shared:
        return "launch"
    if interviewer is None:
        return "none"
    if not isinstance(interviewer, (FileInterviewer, TerminalInterviewer)):
        return "caller"
    flag = interviewer.target_from if interviewer.for_target else None
    if isinstance(interviewer, FileInterviewer) and interviewer.path is None:
        return flag or "nothing yet"
    where = "terminal" if isinstance(interviewer, TerminalInterviewer) else "answers file"
    return f"{where}; the tool from {flag}" if flag else where


def _answer_text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(v).strip() for v in value if str(v).strip())
    return str(value).strip() if value is not None else ""


class FileInterviewer:
    """Answers from a JSON file: {"for": "...", "answers": {"<id>": "..."}, "confirmed": true, "correction": "..."}."""

    def __init__(self, path: Path | None, for_target: str | None = None, target_from: str = "--for") -> None:
        self.data: dict[str, Any] = {}
        self.path, self.target_from = path, target_from
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

    def __init__(self, read: Callable[[], str], write: Callable[[str], None], for_target: str | None = None,
                 kind: str = "", target_from: str = "--for") -> None:
        self.read, self.write, self.for_target, self.kind = read, write, for_target, kind
        self.target_from = target_from

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
            entered = self._line(target_question(self.kind) + ": ")
            if entered:
                return entered
        raise InterviewError(f"say {_ask_for(self.kind)} (--for)")

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
        lines += [f"{target_question(iv.kind)} Put it in answers.json as \"for\" (or pass --for).", ""]
        return "\n".join(lines)
    lines += [f"{'Made with' if iv.target.sort == 'media' else 'Made for'}: {_made_for(iv.target)}", ""]
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
