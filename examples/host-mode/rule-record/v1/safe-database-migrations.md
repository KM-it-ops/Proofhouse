# Safe Postgres database migrations

Use this when you write, review, or run SQL migrations for a production Postgres app. Goal: no long locks, no silent data loss, and a clear rollback path.

## Before you touch SQL

1. Read how this repo names migrations, runs them, and connects to prod-like data.
2. Estimate table size and peak traffic; if a step could lock a hot table for more than a few seconds, split the work (expand/contract, batches, concurrent indexes).
3. Never ship a migration without a tested **down** migration (or an explicit, documented rollback script).

## Golden rules

**Always**

1. One logical change per migration file (schema *or* data backfill, not both).
2. Use **expand/contract** for renames and column drops: add new → backfill → switch reads/writes → drop old.
3. Add nullable columns first; backfill in batches; then add `NOT NULL` and constraints in a later migration.
4. Create indexes **concurrently** on large tables (`CREATE INDEX CONCURRENTLY`); never block writes with a plain `CREATE INDEX` on prod-sized tables.
5. Set `lock_timeout` and `statement_timeout` in migration sessions when your runner allows it.
6. Test the **up** and **down** on a copy with production-like row counts and indexes.

**Never**

1. `ALTER TABLE ... RENAME COLUMN` or `DROP COLUMN` in one step while app code still reads the old name.
2. `ADD COLUMN ... NOT NULL DEFAULT <constant>` on a huge table in Postgres versions that rewrite the whole table (prefer: add nullable → backfill → set default → set NOT NULL).
3. Mix heavy DML (mass `UPDATE`/`DELETE`) with DDL in the same migration.
4. Run `CREATE INDEX` (non-concurrent) on a large live table during peak traffic.
5. Leave a migration running unbounded; know how to cancel safely.

## Expand/contract (renames and drops)

**Wrong (one deploy, data loss risk):**

```sql
ALTER TABLE orders RENAME COLUMN total_cents TO amount_cents;
```

**Right (three migrations minimum):**

```sql
-- Migration 1 (expand): add new column, dual-write in app
ALTER TABLE orders ADD COLUMN amount_cents bigint;
UPDATE orders SET amount_cents = total_cents WHERE amount_cents IS NULL;
```

```sql
-- Migration 2 (switch): app reads/writes amount_cents only (deploy app first)
-- Migration 3 (contract): drop old column after traffic is clean
ALTER TABLE orders DROP COLUMN total_cents;
```

## Adding columns with defaults

**Wrong on a large table:**

```sql
ALTER TABLE users ADD COLUMN status text NOT NULL DEFAULT 'active';
```

**Right:**

```sql
ALTER TABLE users ADD COLUMN status text;
-- backfill in batches (separate migration or job), then:
ALTER TABLE users ALTER COLUMN status SET DEFAULT 'active';
UPDATE users SET status = 'active' WHERE status IS NULL; -- batched in app/job
ALTER TABLE users ALTER COLUMN status SET NOT NULL;
```

## Indexes

**Wrong:**

```sql
CREATE INDEX idx_orders_user_id ON orders (user_id);
```

**Right:**

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_id ON orders (user_id);
-- CONCURRENTLY cannot run inside a transaction block in many runners; use a dedicated migration.
```

## Backfills

- Batch by primary key or indexed range: `WHERE id > $last AND id <= $last + 5000`.
- Commit between batches; avoid one transaction that touches millions of rows.
- Make backfills **idempotent** (`WHERE new_col IS NULL`).
- Log progress; feature-flag or throttle if needed.

## Schema vs data

| Do in schema migration | Do in a separate job/migration |
|------------------------|--------------------------------|
| `ADD COLUMN`, `CREATE INDEX CONCURRENTLY`, constraints after backfill | Mass `UPDATE`, deduplication, backfill loops |

## Rollback

Every migration file must include **Down** (or linked rollback) that reverses **expand** steps safely. Do not write a down that drops data you cannot restore unless the team explicitly accepts that.

## Migration running too long

1. Check `pg_stat_activity` for `wait_event_type`, `wait_event`, and `query`.
2. If safe: `SELECT pg_cancel_backend(pid);` for the session running the migration.
3. If cancel fails and the statement is stuck on a lock: escalate; `pg_terminate_backend` only with ops approval.
4. For `CREATE INDEX CONCURRENTLY` failures: check `pg_index` / invalid indexes; `DROP INDEX CONCURRENTLY` and retry in a new migration.
5. Document what ran, what was partial, and the recovery migration before merging again.

## Review checklist (before merge)

- [ ] One concern per file; down migration exists and was tested
- [ ] No rename/drop without expand/contract plan
- [ ] Large indexes use `CONCURRENTLY`
- [ ] No full-table rewrite from `NOT NULL DEFAULT` on big tables
- [ ] Backfills batched and idempotent
- [ ] Tested on prod-sized copy; lock risk called out in PR description
