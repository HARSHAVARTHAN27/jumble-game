from pydantic import BaseModel, Field, AliasChoices, ConfigDict, model_validator
from typing import Optional, List


class PlayerJoinRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(default=None, min_length=1, max_length=100, validation_alias=AliasChoices("name", "identifier"))
    employee_code: Optional[str] = Field(default=None, max_length=50, validation_alias=AliasChoices("employeeCode", "employee_code"))

    @model_validator(mode="after")
    def require_identity(self):
        self.name = self.name.strip() if self.name else None
        self.employee_code = self.employee_code.strip() if self.employee_code else None
        if not self.name and not self.employee_code:
            raise ValueError("Enter your name or employee ID")
        return self


class PlayerResponse(BaseModel):
    id: str
    name: str
    team_id: Optional[str]
    team_name: Optional[str]
    status: str
    joined_at: str
    last_seen_at: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class PlayerReconnectRequest(BaseModel):
    pass


class PlayerStateResponse(BaseModel):
    player: PlayerResponse
    team_name: Optional[str]
    game_id: str
    current_round: int
    current_question: int
    individual_score: "ScoreSummary"
    submission_status: dict
    answer_locked: bool
    score_status: str


class ScoreSummary(BaseModel):
    committed_score: float = 0
    pending_score: float = 0
    total_score: float = 0

    model_config = ConfigDict(from_attributes=True)
