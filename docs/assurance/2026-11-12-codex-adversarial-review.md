# Proofhouse: adversarial peer review and local hardening

Reviewed repository: **KM-it-ops/Proofhouse**
Baseline: **38eebf8e85ab7f60f123b274ae4cf0c3f7b03c71**, package 0.10.3
Verification date: **November 12, 2026**, America/New_York
Disposition: **candidate prepared for a draft pull request; not merged, released, or deployed**

## My assessment

Proofhouse has useful engineering underneath its very broad ambition. Its strongest work is the machinery that makes a result inspectable: version records, exact request admission, explicit uncertainty, deterministic checks, and reversible installation. Those are practical advantages for someone switching between models and AI workspaces.

Its central weakness is uneven enforcement. The older compiler and installer paths often treat boundaries as contracts. Some newer execution paths treat the same boundaries as conventions. A prompt saying “judge strictly” does not make a judge reliable. A localhost address does not authenticate a caller. A filename that looks safe before Windows creates it may identify a different file afterward.

I would continue building the full product. I would make its existing enforceable contracts travel with every new engine. Adding another capability should inherit the spending, execution, artifact, and evidence rules automatically. Reimplementing each rule in every engine is already producing inconsistencies.

This review found **seven concrete defects**, reproduced six in the first synthetic probe set and the seventh in an additional media transport probe. Local fixes cover all seven. The first probe set also demonstrates one separate cost-accounting trust limitation; that limitation is not a demonstrated provider billing exploit.

The patch improves specific boundaries. It does not establish that arbitrary generated programs, subjective judge scores, provider prices, or all autonomous workflows are safe or correct.

## What I inspected and how

I used the GitHub connection to identify the repository and pin its current main revision, then cloned that revision into an isolated review checkout. I read the current repository instructions and master plan, traced the relevant production paths, inspected nearby tests, and ran targeted tests. Older notes helped locate context; the findings below come from current source and current experiments.

Priority areas were provider transports, spending admission and aggregate accounting, agent bridging, autonomous file actions, generation and delivery selection, portable filesystem names, installation transactions, evidence binding, and release workflows. I also inspected the product documentation and the distinction between offline tests and live demonstrations.

The probes used inert files, dummy credentials, fake model responses, a fake agent runner, loopback HTTP servers, and httpx MockTransport. They did not invoke a real coding agent or send their dummy credentials to an external service. The tests explicitly close their loopback servers and join their threads.

This is a targeted adversarial review, not an exhaustive audit of every source file, dependency, frontend, media renderer, or external integration. No paid provider, cloud deployment, model download, training job, or release was used to validate the fixes. Python verification used Windows and Python 3.13.11, not the full CI platform matrix.

## Confirmed weaknesses and the fixes

Severity here reflects realistic impact under the stated preconditions. P1 means address before relying on the affected boundary; P2 means a significant reliability or portability defect. None is labeled an unauthenticated internet takeover.

| Finding | Priority | Demonstrated behavior at baseline | Local correction |
|---|---|---|---|
| F1: default HTTP fallback forwards credentials on redirects | P1 | With optional httpx absent, a 302 from one host caused urllib to send a dummy bearer token to a second hostname. | Refuse automatic redirects in the standard-library transport. |
| F2: local agent bridge has no caller authentication | P1 | A request with an untrusted Origin, form content type and no Authorization invoked the fake runner. | Require a private bearer token before serving; reject browser-origin/non-JSON calls; bound request size and validate message objects. |
| F3: loop can read common credential files | P1 | A model file action read a synthetic `.env` password; the next model context contained it. | Refuse common credential paths before reading or writing. |
| F4: loop can plant persistent repository hooks | P1 | With commands disabled, a file action created an inert `.git/hooks/pre-commit`. | Refuse repository metadata and credential directories. Reject Windows aliases before path resolution. |
| F5: judge score overrides failed deterministic checks | P1 | A site with a known broken internal link received score 10, stopped after one round, and was delivered. | A version with a failed deterministic check cannot trigger target completion or qualify for delivery. Failed drafts remain recorded. |
| F6: website files collide on Windows | P2 | `index.html` and `INDEX.HTML` were both accepted; the latter overwrote the former on Windows. | Reject case collisions before creating the folder and reuse portable filename validation. |
| F7: media redirects replay requests and forward custom keys | P1 | A synthetic 307 caused a second POST and carried `X-Api-Key` to another host. | Disable automatic POST/GET redirects in generation; refuse redirect results while polling or fetching. |

