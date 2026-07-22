# PRS examples

**Status:** Non-binding illustration only.

```text
prs 0.1-proposal
project "Support triage"
objective "Classify a support request and explain the routing decision"
input ticket: object required
output route: enum[account,billing,technical]
constraint "Do not expose credentials or private account data"
evaluate "schema_valid" deterministic
```

This is not an accepted grammar and cannot be used as an implementation contract. A future PRS compiler would either produce valid PromptRig IR with source mappings or return immutable diagnostics.
