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
