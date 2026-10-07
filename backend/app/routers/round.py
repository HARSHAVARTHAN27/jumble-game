from fastapi import APIRouter, Depends, Path
from supabase import Client
from typing import Optional

from app.database import supabase
from app.schemas.round import RoundStartRequest
from app.services.round_service import RoundService
from app.exceptions import *


router = APIRouter(prefix="/api/host/round", tags=["host/round"])


@router.post("/{round_id}/start")
async def start_round(
    round_id: str,
    game_id: str,
    host_id: str,
):
    """Start a round."""
    # Validate host
    result = supabase.from_('games').select('host_id').eq('id', game_id).single().execute()
    if not result.data or result.data['host_id'] != host_id:
        raise UNAUTHORIZED_HOST()
    
    # Validate active game
    active = supabase.from_('games').select('*').eq('id', game_id).execute()
    if not active.data or active.data[0]['status'] not in ('lobby', 'paused'):
        raise NO_ACTIVE_GAME()
    
    # Service
    from ...app.services.round_service import RoundService
    round_service = RoundService(supabase)
    
    await round_service.start_round(round_id, game_id, host_id)
    
    return {
        "success": True,
        "data": {
            "round_id": round_id,
            "status": "active",
        },
        "error": None,
    }