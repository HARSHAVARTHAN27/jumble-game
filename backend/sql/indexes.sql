create index if not exists idx_employees_normalized_name on public.employees(normalized_name);
create index if not exists idx_employees_team on public.employees(team_id);
create index if not exists idx_players_game_team on public.players(game_id, team_id);
create unique index if not exists uq_players_game_employee on public.players(game_id, employee_id);
create unique index if not exists uq_employee_code on public.employees(employee_code);
-- All active rows have the same index key, allowing at most one.
create unique index if not exists uq_games_one_active on public.games((true))
    where status in ('lobby','playing','paused');
