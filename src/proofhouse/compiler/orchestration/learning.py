"""Recurrence N>=2 learning rules as data. Offline. K=20 GC."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_K = 20


@dataclass
class Rule:
    id: str
    version: int
    hit_count: int
    last_fired: str | None
    consecutive_unfired: int
    regression_case_id: str
    finding_hash: str = ""


def gc(rules: list[Rule], k: int, runs_elapsed: int) -> list[Rule]:
    for rule in rules:
        rule.consecutive_unfired += runs_elapsed
    return [rule for rule in rules if rule.consecutive_unfired >= k]


class RuleStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.rules_path = self.root / "rules.json"
        self.pending_path = self.root / "pending.json"
        if not self.rules_path.is_file():
            self.rules_path.write_text("[]\n", encoding="utf-8")
        if not self.pending_path.is_file():
            self.pending_path.write_text("{}\n", encoding="utf-8")

    def load_rules(self) -> list[Rule]:
        raw = json.loads(self.rules_path.read_text(encoding="utf-8"))
        return [Rule(**item) for item in raw]

    def _save_rules(self, rules: list[Rule]) -> None:
        self.rules_path.write_text(json.dumps([asdict(rule) for rule in rules], indent=2) + "\n", encoding="utf-8")

    def _eval_dataset_path(self) -> Path:
        return self.root.parent / "datasets" / "learning_rules.jsonl"

    def record_finding(self, finding_hash: str) -> Rule | None:
        pending = json.loads(self.pending_path.read_text(encoding="utf-8"))
        pending[finding_hash] = int(pending.get(finding_hash, 0)) + 1
        self.pending_path.write_text(json.dumps(pending, sort_keys=True) + "\n", encoding="utf-8")
        count = pending[finding_hash]
        if count < 2:
            return None
        rules = self.load_rules()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        promoted: Rule | None = None
        for rule in rules:
            if rule.finding_hash == finding_hash:
                rule.hit_count = count
                rule.last_fired = now
                rule.consecutive_unfired = 0
                promoted = rule
                break
        if promoted is None:
            promoted = Rule(
                id=f"LR-{finding_hash[:12]}",
                version=1,
                hit_count=count,
                last_fired=now,
                consecutive_unfired=0,
                regression_case_id=f"REQ-LR-{finding_hash[:12].upper()}",
                finding_hash=finding_hash,
            )
            rules.append(promoted)
        self._save_rules(rules)
        self.write_eval_dataset(self._eval_dataset_path())
        return promoted

    def write_eval_dataset(self, path: Path) -> None:
        lines: list[str] = []
        for rule in self.load_rules():
            payload = {
                "case_id": rule.id,
                "req_ids": [rule.regression_case_id],
                "observations": {"promoted": True},
            }
            lines.append(json.dumps(payload, sort_keys=True))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_retired(self, retired: list[Rule], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        addition = "".join(json.dumps(asdict(rule), sort_keys=True) + "\n" for rule in retired)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(addition)
        retired_ids = {rule.id for rule in retired}
        remaining = [rule for rule in self.load_rules() if rule.id not in retired_ids]
        self._save_rules(remaining)
        self.write_eval_dataset(self._eval_dataset_path())

    def gc_unfired(self, k: int = DEFAULT_K, runs_elapsed: int = 1) -> list[Rule]:
        rules = self.load_rules()
        retired = gc(rules, k=k, runs_elapsed=runs_elapsed)
        self._save_rules(rules)
        if retired:
            self.write_retired(retired, self.root / "retired.jsonl")
        return retired
