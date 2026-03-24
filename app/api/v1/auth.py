from fastapi import APIRouter, HTTPException, Request, status

from app.core.dependencies import CurrentUser, DBSession, UnverifiedCurrentUser
from app.core.email import send_password_reset_email, send_verification_email
from app.core.limiter import limiter
from app.core.search import index_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.totp import (
    decrypt_totp_secret,
    encrypt_totp_secret,
    generate_totp_secret,
    get_totp_uri,
    verify_totp_code,
)
from app.crud.password_reset import consume_reset_token, count_recent_requests, create_reset_token
from app.crud.user import authenticate_user, create_user, get_user_by_email, get_user_by_id, get_user_by_username, record_consent
from app.schemas.token import ChangePasswordRequest, PasswordResetConfirm, PasswordResetRequest, RefreshRequest, TokenPair
from app.schemas.user import TotpDisableRequest, TotpSetupResponse, TotpVerifyRequest, UserCreate, UserLogin, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(request: Request, data: UserCreate, db: DBSession):
    """Register a new account. Rate-limited to prevent abuse."""
    if await get_user_by_username(db, data.username):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Username already taken")
    if await get_user_by_email(db, data.email):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")
    user = await create_user(db, data)
    await index_user(user)
    # Record GDPR consent at registration
    client_ip = request.client.host if request.client else None
    for consent_type in ("terms_of_service", "privacy_policy", "age_confirmation"):
        await record_consent(db, user.id, consent_type, version="1.0", ip=client_ip)
    # Send email verification — fire and forget
    try:
        raw_token = _create_verification_token(user)
        await db.commit()
        await send_verification_email(user.email, raw_token)
    except Exception:
        pass
    return user


@router.post("/login", response_model=TokenPair)
@limiter.limit("20/minute")
async def login(request: Request, data: UserLogin, db: DBSession):
    """
    Authenticate and receive a JWT access + refresh token pair.

    If the account has 2FA enabled, include ``totp_code`` in the request body.
    Without it the server returns ``401`` with ``detail: "totp_required"`` so the
    client knows to prompt the user for their authenticator code.
    """
    user = await authenticate_user(db, data.username, data.password)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if user.totp_enabled:
        if not data.totp_code:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="totp_required")
        secret = decrypt_totp_secret(user.totp_secret)
        if not verify_totp_code(secret, data.totp_code):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect TOTP code")

    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id, user.token_version),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshRequest, db: DBSession):
    """
    Exchange a valid refresh token for a new token pair.

    Returns ``401`` if the token is invalid, expired, or has been revoked
    (e.g. after a password reset).
    """
    from jose import JWTError

    try:
        payload = decode_token(data.refresh_token)
        user_id = int(payload["sub"])
        token_version = int(payload.get("ver", 0))
    except (JWTError, KeyError, ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    if user.token_version != token_version:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id, user.token_version),
    )


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: UnverifiedCurrentUser, db: DBSession):
    """
    Invalidate all outstanding refresh tokens for the current account.

    The client should discard its access and refresh tokens after calling this.
    Any previously issued refresh tokens will be rejected on the next refresh attempt.
    """
    current_user.token_version += 1
    await db.commit()


# ---------------------------------------------------------------------------
# Change password (authenticated)
# ---------------------------------------------------------------------------

@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(data: ChangePasswordRequest, current_user: UnverifiedCurrentUser, db: DBSession):
    """
    Change password for the currently authenticated user.

    Requires the existing password for confirmation. On success, all outstanding
    refresh tokens are invalidated — the client must log in again.
    """
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect current password")

    current_user.hashed_password = hash_password(data.new_password)
    current_user.token_version += 1
    await db.commit()

    return {"detail": "Password updated. Please log in again."}


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("20/minute")
async def password_reset_request(request: Request, data: PasswordResetRequest, db: DBSession):
    """
    Request a password reset email.

    Returns ``404`` if no account exists with that email address.
    Rate-limited to 3 requests per hour per account to prevent email flooding.

    ``mode='link'`` sends a clickable URL valid for 15 minutes.
    ``mode='code'`` sends a 6-digit code valid for 10 minutes (useful for mobile clients).
    """
    from app.core.config import settings as cfg

    user = await get_user_by_email(db, data.email)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No account with that email address")

    recent = await count_recent_requests(db, user.id)
    if recent >= cfg.password_reset_max_requests_per_hour:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests. Try again later.",
        )

    raw_token = await create_reset_token(db, user.id, data.mode)
    try:
        await send_password_reset_email(user.email, raw_token, data.mode)
    except Exception:
        pass  # email failure must never surface to the caller

    return {"detail": "Password reset email sent"}


