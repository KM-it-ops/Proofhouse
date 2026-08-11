# PromptRig Ambition Gap Analysis

**Date:** 2026-08-11  
**Baseline:** `main` @ `9d7321c` (== `origin/main`)  
**Authority:** Evidence from repo + OARs + roadmap; not a mission launch authorization.  
**Boss stance under test:** Reach destinations **sequentially** — complete compiler → production AI platform → enterprise SAST harness → widely adopted OSS — using the MISSION-009→011 campaign pattern (contract → prototype → certify + adversarial audit).

---

## One-line current truth

PromptRig is a **public highlight**: PromptOps + offline eval/closed-loop harness with inspectable contracts. Headless core is shippable for **structured profiles + fake adapter**; live providers, UI, SAST-SKU, and adoption are roadmap — not present tense.

---

## Destination order (Boss sequential thesis)

| Step | Destination | Role in sequence |
|------|-------------|------------------|
| 1 | Complete compiler product | Semantic foundation; unlocks honest claims about intent→IR→eval→repair |
| 2 | Production AI platform | Hosted vertical slice + opt-in live execution on certified headless core |
| 3 | Enterprise SAST harness | Security-analysis SKU reusing compiler evidence model (strategy fork vs pure Phase 9) |
| 4 | Widely adopted OSS | External discovery, install, contribute, cite — mostly GTM; not a fixture campaign |

**Verdict on the thesis:** Engineering destinations **1 → 2** fit the 009→011 pattern cleanly. Destination **3** fits the pattern only after an owner ADR that SAST is an intentional product fork (not DFR-010 “after Phase 9” by default). Destination **4** cannot be “certified” the way EVR fixtures are — stars and community are outcomes; only packaging/docs/release hygiene are campaign-shaped. Running thin OSS hygiene **in parallel** with step 1 does not break the sequence and reduces dual-README damage.

---

## Destination 1 — Complete compiler product

### Definition (no lying)

All of the vision loop is headless-owned and production-grade for declared profiles:

`intent → requirements → IR → capability → lowering → evaluation → bounded repair → evidence`

Plus: offline default, library/CLI parity, versioned evidence, plain-language path on the **schedule** (M1–M2 before any Simple Mode UI). MissionRig/Workspace (Phase 9) and public benchmark *claims* are out of this definition.

### Gap from `9d7321c`

| Present | Missing |
|---------|---------|
| Compiler Core v0.1 certified middle (validate/compile/adapters/offline) | Production eval/repair engines (code still MISSION-010 prototype digests + instruction append) |
| OAR-005 narrow cert: structured profiles + fake closed loop | Phase 4B residual bar: consumer matrix, perf bounds, contract version graduation |
| M0 structured profiles | M1 plain-language headless; M2 model-assisted suggestions |
| MISSION-008/009 contracts | IR v0.2 planning (Phase 5) if multi-turn/tools are part of “complete” demos |
| README Status honest | `CAPABILITY_MATURITY_MAP` + deferred registry **stale** vs OAR-005 |

### Work packages (campaign-shaped)

| ID | Package | Pattern | Size | Person-weeks |
|----|---------|---------|------|--------------|
| C0 | Governance honesty sync (maturity map, deferred registry, closed_loop labels) | doc gate | S | 0.5–1 |
| C1 | MISSION-012 — Honest Phase 4B graduation (eval/repair engines, evidence bundles, consumer smoke) | contractΔ → impl → certify | L–XL | 4–10 |
| C2 | MISSION-013 — Plain-language headless M1 | contract → prototype → certify | L | 3–6 |
| C3 | MISSION-014 — Model-assisted M2 (non-bypass) | contract → prototype → certify | M–L | 2–5 |
| C4 | MISSION-015 — IR v0.2 **planning** only (optional parallel once C1 entered) | planning package | M | 2–4 |

**Critical path:** C0 → C1 → C2 → C3. C4 may start after C1 evidence if separately authorized.  
**Subtotal to honest headless compiler product:** ~**10–22 person-weeks** (medium confidence).

### Honesty risks

Calling OAR-005 “Phase 4B complete”; calling digests “evaluation engines”; implying requirements compiler parses natural language; leaving maturity map denying what README claims.

### Stop conditions

Repair can weaken security/objectives; model output bypasses deterministic validation; live/UI/benchmark scope creep; IR v0.2 code without SPEC; promotion without map+evidence+owner in one change.

