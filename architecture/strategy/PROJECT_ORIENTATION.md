# PromptRig — where you are

**Date:** 2026-08-29. Laptop `main` is ahead of `origin/main`. Do not push unless you say to.

Open the picture beside chat: Cursor canvas `promptrig-project-map.canvas.tsx`.

If this file fights an Accepted OAR or the maturity map, those win.

---

## Picture 1 — one run

```text
want  →  compiler  →  IR  →  fake run  →  score  →  fix
              ↑
         you are here
         (still holes)
```

The right side (fake run / score / fix) already works offline. That loop is CERTIFIED.

The compiler is the weak link. It is PARTIAL. Not CERTIFIED.

---

## Picture 2 — the road (phases)

Phases are “what has to finish first.” Not mission numbers.

```text
1 done → 2 done → 3 done → 4 done → [ 4B YOU ARE HERE ] → 5 → 6 → 7 → 8 Simple Mode → 9
```

- **4B** = remaining headless engineering the product consumes (product eval bar implemented; 008 join remaining). You live here.
- **8** = Simple Mode (the easy UI). Later. Needs remaining 4B engineering plus owner Accept first. Independent review is not a gate. The UI must not own semantics.

---

## Picture 3 — what sits in what

```text
Phase 4B  (you live here)
├── Fake closed loop ........ DONE / CERTIFIED  (offline fake only)
└── Compiler ................ NOT DONE / PARTIAL
      ├── Jobs 016–021 ...... done
      ├── Job 022 ........... done  (questions 3, 5, 10; 4/7/8/9 locked)
      ├── Job 023 ........... done  (numbered + constraints map; Goal already mapped)
      ├── Job 024 ........... done  (remaining 4B inventory; not CERTIFIED)
      ├── Job 025 ........... done  (same-host PARTIAL slice review; not CERTIFIED)
      ├── Job 026 ........... in    (independent-person review pack; OAR-020 Ready; not CERTIFIED)
      ├── Job 027 ........... in    (eval/repair product bar; OAR-021 Ready; not CERTIFIED)
      ├── Job 028 ........... in    (skip-cert law; OAR-022 Ready; peer review is not a gate)
      ├── M1 typing ......... in   (strict prose now compiles SUCCESS for valid grammar)
      └── M2 suggestions .... fake helper only (no live model)

Phase 8  (later)
└── M3 Simple Mode .......... not started
```

Read it as boxes inside boxes:

- **Phase** = neighborhood
- **Mission / job** = a chunk of work in that neighborhood
- **M1 / M2 / M3** = how a person types, not a job number

M3 is not “the next mission.” It is a later neighborhood.

---

## Picture 4 — the ten compiler questions

All ten are decided on paper. Only some are in the engine.

```text
021 (done)                 022 (done)
---------                  --------------
1 digest      in           3 who-may-approve     IN (if unclear → blocked)
2 optional    in           5 exact version       IN (keep 0.1.0-draft)
6 notes       in           10 structured notes   IN

                           4 aliases             LOCKED (do not merge ids)
                           7 PRS language        LOCKED (stay parked)
                           8 continue-state      LOCKED (no IR blob)
                           9 thinking knobs      LOCKED (no IR knobs)
```

After 028 the compiler is still PARTIAL. Numbered / constraint prose is mapped (OAR-017 Accepted 2026-08-24). Remaining 4B blockers are inventoried (OAR-018 Accepted 2026-08-28). Same-host PARTIAL-slice review is recorded (OAR-019 Accepted 2026-08-28). Independent-person review pack is Ready (OAR-020 Ready, not Accepted). Skip-cert law is Ready (OAR-022 Ready, not Accepted): peer review is not a Phase 5–9 gate. Product eval bar is implemented (MISSION-027 / OAR-021 Ready; product surface not CERTIFIED). Remaining 4B engineering is the 008 join. Not CERTIFIED.

---

## Short answers

**Where am I?** Phase 4B. Last closed Accepted job: 025 (OAR-019 Accepted 2026-08-28). Last honesty job: 026 (OAR-020 Ready, not Accepted). Product eval bar: 027 (OAR-021 Ready; product surface not CERTIFIED). Skip-cert law: 028 (OAR-022 Ready, not Accepted). Compiler still PARTIAL.

**Is the product done?** No. Offline fake loop works. Compiler does not.

**Should I start Simple Mode now?** No. That is Phase 8. Remaining compiler work (008 join, owner Accept) is still inside Phase 4B. Independent review is not a gate. The UI must not own semantics.

**Can I push origin/main?** No, unless you explicitly ask.

---

## If you want the long files

- Road: `architecture/strategy/ROADMAP_V1.md`
- Done-or-not: `architecture/strategy/CAPABILITY_MATURITY_MAP.md`
- Questions: `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md`
- Last accept: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-019.md`
- Open job until Accepted: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-020.md`
- Product eval bar until Accepted: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-021.md`
- Skip-cert law until Accepted: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-022.md`
- 027 note: `architecture/mission-027-certification/README.md`
- Prior accept: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-018.md`
- 028 note: `architecture/mission-028-certification/README.md`
- 027 spec: `docs/superpowers/specs/2026-08-28-mission-027-eval-repair-product-design.md`
- 027 plan: `docs/superpowers/plans/2026-08-28-mission-027-eval-repair-product.md`
- 026 spec: `docs/superpowers/specs/2026-08-28-mission-026-independent-review-pack-design.md`
- 026 plan: `docs/superpowers/plans/2026-08-28-mission-026-independent-review-pack.md`
- 025 spec: `docs/superpowers/specs/2026-08-28-mission-025-partial-slice-review-design.md`
- 025 plan: `docs/superpowers/plans/2026-08-28-mission-025-partial-slice-review.md`
- 024 spec: `docs/superpowers/specs/2026-08-24-mission-024-4b-honesty-design.md`
- 024 plan: `docs/superpowers/plans/2026-08-24-mission-024-4b-honesty.md`
- 023 spec: `docs/superpowers/specs/2026-08-24-mission-023-plain-language-ir-mapping-design.md`
- 023 plan: `docs/superpowers/plans/2026-08-24-mission-023-plain-language-ir-mapping.md`
- 022 spec: `docs/superpowers/specs/2026-08-23-mission-022-008-remaining-oq-design.md`
- 022 plan: `docs/superpowers/plans/2026-08-23-mission-022-008-remaining-oq-implementation.md`
