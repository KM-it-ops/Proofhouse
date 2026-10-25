# Safe Postgres database migrations

Use when you write, review, or apply SQL migrations for production Postgres. Goals: short locks, no data loss, tested rollback.

## Start here (every task)

1. Find this repo's migration runner, naming, and how to run against a **prod-sized** database copy.
2. If a step might hold `ACCESS EXCLUSIVE` or rewrite a large heap, split it (expand/contract, batched backfill, `CONCURRENTLY`).
3. Every migration needs a **Down** section (or linked rollback) you have actually executed on the copy.

Set session guards when the runner allows:

```sql
SET lock_timeout = '5s';
SET statement_timeout = '0'; -- or a high cap for index builds; never unbounded on ad-hoc fixes
```

## Always / never

**Always**

1. One logical change per file: **either** DDL **or** a bounded data backfill—not both.
2. Renames and drops use **expand → deploy app → contract** (see below).
3. Add indexes on large tables with `CREATE INDEX CONCURRENTLY` (and `DROP INDEX CONCURRENTLY` when replacing).
4. Add foreign keys as `NOT VALID`, then `VALIDATE CONSTRAINT` in a follow-up step when the table is huge.
5. Backfill in batches with commits between batches; make updates idempotent (`WHERE col IS NULL`).
6. Test **Up** and **Down** on a copy with realistic row counts and indexes.

**Never**

1. Drop or rename a column while any deployed code still reads it.
2. Run a full-table `UPDATE` in the same migration file as `ALTER TABLE ... ADD CONSTRAINT`.
3. Use non-concurrent `CREATE INDEX` on a large hot table in production.
4. Assume `ADD COLUMN ... DEFAULT` is always instant—volatile defaults and some type changes still hurt.
5. Let a stuck migration run without checking locks and having a cancel/escalation plan.

## Expand / contract (rename or drop)

Deploy order matters: **database expand before app switch; database contract after app switch.**

**Wrong (single migration):**

```sql
ALTER TABLE orders RENAME COLUMN total_cents TO amount_cents;
```

**Right (minimum three migrations + two app deploys):**

```sql
-- Up 1 (expand)
ALTER TABLE orders ADD COLUMN amount_cents bigint;
-- batched backfill in a separate data migration or job:
UPDATE orders SET amount_cents = total_cents
WHERE id > $1 AND id <= $2 AND amount_cents IS NULL;
```

Deploy app that writes **both** columns, then reads `amount_cents`. Then:

```sql
-- Up 2 (contract)
ALTER TABLE orders DROP COLUMN total_cents;
```

**Down 2** (before contract is merged): re-add `total_cents` and backfill from `amount_cents` using the same batch pattern—not a blind drop.

## Column defaults and NOT NULL

Postgres 11+: a **constant** `DEFAULT` on `ADD COLUMN` is metadata-only, even with `NOT NULL`. This is fine on a large table:

```sql
ALTER TABLE users ADD COLUMN tier text NOT NULL DEFAULT 'free';
```

**Wrong:** a volatile default (`DEFAULT random()`, `DEFAULT clock_timestamp()`) rewrites the whole table under `ACCESS EXCLUSIVE`. Add the column without a default, set the default for new rows, and backfill old rows in batches.

**Adding `NOT NULL` to an existing column** (a plain `SET NOT NULL` scans the table while holding `ACCESS EXCLUSIVE`):

```sql
ALTER TABLE users ADD CONSTRAINT users_tier_not_null CHECK (tier IS NOT NULL) NOT VALID;
ALTER TABLE users VALIDATE CONSTRAINT users_tier_not_null;  -- scans, but only blocks writes briefly
ALTER TABLE users ALTER COLUMN tier SET NOT NULL;           -- Postgres 12+ reuses the validated CHECK, no scan
ALTER TABLE users DROP CONSTRAINT users_tier_not_null;
```

## Indexes and constraints

**Wrong:**

```sql
CREATE UNIQUE INDEX idx_users_email ON users (email);
```

**Right:**

```sql
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users (email);
```

If a concurrent build fails or is cancelled it leaves an **invalid** index behind, and `IF NOT EXISTS` will then skip it silently: check `pg_index.indisvalid`, drop the invalid index, and rebuild.

Many runners wrap migrations in a transaction; **`CREATE INDEX CONCURRENTLY` cannot run inside a transaction block**—use a dedicated migration file and runner mode that commits per file.

**Large FK add:**

```sql
ALTER TABLE orders ADD CONSTRAINT orders_user_id_fkey
  FOREIGN KEY (user_id) REFERENCES users(id) NOT VALID;
ALTER TABLE orders VALIDATE CONSTRAINT orders_user_id_fkey;
```

## When a migration runs too long

1. `SELECT pid, wait_event_type, wait_event, state, query FROM pg_stat_activity WHERE application_name LIKE '%migrate%';`
2. Try `SELECT pg_cancel_backend(pid);` and re-check.
3. `pg_terminate_backend` only with ops approval if cancel does not free locks.
4. Invalid concurrent index: `SELECT indexrelid::regclass, indisvalid FROM pg_index ...` then `DROP INDEX CONCURRENTLY ...` and fix in a new migration.

## Checklist

- [ ] One concern per file; Down tested on prod-sized copy; expand/contract order in PR
- [ ] Indexes/FKs concurrent or NOT VALID + validate; backfills batched and separate from DDL
- [ ] Lock risk called out for reviewers
