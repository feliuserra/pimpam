from datetime import datetime

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class ReportPublic(BaseModel):
    id: int
    reporter_id: int
    content_type: str
    content_id: int
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}