### F1: the default installation had weaker credential handling

The optional HTTP client did not follow redirects by default. The fallback used `urllib.request.urlopen`, which did. That made installing an optional dependency change the security behavior of the same command.

The reproduction returned a 302 from `127.0.0.1` to `localhost` on another port, using only synthetic credentials. The destination received the dummy bearer header. A compromised or misconfigured remote endpoint could use the same forwarding behavior; the test did not require compromising one.

The patch returns the redirect response without contacting its destination. A regression checks both the returned status and that the second server received no request. Source: [baseline transport](https://github.com/KM-it-ops/Proofhouse/blob/38eebf8e85ab7f60f123b274ae4cf0c3f7b03c71/src/proofhouse/live.py#L127).

### F2: localhost was being used as an authentication boundary

The bridge launches an already logged-in agent. Binding it to loopback limits exposure, but another local caller can still reach it. The baseline also accepted a browser-shaped form request containing JSON. The reproduction proves server acceptance; it is not a claim that every browser/version permits every cross-origin localhost request.

The new `PROOFHOUSE_AGENT_TOKEN` is an environment credential, with constant-time byte comparison. It must be present in both bridge and client environments. Startup and provider guidance now explain this, without printing the token. Requests are limited to 1 MB and require a nonempty list of message objects. Existing successful-client tests were updated to authenticate, rather than deleting them.

This changes setup: an existing unauthenticated bridge provider must be configured with the token environment variable. It does not add process isolation, account-allowance measurement, a concurrency quota, or slow-client protection. Source: [baseline handler](https://github.com/KM-it-ops/Proofhouse/blob/38eebf8e85ab7f60f123b274ae4cf0c3f7b03c71/src/proofhouse/agent_server.py#L151).

### F3 and F4: “inside the folder” was too permissive

The loop confined resolved paths to its work directory, which is useful. But many secrets and execution hooks legitimately live inside that directory. Hiding dotfiles from the initial listing did not prevent a model from requesting them by name. Redaction covered known provider values, not an unrelated password stored in a file.

The patch denies `.env`/`.env.*`, selected credential filenames and private-key formats, version-control metadata, and common credential directories. These checks apply to direct file actions even when shell commands are allowed.

The independent reviewer then demonstrated a bypass in the first patch: on Windows, writing `.git./hooks/pre-commit` into a fresh directory created `.git/hooks/pre-commit`. The corrected guard rejects raw components with trailing dots/spaces or colons before resolving them. Regression cases include that missing-path alias and NTFS stream syntax.

This is defense against common hazards, not a complete secret classifier or sandbox. Arbitrarily named secrets, hard-link aliases, ordinary source files that later execute, and allowed shell commands remain outside that guarantee. Sources: [path boundary](https://github.com/KM-it-ops/Proofhouse/blob/38eebf8e85ab7f60f123b274ae4cf0c3f7b03c71/src/proofhouse/loop.py#L126), [file actions](https://github.com/KM-it-ops/Proofhouse/blob/38eebf8e85ab7f60f123b274ae4cf0c3f7b03c71/src/proofhouse/loop.py#L163).

### F5: deterministic failure must outrank subjective praise

The make engine previously excluded versions that could not be written, but still selected written versions with failed checks. Its target-score stopping condition also ignored those failures. That allowed a flattering or manipulated judge response to end repair while a known defect remained.

The patch applies the same eligibility rule to early completion and final selection: no failed deterministic checks. An unmeasured check stays unmeasured; this patch does not require every optional build/browser check to run before a draft can be delivered. That distinction preserves portability while preventing an observed failure from becoming the winner. Source: [baseline selection](https://github.com/KM-it-ops/Proofhouse/blob/38eebf8e85ab7f60f123b274ae4cf0c3f7b03c71/src/proofhouse/make.py#L500).

### F6: filesystem identity must be portable

The website writer had its own weaker name checks despite an existing shared validator. It now rejects case collisions and Windows device/trailing-dot/sensitive hidden names before writing. This extends a useful existing strength instead of introducing another parallel validation scheme. Source: [baseline writer](https://github.com/KM-it-ops/Proofhouse/blob/38eebf8e85ab7f60f123b274ae4cf0c3f7b03c71/src/proofhouse/sitecheck.py#L36).

### F7: one admitted request could become two transport requests

Media generation followed redirects for shipped and user-configured services, while learned services had stricter behavior. httpx can replay a POST on 307 and forwards arbitrary custom credential headers. One spend-gate callback therefore did not guarantee one HTTP request.

The additional reproduction used a MockTransport: the second host was fictional and no network request occurred. The patch refuses automatic redirects consistently, including authenticated polling. Direct service endpoints are now required. Services or asset URLs that depend on redirects will fail explicitly until a carefully scoped redirect policy is implemented. Source: [baseline media transport](https://github.com/KM-it-ops/Proofhouse/blob/38eebf8e85ab7f60f123b274ae4cf0c3f7b03c71/src/proofhouse/media.py#L313).

## Useful strengths, and how I would expand them

| Strength | Why it is useful | Practical expansion |
|---|---|---|
| Spend admission uses exact serialized bytes and Decimal arithmetic, rejects unknown/unpriced shapes, and records assumptions. | It can stop an unsafe request before sending rather than explain overspend afterward. | Share transport policy with every engine. Separate reserved allowance from provider-reported estimates. Version the pricing assumptions beside each result. |
| Evidence binds judgments to revision, criterion and recorded output digests. | A PASS can be traced to what was actually judged; stale judgments need not silently survive edits. | Carry artifact and checker identities into make/loop delivery records. Keep structural validity, behavioral checks and subjective scores separate. |
| Skill installation stages and verifies content, backs up replacements, and checks rollback state. | Failed upgrades can preserve the working installation; uninstall can refuse to destroy user edits. | Reuse this transaction pattern for other host writers and delivery operations. Extend failure-injection checks where state is swapped. |
| Providers, hosts and service entries are largely data-driven, with learned execution entries requiring approval. | Users can extend integrations without repeatedly editing central dispatch logic. | Add adapter contract tests for auth, redirects, output limits, price units, polling and cancellation. Keep approval bound to the exact entry content. |
| Host mode works with an existing AI workspace and records unmeasured checks honestly. | It gives users value without forcing another hosted account or pretending missing tools passed. | Make one artifact/check/status vocabulary work across host mode and API mode. The patched delivery rule is a step toward that consistency. |
| CI spans operating systems/Python versions, exercises installed wheels, checks generated-contract drift, and includes deliberately broken dashboard copies. | It checks distribution behavior and whether some tests can actually detect defects. | Add mutation cases at the trust boundaries found here: a redirecting transport, a lying judge, a path alias and an unauthenticated caller. Require these checks before merging. |
| The master plan distinguishes offline tests from live demonstrations and records imperfect results. | Readers can assess maturity without inferring that mocked integrations are live-proven. | Generate a capability-status page from records with revision, environment, artifact hashes and unresolved failures. Avoid manually maintained overlapping status prose. |

These are strengths in the inspected design and tests, not measured claims that Proofhouse improves every model's output quality. The patch directly expands two of them: shared portable validation now protects sites, and deterministic checks now govern make delivery.

## Remaining work I would prioritize

1. **Protect the loop's acceptance oracle.** The model can edit ordinary project tests and then run the owner's check command. A green check can mean the implementation improved or that the test became easier. Keep acceptance tests outside model-writable paths, or declare immutable checker inputs and verify their hashes before accepting completion. Acceptance: a model action that replaces a failing checker with `exit 0` must not produce accepted completion. This is especially relevant to the README's “make the tests pass” example.

2. **Separate reservations from estimated bills.** `Budget.charge` prefers provider-reported estimated usage over the admitted worst case. The probe shows that a synthetic successful response reporting zero leaves the entire allowance available. That is not evidence of a real provider underreporting, and prices/counting assumptions are already disclosed. It does mean the ceiling depends on honest usage and accurate prices. Keep conservative reserved/spent exposure separate from reported estimates; optionally release reservations under an explicit trusted-provider policy. Acceptance: missing, delayed, inconsistent and implausibly low usage cannot silently replenish hard exposure allowance.

3. **Bound bridge work, not only body size.** Add a small concurrent-run limit, queue/backpressure policy, request-read timeout and process-tree cancellation. Acceptance: parallel or slow authenticated callers cannot spawn unlimited agent processes or keep workers occupied indefinitely. A subscription-backed bridge also needs allowance labels distinct from dollars.

4. **Enforce the release path.** GitHub reported main as unprotected, with required checks off; the repository rulesets endpoint returned an empty list at review time. The manual publish workflow builds its selected ref without proving that the exact revision passed CI or matches a release tag/version. Pinned actions, read-only source permissions and OIDC publishing are positives. Add protected-main requirements and a publish job that verifies the exact tagged revision/version and its required checks, then publishes the tested artifact. Repository/environment settings were not changed; environment approval rules were not inspected. Sources: [main metadata](https://api.github.com/repos/KM-it-ops/Proofhouse/branches/main), [rulesets](https://api.github.com/repos/KM-it-ops/Proofhouse/rulesets), [publish workflow](https://github.com/KM-it-ops/Proofhouse/blob/38eebf8e85ab7f60f123b274ae4cf0c3f7b03c71/.github/workflows/publish.yml).

5. **Judge produced media and verify learned integrations against retrieved sources.** The plan explicitly says the media judge reads plans/checks rather than seeing or hearing the result. `learn.py` records model-named sources as unchecked. Preserve those honest labels. Add output-based checks and, when supported, visual/audio inspection; distinguish “model proposed this integration” from “official documentation retrieved and verified.” Acceptance: a convincing plan over an irrelevant/silent file cannot earn the same status as inspected output, and generated citations cannot become verified research without retrieval evidence.

6. **Make the documentation agree about maturity.** The README/master plan describe the broad current product, while parts of the development guide still describe the older case/compiler core as the supported surface. Generate command inventory and status from a common source. Keep capability ambition, mocked contract coverage, real integration runs and judged quality as separate fields.

These are concrete follow-on improvements, not implemented claims. The patch intentionally does not redesign accounting, introduce a sandbox, change account settings, or claim to solve prompt injection through wording.

## Verification and patch status

| Check | Result | Meaning |
|---|---|---|
| Original focused baseline | 116 passed | Existing tests passed before hardening. |
| Initial adversarial probes | 7 passed | Six defects and one accounting trust limitation reproduced; these tests assert baseline behavior. |
| Additional media probe | 1 passed | POST replay/custom-key forwarding reproduced using a mocked transport. |
| Final hardening, bridge, model-notes and media suites | **102 passed** | Includes 23 new hardening regression cases. |
| Broader affected offline suites | **251 passed, 3 skipped, 3 failed** | All three failures occurred while creating Windows junction fixtures. |
| Spending, evidence, canonicalization, benchmark and install-transaction suites | **227 passed, 4 failed** | All four failures occurred while creating Windows junction fixtures. |
| Junction failures retried under an explicitly writable workspace test directory | 7 fixture failures | Reproduced the sandbox's inability to create junctions; did not establish product behavior for those cases. |
| `uv lock --check --python 3.13` | Passed | Test-extra dependency and lock metadata agree. |
| `git diff --check` | Passed | No whitespace errors in tracked patch. |
| Independent end review | No remaining actionable findings in inspected changes | Reviewer found and helped correct a Windows alias bypass and a clean-CI dependency gap; did not independently rerun suites. |

Counts overlap between runs and must not be summed into a unique test total. This is not a fully green suite or a CI-matrix result. Seven junction cases still need verification in an environment that can create their fixtures. No test assertions, sandbox protections or approval gates were weakened to conceal those failures.

The sandbox also prevented a normal editable setuptools build through a sandbox-generated path expansion error. Tests used the source checkout on PYTHONPATH with dependencies installed in an isolated environment. Installed-wheel behavior of this patch therefore remains unverified locally.

The local branch is `fix/adversarial-hardening-20261112`. The portable patch includes production changes, documentation, CI/test dependencies, lock metadata, and regression tests. The original reproduction files are supplied separately and intentionally assert the old behavior; use the patch's regression tests to validate corrected behavior.

My recommendation is to review and validate this patch on the normal CI matrix, resolve the junction verification gap, then land it through the repository's normal review path. After that, protect the loop oracle and make cost exposure accounting conservative. Those changes increase the usefulness of the entire product without narrowing its vision.
