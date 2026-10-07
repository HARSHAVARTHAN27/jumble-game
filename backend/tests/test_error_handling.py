"""Error responses without database network access or mutations."""
import asyncio
import json
from postgrest.exceptions import APIError
from app.exceptions import NO_ACTIVE_GAME
from app.main import global_exception_handler


def test_missing_database_has_actionable_response():
    exception = APIError({"code": "PGRST205", "message": "Missing games", "details": None, "hint": None})
    response = asyncio.run(global_exception_handler(None, exception))
    assert response.status_code == 503
    body = json.loads(response.body)
    assert body["error"]["code"] == "DATABASE_NOT_INITIALIZED"
    assert "DATABASE_URL" in body["error"]["message"]


def test_expected_game_error_retains_its_status():
    response = asyncio.run(global_exception_handler(None, NO_ACTIVE_GAME()))
    assert response.status_code == 404
    assert json.loads(response.body)["error"]["code"] == "NO_ACTIVE_GAME"


def test_unexpected_error_does_not_expose_details():
    response = asyncio.run(global_exception_handler(None, RuntimeError("private database information")))
    assert response.status_code == 500
    assert b"private database information" not in response.body
