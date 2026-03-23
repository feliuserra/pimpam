"""
TOTP (Time-based One-Time Password) utilities for 2FA.

Uses pyotp (RFC 6238) for code generation/verification and Fernet (AES-128-CBC +
HMAC-SHA256, from the cryptography library) to encrypt secrets before storing
them in the database.

The encryption key is derived from settings.encryption_key and is kept separate
from the JWT secret so they can be rotated independently.
"""
import base64
import hashlib

import pyotp
from cryptography.fernet import Fernet

from app.core.config import settings


def _fernet() -> Fernet:
    """Return a Fernet instance keyed from the app's encryption_key setting."""
    raw = hashlib.sha256(settings.encryption_key.encode()).digest()  # 32 bytes
    return Fernet(base64.urlsafe_b64encode(raw))


def generate_totp_secret() -> str:
    """Return a fresh random base32 TOTP secret."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, username: str) -> str:
    """
    Return an otpauth:// provisioning URI suitable for QR code generation.
    The client renders this as a QR code that authenticator apps can scan.
    """
    return pyotp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name="PimPam",
    )


def verify_totp_code(secret: str, code: str) -> bool:
    """
    Verify a 6-digit TOTP code. Allows ±1 time-step (30 s) of clock drift
    to account for minor device/server clock skew.
    """
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def encrypt_totp_secret(secret: str) -> str:
    """AES-encrypt a plaintext TOTP secret for storage."""
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_totp_secret(encrypted: str) -> str:
    """Decrypt an AES-encrypted TOTP secret retrieved from the database."""
    return _fernet().decrypt(encrypted.encode()).decode()
