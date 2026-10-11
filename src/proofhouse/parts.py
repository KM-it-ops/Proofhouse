"""The part registry: one explicit table of every part Proofhouse ships.

A part is one unit with exactly one job (its role). Every part answers three
calls: ``describe()`` returns its descriptor, ``check(request)`` says whether it
can do a job (nothing runs), and ``do(request)`` does the job and returns a
``PartResult``. The spine calls ``do`` only after ``check`` did not answer
``unsupported`` (``perform``); there is no fallback to another part.

The table below is the one place parts are looked up. The compiler's adapter
lookup, the ``install-skill`` host list and the check-kind tuple are thin
wrappers over it. There is no plug-in discovery: loading outside code is a
security decision nobody has made, so the table is a plain list in the package.

Roles stay apart. A request builder (the compiler's "adapter") turns a
validated prompt program into one provider's API request and never writes host
config; the host writer copies a skill into a host tool's skills folder and
never builds model requests. Parts never write case files: the spine records
their results.

Importing this module imports no compiler or optimize code; each part loads its
implementation the first time it is asked for, so those modules can derive
their old names from this table without an import cycle.
"""

from __future__ import annotations

import base64
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

from .compiler.canonical import canonical_sha256
from .compiler.immutability import freeze_json

PART_CONTRACT_VERSION = "proofhouse.part/v1"

ROLE_BUILDER = "builder"
ROLE_REQUEST_BUILDER = "request_builder"
ROLE_RUNNER = "runner"
ROLE_CHECKER = "checker"
ROLE_HOST_WRITER = "host_writer"
ROLES = (ROLE_BUILDER, ROLE_REQUEST_BUILDER, ROLE_RUNNER, ROLE_CHECKER, ROLE_HOST_WRITER)

CERTIFIED = "CERTIFIED"
IMPLEMENTED_NOT_CERTIFIED = "IMPLEMENTED_NOT_CERTIFIED"
PARTIAL = "PARTIAL"
CONTRACT_ONLY = "CONTRACT_ONLY"
DEFERRED = "DEFERRED"
EXPERIMENTAL = "EXPERIMENTAL"
STATUSES = (CERTIFIED, IMPLEMENTED_NOT_CERTIFIED, PARTIAL, CONTRACT_ONLY, DEFERRED, EXPERIMENTAL)

DETERMINISTIC = "deterministic"
SEEDED = "seeded"
NON_REPRODUCIBLE = "non_reproducible"
REPRODUCIBILITY = (DETERMINISTIC, SEEDED, NON_REPRODUCIBLE)

EVIDENCE_CLASSES = ("prompt_text_check", "recorded_output_check", "structural_check", "human_judgement", "model_judge")
# AUTHORITY_AND_PRECEDENCE: lower is stronger; a deterministic validator is 1, a model judge 7 (advisory only).
AUTHORITY_DETERMINISTIC_VALIDATOR = 1

NETWORK_NONE = "none"

SUPPORTED = "supported"
CONDITIONAL = "conditional"
UNSUPPORTED = "unsupported"

EXPERIMENTAL_ENV = "PROOFHOUSE_EXPERIMENTAL"

# Statuses on record before this registry existed. No part changes status here:
# a recorded part keeps exactly this status, and any other part starts no higher
# than IMPLEMENTED_NOT_CERTIFIED (promotion needs its own owner record).
RECORDED_STATUS: Mapping[str, str] = {
    "fake": CERTIFIED,
    "openai": CERTIFIED,
    "anthropic": CERTIFIED,
    "gemini": CERTIFIED,
}

TEXT_CHECKER_ID = "text-checker"
HOST_WRITER_ID = "install-skill"
PART_SUITE_VERSION = "0.1.0"

# The text checker's check kinds, in the order the CLI has always listed them.
TEXT_CHECK_KINDS = ("must_contain", "must_not_contain", "max_words", "regex", "manual")
TEXT_TARGETS = ("prompt", "output")
# The host writer's hosts: config folder under the home directory, display name, where to start using the skill.
SKILL_HOSTS: Mapping[str, tuple[str, str, str]] = {
    "cursor": (".cursor", "Cursor", "a new Cursor Agent chat"),
    "claude": (".claude", "Claude Code", "a new Claude Code session"),
}

_PROMPT_TEXT = "prompt.text@1"
_AGENT_SKILL = "agent.skill@1"


