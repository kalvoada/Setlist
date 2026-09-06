"""Profiles, account settings, search and the follow graph."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query, Response, status

from .. import presenters, security
from ..database import models, schemas
from ..database.crud import follows as follows_crud
from ..database.crud import posts as posts_crud
from ..database.crud import users as users_crud
from ..dependencies import CurrentUser, DBSession, OptionalUser, PageParams

router = APIRouter(prefix="/users", tags=["users"])


def _get_user_or_404(db, user_id: int) -> models.DBUser:
    user = users_crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _follow_state(db, target: models.DBUser, viewer: models.DBUser) -> schemas.FollowState:
    return schemas.FollowState(
        user_id=target.id,
        is_following=follows_crud.is_following(db, viewer.id, target.id),
        followers_count=follows_crud.followers_count(db, target.id),
    )


# ── The signed-in user ────────────────────────────────────────────────────────
@router.get("/me", response_model=schemas.CurrentUser)
def read_current_user(current_user: CurrentUser, db: DBSession):
    return presenters.current_user(db, current_user)


@router.patch("/me", response_model=schemas.CurrentUser)
def update_profile(
    payload: schemas.ProfileUpdate, current_user: CurrentUser, db: DBSession
):
    """Settings › Edit profile: display name, bio, avatar."""
    user = users_crud.update_profile(db, current_user, payload)
    return presenters.current_user(db, user)


@router.patch("/me/account", response_model=schemas.CurrentUser)
def update_account(
    payload: schemas.AccountUpdate, current_user: CurrentUser, db: DBSession
):
    """Settings › Account: username, e-mail, password (password confirmed)."""
    if not security.verify_password(
        payload.current_password, current_user.hashed_password
    ):
        raise HTTPException(status_code=403, detail="Current password is incorrect")

    if payload.username and users_crud.username_taken(
        db, payload.username, exclude_user_id=current_user.id
    ):
        raise HTTPException(status_code=409, detail="Username is already taken")
    if payload.email and users_crud.email_taken(
        db, payload.email, exclude_user_id=current_user.id
    ):
        raise HTTPException(
            status_code=409, detail="An account with that e-mail already exists"
        )

    user = users_crud.update_account(db, current_user, payload)
    return presenters.current_user(db, user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    payload: schemas.AccountDelete, current_user: CurrentUser, db: DBSession
):
    """Permanently delete the account and everything attached to it."""
    if not security.verify_password(
        payload.current_password, current_user.hashed_password
    ):
        raise HTTPException(status_code=403, detail="Current password is incorrect")

    users_crud.delete_user(db, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Discovery ─────────────────────────────────────────────────────────────────
@router.get("/search", response_model=schemas.Page[schemas.UserSummary])
def search_users(
    db: DBSession,
    viewer: OptionalUser,
    page: PageParams,
    q: str = Query(min_length=1, max_length=50),
):
    users, total = users_crud.search_users(db, q, limit=page.limit, offset=page.offset)
    return presenters.page(
        presenters.user_summaries(db, users, viewer),
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/suggested", response_model=List[schemas.UserSummary])
def suggested_users(
    db: DBSession, viewer: OptionalUser, limit: int = Query(10, ge=1, le=50)
):
    """Accounts to follow — powers the empty state of the home feed."""
    users = users_crud.suggested_users(db, viewer, limit=limit)
    return presenters.user_summaries(db, users, viewer)


@router.get("/by-username/{username}", response_model=schemas.UserProfile)
def read_user_by_username(username: str, db: DBSession, viewer: OptionalUser):
    user = users_crud.get_user_by_username(db, username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return presenters.user_profile(db, user, viewer)


@router.get("/{user_id}", response_model=schemas.UserProfile)
def read_user(user_id: int, db: DBSession, viewer: OptionalUser):
    return presenters.user_profile(db, _get_user_or_404(db, user_id), viewer)


@router.get("/{user_id}/posts", response_model=schemas.Page[schemas.Post])
def read_user_posts(
    user_id: int, db: DBSession, viewer: OptionalUser, page: PageParams
):
    user = _get_user_or_404(db, user_id)
    posts, total = posts_crud.list_user_posts(
        db, user.id, limit=page.limit, offset=page.offset
    )
    return presenters.page(
        presenters.posts_out(db, posts, viewer),
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


# ── Follow graph ──────────────────────────────────────────────────────────────
@router.post("/{user_id}/follow", response_model=schemas.FollowState)
def follow_user(user_id: int, current_user: CurrentUser, db: DBSession):
    target = _get_user_or_404(db, user_id)
    try:
        follows_crud.follow(db, current_user.id, target.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _follow_state(db, target, current_user)


@router.delete("/{user_id}/follow", response_model=schemas.FollowState)
def unfollow_user(user_id: int, current_user: CurrentUser, db: DBSession):
    target = _get_user_or_404(db, user_id)
    follows_crud.unfollow(db, current_user.id, target.id)
    return _follow_state(db, target, current_user)


@router.get("/{user_id}/followers", response_model=schemas.Page[schemas.UserSummary])
def read_followers(
    user_id: int, db: DBSession, viewer: OptionalUser, page: PageParams
):
    user = _get_user_or_404(db, user_id)
    users, total = follows_crud.list_followers(
        db, user.id, limit=page.limit, offset=page.offset
    )
    return presenters.page(
        presenters.user_summaries(db, users, viewer),
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{user_id}/following", response_model=schemas.Page[schemas.UserSummary])
def read_following(
    user_id: int, db: DBSession, viewer: OptionalUser, page: PageParams
):
    user = _get_user_or_404(db, user_id)
    users, total = follows_crud.list_following(
        db, user.id, limit=page.limit, offset=page.offset
    )
    return presenters.page(
        presenters.user_summaries(db, users, viewer),
        total=total,
        limit=page.limit,
        offset=page.offset,
    )
