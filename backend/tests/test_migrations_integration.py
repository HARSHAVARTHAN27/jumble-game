"""Real PostgreSQL transactions against disposable, loopback-only databases.

Set MIGRATION_TEST_DATABASE_URL to a local PostgreSQL admin database. Each test
creates and drops its own jumble_migration_test_<uuid> database. Supabase's managed
roles and minimal storage/auth tables are provisioned only in this test fixture.
"""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import shutil
from threading import Barrier
from uuid import uuid4
from urllib.parse import urlsplit

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
import pytest
from psycopg.types.json import Jsonb

from app.migrations import MIGRATIONS_DIR, MigrationError, run_migrations


@pytest.fixture(scope="module")
def admin_url():
    url = os.getenv("MIGRATION_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set MIGRATION_TEST_DATABASE_URL to run isolated PostgreSQL integration checks.")
    parameters = conninfo_to_dict(url)
    if parameters.get("host") not in ("localhost", "127.0.0.1", "::1"):
        pytest.fail("Migration integration tests require a loopback database; remote databases are never used.")
    with psycopg.connect(url, autocommit=True, connect_timeout=10) as connection:
        for role in ("anon", "authenticated", "service_role"):
            if not connection.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone():
                connection.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(role)))
    return url


@pytest.fixture
def database_url(admin_url):
    name = "jumble_migration_test_" + uuid4().hex
    url = urlsplit(admin_url)._replace(path='/' + name).geturl()
    with psycopg.connect(admin_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        with psycopg.connect(url, autocommit=True) as connection:
            connection.execute("""
                CREATE SCHEMA storage;
                CREATE TABLE storage.buckets (
                    id text PRIMARY KEY, name text NOT NULL, public boolean DEFAULT false,
                    file_size_limit bigint, allowed_mime_types text[]
                );
                CREATE SCHEMA auth;
                CREATE TABLE auth.users (id uuid PRIMARY KEY, raw_app_meta_data jsonb);
            """)
        yield url
    finally:
        # Only the random database created by this fixture is ever removed.
        with psycopg.connect(admin_url, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.fixture
def migrations(tmp_path):
    for path in MIGRATIONS_DIR.glob("*.sql"):
        shutil.copyfile(path, tmp_path / path.name)
    return tmp_path


def rows(connection, table):
    return connection.execute(sql.SQL("SELECT * FROM {} ORDER BY 1").format(sql.Identifier(*table.split(".")))).fetchall()


def test_fresh_setup_creates_tables_permissions_functions_and_bucket(database_url):
    assert run_migrations(database_url) == ["0001_foundation.sql", "0002_gameplay.sql", "0003_replace_active_game.sql"]
    with psycopg.connect(database_url) as connection:
        assert len(rows(connection, "jumble_internal.schema_migrations")) == 3
        assert len(rows(connection, "public.teams")) == 3
        for name in ("games", "employees", "players", "jumble_content", "jumble_runtime"):
            assert rows(connection, "public." + name) == []
            assert connection.execute("SELECT relrowsecurity FROM pg_class WHERE oid = %s::regclass", ("public." + name,)).fetchone()[0]
        assert connection.execute("SELECT public, file_size_limit FROM storage.buckets WHERE id='jumble-grid'").fetchone() == (False, 5242880)
        assert connection.execute("SELECT has_function_privilege('service_role', 'public.jumble_save_content(uuid,integer,jsonb)', 'EXECUTE')").fetchone()[0]
        assert not connection.execute("SELECT has_function_privilege('anon', 'public.jumble_save_content(uuid,integer,jsonb)', 'EXECUTE')").fetchone()[0]
        for role in ("anon", "authenticated", "service_role"):
            assert not connection.execute("SELECT has_schema_privilege(%s, 'jumble_internal', 'USAGE')", (role,)).fetchone()[0]
            assert not connection.execute("SELECT has_table_privilege(%s, 'jumble_internal.schema_migrations', 'SELECT')", (role,)).fetchone()[0]


def test_existing_manual_database_is_adopted_without_losing_records(database_url):
    with psycopg.connect(database_url, autocommit=True) as connection:
        root = Path(__file__).resolve().parents[1]
        connection.execute((root / 'sql' / 'setup.sql').read_text(encoding='utf-8-sig'), prepare=False)
        connection.execute((root / 'sql' / 'gameplay.sql').read_text(encoding='utf-8-sig'), prepare=False)
        team = connection.execute("SELECT id FROM public.teams ORDER BY slug LIMIT 1").fetchone()[0]
        game = connection.execute("INSERT INTO public.games(title,status) VALUES ('Existing game','lobby') RETURNING id").fetchone()[0]
        employee = connection.execute("INSERT INTO public.employees(name,normalized_name,team_id) VALUES ('Existing Employee','existing employee',%s) RETURNING id", (team,)).fetchone()[0]
        connection.execute("INSERT INTO public.players(game_id,employee_id,team_id,committed_score) VALUES (%s,%s,%s,50)", (game, employee, team))
        connection.execute("INSERT INTO auth.users VALUES (%s, '{\"role\":\"host\"}')", (uuid4(),))
        connection.execute("INSERT INTO public.jumble_content(game_id,document,version) VALUES (%s,'{\"rounds\":[]}',7)", (game,))
        connection.execute("INSERT INTO public.jumble_runtime(game_id,state,version) VALUES (%s,'{\"phase\":\"intro\"}',9)", (game,))
        tables = ['public.' + name for name in ('games', 'teams', 'employees', 'players', 'jumble_content', 'jumble_runtime')] + ['auth.users']
        before = {table: rows(connection, table) for table in tables}
    run_migrations(database_url)
    with psycopg.connect(database_url) as connection:
        before['public.games'] = [row + (None,) for row in before['public.games']]
        assert {table: rows(connection, table) for table in tables} == before
        history = rows(connection, 'jumble_internal.schema_migrations')
    assert run_migrations(database_url) == []
    with psycopg.connect(database_url) as connection:
        assert rows(connection, 'jumble_internal.schema_migrations') == history
        assert {table: rows(connection, table) for table in tables} == before


def test_failed_pending_batch_rolls_back_ddl_data_and_history(database_url, migrations):
    run_migrations(database_url, migrations)
    (migrations / '0004_change.sql').write_text("CREATE TABLE public.test_probe(id integer); UPDATE public.teams SET name='Temporary';", encoding='utf-8')
    (migrations / '0005_fail.sql').write_text("SELECT 1/0;", encoding='utf-8')
    with pytest.raises(MigrationError, match='0005_fail.sql'):
        run_migrations(database_url, migrations)
    with psycopg.connect(database_url) as connection:
        assert connection.execute("SELECT to_regclass('public.test_probe')").fetchone()[0] is None
        assert len(rows(connection, 'jumble_internal.schema_migrations')) == 3
        assert not connection.execute("SELECT 1 FROM public.teams WHERE name='Temporary'").fetchone()


def test_failed_first_setup_leaves_no_partial_application_schema(database_url, migrations):
    (migrations / '0004_fail.sql').write_text("SELECT 1/0;", encoding='utf-8')
    with pytest.raises(MigrationError):
        run_migrations(database_url, migrations)
    with psycopg.connect(database_url) as connection:
        assert connection.execute("SELECT to_regclass('public.games'), to_regclass('jumble_internal.schema_migrations')").fetchone() == (None, None)
        assert rows(connection, 'storage.buckets') == []


def test_concurrent_starts_apply_each_migration_once(database_url, migrations):
    (migrations / '0004_probe.sql').write_text("SELECT pg_sleep(0.3); CREATE TABLE public.test_probe(id integer PRIMARY KEY); INSERT INTO public.test_probe VALUES (1);", encoding='utf-8')
    barrier = Barrier(2)
    def start():
        barrier.wait(timeout=10)
        return run_migrations(database_url, migrations)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(start) for _ in range(2)]
        results = [future.result(timeout=30) for future in futures]
    assert sorted(map(len, results)) == [0, 4]
    with psycopg.connect(database_url) as connection:
        assert rows(connection, 'public.test_probe') == [(1,)]
        assert len(rows(connection, 'jumble_internal.schema_migrations')) == 4


def test_edited_applied_migration_stops_before_pending_changes(database_url, migrations):
    run_migrations(database_url, migrations)
    with (migrations / '0001_foundation.sql').open('a', encoding='utf-8') as file:
        file.write('\n-- Edited history\n')
    (migrations / '0004_probe.sql').write_text('CREATE TABLE public.test_probe(id integer);', encoding='utf-8')
    with pytest.raises(MigrationError, match='has changed'):
        run_migrations(database_url, migrations)
    with psycopg.connect(database_url) as connection:
        assert connection.execute("SELECT to_regclass('public.test_probe')").fetchone()[0] is None
        assert len(rows(connection, 'jumble_internal.schema_migrations')) == 3


def test_incompatible_legacy_data_is_not_deleted(database_url):
    root = Path(__file__).resolve().parents[1]
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute((root / 'sql' / 'setup.sql').read_text(encoding='utf-8-sig'), prepare=False)
        team = connection.execute("INSERT INTO public.teams(name,slug) VALUES ('Legacy team','legacy') RETURNING id").fetchone()[0]
        connection.execute("INSERT INTO public.employees(name,normalized_name,team_id) VALUES ('Keep me','keep me',%s)", (team,))
        before = rows(connection, 'public.employees')
    with pytest.raises(MigrationError, match='0001_foundation.sql'):
        run_migrations(database_url)
    with psycopg.connect(database_url) as connection:
        assert rows(connection, 'public.employees') == before
        assert len(rows(connection, 'public.teams')) == 4
        assert connection.execute("SELECT to_regclass('jumble_internal.schema_migrations')").fetchone()[0] is None


@pytest.mark.parametrize('status', [None, 'lobby', 'playing', 'paused'])
def test_replace_creates_fresh_lobby_and_preserves_history(database_url, status):
    run_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as connection:
        old = None
        if status:
            old = connection.execute("INSERT INTO public.games(title,status) VALUES ('Old session',%s) RETURNING id", (status,)).fetchone()[0]
            team = rows(connection, 'public.teams')[0][0]
            employee = connection.execute("INSERT INTO public.employees(name,normalized_name,team_id) VALUES ('Keep','keep',%s) RETURNING id", (team,)).fetchone()[0]
            connection.execute("INSERT INTO public.players(game_id,employee_id,team_id,committed_score) VALUES (%s,%s,%s,40)", (old, employee, team))
            state = {'phase':'active', 'scores':{str(team):40}, 'submissions':[{'answer':'pending'}], 'deadline':100}
            connection.execute("INSERT INTO public.jumble_runtime VALUES (%s,%s,7)", (old, Jsonb(state)))
            connection.execute("INSERT INTO public.jumble_content VALUES (%s,'{\"rounds\":[]}',4)", (old,))
            preserved = {table: rows(connection, table) for table in ('public.players','public.employees','public.teams','public.jumble_content')}
        created = connection.execute("SELECT public.jumble_create_game('Fresh',true)").fetchone()[0]
        assert created['status'] == 'lobby' and created['current_round'] == 0 and created['current_question'] == 0
        assert created['ended_reason'] is None and created['started_at'] is None
        for table in ('players','jumble_content','jumble_runtime'):
            assert not connection.execute(sql.SQL('SELECT 1 FROM public.{} WHERE game_id=%s').format(sql.Identifier(table)), (created['id'],)).fetchone()
        if old:
            assert created['id'] != str(old)
            assert connection.execute("SELECT status,ended_reason,completed_at IS NOT NULL FROM public.games WHERE id=%s", (old,)).fetchone() == ('completed','replaced',True)
            assert {table: rows(connection, table) for table in preserved} == preserved
            runtime, version = connection.execute("SELECT state,version FROM public.jumble_runtime WHERE game_id=%s", (old,)).fetchone()
            assert runtime == {**state,'phase':'completed','endedReason':'replaced'} and version == 8
            # Both stale and current-version writes are refused after closure.
            for expected in (7,8):
                assert connection.execute("SELECT public.jumble_write_runtime(%s,%s,%s,'playing',1,1)", (old,expected,Jsonb(state))).fetchone() == (False,)
            assert connection.execute("SELECT public.jumble_save_content(%s,4,'{}')", (old,)).fetchone() == (False,)
        assert connection.execute("SELECT count(*) FROM public.games WHERE status IN ('lobby','playing','paused')").fetchone() == (1,)
        for role in ('anon','authenticated'):
            assert not connection.execute("SELECT has_function_privilege(%s,'public.jumble_create_game(text,boolean)','EXECUTE')", (role,)).fetchone()[0]


def test_replacement_failure_rolls_back_old_session_and_runtime(database_url):
    run_migrations(database_url)
    with psycopg.connect(database_url, autocommit=True) as connection:
        old = connection.execute("SELECT public.jumble_create_game('Keep me',true)").fetchone()[0]
        connection.execute("INSERT INTO public.jumble_runtime VALUES (%s,'{\"phase\":\"active\",\"scores\":{\"team\":30}}',1)", (old['id'],))
        connection.execute("ALTER TABLE public.games ADD CONSTRAINT test_reject_title CHECK (title <> 'Reject me')")
        before = {table: rows(connection, table) for table in ('public.games','public.jumble_runtime')}
        with pytest.raises(psycopg.errors.CheckViolation):
            connection.execute("SELECT public.jumble_create_game('Reject me',true)")
        assert {table: rows(connection, table) for table in before} == before
        with pytest.raises(psycopg.errors.UniqueViolation):
            connection.execute("SELECT public.jumble_create_game('Replay',false)")
        assert {table: rows(connection, table) for table in before} == before


def test_simultaneous_replacements_serialize_and_leave_one_active_game(database_url):
    run_migrations(database_url)
    barrier = Barrier(2)
    def create():
        with psycopg.connect(database_url, autocommit=True) as connection:
            barrier.wait(timeout=10)
            return connection.execute("SELECT public.jumble_create_game('New',true)").fetchone()[0]['id']
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(create) for _ in range(2)]
        ids = [future.result(timeout=15) for future in futures]
    assert len(set(ids)) == 2
    with psycopg.connect(database_url) as connection:
        assert connection.execute("SELECT count(*) FROM public.games WHERE status='lobby'").fetchone() == (1,)
        assert connection.execute("SELECT count(*) FROM public.games WHERE status='completed' AND ended_reason='replaced'").fetchone() == (1,)
