"""Follow graph persistence."""

from __future__ import annotations

from typing import List, Sequence, Set

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .. import models


def is_following(db: Session, follower_id: int, following_id: int) -> bool:
    stmt = select(func.count()).select_from(models.DBFollow).where(
        models.DBFollow.follower_id == follower_id,
        models.DBFollow.following_id == following_id,
    )
    return bool(db.scalar(stmt))


def follow(db: Session, follower_id: int, following_id: int) -> bool:
    """Create the edge. Returns ``False`` when it already existed (idempotent)."""
    if follower_id == following_id:
        raise ValueError("You cannot follow yourself.")
    if is_following(db, follower_id, following_id):
        return False

    db.add(models.DBFollow(follower_id=follower_id, following_id=following_id))
    db.commit()
    return True


def unfollow(db: Session, follower_id: int, following_id: int) -> bool:
    result = db.execute(
        delete(models.DBFollow).where(
            models.DBFollow.follower_id == follower_id,
            models.DBFollow.following_id == following_id,
        )
    )
    db.commit()
    return result.rowcount > 0


def followers_count(db: Session, user_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(models.DBFollow)
        .where(models.DBFollow.following_id == user_id)
    ) or 0


def following_count(db: Session, user_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(models.DBFollow)
        .where(models.DBFollow.follower_id == user_id)
    ) or 0


def followers_count_map(db: Session, user_ids: Sequence[int]) -> dict[int, int]:
    if not user_ids:
        return {}
    rows = db.execute(
        select(models.DBFollow.following_id, func.count())
        .where(models.DBFollow.following_id.in_(user_ids))
        .group_by(models.DBFollow.following_id)
    ).all()
    return {user_id: count for user_id, count in rows}


def following_count_map(db: Session, user_ids: Sequence[int]) -> dict[int, int]:
    if not user_ids:
        return {}
    rows = db.execute(
        select(models.DBFollow.follower_id, func.count())
        .where(models.DBFollow.follower_id.in_(user_ids))
        .group_by(models.DBFollow.follower_id)
    ).all()
    return {user_id: count for user_id, count in rows}


def following_ids(db: Session, user_id: int) -> Set[int]:
    return set(
        db.scalars(
            select(models.DBFollow.following_id).where(
                models.DBFollow.follower_id == user_id
            )
        ).all()
    )


def followed_subset(db: Session, viewer_id: int, user_ids: Sequence[int]) -> Set[int]:
    """Which of ``user_ids`` the viewer follows."""
    if not user_ids:
        return set()
    return set(
        db.scalars(
            select(models.DBFollow.following_id).where(
                models.DBFollow.follower_id == viewer_id,
                models.DBFollow.following_id.in_(user_ids),
            )
        ).all()
    )


def follower_subset(db: Session, viewer_id: int, user_ids: Sequence[int]) -> Set[int]:
    """Which of ``user_ids`` follow the viewer."""
    if not user_ids:
        return set()
    return set(
        db.scalars(
            select(models.DBFollow.follower_id).where(
                models.DBFollow.following_id == viewer_id,
                models.DBFollow.follower_id.in_(user_ids),
            )
        ).all()
    )


def list_followers(
    db: Session, user_id: int, *, limit: int = 20, offset: int = 0
) -> tuple[List[models.DBUser], int]:
    total = followers_count(db, user_id)
    stmt = (
        select(models.DBUser)
        .join(models.DBFollow, models.DBFollow.follower_id == models.DBUser.id)
        .where(models.DBFollow.following_id == user_id)
        .order_by(models.DBFollow.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all()), total


def list_following(
    db: Session, user_id: int, *, limit: int = 20, offset: int = 0
) -> tuple[List[models.DBUser], int]:
    total = following_count(db, user_id)
    stmt = (
        select(models.DBUser)
        .join(models.DBFollow, models.DBFollow.following_id == models.DBUser.id)
        .where(models.DBFollow.follower_id == user_id)
        .order_by(models.DBFollow.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all()), total
