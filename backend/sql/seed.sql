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
