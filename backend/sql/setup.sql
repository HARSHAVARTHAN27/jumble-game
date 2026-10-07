-- Generated from the five organized source files. Paste this whole file into Supabase SQL Editor.
-- Rebuild with: python scripts/build_setup.py
begin;

-- backend/sql/schema.sql
-- Foundation only. Run before constraints.sql, indexes.sql, rls.sql, seed.sql.
create table if not exists public.games (
    id uuid primary key default gen_random_uuid(),
    title text not null default 'Jumble',
    status text not null default 'draft',
    current_round integer default 0,
    current_question integer default 0,
    total_rounds integer default 6,
    allow_late_join boolean default false,
    created_at timestamptz default now(),
    started_at timestamptz null,
    completed_at timestamptz null
);
create table if not exists public.teams (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    slug text unique not null,
    created_at timestamptz default now()
);
create table if not exists public.employees (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    normalized_name text not null,
    employee_code text null constraint uq_employee_code unique,
    team_id uuid not null references public.teams(id),
    is_active boolean default true,
    created_at timestamptz default now()
);
create table if not exists public.players (
    id uuid primary key default gen_random_uuid(),
    game_id uuid not null references public.games(id),
    employee_id uuid not null references public.employees(id),
    auth_user_id uuid null,
    team_id uuid not null references public.teams(id),
    status text default 'active',
    committed_score numeric default 0,
    pending_score numeric default 0,
    joined_at timestamptz default now(),
    last_seen_at timestamptz default now(),
    constraint uq_players_game_employee unique (game_id, employee_id)
);

-- Upgrade older foundation definitions without deleting existing data.
alter table public.games alter column title set default 'Jumble';
update public.games set title = 'Jumble' where title is null;
alter table public.games alter column title set not null;
alter table public.games alter column status set default 'draft';
alter table public.games alter column status set not null;
alter table public.employees alter column team_id set not null;
alter table public.players alter column game_id set not null;
alter table public.players alter column employee_id set not null;
alter table public.players alter column team_id set not null;
do $$
begin
    if exists (select 1 from information_schema.columns where table_schema='public'
               and table_name='games' and column_name='host_id') then
        alter table public.games alter column host_id drop not null;
    end if;
end $$;

-- backend/sql/constraints.sql
-- Re-runnable constraints. Invalid legacy rows fail visibly rather than being deleted.
do $$
begin
    if not exists (select 1 from pg_constraint where conrelid='public.games'::regclass and conname='chk_game_status') then
        alter table public.games add constraint chk_game_status
            check (status in ('draft','lobby','playing','paused','completed'));
    end if;
    if not exists (select 1 from pg_constraint where conrelid='public.players'::regclass and conname='chk_player_status') then
        alter table public.players add constraint chk_player_status
            check (status in ('active','disconnected','finished'));
    end if;
end $$;

-- Enforce employee-owned assignment even when a backend caller supplies another team.
create or replace function public.assign_employee_team()
returns trigger language plpgsql set search_path = '' as $$
begin
    select e.team_id into new.team_id from public.employees e where e.id = new.employee_id;
    if new.team_id is null then
        raise exception 'Player requires an employee with a predefined team' using errcode='23503';
    end if;
    return new;
end $$;
drop trigger if exists players_assign_employee_team on public.players;
create trigger players_assign_employee_team
    before insert or update of employee_id, team_id on public.players
    for each row execute function public.assign_employee_team();

-- Keep existing player assignments consistent if an administrator moves an employee.
create or replace function public.sync_employee_team()
returns trigger language plpgsql set search_path = '' as $$
begin
    update public.players set team_id = new.team_id where employee_id = new.id;
    return new;
end $$;
drop trigger if exists employees_sync_team on public.employees;
create trigger employees_sync_team after update of team_id on public.employees
    for each row when (old.team_id is distinct from new.team_id)
    execute function public.sync_employee_team();

-- backend/sql/indexes.sql
create index if not exists idx_employees_normalized_name on public.employees(normalized_name);
create index if not exists idx_employees_team on public.employees(team_id);
create index if not exists idx_players_game_team on public.players(game_id, team_id);
create unique index if not exists uq_players_game_employee on public.players(game_id, employee_id);
create unique index if not exists uq_employee_code on public.employees(employee_code);
-- All active rows have the same index key, allowing at most one.
create unique index if not exists uq_games_one_active on public.games((true))
    where status in ('lobby','playing','paused');

-- backend/sql/rls.sql
-- Sensitive reads and every write go through FastAPI's privileged client.
alter table public.games enable row level security;
alter table public.teams enable row level security;
alter table public.employees enable row level security;
alter table public.players enable row level security;

revoke all on public.games, public.teams, public.employees, public.players from anon, authenticated;
grant all on public.games, public.teams, public.employees, public.players to service_role;
grant select on public.teams to anon, authenticated;
drop policy if exists teams_public_read on public.teams;
create policy teams_public_read on public.teams for select to anon, authenticated using (true);

-- Remove any earlier foundation policies; RLS alone is not a grant of SQL privileges.
do $$
declare policy_row record;
begin
    for policy_row in
        select tablename, policyname from pg_policies
        where schemaname='public' and tablename in ('games','employees','players')
    loop
        execute format('drop policy %I on public.%I', policy_row.policyname, policy_row.tablename);
    end loop;
end $$;
revoke all on function public.assign_employee_team() from public, anon, authenticated;
revoke all on function public.sync_employee_team() from public, anon, authenticated;

-- backend/sql/seed.sql
-- Only team definitions: no sample employees, games, rounds, or questions.
insert into public.teams(name, slug) values
    ('Ctrl Alt Defeat', 'ctrl-alt-defeat'),
    ('Titans', 'titans'),
    ('Vibe Tribe', 'vibe-tribe')
on conflict (slug) do update set name = excluded.name;

do $$
begin
    if (select count(*) from public.teams) <> 3 then
        raise exception 'Unexpected existing teams. Review their employee references and migrate them to the three canonical teams before rerunning setup.';
    end if;
end $$;
notify pgrst, 'reload schema';


commit;