class PartError(Exception):
    """Base class for registry failures."""


class PartNotFoundError(PartError, LookupError):
    """No registered part has this id, or it is EXPERIMENTAL and the gate is off."""


class PartDescriptorError(PartError, ValueError):
    """A descriptor breaks a registry rule; the part is refused, never loaded."""


class PartRefusedError(PartError):
    """``do`` was asked for a job ``check`` answers ``unsupported``; nothing ran."""

    def __init__(self, part_id: str, answer: CheckAnswer) -> None:
        reasons = "; ".join(
            f"{item['need']}: {item.get('reason', item['resolution'])}"
            for item in answer.items
            if item["resolution"] == UNSUPPORTED
        )
        super().__init__(f"part {part_id!r} cannot do this job ({reasons}); nothing was run and no other part was tried")
        self.part_id = part_id
        self.answer = answer


@dataclass(frozen=True)
class PartDescriptor:
    """What a part declares about itself. Descriptor v1 leaves out ``cost_model``: no part here calls a model."""

    part_id: str
    part_version: str
    role: str
    kinds_in: tuple[str, ...]
    kinds_out: tuple[str, ...]
    capability_manifest: Mapping[str, Any]
    manifest_digest: str
    not_measured: tuple[str, ...]
    reproducibility: str
    network: str
    conformance_suite_version: str
    status: str
    evidence_classes: tuple[str, ...] = ()
    authority_rank: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "capability_manifest", freeze_json(dict(self.capability_manifest)))

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "part_id": self.part_id,
            "part_version": self.part_version,
            "role": self.role,
            "kinds_in": list(self.kinds_in),
            "kinds_out": list(self.kinds_out),
            "capability_manifest": self.capability_manifest,
            "manifest_digest": self.manifest_digest,
        }
        if self.role == ROLE_CHECKER:
            d["evidence_classes"] = list(self.evidence_classes)
            d["authority_rank"] = self.authority_rank
        d.update(
            {
                "not_measured": list(self.not_measured),
                "reproducibility": self.reproducibility,
                "network": self.network,
                "conformance_suite_version": self.conformance_suite_version,
                "status": self.status,
            }
        )
        return d


@dataclass(frozen=True)
class CheckAnswer:
    """``check``'s answer: the overall verdict plus one item per need (``need``, ``resolution``, ``reason``)."""

    answer: str
    items: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class PartArtifact:
    """One produced artifact: a payload or a file manifest, its digest, and which part made it."""

    kind: str
    digest: str
    provenance: Mapping[str, str]
    payload: bytes | str | None = None
    manifest: tuple[Mapping[str, str], ...] | None = None
    media_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"kind": self.kind, "digest": self.digest, "provenance": dict(self.provenance)}
        if self.media_type is not None:
            d["media_type"] = self.media_type
        if isinstance(self.payload, bytes):
            d["payload_base64"] = base64.b64encode(self.payload).decode("ascii")
        elif self.payload is not None:
            d["payload"] = self.payload
        if self.manifest is not None:
            d["manifest"] = [dict(entry) for entry in self.manifest]
        return d


@dataclass(frozen=True)
class PartResult:
    """What ``do`` returns. ``cost`` is ``None``: no part in this table runs anything or calls a model."""

    status: str
    not_measured: tuple[str, ...]
    artifacts: tuple[PartArtifact, ...] = ()
    diagnostics: tuple[Mapping[str, Any], ...] = ()
    evidence: tuple[Mapping[str, Any], ...] = ()
    cost: Mapping[str, Any] | None = None
    contract_version: str = PART_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "diagnostics": [dict(d) for d in self.diagnostics],
            "evidence": [dict(e) for e in self.evidence],
            "not_measured": list(self.not_measured),
            "cost": None if self.cost is None else dict(self.cost),
            "contract_version": self.contract_version,
        }


def _answer(items: list[dict[str, Any]]) -> CheckAnswer:
    resolutions = {item["resolution"] for item in items}
    if UNSUPPORTED in resolutions:
        verdict = UNSUPPORTED
    elif CONDITIONAL in resolutions:
        verdict = CONDITIONAL
    else:
        verdict = SUPPORTED
    return CheckAnswer(answer=verdict, items=tuple(items))


def _provenance(descriptor: PartDescriptor) -> dict[str, str]:
    return {
        "part_id": descriptor.part_id,
        "part_version": descriptor.part_version,
        "manifest_digest": descriptor.manifest_digest,
    }


