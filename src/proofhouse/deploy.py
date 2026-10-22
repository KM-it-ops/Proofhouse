"""Put a finished site online when you say so, with the hosting service's own tool.

A deploy target is data: the service's command line with ``{folder}`` and ``{name}``
placeholders. Netlify, Vercel, Cloudflare Pages and Surge ship in
``data/deploy_targets.json``; add any other in ``PROOFHOUSE_HOME/deploy_targets.json``
or through an add-on. The tool signs in your usual way (its own login or its token
variable); Proofhouse never sees or stores the token. Nothing is deployed unless you
run ``proofhouse deploy``; ``--dry-run`` shows the exact command first.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import providers

DEPLOY_SCHEMA = "proofhouse.deploy-targets/v1"
SHIPPED_PATH = Path(__file__).resolve().parent / "data" / "deploy_targets.json"
_URL = re.compile(r"https://[^\s'\"<>()]+")


class DeployError(ValueError):
    """The deploy cannot go ahead as asked; nothing was run."""


@dataclass
class Deployed:
    target: str
    folder: str
    command: list[str]
    status: str  # "deployed", "failed" or "dry run"
    url: str | None = None
    output: str = ""
    record: dict[str, Any] = field(default_factory=dict)


def _check(raw: Any, where: str) -> dict[str, Any]:
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or not providers._ID.fullmatch(raw["id"]):
        raise DeployError(f"{where}: every target needs an id of lowercase letters, digits, '.', '_' or '-'")
    command = raw.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(w, str) and w for w in command):
        raise DeployError(f"{where}: target {raw['id']} needs a command as a list of words")
    if not any("{folder}" in w for w in command):
        raise DeployError(f"{where}: target {raw['id']}'s command must name the {{folder}} to deploy")
    return raw


def _read(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as exc:
        raise DeployError(f"{path} is unreadable: {type(exc).__name__}") from None
    if not isinstance(data, dict) or data.get("schema") != DEPLOY_SCHEMA or not isinstance(data.get("targets"), list):
        raise DeployError(f"{path} must be a {DEPLOY_SCHEMA} file with a targets list")
    return [_check(raw, str(path)) for raw in data["targets"]]


def all_targets() -> dict[str, dict[str, Any]]:
    """Shipped targets, then add-ons, then yours; a later one with the same id replaces an earlier one."""
    from . import addons, learn_catalog

    shipped = {t["id"]: t for t in _read(SHIPPED_PATH)}
    user = {t["id"]: t for t in _read(providers.proofhouse_home() / "deploy_targets.json")}
    found = learn_catalog.merge_learned(shipped, "deploy_targets", user=user)
    for name, raw in addons.contributions("deploy_targets"):
        if name == learn_catalog.LEARNED_PACK:
            continue
        try:
            found[raw["id"]] = {**_check(raw, f"add-on {name}"), "origin": f"add-on {name}"}
        except DeployError:
            continue  # checked when the pack was installed; a package add-on's bad entry is skipped
    found.update(user)
    return found


def deploy(folder: Path, target_id: str, *, name: str | None = None, dry_run: bool = False, timeout: int = 900,
           allow_commands: bool = False, research: Any = None, ask: Any = None) -> Deployed:
    folder = folder.resolve()
    if (folder / "site" / "index.html").is_file():
        folder = folder / "site"  # a make folder: deploy the finished site inside it
    if not (folder / "index.html").is_file():
        raise DeployError(f"{folder} has no index.html to deploy")
    from . import learn_catalog

    targets = all_targets()
    if target_id not in targets:
        if ask is None and research is None:
            raise DeployError(f"no deploy target named {target_id!r}; known: {', '.join(sorted(targets))}")
        from .learn import LearnError

        try:
            if ask is not None:
                learn_catalog.ensure_deploy(target_id, None, ask)
            else:
                learn_catalog.ensure_deploy(target_id, research)
        except LearnError as exc:
            raise DeployError(str(exc)) from None
        targets = all_targets()
    target = targets.get(target_id)
    if target is None:
        raise DeployError(f"could not learn deploy target {target_id!r}")
    learned = learn_catalog.learned_raw("deploy_targets", target_id)
    if learned and learn_catalog.needs_approval(learned):
        raise DeployError(learn_catalog.refusal_message(learned, thing=f"Deploy target {target_id}",
                                                        command=f"{learn_catalog.APPROVE_CMD} {target_id}"))
    if not dry_run and learn_catalog.learned_requires_commands("deploy_targets", target_id) and not allow_commands:
        from . import make_checks
        raise DeployError(make_checks.NOT_ALLOWED)
    label = name or re.sub(r"[^a-z0-9-]+", "-", folder.parent.name.lower() if folder.name == "site" else folder.name.lower()).strip("-")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", label or ""):
        raise DeployError("--name must be lowercase letters, digits and hyphens")
    command = [w.replace("{folder}", str(folder)).replace("{name}", label) for w in target["command"]]
    if dry_run:
        return Deployed(target_id, str(folder), command, "dry run")
    tool = target.get("tool") or command[0]
    if shutil.which(command[0]) is None:
        hint = f"; install it with: {target['install']}" if target.get("install") else ""
        raise DeployError(f"{tool} is not installed{hint}")
    try:
        run = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        raise DeployError(f"{tool} did not finish in {timeout} seconds") from None
    output = (run.stdout or "") + (run.stderr or "")
    urls = _URL.findall(output)
    done = Deployed(target_id, str(folder), command, "deployed" if run.returncode == 0 else "failed",
                    url=urls[-1].rstrip(".,") if urls and run.returncode == 0 else None, output=output[-4000:])
    done.record = {"target": target_id, "folder": str(folder), "command": command, "status": done.status, "url": done.url,
                   "exit": run.returncode, "when": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    log = providers.proofhouse_home() / "deploys.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(done.record, sort_keys=True) + "\n")
    return done
