import asyncio
from uuid import uuid4
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect, UploadFile
from pydantic import BaseModel, Field, ConfigDict
from app.database import supabase
from app.config import settings
from app.exceptions import AppError
from app.schemas.content import GameContent, content_errors
from app.services.live_game import LiveGame
from app.services.game_service import GameService
from app.services.player_service import PlayerService
from app.utils.validators import require_host, require_player_session

host_router = APIRouter(prefix='/api/host', tags=['content and gameplay'], dependencies=[Depends(require_host)])
player_router = APIRouter(prefix='/api/player', tags=['gameplay'])
socket_router = APIRouter()
engine = LiveGame(supabase)

def ok(data):
    return {'success': True, 'data': data, 'error': None}

class Answer(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)
    requestId: str = Field(min_length=1, max_length=80)

class Review(BaseModel):
    correct: bool

class Stroke(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1, max_length=80)
    color: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')
    width: int = Field(ge=1, le=20)
    points: list[tuple[float, float]] = Field(min_length=1, max_length=500)

class Artist(BaseModel):
    teamId: str
    playerId: str

@host_router.get('/game/content')
def get_content(game_id: str):
    return ok(engine.content(game_id))

@host_router.get('/game/content/bank')
def get_bank(game_id: str):
    from app.services.question_bank import question_bank
    return ok(question_bank(engine.content(game_id)['version']))

@host_router.post('/game/clue')
def reveal_clue(game_id: str):
    return ok(engine.action(game_id, 'clue'))

@host_router.put('/game/content')
def save_content(game_id: str, content: GameContent):
    return ok(engine.save_content(game_id, content))

@host_router.get('/game/content/validate')
def validate_content(game_id: str):
    errors = content_errors(engine.content(game_id))
    return ok({'ready': not errors, 'errors': errors})

@host_router.post('/game/content/image')
async def upload_image(game_id: str, file: UploadFile):
    if engine.game(game_id)['status'] not in ('draft', 'lobby'):
        raise AppError('CONTENT_LOCKED', 'Images cannot change after starting.', 409)
    data = await file.read(5242881)
    if len(data) > 5242880: raise AppError('CONTENT_INVALID', 'Images must be at most 5 MB.')
    if data.startswith(b'\x89PNG\r\n\x1a\n'): ext, mime = 'png', 'image/png'
    elif data.startswith(b'\xff\xd8\xff'): ext, mime = 'jpg', 'image/jpeg'
    elif data.startswith(b'RIFF') and data[8:12] == b'WEBP': ext, mime = 'webp', 'image/webp'
    else: raise AppError('CONTENT_INVALID', 'Upload a PNG, JPEG, or WebP image.')
    path = f'{game_id}/{uuid4()}.{ext}'
    await asyncio.to_thread(engine.db.storage.from_('jumble-grid').upload, path, data, {'content-type': mime})
    return ok({'cell': 'image:' + path, 'url': engine.image_url(path)})

@host_router.get('/game/content/image')
def preview_image(game_id: str, path: str):
    engine.game(game_id)
    if not path.startswith(game_id + '/') or '..' in path:
        raise AppError('CONTENT_INVALID', 'Invalid game image path.')
    return ok({'url': engine.image_url(path)})

@host_router.post('/question/{question_id}/{action}')
def question_action(question_id: str, action: str, game_id: str):
    actions = {'start': 'question', 'end': 'end', 'reveal-answer': 'answer', 'reveal-score': 'scores'}
    if action not in actions: raise AppError('INVALID_ACTION', 'Unknown question action.')
    return ok(engine.action(game_id, actions[action], question_id=question_id))

@host_router.post('/round/{round_id}/{action}')
def round_action(round_id: str, action: str, game_id: str):
    if action not in ('start', 'complete'): raise AppError('INVALID_ACTION', 'Unknown round action.')
    return ok(engine.action(game_id, 'round' if action == 'start' else 'complete', round_id=round_id))

@host_router.post('/game/next-question')
def next_question(game_id: str):
    return ok(engine.action(game_id, 'next'))

@host_router.post('/game/finish')
def finish(game_id: str):
    return ok(engine.action(game_id, 'finish'))

