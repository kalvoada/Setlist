"""User, profile and account persistence."""

from __future__ import annotations

from typing import List, Optional, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ... import security
from .. import models, schemas


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def get_user(db: Session, user_id: int) -> Optional[models.DBUser]:
    return db.get(models.DBUser, user_id)


def get_user_by_username(db: Session, username: str) -> Optional[models.DBUser]:
    stmt = select(models.DBUser).where(
        func.lower(models.DBUser.username) == (username or "").strip().lower()
    )
    return db.scalars(stmt).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.DBUser]:
    stmt = select(models.DBUser).where(models.DBUser.email == normalize_email(email))
    return db.scalars(stmt).first()


def get_user_by_identifier(db: Session, identifier: str) -> Optional[models.DBUser]:
    """Look a user up by username *or* e-mail (used by login)."""
    value = (identifier or "").strip().lower()
    stmt = select(models.DBUser).where(
        or_(
            func.lower(models.DBUser.username) == value,
            models.DBUser.email == value,
        )
    )
    return db.scalars(stmt).first()


def username_taken(db: Session, username: str, exclude_user_id: int | None = None) -> bool:
    existing = get_user_by_username(db, username)
    return existing is not None and existing.id != exclude_user_id


def email_taken(db: Session, email: str, exclude_user_id: int | None = None) -> bool:
    existing = get_user_by_email(db, email)
    return existing is not None and existing.id != exclude_user_id


def create_user(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
    display_name: Optional[str] = None,
) -> models.DBUser:
    user = models.DBUser(
        username=username.strip(),
        email=normalize_email(email),
        hashed_password=security.hash_password(password),
        display_name=(display_name or "").strip() or None,
        bio="",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_profile(
    db: Session, user: models.DBUser, payload: schemas.ProfileUpdate
) -> models.DBUser:
    data = payload.model_dump(exclude_unset=True)

    if "display_name" in data:
        value = (data["display_name"] or "").strip()
        user.display_name = value or None
    if "bio" in data:
        user.bio = (data["bio"] or "").strip()
    if "avatar_url" in data:
        value = (data["avatar_url"] or "").strip()
        user.avatar_url = value or None

    db.commit()
    db.refresh(user)
    return user


def update_account(
    db: Session, user: models.DBUser, payload: schemas.AccountUpdate
) -> models.DBUser:
    """Apply username / e-mail / password changes. Callers verify the password."""
    if payload.username is not None:
        user.username = payload.username.strip()
    if payload.email is not None:
        user.email = normalize_email(payload.email)
    if payload.new_password is not None:
        user.hashed_password = security.hash_password(payload.new_password)

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: models.DBUser) -> None:
    db.delete(user)
    db.commit()


def search_users(
    db: Session, query: str, *, limit: int = 20, offset: int = 0
) -> tuple[List[models.DBUser], int]:
    """Search by username or display name, most-followed first."""
    term = f"%{(query or '').strip().lower()}%"
    condition = or_(
        func.lower(models.DBUser.username).like(term),
        func.lower(func.coalesce(models.DBUser.display_name, "")).like(term),
    )

    total = db.scalar(
        select(func.count()).select_from(models.DBUser).where(condition)
    ) or 0

    followers = (
        select(
            models.DBFollow.following_id.label("user_id"),
            func.count().label("followers"),
        )
        .group_by(models.DBFollow.following_id)
        .subquery()
    )

    stmt = (
        select(models.DBUser)
        .outerjoin(followers, followers.c.user_id == models.DBUser.id)
        .where(condition)
        .order_by(func.coalesce(followers.c.followers, 0).desc(), models.DBUser.username)
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all()), total


def suggested_users(
    db: Session, viewer: Optional[models.DBUser], *, limit: int = 20
) -> List[models.DBUser]:
    """People to follow: most followed accounts the viewer does not follow yet."""
    followers = (
        select(
            models.DBFollow.following_id.label("user_id"),
            func.count().label("followers"),
        )
        .group_by(models.DBFollow.following_id)
        .subquery()
    )

    stmt = (
        select(models.DBUser)
        .outerjoin(followers, followers.c.user_id == models.DBUser.id)
        .order_by(func.coalesce(followers.c.followers, 0).desc(), models.DBUser.id)
        .limit(limit)
    )

    if viewer is not None:
        already_following = select(models.DBFollow.following_id).where(
            models.DBFollow.follower_id == viewer.id
        )
        stmt = stmt.where(
            models.DBUser.id != viewer.id,
            models.DBUser.id.not_in(already_following),
        )

    return list(db.scalars(stmt).all())


def posts_count_map(db: Session, user_ids: Sequence[int]) -> dict[int, int]:
    if not user_ids:
        return {}
    rows = db.execute(
        select(models.DBPost.user_id, func.count())
        .where(models.DBPost.user_id.in_(user_ids))
        .group_by(models.DBPost.user_id)
    ).all()
    return {user_id: count for user_id, count in rows}
