# Versioned startup migrations

`0001_foundation.sql` and `0002_gameplay.sql` are frozen copies of the existing
foundation and gameplay setup. They can adopt a database that was already set up
manually. Existing records are retained; incompatible legacy data stops setup.

For each future database change, add the next `NNNN_lowercase_name.sql` file.
Never edit, rename, or delete a migration that has been applied. The runner checks
its SHA-256 checksum (normalizing UTF-8 BOMs and line endings), and rejects missing,
modified, duplicate, or out-of-order history. All releases must include the entire
migration directory, even when the database is already initialized.

The runner owns the transaction. Migration files must not include `BEGIN`,
`COMMIT`, `ROLLBACK`, psql commands, or operations that cannot run inside a
transaction (for example `CREATE INDEX CONCURRENTLY`). PL/pgSQL blocks inside
functions and `DO` statements are supported. These files are trusted release
artifacts, never user-submitted SQL.

All pending files and their history entries commit together. A transaction-level
advisory lock serializes startup attempts, including the first creation of the
private `jumble_internal.schema_migrations` table. Database roles exposed through
the application cannot access that table. The runner sends PostgREST a schema
reload notification after applying pending changes.

The legacy SQL files in the parent directory remain an optional manual baseline.
`scripts/build_setup.py` only rebuilds that legacy bundle; it does not create or
update migration files. New features must ship new migrations here.
