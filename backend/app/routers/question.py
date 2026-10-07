from fastapi import APIRouter, Depends, Path
from supabase import Client
from typing import Optional

from app.database import supabase
from app.schemas.question import QuestionSubmitRequest, QuestionCurrentResponse
from app.services.question_service import QuestionService
from app.exceptions import *


router = APIRouter(prefix="/api/host/question", tags=["host/question"])


@router.post("/{question_id}/start")
async def start_question(
    question_id: str,
    game_id: str,
    host_id: str,
):
    """Start a question."""
    # Validate host
    result = supabase.from_('games').select('host_id').eq('id', game_id).single().execute()
    if not result.data or result.data['host_id'] != host_id:
        raise UNAUTHORIZED_HOST()
    
    # Validate active game
    active = supabase.from_('games').select('*').eq('id', game_id).execute()
    if not active.data or active.data[0]['status'] != 'playing':
        raise NO_ACTIVE_GAME()
    
    # Service
    from ...app.services.question_service import QuestionService
    question_service = QuestionService(supabase)
    
    await question_service.start_question(question_id, game_id, host_id)
    
    return {
        "success": True,
        "data": {},
        "error": None,
    }


@router.get("/current")
async def get_current_question(game_id: str):
    """Get current question for players."""
    from ...app.services.question_service import QuestionService
    question_service = QuestionService(supabase)
    
    round_number = 1  # Would get from game state
    question = await question_service.get_current_question(game_id, round_number)
    
    if not question:
        raise QUESTION_NOT_ACTIVE()
    
    return {
        "success": True,
        "data": question,
        "error": None,
    }


@router.post("/{question_id}/submit", response_model=dict)
async def submit_answer(
    question_id: str,
    request: QuestionSubmitRequest,
    game_id: str,
    # player_id would come from auth in production
    player_id: str = "player-uuid-123",
):
    """Submit answer for a question."""
    # Service
    from ...app.services.question_service import QuestionService
    question_service = QuestionService(supabase)
    
    result = await question_service.submit_answer(question_id, player_id, request.answer, game_id)
    
    return result