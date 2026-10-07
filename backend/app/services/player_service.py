from datetime import datetime, timezone
from postgrest.exceptions import APIError
from app.exceptions import EMPLOYEE_NOT_FOUND, EMPLOYEE_INACTIVE, DUPLICATE_EMPLOYEE_NAME, GAME_ALREADY_STARTED, UNAUTHORIZED, NO_ACTIVE_GAME
from app.utils.name_normalizer import normalize_name
from .game_service import GameService
from app.realtime.manager import lobby_presence


class PlayerService:
    def __init__(self, supabase):
        self.supabase = supabase
        self.games = GameService(supabase)

    def find_employee(self, name=None, employee_code=None):
        query = self.supabase.from_("employees").select("*")
        if employee_code:
            query = query.eq("employee_code", employee_code.strip().upper())
            if name:
                query = query.eq("normalized_name", normalize_name(name))
        elif name:
            query = query.eq("normalized_name", normalize_name(name))
        rows = query.execute().data
        if not rows and name and not employee_code:
            rows = self.supabase.from_("employees").select("*").eq("employee_code", name.strip().upper()).execute().data
        if not rows:
            raise EMPLOYEE_NOT_FOUND(name)
        if len(rows) > 1:
            raise DUPLICATE_EMPLOYEE_NAME(name)
        if not rows[0]["is_active"]:
            raise EMPLOYEE_INACTIVE(name)
        return rows[0]

    def join_player(self, name=None, employee_code=None):
        employee = self.find_employee(name, employee_code)
        return self.join_employee(employee)

    def join_employee(self, employee):
        try:
            game = self.games.get_active_game()
        except NO_ACTIVE_GAME:
            lobby_presence.touch(employee["id"])
            team = self.supabase.from_("teams").select("id,name").eq("id", employee["team_id"]).execute().data[0]
            # A verified employee can wait without fabricating a game or inserting
            # a player with a null game_id. The signed session binds this identity.
            return {"player": {"id": employee["id"], "name": employee["name"], "waitingForGame": True},
                    "team": team, "game": {"id": "", "status": "waiting"}}
        def existing():
            return self.supabase.from_("players").select("*").eq("game_id", game["id"]).eq("employee_id", employee["id"]).execute().data
        rows = existing()
        if not rows:
            if game["status"] != "lobby" and not game.get("allow_late_join", False):
                raise GAME_ALREADY_STARTED()
            try:
                rows = self.supabase.from_("players").insert({
                    "game_id": game["id"], "employee_id": employee["id"],
                    "team_id": employee["team_id"], "status": "active",
                }).execute().data
            except APIError as exc:
                if str(exc.code) != "23505":
                    raise
                # Another request may have joined the same employee concurrently.
                rows = existing()
                if not rows:
                    raise
        player = rows[0]
        lobby_presence.discard(employee["id"])
        self.supabase.from_("players").update({
            "status": "active", "last_seen_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", player["id"]).execute()
        team = self.supabase.from_("teams").select("id,name").eq("id", player["team_id"]).execute().data[0]
        return {"player": {"id": player["id"], "name": employee["name"]},
                "team": team, "game": {"id": game["id"], "status": game["status"]}}

    def get_player_state(self, player_id, game_id):
        if not game_id:
            rows = self.supabase.from_("employees").select("*").eq("id", player_id).eq("is_active", True).execute().data
            if not rows:
                raise UNAUTHORIZED()
            data = self.join_employee(rows[0])
            if data["game"]["id"]:
                return self.get_player_state(data["player"]["id"], data["game"]["id"])
            return {"id": "", "status": "lobby", "current_round": 0,
                    **self.games.get_lobby_roster(viewer=player_id),
                    "player": {**data["player"], "teamId": data["team"]["id"], "gameId": "",
                               "score": 0, "hasSubmitted": False}}
        rows = self.supabase.from_("players").select("id,employee_id,team_id").eq("id", player_id).eq("game_id", game_id).execute().data
        if not rows:
            raise UNAUTHORIZED()
        player = rows[0]
        employee = self.supabase.from_("employees").select("name").eq("id", player["employee_id"]).execute().data[0]
        state = self.games.get_game_with_teams(game_id, viewer=player["employee_id"], player_id=player_id)
        live_player = state.get('player', {})
        state["player"] = {"id": player["id"], "name": employee["name"],
                           "teamId": player["team_id"], "gameId": game_id,
                           "score": 0, "hasSubmitted": False, "waitingForGame": False, **live_player}
        return state
