# MISSION-036 MissionRig and Workspace Consumer

**Status:** OAR-029 Ready (not Accepted).
**Baseline:** MISSION-035 hosted runtime. Skip-cert law is OAR-022 Ready (not undone).
**Profile:** `structured_minimal_v0` evidence bundles only.

This mission is **not CERTIFIED**. The requirements compiler stays **PARTIAL**.

## What this mission records (narrow)

- **OAR-029 Ready (not Accepted).**
- MissionRig generator (`missionrig.py`) preserves objectives, stop conditions, permissions, and REQ ids. [ADR-003](../adr/ADR-003-MissionRig.md) remains the ownership split: MissionRig consumes PromptRig, it does not own IR.
- PARTIAL / unresolved compiler evidence yields a PARTIAL mission. It does not invent SUCCESS.
- Workspace consume is read-only ([ADR-002](../adr/ADR-002-AI-Engineering-Workspace.md)). IR write-back fails closed (`EVR-WS-0001`).
- MissionRig crash after read leaves PromptRig evidence/intake bytes unchanged.
- **Not a live** path. Skip-cert law (OAR-022) is not undone.
- OAR-028 remains MISSION-035 (not rewritten).

## Non-claims

- Not CERTIFIED requirements compiler. Not full MISSION-008. Not full Phase 4B exit.
- Not CERTIFIED MissionRig. Not a multi-agent marketplace.
- **Not a live** provider path. Not M3.
