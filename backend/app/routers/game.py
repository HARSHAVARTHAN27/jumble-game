from fastapi import APIRouter
from app.database import supabase
from app.services.game_service import GameService

router = APIRouter(prefix="/api/game", tags=["game"])
service = GameService(supabase)


@router.get("/active")
def get_active_game():
    return {"success": True, "data": service.get_active_game(), "error": None}


@router.get("/state")
def get_game_state(game_id: str):
    return {"success": True, "data": service.get_game_with_teams(game_id), "error": None}
