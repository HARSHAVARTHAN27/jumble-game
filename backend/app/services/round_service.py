from supabase import Client
from typing import Optional, Dict, Any
from app.exceptions import *


class RoundService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def start_round(self, round_id: str, game_id: str, host_id: str) -> dict:
        """Start a round - validate host, validate game, mark previous round if needed."""
        # Validate host
        from .services.game_service import GameService
        game_service = GameService(self.supabase)
        host_valid = await game_service.validate_host(game_id, host_id)
        if not host_valid:
            raise UNAUTHORIZED_HOST()

        # Validate active game
        active_game = await game_service.get_active_game()
        if not active_game or active_game['id'] != game_id:
            raise NO_ACTIVE_GAME()

        # Mark previous round as completed if exists
        if game_service.get_game_with_teams(game_id)['current_round'] > 0:
            prev_round_num = game_service.get_game_with_teams(game_id)['current_round']
            self.supabase.from_('rounds').update({"status": "completed", "ended_at": "now()"}).eq('game_id', game_id).eq('round_number', prev_round_num).execute()

        # Set round status = active
        self.supabase.from_('rounds').update({"status": "active", "started_at": "now()"}).eq('id', round_id).execute()

        # Update game.current_round
        self.supabase.from_('games').update({"current_round": int(round_id.split('_')[-1]) if '_' in round_id else 1}).eq('id', game_id).execute()

        # Publish ROUND_STARTED event
        await self.publish_realtime(game_id, "ROUND_STARTED", {"round_id": round_id})

        return {
            "round_id": round_id,
            "status": "active",
        }

    async def publish_realtime(self, game_id: str, event: str, payload: dict) -> None:
        """Publish a realtime event to the game channel."""
        self.supabase.channel(f"game:{game_id}").send({
            "event": event,
            "payload": payload,
        })