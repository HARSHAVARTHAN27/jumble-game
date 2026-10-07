"""Persistent six-round engine using optimistic, transactional PostgreSQL writes."""
import json
import random
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4
from app.exceptions import AppError, NO_ACTIVE_GAME, UNAUTHORIZED
from app.schemas.content import GameContent, ROUND_NAMES, content_errors, empty_content
from .game_rules import matches, expression_value, score_question
from .question_bank import question_bank


def timestamp():
    return datetime.now(timezone.utc).timestamp()


def iso(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


class LiveGame:
    def __init__(self, db, clock=timestamp):
        self.db, self.clock = db, clock
        self.signed_images = {}

    def game(self, game_id):
        rows = self.db.from_('games').select('*').eq('id', game_id).execute().data
        if not rows: raise NO_ACTIVE_GAME()
        return rows[0]

    def content(self, game_id):
        self.game(game_id)
        rows = self.db.from_('jumble_content').select('*').eq('game_id', game_id).execute().data
        return {**rows[0]['document'], 'version': rows[0]['version']} if rows else question_bank()

    def save_content(self, game_id, content: GameContent):
        document = content.model_dump(exclude={'version'})
        for round_ in document['rounds']:
            for question in round_['questions']:
                question['acceptedAnswers'] = [answer for answer in question['acceptedAnswers'] if answer.strip()]
        if len(json.dumps(document)) > 1000000:
            raise AppError('CONTENT_INVALID', 'Game content exceeds 1 MB.')
        for round_ in document['rounds']:
            for q in round_['questions']:
                for field in ('cells', 'clues'):
                    for value in q['data'].get(field, []):
                        if isinstance(value, str) and value.startswith('image:'):
                            path = value[6:]
                            if not path.startswith(game_id + '/') or '..' in path:
                                raise AppError('CONTENT_INVALID', 'Use images uploaded for this game.')
        if self.game(game_id)['status'] not in ('draft', 'lobby'):
            raise AppError('CONTENT_LOCKED', 'Content cannot be changed after the game starts.', 409)
        saved = self.db.rpc('jumble_save_content', {'p_game': game_id, 'p_expected': content.version, 'p_document': document}).execute().data
        if not saved: raise AppError('CONTENT_CONFLICT', 'The draft changed. Reload it before saving.', 409)
        return {**document, 'version': content.version + 1, 'errors': content_errors(document)}

    def read(self, game_id):
        rows = self.db.from_('jumble_runtime').select('*').eq('game_id', game_id).execute().data
        return (rows[0]['version'], deepcopy(rows[0]['state'])) if rows else (0, None)

    def write(self, game_id, version, state, content_version=None):
        phase = state['phase']
        status = 'completed' if phase == 'completed' else 'playing'
        q = state['questions'][state['index']]
        return self.db.rpc('jumble_write_runtime', {
            'p_game': game_id, 'p_expected': version, 'p_state': state, 'p_status': status,
            'p_round': q['round'] + 1, 'p_question': q['number'], 'p_content_version': content_version,
        }).execute().data

    def start(self, game_id):
        game = self.game(game_id)
        if game['status'] != 'lobby': raise AppError('GAME_ALREADY_STARTED', 'Game already started.', 409)
        doc = self.content(game_id)
        if doc['version'] == 0:
            self.save_content(game_id, GameContent(**doc))
            doc = self.content(game_id)
        errors = content_errors(doc)
        if errors: raise AppError('ROUND_CONTENT_REQUIRED', 'Complete all six rounds before starting.', 409)
        players = self.db.from_('players').select('*').eq('game_id', game_id).execute().data
        if not players: raise AppError('PLAYERS_REQUIRED', 'Wait for players to join.')
        # Each drawing team needs a guesser as well as an artist.
        teams = [t['id'] for t in self.db.from_('teams').select('id').execute().data]
        if any(sum(p['team_id'] == t for p in players) < 2 for t in teams):
            raise AppError('PLAYERS_REQUIRED', 'Each team needs at least two players for Draw & Guess.')
        state = {'questions': [{**q, 'kind': r['gameType'], 'round': i, 'number': 0 if q.get('isDemo') else sum(not prev.get('isDemo') for prev in r['questions'][:j+1]), 'scoredCount': sum(not v.get('isDemo') for v in r['questions'])} for i, r in enumerate(doc['rounds']) for j, q in enumerate(r['questions'])],
                 'index': 0, 'phase': 'intro', 'scores': {t: 0 for t in teams}, 'baseScores': {t: 0 for t in teams},
                 'contributions': {}, 'baseContributions': {}, 'gains': {}, 'usedArtists': {}, 'artists': {}, 'drawings': {},
                 'submissions': [], 'overrides': {}, 'archive': [], 'sequence': 0}
        if not self.write(game_id, 0, state, doc['version']):
            raise AppError('CONTENT_CONFLICT', 'Content changed while starting. Reload and retry.', 409)
        return {'started': True}

    def mutate(self, game_id, fn):
        for _ in range(8):
            if self.game(game_id)['status'] == 'completed':
                raise AppError('GAME_ENDED', 'This session has ended. Join the new lobby to play again.', 409)
            version, state = self.read(game_id)
            if state is None: raise AppError('QUESTION_NOT_ACTIVE', 'The game has not started.', 409)
            result = fn(state)
            if self.write(game_id, version, state): return result
        raise AppError('GAME_BUSY', 'Another update is in progress. Please retry.', 409)

    def close(self, state):
        q = state['questions'][state['index']]
        gains = score_question(q, q['kind'], state['submissions'], state['scores'], state['overrides'])
        state['gains'] = gains
        state['scores'] = {t: state['baseScores'][t] + gains[t]['points'] for t in gains}
        state['contributions'] = dict(state['baseContributions'])
        for gain in gains.values():
            if gain['playerId']:
                pid = gain['playerId']
                state['contributions'][pid] = state['contributions'].get(pid, 0) + gain['points']
        state['phase'] = 'score_revealed'

    def expire(self, game_id):
        version, state = self.read(game_id)
        if state and state['phase'] == 'active' and self.clock() >= state['deadline']:
            def end(s):
                if s['phase'] == 'active' and self.clock() >= s['deadline']: self.close(s)
            try:
                self.mutate(game_id, end)
            except AppError as exc:
                if exc.code != 'GAME_ENDED': raise

    def action(self, game_id, action, question_id=None, round_id=None):
        def perform(s):
            q = s['questions'][s['index']]
            if question_id and question_id != q['id']:
                raise AppError('QUESTION_NOT_ACTIVE', 'This is not the current question.', 409)
            if round_id and round_id != str(q['round'] + 1):
                raise AppError('ROUND_NOT_ACTIVE', 'This is not the current round.', 409)
            if action == 'round':
                if s['phase'] == 'between': s['phase'] = 'intro'
                elif s['phase'] != 'intro': raise AppError('INVALID_PHASE', 'The next round is not ready.', 409)
            elif action == 'question':
                if s['phase'] == 'active': return {'ok': True}
                if s['phase'] != 'intro': raise AppError('INVALID_PHASE', 'Start from the question introduction.', 409)
                now = self.clock()
                prep = q.get('memoryTime', 10) if q['kind'] in ('memory', 'drawing') else 0
                s.update(phase='active', startedAt=now, answerStartsAt=now + prep, deadline=now + prep + q.get('answerTime', 30),
                         baseScores=dict(s['scores']), baseContributions=dict(s['contributions']))
                if q['kind'] == 'drawing':
                    players = self.db.from_('players').select('*').eq('game_id', game_id).execute().data
                    for team in s['scores']:
                        eligible = [p['id'] for p in players if p['team_id'] == team and p.get('status') != 'disconnected']
                        if len(eligible) < 2: raise AppError('PLAYERS_REQUIRED', 'Each team needs an artist and a guesser.')
                        used = s['usedArtists'].setdefault(team, [])
                        available = [p for p in eligible if p not in used]
                        if not available: used.clear(); available = eligible
                        artist = random.choice(available)
                        used.append(artist)
                        s['artists'][team] = artist
                        s.setdefault('cardUntil', {})[team] = now + 10
                        s.setdefault('questionArtists', {})[team] = [artist]
                        s['drawings'][team] = []
            elif action in ('end', 'answer', 'scores'):
                if s['phase'] == 'score_revealed': return {'ok': True}
                if s['phase'] != 'active': raise AppError('INVALID_PHASE', 'No question is running.', 409)
                self.close(s)
            elif action == 'clue':
                if s['phase'] != 'active' or q['kind'] != 'connection': raise AppError('INVALID_PHASE', 'No connection question is running.', 409)
                automatic = min(4, int((self.clock() - s['answerStartsAt']) // 7) + 1)
                s['clueCount'] = min(4, max(s.get('clueCount', 1), automatic) + 1)
            elif action in ('next', 'complete', 'finish'):
                if s['phase'] != 'score_revealed': raise AppError('INVALID_PHASE', 'Finish this question first.', 409)
                if s['index'] == len(s['questions']) - 1:
                    s['phase'] = 'completed'
                elif action == 'finish':
                    raise AppError('INVALID_PHASE', 'There are questions remaining.', 409)
                else:
                    old_round = q['round']
                    s['archive'].append({'questionId': q['id'], 'submissions': s['submissions'], 'gains': s['gains'], 'overrides': s['overrides']})
                    s['index'] += 1
                    s.update(submissions=[], overrides={}, gains={}, artists={}, drawings={}, cardUntil={}, questionArtists={}, clueCount=1)
                    s['phase'] = 'between' if s['questions'][s['index']]['round'] != old_round else 'intro'
            else: raise AppError('INVALID_ACTION', 'Unknown game action.')
            return {'ok': True}
        return self.mutate(game_id, perform)

    def player(self, game_id, player_id):
        rows = self.db.from_('players').select('*').eq('id', player_id).eq('game_id', game_id).execute().data
        if not rows: raise UNAUTHORIZED()
        return rows[0]

    def submit(self, game_id, question_id, player_id, answer, request_id):
        player = self.player(game_id, player_id)
        now = self.clock()
        def perform(s):
            q = s['questions'][s['index']]
            duplicate = next((a for a in s['submissions'] if a.get('requestId') == request_id and a['playerId'] == player_id), None)
            if duplicate: return {'answerLocked': False}
            if q['id'] != question_id or s['phase'] != 'active' or not s['answerStartsAt'] <= now < s['deadline']:
                raise AppError('QUESTION_NOT_ACTIVE', 'Answers are accepted only during the configured answering phase.', 409)
            team = player['team_id']
            if q['kind'] == 'drawing' and player_id in s.get('questionArtists', {}).get(team, [s['artists'].get(team)]):
                raise AppError('ARTIST_CANNOT_GUESS', 'The artist draws; teammates guess.', 403)
            attempts = [a for a in s['submissions'] if a['playerId'] == player_id]
            if len(attempts) >= 100 or (attempts and now - attempts[-1]['receivedAt'] < .5):
                raise AppError('RATE_LIMITED', 'Wait a moment before another attempt.', 429)
            if q['kind'] != 'target' and any(a['correct'] and a['teamId'] == team for a in s['submissions']):
                return {'answerLocked': True}
            if q.get('lockAfterAttempt') and any(a['teamId'] == team for a in s['submissions']):
                raise AppError('ANSWER_ALREADY_SUBMITTED', 'Your team answer is locked.', 409)
            if q['answerType'] == 'mcq' and answer not in q['options']:
                raise AppError('CONTENT_INVALID', 'Select one of the displayed choices.')
            distance = abs(expression_value(answer, q['data']['numbers'], q['data'].get('operators'), q['data'].get('useAllNumbers', False)) - q['data']['target']) if q['kind'] == 'target' else None
            s['sequence'] += 1
            sub = {'id': str(uuid4()), 'requestId': request_id, 'answer': answer, 'playerId': player_id, 'teamId': team,
                   'receivedAt': now, 'elapsed': now - s['answerStartsAt'], 'sequence': s['sequence'],
                   'correct': distance == 0 if q['kind'] == 'target' else matches(q, answer)}
            if distance is not None: sub['distance'] = distance
            if q['kind'] == 'connection':
                sub['clueNumber'] = max(s.get('clueCount', 1), min(4, int(sub['elapsed'] // 7) + 1))
                sub['elapsed'] = max(sub['elapsed'], (sub['clueNumber'] - 1) * 7)
            s['submissions'].append(sub)
            return {'answerLocked': q.get('lockAfterAttempt', False) or (sub['correct'] and q['kind'] != 'target')}
        return self.mutate(game_id, perform)

    def review(self, game_id, submission_id, correct):
        def perform(s):
            if s['phase'] != 'score_revealed': raise AppError('INVALID_PHASE', 'Review after the question closes.', 409)
            if s['questions'][s['index']]['answerType'] not in ('text', 'output'):
                raise AppError('INVALID_ACTION', 'Only text/output grading can be reviewed.')
            if not any(a['id'] == submission_id for a in s['submissions']):
                raise AppError('SUBMISSION_NOT_FOUND', 'Submission not found.', 404)
            s['overrides'][submission_id] = correct
            self.close(s)
            return {'ok': True}
        return self.mutate(game_id, perform)

    def stroke(self, game_id, question_id, player_id, stroke):
        player = self.player(game_id, player_id)
        now = self.clock()
        def perform(s):
            team = player['team_id']
            if s['questions'][s['index']]['id'] != question_id or s['phase'] != 'active' or s['questions'][s['index']]['kind'] != 'drawing' or not s['answerStartsAt'] <= now < s['deadline']:
                raise AppError('QUESTION_NOT_ACTIVE', 'Drawing is closed.', 409)
            if s['artists'].get(team) != player_id: raise UNAUTHORIZED()
            strokes = s['drawings'].setdefault(team, [])
            if any(v['id'] == stroke['id'] for v in strokes): return {'ok': True}
            if len(strokes) >= 500: raise AppError('DRAWING_LIMIT', 'Canvas stroke limit reached.')
            strokes.append(stroke)
            return {'ok': True}
        return self.mutate(game_id, perform)

    def reassign(self, game_id, team_id, player_id):
        player = self.player(game_id, player_id)
        def perform(s):
            if s['phase'] != 'active' or s['questions'][s['index']]['kind'] != 'drawing' or self.clock() >= s['deadline']:
                raise AppError('QUESTION_NOT_ACTIVE', 'No drawing question is active.')
            if player['team_id'] != team_id or s['artists'].get(team_id) == player_id: raise UNAUTHORIZED()
            members = self.db.from_('players').select('id').eq('game_id', game_id).eq('team_id', team_id).execute().data
            seen = s.setdefault('questionArtists', {}).setdefault(team_id, [s['artists'].get(team_id)])
            if not any(p['id'] not in seen and p['id'] != player_id for p in members):
                raise AppError('PLAYERS_REQUIRED', 'Keep at least one teammate who has not seen the card available to guess.')
            seen.append(player_id)
            s['artists'][team_id] = player_id
            s.setdefault('cardUntil', {})[team_id] = self.clock() + 10
            s['usedArtists'].setdefault(team_id, []).append(player_id)
            return {'ok': True}
        return self.mutate(game_id, perform)

    def image_url(self, path):
        cached = self.signed_images.get(path)
        if not cached or cached[0] < self.clock():
            result = self.db.storage.from_('jumble-grid').create_signed_url(path, 60)
            self.signed_images[path] = (self.clock() + 45, result['signedURL'])
        return self.signed_images[path][1]

    def snapshot(self, game_id, host=False, player_id=None):
        self.expire(game_id)
        _, s = self.read(game_id)
        if not s: return None
        q = s['questions'][s['index']]
        now = self.clock()
        player = self.player(game_id, player_id) if player_id else None
        team = player['team_id'] if player else None
        phase = s['phase']
        revealed = phase in ('score_revealed', 'completed')
        active = phase == 'active'
        prep = active and now < s['answerStartsAt']
        data = {}
        if q['kind'] == 'memory' and prep:
            data = {**q['data'], 'cells': [self.image_url(c[6:]) if c.startswith('image:') else c for c in q['data']['cells']]}
        elif q['kind'] == 'connection' and active:
            count = max(s.get('clueCount', 1), min(4, int((now - s['answerStartsAt']) // 7) + 1))
            data = {'clues': [self.image_url(c[6:]) if c.startswith('image:') else c for c in q['data']['clues'][:count]]}
        elif q['kind'] not in ('memory', 'connection', 'drawing'):
            data = {k: q['data'][k] for k in ('puzzle', 'target', 'numbers', 'code', 'image', 'operators', 'useAllNumbers') if k in q['data']}
        if q['kind'] == 'drawing':
            data = {'isArtist': bool(player and s['artists'].get(team) == player_id)}
            if host or (data['isArtist'] and active and now < s.get('cardUntil', {}).get(team, s.get('answerStartsAt', 0))):
                data['secretCard'] = q['prompt']
                if not host: data['cardExpiresAt'] = iso(min(s['deadline'], s.get('cardUntil', {}).get(team, s['answerStartsAt'])))
            if host: data['canvases'] = s['drawings']; data['artists'] = s['artists']
            elif team: data['strokes'] = s['drawings'].get(team, []); data['artistId'] = s['artists'].get(team)
        question = {'id': q['id'], 'question': 'Draw the secret card' if q['kind'] == 'drawing' else 'Remember this visual' if q['kind'] == 'memory' and (prep or phase in ('intro', 'between')) else q['prompt'],
                    'questionType': q['answerType'], 'gameType': q['kind'], 'questionData': data,
                    'options': q['options'] if not prep else [], 'number': q['number'],
                    'isDemo': q.get('isDemo', False), 'scoredCount': q.get('scoredCount', 6), 'instructions': q.get('instructions', ''), 'lockAfterAttempt': q.get('lockAfterAttempt', False),
                    'durationSeconds': q.get('memoryTime', 10) if prep else q.get('answerTime', 30),
                    'startedAt': iso(s['startedAt'] if prep else s.get('answerStartsAt', now)),
                    'subphase': 'prepare' if prep else 'answer', 'deadline': iso(s.get('deadline', now))}
        if revealed or host: question['correctAnswer'] = q['data'].get('exampleSolution') or str(q['data']['target']) if q['kind'] == 'target' else q['acceptedAnswers'][0]
        if host: question['hostAnswer'] = question['correctAnswer']
        submissions = s['submissions']
        out = {'phase': phase, 'endedReason': s.get('endedReason'), 'round': q['round'] + 1, 'roundId': str(q['round'] + 1), 'roundName': ROUND_NAMES[q['round']],
               'roundDescription': '30 seconds to answer. Every team counts.', 'question': question,
               'serverTime': iso(now), 'submitted': len({a['playerId'] for a in submissions}),
               'isLastQuestion': s['index'] == len(s['questions']) - 1, 'scores': s['scores'],
               'gains': s['gains'], 'teamSubmitted': {t: len({a['playerId'] for a in submissions if a['teamId'] == t}) for t in s['scores']}}
        if player:
            own = [a for a in submissions if a['playerId'] == player_id]
            solved = (any(a['correct'] and a['teamId'] == team for a in submissions) and q['kind'] != 'target') or (q.get('lockAfterAttempt') and any(a['teamId'] == team for a in submissions))
            gain = s['gains'].get(team, {})
            out['player'] = {'score': s['contributions'].get(player_id, 0), 'previousScore': s['baseContributions'].get(player_id, 0),
                             'hasSubmitted': solved, 'attemptCount': len(own),
                             'earnedPoints': gain.get('points', 0) if gain.get('playerId') == player_id else 0,
                             'isCorrect': bool(any(s['overrides'].get(a['id'], a['correct']) for a in own)) if revealed else None}
        if host:
            out['reviewSubmissions'] = [{**a, 'correct': s['overrides'].get(a['id'], a['correct'])} for a in submissions]
        return out
