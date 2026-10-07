"""Apply trusted, versioned SQL before the API accepts traffic.

The migration connection is separate from the application's PostgREST client.
No credentials, database error details, or SQL contents are included in errors.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re

import psycopg
from psycopg.conninfo import conninfo_to_dict


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "sql" / "migrations"
LOCK_ID = int.from_bytes(b"JUMBLEDB", "big")
FILENAME = re.compile(r"(?P<version>[0-9]{4})_[a-z0-9_]+\.sql")


class MigrationError(RuntimeError):
    """Safe to include in startup logs without disclosing connection details."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    checksum: str
    sql: str


def load_migrations(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    migrations = []
    versions = set()
    try:
        for path in sorted(directory.glob("*.sql")):
            match = FILENAME.fullmatch(path.name)
            if not match:
                raise MigrationError("Migration filenames must use NNNN_lowercase_name.sql.")
            version = int(match["version"])
            if version < 1 or version in versions:
                raise MigrationError("Migration versions must be unique positive numbers.")
            # Normalize Windows line endings and an optional UTF-8 BOM before hashing.
            sql = path.read_text(encoding="utf-8-sig")
            if not sql.strip():
                raise MigrationError(f"Migration {path.name} is empty.")
            versions.add(version)
            migrations.append(Migration(version, path.name, sha256(sql.encode("utf-8")).hexdigest(), sql))
    except (OSError, UnicodeError):
        raise MigrationError("Unable to read the SQL migration files. Check the backend installation.") from None
    if not migrations:
        raise MigrationError("No SQL migrations found. Include backend/sql/migrations in the deployment.")
    return migrations


def pending_migrations(migrations: list[Migration], history: list[tuple]) -> list[Migration]:
    by_version = {migration.version: migration for migration in migrations}
    applied = set()
    for version, name, checksum in history:
        migration = by_version.get(version)
        if migration is None:
            raise MigrationError("The database contains a migration missing from this release. Deploy the complete migration history.")
        if (migration.name, migration.checksum) != (name, checksum):
            raise MigrationError(f"Applied migration {migration.name} has changed. Restore it and add a new migration instead.")
        applied.add(version)
    pending = [migration for migration in migrations if migration.version not in applied]
    if applied and any(migration.version <= max(applied) for migration in pending):
        raise MigrationError("A pending migration precedes the applied history. Add changes with a new, higher version.")
    return pending


def run_migrations(database_url: str, directory: Path = MIGRATIONS_DIR) -> list[str]:
    if not database_url.strip():
        raise MigrationError(
            "AUTO_MIGRATE is enabled but DATABASE_URL is missing. Set DATABASE_URL in backend/.env "
            "to this project's Supabase PostgreSQL direct or session-pooler connection string. "
            "Use AUTO_MIGRATE=false only when managing SQL manually."
        )
    if not database_url.strip().startswith(("postgres://", "postgresql://")):
        raise MigrationError("DATABASE_URL must be a PostgreSQL connection URL from Supabase Connect, not an API URL or key.")
    try:
        parameters = conninfo_to_dict(database_url.strip())
    except psycopg.Error:
        raise MigrationError("DATABASE_URL is invalid. Copy the PostgreSQL connection URL and URL-encode reserved password characters.") from None
    parameters.setdefault("sslmode", "require")
    parameters["connect_timeout"] = 10
    migrations = load_migrations(directory)
    applied = []
    stage = "connecting to PostgreSQL"
    try:
        with psycopg.connect(**parameters, autocommit=True, prepare_threshold=None) as connection:
            with connection.transaction():
                # READ COMMITTED lets a waiting startup see history committed by its predecessor.
                connection.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
                connection.execute("SET LOCAL statement_timeout = '120s'")
                connection.execute("SET LOCAL lock_timeout = '30s'")
                stage = "acquiring the migration lock"
                connection.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_ID,))
                stage = "checking migration history"
                connection.execute("CREATE SCHEMA IF NOT EXISTS jumble_internal")
                connection.execute("REVOKE ALL ON SCHEMA jumble_internal FROM PUBLIC, anon, authenticated, service_role")
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS jumble_internal.schema_migrations (
                        version integer PRIMARY KEY,
                        name text NOT NULL,
                        checksum text NOT NULL,
                        applied_at timestamptz NOT NULL DEFAULT now()
                    )
                """)
                connection.execute("REVOKE ALL ON jumble_internal.schema_migrations FROM PUBLIC, anon, authenticated, service_role")
                history = connection.execute(
                    "SELECT version, name, checksum FROM jumble_internal.schema_migrations ORDER BY version"
                ).fetchall()
                for migration in pending_migrations(migrations, history):
                    stage = f"applying {migration.name}"
                    # Migration files are trusted release artifacts; never accept SQL from HTTP.
                    # They must not contain transaction control or nontransactional DDL.
                    connection.execute(migration.sql, prepare=False)
                    connection.execute(
                        "INSERT INTO jumble_internal.schema_migrations (version, name, checksum) VALUES (%s, %s, %s)",
                        (migration.version, migration.name, migration.checksum),
                    )
                    applied.append(migration.name)
                if applied:
                    connection.execute("NOTIFY pgrst, 'reload schema'")
                stage = "committing database migrations"
    except psycopg.Error as error:
        code = error.sqlstate
        suffix = f" (SQLSTATE {code})" if code and re.fullmatch(r"[A-Z0-9]{5}", code) else ""
        raise MigrationError(
            f"Database setup failed while {stage}{suffix}. Startup stopped. "
            "Check database connectivity, permissions, and migration compatibility; then restart."
        ) from None
    return applied
