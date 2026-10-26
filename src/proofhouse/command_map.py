"""Every command path of the one ``proofhouse`` tree, mapped to the spine or to a registered part.

The architecture test (``tests/test_t040_06_front_door.py``) fails the build
when a command exists that is not listed here, when an entry names a part the
registry does not hold, or when an entry has no one-line reason. Adding a
command therefore needs a deliberate edit here (MISSION-040 SPEC §2.1).

``SPINE`` entries are the spine's own commands, including utility, legacy
(``eval ...``) and quarantined commands, each with its reason. ``PART``
entries name the part id the command drives.
"""

from __future__ import annotations

SPINE = "spine"
PART = "part"

_CASE = {
    "new": "opens a case for one artifact kind (--kind prompt or skill)",
    "compile": "renders the compile packet from the clarify answers",
    "record": "records a version the host's model wrote (prompt text or a skill folder)",
    "revise": "renders the self-heal packet for the next version",
    "status": "reads the case: stage, versions, criteria, runs",
    "criteria add": "declares a criterion the case pass rule judges",
    "criteria list": "lists the declared criteria",
    "verdict": "records a human judgement bound to a version digest",
    "check": "runs the checker parts on a version and writes their results into the case",
    "constraints add": "adds an accepted constraint to the ledger",
    "constraints list": "lists the constraint ledger",
    "constraints propose": "proposes a change to an accepted constraint",
    "constraints accept": "accepts a proposed constraint change",
    "constraints reject": "rejects a proposed constraint change",
    "constraints link": "links a constraint to the criterion that evidences it",
    "output add": "records a run: an output produced elsewhere from a version",
    "output list": "lists recorded runs with part and cost",
    "compare": "compares two versions on the same criteria",
    "report": "writes the evidence report for a version",
    "export": "writes the case as a zip with a digest manifest",
    "import": "re-verifies a bundle against its manifest and opens it as a case",
}

