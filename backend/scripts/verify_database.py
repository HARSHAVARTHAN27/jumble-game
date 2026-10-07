"""Read-only live check of the four foundation tables; never prints secrets/employee data."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import supabase
from app.services.game_service import GameService
from app.exceptions import NO_ACTIVE_GAME
from postgrest.exceptions import APIError


def main():
    failed = False
    for table in ("games", "teams", "employees", "players"):
        try:
            supabase.from_(table).select("id").limit(1).execute()
            print(f"{table}: query successful")
        except APIError as exc:
            print(f"{table}: schema missing" if str(exc.code) == "PGRST205" else f"{table}: database check failed ({exc.code})")
            failed = True
        except Exception:
            print(f"{table}: connection check failed")
            failed = True
    if failed:
        return 1
    teams = supabase.from_("teams").select("name,slug").execute().data
    expected = {("Ctrl Alt Defeat", "ctrl-alt-defeat"), ("Titans", "titans"), ("Vibe Tribe", "vibe-tribe")}
    if len(teams) != 3 or {(t["name"], t["slug"]) for t in teams} != expected:
        print("Team seed check failed: run/review sql/seed.sql")
        return 1
    print("Team seed: Ctrl Alt Defeat, Titans, Vibe Tribe")
    try:
        GameService(supabase).get_active_game()
        print("Active game available")
    except NO_ACTIVE_GAME:
        print("Connection successful; no active game (normal before host creates a lobby)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
