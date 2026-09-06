"""Registration, sign-in and token refresh."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from .. import presenters, security
from ..config import settings
from ..database import schemas
from ..database.crud import users as users_crud
from ..dependencies import CurrentUser, DBSession

router = APIRouter(prefix="/auth", tags=["auth"])

INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect username or password",
    headers={"WWW-Authenticate": "Bearer"},
)


def _token_for(user, db) -> schemas.AuthResponse:
    return schemas.AuthResponse(
        access_token=security.create_access_token(user.id),
        token_type=security.TOKEN_TYPE,
        expires_in=settings.access_token_expire_minutes * 60,
        user=presenters.current_user(db, user),
    )


@router.post(
    "/register",
    response_model=schemas.AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: schemas.RegisterRequest, db: DBSession):
    if users_crud.username_taken(db, payload.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username is already taken"
        )
    if users_crud.email_taken(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that e-mail already exists",
        )

    user = users_crud.create_user(
        db,
        username=payload.username,
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
    )
    return _token_for(user, db)


@router.post("/login", response_model=schemas.AuthResponse)
def login(payload: schemas.LoginRequest, db: DBSession):
    user = users_crud.get_user_by_identifier(db, payload.identifier)
    if user is None or not security.verify_password(
        payload.password, user.hashed_password
    ):
        raise INVALID_CREDENTIALS
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
        )
    return _token_for(user, db)


@router.post("/token", response_model=schemas.Token)
def login_form(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DBSession
):
    """OAuth2 password flow — used by the interactive API docs."""
    user = users_crud.get_user_by_identifier(db, form_data.username)
    if user is None or not security.verify_password(
        form_data.password, user.hashed_password
    ):
        raise INVALID_CREDENTIALS
    return schemas.Token(
        access_token=security.create_access_token(user.id),
        token_type=security.TOKEN_TYPE,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=schemas.AuthResponse)
def refresh(current_user: CurrentUser, db: DBSession):
    """Exchange a still-valid token for a fresh one (called on app launch)."""
    return _token_for(current_user, db)


@router.get("/me", response_model=schemas.CurrentUser)
def read_me(current_user: CurrentUser, db: DBSession):
    return presenters.current_user(db, current_user)
