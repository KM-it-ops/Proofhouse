# PromptRig Security and Threat Model

## Protected assets

- user identities and sessions
- project content and uploaded files
- provider API credentials
- generated prompts and proprietary workflows
- evaluation datasets and results
- tenant metadata, billing, and usage
- benchmark hidden tests and sealed submissions

## Trust boundaries

1. browser to web application
2. web application to Supabase
3. web application to compiler API
4. compiler API to provider APIs
5. compiler API to storage and job execution
6. uploaded/retrieved content to model context
7. benchmark runner to competitor workspace
8. public benchmark materials to hidden evaluator

## Primary threats and required controls

### Cross-tenant access
Enforce authorization server-side and through database row-level policies. Test direct object-reference attacks and storage paths.

### Credential theft
Use designated encrypted secret storage. Never include raw keys in browser-readable project records, logs, prompts, traces, exports, or error messages.

### Prompt injection
Treat documents, webpages, tool outputs, and provider-generated content as untrusted data. Delimit them from instructions, restrict tools by policy, and require approval for consequential actions.

### Malicious artifacts
Validate filenames, MIME types, sizes, archive contents, and schemas. Scan or sandbox executable content. Exports must not contain secrets.

### Unbounded execution and cost
Use per-project budgets, timeouts, tool-call limits, repair limits, rate limits, cancellation, and duplicate-call detection.

### Supply-chain compromise
Pin dependencies, generate an SBOM, run license and vulnerability scans, protect CI secrets, and review generated install scripts.

### Benchmark contamination
Keep hidden tests outside competitor workspaces, deny cross-submission access, freeze starting commits, log network policy, and hash all evidence.

### Misleading results
Separate deterministic checks, model-graded judgments, human review, infrastructure failure, and unresolved uncertainty.

## Action classes

- Read-only and reversible local work: may run automatically.
- Reversible project writes: perform and report.
- External messages, purchases, permission changes, publication, deletion, or production deployment: require explicit approval at the action boundary.

## Security release gates

- no critical known vulnerability
- no committed secret
- tested tenant isolation
- tested credential redaction
- tested prompt-injection defenses
- tested rate and retry limits
- documented incident and credential-revocation process
