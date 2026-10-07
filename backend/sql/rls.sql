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
