-- Frozen gameplay baseline. Add future changes as a new numbered migration.
create table if not exists public.jumble_content (
    game_id uuid primary key references public.games(id) on delete cascade,
    document jsonb not null,
    version integer not null default 1
);
create table if not exists public.jumble_runtime (
    game_id uuid primary key references public.games(id) on delete cascade,
    state jsonb not null,
    version integer not null default 1
);
alter table public.jumble_content enable row level security;
alter table public.jumble_runtime enable row level security;
revoke all on public.jumble_content, public.jumble_runtime from anon, authenticated;
grant all on public.jumble_content, public.jumble_runtime to service_role;

create or replace function public.jumble_save_content(p_game uuid, p_expected integer, p_document jsonb)
returns boolean language plpgsql security definer set search_path = '' as $$
declare current_version integer;
begin
    perform 1 from public.games where id = p_game and status in ('draft', 'lobby') for update;
    if not found then return false; end if;
    select version into current_version from public.jumble_content where game_id = p_game;
    if coalesce(current_version, 0) <> p_expected then return false; end if;
    insert into public.jumble_content(game_id, document, version) values(p_game, p_document, p_expected + 1)
        on conflict(game_id) do update set document = excluded.document, version = excluded.version;
    return true;
end $$;

create or replace function public.jumble_write_runtime(
    p_game uuid, p_expected integer, p_state jsonb, p_status text, p_round integer, p_question integer,
    p_content_version integer default null
) returns boolean language plpgsql security definer set search_path = '' as $$
declare current_version integer;
begin
    perform 1 from public.games where id = p_game for update;
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
revoke all on function public.jumble_save_content(uuid, integer, jsonb) from public, anon, authenticated;
revoke all on function public.jumble_write_runtime(uuid, integer, jsonb, text, integer, integer, integer) from public, anon, authenticated;
grant execute on function public.jumble_save_content(uuid, integer, jsonb) to service_role;
grant execute on function public.jumble_write_runtime(uuid, integer, jsonb, text, integer, integer, integer) to service_role;

insert into storage.buckets(id, name, public, file_size_limit, allowed_mime_types)
values('jumble-grid', 'jumble-grid', false, 5242880, array['image/png','image/jpeg','image/webp'])
on conflict(id) do update set public = false, file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;
