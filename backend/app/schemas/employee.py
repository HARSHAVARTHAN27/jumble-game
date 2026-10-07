from pydantic import BaseModel, Field
from typing import Optional, List


class EmployeeImportRow(BaseModel):
    employee_name: str = Field(..., min_length=1, max_length=100)
    employee_code: Optional[str] = Field(default=None, max_length=50)
    team: str = Field(..., min_length=1, max_length=50)


class EmployeeImportResult(BaseModel):
    total: int
    successful: int
    failed: int
    errors: List[str]


class EmployeeImportError(BaseModel):
    row: int
    message: str


class EmployeeResponse(BaseModel):
    id: str
    name: str
    normalized_name: str
    employee_code: Optional[str]
    team_name: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class EmployeeNormalize(BaseModel):
    original: str
    normalized: str