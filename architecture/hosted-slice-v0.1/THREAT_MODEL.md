# Hosted-slice threat model (MISSION-034)

**Status:** Planning threat model. Not a penetration test. Q2 unpicked, so control placement is stack-agnostic.

## Assets

- Canonical IR and evidence
- Requirements records
- Operator identity material
- Export packages
- Opt-in live credentials (not on the default hosted path)

## Threats

| ID | Threat | Mitigation in this package |
|---|---|---|
| T-UI-SEMANTICS | UI becomes the compiler (REJ-007) | Mode-parity on IR digest; hidden UI config rejected; Vite/JSX forbidden |
| T-SIMPLE-UI | `simple_mode_ui` bypasses headless intake | AE5: closed-loop still BLOCKED |
| T-LIVE-DEFAULT | Hosted slice silently calls providers | `execute-openai` is `x-default-hosted-slice: false`; default path `network_allowed=false` |
| T-TENANT-READ | Cross-tenant read once SaaS exists | Fail closed; first slice is single-tenant |
| T-SECRET-IR | Credentials land in IR/fixtures/git | Forbidden; live creds are caller env at invoke time |
| T-DELETE-RESIDUE | Export/delete leaves compiler-visible copies | Deletion contract: CLI cannot see the deleted project |
| T-STACK-LOCKIN | Scaffolding before Q2 locks a vendor | OPTIONS.json invalidates scaffold-before-Q2 |

## Residual risk

No running service exists, so runtime authn/authz is untested. Owner Accept of OAR-027 does not authorize production hosting.