# --- request builders (the compiler's adapters) ------------------------------------------

REQUEST_BUILDER_NOT_MEASURED = (
    "whether the provider accepts the request (it is built offline and never sent)",
    "anything about the model's answer",
)


def _diagnostic_factory() -> Any:
    from .compiler import paths
    from .compiler.diagnostics import DiagnosticFactory, DiagnosticRegistry

    return DiagnosticFactory(DiagnosticRegistry(paths.DIAGNOSTIC_REGISTRY_PATH), paths.DIAGNOSTIC_CONTRACT_SCHEMA_PATH)


class RequestBuilderPart:
    """Wraps one compiler adapter unchanged: the same class, the same lowering, the same bytes."""

    def __init__(self, part_id: str, module: str, class_name: str, status: str) -> None:
        self.part_id = part_id
        self._module = module
        self._class_name = class_name
        self._status = status
        self._descriptor: PartDescriptor | None = None

    def bind(self, diagnostics: Any, source_document: str = "<input>") -> Any:
        """The adapter itself, as ``get_adapter`` has always returned it."""
        cls = getattr(import_module(self._module), self._class_name)
        return cls(diagnostics, source_document)

    def describe(self) -> PartDescriptor:
        if self._descriptor is None:
            adapter = self.bind(_diagnostic_factory())
            info = adapter.describe()
            manifest = adapter.capability_manifest().semantic_payload()
            self._descriptor = PartDescriptor(
                part_id=info.adapter_id,
                part_version=info.adapter_version,
                role=ROLE_REQUEST_BUILDER,
                kinds_in=(f"ir@{info.supported_ir_range}",),
                kinds_out=tuple(info.artifact_kinds),
                capability_manifest=manifest,
                manifest_digest=canonical_sha256(manifest),
                not_measured=REQUEST_BUILDER_NOT_MEASURED,
                reproducibility=DETERMINISTIC,
                network=NETWORK_NONE,
                conformance_suite_version=info.conformance_suite_version,
                status=self._status,
            )
        return self._descriptor

    def _adapter(self, request: Mapping[str, Any]) -> Any:
        diagnostics = request.get("diagnostics") or _diagnostic_factory()
        return self.bind(diagnostics, request.get("source_document", "<input>"))

    def check(self, request: Mapping[str, Any]) -> CheckAnswer:
        """``request``: ``{"ir": <validated IR>}``. Optional needs never make the job unsupported."""
        decisions = self._adapter(request).check_capabilities(request["ir"])
        items = []
        for decision in decisions:
            resolution = decision.resolution
            if decision.requirement == "optional" and resolution == UNSUPPORTED:
                resolution = SUPPORTED  # the request is still built; the optional need is dropped as today
            items.append(
                {
                    "need": decision.capability,
                    "resolution": resolution,
                    "reason": f"{decision.requirement} capability is {decision.resolution}",
                }
            )
        return _answer(items)

    def do(self, request: Mapping[str, Any]) -> PartResult:
        """Lower exactly as the compiler does; an unsupported required capability is a coded failure, no artifact."""
        adapter = self._adapter(request)
        ir = request["ir"]
        resolution = request.get("resolution") or adapter.check_capabilities(ir)
        lowered = adapter.lower(ir, resolution)
        descriptor = self.describe()
        provenance = _provenance(descriptor)
        return PartResult(
            status=lowered.status,
            artifacts=tuple(
                PartArtifact(kind=a.name, digest=a.sha256, provenance=provenance, payload=a.data, media_type=a.media_type)
                for a in lowered.artifacts
            ),
            diagnostics=tuple(d.to_dict() for d in lowered.diagnostics),
            not_measured=descriptor.not_measured,
        )


# --- the text checker --------------------------------------------------------------------

TEXT_CHECKER_NOT_MEASURED = (
    "anything the declared criteria do not state",
    "meaning: checks match words, counts and patterns only",
    "how a model responds, unless recorded outputs are checked",
)


