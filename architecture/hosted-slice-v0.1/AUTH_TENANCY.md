# Auth and tenancy contract

**Status:** Contract only. Q2 unpicked. No identity provider is implemented.

## First slice (recommended)

`AUTH-SINGLE-USER-ALPHA`: one operator, local credential, single-tenant closed-alpha. Cross-tenant reads do not exist because a second tenant does not exist.

## Later option

`AUTH-OIDC` remains an option. It is not authorized here.

## Rules that do not wait on Q2

- Authorization decisions are recorded as audit events, not as IR fields.
- A caller cannot write UI state into canonical IR (REJ-007).
- Cross-tenant read, when tenancy exists, fails closed.
- Session tokens never enter evidence bundles, IR, or git.
- Default hosted operations stay offline. Live `execute-openai` stays behind the existing opt-in boundary and is not on the default hosted slice.

## SaaS multi-tenancy

DFR-006 remains deferred for full hosted multi-tenancy. This package records the fail-closed rule; it does not implement isolation.
