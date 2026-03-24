import hashlib
import base64
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def _prehash(password: str) -> str:
    """SHA-256 prehash so bcrypt's 72-byte limit is never hit."""
    digest = hashlib.sha256(password.encode()).digest()
    return base64.b64encode(digest).decode()


def hash_password(password: str) -> str:
    return pwd_context.hash(_prehash(password))


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(_prehash(plain), hashed)


def create_access_token(subject: Any) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(subject), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: Any, token_version: int = 0) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": str(subject), "exp": expire, "ver": token_version, "type": "refresh"}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    """Decode a JWT without checking the type claim. Prefer the typed variants below."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def decode_access_token(token: str) -> dict:
    """Decode and verify this is an access token."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise JWTError("Not an access token")
    return payload


def decode_refresh_token(token: str) -> dict:
    """Decode and verify this is a refresh token."""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise JWTError("Not a refresh token")
    return payload
