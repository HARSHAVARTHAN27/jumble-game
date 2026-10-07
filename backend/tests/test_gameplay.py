from copy import deepcopy
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app.exceptions import AppError
from app.schemas.content import GameContent, ROUND_TYPES, content_errors
from app.services.live_game import LiveGame
from app.services.game_rules import expression_value, points, matches
from tests.fakes import Database
from app.services.game_service import GameService


def document():
    data = [ {'rows': 3, 'cols': 3, 'cells': ['1','2','3','4','☕','6','7','8','9']},
             {'puzzle': '🕷️ + 👨'}, {'clues': ['phone', 'watch', 'laptop', 'headphones']},
             {'target': 50, 'numbers': [8,6,4,3]}, {}, {'code': 'print(404)'} ]
    answers = ['☕', 'Spider-Man', 'Apple Products', '', 'ROBOT', '404']
    return GameContent(rounds=[{'gameType': kind, 'questions': [{'id': f'q{i}', 'prompt': 'ROBOT' if kind == 'drawing' else 'Question', 'answerType': 'expression' if kind == 'target' else 'text', 'acceptedAnswers': [answers[i]] if answers[i] else [], 'data': data[i]}]} for i, kind in enumerate(ROUND_TYPES)])


@pytest.fixture
def live():
    db = Database()
    for t in db.tables['teams']:
        for i in range(3):
            db.tables['players'].append({'id': t['id'] + str(i), 'game_id': 'game-a', 'team_id': t['id'], 'employee_id': 'employee-a', 'status': 'active'})
    clock = [1000.0]
    engine = LiveGame(db, clock=lambda: clock[0])
    engine.save_content('game-a', document())
    engine.start('game-a')
    return db, engine, clock


def goto(engine, clock, index):
    for _ in range(index):
        engine.action('game-a', 'question')
        engine.action('game-a', 'end')
        engine.action('game-a', 'next')
        engine.action('game-a', 'round')
    engine.action('game-a', 'question')


def test_replacement_freezes_scores_and_rejects_all_old_updates(live):
    db, engine, clock = live
    goto(engine, clock, 1)  # Earned previous round totals remain intact.
    clock[0] += 1
    engine.submit('game-a', 'q1', 'team-a0', 'Spider-Man', 'pending')
    before = deepcopy(db.tables)
    created = GameService(db).create_game(replace_active=True)
    assert created['id'] != 'game-a' and created['status'] == 'lobby'
    _, state = engine.read('game-a')
    old = before['jumble_runtime'][0]['state']
    for field in ('scores', 'contributions', 'submissions', 'questions', 'archive'):
        assert state[field] == old[field]
    assert state['phase'] == 'completed'
    assert db.tables['players'] == before['players']
    assert db.tables['jumble_content'] == before['jumble_content']
    for operation in [lambda: engine.submit('game-a', 'q1', 'team-a0', 'Spider-Man', 'late'),
                      lambda: engine.action('game-a', 'end'),
                      lambda: engine.action('game-a', 'question')]:
        with pytest.raises(AppError) as error: operation()
        assert error.value.code == 'GAME_ENDED'
    assert not engine.write('game-a', db.tables['jumble_runtime'][0]['version'], old)
    clock[0] += 60
    engine.expire('game-a')
    assert engine.read('game-a')[1] == state
    snapshot = GameService(db).get_game_with_teams('game-a', host=True)
    assert snapshot['endedReason'] == 'replaced' and snapshot['newGameAvailable']


def test_editor_drafts_validation_and_conflict():
    db = Database(); engine = LiveGame(db)
    doc = document(); doc.rounds[0].questions.clear()
    saved = engine.save_content('game-a', doc)
    assert saved['version'] == 1 and saved['errors'][0]['path'] == 'rounds.0'
    with pytest.raises(AppError, match='draft changed'): engine.save_content('game-a', doc)
    with pytest.raises(AppError, match='Complete all six'): engine.start('game-a')


def test_memory_preparation_and_speed_and_no_double_award(live):
    db, engine, clock = live; goto(engine, clock, 0)
    snap = engine.snapshot('game-a', player_id='team-a0')
    assert snap['question']['questionData']['cells'][4] == '☕'
    with pytest.raises(AppError): engine.submit('game-a', 'q0', 'team-a0', '☕', 'before')
    clock[0] += 10
    assert 'cells' not in engine.snapshot('game-a', player_id='team-a0')['question']['questionData']
    result = engine.submit('game-a', 'q0', 'team-a0', 'coffee', 'wrong')
    assert not result['answerLocked']
    clock[0] += 5
    assert engine.submit('game-a', 'q0', 'team-a1', '☕', 'right')['answerLocked']
    assert engine.submit('game-a', 'q0', 'team-a1', '☕', 'right') is not None
    clock[0] = 1040
    engine.expire('game-a')
    _, state = engine.read('game-a')
    assert state['phase'] == 'score_revealed' and state['scores']['team-a'] == 25
    engine.action('game-a', 'scores'); engine.expire('game-a')
    assert engine.read('game-a')[1]['scores']['team-a'] == 25
    with pytest.raises(AppError): engine.submit('game-a', 'q0', 'team-b0', '☕', 'late')
    with pytest.raises(AppError): engine.save_content('game-a', document())


