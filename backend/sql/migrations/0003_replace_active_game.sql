-- Create a fresh lobby atomically while retaining the previous session's history.
alter table public.games add column ended_reason text;

create function public.jumble_create_game(p_title text, p_replace_active boolean default false)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare previous_game public.games; created public.games;
begin
    -- All creation paths share this lock, including Play Again.
    perform pg_advisory_xact_lock(73452, 1);
    select * into previous_game from public.games
        where status in ('lobby', 'playing', 'paused') for update;
    if found then
        if not p_replace_active then
            raise exception 'An active session exists' using errcode = '23505';
        end if;
        update public.games set status = 'completed', completed_at = now(), ended_reason = 'replaced'
            where id = previous_game.id;
        -- Preserve submissions and earned totals; do not score the unfinished question.
        update public.jumble_runtime set version = version + 1,
            state = state || jsonb_build_object('phase', 'completed', 'endedReason', 'replaced')
            where game_id = previous_game.id;
    end if;
    insert into public.games(title, status) values (coalesce(nullif(p_title, ''), 'Jumble'), 'lobby')
        returning * into created;
    return to_jsonb(created);
end $$;
revoke all on function public.jumble_create_game(text, boolean) from public, anon, authenticated;
grant execute on function public.jumble_create_game(text, boolean) to service_role;

-- A delayed answer/start/timer must never revive a session closed by replacement.
create or replace function public.jumble_write_runtime(
    p_game uuid, p_expected integer, p_state jsonb, p_status text, p_round integer, p_question integer,
    p_content_version integer default null
) returns boolean language plpgsql security definer set search_path = '' as $$
declare current_version integer;
begin
    perform 1 from public.games where id = p_game and status in ('lobby', 'playing', 'paused') for update;
    if not found then return false; end if;
    if p_content_version is not null and not exists (
        select 1 from public.jumble_content where game_id = p_game and version = p_content_version
    ) then return false; end if;
    select version into current_version from public.jumble_runtime where game_id = p_game;
    if coalesce(current_version, 0) <> p_expected then return false; end if;
    insert into public.jumble_runtime(game_id, state, version) values(p_game, p_state, p_expected + 1)
        on conflict(game_id) do update set state = excluded.state, version = excluded.version;
    update public.games set status = p_status, current_round = p_round, current_question = p_question,
        started_at = case when p_status = 'playing' then coalesce(started_at, now()) else started_at end,
        completed_at = case when p_status = 'completed' then coalesce(completed_at, now()) else completed_at end
        where id = p_game;
    return true;
end $$;