class TextCheckerPart:
    """The five check kinds over one text. Pure: it reads nothing from disk and writes nothing."""

    part_id = TEXT_CHECKER_ID

    def __init__(self, status: str) -> None:
        manifest = {"check_kinds": list(TEXT_CHECK_KINDS), "targets": list(TEXT_TARGETS)}
        self._descriptor = PartDescriptor(
            part_id=TEXT_CHECKER_ID,
            part_version="0.1.0",
            role=ROLE_CHECKER,
            kinds_in=(_PROMPT_TEXT,),
            kinds_out=(),
            capability_manifest=manifest,
            manifest_digest=canonical_sha256(manifest),
            not_measured=TEXT_CHECKER_NOT_MEASURED,
            reproducibility=DETERMINISTIC,
            network=NETWORK_NONE,
            conformance_suite_version=PART_SUITE_VERSION,
            status=status,
            evidence_classes=("prompt_text_check", "recorded_output_check", "human_judgement"),
            authority_rank=AUTHORITY_DETERMINISTIC_VALIDATOR,
        )

    def describe(self) -> PartDescriptor:
        return self._descriptor

    def check(self, request: Mapping[str, Any]) -> CheckAnswer:
        """``request``: ``{"kind", "target", "criteria"}``; every criterion kind must be one of the five."""
        kind = request.get("kind", _PROMPT_TEXT)
        target = request.get("target", "prompt")
        items: list[dict[str, Any]] = [
            {
                "need": f"kind {kind}",
                "resolution": SUPPORTED if kind in self._descriptor.kinds_in else UNSUPPORTED,
                "reason": f"accepts {', '.join(self._descriptor.kinds_in)}",
            },
            {
                "need": f"target {target}",
                "resolution": SUPPORTED if target in TEXT_TARGETS else UNSUPPORTED,
                "reason": f"targets are {', '.join(TEXT_TARGETS)}",
            },
        ]
        for criterion in request.get("criteria", ()):
            check_kind = criterion.get("kind")
            criterion_target = criterion.get("target", "prompt")
            if check_kind not in TEXT_CHECK_KINDS:
                resolution, reason = UNSUPPORTED, f"check kinds are {', '.join(TEXT_CHECK_KINDS)}"
            elif criterion_target != target:
                resolution, reason = UNSUPPORTED, f"it checks {criterion_target} text, but this text is {target}"
            else:
                resolution, reason = SUPPORTED, "check kind and target match"
            items.append(
                {"need": f"criterion {criterion.get('id')} ({check_kind})", "resolution": resolution, "reason": reason}
            )
        return _answer(items)

    def do(self, request: Mapping[str, Any]) -> PartResult:
        """``request`` adds ``text`` and ``verdicts`` (criterion id -> pass/fail); returns one evidence row per criterion."""
        answer = self.check(request)
        if answer.answer == UNSUPPORTED:
            raise PartRefusedError(self.part_id, answer)
        from .optimize.checks import evaluate

        target = request.get("target", "prompt")
        verdicts = request.get("verdicts") or {}
        evidence = []
        for criterion in request.get("criteria", ()):
            if criterion["kind"] == "manual":
                evidence_class = "human_judgement"
            elif target == "output":
                evidence_class = "recorded_output_check"
            else:
                evidence_class = "prompt_text_check"
            evidence.append(
                {
                    "criterion": criterion["id"],
                    "check_kind": criterion["kind"],
                    "result": evaluate(criterion, request["text"], verdict=verdicts.get(criterion["id"])),
                    "evidence_class": evidence_class,
                    "authority_rank": self._descriptor.authority_rank,
                }
            )
        return PartResult(status="success", evidence=tuple(evidence), not_measured=self._descriptor.not_measured)


# --- the install-skill host writer -------------------------------------------------------

HOST_WRITER_NOT_MEASURED = (
    "behaviour in hosts not tested",
    "whether the host tool loads or uses the installed skill",
)


