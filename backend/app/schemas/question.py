from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class QuestionCreate(BaseModel):
    round_id: str
    question_number: int
    question_type: str
    question_text: str = Field(..., min_length=1)
    options: Optional[List[str]] = Field(default=None)
    duration_seconds: int = Field(default=20)
    max_points: float = Field(default=100)


class QuestionData(BaseModel):
    question_text: str
    options: Optional[List[str]] = None
    correct_answer: Optional[List] = None


class QuestionResponse(BaseModel):
    id: str
    question_number: int
    question_type: str
    question_text: str
    options: Optional[List[str]]
    duration_seconds: int
    max_points: float
    status: str
    started_at: Optional[str]
    ended_at: Optional[str]
    answer_revealed_at: Optional[str]
    score_revealed_at: Optional[str]

    class Config:
        from_attributes = True


class QuestionSubmitRequest(BaseModel):
    answer: str = Field(..., min_length=1, max_length=200)


class QuestionCurrentResponse(BaseModel):
    id: str
    question: str
    options: Optional[List[str]]
    durationSeconds: int

    class Config:
        from_attributes = True