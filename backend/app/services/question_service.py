from supabase import Client
from typing import Optional, Dict, Any
from app.exceptions import *


class QuestionService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def start_question(self, question_id: str, game_id: str, host_id: str) -> dict:
        """Start a question - validate host, game, round."""
        # Validate host
        from .services.game_service import GameService
        game_service = GameService(self.supabase)
        host_valid = await game_service.validate_host(game_id, host_id)
        if not host_valid:
            raise UNAUTHORIZED_HOST()

        # Validate active game
        active_game = await game_service.get_active_game()
        if not active_game or active_game['id'] != game_id:
            raise NO_ACTIVE_GAME()

        # Validate active round
        round_number = active_game['current_round'] if active_game else 0
        round_result = self.supabase.from_('rounds').select('status').eq('game_id', game_id).eq('round_number', round_number).single().execute()
        round_data = round_result.data
        if not round_data or round_data['status'] != 'active':
            raise ROUND_NOT_ACTIVE()

        # Get question and check it's not already active/ended
        question_result = self.supabase.from_('questions').select('*').eq('id', question_id).eq('round_id', f"round_{round_number}").single().execute()
        question = question_result.data
        if not question:
            raise QUESTION_NOT_ACTIVE()

        if question['status'] not in ('waiting', 'active'):
            raise QUESTION_ALREADY_ENDED()

        # Set question status = active
        self.supabase.from_('questions').update({"status": "active", "started_at": "now()"}).eq('id', question_id).execute()

        # Update current question
        self.supabase.from_('games').update({"current_question": int(question_id.split('_')[-1]) if '_' in question_id else 1}).eq('id', game_id).execute()

        # Publish QUESTION_STARTED event
        await self.publish_realtime(game_id, "QUESTION_STARTED", {"question_id": question_id})

        return {
            "question_id": question_id,
            "status": "active",
        }

    async def get_current_question(self, game_id: str, round_number: int) -> Optional[dict]:
        """Get current question data for players (without correct answer)."""
        question_result = self.supabase.from_('questions').select('*, rounds(round_number)').eq('game_id', game_id).eq('round_id', f"round_{round_number}").eq('status', 'active').single().execute()
        question = question_result.data
        if not question:
            return None

        # Build response without correct_answer
        response = {
            "id": question['id'],
            "question": question['question_text'],
            "options": question.get('question_data', {}).get('options'),
            "durationSeconds": question.get('duration_seconds', 20),
        }
        return response

    async def submit_answer(self, question_id: str, player_id: str, answer: str, game_id: str) -> dict:
        """Submit answer for a question."""
        # Find the question and round
        question_result = self.supabase.from_('questions').select('*, rounds(game_id), rounds(round_number)').eq('id', question_id).single().execute()
        question = question_result.data
        if not question:
            raise QUESTION_NOT_ACTIVE()

        round_number = question['round_id']['round_number'] if question.get('round_id') else 0

        # Check duplicate submission
        existing = self.supabase.from_('submissions').select('*').eq('player_id', player_id).eq('question_id', question_id).execute()
        if existing.data:
            raise ANSWER_ALREADY_SUBMITTED("Player")

        # Calculate response time and points
        # Get question start time
        question_started = question.get('started_at')
        if question_started:
            from datetime import datetime
            start_dt = datetime.fromisoformat(question_started.replace('Z', '+00:00'))
            now_dt = datetime.utcnow()
            response_time_ms = int((now_dt - start_dt).total_seconds() * 1000)
        else:
            response_time_ms = 0

        # Check answer correctness (we need correct_answer from question)
        correct_answer = question.get('correct_answer')
        is_correct = answer == correct_answer if correct_answer else False

        # Calculate points using scoring service
        from .services.scoring_service import ScoringService
        scoring = ScoringService(self.supabase)
        points = await scoring.calculate_points(
            question_id=question_id,
            response_time_ms=response_time_ms,
            is_correct=is_correct
        )

        # Insert submission
        submission_data = {
            "game_id": game_id,
            "round_id": f"round_{round_number}",
            "question_id": question_id,
            "player_id": player_id,
            "team_id": (await self.supabase.from_('players').select('team_id').eq('id', player_id).single().execute()).data['team_id'],
            "answer": answer,
            "response_time_ms": response_time_ms,
            "is_correct": is_correct,
            "calculated_points": points,
            "score_status": "pending",
        }
        self.supabase.from_('submissions').insert(submission_data).execute()

        # Increase player.pending_score
        player_result = self.supabase.from_('players').select('pending_score').eq('id', player_id).single().execute()
        current_pending = player_result.data['pending_score'] if player_result.data else 0
        self.supabase.from_('players').update({"pending_score": current_pending + points}).eq('id', player_id).execute()

        # Update player_round_scores pending_score
        round_score_result = self.supabase.from_('player_round_scores').select('pending_score').eq('player_id', player_id).eq('round_id', f"round_{round_number}").single().execute()
        round_score = round_score_result.data if round_score_result.data else None
        if round_score:
            self.supabase.from_('player_round_scores').update({
                "pending_score": round_score['pending_score'] + points,
                "total_answers": round_score['total_answers'] + 1,
            }).eq('player_id', player_id).eq('round_id', f"round_{round_number}").execute()
        else:
            self.supabase.from_('player_round_scores').insert({
                "player_id": player_id,
                "round_id": f"round_{round_number}",
                "pending_score": points,
                "committed_score": 0,
                "total_answers": 1,
                "correct_answers": 1 if is_correct else 0,
            }).execute()

        # Return answer locked
        return {
            "success": True,
            "data": {
                "answerLocked": True,
            }
        }

    async def get_current_question_player(self, game_id: str, round_number: int) -> Optional[dict]:
        """Get current question for players (before reveal)."""
        question_result = self.supabase.from_('questions').select('*, rounds(round_number)').eq('game_id', game_id).eq('round_id', f"round_{round_number}").eq('status', 'active').single().execute()
        question = question_result.data
        if not question:
            return None

        return {
            "id": question['id'],
            "question": question['question_text'],
            "options": question.get('question_data', {}).get('options'),
            "durationSeconds": question.get('duration_seconds', 20),
        }

    async def end_question(self, question_id: str, host_id: str) -> dict:
        """End a question - set status = ended."""
        # Validate host
        from .services.game_service import GameService
        game_service = GameService(self.supabase)
        host_valid = await game_service.validate_host(question_id, host_id)  # This won't work, need game_id
        # Actually need to get game_id from question first
        question_result = self.supabase.from_('questions').select('game_id').eq('id', question_id).single().execute()
        game_id = question_result.data['game_id']
        host_valid = await game_service.validate_host(game_id, host_id)
        if not host_valid:
            raise UNAUTHORIZED_HOST()

        # Set question status = ended
        self.supabase.from_('questions').update({"status": "ended", "ended_at": "now()"}).eq('id', question_id).execute()

        # Publish QUESTION_ENDED event
        await self.publish_realtime(game_id, "QUESTION_ENDED", {"question_id": question_id})

        return {"status": "ended"}

    async def reveal_answer(self, question_id: str, game_id: str, host_id: str) -> dict:
        """Reveal answer - set status = answer_revealed."""
        # Validate host
        from .services.game_service import GameService
        game_service = GameService(self.supabase)
        host_valid = await game_service.validate_host(game_id, host_id)
        if not host_valid:
            raise UNAUTHORIZED_HOST()

        # Set question status = answer_revealed
        self.supabase.from_('questions').update({"status": "answer_revealed", "answer_revealed_at": "now()"}).eq('id', question_id).execute()

        # Publish ANSWER_REVEALED event
        await self.publish_realtime(game_id, "ANSWER_REVEALED", {"question_id": question_id})

        return {"status": "answer_revealed"}

    async def reveal_score(self, question_id: str, game_id: str, host_id: str) -> dict:
        """Reveal score - atomic operation."""
        # Validate host
        from .services.game_service import GameService
        game_service = GameService(self.supabase)
        host_valid = await game_service.validate_host(game_id, host_id)
        if not host_valid:
            raise UNAUTHORIZED_HOST()

        # Use RPC for atomic score reveal
        from .utils.validators import validate_active_game
        await validate_active_game(self.supabase, game_id)

        # Call the RPC function for score reveal
        result = self.supabase.rpc('reveal_question_score', {
            "p_question_id": question_id,
            "p_game_id": game_id,
        }).execute()

        return {"status": "score_revealed", "data": result.data if result.data else {}}

    async def publish_realtime(self, game_id: str, event: str, payload: dict) -> None:
        """Publish a realtime event to the game channel."""
        self.supabase.channel(f"game:{game_id}").send({
            "event": event,
            "payload": payload,
        })

    async def get_host_question_status(self, game_id: str, host_id: str) -> dict:
        """Get host question status."""
        # Validate host
        from .services.game_service import GameService
        game_service = GameService(self.supabase)
        host_valid = await game_service.validate_host(game_id, host_id)
        if not host_valid:
            raise UNAUTHORIZED_HOST()

        # Get current round
        active_game = await game_service.get_active_game()
        round_number = active_game['current_round'] if active_game else 0

        # Get current question
        question_result = self.supabase.from_('questions').select('*, rounds(round_number)').eq('game_id', game_id).eq('round_id', f"round_{round_number}").single().execute()
        question = question_result.data

        # Get submissions count
        submissions_result = self.supabase.from_('submissions').select('*, players(team_id), rounds(round_number)').eq('game_id', game_id).eq('round_id', f"round_{round_number}").execute()
        total_submissions = len(submissions_result.data) if submissions_result.data else 0

        # Get submissions per team
        teams_data = {}
        teams_result = self.supabase.from_('game_teams').select('*, teams(name)').eq('game_id', game_id).execute()
        for team in teams_result.data:
            team_name = team['teams']['name']
            teams_data[team_name.lower()] = {
                "submitted": 0,
                "players": team['player_count'] or 0,
            }

        # Count submissions per team
        for sub in submissions_result.data:
            player_result = self.supabase.from_('players').select('team_id').eq('id', sub['player_id']).single().execute()
            player_team = player_result.data['team_id']
            team_name_res = self.supabase.from_('teams').select('name').eq('id', player_team).single().execute()
            team_key = team_name_res.data['name'].lower() if team_name_res.data else None
            if team_key and team_key in teams_data:
                teams_data[team_key]["submitted"] += 1

        return {
            "current_round": round_number,
            "current_question": question['question_number'] if question else 0,
            "server_timer_state": "active" if question and question['status'] == 'active' else "waiting",
            "submitted": total_submissions,
            "totalPlayers": active_game['total_rounds'] if active_game else 0,
            "teams": teams_data,
        }

    async def get_leaderboard(self, game_id: str) -> list:
        """Get leaderboard for a game."""
        # Get team round scores
        result = self.supabase.from_('team_round_scores').select('*, teams(name)').eq('game_id', game_id).execute()

        leaderboard = []
        for i, ts in enumerate(result.data):
            leaderboard.append({
                "rank": i + 1,
                "teamName": ts['teams']['name'],
                "score": ts['normalized_score'] or 0,
                "roundGain": ts['raw_score'] or 0,
            })

        # Sort by normalized_score descending
        leaderboard.sort(key=lambda x: x['score'], reverse=True)
        # Re-rank
        for i, entry in enumerate(leaderboard):
            entry['rank'] = i + 1

        return leaderboard