COMMAND_MAP: dict[str, tuple[str, str, str]] = {
    # path: (SPINE or PART, part id or "", one-line reason)
    **{f"case {sub}": (SPINE, "", reason) for sub, reason in _CASE.items()},
    **{f"optimize {sub}": (SPINE, "", f"deprecated alias of 'case {sub}' for 0.5") for sub in _CASE},
    "install-skill": (PART, "install-skill", "the host writer part: installs a skill into a host's skills folder"),
    "uninstall-skill": (PART, "install-skill", "the host writer part: removes what it installed and restores the prior one"),
    "parts": (SPINE, "", "utility: lists the part registry"),
    "providers list": (SPINE, "", "model layer: every provider, shipped and yours"),
    "providers add": (SPINE, "", "model layer: adds or overrides a provider with no code change"),
    "providers remove": (SPINE, "", "model layer: removes a provider you added"),
    "providers price": (SPINE, "", "model layer: declares a model's price when none is shipped"),
    "run": (SPINE, "", "model layer: runs a prompt on any provider and model through the spend gate"),
    "hosts list": (SPINE, "", "delivery: the tools Proofhouse installs into, shipped and yours"),
    **{f"install {kind}": (SPINE, "", f"delivery: writes a {kind} into a tool, with a record and a backup") for kind in ("agent", "rule", "mcp")},
    **{f"uninstall {kind}": (SPINE, "", f"delivery: removes only the {kind} Proofhouse wrote") for kind in ("agent", "rule", "mcp")},
    "generate": (SPINE, "", "media engine: one image, video clip, voice or music track from any service through the spend gate"),
    "media list": (SPINE, "", "media engine: every media service, shipped and yours"),
    "media price": (SPINE, "", "media engine: declares a price per unit"),
    "media add": (SPINE, "", "media engine: adds a media service from a template, no code change"),
    "deploy": (SPINE, "", "delivery: puts a finished site online with the hosting service's own tool, only when you run it"),
    "addons list": (SPINE, "", "add-ons: every pack and package add-on, what each adds, and any that failed to load"),
    "addons install": (SPINE, "", "add-ons: checks and installs a pack of providers, services, tools and make kinds"),
    "addons remove": (SPINE, "", "add-ons: removes an installed pack"),
    "addons approve": (SPINE, "", "add-ons: approves a learned entry that sends a key or runs a command"),
    "train data": (SPINE, "", "training: cleans examples into training and check files"),
    "train services": (SPINE, "", "training: every training service, online and on this machine, shipped and yours"),
    "train price": (SPINE, "", "training: declares a price per million training tokens"),
    "train add": (SPINE, "", "training: adds a training service from a template, no code change"),
    "train start": (SPINE, "", "training: trains a model on your data through the spend gate, or on this machine"),
    "train status": (SPINE, "", "training: reads a training job's status"),
    "compare": (SPINE, "", "compare engine: the same job on many models at once, side by side with cost, time and a judge's scores"),
    "loop": (SPINE, "", "loop engine: an agent acts, checks and repeats on its own, or watches and acts, within one spending limit"),
    "referee start": (SPINE, "", "host mode: start a referee record while your own agent runs the work loop"),
    "referee round": (SPINE, "", "host mode: run the check, append a round, and say whether to stop"),
    "referee status": (SPINE, "", "host mode: read a referee record"),
    "make": (SPINE, "", "make engine: writes, tries, judges and improves a prompt, skill, agent, site, app or copy, a video, or a whole launch, within one spending limit"),
    "check": (SPINE, "", "host mode: tries a site, MCP server, hook, rule, skill or agent the host's own model wrote, with no key (Proofhouse itself makes no network calls)"),
    "record": (SPINE, "", "host mode: keeps each version the host's model wrote with its checks and score, and delivers the best in the make layout"),
    "render video": (SPINE, "", "host mode: assembles a finished video from the host's script, shots, voice and music with FFmpeg, no paid call"),
    "adapters": (SPINE, "", "utility: alias of parts limited to request builders, with its 0.4.1 output"),
    "models list": (SPINE, "", "utility: model-notes registry"),
    "models update": (SPINE, "", "utility: adds newly released models and workspaces from each provider's own list and the official release notes"),
    "models show": (SPINE, "", "utility: model-notes registry"),
    "models remember": (SPINE, "", "utility: stores the user's own model notes"),
    "models forget": (SPINE, "", "utility: removes cached model notes"),
    "demo": (SPINE, "", "utility: the packaged reference workflow"),
    "scan": (SPINE, "", "utility: read-only project scan for the skill's questions"),
    "doctor": (SPINE, "", "utility: environment and contract check"),
    "validate": (SPINE, "", "compiler: IR validation"),
    "inspect": (SPINE, "", "compiler: IR inspection"),
    "compile": (SPINE, "", "compiler: lowers IR through a request builder part"),
    "closed-loop": (SPINE, "", "compiler: offline structural loop with the fake request builder"),
    "compile-requirements": (SPINE, "", "compiler: requirements-contract evaluation (experimental)"),
    "closed-loop-bridged-008": (SPINE, "", "compiler: bridged requirements loop (experimental)"),
    "evaluate-product": (SPINE, "", "compiler: imported observations against a rubric (experimental)"),
    "execute-openai": (SPINE, "", "opt-in live send of a compiled artifact to any provider with --provider"),
    "route": (SPINE, "", "overseer station: classifies an objective (experimental)"),
    "assay": (SPINE, "", "overseer station: claim ledger (experimental)"),
    "proof": (SPINE, "", "overseer station: two-pass audit (experimental)"),
    "eval validate": (SPINE, "", "legacy eval harness: dataset validation"),
    "eval report": (SPINE, "", "legacy eval harness: report skeleton"),
    "eval loadouts": (SPINE, "", "legacy eval harness: loadout list"),
    "eval compile-loadout": (SPINE, "", "legacy eval harness: loadout compile"),
    "eval generate": (SPINE, "", "legacy eval harness: prompt templates"),
    "hosted-compile": (SPINE, "", "quarantined behind the PROOFHOUSE_EXPERIMENTAL gate"),
    "hosted-view": (SPINE, "", "quarantined behind the PROOFHOUSE_EXPERIMENTAL gate"),
    "hosted-export": (SPINE, "", "quarantined behind the PROOFHOUSE_EXPERIMENTAL gate"),
    "hosted-delete": (SPINE, "", "quarantined behind the PROOFHOUSE_EXPERIMENTAL gate"),
    "missionrig-generate": (SPINE, "", "quarantined behind the PROOFHOUSE_EXPERIMENTAL gate"),
    "workspace-consume": (SPINE, "", "quarantined behind the PROOFHOUSE_EXPERIMENTAL gate"),
}
