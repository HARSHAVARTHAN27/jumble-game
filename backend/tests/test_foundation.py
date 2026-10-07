import asyncio
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app import main
from app.exceptions import AppError
from app.routers import employee, game, host
from app.services.game_service import GameService
from app.services.player_service import PlayerService
from app.utils import validators
from app.utils.name_normalizer import normalize_name
from scripts.import_employees import import_employees
from tests.fakes import Database, api_error


@pytest.fixture
def db(monkeypatch):
    from app.realtime.manager import LobbyPresence
    from app.services import game_service, player_service
    presence = LobbyPresence()
    monkeypatch.setattr(game_service, "lobby_presence", presence)
    monkeypatch.setattr(player_service, "lobby_presence", presence)
    return Database()


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setattr(employee, "service", PlayerService(db))
    monkeypatch.setattr(game, "service", GameService(db))
    monkeypatch.setattr(host, "service", GameService(db))
    monkeypatch.setattr(validators, "supabase", db)
    return TestClient(main.app, raise_server_exceptions=False)


@pytest.mark.parametrize("raw,expected", [("  Harsha  ", "harsha"), ("HARSHA", "harsha"),
                                        ("Harsha   Kumar", "harsha kumar"), ("Harsha\tKumar", "harsha kumar")])
def test_normalization(raw, expected):
    assert normalize_name(raw) == expected


@pytest.mark.parametrize("status", ["lobby", "playing", "paused"])
def test_active_statuses(db, status):
    db.tables["games"][0]["status"] = status
    assert GameService(db).get_active_game()["status"] == status


@pytest.mark.parametrize("status", ["draft", "completed"])
def test_verified_employee_can_wait_without_active_game(db, status):
    db.tables["games"][0]["status"] = status
    result = PlayerService(db).join_player("Harsha Kumar")
    assert result["player"]["waitingForGame"] is True
    assert result["game"] == {"id": "", "status": "waiting"}
    assert not db.tables["players"]


@pytest.mark.parametrize("payload", [{"name": " emp001 "}, {"identifier": "EMP001"},
                                    {"employeeCode": "emp001"}, {"employee_code": "EMP001"}])
def test_join_by_employee_id(client, payload):
    result = client.post("/api/player/join", json=payload)
    assert result.status_code == 200
    assert result.json()["data"]["player"]["name"] == "Harsha Kumar"
    assert result.json()["data"]["team"]["name"] == "Ctrl Alt Defeat"


@pytest.mark.parametrize("payload", [{}, {"name": "  "}, {"employeeCode": "   "}])
def test_missing_identifier_rejected(client, payload):
    assert client.post("/api/player/join", json=payload).status_code == 422


def test_waiting_session_promotes_when_host_opens_lobby(client, db):
    db.tables["games"].clear()
    result = client.post("/api/player/join", json={"name": "EMP001"})
    assert result.status_code == 200
    employee_id = result.json()["data"]["player"]["id"]
    pending_cookie = client.cookies.get("jumble_player")
    query = {"player_id": employee_id, "game_id": ""}
    state = client.get("/api/player/state", params=query)
    assert state.status_code == 200
    assert state.json()["data"]["player"]["waitingForGame"] is True
    assert state.json()["data"]["total"] == 1 and state.json()["data"]["joined"] == 1
    assert not db.tables["players"]
    assert client.get("/api/player/state", params={"player_id": "other", "game_id": ""}).status_code == 403
    db.tables["games"].append({"id": "opened-game", "status": "lobby", "allow_late_join": False})
    state = client.get("/api/player/state", params=query)
    data = state.json()["data"]
    assert state.status_code == 200 and data["id"] == "opened-game"
    assert data["player"]["waitingForGame"] is False and data["joined"] == 1
    assert data["player"]["id"] != employee_id
    assert client.get("/api/player/state", params={"player_id": data["player"]["id"], "game_id": "opened-game"}).status_code == 200
    # A concurrent retry carrying the original signed waiting identity must
    # restore the same membership, not create a second player.
    client.cookies.clear()
    client.cookies.set("jumble_player", pending_cookie)
    again = client.get("/api/player/state", params=query)
    assert again.status_code == 200 and again.json()["data"]["player"]["id"] == data["player"]["id"]
    assert len(db.tables["players"]) == 1