@host_router.post('/game/replay')
def replay(game_id: str):
    if engine.game(game_id)['status'] != 'completed': raise AppError('INVALID_PHASE', 'Finish the game first.')
    document = engine.content(game_id)
    created = GameService(engine.db).create_game(engine.game(game_id)['title'])
    # Give replayed grids their own private assets so authoring checks remain scoped.
    for round_ in document['rounds']:
        for question in round_['questions']:
            for field in ('cells', 'clues'):
                values = question['data'].get(field, [])
                for i, value in enumerate(values):
                    if value.startswith('image:'):
                        old_path = value[6:]
                        new_path = created['id'] + '/' + str(uuid4()) + '.' + old_path.rsplit('.', 1)[-1]
                        engine.db.storage.from_('jumble-grid').copy(old_path, new_path)
                        values[i] = 'image:' + new_path
    engine.save_content(created['id'], GameContent(**{**document, 'version': 0}))
    return ok(created)

@host_router.post('/game/review/{submission_id}')
def review(submission_id: str, game_id: str, body: Review):
    return ok(engine.review(game_id, submission_id, body.correct))

@host_router.post('/game/artist')
def reassign(game_id: str, body: Artist):
    return ok(engine.reassign(game_id, body.teamId, body.playerId))

@player_router.post('/question/{question_id}/submit')
def submit(request: Request, question_id: str, game_id: str, player_id: str, body: Answer):
    require_player_session(request, player_id, game_id)
    return ok(engine.submit(game_id, question_id, player_id, body.answer, body.requestId))

@player_router.post('/question/{question_id}/stroke')
def stroke(request: Request, question_id: str, game_id: str, player_id: str, body: Stroke):
    require_player_session(request, player_id, game_id)
    if any(not 0 <= v <= 1 for point in body.points for v in point):
        raise AppError('CONTENT_INVALID', 'Drawing points must be within the canvas.')
    return ok(engine.stroke(game_id, question_id, player_id, body.model_dump()))

async def serve_socket(websocket, game_id, player_id=None):
    origin = websocket.headers.get('origin')
    allowed = {settings.FRONTEND_URL}
    if settings.ENVIRONMENT == 'development': allowed.add('http://localhost:5173')
    if origin not in allowed:
        await websocket.close(code=1008); return
    await websocket.accept()
    try:
        token = None
        players = PlayerService(engine.db)
        games = GameService(engine.db)
        verified_until = 0
        if player_id:
            require_player_session(websocket, player_id, game_id)
            await asyncio.to_thread(engine.player, game_id, player_id)
        else:
            frame = await asyncio.wait_for(websocket.receive_json(), 10)
            token = frame.get('token')
        while True:
            if player_id:
                require_player_session(websocket, player_id, game_id)
                data = await asyncio.to_thread(players.get_player_state, player_id, game_id)
            else:
                if engine.clock() >= verified_until:
                    user = await asyncio.to_thread(engine.db.auth.get_user, token)
                    if not user.user or user.user.app_metadata.get('role') != 'host': break
                    verified_until = engine.clock() + 30
                data = await asyncio.to_thread(games.get_game_with_teams, game_id, True)
            await websocket.send_json(ok(data))
            await asyncio.sleep(1)
    except (WebSocketDisconnect, AppError, asyncio.TimeoutError, RuntimeError):
        pass
    except Exception:
        pass  # Clients recover using authenticated REST snapshots.
    finally:
        try: await websocket.close(code=1008)
        except RuntimeError: pass

@socket_router.websocket('/api/player/live')
async def player_live(websocket: WebSocket, game_id: str, player_id: str):
    await serve_socket(websocket, game_id, player_id)

@socket_router.websocket('/api/host/live')
async def host_live(websocket: WebSocket, game_id: str):
    await serve_socket(websocket, game_id)

async def deadline_worker():
    while True:
        try:
            rows = await asyncio.to_thread(lambda: engine.db.from_('games').select('id').eq('status', 'playing').execute().data)
            for row in rows: await asyncio.to_thread(engine.expire, row['id'])
        except Exception:
            pass  # Missing migration is surfaced by host content endpoints.
        await asyncio.sleep(.5)
