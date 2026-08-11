# MISSION-011 Security Certification Notes

## Threats considered

- Model-judge executable authority bypass
- Repair weakening security constraints / accepted objectives
- Network/credential use under offline defaults
- Discarding failed attempts / unresolved defects
- Provider-specific fields entering canonical IR via closed-loop

## Controls verified in automated tests

- `tests/compiler/test_closed_loop.py` — security weaken refuse, no-network evidence
- `tests/compiler/test_mission_011_certification.py` — developer profile, packaging smoke, schedule presence, offline defaults
- `tests/evaluation/test_evaluation_repair_contract.py` — EVR stop-conditions

## Residual risk

Prototype force_* test hooks exist only in unit tests; production CLI does not expose them.
