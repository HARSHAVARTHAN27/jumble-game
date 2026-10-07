"""Play the complete imported bank against the existing persistent engine."""
import json
from pathlib import Path
import pytest
from app.exceptions import AppError
from app.schemas.content import GameContent, content_errors
from app.services.live_game import LiveGame
from app.services.question_bank import question_bank
from app.services.game_rules import expression_value, score_question
from tests.fakes import Database


def engine_fixture():
    db = Database()
    for team in db.tables['teams']:
        for i in range(3):
            db.tables['players'].append(dict(id=team['id'] + str(i), game_id='game-a', team_id=team['id'], status='active'))
    now = [1000.0]
    engine = LiveGame(db, clock=lambda: now[0])
    engine.start('game-a')  # New lobbies receive the bank without a database seed.
    return engine, now


def test_complete_bank_flow_privacy_timers_scoring_and_rotation():
    bank = question_bank()
    assert not content_errors(bank)
    assert len(bank['rounds']) == 6
    engine, clock = engine_fixture()
    artists = {t: [] for t in ['team-a', 'team-b', 'team-c']}
    root = Path(__file__).resolve().parents[2]
    for ri, round_ in enumerate(bank['rounds']):
        assert len(round_['questions']) == 7
        assert [q['isDemo'] for q in round_['questions']] == [True] + [False] * 6
        if ri:
            assert engine.snapshot('game-a')['phase'] == 'between'
            engine.action('game-a', 'round')
        for qi, q in enumerate(round_['questions']):
            kind = round_['gameType']
            intro = engine.snapshot('game-a', player_id='team-a0')
            assert intro['phase'] == 'intro'
            assert intro['question']['number'] == qi
            assert intro['question']['scoredCount'] == 6
            if kind == 'memory': assert q['prompt'] not in intro['question']['question']
            before = engine.read('game-a')[1]['scores'].copy()
            engine.action('game-a', 'question')
            snap = engine.snapshot('game-a', player_id='team-a0')
            assert 'correctAnswer' not in snap['question'] and 'hostAnswer' not in snap['question']
            assert 'acceptedAnswers' not in json.dumps(snap)
            assert engine.snapshot('game-a', host=True)['question']['hostAnswer']
            player = 'team-a0'
            if kind in ('memory', 'drawing'):
                assert snap['question']['durationSeconds'] == q['memoryTime']
                if kind == 'memory':
                    assert snap['question']['questionData']['image'] == q['data']['image']
                    assert (root / 'frontend/public' / q['data']['image'].lstrip('/')).is_file()
                    assert q['prompt'] not in snap['question']['question']
                else:
                    state = engine.read('game-a')[1]
                    for team, artist in state['artists'].items(): artists[team].append(artist)
                    player = next(f'team-a{i}' for i in range(3) if f'team-a{i}' != state['artists']['team-a'])
                    teammate = engine.snapshot('game-a', player_id=player)
                    assert q['prompt'] not in json.dumps(teammate)
                    assert engine.snapshot('game-a', player_id=state['artists']['team-a'])['question']['questionData']['secretCard'] == q['prompt']
                clock[0] += q['memoryTime']
                assert 'image' not in engine.snapshot('game-a', player_id=player)['question']['questionData']
            if kind == 'connection':
                assert len(snap['question']['questionData']['clues']) == 1
                engine.action('game-a', 'clue')
                assert len(engine.snapshot('game-a', player_id=player)['question']['questionData']['clues']) == 2
            answer = q['data']['exampleSolution'] if kind == 'target' else q['acceptedAnswers'][0]
            clock[0] += 1
            engine.submit('game-a', q['id'], player, answer, f'answer-{q["id"]}')
            if q['lockAfterAttempt']:
                assert engine.snapshot('game-a', player_id='team-a1')['player']['hasSubmitted']
            clock[0] = engine.read('game-a')[1]['deadline']
            engine.expire('game-a')
            closed = engine.snapshot('game-a', player_id=player)
            assert closed['phase'] == 'score_revealed'
            assert closed['question']['correctAnswer']
            if q['isDemo']:
                assert closed['scores'] == before
                assert all(v['points'] == 0 and v['playerId'] is None for v in closed['gains'].values())
            else: assert closed['scores']['team-a'] > before['team-a']
            with pytest.raises(AppError): engine.submit('game-a', q['id'], player, answer, 'late')
            engine.action('game-a', 'next')
        if ri < 5: assert engine.snapshot('game-a')['phase'] == 'between'
    assert engine.snapshot('game-a')['phase'] == 'completed'
    for selected in artists.values():
        assert len(set(selected[:3])) == 3
        assert len(set(selected[3:6])) == 3


def test_bank_target_all_numbers_operators_and_team_ranking():
    for q in question_bank()['rounds'][3]['questions']:
        assert expression_value(q['data']['exampleSolution'], q['data']['numbers'], q['data']['operators'], True) == q['data']['target']
    with pytest.raises(AppError): expression_value('8 * 4', [8, 6, 4, 2], use_all=True)
    with pytest.raises(AppError): expression_value('8 * 4', [8, 4], ['+'], True)
    with pytest.raises(AppError): expression_value('__import__("os")', [8, 4], use_all=True)
    q = question_bank()['rounds'][3]['questions'][1]
    subs = [dict(id=t, playerId=t+'0', teamId=t, distance=d, receivedAt=i, sequence=i, elapsed=2, correct=False) for i, (t, d) in enumerate([('a', 3), ('b', 8), ('c', 1)])]
    result = score_question(q, 'target', subs, ['a','b','c'])
    assert [result[t]['points'] for t in ['a','b','c']] == [20, 10, 30]
    subs[0]['distance'] = 0
    assert [score_question(q, 'target', subs, ['a','b','c'])[t]['points'] for t in ['a','b','c']] == [40, 0, 0]


def test_wrong_memory_and_technical_team_answers_lock():
    for ri in [0, 5]:
        engine, clock = engine_fixture()
        def move(s): s['index'] = ri * 7 + 1
        engine.mutate('game-a', move)
        engine.action('game-a', 'question')
        q = engine.read('game-a')[1]['questions'][ri * 7 + 1]
        clock[0] += q['memoryTime'] if ri == 0 else 0
        wrong = 'wrong' if ri == 0 else q['options'][0]
        assert engine.submit('game-a', q['id'], 'team-a0', wrong, 'first')['answerLocked']
        clock[0] += 1
        with pytest.raises(AppError): engine.submit('game-a', q['id'], 'team-a1', q['acceptedAnswers'][0], 'retry')
