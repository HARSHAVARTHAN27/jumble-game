from fastapi import APIRouter, Depends
from app.database import supabase
from app.schemas.game import GameCreate
from app.services.game_service import GameService
from app.utils.validators import require_host

router = APIRouter(prefix="/api/host", tags=["host"], dependencies=[Depends(require_host)])
service = GameService(supabase)


@router.get("/access")
def host_access():
    return {"success": True, "data": {"role": "host"}, "error": None}


@router.post("/game/create")
def create_game(request: GameCreate):
    return {"success": True, "data": service.create_game(request.title, replace_active=True), "error": None}


@router.get("/lobby")
@router.get("/status")
def get_host_lobby(game_id: str):
    return {"success": True, "data": service.get_game_with_teams(game_id, host=True), "error": None}


@router.post("/game/start")
def start_game(game_id: str):
    return {"success": True, "data": service.start_game(game_id), "error": None}