class SkillHostWriterPart:
    """Copies the bundled skill into a host's skills folder; read back and fingerprinted after the write."""

    part_id = HOST_WRITER_ID

    def __init__(self, status: str) -> None:
        manifest = {
            "hosts": {
                name: {"folder": folder, "label": label, "start_hint": hint}
                for name, (folder, label, hint) in sorted(SKILL_HOSTS.items())
            },
        }
        self._descriptor = PartDescriptor(
            part_id=HOST_WRITER_ID,
            part_version="0.1.0",
            role=ROLE_HOST_WRITER,
            kinds_in=(_AGENT_SKILL,),
            kinds_out=(_AGENT_SKILL,),
            capability_manifest=manifest,
            manifest_digest=canonical_sha256(manifest),
            not_measured=HOST_WRITER_NOT_MEASURED,
            reproducibility=DETERMINISTIC,
            network=NETWORK_NONE,
            conformance_suite_version=PART_SUITE_VERSION,
            status=status,
        )

    def describe(self) -> PartDescriptor:
        return self._descriptor

    def check(self, request: Mapping[str, Any]) -> CheckAnswer:
        """``request``: ``{"kind", "host"}`` or ``{"kind", "dest"}``; an unknown host is unsupported, never guessed."""
        kind = request.get("kind", _AGENT_SKILL)
        host = request.get("host")
        items: list[dict[str, Any]] = [
            {
                "need": f"kind {kind}",
                "resolution": SUPPORTED if kind in self._descriptor.kinds_in else UNSUPPORTED,
                "reason": f"accepts {', '.join(self._descriptor.kinds_in)}",
            }
        ]
        if host is not None:
            items.append(
                {
                    "need": f"host {host}",
                    "resolution": SUPPORTED if host in SKILL_HOSTS else UNSUPPORTED,
                    "reason": f"hosts are {', '.join(sorted(SKILL_HOSTS))}",
                }
            )
        elif request.get("dest") is None:
            items.append({"need": "destination", "resolution": UNSUPPORTED, "reason": "name a host or a skills folder"})
        return _answer(items)

    def do(self, request: Mapping[str, Any]) -> PartResult:
        """``request`` adds optional ``bundle`` and ``force``; errors are ``InstallSkillError`` as before."""
        answer = self.check(request)
        if answer.answer == UNSUPPORTED:
            raise PartRefusedError(self.part_id, answer)
        from .optimize import install_skill
        from .optimize.kinds import folder_manifest, manifest_digest

        installed = install_skill.install(
            dest=request.get("dest"),
            bundle=request.get("bundle"),
            force=bool(request.get("force", False)),
            host=request.get("host"),
        )
        manifest = folder_manifest(installed.dest)
        return PartResult(
            status="success",
            artifacts=(
                PartArtifact(
                    kind=_AGENT_SKILL,
                    digest=manifest_digest(manifest),
                    provenance=_provenance(self._descriptor),
                    manifest=tuple(manifest),
                ),
            ),
            not_measured=self._descriptor.not_measured,
        )


# --- the table ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Entry:
    part_id: str
    role: str
    status: str
    load: Callable[[str], Any] = field(repr=False)


def _request_builder(part_id: str, module: str, class_name: str) -> Callable[[str], Any]:
    return lambda status: RequestBuilderPart(part_id, module, class_name, status)


_TABLE: tuple[_Entry, ...] = (
    _Entry("fake", ROLE_REQUEST_BUILDER, CERTIFIED, _request_builder("fake", "proofhouse.compiler.adapters.fake", "FakeAdapter")),
    _Entry("openai", ROLE_REQUEST_BUILDER, CERTIFIED, _request_builder("openai", "proofhouse.compiler.adapters.openai", "OpenAIAdapter")),
    _Entry(
        "anthropic",
        ROLE_REQUEST_BUILDER,
        CERTIFIED,
        _request_builder("anthropic", "proofhouse.compiler.adapters.anthropic", "AnthropicAdapter"),
    ),
    _Entry("gemini", ROLE_REQUEST_BUILDER, CERTIFIED, _request_builder("gemini", "proofhouse.compiler.adapters.gemini", "GeminiAdapter")),
    _Entry(TEXT_CHECKER_ID, ROLE_CHECKER, IMPLEMENTED_NOT_CERTIFIED, TextCheckerPart),
    _Entry(HOST_WRITER_ID, ROLE_HOST_WRITER, IMPLEMENTED_NOT_CERTIFIED, SkillHostWriterPart),
)

_loaded: dict[str, Any] = {}


def experimental_enabled() -> bool:
    return os.environ.get(EXPERIMENTAL_ENV) == "1"


def _visible(entry: _Entry) -> bool:
    return entry.status != EXPERIMENTAL or experimental_enabled()


def part_ids(role: str | None = None) -> tuple[str, ...]:
    """Ids in table order, without loading any part; EXPERIMENTAL parts only behind the gate."""
    return tuple(e.part_id for e in _TABLE if (role is None or e.role == role) and _visible(e))


