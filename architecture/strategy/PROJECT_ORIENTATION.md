# PromptRig — where you are

**Date:** 2026-08-23. Local `main` is 61 commits ahead of `origin/main`. Do not push `origin/main` unless you say to.

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

- **4B** = harden the headless core. You live here.
- **8** = Simple Mode (the easy UI). Later. Needs a done compiler first.

---

## Picture 3 — what sits in what

```text
Phase 4B  (you live here)
├── Fake closed loop ........ DONE / CERTIFIED  (offline fake only)
└── Compiler ................ NOT DONE / PARTIAL
      ├── Jobs 016–021 ...... done
      ├── Job 022 ........... done  (questions 3, 5, 10; 4/7/8/9 locked)
      ├── M1 typing ......... in   (strict prose; numbered lines still blocked)
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

After 022 the compiler is still PARTIAL. Numbered / constraint prose is still blocked. That is a later job.

---

## Short answers

**Where am I?** Phase 4B. Last closed job: 022 (OAR-016 Ready, not Accepted). Compiler still PARTIAL.

**Is the product done?** No. Offline fake loop works. Compiler does not.

**Should I start Simple Mode now?** No. That is Phase 8. Remaining compiler work (numbered/constraint prose, CERTIFIED, full 008) is still inside Phase 4B.

**Can I push origin/main?** No, unless you explicitly ask.

---

## If you want the long files

- Road: `architecture/strategy/ROADMAP_V1.md`
- Done-or-not: `architecture/strategy/CAPABILITY_MATURITY_MAP.md`
- Questions: `architecture/requirements-compiler-contract-v0.1/OPEN_QUESTIONS.md`
- Last accept: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-015.md`
- 022 Ready (not Accepted): `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-016.md`
- 022 spec: `docs/superpowers/specs/2026-08-23-mission-022-008-remaining-oq-design.md`
- 022 plan: `docs/superpowers/plans/2026-08-23-mission-022-008-remaining-oq-implementation.md`
