# PromptRig MISSION-009 Report

**Mission:** Evaluation and Bounded Repair Contract  
**Status:** Proposed package prepared for adversarial audit and merge; not production-certified.  
**Baseline:** `main` at `d0bca1c9ebbf6ab4dfbfbab75ec27456c4f263cf`  
**Branch:** `contracts/mission-009-evaluation-repair-v0.1`

## Deliverables

- Contract package at `architecture/evaluation-repair-contract-v0.1/`
- Nine Draft 2020-12 schemas
- EVR-* diagnostic registry (separate from RQC-* and frozen compiler registry)
- 24 semantic-oracle fixtures covering precedence, repair budgets 0–2, regressions, security immutability, no-network, evidence retention
- Deterministic `validate_contract.py` harness
- Pytest suite `tests/evaluation/test_evaluation_repair_contract.py`

## Stop-condition posture

Encoded as fixtures + oracle rules:

- Model judges cannot be executable-authoritative (`EVR-AUT-0001`)
- Failed attempts cannot be discarded (`EVR-EVD-0001`)
- Termination cannot depend on model self-report (`EVR-TRM-0001`)
- Scoring cannot hide evaluator errors (`EVR-SCR-0001`)
- Repair cannot weaken security/objectives (`EVR-SEC-0001`)
- MISSION-008 requirement IDs must resolve (`EVR-REQ-0001`)

## Non-claims

No production evaluator/repair engine, no live providers, no benchmark runner, no UI.
