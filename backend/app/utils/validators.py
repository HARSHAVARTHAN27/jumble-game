"""Authentication and foundation validation shared by API routes."""
import base64
import hashlib
import hmac
import json
import time
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.database import supabase
from app.exceptions import UNAUTHORIZED_HOST, UNAUTHORIZED
from app.services.game_service import GameService

bearer = HTTPBearer(auto_error=False)


def require_host(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not credentials:
        raise UNAUTHORIZED_HOST()
    try:
        user = supabase.auth.get_user(credentials.credentials).user
    except Exception:
        raise UNAUTHORIZED_HOST() from None
    # app_metadata is administrator managed. Never trust editable user_metadata.
    if not user or user.app_metadata.get("role") != "host":
        raise UNAUTHORIZED_HOST()
    return user


def player_session(player_id, game_id):
    payload = base64.urlsafe_b64encode(json.dumps({
        "player": player_id, "game": game_id, "expires": int(time.time()) + 86400,
    }, separators=(",", ":")).encode()).decode()
    key = hashlib.sha256(("jumble-player-session:" + settings.SUPABASE_SERVICE_ROLE_KEY).encode()).digest()
    signature = hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()
    return payload + "." + signature


def require_player_session(request: Request, player_id: str, game_id: str):
    try:
        payload, signature = request.cookies["jumble_player"].rsplit(".", 1)
        key = hashlib.sha256(("jumble-player-session:" + settings.SUPABASE_SERVICE_ROLE_KEY).encode()).digest()
        expected = hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()
        data = json.loads(base64.urlsafe_b64decode(payload))
        if not hmac.compare_digest(signature, expected) or data["expires"] < time.time():
            raise ValueError()
        if data["player"] != player_id or data["game"] != game_id:
            # Waiting and enrolled snapshots may overlap in flight. Accept
            # either signed identity only when the DB confirms the same employee.
            if not data["game"] and game_id:
                rows = supabase.from_("players").select("employee_id").eq("id", player_id).eq("game_id", game_id).execute().data
                if not rows or rows[0]["employee_id"] != data["player"]:
                    raise ValueError()
            elif data["game"] and not game_id:
                rows = supabase.from_("players").select("employee_id").eq("id", data["player"]).eq("game_id", data["game"]).execute().data
                if not rows or rows[0]["employee_id"] != player_id:
                    raise ValueError()
            elif data['game'] and game_id:
                # A late old-session poll may renew its cookie after an explicit
                # rejoin. Accept either membership only for the same employee.
                old = supabase.from_('players').select('employee_id').eq('id', data['player']).eq('game_id', data['game']).execute().data
                new = supabase.from_('players').select('employee_id').eq('id', player_id).eq('game_id', game_id).execute().data
                if not old or not new or old[0]['employee_id'] != new[0]['employee_id']:
                    raise ValueError()
            else:
                raise ValueError()
    except (KeyError, ValueError, TypeError):
        raise UNAUTHORIZED() from None


def validate_active_game(client, game_id=None):
    game = GameService(client).get_active_game()
    if game_id and game["id"] != game_id:
        from app.exceptions import NO_ACTIVE_GAME
        raise NO_ACTIVE_GAME()
    return game


def validate_host(*args, **kwargs):
    # Legacy deferred round services must never accept a UUID as authorization.
    raise UNAUTHORIZED_HOST()
