"""Shared FastAPI dependencies: authentication and pagination."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import security
from .database import models
from .database.crud import users as users_crud
from .database.database import get_db

# ``auto_error=False`` lets endpoints stay readable for both the "must be
# signed in" and the "nice to know who you are" cases.
_bearer = HTTPBearer(auto_error=False)

DBSession = Annotated[Session, Depends(get_db)]
_Credentials = Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)]

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_optional_user(
    db: DBSession, credentials: _Credentials = None
) -> Optional[models.DBUser]:
    """Resolve the caller when a valid token is present, else ``None``."""
    if credentials is None or not credentials.credentials:
        return None

    user_id = security.decode_access_token(credentials.credentials)
    if user_id is None:
        return None

    user = users_crud.get_user(db, user_id)
    if user is None or not user.is_active:
        return None
    return user


def get_current_user(
    db: DBSession, credentials: _Credentials = None
) -> models.DBUser:
    """Require a signed-in caller."""
    user = get_optional_user(db, credentials)
    if user is None:
        raise CREDENTIALS_EXCEPTION
    return user


CurrentUser = Annotated[models.DBUser, Depends(get_current_user)]
OptionalUser = Annotated[Optional[models.DBUser], Depends(get_optional_user)]


@dataclass
class Pagination:
    limit: int
    offset: int


def pagination(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Pagination:
    return Pagination(limit=limit, offset=offset)


PageParams = Annotated[Pagination, Depends(pagination)]
