# PromptRig Risk Register

| ID | Risk | Impact | Mitigation | Gate |
|---|---|---:|---|---|
| R-01 | Scope exceeds agent run capacity | High | gated milestones, frozen MVP, hard exclusions | benchmark start |
| R-02 | Provider APIs change | High | dated manifests, conformance tests, fallbacks | each release |
| R-03 | Benchmark compares labels rather than systems | High | harness/model/environment disclosure | publication |
| R-04 | Hidden benchmark contamination | High | isolated workspaces, no cross-branch access, hashes | each run |
| R-05 | LLM evaluator bias | High | deterministic tests first, blind human review | scoring |
| R-06 | Cross-tenant data leak | Critical | RLS, server authorization, adversarial tests | alpha |
| R-07 | User API-key exposure | Critical | encrypted secret storage and redaction | benchmark |
| R-08 | Frontier-model costs explode | High | evaluation ladder, budgets, cancellation | hosted alpha |
| R-09 | Open-source license weakens business | Medium | delayed license decision and counsel review | public release |
| R-10 | Simple Mode overwhelms users | High | observed usability testing and jargon limits | alpha |
| R-11 | Provider-neutral core becomes mediocre | High | provider lowering passes and native features | adapter gate |
| R-12 | Marketing overstates results | High | claim provenance and exact benchmark language | launch |