def validate_descriptor(descriptor: PartDescriptor) -> None:
    """Apply every registry rule; raise ``PartDescriptorError`` naming the first one broken."""
    d = descriptor

    def refuse(reason: str) -> PartDescriptorError:
        return PartDescriptorError(f"part {d.part_id!r} refused: {reason}")

    if d.role not in ROLES:
        raise refuse(f"role {d.role!r} is not one of {', '.join(ROLES)}")
    if d.status not in STATUSES:
        raise refuse(f"status {d.status!r} is not one of {', '.join(STATUSES)}")
    if d.reproducibility not in REPRODUCIBILITY:
        raise refuse(f"reproducibility {d.reproducibility!r} is not one of {', '.join(REPRODUCIBILITY)}")
    if d.reproducibility == NON_REPRODUCIBLE and d.status == CERTIFIED:
        raise refuse("a non_reproducible part can never be CERTIFIED")
    recorded = RECORDED_STATUS.get(d.part_id)
    if recorded is not None and d.status != recorded:
        raise refuse(f"status {d.status} differs from its recorded status {recorded}; no part changes status")
    if recorded is None and d.status == CERTIFIED:
        raise refuse("a new part starts no higher than IMPLEMENTED_NOT_CERTIFIED; CERTIFIED needs its own owner record")
    if d.network != NETWORK_NONE:
        raise refuse(f"network {d.network!r} is not allowed; descriptor v1 declares network 'none' only")
    if d.manifest_digest != canonical_sha256(d.capability_manifest):
        raise refuse("manifest_digest does not match the capability manifest")
    if not isinstance(d.not_measured, tuple):
        raise refuse("not_measured must be present (a tuple, possibly empty)")
    if not d.part_version or not d.conformance_suite_version:
        raise refuse("part_version and conformance_suite_version are required")
    if d.role == ROLE_CHECKER:
        if not d.evidence_classes or any(c not in EVIDENCE_CLASSES for c in d.evidence_classes):
            raise refuse(f"a checker declares evidence classes from {', '.join(EVIDENCE_CLASSES)}")
        if not isinstance(d.authority_rank, int) or isinstance(d.authority_rank, bool) or d.authority_rank < 1:
            raise refuse("a checker declares an authority_rank (1 is strongest)")
    elif d.evidence_classes or d.authority_rank is not None:
        raise refuse("only a checker declares evidence classes or an authority rank")
    if d.role != ROLE_REQUEST_BUILDER:
        # Request builders speak compiler labels (IR range, request payload names); every other part
        # takes and makes case artifacts, so its kinds must be registered ones.
        from .optimize.kinds import KIND_IDS

        for kind in d.kinds_in + d.kinds_out:
            if kind not in KIND_IDS:
                raise refuse(f"kind {kind!r} is not a registered artifact kind")


def _entry(part_id: str) -> _Entry:
    for entry in _TABLE:
        if entry.part_id == part_id:
            return entry
    raise PartNotFoundError(f"unknown part id {part_id!r}")


def get_part(part_id: str) -> Any:
    """The part with this id, loaded and validated once; EXPERIMENTAL parts need ``PROOFHOUSE_EXPERIMENTAL=1``."""
    entry = _entry(part_id)
    if not _visible(entry):
        raise PartNotFoundError(f"part {part_id!r} is EXPERIMENTAL; set {EXPERIMENTAL_ENV}=1 to use it")
    part = _loaded.get(part_id)
    if part is None:
        part = entry.load(entry.status)
        descriptor = part.describe()
        if (descriptor.part_id, descriptor.role, descriptor.status) != (entry.part_id, entry.role, entry.status):
            raise PartDescriptorError(f"part {part_id!r} refused: its descriptor disagrees with the registry table")
        validate_descriptor(descriptor)
        _loaded[part_id] = part
    return part


def list_parts() -> tuple[Any, ...]:
    """Every visible part, in table order, each loaded and validated."""
    ids = [e.part_id for e in _TABLE]
    if len(ids) != len(set(ids)):
        raise PartDescriptorError("two registry entries share a part id")
    return tuple(get_part(part_id) for part_id in part_ids())


def perform(part: Any, request: Mapping[str, Any]) -> PartResult:
    """The spine's only way to run a part: ``check`` first, and ``do`` never after ``unsupported``."""
    answer = part.check(request)
    if answer.answer == UNSUPPORTED:
        raise PartRefusedError(part.describe().part_id, answer)
    return part.do(request)
