# Decision records

Public, self-contained records of decisions that shape what Proofhouse promises. Each says what was decided, why, and what it costs. Earlier internal decision ids (OAR-*, ADR-*, MISSION-*) that appear in older history are not published; where one still matters, a record here states its substance.

To propose a change: open an issue describing the problem and the option you prefer. A change that alters a public contract (a record schema, a CLI's meaning, what a PASS means) lands with a new or updated record in this directory in the same pull request.

| # | Decision | Status |
|---|---|---|
| [0001](0001-local-first-evidence-workspace.md) | Proofhouse is a local-first prompt revision and evidence workspace | accepted 2026-09-21 |
| [0002](0002-what-pass-means.md) | A PASS means every declared check passed and every accepted constraint has evidence | accepted 2026-09-21 |
| [0003](0003-imported-observations-and-repair.md) | Imported observations are bound to a candidate and are never repaired against | accepted 2026-09-21 |
| [0004](0004-model-note-provenance.md) | Model notes carry source and evidence labels; efficiency advice never removes a required gate | accepted 2026-09-21 |
| [0005](0005-live-requests-carry-every-mandatory-field.md) | Live requests carry every mandatory IR field or refuse before sending | accepted 2026-09-21 |
