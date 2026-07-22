# Library and CLI contract

## Public library

Compiler Core v0.1 exposes equivalent operations for `compile`, `validate`, `inspect`, `list_adapters`, and `doctor`. Operations accept typed values/options and return typed result envelopes; expected user errors are values containing diagnostics, not process exits.

The public library owns all parsing, normalization, validation, compilation, capability resolution, inspection, and environment checks. The CLI owns argument parsing, file/stdin/stdout handling, envelope serialization, and exit-code mapping only.

## Required CLI

- `promptrig compile INPUT [--adapter ID] [--output DIR] [--json]`
- `promptrig validate INPUT [--json]`
- `promptrig inspect INPUT [--json]`
- `promptrig adapters [--json]`
- `promptrig doctor [--json]`

`evaluate`, `repair`, `explain`, and `schema` are deferred from v0.1. Existing `report`, `loadouts`, `compile-loadout`, and `generate` commands remain supported legacy PromptOps surfaces and MUST NOT be reimplemented inside Compiler Core.

## JSON envelope

With `--json`, stdout contains exactly one JSON object with `contract_version`, `command`, `status`, `data`, and `diagnostics`. Logs and progress go to stderr. Paths in semantic data use portable forward-slash logical paths; OS-native paths may appear only in clearly identified environment metadata.

## Exit codes

| Code | Meaning |
|---:|---|
| 0 | Success, including warning-only results |
| 2 | CLI usage error |
| 3 | Input/schema/semantic validation failure |
| 4 | Required capability unsupported |
| 5 | Compilation or artifact failure |
| 6 | Adapter contract/load failure |
| 7 | Environment/configuration failure |
| 8 | Unexpected internal error |

The highest-priority applicable code wins; diagnostics preserve all detected failures. Exit-code meanings are stable within the 0.x public contract.

## Installation and platforms

Wheels and source installs MUST be tested on supported Python versions for Windows, Linux, and macOS. Tests invoke both `python -m promptrig.cli` and the installed `promptrig` script. Offline commands MUST not read provider credentials or access the network.

## Parity

For each command fixture, CLI JSON after removal of declared transport metadata MUST deep-equal serialization of the corresponding library result. The required cases are enumerated in [LIBRARY_CLI_PARITY_MATRIX.json](LIBRARY_CLI_PARITY_MATRIX.json).
