# Jumble backend

FastAPI owns authentication checks, content, live gameplay and scoring. Supabase supplies PostgreSQL, Auth and private grid-image storage. The foundation contains games, teams, employees and players; the gameplay migration adds private versioned content and runtime documents. Host forms supply real questions; there are no question seeds.

## Automatic database setup

The backend applies pending SQL migrations before accepting requests or starting
the game timer. After one-time connection configuration, starting the backend
creates or upgrades the database automatically; no SQL Editor copy/paste is needed.

1. In the **same Supabase project** used by `SUPABASE_URL`, click **Connect** and
   copy the PostgreSQL direct connection string. On an IPv4-only network, use the
   **Session pooler** connection on port 5432 instead of the transaction pooler.
2. Set `DATABASE_URL` in `backend/.env`, replacing the database password placeholder
   with its URL-encoded value. This is the database password, not the host user's
   password or an API key. Keep the connection string in the backend only; never
   put it in a `VITE_` setting, source control, or chat.
3. Leave `AUTO_MIGRATE=true` (the default), install `requirements.txt`, and start
   the backend with `python run.py`.

See [Supabase's connection guide](https://supabase.com/docs/guides/database/connecting-to-postgres)
for the appropriate connection string. The runner requires SSL unless the URL
explicitly supplies another `sslmode` (local test databases use `disable`). It
uses a 10-second connection timeout, 30-second lock timeout, and 120-second SQL
statement timeout. The ordinary API still uses the existing Supabase client.

Startup runs the ordered files in `sql/migrations`. The first two migrations
install the foundation and gameplay objects, including the three canonical teams,
private gameplay documents and `jumble-grid` bucket. They preserve existing game,
employee, player, content and host records. They do not provision Auth users,
change host passwords, import employees or seed sample questions.

Applied versions and checksums are stored in the private
`jumble_internal.schema_migrations` table. Restarts skip completed migrations;
concurrent starts are serialized using a database lock. All pending migrations
and history entries form a single transaction. SQL errors roll back that batch
and stop startup. Missing credentials, invalid migration history, and connection
errors also stop startup with sanitized diagnostics. Fix the reported problem
and restart; never reset the database or delete migration history to bypass it.

For future schema changes, add a new numbered SQL file under `sql/migrations`.
Do not edit an applied migration or expect edits to the legacy setup files to
run again. See `sql/migrations/README.md` for transaction and release rules.

`0003_replace_active_game.sql` adds atomic session replacement. **Create Game**
ends any active lobby/playing/paused session and creates an empty lobby with a
new ID. Prior content, memberships, submissions and earned totals remain stored;
unfinished questions receive no additional marks. Closed sessions reject delayed
gameplay writes. **Play Again** remains the separate content-copying workflow and
does not replace an unrelated active session. Players see an ended-session notice
and use **Join New Game** to enter their name or employee ID again; no players
are transferred automatically. Restart the backend to apply this migration.

## Optional manual database setup

Set `AUTO_MIGRATE=false` to retain manual setup without a PostgreSQL connection
string. Automatic setup is preferred; the files below provide the original baseline.

1. Open the Supabase project matching backend/.env.
2. In **SQL Editor → New query**, paste the entire **backend/sql/setup.sql** file and run it. This generated transaction combines the organized SQL sources.
3. Alternatively run the files in this exact order: **schema.sql → constraints.sql → indexes.sql → rls.sql → seed.sql**.
4. From the backend directory run:
   `python scripts/verify_database.py`
5. Apply **backend/sql/gameplay.sql** in SQL Editor for the six-round content editor, transactional gameplay functions, and private image bucket. This is separate from the foundation bundle.
   Then apply **sql/migrations/0003_replace_active_game.sql** once for fresh-session creation; future numbered migrations must also be applied in order when automatic setup is disabled.
6. Restart FastAPI. Follow **GAMEPLAY.md** at the project root for the host workflow.

These legacy SQL bundles can be applied manually in Supabase SQL Editor. API keys cannot execute database DDL through PostgREST. Verify tables afterward with the read-only verification script. `python scripts/build_setup.py` rebuilds only the optional legacy foundation bundle, not the versioned migrations. Switching from manual to automatic setup safely adopts the baseline and records its history; subsequent upgrades must use new migration files.

The setup is re-runnable. It preserves existing rows and does not create or delete deferred round tables. Invalid legacy rows, multiple active games, or unexpected extra teams cause a visible migration error; review those rows instead of deleting data automatically.

Tables:
- games: status/default fields, six reserved rounds, one active lobby/playing/paused enforced by a partial unique index.
- teams: database-generated IDs; Ctrl Alt Defeat (ctrl-alt-defeat), Titans (titans), Vibe Tribe (vibe-tribe).
- employees: exact normalized name lookup, optional unique employee code, predefined required team.
- players: unique game/employee membership, required foreign keys, score defaults, timestamps. Triggers derive the team from the employee and keep assignments consistent.

## Environment and run commands

Keep your existing backend/.env and add DATABASE_URL for automatic setup. AUTO_MIGRATE defaults to true; use false only for manual setup. Empty examples also use SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY. The existing loader accepts SUPABASE_PUBLISHABLE_KEY and SUPABASE_SECRET_KEY. Never copy a backend secret into Vite configuration.

```powershell
cd C:\Users\Harshavardhan\Desktop\Jumble\backend
python -m pip install -r requirements.txt
python run.py
```

API: http://localhost:8000 — docs: http://localhost:8000/docs

After successful migrations (or immediately in manual mode), startup distinguishes ready, schema_missing, and connection_failed. An empty active-game query is a normal ready state. /health retains its database check status. Migration failure prevents the app from serving requests. Missing tables return a structured 503 DATABASE_NOT_INITIALIZED response without database details.

## Import real employees

CSV headers: employee_name,employee_code,team. Use canonical database team names or slugs. Blank employee codes are allowed; repeated names should use distinct codes.

```powershell
cd C:\Users\Harshavardhan\Desktop\Jumble\backend
python scripts/import_employees.py employees.csv
```

The importer validates headers/names/codes/teams, normalizes names, continues row failures, and prints totals and line-specific errors. It uses the application's singleton privileged client. It does not update existing employees silently. No synthetic-player simulation is enabled.

## Host authorization

Every registered /api/host/* route verifies the Bearer token with Supabase Auth and requires the administrator-managed **app_metadata.role = "host"**. Host IDs and editable user_metadata do not grant access. The browser's /control area signs in through Supabase Auth using public credentials.

Provision a real host account in Supabase Authentication → Users. Then, in SQL Editor, assign the role to that specific Auth user (replace the placeholder with its actual UUID):

```sql
update auth.users
set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) || '{"role":"host"}'::jsonb
where id = '<actual Auth user UUID>'::uuid;
```

Alternatively run the provisioning script, which creates the Auth user, sets `app_metadata.role = "host"`, and then replays the password grant to confirm the account can sign in:

```powershell
cd C:\Users\Harshavardhan\Desktop\Jumble\backend
python scripts/create_host.py --email host@example.com
```

The password is prompted with hidden input when `--password` is omitted (pass it explicitly only in non-interactive runs). `--rotate` resets an existing account's password and re-applies the role; `--no-verify` skips the sign-in check. The script prints the email, user ID and role but never the password.

Sign in at /control. Never assign this role through normal frontend signup metadata. See [Supabase Auth user metadata guidance](https://supabase.com/docs/guides/auth/users).

## Foundation routes

| Route | Behavior |
| --- | --- |
| GET /api/game/active | Active lobby/playing/paused game; NO_ACTIVE_GAME when absent |
| GET /api/game/state?game_id=… | Public counts and canonical teams; no employee identities or pending scores |
| POST /api/player/join | Name or employee ID in name/identifier, or employeeCode alone (legacy employee_code accepted); predefined team |
| GET /api/player/state?player_id=…&game_id=… | Signed waiting/playing snapshot; game_id may be empty before a host opens a lobby |
| GET /api/host/access | Verified host access check |
| POST /api/host/game/create | Atomically ends the active session and creates a fresh empty lobby; preserves history |
| GET /api/host/lobby or /api/host/status?game_id=… | Protected roster/counts derived from foundation tables |
| POST /api/host/game/start?game_id=… | Protected; validates all six rounds and at least two players per team |

Join restores existing membership safely, including a concurrent unique-key race, without counting the same person twice. New late joins are blocked outside lobby unless enabled; reconnects remain allowed. Request team overrides are rejected.

The supplied employees.csv contains 44 roster entries and has been imported successfully. Join checks that imported roster in Supabase using an exact normalized full name or an uppercase employee ID. It never downloads the CSV into React or uses fuzzy name matching. Future CSV changes require importing the new records; existing employee changes must be reviewed rather than silently overwritten.

Verified employees can wait before any active game exists. A signed HttpOnly cookie binds the waiting employee identity; no dummy game or player with a null game_id is created. Waiting employees do not increase a game's joined count until the host opens it. The lobby checks every five seconds, creates/restores the unique player membership when a game becomes available, and updates the session. Overlapping waiting/enrolled requests are accepted only when the database confirms they belong to the same employee.

RLS and SQL grants prevent anonymous/authenticated clients from directly reading employees/players or writing foundation rows/scores. Only public team definitions are readable. FastAPI alone uses the secret/service-role client. Player cookies expire after one day; re-entering the name restores membership. Production needs HTTPS and frontend/API deployment on the same site for SameSite=Lax cookies.

## Verification and remaining work

```powershell
python -m compileall -q app scripts tests
python -m pytest -q
python scripts/verify_database.py
```

Offline tests use a fake PostgREST boundary and never mutate Supabase. The migration
integration tests are skipped unless `MIGRATION_TEST_DATABASE_URL` points to a
disposable PostgreSQL admin database on localhost (remote hosts are rejected).
They create and drop only randomly named `jumble_migration_test_*` databases,
with minimal Supabase role/storage/Auth fixtures. Use a disposable PostgreSQL
instance, not your development or production Supabase URL:

```powershell
$env:MIGRATION_TEST_DATABASE_URL = 'postgresql://postgres:LOCAL_TEST_PASSWORD@127.0.0.1:55432/postgres?sslmode=disable'
python -m pytest -q tests/test_migrations.py tests/test_migrations_integration.py
```

These checks cover fresh setup, adoption with existing records, no-op restarts,
concurrent starts, rollback, incompatible legacy data, checksum drift, and startup
failure. Live table/seed verification is read-only. Live employee lookup and waiting
require the applied schema and imported employee roster; game enrollment additionally
requires an authorized host-created lobby.

The six-round engine is registered through app/routers/live.py. Older round/question/scoring modules remain unregistered; the versioned engine replaces their incomplete implementations. Startup migrations install its database objects; provision a host and supply real content separately. Production load testing remains deployment-specific.

Verified lobby participants receive joined display names, team IDs, and an own-player flag through signed player snapshots. Public snapshots contain counts, scores and phase-appropriate question content, with no private roster, answer keys before closing, artist cards or team canvases. Before a game exists, waiting presence is ephemeral: five-second polls renew it and closed tabs expire after 30 seconds. Run one backend worker; waiting presence needs a shared store before multiple-worker deployment. Live game data survives restarts in PostgreSQL. WebSockets use host tokens in the first frame or the signed player cookie, and validate Origin; REST polling restores disconnected clients.