---

## Destination 2 — Production AI platform

### Definition

Hosted vertical slice: Simple + Developer Mode on one canonical project; headless owns semantics; **opt-in** live providers (BYOK, budgets, audit); persistence/auth/tenancy/export/delete. Roadmap Phases **6 + 8** (7 optional for claims).

### Gap

No Phase 6 execution boundary, no credentials model, no product persistence/tenancy, no mode-parity UI on certified path. Vite/legacy PromptOps ≠ Simple/Developer Mode.

### Work packages

| ID | Package | Pattern | Size | Person-weeks |
|----|---------|---------|------|--------------|
| P0 | Phase 5 runtime decisions consumed (from C4) | planning exit | — | (from C4) |
| P1 | MISSION-016 — Live execution permission boundary | contract → opt-in prototype → security certify | L–XL | 4–8 |
| P2 | MISSION-017 — Platform/security SPECs (auth, tenancy, retention) | contract-only | M–L | 2–4 |
| P3 | MISSION-018 — Vertical slice (transport + UI clients of headless) | prototype → certify | XL | 8–16 |
| P4 | MISSION-019 — Benchmark runner (only if claims wanted) | contract → sealed runner → review | XL | 6–12 |

**Critical path:** Destination 1 exit (esp. C2/C3 before Simple Mode) → P1 → P2 → P3.  
**Subtotal:** ~**20–40 person-weeks** after compiler (medium–low confidence).  
**Cumulative through platform closed-alpha:** ~**30–60 person-weeks**.

### Honesty risks

“Production platform” on fake-only path; green CI = hosted ready; UI-owned config (REJ-007).

### Pattern fit

**Strong.** Same 009→011 shape; live/CI must stay opt-in and isolated from offline default (Phase 6 doctrine).

---

## Destination 3 — Enterprise SAST harness

### Definition

Security analysis **product**: ingest prompts/agent configs/IR/artifacts; machine-readable findings; CI/IDE integration; FP discipline; audit trail. Not “we have adversarial fixtures.”

### Gap

Building blocks exist (fail-closed security/privacy, EVR-SEC, SAFETY_COVERAGE_MATRIX, adversarial fixtures). Missing: finding schema/rule language, scanner surface, SARIF/CI story, enterprise controls, measured corpus. DFR-010 parks “enterprise control plane” **after Phase 9** — treating SAST as next primary SKU is a **strategy change**, not automatic roadmap continuation.

### Work packages

| ID | Package | Pattern | Size | Person-weeks |
|----|---------|---------|------|--------------|
| S0 | Owner ADR: compiler-primary vs SAST-SKU (or dual with clear messaging) | decision | S | 1–2 |
| S1 | Finding/policy schema + fixtures | contract → certify | L | 6–10 |
| S2 | Offline scanner CLI/API on IR + evidence | prototype → certify | L | 6–12 |
| S3 | CI/SARIF integration | impl → certify | M | 3–6 |
| S4 | Enterprise packaging (SSO/RBAC/retention/air-gap) | XL product | XL | 12–24 |

**Air-gapped SAST MVP** can start after Destination 1 (reuses evidence model) **without** waiting for full platform — but Boss sequential thesis places it **after** platform. That is valid if the SKU needs live-run analysis / multi-tenant findings store; otherwise it burns calendar waiting on Phase 8.

**Subtotal MVP:** ~**25–50 person-weeks** (if after platform; less if air-gap-first after compiler).

### Honesty risks

Equating MISSION-011 adversarial CLEAN with customer SAST certification; OWASP-LLM coverage without mapped rules + FP evidence; “runtime protection” without Phase 6.

### Pattern fit

**Partial.** Contract→prototype→certify works for scanner MVP. SOC2, sales, competitor FP rates do **not** exit via OAR.

---

## Destination 4 — Widely adopted OSS

### Definition

External developers discover, install, contribute, and cite PromptRig. Releases, docs matching reality, issue hygiene, ecosystem examples. Stars are outcomes.

### Gap (GitHub checked 2026-08-11)

| Signal | Value |
|--------|-------|
| Stars / forks / watchers | **0 / 0 / 0** |
| Releases | **0** (`latestRelease: null`) |
| License | MIT |
| Contributors | 1 |
| Topics | none |
| Dual identity | README PromptOps framing vs Status Compiler Core |

