# PromptRig — where you are

**Date:** 2026-08-30. Campaign branch ahead of `origin/main`. Do not push `origin/main` unless you say to.

Open the picture beside chat: Cursor canvas `promptrig-project-map.canvas.tsx`.

If this file fights an Accepted OAR or the maturity map, those win.

---

## Picture 1 — one run

```text
want  →  compiler  →  IR  →  fake run  →  score  →  fix
              ↑                              ↑
         PARTIAL                         product bar
         (008 bridged)                   + hosted slice
```

The offline fake loop is CERTIFIED. Product eval/repair bar, 008 bridge, sealed benchmark, stdlib hosted Simple/Developer slice, and MissionRig consume are Accepted (OAR-021 through OAR-029) but mostly **not CERTIFIED** product surfaces. The requirements compiler stays **PARTIAL**.

---

## Picture 2 — the road (phases)

```text
1 done → 2 done → 3 done → 4 done → [ 4B engineering done ] → 5 → 6 → 7 → 8 → 9
```

- **4B** remaining engineering from the remaining-product campaign is **Accepted** (OAR-021–029). Compiler still **PARTIAL**. Not full Phase 4B exit. Not CERTIFIED compiler.
- **8** = broader Simple Mode polish and hosted product hardening. Stdlib slice exists (MISSION-035 / OAR-028 Accepted). Q2 runtime pick is STACK-OWNER-SELECTED — not FastAPI/Next.js.

---

## Picture 3 — what sits in what

```text
Phase 4B  (Accepted engineering; compiler still PARTIAL)
├── Fake closed loop ........ DONE / CERTIFIED  (offline fake only)
├── Product eval bar ........ DONE / Accepted OAR-021 (not CERTIFIED product surface)
├── 008→IR bridge ........... DONE / Accepted OAR-023
├── Live OpenAI ............. DONE / Accepted OAR-025 (opt-in; Q1 unpicked)
├── Sealed benchmark ........ DONE / Accepted OAR-026 (not a published claim)
├── Hosted contracts ........ DONE / Accepted OAR-027
├── Hosted runtime .......... DONE / Accepted OAR-028 (stdlib; not CERTIFIED hosted)
├── MissionRig consume ...... DONE / Accepted OAR-029 (one profile; not CERTIFIED)
└── Compiler ................ PARTIAL (not CERTIFIED)

Phase 8+ (later)
└── FastAPI/Next.js restack, Q1 live, Q4 IR v0.2 schema, CERTIFIED promotion ... not started
```

---

## Picture 4 — the ten compiler questions

All ten are decided on paper. Engine coverage is unchanged from MISSION-022 except numbered/constraint prose maps (OAR-017) and 008 bridge (OAR-023).

---

## Short answers

**Where am I?** Remaining-product campaign Accepted through MISSION-036 (OAR-029 Accepted 2026-08-30). Compiler still PARTIAL.

**Is the product done?** Headless compile-eval-repair, product eval bar, 008 bridge, opt-in live, sealed benchmark, stdlib hosted slice, and MissionRig consume are Accepted. Not CERTIFIED hosted product. Not CERTIFIED compiler. Not a published benchmark claim.

**Should I start Simple Mode now?** Phase 8 stdlib slice exists (OAR-028 Accepted). Q2 pick is STACK-OWNER-SELECTED — do not scaffold FastAPI or Next.js. Do not extend `apps/dashboard` or `apps/promptrig.jsx`. UI must not own semantics.

**Can I push origin/main?** No, unless you explicitly ask.

---

## If you want the long files

- Road: `architecture/strategy/ROADMAP_V1.md`
- Done-or-not: `architecture/strategy/CAPABILITY_MATURITY_MAP.md`
- Questions: `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md`
- Last accept: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-029.md`
- Campaign handoff: `docs/handoffs/2026-08-30-remaining-product-campaign.md`
- Prior accept: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-022.md`
