# Hosted slice v0.1 (MISSION-034)

Contract package for one future Simple Mode + Developer Mode slice on the headless compiler.

**Q2 is unpicked.** This folder is not a hosted implementation. Do not scaffold FastAPI or Next.js from these files. Do not extend `apps/dashboard` or `apps/promptrig.jsx`.

| File | Role |
|---|---|
| `SPEC.md` | Slice boundary, intake, non-claims |
| `OPTIONS.json` | Q2 / identity / persistence options; invalid scaffolding examples |
| `openapi.json` | Generated from `promptrig-compiler` CLI |
| `MODE_PARITY.md` | Same project, same IR digest, both modes |
| `AUTH_TENANCY.md` | Identity, authorization, isolation |
| `PERSISTENCE_RETENTION.md` | Store, export, deletion, retention |
| `THREAT_MODEL.md` | Hosted threats with Q2 still open |
| `ACCESSIBILITY.md` | Nontechnical presentation and a11y gates |
| `FORBIDDEN_SURFACES.md` | Vite/JSX/`simple_mode_ui` |
| `fixtures/` | Mode-parity and fail-closed cases |

Certification note: `architecture/mission-034-certification/README.md`. Owner record: `architecture/OWNER_ACCEPTANCE_RECORDS/OAR-027.md` (Ready, not Accepted).