@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
async def password_reset_confirm(data: PasswordResetConfirm, db: DBSession):
    """
    Complete a password reset using the token or code from the reset email.

    On success, the password is updated and all existing refresh tokens are
    invalidated. The user must log in again to obtain a new token pair.
    2FA settings are left unchanged.

    Returns ``400`` if the token is invalid, already used, or expired.
    """
    token_row = await consume_reset_token(db, data.token)
    if token_row is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user = await get_user_by_id(db, token_row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user.hashed_password = hash_password(data.new_password)
    user.token_version += 1  # invalidate all outstanding refresh tokens
    await db.commit()

    return {"detail": "Password updated. Please log in again."}


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

def _create_verification_token(user) -> str:
    """Generate a verification token, store its hash on the user, and return the raw token."""
    import hashlib
    import secrets
    from datetime import timedelta, timezone
    from datetime import datetime as _dt

    from app.core.config import settings as cfg

    raw = secrets.token_urlsafe(32)
    user.email_verification_token_hash = hashlib.sha256(raw.encode()).hexdigest()
    user.email_verification_token_expires_at = _dt.now(timezone.utc) + timedelta(
        minutes=cfg.email_verification_token_expire_minutes
    )
    return raw


@router.get("/verify", status_code=status.HTTP_200_OK)
async def verify_email(token: str, db: DBSession):
    """
    Verify an email address using the token from the verification email.

    Sets the account as verified, allowing full platform access.
    Returns ``400`` if the token is invalid or expired.
    """
    import hashlib
    from datetime import datetime, timezone

    from sqlalchemy import select as _select

    from app.models.user import User as _User

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await db.execute(
        _select(_User).where(_User.email_verification_token_hash == token_hash)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token")

    expires = user.email_verification_token_expires_at
    if expires is not None:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token")

    user.is_verified = True
    user.email_verification_token_hash = None
    user.email_verification_token_expires_at = None
    await db.commit()

    return {"detail": "Email verified. You now have full access."}


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("5/hour")
async def resend_verification(request: Request, current_user: UnverifiedCurrentUser, db: DBSession):
    """
    Resend the email verification link.

    Returns ``400`` if the account is already verified.
    Rate-limited to 5 per hour per account.
    """
    if current_user.is_verified:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Account is already verified")

    raw_token = _create_verification_token(current_user)
    await db.commit()
    try:
        await send_verification_email(current_user.email, raw_token)
    except Exception:
        pass

    return {"detail": "Verification email sent"}


# ---------------------------------------------------------------------------
# 2FA — TOTP endpoints
# ---------------------------------------------------------------------------

@router.post("/totp/setup", response_model=TotpSetupResponse, status_code=status.HTTP_201_CREATED)
async def totp_setup(current_user: UnverifiedCurrentUser, db: DBSession):
    """
    Generate a TOTP secret and return the provisioning URI for QR code display.

    2FA is **not yet active** after this call — the user must confirm they can
    produce a valid code by calling ``POST /auth/totp/verify``.

    Returns ``409`` if 2FA is already enabled (disable it first).
    """
    if current_user.totp_enabled:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="2FA is already enabled. Disable it with DELETE /auth/totp/disable before re-enrolling.",
        )

    secret = generate_totp_secret()
    current_user.totp_secret = encrypt_totp_secret(secret)
    await db.commit()

    return TotpSetupResponse(
        uri=get_totp_uri(secret, current_user.username),
        secret=secret,
    )


@router.post("/totp/verify", status_code=status.HTTP_200_OK)
async def totp_verify(data: TotpVerifyRequest, current_user: UnverifiedCurrentUser, db: DBSession):
    """
    Confirm a TOTP code to activate 2FA on the account.

    Call this after ``POST /auth/totp/setup`` once the user has scanned the QR
    code and their authenticator app is producing codes.
    """
    if current_user.totp_enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="2FA is already enabled.")
    if not current_user.totp_secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Call POST /auth/totp/setup first.")

    secret = decrypt_totp_secret(current_user.totp_secret)
    if not verify_totp_code(secret, data.code):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid TOTP code.")

    current_user.totp_enabled = True
    await db.commit()
    return {"detail": "2FA enabled."}


@router.post("/totp/disable", status_code=status.HTTP_200_OK)
async def totp_disable(data: TotpDisableRequest, current_user: UnverifiedCurrentUser, db: DBSession):
    """
    Disable 2FA on the account.

    Requires both the current account password and a valid TOTP code to prevent
    an attacker with a hijacked session from silently disabling 2FA.
    """
    if not current_user.totp_enabled:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="2FA is not enabled.")
    if not verify_password(data.password, current_user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect password.")

    secret = decrypt_totp_secret(current_user.totp_secret)
    if not verify_totp_code(secret, data.code):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid TOTP code.")

    current_user.totp_secret = None
    current_user.totp_enabled = False
    await db.commit()
    return {"detail": "2FA disabled."}
