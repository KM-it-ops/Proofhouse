# Compatibility promise

- Internal APIs may change before 1.0.
- Public library, CLI, schema, diagnostic, adapter, and artifact contracts are versioned beginning with 0.1.0.
- Breaking public changes require release notes, a migration path, and a version change appropriate to pre-1.0 semantic versioning.
- Experimental APIs are explicitly marked and excluded from stability guarantees.
- Stable compatibility is mandatory by 1.x.
- Unsupported semantics are never silently ignored.
- Providers are never silently downgraded.
- User intent is never silently mutated.
- Diagnostics are immutable once emitted; corrections create a new result.
- Traceability from source IR through passes and artifacts is preserved.
- Readers reject unknown major contract versions. Minor-version extensions require declared compatibility behavior.
- Automatic IR migration is opt-in and emits a provenance record; compilation never migrates silently.
