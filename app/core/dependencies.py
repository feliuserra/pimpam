from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_session

bearer = HTTPBearer()
bearer_optional = HTTPBearer(auto_error=False)

# Reusable type aliases — import these in route files
DBSession = Annotated[AsyncSession, Depends(get_session)]


async def _get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
    db: DBSession,
):
    # Import here to avoid circular imports
    from app.crud.user import get_user_by_id

    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )
    try:
        payload = decode_token(credentials.credentials)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise exc
    except JWTError:
        raise exc

    user = await get_user_by_id(db, int(user_id))
    if user is None:
        raise exc
    return user


async def _get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_optional)],
    db: DBSession,
):
    """Returns the authenticated user or None if no/invalid token is provided."""
    if credentials is None:
        return None
    from app.crud.user import get_user_by_id

    try:
        payload = decode_token(credentials.credentials)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None

    return await get_user_by_id(db, int(user_id))


CurrentUser = Annotated[Any, Depends(_get_current_user)]
OptionalUser = Annotated[Any, Depends(_get_optional_user)]
