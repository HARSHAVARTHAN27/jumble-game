from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List


class GameCreate(BaseModel):
    title: str = Field(default="Jumble", min_length=1, max_length=200)


class GameResponse(BaseModel):
    id: str
    title: Optional[str]
    status: str
    current_round: int
    current_question: int
    total_rounds: int
    allow_late_join: bool
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class GameStatusUpdate(BaseModel):
    status: str
