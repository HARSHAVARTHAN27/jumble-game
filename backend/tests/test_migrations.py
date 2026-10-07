"""Migration validation and startup behavior; no live database access."""
import asyncio
import traceback

import psycopg
import pytest

from app import main
from app.config import env_bool
from app.migrations import MigrationError, load_migrations, pending_migrations, run_migrations
from tests.fakes import Database


def migration_file(directory, name="0001_test.sql", sql="SELECT 1;\n"):
    path = directory / name
    path.write_text(sql, encoding="utf-8")
    return path


def test_checksum_survives_windows_line_endings_and_bom(tmp_path):
    path = migration_file(tmp_path)
    original = load_migrations(tmp_path)[0]
    path.write_bytes(b"\xef\xbb\xbfSELECT 1;\r\n")
    assert load_migrations(tmp_path)[0].checksum == original.checksum


@pytest.mark.parametrize("filename", ["test.sql", "0000_test.sql", "0001_Test.sql"])
def test_invalid_filename_stops_before_connection(tmp_path, filename, monkeypatch):
    migration_file(tmp_path, filename)
    monkeypatch.setattr(psycopg, "connect", lambda **kwargs: pytest.fail("Must validate files before connecting"))
    with pytest.raises(MigrationError):
        run_migrations("postgresql://localhost/test", tmp_path)


def test_duplicate_empty_and_missing_migrations_rejected(tmp_path):
    with pytest.raises(MigrationError, match="No SQL migrations"):
        load_migrations(tmp_path)
    first = migration_file(tmp_path)
    second = migration_file(tmp_path, "0001_duplicate.sql")
    with pytest.raises(MigrationError, match="unique"):
        load_migrations(tmp_path)
    second.unlink()
    first.write_text(" ", encoding="utf-8")
    with pytest.raises(MigrationError, match="empty"):
        load_migrations(tmp_path)


def test_applied_files_must_match_and_new_versions_must_follow_history(tmp_path):
    migration_file(tmp_path)
    migration_file(tmp_path, "0002_next.sql")
    migrations = load_migrations(tmp_path)
    history = [(m.version, m.name, m.checksum) for m in migrations]
    assert pending_migrations(migrations, history) == []
    assert pending_migrations(migrations, history[:1]) == migrations[1:]
    with pytest.raises(MigrationError, match="precedes"):
        pending_migrations(migrations, history[1:])
    with pytest.raises(MigrationError, match="missing from this release"):
        pending_migrations(migrations[:1], history)
    with pytest.raises(MigrationError, match="has changed"):
        pending_migrations(migrations, [(1, migrations[0].name, "different")])


@pytest.mark.parametrize("url", ["", " ", "https://not-a-database.example", "postgresql://host/db?unknown_parameter=hidden"])
def test_bad_configuration_never_connects_or_exposes_credentials(url, monkeypatch):
    monkeypatch.setattr(psycopg, "connect", lambda **kwargs: pytest.fail("Must not connect"))
    with pytest.raises(MigrationError) as error:
        run_migrations(url)
    assert "hidden" not in str(error.value)


def test_connection_error_is_redacted_including_traceback(monkeypatch):
    def fail(**kwargs):
        raise psycopg.OperationalError("private-password and private-host from libpq")
    monkeypatch.setattr(psycopg, "connect", fail)
    url = "postgresql://postgres:private-password@private-host/postgres"
    with pytest.raises(MigrationError) as error:
        run_migrations(url)
    rendered = "".join(traceback.format_exception(error.value))
    assert "private-password" not in rendered
    assert "private-host" not in rendered
    assert "connecting to PostgreSQL" in str(error.value)


def test_bool_defaults_enabled_and_rejects_typo(monkeypatch):
    monkeypatch.delenv("AUTO_MIGRATE", raising=False)
    assert env_bool("AUTO_MIGRATE", True)
    monkeypatch.setenv("AUTO_MIGRATE", "false")
    assert not env_bool("AUTO_MIGRATE", True)
    monkeypatch.setenv("AUTO_MIGRATE", "fales")
    with pytest.raises(ValueError, match="true or false"):
        env_bool("AUTO_MIGRATE", True)


def test_migrations_finish_before_startup_reads(monkeypatch, capsys):
    events = []
    db = Database()
    original_from = db.from_
    def read(table):
        assert events[0] == "migrations"
        events.append("read")
        return original_from(table)
    db.from_ = read
    def migrate(url):
        assert url == "configured"
        events.append("migrations")
        return ["0001_foundation.sql", "0002_gameplay.sql"]
    monkeypatch.setattr(main, "supabase", db)
    monkeypatch.setattr(main, "run_migrations", migrate)
    monkeypatch.setattr(main.settings, "AUTO_MIGRATE", True)
    monkeypatch.setattr(main.settings, "DATABASE_URL", "configured")
    asyncio.run(main.startup())
    assert events[1] == "read"
    assert main.app.state.database_status == "ready"
    assert "0002_gameplay.sql" in capsys.readouterr().out


def test_failed_migration_prevents_api_lifespan_and_timer(monkeypatch):
    def fail(url):
        raise MigrationError("Database migration failed.")
    async def worker():
        pytest.fail("Timer must not start after failed setup")
    monkeypatch.setattr(main.settings, "AUTO_MIGRATE", True)
    monkeypatch.setattr(main, "run_migrations", fail)
    monkeypatch.setattr(main, "deadline_worker", worker)
    monkeypatch.setattr(main, "supabase", None)
    async def start():
        async with main.lifespan(main.app):
            pytest.fail("API must not start after failed setup")
    with pytest.raises(MigrationError):
        asyncio.run(start())


def test_disabled_migrations_keep_manual_startup(monkeypatch):
    monkeypatch.setattr(main.settings, "AUTO_MIGRATE", False)
    monkeypatch.setattr(main.settings, "DATABASE_URL", "")
    monkeypatch.setattr(main, "supabase", Database())
    monkeypatch.setattr(main, "run_migrations", lambda url: pytest.fail("Manual mode must not migrate"))
    asyncio.run(main.startup())
    assert main.app.state.database_status == "ready"
