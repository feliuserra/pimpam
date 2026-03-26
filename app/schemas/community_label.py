import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class LabelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str | None = None
    description: str | None = Field(default=None, max_length=200)

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not re.match(r"^#[0-9a-fA-F]{6}$", v):
            raise ValueError("Color must be a hex color like #ff5500")
        return v.lower()


class LabelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = None
    description: str | None = Field(default=None, max_length=200)

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not re.match(r"^#[0-9a-fA-F]{6}$", v):
            raise ValueError("Color must be a hex color like #ff5500")
        return v.lower()


class LabelPublic(BaseModel):
    id: int
    name: str
    color: str | None
    description: str | None
    position: int
    created_at: datetime

    model_config = {"from_attributes": True}


class LabelReorder(BaseModel):
    ids: list[int]
