from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DeviceTokenCreate(BaseModel):
    token: str = Field(min_length=1, max_length=500)
    platform: Literal["ios", "android", "web"]


class DeviceTokenPublic(BaseModel):
    id: int
    token: str
    platform: str
    created_at: datetime

    model_config = {"from_attributes": True}
