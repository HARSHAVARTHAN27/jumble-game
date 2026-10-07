from pydantic import BaseModel, Field
from typing import Optional, List


class RoundCreate(BaseModel):
    round_number: int
    name: str
    game_type: str


class RoundResponse(BaseModel):
    id: str
    round_number: int
    name: str
    game_type: str
    status: str
    started_at: Optional[str]
    ended_at: Optional[str]

    class Config:
        from_attributes = True


class RoundStartRequest(BaseModel):
    pass


class RoundStatusUpdate(BaseModel):
    status: str