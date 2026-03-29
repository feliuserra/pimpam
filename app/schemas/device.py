from datetime import datetime

from pydantic import BaseModel, Field


class DeviceRegister(BaseModel):
    device_name: str = Field(max_length=100)
    public_key: str  # base64-encoded SPKI — validated server-side


class DevicePublic(BaseModel):
    id: int
    device_name: str
    public_key: str
    public_key_fingerprint: str
    is_active: bool
    created_at: datetime
    last_seen_at: datetime

    model_config = {"from_attributes": True}


class DeviceKeyPublic(BaseModel):
    """Returned to senders — just what they need to encrypt for this device."""

    device_id: int
    public_key: str
    public_key_fingerprint: str


class DeviceRename(BaseModel):
    device_name: str = Field(max_length=100)


class BackupUpload(BaseModel):
    encrypted_private_key: str = Field(max_length=5000)
    salt: str = Field(max_length=44)
    kdf: str = "argon2id"
    kdf_params: str  # JSON string, e.g. {"memory":65536,"iterations":3,"parallelism":1}


class BackupDownload(BaseModel):
    encrypted_private_key: str
    salt: str
    kdf: str
    kdf_params: str

    model_config = {"from_attributes": True}
