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
