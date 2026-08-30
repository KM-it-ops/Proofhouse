# Persistence, retention, export, and deletion

**Status:** Contract only. No product store is implemented. Directory artifacts and browser storage are not product persistence.

## Recommended first store

`PERS-SQLITE-PORTABLE`: a local portable store for closed-alpha. Canonical meaning stays in IR + evidence produced by the compiler. The store holds project records, view preferences, and export packages.

## Rejected inheritance

`PERS-SUPABASE-INHERITED` is explicitly rejected (REJ-001). Supabase may compete later without presumption.

## Retention and deletion

- Export produces a versioned package of IR, evidence, and requirements records the CLI already knows.
- Deletion is user-initiated, complete for that project, and leaves the compiler unable to see the deleted project.
- Retention class is recorded on stored blobs. Opaque provider continuation is not an IR field (MISSION-031 evidence-only recommendation).
- Backup/recovery must restore compiler-visible state, not UI chrome.

## Secrets

Credentials never enter the store as canonical fields. Live credentials stay in caller-supplied env vars at invoke time (MISSION-032). Redact secrets from logs and export packages.
