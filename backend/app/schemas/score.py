from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ScoreSummary(BaseModel):
    committed_score: float = Field(default=0)
    pending_score: float = Field(default=0)
    total_score: float = Field(default=0)

    class Config:
        from_attributes = True


class PlayerScoreDetail(BaseModel):
    player_id: str
    name: str
    team_name: str
    committed_score: float
    pending_score: float
    correct_answers: int
    total_answers: int
    average_response_time: Optional[int] = None

    class Config:
        from_attributes = True


class TeamRoundScore(BaseModel):
    team_id: str
    team_name: str
    raw_score: float
    normalized_score: float
    active_player_count: int

    class Config:
        from_attributes = True


class LeaderboardEntry(BaseModel):
    rank: int
    team_name: str
    score: float
    round_gain: float

    class Config:
        from_attributes = True


class SubmissionResponse(BaseModel):
    id: str
    answer: Any
    is_correct: Optional[bool]
    calculated_points: float
    score_status: str
    submitted_at: str
    response_time_ms: Optional[int]

    class Config:
        from_attributes = True