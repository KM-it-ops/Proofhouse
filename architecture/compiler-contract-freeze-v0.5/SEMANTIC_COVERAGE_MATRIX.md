# Semantic coverage matrix — PromptRig IR v0.1

**Recovery status:** MISSION-006 correction. This matrix classifies the frozen
schema; it does not alter it. A source pointer, source digest, or a top-level
section label is not semantic preservation.

## Successful-artifact rule

Every populated frozen IR semantic leaf receives exactly one machine-readable
`semantic_dispositions` entry. In v0.1, successful artifacts retain the exact
canonical IR value at the matching path under
`/promptrig_semantic_context/ir`; the disposition is `retained` and identifies
that artifact path. This is an authorized deterministic compiler sidecar,
separate from provider-native request fields. It causes a semantic IR change to
change artifact bytes and SHA-256 even where the selected provider has no
native representation.

Provider-native fields may also be lowered by an adapter, but provenance does
not claim that native lowering substitutes for the complete semantic context.
Security/privacy policy prose is never retained as successful deployable
meaning: populated policy blocks fail closed before artifact production.

| IR path(s) | Successful disposition | Failure / omission behavior | Evidence |
|---|---|---|---|
| `/spec_version` | `retained` after schema validation | invalid version errors | schema and metamorphic tests |
| `/project/*`, `/objective/*`, `/requirements/*` | `retained`; supported goal/instructions also lower natively | schema-invalid values error | generated semantic metamorphic suite |
| `/input_contracts/*` | `retained` | no silent truncation | generated semantic metamorphic suite |
| `/output_contracts/*` | `retained`; exactly one declared structured contract may lower natively | any length above one errors | four multi-contract regression cases |
| `/behavior/*`, `/knowledge/*`, `/memory/*` | `retained` | schema-invalid values error | generated semantic metamorphic suite |
| `/tools/*`, `/workflow/*`, `/autonomy/*` | `retained`; compatible tool fields may lower natively | declaration or safety conflicts error | semantic, capability, and safety tests |
| `/security/*`, `/privacy/*` | no successful artifact disposition | populated free-text policy blocks fail closed | safety coverage matrix |
| `/provider_requirements/*` | supported decisions retained in context/provenance | required unresolved capability errors; optional unresolved capability creates an `omissions` record and a nondeployable artifact/envelope | capability omission tests |
| `/evaluation/*`, `/deployment/*`, `/assumptions/*`, `/open_questions/*`, `/provenance/*` | `retained` | schema-invalid values error | generated semantic metamorphic suite |

`source_ir_paths` and `semantic_coverage` are the ordered actual IR leaf paths
from `SemanticDisposition.source_path`. Each source path appears exactly once.
Artifact destinations appear only in `SemanticDisposition.artifact_paths`,
under `/promptrig_semantic_context/ir`; they are never represented as source
IR paths or inferred from an IR digest/all-pointer inventory.