def test_first_correct_bonus_and_grading_recompute(live):
    db, engine, clock = live; goto(engine, clock, 1)
    engine.submit('game-a', 'q1', 'team-a0', 'Spiderman', 'a')
    clock[0] += 1
    engine.submit('game-a', 'q1', 'team-b0', 'Spider-Man', 'b')
    engine.submit('game-a', 'q1', 'team-c0', 'Spider-Man', 'c')
    clock[0] += 29; engine.expire('game-a')
    s = engine.read('game-a')[1]
    assert s['scores'] == {'team-a': 0, 'team-b': 30, 'team-c': 20}
    engine.review('game-a', s['submissions'][0]['id'], True)
    assert engine.read('game-a')[1]['scores'] == {'team-a': 30, 'team-b': 20, 'team-c': 20}
    engine.review('game-a', s['submissions'][0]['id'], True)
    assert engine.read('game-a')[1]['scores']['team-a'] == 30


def test_connection_clue_projection_and_tier(live):
    _, engine, clock = live; goto(engine, clock, 2)
    assert engine.snapshot('game-a')['question']['questionData']['clues'] == ['phone']
    clock[0] += 14
    assert len(engine.snapshot('game-a')['question']['questionData']['clues']) == 3
    engine.submit('game-a', 'q2', 'team-a0', 'APPLE   PRODUCTS', 'a')
    engine.action('game-a', 'end')
    assert engine.read('game-a')[1]['scores']['team-a'] == 20


def test_target_best_result_and_integer_rules(live):
    _, engine, clock = live; goto(engine, clock, 3)
    engine.submit('game-a', 'q3', 'team-a0', '(8 * 6) + 4 - 3', 'a')
    clock[0] += 1
    engine.submit('game-a', 'q3', 'team-a1', '8 * 6', 'b')
    engine.action('game-a', 'end')
    assert engine.read('game-a')[1]['scores']['team-a'] == 30
    assert expression_value('(8*6)+4-3', [8,6,4,3]) == 49


@pytest.mark.parametrize('expression', ['8+8', '2**6', '__import__("os")', '8/(6-6)', '8/3', '50', '-8', 'True', '(8).real', '8//3'])
def test_expression_rejects_unsafe_or_invalid_input(expression):
    with pytest.raises(AppError): expression_value(expression, [8,6,4,3])


def test_drawing_secret_team_canvas_and_rotation(live):
    db, engine, clock = live; goto(engine, clock, 4)
    s = engine.read('game-a')[1]; artist = s['artists']['team-a']; other = next(p['id'] for p in db.tables['players'] if p['team_id'] == 'team-a' and p['id'] != artist)
    assert engine.snapshot('game-a', player_id=artist)['question']['questionData']['secretCard'] == 'ROBOT'
    assert 'ROBOT' not in str(engine.snapshot('game-a', player_id=other))
    assert engine.snapshot('game-a', host=True)['question']['questionData']['secretCard'] == 'ROBOT'
    with pytest.raises(AppError): engine.submit('game-a', 'q4', artist, 'ROBOT', 'artist-answer')
    clock[0] += 10
    assert 'secretCard' not in engine.snapshot('game-a', player_id=artist)['question']['questionData']
    stroke = {'id': 'stroke-a', 'color': '#000000', 'width': 4, 'points': [[0, 0], [1, 1]]}
    engine.stroke('game-a', 'q4', artist, stroke)
    assert engine.snapshot('game-a', player_id=other)['question']['questionData']['strokes'] == [stroke]
    assert engine.snapshot('game-a', player_id='team-b0')['question']['questionData']['strokes'] == []
    with pytest.raises(AppError): engine.stroke('game-a', 'q4', other, stroke)
    clock[0] += 16
    engine.submit('game-a', 'q4', other, 'robot', 'guess')
    clock[0] += 14; engine.expire('game-a')
    assert engine.read('game-a')[1]['scores']['team-a'] == 20
    assert engine.read('game-a')[1]['usedArtists']['team-a'] == [artist]


