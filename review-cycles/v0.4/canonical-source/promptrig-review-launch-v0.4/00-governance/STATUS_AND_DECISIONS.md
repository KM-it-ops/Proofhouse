# Status and Decisions

## Accepted

- Product identity: PromptRig.
- Hosted commercial SaaS plus open developer tooling.
- Nontechnical Simple Mode with a Developer Mode toggle.
- PromptRig Intermediate Representation as the semantic source of truth.
- Provider-specific lowering through capability manifests and adapters.
- Evaluation and bounded repair as first-class compiler stages.
- Next.js frontend plus FastAPI compiler service in a monorepo.
- Supabase as the provisional MVP platform for Postgres, authentication, storage, and realtime features.
- Multi-stage coding-agent benchmark rather than one oversized pass/fail run.
- Autonomous and steered benchmark results must remain separate.
- The benchmark unit is the complete agent configuration, not the model label alone.

## Provisional—must be confirmed during review

- Exact open-core licensing boundary.
- Supabase versus a Postgres-first alternative for long-term infrastructure.
- Background-job system and queue provider.
- Managed-credit billing architecture.
- First two mandatory provider adapters.
- Exact benchmark resource limits and run count.
- Deployment targets and infrastructure-as-code stack.

## Explicitly deferred

- Marketplace.
- Mobile-native applications.
- Self-hosted enterprise control plane.
- Arbitrary user-authored executable plugins.
- Full provider catalog beyond the first four adapters.


## v0.4 status

Round 1 independent review is now launch-ready. Architecture remains unfrozen. The only authorized next activity is isolated reviewer execution and evidence intake under `09-review-execution/`.
