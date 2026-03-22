from pydantic import BaseModel, field_validator


class VoteCreate(BaseModel):
    direction: int

    @field_validator("direction")
    @classmethod
    def must_be_one_or_minus_one(cls, v: int) -> int:
        if v not in (1, -1):
            raise ValueError("direction must be 1 or -1")
        return v


class VotePublic(BaseModel):
    post_id: int
    direction: int

    model_config = {"from_attributes": True}
