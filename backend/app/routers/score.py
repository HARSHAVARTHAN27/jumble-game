from fastapi import APIRouter, Depends, Path
from supabase import Client
from typing import Optional

from app.database import supabase
from app.services.question_service import QuestionService
from app.exceptions import *


router = APIRouter(prefix="/api/host/question", tags=["host/question"])


@router.post("/{question_id}/end")
async def end_question(
    question_id: str,
    game_id: str,
    host_id: str,
):
    """End a question."""
    # Validate host
    result = supabase.from_('games').select('host_id').eq('id', game_id).single().execute()
    if not result.data or result.data['host_id'] != host_id:
        raise UNAUTHORIZED_HOST()
    
    # Service
    question_service = QuestionService(supabase)
    
    await question_service.end_question(question_id, game_id, host_id)
    
    return {
        "success": True,
        "data": {},
        "error": None,
    }


@router.post("/{question_id}/reveal-answer")
async def reveal_answer(
    question_id: str,
    game_id: str,
    host_id: str,
):
    """Reveal answer for a question."""
    # Validate host
    result = supabase.from_('games').select('host_id').eq('id', game_id).single().execute()
    if not result.data or result.data['host_id'] != host_id:
        raise UNAUTHORIZED_HOST()
    
    # Service
    question_service = QuestionService(supabase)
    
    await question_service.reveal_answer(question_id, game_id, host_id)
    
    return {
        "success": True,
        "data": {},
        "error": None,
    }


@router.post("/{question_id}/reveal-score")
async def reveal_score(
    question_id: str,
    game_id: str,
    host_id: str,
):
    """Reveal score for a question (atomic operation)."""
    # Validate host
    result = supabase.from_('games').select('host_id').eq('id', game_id).single().execute()
    if not result.data or result.data['host_id'] != host_id:
        raise UNAUTHORIZED_HOST()
    
    # Service
    question_service = QuestionService(supabase)
    
    await question_service.reveal_score(question_id, game_id, host_id)
    
    return {
        "success": True,
        "data": {},
        "error": None,
    }