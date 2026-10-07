from supabase import Client
from typing import Optional, Dict, Any, List


class LeaderboardService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def get_leaderboard(self, game_id: str) -> List[dict]:
        """Get leaderboard for a game with normalized team scoring."""
        # Get team round scores with game data
        result = self.supabase.from_('team_round_scores').select('*, teams(name)').eq('game_id', game_id).execute()

        teams_scores = []
        for ts in result.data:
            team_name = ts['teams']['name']
            raw_score = ts['raw_score'] or 0
            normalized_score = ts['normalized_score'] or 0
            active_player_count = ts['active_player_count'] or 0

            teams_scores.append({
                "team_name": team_name,
                "raw_score": raw_score,
                "normalized_score": normalized_score,
                "active_player_count": active_player_count,
            })

        # Sort by normalized_score descending
        teams_scores.sort(key=lambda x: x['normalized_score'], reverse=True)

        # Rank
        leaderboard = []
        for i, ts in enumerate(teams_scores):
            leaderboard.append({
                "rank": i + 1,
                "teamName": ts['team_name'],
                "score": float(ts['normalized_score']),
                "roundGain": float(ts['raw_score']),
            })

        return leaderboard

    async def update_team_round_score(self, game_id: str, round_id: str, team_id: str, points: float, player_count: int) -> None:
        """Update team round score after score reveal."""
        # Calculate normalized score
        # Get max possible score for this round (active players * max_points per player)
        # We'll use a simplified approach: normalized = (raw_score / (player_count * 100)) * 200
        # where 200 is the round maximum

        raw_score = (self.supabase.from_('team_round_scores').select('raw_score').eq('game_id', game_id).eq('round_id', round_id).eq('team_id', team_id).single().execute().data or {}).get('raw_score', 0) or 0

        new_raw_score = raw_score + points

        # Calculate normalized score
        # Maximum possible: player_count * 100 (assuming 100 max points per player)
        max_possible = player_count * 100.0 if player_count > 0 else 1.0
        normalized = (new_raw_score / max_possible) * 200.0 if max_possible > 0 else 0

        self.supabase.from_('team_round_scores').update({
            "raw_score": new_raw_score,
            "normalized_score": normalized,
            "active_player_count": player_count,
        }).eq('game_id', game_id).eq('round_id', round_id).eq('team_id', team_id).execute()