def test_technical_multiple_questions_before_finish(live):
    db, engine, clock = live
    # Add a second technical question to test that round six doesn't finish early.
    row = db.tables['jumble_runtime'][0]
    second = {**deepcopy(row['state']['questions'][-1]), 'id': 'q6', 'number': 2, 'hard': True}
    row['state']['questions'].append(second)
    goto(engine, clock, 5)
    engine.action('game-a', 'end')
    with pytest.raises(AppError): engine.action('game-a', 'finish')
    engine.action('game-a', 'next'); engine.action('game-a', 'question')
    engine.submit('game-a', 'q6', 'team-a0', '404', 'answer')
    clock[0] += 30; engine.expire('game-a')
    assert engine.read('game-a')[1]['scores']['team-a'] == 60
    engine.action('game-a', 'finish')
    assert db.tables['games'][0]['status'] == 'completed'


def test_reassigned_artist_card_expiry_and_original_deadline(live):
    db, engine, clock = live; goto(engine, clock, 4)
    s = engine.read('game-a')[1]
    first = s['artists']['team-a']; deadline = s['deadline']
    second = next(p['id'] for p in db.tables['players'] if p['team_id'] == 'team-a' and p['id'] != first)
    clock[0] += 12
    engine.reassign('game-a', 'team-a', second)
    assert engine.read('game-a')[1]['deadline'] == deadline
    snap = engine.snapshot('game-a', player_id=second)
    assert snap['question']['questionData']['secretCard'] == 'ROBOT'
    assert snap['question']['questionData']['cardExpiresAt']
    with pytest.raises(AppError): engine.submit('game-a', 'q4', first, 'ROBOT', 'old-artist')
    clock[0] += 10
    assert 'secretCard' not in engine.snapshot('game-a', player_id=second)['question']['questionData']
    assert engine.snapshot('game-a', host=True)['question']['questionData']['secretCard'] == 'ROBOT'


def test_empty_answer_variants_are_removed_before_reveal():
    db = Database(); engine = LiveGame(db)
    doc = document(); doc.rounds[1].questions[0].acceptedAnswers = ['', 'Spider-Man', '  ']
    saved = engine.save_content('game-a', doc)
    assert saved['rounds'][1]['questions'][0]['acceptedAnswers'] == ['Spider-Man']


def test_receipt_ids_bound_to_player_and_optimistic_retry(live):
    db, engine, clock = live; goto(engine, clock, 1)
    engine.submit('game-a', 'q1', 'team-a0', 'wrong', 'same-id')
    engine.submit('game-a', 'q1', 'team-b0', 'wrong', 'same-id')
    s = engine.read('game-a')[1]
    assert len({a['id'] for a in s['submissions']}) == 2
    original = engine.write; failures = [1]
    def write(*args, **kwargs):
        if failures[0]: failures[0] -= 1; return False
        return original(*args, **kwargs)
    engine.write = write
    engine.action('game-a', 'end')
    assert engine.read('game-a')[1]['phase'] == 'score_revealed'


@pytest.mark.parametrize('kind,elapsed,expected', [('memory',5,25),('memory',5.001,20),('connection',6.99,40),('connection',7,30),('connection',14,20),('connection',21,10),('drawing',15,30),('drawing',15.001,20),('drawing',29.99,20)])
def test_scoring_boundaries(kind, elapsed, expected):
    assert points(kind, elapsed) == expected


def test_output_case_and_spacing():
    q = {'answerType': 'output', 'acceptedAnswers': ['True\n  404']}
    assert matches(q, 'True\r\n  404')
    assert not matches(q, 'true\n 404')


def test_content_and_submission_routes_require_authentication(live, monkeypatch):
    from app import main
    from app.routers import live as routes
    from app.utils import validators
    db, engine, clock = live
    monkeypatch.setattr(routes, 'engine', engine)
    monkeypatch.setattr(validators, 'supabase', db)
    db.auth.get_user = lambda token: SimpleNamespace(user=SimpleNamespace(app_metadata={'role': 'host'} if token == 'host' else {}))
    client = TestClient(main.app, raise_server_exceptions=False)
    assert client.get('/api/host/game/content?game_id=game-a').status_code == 403
    assert client.get('/api/host/game/content?game_id=game-a', headers={'Authorization': 'Bearer host'}).status_code == 200
    body = {'answer': 'ROBOT', 'requestId': 'spoof'}
    assert client.post('/api/player/question/q4/submit?game_id=game-a&player_id=team-a0', json=body).status_code == 403
    with client.websocket_connect('/api/player/live?game_id=game-a&player_id=team-a0', headers={'origin': validators.settings.FRONTEND_URL}) as websocket:
        with pytest.raises(Exception): websocket.receive_json()