def test_waiting_and_enrolled_cookies_handle_overlapping_requests(client, db):
    db.tables["games"].clear()
    result = client.post("/api/player/join", json={"employeeCode": "EMP001"})
    employee_id = result.json()["data"]["player"]["id"]
    pending_cookie = client.cookies.get("jumble_player")
    db.tables["games"].append({"id": "opened-game", "status": "lobby"})
    response = client.get("/api/player/state", params={"player_id": employee_id, "game_id": ""})
    actual_id = response.json()["data"]["player"]["id"]
    # An earlier waiting request may arrive after the cookie has been upgraded.
    assert client.get("/api/player/state", params={"player_id": employee_id, "game_id": ""}).status_code == 200
    client.cookies.clear()
    client.cookies.set("jumble_player", pending_cookie)
    # Or its response may restore the original cookie after the new snapshot.
    assert client.get("/api/player/state", params={"player_id": actual_id, "game_id": "opened-game"}).status_code == 200
    assert client.get("/api/player/state", params={"player_id": "someone-else", "game_id": "opened-game"}).status_code == 403
    assert len(db.tables["players"]) == 1


def test_unknown_employee_cannot_wait(client, db):
    db.tables["games"].clear()
    response = client.post("/api/player/join", json={"name": "Unknown"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EMPLOYEE_NOT_FOUND"
    assert "jumble_player" not in client.cookies


def test_supplied_csv_names_and_codes_match_their_teams(db):
    from pathlib import Path
    db.tables["employees"].clear()
    content = (Path(__file__).resolve().parents[1] / "employees.csv").read_text(encoding="utf-8-sig")
    result = import_employees(content, db)
    assert result == {"successful": 44, "failed": 0, "errors": []}
    service = PlayerService(db)
    by_id = service.join_player("gipl042")
    by_name = service.join_player("  HARSHAVARTHAN  ")
    assert by_id == by_name
    assert by_id["player"]["name"] == "Harshavarthan"
    assert by_id["team"]["name"] == "Ctrl Alt Defeat"
    assert service.join_player("GIPL001")["team"]["name"] == "Titans"
    assert service.join_player("Gnana   sree")["team"]["name"] == "Vibe Tribe"


def test_join_restore_auto_team_and_cookie(client, db):
    result = client.post("/api/player/join", json={"name": " HARSHA   KUMAR "})
    assert result.status_code == 200
    body = result.json()
    assert body["success"] and body["error"] is None
    assert body["data"]["team"] == {"id": "team-a", "name": "Ctrl Alt Defeat"}
    player_id = body["data"]["player"]["id"]
    assert "HttpOnly" in result.headers["set-cookie"]
    again = client.post("/api/player/join", json={"name": "Harsha Kumar"})
    assert again.json()["data"]["player"]["id"] == player_id
    assert len(db.tables["players"]) == 1
    assert db.tables["players"][0]["last_seen_at"] != "now()"
    state = client.get("/api/player/state", params={"player_id": player_id, "game_id": "game-a"})
    assert state.status_code == 200
    assert state.json()["data"]["joined"] == 1
    assert "pending_score" not in state.text
    assert "employee_code" not in state.text
    assert client.get("/api/player/state", params={"player_id": "other", "game_id": "game-a"}).status_code == 403
    client.cookies.clear()
    assert client.get("/api/player/state", params={"player_id": player_id, "game_id": "game-a"}).status_code == 403


def test_team_override_rejected(client, db):
    response = client.post("/api/player/join", json={"name": "Harsha Kumar", "team_id": "team-b"})
    assert response.status_code == 422
    assert not db.tables["players"]


@pytest.mark.parametrize("field", ["employeeCode", "employee_code"])
def test_duplicate_name_disambiguation(client, db, field):
    db.tables["employees"].append({**db.tables["employees"][0], "id": "employee-b",
                                   "employee_code": "EMP002", "team_id": "team-b"})
    response = client.post("/api/player/join", json={"name": "Harsha Kumar"})
    assert response.json()["error"]["code"] == "DUPLICATE_EMPLOYEE_NAME"
    response = client.post("/api/player/join", json={"name": "Harsha Kumar", field: "EMP002"})
    assert response.status_code == 200
    assert response.json()["data"]["team"]["id"] == "team-b"


def test_wrong_code_even_with_unique_name(client):
    response = client.post("/api/player/join", json={"name": "Harsha Kumar", "employeeCode": "wrong"})
    assert response.json()["error"]["code"] == "EMPLOYEE_NOT_FOUND"


def test_inactive_employee(client, db):
    db.tables["employees"][0]["is_active"] = False
    assert client.post("/api/player/join", json={"name": "Harsha Kumar"}).json()["error"]["code"] == "EMPLOYEE_INACTIVE"


def test_concurrent_join_restores_unique_row(db):
    db.race = True
    result = PlayerService(db).join_player("Harsha Kumar")
    assert result["player"]["id"] == db.tables["players"][0]["id"]
    assert len(db.tables["players"]) == 1


def test_late_join_blocked_but_reconnect_allowed(db):
    service = PlayerService(db)
    original = service.join_player("Harsha Kumar")
    db.tables["games"][0]["status"] = "playing"
    assert service.join_player("Harsha Kumar") == {**original, "game": {"id": "game-a", "status": "playing"}}
    db.tables["players"].clear()
    with pytest.raises(AppError) as exc:
        service.join_player("Harsha Kumar")
    assert exc.value.code == "GAME_ALREADY_STARTED"
    db.tables["games"][0]["allow_late_join"] = True
    assert service.join_player("Harsha Kumar")["game"]["status"] == "playing"


def test_create_only_foundation(db):
    db.tables["games"].clear()
    result = GameService(db).create_game()
    assert result["title"] == "Jumble" and result["status"] == "lobby"
    assert not db.tables["players"]
    with pytest.raises(AppError):
        GameService(db).create_game()


def test_create_route_replaces_old_lobby_and_player_rejoins_explicitly(client, db):
    db.auth.get_user = lambda token: SimpleNamespace(user=SimpleNamespace(app_metadata={'role':'host'}))
    original = client.post('/api/player/join', json={'name':'Harsha Kumar'}).json()['data']
    old_cookie = client.cookies.get('jumble_player')
    old_player = original['player']['id']
    created = client.post('/api/host/game/create', json={'title':'Fresh'}, headers={'Authorization':'Bearer host'})
    assert created.status_code == 200
    fresh = created.json()['data']
    assert fresh['id'] != 'game-a' and fresh['status'] == 'lobby'
    state = client.get('/api/player/state', params={'player_id':old_player,'game_id':'game-a'}).json()['data']
    assert state['status'] == 'completed' and state['endedReason'] == 'replaced' and state['newGameAvailable']
    assert len(db.tables['players']) == 1  # Reading does not transfer anyone.
    joined = client.post('/api/player/join', json={'name':'Harsha Kumar'}).json()['data']
    assert joined['game']['id'] == fresh['id'] and joined['team'] == original['team']
    assert len(db.tables['players']) == 2
    # A late response carrying the old cookie does not break the new membership.
    client.cookies.set('jumble_player', old_cookie)
    response = client.get('/api/player/state', params={'player_id':joined['player']['id'],'game_id':fresh['id']})
    assert response.status_code == 200
    db.tables['players'].append({'id':'other-player','game_id':fresh['id'],'employee_id':'different-employee'})
    assert client.get('/api/player/state', params={'player_id':'other-player','game_id':fresh['id']}).status_code == 403


@pytest.mark.parametrize("path,method", [("/api/host/access", "get"), ("/api/host/lobby?game_id=game-a&host_id=fake", "get"),
                                       ("/api/host/game/create?host_id=fake", "post"), ("/api/host/game/start?game_id=game-a", "post")])
def test_host_id_not_authorization(client, path, method):
    response = getattr(client, method)(path, **({"json": {}} if method == "post" else {}))
    assert response.status_code == 403 and response.json()["error"]["code"] == "UNAUTHORIZED_HOST"


def test_host_role_must_be_server_verified(client, db):
    def get_user(token):
        if token == "bad":
            raise RuntimeError("invalid JWT")
        return SimpleNamespace(user=SimpleNamespace(app_metadata={"role": "host"} if token == "host" else {},
                                                     user_metadata={"role": "host"}))
    db.auth.get_user = get_user
    for token in ("bad", "player"):
        assert client.get("/api/host/access", headers={"Authorization": f"Bearer {token}"}).status_code == 403
    assert client.get("/api/host/access", headers={"Authorization": "Bearer host"}).status_code == 200
    response = client.post("/api/host/game/start?game_id=game-a", headers={"Authorization": "Bearer host"})
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'PLAYERS_REQUIRED'


def test_old_host_route_and_round_routes_removed(client):
    assert client.post("/api/game/host/game", json={}).status_code == 404
    assert client.post('/api/host/question/q/start?game_id=game-a').status_code == 403
    assert client.post('/api/host/round/1/start?game_id=game-a').status_code == 403


def test_public_snapshot_has_no_employee_names(client, db):
    PlayerService(db).join_player("Harsha Kumar")
    response = client.get("/api/game/state?game_id=game-a")
    assert response.status_code == 200
    assert "Harsha" not in response.text and "pending_score" not in response.text


def test_import_continues_and_uses_database_team_ids(db):
    db.insert_fail_name = "Failure"
    content = """employee_name,employee_code,team
  Pavan   Kumar  ,EMP002,titans
Hema,EMP003,  VIBE TRIBE
Other,EMP001,Ctrl Alt Defeat
Nobody,EMP004,Unknown
Failure,EMP005,Titans
Harsha Kumar,,Titans
"""
    result = import_employees(content, db)
    assert result["successful"] == 2 and result["failed"] == 4
    assert db.tables["employees"][1]["normalized_name"] == "pavan kumar"
    assert db.tables["employees"][1]["team_id"] == "team-b"
    assert "Row 4 - Duplicate employee code" in result["errors"]
    assert "Row 5 - Unknown team" in result["errors"]
    assert "private database" not in str(result)


def test_import_rejects_bad_headers(db):
    with pytest.raises(ValueError, match="employee_name"):
        import_employees("name,team\nHarsha,Titans", db)


@pytest.mark.parametrize("fault,expected", [(None, "ready"), (api_error("PGRST205"), "schema_missing"),
                                          (api_error("42501"), "connection_failed"), (RuntimeError("network"), "connection_failed")])
def test_startup_distinguishes_schema_connection_and_empty_game(db, monkeypatch, capsys, fault, expected):
    monkeypatch.setattr(main.settings, "AUTO_MIGRATE", False)
    db.tables["games"].clear()
    db.fault = fault
    monkeypatch.setattr(main, "supabase", db)
    asyncio.run(main.startup())
    assert main.app.state.database_status == expected
    output = capsys.readouterr().out
    if not fault:
        assert "connection successful" in output and "No active game" in output

@pytest.mark.parametrize('before_game', [True, False])
def test_joined_names_visible_between_signed_sessions(client, db, before_game):
    if before_game:
        db.tables['games'] = []
    db.tables['employees'].append({'id': 'employee-b', 'name': 'Kanishkaa', 'normalized_name': 'kanishkaa',
                                  'employee_code': 'EMP002', 'team_id': 'team-b', 'is_active': True})
    first = client.post('/api/player/join', json={'name': 'EMP001'}).json()['data']
    first_cookie = client.cookies.get('jumble_player')
    second = client.post('/api/player/join', json={'name': 'EMP002'}).json()['data']
    second_cookie = client.cookies.get('jumble_player')
    for joined, cookie, own_name in [(first, first_cookie, 'Harsha Kumar'), (second, second_cookie, 'Kanishkaa')]:
        client.cookies.set('jumble_player', cookie)
        result = client.get('/api/player/state', params={'player_id': joined['player']['id'], 'game_id': joined['game']['id']})
        assert result.status_code == 200
        state = result.json()['data']
        assert {p['name'] for p in state['participants']} == {'Harsha Kumar', 'Kanishkaa'}
        assert [p['name'] for p in state['participants'] if p['isYou']] == [own_name]
        assert state['joined'] == 2
        assert 'EMP001' not in str(state) and 'EMP002' not in str(state)
        assert state['teams'][0]['members'] == ['Harsha Kumar']
    if before_game:
        assert not db.tables['players']
    else:
        public = client.get('/api/game/state', params={'game_id': first['game']['id']}).json()['data']
        assert 'participants' not in public and 'Kanishkaa' not in str(public)
    client.cookies.clear()
    assert client.get('/api/player/state', params={'player_id': first['player']['id'], 'game_id': first['game']['id']}).status_code == 403


def test_waiting_presence_deduplicates_and_expires():
    from app.realtime.manager import LobbyPresence
    now = [0]
    presence = LobbyPresence(clock=lambda: now[0], ttl=30)
    presence.touch('employee-a')
    original = presence.snapshot()['employee-a']['id']
    now[0] = 10
    presence.touch('employee-a')
    presence.touch('employee-b')
    assert presence.snapshot()['employee-a']['id'] == original
    assert len(presence.snapshot()) == 2
    presence.discard('employee-b')
    now[0] = 39
    assert len(presence.snapshot()) == 1
    now[0] = 40
    assert presence.snapshot() == {}

