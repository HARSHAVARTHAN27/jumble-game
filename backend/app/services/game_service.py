from postgrest.exceptions import APIError
from app.exceptions import AppError, NO_ACTIVE_GAME
from app.realtime.manager import lobby_presence

ACTIVE_STATUSES = ["lobby", "playing", "paused"]


class GameService:
    def __init__(self, supabase):
        self.supabase = supabase
        from .live_game import LiveGame
        self.live = LiveGame(supabase)

    def get_active_game(self):
        rows = self.supabase.from_("games").select("*").in_("status", ACTIVE_STATUSES).limit(1).execute().data
        if not rows:
            raise NO_ACTIVE_GAME()
        return rows[0]

    def create_game(self, title="Jumble", replace_active=False):
        try:
            return self.supabase.rpc('jumble_create_game', {
                'p_title': title or 'Jumble', 'p_replace_active': replace_active,
            }).execute().data
        except APIError as exc:
            if str(exc.code) == "23505":
                raise AppError('ACTIVE_GAME_EXISTS', 'An active session exists. Use Create Game to replace it.', 409) from exc
            raise

    def get_game_with_teams(self, game_id, host=False, viewer=None, player_id=None):
        rows = self.supabase.from_("games").select("*").eq("id", game_id).execute().data
        if not rows:
            raise NO_ACTIVE_GAME()
        game = rows[0]
        result = {**game, **self.get_lobby_roster(game_id, host, viewer)}
        result['endedReason'] = game.get('ended_reason')
        result['completedAt'] = game.get('completed_at')
        result['newGameAvailable'] = False
        if game['status'] == 'completed':
            try:
                active = self.get_active_game()
                result['newGameAvailable'] = active['id'] != game_id and active['status'] == 'lobby'
            except NO_ACTIVE_GAME:
                pass
        if game.get('current_round', 0) or game['status'] in ('playing', 'paused', 'completed'):
            live = self.live.snapshot(game_id, host=host, player_id=player_id)
            if live:
                result.update(live)
                for team in result['teams']:
                    team['score'] = live['scores'].get(team['id'], 0)
                    team['roundGain'] = live['gains'].get(team['id'], {}).get('points', 0)
                    team['submitted'] = live['teamSubmitted'].get(team['id'], 0)
                for key in ('scores', 'gains', 'teamSubmitted'): result.pop(key, None)
        return result

    def get_lobby_roster(self, game_id=None, host=False, viewer=None):
        teams = self.supabase.from_("teams").select("id,name,slug").execute().data
        employees = self.supabase.from_("employees").select("id,name,team_id").eq("is_active", True).execute().data
        waiting = lobby_presence.snapshot() if not game_id else {}
        players = self.supabase.from_("players").select("id,employee_id,team_id,status,joined_at").eq("game_id", game_id).execute().data if game_id else [
            {"id": entry["id"], "employee_id": employee["id"], "team_id": employee["team_id"], "joined_at": entry["joinedAt"]}
            for employee in employees if (entry := waiting.get(employee["id"]))
        ]
        names = {e["id"]: e["name"] for e in employees}
        roster = []
        for team in teams:
            members = [p for p in players if p["team_id"] == team["id"]]
            item = {**team, "joined": len(members),
                    "total": sum(e["team_id"] == team["id"] for e in employees), "score": 0}
            if host or viewer:
                item["members"] = [names.get(p["employee_id"], "Inactive employee") for p in members]
            roster.append(item)
        result = {"teams": roster, "joined": len(players), "total": len(employees)}
        if host or viewer:
            result["participants"] = [{"id": p["id"], "name": names.get(p["employee_id"], "Inactive employee"),
                                       "teamId": p["team_id"], "joinedAt": p.get("joined_at"),
                                       "isYou": p["employee_id"] == viewer} for p in players]
        return result

    def start_game(self, game_id):
        return self.live.start(game_id)
