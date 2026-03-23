from fastapi import APIRouter, HTTPException, Request, status

from app.core.dependencies import CurrentUser, DBSession
from app.core.limiter import limiter
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.core.totp import (
    decrypt_totp_secret,
    encrypt_totp_secret,
    generate_totp_secret,
    get_totp_uri,
    verify_totp_code,
)
from app.crud.user import authenticate_user, create_user, get_user_by_email, get_user_by_username
from app.schemas.token import RefreshRequest, TokenPair
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
    return await create_user(db, data)


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
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshRequest):
    """Exchange a valid refresh token for a new token pair."""
    from jose import JWTError

    try:
        payload = decode_token(data.refresh_token)
        user_id = payload.get("sub")
        if user_id is None:
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    return TokenPair(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


# ---------------------------------------------------------------------------
# 2FA — TOTP endpoints
# ---------------------------------------------------------------------------

@router.post("/totp/setup", response_model=TotpSetupResponse, status_code=status.HTTP_201_CREATED)
async def totp_setup(current_user: CurrentUser, db: DBSession):
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
async def totp_verify(data: TotpVerifyRequest, current_user: CurrentUser, db: DBSession):
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
async def totp_disable(data: TotpDisableRequest, current_user: CurrentUser, db: DBSession):
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
