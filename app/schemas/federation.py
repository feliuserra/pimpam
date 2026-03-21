from datetime import datetime

from pydantic import BaseModel


class RemoteActorCreate(BaseModel):
    ap_id: str
    username: str
    domain: str
    inbox_url: str
    shared_inbox_url: str | None = None
    public_key_pem: str
    actor_json: str


class RemoteActorRead(RemoteActorCreate):
    fetched_at: datetime

    model_config = {"from_attributes": True}
