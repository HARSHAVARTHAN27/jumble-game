from fastapi import APIRouter, Response, Request
from app.config import settings
from app.database import supabase
from app.schemas.player import PlayerJoinRequest
from app.services.player_service import PlayerService
from app.utils.validators import player_session, require_player_session

router = APIRouter(prefix="/api/player", tags=["player"])
service = PlayerService(supabase)


@router.post("/join")
def join_player(request: PlayerJoinRequest, response: Response):
    data = service.join_player(request.name, request.employee_code)
    response.set_cookie("jumble_player", player_session(data["player"]["id"], data["game"]["id"]),
                        httponly=True, secure=settings.ENVIRONMENT != "development",
                        samesite=settings.PLAYER_COOKIE_SAMESITE, max_age=86400, path="/api/player")
    return {"success": True, "data": data, "error": None}


@router.get("/state")
def get_player_state(request: Request, response: Response, player_id: str, game_id: str = ""):
    require_player_session(request, player_id, game_id)
    data = service.get_player_state(player_id, game_id)
    # Upgrade the waiting employee's cookie to a real game/player session when
    # the host opens a lobby. Retries restore the unique membership.
    response.set_cookie("jumble_player", player_session(data["player"]["id"], data["player"]["gameId"]),
                        httponly=True, secure=settings.ENVIRONMENT != "development",
                        samesite=settings.PLAYER_COOKIE_SAMESITE, max_age=86400, path="/api/player")
    return {"success": True, "data": data, "error": None}