### Work packages

| ID | Package | Size | Person-weeks |
|----|---------|------|--------------|
| O1 | Unify README/docs/badges with Compiler Core truth | M | 2–4 |
| O2 | Versioned PyPI releases + changelog tied to tags | M | 2–4 |
| O3 | Tutorial: install → closed-loop → evidence | M | 2–4 |
| O4 | CoC, issue templates, good-first-issues, discussions | S | 1–2 |
| O5 | Sustained triage + public roadmap | L ongoing | 0.25–0.5 FTE |

**Critical path:** O1–O3 can run **parallel to Destination 1** without claiming adoption. “Widely adopted” has **no deterministic exit**.

### Pattern fit

**Weak for the success criterion.** Packaging/docs are campaign-shaped; network effects are not. Do not invent a MISSION that “exits” when star count moves.

---

## Ranked leverage (career highlight vs company vs fame)

| Rank | Path | Why |
|------|------|-----|
| 1 | Finish Destination 1 (C0–C3) | Highest honesty leverage; matches portfolio voice; unblocks everything |
| 2 | Thin OSS hygiene (O1–O3) in parallel | Cheap; stops dual-message damage; no false adoption claim |
| 3 | Destination 2 if building a company | Only after 1; real product surface |
| 4 | Destination 3 | Only after S0 ADR; competing SKU messaging risk |
| 5 | Destination 4 “widely adopted” as a gate | Non-deterministic; track as continuous ops, not campaign exit |

---

## Intermediate honest labels (use until destinations exit)

| Until… | Say |
|--------|-----|
| Now (`9d7321c`) | Public highlight; certified offline structured closed-loop on fake adapter |
| After C1 | Production-grade headless eval/repair (still offline; still structured ± declared profiles) |
| After C2–C3 | Headless compiler product (intent path certified; still no hosted UI) |
| After P3 | Closed-alpha production AI platform vertical slice |
| After S2 | Offline prompt/agent SAST MVP (not “enterprise” until S4) |
| After sustained O* + external use | Widely adopted OSS (evidence: installs, issues, PRs from others — not star vanity alone) |

---

## Sequential campaign map (009→011 pattern)

```text
Campaign COMPILER (Dest 1)
  C0 honesty sync
  C1 MISSION-012  4B graduation     [contractΔ → impl → adversarial certify]
  C2 MISSION-013  plain-language M1 [contract → prototype → certify]
  C3 MISSION-014  model-assisted M2 [contract → prototype → certify]
  || parallel thin: O1–O3 OSS hygiene (no “adoption” claim)

Campaign PLATFORM (Dest 2) — requires Dest 1 exit for Simple Mode
  P1 MISSION-016  live execution    [contract → opt-in prototype → security certify]
  P2 MISSION-017  platform SPECs
  P3 MISSION-018  vertical slice    [prototype → certify]
  P4 optional benchmark

Campaign SAST (Dest 3) — requires S0 ADR; Boss places after platform
  S1–S3 scanner MVP                 [contract → prototype → certify]
  S4 enterprise packaging

Campaign ADOPTION (Dest 4) — continuous; never a fake “CLEAN” exit
  O4–O5 + measure external contribution
```

**Heal-loop policy (carry from 009–011):** max 3 adversarial/heal cycles per mission; merge only after independent review + owner OAR; no auto-merge; exact-baseline worktree launch; ask before push/visibility/site deploy.

---

## Pre-flight conflicts (for SDD)

1. **OAR-005 vs Phase 4B language:** 011 certified a *narrow* boundary; full `MISSION_SEQUENCE_V1` 011 bar is only partially met. C1 must not pretend 011 already exited full 4B.  
2. **Maturity map contradiction:** map still says headless loop `NOT_STARTED`. C0 is mandatory before loud claims.  
3. **SAST vs DFR-010:** sequential Dest 3 needs explicit owner override of “after Phase 9” deferral.  
4. **OSS last vs OSS parallel:** pure serialization delays zero-cost honesty fixes in README/releases.

---

## What this document does **not** authorize

- No mission launch, merge, tag move, PyPI publish, mash-site push, or visibility change.  
- No invention of enterprise SAST tenure or adoption metrics.  
- Next action for execution: Boss authorizes **Campaign COMPILER** (C0–C1 first) under SDD with exact baseline `9d7321c`.
